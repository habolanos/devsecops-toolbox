#!/usr/bin/env python3
"""Script simple para probar GCP tools.py"""

import sys
from pathlib import Path

# Rutas
SCRIPT_DIR = Path(__file__).parent.absolute()
SCM_DIR = SCRIPT_DIR.parent / "scm"
GCP_DIR = SCM_DIR / "gcp"

# Agregar scm/ al path
sys.path.insert(0, str(SCM_DIR))

print("Cargando gcp/tools.py...")

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("gcp_tools", str(GCP_DIR / "tools.py"))
    gcp_tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gcp_tools)
    
    print("✅ GCP tools.py cargado exitosamente")
    print(f"✅ Total de herramientas: {len(gcp_tools.TOOLS)}")
    print(f"✅ Claves del sistema: {[k for k in gcp_tools.TOOLS.keys() if k in ('A', 'Q')]}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
