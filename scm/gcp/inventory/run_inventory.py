#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inventario GKE + Cloud SQL - Launcher

Ejecuta el pipeline completo de inventario:
  1. generar-inventario-csv.sh  → genera CSVs por proyecto
  2. generar-inventario-csv-combinar-a-excel.py → consolida en Excel

Uso:
    python run_inventory.py [--skip-csv]
"""

import os
import subprocess
import sys
import platform
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()


def ensure_unix_line_endings(filepath: Path) -> None:
    """Convierte CRLF (Windows) a LF (Unix) si es necesario.
    Esto evita errores $'\r': command not found al ejecutar .sh en WSL/Linux.
    """
    if platform.system() == "Windows":
        return
    try:
        raw = filepath.read_bytes()
        if b"\r\n" in raw:
            filepath.write_bytes(raw.replace(b"\r\n", b"\n"))
    except Exception:
        pass


def run_step(desc: str, cmd: list, cwd: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n❌ Error en: {desc} (código {result.returncode})")
        return False
    print(f"✅ {desc} completado.")
    return True


def main():
    skip_csv = "--skip-csv" in sys.argv

    if not skip_csv:
        bash_script = SCRIPT_DIR / "generar-inventario-csv.sh"
        if not bash_script.exists():
            print(f"❌ No se encontró: {bash_script}")
            sys.exit(1)
        ensure_unix_line_endings(bash_script)
        os.chmod(bash_script, 0o755)
        if not run_step(
            "Paso 1/2 – Generando CSVs de inventario",
            ["bash", str(bash_script)],
            str(SCRIPT_DIR),
        ):
            sys.exit(1)

    python_script = SCRIPT_DIR / "generar-inventario-csv-combinar-a-excel.py"
    if not python_script.exists():
        print(f"❌ No se encontró: {python_script}")
        sys.exit(1)
    if not run_step(
        "Paso 2/2 – Consolidando CSVs en Excel",
        [sys.executable, str(python_script)],
        str(SCRIPT_DIR),
    ):
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  ✅ Inventario completado exitosamente")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
