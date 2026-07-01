#!/usr/bin/env python3
"""
Base Launcher - Módulo centralizado para funciones comunes de todas las plataformas.

Consolida funciones duplicadas como:
- clear_screen()
- print_header() / print_header_rich() / print_header_fallback()
- print_menu() / print_menu_rich() / print_menu_fallback()
- get_menu_order()
- build_system_options()
- get_auto_tools()
- run_tool()
- log_command()

Reduce código duplicado en ~1,080 líneas.
"""

import os
import sys
import platform
import subprocess
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime as dt

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    from rich.box import ROUNDED, DOUBLE_EDGE
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


class Colors:
    """Códigos ANSI para colores en terminal."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def clear_screen():
    """Limpia la pantalla de la consola."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')


def print_header(title: str, subtitle: str, description: str, emoji: str = "🛠️", 
                 border_color: str = "cyan", platform_name: str = ""):
    """
    Imprime el encabezado del menú de forma consistente.
    
    Args:
        title: Título principal
        subtitle: Subtítulo (versión y autor)
        description: Descripción de la herramienta
        emoji: Emoji para el título
        border_color: Color del borde (cyan, magenta, etc.)
        platform_name: Nombre de la plataforma (para fallback)
    """
    clear_screen()
    
    if RICH_AVAILABLE and console:
        title_text = Text()
        title_text.append(f"{emoji}  ", style="bold white")
        title_text.append(title, style="bold cyan")
        title_text.append(f"  {emoji}", style="bold white")
        
        subtitle_text = Text()
        subtitle_text.append(subtitle, style="bold green")
        
        panel = Panel(
            Align.center(
                Text.assemble(
                    title_text,
                    "\n",
                    subtitle_text,
                    "\n",
                    Text(description, style="dim white")
                )
            ),
            box=DOUBLE_EDGE,
            border_style=border_color,
            padding=(1, 2),
            expand=False,
        )
        console.print(Align.left(panel))
        console.print()
    else:
        print(f"{Colors.HEADER}{'='*60}")
        print(f"{(platform_name or title):^60}")
        print(f"{subtitle:^60}")
        print(f"{'='*60}{Colors.ENDC}\n")


def _menu_sort_key(key: str) -> Tuple:
    """Ordena claves numéricamente."""
    if key.isdigit():
        return (0, int(key))
    return (1, key)


def get_menu_order(tools: Dict, group_order: List[str], 
                  system_keys: List[str] = None) -> List[str]:
    """
    Retorna las claves del menú ordenadas por grupo y numéricamente.
    
    Args:
        tools: Diccionario TOOLS con todas las herramientas
        group_order: Lista de grupos en orden (ej: ["core", "analysis", "system"])
        system_keys: Claves de sistema a incluir al final (ej: ["A", "Q"])
    
    Returns:
        Lista de claves ordenadas
    """
    system_keys = system_keys or ["Q"]
    ordered: List[str] = []
    
    for group_key in group_order:
        group_keys = [
            key for key, tool in tools.items()
            if tool.get("group", "system") == group_key and key not in system_keys
        ]
        group_keys.sort(key=_menu_sort_key)
        ordered.extend(group_keys)
    
    # Agregar claves de sistema al final
    for sys_key in system_keys:
        if sys_key in tools:
            ordered.append(sys_key)
    
    return ordered


def get_auto_tools(tools: Dict, group_order: List[str], 
                  exclude_list: List[str] = None) -> List[str]:
    """
    Genera lista de herramientas para auto_run dinámicamente.
    
    Args:
        tools: Diccionario TOOLS
        group_order: Lista de grupos en orden
        exclude_list: IDs a excluir
    
    Returns:
        Lista de IDs de herramientas válidas, ordenadas por grupo
    """
    exclude_list = exclude_list or []
    auto_tools = []
    
    for group_key in group_order:
        group_tools = [
            key for key, tool in tools.items()
            if (tool.get("group") == group_key and 
                key not in ("Q", "A", "B", "_system_options") and
                key not in exclude_list)
        ]
        
        group_tools.sort(key=_menu_sort_key)
        auto_tools.extend(group_tools)
    
    return auto_tools


