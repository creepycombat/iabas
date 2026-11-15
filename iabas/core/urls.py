# =============================================================================
# Archivo        : iabas/core/urls.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Rutas de la aplicación core (administrador, colaborador y seguimiento).
# Modificaciones :
#   12-11-2026  Se agregaron las rutas de riesgo y de exportación CSV.
#   14-11-2026  Se agregó el encabezado de documentación.
# Notas          : Archivo original de Alexis Villegas. Las modificaciones fueron hechas por
#                  Marcelo Herquiñigo Vargas al integrar el módulo de riesgo con ML.
# =============================================================================
from django.contrib.auth import views as auth
from django.urls import path

from . import views as v

urlpatterns = [
    path("", v.inicio, name="inicio"),
    path("login/", auth.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    # administrador
    path("panel/", v.panel, name="panel"),
    path("panel/campana/<int:pk>/ejecutar/", v.ejecutar_campana, name="ejecutar"),
    path("panel/campana/<int:pk>/consentimiento/", v.registrar_consentimiento, name="consentimiento"),
    path("panel/campana/<int:pk>/exportar/", v.exportar_campana, name="exportar_campana"),
    # riesgo (ML) - añadido 12-11-2026
    path("panel/riesgo/", v.riesgo, name="riesgo"),
    path("panel/riesgo/recalcular/", v.riesgo_recalcular, name="riesgo_recalcular"),
    path("panel/riesgo/reentrenar/", v.riesgo_reentrenar, name="riesgo_reentrenar"),
    path("panel/riesgo/exportar/", v.exportar_riesgo, name="exportar_riesgo"),
    # colaborador
    path("bandeja/", v.bandeja, name="bandeja"),
    path("bandeja/<uuid:token>/", v.correo, name="correo"),
    path("privacidad/", v.privacidad, name="privacidad"),
    # tracking
    path("o/<uuid:token>.png", v.pixel_apertura, name="pixel"),
    path("s/<uuid:token>/", v.clic, name="clic"),
    path("r/<uuid:token>/", v.reportar, name="reportar"),
    path("refuerzo/<uuid:token>/", v.refuerzo, name="refuerzo"),
]
