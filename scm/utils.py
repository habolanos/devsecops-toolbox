#!/usr/bin/env python3
"""
Utilidades compartidas para todo el DevSecOps Toolbox.

Este módulo debe ser importable desde cualquier script bajo scm/.
main.py y los tools.py agregan scm/ a PYTHONPATH antes de lanzar scripts.
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime


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


# Extensiones por formato de salida
FORMAT_EXTENSIONS = {
    "excel": ".xlsx",
    "csv":   ".csv",
    "json":  ".json",
}


def resolve_output_path(output_arg: Optional[str], base_name: str,
                        default_format: str = "excel") -> str:
    """
    Normaliza el argumento --output del menú.

    El menú pasa formatos como 'excel', 'csv', 'json' en vez de paths.
    Esta función:
      - Si output_arg es None → genera path en outcome/ con extensión default
      - Si output_arg es un formato (excel/csv/json) → genera path en outcome/ con esa extensión
      - Si output_arg es un path real → lo usa tal cual (agrega extensión si no tiene)

    Retorna string con path absoluto.
    """
    output_dir = get_output_dir("outcome")
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = FORMAT_EXTENSIONS.get(default_format, ".xlsx")

    if not output_arg:
        return str(output_dir / f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")

    # ¿Es un formato del menú?
    if output_arg.lower() in FORMAT_EXTENSIONS:
        ext = FORMAT_EXTENSIONS[output_arg.lower()]
        return str(output_dir / f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")

    # Es un path proporcionado por el usuario
    p = Path(output_arg)
    if p.suffix == "":
        p = p.with_suffix(ext)
    return str(p.resolve())
