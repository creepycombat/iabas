# =============================================================================
# Archivo        : iabas/core/tests/conftest.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Fixtures compartidas de las pruebas (usuarios, grupos, consentimiento, campaña, simulaciones).
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
# Notas          : Las simulaciones se arman a mano para controlar fechas y eventos exactos.
# =============================================================================
from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from core.models import (Campana, Consentimiento, EventoComportamiento, Grupo, Perfil, Reforzamiento, Simulacion)


@pytest.fixture
def grupos(db):
    return [Grupo.objects.create(nombre=n) for n in ("Finanzas", "TI")]


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user("admin", password="admin1234", is_staff=True, first_name="Ana")
    Perfil.objects.create(user=u)
    return u


def crear_colab(nombre, grupo, ingreso=date(2026, 1, 12)):
    """Crea un colaborador con su perfil (grupo y fecha de ingreso)."""
    u = User.objects.create_user(nombre, password="demo1234", first_name=nombre.capitalize(),
                                 email=f"{nombre}@empresa-demo.test")
    Perfil.objects.create(user=u, grupo=grupo, fecha_ingreso=ingreso)
    return u


@pytest.fixture
def ana(grupos):
    return crear_colab("ana", grupos[0])


@pytest.fixture
def beto(grupos):
    return crear_colab("beto", grupos[1])


@pytest.fixture
def consentimiento(admin_user):
    return Consentimiento.objects.create(organizacion="Org Demo", registrado_por=admin_user, texto="Consiente.")


def crear_campana(consentimiento, grupos, nombre="C1", estado="borrador", ejecutada=None):
    c = Campana.objects.create(nombre=nombre, consentimiento=consentimiento, asunto="Asunto", estado=estado,
                               cuerpo="Hola {nombre}, entra aquí: {enlace}", ejecutada=ejecutada)
    c.grupos.set(grupos)
    return c


@pytest.fixture
def campana(consentimiento, grupos):
    return crear_campana(consentimiento, grupos)


def crear_sim(usuario, campana, eventos=(), nota=None, enviada=None):
    """Crea una simulación con eventos [(tipo, minutos_despues_de_enviada)] y, si hay nota, su reforzamiento."""
    enviada = enviada or campana.ejecutada or timezone.now()
    s = Simulacion.objects.create(usuario=usuario, campana=campana)
    Simulacion.objects.filter(pk=s.pk).update(enviada=enviada)   # 'enviada' es auto_now_add
    for tipo, minutos in eventos:
        e = EventoComportamiento.objects.create(simulacion=s, tipo=tipo)
        EventoComportamiento.objects.filter(pk=e.pk).update(fecha=enviada + timedelta(minutes=minutos))
    if nota is not None:
        Reforzamiento.objects.create(simulacion=s, nota=nota, completado=enviada)
    return Simulacion.objects.get(pk=s.pk)


@pytest.fixture
def cliente_admin(admin_user):
    c = Client()
    c.login(username="admin", password="admin1234")
    return c


def cliente_de(usuario):
    c = Client()
    c.login(username=usuario.username, password="demo1234")
    return c
