#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DevSecOps Toolbox - Main Launcher

Punto de entrada unificado para acceder a las herramientas de:
- Azure DevOps (azdo/tools.py)
- Google Cloud Platform (gcp/tools.py)
- Amazon Web Services (aws/tools.py)

Uso:
    python main.py
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path
from typing import Dict, Any, Optional

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

    # Leer paquetes desde requirements.txt
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

# Importar rich (ya garantizado si RICH_AVAILABLE)
if RICH_AVAILABLE:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.style import Style
    from rich.box import ROUNDED, DOUBLE_EDGE, HEAVY
    from rich.align import Align
    from rich.prompt import Prompt
    from rich.status import Status

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.6.0"
__author__ = "Harold Adrian"
__description__ = "DevSecOps Toolbox - Launcher Principal"

# Consola Rich
console = Console() if RICH_AVAILABLE else None

# Rutas
BASE_DIR = Path(__file__).parent.absolute()
HOST_PYTHON = sys.executable or "python"
CONFIG_FILE = BASE_DIR / "config.json"
CONFIG_TEMPLATE = BASE_DIR / "config.json.template"

# Configuración global cargada
_config: Optional[Dict[str, Any]] = None

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
        "description": "22 herramientas SRE: monitoreo, IAM, networking, K8s, inventario y más",
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
        "description": "IAM, RDS, VPC, EKS, ECR, EC2, Lambda, CloudWatch (13 herramientas)",
        "status": "ready"
    },
    "4": {
        "name": "Terminal Scripts",
        "short": "TERMINAL",
        "emoji": "🐧",
        "color": "gray",
        "path": "terminal/tools.py",
        "description": "Scripts shell agnósticos: certificados TLS, DB connections, K8s deployments (5 herramientas)",
        "status": "ready"
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


# ═══════════════════════════════════════════════════════════════════════════════
# GESTIÓN DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
def load_config() -> Optional[Dict[str, Any]]:
    """Carga la configuración desde config.json."""
    global _config
    
    if _config is not None:
        return _config
    
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            _config = json.load(f)
        return _config
    except json.JSONDecodeError as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error al parsear config.json: {e}[/red]")
        else:
            print(f"❌ Error al parsear config.json: {e}")
        return None
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error al cargar config.json: {e}[/red]")
        else:
            print(f"❌ Error al cargar config.json: {e}")
        return None


def get_platform_config(platform_key: str) -> Optional[Dict[str, Any]]:
    """Obtiene la configuración específica de una plataforma."""
    config = load_config()
    if not config:
        return None
    
    platform_map = {
        "1": "gcp",
        "2": "azdo",
        "3": "aws",
        "4": "terminal"
    }
    
    platform_name = platform_map.get(platform_key)
    if not platform_name:
        return None
    
    return config.get(platform_name)


def is_platform_configured(platform_key: str) -> bool:
    """Verifica si una plataforma tiene configuración válida."""
    platform_config = get_platform_config(platform_key)
    if not platform_config:
        return False
    
    # Verificar si está habilitada
    if not platform_config.get("enabled", True):
        return False
    
    # Verificaciones específicas por plataforma
    platform_map = {"1": "gcp", "2": "azdo", "3": "aws", "4": "terminal"}
    platform_name = platform_map.get(platform_key)
    
    if platform_name == "azdo":
        # AZDO requiere PAT y organización
        return bool(platform_config.get("pat") and 
                   platform_config.get("organization_url") and
                   "<TU_" not in str(platform_config.get("pat", "")) and
                   "<TU_" not in str(platform_config.get("organization_url", "")))
    
    elif platform_name == "gcp":
        # GCP requiere project_id
        return bool(platform_config.get("project_id") and
                   "<TU_" not in str(platform_config.get("project_id", "")))
    
    elif platform_name == "aws":
        # AWS requiere profile o credentials
        creds = platform_config.get("credentials", {})
        cred_type = creds.get("type", "profile")
        if cred_type == "profile":
            return bool(platform_config.get("profile"))
        elif cred_type == "keys":
            return bool(creds.get("access_key_id") and creds.get("secret_access_key"))
        return True
    
    elif platform_name == "terminal":
        # Terminal no requiere configuración especial
        return True
    
    return True


def get_config_status() -> Dict[str, str]:
    """Obtiene el estado de configuración de cada plataforma."""
    config = load_config()
    status = {}
    
    for key in ["1", "2", "3", "4"]:
        if not config:
            status[key] = "no_config"
        elif is_platform_configured(key):
            status[key] = "configured"
        else:
            status[key] = "incomplete"
    
    return status


def prepare_env_for_platform(platform_key: str) -> Dict[str, str]:
    """Prepara variables de entorno con la configuración de la plataforma."""
    env = os.environ.copy()
    config = load_config()
    
    if not config:
        return env
    
    platform_config = get_platform_config(platform_key)
    global_config = config.get("global", {})
    
    # Variables globales
    if global_config.get("debug"):
        env["DEVSECOPS_DEBUG"] = "1"
    if global_config.get("verbose"):
        env["DEVSECOPS_VERBOSE"] = "1"
    if global_config.get("output_dir"):
        output_dir = Path(global_config["output_dir"])
        if not output_dir.is_absolute():
            output_dir = BASE_DIR / output_dir
        env["DEVSECOPS_OUTPUT_DIR"] = str(output_dir.resolve())
    
    # Proxy
    proxy = global_config.get("proxy", {})
    if proxy.get("enabled"):
        if proxy.get("http"):
            env["HTTP_PROXY"] = proxy["http"]
        if proxy.get("https"):
            env["HTTPS_PROXY"] = proxy["https"]
        if proxy.get("no_proxy"):
            env["NO_PROXY"] = ",".join(proxy["no_proxy"])
    
    if not platform_config:
        return env
    
    # Variables específicas por plataforma
    platform_map = {"1": "gcp", "2": "azdo", "3": "aws", "4": "terminal"}
    platform_name = platform_map.get(platform_key)
    
    if platform_name == "azdo":
        if platform_config.get("organization_url"):
            env["AZDO_ORG_URL"] = platform_config["organization_url"]
        if platform_config.get("project"):
            env["AZDO_PROJECT"] = platform_config["project"]
        if platform_config.get("pat"):
            env["AZDO_PAT"] = platform_config["pat"]
        defaults = platform_config.get("defaults", {})
        if defaults.get("timezone"):
            env["AZDO_TIMEZONE"] = defaults["timezone"]
    
    elif platform_name == "gcp":
        if platform_config.get("project_id"):
            env["GCP_PROJECT_ID"] = platform_config["project_id"]
            env["CLOUDSDK_CORE_PROJECT"] = platform_config["project_id"]
        if platform_config.get("region"):
            env["GCP_REGION"] = platform_config["region"]
        creds = platform_config.get("credentials", {})
        if creds.get("service_account_key_path"):
            env["GOOGLE_APPLICATION_CREDENTIALS"] = creds["service_account_key_path"]
        k8s = platform_config.get("kubernetes", {})
        if k8s.get("cluster_name"):
            env["GKE_CLUSTER_NAME"] = k8s["cluster_name"]
        if k8s.get("cluster_region"):
            env["GKE_CLUSTER_REGION"] = k8s["cluster_region"]
    
    elif platform_name == "aws":
        if platform_config.get("profile"):
            env["AWS_PROFILE"] = platform_config["profile"]
        if platform_config.get("region"):
            env["AWS_DEFAULT_REGION"] = platform_config["region"]
            env["AWS_REGION"] = platform_config["region"]
        creds = platform_config.get("credentials", {})
        if creds.get("type") == "keys":
            if creds.get("access_key_id"):
                env["AWS_ACCESS_KEY_ID"] = creds["access_key_id"]
            if creds.get("secret_access_key"):
                env["AWS_SECRET_ACCESS_KEY"] = creds["secret_access_key"]
            if creds.get("session_token"):
                env["AWS_SESSION_TOKEN"] = creds["session_token"]
    
    return env


def print_config_status():
    """Muestra el estado de configuración."""
    config = load_config()
    status = get_config_status()
    
    if RICH_AVAILABLE and console:
        if not config:
            console.print(Panel(
                "[yellow]⚠️ No se encontró config.json[/yellow]\n"
                f"[dim]Copia config.json.template a config.json y configura tus credenciales.[/dim]",
                title="📋 Configuración",
                border_style="yellow",
                expand=False
            ))
        else:
            status_lines = []
            platform_names = {"1": "GCP", "2": "AZDO", "3": "AWS", "4": "TERMINAL"}
            for key, name in platform_names.items():
                st = status.get(key, "no_config")
                if st == "configured":
                    status_lines.append(f"[green]✅ {name}[/green]")
                elif st == "incomplete":
                    status_lines.append(f"[yellow]⚠️ {name} (incompleto)[/yellow]")
                else:
                    status_lines.append(f"[dim]❌ {name}[/dim]")
            
            console.print(Panel(
                "  ".join(status_lines),
                title="📋 Estado de Configuración",
                border_style="cyan",
                expand=False
            ))
    else:
        if not config:
            print(f"{Colors.WARNING}⚠️ No se encontró config.json{Colors.ENDC}")
        else:
            print(f"{Colors.CYAN}Estado de configuración:{Colors.ENDC}")
            for key, name in {"1": "GCP", "2": "AZDO", "3": "AWS", "4": "TERMINAL"}.items():
                st = status.get(key, "no_config")
                symbol = "✅" if st == "configured" else "⚠️" if st == "incomplete" else "❌"
                print(f"  {symbol} {name}")


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
    config_status = get_config_status()
    platform_map = {"1": "GCP", "2": "AZDO", "3": "AWS", "4": "TERMINAL"}

    table = Table(
        title="🚀 Seleccione una Plataforma",
        title_style="bold white",
        box=ROUNDED,
        header_style="bold cyan",
        border_style="blue",
        show_lines=False,
        pad_edge=True,
        expand=False,
    )
    
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Plataforma", justify="left", width=28)
    table.add_column("Config", justify="center", width=8)
    table.add_column("Descripción", justify="left", style="dim", min_width=45)
    
    for key, platform in PLATFORMS.items():
        status = platform.get("status", "ready")
        
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
        
        # Config status badge
        if key in platform_map:
            cfg = config_status.get(key, "no_config")
            if cfg == "configured":
                config_badge = "[green]✅[/green]"
            elif cfg == "incomplete":
                config_badge = "[yellow]⚠️[/yellow]"
            else:
                config_badge = "[dim]—[/dim]"
        elif status == "exit":
            config_badge = ""
        else:
            config_badge = ""
        
        table.add_row(
            f"[{key_style}]{key}[/{key_style}]",
            f"[{name_style}]{platform_name}[/{name_style}]",
            config_badge,
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
        if RICH_AVAILABLE and console:
            console.print("[red]❌ Opción no válida.[/red]")
        else:
            print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return
    
    platform = PLATFORMS[platform_key]
    
    if platform_key == "Q":
        if RICH_AVAILABLE and console:
            console.print("\n[bold green]👋 Saliendo...[/bold green]")
        else:
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
    
    # Preparar variables de entorno con configuración
    env = prepare_env_for_platform(platform_key)

    # Asegurar que scm/ está en PYTHONPATH para imports compartidos (utils.py)
    scm_path = str(BASE_DIR)
    existing_pp = env.get("PYTHONPATH", "")
    if scm_path not in existing_pp.split(os.pathsep):
        env["PYTHONPATH"] = scm_path + (os.pathsep + existing_pp if existing_pp else "")

    # Mostrar mensaje de transición con spinner
    if RICH_AVAILABLE and console:
        with console.status(f"[bold cyan]🚀 Lanzando {platform['emoji']} {platform['name']}...[/bold cyan]", spinner="dots"):
            pass
        console.print(f"[bold cyan]🚀 Lanzando {platform['emoji']} {platform['name']}...[/bold cyan]\n")
    else:
        print(f"\n{Colors.CYAN}🚀 Lanzando {platform['emoji']} {platform['name']}...{Colors.ENDC}\n")
    
    # Ejecutar el tools.py de la plataforma con las variables de entorno
    try:
        subprocess.run([HOST_PYTHON, str(tools_path)], check=False, env=env)
    except KeyboardInterrupt:
        if RICH_AVAILABLE and console:
            console.print("\n[yellow]↩️  Regresando al menú principal...[/yellow]")
        else:
            print(f"\n{Colors.WARNING}Regresando al menú principal...{Colors.ENDC}")
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"\n[red]❌ Error al ejecutar: {e}[/red]")
        else:
            print(f"\n{Colors.FAIL}❌ Error al ejecutar: {e}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")


def show_config_details():
    """Muestra detalles de la configuración actual."""
    config = load_config()
    
    if RICH_AVAILABLE and console:
        if not config:
            console.print(Panel(
                "[yellow]⚠️ No se encontró config.json[/yellow]\n\n"
                f"[white]Para configurar el toolbox:[/white]\n"
                f"  1. Copia [cyan]config.json.template[/cyan] a [cyan]config.json[/cyan]\n"
                f"  2. Edita config.json con tus credenciales\n"
                f"  3. Reinicia el launcher\n\n"
                f"[dim]Ruta: {CONFIG_FILE}[/dim]",
                title="📋 Configuración",
                border_style="yellow",
                expand=False
            ))
        else:
            # Mostrar configuración por plataforma
            table = Table(title="📋 Configuración Actual", box=ROUNDED, border_style="cyan")
            table.add_column("Plataforma", style="bold white")
            table.add_column("Estado", justify="center")
            table.add_column("Detalles", style="dim")
            
            # GCP
            gcp = config.get("gcp", {})
            gcp_status = "✅" if is_platform_configured("1") else "⚠️"
            gcp_details = f"Project: {gcp.get('project_id', 'N/A')[:30]}"
            table.add_row("☁️ GCP", f"[green]{gcp_status}[/]" if gcp_status == "✅" else f"[yellow]{gcp_status}[/]", gcp_details)
            
            # AZDO
            azdo = config.get("azdo", {})
            azdo_status = "✅" if is_platform_configured("2") else "⚠️"
            org_url = azdo.get("organization_url", "N/A")
            azdo_details = f"Org: {org_url.replace('https://dev.azure.com/', '')[:25]}"
            table.add_row("🔷 Azure DevOps", f"[green]{azdo_status}[/]" if azdo_status == "✅" else f"[yellow]{azdo_status}[/]", azdo_details)
            
            # AWS
            aws = config.get("aws", {})
            aws_status = "✅" if is_platform_configured("3") else "⚠️"
            aws_details = f"Profile: {aws.get('profile', 'N/A')} | Region: {aws.get('region', 'N/A')}"
            table.add_row("🟠 AWS", f"[green]{aws_status}[/]" if aws_status == "✅" else f"[yellow]{aws_status}[/]", aws_details)
            
            console.print(table)
            console.print(f"\n[dim]Archivo de configuración: {CONFIG_FILE}[/dim]")
    else:
        if not config:
            print(f"\n{Colors.WARNING}⚠️ No se encontró config.json{Colors.ENDC}")
            print(f"Copia config.json.template a config.json y configura tus credenciales.")
        else:
            print(f"\n{Colors.BOLD}📋 Configuración Actual{Colors.ENDC}")
            for name, key in [("GCP", "gcp"), ("AZDO", "azdo"), ("AWS", "aws")]:
                plat = config.get(key, {})
                status = "✅" if plat else "❌"
                print(f"  {status} {name}")
    
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
        info_text.append("22 herramientas SRE\n", style="white")
        info_text.append("  • Azure DevOps: ", style="blue")
        info_text.append("PRs, políticas, releases\n", style="white")
        info_text.append("  • AWS: ", style="yellow")
        info_text.append("13 herramientas DevSecOps\n", style="white")
        
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
            print_config_status()
            console.print() if RICH_AVAILABLE and console else print()
            print_menu()
            
            # Tip
            if RICH_AVAILABLE and console:
                console.print("[dim]💡 Tip: 'info' = información | 'config' = estado de configuración[/dim]\n")
                choice = Prompt.ask("[bold cyan]Seleccione una opción[/]", default="Q").strip().upper()
            else:
                choice = input(f"{Colors.BOLD}Seleccione una opción: {Colors.ENDC}").strip().upper()
            
            if choice == "INFO":
                show_info()
            elif choice == "CONFIG":
                show_config_details()
            elif choice in PLATFORMS:
                launch_platform(choice)
            else:
                if RICH_AVAILABLE and console:
                    console.print("[red]❌ Opción no válida. Intente de nuevo.[/red]")
                else:
                    print(f"\n{Colors.FAIL}Opción no válida. Por favor, intente de nuevo.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                
        except KeyboardInterrupt:
            if RICH_AVAILABLE and console:
                console.print("\n[bold yellow]👋 Saliendo...[/bold yellow]")
            else:
                print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
            sys.exit(0)
        except Exception as e:
            if RICH_AVAILABLE and console:
                console.print(f"\n[red]❌ Error inesperado: {e}[/red]")
            else:
                print(f"\n{Colors.FAIL}Error inesperado: {e}{Colors.ENDC}")
            input("\nPresione Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Saliendo...{Colors.ENDC}")
        sys.exit(0)