def build_system_options(tools: Dict, group_order: List[str]):
    """
    Construye las opciones de sistema dinámicamente.
    
    Args:
        tools: Diccionario TOOLS (se modifica in-place)
        group_order: Lista de grupos en orden
    """
    system_opts = tools.get("_system_options", {})
    
    for key, opt_config in system_opts.items():
        if opt_config.get("type") in ("auto_run", "auto_run_json"):
            exclude = opt_config.get("exclude", [])
            auto_tools = get_auto_tools(tools, group_order, exclude)
            
            tools[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "auto_tools": auto_tools,
                "group": "system",
                "status": "ready"
            }
        else:
            tools[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "group": "system",
                "status": opt_config.get("type", "exit")
            }
    
    if "_system_options" in tools:
        del tools["_system_options"]


def print_menu(tools: Dict, group_order: List[str], tool_groups: Dict,
              status_indicators: Dict = None):
    """
    Muestra el menú principal de forma consistente.
    
    Args:
        tools: Diccionario TOOLS
        group_order: Lista de grupos en orden
        tool_groups: Diccionario con info de grupos (emoji, name, color)
        status_indicators: Diccionario con indicadores de estado
    """
    status_indicators = status_indicators or {}
    
    if RICH_AVAILABLE and console:
        _print_menu_rich(tools, group_order, tool_groups)
    else:
        _print_menu_fallback(tools, group_order, tool_groups, status_indicators)


def _print_menu_rich(tools: Dict, group_order: List[str], tool_groups: Dict):
    """Muestra el menú con Rich."""
    table = Table(
        title="🛠️  Menú Principal",
        title_style="bold white",
        box=ROUNDED,
        header_style="bold cyan",
        border_style="blue",
        show_lines=False,
        pad_edge=True,
        expand=False,
    )
    
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Grupo", justify="left", width=18)
    table.add_column("Herramienta", justify="left", style="white")
    table.add_column("Descripción", justify="left", style="dim", min_width=40)
    
    sorted_keys = get_menu_order(tools, group_order, system_keys=["A", "Q"])
    
    for key in sorted_keys:
        tool = tools[key]
        group_key = tool.get("group", "system")
        group_info = tool_groups.get(group_key, tool_groups.get("system", {}))
        group_text = f"{group_info.get('emoji', '⚙️')} {group_info.get('name', 'Sistema')}"
        
        if key == "Q":
            key_style = "bold yellow"
            name_style = "yellow"
        elif key == "A":
            key_style = "bold magenta"
            name_style = "magenta"
        else:
            key_style = "bold cyan"
            name_style = "white"
        
        table.add_row(
            f"[{key_style}]{key}[/{key_style}]",
            f"[{group_info.get('color', 'white')}]{group_text}[/{group_info.get('color', 'white')}]",
            f"[{name_style}]{tool['name']}[/{name_style}]",
            tool.get('description', '')
        )
    
    console.print(table)
    console.print()


def _print_menu_fallback(tools: Dict, group_order: List[str], tool_groups: Dict,
                        status_indicators: Dict):
    """Muestra el menú sin Rich."""
    print(f"{Colors.BOLD}Menú Principal:{Colors.ENDC}\n")
    
    sorted_keys = get_menu_order(tools, group_order, system_keys=["A", "Q"])
    
    for key in sorted_keys:
        tool = tools[key]
        group_key = tool.get("group", "system")
        group_info = tool_groups.get(group_key, {"emoji": "⚙️", "name": "Sistema"})
        status_emoji = status_indicators.get(tool.get("status", "ready"), ("⚪",))[0]
        
        if key == "Q":
            print(f"  {Colors.WARNING}[{key}]{Colors.ENDC} {status_emoji} {tool['name']}")
        else:
            print(f"  {Colors.BLUE}[{key}]{Colors.ENDC} {status_emoji} [{group_info['name']}] {tool['name']} - {tool['description']}")
    print()


def log_command(cmd: List[str], status: str = "EXEC", 
               platform: str = "unknown", output_dir: str = "outcome") -> None:
    """
    Registra el comando en el log global.
    
    Args:
        cmd: Lista de comandos
        status: Estado (EXEC, ERROR, etc.)
        platform: Nombre de la plataforma
        output_dir: Directorio de salida
    """
    if os.environ.get("DEVSECOPS_LOG_COMMANDS") != "1":
        return
    
    output_dir_env = os.environ.get("DEVSECOPS_OUTPUT_DIR")
    log_dir = Path(output_dir_env) if output_dir_env else Path(output_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    today = dt.now().strftime("%Y%m%d")
    log_file = log_dir / f"commands_{today}.log"
    ts = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    cmd_str = " ".join(str(c) for c in cmd)
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{platform}] [{status}] {cmd_str}\n")


