#!/usr/bin/env python3
"""Script para ejecutar gcp/tools.py y capturar el traceback completo"""

import sys
import os
import traceback
from pathlib import Path

# Configurar PYTHONPATH como lo hace main.py
SCRIPT_DIR = Path(__file__).parent.absolute()
SCM_DIR = SCRIPT_DIR.parent / "scm"
GCP_DIR = SCM_DIR / "gcp"

# Agregar scm/ al PYTHONPATH
sys.path.insert(0, str(SCM_DIR))
os.environ["PYTHONPATH"] = str(SCM_DIR)

print("=" * 80)
print("CAPTURANDO TRACEBACK DE GCP/TOOLS.PY")
print("=" * 80)

# Cambiar al directorio de gcp/
os.chdir(str(GCP_DIR))

# Ejecutar el archivo como script
try:
    with open(str(GCP_DIR / "tools.py"), 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Ejecutar el código
    exec(code, {'__name__': '__main__', '__file__': str(GCP_DIR / "tools.py")})
    
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    print("\nTraceback completo:")
    traceback.print_exc()
    
    # Mostrar información adicional
    print("\n" + "=" * 80)
    print("INFORMACIÓN DEL ERROR")
    print("=" * 80)
    
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    # Recorrer el traceback
    tb = exc_traceback
    while tb:
        frame = tb.tb_frame
        lineno = tb.tb_lineno
        filename = frame.f_code.co_filename
        funcname = frame.f_code.co_name
        
        print(f"\nArchivo: {filename}")
        print(f"Función: {funcname}")
        print(f"Línea: {lineno}")
        
        # Mostrar el código de la línea
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if lineno <= len(lines):
                print(f"Código: {lines[lineno-1].strip()}")
        except:
            pass
        
        # Mostrar variables locales
        print(f"Variables locales: {list(frame.f_locals.keys())}")
        
        tb = tb.tb_next
