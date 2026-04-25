#!/usr/bin/env python3
"""
Utilidades compartidas para todo el DevSecOps Toolbox.

Este módulo debe ser importable desde cualquier script bajo scm/.
main.py y los tools.py agregan scm/ a PYTHONPATH antes de lanzar scripts.
"""

import os
from pathlib import Path
from typing import Optional


def get_output_dir(default: str = ".") -> Path:
    """
    Retorna el directorio de salida para reportes.

    Orden de resolución:
      1. Variable de entorno DEVSECOPS_OUTPUT_DIR (inyectada por main.py)
      2. Parámetro `default` (usualmente "outcome" o ".")

    El directorio se crea automáticamente si no existe.
    """
    env = os.getenv("DEVSECOPS_OUTPUT_DIR")
    if env:
        p = Path(env)
    else:
        p = Path(default)
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()
