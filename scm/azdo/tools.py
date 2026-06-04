#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Tools Launcher

Interfaz de menú unificado para ejecutar las herramientas de Azure DevOps
desde un solo lugar.

- Crea (si no existe) un entorno virtual en BASE_DIR/.venv
- Instala el requirements.txt compartido dentro de ese venv
- Carga PAT y configuración desde config.json si existe
- Ejecuta las herramientas usando el Python del venv

Uso:
    python tools.py
"""

import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import time as time_module
from pathlib import Path
from typing import Dict, List, Optional

try:
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.box import ROUNDED, DOUBLE_EDGE
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA
# ═══════════════════════════════════════════════════════════════════════════════
__version__     = "1.3.2"
__author__      = "Harold Adrian"
__description__ = "Launcher unificado de herramientas Azure DevOps"

console = Console() if RICH_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# RUTAS
# ═══════════════════════════════════════════════════════════════════════════════
BASE_DIR          = Path(__file__).parent.absolute()
HOST_PYTHON       = sys.executable or "python"
VENV_DIR          = BASE_DIR / ".venv"
INSTALLED_MARKER  = VENV_DIR / ".installed_requirements"
CONFIG_FILE       = BASE_DIR / "config.json"
REQUIREMENTS_FILE = "requirements.txt"

# ═══════════════════════════════════════════════════════════════════════════════
# COLORES FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    HEADER    = '\033[95m'
    BLUE      = '\033[94m'
    CYAN      = '\033[96m'
    GREEN     = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'

# ═══════════════════════════════════════════════════════════════════════════════
# GRUPOS DE HERRAMIENTAS
# ═══════════════════════════════════════════════════════════════════════════════
TOOL_GROUPS = {
    "pr":         {"name": "Pull Requests",      "emoji": "📬", "color": "cyan"},
    "policy":     {"name": "Políticas de Rama",  "emoji": "🔒", "color": "yellow"},
    "release":    {"name": "Releases & CD",      "emoji": "🚀", "color": "green"},
    "drift":      {"name": "Drift & Cambios",    "emoji": "🌪️", "color": "magenta"},
    "validation": {"name": "Validación",         "emoji": "✅", "color": "blue"},
    "security":   {"name": "Seguridad",          "emoji": "🛡️", "color": "red"},
    "inventory":  {"name": "Inventario",         "emoji": "📋", "color": "bright_white"},
    "health":     {"name": "Health Score",       "emoji": "📊", "color": "bright_cyan"},
    "quality":    {"name": "Calidad Deploy",     "emoji": "🎯", "color": "pink"},
    "system":     {"name": "Sistema",            "emoji": "⚙️", "color": "white"},
}

GROUP_ORDER = ["pr", "policy", "release", "drift", "validation", "security", "inventory", "health", "quality", "system"]

# ═══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS DISPONIBLES
# ═══════════════════════════════════════════════════════════════════════════════
TOOLS: Dict = {
    "1": {
        "name":        "PR Master Checker",
        "description": "Lista PRs hacia master/main con pipeline CD asociado y stage 'validador'",
        "path":        "azdo_pr_master_checker.py",
        "args":        ["--pat", "--org", "--project", "--repo", "--branch",
                        "--status", "--stage-name", "--output"],
        "group":       "pr",
        "status":      "ready",
    },
    "1b": {
        "name":        "PR Pipeline Analyzer",
        "description": "Analiza PRs de múltiples ramas y cruza con CD pipelines y releases",
        "path":        "azdo_pr_pipeline_analyzer.py",
        "args":        ["--pat", "--org", "--project", "--branches", "--status",
                        "--threads", "--output", "--list-cds", "--debug"],
        "group":       "pr",
        "status":      "ready",
    },
    "2": {
        "name":        "Branch Policy Checker",
        "description": "Audita políticas de rama (master/main, QA, develop) por repositorio",
        "path":        "azdo_branch_policy_checker.py",
        "args":        ["--pat", "--org", "--project", "--repo", "--output"],
        "group":       "policy",
        "status":      "ready",
    },
    "2b": {
        "name":        "Branch Lock Checker",
        "description": "Lista todas las ramas con lock (isLocked) por repositorio — Repo | Rama | Bloqueado por",
        "path":        "azdo_branch_lock_checker.py",
        "args":        ["--pat", "--org", "--project", "--repo", "--workers", "--output"],
        "group":       "policy",
        "status":      "ready",
    },
    "3": {
        "name":        "Release CD Health",
        "description": "Score de salud de Release Pipelines CD: recencia + estabilidad + consistencia",
        "path":        "azdo_release_cd_health.py",
        "args":        ["--pat", "--org", "--project", "--repo", "--sort",
                        "--diagram", "--output"],
        "group":       "release",
        "status":      "ready",
    },
    "4": {
        "name":        "Pipeline Drift Analyzer",
        "description": "Detecta drift entre pipeline actual y snapshot del último release (stages/vars/approvals/tasks)",
        "path":        "azdo_pipeline_drift.py",
        "args":        ["--pat", "--org", "--project", "--repo", "--severity",
                        "--sort", "--output"],
        "group":       "drift",
        "status":      "ready",
    },
    "5": {
        "name":        "Release Deep Dive",
        "description": "Análisis profundo de un Release Definition por ID: PRs + Políticas + CD Health + Drift",
        "path":        "azdo_release_deep_dive.py",
        "args":        ["--pat", "--org", "--project", "--release-id", "--branch",
                        "--stage-name", "--output"],
        "group":       "release",
        "status":      "ready",
    },
    "6": {
        "name":        "Task Validator",
        "description": "Validación DevSecOps: imágenes Docker, rollback, credenciales GIT, ConfigMap vs Repo",
        "path":        "azdo_task_validator.py",
        "args":        ["--pat", "--org", "--project", "--release-id",
                        "--image-actual", "--image-nueva", "--gcp-project",
                        "--group-id", "--artifact-name", "--namespace", "--output"],
        "group":       "validation",
        "status":      "ready",
    },
    "7": {
        "name":        "Pipeline Logs Scanner",
        "description": "Escanea logs de pipelines CI buscando términos de vulnerabilidades (axios, plain-crypto-js)",
        "path":        "azdo_scan_pipeline_logs.py",
        "args":        ["--pat", "--org", "--project", "--search-terms", "--top-runs",
                        "--threads", "--output"],
        "group":       "security",
        "status":      "ready",
    },
    "8": {
        "name":        "Repo Vulnerabilities Scanner",
        "description": "Escanea package.json en repositorios buscando dependencias vulnerables",
        "path":        "azdo_scan_repos_vulnerabilities.py",
        "args":        ["--pat", "--org", "--project", "--branches", "--targets",
                        "--repo", "--output"],
        "group":       "security",
        "status":      "ready",
    },
    "9": {
        "name":        "CICD Inventory",
        "description": "Inventario completo de repos, CI pipelines (YAML) y CD pipelines (classic releases) con relación Repo ↔ CI ↔ CD",
        "path":        "cicd_inventory.py",
        "args":        ["--pat", "--org", "--project", "--limit", "--output"],
        "json_output": True,
        "group":       "inventory",
        "status":      "ready",
    },
    "10": {
        "name":        "GKE Pipelines Inventory",
        "description": "Inventario de Release Definitions CD que contienen 'GKE' con detalle de stages y último estado",
        "path":        "cicd_inventory_gke_pipelines.py",
        "args":        ["--pat", "--org", "--project", "--keyword", "--output"],
        "json_output": True,
        "group":       "inventory",
        "status":      "ready",
    },
    "11": {
        "name":        "Pending Approvals",
        "description": "Releases con aprobaciones pendientes + estado del stage 'Validador'",
        "path":        "cicd_inventory_pending_approvals.py",
        "args":        ["--pat", "--org", "--project", "--output"],
        "json_output": True,
        "group":       "inventory",
        "status":      "ready",
    },
    "12": {
        "name":        "Branches Created",
        "description": "Ramas creadas desde fecha específica usando Pushes API (concurrente)",
        "path":        "cicd_inventory_branches_created.py",
        "args":        ["--pat", "--org", "--project", "--since", "--workers", "--output"],
        "group":       "inventory",
        "status":      "ready",
    },
    "13": {
        "name":        "Hotfix Branches Inventory",
        "description": "Inventario de ramas hotfix con creador, fecha de creación y actividad del repo",
        "path":        "cicd_inventory_hotfix_branches.py",
        "args":        ["--pat", "--org", "--project", "--pattern", "--workers", "--output"],
        "json_output": True,
        "group":       "inventory",
        "status":      "ready",
    },
    "14": {
        "name":        "CI Detailed Inventory",
        "description": "[Flujo] Inventario detallado de pipelines CI. Verifica cache previo (ci_raw.json < 24h) para skip APIs. Genera Excel + CSV + JSON cache.",
        "path":        "cicd_inventory_ci_detailed.py",
        "args":        ["--pat", "--org", "--project", "--workers", "--output", "--force-refresh", "--use-cache-only"],
        "group":       "inventory",
        "status":      "ready",
    },
    "15": {
        "name":        "CD Detailed Inventory",
        "description": "[Flujo] Inventario detallado de pipelines CD (Release Definitions). Verifica cache previo (cd_raw.json < 24h) para skip APIs. Genera Excel + CSV + JSON cache.",
        "path":        "cicd_inventory_cd_detailed.py",
        "args":        ["--pat", "--org", "--project", "--workers", "--output", "--force-refresh", "--use-cache-only"],
        "group":       "inventory",
        "status":      "ready",
    },
    "16": {
        "name":        "Pipeline Health Score",
        "description": "[Flujo / Orquestador] Reporte de salud con scoring DORA/SRE en 5 dimensiones. Genera 1 Excel con 3 pestañas (CI + CD + Health). Lee cache CI/CD si existe < 24h, consulta APIs solo si es necesario.",
        "path":        "cicd_inventory_health_score.py",
        "args":        ["--pat", "--org", "--project", "--workers", "--output", "--force-refresh", "--offline", "--skip-incremental", "--run-inventory"],
        "group":       "health",
        "status":      "ready",
    },
    "17": {
        "name":        "Prod Deploy Credenciales Git",
        "description": "[Flujo] Rastrea último despliegue exitoso a Producción por pipeline CD. Requiere cache CD previo. Genera Excel + CSV + JSON cache con deadline de vigencia, commit SHA y build ID.",
        "path":        "cicd_inventory_prod_deploy.py",
        "args":        ["--pat", "--org", "--project", "--deadline", "--workers", "--output", "--force-refresh"],
        "group":       "health",
        "status":      "ready",
    },
    "18": {
        "name":        "Pipeline Status",
        "description": "Reporte consolidado CI+CD: totales, deprecados, última actualización, estado (enabled/disabled/paused/inactivo)",
        "path":        "cicd_pipeline_status.py",
        "args":        ["--pat", "--org", "--project", "--workers", "--inactive-days", "--type", "--only-deprecated", "--output", "--force-refresh"],
        "group":       "health",
        "status":      "ready",
    },
    "19": {
        "name":        "Properties Branch Diff",
        "description": "Compara la configuración de un componente (carpeta) entre dos ramas de un repositorio de propiedades. Detecta diferencias de configuración que puedan impactar un despliegue productivo. Exit 0=OK / 1=HIGH / 2=CRITICAL.",
        "path":        "azdo_repo_properties_branch_diff.py",
        "args":        ["--pat", "--org", "--project", "--repo", "--component",
                        "--source", "--target", "--context", "--severity",
                        "--only-diff", "--no-content", "--output"],
        "group":       "quality",
        "status":      "ready",
    },
    "20": {
        "name":        "Repo Branch Diff",
        "description": "[Informe Ejecutivo] Analiza el impacto de cambios entre dos ramas de cualquier repositorio. Clasifica archivos por riesgo (CRITICAL/HIGH/MEDIUM/LOW): CI/CD, seguridad, K8s, build, BD, código, tests. Score 0-100, commits, autores y recomendaciones automáticas. Exit 0=OK / 1=HIGH / 2=CRITICAL.",
        "path":        "azdo_repo_branch_diff.py",
        "args":        ["--pat", "--org", "--project", "--repo",
                        "--source", "--target", "--top-files", "--top-commits",
                        "--no-commits", "--no-authors", "--severity", "--output"],
        "group":       "quality",
        "status":      "ready",
    },
    "A": {
        "name":        "Ejecutar Todos",
        "description": "Ejecuta todas las herramientas con la misma configuración (sin Deep Dive)",
        "auto_tools":  ["1", "2", "2b", "3", "4", "7", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
        "group":       "system",
        "status":      "ready",
    },
    "B": {
        "name":        "Ejecutar Todo + JSON",
        "description": "Ejecuta TODAS las herramientas en secuencia forzando salida JSON en outcome/. Ideal para alimentar el dashboard.",
        "auto_tools":  ["1", "2", "2b", "3", "4", "7", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
        "group":       "system",
        "status":      "ready",
    },
    "Q": {
        "name":        "Salir",
        "description": "Salir del menú",
        "group":       "system",
        "status":      "exit",
    },
}

STATUS_INDICATORS = {
    "ready":   ("🟢", "green",  "Listo"),
    "warning": ("🟡", "yellow", "Advertencia"),
    "error":   ("🔴", "red",    "Error"),
    "running": ("🔵", "blue",   "Ejecutando"),
    "exit":    ("🚪", "white",  "Salir"),
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG.JSON
# ═══════════════════════════════════════════════════════════════════════════════
def load_config() -> Dict:
    """Carga config.json si existe. Retorna dict vacío si no."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def config_get(cfg: Dict, *keys, default=""):
    """Acceso seguro a claves anidadas del config."""
    val = cfg
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
    return val if val is not None else default


