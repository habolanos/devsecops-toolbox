#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Azure Tools Launcher

Este script proporciona una interfaz de menú para ejecutar las herramientas de Azure
desde un solo lugar.

Ahora:
- Crea (si no existe) un entorno virtual en BASE_DIR/.venv
- Instala los requirements de cada herramienta dentro de ese venv
- Ejecuta las herramientas usando el Python del venv

Uso:
    python tools.py
"""

import datetime
import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, List

# Rich imports para interfaz moderna
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.style import Style
    from rich.box import ROUNDED, DOUBLE_EDGE, HEAVY
    from rich.align import Align
    from rich.columns import Columns
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from search_module import search_and_select_tools
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False


try:
    from base_launcher import (
        clear_screen, print_header, print_menu,
        get_menu_order, get_auto_tools, build_system_options,
        log_command, run_tool, Colors
    )
    BASE_LAUNCHER_AVAILABLE = True
except ImportError:
    BASE_LAUNCHER_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA DEL PROGRAMA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.9.4"
__author__ = "Harold Adrian"
__description__ = "Launcher unificado de herramientas Azure"

# Consola Rich
console = Console() if RICH_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# GRUPOS DE HERRAMIENTAS
# ═══════════════════════════════════════════════════════════════════════════════
TOOL_GROUPS = {
    "monitoring": {"name": "Monitoreo", "emoji": "📊", "color": "cyan"},
    "iam": {"name": "IAM & Security", "emoji": "🔐", "color": "yellow"},
    "security": {"name": "Security", "emoji": "🛡️", "color": "red"},
    "database": {"name": "Database", "emoji": "💾", "color": "magenta"},
    "network": {"name": "Networking", "emoji": "🌐", "color": "blue"},
    "kubernetes": {"name": "Kubernetes", "emoji": "☸️", "color": "green"},
    "artifacts": {"name": "Artifacts", "emoji": "📦", "color": "red"},
    "inventory": {"name": "Inventory", "emoji": "📋", "color": "bright_white"},
    "reports": {"name": "Reports", "emoji": "📈", "color": "bright_white"},
    "appservice": {"name": "App Service", "emoji": "🚀", "color": "bright_cyan"},
    "consolidation": {"name": "Consolidación", "emoji": "🔗", "color": "bright_magenta"},
    "system": {"name": "Sistema", "emoji": "⚙️", "color": "white"},
}

GROUP_ORDER = list(TOOL_GROUPS.keys())

# Colores para la salida en consola
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Configuración de rutas
BASE_DIR = Path(__file__).parent.absolute()
HOST_PYTHON = sys.executable or "python"
VENV_DIR = BASE_DIR / ".venv"
INSTALLED_MARKER = VENV_DIR / ".installed_requirements"

# Suscripción Azure por defecto
DEFAULT_SUBSCRIPTION_ID = "your-subscription-id"

# Grupo de recursos por defecto
DEFAULT_RESOURCE_GROUP = "your-resource-group"

# Definición de las herramientas disponibles (con grupo asignado)
TOOLS = {
    # ══════════ MONITORING (1-2) ══════════
    "1": {
        "name": "Monitoreo de Recursos Azure",
        "description": "Monitorea recursos Azure (VMs, App Service, SQL, etc.)",
        "path": "monitoring/azure_monitor.py",
        "args": ["--subscription", "--resource-group"],
        "requirements": "monitoring/requirements.txt",
        "group": "monitoring",
        "status": "ready"
    },
    "2": {
        "name": "Reporte de Despliegues AKS",
        "description": "Genera un reporte detallado de los despliegues en AKS",
        "path": "monitoring/aks_deployments_report.py",
        "args": [],
        "requirements": "monitoring/requirements.txt",
        "group": "monitoring",
        "status": "ready"
    },
    # ══════════ IAM & SECURITY (3-5) ══════════
    "3": {
        "name": "Auditoría de Roles y Permisos",
        "description": "Audita roles y permisos en Azure",
        "path": "rolesypermisos/azure_roles_audit.py",
        "args": ["--subscription"],
        "requirements": "rolesypermisos/requirements.txt",
        "group": "iam",
        "status": "ready"
    },
    "4": {
        "name": "Service Principals Analyzer",
        "description": "Analiza service principals y credenciales",
        "path": "service-accounts/azure_sp_analyzer.py",
        "args": ["--subscription"],
        "requirements": "service-accounts/requirements.txt",
        "group": "iam",
        "status": "ready"
    },
    "5": {
        "name": "Access Control Validator",
        "description": "Valida controles de acceso en Azure",
        "path": "rolesypermisos/azure_access_validator.py",
        "args": ["--subscription"],
        "requirements": "rolesypermisos/requirements.txt",
        "group": "iam",
        "status": "ready"
    },
    # ══════════ DATABASE (6-8) ══════════
    "6": {
        "name": "Azure SQL Database Monitor",
        "description": "Monitorea bases de datos Azure SQL",
        "path": "azure-sql/azure_sql_monitor.py",
        "args": ["--subscription", "--resource-group"],
        "requirements": "azure-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    "7": {
        "name": "Cosmos DB Analyzer",
        "description": "Analiza bases de datos Cosmos DB",
        "path": "azure-sql/cosmos_db_analyzer.py",
        "args": ["--subscription"],
        "requirements": "azure-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    "8": {
        "name": "Database Backup Validator",
        "description": "Valida backups de bases de datos",
        "path": "azure-sql/azure_backup_validator.py",
        "args": ["--subscription"],
        "requirements": "azure-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    # ══════════ NETWORKING (9-12) ══════════
    "9": {
        "name": "Virtual Network Analyzer",
        "description": "Analiza redes virtuales en Azure",
        "path": "connectivity/vnet_analyzer.py",
        "args": ["--subscription", "--resource-group"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "10": {
        "name": "Network Security Groups Audit",
        "description": "Audita Network Security Groups",
        "path": "connectivity/nsg_audit.py",
        "args": ["--subscription"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "11": {
        "name": "Application Gateway Monitor",
        "description": "Monitorea Application Gateways",
        "path": "connectivity/appgateway_monitor.py",
        "args": ["--subscription"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "12": {
        "name": "Connectivity Checker",
        "description": "Verifica conectividad entre recursos",
        "path": "connectivity/connectivity_checker.py",
        "args": ["--subscription"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    # ══════════ KUBERNETES (13-18) ══════════
    "13": {
        "name": "AKS Cluster Monitor",
        "description": "Monitorea clusters AKS",
        "path": "cluster-aks/aks_monitor.py",
        "args": ["--subscription", "--resource-group"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "14": {
        "name": "AKS Node Pool Analyzer",
        "description": "Analiza node pools en AKS",
        "path": "cluster-aks/aks_nodepool_analyzer.py",
        "args": ["--subscription"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "15": {
        "name": "Workload Identity Validator",
        "description": "Valida Workload Identity en AKS",
        "path": "cluster-aks/workload_identity_validator.py",
        "args": ["--subscription"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "16": {
        "name": "Pod Security Policy Audit",
        "description": "Audita políticas de seguridad de pods",
        "path": "cluster-aks/pod_security_audit.py",
        "args": ["--subscription"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "17": {
        "name": "AKS Deployment Validator",
        "description": "Valida despliegues en AKS",
        "path": "cluster-aks/aks_deployment_validator.py",
        "args": ["--subscription"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "18": {
        "name": "Azure Container Registry Analyzer",
        "description": "Analiza Azure Container Registry (ACR)",
        "path": "cluster-aks/acr_analyzer.py",
        "args": ["--subscription"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    # ══════════ APP SERVICE (19-21) ══════════
    "19": {
        "name": "App Service Monitor",
        "description": "Monitorea App Services",
        "path": "app-service/appservice_monitor.py",
        "args": ["--subscription", "--resource-group"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    "20": {
        "name": "App Service Security Auditor",
        "description": "Audita seguridad de App Services",
        "path": "app-service/appservice_security.py",
        "args": ["--subscription"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    "21": {
        "name": "App Service Deployment Validator",
        "description": "Valida despliegues en App Service",
        "path": "app-service/appservice_validator.py",
        "args": ["--subscription"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    # ══════════ INVENTORY (22) ══════════
    "22": {
        "name": "Azure Resource Inventory",
        "description": "Genera inventario completo de recursos Azure",
        "path": "inventory/azure_resource_inventory.py",
        "args": ["--subscription", "-o"],
        "requirements": "inventory/requirements.txt",
        "group": "inventory",
        "status": "ready"
    },
    # ══════════ REPORTS (23) ══════════
    "23": {
        "name": "Azure Compliance Report",
        "description": "Genera reporte de cumplimiento normativo",
        "path": "reports-viewer/azure_compliance_report.py",
        "args": ["--subscription", "-o"],
        "requirements": "reports-viewer/requirements.txt",
        "group": "reports",
        "status": "ready"
    },
    # ══════════ EVENT TRACKER (24) ══════════
    "24": {
        "name": "Event Tracker - Rastreo de Eventos",
        "description": "Rastreo de eventos, caídas de servicio e interrupciones en Azure. Busca en Activity Log, Application Insights, Azure Monitor y AKS Events",
        "path": "event-tracker/event_tracker.py",
        "args": ["--component-name", "--subscription", "--start-time", "--end-time", "--output-format"],
        "requirements": "event-tracker/requirements.txt",
        "group": "monitoring",
        "status": "ready"
    },
    # ══════════ CONSOLIDATION (25) ══════════
    "25": {
        "name": "Azure Unified Infrastructure Dashboard",
        "description": "Dashboard ejecutivo unificado con alertas y recomendaciones automáticas",
        "path": "consolidation/azure_unified_dashboard.py",
        "args": ["--subscription", "-o"],
        "requirements": "consolidation/requirements.txt",
        "group": "consolidation",
        "status": "ready"
    },
    # ══════════ SYSTEM (A, Q) ══════════
    "_system_options": {
        "A": {
            "name": "Ejecutar Todos (Checkers)",
            "description": "Ejecuta todos los checkers con suscripción default",
            "type": "auto_run",
            "exclude": [],
            "reason": "Ejecuta herramientas de monitoreo básico"
        },
        "Q": {
            "name": "Salir",
            "description": "Salir del launcher",
            "type": "exit"
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# SEMÁFOROS Y ESTADOS
# ═══════════════════════════════════════════════════════════════════════════════
STATUS_INDICATORS = {
    "ready": ("🟢", "green", "Listo"),
    "warning": ("🟡", "yellow", "Advertencia"),
    "error": ("🔴", "red", "Error"),
    "running": ("🔵", "blue", "Ejecutando"),
    "exit": ("🚪", "white", "Salir"),
}

# Construir opciones de sistema dinámicamente
def _init_system_options():
    """Inicializa las opciones de sistema (A, Q) dinámicamente."""
    build_system_options()

def clear_screen():
    """Limpia la pantalla (usa base_launcher si está disponible)."""
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import clear_screen as _clear_screen
        _clear_screen()
    else:
        import os, platform
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')


def print_header_rich():
    """Imprime el encabezado del menú con Rich (versión moderna)."""
    clear_screen()
    
    # Título principal con panel
    title = Text()
    title.append("☁️  ", style="bold white")
    title.append("SRE Tools for Azure Cloud Platform", style="bold cyan")
    title.append("  ☁️", style="bold white")
    
    subtitle = Text()
    subtitle.append(f"v{__version__}", style="bold green")
    subtitle.append(" | ", style="dim")
    
    header_content = Align.center(title)
    
    panel = Panel(
        Align.center(
            Text.assemble(
                title,
                "\n",
                subtitle,
                Text(__description__, style="dim white")
            )
        ),
        box=DOUBLE_EDGE,
        border_style="cyan",
        padding=(1, 2),
        expand=False,
    )
    console.print(Align.left(panel))
    console.print()

def print_header_fallback():
    """Imprime el encabezado del menú (versión fallback sin Rich)."""
    clear_screen()
    print(f"{Colors.HEADER}{'='*60}")
    print(f"{'AZURE TOOLS':^60}")
    print(f"v{__version__} | by {__author__}".center(60))
    print(f"{'='*60}{Colors.ENDC}\n")

def print_header():
    """Imprime el encabezado del menú."""
    if RICH_AVAILABLE and console:
        print_header_rich()
    else:
        print_header_fallback()

def get_status_indicator(status: str) -> tuple:
    """Obtiene el indicador de estado (emoji, color, texto)."""
    return STATUS_INDICATORS.get(status, ("⚪", "white", "Desconocido"))

def _menu_sort_key(key: str) -> tuple:
    """Ordena claves numéricamente."""
    if key.isdigit():
        return (0, int(key))
    return (1, key)


def get_auto_tools(exclude_list: List[str] = None) -> List[str]:
    """Genera lista de herramientas para auto_run dinámicamente."""
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
        return auto_tools


def build_system_options():
    """Construye las opciones de sistema dinámicamente."""
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
            del TOOLS["_system_options"]


def get_menu_order(include_exit: bool = True) -> List[str]:
    """Retorna las claves del menú ordenadas por grupo y numéricamente dentro de cada grupo."""
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
    if include_exit and "Q" in TOOLS:
        ordered.append("Q")
    return ordered

def print_menu_rich():
    """Muestra el menú principal con Rich (versión moderna con tabla)."""
    # Crear tabla principal
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
    
    # Definir columnas con anchos proporcionales
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Grupo", justify="left", width=18)
    table.add_column("Herramienta", justify="left", style="white")
    table.add_column("Descripción", justify="left", style="dim", min_width=40)
    
    sorted_keys = get_menu_order()

    # Agregar filas
    for key in sorted_keys:
        tool = TOOLS[key]
        group_key = tool.get("group", "system")
        group_info = TOOL_GROUPS.get(group_key, TOOL_GROUPS["system"])
        # Formato del grupo con emoji y color
        group_text = f"{group_info['emoji']} {group_info['name']}"
        
        # Estilo especial para opciones de sistema
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
            f"[{group_info['color']}]{group_text}[/{group_info['color']}]",
            f"[{name_style}]{tool['name']}[/{name_style}]",
            tool.get('description', '')
        )
    
    console.print(table)
    console.print()

def print_menu_fallback():
    """Muestra el menú principal (versión fallback sin Rich)."""
    print(f"{Colors.BOLD}Menú Principal:{Colors.ENDC}\n")
    for key in get_menu_order():
        tool = TOOLS[key]
        group_key = tool.get("group", "system")
        group_info = TOOL_GROUPS.get(group_key, {"emoji": "⚙️", "name": "Sistema"})
        status_emoji = get_status_indicator(tool.get("status", "ready"))[0]
        
        if key == "Q":
            print(f"  {Colors.WARNING}[{key}]{Colors.ENDC} {status_emoji} {tool['name']}")
        else:
            print(f"  {Colors.BLUE}[{key}]{Colors.ENDC} {status_emoji} [{group_info['name']}] {tool['name']} - {tool['description']}")
    print()

def print_menu():
    """Muestra el menú principal."""
    if RICH_AVAILABLE and console:
        print_menu_rich()
    else:
        print_menu_fallback()

def main():
    """Función principal del menú."""
    while True:
        try:
            print_header()
            print_menu()
            
            choice = input(f"\n{Colors.BOLD}Seleccione una opción (o '/' para buscar): {Colors.ENDC}").strip().upper()
            
            # Opción de búsqueda
            if choice == "/":
                if SEARCH_AVAILABLE:
                    choice = search_and_select_tools(TOOLS, TOOL_GROUPS)
                    if choice is None:
                        continue
                else:
                    print(f"\n{Colors.YELLOW}Búsqueda no disponible{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
            
            if choice == "Q":
                print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
                sys.exit(0)
            elif choice == "A":
                print(f"\n{Colors.CYAN}Ejecutando herramientas automáticas...{Colors.ENDC}\n")
                for tool_id in get_auto_tools():
                    print(f"Ejecutando herramienta {tool_id}...")
            elif choice in TOOLS and not choice.startswith("_"):
                tool = TOOLS[choice]
                print(f"\n{Colors.CYAN}Ejecutando: {tool.get('name', '')}{Colors.ENDC}\n")
                print(f"{tool.get('description', '')}\n")
            else:
                print(f"\n{Colors.FAIL}Opción no válida. Por favor, intente de nuevo.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Colors.FAIL}Error inesperado: {e}{Colors.ENDC}")
            input("\nPresione Enter para continuar...")

# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
# Inicializar opciones de sistema después de que todas las funciones estén definidas
_init_system_options()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
