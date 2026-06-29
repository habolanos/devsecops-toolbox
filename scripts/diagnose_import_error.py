#!/usr/bin/env python3
"""Script de diagnóstico para identificar errores de importación."""

import sys
import os
from pathlib import Path

# Rutas
SCRIPT_DIR = Path(__file__).parent.absolute()
SCM_DIR = SCRIPT_DIR.parent / "scm"
AZDO_DIR = SCM_DIR / "azdo"
GCP_DIR = SCM_DIR / "gcp"
AWS_DIR = SCM_DIR / "aws"

print("=" * 80)
print("DIAGNÓSTICO DE ERRORES DE IMPORTACIÓN")
print("=" * 80)

# 1. Verificar que search_module.py existe
print("\n1. Verificando ubicación de search_module.py:")
search_module_path = SCM_DIR / "search_module.py"
if search_module_path.exists():
    print(f"   ✅ Encontrado: {search_module_path}")
else:
    print(f"   ❌ NO ENCONTRADO: {search_module_path}")

# 2. Verificar PYTHONPATH actual
print("\n2. PYTHONPATH actual:")
pythonpath = os.environ.get("PYTHONPATH", "")
if pythonpath:
    print(f"   Valor: {pythonpath}")
    for path in pythonpath.split(os.pathsep):
        print(f"     - {path}")
else:
    print("   ⚠️  PYTHONPATH no está configurado")

# 3. Verificar sys.path
print("\n3. sys.path actual:")
for i, path in enumerate(sys.path):
    marker = "✅" if path else "❌"
    print(f"   {marker} [{i}] {path}")

# 4. Intentar importar search_module desde diferentes ubicaciones
print("\n4. Intentando importar search_module:")

# 4a. Desde scm/
print("\n   a) Desde scm/:")
sys.path.insert(0, str(SCM_DIR))
try:
    from search_module import search_and_select_tools
    print(f"      ✅ Importación exitosa desde scm/")
except ImportError as e:
    print(f"      ❌ Error: {e}")
except Exception as e:
    print(f"      ❌ Error inesperado: {type(e).__name__}: {e}")

# 4b. Desde azdo/
print("\n   b) Desde azdo/:")
sys.path.insert(0, str(AZDO_DIR))
try:
    from search_module import search_and_select_tools
    print(f"      ✅ Importación exitosa desde azdo/")
except ImportError as e:
    print(f"      ❌ Error: {e}")
except Exception as e:
    print(f"      ❌ Error inesperado: {type(e).__name__}: {e}")

# 4c. Desde gcp/
print("\n   c) Desde gcp/:")
sys.path.insert(0, str(GCP_DIR))
try:
    from search_module import search_and_select_tools
    print(f"      ✅ Importación exitosa desde gcp/")
except ImportError as e:
    print(f"      ❌ Error: {e}")
except Exception as e:
    print(f"      ❌ Error inesperado: {type(e).__name__}: {e}")

# 5. Verificar que search_module.py es válido
print("\n5. Verificando validez de search_module.py:")
try:
    with open(search_module_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'def search_and_select_tools' in content:
        print(f"   ✅ Función search_and_select_tools encontrada")
    else:
        print(f"   ❌ Función search_and_select_tools NO encontrada")
    
    # Verificar sintaxis
    try:
        compile(content, str(search_module_path), 'exec')
        print(f"   ✅ Sintaxis válida")
    except SyntaxError as e:
        print(f"   ❌ Error de sintaxis: {e}")
except Exception as e:
    print(f"   ❌ Error al leer archivo: {e}")

# 6. Intentar ejecutar azdo/tools.py
print("\n6. Intentando ejecutar azdo/tools.py:")
azdo_tools_path = AZDO_DIR / "tools.py"
if azdo_tools_path.exists():
    print(f"   ✅ Archivo encontrado: {azdo_tools_path}")
    
    # Intentar importarlo
    sys.path.insert(0, str(AZDO_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("azdo_tools", str(azdo_tools_path))
        azdo_tools = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(azdo_tools)
        print(f"   ✅ Módulo azdo/tools.py cargado exitosamente")
    except ImportError as e:
        print(f"   ❌ Error de importación: {e}")
    except Exception as e:
        print(f"   ❌ Error inesperado: {type(e).__name__}: {e}")
else:
    print(f"   ❌ Archivo NO encontrado: {azdo_tools_path}")

print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
