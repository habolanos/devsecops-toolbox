#!/usr/bin/env python3
"""
Script para refactorizar scm/azdo/tools.py para usar base_launcher.py

Cambios:
1. Agregar import de base_launcher
2. Reemplazar clear_screen() con base_launcher.clear_screen()
3. Reemplazar print_header() con base_launcher.print_header()
4. Reemplazar print_menu() con base_launcher.print_menu()
5. Reemplazar get_menu_order() con base_launcher.get_menu_order()
6. Reemplazar get_auto_tools() con base_launcher.get_auto_tools()
7. Reemplazar build_system_options() con base_launcher.build_system_options()
8. Eliminar funciones duplicadas
"""

import re
from pathlib import Path

# Ruta del archivo a refactorizar
AZDO_TOOLS = Path("scm/azdo/tools.py")

# Leer el archivo
with open(AZDO_TOOLS, 'r', encoding='utf-8') as f:
    content = f.read()

print("=" * 80)
print("REFACTORIZACIÓN DE scm/azdo/tools.py")
print("=" * 80)

# 1. Agregar import de base_launcher después de otros imports
print("\n1. Agregando import de base_launcher...")

# Buscar la línea después de los imports de search_module
import_section_end = content.find("# ═══════════════════════════════════════════════════════════════════════════════")
if import_section_end > 0:
    # Encontrar el final de los imports
    lines = content[:import_section_end].split('\n')
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('try:') or line.startswith('import ') or line.startswith('from '):
            last_import_idx = i
    
    # Insertar el import de base_launcher
    import_line = "\ntry:\n    from base_launcher import (\n        clear_screen, print_header, print_menu,\n        get_menu_order, get_auto_tools, build_system_options,\n        log_command, run_tool, Colors\n    )\n    BASE_LAUNCHER_AVAILABLE = True\nexcept ImportError:\n    BASE_LAUNCHER_AVAILABLE = False\n"
    
    # Encontrar la posición correcta para insertar
    insert_pos = content.find("# ═══════════════════════════════════════════════════════════════════════════════")
    if insert_pos > 0:
        content = content[:insert_pos] + import_line + "\n" + content[insert_pos:]
        print("   ✅ Import agregado")

# 2. Reemplazar la función clear_screen() con un wrapper
print("\n2. Reemplazando clear_screen()...")
clear_screen_pattern = r"def clear_screen\(\):.*?(?=\ndef )"
if re.search(clear_screen_pattern, content, re.DOTALL):
    content = re.sub(
        clear_screen_pattern,
        "def clear_screen():\n    \"\"\"Limpia la pantalla (usa base_launcher si está disponible).\"\"\"\n    if BASE_LAUNCHER_AVAILABLE:\n        from base_launcher import clear_screen as _clear_screen\n        _clear_screen()\n    else:\n        import os, platform\n        if platform.system() == 'Windows':\n            os.system('cls')\n        else:\n            os.system('clear')\n\n",
        content,
        flags=re.DOTALL
    )
    print("   ✅ clear_screen() reemplazada")

# 3. Reemplazar print_header() - función más compleja
print("\n3. Reemplazando print_header()...")
print_header_pattern = r"def print_header\(\):.*?(?=\ndef )"
if re.search(print_header_pattern, content, re.DOTALL):
    new_print_header = """def print_header():
    \"\"\"Imprime el encabezado del menú.\"\"\"
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import print_header as _print_header
        _print_header(
            title="Azure DevOps Tools",
            subtitle=f"v{__version__} | by {__author__}",
            description=__description__,
            emoji="🔷",
            border_color="cyan",
            platform_name="AZURE DEVOPS TOOLS"
        )
        _print_config_status()
    else:
        clear_screen()
        print(f"{Colors.HEADER}{'='*60}")
        print(f"{'AZURE DEVOPS TOOLS':^60}")
        print(f"v{__version__} | by {__author__}".center(60))
        print(f"{'='*60}{Colors.ENDC}")
        _print_config_status_fallback()
        print()

"""
    content = re.sub(
        print_header_pattern,
        new_print_header,
        content,
        flags=re.DOTALL
    )
    print("   ✅ print_header() reemplazada")

