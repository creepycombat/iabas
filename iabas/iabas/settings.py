# =============================================================================
# Archivo        : iabas/iabas/settings.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Configuración del proyecto Django.
# Modificaciones :
#   12-11-2026  Variables de entorno (SECRET_KEY, DEBUG, BD, ML, SITE_URL), WhiteNoise y DEFAULT_AUTO_FIELD.
#   14-11-2026  Se agregó el encabezado de documentación y se tradujeron los comentarios al español.
# Notas          : Archivo original de Alexis Villegas. Las modificaciones fueron hechas por
#                  Marcelo Herquiñigo Vargas al integrar el módulo de riesgo con ML.
# =============================================================================
"""
Configuración de Django para el proyecto IABAS.

Generado por 'django-admin startproject' con Django 6.1.3.

Más información sobre este archivo:
https://docs.djangoproject.com/en/6.1/topics/settings/

Lista completa de configuraciones y sus valores:
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import os
from pathlib import Path

# Rutas dentro del proyecto, por ejemplo: BASE_DIR / 'subcarpeta'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Configuración de inicio rápido para desarrollo: NO apta para producción
# Ver https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# ADVERTENCIA DE SEGURIDAD: la clave secreta usada en producción debe mantenerse en secreto.
# 12-11-2026: la clave se lee del entorno; el valor por defecto es solo para desarrollo local.
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-insegura-solo-desarrollo')

# ADVERTENCIA DE SEGURIDAD: no ejecutar con DEBUG activado en producción.
DEBUG = os.environ.get('DEBUG', '1') == '1'

ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',') if h]


# Definición de aplicaciones

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # añadido 12-11-2026: sirve los estáticos del admin con gunicorn
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'iabas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'iabas.wsgi.application'


# Base de datos
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DB_PATH', BASE_DIR / 'db.sqlite3'),
    }
}


# Validación de contraseñas
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internacionalización
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'es-cl'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True


# Archivos estáticos (CSS, JavaScript, imágenes)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'


# Correo electrónico
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')

# --- Añadido 12-11-2026 (integración ML) --------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_ROOT = BASE_DIR / 'staticfiles'
ML_URL = os.environ.get('ML_URL', 'http://localhost:8001').rstrip('/')      # servicio ML (FastAPI)
ML_API_KEY = os.environ.get('ML_API_KEY', 'dev-ml-key')                     # clave compartida con el servicio ML
