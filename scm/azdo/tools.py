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
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    from rich.box import ROUNDED, DOUBLE_EDGE
    from rich.columns import Columns
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
# METADATA
# ═══════════════════════════════════════════════════════════════════════════════
__version__     = "1.3.4"
__author__      = "Harold Adrian"
__description__ = "Launcher unificado de herramientas Azure DevOps"

console = Console() if RICH_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# RUTAS
# ═══════════════════════════════════════════════════════════════════════════════
BASE_DIR          = Path(__file__).parent.absolute()
SCM_ROOT          = BASE_DIR.parent  # Raíz de scm/
HOST_PYTHON       = sys.executable or "python"
VENV_DIR          = BASE_DIR / ".venv"
INSTALLED_MARKER  = VENV_DIR / ".installed_requirements"
CONFIG_FILE       = SCM_ROOT / "config.json"  # Ahora apunta a scm/config.json
LAST_PARAMS_FILE  = BASE_DIR / ".last_params.json"  # Cache de últimos parámetros
REQUIREMENTS_FILE = "requirements.txt"
_PLATFORM         = platform.system()  # Windows, Linux, Darwin, etc.

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
    
    # Aliases para compatibilidad
    RED       = FAIL
    YELLOW    = WARNING

# ═══════════════════════════════════════════════════════════════════════════════
# GRUPOS DE HERRAMIENTAS
# ═══════════════════════════════════════════════════════════════════════════════
TOOL_GROUPS = {
    "pr":         {"name": "Pull Requests",      "emoji": "📬", "color": "cyan"},
    "policy":     {"name": "Políticas de Rama",  "emoji": "🔒", "color": "yellow"},
    "release":    {"name": "Releases & CD",      "emoji": "🚀", "color": "green"},
    "updatepipe": {"name": "Update Pipeline",    "emoji": "🆙", "color": "cyan"},
    "drift":      {"name": "Drift & Cambios",    "emoji": "🌪️", "color": "magenta"},
    "validation": {"name": "Validación",         "emoji": "✅", "color": "blue"},
    "security":   {"name": "Seguridad",          "emoji": "🛡️", "color": "red"},
    "inventory":  {"name": "Inventario",         "emoji": "📋", "color": "dark_gray"},
    "health":     {"name": "Health Score",       "emoji": "📊", "color": "bright_cyan"},
    "quality":    {"name": "Calidad Deploy",     "emoji": "🎯", "color": "pink"},
    "system":     {"name": "Sistema",            "emoji": "⚙️", "color": "white"},
}

GROUP_ORDER = ["pr", "policy", "release", "updatepipe", "drift", "validation", "security", "inventory", "health", "quality", "system"]

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
        "args":        ["--pat", "--org", "--project", "--repo", "--sort", "--diagram", "--output"],
        "group":       "release",
        "status":      "ready",
    },
    "4": {
        "name":        "Pipeline Drift Analyzer",
        "description": "Detecta drift entre pipeline actual y snapshot del último release (stages/vars/approvals/tasks)",
        "path":        "azdo_pipeline_drift.py",
        "args":        ["--pat", "--org", "--project", "--repo", "--severity", "--sort", "--output"],
        "group":       "drift",
        "status":      "ready",
    },
    "5": {
        "name":        "Release Deep Dive",
        "description": "Análisis profundo de un Release Definition por ID: PRs + Políticas + CD Health + Drift",
        "path":        "azdo_release_deep_dive.py",
        "args":        ["--pat", "--org", "--project", "--release-id", "--branch", "--stage-name", "--output"],
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
        "description": "[Flujo] Inventario detallado de pipelines CD (Release Definitions). Extrae variables, filtra por var-name/var-value. Verifica cache previo (cd_raw.json < 24h) para skip APIs. Genera Excel + CSV + JSON cache.",
        "path":        "cicd_inventory_cd_detailed.py",
        "args":        ["--pat", "--org", "--project", "--workers", "--output", "--var-name", "--var-value", "--force-refresh", "--use-cache-only"],
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
    "21": {
        "name":        "Pipeline Updater",
        "description": "Actualiza variable branchConfig y scripts de tareas en Release Pipelines vía API REST. Modo interactivo con config.json.",
        "path":        "pipeline-cd-update-branchconfig.py",
        "args":        ["--interactive"],
        "group":       "updatepipe",
        "status":      "ready",
    },
    "22": {
        "name":        "Pipeline Rollback",
        "description": "Revierte cambios en Release Pipelines con 3 métodos: (1) Full Backup Restore (máxima seguridad), (2) Hybrid Rollback (revisión del backup desde Azure DevOps), (3) Manual Revision (rollback a revisión específica). Incluye listado de backups/revisiones, validación y dry-run.",
        "path":        "pipeline-cd-rollback-pipeline.py",
        "args":        ["--list-backups", "--list-revisions", "--backup-file", "--hybrid", "--pipeline-id", "--to-revision", "--pat", "--dry-run"],
        "group":       "updatepipe",
        "status":      "ready",
    },
    "23": {
        "name":        "Refresh Release",
        "description": "Crea Nuevo Release desde uno existente con backup automático versionado. Renueva variables de grupo, ideal para actualizar Credenciales Git.",
        "path":        "pipeline_cd_new_re_release.py",
        "args":        ["--org", "--project", "--source-release-id", "--release-comment", "--pat", "--backup-path"],
        "defaults":    {
            "org": "Coppel-Retail",
            "project": "Cadena_de_Suministros",
            "source_release_id": 999999,
            "release_comment": "Renovacion de Credenciales Git",
            "pat": "",
            "backup_path": "./outcome/backups"
        },
        "group":       "updatepipe",
        "status":      "ready",
    },
    "24": {
        "name":        "Pipeline Restore Release",
        "description": "Restaura un Release desde un backup versionado. Permite rollback completo con trazabilidad y confirmación interactiva.",
        "path":        "pipeline_cd_restore_release.py",
        "args":        ["--org", "--project", "--backup-file", "--restore-comment", "--pat", "--backup-path"],
        "defaults":    {
            "org": "Coppel-Retail",
            "project": "Cadena_de_Suministros",
            "backup_file": "",
            "restore_comment": "Restore automático desde tools.py",
            "pat": "",
            "backup_path": "./outcome/backups"
        },
        "group":       "updatepipe",
        "status":      "ready",
    },
    "25": {
        "name":        "Release Explorer",
        "description": "Explorador interactivo de Release Pipelines con búsqueda, filtros, detalles y comparación (diff) lado a lado",
        "path":        "azdo_release_explorer_rich.py",
        "args":        ["--org", "--project", "--pat", "--search", "--definition-id", "--release-id", 
                        "--stage-filter", "--status-filter", "--active-only", "--top", "--diff", "--interactive", "--json"],
        "group":       "release",
        "status":      "ready",
    },
    "26": {
        "name":        "Pipeline History",
        "description": "Evolución histórica de un Pipeline CD: revisiones, releases, diff exacto entre versiones y timeline interactiva HTML",
        "path":        "azdo_pipeline_history.py",
        "args":        ["--pat", "--org", "--project", "--definition-id", "--months", "--timezone", "--output", "--debug"],
        "group":       "release",
        "status":      "ready",
    },
    "40": {
        "name":        "Health Probe Masivo Validator",
        "description": "Validación masiva de health probes en K8s desde AZDO - Mapeo de stages, pruebas de conectividad, reportería ejecutiva",
        "path":        "health-probe-masive/health_probe_validator.py",
        "args":        ["-i", "-o", "--workers", "--timeout", "--format", "--verbose"],
        "group":       "health",
        "status":      "ready",
    },
    "27": {
        "name":        "Pipeline CD Backup & Restore",
        "description": "Backup/restore completo de definiciones de Pipeline CD. Individual (max 500 IDs), masivo, restore, crear desde backup, diff y conversion JSON→YAML. Submenú interactivo.",
        "path":        "pipeline_cd_backup_restore.py",
        "args":        ["--org", "--project", "--pat", "--mode", "--pipeline-ids",
                        "--backup-files", "--backup-file", "--new-name", "--path-filter",
                        "--format", "--workers", "--dry-run", "--interactive", "--output"],
        "group":       "updatepipe",
        "status":      "ready",
    },
    "41": {
        "name":        "Pipeline Updater Template",
        "description": "Actualización masiva de pipelines CD usando templates YAML. Define búsquedas y cambios de forma declarativa. Soporta ejecución paralela, snapshots automáticos y rollback.",
        "path":        "pipeline_updater/pipeline_updater.py",
        "args":        ["--definition-ids", "--template", "--dry-run", "--workers"],
        "group":       "updatepipe",
        "status":      "ready",
    },
    "28": {
        "name":        "Update Release",
        "description": "Actualiza un Release existente por releaseId via PATCH API usando templates YAML. Modifica variables globales, variables por environment, status (abandonar) y descripcion. Incluye backup automatico, dry-run y soporte multi-release.",
        "path":        "pipeline_cd_update_release/pipeline_cd_update_release.py",
        "args":        ["--org", "--project", "--release-id", "--set-var", "--set-env-var",
                        "--abandon", "--description", "--pat", "--backup-path", "--dry-run"],
        "defaults":    {
            "org": "Coppel-Retail",
            "project": "Cadena_de_Suministros",
            "release_id": "",
            "pat": "",
            "backup_path": "./outcome/backups"
        },
        "group":       "updatepipe",
        "status":      "ready",
    },
    "_system_options": {
        "A": {
            "name": "Ejecutar Todos",
            "description": "Ejecuta todas las herramientas con la misma configuración (sin Deep Dive)",
            "type": "auto_run",
            "exclude": ["1b", "5", "6", "7"],
            "reason": "Excluye: PR Pipeline Analyzer, Release Deep Dive, Task Validator, Pipeline Logs Scanner"
        },
        "B": {
            "name": "Ejecutar Todo + JSON",
            "description": "Ejecuta TODAS las herramientas en secuencia forzando salida JSON en outcome/. Ideal para alimentar el dashboard.",
            "type": "auto_run_json",
            "exclude": ["1b", "5", "6", "7"],
            "reason": "Excluye: PR Pipeline Analyzer, Release Deep Dive, Task Validator, Pipeline Logs Scanner"
        },
        "Q": {
            "name": "Salir",
            "description": "Salir del menú",
            "type": "exit"
        }
    }
}

