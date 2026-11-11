"""Contenido del reforzamiento (RF-05): señales de alerta y evaluación de 3 preguntas."""

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