# ═══════════════════════════════════════════════════════════════════════════════
# VENV
# ═══════════════════════════════════════════════════════════════════════════════
def get_venv_python() -> Optional[str]:
    venv_python = (
        VENV_DIR / "Scripts" / "python.exe"
        if platform.system() == "Windows"
        else VENV_DIR / "bin" / "python"
    )
    if venv_python.exists():
        return str(venv_python)

    print(f"{Colors.CYAN}Creando entorno virtual en {VENV_DIR}...{Colors.ENDC}")
    try:
        subprocess.check_call([HOST_PYTHON, "-m", "venv", str(VENV_DIR)])
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al crear el entorno virtual: {e}{Colors.ENDC}")
        return None

    if not venv_python.exists():
        print(f"{Colors.FAIL}No se encontró Python en el venv: {venv_python}{Colors.ENDC}")
        return None

    print(f"{Colors.GREEN}Entorno virtual creado correctamente.{Colors.ENDC}")
    return str(venv_python)


def _req_hash(req_file: Path) -> str:
    """MD5 del contenido de requirements.txt para detectar cambios."""
    try:
        return hashlib.md5(req_file.read_bytes()).hexdigest()
    except Exception:
        return ""


def get_installed_marker() -> str:
    """Retorna el token almacenado en el marker o cadena vacía."""
    if not INSTALLED_MARKER.exists():
        return ""
    try:
        return INSTALLED_MARKER.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def mark_requirements_installed(req_file: Path):
    """Guarda 'filename:hash' en el marker para validación futura."""
    token = f"{REQUIREMENTS_FILE}:{_req_hash(req_file)}"
    try:
        INSTALLED_MARKER.parent.mkdir(parents=True, exist_ok=True)
        INSTALLED_MARKER.write_text(token, encoding="utf-8")
    except Exception:
        pass


