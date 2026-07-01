#!/usr/bin/env python3
"""
Script para testear todos los tools.py de las plataformas.

Verifica:
1. Que el módulo se importe sin errores
2. Que las funciones principales existan
3. Que base_launcher esté disponible
4. Que los TOOLS y GROUP_ORDER estén definidos
"""

import sys
import importlib.util
from pathlib import Path

# Rutas de los archivos a testear
PLATFORMS = [
    ("scm/azdo/tools.py", "AZDO Tools"),
    ("scm/aws/tools.py", "AWS Tools"),
    ("scm/gcp/tools.py", "GCP Tools"),
    ("scm/kpi_analyzer/tools.py", "KPI Analyzer"),
]

def test_platform(filepath: str, platform_name: str) -> bool:
    """Testea un archivo tools.py"""
    
    print(f"\n{'='*80}")
    print(f"TESTING: {platform_name}")
    print(f"{'='*80}")
    
    file_path = Path(filepath)
    
    if not file_path.exists():
        print(f"❌ Archivo no encontrado: {filepath}")
        return False
    
    print(f"✅ Archivo encontrado: {filepath}")
    
    # Cargar el módulo
    print("\n1. Importando módulo...")
    try:
        spec = importlib.util.spec_from_file_location("tools_module", file_path)
        module = importlib.util.module_from_spec(spec)
        
        # Agregar el directorio padre al sys.path para que pueda importar módulos locales
        parent_dir = str(file_path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Agregar scm/ al sys.path para que pueda importar base_launcher
        scm_dir = str(file_path.parent.parent)
        if scm_dir not in sys.path:
            sys.path.insert(0, scm_dir)
        
        spec.loader.exec_module(module)
        print("   ✅ Módulo importado correctamente")
    except Exception as e:
        print(f"   ❌ Error al importar módulo: {e}")
        return False
    
    # Verificar que base_launcher esté disponible
    print("\n2. Verificando base_launcher...")
    try:
        if hasattr(module, 'BASE_LAUNCHER_AVAILABLE'):
            if module.BASE_LAUNCHER_AVAILABLE:
                print("   ✅ base_launcher disponible")
            else:
                print("   ⚠️  base_launcher NO disponible (usando fallback)")
        else:
            print("   ⚠️  BASE_LAUNCHER_AVAILABLE no definido")
    except Exception as e:
        print(f"   ❌ Error al verificar base_launcher: {e}")
        return False
    
    # Verificar que TOOLS esté definido
    print("\n3. Verificando TOOLS...")
    try:
        if hasattr(module, 'TOOLS'):
            tools_count = len(module.TOOLS)
            print(f"   ✅ TOOLS definido ({tools_count} herramientas)")
        else:
            print("   ❌ TOOLS no definido")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar TOOLS: {e}")
        return False
    
    # Verificar que GROUP_ORDER esté definido
    print("\n4. Verificando GROUP_ORDER...")
    try:
        if hasattr(module, 'GROUP_ORDER'):
            groups_count = len(module.GROUP_ORDER)
            print(f"   ✅ GROUP_ORDER definido ({groups_count} grupos)")
        else:
            print("   ❌ GROUP_ORDER no definido")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar GROUP_ORDER: {e}")
        return False
    
    # Verificar funciones principales
    print("\n5. Verificando funciones principales...")
    required_functions = [
        'clear_screen',
        'print_header',
        'print_menu',
        'get_menu_order',
        'get_auto_tools',
        'build_system_options',
        'log_command',
        'run_tool'
    ]
    
    missing_functions = []
    for func_name in required_functions:
        if hasattr(module, func_name):
            print(f"   ✅ {func_name}()")
        else:
            print(f"   ❌ {func_name}() NO ENCONTRADA")
            missing_functions.append(func_name)
    
    if missing_functions:
        print(f"\n   ❌ Funciones faltantes: {', '.join(missing_functions)}")
        return False
    
    # Verificar que Colors esté disponible
    print("\n6. Verificando Colors...")
    try:
        if hasattr(module, 'Colors'):
            print("   ✅ Colors disponible")
        else:
            print("   ❌ Colors no disponible")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar Colors: {e}")
        return False
    
    # Intentar llamar a build_system_options()
    print("\n7. Ejecutando build_system_options()...")
    try:
        module.build_system_options()
        print("   ✅ build_system_options() ejecutada correctamente")
    except Exception as e:
        print(f"   ❌ Error al ejecutar build_system_options(): {e}")
        return False
    
    # Intentar llamar a get_menu_order()
    print("\n8. Ejecutando get_menu_order()...")
    try:
        menu_order = module.get_menu_order()
        print(f"   ✅ get_menu_order() retornó {len(menu_order)} elementos")
    except Exception as e:
        print(f"   ❌ Error al ejecutar get_menu_order(): {e}")
        return False
    
    print(f"\n✅ {platform_name} PASÓ TODOS LOS TESTS")
    return True

# Ejecutar tests
print("=" * 80)
print("TESTING DE TODAS LAS PLATAFORMAS")
print("=" * 80)

passed = 0
failed = 0

for filepath, platform_name in PLATFORMS:
    if test_platform(filepath, platform_name):
        passed += 1
    else:
        failed += 1

print("\n" + "=" * 80)
print("RESULTADOS FINALES")
print("=" * 80)
print(f"\n✅ Pasados:  {passed}/{len(PLATFORMS)}")
print(f"❌ Fallidos: {failed}/{len(PLATFORMS)}")

if failed == 0:
    print("\n🎉 TODOS LOS TESTS PASARON CORRECTAMENTE")
    sys.exit(0)
else:
    print(f"\n⚠️  {failed} plataforma(s) fallaron los tests")
    sys.exit(1)
