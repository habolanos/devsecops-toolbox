#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_branch_lock_checker.py

Lista todas las ramas bloqueadas (isLocked=true) en todos los
repositorios de un proyecto Azure DevOps.

Columnas mostradas:
  # | Repositorio | Rama | Bloqueado por

El repositorio se repite por cada rama bloqueada que tenga.
Si un repo no tiene ninguna rama bloqueada no aparece en el resultado.

Flags opcionales:
  --repo     Filtrar por nombre de repositorio (substring, case insensitive)
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
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
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
__author__  = "Harold Adrian"

# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULT_ORG_URL  = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT  = "Compras.RMI"
DEFAULT_TIMEZONE = "America/Mazatlan"
API_VERSION      = "7.1"


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS
# ═══════════════════════════════════════════════════════════════════════════════
def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lista todas las ramas bloqueadas (isLocked) en los repos de AzDO"
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
        help="Personal Access Token con permisos: Code (Read)"
    )
    parser.add_argument(
        "--repo", "-r",
        default=None,
        help="Filtrar por nombre de repositorio (substring, case insensitive)"
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
        "Content-Type":  "application/json",
        "Accept":        "application/json",
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
            label = url.split("/_apis")[0].split("/")[-1] if "/_apis" in url else url
            print(f"  ⚠  HTTP {resp.status_code} ({label})")
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


def get_refs(
    org: str, project: str, repo_id: str, headers: Dict, debug: bool = False
) -> List[Dict]:
    """Obtiene todas las refs (ramas) de un repositorio."""
    url    = f"{org}/{quote(project, safe='')}/_apis/git/repositories/{repo_id}/refs"
    params = {
        "api-version": API_VERSION,
        "filter":      "heads/",
        "$top":        1000,
    }
    data = api_get(url, headers, params, debug)
    return data.get("value", []) if data else []


# ═══════════════════════════════════════════════════════════════════════════════
# LOCK LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def extract_locked_branches(refs: List[Dict]) -> List[Dict]:
    """
    Filtra refs con isLocked=True.
    Retorna lista de dicts con: branch, bloqueada, creador, locked_by.
    """
    locked = []
    for ref in refs:
        if not ref.get("isLocked", False):
            continue
        name      = ref.get("name", "")
        branch    = name.removeprefix("refs/heads/") if name.startswith("refs/heads/") else name
        creator   = ref.get("creator", {})
        creador   = (
            creator.get("displayName")
            or creator.get("uniqueName")
            or creator.get("id")
            or "—"
        )
        locked_by_obj = ref.get("isLockedBy", {})
        locked_by     = (
            locked_by_obj.get("displayName")
            or locked_by_obj.get("uniqueName")
            or locked_by_obj.get("id")
            or "—"
        )
        locked.append({
            "branch":    branch,
            "bloqueada": "🔒 Sí",
            "creador":   creador,
            "locked_by": locked_by,
        })
    return locked


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT — RICH
# ═══════════════════════════════════════════════════════════════════════════════
def print_rich_table(console: "Console", rows: List[Dict]):
    table = Table(
        title="🔒  Branch Lock Checker — Ramas bloqueadas",
        title_style="bold cyan",
        header_style="bold white",
        border_style="dim",
        box=box.ROUNDED,
        show_lines=False,
    )
    table.add_column("#",           style="dim",         width=4,   justify="right")
    table.add_column("Proyecto",    style="dim cyan",     min_width=18)
    table.add_column("Repositorio", style="bold white",   min_width=28)
    table.add_column("Rama",        style="bold yellow",  min_width=25)
    table.add_column("Bloqueada",   justify="center",     width=10)
    table.add_column("Creador",     style="cyan",         min_width=22)
    table.add_column("URL Repo",    style="dim blue",     min_width=30)

    for idx, row in enumerate(rows, 1):
        table.add_row(
            str(idx),
            row["proyecto"],
            row["repository"],
            row["branch"],
            row["bloqueada"],
            row["creador"],
            row["url_repo"],
        )

    console.print(table)
    console.print()


def print_rich_summary(console: "Console", rows: List[Dict], repos_total: int, elapsed: float):
    repos_with_locks = len({r["repository"] for r in rows})
    repos_clean      = repos_total - repos_with_locks

    console.print(Panel(
        f"[bold white]📋 Repositorios analizados:[/]  [cyan]{repos_total}[/]\n"
        f"[bold red]🔒 Ramas bloqueadas:[/]         [red]{len(rows)}[/]\n"
        f"[bold yellow]📁 Repos con locks:[/]          [yellow]{repos_with_locks}[/]\n"
        f"[bold green]✅ Repos sin locks:[/]          [green]{repos_clean}[/]\n"
        f"[dim]⏱️  Tiempo: {elapsed:.2f}s[/]",
        title="📊 Resumen",
        border_style="blue",
        expand=False,
    ))
    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT — FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
def print_plain_table(rows: List[Dict], repos_total: int, elapsed: float):
    hdr = f"{'#':>4}  {'Proyecto':<20} {'Repositorio':<30} {'Rama':<28} {'Bloq':^6} {'Creador':<25} URL Repo"
    sep = "=" * len(hdr)
    print(f"\n{sep}")
    print(hdr)
    print(sep)
    for idx, row in enumerate(rows, 1):
        print(f"{idx:>4}  {row['proyecto']:<20} {row['repository']:<30} {row['branch']:<28} "
              f"{'SI':^6} {row['creador']:<25} {row['url_repo']}")
    repos_with_locks = len({r["repository"] for r in rows})
    print(f"\nTotal: {len(rows)} ramas bloqueadas | "
          f"Repos con locks: {repos_with_locks}/{repos_total} | "
          f"\u23f1\ufe0f {elapsed:.2f}s\n")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
def export_results(
    rows: List[Dict],
    output_format: str,
    tz_name: str,
) -> Optional[str]:
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    export_fields = ["proyecto", "repository", "branch", "bloqueada", "creador", "locked_by", "url_repo"]

    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"branch_locks_{ts}.json")
        payload  = {
            "metadata": {
                "tool":         "azdo_branch_lock_checker",
                "version":      __version__,
                "generated_at": datetime.now(ZoneInfo(tz_name)).isoformat(),
            },
            "total_locked_branches": len(rows),
            "repos_with_locks":      len({r["repository"] for r in rows}),
            "data": [{f: r.get(f, "") for f in export_fields} for r in rows],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath

    elif output_format == "csv":
        if not rows:
            return None
        filepath = os.path.join(outcome_dir, f"branch_locks_{ts}.csv")
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=export_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return filepath

    elif output_format == "excel":
        try:
            import pandas as pd
            filepath = os.path.join(outcome_dir, f"branch_locks_{ts}.xlsx")
            flat = [{f: r.get(f, "") for f in export_fields} for r in rows]
            pd.DataFrame(flat).to_excel(filepath, index=False, engine="openpyxl")
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
            f"[bold cyan]🔒  Branch Lock Checker[/]\n"
            f"[dim]🕐 {revision_time}[/]\n"
            f"[dim]🏢 Organización: {args.org}[/]\n"
            f"[dim]📁 Proyecto:     {args.project}[/]",
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

    repos_total = len(repos)

    # ── 2. Refs por repo ─────────────────────────────────────────────────────
    rows: List[Dict] = []

    if RICH_AVAILABLE and console:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as p:
            t = p.add_task("Consultando refs...", total=repos_total)
            for repo in repos:
                p.update(t, description=f"[dim]{repo['name'][:40]}[/]")
                refs   = get_refs(args.org, args.project, repo["id"], headers, args.debug)
                locked = extract_locked_branches(refs)
                for lb in locked:
                    rows.append({
                        "proyecto":    args.project,
                        "repository":  repo["name"],
                        "branch":      lb["branch"],
                        "bloqueada":   lb["bloqueada"],
                        "creador":     lb["creador"],
                        "locked_by":   lb["locked_by"],
                        "url_repo":    repo.get("webUrl", repo.get("remoteUrl", "")),
                    })
                p.advance(t)
            p.update(t, description=f"✅ {repos_total} repos procesados")
        console.print()
    else:
        for repo in repos:
            print(f"  Consultando {repo['name']}...", end="\r")
            refs   = get_refs(args.org, args.project, repo["id"], headers, args.debug)
            locked = extract_locked_branches(refs)
            for lb in locked:
                rows.append({
                    "proyecto":   args.project,
                    "repository": repo["name"],
                    "branch":     lb["branch"],
                    "bloqueada":  lb["bloqueada"],
                    "creador":    lb["creador"],
                    "locked_by":  lb["locked_by"],
                    "url_repo":   repo.get("webUrl", repo.get("remoteUrl", "")),
                })
        print()

    elapsed = time.time() - start_time

    # ── 3. Mostrar resultado ──────────────────────────────────────────────────
    if not rows:
        msg = "✅ No se encontraron ramas bloqueadas."
        (console.print(f"[bold green]{msg}[/]\n") if console else print(msg))
        if RICH_AVAILABLE and console:
            print_rich_summary(console, rows, repos_total, elapsed)
        return

    # Ordenar: repo asc → branch asc
    rows.sort(key=lambda r: (r["repository"].lower(), r["branch"].lower()))

    if RICH_AVAILABLE and console:
        print_rich_table(console, rows)
        print_rich_summary(console, rows, repos_total, elapsed)
    else:
        print_plain_table(rows, repos_total, elapsed)

    # ── 4. Exportar ───────────────────────────────────────────────────────────
    if args.output:
        filepath = export_results(rows, args.output, tz_name)
        if filepath:
            msg = f"📁 Exportado: {filepath}"
            (console.print(f"[bold green]{msg}[/]\n") if console else print(msg))


if __name__ == "__main__":
    main()
