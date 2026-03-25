#!/usr/bin/env python3
"""
azdo_release_deep_dive.py

Deep-dive report para un Release Definition específico (por ID obligatorio).
Identifica el repositorio Git vinculado en los artefactos y ejecuta los
cuatro análisis del toolbox sobre esa combinación pipeline + repo:

  1. Pull Requests  — PRs activos hacia el target branch del repo vinculado
  2. Branch Policies— Políticas en master/QA/develop del repo vinculado
  3. CD Health      — Score de salud basado en últimos N releases
  4. Pipeline Drift — Cambios de stages/variables vs snapshot del último release

Uso:
  python azdo_release_deep_dive.py --release-id 42 --pat <PAT>

Autor: Harold Adrian
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from datetime import timezone as dt_tz
from typing import Any, Dict, List, Optional
from urllib.parse import quote

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None  # type: ignore

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__  = "Harold Adrian"

DEFAULT_ORG_URL  = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT  = "Compras.RMI"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_BRANCH   = "master"
DEFAULT_STAGE    = "validador"
DEFAULT_TOP      = 15

API_VERSION      = "7.1"
API_VERSION_DEFS = "7.2-preview.4"
API_VERSION_RELS = "7.2-preview.8"

BRANCH_ALIASES: Dict[str, List[str]] = {
    "master":  ["refs/heads/master", "refs/heads/main"],
    "qa":      ["refs/heads/qa", "refs/heads/QA"],
    "develop": ["refs/heads/develop", "refs/heads/dev", "refs/heads/development"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS
# ═══════════════════════════════════════════════════════════════════════════════
def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Deep-dive de un Release Definition por ID: PRs + Políticas + CD Health + Drift"
    )
    p.add_argument("--org", "-g", default=DEFAULT_ORG_URL,
                   help=f"URL de la organización (default: {DEFAULT_ORG_URL})")
    p.add_argument("--project", "-p", default=DEFAULT_PROJECT,
                   help=f"Nombre del proyecto (default: {DEFAULT_PROJECT})")
    p.add_argument("--pat", required=True,
                   help="PAT con permisos: Code (Read), Policy (Read), Release (Read)")
    p.add_argument("--release-id", "--id", dest="release_id", type=int, required=True,
                   help="ID de la Release Definition a analizar")
    p.add_argument("--branch", "-b", default=DEFAULT_BRANCH,
                   help=f"Branch destino para análisis de PRs (default: {DEFAULT_BRANCH})")
    p.add_argument("--stage-name", default=DEFAULT_STAGE,
                   help=f"Stage/environment a verificar en el pipeline (default: {DEFAULT_STAGE})")
    p.add_argument("--top", type=int, default=DEFAULT_TOP,
                   help=f"Últimos N releases para health/drift (default: {DEFAULT_TOP})")
    p.add_argument("--timezone", "-tz", default=DEFAULT_TIMEZONE,
                   help=f"Zona horaria para fechas (default: {DEFAULT_TIMEZONE})")
    p.add_argument("--output", "-o", choices=["json", "csv", "excel"], default=None,
                   help="Exportar resultados (json / csv / excel)")
    p.add_argument("--debug", action="store_true",
                   help="Mostrar errores HTTP detallados")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP
# ═══════════════════════════════════════════════════════════════════════════════
def make_headers(pat: str) -> Dict:
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def vsrm(org_url: str) -> str:
    return org_url.replace("dev.azure.com", "vsrm.dev.azure.com")


def api_get(
    url: str, headers: Dict, params: Dict = None, debug: bool = False
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
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception on {url}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# DATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=dt_tz.utc)
        except ValueError:
            continue
    return None


def format_date(s: str, tz_name: str) -> str:
    dt = parse_iso(s)
    if not dt:
        return "—"
    if ZoneInfo:
        try:
            dt = dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass
    return dt.strftime("%Y-%m-%d %H:%M")


def days_ago(s: str) -> float:
    dt = parse_iso(s)
    if not dt:
        return 9999.0
    return (datetime.now(dt_tz.utc) - dt).total_seconds() / 86400


# ═══════════════════════════════════════════════════════════════════════════════
# RELEASE DEFINITION & RELEASES
# ═══════════════════════════════════════════════════════════════════════════════
def get_release_definition(
    org: str, project: str, release_id: int,
    headers: Dict, debug: bool = False,
) -> Optional[Dict]:
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/definitions/{release_id}"
    return api_get(url, headers, {"api-version": API_VERSION_DEFS}, debug)


def get_releases(
    org: str, project: str, release_id: int, top: int,
    headers: Dict, debug: bool = False,
) -> List[Dict]:
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/releases"
    data = api_get(url, headers, {
        "api-version":  API_VERSION_RELS,
        "definitionId": release_id,
        "$top":         top,
        "$expand":      "environments",
    }, debug)
    return data.get("value", []) if data else []


# ═══════════════════════════════════════════════════════════════════════════════
# GIT — REPO, PRs, POLICIES
# ═══════════════════════════════════════════════════════════════════════════════
def get_repository_by_id(
    org: str, project: str, repo_id: str,
    headers: Dict, debug: bool = False,
) -> Optional[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories/{repo_id}"
    return api_get(url, headers, {"api-version": API_VERSION}, debug)


def get_pull_requests(
    org: str, project: str, repo_id: str,
    branch: str, top: int,
    headers: Dict, debug: bool = False,
) -> List[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories/{repo_id}/pullrequests"
    data = api_get(url, headers, {
        "api-version":                      API_VERSION,
        "searchCriteria.targetRefName":     f"refs/heads/{branch}",
        "searchCriteria.status":            "active",
        "$top":                             top,
    }, debug)
    return data.get("value", []) if data else []


def get_policy_configurations(
    org: str, project: str, headers: Dict, debug: bool = False
) -> List[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/policy/configurations"
    data = api_get(url, headers, {"api-version": API_VERSION, "$top": 1000}, debug)
    return data.get("value", []) if data else []


def policies_for_branch(
    repo_id: str, aliases: List[str], configs: List[Dict]
) -> List[str]:
    """Returns names of enabled policies that match repo_id + any branch alias."""
    seen: List[str] = []
    repo_lower = repo_id.lower()
    for cfg in configs:
        if not cfg.get("isEnabled"):
            continue
        for scope in cfg.get("settings", {}).get("scope", []):
            scope_repo = (scope.get("repositoryId") or "").lower()
            scope_ref  = (scope.get("refName") or "").lower()
            if scope_repo and scope_repo != repo_lower:
                continue
            if any(scope_ref == alias.lower() for alias in aliases):
                name = cfg.get("type", {}).get("displayName") or cfg.get("type", {}).get("id", "?")
                if name not in seen:
                    seen.append(name)
                break
    return seen


# ═══════════════════════════════════════════════════════════════════════════════
# CD HEALTH SCORING
# ═══════════════════════════════════════════════════════════════════════════════
def compute_health(releases: List[Dict], top: int) -> Dict:
    if not releases:
        return {"score": 0, "success_rate": 0.0, "last_success_days": None,
                "freq_per_week": 0.0, "total": 0, "succeeded": 0}

    total     = len(releases)
    succeeded = [r for r in releases if r.get("status") == "succeeded"]

    success_rate: float = len(succeeded) / total * 100

    last_success_days: Optional[float] = None
    for r in releases:
        if r.get("status") == "succeeded":
            fin = r.get("finishTime") or r.get("modifiedOn")
            if fin:
                last_success_days = days_ago(fin)
                break

    freq_per_week: float = 0.0
    dates = [parse_iso(r.get("createdOn") or "") for r in releases]
    dates = [d for d in dates if d is not None]
    if len(dates) >= 2:
        dates.sort()
        span_days = (dates[-1] - dates[0]).total_seconds() / 86400
        if span_days > 0:
            freq_per_week = (total - 1) / span_days * 7

    s_stability = success_rate
    if last_success_days is None:
        s_recency = 0
    elif last_success_days <= 7:
        s_recency = 100
    elif last_success_days <= 30:
        s_recency = 75
    elif last_success_days <= 90:
        s_recency = 40
    else:
        s_recency = 10
    s_freq  = min(100.0, freq_per_week / 3 * 100)
    score   = round(0.5 * s_stability + 0.3 * s_recency + 0.2 * s_freq)

    return {
        "score":            score,
        "success_rate":     round(success_rate, 1),
        "last_success_days": round(last_success_days, 1) if last_success_days is not None else None,
        "freq_per_week":    round(freq_per_week, 2),
        "total":            total,
        "succeeded":        len(succeeded),
    }


def score_color(score: int) -> str:
    if score >= 80:
        return "green"
    if score >= 50:
        return "yellow"
    return "red"


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE DRIFT
# ═══════════════════════════════════════════════════════════════════════════════
def extract_stage_names(obj: Dict) -> List[str]:
    return sorted(e.get("name", "") for e in obj.get("environments", []) if e.get("name"))


def extract_variables(obj: Dict) -> Dict[str, str]:
    return {
        k: (v.get("value", "") if isinstance(v, dict) else str(v))
        for k, v in obj.get("variables", {}).items()
    }


def compute_drift(current_def: Dict, last_release: Dict) -> List[Dict]:
    changes: List[Dict] = []

    cur_stages  = set(extract_stage_names(current_def))
    snap_stages = set(extract_stage_names(last_release))

    for name in cur_stages - snap_stages:
        changes.append({"kind": "stage",    "detail": f"+ Stage añadido: '{name}'"})
    for name in snap_stages - cur_stages:
        changes.append({"kind": "stage",    "detail": f"- Stage eliminado: '{name}'"})

    cur_vars  = extract_variables(current_def)
    snap_vars = extract_variables(last_release)

    for k in set(cur_vars) - set(snap_vars):
        changes.append({"kind": "var_add",  "detail": f"+ Variable nueva: '{k}'"})
    for k in set(snap_vars) - set(cur_vars):
        changes.append({"kind": "var_del",  "detail": f"- Variable eliminada: '{k}'"})
    for k in set(cur_vars) & set(snap_vars):
        if cur_vars[k] != snap_vars[k] and cur_vars[k] != "":
            changes.append({"kind": "var_chg", "detail": f"~ Variable '{k}' cambió valor"})

    return changes


# ═══════════════════════════════════════════════════════════════════════════════
# RICH OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════
def render_report(console: "Console", d: Dict, tz_name: str) -> None:
    rdef     = d["definition"]
    repo     = d.get("repo")
    prs      = d.get("prs", [])
    policies = d.get("policies", {})
    health   = d.get("health", {})
    drift    = d.get("drift", [])
    releases = d.get("releases", [])

    def_name    = rdef.get("name", "?")
    def_id      = rdef.get("id", "?")
    modified    = format_date(rdef.get("modifiedOn", ""), tz_name)
    modified_by = (rdef.get("modifiedBy") or {}).get("displayName", "?")
    repo_name   = repo.get("name", "?") if repo else "[dim]No vinculado[/]"
    repo_branch = d.get("artifact_branch", "?")

    console.rule(f"[bold cyan]🚀 Release Deep Dive — {def_name}  (ID: {def_id})[/]")
    console.print(
        f"  [dim]Modificado:[/] {modified}  [dim]por[/] {modified_by}\n"
        f"  [dim]Repo vinculado:[/] [bold white]{repo_name}[/]  "
        f"[dim]artifact branch:[/] {repo_branch}\n"
    )

    # ── Stages ───────────────────────────────────────────────────────────────
    envs          = sorted(rdef.get("environments", []), key=lambda e: e.get("rank", 99))
    stage_keyword = d.get("stage_name", "").lower()

    ts = Table(
        title="Stages / Environments",
        box=box.SIMPLE_HEAVY, border_style="dim",
        show_header=True, header_style="bold cyan",
    )
    ts.add_column("Rank",          width=5, justify="right")
    ts.add_column("Stage",         min_width=24)
    ts.add_column("Pre-Aprov.",    justify="center", width=11)
    ts.add_column("Post-Aprov.",   justify="center", width=12)
    ts.add_column(f"'{d.get('stage_name', '')}'", justify="center", width=10)
    for env in envs:
        pre  = [a for a in env.get("preDeployApprovals",  {}).get("approvals", []) if not a.get("isAutomated")]
        post = [a for a in env.get("postDeployApprovals", {}).get("approvals", []) if not a.get("isAutomated")]
        hit  = "✅" if stage_keyword and stage_keyword in env.get("name", "").lower() else ""
        ts.add_row(str(env.get("rank", "?")), env.get("name", "?"), str(len(pre)), str(len(post)), hit)
    console.print(ts)

    # ── Pull Requests ─────────────────────────────────────────────────────────
    pr_branch = d.get("branch", DEFAULT_BRANCH)
    if prs:
        tp = Table(
            title=f"Pull Requests activos → {pr_branch}",
            box=box.SIMPLE_HEAVY, border_style="dim",
            show_header=True, header_style="bold cyan",
        )
        tp.add_column("PR#",   width=6,  justify="right")
        tp.add_column("Título",  min_width=38)
        tp.add_column("Autor",   min_width=22)
        tp.add_column("Fecha",   width=18, justify="center")
        for pr in prs:
            tp.add_row(
                str(pr.get("pullRequestId", "?")),
                pr.get("title", ""),
                (pr.get("createdBy") or {}).get("displayName", "?"),
                format_date(pr.get("creationDate", ""), tz_name),
            )
        console.print(tp)
    else:
        console.print(f"  [dim]✅ Sin PRs activos hacia '{pr_branch}'[/]\n")

    # ── Branch Policies ───────────────────────────────────────────────────────
    def _pol_cell(names: List[str]) -> str:
        if not names:
            return "[red]❌ Sin políticas[/]"
        label = ", ".join(names[:2]) + ("…" if len(names) > 2 else "")
        return f"[green]✅ {len(names)}[/] [dim]({label})[/]"

    tpo = Table(
        title="Branch Policies",
        box=box.SIMPLE_HEAVY, border_style="dim",
        show_header=True, header_style="bold cyan",
    )
    tpo.add_column("Rama",    min_width=16)
    tpo.add_column("Estado",  min_width=50)
    tpo.add_row("master / main", _pol_cell(policies.get("master",  [])))
    tpo.add_row("QA",            _pol_cell(policies.get("qa",      [])))
    tpo.add_row("develop",       _pol_cell(policies.get("develop", [])))
    console.print(tpo)

    # ── CD Health ─────────────────────────────────────────────────────────────
    score   = health.get("score", 0)
    sc_col  = score_color(score)
    last_ok = health.get("last_success_days")
    last_ok_str = f"{last_ok} días" if last_ok is not None else "—"
    console.print(Panel(
        f"[bold {sc_col}]Score: {score}/100[/]\n\n"
        f"  Estabilidad:  [cyan]{health.get('succeeded', 0)}/{health.get('total', 0)}[/] éxitos "
        f"([bold]{health.get('success_rate', 0)}%[/])\n"
        f"  Último éxito: {last_ok_str}\n"
        f"  Frecuencia:   {health.get('freq_per_week', 0)} deploys/semana",
        title=f"❤️  CD Health  (últimos {d.get('top', DEFAULT_TOP)} releases)",
        border_style=sc_col,
        expand=False,
    ))

    # ── Recent Releases ───────────────────────────────────────────────────────
    if releases:
        STATUS_COLOR = {
            "succeeded": "green", "failed": "red",
            "inProgress": "yellow", "partiallySucceeded": "yellow",
        }
        tr = Table(
            title=f"Últimos {len(releases)} Releases",
            box=box.SIMPLE_HEAVY, border_style="dim",
            show_header=True, header_style="bold cyan",
        )
        tr.add_column("ID",     width=7,  justify="right")
        tr.add_column("Nombre", min_width=38)
        tr.add_column("Estado", width=22)
        tr.add_column("Fecha",  width=18, justify="center")
        for r in releases[:10]:
            rstat = r.get("status", "?")
            col   = STATUS_COLOR.get(rstat, "white")
            tr.add_row(
                str(r.get("id", "?")),
                r.get("name", "?"),
                f"[{col}]{rstat}[/{col}]",
                format_date(r.get("createdOn", ""), tz_name),
            )
        console.print(tr)

    # ── Pipeline Drift ────────────────────────────────────────────────────────
    if not drift:
        console.print(Panel(
            "[green]✅ Sin drift detectado[/] — el pipeline coincide con el último release.",
            title="🔍 Pipeline Drift",
            border_style="green",
            expand=False,
        ))
    else:
        sev_col   = "red" if len(drift) >= 5 else "yellow" if len(drift) >= 2 else "dim"
        drift_txt = "\n".join(f"  • {c['detail']}" for c in drift)
        console.print(Panel(
            f"[{sev_col}]{len(drift)} cambio(s) detectado(s):[/]\n\n{drift_txt}",
            title="🔍 Pipeline Drift",
            border_style=sev_col,
            expand=False,
        ))


def render_fallback(d: Dict, tz_name: str) -> None:
    rdef   = d["definition"]
    health = d.get("health", {})
    drift  = d.get("drift", [])
    prs    = d.get("prs", [])
    sep    = "=" * 60
    print(f"\n{sep}")
    print(f"  Release Definition: {rdef.get('name')} (ID: {rdef.get('id')})")
    print(sep)
    print(f"  PRs activos → {d.get('branch', DEFAULT_BRANCH)}: {len(prs)}")
    print(f"  CD Health Score: {health.get('score', 0)}/100  "
          f"(success rate: {health.get('success_rate', 0)}%  "
          f"total: {health.get('total', 0)})")
    print(f"  Pipeline Drift:  {len(drift)} cambio(s)")
    for c in drift:
        print(f"    {c['detail']}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
def export_results(d: Dict, fmt: str, tz_name: str) -> None:
    ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
    def_id      = d["definition"].get("id", "unknown")
    outcome_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outcome")
    os.makedirs(outcome_dir, exist_ok=True)
    base = os.path.join(outcome_dir, f"release_deep_dive_{def_id}_{ts}")

    rows: List[Dict] = []
    for pr in d.get("prs", []):
        rows.append({
            "section": "PR",
            "id":      pr.get("pullRequestId"),
            "name":    pr.get("title", ""),
            "author":  (pr.get("createdBy") or {}).get("displayName", ""),
            "date":    format_date(pr.get("creationDate", ""), tz_name),
            "detail":  "",
        })
    for env_name, names in d.get("policies", {}).items():
        rows.append({
            "section": "Policy",
            "id":      None,
            "name":    env_name,
            "author":  "",
            "date":    "",
            "detail":  ", ".join(names) if names else "Sin políticas",
        })
    h = d.get("health", {})
    rows.append({
        "section": "Health",
        "id":      d["definition"].get("id"),
        "name":    f"Score: {h.get('score', 0)}/100",
        "author":  "",
        "date":    "",
        "detail":  (f"success_rate={h.get('success_rate')}%  "
                    f"freq={h.get('freq_per_week')} dep/wk  "
                    f"total={h.get('total')}"),
    })
    for c in d.get("drift", []):
        rows.append({
            "section": "Drift",
            "id":      None,
            "name":    c["kind"],
            "author":  "",
            "date":    "",
            "detail":  c["detail"],
        })

    try:
        if fmt == "json":
            import json
            path = base + ".json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
            print(f"✅ Exportado: {path}")
        elif fmt == "csv":
            import csv
            path = base + ".csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["section", "id", "name", "author", "date", "detail"])
                writer.writeheader()
                writer.writerows(rows)
            print(f"✅ Exportado: {path}")
        elif fmt == "excel":
            import pandas as pd  # type: ignore
            path = base + ".xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, engine="openpyxl", sheet_name="Deep Dive")
            print(f"✅ Exportado: {path}")
    except Exception as e:
        print(f"⚠️  Error al exportar: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    if not REQUESTS_AVAILABLE:
        sys.exit("❌ Instala requests: pip install requests")

    args    = get_args()
    headers = make_headers(args.pat)
    console = Console() if RICH_AVAILABLE else None
    tz_name = args.timezone
    start   = time.time()

    # ── 1. Release Definition ─────────────────────────────────────────────────
    if console:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task(f"Obteniendo Release Definition {args.release_id}…", total=None)
            rdef = get_release_definition(args.org, args.project, args.release_id, headers, args.debug)
            p.update(t, description=f"✅ {rdef.get('name', '?')}" if rdef else "❌ No encontrada")
    else:
        rdef = get_release_definition(args.org, args.project, args.release_id, headers, args.debug)

    if not rdef:
        msg = f"❌ Release Definition {args.release_id} no encontrada. Verifica --release-id, --project y --pat."
        (console.print(f"[red]{msg}[/]") if console else print(msg))
        sys.exit(1)

    # ── 2. Linked Git repo from artifacts ─────────────────────────────────────
    repo_id: Optional[str] = None
    artifact_branch: str   = args.branch

    for artifact in rdef.get("artifacts", []):
        if artifact.get("type") == "Git":
            dr       = artifact.get("definitionReference", {})
            repo_ref = dr.get("repository", {})
            if not repo_ref:
                repo_ref = dr.get("definition", {})
            repo_id  = repo_ref.get("id")
            br_ref   = dr.get("branch", dr.get("branches", {}))
            artifact_branch = (br_ref.get("name") or br_ref.get("id") or args.branch).replace("refs/heads/", "")
            break

    repo: Optional[Dict] = None
    if repo_id:
        repo = get_repository_by_id(args.org, args.project, repo_id, headers, args.debug)

    if not repo_id:
        msg = "⚠️  No se encontró un artefacto Git en esta Release Definition. Políticas y PRs no estarán disponibles."
        (console.print(f"[yellow]{msg}[/]") if console else print(msg))

    # ── 3. Parallel data fetch ────────────────────────────────────────────────
    def _fetch_prs() -> List[Dict]:
        if not repo_id:
            return []
        return get_pull_requests(args.org, args.project, repo_id, args.branch, 50, headers, args.debug)

    def _fetch_policies() -> Dict[str, List[str]]:
        if not repo_id:
            return {"master": [], "qa": [], "develop": []}
        confs = get_policy_configurations(args.org, args.project, headers, args.debug)
        return {
            branch: policies_for_branch(repo_id, aliases, confs)
            for branch, aliases in BRANCH_ALIASES.items()
        }

    def _fetch_releases() -> List[Dict]:
        return get_releases(args.org, args.project, args.release_id, args.top, headers, args.debug)

    if console:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task("Descargando datos en paralelo…", total=None)
            with ThreadPoolExecutor(max_workers=3) as ex:
                f_prs      = ex.submit(_fetch_prs)
                f_policies = ex.submit(_fetch_policies)
                f_releases = ex.submit(_fetch_releases)
                prs           = f_prs.result()
                policies_data = f_policies.result()
                recent_rels   = f_releases.result()
            p.update(t, description=(
                f"✅ {len(prs)} PRs · "
                f"{sum(len(v) for v in policies_data.values())} políticas · "
                f"{len(recent_rels)} releases"
            ))
    else:
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_prs      = ex.submit(_fetch_prs)
            f_policies = ex.submit(_fetch_policies)
            f_releases = ex.submit(_fetch_releases)
            prs           = f_prs.result()
            policies_data = f_policies.result()
            recent_rels   = f_releases.result()

    # ── 4. Health + Drift ─────────────────────────────────────────────────────
    health = compute_health(recent_rels, args.top)

    drift_changes: List[Dict] = []
    if recent_rels:
        last_release = recent_rels[0]
        drift_changes = compute_drift(rdef, last_release)

    data: Dict = {
        "definition":     rdef,
        "repo":           repo,
        "artifact_branch": artifact_branch,
        "branch":         args.branch,
        "stage_name":     args.stage_name,
        "top":            args.top,
        "prs":            prs,
        "policies":       policies_data,
        "health":         health,
        "drift":          drift_changes,
        "releases":       recent_rels,
        "elapsed":        round(time.time() - start, 2),
    }

    # ── 5. Output ─────────────────────────────────────────────────────────────
    if console:
        render_report(console, data, tz_name)
        console.print(f"\n[dim]⏱️  Completado en {data['elapsed']}s[/]\n")
    else:
        render_fallback(data, tz_name)

    # ── 6. Export ─────────────────────────────────────────────────────────────
    if args.output:
        export_results(data, args.output, tz_name)


if __name__ == "__main__":
    main()
