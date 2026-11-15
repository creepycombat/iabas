# =============================================================================
# Archivo        : iabas/core/tests/test_refuerzo.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 15-11-2026
# Descripción    : Pruebas del contenido formativo ampliado de la página de reforzamiento (RF-05).
# Modificaciones :
#   Sin modificaciones posteriores a la creación.
# Notas          : Complementa a CP-05 de test_flujo.py (que valida la evaluación y la nota).
# =============================================================================
import pytest

from core import services
from core.models import Campana, Simulacion
from core.refuerzo_contenido import analizar_correo

pytestmark = pytest.mark.django_db


def _campana(**kw):
    datos = dict(nombre="X", asunto="Restablece tu contraseña", remitente="Soporte TI <soporte@empresa-falsa.test>",
                 cuerpo="Hola, tu contraseña vence hoy. Restablécela aquí: {enlace}")
    datos.update(kw)
    return Campana(**datos)


def test_analisis_detecta_dominio_enlace_urgencia_y_credenciales():
    texto = " ".join(analizar_correo(_campana(), "localhost:8000"))
    assert "empresa-falsa.test" in texto and "localhost:8000" in texto
    assert "Presión de tiempo" in texto and "datos de acceso" in texto


def test_analisis_sin_palabras_clave_ni_remitente_no_falla():
    c = _campana(asunto="Hola", remitente="", cuerpo="Saludos")
    assert analizar_correo(c, "") == []


def test_pagina_muestra_secciones_y_variante_segun_lo_que_hizo(sim, client):
    client.get(f"/s/{sim.token}/")                                   # solo clic
    html = client.get(f"/refuerzo/{sim.token}/").content.decode()
    assert "Qué tenía de sospechoso este correo" in html and "Antes de hacer clic, revisa" in html
    assert "Hiciste clic en el enlace" in html and "Ingresaste datos" not in html
    client.post(f"/s/{sim.token}/", {"usuario": "ana", "clave": "x"})   # ahora ingresa datos
    html = client.get(f"/refuerzo/{sim.token}/").content.decode()
    assert "Ingresaste datos en el formulario" in html


@pytest.fixture
def sim(campana, ana):
    services.lanzar_campana(campana)
    return Simulacion.objects.get(usuario=ana)
