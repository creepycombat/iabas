# =============================================================================
# Archivo        : ml/Dockerfile
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 11-11-2026
# Descripción    : Imagen del servicio ML (Python 3.12 + scikit-learn + FastAPI).
# Modificaciones :
#   11-11-2026  Creación inicial.
#   12-11-2026  Se usa entrypoint.sh: genera los datos y entrena el modelo inicial si faltan.
# Notas          :
#   - Los datos y los modelos no van en la imagen: se montan como volúmenes.
# =============================================================================
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py entrypoint.sh ./
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh
EXPOSE 8001
CMD ["./entrypoint.sh"]
