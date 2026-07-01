#!/usr/bin/env python3
"""
Script para refactorizar todos los tools.py de las plataformas para usar base_launcher.py
"""

import re
from pathlib import Path

PLATFORMS = [
    ("scm/aws/tools.py", "AWS Tools"),
    ("scm/gcp/tools.py", "GCP Tools"),
    ("scm/kpi_analyzer/tools.py", "KPI Analyzer"),
]

def refactor_platform(filepath: str, platform_name: str):
    """Refactoriza un archivo tools.py para usar base_launcher"""
    
    print(f"\n{'='*80}")
    print(f"REFACTORIZANDO: {platform_name}")
    print(f"{'='*80}")
    
    file_path = Path(filepath)
    
    if not file_path.exists():
        print(f"❌ Archivo no encontrado: {filepath}")
        return False
    
    # Leer el archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_size = len(content)
    
    # 1. Agregar import de base_launcher
    print("\n1. Agregando import de base_launcher...")
    import_section_end = content.find("# ═══════════════════════════════════════════════════════════════════════════════")
    if import_section_end > 0:
        import_line = "\ntry:\n    from base_launcher import (\n        clear_screen, print_header, print_menu,\n        get_menu_order, get_auto_tools, build_system_options,\n        log_command, run_tool, Colors\n    )\n    BASE_LAUNCHER_AVAILABLE = True\nexcept ImportError:\n    BASE_LAUNCHER_AVAILABLE = False\n"
        content = content[:import_section_end] + import_line + "\n" + content[import_section_end:]
        print("   ✅ Import agregado")
    
    # 2. Reemplazar clear_screen()
    print("2. Reemplazando clear_screen()...")
    clear_screen_pattern = r"def clear_screen\(\):.*?(?=\ndef )"
    if re.search(clear_screen_pattern, content, re.DOTALL):
        new_clear_screen = """def clear_screen():
    \"\"\"Limpia la pantalla (usa base_launcher si está disponible).\"\"\"
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import clear_screen as _clear_screen
        _clear_screen()
    else:
        import os, platform
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')

"""
        content = re.sub(clear_screen_pattern, new_clear_screen, content, flags=re.DOTALL)
        print("   ✅ clear_screen() reemplazada")
    
    # 3. Reemplazar get_auto_tools()
    print("3. Reemplazando get_auto_tools()...")
    get_auto_tools_pattern = r"def get_auto_tools\(exclude_list.*?\n    return auto_tools"
    if re.search(get_auto_tools_pattern, content, re.DOTALL):
        new_get_auto_tools = """def get_auto_tools(exclude_list: List[str] = None) -> List[str]:
    \"\"\"Genera lista de herramientas para auto_run dinámicamente.\"\"\"
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import get_auto_tools as _get_auto_tools
        return _get_auto_tools(
            tools=TOOLS,
            group_order=GROUP_ORDER,
            exclude_list=exclude_list
        )
    else:
        exclude_list = exclude_list or []
        auto_tools = []
        for group_key in GROUP_ORDER:
            group_tools = [
                key for key, tool in TOOLS.items()
                if (tool.get("group") == group_key and 
                    key not in ("Q", "A", "_system_options") and
                    key not in exclude_list)
            ]
            group_tools.sort(key=_menu_sort_key)
            auto_tools.extend(group_tools)
        return auto_tools"""
        content = re.sub(get_auto_tools_pattern, new_get_auto_tools, content, flags=re.DOTALL)
        print("   ✅ get_auto_tools() reemplazada")
    
    # 4. Reemplazar build_system_options()
    print("4. Reemplazando build_system_options()...")
    build_system_options_pattern = r"def build_system_options\(\):.*?del TOOLS\[\"_system_options\"\]"
    if re.search(build_system_options_pattern, content, re.DOTALL):
        new_build_system_options = """def build_system_options():
    \"\"\"Construye las opciones de sistema dinámicamente.\"\"\"
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import build_system_options as _build_system_options
        _build_system_options(TOOLS, GROUP_ORDER)
    else:
        system_opts = TOOLS.get("_system_options", {})
        for key, opt_config in system_opts.items():
            if opt_config.get("type") in ("auto_run", "auto_run_json"):
                exclude = opt_config.get("exclude", [])
                auto_tools = get_auto_tools(exclude)
                TOOLS[key] = {
                    "name": opt_config["name"],
                    "description": opt_config["description"],
                    "auto_tools": auto_tools,
                    "group": "system",
                    "status": "ready"
                }
            else:
                TOOLS[key] = {
                    "name": opt_config["name"],
                    "description": opt_config["description"],
                    "group": "system",
                    "status": opt_config.get("type", "exit")
                }
        if "_system_options" in TOOLS:
            del TOOLS["_system_options"]"""
        content = re.sub(build_system_options_pattern, new_build_system_options, content, flags=re.DOTALL)
        print("   ✅ build_system_options() reemplazada")
    
    # 5. Reemplazar get_menu_order()
    print("5. Reemplazando get_menu_order()...")
    get_menu_order_pattern = r"def get_menu_order\(\).*?return ordered"
    if re.search(get_menu_order_pattern, content, re.DOTALL):
        new_get_menu_order = """def get_menu_order() -> List[str]:
    \"\"\"Retorna las claves del menú ordenadas.\"\"\"
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import get_menu_order as _get_menu_order
        return _get_menu_order(
            tools=TOOLS,
            group_order=GROUP_ORDER,
            system_keys=["A", "Q"]
        )
    else:
        ordered: List[str] = []
        for group_key in GROUP_ORDER:
            group_keys = [
                key for key, tool in TOOLS.items()
                if tool.get("group", "system") == group_key and key not in ("Q", "A")
            ]
            group_keys.sort(key=_menu_sort_key)
            ordered.extend(group_keys)
        if "A" in TOOLS:
            ordered.append("A")
        if "Q" in TOOLS:
            ordered.append("Q")
        return ordered"""
        content = re.sub(get_menu_order_pattern, new_get_menu_order, content, flags=re.DOTALL)
        print("   ✅ get_menu_order() reemplazada")
    
    # Guardar el archivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    new_size = len(content)
    reduction = original_size - new_size
    reduction_pct = (reduction / original_size * 100) if original_size > 0 else 0
    
    print(f"\n✅ {platform_name} refactorizada")
    print(f"   Tamaño original: {original_size} bytes")
    print(f"   Tamaño nuevo: {new_size} bytes")
    print(f"   Reducción: {reduction} bytes ({reduction_pct:.1f}%)")
    
    return True

# Refactorizar todas las plataformas
print("=" * 80)
print("REFACTORIZACIÓN DE TODAS LAS PLATAFORMAS")
print("=" * 80)

success_count = 0
for filepath, platform_name in PLATFORMS:
    if refactor_platform(filepath, platform_name):
        success_count += 1

print("\n" + "=" * 80)
print(f"✅ REFACTORIZACIÓN COMPLETADA: {success_count}/{len(PLATFORMS)} plataformas")
print("=" * 80)
print("\nPróximos pasos:")
print("  1. Verificar que los archivos se vean correctos")
print("  2. Ejecutar cada tools.py para verificar que funcione")
print("  3. Hacer commit de los cambios")
