#!/usr/bin/env python3
"""Script para probar _init_system_options()"""

import sys
import traceback
from pathlib import Path

# Rutas
SCRIPT_DIR = Path(__file__).parent.absolute()
SCM_DIR = SCRIPT_DIR.parent / "scm"
GCP_DIR = SCM_DIR / "gcp"

print("=" * 80)
print("PROBANDO _init_system_options()")
print("=" * 80)

# Agregar scm/ al path
sys.path.insert(0, str(SCM_DIR))

# Importar el módulo
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("gcp_tools", str(GCP_DIR / "tools.py"))
    gcp_tools = importlib.util.module_from_spec(spec)
    
    print("\n1. Cargando módulo...")
    spec.loader.exec_module(gcp_tools)
    print("   ✅ Módulo cargado")
    
    print("\n2. Verificando que las funciones existen...")
    print(f"   - _init_system_options: {hasattr(gcp_tools, '_init_system_options')}")
    print(f"   - build_system_options: {hasattr(gcp_tools, 'build_system_options')}")
    print(f"   - get_auto_tools: {hasattr(gcp_tools, 'get_auto_tools')}")
    print(f"   - TOOLS: {hasattr(gcp_tools, 'TOOLS')}")
    
    print("\n3. Verificando TOOLS['_system_options']...")
    if "_system_options" in gcp_tools.TOOLS:
        print(f"   ✅ Encontrado: {list(gcp_tools.TOOLS['_system_options'].keys())}")
    else:
        print("   ❌ NO encontrado")
    
    print("\n4. Llamando _init_system_options() manualmente...")
    gcp_tools._init_system_options()
    print("   ✅ Llamada exitosa")
    
    print("\n5. Verificando TOOLS después de _init_system_options()...")
    print(f"   - Total de herramientas: {len(gcp_tools.TOOLS)}")
    print(f"   - Claves del sistema: {[k for k in gcp_tools.TOOLS.keys() if k in ('A', 'Q', '_system_options')]}")
    
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    print("\nTraceback completo:")
    traceback.print_exc()
