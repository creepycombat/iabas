# =============================================================================
# Archivo        : iabas/core/management/commands/recalcular_puntajes.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Calcula los puntajes de riesgo llamando al servicio ML (lo usa el arranque y Cloud Scheduler).
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
# Notas          :
#   - --esperar N reintenta hasta N segundos mientras el servicio ML termina de arrancar y entrenar.
# =============================================================================
import time

from django.core.management.base import BaseCommand, CommandError

from core import ml_client, riesgo


class Command(BaseCommand):
    help = "Calcula los puntajes de riesgo con el servicio ML"

    def add_arguments(self, parser):
        parser.add_argument("--esperar", type=int, default=0, help="segundos a reintentar si el ML aún no responde")

    def handle(self, *args, **o):
        limite = time.time() + o["esperar"]
        while True:
            try:
                r = riesgo.recalcular()
                break
            except ml_client.MLNoDisponible as e:
                if time.time() >= limite:
                    raise CommandError(str(e))
                time.sleep(5)   # el servicio ML puede estar entrenando el modelo inicial
        self.stdout.write(self.style.SUCCESS(f"{r['actualizados']} puntajes (modelo v{r['version_modelo']})"))
