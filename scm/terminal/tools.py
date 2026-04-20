#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal Tools Launcher

Menú para ejecutar scripts shell universales (agnostic) que funcionan
con cualquier Kubernetes cluster (GKE, EKS, AKS, OpenShift, etc.)

Uso:
    python terminal/tools.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict

# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-INSTALACIÓN DE RICH
# ═══════════════════════════════════════════════════════════════════════════════
def _ensure_rich():
    """Verifica si rich está instalado; si no, lo instala automáticamente."""
    try:
        import rich  # noqa: F401
        return True
    except ImportError:
        pass

    print("📦 Instalando rich para interfaz moderna...")
    pip_args = [sys.executable, "-m", "pip", "install", "-q", "rich"]
    
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
    from rich.style import Style
    from rich.box import ROUNDED, DOUBLE_EDGE
    from rich.align import Align

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.0.0"
__author__ = "Harold Adrian"
__description__ = "Terminal Tools - Scripts Universales para Kubernetes"

console = Console() if RICH_AVAILABLE else None
BASE_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = BASE_DIR / "config.json"
CONFIG_TEMPLATE = BASE_DIR / "config.json.template"

# ═══════════════════════════════════════════════════════════════════════════════
# GESTIÓN DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
def load_config() -> Dict:
    """Carga la configuración desde config.json si existe."""
    if CONFIG_FILE.exists():
        try:
            import json
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def prepare_env_from_config() -> Dict[str, str]:
    """Prepara variables de entorno desde la configuración."""
    env = os.environ.copy()
    config = load_config()
    
    # Variables globales
    if config.get("timezone"):
        env["TERMINAL_TIMEZONE"] = config["timezone"]
    if config.get("timeout"):
        env["TERMINAL_TIMEOUT"] = str(config["timeout"])
    if config.get("default_namespace"):
        env["TERMINAL_NAMESPACE"] = config["default_namespace"]
    
    # Variables de K8s
    k8s_config = config.get("kubernetes", {})
    if k8s_config.get("default_limit"):
        env["TERMINAL_K8S_LIMIT"] = str(k8s_config["default_limit"])
    if k8s_config.get("context"):
        env["TERMINAL_K8S_CONTEXT"] = k8s_config["context"]
    
    return env

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
# SCRIPTS DISPONIBLES
# ═══════════════════════════════════════════════════════════════════════════════
SCRIPTS = {
    "1": {
        "name": "Certificate TLS Report",
        "description": "Valida certificados SSL/TLS remotos desde cualquier cluster K8s (CN, emisor, expiración, chain, TLS version, cipher reales)",
        "path": "check-certificate-report.sh",
        "args": ["host", "port"],
        "status": "ready"
    },
    "2": {
        "name": "Database Connections Checker",
        "description": "Valida conectividad a múltiples instancias PostgreSQL usando netcat (nc)",
        "path": "db-connections-checker.sh",
        "args": [],
        "status": "ready"
    },
    "3": {
        "name": "Deployments Last News",
        "description": "Muestra los deployments más recientes ordenados por fecha de creación",
        "path": "deployments-last-news.sh",
        "args": ["limit"],
        "status": "ready"
    },
    "4": {
        "name": "Deployments Last Update",
        "description": "Muestra deployments ordenados por último rollout (usando ReplicaSet)",
        "path": "deployments-last-update.sh",
        "args": ["limit", "namespace"],
        "status": "ready"
    },
    "5": {
        "name": "Deployments Recent Events",
        "description": "Muestra eventos recientes relacionados con Deployments",
        "path": "deployments-recent-events.sh",
        "args": ["limit", "namespace"],
        "status": "ready"
    },
    "Q": {
        "name": "Volver al menú principal",
        "description": "Regresar al launcher principal",
        "path": None,
        "args": [],
        "status": "exit"
    }
}

STATUS_EMOJI = {
    "ready": "🟢",
    "exit": "🚪"
}

