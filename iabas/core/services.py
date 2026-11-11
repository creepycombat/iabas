"""Lógica de negocio de IABAS. Las vistas y el dashboard llaman a estas funciones."""
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Campana, EventoComportamiento, Reforzamiento, Simulacion


class ConsentimientoRequerido(Exception):
    """RF-10: no se puede ejecutar una campaña sin consentimiento registrado."""


class CampanaInvalida(Exception):
    pass


def destinatarios(campana):
    """Colaboradores activos de los grupos de la campaña. RNF-06: excluye a quienes revocaron."""
    return (User.objects
            .filter(is_active=True, is_staff=False,
                    perfil__grupo__in=campana.grupos.all(),
                    perfil__consentimiento_revocado=False)
            .distinct())


@transaction.atomic
def lanzar_campana(campana):
    """RF-03 + RF-10: crea una Simulacion (correo simulado) por destinatario."""
    if campana.consentimiento_id is None:
        raise ConsentimientoRequerido(
            "No se puede ejecutar la campaña: falta el consentimiento informado de la organización.")
    if campana.estado == "ejecutada":
        raise CampanaInvalida("La campaña ya fue ejecutada.")
    users = list(destinatarios(campana))
    if not users:
        raise CampanaInvalida("La campaña no tiene destinatarios válidos.")
    sims = [Simulacion(usuario=u, campana=campana) for u in users]
    Simulacion.objects.bulk_create(sims)
    campana.estado = "ejecutada"
    campana.ejecutada = timezone.now()
    campana.save(update_fields=["estado", "ejecutada"])
    return len(sims)


def registrar_evento(token, tipo):
    """RF-04: registra un evento (una vez por tipo). Un clic o ingreso de datos
    es una simulación fallida y asigna el reforzamiento (RF-05)."""
    sim = Simulacion.objects.select_related("campana", "usuario").get(token=token)
    if tipo in ("clic", "datos"):
        # un clic implica que el correo se abrió
        _evento_unico(sim, "apertura")
    _evento_unico(sim, tipo)
    if tipo in ("clic", "datos"):
        Reforzamiento.objects.get_or_create(simulacion=sim)
    return sim


def _evento_unico(sim, tipo):
    return EventoComportamiento.objects.get_or_create(simulacion=sim, tipo=tipo)[0]


def completar_reforzamiento(simulacion, aciertos, total):
    """RF-05: la evaluación se rinde una sola vez (según el BPMN del informe 2)."""
    ref = simulacion.reforzamiento
    if ref.completado:
        return ref
    ref.nota = round(100 * aciertos / total, 1)
    ref.completado = timezone.now()
    ref.save()
    return ref


def revocar_consentimiento(user):
    """RNF-06: el usuario deja de recibir nuevas campañas."""
    user.perfil.consentimiento_revocado = True
    user.perfil.save(update_fields=["consentimiento_revocado"])


def renderizar_correo(simulacion, base_url):
    """Arma el cuerpo del correo con el enlace de tracking del usuario."""
    enlace = f"{base_url}/s/{simulacion.token}/"
    u = simulacion.usuario
    return simulacion.campana.cuerpo.format(nombre=u.first_name or u.username, enlace=enlace)
