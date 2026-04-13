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
__version__     = "1.3.0"
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
    "release":    {"name": "Release Pipelines",  "emoji": "🚀", "color": "green"},
    "drift":      {"name": "Drift Analysis",     "emoji": "🔍", "color": "magenta"},
    "validation": {"name": "Validación",         "emoji": "✅", "color": "blue"},
    "security":   {"name": "Seguridad",          "emoji": "🛡️", "color": "red"},
    "system":     {"name": "Sistema",            "emoji": "⚙️",  "color": "white"},
}

GROUP_ORDER = ["pr", "policy", "release", "drift", "validation", "security", "system"]

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
    "A": {
        "name":        "Ejecutar Todos",
        "description": "Ejecuta todas las herramientas con la misma configuración (sin Deep Dive)",
        "auto_tools":  ["1", "2", "3", "4"],
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


def get_installed_requirements() -> set:
    if not INSTALLED_MARKER.exists():
        return set()
    try:
        with open(INSTALLED_MARKER, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except Exception:
        return set()


def mark_requirements_installed(req_path: str):
    installed = get_installed_requirements()
    installed.add(req_path)
    try:
        INSTALLED_MARKER.parent.mkdir(parents=True, exist_ok=True)
        with open(INSTALLED_MARKER, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(installed)))
    except Exception:
        pass


def install_requirements(python_exec: str, force: bool = False) -> bool:
    req_file = BASE_DIR / REQUIREMENTS_FILE
    if not req_file.exists():
        print(f"{Colors.WARNING}Advertencia: No se encontró {req_file}{Colors.ENDC}")
        return True

    if not force and REQUIREMENTS_FILE in get_installed_requirements():
        print(f"{Colors.GREEN}Dependencias ya instaladas (usando caché).{Colors.ENDC}")
        return True

    print(f"\n{Colors.CYAN}Instalando dependencias de {req_file} en el venv...{Colors.ENDC}")
    try:
        subprocess.check_call([python_exec, "-m", "pip", "install", "-r", str(req_file)])
        print(f"{Colors.GREEN}Dependencias instaladas correctamente.{Colors.ENDC}")
        mark_requirements_installed(REQUIREMENTS_FILE)
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
                if t.get("group") == group_key and k not in ("Q", "A")]
        keys.sort(key=_menu_sort_key)
        ordered.extend(keys)
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

    cmd = [venv_python, str(script_path)] + extra

    if RICH_AVAILABLE and console:
        console.print(f"\n[dim]▶ Ejecutando:[/] [cyan]{' '.join(cmd[:4])} ...[/cyan]\n")
    else:
        print(f"\n{Colors.CYAN}Ejecutando: {' '.join(cmd[:4])} ...{Colors.ENDC}\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al ejecutar la herramienta: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")

    input("\nPresione Enter para continuar...")


# ═══════════════════════════════════════════════════════════════════════════════
# EJECUTAR TODOS
# ═══════════════════════════════════════════════════════════════════════════════
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

        try:
            subprocess.run(cmd, check=True)
            results.append((tool["name"], "OK", "Completado"))
        except subprocess.CalledProcessError as e:
            results.append((tool["name"], "ERROR", str(e)))
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")
            break

    elapsed = time_module.time() - start
    _print_execution_summary(results, elapsed)
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

            if choice_norm == "A":
                run_all_tools()
            elif choice_norm in TOOLS:
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
