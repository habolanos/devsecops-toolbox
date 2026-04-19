#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GCP Tools Launcher

Este script proporciona una interfaz de menú para ejecutar las herramientas de GCP
desde un solo lugar.

Ahora:
- Crea (si no existe) un entorno virtual en BASE_DIR/.venv
- Instala los requirements de cada herramienta dentro de ese venv
- Ejecuta las herramientas usando el Python del venv

Uso:
    python gcp_tools_launcher.py
"""

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

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA DEL PROGRAMA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.9.0"
__author__ = "Harold Adrian"
__description__ = "Launcher unificado de herramientas GCP"

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
# Python con el que se ejecuta el launcher (host)
HOST_PYTHON = sys.executable or "python"
# Directorio del venv (único para todas las herramientas)
VENV_DIR = BASE_DIR / ".venv"
# Archivo marker para tracking de dependencias instaladas
INSTALLED_MARKER = VENV_DIR / ".installed_requirements"

# Proyecto GCP por defecto
DEFAULT_PROJECT_ID = "cpl-corp-cial-prod-17042024"

# Cluster por defecto
DEFAULT_CLUSTER_ID = "gke-corp-cial-prod-01"

# Deployment por defecto para checkers de conectividad
DEFAULT_DEPLOYMENT = "ds-ppm-pricing-discount"

# Definición de las herramientas disponibles (con grupo asignado)
# Ordenadas por grupo: monitoring(1-2), iam(3-5), security(6,23), database(7-9), network(10-13), kubernetes(14-19), artifacts(20), inventory(22), reports(21)
TOOLS = {
    # ══════════ MONITORING (1-2) ══════════
    "1": {
        "name": "Monitoreo de Recursos GCP",
        "description": "Monitorea recursos GCP (CPU, memoria, SQL, etc.)",
        "path": "monitoring/gcp_monitor.py",
        "args": ["--project"],
        "requirements": "monitoring/requirements.txt",
        "group": "monitoring",
        "status": "ready"
    },
    "2": {
        "name": "Reporte de Despliegues GKE",
        "description": "Genera un reporte detallado de los despliegues en GKE",
        "path": "monitoring/gke_deployments_report.py",
        "args": [],
        "requirements": "monitoring/requirements.txt",
        "group": "monitoring",
        "status": "ready"
    },
    # ══════════ IAM & SECURITY (3-5) ══════════
    "3": {
        "name": "Reporte de Roles y Permisos IAM",
        "description": "Genera un reporte detallado de roles y permisos IAM",
        "path": "rolesypermisos/gcp_iam_roles_report.py",
        "args": ["--project"],
        "requirements": "rolesypermisos/requirements.txt",
        "group": "iam",
        "status": "ready"
    },
    "4": {
        "name": "Service Account Checker",
        "description": "Lista y analiza Service Accounts, keys y roles IAM",
        "path": "service-account/gcp_service_account_checker.py",
        "args": ["--project", "-o"],
        "requirements": None,
        "group": "iam",
        "status": "ready"
    },
    "5": {
        "name": "Certificate Manager Checker",
        "description": "Monitorea certificados SSL/TLS en Certificate Manager",
        "path": "certificate-manager/gcp_certificate_checker.py",
        "args": ["--project", "--output"],
        "requirements": None,
        "group": "iam",
        "status": "ready"
    },
    # ══════════ SECURITY (6) ══════════
    "6": {
        "name": "Cloud Armor Checker",
        "description": "Audita Security Policies (WAF/DDoS), cobertura de backends y gaps de seguridad",
        "path": "cloud-armor/gcp_cloud_armor_checker.py",
        "args": ["--project", "--view", "--audit", "--severity", "--compare", "--output"],
        "requirements": "cloud-armor/requirements.txt",
        "group": "security",
        "status": "ready"
    },
    # ══════════ DATABASE (7-9) ══════════
    "7": {
        "name": "Cloud SQL Disk Monitor",
        "description": "Monitorea uso de disco en instancias Cloud SQL",
        "path": "cloud-sql/gcp_disk_checker.py",
        "args": ["--project", "-o"],
        "requirements": "cloud-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    "8": {
        "name": "Cloud SQL Database Checker",
        "description": "Lista bases de datos por instancia de Cloud SQL",
        "path": "cloud-sql/gcp_database_checker.py",
        "args": ["--project", "-o"],
        "requirements": "cloud-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    "9": {
        "name": "Cloud SQL Comparator",
        "description": "Compara instancias Cloud SQL (edición, tipo, puertos, IPs) entre dos proyectos GCP",
        "path": "cloud-sql/gcp_sql_comparator.py",
        "args": ["--project1", "--project2", "--instance", "--output", "--all"],
        "requirements": "cloud-sql/requirements.txt",
        "group": "database",
        "status": "ready"
    },
    # ══════════ NETWORKING (10-13) ══════════
    "10": {
        "name": "VPC Networks Checker",
        "description": "Visualiza VPC, subnets, IPs, CIDR, firewall y rutas",
        "path": "vpc-networks/gcp_vpc_networks_checker.py",
        "args": ["--project", "-o"],
        "requirements": "vpc-networks/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "11": {
        "name": "Gateway Services Checker",
        "description": "Monitorea Gateways, Routes, Services y Policies en GKE",
        "path": "gateway-services/gcp_gateway_checker.py",
        "args": ["--project", "--cluster", "--namespace", "--view", "-o"],
        "requirements": "gateway-services/requirements.txt",
        "group": "network",
        "status": "ready"
    },
    "12": {
        "name": "Load Balancer Checker",
        "description": "Analiza Load Balancers, Backend Services, Health Checks y SSL",
        "path": "load-balancer/gcp_load_balancer_checker.py",
        "args": ["--project", "--view", "-o"],
        "requirements": None,
        "group": "network",
        "status": "ready"
    },
    "13": {
        "name": "IP Addresses Checker",
        "description": "Analiza capacidad de red de clusters GKE (IPs de pods y servicios)",
        "path": "vpc-networks/gcp_ip_addresses_checker.py",
        "args": ["--project", "--cluster", "--region", "-o"],
        "requirements": None,
        "group": "network",
        "status": "ready"
    },
    # ══════════ KUBERNETES (14-19) ══════════
    "14": {
        "name": "GKE Cluster Checker",
        "description": "Monitorea clusters GKE, versiones, nodos y pods",
        "path": "cluster-gke/gcp_cluster_checker.py",
        "args": ["--project", "--output"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "15": {
        "name": "Secrets & ConfigMaps Checker",
        "description": "Valida referencias de Secrets y ConfigMaps en GKE",
        "path": "secrets-configmaps/gcp_secrets_configmaps_checker.py",
        "args": ["--project", "--cluster", "--output"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "16": {
        "name": "Pod Connectivity Checker",
        "description": "Valida conectividad desde un Pod GKE hasta Cloud SQL",
        "path": "connectivity/pod_connectivity_checker.py",
        "args": ["--deployment", "--sql-instance"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "17": {
        "name": "Deploy Dependency Checker",
        "description": "Analiza ConfigMaps de un deployment y valida conexiones a bases de datos",
        "path": "connectivity/deploy_dependency_checker.py",
        "args": ["--project", "--cluster", "--region", "--deployment", "--namespace", "--probe-mode", "--probe-image", "--timeout", "-o"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "18": {
        "name": "Cloud Run Checker",
        "description": "Analiza servicios Cloud Run, revisiones, Jobs, IAM y networking",
        "path": "cloud-run/gcp_cloudrun_checker.py",
        "args": ["--project", "--region", "--view", "--compare", "-o"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "19": {
        "name": "Deployment Validator",
        "description": "Valida ConfigMaps, Secrets y conectividad de un Deployment",
        "path": "connectivity/deployment_validator.py",
        "args": ["--project", "--cluster", "--region", "--deployment", "--namespace", "--validate", "--probe-image", "--timeout", "--severity", "-o"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    # ══════════ ARTIFACTS (20) ══════════
    "20": {
        "name": "Artifact Registry Tag Filter",
        "description": "Filtra y exporta imágenes de Artifact Registry a Excel",
        "path": "artifact-registry/tag_filter.py",
        "args": ["--csv-file"],
        "requirements": "artifact-registry/requirements.txt",
        "group": "artifacts",
        "status": "ready"
    },
    # ══════════ CERTIFICATES (23) ══════════
    "23": {
        "name": "Certificate TLS Report",
        "description": "Valida certificados SSL/TLS remotos desde GKE (CN, emisor, expiración, chain, TLS version, cipher)",
        "path": "scripts-console/check-certificate-report.sh",
        "args": ["--host", "--port"],
        "group": "security",
        "status": "ready"
    },
    # ══════════ INVENTORY (22) ══════════
    "22": {
        "name": "Inventario GKE + Cloud SQL",
        "description": "Genera inventario consolidado de recursos GCP (CSV + Excel con gráficos radar)",
        "path": "inventory/run_inventory.py",
        "args": [],
        "requirements": "inventory/requirements.txt",
        "group": "inventory",
        "status": "ready"
    },
    # ══════════ REPORTS (21) ══════════
    "21": {
        "name": "Visualizar Reportes JSON",
        "description": "Genera graficos HTML desde reportes JSON de los checkers",
        "path": "reports-viewer/gcp_reports_viewer.py",
        "args": [],
        "requirements": "reports-viewer/requirements.txt",
        "group": "reports",
        "status": "ready"
    },
    # ══════════ SYSTEM (A, Q) ══════════
    "A": {
        "name": "Ejecutar Todos (Checkers)",
        "description": "Ejecuta todos los checkers con proyecto default y output JSON",
        "auto_tools": ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"],
        "excluded_reason": "Excluye: Pod Connectivity (requiere deployment), Artifact Registry (requiere CSV), Inventario (pipeline propio)",
        "group": "system",
        "status": "ready"
    },
    "Q": {
        "name": "Salir",
        "description": "Salir del menú",
        "group": "system",
        "status": "exit"
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

def clear_screen():
    """Limpia la pantalla de la consola."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def print_header_rich():
    """Imprime el encabezado del menú con Rich (versión moderna)."""
    clear_screen()
    
    # Título principal con panel
    title = Text()
    title.append("☁️  ", style="bold white")
    title.append("SRE Tools for GCP Cloud Platform", style="bold cyan")
    title.append("  ☁️", style="bold white")
    
    subtitle = Text()
    subtitle.append(f"v{__version__}", style="bold green")
    subtitle.append(" | ", style="dim")
    subtitle.append(f"by {__author__}", style="italic yellow")
    
    header_content = Align.center(title)
    
    panel = Panel(
        Align.center(
            Text.assemble(
                title,
                "\n",
                subtitle,
                "\n",
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
    print(f"{'GCP TOOLS':^60}")
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
    # ... (rest of the code remains the same)
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

def get_venv_python() -> Optional[str]:
    """
    Devuelve la ruta al ejecutable de python dentro del venv.
    Si no existe el venv, lo crea usando el HOST_PYTHON.
    

    Retorna:
        str con la ruta al python del venv, o None si falla.
    """
    # Determinar ruta del python dentro del venv dependiendo de la plataforma
    if platform.system() == "Windows":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

    # Si ya existe el ejecutable del venv, verificar que funcione
    # (un venv creado en Linux/WSL no funciona en Windows nativo y viceversa)
    if venv_python.exists():
        try:
            result = subprocess.run(
                [str(venv_python), "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return str(venv_python)
            else:
                print(f"{Colors.WARNING}Venv existente no es funcional, recreando...{Colors.ENDC}")
        except (subprocess.SubprocessError, OSError):
            print(f"{Colors.WARNING}Venv existente no es funcional (creado en otra plataforma?), recreando...{Colors.ENDC}")
        # Eliminar venv corrupto/incompatible y su caché de requirements
        try:
            import shutil
            shutil.rmtree(str(VENV_DIR), ignore_errors=True)
        except Exception:
            pass
        # Limpiar marker de requirements instalados (el venv nuevo no tiene paquetes)
        try:
            if INSTALLED_MARKER.exists():
                INSTALLED_MARKER.unlink()
        except Exception:
            pass

    # Si no existe o no funciona, creamos el venv
    print(f"{Colors.CYAN}Creando entorno virtual en {VENV_DIR}...{Colors.ENDC}")
    try:
        subprocess.check_call([HOST_PYTHON, "-m", "venv", str(VENV_DIR)])
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al crear el entorno virtual: {e}{Colors.ENDC}")
        return None

    # Verificar que el ejecutable se haya creado
    if not venv_python.exists():
        print(f"{Colors.FAIL}No se encontró el ejecutable de Python en el venv: {venv_python}{Colors.ENDC}")
        return None

    print(f"{Colors.GREEN}Entorno virtual creado correctamente.{Colors.ENDC}")
    return str(venv_python)

def get_installed_requirements() -> set:
    """Obtiene el conjunto de requirements ya instalados desde el archivo marker."""
    if not INSTALLED_MARKER.exists():
        return set()
    try:
        with open(INSTALLED_MARKER, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()

def mark_requirements_installed(requirements_path: str):
    """Marca un archivo de requirements como instalado."""
    installed = get_installed_requirements()
    installed.add(requirements_path)
    try:
        INSTALLED_MARKER.parent.mkdir(parents=True, exist_ok=True)
        with open(INSTALLED_MARKER, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(installed)))
    except Exception:
        pass  # No es crítico si falla el marker

def verify_package_installed(python_exec: str, package_name: str) -> bool:
    """Verifica si un paquete está instalado en el venv."""
    try:
        result = subprocess.run(
            [python_exec, "-c", f"import {package_name}"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def install_requirements(requirements_path: str, python_exec: str, force: bool = False) -> bool:
    """Instala las dependencias necesarias usando el python del venv.
    
    Args:
        requirements_path: Ruta relativa al archivo requirements.txt
        python_exec: Ruta al ejecutable de Python del venv
        force: Si es True, reinstala aunque ya estén marcadas como instaladas
    """
    req_file = BASE_DIR / requirements_path
    if not req_file.exists():
        print(f"{Colors.WARNING}Advertencia: No se encontró {req_file}{Colors.ENDC}")
        return True
    
    # Verificar si ya están instaladas (usar caché)
    if not force and requirements_path in get_installed_requirements():
        # Verificar que los paquetes clave realmente estén instalados
        needs_reinstall = False
        if "reports-viewer" in requirements_path:
            if not verify_package_installed(python_exec, "plotly"):
                print(f"{Colors.WARNING}Plotly no encontrado, reinstalando...{Colors.ENDC}")
                needs_reinstall = True
        if "inventory" in requirements_path:
            if not verify_package_installed(python_exec, "rich"):
                print(f"{Colors.WARNING}Rich no encontrado, reinstalando...{Colors.ENDC}")
                needs_reinstall = True
        if not needs_reinstall:
            print(f"{Colors.GREEN}Dependencias de {requirements_path} ya instaladas (usando caché).{Colors.ENDC}")
            return True
        force = True
        
    print(f"\n{Colors.CYAN}Instalando dependencias de {req_file} en el venv...{Colors.ENDC}")
    try:
        # Mostrar salida para debug
        subprocess.check_call([python_exec, "-m", "pip", "install", "-r", str(req_file)])
        print(f"{Colors.GREEN}Dependencias instaladas correctamente.{Colors.ENDC}")
        mark_requirements_installed(requirements_path)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al instalar dependencias: {e}{Colors.ENDC}")
        return False

def get_project_id() -> Optional[str]:
    """Solicita al usuario el ID del proyecto GCP con valor por defecto."""
    print(f"\n{Colors.BOLD}Proyecto GCP [{Colors.CYAN}{DEFAULT_PROJECT_ID}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
    project_id = input().strip()
    if not project_id:
        project_id = DEFAULT_PROJECT_ID
        print(f"{Colors.GREEN}Usando proyecto: {project_id}{Colors.ENDC}")
    return project_id

def run_tool(tool_key: str):
    """Ejecuta la herramienta seleccionada."""
    if tool_key not in TOOLS:
        print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return
    
    tool = TOOLS[tool_key]
    
    if tool_key == "Q":  # Salir
        print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
        sys.exit(0)
    
    print(f"\n{Colors.HEADER}=== {tool['name']} ==={Colors.ENDC}")
    print(f"{tool['description']}\n")

    # Asegurarnos de tener el venv listo y obtener el python del venv
    venv_python = get_venv_python()
    if not venv_python:
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual. Abortando herramienta.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    # Instalar dependencias si es necesario (siempre dentro del venv)
    if tool.get("requirements"):
        if not install_requirements(tool["requirements"], venv_python):
            print(f"{Colors.FAIL}No se pudieron instalar las dependencias necesarias.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
    
    # Construir el comando para ejecutar el script usando el python del venv
    script_path = BASE_DIR / tool["path"]
    
    # Validar que el script exista
    if not script_path.exists():
        print(f"{Colors.FAIL}Error: No se encontró el script {script_path}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    # Detectar si es script shell (.sh) o Python
    is_shell_script = str(script_path).endswith('.sh')
    if is_shell_script:
        # Para scripts shell, usar sh directamente (no requiere venv)
        cmd = ["sh", str(script_path)]
    else:
        # Para scripts Python, usar el Python del venv
        cmd = [venv_python, str(script_path)]

    # Añadir argumentos necesarios
    args = []
    tool_args = tool.get("args", [])

    if "--project" in tool_args:
        print(f"\n{Colors.BOLD}Proyecto GCP [{Colors.CYAN}{DEFAULT_PROJECT_ID}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        project = input().strip()
        if not project:
            project = DEFAULT_PROJECT_ID
            print(f"{Colors.GREEN}Usando proyecto: {project}{Colors.ENDC}")
        args.extend(["--project", project])

    if "--cluster" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese el nombre del cluster [{Colors.CYAN}{DEFAULT_CLUSTER_ID}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        cluster = input().strip()
        if not cluster:
            cluster = DEFAULT_CLUSTER_ID
            print(f"{Colors.GREEN}Usando cluster: {cluster}{Colors.ENDC}")
        args.extend(["--cluster", cluster])

    if "--region" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese la región del cluster [us-central1]:{Colors.ENDC} ", end="")
        region = input().strip()
        if not region:
            region = "us-central1"
            print(f"{Colors.GREEN}Usando región: {region}{Colors.ENDC}")
        args.extend(["--region", region])

    if "--project1" in tool_args:
        print(f"\n{Colors.BOLD}Proyecto GCP 1 - referencia [{Colors.CYAN}{DEFAULT_PROJECT_ID}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        project1 = input().strip()
        if not project1:
            project1 = DEFAULT_PROJECT_ID
            print(f"{Colors.GREEN}Usando proyecto 1: {project1}{Colors.ENDC}")
        args.extend(["--project1", project1])

    if "--project2" in tool_args:
        print(f"\n{Colors.BOLD}Proyecto GCP 2 - a comparar:{Colors.ENDC} ", end="")
        project2 = input().strip()
        if not project2:
            print(f"{Colors.FAIL}Se requiere el ID del segundo proyecto GCP.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        args.extend(["--project2", project2])

    if "--deployment" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese el nombre del deployment [{Colors.CYAN}{DEFAULT_DEPLOYMENT}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        deployment = input().strip()
        if not deployment:
            deployment = DEFAULT_DEPLOYMENT
            print(f"{Colors.GREEN}Usando deployment: {deployment}{Colors.ENDC}")
        args.extend(["--deployment", deployment])
    
    if "--sql-instance" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese el nombre de la instancia Cloud SQL:{Colors.ENDC} ", end="")
        sql_instance = input().strip()
        if not sql_instance:
            print(f"{Colors.FAIL}Se requiere el nombre de la instancia SQL.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        args.extend(["--sql-instance", sql_instance])
    
    if "--csv-file" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese la ruta al archivo CSV:{Colors.ENDC} ", end="")
        csv_file = input().strip()
        if not csv_file:
            print(f"{Colors.FAIL}Se requiere la ruta al archivo CSV.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        args.append(csv_file)  # Este script usa argumento posicional
    
    if "--namespace" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese el namespace (vacío para todos):{Colors.ENDC} ", end="")
        namespace = input().strip()
        if namespace:
            args.extend(["--namespace", namespace])

    if "--host" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese el host a validar (ej: api.ejemplo.com):{Colors.ENDC} ", end="")
        host = input().strip()
        if not host:
            print(f"{Colors.FAIL}Se requiere el host para validar el certificado.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        args.append(host)  # Script shell usa argumento posicional para host

    if "--port" in tool_args:
        print(f"\n{Colors.BOLD}Ingrese el puerto [443]:{Colors.ENDC} ", end="")
        port = input().strip()
        if not port:
            port = "443"
            print(f"{Colors.GREEN}Usando puerto: {port}{Colors.ENDC}")
        else:
            print(f"{Colors.GREEN}Usando puerto: {port}{Colors.ENDC}")
        args.append(port)  # Script shell usa argumento posicional para puerto

    if "--probe-mode" in tool_args:
        print(f"\n{Colors.BOLD}Seleccione modo de validación (pod/local) [pod]:{Colors.ENDC} ", end="")
        probe_mode = input().strip().lower()
        if probe_mode not in ["pod", "local"]:
            probe_mode = "pod"
            print(f"{Colors.GREEN}Usando modo: {probe_mode}{Colors.ENDC}")
        args.extend(["--probe-mode", probe_mode])

    if "--probe-image" in tool_args:
        print(f"\n{Colors.BOLD}Imagen del pod temporal [jrecord/nettools:latest]:{Colors.ENDC} ", end="")
        probe_image = input().strip()
        if not probe_image:
            probe_image = "jrecord/nettools:latest"
            print(f"{Colors.GREEN}Usando imagen: {probe_image}{Colors.ENDC}")
        args.extend(["--probe-image", probe_image])

    if "--timeout" in tool_args:
        print(f"\n{Colors.BOLD}Timeout por validación (segundos) [5]:{Colors.ENDC} ", end="")
        timeout_input = input().strip()
        try:
            timeout_val = int(timeout_input) if timeout_input else 5
            if timeout_val <= 0:
                raise ValueError
        except ValueError:
            timeout_val = 5
            print(f"{Colors.GREEN}Usando timeout: {timeout_val}{Colors.ENDC}")
        args.extend(["--timeout", str(timeout_val)])

    if "--view" in tool_args:
        # Determinar opciones de vista según la herramienta
        if "cloud-run" in tool.get("path", ""):
            view_options = "all/services/revisions/security/jobs/networking"
            valid_views = ["all", "services", "revisions", "security", "jobs", "networking"]
        elif "load-balancer" in tool.get("path", ""):
            view_options = "all/forwarding/backends/urlmaps/healthchecks/ssl/security/cdn"
            valid_views = ["all", "forwarding", "backends", "urlmaps", "healthchecks", "ssl", "security", "cdn"]
        elif "cloud-armor" in tool.get("path", ""):
            view_options = "all/policies/rules/backends/gaps"
            valid_views = ["all", "policies", "rules", "backends", "gaps"]
        else:
            view_options = "all/gateways/routes/services/policies"
            valid_views = ["all", "gateways", "routes", "services", "policies"]
        
        print(f"\n{Colors.BOLD}Seleccione vista ({view_options}) [all]:{Colors.ENDC} ", end="")
        view = input().strip().lower()
        if view and view in valid_views:
            args.extend(["--view", view])
    
    if "--audit" in tool_args:
        print(f"\n{Colors.BOLD}¿Ejecutar auditoría completa de seguridad? (s/n) [s]:{Colors.ENDC} ", end="")
        run_audit = input().strip().lower()
        if run_audit != "n":
            args.append("--audit")
    
    if "--severity" in tool_args:
        print(f"\n{Colors.BOLD}Filtrar hallazgos por severidad (all/critical/warning/info) [all]:{Colors.ENDC} ", end="")
        severity = input().strip().lower()
        if severity and severity in ["all", "critical", "warning", "info"]:
            args.extend(["--severity", severity])
    
    if "--compare" in tool_args:
        print(f"\n{Colors.BOLD}Comparar con otro proyecto (vacío para omitir):{Colors.ENDC} ", end="")
        compare_project = input().strip()
        if compare_project:
            args.extend(["--compare", compare_project])

    if "--instance" in tool_args:
        print(f"\n{Colors.BOLD}Filtrar por nombre de instancia (vacío para todas):{Colors.ENDC} ", end="")
        instance_filter = input().strip()
        if instance_filter:
            args.extend(["--instance", instance_filter])

    if "--all" in tool_args:
        print(f"\n{Colors.BOLD}¿Mostrar comparación de todos los atributos? (s/n) [n]:{Colors.ENDC} ", end="")
        show_all = input().strip().lower()
        if show_all == "s":
            args.append("--all")
    
    if "--output" in tool_args or "-o" in tool_args:
        print(f"\n{Colors.BOLD}¿Exportar resultado? (json/csv/ninguno) [json]:{Colors.ENDC} ", end="")
        output_format = input().strip().lower()
        if output_format in ["json", "csv"]:
            args.extend(["-o", output_format])
        elif output_format == "" or output_format == "json":
            args.extend(["-o", "json"])
    
    # Añadir argumentos adicionales si los hay
    if "additional_args" in tool:
        args.extend(tool["additional_args"])
    
    cmd.extend(args)
    
    # Mostrar comando que se va a ejecutar
    print(f"\n{Colors.CYAN}Ejecutando (en venv):{Colors.ENDC} {' '.join(cmd)}\n")
    
    try:
        # Ejecutar el comando dentro del venv
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al ejecutar la herramienta: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida por el usuario.{Colors.ENDC}")
    
    input("\nPresione Enter para continuar...")

def print_execution_summary_rich(results: list, elapsed: float):
    """Muestra el resumen de ejecución con Rich."""
    ok_count = sum(1 for r in results if r[1] == "OK")
    error_count = sum(1 for r in results if r[1] == "ERROR")
    
    # Tabla de resultados
    table = Table(
        title="📊 Resumen de Ejecución",
        title_style="bold white",
        box=ROUNDED,
        header_style="bold cyan",
        border_style="green" if error_count == 0 else "yellow",
    )
    
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
    
    # Panel de estadísticas
    stats = Text()
    stats.append(f"✅ Exitosos: {ok_count}  ", style="bold green")
    stats.append(f"❌ Errores: {error_count}  ", style="bold red")
    stats.append(f"⏱️ Tiempo: {elapsed:.2f}s", style="bold cyan")
    
    console.print(Panel(stats, title="📈 Estadísticas", box=ROUNDED, border_style="blue"))
    console.print()
    console.print(Panel(
        "💡 Los reportes JSON se generaron en las carpetas [cyan]outcome/[/cyan] de cada checker.",
        box=ROUNDED,
        border_style="dim"
    ))

def run_all_checkers():
    """Ejecuta todos los checkers de forma automática con proyecto default y output JSON."""
    import time as time_module
    
    tool_config = TOOLS.get("A")
    if not tool_config:
        print(f"{Colors.FAIL}Configuración de 'Ejecutar Todos' no encontrada.{Colors.ENDC}")
        return
    
    auto_tools = tool_config.get("auto_tools", [])
    
    # Header con Rich si está disponible
    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel(
            Align.center(Text("🚀 EJECUTAR TODOS LOS CHECKERS", style="bold cyan")),
            box=DOUBLE_EDGE,
            border_style="magenta",
        ))
        console.print()
        
        # Lista de checkers a ejecutar
        checkers_table = Table(box=ROUNDED, border_style="cyan", show_header=False)
        checkers_table.add_column("Info", style="cyan")
        for tool_key in auto_tools:
            tool = TOOLS.get(tool_key, {})
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            checkers_table.add_row(f"{group.get('emoji', '🔧')} {tool.get('name', 'Unknown')}")
        console.print(checkers_table)
        
        console.print(f"\n[yellow]⚠️ {tool_config.get('excluded_reason', '')}[/yellow]\n")
    else:
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f"{'EJECUTAR TODOS LOS CHECKERS':^60}")
        print(f"{'='*60}{Colors.ENDC}\n")
        
        print(f"{Colors.CYAN}Se ejecutarán {len(auto_tools)} checkers:{Colors.ENDC}")
        for tool_key in auto_tools:
            tool = TOOLS.get(tool_key, {})
            print(f"  • {tool.get('name', 'Unknown')}")
        
        print(f"\n{Colors.WARNING}{tool_config.get('excluded_reason', '')}{Colors.ENDC}")
    
    # Solicitar proyecto una sola vez
    print(f"\n{Colors.BOLD}Proyecto GCP [{Colors.CYAN}{DEFAULT_PROJECT_ID}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
    project = input().strip()
    if not project:
        project = DEFAULT_PROJECT_ID
        print(f"{Colors.GREEN}Usando proyecto: {project}{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}¿Continuar? (s/n) [s]:{Colors.ENDC} ", end="")
    confirm = input().strip().lower()
    if confirm == 'n':
        print(f"{Colors.WARNING}Operación cancelada.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    # Preparar venv
    venv_python = get_venv_python()
    if not venv_python:
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    start_time = time_module.time()
    results = []
    
    for idx, tool_key in enumerate(auto_tools, 1):
        tool = TOOLS.get(tool_key)
        if not tool:
            continue
        
        # Progress indicator
        if RICH_AVAILABLE and console:
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            console.print(f"\n[bold cyan]🔵 [{idx}/{len(auto_tools)}][/bold cyan] {group.get('emoji', '🔧')} [white]{tool['name']}[/white]")
            console.print(f"[dim]{'─'*50}[/dim]")
        else:
            print(f"\n{Colors.HEADER}[{idx}/{len(auto_tools)}] {tool['name']}{Colors.ENDC}")
            print(f"{Colors.CYAN}{'-'*50}{Colors.ENDC}")
        
        # Instalar dependencias si es necesario
        if tool.get("requirements"):
            if not install_requirements(tool["requirements"], venv_python):
                results.append((tool['name'], "ERROR", "Fallo instalación dependencias"))
                continue
        
        # Construir comando
        script_path = BASE_DIR / tool["path"]
        if not script_path.exists():
            results.append((tool['name'], "ERROR", f"Script no encontrado: {script_path}"))
            continue
        
        cmd = [venv_python, str(script_path), "--project", project, "-o", "json"]
        
        try:
            result = subprocess.run(cmd, check=True)
            results.append((tool['name'], "OK", "Completado"))
        except subprocess.CalledProcessError as e:
            results.append((tool['name'], "ERROR", str(e)))
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")
            break
    
    # Resumen final
    elapsed = time_module.time() - start_time
    
    if RICH_AVAILABLE and console:
        print_execution_summary_rich(results, elapsed)
    else:
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f"{'RESUMEN DE EJECUCIÓN':^60}")
        print(f"{'='*60}{Colors.ENDC}\n")
        
        ok_count = sum(1 for r in results if r[1] == "OK")
        error_count = sum(1 for r in results if r[1] == "ERROR")
        
        for name, status, msg in results:
            if status == "OK":
                print(f"  {Colors.GREEN}✅ {name}{Colors.ENDC}")
            else:
                print(f"  {Colors.FAIL}❌ {name}: {msg}{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Total: {ok_count} OK, {error_count} errores")
        print(f"Tiempo total: {elapsed:.2f} segundos{Colors.ENDC}")
        print(f"\n{Colors.CYAN}Tip: Los reportes JSON se generaron en las carpetas outcome/ de cada checker.{Colors.ENDC}")
    
    input("\nPresione Enter para continuar...")

def main():
    """Función principal del menú."""
    while True:
        try:
            print_header()
            print_menu()
            
            choice = input(f"\n{Colors.BOLD}Seleccione una opción: {Colors.ENDC}").strip().upper()
            
            if choice == "A":
                run_all_checkers()
            elif choice in TOOLS:
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
        sys.exit(0)