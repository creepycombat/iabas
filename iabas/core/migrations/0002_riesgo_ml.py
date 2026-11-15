# =============================================================================
# Archivo        : iabas/core/migrations/0002_riesgo_ml.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Migración: agrega Perfil.fecha_ingreso y PuntajeRiesgo.nivel.
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
# Notas          : Generada con 'makemigrations' de Django 6.1.3; el contenido no se edita a mano.
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="fecha_ingreso",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="puntajeriesgo",
            name="nivel",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
    ]
