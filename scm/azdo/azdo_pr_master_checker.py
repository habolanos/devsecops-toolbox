#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_pr_master_checker.py

Lista todos los Pull Requests hacia master (o cualquier rama destino)
en todos los repositorios de un proyecto Azure DevOps.

Por cada PR muestra:
  - Repositorio
  - Fecha/Hora (merge si completado, creación si activo)
  - Link al PR
  - Pipeline CD asociado (nombre o —)
  - Si el pipeline CD tiene un stage/environment llamado "validador" (✅ / ⛔ / —)

Flujo:
  1. Lista todos los repos del proyecto
  2. Obtiene PRs hacia la rama destino (por defecto: master)
  3. Lista todas las Release Definitions (CD clásico) del proyecto
  4. Cruza repo ↔ CD por similitud de nombre
  5. Para cada CD encontrado, obtiene sus environments y verifica el stage buscado
  6. Muestra tabla Rich en consola + exporta (CSV / JSON / Excel)

Autor: Harold Adrian
"""

import argparse
import base64
import csv
import fnmatch
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
    from rich.table import Table
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULT_ORG_URL = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT = "Compras.RMI"
DEFAULT_TARGET_BRANCH = "master"
DEFAULT_PR_STATUS = "active"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_STAGE_NAME = "validador"
DEFAULT_TOP = 500
DEFAULT_THREADS = 20
API_VERSION = "7.1"


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS
# ═══════════════════════════════════════════════════════════════════════════════
def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lista PRs hacia master cruzados con pipeline CD y stage 'validador'"
    )
    parser.add_argument(
        "--org", "-g",
        default=DEFAULT_ORG_URL,
        help=f"URL de la organización AzDO (default: {DEFAULT_ORG_URL})"
    )
    parser.add_argument(
        "--project", "-p",
        default=DEFAULT_PROJECT,
        help=f"Nombre del proyecto (default: {DEFAULT_PROJECT})"
    )
    parser.add_argument(
        "--pat",
        required=True,
        help="Personal Access Token con permisos: Code (Read), Release (Read)"
    )
    parser.add_argument(
        "--branch", "-b",
        default=DEFAULT_TARGET_BRANCH,
        help=f"Rama destino del PR (acepta wildcards: release/*, release/v*) (default: {DEFAULT_TARGET_BRANCH})"
    )
    parser.add_argument(
        "--status", "-s",
        default=DEFAULT_PR_STATUS,
        choices=["all", "active", "completed", "abandoned"],
        help=f"Filtro de estado de PR (default: {DEFAULT_PR_STATUS})"
    )
    parser.add_argument(
        "--repo", "-r",
        default=None,
        help="Filtrar por nombre de repositorio (substring, case insensitive)"
    )
    parser.add_argument(
        "--stage-name",
        default=DEFAULT_STAGE_NAME,
        help=f"Nombre del stage/environment a buscar en el CD (default: {DEFAULT_STAGE_NAME})"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "csv", "excel"],
        default=None,
        help="Exportar resultados a archivo (json / csv / excel)"
    )
    parser.add_argument(
        "--timezone", "-tz",
        default=DEFAULT_TIMEZONE,
        help=f"Zona horaria para mostrar fechas (default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP,
        help=f"Max PRs por repositorio (default: {DEFAULT_TOP})"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help=f"Hilos paralelos para consultar repos (default: {DEFAULT_THREADS})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostrar detalles de errores HTTP"
    )
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP
# ═══════════════════════════════════════════════════════════════════════════════
def make_headers(pat: str) -> Dict:
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def api_get(url: str, headers: Dict, params: Dict = None, debug: bool = False) -> Optional[Any]:
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code >= 400:
            _api_label = url.split("/_apis")[0].split("/")[-1] if "/_apis" in url else url
            print(f"  ⚠  HTTP {resp.status_code} ({_api_label})")
            if debug:
                print(f"[DEBUG] URL: {url}")
                print(f"[DEBUG] Body: {resp.text[:300]}")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if debug:
            print(f"[DEBUG] HTTPError: {e}")
        return None
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception on {url}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# API CALLS
# ═══════════════════════════════════════════════════════════════════════════════
def get_repositories(org: str, project: str, headers: Dict, debug: bool = False) -> List[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories"
    data = api_get(url, headers, {"api-version": API_VERSION}, debug)
    return data.get("value", []) if data else []


def get_pull_requests(
    org: str, project: str, repo_id: str,
    target_branch: str, status: str, top: int,
    headers: Dict, debug: bool = False
) -> List[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories/{repo_id}/pullrequests"
    params = {
        "searchCriteria.targetRefName": f"refs/heads/{target_branch}",
        "searchCriteria.status": status,
        "$top": top,
        "api-version": API_VERSION,
    }
    data = api_get(url, headers, params, debug)
    return data.get("value", []) if data else []


def vsrm_base(org_url: str) -> str:
    """Transforma dev.azure.com/{org} → vsrm.dev.azure.com/{org} para Release APIs."""
    return org_url.replace("dev.azure.com", "vsrm.dev.azure.com")


def is_wildcard_branch(branch: str) -> bool:
    """Retorna True si el branch contiene wildcards (* o ?)."""
    return '*' in branch or '?' in branch


def get_all_pull_requests(
    org: str, project: str,
    target_branch: str, status: str, top: int,
    headers: Dict, debug: bool = False,
) -> List[Dict]:
    """Descarga todos los PRs del proyecto en bloque (cross-repo, paginado).
    1-N llamadas en lugar de 1 por repositorio.
    Si target_branch contiene wildcards, no filtra por branch en la API
    (la API no soporta wildcards) y se filtra localmente después.
    """
    url = f"{org}/{quote(project, safe='')}/_apis/git/pullrequests"
    all_prs: List[Dict] = []
    skip = 0
    page_size = min(top, 1000)
    wildcard = is_wildcard_branch(target_branch)
    while True:
        params = {
            "searchCriteria.status": status,
            "$top": page_size,
            "$skip": skip,
            "api-version": API_VERSION,
        }
        if not wildcard:
            params["searchCriteria.targetRefName"] = f"refs/heads/{target_branch}"
        data = api_get(url, headers, params, debug)
        if not data:
            break
        batch = data.get("value", [])
        all_prs.extend(batch)
        if len(batch) < page_size or len(all_prs) >= top:
            break
        skip += page_size
    return all_prs[:top]


def filter_prs_by_branch_wildcard(prs: List[Dict], branch_pattern: str) -> List[Dict]:
    """Filtra PRs localmente usando fnmatch sobre el target branch.
    branch_pattern puede contener * y ? (ej: 'release/*', 'release/v*').
    """
    if not is_wildcard_branch(branch_pattern):
        return prs
    pattern = f"refs/heads/{branch_pattern}"
    return [
        pr for pr in prs
        if fnmatch.fnmatch(pr.get("targetRefName", ""), pattern)
    ]


def get_release_definitions_list(
    org: str, project: str, headers: Dict, debug: bool = False
) -> List[Dict]:
    """Lista resumida de release definitions (ID + nombre). Paginado."""
    base = vsrm_base(org)
    url = f"{base}/{quote(project, safe='')}/_apis/release/definitions"
    all_defs: List[Dict] = []
    skip = 0
    page_size = 500
    while True:
        params = {"api-version": "7.2-preview.4", "$top": page_size, "$skip": skip}
        data = api_get(url, headers, params, debug)
        if not data:
            break
        batch = data.get("value", [])
        all_defs.extend(batch)
        if len(batch) < page_size:
            break
        skip += page_size
    return all_defs


def get_release_definition_detail(
    org: str, project: str, def_id: int, headers: Dict, debug: bool = False
) -> Optional[Dict]:
    """Detalle completo de una release definition (incluye environments/stages)."""
    base = vsrm_base(org)
    url = f"{base}/{quote(project, safe='')}/_apis/release/definitions/{def_id}"
    params = {"api-version": "7.2-preview.4"}
    return api_get(url, headers, params, debug)


# ═══════════════════════════════════════════════════════════════════════════════
# MATCHING LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def normalize(name: str) -> str:
    return name.lower().strip().replace("-", "").replace("_", "").replace(" ", "").replace(".", "")


def find_cd_candidates_for_repo(repo_name: str, release_defs: List[Dict], debug: bool = False) -> List[Tuple[int, int]]:
    """
    Busca CDs candidatos para un repositorio por nombre (sin descargar detalles).
    Retorna lista de (cd_id, score) ordenada por score descendente.
    """
    repo_lower = repo_name.lower()
    repo_norm = normalize(repo_name)

    candidates = []

    for rd in release_defs:
        cd_name = rd.get("name", "").lower()
        cd_norm = normalize(cd_name)
        score = 0

        # Heurística 1: Match exacto o contiene
        if cd_name == repo_lower:
            score = 100
        elif cd_name.startswith(repo_lower):
            score = 90
        elif repo_lower in cd_name:
            score = 70
        elif repo_norm in cd_norm or cd_norm in repo_norm:
            score = 60

        # Heurística 2: Palabras compartidas (3+ caracteres)
        if score < 50:
            repo_words = set(w for w in re.split(r'[-_\s\.]+', repo_lower) if len(w) >= 3)
            cd_words = set(w for w in re.split(r'[-_\s\.]+', cd_name) if len(w) >= 3)
            shared = repo_words & cd_words
            generic = {'api', 'svc', 'service', 'web', 'app', 'frontend', 'backend', 'legacy', 'uc', 'wm', 'wms', 'tms', 'iwms'}
            specific_shared = shared - generic
            if len(specific_shared) >= 1:
                score = 40 + len(specific_shared) * 10
            elif len(shared) >= 2:
                score = 30

        if score > 0:
            candidates.append((rd["id"], score))

    candidates.sort(key=lambda x: x[1], reverse=True)

    if debug and candidates:
        cd_names = {rd["id"]: rd["name"] for rd in release_defs}
        print(f"[DEBUG] CD candidates for '{repo_name}' ({len(candidates)}):")
        for i, (cd_id, s) in enumerate(candidates[:5], 1):
            marker = " ✅ TOP" if i == 1 else ""
            print(f"  {i}. '{cd_names.get(cd_id, '?')}' (score: {s}){marker}")

    return candidates


def find_cd_by_artifact_source(repo_name: str, cd_details_map: Dict[int, Dict], debug: bool = False) -> Optional[Dict]:
    """Busca CD por nombre exacto del repositorio en artifact source."""
    repo_lower = repo_name.lower()

    for cd_id, cd_detail in cd_details_map.items():
        if not cd_detail:
            continue
        for artifact in cd_detail.get("artifacts", []):
            if artifact.get("type") == "Git":
                artifact_repo_name = (
                    artifact.get("definitionReference", {})
                    .get("definition", {})
                    .get("name", "")
                    .lower()
                )
                if artifact_repo_name == repo_lower:
                    if debug:
                        print(f"[DEBUG] ✅ Match por artifact source: '{cd_detail.get('name')}' (ID: {cd_id})")
                    return cd_detail

    return None


def find_cd_for_repo_with_details(
    repo_name: str,
    release_defs: List[Dict],
    cd_details_map: Dict[int, Dict],
    debug: bool = False
) -> Optional[Dict]:
    """
    Busca CD pipeline para un repositorio usando detalles descargados:
    1. Artifact source (más preciso)
    2. Nombre del CD (fallback con scoring)
    """
    # PASO 1: Artifact source (más preciso)
    cd_match = find_cd_by_artifact_source(repo_name, cd_details_map, debug)
    if cd_match:
        return cd_match

    # PASO 2: Fallback por nombre con scoring
    repo_lower = repo_name.lower()
    repo_norm = normalize(repo_name)
    best_match = None
    best_score = 0

    for rd in release_defs:
        cd_id = rd.get("id")
        if cd_id not in cd_details_map:
            continue

        cd_name = rd.get("name", "").lower()
        cd_norm = normalize(cd_name)
        score = 0

        if cd_name == repo_lower:
            score = 100
        elif cd_name.startswith(repo_lower):
            score = 90
        elif repo_lower in cd_name:
            score = 70
        elif repo_norm in cd_norm or cd_norm in repo_norm:
            score = 60
        else:
            repo_words = set(w for w in re.split(r'[-_\s\.]+', repo_lower) if len(w) >= 3)
            cd_words = set(w for w in re.split(r'[-_\s\.]+', cd_name) if len(w) >= 3)
            shared = repo_words & cd_words
            generic = {'api', 'svc', 'service', 'web', 'app', 'frontend', 'backend', 'legacy', 'uc', 'wm', 'wms', 'tms', 'iwms'}
            specific_shared = shared - generic
            if len(specific_shared) >= 1:
                score = 40 + len(specific_shared) * 10
            elif len(shared) >= 2:
                score = 30

        if score > best_score:
            best_score = score
            best_match = rd

    if best_match and best_score >= 30:
        cd_id = best_match.get("id")
        cd_detail = cd_details_map.get(cd_id, best_match)
        if not cd_detail:
            cd_detail = best_match
        if debug:
            print(f"[DEBUG] ✅ Match por nombre: '{best_match.get('name')}' (score: {best_score})")
        return cd_detail

    return None


def has_stage(release_def_detail: Dict, stage_name: str) -> bool:
    """Verifica si una release definition tiene un environment con el nombre buscado."""
    envs = release_def_detail.get("environments", [])
    stage_norm = stage_name.lower().strip()
    return any(env.get("name", "").lower().strip() == stage_norm for env in envs)


# ═══════════════════════════════════════════════════════════════════════════════
# DATE / URL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def format_date(date_str: str, tz_name: str) -> str:
    if not date_str:
        return "—"
    try:
        # AzDO dates can be "2024-03-15T18:22:41.123Z" or "2024-03-15T18:22:41"
        clean = date_str.rstrip("Z").split(".")[0]
        dt = datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return date_str


def get_pr_date(pr: Dict, tz_name: str) -> str:
    """Retorna closedDate para PRs completados, creationDate para el resto."""
    if pr.get("status") == "completed" and pr.get("closedDate"):
        return format_date(pr["closedDate"], tz_name)
    return format_date(pr.get("creationDate", ""), tz_name)


def build_pr_url(org: str, project: str, repo_name: str, pr_id: int) -> str:
    base = org.rstrip("/")
    return f"{base}/{project}/_git/{repo_name}/pullrequest/{pr_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════
def print_rich_table(console: "Console", rows: List[Dict], stage_name: str, branch: str):
    table = Table(
        title=f"🔀 Pull Requests → {branch}",
        title_style="bold cyan",
        header_style="bold white",
        border_style="dim",
        box=box.ROUNDED,
        show_lines=False,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Repositorio", style="bold white", min_width=22)
    table.add_column("PR", justify="center", width=7)
    table.add_column("Estado", justify="center", width=11)
    table.add_column("Fecha/Hora", justify="center", width=20)
    table.add_column("Autor", min_width=14)
    table.add_column("Título", min_width=22)
    table.add_column("Pipeline CD", min_width=22)
    table.add_column(f"Stage '{stage_name}'", justify="center", width=12)

    status_style = {
        "active": "green",
        "completed": "blue",
        "abandoned": "red",
    }

    for idx, row in enumerate(rows, 1):
        st = row["status"]
        st_color = status_style.get(st, "white")

        cd_cell = f"[cyan]{row['cd_name']}[/cyan]" if row["has_cd"] else "[dim]—[/dim]"

        if not row["has_cd"]:
            stage_cell = "[dim]—[/dim]"
        elif row["cd_has_stage"]:
            stage_cell = "[bold green]✅[/bold green]"
        else:
            stage_cell = "[bold red]⛔[/bold red]"

        table.add_row(
            str(idx),
            row["repository"],
            str(row["pr_id"]),
            f"[{st_color}]{st}[/{st_color}]",
            row["date"],
            row["created_by"],
            row["title"],
            cd_cell,
            stage_cell,
        )

    console.print(table)
    console.print()


def print_summary(console: "Console", rows: List[Dict], stage_name: str, elapsed: float):
    total = len(rows)
    active = sum(1 for r in rows if r["status"] == "active")
    completed = sum(1 for r in rows if r["status"] == "completed")
    abandoned = sum(1 for r in rows if r["status"] == "abandoned")
    with_cd = sum(1 for r in rows if r["has_cd"])
    with_stage = sum(1 for r in rows if r["cd_has_stage"])
    repos_count = len({r["repository"] for r in rows})

    console.print(Panel(
        f"[bold white]📋 Total PRs:[/]       [cyan]{total}[/]  ([dim]{repos_count} repos[/])\n"
        f"[bold white]🟢 Activos:[/]         [green]{active}[/]\n"
        f"[bold white]✅ Completados:[/]     [blue]{completed}[/]\n"
        f"[bold white]🚫 Abandonados:[/]     [red]{abandoned}[/]\n"
        f"[bold white]⚙️  Con CD:[/]          [magenta]{with_cd}[/] de {total}\n"
        f"[bold white]🔍 Con '{stage_name}':[/]  [yellow]{with_stage}[/] de {with_cd if with_cd else '—'}\n"
        f"[dim]⏱️  Tiempo: {elapsed:.2f}s[/]",
        title="📊 Resumen",
        border_style="blue",
        expand=False,
    ))
    console.print()


def export_results(rows: List[Dict], output_format: str, script_dir: str, stage_name: str, tz_name: str) -> Optional[str]:
    outcome_dir = os.path.join(script_dir, "outcome")
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"pr_master_{ts}.json")
        payload = {
            "metadata": {
                "tool": "azdo_pr_master_checker",
                "version": __version__,
                "stage_searched": stage_name,
                "generated_at": datetime.now(ZoneInfo(tz_name)).isoformat(),
            },
            "total": len(rows),
            "data": rows,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath

    elif output_format == "csv":
        if not rows:
            return None
        filepath = os.path.join(outcome_dir, f"pr_master_{ts}.csv")
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return filepath

    elif output_format == "excel":
        try:
            import pandas as pd
            filepath = os.path.join(outcome_dir, f"pr_master_{ts}.xlsx")
            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False, engine="openpyxl")
            return filepath
        except ImportError:
            print("ERROR: Instala pandas y openpyxl para exportar a Excel.")
            return None

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    start_time = time.time()

    if not REQUESTS_AVAILABLE:
        print("ERROR: Instala 'requests': pip install requests rich")
        return

    args = get_args()
    console = Console() if RICH_AVAILABLE else None

    # Validar timezone
    tz_name = args.timezone
    try:
        ZoneInfo(tz_name)
    except Exception:
        if console:
            console.print(f"[yellow]⚠️ Zona horaria '{tz_name}' inválida. Usando {DEFAULT_TIMEZONE}[/]")
        tz_name = DEFAULT_TIMEZONE

    revision_time = datetime.now(ZoneInfo(tz_name)).strftime(f"%Y-%m-%d %H:%M:%S ({tz_name})")
    headers = make_headers(args.pat)

    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel(
            f"[bold cyan]🔀 PR Master Checker[/]\n"
            f"[dim]🕐 {revision_time}[/]\n"
            f"[dim]🏢 Organización:  {args.org}[/]\n"
            f"[dim]📁 Proyecto:      {args.project}[/]\n"
            f"[dim]🌿 Branch destino: [bold]{args.branch}[/][/]\n"
            f"[dim]📊 Status PRs:    {args.status}[/]\n"
            f"[dim]🔍 Stage buscado: [bold yellow]{args.stage_name}[/][/]",
            border_style="cyan",
            expand=False,
        ))
        console.print()

    # ── 1. Repositorios ──────────────────────────────────────────────────────
    if RICH_AVAILABLE and console:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task("Obteniendo repositorios...", total=None)
            repos = get_repositories(args.org, args.project, headers, args.debug)
            p.update(t, description=f"✅ {len(repos)} repositorios encontrados")
    else:
        repos = get_repositories(args.org, args.project, headers, args.debug)
        print(f"{len(repos)} repositorios encontrados")

    if not repos:
        msg = ("❌ Sin repositorios. Verifica URL de org, nombre de proyecto y PAT.\n"
               "   💡 Si el proyecto tiene espacios (ej: 'Cadena de Suministros') ingrésalo con espacios, no con guiones bajos.")
        if console:
            console.print(f"[red]{msg}[/]")
        else:
            print(msg)
        return

    if args.repo:
        repos = [r for r in repos if args.repo.lower() in r["name"].lower()]
        if console:
            console.print(f"[dim]🔍 Repos filtrados: {len(repos)} (contienen '{args.repo}')[/]")

    # ── 2. Release Definitions (CD) ──────────────────────────────────────────
    if RICH_AVAILABLE and console:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task("Obteniendo pipelines CD (release definitions)...", total=None)
            release_defs_list = get_release_definitions_list(args.org, args.project, headers, args.debug)
            p.update(t, description=f"✅ {len(release_defs_list)} release definitions encontradas")
    else:
        release_defs_list = get_release_definitions_list(args.org, args.project, headers, args.debug)
        print(f"{len(release_defs_list)} release definitions encontradas")

    console.print() if console else None

    # ── 3. PRs en bloque (cross-project) ───────────────────────────────────────
    repo_ids_in_scope = {r["id"] for r in repos}
    wildcard_mode = is_wildcard_branch(args.branch)

    if wildcard_mode:
        if console:
            console.print(f"[dim]🌿 Branch con wildcard: '{args.branch}' — se descargan todos los PRs y se filtra localmente[/]")
        else:
            print(f"  Branch con wildcard: '{args.branch}' — se descargan todos los PRs y se filtra localmente")

    if RICH_AVAILABLE and console:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task("Descargando PRs del proyecto en bloque...", total=None)
            raw_prs = get_all_pull_requests(
                args.org, args.project, args.branch, args.status, args.top, headers, args.debug
            )
            # Filtrar por wildcard si aplica
            if wildcard_mode:
                raw_prs = filter_prs_by_branch_wildcard(raw_prs, args.branch)
            prs_in_scope = [pr for pr in raw_prs if pr.get("repository", {}).get("id") in repo_ids_in_scope]
            branch_label = args.branch if not wildcard_mode else f"{args.branch} (wildcard)"
            p.update(t, description=f"✅ {len(prs_in_scope)} PRs → {branch_label} ({len(raw_prs)} totales en proyecto)")
    else:
        print("  Descargando PRs del proyecto en bloque...", end="", flush=True)
        raw_prs = get_all_pull_requests(
            args.org, args.project, args.branch, args.status, args.top, headers, args.debug
        )
        if wildcard_mode:
            raw_prs = filter_prs_by_branch_wildcard(raw_prs, args.branch)
        prs_in_scope = [pr for pr in raw_prs if pr.get("repository", {}).get("id") in repo_ids_in_scope]
        print(f"\r  ✅ {len(prs_in_scope)} PRs → {args.branch} ({len(raw_prs)} totales en proyecto)          ")

    console.print() if console else None

    # ── 4. Buscar CD candidates y descargar solo sus detalles ────────────────
    repos_with_prs_names = {pr.get("repository", {}).get("name", "") for pr in prs_in_scope}

    # 4a. Buscar candidatos por nombre (local, sin API calls)
    candidate_ids_per_repo: Dict[str, List[Tuple[int, int]]] = {}
    all_candidate_ids: set = set()

    for name in repos_with_prs_names:
        candidates = find_cd_candidates_for_repo(name, release_defs_list, args.debug)
        candidate_ids_per_repo[name] = candidates
        for cd_id, score in candidates:
            all_candidate_ids.add(cd_id)

    if RICH_AVAILABLE and console:
        console.print(f"[dim]🔍 Candidatos CD: {len(all_candidate_ids)} únicos (de {len(release_defs_list)} totales)[/]")
    else:
        print(f"  Candidatos CD: {len(all_candidate_ids)} únicos (de {len(release_defs_list)} totales)")

    # 4b. Descargar detalles solo de los candidatos en paralelo
    cd_details: Dict[int, Optional[Dict]] = {}
    if all_candidate_ids:
        if RICH_AVAILABLE and console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as p:
                t = p.add_task(f"Cargando detalles de {len(all_candidate_ids)} CDs candidatos...", total=len(all_candidate_ids))
                with ThreadPoolExecutor(max_workers=args.threads) as executor:
                    futs = {
                        executor.submit(
                            get_release_definition_detail,
                            args.org, args.project, cd_id, headers, args.debug,
                        ): cd_id
                        for cd_id in all_candidate_ids
                    }
                    for fut in as_completed(futs):
                        cd_id = futs[fut]
                        try:
                            cd_details[cd_id] = fut.result()
                        except Exception:
                            cd_details[cd_id] = None
                        p.advance(t)
        else:
            print(f"  Cargando detalles de {len(all_candidate_ids)} CDs candidatos...", end="", flush=True)
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futs = {
                    executor.submit(
                        get_release_definition_detail,
                        args.org, args.project, cd_id, headers, args.debug,
                    ): cd_id
                    for cd_id in all_candidate_ids
                }
                for fut in as_completed(futs):
                    cd_id = futs[fut]
                    try:
                        cd_details[cd_id] = fut.result()
                    except Exception:
                        cd_details[cd_id] = None
            print(f"\r  ✅ {len(all_candidate_ids)} CDs candidatos cargados                              ")

    # 4c. Matching final: artifact source + nombre fallback
    cd_for_repo: Dict[str, Optional[Dict]] = {}
    for name in repos_with_prs_names:
        repo_candidate_ids = {cd_id for cd_id, _ in candidate_ids_per_repo.get(name, [])}
        repo_cd_details = {k: v for k, v in cd_details.items() if k in repo_candidate_ids}
        repo_release_defs = [rd for rd in release_defs_list if rd["id"] in repo_candidate_ids]
        cd_for_repo[name] = find_cd_for_repo_with_details(name, repo_release_defs, repo_cd_details, args.debug)

    console.print() if console else None

    # ── 5. Construir filas (sin HTTP) ────────────────────────────────────
    all_rows: List[Dict] = []
    for pr in prs_in_scope:
        repo_info = pr.get("repository", {})
        repo_name = repo_info.get("name", "")
        pr_id = pr.get("pullRequestId")

        cd_detail = cd_for_repo.get(repo_name)
        has_cd = cd_detail is not None
        cd_name = cd_detail.get("name", "—") if cd_detail else "—"
        cd_has_stage = False
        if cd_detail:
            cd_has_stage = has_stage(cd_detail, args.stage_name)

        all_rows.append({
            "repository": repo_name,
            "pr_id": pr_id,
            "title": pr.get("title", ""),
            "status": pr.get("status", ""),
            "created_by": pr.get("createdBy", {}).get("displayName", ""),
            "date": get_pr_date(pr, tz_name),
            "url": build_pr_url(args.org, args.project, repo_name, pr_id),
            "has_cd": has_cd,
            "cd_name": cd_name,
            "cd_has_stage": cd_has_stage,
        })

    # Ordenar por fecha descendente
    all_rows.sort(key=lambda r: r["date"], reverse=True)

    if not all_rows:
        msg = f"⚠️ No se encontraron PRs hacia '{args.branch}' con status '{args.status}'."
        if console:
            console.print(f"[yellow]{msg}[/]")
        else:
            print(msg)
        return

    # ── 4. Tabla ─────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time

    if RICH_AVAILABLE and console:
        print_rich_table(console, all_rows, args.stage_name, args.branch)
        print_summary(console, all_rows, args.stage_name, elapsed)
    else:
        print(f"\n{'='*80}")
        print(f"{'Repositorio':<28} {'PR':>6} {'Estado':<12} {'Fecha':^20} {'CD':<25} {'Validador'}")
        print(f"{'='*80}")
        for row in all_rows:
            stage_val = ("SI" if row["cd_has_stage"] else "NO") if row["has_cd"] else "—"
            print(f"{row['repository']:<28} {row['pr_id']:>6} {row['status']:<12} "
                  f"{row['date']:^20} {row['cd_name']:<25} {stage_val}")
        print(f"\nTotal: {len(all_rows)} PRs | Tiempo: {elapsed:.2f}s")

    # ── 5. Exportar ───────────────────────────────────────────────────────────
    if args.output:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = export_results(all_rows, args.output, script_dir, args.stage_name, tz_name)
        if filepath:
            if console:
                console.print(f"[bold green]📁 Exportado:[/] {filepath}\n")
            else:
                print(f"Exportado: {filepath}")


if __name__ == "__main__":
    main()