def install_requirements(python_exec: str, force: bool = False) -> bool:
    req_file = BASE_DIR / REQUIREMENTS_FILE
    if not req_file.exists():
        print(f"{Colors.WARNING}Advertencia: No se encontró {req_file}{Colors.ENDC}")
        return True

    current_token = f"{REQUIREMENTS_FILE}:{_req_hash(req_file)}"
    cached_token  = get_installed_marker()

    if not force and current_token == cached_token:
        print(f"{Colors.GREEN}Dependencias ya instaladas (usando caché).{Colors.ENDC}")
        return True

    if cached_token and current_token != cached_token:
        print(f"{Colors.WARNING}requirements.txt actualizado — reinstalando dependencias...{Colors.ENDC}")
    else:
        print(f"\n{Colors.CYAN}Instalando dependencias de {req_file} en el venv...{Colors.ENDC}")

    try:
        subprocess.check_call([python_exec, "-m", "pip", "install", "-r", str(req_file)])
        print(f"{Colors.GREEN}Dependencias instaladas correctamente.{Colors.ENDC}")
        mark_requirements_installed(req_file)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al instalar dependencias: {e}{Colors.ENDC}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")


def prompt(label: str, default: str = "", secret: bool = False) -> str:
    """Solicita un valor al usuario con default opcional."""
    masked = "****" if (secret and default) else default
    suffix = f" [{Colors.CYAN}{masked}{Colors.ENDC}]" if default else ""
    print(f"{Colors.BOLD}{label}{suffix}:{Colors.ENDC} ", end="")
    value = input().strip()
    if not value and default:
        value = default
        if not secret:
            print(f"{Colors.GREEN}Usando: {value}{Colors.ENDC}")
        else:
            print(f"{Colors.GREEN}Usando valor del config.json{Colors.ENDC}")
    return value