def run_tool(tool_key: str, tools: Dict, base_dir: Path, 
            venv_python: Optional[str] = None,
            install_requirements_fn = None,
            get_venv_python_fn = None) -> None:
    """
    Ejecuta la herramienta seleccionada de forma consistente.
    
    Args:
        tool_key: Clave de la herramienta
        tools: Diccionario TOOLS
        base_dir: Directorio base del proyecto
        venv_python: Ruta al python del venv (si no se proporciona, se obtiene)
        install_requirements_fn: Función para instalar requirements
        get_venv_python_fn: Función para obtener python del venv
    """
    if tool_key not in tools:
        print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return
    
    tool = tools[tool_key]
    
    if tool_key == "Q":
        print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
        sys.exit(0)
    
    print(f"\n{Colors.HEADER}=== {tool['name']} ==={Colors.ENDC}")
    print(f"{tool['description']}\n")
    
    # Obtener python del venv si no se proporciona
    if not venv_python and get_venv_python_fn:
        venv_python = get_venv_python_fn()
        if not venv_python:
            print(f"{Colors.FAIL}No se pudo preparar el entorno virtual. Abortando herramienta.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
    
    # Instalar requirements si es necesario
    if tool.get("requirements") and install_requirements_fn:
        if not install_requirements_fn(tool["requirements"], venv_python):
            print(f"{Colors.FAIL}No se pudieron instalar las dependencias necesarias.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
    
    # Construir comando
    script_path = base_dir / tool["path"]
    
    if not script_path.exists():
        print(f"{Colors.FAIL}Error: No se encontró el script {script_path}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    is_shell_script = str(script_path).endswith('.sh')
    if is_shell_script:
        if platform.system() == "Windows":
            print(f"\n{Colors.FAIL}{'='*60}{Colors.ENDC}")
            print(f"{Colors.FAIL}  ⚠️  HERRAMIENTA NO COMPATIBLE CON WINDOWS{Colors.ENDC}")
            print(f"{Colors.FAIL}{'='*60}{Colors.ENDC}")
            print(f"\n{Colors.WARNING}La herramienta '{tool['name']}' es un script shell (.sh){Colors.ENDC}")
            print(f"{Colors.WARNING}y solo puede ejecutarse en sistemas Linux/Unix.{Colors.ENDC}")
            print(f"\n{Colors.CYAN}Opciones para usar esta herramienta:{Colors.ENDC}")
            print(f"  1. Ejecutar este launcher en {Colors.BOLD}WSL (Windows Subsystem for Linux){Colors.ENDC}")
            print(f"  2. Usar {Colors.BOLD}Git Bash{Colors.ENDC} si está disponible")
            print(f"  3. Ejecutar desde una máquina Linux nativa")
            print(f"\n{Colors.FAIL}Abortando ejecución.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        cmd = ["sh", str(script_path)]
    else:
        cmd = [venv_python, str(script_path)]
    
    # Agregar argumentos si existen
    args = []
    tool_args = tool.get("args", [])
    
    # Procesar argumentos comunes
    if "--profile" in tool_args:
        print(f"\n{Colors.BOLD}AWS Profile [default]:{Colors.ENDC} ", end="")
        profile = input().strip() or "default"
        args.extend(["--profile", profile])
    
    if "--region" in tool_args:
        print(f"\n{Colors.BOLD}AWS Region [us-east-1]:{Colors.ENDC} ", end="")
        region = input().strip() or "us-east-1"
        args.extend(["--region", region])
    
    if "--output" in tool_args or "-o" in tool_args:
        print(f"\n{Colors.BOLD}Formato de salida (json/csv/table) [json]:{Colors.ENDC} ", end="")
        output_format = input().strip().lower() or "json"
        if output_format in ["json", "csv", "table"]:
            args.extend(["-o", output_format])
    
    cmd.extend(args)
    
    print(f"\n{Colors.CYAN}Ejecutando:{Colors.ENDC} {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al ejecutar la herramienta: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida por el usuario.{Colors.ENDC}")
    
    input("\nPresione Enter para continuar...")
