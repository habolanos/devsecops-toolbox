#!/usr/bin/env python3
"""Script para probar la ejecución de gcp/tools.py"""

import sys
import traceback
from pathlib import Path

# Rutas
SCRIPT_DIR = Path(__file__).parent.absolute()
SCM_DIR = SCRIPT_DIR.parent / "scm"
GCP_DIR = SCM_DIR / "gcp"

print("=" * 80)
print("PRUEBA DE EJECUCIÓN DE GCP TOOLS.PY")
print("=" * 80)

# Agregar scm/ al path
sys.path.insert(0, str(SCM_DIR))

# Intentar cargar y ejecutar main()
print("\nIntentando cargar gcp/tools.py...")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("gcp_tools", str(GCP_DIR / "tools.py"))
    gcp_tools = importlib.util.module_from_spec(spec)
    
    print("✅ Módulo cargado")
    
    print("\nEjecutando spec.loader.exec_module()...")
    spec.loader.exec_module(gcp_tools)
    
    print("✅ Módulo ejecutado")
    
    print("\nVerificando si main() existe...")
    if hasattr(gcp_tools, 'main'):
        print("✅ main() encontrada")
        
        print("\nIntentando llamar main()...")
        # No llamamos main() porque entraría en un loop interactivo
        # Solo verificamos que existe
        print("✅ main() existe y es callable")
    else:
        print("❌ main() NO encontrada")
        
except Exception as e:
    print(f"❌ Error:")
    print(f"\nTipo de error: {type(e).__name__}")
    print(f"Mensaje: {e}")
    print("\nTraceback completo:")
    traceback.print_exc()
    
    # Análisis detallado
    print("\n" + "=" * 80)
    print("ANÁLISIS DEL ERROR")
    print("=" * 80)
    
    if hasattr(e, '__traceback__'):
        tb = e.__traceback__
        while tb.tb_next:
            tb = tb.tb_next
        
        lineno = tb.tb_lineno
        filename = tb.tb_frame.f_code.co_filename
        
        print(f"\nArchivo: {filename}")
        print(f"Línea: {lineno}")
        print(f"Función: {tb.tb_frame.f_code.co_name}")
        
        # Leer el archivo y mostrar contexto
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = max(0, lineno - 10)
            end = min(len(lines), lineno + 10)
            
            print(f"\nContexto (líneas {start+1}-{end}):")
            for i in range(start, end):
                marker = ">>> " if i == lineno - 1 else "    "
                print(f"{marker}{i+1:4d}: {lines[i]}", end='')
        except Exception as read_err:
            print(f"No se pudo leer el archivo: {read_err}")

print("\n" + "=" * 80)
print("FIN DE LA PRUEBA")
print("=" * 80)
