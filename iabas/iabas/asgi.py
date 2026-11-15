# =============================================================================
# Archivo        : iabas/iabas/asgi.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Punto de entrada ASGI del proyecto.
# Modificaciones :
#   14-11-2026  Se agregó el encabezado de documentación y se tradujeron los comentarios al español.
# Notas          : Archivo original de Alexis Villegas; solo se agregó el encabezado.
# =============================================================================
"""
Configuración ASGI del proyecto IABAS.

Expone el objeto ASGI como variable de módulo llamada ``application``.

Más información sobre este archivo:
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iabas.settings')

application = get_asgi_application()
