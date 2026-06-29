#!/usr/bin/env python3
"""Script de diagnóstico detallado para GCP tools.py"""

import sys
import traceback
from pathlib import Path

# Rutas
SCRIPT_DIR = Path(__file__).parent.absolute()
SCM_DIR = SCRIPT_DIR.parent / "scm"
GCP_DIR = SCM_DIR / "gcp"

print("=" * 80)
print("DIAGNÓSTICO DETALLADO DE GCP TOOLS.PY")
print("=" * 80)

# Agregar scm/ al path
sys.path.insert(0, str(SCM_DIR))

# Intentar cargar gcp/tools.py con traceback completo
print("\nIntentando cargar gcp/tools.py...")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("gcp_tools", str(GCP_DIR / "tools.py"))
    gcp_tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gcp_tools)
    print("✅ Módulo gcp/tools.py cargado exitosamente")
except Exception as e:
    print(f"❌ Error al cargar gcp/tools.py:")
    print(f"\nTipo de error: {type(e).__name__}")
    print(f"Mensaje: {e}")
    print("\nTraceback completo:")
    traceback.print_exc()
    
    # Intentar identificar la línea exacta
    print("\n" + "=" * 80)
    print("ANÁLISIS DEL ERROR")
    print("=" * 80)
    
    # Leer el archivo y mostrar líneas alrededor del error
    if hasattr(e, '__traceback__'):
        tb = e.__traceback__
        while tb.tb_next:
            tb = tb.tb_next
        
        lineno = tb.tb_lineno
        filename = tb.tb_frame.f_code.co_filename
        
        print(f"\nArchivo: {filename}")
        print(f"Línea: {lineno}")
        
        # Leer el archivo y mostrar contexto
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = max(0, lineno - 5)
            end = min(len(lines), lineno + 5)
            
            print(f"\nContexto (líneas {start+1}-{end}):")
            for i in range(start, end):
                marker = ">>> " if i == lineno - 1 else "    "
                print(f"{marker}{i+1:4d}: {lines[i]}", end='')
        except Exception as read_err:
            print(f"No se pudo leer el archivo: {read_err}")

print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
