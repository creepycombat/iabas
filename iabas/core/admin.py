from django.contrib import admin
from .models import *

admin.site.site_header = "IABAS · Administración"

@admin.register(Campana)
class CampanaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado", "consentimiento", "ejecutada")
    filter_horizontal = ("grupos",)

admin.site.register([Grupo, Perfil, Consentimiento, Simulacion, EventoComportamiento,
                     Reforzamiento, ModeloML, PuntajeRiesgo])