STATUS_INDICATORS = {
    "ready":   ("🟢", "green",  "Listo"),
    "warning": ("🟡", "yellow", "Advertencia"),
    "error":   ("🔴", "red",    "Error"),
    "running": ("🔵", "blue",   "Ejecutando"),
    "exit":    ("🚪", "white",  "Salir"),
}

# Construir opciones de sistema dinámicamente
# Esto debe ocurrir después de definir TOOLS y todas las funciones necesarias
def _init_system_options():
    """Inicializa las opciones de sistema (A, B, Q) dinámicamente."""
    build_system_options()

# NOTA: _init_system_options() se llama al final del archivo después de definir todas las funciones

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


def load_last_params(tool_key: str = "common") -> Dict:
    """Carga los últimos parámetros usados para una herramienta."""
    if not LAST_PARAMS_FILE.exists():
        return {}
    try:
        with open(LAST_PARAMS_FILE, "r", encoding="utf-8") as f:
            all_params = json.load(f)
            return all_params.get(tool_key, {})
    except Exception:
        return {}


def save_last_params(tool_key: str, params: Dict) -> None:
    """Guarda los parámetros usados para una herramienta."""
    try:
        all_params = {}
        if LAST_PARAMS_FILE.exists():
            with open(LAST_PARAMS_FILE, "r", encoding="utf-8") as f:
                all_params = json.load(f)
        
        all_params[tool_key] = params
        
        with open(LAST_PARAMS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_params, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # Silenciosamente ignorar errores de guardado
        pass


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


def ask_common_params(cfg: dict, tool_key: str = "") -> dict:
    """Solicita parámetros comunes (org, project, pat) al usuario."""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Parámetros Comunes{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    # Organización - Retornar URL completa
    cfg_org = config_get(cfg, "azdo", "organization_url", default="https://dev.azure.com/Coppel-Retail")
    
    org = prompt("Organización", default=cfg_org)
    # Asegurar que org es la URL completa
    if not org.startswith("https://"):
        # Si el usuario ingresó solo el nombre, construir la URL
        org = f"https://dev.azure.com/{org}"
    
    # Proyecto
    project = prompt("Proyecto", default=config_get(cfg, "azdo", "project", default="Cadena_de_Suministros"))
    
    # PAT
    pat = prompt("Personal Access Token (PAT)",
                default=config_get(cfg, "azdo", "pat", default=""),
                secret=True)
    if not pat:
        print(f"{Colors.RED}❌ El PAT es obligatorio.{Colors.ENDC}")
        return None
    
    return {
        "org": org,
        "project": project,
        "pat": pat
    }


def print_header():
    """Imprime el encabezado del menú."""
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import print_header as _print_header
        _print_header(
            title="Azure DevOps Tools",
            subtitle=f"v{__version__} | ",
            description=__description__,
            emoji="🔷",
            border_color="cyan",
            platform_name="AZURE DEVOPS TOOLS"
        )
        _print_config_status()
    else:
        clear_screen()
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
    # Leer desde la nueva estructura consolidada: azdo.*
    pat   = config_get(cfg, "azdo", "pat")
    org   = config_get(cfg, "azdo", "organization_url")
    proj  = config_get(cfg, "azdo", "project")
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
    # Leer desde la nueva estructura consolidada: azdo.*
    pat   = config_get(cfg, "azdo", "pat")
    org   = config_get(cfg, "azdo", "organization_url")
    proj  = config_get(cfg, "azdo", "project")
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
                    key not in ("Q", "A", "B", "_system_options") and
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


def get_menu_order() -> List[str]:
    """Retorna las claves del menú ordenadas."""
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import get_menu_order as _get_menu_order
        return _get_menu_order(
            tools=TOOLS,
            group_order=GROUP_ORDER,
            system_keys=["B", "A", "Q"]
        )
    else:
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
    """Muestra el menú principal."""
    if BASE_LAUNCHER_AVAILABLE:
        from base_launcher import print_menu as _print_menu
        _print_menu(
            tools=TOOLS,
            group_order=GROUP_ORDER,
            tool_groups=TOOL_GROUPS,
            status_indicators=STATUS_INDICATORS
        )
    else:
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
    
    # ── Caso especial: Pipeline Updater (tool 21) usa modo interactivo ────────
    if tool_key == "21":
        # Pipeline Updater maneja sus propios parámetros en modo interactivo
        cmd = [str(venv_python), str(script_path), "--interactive"]
        
        print(f"\n{Colors.CYAN}▶ Ejecutando: {' '.join(cmd[:3])} ...{Colors.ENDC}\n")
        try:
            result = subprocess.run(cmd, cwd=BASE_DIR)
            
            if result.returncode == 0:
                print(f"\n{Colors.GREEN}✅ Completado exitosamente.{Colors.ENDC}")
            elif result.returncode == 1:
                print(f"\n{Colors.WARNING}🟡 Quality gate: HIGH (exit 1){Colors.ENDC}")
            else:
                print(f"\n{Colors.RED}🔴 Quality gate: CRITICAL (exit {result.returncode}){Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
        
        input("\nPresione Enter para continuar...")
        return
    
    # ── Caso especial: Pipeline Rollback (tool 22) ────────────────────────────
    if tool_key == "22":
        while True:
            # Mostrar menú de opciones de rollback
            print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}  🚀 Pipeline Rollback - Seleccione una opción{Colors.ENDC}")
            print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
            print(f"{Colors.CYAN}[1]{Colors.ENDC} Full Backup Restore (restaurar backup completo)")
            print(f"{Colors.CYAN}[2]{Colors.ENDC} Hybrid Rollback (revisión del backup desde Azure DevOps)")
            print(f"{Colors.CYAN}[3]{Colors.ENDC} Manual Revision (rollback a revisión específica)")
            print(f"{Colors.CYAN}[4]{Colors.ENDC} Listar backups disponibles")
            print(f"{Colors.CYAN}[5]{Colors.ENDC} Listar revisiones de un pipeline")
            print(f"{Colors.CYAN}[6]{Colors.ENDC} Redo (volver a versión previa del pipeline)")
            print(f"{Colors.WARNING}[0]{Colors.ENDC} Volver al menú principal")
            print(f"\n{Colors.BOLD}Seleccione una opción:{Colors.ENDC} ", end="")
            
            option = input().strip()
            
            # Opción 0: Volver
            if option == "0":
                return
            
            # Opción 4: Listar backups
            elif option == "4":
                cmd_list = [str(venv_python), str(script_path), "--list-backups"]
                print(f"\n{Colors.CYAN}▶ Listando backups disponibles...{Colors.ENDC}\n")
                subprocess.run(cmd_list, cwd=BASE_DIR)
                input("\nPresione Enter para continuar...")
                continue
            
            # Opción 5: Listar revisiones
            elif option == "5":
                print(f"\n{Colors.BOLD}Pipeline ID:{Colors.ENDC} ", end="")
                pipeline_id = input().strip()
                if not pipeline_id:
                    print(f"{Colors.RED}✗ Pipeline ID requerido{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                params = ask_common_params(cfg, tool_key=tool_key)
                if not params:
                    input("\nPresione Enter para continuar...")
                    continue
                
                cmd_list = [
                    str(venv_python), str(script_path),
                    "--list-revisions",
                    "--pipeline-id", pipeline_id,
                    "--org", params["org"],
                    "--project", params["project"],
                    "--pat", params["pat"]
                ]
                print(f"\n{Colors.CYAN}▶ Listando revisiones del pipeline {pipeline_id}...{Colors.ENDC}\n")
                subprocess.run(cmd_list, cwd=BASE_DIR)
                input("\nPresione Enter para continuar...")
                continue
            
            # Opción 1: Full Backup Restore
            elif option == "1":
                # Listar backups primero
                cmd_list = [str(venv_python), str(script_path), "--list-backups"]
                print(f"\n{Colors.CYAN}▶ Listando backups disponibles...{Colors.ENDC}\n")
                subprocess.run(cmd_list, cwd=BASE_DIR)
                
                # Solicitar archivo de backup
                print(f"\n{Colors.BOLD}Ruta del archivo de backup:{Colors.ENDC} ", end="")
                backup_file = input().strip()
                
                if not backup_file:
                    print(f"{Colors.RED}✗ Ruta de backup requerida{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Solicitar PAT
                params = ask_common_params(cfg, tool_key=tool_key)
                if not params:
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Preguntar si dry-run
                print(f"{Colors.BOLD}¿Modo DRY-RUN (simular sin aplicar)? (s/n) [n]:{Colors.ENDC} ", end="")
                dry_run = input().strip().lower()
                
                # Construir comando
                cmd = [str(venv_python), str(script_path), "--backup-file", backup_file, "--pat", params["pat"]]
                if dry_run == 's':
                    cmd.append("--dry-run")
                
                print(f"\n{Colors.CYAN}▶ Ejecutando Full Backup Restore...{Colors.ENDC}\n")
                try:
                    result = subprocess.run(cmd, cwd=BASE_DIR)
                    if result.returncode == 0:
                        print(f"\n{Colors.GREEN}✅ Rollback completado exitosamente.{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.RED}✗ Rollback falló (exit {result.returncode}){Colors.ENDC}")
                except Exception as e:
                    print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
                
                input("\nPresione Enter para continuar...")
                continue
            
            # Opción 2: Hybrid Rollback
            elif option == "2":
                # Listar backups primero
                cmd_list = [str(venv_python), str(script_path), "--list-backups"]
                print(f"\n{Colors.CYAN}▶ Listando backups disponibles...{Colors.ENDC}\n")
                subprocess.run(cmd_list, cwd=BASE_DIR)
                
                # Solicitar archivo de backup
                print(f"\n{Colors.BOLD}Ruta del archivo de backup:{Colors.ENDC} ", end="")
                backup_file = input().strip()
                
                if not backup_file:
                    print(f"{Colors.RED}✗ Ruta de backup requerida{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Solicitar PAT
                params = ask_common_params(cfg, tool_key=tool_key)
                if not params:
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Preguntar si dry-run
                print(f"{Colors.BOLD}¿Modo DRY-RUN (simular sin aplicar)? (s/n) [n]:{Colors.ENDC} ", end="")
                dry_run = input().strip().lower()
                
                # Construir comando con --hybrid
                cmd = [str(venv_python), str(script_path), "--backup-file", backup_file, "--hybrid", "--pat", params["pat"]]
                if dry_run == 's':
                    cmd.append("--dry-run")
                
                print(f"\n{Colors.CYAN}▶ Ejecutando Hybrid Rollback...{Colors.ENDC}\n")
                try:
                    result = subprocess.run(cmd, cwd=BASE_DIR)
                    if result.returncode == 0:
                        print(f"\n{Colors.GREEN}✅ Rollback híbrido completado exitosamente.{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.RED}✗ Rollback híbrido falló (exit {result.returncode}){Colors.ENDC}")
                except Exception as e:
                    print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
                
                input("\nPresione Enter para continuar...")
                continue
            
            # Opción 3: Manual Revision
            elif option == "3":
                print(f"\n{Colors.BOLD}Pipeline ID:{Colors.ENDC} ", end="")
                pipeline_id = input().strip()
                if not pipeline_id:
                    print(f"{Colors.RED}✗ Pipeline ID requerido{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Solicitar PAT y otros parámetros
                params = ask_common_params(cfg, tool_key=tool_key)
                if not params:
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Listar revisiones del pipeline
                cmd_list = [
                    str(venv_python), str(script_path),
                    "--list-revisions",
                    "--pipeline-id", pipeline_id,
                    "--org", params["org"],
                    "--project", params["project"],
                    "--pat", params["pat"]
                ]
                print(f"\n{Colors.CYAN}▶ Listando revisiones del pipeline {pipeline_id}...{Colors.ENDC}\n")
                subprocess.run(cmd_list, cwd=BASE_DIR)
                
                # Solicitar número de revisión
                print(f"\n{Colors.BOLD}Número de revisión objetivo:{Colors.ENDC} ", end="")
                to_revision = input().strip()
                if not to_revision:
                    print(f"{Colors.RED}✗ Número de revisión requerido{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Preguntar si dry-run
                print(f"{Colors.BOLD}¿Modo DRY-RUN (simular sin aplicar)? (s/n) [n]:{Colors.ENDC} ", end="")
                dry_run = input().strip().lower()
                
                # Construir comando
                cmd = [
                    str(venv_python), str(script_path),
                    "--pipeline-id", pipeline_id,
                    "--to-revision", to_revision,
                    "--org", params["org"],
                    "--project", params["project"],
                    "--pat", params["pat"]
                ]
                if dry_run == 's':
                    cmd.append("--dry-run")
                
                print(f"\n{Colors.CYAN}▶ Ejecutando Manual Revision Rollback...{Colors.ENDC}\n")
                try:
                    result = subprocess.run(cmd, cwd=BASE_DIR)
                    if result.returncode == 0:
                        print(f"\n{Colors.GREEN}✅ Rollback a revisión {to_revision} completado exitosamente.{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.RED}✗ Rollback a revisión {to_revision} falló (exit {result.returncode}){Colors.ENDC}")
                except Exception as e:
                    print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
                
                input("\nPresione Enter para continuar...")
                continue
            
            # Opción 6: Redo (volver a versión previa)
            elif option == "6":
                print(f"\n{Colors.BOLD}Pipeline ID (Definition ID):{Colors.ENDC} ", end="")
                definition_id = input().strip()
                if not definition_id:
                    print(f"{Colors.RED}✗ Pipeline ID requerido{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Solicitar PAT y otros parámetros
                params = ask_common_params(cfg, tool_key=tool_key)
                if not params:
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Preguntar si dry-run
                print(f"{Colors.BOLD}¿Modo DRY-RUN (simular sin aplicar)? (s/n) [n]:{Colors.ENDC} ", end="")
                dry_run = input().strip().lower()
                
                # Construir comando para redo
                cmd = [
                    str(venv_python), str(script_path),
                    "--redo",
                    "--definition-id", definition_id,
                    "--org", params["org"],
                    "--project", params["project"],
                    "--pat", params["pat"]
                ]
                if dry_run == 's':
                    cmd.append("--dry-run")
                
                print(f"\n{Colors.CYAN}▶ Ejecutando Redo (volver a versión previa) del pipeline {definition_id}...{Colors.ENDC}\n")
                try:
                    result = subprocess.run(cmd, cwd=BASE_DIR)
                    if result.returncode == 0:
                        print(f"\n{Colors.GREEN}✅ Redo completado exitosamente.{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.RED}✗ Redo falló (exit {result.returncode}){Colors.ENDC}")
                except Exception as e:
                    print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
                
                input("\nPresione Enter para continuar...")
                continue
            
            else:
                print(f"{Colors.RED}✗ Opción inválida. Por favor seleccione 0-6.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                continue
    
    # ── Caso especial: Pipeline Re-Release (tool 23) ────────────────────────────
    if tool_key == "23":
        tool_defaults = tool.get("defaults", {})
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  🚀 Pipeline Re-Release - Parámetros{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        
        # Solicitar parámetros específicos
        cfg_org = config_get(cfg, "azdo", "organization_url", default="https://dev.azure.com/Coppel-Retail")
        if cfg_org.startswith("https://"):
            cfg_org = cfg_org.split('/')[-1]
        
        org = prompt("Organización", default=cfg_org)
        if not org.startswith("https://"):
            org = f"https://dev.azure.com/{org}"
        
        project = prompt("Proyecto", default=config_get(cfg, "azdo", "project", default="Cadena_de_Suministros"))
        
        print(f"{Colors.BOLD}Release IDs origen (obligatorio, máx 50, separados por coma):{Colors.ENDC} ", end="")
        source_release_ids_input = input().strip()
        if not source_release_ids_input:
            print(f"{Colors.RED}❌ El Release ID es obligatorio.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        
        # Parsear y validar Release IDs
        source_release_ids = []
        for rid in source_release_ids_input.split(','):
            rid = rid.strip()
            if not rid or not rid.isdigit():
                print(f"{Colors.RED}❌ Release ID inválido: '{rid}'. Debe ser un número entero.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                return
            source_release_ids.append(rid)
        
        if len(source_release_ids) > 50:
            print(f"{Colors.RED}❌ Máximo 50 Release IDs permitidos. Se proporcionaron {len(source_release_ids)}.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        
        release_comment = prompt("Comentario para el nuevo release", 
                                default=tool_defaults.get("release_comment", "Renovacion de Credenciales Git"))
        
        pat = prompt("Personal Access Token (PAT)", 
                    default=config_get(cfg, "azdo", "pat", default=""), 
                    secret=True)
        if not pat:
            print(f"{Colors.RED}❌ El PAT es obligatorio.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        
        backup_path = prompt("Carpeta de backups", 
                            default=tool_defaults.get("backup_path", "./outcome/backups"))
        
        # Confirmación
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.YELLOW}⚠  CONFIRMACIÓN REQUERIDA{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"Se crearán {len(source_release_ids)} nuevo(s) Release(s) desde:")
        for rid in source_release_ids:
            print(f"  • Release #{rid}")
        print(f"Se generarán backup(s) automático(s) versionado(s)\n")
        
        confirm = input(f"{Colors.BOLD}¿Deseas continuar? (escribe 'SI' para confirmar): {Colors.ENDC}").strip().upper()
        if confirm != 'SI':
            print(f"\n{Colors.YELLOW}✗ Operación cancelada por el usuario{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        
        # Construir comando con múltiples Release IDs
        cmd = [
            str(venv_python), str(script_path),
            "--org", org,
            "--project", project,
            "--source-release-id", ",".join(source_release_ids),
            "--release-comment", release_comment,
            "--pat", pat,
            "--backup-path", backup_path
        ]
        
        print(f"\n{Colors.CYAN}▶ Ejecutando: {' '.join(cmd[:3])} ...{Colors.ENDC}\n")
        try:
            result = subprocess.run(cmd, cwd=BASE_DIR)
            if result.returncode == 0:
                print(f"\n{Colors.GREEN}✅ Re-Release completado exitosamente.{Colors.ENDC}")
            else:
                print(f"\n{Colors.RED}✗ Re-Release falló (exit {result.returncode}){Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
        
        input("\nPresione Enter para continuar...")
        return
    
    # ── Caso especial: Pipeline Restore Release (tool 24) ────────────────────────
    if tool_key == "24":
        tool_defaults = tool.get("defaults", {})
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  🔄 Pipeline Restore Release - Parámetros{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        
        # Solicitar parámetros específicos
        cfg_org = config_get(cfg, "azdo", "organization_url", default="https://dev.azure.com/Coppel-Retail")
        if cfg_org.startswith("https://"):
            cfg_org = cfg_org.split('/')[-1]
        
        org = prompt("Organización", default=cfg_org)
        if not org.startswith("https://"):
            org = f"https://dev.azure.com/{org}"
        
        project = prompt("Proyecto", default=config_get(cfg, "azdo", "project", default="Cadena_de_Suministros"))
        
        backup_file = prompt("Archivo de backup (ruta o nombre)", 
                            default=tool_defaults.get("backup_file", ""),
                            required=True)
        if not backup_file:
            print(f"{Colors.RED}❌ El archivo de backup es obligatorio.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        
        restore_comment = prompt("Comentario para el restore", 
                                default=tool_defaults.get("restore_comment", "Restore automático desde tools.py"))
        
        pat = prompt("Personal Access Token (PAT)", 
                    default=config_get(cfg, "azdo", "pat", default=""), 
                    secret=True)
        if not pat:
            print(f"{Colors.RED}❌ El PAT es obligatorio.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        
        backup_path = prompt("Carpeta de backups", 
                            default=tool_defaults.get("backup_path", "./outcome/backups"))
        
        # Construir comando
        cmd = [
            str(venv_python), str(script_path),
            "--org", org,
            "--project", project,
            "--backup-file", backup_file,
            "--restore-comment", restore_comment,
            "--pat", pat,
            "--backup-path", backup_path
        ]
        
        print(f"\n{Colors.CYAN}▶ Ejecutando: {' '.join(cmd[:3])} ...{Colors.ENDC}\n")
        try:
            result = subprocess.run(cmd, cwd=BASE_DIR)
            if result.returncode == 0:
                print(f"\n{Colors.GREEN}✅ Restore completado exitosamente.{Colors.ENDC}")
            else:
                print(f"\n{Colors.RED}✗ Restore falló (exit {result.returncode}){Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
        
        input("\nPresione Enter para continuar...")
        return
    
    # ── Caso especial: Release Explorer (tool 25) ────────────────────────────────
    if tool_key == "25":
        params = ask_common_params(cfg, tool_key=tool_key)
        if not params:
            input("\nPresione Enter para continuar...")
            return
        
        # Menú de opciones para Release Explorer
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  🔍 Release Explorer - Seleccione una opción{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        print(f"{Colors.CYAN}[1]{Colors.ENDC} Modo Interactivo (búsqueda y selección guiada)")
        print(f"{Colors.CYAN}[2]{Colors.ENDC} Buscar pipelines por nombre")
        print(f"{Colors.CYAN}[3]{Colors.ENDC} Listar releases de un pipeline")
        print(f"{Colors.CYAN}[4]{Colors.ENDC} Ver detalles de un release")
        print(f"{Colors.CYAN}[5]{Colors.ENDC} Comparar dos releases (Diff)")
        print(f"{Colors.WARNING}[0]{Colors.ENDC} Volver al menú principal")
        print(f"\n{Colors.BOLD}Seleccione una opción:{Colors.ENDC} ", end="")
        
        option = input().strip()
        
        if option == "0":
            return
        
        cmd = [str(venv_python), str(script_path), "--pat", params["pat"], "--org", params["org"], "--project", params["project"]]
        
        if option == "1":
            # Modo interactivo
            cmd.append("--interactive")
        elif option == "2":
            # Buscar pipelines
            print(f"{Colors.BOLD}Texto de búsqueda (inicio del nombre):{Colors.ENDC} ", end="")
            search = input().strip()
            if search:
                cmd += ["--search", search]
            else:
                print(f"{Colors.YELLOW}⚠  Búsqueda vacía, abriendo modo interactivo...{Colors.ENDC}")
                cmd.append("--interactive")
        elif option == "3":
            # Listar releases de un pipeline
            print(f"{Colors.BOLD}Pipeline Definition ID:{Colors.ENDC} ", end="")
            def_id = input().strip()
            if not def_id or not def_id.isdigit():
                print(f"{Colors.RED}❌ Definition ID inválido.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                return
            cmd += ["--definition-id", def_id]
            
            # Filtros opcionales
            print(f"{Colors.BOLD}Filtrar por stage (Enter para todos):{Colors.ENDC} ", end="")
            stage = input().strip()
            if stage:
                cmd += ["--stage-filter", stage]
            
            print(f"{Colors.BOLD}¿Solo stages activos? (s/n) [n]:{Colors.ENDC} ", end="")
            if input().strip().lower() == "s":
                cmd.append("--active-only")
        elif option == "4":
            # Ver detalles de un release
            print(f"{Colors.BOLD}Release ID:{Colors.ENDC} ", end="")
            rel_id = input().strip()
            if not rel_id or not rel_id.isdigit():
                print(f"{Colors.RED}❌ Release ID inválido.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                return
            cmd += ["--release-id", rel_id]
        elif option == "5":
            # Comparar dos releases
            print(f"{Colors.BOLD}Release ID 1:{Colors.ENDC} ", end="")
            rel1 = input().strip()
            print(f"{Colors.BOLD}Release ID 2:{Colors.ENDC} ", end="")
            rel2 = input().strip()
            if not rel1 or not rel1.isdigit() or not rel2 or not rel2.isdigit():
                print(f"{Colors.RED}❌ Release IDs inválidos.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                return
            cmd += ["--diff", rel1, rel2]
        else:
            print(f"{Colors.RED}❌ Opción no válida.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        
        print(f"\n{Colors.CYAN}▶ Ejecutando: {' '.join(cmd[:3])} ...{Colors.ENDC}\n")
        try:
            result = subprocess.run(cmd, cwd=BASE_DIR)
            if result.returncode == 0:
                print(f"\n{Colors.GREEN}✅ Completado exitosamente.{Colors.ENDC}")
            else:
                print(f"\n{Colors.RED}✗ Falló (exit {result.returncode}){Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
        
        input("\nPresione Enter para continuar...")
        return
    
    # ── Caso especial: Pipeline CD Backup & Restore (tool 27) usa modo interactivo ──
    if tool_key == "27":
        cmd = [str(venv_python), str(script_path), "--interactive"]

        print(f"\n{Colors.CYAN}▶ Ejecutando: {' '.join(cmd[:3])} ...{Colors.ENDC}\n")
        try:
            result = subprocess.run(cmd, cwd=BASE_DIR)

            if result.returncode == 0:
                print(f"\n{Colors.GREEN}✅ Completado exitosamente.{Colors.ENDC}")
            elif result.returncode == 1:
                print(f"\n{Colors.WARNING}🟡 Quality gate: HIGH (exit 1){Colors.ENDC}")
            else:
                print(f"\n{Colors.RED}🔴 Quality gate: CRITICAL (exit {result.returncode}){Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")

        input("\nPresione Enter para continuar...")
        return

    # ── Caso especial: Update Release (tool 28) - Submenú ──────────────────────
    if tool_key == "28":
        tool_defaults = tool.get("defaults", {})

        while True:
            print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}  🆙 Update Release - Seleccione una opción{Colors.ENDC}")
            print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
            print(f"{Colors.CYAN}[1]{Colors.ENDC} Actualizar release (interactivo)")
            print(f"{Colors.CYAN}[2]{Colors.ENDC} Dry-run (simular cambios sin aplicar)")
            print(f"{Colors.CYAN}[3]{Colors.ENDC} Listar backups disponibles")
            print(f"{Colors.CYAN}[4]{Colors.ENDC} Ejecutar desde CLI (argumentos directos)")
            print(f"{Colors.WARNING}[0]{Colors.ENDC} Volver al menú principal")
            print(f"\n{Colors.BOLD}Seleccione una opción:{Colors.ENDC} ", end="")

            option = input().strip()

            # Opción 0: Volver
            if option == "0":
                return

            # Opción 3: Listar backups
            elif option == "3":
                backups_dir = BASE_DIR / "outcome" / "backups"
                if backups_dir.exists():
                    print(f"\n{Colors.CYAN}📁 Backups disponibles:{Colors.ENDC}\n")
                    backups = sorted(backups_dir.glob("release_backup_UPD_REL_*.json"))
                    if backups:
                        for i, bk in enumerate(backups[-20:], 1):
                            print(f"  {i}. {bk.name}")
                    else:
                        print(f"  {Colors.YELLOW}No hay backups de update release disponibles{Colors.ENDC}")
                else:
                    print(f"  {Colors.YELLOW}Directorio de backups no existe{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                continue

            # Opciones 1 y 2: Actualizar / Dry-run (misma lógica, dry-run opcional)
            elif option in ("1", "2"):
                is_dry_run = (option == "2")

                print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
                print(f"{Colors.BOLD}  🆙 Update Release - {'Dry-Run' if is_dry_run else 'Actualizar'} Release{Colors.ENDC}")
                print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

                # Solicitar parámetros específicos
                cfg_org = config_get(cfg, "azdo", "organization_url", default="https://dev.azure.com/Coppel-Retail")
                if cfg_org.startswith("https://"):
                    cfg_org = cfg_org.split('/')[-1]

                org = prompt("Organización", default=cfg_org)
                if not org.startswith("https://"):
                    org = f"https://dev.azure.com/{org}"

                project = prompt("Proyecto", default=config_get(cfg, "azdo", "project", default="Cadena_de_Suministros"))

                print(f"{Colors.BOLD}Release IDs a actualizar (obligatorio, separados por coma):{Colors.ENDC} ", end="")
                release_ids_input = input().strip()
                if not release_ids_input:
                    print(f"{Colors.RED}❌ El Release ID es obligatorio.{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue

                release_ids = []
                valid = True
                for rid in release_ids_input.split(','):
                    rid = rid.strip()
                    if not rid or not rid.isdigit():
                        print(f"{Colors.RED}❌ Release ID inválido: '{rid}'. Debe ser un número entero.{Colors.ENDC}")
                        valid = False
                        break
                    release_ids.append(rid)
                if not valid:
                    input("\nPresione Enter para continuar...")
                    continue

                # Variables globales (opcional, repetible)
                global_vars = []
                print(f"\n{Colors.CYAN}--- Variables Globales (opcional) ---{Colors.ENDC}")
                print(f"{Colors.DIM}Formato: NOMBRE=VALOR (Enter vacío para saltar){Colors.ENDC}")
                while True:
                    var_input = input(f"{Colors.BOLD}  Variable (o Enter para saltar): {Colors.ENDC}").strip()
                    if not var_input:
                        break
                    if '=' in var_input:
                        global_vars.append(var_input)
                    else:
                        print(f"{Colors.RED}  ✗ Formato inválido. Use NOMBRE=VALOR{Colors.ENDC}")

                # Variables por environment (opcional, repetible)
                env_vars = []
                print(f"\n{Colors.CYAN}--- Variables por Environment (opcional) ---{Colors.ENDC}")
                print(f"{Colors.DIM}Formato: STAGE,NOMBRE=VALOR (Enter vacío para saltar){Colors.ENDC}")
                while True:
                    var_input = input(f"{Colors.BOLD}  Variable (o Enter para saltar): {Colors.ENDC}").strip()
                    if not var_input:
                        break
                    if ',' in var_input and '=' in var_input:
                        env_vars.append(var_input)
                    else:
                        print(f"{Colors.RED}  ✗ Formato inválido. Use STAGE,NOMBRE=VALOR{Colors.ENDC}")

                # Abandonar release
                print(f"\n{Colors.BOLD}¿Abandonar release(s)? (s/n) [n]:{Colors.ENDC} ", end="")
                abandon = input().strip().lower() in ('s', 'si', 'yes', 'y')

                # Descripción (opcional)
                print(f"{Colors.BOLD}Nueva descripción (Enter para mantener):{Colors.ENDC} ", end="")
                description = input().strip()

                # PAT
                pat = prompt("Personal Access Token (PAT)",
                            default=config_get(cfg, "azdo", "pat", default=""),
                            secret=True)
                if not pat:
                    print(f"{Colors.RED}❌ El PAT es obligatorio.{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue

                backup_path = prompt("Carpeta de backups",
                                    default=tool_defaults.get("backup_path", "./outcome/backups"))

                # Construir comando
                cmd = [
                    str(venv_python), str(script_path),
                    "--org", org,
                    "--project", project,
                    "--release-id", ",".join(release_ids),
                    "--pat", pat,
                    "--backup-path", backup_path
                ]

                for var in global_vars:
                    cmd += ["--set-var", var]

                for var in env_vars:
                    cmd += ["--set-env-var", var]

                if abandon:
                    cmd.append("--abandon")

                if description:
                    cmd += ["--description", description]

                if is_dry_run:
                    cmd.append("--dry-run")

                label = "Dry-Run" if is_dry_run else "Update"
                print(f"\n{Colors.CYAN}▶ Ejecutando {label}...{Colors.ENDC}\n")
                try:
                    result = subprocess.run(cmd, cwd=BASE_DIR)
                    if result.returncode == 0:
                        print(f"\n{Colors.GREEN}✅ {label} completado exitosamente.{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.RED}✗ {label} falló (exit {result.returncode}){Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")

                input("\nPresione Enter para continuar...")
                continue

            # Opción 4: Ejecutar desde CLI (argumentos directos)
            elif option == "4":
                print(f"\n{Colors.BOLD}Ingrese los argumentos completos para el script:{Colors.ENDC}")
                print(f"{Colors.DIM}Ej: --release-id 987 --pat TOKEN --set-var FOO=bar --dry-run{Colors.ENDC}")
                print(f"{Colors.BOLD}Args:{Colors.ENDC} ", end="")
                cli_args = input().strip()
                if not cli_args:
                    print(f"{Colors.YELLOW}Sin argumentos. Cancelando...{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue

                cmd = [str(venv_python), str(script_path)] + cli_args.split()
                print(f"\n{Colors.CYAN}▶ Ejecutando: {' '.join(cmd[:3])} ...{Colors.ENDC}\n")
                try:
                    result = subprocess.run(cmd, cwd=BASE_DIR)
                    if result.returncode == 0:
                        print(f"\n{Colors.GREEN}✅ Completado exitosamente.{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.RED}✗ Falló (exit {result.returncode}){Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")

                input("\nPresione Enter para continuar...")
                continue

            else:
                print(f"{Colors.RED}✗ Opción inválida. Por favor seleccione 0-4.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                continue

    # ── Caso especial: Pipeline Updater Template (tool 41) ──────────────────────
    if tool_key == "41":
        while True:
            # Mostrar menú de opciones
            print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}  🆙 Pipeline Updater Template - Seleccione una opción{Colors.ENDC}")
            print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
            print(f"{Colors.CYAN}[1]{Colors.ENDC} Actualizar pipelines (modo interactivo)")
            print(f"{Colors.CYAN}[2]{Colors.ENDC} Rollback desde snapshot")
            print(f"{Colors.CYAN}[3]{Colors.ENDC} Listar snapshots disponibles")
            print(f"{Colors.WARNING}[0]{Colors.ENDC} Volver al menú principal")
            print(f"\n{Colors.BOLD}Seleccione una opción:{Colors.ENDC} ", end="")
            
            option = input().strip()
            
            # Opción 0: Volver
            if option == "0":
                return
            
            # Opción 3: Listar snapshots
            elif option == "3":
                snapshots_dir = BASE_DIR / "outcome" / "snapshots"
                if snapshots_dir.exists():
                    print(f"\n{Colors.CYAN}📁 Snapshots disponibles:{Colors.ENDC}\n")
                    snapshots = sorted(snapshots_dir.glob("*.json"))
                    if snapshots:
                        for i, snap in enumerate(snapshots[-20:], 1):  # Últimos 20
                            print(f"  {i}. {snap.name}")
                    else:
                        print(f"  {Colors.YELLOW}No hay snapshots disponibles{Colors.ENDC}")
                else:
                    print(f"  {Colors.YELLOW}Directorio de snapshots no existe{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                continue
            
            # Opción 2: Rollback desde snapshot
            elif option == "2":
                params = ask_common_params(cfg, tool_key=tool_key)
                if not params:
                    input("\nPresione Enter para continuar...")
                    continue
                
                print(f"\n{Colors.BOLD}Definition ID (pipeline a restaurar):{Colors.ENDC} ", end="")
                def_id = input().strip()
                if not def_id or not def_id.isdigit():
                    print(f"{Colors.RED}❌ Definition ID inválido.{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                print(f"{Colors.BOLD}Snapshot ID (ej: snapshot_3388_1689254400):{Colors.ENDC} ", end="")
                snapshot_id = input().strip()
                if not snapshot_id:
                    print(f"{Colors.RED}❌ Snapshot ID requerido.{Colors.ENDC}")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Construir comando de rollback
                cmd = [
                    str(venv_python), str(script_path),
                    "--rollback",
                    "--definition-id", def_id,
                    "--snapshot-id", snapshot_id,
                    "--org", params["org"],
                    "--project", params["project"],
                    "--pat", params["pat"]
                ]
                
                print(f"\n{Colors.CYAN}▶ Ejecutando rollback...{Colors.ENDC}\n")
                try:
                    result = subprocess.run(cmd, cwd=BASE_DIR)
                    
                    if result.returncode == 0:
                        print(f"\n{Colors.GREEN}✅ Rollback completado exitosamente.{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.RED}✗ Rollback falló (exit {result.returncode}){Colors.ENDC}")
                except Exception as e:
                    print(f"\n{Colors.FAIL}Error al ejecutar: {e}{Colors.ENDC}")
                
                input("\nPresione Enter para continuar...")
                continue
            
            # Opción 1: Actualizar pipelines
            elif option == "1":
                console.print(f"\n[bold]{'='*70}[/]")
                console.print(f"[bold]  🆙 Pipeline Updater Template - Actualización Masiva[/]")
                console.print(f"[bold]{'='*70}[/]\n")
                
                # Solicitar definition IDs
                definition_ids_str = Prompt.ask(
                    "[bold]Definition IDs[/bold] (separados por coma, ej: 2758,2759,2760)",
                    console=console
                ).strip()
                
                if not definition_ids_str:
                    console.print("[red]❌ Definition IDs requeridos.[/]")
                    input("\nPresione Enter para continuar...")
                    continue
                
                try:
                    definition_ids = [int(x.strip()) for x in definition_ids_str.split(',')]
                except ValueError:
                    console.print("[red]❌ Definition IDs deben ser números separados por coma.[/]")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Solicitar ruta del template
                template_path_input = Prompt.ask(
                    "[bold]Ruta del template YAML[/bold] (ej: scm/templates/example_template.yaml)",
                    console=console
                ).strip()
                
                if not template_path_input:
                    console.print("[red]❌ Ruta del template requerida.[/]")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Resolver ruta del template desde la raíz del proyecto
                template_path_obj = Path(template_path_input)
                if template_path_obj.is_absolute():
                    template_full_path = template_path_obj
                else:
                    # BASE_DIR es scm/azdo, necesitamos subir 2 niveles para llegar a la raíz
                    project_root = BASE_DIR.parent.parent
                    template_full_path = project_root / template_path_input
                    
                    # Si no existe, intentar limpiar prefijos duplicados (autocompletado del shell)
                    if not template_full_path.exists():
                        # Caso: el usuario ingreso algo como scm/templates/devsecops-toolbox\scm\templates\file.yaml
                        # Normalizar separadores y usar la ultima ocurrencia de 'scm/templates/' como punto de corte
                        normalized = template_path_input.replace('\\', '/').replace('//', '/')
                        if 'scm/templates/' in normalized:
                            # rsplit para tomar despues de la ultima ocurrencia de 'scm/templates/'
                            last_part = normalized.rsplit('scm/templates/', 1)[-1]
                            clean_path = 'scm/templates/' + last_part
                            template_full_path = project_root / clean_path
                
                # Verificar que el template existe
                if not template_full_path.exists():
                    console.print(f"[red]❌ Template no encontrado: {template_full_path}[/]")
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Pasar la ruta absoluta al script
                template_path = str(template_full_path)
                
                # Solicitar parámetros comunes
                params = ask_common_params(cfg, tool_key=tool_key)
                if not params:
                    input("\nPresione Enter para continuar...")
                    continue
                
                # Solicitar número de workers
                workers_str = Prompt.ask(
                    "[bold]Número de workers paralelos[/]",
                    default="5",
                    console=console
                ).strip()
                try:
                    workers = int(workers_str)
                except ValueError:
                    workers = 5
                
                # Preguntar si es dry-run
                dry_run = Confirm.ask(
                    "[bold]¿Modo dry-run?[/bold] (simulación sin cambios)",
                    default=False,
                    console=console
                )
                
                # Construir comando
                # Ejecutar como módulo para evitar problemas con imports relativos
                # Usar python global en lugar del venv para acceso a dependencias
                cmd = [
                    sys.executable, "-m", "scm.azdo.pipeline_updater.pipeline_updater",
                    "--definition-ids", definition_ids_str,
                    "--template", template_path,
                    "--org", params["org"],
                    "--project", params["project"],
                    "--pat", params["pat"],
                    "--workers", str(workers)
                ]
                
                if dry_run:
                    cmd.append("--dry-run")
                
                console.print(f"\n[cyan]▶ Ejecutando: {' '.join(cmd[:3])} ...[/]\n")
                try:
                    # Ejecutar desde la raíz del proyecto para que los imports funcionen
                    project_root = BASE_DIR.parent.parent
                    result = subprocess.run(cmd, cwd=project_root)
                    
                    if result.returncode == 0:
                        console.print(f"\n[green]✅ Actualización completada exitosamente.[/]")
                    else:
                        console.print(f"\n[red]✗ Actualización falló (exit {result.returncode})[/]")
                except Exception as e:
                    console.print(f"[red]Error al ejecutar: {e}[/]")
                
                input("\nPresione Enter para continuar...")
                continue
            
            else:
                print(f"{Colors.RED}❌ Opción no válida.{Colors.ENDC}")
                input("\nPresione Enter para continuar...")
                continue
    
    params = ask_common_params(cfg, tool_key=tool_key)
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

    if "--definition-id" in tool_args and "--release-id" not in extra:
        print(f"{Colors.BOLD}Pipeline Definition ID (obligatorio):{Colors.ENDC} ", end="")
        val = input().strip()
        if not val or not val.isdigit():
            print(f"{Colors.RED}❌ El Definition ID es obligatorio y debe ser un número entero.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
            return
        extra += ["--definition-id", val]

    if "--months" in tool_args:
        print(f"{Colors.BOLD}Meses hacia atrás a analizar [6]:{Colors.ENDC} ", end="")
        val = input().strip()
        if val and val.isdigit():
            extra += ["--months", val]
        else:
            extra += ["--months", "6"]

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
        cfg_fmt = config_get(cfg, "defaults", "output_format", default="excel")
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
        result = subprocess.run(cmd, cwd=BASE_DIR)
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
    params = ask_common_params(cfg, tool_key="run_all")
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
            result = subprocess.run(cmd, cwd=BASE_DIR)
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
    params = ask_common_params(cfg, tool_key="run_all_json")
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
            result = subprocess.run(cmd, cwd=BASE_DIR)
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
                console.print(f"[bold]Seleccione una opción (o '/' para buscar):[/] ", end="")
            else:
                print(f"{Colors.BOLD}Seleccione una opción (o '/' para buscar):{Colors.ENDC} ", end="")

            choice = input().strip()

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
        sys.exit(0)
