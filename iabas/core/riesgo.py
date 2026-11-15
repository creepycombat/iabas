# =============================================================================
# Archivo        : iabas/core/riesgo.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Puntaje de riesgo (RF-06/07): arma las características desde los eventos, consulta al
#                  servicio ML, guarda el historial de puntajes y entrega los resúmenes del panel de riesgo.
# Modificaciones :
#   12-11-2026  Creación inicial (adaptada del backend DRF a los modelos de la versión de Alexis).
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
# Notas          :
#   - Las columnas deben coincidir con dataset_entrenamiento.csv (ml/generar_datos.py).
#   - Un usuario "cayó" en una simulación si hizo clic o ingresó datos (evento 'datos').
#   - Los datos de la demo son SIMULADOS: el AUC refleja el generador, no el mundo real.
# =============================================================================
from collections import defaultdict
from datetime import date

from django.contrib.auth.models import User

from . import ml_client
from .models import ModeloML, PuntajeRiesgo, Simulacion


# ---------------------------------------------------------------------------------------------
# 1) Características (features) a partir del historial de eventos
# ---------------------------------------------------------------------------------------------
def _cayo(sim):
    """Una simulación es fallida si hubo clic o ingreso de datos."""
    return bool({e.tipo for e in sim.eventos.all()} & {"clic", "datos"})


def _historial(usuario):
    """Simulaciones ya ejecutadas del usuario, en orden cronológico."""
    return list(Simulacion.objects.filter(usuario=usuario, campana__estado="ejecutada")
                .select_related("campana", "reforzamiento").prefetch_related("eventos")
                .order_by("campana__ejecutada", "id"))


def _features(usuario, sims, hoy):
    """Calcula las características con el historial `sims` (las columnas del dataset de entrenamiento)."""
    n = len(sims)
    clics = ingresos = reportes = 0
    minutos, notas, ultimo_fallo = [], [], None
    for i, s in enumerate(sims):
        eventos = list(s.eventos.all())
        tipos = {e.tipo for e in eventos}
        clic = bool(tipos & {"clic", "datos"})      # ingresar datos implica haber hecho clic
        clics += clic
        ingresos += "datos" in tipos
        reportes += "reporte" in tipos
        if clic:
            ultimo_fallo = i
        aperturas = [e.fecha for e in eventos if e.tipo == "apertura"]
        if aperturas:
            minutos.append(max((min(aperturas) - s.enviada).total_seconds() / 60.0, 0.0))
        ref = getattr(s, "reforzamiento", None)     # la evaluación se rinde una sola vez (Proceso 2)
        if ref is not None and ref.nota is not None:
            notas.append(ref.nota)
    ingreso = usuario.perfil.fecha_ingreso
    meses = max((hoy.year - ingreso.year) * 12 + (hoy.month - ingreso.month), 0) if ingreso else 0
    grupo = usuario.perfil.grupo
    return {
        "usuario_id": usuario.pk,
        "campana_actual": n,
        "grupo": grupo.nombre if grupo else "",
        "antiguedad_meses": meses,
        "n_simulaciones": n,
        "n_clics": clics,
        "tasa_clic": round(clics / n, 4),
        "n_ingresos_datos": ingresos,
        "n_reportes": reportes,
        "tasa_reporte": round(reportes / n, 4),
        "minutos_apertura_medio": round(sum(minutos) / len(minutos), 2) if minutos else None,
        "evaluacion_promedio": round(sum(notas) / len(notas), 2) if notas else None,
        "campanas_desde_ultimo_fallo": (n - 1 - ultimo_fallo) if ultimo_fallo is not None else n,
    }


def _colaboradores():
    return User.objects.filter(is_active=True, is_staff=False, perfil__isnull=False).select_related("perfil__grupo")


def construir_features(usuario, hoy=None):
    """Características actuales de un usuario. None si todavía no tiene simulaciones."""
    sims = _historial(usuario)
    return _features(usuario, sims, hoy or date.today()) if sims else None


def filas_entrenamiento(hoy=None):
    """Filas para reentrenar con los datos de la plataforma: historial hasta la simulación i y
    etiqueta 'cayó en la siguiente' (i+1). Misma definición que ml/generar_datos.py."""
    hoy = hoy or date.today()
    filas = []
    for u in _colaboradores():
        sims = _historial(u)
        for i in range(len(sims) - 1):
            fila = _features(u, sims[: i + 1], hoy)
            fila["cayo_en_siguiente"] = int(_cayo(sims[i + 1]))
            filas.append(fila)
    return filas


