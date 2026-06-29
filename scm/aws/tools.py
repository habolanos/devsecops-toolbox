#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Tools Launcher

Este script proporciona una interfaz de menú para ejecutar las herramientas de AWS
desde un solo lugar.

Ahora:
- Crea (si no existe) un entorno virtual en BASE_DIR/.venv
- Instala los requirements de cada herramienta dentro de ese venv
- Ejecuta las herramientas usando el Python del venv

Uso:
    python tools.py
    python tools.py --profile my-profile --region us-east-1
"""

import datetime
import os
import sys
import subprocess
import platform
import argparse
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

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA DEL PROGRAMA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.0.1"
__author__ = "Harold Adrian"
__description__ = "Launcher unificado de herramientas AWS DevSecOps"

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
    "compute": {"name": "Compute", "emoji": "💻", "color": "bright_blue"},
    "inventory": {"name": "Inventory", "emoji": "📋", "color": "bright_white"},
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
OUTCOME_DIR = BASE_DIR / "outcome"

# Valores por defecto AWS
DEFAULT_PROFILE = "default"
DEFAULT_REGION = "us-east-1"

# Definición de las herramientas disponibles (con grupo asignado)
# Ordenadas por grupo: iam(1-3), security(17), database(4-5,14), network(6-8,18), kubernetes(9,15,16), artifacts(10), compute(11-12), monitoring(13), inventory(19)
TOOLS = {
    # ══════════ IAM & SECURITY (1-3) ══════════
    "1": {
        "name": "IAM Users & Policies Checker",
        "description": "Analiza usuarios IAM, políticas, MFA y access keys",
        "path": "iam/aws_iam_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "iam",
        "status": "ready"
    },
    "2": {
        "name": "IAM Roles Checker",
        "description": "Lista roles IAM, trust policies y permisos adjuntos",
        "path": "iam/aws_roles_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "iam",
        "status": "ready"
    },
    "3": {
        "name": "ACM Certificate Checker",
        "description": "Monitorea certificados SSL/TLS en AWS Certificate Manager",
        "path": "acm/aws_acm_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "iam",
        "status": "ready"
    },
    # ══════════ SECURITY (17) ══════════
    "17": {
        "name": "Secrets Manager & SSM Checker",
        "description": "Secretos, rotación y parámetros SSM Parameter Store",
        "path": "secretsmanager/aws_secrets_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "security",
        "status": "ready"
    },
    # ══════════ DATABASE (4-5, 14) ══════════
    "4": {
        "name": "RDS Instance Checker",
        "description": "Analiza instancias RDS: estado, almacenamiento, backups",
        "path": "rds/aws_rds_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "database",
        "status": "ready"
    },
    "5": {
        "name": "RDS Storage Monitor",
        "description": "Monitorea uso de almacenamiento en instancias RDS",
        "path": "rds/aws_rds_storage_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "database",
        "status": "ready"
    },
    "14": {
        "name": "EBS Volume Checker",
        "description": "Analiza volúmenes EBS: cifrado, snapshots, adjuntos",
        "path": "ec2/aws_ebs_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "database",
        "status": "ready"
    },
    # ══════════ NETWORKING (6-8, 18) ══════════
    "6": {
        "name": "VPC Networks Checker",
        "description": "Visualiza VPCs, subnets, route tables y NAT gateways",
        "path": "vpc/aws_vpc_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "network",
        "status": "ready"
    },
    "7": {
        "name": "Security Groups Checker",
        "description": "Analiza Security Groups y reglas de entrada/salida",
        "path": "vpc/aws_security_groups_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "network",
        "status": "ready"
    },
    "8": {
        "name": "Load Balancer Checker (ALB/NLB)",
        "description": "Analiza Application y Network Load Balancers",
        "path": "elb/aws_load_balancer_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "network",
        "status": "ready"
    },
    "18": {
        "name": "WAF Web ACL Checker",
        "description": "AWS WAF v2: Web ACLs, reglas, logging y asociaciones",
        "path": "waf/aws_waf_checker.py",
        "args": ["--profile", "--region", "--scope", "-o"],
        "requirements": None,
        "group": "network",
        "status": "ready"
    },
    # ══════════ KUBERNETES (9, 15, 16) ══════════
    "9": {
        "name": "EKS Cluster Checker",
        "description": "Monitorea clusters EKS, node groups y configuración",
        "path": "eks/aws_eks_checker.py",
        "args": ["--profile", "--region", "--cluster", "-o"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "15": {
        "name": "EKS Pod Monitor",
        "description": "CPU/memoria por pod en clusters EKS (kubectl top pods)",
        "path": "eks/aws_eks_pod_checker.py",
        "args": ["--profile", "--region", "--cluster", "--namespace", "--sort", "--top", "-o"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "16": {
        "name": "EKS Node Monitor",
        "description": "Estado y recursos de nodos EKS (kubectl top nodes)",
        "path": "eks/aws_eks_node_checker.py",
        "args": ["--profile", "--region", "--cluster", "--sort", "-o"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    # ══════════ ARTIFACTS (10) ══════════
    "10": {
        "name": "ECR Repository Checker",
        "description": "Lista repositorios ECR, imágenes y políticas de ciclo de vida",
        "path": "ecr/aws_ecr_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "artifacts",
        "status": "ready"
    },
    # ══════════ COMPUTE (11-12) ══════════
    "11": {
        "name": "EC2 Instances Checker",
        "description": "Analiza instancias EC2: estado, tipo, volúmenes, tags",
        "path": "ec2/aws_ec2_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "compute",
        "status": "ready"
    },
    "12": {
        "name": "Lambda Functions Checker",
        "description": "Lista funciones Lambda, runtime, memoria y timeouts",
        "path": "lambda/aws_lambda_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "compute",
        "status": "ready"
    },
    # ══════════ MONITORING (13) ══════════
    "13": {
        "name": "CloudWatch Alarms Checker",
        "description": "Monitorea alarmas CloudWatch y su estado",
        "path": "cloudwatch/aws_cloudwatch_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "monitoring",
        "status": "ready"
    },
    # ══════════ INVENTORY (19) ══════════
    "19": {
        "name": "AWS Inventory Generator",
        "description": "Inventario completo EKS/RDS/EC2/ELB/Lambda/DynamoDB/S3",
        "path": "inventory/aws_inventory_generator.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": "inventory/requirements.txt",
        "group": "inventory",
        "status": "ready"
    },
    # ══════════ SYSTEM (A, Q) ══════════
    "_system_options": {
        "A": {
            "name": "Ejecutar Todos (Checkers)",
            "description": "Ejecuta todos los checkers con profile y región por defecto",
            "type": "auto_run",
            "exclude": ["15", "16", "19"],
            "reason": "Excluye: EKS Pod Monitor, EKS Node Monitor, Inventory (pipeline propio)"
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

_init_system_options()

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
    title.append("SRE Tools for AWS Cloud Platform", style="bold cyan")
    title.append("  ☁️", style="bold white")

    subtitle = Text()
    subtitle.append(f"v{__version__}", style="bold green")
    subtitle.append(" | ", style="dim")
    subtitle.append(f"by {__author__}", style="italic yellow")

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
    print(f"{'AWS TOOLS':^60}")
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
    """
    Genera lista de herramientas para auto_run dinámicamente.
    
    Itera por GROUP_ORDER, obtiene herramientas de cada grupo,
    excluye las especificadas, y retorna lista ordenada.
    
    Args:
        exclude_list: Lista de IDs a excluir (ej: ["15", "16"])
    
    Returns:
        Lista de IDs de herramientas válidas, ordenadas por grupo
    """
    exclude_list = exclude_list or []
    auto_tools = []
    
    # Iterar por grupos en orden
    for group_key in GROUP_ORDER:
        # Obtener herramientas de este grupo
        group_tools = [
            key for key, tool in TOOLS.items()
            if (tool.get("group") == group_key and 
                key not in ("Q", "A", "_system_options") and
                key not in exclude_list)
        ]
        
        # Ordenar numéricamente dentro del grupo
        group_tools.sort(key=_menu_sort_key)
        auto_tools.extend(group_tools)
    
    return auto_tools


def build_system_options():
    """
    Construye las opciones de sistema (A, Q) dinámicamente.
    Reemplaza el hardcode actual con generación dinámica.
    
    Lee la configuración de _system_options y genera auto_tools
    para cada opción de tipo auto_run.
    """
    system_opts = TOOLS.get("_system_options", {})
    
    for key, opt_config in system_opts.items():
        if opt_config.get("type") in ("auto_run", "auto_run_json"):
            # Generar auto_tools dinámicamente
            exclude = opt_config.get("exclude", [])
            auto_tools = get_auto_tools(exclude)
            
            # Crear opción final
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "auto_tools": auto_tools,
                "group": "system",
                "status": "ready"
            }
        else:
            # Opciones simples (como "Q")
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "group": "system",
                "status": opt_config.get("type", "exit")
            }


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
# GESTIÓN DEL ENTORNO VIRTUAL
# ═══════════════════════════════════════════════════════════════════════════════

def get_venv_python() -> Optional[str]:
    """
    Devuelve la ruta al ejecutable de python dentro del venv.
    Si no existe el venv, lo crea usando el HOST_PYTHON.

    Retorna:
        str con la ruta al python del venv, o None si falla.
    """
    if platform.system() == "Windows":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

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
        try:
            import shutil
            shutil.rmtree(str(VENV_DIR), ignore_errors=True)
        except Exception:
            pass
        try:
            if INSTALLED_MARKER.exists():
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
        pass

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

    if not force and requirements_path in get_installed_requirements():
        needs_reinstall = False
        if "inventory" in requirements_path:
            if not verify_package_installed(python_exec, "pandas"):
                print(f"{Colors.WARNING}Pandas no encontrado, reinstalando...{Colors.ENDC}")
                needs_reinstall = True
        if not needs_reinstall:
            print(f"{Colors.GREEN}Dependencias de {requirements_path} ya instaladas (usando caché).{Colors.ENDC}")
            return True
        force = True

    print(f"\n{Colors.CYAN}Instalando dependencias de {req_file} en el venv...{Colors.ENDC}")
    try:
        subprocess.check_call([python_exec, "-m", "pip", "install", "-r", str(req_file)])
        print(f"{Colors.GREEN}Dependencias instaladas correctamente.{Colors.ENDC}")
        mark_requirements_installed(requirements_path)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al instalar dependencias: {e}{Colors.ENDC}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN DE HERRAMIENTAS
# ═══════════════════════════════════════════════════════════════════════════════

_PLATFORM = "AWS"

def log_command(cmd: List[str], status: str = "EXEC") -> None:
    """Registra el comando en el log global si DEVSECOPS_LOG_COMMANDS=1."""
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

def run_tool(tool_key: str):
    """Ejecuta la herramienta seleccionada."""
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
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual. Abortando herramienta.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    if tool.get("requirements"):
        if not install_requirements(tool["requirements"], venv_python):
            print(f"{Colors.FAIL}No se pudieron instalar las dependencias necesarias.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return

    script_path = BASE_DIR / tool["path"]

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

    args = []
    tool_args = tool.get("args", [])

    if "--profile" in tool_args:
        print(f"\n{Colors.BOLD}AWS Profile [{Colors.CYAN}{DEFAULT_PROFILE}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        profile = input().strip()
        if not profile:
            profile = DEFAULT_PROFILE
            print(f"{Colors.GREEN}Usando profile: {profile}{Colors.ENDC}")
        args.extend(["--profile", profile])

    if "--region" in tool_args:
        print(f"\n{Colors.BOLD}AWS Region [{Colors.CYAN}{DEFAULT_REGION}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        region = input().strip()
        if not region:
            region = DEFAULT_REGION
            print(f"{Colors.GREEN}Usando región: {region}{Colors.ENDC}")
        args.extend(["--region", region])

    if "--cluster" in tool_args:
        print(f"\n{Colors.BOLD}Nombre del cluster EKS (vacío para selección automática):{Colors.ENDC} ", end="")
        cluster = input().strip()
        if cluster:
            args.extend(["--cluster", cluster])

    if "--namespace" in tool_args:
        print(f"\n{Colors.BOLD}Namespace Kubernetes (vacío para todos):{Colors.ENDC} ", end="")
        namespace = input().strip()
        if namespace:
            args.extend(["--namespace", namespace])

    if "--scope" in tool_args:
        print(f"\n{Colors.BOLD}WAF Scope (REGIONAL/CLOUDFRONT) [REGIONAL]:{Colors.ENDC} ", end="")
        scope = input().strip().upper()
        if scope not in ["REGIONAL", "CLOUDFRONT"]:
            scope = "REGIONAL"
            print(f"{Colors.GREEN}Usando scope: {scope}{Colors.ENDC}")
        args.extend(["--scope", scope])

    if "--sort" in tool_args:
        print(f"\n{Colors.BOLD}Ordenar por (cpu/memory/name) [cpu]:{Colors.ENDC} ", end="")
        sort = input().strip().lower()
        if sort in ["cpu", "memory", "name"]:
            args.extend(["--sort", sort])

    if "--top" in tool_args:
        print(f"\n{Colors.BOLD}Mostrar top N resultados (0 = todos) [0]:{Colors.ENDC} ", end="")
        top_val = input().strip()
        try:
            top_int = int(top_val) if top_val else 0
            if top_int > 0:
                args.extend(["--top", str(top_int)])
        except ValueError:
            pass

    if "--output" in tool_args or "-o" in tool_args:
        print(f"\n{Colors.BOLD}¿Exportar resultado? (json/csv/table) [json]:{Colors.ENDC} ", end="")
        output_format = input().strip().lower()
        if output_format in ["json", "csv", "table"]:
            args.extend(["-o", output_format])
        else:
            args.extend(["-o", "json"])

    cmd.extend(args)

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

# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN MASIVA Y RESUMEN
# ═══════════════════════════════════════════════════════════════════════════════

def print_execution_summary_rich(results: list, elapsed: float):
    """Muestra el resumen de ejecución con Rich."""
    ok_count = sum(1 for r in results if r[1] == "OK")
    error_count = sum(1 for r in results if r[1] == "ERROR")

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
    """Ejecuta todos los checkers de forma automática con profile y región por defecto."""
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
            box=DOUBLE_EDGE,
            border_style="magenta",
        ))
        console.print()

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

    print(f"\n{Colors.BOLD}AWS Profile [{Colors.CYAN}{DEFAULT_PROFILE}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
    profile = input().strip()
    if not profile:
        profile = DEFAULT_PROFILE
        print(f"{Colors.GREEN}Usando profile: {profile}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}AWS Region [{Colors.CYAN}{DEFAULT_REGION}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
    region = input().strip()
    if not region:
        region = DEFAULT_REGION
        print(f"{Colors.GREEN}Usando región: {region}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}¿Continuar? (s/n) [s]:{Colors.ENDC} ", end="")
    confirm = input().strip().lower()
    if confirm == 'n':
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

    for idx, tool_key in enumerate(auto_tools, 1):
        tool = TOOLS.get(tool_key)
        if not tool:
            continue

        if RICH_AVAILABLE and console:
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            console.print(f"\n[bold cyan]🔵 [{idx}/{len(auto_tools)}][/bold cyan] {group.get('emoji', '🔧')} [white]{tool['name']}[/white]")
            console.print(f"[dim]{'─'*50}[/dim]")
        else:
            print(f"\n{Colors.HEADER}[{idx}/{len(auto_tools)}] {tool['name']}{Colors.ENDC}")
            print(f"{Colors.CYAN}{'-'*50}{Colors.ENDC}")

        if tool.get("requirements"):
            if not install_requirements(tool["requirements"], venv_python):
                results.append((tool['name'], "ERROR", "Fallo instalación dependencias"))
                continue

        script_path = BASE_DIR / tool["path"]
        if not script_path.exists():
            results.append((tool['name'], "ERROR", f"Script no encontrado: {script_path}"))
            continue

        cmd = [venv_python, str(script_path), "--profile", profile, "--region", region, "-o", "json"]

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

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Función principal del menú."""
    global DEFAULT_PROFILE, DEFAULT_REGION

    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument("--profile", "-p", default=DEFAULT_PROFILE, help="AWS CLI profile por defecto")
    parser.add_argument("--region", "-r", default=DEFAULT_REGION, help="AWS region por defecto")
    cli_args = parser.parse_args()

    DEFAULT_PROFILE = cli_args.profile
    DEFAULT_REGION = cli_args.region

    OUTCOME_DIR.mkdir(exist_ok=True)

    while True:
        try:
            print_header()
            if RICH_AVAILABLE and console:
                console.print(f"[dim]Profile: {DEFAULT_PROFILE} | Region: {DEFAULT_REGION}[/dim]\n")
            else:
                print(f"Profile: {DEFAULT_PROFILE} | Region: {DEFAULT_REGION}\n")
            print_menu()

            choice = input(f"\n{Colors.BOLD}Seleccione una opción (o '/' para buscar): {Colors.ENDC}").strip().upper()

            # Opción de búsqueda
            if choice == "/":
                if SEARCH_AVAILABLE:
                    choice = search_and_select_tools(TOOLS, TOOL_GROUPS)
                    if choice is None:
                        continue
                else:
                    print(f"\n{Colors.YELLOW}⚠️  Búsqueda no disponible{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue

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
