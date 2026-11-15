#!/bin/sh
# =============================================================================
# Archivo        : ml/entrypoint.sh
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Arranque del contenedor ML: genera datos y entrena el modelo inicial si faltan, y levanta el servicio.
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
# Notas          :
#   - Los datos y modelos viven en volúmenes, así que esto solo ocurre la primera vez.
# =============================================================================
set -e
[ -f salida/dataset_entrenamiento.csv ] || python generar_datos.py --usuarios 500 --campanas 8 --semilla 42 --salida salida
[ -f modelos/vigente.json ] || python entrenar_modelo.py --datos salida/dataset_entrenamiento.csv --modelos modelos
exec uvicorn servicio_ml:app --host 0.0.0.0 --port 8001
