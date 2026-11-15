# =============================================================================
# Archivo        : iabas/iabas/urls.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Rutas principales del proyecto (administración y aplicación core).
# Modificaciones :
#   14-11-2026  Se agregó el encabezado de documentación y se tradujeron los comentarios al español.
# Notas          : Archivo original de Alexis Villegas; solo se agregó el encabezado.
# =============================================================================
"""
Configuración de URLs del proyecto IABAS.

La lista `urlpatterns` enruta las URL hacia las vistas. Más información en:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Ejemplos:
Vistas basadas en funciones
    1. Importar:  from mi_app import views
    2. Agregar a urlpatterns:  path('', views.home, name='home')
Vistas basadas en clases
    1. Importar:  from otra_app.views import Home
    2. Agregar a urlpatterns:  path('', Home.as_view(), name='home')
Incluir otro URLconf
    1. Importar include():  from django.urls import include, path
    2. Agregar a urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]
