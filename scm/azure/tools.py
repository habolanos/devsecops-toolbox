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
__version__ = "1.8.33"
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
        "args": ["--subscription", "--cluster", "--resource-group", "--namespace", "-o"],
        "requirements": "monitoring/requirements.txt",
        "group": "monitoring",
        "status": "ready"
    },
    # ══════════ IAM & SECURITY (3-5) ══════════
    "3": {
        "name": "Auditoría de Roles y Permisos",
        "description": "Audita roles y permisos en Azure",
        "path": "rolesypermisos/azure_roles_audit.py",
        "args": ["--subscription", "-o"],
        "requirements": "rolesypermisos/requirements.txt",
        "group": "iam",
        "status": "ready"
    },
    "4": {
        "name": "Service Principals Analyzer",
        "description": "Analiza service principals y credenciales",
        "path": "service-accounts/azure_sp_analyzer.py",
        "args": ["--subscription", "--days", "-o"],
        "requirements": "service-accounts/requirements.txt",
        "group": "iam",
        "status": "ready"
    },
    "5": {
        "name": "Access Control Validator",
        "description": "Valida controles de acceso en Azure",
        "path": "rolesypermisos/azure_access_validator.py",
        "args": ["--subscription", "-o"],
        "requirements": "rolesypermisos/requirements.txt",
        "group": "iam",
        "status": "ready"
    },
    # ══════════ DATABASE (6-8) ══════════
    "6": {
        "name": "Azure SQL Database Monitor",
        "description": "Monitorea bases de datos Azure SQL",
        "path": "azure-sql/azure_sql_monitor.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "azure-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    "7": {
        "name": "Cosmos DB Analyzer",
        "description": "Analiza bases de datos Cosmos DB",
        "path": "azure-sql/cosmos_db_analyzer.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "azure-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    "8": {
        "name": "Database Backup Validator",
        "description": "Valida backups de bases de datos",
        "path": "azure-sql/azure_backup_validator.py",
        "args": ["--subscription", "-o"],
        "requirements": "azure-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    # ══════════ NETWORKING (9-12) ══════════
    "9": {
        "name": "Virtual Network Analyzer",
        "description": "Analiza redes virtuales en Azure",
        "path": "connectivity/vnet_analyzer.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "10": {
        "name": "Network Security Groups Audit",
        "description": "Audita Network Security Groups",
        "path": "connectivity/nsg_audit.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "11": {
        "name": "Application Gateway Monitor",
        "description": "Monitorea Application Gateways",
        "path": "connectivity/appgateway_monitor.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "12": {
        "name": "Connectivity Checker",
        "description": "Verifica conectividad entre recursos",
        "path": "connectivity/connectivity_checker.py",
        "args": ["--subscription", "--cluster", "--resource-group", "--deployment", "--namespace", "--host", "--port", "--skip-pod-test", "-o"],
        "required_args": ["--cluster", "--resource-group", "--host"],
        "requirements": "connectivity/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    # ══════════ KUBERNETES (13-18) ══════════
    "13": {
        "name": "AKS Cluster Monitor",
        "description": "Monitorea clusters AKS",
        "path": "cluster-aks/aks_monitor.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "14": {
        "name": "AKS Node Pool Analyzer",
        "description": "Analiza node pools en AKS",
        "path": "cluster-aks/aks_nodepool_analyzer.py",
        "args": ["--subscription", "--cluster", "--resource-group", "-o"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "15": {
        "name": "Workload Identity Validator",
        "description": "Valida Workload Identity en AKS",
        "path": "cluster-aks/workload_identity_validator.py",
        "args": ["--subscription", "--cluster", "--resource-group", "-o"],
        "required_args": ["--cluster", "--resource-group"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "16": {
        "name": "Pod Security Policy Audit",
        "description": "Audita políticas de seguridad de pods",
        "path": "cluster-aks/pod_security_audit.py",
        "args": ["--subscription", "--cluster", "--resource-group", "--namespace", "-o"],
        "required_args": ["--cluster", "--resource-group"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "17": {
        "name": "AKS Deployment Validator",
        "description": "Valida despliegues en AKS",
        "path": "cluster-aks/aks_deployment_validator.py",
        "args": ["--subscription", "--cluster", "--resource-group", "--deployment", "--namespace", "--validate", "-o"],
        "required_args": ["--cluster", "--resource-group", "--deployment"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    "18": {
        "name": "Azure Container Registry Analyzer",
        "description": "Analiza Azure Container Registry (ACR)",
        "path": "cluster-aks/acr_analyzer.py",
        "args": ["--subscription", "-o"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    # ══════════ APP SERVICE (19-21) ══════════
    "19": {
        "name": "App Service Monitor",
        "description": "Monitorea App Services",
        "path": "app-service/appservice_monitor.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    "20": {
        "name": "App Service Security Auditor",
        "description": "Audita seguridad de App Services",
        "path": "app-service/appservice_security.py",
        "args": ["--subscription", "--resource-group", "--severity", "-o"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    "21": {
        "name": "App Service Deployment Validator",
        "description": "Valida despliegues en App Service",
        "path": "app-service/appservice_validator.py",
        "args": ["--subscription", "--resource-group", "--app-name", "-o"],
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
        "args": ["--subscription", "--component-name", "--hours", "--start-time", "--end-time", "--output-format"],
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
    # ══════════ CONTAINER APPS (26) ══════════
    "26": {
        "name": "Azure Container Apps Metrics Monitor",
        "description": "Monitorea métricas de Azure Container Apps: requests, latencia p95, CPU%, memoria% y errores",
        "path": "container-apps/azure_container_apps_metrics_monitor.py",
        "args": ["--subscription", "--resource-group", "-o"],
        "requirements": "monitoring/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    # ══════════ SECURITY (27) ══════════
    "27": {
        "name": "Azure Front Door / WAF Checker",
        "description": "Audita Web Application Firewall (WAF), políticas, reglas y cobertura de backends en Azure Front Door",
        "path": "security/azure_waf_checker.py",
        "args": ["--subscription", "--view", "--severity", "-o"],
        "requirements": "security/requirements.txt",
        "group": "security",
        "status": "ready"
    },
    # ══════════ ARTIFACTS (28) ══════════
    "28": {
        "name": "ACR Image Filter",
        "description": "Filtra y exporta imágenes de Azure Container Registry a Excel",
        "path": "artifacts/azure_acr_image_filter.py",
        "args": ["--subscription", "--registry", "--filter", "--csv-file", "-o"],
        "requirements": "artifacts/requirements.txt",
        "group": "artifacts",
        "status": "ready"
    },
    # ══════════ MONITORING (29-30) ══════════
    "29": {
        "name": "AKS Node Resources Monitor",
        "description": "Uso de CPU y memoria por nodo en clusters AKS (HTML report)",
        "path": "monitoring/aks_monitor_node.py",
        "args": ["--subscription", "--cluster", "--resource-group", "--output"],
        "required_args": ["--cluster", "--resource-group"],
        "requirements": "monitoring/requirements.txt",
        "group": "monitoring",
        "status": "ready",
        "auto_run": {"output_format": "html"}
    },
    "30": {
        "name": "AKS Pod Resources Monitor",
        "description": "Uso de CPU y memoria por pod en clusters AKS con selección interactiva",
        "path": "monitoring/aks_monitor_pod.py",
        "args": ["--subscription", "--cluster", "--resource-group", "--namespace", "--sort", "--top"],
        "required_args": ["--cluster", "--resource-group"],
        "requirements": "monitoring/requirements.txt",
        "group": "monitoring",
        "status": "ready",
        "auto_run": {"skip_output": True}
    },
    # ══════════ APP SERVICE (31-33) ══════════
    "31": {
        "name": "App Service Health Analyzer",
        "description": "Análisis profundo de salud y rendimiento de App Services",
        "path": "app-service/appservice_health_analyzer.py",
        "args": ["--subscription", "--resource-group", "--app-name", "--output", "--debug", "--timezone"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    "32": {
        "name": "App Service Cost Analyzer",
        "description": "Análisis de costos y optimización de recursos en App Services",
        "path": "app-service/appservice_cost_analyzer.py",
        "args": ["--subscription", "--resource-group", "--compare", "--period", "--output", "--debug", "--timezone"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    "33": {
        "name": "App Service Traffic Analyzer",
        "description": "Análisis de tráfico y distribución entre App Services",
        "path": "app-service/appservice_traffic_analyzer.py",
        "args": ["--subscription", "--resource-group", "--app-name", "--period", "--output", "--debug"],
        "requirements": "app-service/requirements.txt",
        "group": "appservice",
        "status": "ready"
    },
    # ══════════ CONSOLIDATION (34-35) ══════════
    "34": {
        "name": "Azure Functions Analyzer",
        "description": "Análisis profundo de Azure Functions (seguridad, costos, triggers, performance)",
        "path": "consolidation/azure_functions_analyzer.py",
        "args": ["--subscription", "--view", "--output", "--debug", "--timezone"],
        "requirements": "consolidation/requirements.txt",
        "group": "consolidation",
        "status": "ready"
    },
    "35": {
        "name": "Azure Infrastructure Consolidator",
        "description": "Consolida Application Gateways, App Services y Azure Functions con mapeo de relaciones",
        "path": "consolidation/azure_infrastructure_consolidator.py",
        "args": ["--subscription", "--view", "--output", "--debug", "--timezone"],
        "requirements": "consolidation/requirements.txt",
        "group": "consolidation",
        "status": "ready"
    },
    # ══════════ IAM (36) ══════════
    "36": {
        "name": "Service Principals Multi-Subscription Reporter",
        "description": "Extrae, analiza y reporta service principals de múltiples suscripciones Azure con análisis de roles, permisos temporales y días restantes",
        "path": "service-accounts/azure_sp_multi_subscription_reporter.py",
        "args": ["--subs", "-o"],
        "requirements": "service-accounts/requirements.txt",
        "group": "iam",
        "status": "ready",
        "additional_args": ["--config", "scm/config.json"]
    },
    # ══════════ KUBERNETES (37) ══════════
    "37": {
        "name": "AKS Deployments Off Analyzer",
        "description": "Analiza deployments no running en AKS con diagnóstico automático de causa raíz y recomendaciones",
        "path": "cluster-aks/aks_deployments_off_analyzer.py",
        "args": ["--subscription", "--cluster", "--resource-group", "--namespace", "-o"],
        "required_args": ["--cluster", "--resource-group"],
        "requirements": "cluster-aks/requirements.txt",
        "group": "kubernetes",
        "status": "ready"
    },
    # ══════════ MONITORING (38) ══════════
    "38": {
        "name": "Service Bus Monitor - Multi-Suscripción",
        "description": "Monitoreo profesional de Azure Service Bus con soporte multi-suscripción, alertas preventivas y dashboards ejecutivos",
        "path": "servicebus/azure_service_bus_monitor.py",
        "args": ["-o"],
        "requirements": "servicebus/requirements.txt",
        "group": "monitoring",
        "status": "ready",
        "additional_args": ["--config", "scm/config.json"]
    },
    # ══════════ SECRETS & CONFIGMAPS (39) ══════════
    "39": {
        "name": "Key Vault Secrets Checker",
        "description": "Audita Azure Key Vaults: RBAC, soft-delete, purge protection, secretos expirados o próximos a vencer",
        "path": "secrets-configmaps/azure_keyvault_checker.py",
        "args": ["--subscription", "--vault", "--secrets", "-o"],
        "requirements": "secrets-configmaps/requirements.txt",
        "group": "security",
        "status": "ready"
    },
    # ══════════ SYSTEM (A, Q) ══════════
    "_system_options": {
        "A": {
            "name": "Ejecutar Todos (Checkers)",
            "description": "Ejecuta todos los checkers con suscripción default y output JSON",
            "type": "auto_run",
            "exclude": ["12", "15", "16", "17", "27", "28", "29", "30", "37", "38"],
            "reason": "Excluye: herramientas que requieren cluster/host/config interactivo (12,15,16,17,29,30,37), WAF (27), ACR Image Filter (28), Service Bus (38)"
        },
        "Q": {
            "name": "Salir",
            "description": "Salir del menú",
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

# ═══════════════════════════════════════════════════════════════════════════════
# ENTORNO VIRTUAL Y DEPENDENCIAS
# ═══════════════════════════════════════════════════════════════════════════════

def get_venv_python() -> Optional[str]:
    """Devuelve el python del venv (lo crea si no existe)."""
    if platform.system() == "Windows":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

    if venv_python.exists():
        try:
            result = subprocess.run(
                [str(venv_python), "--version"],
                capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return str(venv_python)
        except (subprocess.SubprocessError, OSError):
            pass
        import shutil
        shutil.rmtree(str(VENV_DIR), ignore_errors=True)
        if INSTALLED_MARKER.exists():
            try:
                INSTALLED_MARKER.unlink()
            except Exception:
                pass

    print(f"{Colors.CYAN}Creando entorno virtual en {VENV_DIR}...{Colors.ENDC}")
    try:
        subprocess.check_call([HOST_PYTHON, "-m", "venv", str(VENV_DIR)])
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al crear el entorno virtual: {e}{Colors.ENDC}")
        return None
    if not venv_python.exists():
        print(f"{Colors.FAIL}No se encontró Python en el venv: {venv_python}{Colors.ENDC}")
        return None
    return str(venv_python)


def get_installed_requirements() -> set:
    if not INSTALLED_MARKER.exists():
        return set()
    try:
        with open(INSTALLED_MARKER, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()


def mark_requirements_installed(requirements_path: str):
    installed = get_installed_requirements()
    installed.add(requirements_path)
    try:
        INSTALLED_MARKER.parent.mkdir(parents=True, exist_ok=True)
        with open(INSTALLED_MARKER, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(installed)))
    except Exception:
        pass


def install_requirements(requirements_path: str, python_exec: str,
                         force: bool = False) -> bool:
    """Instala requirements de la herramienta en el venv."""
    req_file = BASE_DIR / requirements_path
    if not req_file.exists():
        # Muchos tools nuevos solo usan az CLI — sin requirements propios
        return True
    if not force and requirements_path in get_installed_requirements():
        return True
    print(f"\n{Colors.CYAN}Instalando dependencias de {req_file}...{Colors.ENDC}")
    try:
        subprocess.check_call(
            [python_exec, "-m", "pip", "install", "-r", str(req_file)])
        mark_requirements_installed(requirements_path)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al instalar dependencias: {e}{Colors.ENDC}")
        return False


_PLATFORM = "Azure"

def log_command(cmd: List[str], status: str = "EXEC") -> None:
    """Registra el comando en outcome/commands_<fecha>.log si DEVSECOPS_LOG_COMMANDS=1."""
    if os.environ.get("DEVSECOPS_LOG_COMMANDS") != "1":
        return
    output_dir_env = os.environ.get("DEVSECOPS_OUTPUT_DIR")
    log_dir = Path(output_dir_env) if output_dir_env else BASE_DIR / "outcome"
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"commands_{today}.log"
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cmd_str = " ".join(str(c) for c in cmd)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{_PLATFORM}] [{status}] {cmd_str}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# RESOLUCIÓN DE SUSCRIPCIÓN Y PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

_cached_subscription: Optional[str] = None

def resolve_default_subscription() -> str:
    """Default de suscripción: config.json > `az account show` > placeholder."""
    global _cached_subscription
    if _cached_subscription is not None:
        return _cached_subscription
    sub = ""
    cfg_path = BASE_DIR.parent / "config.json"
    try:
        import json
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        sub = (cfg.get("azure") or {}).get("subscription_id", "")
        if sub and "<" in sub:
            sub = ""
    except Exception:
        pass
    if not sub:
        try:
            result = subprocess.run(
                ["az", "account", "show", "--query", "id", "-o", "tsv"],
                capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                sub = result.stdout.strip()
        except Exception:
            pass
    _cached_subscription = sub or DEFAULT_SUBSCRIPTION_ID
    return _cached_subscription


def _normalize_additional_args(additional: List[str]) -> List[str]:
    """Resuelve paths relativos en additional_args contra el root del repo."""
    out = []
    for i, a in enumerate(additional):
        prev = additional[i - 1] if i else ""
        if prev == "--config" and not Path(a).is_absolute():
            candidate = BASE_DIR.parent / a.replace("scm/", "", 1)
            if candidate.exists():
                out.append(str(candidate))
                continue
            root_candidate = BASE_DIR.parent.parent / a
            if root_candidate.exists():
                out.append(str(root_candidate))
                continue
        out.append(a)
    return out


# Flags booleanos (store_true): se preguntan como s/n y se pasan sin valor
_FLAG_ARGS = {"--debug", "--secrets", "--skip-pod-test", "--compare"}

# Args que se preguntan como formato de exportación
_OUTPUT_ARGS = ("-o", "--output", "--output-format")

# (flag, texto del prompt, valor por defecto o None)
_ARG_PROMPTS = {
    "--subscription": ("Suscripción Azure", None),  # default dinámico
    "--resource-group": ("Resource Group (vacío = todos)", ""),
    "--cluster": ("Cluster AKS", ""),
    "--namespace": ("Namespace Kubernetes (vacío = todos)", ""),
    "--deployment": ("Deployment", ""),
    "--validate": ("Validación (all/configmaps/secrets/connectivity)", "all"),
    "--host": ("Host destino a probar", ""),
    "--port": ("Puerto destino", "443"),
    "--app-name": ("Nombre del App Service (vacío = todos)", ""),
    "--vault": ("Nombre del Key Vault (vacío = todos)", ""),
    "--registry": ("Nombre del ACR (vacío si usas --csv-file)", ""),
    "--filter": ("Filtro de tags (ej. >=1.2.0 o regex; vacío = todos)", ""),
    "--csv-file": ("Ruta a CSV de entrada (vacío = consultar ACR)", ""),
    "--component-name": ("Nombre del componente a rastrear (vacío = todos)", ""),
    "--hours": ("Horas hacia atrás", "24"),
    "--start-time": ("Inicio ISO (ej. 2025-01-01T00:00:00Z; vacío = --hours)", ""),
    "--end-time": ("Fin ISO (vacío = ahora)", ""),
    "--view": ("Vista", ""),
    "--severity": ("Severidad mínima (critical/high/medium/low)", ""),
    "--period": ("Período en días", ""),
    "--sort": ("Ordenar por (cpu/memory/name)", "cpu"),
    "--top": ("Top N (0 = todos)", ""),
    "--days": ("Días de antigüedad para credenciales", "90"),
    "--subs": ("Suscripciones CSV o 'ALL' (vacío = config)", ""),
    "--timezone": ("Timezone para reportes", ""),
    "--config": ("Ruta a config.json", "scm/config.json"),
}


def _prompt_value(flag: str, tool: Dict) -> Optional[str]:
    """Pide el valor de un arg; retorna None para no pasarlo."""
    label, default = _ARG_PROMPTS.get(flag, (f"Valor para {flag}", ""))
    if flag == "--subscription":
        default = resolve_default_subscription()
    required = flag in (tool.get("required_args") or [])
    suffix = " (requerido)" if required else (f" [{default}]" if default else "")
    value = input(f"{Colors.BOLD}{label}{suffix}:{Colors.ENDC} ").strip()
    if not value:
        value = default or ""
    if required and not value:
        print(f"{Colors.WARNING}⚠ {flag} es requerido por esta herramienta.{Colors.ENDC}")
        value = input(f"{Colors.BOLD}{label}:{Colors.ENDC} ").strip()
        if not value:
            return None
    return value or None


def _build_tool_args(tool: Dict) -> Optional[List[str]]:
    """Construye los args del script preguntando al usuario.

    Retorna None si el usuario no completó un arg requerido.
    """
    args: List[str] = []
    tool_args = tool.get("args", [])

    for flag in tool_args:
        if flag in _OUTPUT_ARGS:
            continue  # se maneja al final
        if flag in _FLAG_ARGS:
            label = flag.lstrip("-").replace("-", " ")
            ans = input(f"{Colors.BOLD}¿Activar {label}? (s/N):{Colors.ENDC} ").strip().lower()
            if ans in ("s", "si", "y", "yes"):
                args.append(flag)
            continue
        value = _prompt_value(flag, tool)
        if value is None and flag in (tool.get("required_args") or []):
            return None
        if value:
            args.extend([flag, value])

    # Exportación: respeta el nombre de flag registrado (-o/--output/--output-format)
    out_flag = next((f for f in _OUTPUT_ARGS if f in tool_args), None)
    if out_flag:
        fmt = input(f"{Colors.BOLD}¿Exportar resultado? (json/csv/html/excel; vacío = no):{Colors.ENDC} ").strip().lower()
        if fmt:
            args.extend([out_flag, fmt])

    args.extend(_normalize_additional_args(tool.get("additional_args", [])))
    return args


def _build_auto_args(tool: Dict, subscription: str) -> List[str]:
    """Args no interactivos para run-all: subscription + output json/auto_run."""
    args: List[str] = []
    tool_args = tool.get("args", [])
    if "--subscription" in tool_args:
        args.extend(["--subscription", subscription])
    auto = tool.get("auto_run") or {}
    if not auto.get("skip_output"):
        fmt = auto.get("output_format", "json")
        out_flag = next((f for f in _OUTPUT_ARGS if f in tool_args), None)
        if out_flag:
            args.extend([out_flag, fmt])
    args.extend(_normalize_additional_args(tool.get("additional_args", [])))
    return args


# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN DE HERRAMIENTAS
# ═══════════════════════════════════════════════════════════════════════════════

def run_tool(tool_key: str):
    """Ejecuta la herramienta seleccionada con prompts interactivos."""
    if tool_key not in TOOLS:
        print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return
    tool = TOOLS[tool_key]
    if tool_key == "Q":
        print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
        sys.exit(0)

    print(f"\n{Colors.HEADER}=== {tool['name']} ==={Colors.ENDC}")
    print(f"{tool['description']}\n")

    venv_python = get_venv_python()
    if not venv_python:
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    if tool.get("requirements"):
        if not install_requirements(tool["requirements"], venv_python):
            input("\nPresione Enter para continuar...")
            return

    script_path = BASE_DIR / tool["path"]
    if not script_path.exists():
        print(f"{Colors.FAIL}Error: No se encontró el script {script_path}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    if str(script_path).endswith('.sh') and platform.system() == "Windows":
        print(f"{Colors.WARNING}'{tool['name']}' es un script .sh — requiere Linux/WSL/Git Bash.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    tool_args = _build_tool_args(tool)
    if tool_args is None:
        print(f"{Colors.WARNING}Ejecución cancelada.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    cmd = (["sh", str(script_path)] if str(script_path).endswith('.sh')
           else [venv_python, str(script_path)]) + tool_args

    print(f"\n{Colors.CYAN}Ejecutando (en venv):{Colors.ENDC} {' '.join(cmd)}\n")
    log_command(cmd)
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        log_command(cmd, "ERROR")
        print(f"{Colors.FAIL}Error al ejecutar la herramienta: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida por el usuario.{Colors.ENDC}")
    input("\nPresione Enter para continuar...")


def print_execution_summary_rich(results: list, elapsed: float):
    """Resumen de ejecución con Rich."""
    ok_count = sum(1 for r in results if r[1] == "OK")
    error_count = sum(1 for r in results if r[1] == "ERROR")
    table = Table(
        title="📊 Resumen de Ejecución", title_style="bold white",
        box=ROUNDED, header_style="bold cyan",
        border_style="green" if error_count == 0 else "yellow")
    table.add_column("Estado", justify="center", width=8)
    table.add_column("Herramienta", justify="left", style="white")
    table.add_column("Mensaje", justify="left", style="dim")
    for name, status, msg in results:
        if status == "OK":
            table.add_row("✅", f"[green]{name}[/green]", msg)
        else:
            table.add_row("❌", f"[red]{name}[/red]", f"[red]{msg}[/red]")
    console.print()
    console.print(table)
    console.print()
    stats = Text()
    stats.append(f"✅ Exitosos: {ok_count}  ", style="bold green")
    stats.append(f"❌ Errores: {error_count}  ", style="bold red")
    stats.append(f"⏱️ Tiempo: {elapsed:.2f}s", style="bold cyan")
    console.print(Panel(stats, title="📈 Estadísticas", box=ROUNDED, border_style="blue"))
    console.print()
    console.print(Panel(
        "💡 Los reportes se generaron en [cyan]outcome/[/cyan].",
        box=ROUNDED, border_style="dim"))


def run_all_checkers():
    """Ejecuta todos los checkers de forma automática (no interactiva)."""
    import time as time_module

    tool_config = TOOLS.get("A")
    if not tool_config:
        print(f"{Colors.FAIL}Configuración de 'Ejecutar Todos' no encontrada.{Colors.ENDC}")
        return
    auto_tools = tool_config.get("auto_tools", [])

    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel(
            Align.center(Text("🚀 EJECUTAR TODOS LOS CHECKERS", style="bold cyan")),
            box=DOUBLE_EDGE, border_style="magenta"))
        console.print()
        checkers_table = Table(box=ROUNDED, border_style="cyan", show_header=False)
        checkers_table.add_column("Info", style="cyan")
        for tk in auto_tools:
            t = TOOLS.get(tk, {})
            group = TOOL_GROUPS.get(t.get("group", "system"), {})
            checkers_table.add_row(f"{group.get('emoji', '🔧')} {t.get('name', 'Unknown')}")
        console.print(checkers_table)
    else:
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f"{'EJECUTAR TODOS LOS CHECKERS':^60}")
        print(f"{'='*60}{Colors.ENDC}\n")
        print(f"{Colors.CYAN}Se ejecutarán {len(auto_tools)} checkers:{Colors.ENDC}")
        for tk in auto_tools:
            print(f"  • {TOOLS.get(tk, {}).get('name', 'Unknown')}")

    print(f"\n{Colors.WARNING}{tool_config.get('reason', '')}{Colors.ENDC}")

    default_sub = resolve_default_subscription()
    print(f"\n{Colors.BOLD}Suscripción Azure [{Colors.CYAN}{default_sub}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
    subscription = input().strip() or default_sub

    print(f"\n{Colors.BOLD}¿Continuar? (s/n) [s]:{Colors.ENDC} ", end="")
    if input().strip().lower() == 'n':
        print(f"{Colors.WARNING}Operación cancelada.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    venv_python = get_venv_python()
    if not venv_python:
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    start_time = time_module.time()
    results = []

    for idx, tk in enumerate(auto_tools, 1):
        tool = TOOLS.get(tk)
        if not tool:
            continue
        if RICH_AVAILABLE and console:
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            console.print(f"\n[bold cyan]🔵 [{idx}/{len(auto_tools)}][/bold cyan] {group.get('emoji', '🔧')} [white]{tool['name']}[/white]")
            console.print(f"[dim]{'─'*50}[/dim]")
        else:
            print(f"\n{Colors.HEADER}[{idx}/{len(auto_tools)}] {tool['name']}{Colors.ENDC}")

        if tool.get("requirements"):
            if not install_requirements(tool["requirements"], venv_python):
                results.append((tool['name'], "ERROR", "Fallo instalación dependencias"))
                continue

        script_path = BASE_DIR / tool["path"]
        if not script_path.exists():
            results.append((tool['name'], "ERROR", f"Script no encontrado: {script_path}"))
            continue

        tool_args = _build_auto_args(tool, subscription)
        cmd = [venv_python, str(script_path)] + tool_args

        log_command(cmd)
        try:
            subprocess.run(cmd, check=True)
            results.append((tool['name'], "OK", "Completado"))
        except subprocess.CalledProcessError as e:
            log_command(cmd, "ERROR")
            results.append((tool['name'], "ERROR", str(e)))
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")
            break

    elapsed = time_module.time() - start_time

    if RICH_AVAILABLE and console:
        print_execution_summary_rich(results, elapsed)
    else:
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f"{'RESUMEN DE EJECUCIÓN':^60}")
        print(f"{'='*60}{Colors.ENDC}")
        for name, status, msg in results:
            icon = "✅" if status == "OK" else "❌"
            print(f"{icon} {name}: {msg}")
        print(f"\n⏱️  Tiempo total: {elapsed:.2f}s")
    input("\nPresione Enter para continuar...")


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
                run_all_checkers()
            elif choice in TOOLS and not choice.startswith("_"):
                run_tool(choice)
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