# 4. Reemplazar print_menu()
print("\n4. Reemplazando print_menu()...")
print_menu_pattern = r"def print_menu\(\):.*?(?=\n\ndef )"
if re.search(print_menu_pattern, content, re.DOTALL):
    new_print_menu = """def print_menu():
    \"\"\"Muestra el menú principal.\"\"\"
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import print_menu as _print_menu
        _print_menu(
            tools=TOOLS,
            group_order=GROUP_ORDER,
            tool_groups=TOOL_GROUPS,
            status_indicators=STATUS_INDICATORS
        )
    else:
        if RICH_AVAILABLE and console:
            t = Table(
                title="🛠️  Menú Principal",
                title_style="bold white",
                box=ROUNDED,
                header_style="bold cyan",
                border_style="blue",
                show_lines=False,
                expand=False,
            )
            t.add_column("#",            justify="center", style="bold white", width=4)
            t.add_column("Grupo",        justify="left",   width=20)
            t.add_column("Herramienta",  justify="left",   style="white", min_width=26)
            t.add_column("Descripción",  justify="left",   style="dim",   min_width=46)

            for key in get_menu_order():
                tool       = TOOLS[key]
                group_key  = tool.get("group", "system")
                group_info = TOOL_GROUPS.get(group_key, TOOL_GROUPS["system"])
                group_text = f"{group_info['emoji']} {group_info['name']}"

                if key == "Q":
                    ks, ns = "bold yellow", "yellow"
                elif key == "B":
                    ks, ns = "bold yellow", "yellow"
                elif key == "A":
                    ks, ns = "bold magenta", "magenta"
                else:
                    ks, ns = "bold cyan", "white"

                t.add_row(
                    f"[{ks}]{key}[/{ks}]",
                    f"[{group_info['color']}]{group_text}[/{group_info['color']}]",
                    f"[{ns}]{tool['name']}[/{ns}]",
                    tool.get("description", ""),
                )

            console.print(t)
            console.print()
        else:
            print(f"{Colors.BOLD}Menú Principal:{Colors.ENDC}\\n")
            for key in get_menu_order():
                tool       = TOOLS[key]
                group_info = TOOL_GROUPS.get(tool.get("group", "system"), {})
                emoji      = group_info.get("emoji", "🔧")
                if key == "Q":
                    print(f"  {Colors.WARNING}[{key}]{Colors.ENDC} {tool['name']}")
                elif key == "A":
                    print(f"  {Colors.HEADER}[{key}]{Colors.ENDC} {emoji} {tool['name']} — {tool['description']}")
                else:
                    print(f"  {Colors.BLUE}[{key}]{Colors.ENDC} {emoji} [{group_info.get('name','')}] "
                          f"{tool['name']} — {tool['description']}")
            print()

"""
    content = re.sub(
        print_menu_pattern,
        new_print_menu,
        content,
        flags=re.DOTALL
    )
    print("   ✅ print_menu() reemplazada")

# 5. Reemplazar get_menu_order()
print("\n5. Reemplazando get_menu_order()...")
get_menu_order_pattern = r"def get_menu_order\(\).*?return ordered"
if re.search(get_menu_order_pattern, content, re.DOTALL):
    new_get_menu_order = """def get_menu_order() -> List[str]:
    \"\"\"Retorna las claves del menú ordenadas.\"\"\"
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import get_menu_order as _get_menu_order
        return _get_menu_order(
            tools=TOOLS,
            group_order=GROUP_ORDER,
            system_keys=["B", "A", "Q"]
        )
    else:
        ordered: List[str] = []
        for group_key in GROUP_ORDER:
            keys = [k for k, t in TOOLS.items()
                    if t.get("group") == group_key and k not in ("Q", "A", "B")]
            keys.sort(key=_menu_sort_key)
            ordered.extend(keys)
        if "B" in TOOLS:
            ordered.append("B")
        if "A" in TOOLS:
            ordered.append("A")
        if "Q" in TOOLS:
            ordered.append("Q")
        return ordered"""
    content = re.sub(
        get_menu_order_pattern,
        new_get_menu_order,
        content,
        flags=re.DOTALL
    )
    print("   ✅ get_menu_order() reemplazada")

# 6. Reemplazar get_auto_tools()
print("\n6. Reemplazando get_auto_tools()...")
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
                    key not in ("Q", "A", "B", "_system_options") and
                    key not in exclude_list)
            ]
            group_tools.sort(key=_menu_sort_key)
            auto_tools.extend(group_tools)
        return auto_tools"""
    content = re.sub(
        get_auto_tools_pattern,
        new_get_auto_tools,
        content,
        flags=re.DOTALL
    )
    print("   ✅ get_auto_tools() reemplazada")

# 7. Reemplazar build_system_options()
print("\n7. Reemplazando build_system_options()...")
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
    content = re.sub(
        build_system_options_pattern,
        new_build_system_options,
        content,
        flags=re.DOTALL
    )
    print("   ✅ build_system_options() reemplazada")

# Guardar el archivo refactorizado
with open(AZDO_TOOLS, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 80)
print("✅ REFACTORIZACIÓN COMPLETADA")
print("=" * 80)
print(f"\nArchivo actualizado: {AZDO_TOOLS}")
print("\nCambios realizados:")
print("  ✅ Import de base_launcher agregado")
print("  ✅ clear_screen() reemplazada")
print("  ✅ print_header() reemplazada")
print("  ✅ print_menu() reemplazada")
print("  ✅ get_menu_order() reemplazada")
print("  ✅ get_auto_tools() reemplazada")
print("  ✅ build_system_options() reemplazada")
print("\nPróximos pasos:")
print("  1. Verificar que el archivo se vea correcto")
print("  2. Ejecutar: python scm/azdo/tools.py")
print("  3. Verificar que el menú funcione correctamente")
print("  4. Hacer commit de los cambios")
