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