def print_menu_rich():
    """Muestra el menú con Rich."""
    console.print()
    
    # Header
    header = Panel(
        Align.center(Text("🔧 TERMINAL TOOLS", style="bold cyan")),
        box=DOUBLE_EDGE,
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(header)
    
    # Descripción
    console.print(Panel(
        "[dim]Scripts universales para Kubernetes - Compatibles con GKE, EKS, AKS, OpenShift[/dim]",
        box=ROUNDED,
        border_style="dim"
    ))
    console.print()
    
    # Tabla de scripts
    table = Table(
        box=ROUNDED,
        header_style="bold cyan",
        border_style="cyan",
        title="[bold]Scripts Disponibles[/bold]",
        title_style="cyan"
    )
    
    table.add_column("#", justify="center", width=4)
    table.add_column("Estado", justify="center", width=4)
    table.add_column("Nombre", style="white", min_width=25)
    table.add_column("Descripción", style="dim", min_width=40)
    
    for key, script in SCRIPTS.items():
        emoji = STATUS_EMOJI.get(script.get("status", "ready"), "⚪")
        name_style = "bold white" if key != "Q" else "bold yellow"
        
        table.add_row(
            f"[cyan]{key}[/cyan]",
            emoji,
            f"[{name_style}]{script['name']}[/{name_style}]",
            script.get('description', '')
        )
    
    console.print(table)
    console.print()

def print_menu_fallback():
    """Muestra el menú sin Rich."""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'🔧  TERMINAL TOOLS':^60}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.DIM}Scripts universales para Kubernetes{Colors.ENDC}")
    print()
    
    for key, script in SCRIPTS.items():
        emoji = STATUS_EMOJI.get(script.get("status", "ready"), "⚪")
        color = Colors.WARNING if key == "Q" else Colors.BLUE
        print(f"  {color}[{key}]{Colors.ENDC} {emoji} {Colors.BOLD}{script['name']}{Colors.ENDC}")
        print(f"      {script.get('description', '')}")
    print()

def check_windows_compatibility():
    """Verifica si estamos en Windows y muestra advertencia."""
    if platform.system() == "Windows":
        print(f"\n{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"{Colors.FAIL}  ⚠️  ATENCIÓN: PLATAFORMA WINDOWS DETECTADA{Colors.ENDC}")
        print(f"{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Los scripts de esta sección son archivos shell (.sh){Colors.ENDC}")
        print(f"{Colors.WARNING}y requieren un entorno Linux/Unix para ejecutarse.{Colors.ENDC}")
        print(f"\n{Colors.CYAN}Opciones:{Colors.ENDC}")
        print(f"  1. Ejecutar en {Colors.BOLD}WSL (Windows Subsystem for Linux){Colors.ENDC}")
        print(f"  2. Usar {Colors.BOLD}Git Bash{Colors.ENDC} o similar")
        print(f"  3. Conectarse a una máquina Linux remota")
        print(f"\n{Colors.FAIL}Presione Enter para volver al menú principal...{Colors.ENDC}")
        input()
        return False
    return True

def run_script(script_key: str):
    """Ejecuta el script seleccionado."""
    if script_key not in SCRIPTS:
        print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return
    
    script = SCRIPTS[script_key]
    
    if script_key == "Q":
        print(f"\n{Colors.GREEN}Volviendo al menú principal...{Colors.ENDC}")
        return
    
    print(f"\n{Colors.HEADER}=== {script['name']} ==={Colors.ENDC}")
    print(f"{script['description']}\n")
    
    # Verificar compatibilidad con Windows
    if not check_windows_compatibility():
        return
    
    script_path = BASE_DIR / script["path"]
    
    if not script_path.exists():
        print(f"{Colors.FAIL}Error: No se encontró el script {script_path}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return
    
    # Construir comando
    cmd = ["sh", str(script_path)]
    
    # Solicitar argumentos
    args = script.get("args", [])
    
    if "host" in args:
        host = input(f"{Colors.BOLD}Host a validar (ej: api.ejemplo.com): {Colors.ENDC}").strip()
        if not host:
            print(f"{Colors.FAIL}Se requiere el host.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        cmd.append(host)
    
    if "port" in args:
        port = input(f"{Colors.BOLD}Puerto [443]: {Colors.ENDC}").strip()
        if not port:
            port = "443"
        cmd.append(port)
    
    if "limit" in args:
        limit = input(f"{Colors.BOLD}Cantidad a mostrar [15]: {Colors.ENDC}").strip()
        if not limit:
            limit = "15"
        cmd.append(limit)
    
    if "namespace" in args:
        ns = input(f"{Colors.BOLD}Namespace (vacío para todos): {Colors.ENDC}").strip()
        if ns:
            cmd.append(ns)
    
    print(f"\n{Colors.CYAN}Ejecutando: {' '.join(cmd)}{Colors.ENDC}\n")
    
    # Preparar variables de entorno con configuración
    env = prepare_env_from_config()
    
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}Error al ejecutar el script: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")
    
    input("\nPresione Enter para continuar...")

def main():
    """Bucle principal del menú."""
    while True:
        if RICH_AVAILABLE and console:
            print_menu_rich()
        else:
            print_menu_fallback()
        
        try:
            choice = input(f"{Colors.BOLD}Seleccione una opción: {Colors.ENDC}").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
            break
        
        if choice == "Q":
            print(f"\n{Colors.GREEN}Volviendo al menú principal...{Colors.ENDC}")
            break
        
        run_script(choice)

if __name__ == "__main__":
    main()
