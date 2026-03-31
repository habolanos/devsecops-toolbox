#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Tools Launcher

Interfaz de menú interactivo para ejecutar herramientas DevSecOps de AWS.
Proporciona acceso unificado a checkers de IAM, RDS, VPC, EKS, ECR y más.

Uso:
    python tools.py
    python tools.py --profile my-profile --region us-west-2
"""

import os
import sys
import json
import subprocess
import platform
import argparse
from pathlib import Path
from typing import Optional, Dict, List

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

__version__ = "1.0.0"
__author__ = "Harold Adrian"
__description__ = "Launcher unificado de herramientas AWS DevSecOps"

console = Console() if RICH_AVAILABLE else None

BASE_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = BASE_DIR / "config.json"
OUTCOME_DIR = BASE_DIR / "outcome"
VENV_DIR = BASE_DIR / ".venv"
INSTALLED_MARKER = VENV_DIR / ".installed_requirements"

TOOL_GROUPS = {
    "iam": {"name": "IAM & Security", "emoji": "🔐", "color": "yellow"},
    "database": {"name": "Database (RDS)", "emoji": "💾", "color": "magenta"},
    "network": {"name": "Networking", "emoji": "🌐", "color": "blue"},
    "kubernetes": {"name": "Kubernetes (EKS)", "emoji": "☸️", "color": "green"},
    "artifacts": {"name": "Artifacts (ECR)", "emoji": "📦", "color": "red"},
    "compute": {"name": "Compute", "emoji": "💻", "color": "cyan"},
    "monitoring": {"name": "Monitoring", "emoji": "📊", "color": "bright_white"},
    "system": {"name": "Sistema", "emoji": "⚙️", "color": "white"},
}

GROUP_ORDER = list(TOOL_GROUPS.keys())

TOOLS = {
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
    "9": {
        "name": "EKS Cluster Checker",
        "description": "Monitorea clusters EKS, node groups y configuración",
        "path": "eks/aws_eks_checker.py",
        "args": ["--profile", "--region", "--cluster", "-o"],
        "requirements": None,
        "group": "kubernetes",
        "status": "ready"
    },
    "10": {
        "name": "ECR Repository Checker",
        "description": "Lista repositorios ECR, imágenes y políticas de ciclo de vida",
        "path": "ecr/aws_ecr_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "artifacts",
        "status": "ready"
    },
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
    "13": {
        "name": "CloudWatch Alarms Checker",
        "description": "Monitorea alarmas CloudWatch y su estado",
        "path": "cloudwatch/aws_cloudwatch_checker.py",
        "args": ["--profile", "--region", "-o"],
        "requirements": None,
        "group": "monitoring",
        "status": "ready"
    },
    "A": {
        "name": "Ejecutar Todos (Checkers)",
        "description": "Ejecuta todos los checkers con configuración por defecto",
        "auto_tools": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
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

STATUS_INDICATORS = {
    "ready": ("🟢", "green", "Listo"),
    "warning": ("🟡", "yellow", "Advertencia"),
    "error": ("🔴", "red", "Error"),
    "running": ("🔵", "blue", "Ejecutando"),
    "exit": ("🚪", "white", "Salir"),
}

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def clear_screen():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_venv_python() -> str:
    if platform.system() == "Windows":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def ensure_venv():
    if not VENV_DIR.exists():
        print(f"Creando entorno virtual en {VENV_DIR}...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("Entorno virtual creado.\n")


def install_requirements(req_file: Optional[str]):
    if not req_file:
        return
    
    req_path = BASE_DIR / req_file
    if not req_path.exists():
        return
    
    marker_content = ""
    if INSTALLED_MARKER.exists():
        marker_content = INSTALLED_MARKER.read_text()
    
    if str(req_path) in marker_content:
        return
    
    venv_python = get_venv_python()
    print(f"Instalando dependencias de {req_file}...")
    subprocess.run([venv_python, "-m", "pip", "install", "-q", "-r", str(req_path)], check=True)
    
    with open(INSTALLED_MARKER, "a") as f:
        f.write(f"{req_path}\n")


def show_header_rich():
    header = Panel(
        Align.center(
            Text.from_markup(
                f"[bold cyan]AWS DevSecOps Toolbox[/bold cyan]\n"
                f"[dim]v{__version__} | {__author__}[/dim]"
            )
        ),
        box=DOUBLE_EDGE,
        style="cyan",
        padding=(1, 2)
    )
    console.print(header)
    console.print()


def show_header_plain():
    print("=" * 60)
    print(f"  AWS DevSecOps Toolbox v{__version__}")
    print(f"  {__author__}")
    print("=" * 60)
    print()


def show_menu_rich():
    grouped_tools: Dict[str, List[tuple]] = {g: [] for g in GROUP_ORDER}
    
    for key, tool in TOOLS.items():
        group = tool.get("group", "system")
        if group in grouped_tools:
            grouped_tools[group].append((key, tool))
    
    table = Table(
        title="[bold]Herramientas Disponibles[/bold]",
        box=ROUNDED,
        show_header=True,
        header_style="bold white on blue",
        title_style="bold cyan",
        expand=True
    )
    
    table.add_column("#", style="bold cyan", width=3, justify="center")
    table.add_column("Estado", width=6, justify="center")
    table.add_column("Herramienta", style="white", min_width=30)
    table.add_column("Descripción", style="dim")
    
    for group_key in GROUP_ORDER:
        tools_in_group = grouped_tools.get(group_key, [])
        if not tools_in_group:
            continue
        
        group_info = TOOL_GROUPS[group_key]
        group_header = f"{group_info['emoji']} [bold {group_info['color']}]{group_info['name']}[/bold {group_info['color']}]"
        table.add_row("", "", group_header, "", style=f"on grey23")
        
        for key, tool in tools_in_group:
            status = tool.get("status", "ready")
            indicator = STATUS_INDICATORS.get(status, STATUS_INDICATORS["ready"])
            emoji, color, _ = indicator
            
            table.add_row(
                key,
                emoji,
                tool["name"],
                tool["description"]
            )
    
    console.print(table)
    console.print()


def show_menu_plain():
    print("\nHerramientas disponibles:\n")
    for key, tool in TOOLS.items():
        print(f"  [{key}] {tool['name']}")
        print(f"      {tool['description']}")
    print()


def run_tool(tool_key: str, profile: str, region: str):
    tool = TOOLS.get(tool_key)
    if not tool:
        print(f"Herramienta '{tool_key}' no encontrada.")
        return
    
    if tool.get("status") == "exit":
        return "exit"
    
    if "auto_tools" in tool:
        print(f"\n{'='*60}")
        print(f"Ejecutando todos los checkers automáticamente...")
        print(f"{'='*60}\n")
        for auto_key in tool["auto_tools"]:
            run_tool(auto_key, profile, region)
        return
    
    tool_path = BASE_DIR / tool["path"]
    if not tool_path.exists():
        if RICH_AVAILABLE:
            console.print(f"[red]✗ Script no encontrado: {tool_path}[/red]")
        else:
            print(f"ERROR: Script no encontrado: {tool_path}")
        return
    
    ensure_venv()
    install_requirements(tool.get("requirements"))
    
    venv_python = get_venv_python()
    cmd = [venv_python, str(tool_path)]
    
    if "--profile" in tool.get("args", []) and profile:
        cmd.extend(["--profile", profile])
    if "--region" in tool.get("args", []) and region:
        cmd.extend(["--region", region])
    if "-o" in tool.get("args", []):
        cmd.extend(["-o", "json"])
    
    if RICH_AVAILABLE:
        console.print(f"\n[bold cyan]▶ Ejecutando:[/bold cyan] {tool['name']}")
        console.print(f"[dim]  Comando: {' '.join(cmd)}[/dim]\n")
    else:
        print(f"\n>>> Ejecutando: {tool['name']}")
        print(f"    Comando: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR))
        if result.returncode != 0:
            if RICH_AVAILABLE:
                console.print(f"[yellow]⚠ La herramienta terminó con código: {result.returncode}[/yellow]")
            else:
                print(f"ADVERTENCIA: La herramienta terminó con código: {result.returncode}")
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[red]✗ Error ejecutando herramienta: {e}[/red]")
        else:
            print(f"ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    args = parser.parse_args()
    
    config = load_config()
    profile = config.get("aws", {}).get("profile", args.profile)
    region = config.get("aws", {}).get("region", args.region)
    
    OUTCOME_DIR.mkdir(exist_ok=True)
    
    while True:
        clear_screen()
        
        if RICH_AVAILABLE:
            show_header_rich()
            console.print(f"[dim]Profile: {profile} | Region: {region}[/dim]\n")
            show_menu_rich()
            choice = console.input("[bold cyan]Seleccione una opción:[/bold cyan] ").strip().upper()
        else:
            show_header_plain()
            print(f"Profile: {profile} | Region: {region}\n")
            show_menu_plain()
            choice = input("Seleccione una opción: ").strip().upper()
        
        if choice == "Q":
            if RICH_AVAILABLE:
                console.print("\n[green]👋 ¡Hasta pronto![/green]\n")
            else:
                print("\n¡Hasta pronto!\n")
            break
        
        if choice in TOOLS:
            result = run_tool(choice, profile, region)
            if result == "exit":
                break
            input("\nPresione Enter para continuar...")
        else:
            if RICH_AVAILABLE:
                console.print(f"[red]Opción '{choice}' no válida.[/red]")
            else:
                print(f"Opción '{choice}' no válida.")
            input("Presione Enter para continuar...")


if __name__ == "__main__":
    main()
