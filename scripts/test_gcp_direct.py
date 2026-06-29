#!/usr/bin/env python3
"""Script para ejecutar gcp/tools.py directamente y capturar el error"""

import sys
import os
from pathlib import Path

# Configurar PYTHONPATH como lo hace main.py
SCRIPT_DIR = Path(__file__).parent.absolute()
SCM_DIR = SCRIPT_DIR.parent / "scm"
GCP_DIR = SCM_DIR / "gcp"

# Agregar scm/ al PYTHONPATH
sys.path.insert(0, str(SCM_DIR))
os.environ["PYTHONPATH"] = str(SCM_DIR)

print("=" * 80)
print("EJECUTANDO GCP/TOOLS.PY DIRECTAMENTE")
print("=" * 80)
print(f"\nPYTHONPATH: {sys.path[0]}")
print(f"Directorio: {GCP_DIR}")

# Cambiar al directorio de gcp/
os.chdir(str(GCP_DIR))

print(f"\nDirectorio actual: {os.getcwd()}")

# Ejecutar el archivo como script
try:
    with open(str(GCP_DIR / "tools.py"), 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Ejecutar el código
    exec(code, {'__name__': '__main__', '__file__': str(GCP_DIR / "tools.py")})
    
except Exception as e:
    import traceback
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    print("\nTraceback completo:")
    traceback.print_exc()