def print_header():
    clear_screen()
    if RICH_AVAILABLE and console:
        console.print(Panel(
            Align.center(Text.assemble(
                Text("🔷  Azure DevOps Tools  🔷\n", style="bold cyan"),
                Text(f"v{__version__}  |  by {__author__}\n", style="bold green"),
                Text(__description__, style="dim white"),
            )),
            box=DOUBLE_EDGE,
            border_style="cyan",
            padding=(1, 4),
            expand=False,
        ))
        _print_config_status()
        console.print()
    else:
        print(f"{Colors.HEADER}{'='*60}")
        print(f"{'AZURE DEVOPS TOOLS':^60}")
        print(f"v{__version__} | by {__author__}".center(60))
        print(f"{'='*60}{Colors.ENDC}")
        _print_config_status_fallback()
        print()


def _print_config_status_fallback():
    """Versión plain-text (sin Rich) del estado de config.json."""
    cfg = load_config()
    if not cfg:
        print(f"{Colors.WARNING}⚠  config.json no encontrado — "
              f"se pedirá PAT/org/proyecto en cada ejecución.{Colors.ENDC}")
        print(f"{Colors.CYAN}   (copia config.json.template → config.json){Colors.ENDC}")
        return
    pat   = config_get(cfg, "organization", "pat")
    org   = config_get(cfg, "organization", "url")
    proj  = config_get(cfg, "organization", "project")
    valid = pat and not pat.startswith("<")
    pat_display = (f"{Colors.GREEN}✅ Configurado{Colors.ENDC}"
                   if valid else f"{Colors.FAIL}❌ Sin configurar{Colors.ENDC}")
    print(f"📄 config.json:  PAT: {pat_display}  "
          f"| Org: {Colors.CYAN}{org}{Colors.ENDC}  "
          f"| Proyecto: {Colors.CYAN}{proj}{Colors.ENDC}")


def _print_config_status():
    """Muestra si config.json existe y si el PAT está configurado."""
    cfg = load_config()
    if not cfg:
        console.print(
            "[yellow]⚠️  config.json no encontrado — "
            "se pedirá PAT/org/proyecto en cada ejecución.[/]  "
            "[dim](copia config.json.template → config.json)[/dim]"
        )
        return
    pat   = config_get(cfg, "organization", "pat")
    org   = config_get(cfg, "organization", "url")
    proj  = config_get(cfg, "organization", "project")
    valid = pat and not pat.startswith("<")
    pat_display = "[green]✅ Configurado[/green]" if valid else "[red]❌ Sin configurar[/red]"
    console.print(
        f"[dim]📄 config.json:[/dim]  PAT: {pat_display}  "
        f"[dim]|  Org: [cyan]{org}[/cyan]  |  Proyecto: [cyan]{proj}[/cyan][/dim]"
    )


def _menu_sort_key(k: str):
    if k.isdigit():
        return (0, int(k), 0)
    # Handle keys like "1b", "2a", etc.
    base = ""
    suffix = ""
    for c in k:
        if c.isdigit():
            base += c
        else:
            suffix += c
    if base:
        return (0, int(base), ord(suffix) if suffix else 0)
    return (1, 0, ord(k))


def get_menu_order() -> List[str]:
    ordered: List[str] = []
    for group_key in GROUP_ORDER:
        keys = [k for k, t in TOOLS.items()
                if t.get("group") == group_key and k not in ("Q", "A", "B")]
        keys.sort(key=_menu_sort_key)
        ordered.extend(keys)
    if "B" in TOOLS:
        ordered.append("B")
    if "A" in TOOLS:
        ordered.append("A")
    if "Q" in TOOLS:
        ordered.append("Q")
    return ordered


def print_menu():
    if RICH_AVAILABLE and console:
        t = Table(
            title="🛠️  Menú Principal",
            title_style="bold white",
            box=ROUNDED,
            header_style="bold cyan",
            border_style="blue",
            show_lines=False,
            expand=False,
        )
        t.add_column("#",            justify="center", style="bold white", width=4)
        t.add_column("Grupo",        justify="left",   width=20)
        t.add_column("Herramienta",  justify="left",   style="white", min_width=26)
        t.add_column("Descripción",  justify="left",   style="dim",   min_width=46)

        for key in get_menu_order():
            tool       = TOOLS[key]
            group_key  = tool.get("group", "system")
            group_info = TOOL_GROUPS.get(group_key, TOOL_GROUPS["system"])
            group_text = f"{group_info['emoji']} {group_info['name']}"

            if key == "Q":
                ks, ns = "bold yellow", "yellow"
            elif key == "B":
                ks, ns = "bold yellow", "yellow"
            elif key == "A":
                ks, ns = "bold magenta", "magenta"
            else:
                ks, ns = "bold cyan", "white"

            t.add_row(
                f"[{ks}]{key}[/{ks}]",
                f"[{group_info['color']}]{group_text}[/{group_info['color']}]",
                f"[{ns}]{tool['name']}[/{ns}]",
                tool.get("description", ""),
            )

        console.print(t)
        console.print()
    else:
        print(f"{Colors.BOLD}Menú Principal:{Colors.ENDC}\n")
        for key in get_menu_order():
            tool       = TOOLS[key]
            group_info = TOOL_GROUPS.get(tool.get("group", "system"), {})
            emoji      = group_info.get("emoji", "🔧")
            if key == "Q":
                print(f"  {Colors.WARNING}[{key}]{Colors.ENDC} {tool['name']}")
            elif key == "A":
                print(f"  {Colors.HEADER}[{key}]{Colors.ENDC} {emoji} {tool['name']} — {tool['description']}")
            else:
                print(f"  {Colors.BLUE}[{key}]{Colors.ENDC} {emoji} [{group_info.get('name','')}] "
                      f"{tool['name']} — {tool['description']}")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT DE PARÁMETROS COMUNES (PAT / ORG / PROYECTO)
