# =============================================================================
# Archivo        : iabas/core/tests/test_flujo.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Pruebas del flujo de la plataforma ligadas a los casos CP-xx del Anexo B del informe.
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
#   15-11-2026  Pruebas de CSV ajustadas al separador ";" y a la codificación UTF-8 con BOM.
# Notas          : Cubre CP-01, 02, 03, 04, 05, 10, 11, 12 y 18.
# =============================================================================
import pytest
from django.core.management import call_command
from io import StringIO

from core import services
from core.models import Campana, Consentimiento, EventoComportamiento, Reforzamiento, Simulacion
from core.tests.conftest import cliente_de, crear_campana, crear_colab

pytestmark = pytest.mark.django_db


# --- CP-01: acceso por rol ----------------------------------------------------------------
def test_cp01_login_con_credenciales_invalidas(admin_user, client):
    r = client.post("/login/", {"username": "admin", "password": "mala"})
    assert r.status_code == 200 and "incorrectos" in r.content.decode()


def test_cp01_vistas_diferenciadas_por_rol(cliente_admin, ana, db):
    assert cliente_admin.get("/panel/").status_code == 200
    assert cliente_admin.get("/").status_code == 302 and cliente_admin.get("/").url == "/panel/"
    c = cliente_de(ana)
    assert c.get("/").url == "/bandeja/"
    assert c.get("/panel/").status_code == 302          # el colaborador no entra al panel
    assert c.get("/panel/riesgo/").status_code == 302


def test_cp01_sin_sesion_no_hay_acceso(client, db):
    for ruta in ("/panel/", "/bandeja/", "/panel/riesgo/", "/privacidad/"):
        assert client.get(ruta).status_code == 302


# --- CP-10: consentimiento ----------------------------------------------------------------
def test_cp10_sin_consentimiento_no_se_ejecuta(cliente_admin, grupos, ana):
    c = Campana.objects.create(nombre="Sin", asunto="x", cuerpo="{enlace}")
    c.grupos.set(grupos)
    r = cliente_admin.post(f"/panel/campana/{c.pk}/ejecutar/", follow=True)
    assert "falta el consentimiento" in r.content.decode()
    assert Simulacion.objects.count() == 0 and Campana.objects.get(pk=c.pk).estado == "borrador"


def test_cp10_registrar_consentimiento_y_ejecutar(cliente_admin, grupos, ana):
    c = Campana.objects.create(nombre="Sin", asunto="x", cuerpo="Hola {nombre} {enlace}")
    c.grupos.set(grupos)
    cliente_admin.post(f"/panel/campana/{c.pk}/consentimiento/", {"organizacion": "Org", "acepto": "on"})
    assert Campana.objects.get(pk=c.pk).consentimiento is not None             # queda trazabilidad
    cliente_admin.post(f"/panel/campana/{c.pk}/ejecutar/")
    assert Simulacion.objects.filter(campana=c).count() == 1


def test_cp10_exige_marcar_la_confirmacion(cliente_admin, grupos):
    c = Campana.objects.create(nombre="Sin", asunto="x", cuerpo="{enlace}")
    cliente_admin.post(f"/panel/campana/{c.pk}/consentimiento/", {"organizacion": "Org"})
    assert Campana.objects.get(pk=c.pk).consentimiento is None


# --- CP-03: creación y ejecución de campaña ------------------------------------------------
def test_cp03_ejecutar_crea_una_simulacion_por_colaborador_y_no_repite(campana, ana, beto, admin_user):
    assert services.lanzar_campana(campana) == 2        # el administrador (staff) no recibe simulación
    assert Campana.objects.get(pk=campana.pk).estado == "ejecutada"
    with pytest.raises(services.CampanaInvalida):
        services.lanzar_campana(campana)


# --- CP-18: revocación del consentimiento (RNF-06) -----------------------------------------
def test_cp18_usuario_que_revoca_no_recibe_campañas(consentimiento, grupos, ana, beto):
    cliente_de(ana).post("/privacidad/")
    ana.perfil.refresh_from_db()
    assert ana.perfil.consentimiento_revocado
    c = crear_campana(consentimiento, grupos)
    assert services.lanzar_campana(c) == 1
    assert list(c.simulaciones.values_list("usuario__username", flat=True)) == ["beto"]


# --- CP-04: registro de eventos ------------------------------------------------------------
@pytest.fixture
def sim(campana, ana):
    services.lanzar_campana(campana)
    return Simulacion.objects.get(usuario=ana)


