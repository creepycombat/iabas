<!--
Archivo        : README.md
Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
Autor          : Marcelo Herquiñigo Vargas (la aplicación Django base es de Alexis; ver docs/cambios.md)
Fecha creación : 12-11-2026
Modificaciones : 12-11-2026 Creación inicial (versión corta; el manual completo se hará más adelante); 14-11-2026 Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
-->
# IABAS – MVP integrado

Plataforma de simulaciones de phishing con consentimiento, reforzamiento educativo y **puntaje de riesgo
calculado con Machine Learning**. Dos servicios:

| Servicio | Qué es | Puerto |
|---|---|---|
| `iabas/` (web) | Django: login por rol, campañas, bandeja interna, seguimiento de eventos, reforzamiento, panel y panel de riesgo | 8000 |
| `ml/` (ml) | FastAPI + scikit-learn: calcula puntajes y reentrena el modelo (solo analiza resultados) | 8001 |

> ⚠️ **Los datos son simulados.** El AUC del modelo refleja el generador de datos, no a personas reales.

## Cómo levantarlo (Docker)

```bash
copy .env.example .env        # (Linux/Mac: cp .env.example .env)
docker compose up --build
```

Cuando termine de arrancar (1–3 min la primera vez): <http://localhost:8000>

| Rol | Usuario | Clave |
|---|---|---|
| Administrador | `admin` | `admin1234` |
| Colaborador (cualquiera de los 60) | p. ej. `vicente.hernandez14` | `demo1234` |

Comandos útiles:

```bash
docker compose ps                 # estado (ml debe decir "healthy")
docker compose logs -f web        # ver el log de la web
docker compose down               # detener (conserva los datos)
docker compose down -v            # detener y borrar todo (empezar de cero)
docker compose exec web python -m pytest -q    # correr las pruebas (37)
```

## Cómo levantarlo sin Docker (notebook)

Requiere Python 3.12+. En **dos terminales**:

```bash
# Terminal 1 – servicio ML
cd ml
pip install -r requirements.txt
set ML_API_KEY=dev-ml-key          # (Linux/Mac: export ML_API_KEY=dev-ml-key)
python generar_datos.py && python entrenar_modelo.py
uvicorn servicio_ml:app --port 8001

# Terminal 2 – web
cd iabas
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --solo-si-vacio
python manage.py recalcular_puntajes --esperar 30
python manage.py runserver
```

## Documentación
Diferencias respecto del informe: [`docs/cambios.md`](docs/cambios.md).

## Estructura

```
iabas-integrado/
├─ docker-compose.yml  .env.example  .gitignore
├─ iabas/              # Django (web)
│  └─ core/            # models, views, services, riesgo.py (features + ML), ml_client.py, tests/
└─ ml/                 # servicio ML (FastAPI), generador de datos y entrenamiento
```
