#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Azure Tools Launcher

Este script proporciona una interfaz de menú para ejecutar las herramientas de Azure
desde un solo lugar.

Características:
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
__version__ = "1.0.0"
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
    "appservice": {"name": "App Service", "emoji": "🌐", "color": "bright_cyan"},
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
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def get_auto_tools() -> List[str]:
    """Obtiene lista de herramientas para ejecutar automáticamente."""
    system_options = TOOLS.get("_system_options", {})
    auto_option = system_options.get("A", {})
    exclude = auto_option.get("exclude", [])
    
    auto_tools = []
    for tool_id, tool_info in TOOLS.items():
        if tool_id.startswith("_"):
            continue
        if tool_id in exclude:
            continue
        if tool_info.get("status") == "ready":
            auto_tools.append(tool_id)
    
    return auto_tools

def build_system_options() -> Dict[str, Dict]:
    """Construye opciones del sistema."""
    return TOOLS.get("_system_options", {})

def clear_screen():
    """Limpia la pantalla."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def print_header():
    """Imprime el encabezado."""
    clear_screen()
    if RICH_AVAILABLE and console:
        title = Text()
        title.append("Azure Tools", style="bold cyan")
        panel = Panel(
            title,
            border_style="cyan",
            padding=(1, 2),
            expand=False,
        )
        console.print(panel)
    else:
        print(f"{Colors.BOLD}═══════════════════════════════════════{Colors.ENDC}")
        print(f"{Colors.CYAN}Azure Tools Launcher{Colors.ENDC}")
        print(f"{Colors.BOLD}═══════════════════════════════════════{Colors.ENDC}\n")

def print_menu():
    """Imprime el menú de herramientas."""
    if RICH_AVAILABLE and console:
        table = Table(
            title="Herramientas Disponibles",
            box=ROUNDED,
            header_style="bold cyan",
        )
        table.add_column("#", style="bold white", width=4)
        table.add_column("Nombre", style="cyan", width=30)
        table.add_column("Descripción", style="dim", width=50)
        table.add_column("Estado", justify="center", width=12)
        
        for tool_id, tool_info in sorted(TOOLS.items()):
            if tool_id.startswith("_"):
                continue
            
            status = tool_info.get("status", "ready")
            status_symbol = "✅" if status == "ready" else "🔄" if status == "coming_soon" else "❌"
            
            table.add_row(
                tool_id,
                tool_info.get("name", ""),
                tool_info.get("description", ""),
                f"{status_symbol} {status}"
            )
        
        console.print(table)
    else:
        print(f"{Colors.BOLD}Herramientas Disponibles:{Colors.ENDC}\n")
        for tool_id, tool_info in sorted(TOOLS.items()):
            if tool_id.startswith("_"):
                continue
            status = tool_info.get("status", "ready")
            symbol = "✅" if status == "ready" else "🔄"
            print(f"  [{tool_id}] {symbol} {tool_info.get('name', '')}")
            print(f"      {tool_info.get('description', '')}\n")

def main():
    """Función principal."""
    while True:
        try:
            print_header()
            print_menu()
            
            choice = input(f"{Colors.BOLD}Seleccione una opción (o 'Q' para salir): {Colors.ENDC}").strip().upper()
            
            if choice == "Q":
                print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
                sys.exit(0)
            elif choice == "A":
                print(f"\n{Colors.CYAN}Ejecutando herramientas automáticas...{Colors.ENDC}\n")
                for tool_id in get_auto_tools():
                    print(f"Ejecutando herramienta {tool_id}...")
            elif choice in TOOLS and not choice.startswith("_"):
                tool = TOOLS[choice]
                if tool.get("status") == "coming_soon":
                    print(f"\n{Colors.WARNING}Esta herramienta estará disponible próximamente.{Colors.ENDC}\n")
                    input("Presione Enter para continuar...")
                else:
                    print(f"\n{Colors.CYAN}Ejecutando: {tool.get('name', '')}{Colors.ENDC}\n")
                    # Aquí iría la lógica para ejecutar la herramienta
            else:
                print(f"\n{Colors.FAIL}Opción no válida.{Colors.ENDC}\n")
                input("Presione Enter para continuar...")
        
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}\n")
            input("Presione Enter para continuar...")

if __name__ == "__main__":
    main()
