# =============================================================================
# Archivo        : iabas/core/tests/test_riesgo.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Pruebas del puntaje de riesgo, la integración con el servicio ML (simulado) y el panel de riesgo.
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
#   15-11-2026  Prueba de CSV ajustada al separador ";" y a la codificación UTF-8 con BOM.
# Notas          : Cubre CP-06, CP-07, CP-08, CP-16 (lógica) y CP-19. El servicio ML se reemplaza por funciones falsas.
# =============================================================================
from datetime import date

import pytest
from django.utils import timezone

from core import ml_client, riesgo
from core.models import ModeloML, PuntajeRiesgo
from core.tests.conftest import cliente_de, crear_campana, crear_colab, crear_sim

pytestmark = pytest.mark.django_db
HOY = date(2026, 11, 12)


@pytest.fixture
def historial(ana, consentimiento, grupos):
    """3 campañas: cae en la 1ª (con reforzamiento evaluado), reporta en la 2ª y no abre la 3ª."""
    base = timezone.now() - timezone.timedelta(days=90)
    camps = [crear_campana(consentimiento, grupos, f"C{k}", "ejecutada", base + timezone.timedelta(days=30 * k))
             for k in range(3)]
    crear_sim(ana, camps[0], [("apertura", 10), ("clic", 11)], nota=70.0)
    crear_sim(ana, camps[1], [("reporte", 5)])
    crear_sim(ana, camps[2], [])
    return camps


def ml_falso(version=1, valor=40.0, auc=0.75):
    """Reemplaza al servicio ML: devuelve el mismo puntaje para todos y un modelo con el AUC indicado."""
    def puntuar(filas):
        nivel = "alto" if valor >= 50 else "medio" if valor >= 30 else "bajo"
        return {"version_modelo": version, "puntajes": [{"usuario_id": f["usuario_id"], "puntaje": valor, "nivel": nivel} for f in filas]}
    def salud():
        return {"estado": "ok", "modelo": {"version": version, "algoritmo": "regresion_logistica", "auc": auc, "cumple_meta": auc >= 0.8}}
    return puntuar, salud


# --- CP-06: características e historial ----------------------------------------------------
def test_cp06_caracteristicas_coinciden_con_el_dataset_de_entrenamiento(historial, ana):
    f = riesgo.construir_features(ana, HOY)
    assert (f["n_simulaciones"], f["n_clics"], f["n_ingresos_datos"], f["n_reportes"]) == (3, 1, 0, 1)
    assert f["tasa_clic"] == round(1 / 3, 4) and f["tasa_reporte"] == round(1 / 3, 4)
    assert f["minutos_apertura_medio"] == 10.0 and f["evaluacion_promedio"] == 70.0
    assert f["campanas_desde_ultimo_fallo"] == 2        # falló en la 1ª de 3 -> n-1-0
    assert f["grupo"] == "Finanzas" and f["antiguedad_meses"] == 10
    assert set(f) == {"usuario_id", "campana_actual", "grupo", "antiguedad_meses", "n_simulaciones", "n_clics",
                      "tasa_clic", "n_ingresos_datos", "n_reportes", "tasa_reporte", "minutos_apertura_medio",
                      "evaluacion_promedio", "campanas_desde_ultimo_fallo"}


def test_cp06_ingresar_datos_cuenta_como_clic(ana, consentimiento, grupos):
    c = crear_campana(consentimiento, grupos, "C", "ejecutada", timezone.now())
    crear_sim(ana, c, [("datos", 3)])
    f = riesgo.construir_features(ana, HOY)
    assert f["n_clics"] == 1 and f["n_ingresos_datos"] == 1


def test_cp06_sin_historial_no_hay_caracteristicas(ana):
    assert riesgo.construir_features(ana, HOY) is None


def test_cp06_filas_de_entrenamiento_y_etiqueta(historial, ana, consentimiento, grupos):
    c4 = crear_campana(consentimiento, grupos, "C3", "ejecutada", timezone.now())
    crear_sim(ana, c4, [("clic", 4)])                    # la 4ª simulación sí falla
    filas = riesgo.filas_entrenamiento(HOY)
    assert [f["cayo_en_siguiente"] for f in filas] == [0, 0, 1]    # etiqueta = resultado de la simulación siguiente
    assert [f["n_simulaciones"] for f in filas] == [1, 2, 3]


# --- CP-07 / RNF-04: cálculo y registro de puntajes ---------------------------------------
def test_cp07_recalcular_guarda_puntajes_y_registra_el_modelo(historial, ana, monkeypatch):
    puntuar, salud = ml_falso(version=1, valor=62.0, auc=0.747)
    monkeypatch.setattr(ml_client, "puntuar", puntuar)
    monkeypatch.setattr(ml_client, "salud", salud)
    assert riesgo.recalcular() == {"actualizados": 1, "version_modelo": 1}
    p = PuntajeRiesgo.objects.get()
    assert (p.valor, p.nivel, p.modelo.version) == (62.0, "alto", 1)
    assert ModeloML.objects.get().vigente and ModeloML.objects.get().auc == 0.747


def test_cp07_nueva_version_del_modelo_pasa_a_vigente(historial, monkeypatch):
    for version in (1, 2):
        puntuar, salud = ml_falso(version=version)
        monkeypatch.setattr(ml_client, "puntuar", puntuar)
        monkeypatch.setattr(ml_client, "salud", salud)
        riesgo.recalcular()
    assert list(ModeloML.objects.filter(vigente=True).values_list("version", flat=True)) == [2]


