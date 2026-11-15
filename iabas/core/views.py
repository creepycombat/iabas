# =============================================================================
# Archivo        : iabas/core/views.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Vistas: panel del administrador, bandeja del colaborador, seguimiento, reforzamiento y riesgo.
# Modificaciones :
#   12-11-2026  Se agregaron las vistas de riesgo (panel, recalcular, reentrenar) y las exportaciones CSV.
#   14-11-2026  Se agregó el encabezado de documentación.
#   15-11-2026  La vista de reforzamiento entrega el análisis del correo y el contenido formativo ampliado.
#   15-11-2026  Los CSV se abren bien en Excel en español (separador ";" y codificación UTF-8 con BOM) y la fecha va en hora local.
# Notas          : Archivo original de Alexis Villegas. Las modificaciones fueron hechas por
#                  Marcelo Herquiñigo Vargas al integrar el módulo de riesgo con ML.
# =============================================================================
import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import ml_client, services
from . import riesgo as riesgo_svc
from .models import Campana, Consentimiento, EventoComportamiento, Simulacion
from .refuerzo_contenido import (CHECKLIST, POR_QUE_FUNCIONAN, PREGUNTAS, QUE_HACER_CLIC, QUE_HACER_DATOS,
                                 SENALES, analizar_correo)

# GIF transparente de 1x1 (pixel de apertura)
PIXEL = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
         b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


def es_admin(u):
    return u.is_authenticated and (u.is_staff or u.groups.filter(name="admin_seguridad").exists())


admin_requerido = user_passes_test(es_admin, login_url="/login/")


@login_required
def inicio(request):
    return redirect("panel" if es_admin(request.user) else "bandeja")


# ---------- Administrador de seguridad ----------
@admin_requerido
def panel(request):
    filas = []
    for c in Campana.objects.select_related("consentimiento").order_by("-creada"):
        n = c.simulaciones.count()
        ev = EventoComportamiento.objects.filter(simulacion__campana=c)
        filas.append({
            "c": c, "n": n,
            "destinatarios": services.destinatarios(c).count(),
            "clic": round(100 * ev.filter(tipo="clic").count() / n) if n else None,
            "reporte": round(100 * ev.filter(tipo="reporte").count() / n) if n else None,
        })
    return render(request, "core/panel.html", {"filas": filas})


@admin_requerido
@require_POST
def ejecutar_campana(request, pk):
    c = get_object_or_404(Campana, pk=pk)
    try:
        n = services.lanzar_campana(c)
        messages.success(request, f"Campaña ejecutada: {n} correos simulados enviados.")
    except services.ConsentimientoRequerido as e:
        messages.error(request, str(e))
    except services.CampanaInvalida as e:
        messages.warning(request, str(e))
    return redirect("panel")


@admin_requerido
@require_POST
def registrar_consentimiento(request, pk):
    c = get_object_or_404(Campana, pk=pk)
    if not request.POST.get("acepto"):
        messages.error(request, "Debes confirmar el consentimiento para registrarlo.")
        return redirect("panel")
    c.consentimiento = Consentimiento.objects.create(
        organizacion=request.POST.get("organizacion") or "Empresa Demo SpA",
        registrado_por=request.user,
        texto="La organización autoriza simulaciones de phishing con fines formativos, "
              "conforme a la Ley N.º 21.719, sin informar de forma anticipada su contenido.")
    c.save(update_fields=["consentimiento"])
    messages.success(request, "Consentimiento registrado. Ya puedes ejecutar la campaña.")
    return redirect("panel")


# ---------- Colaborador evaluado ----------
@login_required
def bandeja(request):
    sims = request.user.simulaciones.select_related("campana").order_by("-enviada")
    return render(request, "core/bandeja.html", {"sims": sims})


@login_required
def correo(request, token):
    sim = get_object_or_404(Simulacion, token=token, usuario=request.user)
    cuerpo = services.renderizar_correo(sim, request.build_absolute_uri("/").rstrip("/"))
    return render(request, "core/correo.html", {"sim": sim, "cuerpo": cuerpo})


@login_required
def privacidad(request):
    if request.method == "POST":
        services.revocar_consentimiento(request.user)
        messages.success(request, "Tu consentimiento fue revocado. No recibirás nuevas simulaciones.")
        return redirect("privacidad")
    return render(request, "core/privacidad.html")


# ---------- Tracking (públicas: se accede desde el correo, con el token) ----------
def _evento(token, tipo):
    try:
        return services.registrar_evento(token, tipo)
    except Simulacion.DoesNotExist:
        raise Http404


def pixel_apertura(request, token):
    _evento(token, "apertura")
    return HttpResponse(PIXEL, content_type="image/gif")


def clic(request, token):
    """Registra el clic y muestra un login falso. No se guarda ninguna credencial."""
    sim = _evento(token, "clic")
    if request.method == "POST":
        _evento(token, "datos")   # solo el evento: nunca se lee ni guarda la clave
        return redirect("refuerzo", token=token)
    return render(request, "core/login_falso.html", {"sim": sim})


def reportar(request, token):
    sim = _evento(token, "reporte")
    return render(request, "core/reporte_ok.html", {"sim": sim})


