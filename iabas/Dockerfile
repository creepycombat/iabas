# =============================================================================
# Archivo        : iabas/Dockerfile
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 12-11-2026
# Descripción    : Imagen de la aplicación web Django (plataforma IABAS).
# Modificaciones :
#   12-11-2026  Creación inicial.
#   14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
# Notas          :
#   - La base de datos SQLite NO va en la imagen: vive en el volumen /data.
#   - collectstatic se ejecuta al construir para servir CSS con WhiteNoise.
# =============================================================================
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Quita finales de línea de Windows (CRLF) para que el script corra en Linux
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh \
    && SECRET_KEY=build python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["./entrypoint.sh"]