def test_cp07_sin_simulaciones_no_llama_al_ml(ana, monkeypatch):
    monkeypatch.setattr(ml_client, "puntuar", lambda f: pytest.fail("no debía llamar al ML"))
    assert riesgo.recalcular() == {"actualizados": 0, "version_modelo": None}


def test_cp07_cambio_respecto_al_puntaje_anterior(historial, ana, monkeypatch):
    monkeypatch.setattr(ml_client, "salud", ml_falso()[1])
    for valor in (30.0, 45.5):
        monkeypatch.setattr(ml_client, "puntuar", ml_falso(valor=valor)[0])
        riesgo.recalcular()
    f = riesgo.ultimos_puntajes()[0]
    assert (f["valor"], f["cambio"], f["nivel"]) == (45.5, 15.5, "medio")


# --- CP-08: panel de riesgo ---------------------------------------------------------------
def test_cp08_resumen_prioriza_por_riesgo_y_agrupa(historial, ana, beto, consentimiento, grupos, monkeypatch):
    crear_sim(beto, historial[0], [])
    monkeypatch.setattr(ml_client, "salud", ml_falso()[1])
    def puntuar(filas):
        v = {ana.pk: 70.0, beto.pk: 20.0}
        return {"version_modelo": 1, "puntajes": [{"usuario_id": f["usuario_id"], "puntaje": v[f["usuario_id"]],
                "nivel": "alto" if v[f["usuario_id"]] >= 50 else "bajo"} for f in filas]}
    monkeypatch.setattr(ml_client, "puntuar", puntuar)
    riesgo.recalcular()
    r = riesgo.resumen()
    assert r["niveles"] == {"alto": 1, "medio": 0, "bajo": 1}
    assert r["top"][0]["usuario"] == ana and [g["grupo"] for g in r["por_grupo"]] == ["Finanzas", "TI"]


def test_cp08_pagina_de_riesgo_con_datos_y_sin_servicio(historial, cliente_admin, monkeypatch):
    monkeypatch.setattr(ml_client, "salud", ml_falso(auc=0.75)[1])
    monkeypatch.setattr(ml_client, "puntuar", ml_falso(valor=62.0)[0])
    riesgo.recalcular()
    html = cliente_admin.get("/panel/riesgo/").content.decode()
    assert "No cumple la meta" in html and "Riesgo alto" in html and "Ana" in html

    def caido():
        raise ml_client.MLNoDisponible("caído")
    monkeypatch.setattr(ml_client, "salud", caido)
    assert "Servicio ML no disponible" in cliente_admin.get("/panel/riesgo/").content.decode()


def test_cp08_recalcular_con_ml_caido_muestra_error_y_no_falla(historial, cliente_admin, monkeypatch):
    def caido(filas):
        raise ml_client.MLNoDisponible("sin conexión")
    monkeypatch.setattr(ml_client, "puntuar", caido)
    r = cliente_admin.post("/panel/riesgo/recalcular/", follow=True)
    assert r.status_code == 200 and "sin conexión" in r.content.decode() and PuntajeRiesgo.objects.count() == 0


def test_cp08_solo_el_administrador_ve_el_riesgo(ana, historial):
    c = cliente_de(ana)
    assert c.get("/panel/riesgo/").status_code == 302
    assert c.post("/panel/riesgo/recalcular/").status_code == 302
    assert c.get("/panel/riesgo/exportar/").status_code == 302


def test_cp12_exportar_riesgo(historial, cliente_admin, monkeypatch):
    monkeypatch.setattr(ml_client, "salud", ml_falso()[1])
    monkeypatch.setattr(ml_client, "puntuar", ml_falso(valor=55.0)[0])
    riesgo.recalcular()
    csv = cliente_admin.get("/panel/riesgo/exportar/").content.decode("utf-8-sig").splitlines()
    assert csv[0] == "usuario;grupo;puntaje;nivel;version_modelo;fecha" and csv[1].startswith("ana;Finanzas;55.0;alto;1;")


# --- CP-19 / RNF-07: reentrenamiento (regla del Proceso 3) ---------------------------------
@pytest.mark.parametrize("decision,auc,texto", [
    ("conservado", 0.62, "se conserva el modelo vigente"),
    ("reemplazado", 0.84, "Nuevo modelo vigente"),
    ("inicial", 0.74, "Modelo inicial"),
])
def test_cp19_mensaje_segun_la_decision_del_servicio(historial, cliente_admin, monkeypatch, decision, auc, texto):
    ana_historial = historial                                    # asegura al menos 2 simulaciones por usuario
    assert ana_historial
    monkeypatch.setattr(ml_client, "reentrenar", lambda filas=None: {
        "decision": decision, "mejor": "regresion_logistica", "meta_auc": 0.8, "version_vigente": 2,
        "resultados": {"regresion_logistica": {"auc": auc}}})
    r = cliente_admin.post("/panel/riesgo/reentrenar/", follow=True)
    assert texto in r.content.decode()


def test_cp19_envia_filas_con_etiqueta_a_reentrenar(historial, cliente_admin, monkeypatch):
    recibido = {}
    def falso(filas=None):
        recibido["filas"] = filas
        return {"decision": "conservado", "mejor": "x", "meta_auc": 0.8, "version_vigente": 1, "resultados": {"x": {"auc": 0.5}}}
    monkeypatch.setattr(ml_client, "reentrenar", falso)
    cliente_admin.post("/panel/riesgo/reentrenar/")
    assert len(recibido["filas"]) == 2 and all("cayo_en_siguiente" in f for f in recibido["filas"])


def test_cp19_sin_historial_no_reentrena(cliente_admin, ana):
    r = cliente_admin.post("/panel/riesgo/reentrenar/", follow=True)
    assert "historial suficiente" in r.content.decode()