# ═══════════════════════════════════════════════════════════════════════════════
def ask_common_params(cfg: Dict) -> Optional[Dict]:
    """
    Solicita PAT, org URL y proyecto. Usa config.json como defaults.
    Retorna dict con los valores o None si el usuario cancela.
    """
    def_pat  = config_get(cfg, "organization", "pat")
    def_org  = config_get(cfg, "organization", "url",     default="https://dev.azure.com/Coppel-Retail")
    def_proj = config_get(cfg, "organization", "project", default="Compras.RMI")

    print()
    pat = prompt("PAT (Personal Access Token)", default=def_pat, secret=True)
    if not pat or pat.startswith("<"):
        print(f"{Colors.FAIL}Se requiere un PAT válido.{Colors.ENDC}")
        return None

    org  = prompt("Organización URL", default=def_org)
    proj = prompt("Proyecto",         default=def_proj)
    return {"pat": pat, "org": org, "project": proj}


# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN DE HERRAMIENTA
# ═══════════════════════════════════════════════════════════════════════════════

_PLATFORM = "AZDO"

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
    if tool_key not in TOOLS:
        print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return

    tool = TOOLS[tool_key]

    if tool_key == "Q":
        print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
        sys.exit(0)

    if tool_key == "A":
        run_all_tools()
        return

    if tool_key == "B":
        run_all_json()
        return

    if RICH_AVAILABLE and console:
        group_info = TOOL_GROUPS.get(tool.get("group", "system"), {})
        console.print()
        console.print(Panel(
            f"{group_info.get('emoji', '🔧')} [bold white]{tool['name']}[/]\n"
            f"[dim]{tool['description']}[/]",
            border_style="cyan", expand=False,
        ))
    else:
        print(f"\n{Colors.HEADER}=== {tool['name']} ==={Colors.ENDC}")
        print(f"{tool['description']}\n")

    venv_python = get_venv_python()
    if not venv_python:
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    if not install_requirements(venv_python):
        print(f"{Colors.FAIL}No se pudieron instalar las dependencias.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    script_path = BASE_DIR / tool["path"]
    if not script_path.exists():
        print(f"{Colors.FAIL}Script no encontrado: {script_path}{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    cfg    = load_config()
    params = ask_common_params(cfg)
    if not params:
        input("\nPresione Enter para continuar...")
        return

    tool_args = tool.get("args", [])
    extra: List[str] = []

    # ── Parámetros comunes ────────────────────────────────────────────────────
    extra += ["--pat",     params["pat"]]
    extra += ["--org",     params["org"]]
    extra += ["--project", params["project"]]

    # ── Parámetros específicos por herramienta ────────────────────────────────
    if "--release-id" in tool_args:
        print(f"{Colors.BOLD}Release Definition ID (obligatorio):{Colors.ENDC} ", end="")
        val = input().strip()
        if not val or not val.isdigit():
            print(f"{Colors.RED}❌ El Release ID es obligatorio y debe ser un número entero.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        extra += ["--release-id", val]

    if "--repo" in tool_args:
        if tool_key == "19":
            cfg_props_repo = config_get(cfg, "tools", "properties_branch_diff", "repo", default="")
            val = prompt("Repositorio de propiedades (ej: retail-properties)", default=cfg_props_repo)
            if not val:
                print(f"{Colors.FAIL}Se requiere el nombre del repositorio de propiedades.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                return
            extra += ["--repo", val]
        else:
            val = prompt("Filtrar por repo/nombre (vacío = todos)", default="")
            if val:
                extra += ["--repo", val]

    if "--branch" in tool_args:
        cfg_branch = config_get(cfg, "tools", "pr_master_checker", "target_branch", default="master")
        val = prompt("Branch destino (develop/QA/release/*/master/all, comas para varias)", default=cfg_branch)
        extra += ["--branch", val]

    if "--branches" in tool_args:
        cfg_branches = config_get(cfg, "tools", "pr_pipeline_analyzer", "branches", default="master")
        print(f"{Colors.BOLD}Ramas destino (dev/QA/master/release/all, separadas por espacio) [{Colors.CYAN}{cfg_branches}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        val = input().strip() or cfg_branches
        extra += ["--branches"] + val.split()

    if "--status" in tool_args:
        cfg_status = config_get(cfg, "tools", "pr_master_checker", "pr_status", default="active")
        print(f"{Colors.BOLD}Estado de PRs (all/active/completed/abandoned) [{Colors.CYAN}{cfg_status}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        val = input().strip() or cfg_status
        extra += ["--status", val]

    if "--threads" in tool_args:
        cfg_threads = config_get(cfg, "tools", "pr_pipeline_analyzer", "threads", default="20")
        print(f"{Colors.BOLD}Hilos paralelos [{Colors.CYAN}{cfg_threads}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        val = input().strip() or cfg_threads
        extra += ["--threads", val]

    if "--list-cds" in tool_args:
        print(f"{Colors.BOLD}¿Listar todos los CDs disponibles? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--list-cds")

    if "--debug" in tool_args:
        print(f"{Colors.BOLD}¿Modo debug? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--debug")

    if "--stage-name" in tool_args:
        cfg_stage = config_get(cfg, "tools", "pr_master_checker", "stage_name", default="validador")
        val = prompt("Nombre del stage a buscar en CD", default=cfg_stage)
        extra += ["--stage-name", val]

    if "--sort" in tool_args:
        if tool_key == "3":
            cfg_sort = config_get(cfg, "tools", "release_cd_health", "sort", default="score")
            choices  = "score/name/date"
        else:
            cfg_sort = config_get(cfg, "tools", "pipeline_drift", "sort", default="severity")
            choices  = "severity/name/gap"
        print(f"{Colors.BOLD}Ordenar por ({choices}) [{Colors.CYAN}{cfg_sort}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        val = input().strip() or cfg_sort
        extra += ["--sort", val]

    if "--severity" in tool_args:
        cfg_sev = config_get(cfg, "tools", "pipeline_drift", "min_severity", default="")
        print(f"{Colors.BOLD}Severidad mínima (NONE/LOW/MEDIUM/HIGH/CRITICAL) "
              f"[{Colors.CYAN}{cfg_sev or 'todos'}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        val = input().strip().upper()
        if val in ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"):
            extra += ["--severity", val]

    if "--diagram" in tool_args:
        cfg_diag = config_get(cfg, "tools", "release_cd_health", "diagram", default=False)
        default_diag = "s" if cfg_diag else "n"
        print(f"{Colors.BOLD}¿Imprimir diagrama ASCII de stages? (s/n) [{Colors.CYAN}{default_diag}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        val = input().strip().lower() or default_diag
        if val == "s":
            extra.append("--diagram")

    if "--output" in tool_args:
        cfg_fmt = config_get(cfg, "defaults", "output_format", default="")
        print(f"{Colors.BOLD}¿Exportar resultado? (json/csv/excel/ninguno) "
              f"[{Colors.CYAN}{cfg_fmt or 'ninguno'}{Colors.ENDC}{Colors.BOLD}]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val in ("json", "csv", "excel"):
            extra += ["--output", val]
        elif not val and cfg_fmt in ("json", "csv", "excel"):
            extra += ["--output", cfg_fmt]

    if "--deadline" in tool_args:
        print(f"{Colors.BOLD}Fecha deadline (YYYY-MM-DD, obligatorio):{Colors.ENDC} ", end="")
        val = input().strip()
        if not val:
            print(f"{Colors.RED}❌ El deadline es obligatorio.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        extra += ["--deadline", val]

    if "--force-refresh" in tool_args:
        print(f"{Colors.BOLD}¿Forzar refresh (ignorar cache)? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--force-refresh")

    if "--offline" in tool_args:
        print(f"{Colors.BOLD}¿Modo offline (solo cache)? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--offline")

    if "--skip-incremental" in tool_args:
        print(f"{Colors.BOLD}¿Saltar datos incrementales? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--skip-incremental")

    if "--run-inventory" in tool_args:
        print(f"{Colors.BOLD}¿Ejecutar CI y CD inventory en paralelo antes de procesar? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--run-inventory")

    if "--use-cache-only" in tool_args:
        print(f"{Colors.BOLD}¿Usar solo cache (fallar si no existe)? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--use-cache-only")

    if "--source" in tool_args:
        if tool_key == "19":
            cfg_src = config_get(cfg, "tools", "properties_branch_diff", "source_branch", default="develop")
        else:
            cfg_src = config_get(cfg, "tools", "repo_branch_diff", "source_branch", default="develop")
        val = prompt("Rama ORIGEN (la que se desplegará, ej: release/release-1.6.0)", default=cfg_src)
        if val:
            extra += ["--source", val]

    if "--target" in tool_args:
        if tool_key == "19":
            cfg_tgt = config_get(cfg, "tools", "properties_branch_diff", "target_branch", default="master")
        else:
            cfg_tgt = config_get(cfg, "tools", "repo_branch_diff", "target_branch", default="master")
        val = prompt("Rama DESTINO (entorno receptor, ej: master)", default=cfg_tgt)
        if val:
            extra += ["--target", val]

    if "--component" in tool_args:
        if tool_key == "19":
            val = prompt("Nombre del servicio/componente a analizar (ej: ps-om-com-customerorder)", default="")
            if not val:
                print(f"{Colors.FAIL}Se requiere el nombre del servicio/componente.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                return
            extra += ["--component", val]
        else:
            val = prompt("Componente / carpeta dentro del repo (vacío = prompt interactivo en el script)", default="")
            if val:
                extra += ["--component", val]

    if "--context" in tool_args:
        print(f"{Colors.BOLD}Líneas de contexto en el diff [3]:{Colors.ENDC} ", end="")
        val = input().strip()
        if val and val.isdigit():
            extra += ["--context", val]

    if "--severity" in tool_args and "--source" in tool_args:  # solo para tool 19
        print(f"{Colors.BOLD}Filtrar severidad mínima (CRITICAL/HIGH/MEDIUM/LOW/NONE, vacío=todos):{Colors.ENDC} ", end="")
        val = input().strip().upper()
        if val in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"):
            extra += ["--severity", val]

    if "--only-diff" in tool_args:
        print(f"{Colors.BOLD}¿Mostrar solo archivos con diferencias? (s/n) [s]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val != "n":
            extra.append("--only-diff")

    if "--no-content" in tool_args:
        print(f"{Colors.BOLD}¿Omitir detalle de diff de contenido? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--no-content")

    if "--top-files" in tool_args:
        print(f"{Colors.BOLD}Máx. archivos en tabla (0=todos) [60]:{Colors.ENDC} ", end="")
        val = input().strip()
        if val and val.isdigit():
            extra += ["--top-files", val]

    if "--top-commits" in tool_args:
        print(f"{Colors.BOLD}Máx. commits en tabla [25]:{Colors.ENDC} ", end="")
        val = input().strip()
        if val and val.isdigit():
            extra += ["--top-commits", val]

    if "--no-commits" in tool_args:
        print(f"{Colors.BOLD}¿Omitir tabla de commits del informe? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--no-commits")

    if "--no-authors" in tool_args:
        print(f"{Colors.BOLD}¿Omitir estadísticas por autor? (s/n) [n]:{Colors.ENDC} ", end="")
        val = input().strip().lower()
        if val == "s":
            extra.append("--no-authors")

    cmd = [venv_python, str(script_path)] + extra

    if RICH_AVAILABLE and console:
        console.print(f"\n[dim]▶ Ejecutando:[/] [cyan]{' '.join(cmd[:4])} ...[/cyan]\n")
    else:
        print(f"\n{Colors.CYAN}Ejecutando: {' '.join(cmd[:4])} ...{Colors.ENDC}\n")

    log_command(cmd)
    try:
        result = subprocess.run(cmd)
        rc = result.returncode
        if rc not in (0, 1, 2):
            log_command(cmd, "ERROR")
            print(f"{Colors.FAIL}Error al ejecutar la herramienta (exit {rc}).{Colors.ENDC}")
        elif rc == 2:
            msg = "🚨 Quality gate: CRITICAL (exit 2)"
            (console.print(f"[bold red]{msg}[/]") if RICH_AVAILABLE and console
             else print(f"{Colors.FAIL}{msg}{Colors.ENDC}"))
        elif rc == 1:
            msg = "🔴 Quality gate: HIGH (exit 1)"
            (console.print(f"[yellow]{msg}[/]") if RICH_AVAILABLE and console
             else print(f"{Colors.WARNING}{msg}{Colors.ENDC}"))
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")

    input("\nPresione Enter para continuar...")


# ═══════════════════════════════════════════════════════════════════════════════
# EJECUTAR TODOS
# ═══════════════════════════════════════════════════════════════════════════════
# Tools que usan --output como selector de formato (json/csv/excel)
_JSON_FORMAT_TOOLS = {"1", "1b", "2", "2b", "3", "4", "7", "8", "9", "10", "11", "13", "17", "18"}
# Tools que usan --output como directorio; ya generan JSON cache automáticamente
_CACHE_JSON_TOOLS  = {"14", "15", "16"}


def run_all_tools():
    tool_config = TOOLS.get("A", {})
    auto_keys   = tool_config.get("auto_tools", [])

    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel(
            Align.center(Text("🚀 EJECUTAR TODAS LAS HERRAMIENTAS", style="bold cyan")),
            box=DOUBLE_EDGE, border_style="magenta",
        ))
        console.print()
        t = Table(box=ROUNDED, border_style="cyan", show_header=False)
        t.add_column("Herramienta", style="cyan")
        for k in auto_keys:
            tool  = TOOLS.get(k, {})
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            t.add_row(f"{group.get('emoji','🔧')}  {tool.get('name','')}")
        console.print(t)
        console.print()
    else:
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f"{'EJECUTAR TODAS LAS HERRAMIENTAS':^60}")
        print(f"{'='*60}{Colors.ENDC}\n")
        for k in auto_keys:
            print(f"  • {TOOLS.get(k, {}).get('name', '')}")

    cfg    = load_config()
    params = ask_common_params(cfg)
    if not params:
        input("\nPresione Enter para continuar...")
        return

    print(f"\n{Colors.BOLD}¿Exportar resultados? (json/csv/excel/ninguno) [json]:{Colors.ENDC} ", end="")
    output_fmt = input().strip().lower()
    if output_fmt not in ("json", "csv", "excel"):
        output_fmt = "json"

    print(f"\n{Colors.BOLD}¿Continuar? (s/n) [s]:{Colors.ENDC} ", end="")
    if input().strip().lower() == "n":
        print(f"{Colors.WARNING}Cancelado.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    venv_python = get_venv_python()
    if not venv_python:
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    if not install_requirements(venv_python):
        print(f"{Colors.FAIL}No se pudieron instalar las dependencias.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    results = []
    start   = time_module.time()

    for idx, key in enumerate(auto_keys, 1):
        tool        = TOOLS.get(key)
        script_path = BASE_DIR / tool["path"]

        if RICH_AVAILABLE and console:
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            console.print(
                f"\n[bold cyan]🔵 [{idx}/{len(auto_keys)}][/bold cyan] "
                f"{group.get('emoji','🔧')} [white]{tool['name']}[/white]"
            )
            console.print(f"[dim]{'─'*50}[/dim]")
        else:
            print(f"\n{Colors.HEADER}[{idx}/{len(auto_keys)}] {tool['name']}{Colors.ENDC}")
            print(f"{Colors.CYAN}{'-'*50}{Colors.ENDC}")

        if not script_path.exists():
            results.append((tool["name"], "ERROR", f"Script no encontrado: {script_path}"))
            continue

        cmd = [
            venv_python, str(script_path),
            "--pat",     params["pat"],
            "--org",     params["org"],
            "--project", params["project"],
            "--output",  output_fmt,
        ]

        log_command(cmd)
        try:
            result = subprocess.run(cmd)
            rc = result.returncode
            if rc in (0, 1, 2):
                label = {0: "OK", 1: "HIGH", 2: "CRITICAL"}.get(rc, "OK")
                results.append((tool["name"], "OK", label))
            else:
                log_command(cmd, "ERROR")
                results.append((tool["name"], "ERROR", f"exit {rc}"))
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")
            break

    elapsed = time_module.time() - start
    _print_execution_summary(results, elapsed)
    input("\nPresione Enter para continuar...")


def run_all_json():
    """Opción B: ejecuta todos los tools batcheables forzando --output json."""
    tool_config = TOOLS.get("B", {})
    auto_keys   = tool_config.get("auto_tools", [])

    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel(
            Align.center(Text("⚡ EJECUTAR TODO + JSON (Dashboard Feed)", style="bold yellow")),
            box=DOUBLE_EDGE, border_style="yellow",
        ))
        console.print()
        t = Table(box=ROUNDED, border_style="yellow", show_header=False)
        t.add_column("Herramienta", style="cyan")
        for k in auto_keys:
            tool  = TOOLS.get(k, {})
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            cache_note = " [dim](JSON cache)[/dim]" if k in _CACHE_JSON_TOOLS else ""
            t.add_row(f"{group.get('emoji','🔧')}  {tool.get('name','')}{cache_note}")
        console.print(t)
        console.print(f"[dim]Los JSON se generarán en [cyan]outcome/[/cyan][/dim]")
        console.print()
    else:
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f"{'EJECUTAR TODO + JSON':^60}")
        print(f"{'='*60}{Colors.ENDC}\n")
        for k in auto_keys:
            tool = TOOLS.get(k, {})
            note = " (JSON cache)" if k in _CACHE_JSON_TOOLS else ""
            print(f"  • {tool.get('name', '')}{note}")

    cfg    = load_config()
    params = ask_common_params(cfg)
    if not params:
        input("\nPresione Enter para continuar...")
        return

    print(f"\n{Colors.BOLD}¿Continuar? (s/n) [s]:{Colors.ENDC} ", end="")
    if input().strip().lower() == "n":
        print(f"{Colors.WARNING}Cancelado.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    venv_python = get_venv_python()
    if not venv_python:
        print(f"{Colors.FAIL}No se pudo preparar el entorno virtual.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    if not install_requirements(venv_python):
        print(f"{Colors.FAIL}No se pudieron instalar las dependencias.{Colors.ENDC}")
        input("\nPresione Enter para continuar...")
        return

    results = []
    start   = time_module.time()

    for idx, key in enumerate(auto_keys, 1):
        tool        = TOOLS.get(key)
        script_path = BASE_DIR / tool["path"]

        if RICH_AVAILABLE and console:
            group = TOOL_GROUPS.get(tool.get("group", "system"), {})
            console.print(
                f"\n[bold yellow]⚡ [{idx}/{len(auto_keys)}][/bold yellow] "
                f"{group.get('emoji','🔧')} [white]{tool['name']}[/white]"
                + (" [dim](JSON cache)[/dim]" if key in _CACHE_JSON_TOOLS else " [dim]→ json[/dim]")
            )
            console.print(f"[dim]{'─'*50}[/dim]")
        else:
            note = " (JSON cache)" if key in _CACHE_JSON_TOOLS else " → json"
            print(f"\n{Colors.HEADER}[{idx}/{len(auto_keys)}] {tool['name']}{note}{Colors.ENDC}")
            print(f"{Colors.CYAN}{'-'*50}{Colors.ENDC}")

        if not script_path.exists():
            results.append((tool["name"], "ERROR", f"Script no encontrado: {script_path}"))
            continue

        cmd = [
            venv_python, str(script_path),
            "--pat",     params["pat"],
            "--org",     params["org"],
            "--project", params["project"],
        ]
        if key in _JSON_FORMAT_TOOLS:
            cmd += ["--output", "json"]

        log_command(cmd)
        try:
            result = subprocess.run(cmd)
            rc = result.returncode
            if rc in (0, 1, 2):
                label = {0: "OK", 1: "HIGH", 2: "CRITICAL"}.get(rc, "OK")
                results.append((tool["name"], "OK", label))
            else:
                log_command(cmd, "ERROR")
                results.append((tool["name"], "ERROR", f"exit {rc}"))
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")
            break

    elapsed = time_module.time() - start
    _print_execution_summary(results, elapsed)

    if RICH_AVAILABLE and console:
        console.print(Panel(
            "💡 Todos los JSON están en [cyan]outcome/[/cyan]. "
            "Carga esa carpeta en el dashboard para visualizar.",
            box=ROUNDED, border_style="yellow",
        ))
    input("\nPresione Enter para continuar...")


def _print_execution_summary(results: list, elapsed: float):
    ok_count  = sum(1 for r in results if r[1] == "OK")
    err_count = sum(1 for r in results if r[1] == "ERROR")

    if RICH_AVAILABLE and console:
        t = Table(
            title="📊 Resumen de Ejecución",
            title_style="bold white",
            box=ROUNDED,
            header_style="bold cyan",
            border_style="green" if err_count == 0 else "yellow",
        )
        t.add_column("Estado",       justify="center", width=8)
        t.add_column("Herramienta",  justify="left",   style="white")
        t.add_column("Mensaje",      justify="left",   style="dim")

        for name, status, msg in results:
            if status == "OK":
                t.add_row("✅", f"[green]{name}[/green]", msg)
            else:
                t.add_row("❌", f"[red]{name}[/red]",     f"[red]{msg}[/red]")

        console.print()
        console.print(t)
        console.print()
        console.print(Panel(
            f"[bold green]✅ Exitosos: {ok_count}[/]  "
            f"[bold red]❌ Errores: {err_count}[/]  "
            f"[bold cyan]⏱️  Tiempo: {elapsed:.2f}s[/]",
            title="📈 Estadísticas",
            box=ROUNDED, border_style="blue",
        ))
        console.print(Panel(
            "💡 Los reportes se generaron en la carpeta [cyan]outcome/[/cyan].",
            box=ROUNDED, border_style="dim",
        ))
    else:
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f"{'RESUMEN':^60}")
        print(f"{'='*60}{Colors.ENDC}\n")
        for name, status, msg in results:
            icon = f"{Colors.GREEN}✅" if status == "OK" else f"{Colors.FAIL}❌"
            print(f"  {icon} {name}{Colors.ENDC}" + (f": {msg}" if status != "OK" else ""))
        print(f"\n{Colors.BOLD}Total: {ok_count} OK, {err_count} errores | "
              f"Tiempo: {elapsed:.2f}s{Colors.ENDC}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    while True:
        try:
            print_header()
            print_menu()

            if RICH_AVAILABLE and console:
                console.print(f"[bold]Seleccione una opción:[/] ", end="")
            else:
                print(f"{Colors.BOLD}Seleccione una opción:{Colors.ENDC} ", end="")

            choice = input().strip()

            # Normalizar: "A"/"Q" en mayúsculas, claves como "1b" en minúsculas
            choice_norm = choice.upper() if choice.isalpha() else choice.lower()

            if choice_norm in TOOLS:
                run_tool(choice_norm)
            else:
                print(f"\n{Colors.FAIL}Opción no válida.{Colors.ENDC}")
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