def refuerzo(request, token):
    sim = get_object_or_404(Simulacion, token=token)
    if not hasattr(sim, "reforzamiento"):
        raise Http404
    ref = sim.reforzamiento
    ctx = {"sim": sim, "ref": ref, "senales": SENALES, "preguntas": list(enumerate(PREGUNTAS))}
    # 15-11-2026 (Marcelo): contenido formativo según lo que hizo la persona y el correo que recibió
    ingreso_datos = "datos" in sim.tipos_eventos()
    ctx.update(hallazgos=analizar_correo(sim.campana, request.get_host()), por_que=POR_QUE_FUNCIONAN,
               que_hacer=QUE_HACER_DATOS if ingreso_datos else QUE_HACER_CLIC,
               ingreso_datos=ingreso_datos, checklist=CHECKLIST)
    if request.method == "POST" and not ref.completado:
        resultados, aciertos = [], 0
        for i, p in enumerate(PREGUNTAS):
            ok = request.POST.get(f"p{i}") == str(p["correcta"])
            aciertos += ok
            resultados.append({"p": p, "ok": ok, "elegida": request.POST.get(f"p{i}")})
        services.completar_reforzamiento(sim, aciertos, len(PREGUNTAS))
        ctx.update(resultados=resultados, aciertos=aciertos, total=len(PREGUNTAS))
    ctx["ref"] = sim.reforzamiento
    return render(request, "core/refuerzo.html", ctx)


# =============================================================================================
# Añadido el 12-11-2026 (Marcelo Herquiñigo): riesgo con ML (RF-06/07/08) y exportación (RF-12)
# =============================================================================================
@admin_requerido
def riesgo(request):
    """Panel de riesgo: modelo vigente, niveles, promedio por grupo y ranking de usuarios."""
    return render(request, "core/riesgo.html", {"r": riesgo_svc.resumen(), "modelo": riesgo_svc.estado_modelo()})


@admin_requerido
@require_POST
def riesgo_recalcular(request):
    """Pide al servicio ML los puntajes actuales (normalmente corre solo cada 24 h, RNF-04)."""
    try:
        r = riesgo_svc.recalcular()
        if r["actualizados"]:
            messages.success(request, f"Puntajes actualizados: {r['actualizados']} usuarios (modelo v{r['version_modelo']}).")
        else:
            messages.warning(request, "Todavía no hay simulaciones ejecutadas para calcular puntajes.")
    except ml_client.MLNoDisponible as e:
        messages.error(request, str(e))
    return redirect("riesgo")


@admin_requerido
@require_POST
def riesgo_reentrenar(request):
    """Proceso 3: reentrena con los datos de la plataforma; solo reemplaza el modelo si AUC >= 0,80."""
    try:
        r = riesgo_svc.reentrenar_con_datos_de_la_plataforma()
    except ml_client.MLNoDisponible as e:
        messages.error(request, str(e))
        return redirect("riesgo")
    auc = r["resultados"][r["mejor"]]["auc"]
    if r["decision"] == "conservado":
        messages.warning(request, f"Reentrenamiento: AUC {auc:.3f} < {r['meta_auc']:.2f}. No cumple la meta, "
                                  f"se conserva el modelo vigente v{r['version_vigente']}.")
    elif r["decision"] == "reemplazado":
        messages.success(request, f"Reentrenamiento: AUC {auc:.3f} cumple la meta. Nuevo modelo vigente v{r['version_vigente']}.")
    else:
        messages.success(request, f"Modelo inicial v{r['version_vigente']} registrado (AUC {auc:.3f}).")
    return redirect("riesgo")


def _csv(nombre):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
    resp.write("\ufeff")   # 15-11-2026: marca UTF-8 para que Excel muestre bien las tildes
    return resp, csv.writer(resp, delimiter=";")   # ";" es el separador que Excel usa en configuración regional chilena


@admin_requerido
def exportar_campana(request, pk):
    """RF-12: resultados de una campaña por usuario (sin correos electrónicos)."""
    c = get_object_or_404(Campana, pk=pk)
    resp, w = _csv(f"campana_{c.pk}.csv")
    w.writerow(["usuario", "grupo", "abrio", "clic", "ingreso_datos", "reporto", "nota_reforzamiento"])
    for s in c.simulaciones.select_related("usuario__perfil__grupo", "reforzamiento").prefetch_related("eventos"):
        t = {e.tipo for e in s.eventos.all()}
        grupo = s.usuario.perfil.grupo.nombre if getattr(s.usuario, "perfil", None) and s.usuario.perfil.grupo else ""
        ref = getattr(s, "reforzamiento", None)
        w.writerow([s.usuario.username, grupo, int("apertura" in t), int(bool(t & {"clic", "datos"})),
                    int("datos" in t), int("reporte" in t), "" if ref is None or ref.nota is None else ref.nota])
    return resp


@admin_requerido
def exportar_riesgo(request):
    """RF-12: último puntaje de riesgo de cada usuario."""
    resp, w = _csv("riesgo.csv")
    w.writerow(["usuario", "grupo", "puntaje", "nivel", "version_modelo", "fecha"])
    for f in riesgo_svc.ultimos_puntajes():
        w.writerow([f["usuario"].username, f["grupo"], f["valor"], f["nivel"],
                    f["modelo"].version if f["modelo"] else "", timezone.localtime(f["fecha"]).strftime("%Y-%m-%d %H:%M")])
    return resp
