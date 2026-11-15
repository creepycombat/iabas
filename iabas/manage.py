#!/usr/bin/env python
# =============================================================================
# Archivo        : iabas/manage.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Alexis Villegas
# Fecha creación : 11-11-2026
# Descripción    : Utilidad de línea de comandos de Django.
# Modificaciones :
#   14-11-2026  Se agregó el encabezado de documentación y se tradujeron los comentarios al español.
# Notas          : Archivo original de Alexis Villegas; solo se agregó el encabezado.
# =============================================================================
"""Utilidad de línea de comandos de Django para tareas administrativas."""
import os
import sys


def main():
    """Ejecuta las tareas administrativas."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iabas.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y disponible en tu "
            "PYTHONPATH? ¿Olvidaste activar el entorno virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
