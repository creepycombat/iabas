# =============================================================================
# Archivo        : iabas/core/ml_client.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Cliente HTTP del servicio ML (FastAPI): puntuar usuarios, reentrenar y consultar el modelo vigente.
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
# Notas          :
#   - Toda falla de red o respuesta de error se convierte en MLNoDisponible, para que la plataforma
#     siga funcionando (y muestre un aviso) aunque el servicio ML esté caído.
#   - La clave compartida viaja en la cabecera X-API-Key (settings.ML_API_KEY).
# =============================================================================
import requests
from django.conf import settings


class MLNoDisponible(Exception):
    """El servicio ML no respondió o devolvió un error."""


def _llamar(metodo, ruta, **kwargs):
    """Hace la llamada HTTP al servicio ML y devuelve el JSON, o lanza MLNoDisponible."""
    try:
        r = requests.request(metodo, f"{settings.ML_URL}{ruta}", headers={"X-API-Key": settings.ML_API_KEY},
                             timeout=kwargs.pop("timeout", 30), **kwargs)
    except requests.RequestException as e:
        raise MLNoDisponible(f"No se pudo contactar al servicio ML: {e}")
    if r.status_code != 200:
        raise MLNoDisponible(f"El servicio ML respondió {r.status_code}: {r.text[:200]}")
    return r.json()


def salud():
    """Estado del servicio y del modelo vigente (versión, AUC, si cumple la meta)."""
    return _llamar("GET", "/salud", timeout=5)


def puntuar(filas):
    """Envía las características de cada usuario y devuelve {'version_modelo', 'puntajes': [...]}."""
    return _llamar("POST", "/puntajes/recalcular", json={"usuarios": filas})


def reentrenar(filas=None):
    """Reentrena el modelo (Proceso 3). Con filas usa los datos de la plataforma; sin ellas, el dataset simulado."""
    return _llamar("POST", "/reentrenar", json={"filas": filas} if filas else {}, timeout=180)