# ---------------------------------------------------------------------------------------------
# 2) Cálculo y guardado de puntajes (RF-06)
# ---------------------------------------------------------------------------------------------
def _registrar_modelo(version):
    """Deja en la tabla ModeloML el modelo con que se calcularon los puntajes (trazabilidad, RNF-07)."""
    try:
        info = ml_client.salud().get("modelo") or {}
    except ml_client.MLNoDisponible:
        info = {}
    modelo, _ = ModeloML.objects.update_or_create(
        version=version, defaults={"auc": info.get("auc", 0.0), "archivo": f"modelo_v{version}.joblib"})
    ModeloML.objects.exclude(pk=modelo.pk).update(vigente=False)
    if not modelo.vigente:
        modelo.vigente = True
        modelo.save(update_fields=["vigente"])
    return modelo


def recalcular():
    """Calcula y guarda el puntaje de todos los colaboradores con historial. Devuelve un resumen."""
    filas = [f for f in (construir_features(u) for u in _colaboradores()) if f]
    if not filas:
        return {"actualizados": 0, "version_modelo": None}
    datos = ml_client.puntuar(filas)
    modelo = _registrar_modelo(datos["version_modelo"])
    PuntajeRiesgo.objects.bulk_create([
        PuntajeRiesgo(usuario_id=p["usuario_id"], valor=p["puntaje"], nivel=p["nivel"], modelo=modelo)
        for p in datos["puntajes"]])
    return {"actualizados": len(datos["puntajes"]), "version_modelo": datos["version_modelo"]}


def reentrenar_con_datos_de_la_plataforma():
    """Proceso 3: reentrena con el historial acumulado. El servicio solo reemplaza el modelo si AUC >= 0,80."""
    filas = filas_entrenamiento()
    if not filas:
        raise ml_client.MLNoDisponible("Aún no hay historial suficiente para reentrenar")
    return ml_client.reentrenar(filas)


# ---------------------------------------------------------------------------------------------
# 3) Consultas para el panel de riesgo (RF-07, RF-08)
# ---------------------------------------------------------------------------------------------
def ultimos_puntajes():
    """Último puntaje de cada usuario (y el anterior, para mostrar el cambio), de mayor a menor riesgo."""
    por_usuario = defaultdict(list)
    for p in (PuntajeRiesgo.objects.select_related("usuario__perfil__grupo", "modelo").order_by("-fecha", "-id")):
        if len(por_usuario[p.usuario_id]) < 2:
            por_usuario[p.usuario_id].append(p)
    filas = []
    for pts in por_usuario.values():
        actual = pts[0]
        anterior = pts[1].valor if len(pts) > 1 else None
        grupo = actual.usuario.perfil.grupo if hasattr(actual.usuario, "perfil") else None
        filas.append({"usuario": actual.usuario, "grupo": grupo.nombre if grupo else "Sin grupo",
                      "valor": actual.valor, "nivel": actual.nivel, "fecha": actual.fecha,
                      "modelo": actual.modelo, "cambio": None if anterior is None else round(actual.valor - anterior, 1)})
    return sorted(filas, key=lambda f: -f["valor"])


def resumen():
    """Vista priorizada 80/20: niveles, promedio por grupo y los 10 usuarios de mayor riesgo."""
    filas = ultimos_puntajes()
    niveles = {"alto": 0, "medio": 0, "bajo": 0}
    por_grupo = defaultdict(list)
    for f in filas:
        niveles[f["nivel"]] = niveles.get(f["nivel"], 0) + 1
        por_grupo[f["grupo"]].append(f["valor"])
    grupos = sorted(({"grupo": g, "medio": round(sum(v) / len(v), 1), "usuarios": len(v)} for g, v in por_grupo.items()),
                    key=lambda x: -x["medio"])
    return {"total": len(filas), "niveles": niveles, "por_grupo": grupos, "top": filas[:10], "todos": filas}


def estado_modelo():
    """Modelo vigente según el servicio ML, o None si el servicio no responde."""
    try:
        return ml_client.salud()
    except ml_client.MLNoDisponible:
        return None