def tipos(s):
    return sorted(s.eventos.values_list("tipo", flat=True))


def test_cp04_apertura_clic_datos_y_reporte(sim, client):
    assert client.get(f"/o/{sim.token}.png").status_code == 200
    assert client.get(f"/o/{sim.token}.png").status_code == 200            # reabrir no duplica
    assert client.get(f"/s/{sim.token}/").status_code == 200
    r = client.post(f"/s/{sim.token}/", {"usuario": "ana", "clave": "x"})
    assert r.status_code == 302 and r.url == f"/refuerzo/{sim.token}/"
    assert client.get(f"/r/{sim.token}/").status_code == 200
    assert tipos(sim) == ["apertura", "clic", "datos", "reporte"]


def test_cp04_clic_repetido_no_duplica_eventos(sim, client):
    client.get(f"/s/{sim.token}/")
    client.get(f"/s/{sim.token}/")
    assert tipos(sim) == ["apertura", "clic"]


def test_cp04_lo_escrito_en_el_formulario_no_se_guarda(sim, client):
    client.post(f"/s/{sim.token}/", {"usuario": "ana@empresa", "clave": "SuperSecreta123"})
    volcado = StringIO()
    call_command("dumpdata", "core", stdout=volcado)
    assert "SuperSecreta123" not in volcado.getvalue() and "ana@empresa" not in volcado.getvalue()


def test_cp04_token_desconocido_404(db, client):
    for ruta in ("/s/", "/r/", "/o/"):
        sufijo = ".png" if ruta == "/o/" else "/"
        assert client.get(f"{ruta}00000000-0000-0000-0000-000000000000{sufijo}").status_code == 404


# --- CP-05: reforzamiento ------------------------------------------------------------------
def test_cp05_fallo_genera_reforzamiento_y_reporte_no(sim, client):
    client.get(f"/r/{sim.token}/")
    assert not Reforzamiento.objects.exists()
    client.get(f"/s/{sim.token}/")
    assert Reforzamiento.objects.filter(simulacion=sim).count() == 1


def test_cp05_evaluacion_se_rinde_una_sola_vez(sim, client):
    client.get(f"/s/{sim.token}/")
    r = client.post(f"/refuerzo/{sim.token}/", {"p0": "1", "p1": "2", "p2": "0"})
    assert "3 de 3" in r.content.decode()
    assert Reforzamiento.objects.get(simulacion=sim).nota == 100.0
    client.post(f"/refuerzo/{sim.token}/", {"p0": "0", "p1": "0", "p2": "1"})   # segundo intento: no cuenta
    assert Reforzamiento.objects.get(simulacion=sim).nota == 100.0


def test_cp05_sin_fallo_no_hay_reforzamiento(sim, client):
    assert client.get(f"/refuerzo/{sim.token}/").status_code == 404


# --- CP-11: no revelar la simulación -------------------------------------------------------
def test_cp11_colaborador_solo_ve_su_propio_correo(campana, ana, beto):
    services.lanzar_campana(campana)
    de_beto = Simulacion.objects.get(usuario=beto)
    c = cliente_de(ana)
    assert c.get(f"/bandeja/{de_beto.token}/").status_code == 404
    assert c.get("/bandeja/").status_code == 200 and de_beto.campana.asunto in c.get("/bandeja/").content.decode()


def test_cp11_antes_del_envio_el_colaborador_no_ve_nada(campana, ana):
    c = cliente_de(ana)
    assert "No tienes correos nuevos" in c.get("/bandeja/").content.decode()
    assert Campana.objects.get(pk=campana.pk).nombre not in c.get("/bandeja/").content.decode()


# --- CP-12: exportación --------------------------------------------------------------------
def test_cp12_exportar_campana_coincide_con_los_eventos(sim, client, cliente_admin):
    client.get(f"/s/{sim.token}/")
    csv = cliente_admin.get(f"/panel/campana/{sim.campana_id}/exportar/").content.decode("utf-8-sig").splitlines()
    assert csv[0] == "usuario;grupo;abrio;clic;ingreso_datos;reporto;nota_reforzamiento"
    assert csv[1] == "ana;Finanzas;1;1;0;0;"
    assert "@" not in "".join(csv)          # no se exportan correos


def test_cp12_solo_el_administrador_exporta(sim, ana):
    assert cliente_de(ana).get(f"/panel/campana/{sim.campana_id}/exportar/").status_code == 302
