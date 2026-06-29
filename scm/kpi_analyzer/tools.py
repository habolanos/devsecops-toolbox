#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KPI Analyzer Tools — DevSecOps Toolbox
Menú interactivo para análisis de KPIs DevSecOps

Version: 1.0.0
Author: Harold Adrian
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional

# Auto-instalación de Rich
def _ensure_rich():
    """Verifica si rich está instalado; si no, lo instala automáticamente."""
    try:
        import rich
        return True
    except ImportError:
        pass
    
    req_file = Path(__file__).parent / "requirements.txt"
    pip_args = [sys.executable, "-m", "pip", "install", "-q"]
    if req_file.exists():
        pip_args += ["-r", str(req_file)]
        print("📦 Instalando dependencias desde requirements.txt...")
    else:
        print("📦 Instalando rich para interfaz moderna...")
        pip_args.append("rich")
    
    try:
        subprocess.check_call(pip_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Dependencias instaladas correctamente.\n")
        return True
    except subprocess.CalledProcessError:
        print("⚠️  No se pudo instalar rich. Se usará interfaz básica.\n")
        return False

RICH_AVAILABLE = _ensure_rich()

if RICH_AVAILABLE:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt
    from rich.box import ROUNDED, DOUBLE_EDGE

try:
    from search_module import search_and_select_tools
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# Metadata
__version__ = "1.0.0"
__author__ = "Harold Adrian"

# Paths
BASE_DIR = Path(__file__).parent.absolute()
HOST_PYTHON = sys.executable or "python"

# Console
console = Console() if RICH_AVAILABLE else None

# Colores fallback
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Herramientas disponibles
TOOLS = {
    "1": {
        "name": "Análisis Básico de KPIs",
        "emoji": "📊",
        "script": "analyze_kpis.py",
        "args": [],
        "description": "Analizar todos los KPIs desde salidas JSON"
    },
    "2": {
        "name": "Análisis por Plataforma",
        "emoji": "🎯",
        "script": "analyze_kpis.py",
        "args": None,  # Se preguntará interactivamente
        "description": "Filtrar análisis por plataforma (GCP, AZDO, AWS, Terminal)"
    },
    "3": {
        "name": "Evaluación de Madurez",
        "emoji": "🎯",
        "script": "analyze_kpis.py",
        "args": ["--maturity"],
        "description": "Mostrar evaluación de madurez DevSecOps (6 niveles)"
    },
    "4": {
        "name": "Generar Reporte JSON",
        "emoji": "📄",
        "script": "analyze_kpis.py",
        "args": ["--output", "json"],
        "description": "Exportar resultados en formato JSON"
    },
    "5": {
        "name": "Generar Reporte CSV",
        "emoji": "📊",
        "script": "analyze_kpis.py",
        "args": ["--output", "csv"],
        "description": "Exportar resultados en formato CSV"
    },
    "6": {
        "name": "Generar Reporte HTML Simple",
        "emoji": "🌐",
        "script": "analyze_kpis.py",
        "args": ["--output", "html"],
        "description": "Exportar reporte HTML básico con estilos"
    },
    "7": {
        "name": "Dashboard Estático (HTML + Chart.js)",
        "emoji": "📈",
        "script": "analyze_kpis.py",
        "args": ["--dashboard", "--maturity"],
        "description": "Generar dashboard HTML interactivo con gráficos"
    },
    "8": {
        "name": "Dashboard Interactivo (Streamlit)",
        "emoji": "🚀",
        "script": "streamlit_app.py",
        "args": None,  # Streamlit usa su propio comando
        "description": "Lanzar dashboard web interactivo con Streamlit"
    },
    "9": {
        "name": "Análisis Completo (Todos los Reportes)",
        "emoji": "📦",
        "script": "analyze_kpis.py",
        "args": ["--output", "all", "--maturity", "--dashboard"],
        "description": "Generar todos los reportes y dashboard"
    },
    "10": {
        "name": "Ejecutar Tests Unitarios",
        "emoji": "🧪",
        "script": "test_kpi_analyzer.py",
        "args": [],
        "description": "Ejecutar suite de tests del KPI Analyzer"
    },
    "_system_options": {
        "Q": {
            "name": "Volver al Menú Principal",
            "emoji": "🔙",
            "description": "Regresar al launcher principal",
            "type": "exit"
        }
    }
}

def build_system_options():
    """
    Construye las opciones de sistema (Q) dinámicamente.
    Reemplaza el hardcode actual con generación dinámica.
    """
    system_opts = TOOLS.get("_system_options", {})
    
    for key, opt_config in system_opts.items():
        # Opciones simples (como "Q")
        TOOLS[key] = {
            "name": opt_config["name"],
            "emoji": opt_config.get("emoji", "🔙"),
            "script": None,
            "args": None,
            "description": opt_config["description"]
        }

def _init_system_options():
    """Inicializa las opciones de sistema (Q) dinámicamente."""
    build_system_options()

_init_system_options()

def clear_screen():
    """Limpia la pantalla de la consola."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def print_header_rich():
    """Imprime el encabezado con Rich."""
    clear_screen()
    
    title = Text()
    title.append("📊  ", style="bold white")
    title.append("KPI Analyzer", style="bold magenta")
    title.append("  📊", style="bold white")
    
    subtitle = Text()
    subtitle.append(f"v{__version__}", style="bold green")
    subtitle.append(" | ", style="dim")
    subtitle.append(f"by {__author__}", style="italic yellow")
    
    panel = Panel(
        Text.assemble(
            title,
            "\n",
            subtitle,
            "\n",
            Text("Análisis de KPIs DevSecOps con Modelo de Madurez", style="dim white")
        ),
        box=DOUBLE_EDGE,
        border_style="magenta",
        padding=(1, 2),
        expand=False,
    )
    console.print(panel)
    console.print()

def print_header_fallback():
    """Imprime el encabezado sin Rich."""
    clear_screen()
    print(f"{'='*70}")
    print(f"{'KPI ANALYZER - DEVSECOPS TOOLBOX':^70}")
    print(f"{'v' + __version__:^70}")
    print(f"{'='*70}\n")

def print_header():
    """Imprime el encabezado del menú."""
    if RICH_AVAILABLE and console:
        print_header_rich()
    else:
        print_header_fallback()

def print_menu_rich():
    """Muestra el menú con Rich."""
    table = Table(
        title="🚀 Herramientas Disponibles",
        title_style="bold white",
        box=ROUNDED,
        header_style="bold cyan",
        border_style="magenta",
        show_lines=False,
        pad_edge=True,
        expand=False,
    )
    
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Herramienta", justify="left", width=40)
    table.add_column("Descripción", justify="left", style="dim", min_width=35)
    
    for key, tool in TOOLS.items():
        if key == "Q":
            name_style = "bold yellow"
            key_style = "bold yellow"
        else:
            name_style = "cyan"
            key_style = "bold cyan"
        
        tool_name = f"{tool['emoji']} {tool['name']}"
        
        table.add_row(
            f"[{key_style}]{key}[/{key_style}]",
            f"[{name_style}]{tool_name}[/{name_style}]",
            tool['description']
        )
    
    console.print(table)
    console.print()

def print_menu_fallback():
    """Muestra el menú sin Rich."""
    print(f"{Colors.BOLD}Herramientas Disponibles:{Colors.ENDC}\n")
    
    for key, tool in TOOLS.items():
        if key == "Q":
            style = Colors.WARNING
        else:
            style = Colors.CYAN
        
        print(f"  {style}[{key}]{Colors.ENDC} {tool['emoji']} {tool['name']}")
        print(f"      {tool['description']}")
    print()

def print_menu():
    """Muestra el menú principal."""
    if RICH_AVAILABLE and console:
        print_menu_rich()
    else:
        print_menu_fallback()

def get_platform_choice():
    """Solicita al usuario que seleccione una plataforma."""
    platforms = {
        "1": "gcp",
        "2": "azdo",
        "3": "aws",
        "4": "terminal",
        "5": "all"
    }
    
    if RICH_AVAILABLE and console:
        console.print("\n[bold cyan]Seleccione una plataforma:[/bold cyan]")
        console.print("  [cyan]1[/cyan] - GCP (Google Cloud Platform)")
        console.print("  [cyan]2[/cyan] - AZDO (Azure DevOps)")
        console.print("  [cyan]3[/cyan] - AWS (Amazon Web Services)")
        console.print("  [cyan]4[/cyan] - Terminal (Scripts universales)")
        console.print("  [cyan]5[/cyan] - Todas las plataformas")
        choice = Prompt.ask("\n[bold cyan]Opción[/]", default="5")
    else:
        print(f"\n{Colors.BOLD}Seleccione una plataforma:{Colors.ENDC}")
        print("  1 - GCP (Google Cloud Platform)")
        print("  2 - AZDO (Azure DevOps)")
        print("  3 - AWS (Amazon Web Services)")
        print("  4 - Terminal (Scripts universales)")
        print("  5 - Todas las plataformas")
        choice = input(f"\n{Colors.CYAN}Opción [5]: {Colors.ENDC}").strip() or "5"
    
    return platforms.get(choice, "all")

def run_tool(tool_key: str):
    """Ejecuta una herramienta específica."""
    if tool_key not in TOOLS:
        if RICH_AVAILABLE and console:
            console.print("[red]❌ Opción no válida.[/red]")
        else:
            print(f"{Colors.FAIL}❌ Opción no válida.{Colors.ENDC}")
        return
    
    tool = TOOLS[tool_key]
    
    if tool_key == "Q":
        if RICH_AVAILABLE and console:
            console.print("\n[bold green]👋 Regresando al menú principal...[/bold green]")
        else:
            print(f"\n{Colors.GREEN}👋 Regresando al menú principal...{Colors.ENDC}")
        sys.exit(0)
    
    script_path = BASE_DIR / tool["script"]
    
    if not script_path.exists():
        if RICH_AVAILABLE and console:
            console.print(f"\n[red]❌ No se encontró: {script_path}[/red]")
        else:
            print(f"\n{Colors.FAIL}❌ No se encontró: {script_path}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    # Preparar argumentos
    args = tool["args"]
    
    # Caso especial: Análisis por plataforma
    if tool_key == "2":
        platform = get_platform_choice()
        args = ["--platform", platform]
    
    # Caso especial: Streamlit
    if tool_key == "8":
        if RICH_AVAILABLE and console:
            console.print(f"\n[bold cyan]🚀 Lanzando Dashboard Streamlit...[/bold cyan]")
            console.print(f"[dim]Acceder en: http://localhost:8501[/dim]\n")
        else:
            print(f"\n{Colors.CYAN}🚀 Lanzando Dashboard Streamlit...{Colors.ENDC}")
            print("Acceder en: http://localhost:8501\n")
        
        try:
            # Verificar si streamlit está instalado
            subprocess.run([HOST_PYTHON, "-m", "streamlit", "--version"], 
                         check=True, capture_output=True)
            
            # Ejecutar streamlit
            subprocess.run([HOST_PYTHON, "-m", "streamlit", "run", str(script_path)])
        except subprocess.CalledProcessError:
            if RICH_AVAILABLE and console:
                console.print("[red]❌ Streamlit no está instalado.[/red]")
                console.print("[yellow]Instalar con: pip install streamlit[/yellow]")
            else:
                print(f"{Colors.FAIL}❌ Streamlit no está instalado.{Colors.ENDC}")
                print("Instalar con: pip install streamlit")
            input("\nPresione Enter para continuar...")
        except KeyboardInterrupt:
            if RICH_AVAILABLE and console:
                console.print("\n[yellow]↩️  Dashboard cerrado[/yellow]")
            else:
                print(f"\n{Colors.WARNING}↩️  Dashboard cerrado{Colors.ENDC}")
        return
    
    # Mostrar mensaje de ejecución
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold cyan]🚀 Ejecutando: {tool['emoji']} {tool['name']}...[/bold cyan]\n")
    else:
        print(f"\n{Colors.CYAN}🚀 Ejecutando: {tool['emoji']} {tool['name']}...{Colors.ENDC}\n")
    
    # Ejecutar script
    try:
        cmd = [HOST_PYTHON, str(script_path)]
        if args:
            cmd.extend(args)
        
        subprocess.run(cmd, check=False)
        
        if RICH_AVAILABLE and console:
            console.print("\n[bold green]✅ Ejecución completada[/bold green]")
        else:
            print(f"\n{Colors.GREEN}✅ Ejecución completada{Colors.ENDC}")
        
    except KeyboardInterrupt:
        if RICH_AVAILABLE and console:
            console.print("\n[yellow]↩️  Ejecución interrumpida[/yellow]")
        else:
            print(f"\n{Colors.WARNING}↩️  Ejecución interrumpida{Colors.ENDC}")
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"\n[red]❌ Error al ejecutar: {e}[/red]")
        else:
            print(f"\n{Colors.FAIL}❌ Error al ejecutar: {e}{Colors.ENDC}")
    
    input("\nPresione Enter para continuar...")

def main():
    """Función principal del menú."""
    while True:
        try:
            print_header()
            print_menu()
            
            # Tip
            if RICH_AVAILABLE and console:
                console.print("[dim]💡 Tip: Seleccione una opción, '/' para buscar o 'Q' para salir[/dim]\n")
                choice = Prompt.ask("[bold cyan]Seleccione una opción[/]", default="Q").strip().upper()
            else:
                choice = input(f"{Colors.BOLD}Seleccione una opción (o '/' para buscar): {Colors.ENDC}").strip().upper()
            
            # Opción de búsqueda
            if choice == "/":
                if SEARCH_AVAILABLE:
                    choice = search_and_select_tools(TOOLS)
                    if choice is None:
                        continue
                else:
                    if RICH_AVAILABLE and console:
                        console.print("[yellow]⚠️  Búsqueda no disponible[/yellow]")
                    else:
                        print(f"\n{Colors.YELLOW}⚠️  Búsqueda no disponible{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
            
            if choice in TOOLS:
                run_tool(choice)
            else:
                if RICH_AVAILABLE and console:
                    console.print("[red]❌ Opción no válida. Intente de nuevo.[/red]")
                else:
                    print(f"\n{Colors.FAIL}❌ Opción no válida. Por favor, intente de nuevo.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                
        except KeyboardInterrupt:
            if RICH_AVAILABLE and console:
                console.print("\n[bold yellow]👋 Saliendo...[/bold yellow]")
            else:
                print(f"\n{Colors.WARNING}👋 Saliendo...{Colors.ENDC}")
            sys.exit(0)
        except Exception as e:
            if RICH_AVAILABLE and console:
                console.print(f"\n[red]❌ Error inesperado: {e}[/red]")
            else:
                print(f"\n{Colors.FAIL}❌ Error inesperado: {e}{Colors.ENDC}")
            input("\nPresione Enter para continuar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}👋 Saliendo...{Colors.ENDC}")
        sys.exit(0)
