#!/bin/sh
# =============================================================================
# Archivo        : iabas/entrypoint.sh
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Arranque del contenedor web: migra la BD, carga datos demo si corresponde y levanta gunicorn.
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
#   14-11-2026  Corrección: la línea #!/bin/sh pasó a ser la primera del archivo (antes el contenedor no arrancaba).
# Notas          :
#   - SEED_DEMO=1 crea los datos de demostración solo si la base está vacía.
#   - El recálculo inicial de puntajes corre en segundo plano y espera a que el servicio ML esté listo.
# =============================================================================
set -e
mkdir -p "$(dirname "${DB_PATH:-/data/db.sqlite3}")"

python manage.py migrate --noinput

if [ "${SEED_DEMO:-0}" = "1" ]; then
    python manage.py seed_demo --solo-si-vacio
    # En segundo plano: no retrasa el arranque de la web; reintenta mientras el ML termina de iniciar
    python manage.py recalcular_puntajes --esperar 180 &
fi

exec gunicorn iabas.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile -
