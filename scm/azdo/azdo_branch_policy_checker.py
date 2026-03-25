#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_branch_policy_checker.py

Consulta todos los repositorios de un proyecto Azure DevOps y verifica
las políticas de ramas configuradas para master/main, QA y develop.

Estado por repositorio:
  ✅ OK      — Las 3 ramas tienen al menos una política habilitada
  🟡 WARNING — Solo 1 o 2 ramas tienen políticas (parcial)
  🔴 ALERT   — Ninguna rama tiene políticas configuradas

Columnas mostradas:
  Repositorio | master/main | QA | develop | Estado

Flags opcionales:
  --detail   Muestra lista de políticas por rama debajo de cada repo
  --output   Exporta a csv / json / excel

Autor: Harold Adrian
"""

import argparse
import base64
import csv
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text
    from rich import box
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
DEFAULT_ORG_URL  = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT  = "Compras.RMI"
DEFAULT_TIMEZONE = "America/Mazatlan"
API_VERSION      = "7.1"

# Nombres canónicos y sus variantes en refs/heads/
BRANCH_ALIASES: Dict[str, List[str]] = {
    "master": [
        "refs/heads/master",
        "refs/heads/main",
    ],
    "QA": [
        "refs/heads/QA",
        "refs/heads/qa",
        "refs/heads/Qa",
        "refs/heads/release",
        "refs/heads/Release",
    ],
    "develop": [
        "refs/heads/develop",
        "refs/heads/development",
        "refs/heads/dev",
        "refs/heads/Dev",
    ],
}

# Status semáforo
STATUS_OK      = "OK"
STATUS_WARNING = "WARNING"
STATUS_ALERT   = "ALERT"


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS
# ═══════════════════════════════════════════════════════════════════════════════
def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifica políticas de ramas (master/QA/develop) en todos los repos de AzDO"
    )
    parser.add_argument(
        "--org", "-g",
        default=DEFAULT_ORG_URL,
        help=f"URL de la organización (default: {DEFAULT_ORG_URL})"
    )
    parser.add_argument(
        "--project", "-p",
        default=DEFAULT_PROJECT,
        help=f"Nombre del proyecto (default: {DEFAULT_PROJECT})"
    )
    parser.add_argument(
        "--pat",
        required=True,
        help="Personal Access Token con permisos: Code (Read), Policy (Read)"
    )
    parser.add_argument(
        "--repo", "-r",
        default=None,
        help="Filtrar por nombre de repositorio (substring, case insensitive)"
    )
    parser.add_argument(
        "--status-filter",
        choices=["OK", "WARNING", "ALERT", "all"],
        default="all",
        help="Mostrar solo repos con cierto estado (default: all)"
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Mostrar detalle de políticas por rama bajo cada repositorio"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "csv", "excel"],
        default=None,
        help="Exportar resultados (json / csv / excel)"
    )
    parser.add_argument(
        "--timezone", "-tz",
        default=DEFAULT_TIMEZONE,
        help=f"Zona horaria para fechas (default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostrar errores HTTP detallados"
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


def api_get(
    url: str,
    headers: Dict,
    params: Dict = None,
    debug: bool = False,
) -> Optional[Any]:
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code >= 400:
            _api_label = url.split("/_apis")[0].split("/")[-1] if "/_apis" in url else url
            print(f"  ⚠  HTTP {resp.status_code} ({_api_label})")
            if debug:
                print(f"[DEBUG] URL: {url}")
                print(f"[DEBUG] Body: {resp.text[:400]}")
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
def get_repositories(
    org: str, project: str, headers: Dict, debug: bool = False
) -> List[Dict]:
    url  = f"{org}/{quote(project, safe='')}/_apis/git/repositories"
    data = api_get(url, headers, {"api-version": API_VERSION}, debug)
    return data.get("value", []) if data else []


def get_policy_configurations(
    org: str, project: str, headers: Dict, debug: bool = False
) -> List[Dict]:
    """
    Obtiene TODAS las policy configurations del proyecto en una sola llamada.
    Incluye políticas con scope de repo específico Y políticas globales (sin repositoryId).
    """
    url    = f"{org}/{quote(project, safe='')}/_apis/policy/configurations"
    params = {"api-version": API_VERSION, "$top": 1000}
    data   = api_get(url, headers, params, debug)
    return data.get("value", []) if data else []


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY INDEX
# ═══════════════════════════════════════════════════════════════════════════════
PolicyInfo = Dict[str, Any]  # {"name": str, "is_blocking": bool, "is_enabled": bool}


def build_policy_index(
    configurations: List[Dict],
) -> Tuple[Dict[str, Dict[str, List[PolicyInfo]]], List[Dict]]:
    """
    Construye un índice:
      repo_index  → { repo_id:  { ref_name: [PolicyInfo, ...] } }
      global_list → [ { ref_name: str, policies: [PolicyInfo] }, ... ]
                    (políticas sin repositoryId — aplican a todos los repos)
    """
    repo_index: Dict[str, Dict[str, List[PolicyInfo]]] = {}  # keyed by repo_id (lower)
    global_by_ref: Dict[str, List[PolicyInfo]] = {}          # keyed by ref_name (lower)

    for cfg in configurations:
        policy_name = cfg.get("type", {}).get("displayName", "Unknown Policy")
        is_enabled  = cfg.get("isEnabled", False)
        is_blocking = cfg.get("isBlocking", False)

        info: PolicyInfo = {
            "name":        policy_name,
            "is_enabled":  is_enabled,
            "is_blocking": is_blocking,
        }

        scopes = cfg.get("settings", {}).get("scope", [])
        for scope in scopes:
            ref_name    = (scope.get("refName") or "").lower().strip()
            match_kind  = (scope.get("matchKind") or "Exact").strip()
            repo_id     = (scope.get("repositoryId") or "").lower().strip()

            if not ref_name:
                continue

            if repo_id:
                # Política específica de un repo
                if repo_id not in repo_index:
                    repo_index[repo_id] = {}
                key = (ref_name, match_kind)
                bucket_key = f"{ref_name}|{match_kind}"
                if bucket_key not in repo_index[repo_id]:
                    repo_index[repo_id][bucket_key] = []
                repo_index[repo_id][bucket_key].append(info)
            else:
                # Política global (aplica a todos los repos)
                bucket_key = f"{ref_name}|{match_kind}"
                if bucket_key not in global_by_ref:
                    global_by_ref[bucket_key] = []
                global_by_ref[bucket_key].append(info)

    return repo_index, global_by_ref


def _ref_matches_aliases(
    bucket_key: str,
    aliases: List[str],
) -> bool:
    """
    Verifica si un bucket_key del índice corresponde a alguno de los aliases.
    bucket_key formato: "refs/heads/master|Exact" o "refs/heads/|Prefix"
    """
    ref, match_kind = bucket_key.rsplit("|", 1)
    ref_lower = ref.lower()

    if match_kind == "Exact":
        return ref_lower in [a.lower() for a in aliases]

    if match_kind == "Prefix":
        # La política aplica a toda rama que empiece por ref
        return any(a.lower().startswith(ref_lower) for a in aliases)

    return False


def get_policies_for_branch(
    repo_id: str,
    canonical_branch: str,
    repo_index: Dict[str, Dict[str, List[PolicyInfo]]],
    global_by_ref: Dict[str, List[PolicyInfo]],
) -> List[PolicyInfo]:
    """
    Retorna las políticas (habilitadas) que aplican a una rama canónica
    de un repo concreto, combinando políticas específicas + globales.
    """
    aliases = BRANCH_ALIASES.get(canonical_branch, [])
    found: List[PolicyInfo] = []

    # Repo-specific policies
    repo_policies = repo_index.get(repo_id.lower(), {})
    for bucket_key, infos in repo_policies.items():
        if _ref_matches_aliases(bucket_key, aliases):
            found.extend(infos)

    # Global policies
    for bucket_key, infos in global_by_ref.items():
        if _ref_matches_aliases(bucket_key, aliases):
            found.extend(infos)

    # Solo políticas habilitadas
    return [p for p in found if p["is_enabled"]]


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def compute_status(
    master_p: List, qa_p: List, develop_p: List
) -> str:
    count = sum(1 for p in [master_p, qa_p, develop_p] if p)
    if count == 3:
        return STATUS_OK
    if count == 0:
        return STATUS_ALERT
    return STATUS_WARNING


def policies_cell(policies: List[PolicyInfo]) -> str:
    """Texto resumen para una celda de rama."""
    if not policies:
        return ""
    n        = len(policies)
    blocking = sum(1 for p in policies if p["is_blocking"])
    names    = ", ".join(sorted({p["name"] for p in policies}))
    return f"{n} pol. ({blocking} bloq.) | {names}"


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════
def _branch_cell_rich(policies: List[PolicyInfo]) -> str:
    if not policies:
        return "[dim]⛔ Sin políticas[/dim]"
    n        = len(policies)
    blocking = sum(1 for p in policies if p["is_blocking"])
    return f"[green]✅ {n} pol.[/green] [dim]({blocking} bloq.)[/dim]"


def _status_cell_rich(status: str) -> str:
    if status == STATUS_OK:
        return "[bold green]✅ OK[/bold green]"
    if status == STATUS_WARNING:
        return "[bold yellow]🟡 WARNING[/bold yellow]"
    return "[bold red]🔴 ALERT[/bold red]"


def print_rich_table(
    console: "Console",
    rows: List[Dict],
    detail: bool = False,
):
    table = Table(
        title="🛡️  Branch Policy Checker — master | QA | develop",
        title_style="bold cyan",
        header_style="bold white",
        border_style="dim",
        box=box.ROUNDED,
        show_lines=detail,
    )
    table.add_column("#",            style="dim",       width=4,  justify="right")
    table.add_column("Repositorio",  style="bold white", min_width=28)
    table.add_column("master / main", justify="center",  min_width=18)
    table.add_column("QA",           justify="center",  min_width=18)
    table.add_column("develop",      justify="center",  min_width=18)
    table.add_column("Estado",       justify="center",  width=14)

    for idx, row in enumerate(rows, 1):
        table.add_row(
            str(idx),
            row["repository"],
            _branch_cell_rich(row["master_policies"]),
            _branch_cell_rich(row["qa_policies"]),
            _branch_cell_rich(row["develop_policies"]),
            _status_cell_rich(row["status"]),
        )

        if detail and any([row["master_policies"], row["qa_policies"], row["develop_policies"]]):
            for canonical, key in [("master", "master_policies"), ("QA", "qa_policies"), ("develop", "develop_policies")]:
                for p in row[key]:
                    blocking_tag = "[yellow] (blocking)[/yellow]" if p["is_blocking"] else ""
                    table.add_row(
                        "",
                        f"[dim]  ↳ {canonical}[/dim]",
                        f"[dim]{p['name']}{blocking_tag}[/dim]" if canonical == "master" else "",
                        f"[dim]{p['name']}{blocking_tag}[/dim]" if canonical == "QA" else "",
                        f"[dim]{p['name']}{blocking_tag}[/dim]" if canonical == "develop" else "",
                        "",
                    )

    console.print(table)
    console.print()


def print_rich_summary(console: "Console", rows: List[Dict], elapsed: float):
    total   = len(rows)
    ok      = sum(1 for r in rows if r["status"] == STATUS_OK)
    warning = sum(1 for r in rows if r["status"] == STATUS_WARNING)
    alert   = sum(1 for r in rows if r["status"] == STATUS_ALERT)

    console.print(Panel(
        f"[bold white]📋 Repositorios analizados:[/]  [cyan]{total}[/]\n"
        f"[bold green]✅ OK      (3/3 ramas):[/]  {ok}\n"
        f"[bold yellow]🟡 WARNING (1-2 ramas):[/]  {warning}\n"
        f"[bold red]🔴 ALERT   (0 ramas):[/]    {alert}\n"
        f"[dim]⏱️  Tiempo: {elapsed:.2f}s[/]",
        title="📊 Resumen",
        border_style="blue",
        expand=False,
    ))
    console.print()


def export_results(
    rows: List[Dict],
    output_format: str,
    script_dir: str,
    tz_name: str,
) -> Optional[str]:
    outcome_dir = os.path.join(script_dir, "outcome")
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Aplanar para exportar
    flat = []
    for row in rows:
        flat.append({
            "repository":       row["repository"],
            "status":           row["status"],
            "master_policies":  policies_cell(row["master_policies"]),
            "qa_policies":      policies_cell(row["qa_policies"]),
            "develop_policies": policies_cell(row["develop_policies"]),
            "master_count":     len(row["master_policies"]),
            "qa_count":         len(row["qa_policies"]),
            "develop_count":    len(row["develop_policies"]),
        })

    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"branch_policies_{ts}.json")
        payload = {
            "metadata": {
                "tool":         "azdo_branch_policy_checker",
                "version":      __version__,
                "generated_at": datetime.now(ZoneInfo(tz_name)).isoformat(),
            },
            "total":   len(rows),
            "summary": {
                "ok":      sum(1 for r in rows if r["status"] == STATUS_OK),
                "warning": sum(1 for r in rows if r["status"] == STATUS_WARNING),
                "alert":   sum(1 for r in rows if r["status"] == STATUS_ALERT),
            },
            "data": flat,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath

    elif output_format == "csv":
        if not flat:
            return None
        filepath = os.path.join(outcome_dir, f"branch_policies_{ts}.csv")
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(flat[0].keys()))
            writer.writeheader()
            writer.writerows(flat)
        return filepath

    elif output_format == "excel":
        try:
            import pandas as pd
            filepath = os.path.join(outcome_dir, f"branch_policies_{ts}.xlsx")
            df = pd.DataFrame(flat)
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
        print("ERROR: Instala dependencias: pip install requests rich pandas openpyxl")
        return

    args    = get_args()
    console = Console() if RICH_AVAILABLE else None
    headers = make_headers(args.pat)

    tz_name = args.timezone
    try:
        ZoneInfo(tz_name)
    except Exception:
        if console:
            console.print(f"[yellow]⚠️ Zona horaria '{tz_name}' inválida. Usando {DEFAULT_TIMEZONE}[/]")
        tz_name = DEFAULT_TIMEZONE

    revision_time = datetime.now(ZoneInfo(tz_name)).strftime(f"%Y-%m-%d %H:%M:%S ({tz_name})")

    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel(
            f"[bold cyan]🛡️  Branch Policy Checker[/]\n"
            f"[dim]🕐 {revision_time}[/]\n"
            f"[dim]🏢 Organización: {args.org}[/]\n"
            f"[dim]📁 Proyecto:     {args.project}[/]\n"
            f"[dim]🔍 Ramas:        master/main · QA · develop[/]",
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
        msg = "❌ Sin repositorios. Verifica URL de org, nombre de proyecto y PAT."
        (console.print(f"[red]{msg}[/]") if console else print(msg))
        return

    if args.repo:
        repos = [r for r in repos if args.repo.lower() in r["name"].lower()]
        if console:
            console.print(f"[dim]🔍 Filtrado: {len(repos)} repos que contienen '{args.repo}'[/]")

    # ── 2. Policy configurations (UNA sola llamada) ──────────────────────────
    if RICH_AVAILABLE and console:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task("Obteniendo policy configurations...", total=None)
            configurations = get_policy_configurations(args.org, args.project, headers, args.debug)
            p.update(t, description=f"✅ {len(configurations)} configuraciones de políticas obtenidas")
    else:
        configurations = get_policy_configurations(args.org, args.project, headers, args.debug)
        print(f"{len(configurations)} configuraciones de políticas obtenidas")

    console.print() if console else None

    # ── 3. Construir índice de políticas ─────────────────────────────────────
    repo_index, global_by_ref = build_policy_index(configurations)

    # ── 4. Evaluar cada repo ──────────────────────────────────────────────────
    rows: List[Dict] = []
    for repo in repos:
        repo_id   = repo["id"]
        repo_name = repo["name"]

        master_p  = get_policies_for_branch(repo_id, "master",  repo_index, global_by_ref)
        qa_p      = get_policies_for_branch(repo_id, "QA",      repo_index, global_by_ref)
        develop_p = get_policies_for_branch(repo_id, "develop", repo_index, global_by_ref)
        status    = compute_status(master_p, qa_p, develop_p)

        rows.append({
            "repository":       repo_name,
            "repo_id":          repo_id,
            "master_policies":  master_p,
            "qa_policies":      qa_p,
            "develop_policies": develop_p,
            "status":           status,
        })

    # Ordenar: ALERT primero, luego WARNING, luego OK
    order = {STATUS_ALERT: 0, STATUS_WARNING: 1, STATUS_OK: 2}
    rows.sort(key=lambda r: (order[r["status"]], r["repository"].lower()))

    # Filtro por status si se especificó
    if args.status_filter != "all":
        rows = [r for r in rows if r["status"] == args.status_filter]

    if not rows:
        msg = f"⚠️ No hay repos con status '{args.status_filter}'."
        (console.print(f"[yellow]{msg}[/]") if console else print(msg))
        return

    # ── 5. Mostrar tabla ─────────────────────────────────────────────────────
    elapsed = time.time() - start_time

    if RICH_AVAILABLE and console:
        print_rich_table(console, rows, detail=args.detail)
        print_rich_summary(console, rows, elapsed)
    else:
        # Fallback sin Rich
        hdr = f"{'#':>4}  {'Repositorio':<35} {'master':^18} {'QA':^18} {'develop':^18} Estado"
        print(f"\n{'='*len(hdr)}")
        print(hdr)
        print(f"{'='*len(hdr)}")
        for idx, row in enumerate(rows, 1):
            m = f"✅ {len(row['master_policies'])}" if row["master_policies"] else "⛔"
            q = f"✅ {len(row['qa_policies'])}"     if row["qa_policies"]     else "⛔"
            d = f"✅ {len(row['develop_policies'])}" if row["develop_policies"] else "⛔"
            st = {"OK": "✅ OK", "WARNING": "🟡 WARN", "ALERT": "🔴 ALERT"}[row["status"]]
            print(f"{idx:>4}  {row['repository']:<35} {m:^18} {q:^18} {d:^18} {st}")
        ok      = sum(1 for r in rows if r["status"] == STATUS_OK)
        warning = sum(1 for r in rows if r["status"] == STATUS_WARNING)
        alert   = sum(1 for r in rows if r["status"] == STATUS_ALERT)
        print(f"\nTotal: {len(rows)} | ✅ OK: {ok} | 🟡 WARNING: {warning} | 🔴 ALERT: {alert} | ⏱️ {elapsed:.2f}s\n")

    # ── 6. Exportar ───────────────────────────────────────────────────────────
    if args.output:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath   = export_results(rows, args.output, script_dir, tz_name)
        if filepath:
            msg = f"📁 Exportado: {filepath}"
            (console.print(f"[bold green]{msg}[/]\n") if console else print(msg))


if __name__ == "__main__":
    main()
