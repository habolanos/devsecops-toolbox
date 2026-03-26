#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DevSecOps Toolbox - Main Launcher

Punto de entrada unificado para acceder a las herramientas de:
- Azure DevOps (azdo/tools.py)
- Google Cloud Platform (gcp/tools.py)

Uso:
    python main.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.box import ROUNDED, DOUBLE_EDGE, HEAVY
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.0.0"
__author__ = "Harold Adrian"
__description__ = "DevSecOps Toolbox - Launcher Principal"

# Consola Rich
console = Console() if RICH_AVAILABLE else None

# Rutas
BASE_DIR = Path(__file__).parent.absolute()
HOST_PYTHON = sys.executable or "python"

# ═══════════════════════════════════════════════════════════════════════════════
# COLORES FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ═══════════════════════════════════════════════════════════════════════════════
# PLATAFORMAS DISPONIBLES
# ═══════════════════════════════════════════════════════════════════════════════
PLATFORMS = {
    "1": {
        "name": "Google Cloud Platform",
        "short": "GCP",
        "emoji": "☁️",
        "color": "cyan",
        "path": "gcp/tools.py",
        "description": "Herramientas SRE para monitoreo, IAM, networking, Kubernetes y más",
        "status": "ready"
    },
    "2": {
        "name": "Azure DevOps",
        "short": "AZDO",
        "emoji": "🔷",
        "color": "blue",
        "path": "azdo/tools.py",
        "description": "Herramientas para PRs, políticas de rama, releases y drift analysis",
        "status": "ready"
    },
    "3": {
        "name": "Amazon Web Services",
        "short": "AWS",
        "emoji": "🟠",
        "color": "yellow",
        "path": "aws/tools.py",
        "description": "Herramientas para AWS (próximamente)",
        "status": "coming_soon"
    },
    "Q": {
        "name": "Salir",
        "short": "EXIT",
        "emoji": "🚪",
        "color": "white",
        "path": None,
        "description": "Salir del launcher",
        "status": "exit"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# INDICADORES DE ESTADO
# ═══════════════════════════════════════════════════════════════════════════════
STATUS_INDICATORS = {
    "ready": ("🟢", "green", "Disponible"),
    "coming_soon": ("🟡", "yellow", "Próximamente"),
    "error": ("🔴", "red", "Error"),
    "exit": ("🚪", "white", "Salir"),
}


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
    title.append("🛡️  ", style="bold white")
    title.append("DevSecOps Toolbox", style="bold cyan")
    title.append("  🛡️", style="bold white")
    
    panel = Panel(
        Align.center(
            Text.assemble(
                title,
                "\n",
                Text(__description__, style="dim white")
            )
        ),
        box=DOUBLE_EDGE,
        border_style="white",
        padding=(1, 2),
        expand=False,
    )
    console.print(Align.center(panel))
    console.print()


def print_header_fallback():
    """Imprime el encabezado sin Rich."""
    clear_screen()
    print(f"{'='*60}")
    print(f"{'DEVSECOPS TOOLBOX':^60}")
    print(f"{__description__:^60}")
    print(f"{'='*60}\n")


def print_header():
    """Imprime el encabezado del menú."""
    if RICH_AVAILABLE and console:
        print_header_rich()
    else:
        print_header_fallback()


def print_menu_rich():
    """Muestra el menú con Rich."""
    table = Table(
        title="🚀 Seleccione una Plataforma",
        title_style="bold white",
        box=ROUNDED,
        header_style="bold cyan",
        border_style="blue",
        show_lines=True,
        pad_edge=True,
        expand=False,
    )
    
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Estado", justify="center", width=8)
    table.add_column("Plataforma", justify="left", width=25)
    table.add_column("Descripción", justify="left", style="dim", min_width=45)
    
    for key, platform in PLATFORMS.items():
        status = platform.get("status", "ready")
        indicator = STATUS_INDICATORS.get(status, STATUS_INDICATORS["ready"])
        
        # Estilo según estado
        if status == "coming_soon":
            name_style = "yellow dim"
            key_style = "yellow dim"
        elif status == "exit":
            name_style = "white"
            key_style = "bold yellow"
        else:
            name_style = platform.get("color", "white")
            key_style = "bold cyan"
        
        platform_name = f"{platform['emoji']} {platform['name']}"
        
        table.add_row(
            f"[{key_style}]{key}[/{key_style}]",
            indicator[0],
            f"[{name_style}]{platform_name}[/{name_style}]",
            platform.get("description", "")
        )
    
    console.print(table)
    console.print()


def print_menu_fallback():
    """Muestra el menú sin Rich."""
    print(f"{Colors.BOLD}Seleccione una Plataforma:{Colors.ENDC}\n")
    
    for key, platform in PLATFORMS.items():
        status = platform.get("status", "ready")
        indicator = STATUS_INDICATORS.get(status, STATUS_INDICATORS["ready"])
        
        if status == "coming_soon":
            style = Colors.WARNING
        elif status == "exit":
            style = Colors.WARNING
        else:
            style = Colors.CYAN
        
        print(f"  {style}[{key}]{Colors.ENDC} {indicator[0]} {platform['emoji']} {platform['name']}")
        print(f"      {platform.get('description', '')}")
    print()


def print_menu():
    """Muestra el menú principal."""
    if RICH_AVAILABLE and console:
        print_menu_rich()
    else:
        print_menu_fallback()


def launch_platform(platform_key: str):
    """Lanza el tools.py de la plataforma seleccionada."""
    if platform_key not in PLATFORMS:
        print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return
    
    platform = PLATFORMS[platform_key]
    
    if platform_key == "Q":
        print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
        sys.exit(0)
    
    if platform.get("status") == "coming_soon":
        if RICH_AVAILABLE and console:
            console.print(f"\n[yellow]⚠️ {platform['name']} estará disponible próximamente.[/yellow]")
        else:
            print(f"\n{Colors.WARNING}⚠️ {platform['name']} estará disponible próximamente.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    tools_path = BASE_DIR / platform["path"]
    
    if not tools_path.exists():
        if RICH_AVAILABLE and console:
            console.print(f"\n[red]❌ No se encontró: {tools_path}[/red]")
        else:
            print(f"\n{Colors.FAIL}❌ No se encontró: {tools_path}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    # Mostrar mensaje de transición
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold cyan]🚀 Lanzando {platform['emoji']} {platform['name']}...[/bold cyan]\n")
    else:
        print(f"\n{Colors.CYAN}🚀 Lanzando {platform['emoji']} {platform['name']}...{Colors.ENDC}\n")
    
    # Ejecutar el tools.py de la plataforma
    try:
        subprocess.run([HOST_PYTHON, str(tools_path)], check=False)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Regresando al menú principal...{Colors.ENDC}")
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"\n[red]❌ Error al ejecutar: {e}[/red]")
        else:
            print(f"\n{Colors.FAIL}❌ Error al ejecutar: {e}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")


def show_info():
    """Muestra información sobre el toolbox."""
    if RICH_AVAILABLE and console:
        info_text = Text()
        info_text.append("\n📋 DevSecOps Toolbox\n\n", style="bold cyan")
        info_text.append("Este launcher proporciona acceso unificado a herramientas\n", style="white")
        info_text.append("para múltiples plataformas cloud y DevOps.\n\n", style="white")
        info_text.append("Plataformas soportadas:\n", style="bold white")
        info_text.append("  • GCP: ", style="cyan")
        info_text.append("19+ herramientas SRE\n", style="white")
        info_text.append("  • Azure DevOps: ", style="blue")
        info_text.append("PRs, políticas, releases\n", style="white")
        info_text.append("  • AWS: ", style="yellow")
        info_text.append("Próximamente\n", style="dim")
        
        panel = Panel(info_text, title="ℹ️ Información", border_style="cyan", box=ROUNDED)
        console.print(panel)
    else:
        print(f"\n{Colors.BOLD}📋 DevSecOps Toolbox{Colors.ENDC}")
        print("Este launcher proporciona acceso unificado a herramientas")
        print("para múltiples plataformas cloud y DevOps.")
    
    input("\nPresione Enter para continuar...")


def main():
    """Función principal del menú."""
    while True:
        try:
            print_header()
            print_menu()
            
            # Tip
            if RICH_AVAILABLE and console:
                console.print("[dim]💡 Tip: Escriba 'info' para más información[/dim]\n")
            
            choice = input(f"{Colors.BOLD}Seleccione una opción: {Colors.ENDC}").strip().upper()
            
            if choice == "INFO":
                show_info()
            elif choice in PLATFORMS:
                launch_platform(choice)
            else:
                print(f"\n{Colors.FAIL}Opción no válida. Por favor, intente de nuevo.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Colors.FAIL}Error inesperado: {e}{Colors.ENDC}")
            input("\nPresione Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
        sys.exit(0)
