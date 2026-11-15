<!--
Archivo        : docs/cambios.md
Proyecto       : IABAS
Autor          : Marcelo Herquiñigo Vargas
Fecha creación : 12-11-2026
Modificaciones :
  12-11-2026  Creación inicial.
  14-11-2026  Nuevas modificaciones o ajustes (revisión del encabezado y de los comentarios de documentación).
  14-11-2026  Se declararon como diferencias el reforzamiento no personalizado, la reevaluación periódica (RF-09) y el recálculo diario (RNF-04).
  15-11-2026  Se actualizó la fila de reforzamiento: ahora analiza el correo recibido y distingue si hubo ingreso de datos.
-->
# Diferencias entre el MVP y lo declarado en el informe

Para explicarlas con honestidad en la presentación.

| Tema | Informe | MVP | Motivo |
|---|---|---|---|
| Autenticación | Firebase Auth | Autenticación de Django (sesión) | Simplicidad y cero dependencias externas en la demo. La versión con DRF + Firebase queda como arquitectura objetivo (`iabas-mvp`). |
| Base de datos | MySQL | SQLite | Un contenedor menos; el modelo de datos es el mismo. |
| Cifrado de campos | Cifrado de datos sensibles | No implementado | No se almacena contenido sensible: lo escrito en el formulario simulado nunca se guarda (solo el evento). |
| Envío de correo | Proveedor externo (SendGrid) | Bandeja interna de la plataforma | La demo no depende de Internet ni de spam filters. El envío real es una extensión futura. |
| Seguimiento | Webhooks del proveedor | Endpoints propios (`/o/`, `/s/`, `/r/`) | Mismo resultado sin depender del proveedor. |
| ML | Servicio de análisis | Servicio FastAPI separado, con clave de API | Se integra a la web vía HTTP (`core/ml_client.py`). Solo analiza resultados; no envía correos ni genera reforzamiento. |
| Umbrales de nivel | 70 / 40 | **50 / 30** | Con los datos simulados casi nadie superaba 70; se ajustó para que el panel sea informativo. |
| Meta de AUC | ≥ 0,80 | Se mantiene | El modelo inicial (~0,75) **no la cumple** y se declara así; el reentrenamiento solo reemplaza al vigente si logra ≥ 0,80. |
| Datos | Reales | **Simulados** | No hay datos reales de la organización; el AUC refleja al generador. |
| Revocación de consentimiento | Por organización | Por usuario (`Perfil.consentimiento_revocado`) | Así venía en la base de Alexis; cumple RNF-06 a nivel individual. |
| Reforzamiento personalizado | Contenido según el tipo de engaño y el historial de cada persona (plan técnico del MVP) | **Parcial**: la página analiza el correo que recibió la persona (dominio del remitente, enlace, palabras de urgencia o de credenciales) y cambia el consejo según si solo hizo clic o también ingresó datos. La evaluación es fija (3 preguntas) y no usa el historial | Falta de tiempo: el MVP priorizó el flujo completo y el puntaje de riesgo con ML. Queda como mejora futura. |
| Reevaluación periódica (RF-09) | Campaña de reevaluación programada para quienes completaron el reforzamiento | **No implementada** | Falta de tiempo; requiere un programador de tareas (Cloud Scheduler en el diseño). Queda como mejora futura. |
| Recálculo diario del riesgo (RNF-04) | Programado cada 24 horas | Manual con el botón «Recalcular riesgo ahora» y automático al iniciar el sistema | Falta de tiempo. El comando `recalcular_puntajes` ya existe y puede programarse a futuro. |

## Cambios hechos sobre el repositorio de Alexis
- `settings.py`: variables de entorno (SECRET_KEY, DEBUG, BD, ML), WhiteNoise, `DEFAULT_AUTO_FIELD`.
- `models.py`: `Perfil.fecha_ingreso`, `PuntajeRiesgo.nivel` (migración `0002_riesgo_ml`).
- Nuevos: `ml_client.py`, `riesgo.py`, plantilla `riesgo.html`, vistas/URLs de riesgo y exportación CSV, comando `recalcular_puntajes`, pruebas `core/tests/`.
- `seed_demo`: grupos alineados con el generador del ML, correos de prueba, opción `--solo-si-vacio`.
- Se quitó del repositorio `db.sqlite3` y la `SECRET_KEY` fija; se fijaron versiones y se retiraron dependencias sin uso.
