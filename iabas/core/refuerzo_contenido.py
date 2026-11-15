# =============================================================================
# Archivo        : iabas/core/refuerzo_contenido.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Contenido del reforzamiento (RF-05): señales de alerta y evaluación de 3 preguntas.
# Modificaciones :
#   14-11-2026  Se agregó el encabezado de documentación.
#   15-11-2026  Se enriqueció el reforzamiento: análisis del correo recibido, por qué funcionan estos
#               engaños, qué hacer ahora y lista de verificación (se mantienen señales y preguntas).
# Notas          : Archivo original de Alexis Villegas. Las SENALES y las PREGUNTAS no cambiaron; lo
#                  agregado el 15-11-2026 lo hizo Marcelo Herquiñigo Vargas.
# =============================================================================
"""Contenido del reforzamiento (RF-05): señales de alerta y evaluación de 3 preguntas."""
import re

SENALES = [
    "Urgencia o amenaza: plazos de horas, bloqueos de cuenta, multas.",
    "Un remitente que imita a una área conocida, pero con un dominio extraño.",
    "Un enlace que no lleva al sitio oficial de la organización.",
    "Una petición de credenciales o datos personales por correo.",
]

PREGUNTAS = [
    {"texto": "¿Cuál es la señal más fiable de que un correo que te pide cambiar tu contraseña es falso?",
     "opciones": ["Llegó dentro del horario laboral",
                  "Genera urgencia e incluye un enlace a un sitio que no reconoces",
                  "Está escrito con tu nombre"],
     "correcta": 1,
     "explicacion": "La urgencia y los enlaces desconocidos son las señales más comunes. Tu nombre y el horario no prueban nada."},
    {"texto": "Antes de hacer clic en un enlace, ¿qué conviene hacer?",
     "opciones": ["Hacer clic para ver adónde lleva",
                  "Reenviarlo a colegas para que lo prueben",
                  "Pasar el cursor para ver la dirección real, o entrar al sitio escribiendo la dirección tú mismo"],
     "correcta": 2,
     "explicacion": "Ver la dirección real, o entrar por tu cuenta, evita que el clic active el engaño."},
    {"texto": "Si sospechas de un correo, ¿qué debes hacer?",
     "opciones": ["Reportarlo al equipo de seguridad y no interactuar con él",
                  "Borrarlo sin avisar a nadie",
                  "Responder preguntando si es real"],
     "correcta": 0,
     "explicacion": "Reportar ayuda a proteger también a tus compañeros. Responder le confirma al atacante que tu cuenta está activa."},
]


# ---------------------------------------------------------------------------------------------
# Agregado el 15-11-2026 (Marcelo Herquiñigo): contenido formativo más completo para el reforzamiento
# ---------------------------------------------------------------------------------------------
POR_QUE_FUNCIONAN = [
    "Apelan a emociones (urgencia, miedo, curiosidad o autoridad) para que actúes antes de pensar.",
    "Imitan a áreas y proveedores que ya conoces, por eso el correo se siente familiar.",
    "Llegan en horario laboral y con temas cotidianos (facturas, beneficios, documentos compartidos).",
    "Un solo clic o una sola contraseña entregada puede dar acceso a las cuentas de toda la organización.",
]

QUE_HACER_CLIC = [
    "Cierra la página sin ingresar ningún dato.",
    "Si fuera un caso real, avisa de inmediato al equipo de seguridad: mientras antes se sepa, menos daño.",
    "La próxima vez, reporta el correo sospechoso en lugar de abrir el enlace.",
]

QUE_HACER_DATOS = [
    "En un caso real, cambia de inmediato la contraseña de esa cuenta desde el sitio oficial.",
    "Cambia también la contraseña en otros servicios donde la hayas repetido y activa la verificación en dos pasos.",
    "Avisa al equipo de seguridad aunque creas que no pasó nada: ellos pueden revisar accesos extraños.",
    "Aquí no corriste riesgo: es una simulación y lo que escribiste no se guarda.",
]

CHECKLIST = [
    "¿Conozco al remitente y el dominio de su dirección es el oficial de mi organización?",
    "¿Me presiona con plazos, amenazas o consecuencias inmediatas?",
    "¿Me pide contraseña, datos personales o bancarios?",
    "¿Esperaba este correo o este documento?",
    "¿La dirección real del enlace (al pasar el cursor) coincide con el sitio oficial?",
    "Si tengo dudas: no hago clic, lo reporto y consulto por otro canal (llamada o mensaje directo).",
]

# Palabras que delatan cada técnica; se buscan en el asunto y en el cuerpo del correo recibido
_TECNICAS = [
    ("urgencia", r"hoy|mañana|vence\w*|urgente|inmediat\w*|bloqueo|bloquear|horas|sospechos\w*|alerta",
     "Presión de tiempo o amenaza: el correo usaba palabras como {palabras}. Los estafadores quieren que reacciones sin pensar."),
    ("credenciales", r"contraseña|credencial\w*|datos de acceso|cuenta|acceso|ingresa|verifica|confirma",
     "Te pedía actuar sobre tu cuenta o tus datos de acceso ({palabras}). Una organización seria no pide eso por correo con un enlace."),
    ("atractivo", r"bono|beneficio|premio|gratis|aguinaldo",
     "Ofrecía algo atractivo ({palabras}) para despertar tu curiosidad o tu interés."),
    ("cotidiano", r"factura|document\w*|informe|adjunt\w*|comparti\w*",
     "Se apoyaba en un asunto cotidiano de trabajo ({palabras}), que baja la guardia."),
]


def _dominio_remitente(remitente):
    """Devuelve el dominio de la dirección del remitente (lo que va después de la @), o ''."""
    m = re.search(r"@([\w.-]+)", remitente or "")
    return m.group(1) if m else ""


def analizar_correo(campana, host_enlace):
    """Lista de observaciones sobre el correo que recibió el colaborador (remitente, enlace y texto)."""
    hallazgos = []
    dominio = _dominio_remitente(campana.remitente)
    nombre = campana.remitente.split("<")[0].strip() or "un remitente"
    if dominio:
        hallazgos.append(
            f"El remitente se presentaba como «{nombre}», pero escribía desde el dominio «{dominio}». "
            "Compara siempre ese dominio con el oficial de tu organización.")
    if host_enlace and host_enlace != dominio:
        hallazgos.append(
            f"El enlace llevaba a «{host_enlace}», un sitio distinto al del remitente. "
            "Al pasar el cursor sobre un enlace se ve su destino real.")
    texto = f"{campana.asunto} {campana.cuerpo}".lower()
    for _, patron, frase in _TECNICAS:
        palabras = sorted(set(re.findall(patron, texto)))
        if palabras:
            hallazgos.append(frase.format(palabras=", ".join(f"«{w}»" for w in palabras[:3])))
    return hallazgos
