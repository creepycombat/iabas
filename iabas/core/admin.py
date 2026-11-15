# =============================================================================
# Archivo        : iabas/core/admin.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Registro de los modelos en el sitio de administración de Django.
# Modificaciones :
#   14-11-2026  Se agregó el encabezado de documentación.
# Notas          : Archivo original de Alexis Villegas; solo se agregó el encabezado.
# =============================================================================
from django.contrib import admin
from .models import *

admin.site.site_header = "IABAS · Administración"

@admin.register(Campana)
class CampanaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado", "consentimiento", "ejecutada")
    filter_horizontal = ("grupos",)

admin.site.register([Grupo, Perfil, Consentimiento, Simulacion, EventoComportamiento,
                     Reforzamiento, ModeloML, PuntajeRiesgo])
