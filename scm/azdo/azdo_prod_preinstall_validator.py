#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_prod_preinstall_validator.py

Pre-validacion de instalaciones al stage Production: identifica los Pull
Requests a master ya aplicados cuyo release tiene Production pendiente
(en progreso o no instalado), evaluando el stage Validator (si existe o
fue ejecutado) con la misma logica de violaciones de la opcion 44.

Flujo:
  1. Lista los pipeline CD con artifact tipo Git en rama master.
  2. Por CD toma los releases recientes y excluye los que ya tienen el
     stage Production instalado (deployStep succeeded/partiallySucceeded).
  3. De cada release pendiente extrae: Build artifact (build id/numero y
     rama refs/pull/N/merge → PR a master), artifact Git (repo + commit),
     commit de properties (commitPropertiesRollback) y RELEASE_ID.
  4. Extrae los logs de todas las tareas del stage Validator y evalua las
     violaciones como la opcion 44 (reglas ##[SEV] RULE_*) mas los issues
     genericos de tarea (##[warning]/##[error] sueltos).
  5. Calcula el health score del CD (formula opcion 3: recencia +
     estabilidad + definicion) y el snapshot de stages (estilo Deep Dive).
  6. Imprime el listado detallado de PRs a master en progreso para
     instalarse en Production: Build ID, commit Git, score, commit
     properties, rollback (build id, commit Git, commit properties) y el
     detalle de violaciones por release.

Uso:
    python azdo_prod_preinstall_validator.py --pat $PAT
    python azdo_prod_preinstall_validator.py --pat $PAT --top-releases 20
"""

import argparse
import base64
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import (BarColumn, Progress, SpinnerColumn,
                               TaskProgressColumn, TextColumn)

    from rich import box
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None

__version__ = "1.0.3"
__author__ = "Harold Adrian"

DEFAULT_ORG_URL = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT = "Cadena_de_Suministros"
API_VERSION = "7.1"
API_VERSION_REL = "7.2-preview.8"
API_VERSION_DEF = "7.2-preview.4"
GIT_ARTIFACT_TYPES = ("git", "github", "externalgit", "tfvc")
TOP_PR_SEARCH = 200
MAX_PR_PAGES = 5
SEV_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4,
             "WARNING": 2, "ERROR": 1}

# Iconos ASCII-safe (cp1252-safe en consolas legacy)
_UTF8 = "utf" in ((getattr(sys.stdout, "encoding", "") or "").lower())
ICON_OK = "✅" if _UTF8 else "[OK]"
ICON_WARN = "⚠" if _UTF8 else "!"
ICON_ERR = "❌" if _UTF8 else "[X]"
ICON_PEND = "⏳" if _UTF8 else "..."
ICON_SKIP = "—" if _UTF8 else "-"

SEV_STYLE = {"CRITICAL": "bold white on red", "HIGH": "bold red",
             "MEDIUM": "yellow", "LOW": "cyan", "INFO": "dim",
             "WARNING": "yellow", "ERROR": "bold red"}


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS / HTTP
# ═══════════════════════════════════════════════════════════════════════════════
def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Pre-valida PRs a master pendientes de instalar en "
                    "el stage Production de su pipeline CD")
    p.add_argument("--pat", required=True)
    p.add_argument("--org", default=DEFAULT_ORG_URL)
    p.add_argument("--project", default=DEFAULT_PROJECT)
    p.add_argument("--master-branch", default="master",
                   help="Rama master del artifact Git del CD (default: master)")
    p.add_argument("--prod-stage", default="Production",
                   help="Nombre del stage de produccion (default: Production)")
    p.add_argument("--validator-stage", default="Validator",
                   help="Nombre del stage validador (default: Validator)")
    p.add_argument("--top-releases", type=int, default=10,
                   help="Releases recientes a revisar por CD (default: 10)")
    p.add_argument("--threads", type=int, default=20,
                   help="Workers paralelos: detalle de definiciones y "
                        "análisis por CD (default: 20)")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def make_headers(pat: str) -> Dict[str, str]:
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}",
            "Accept": "application/json"}


def vsrm(org_url: str) -> str:
    if "vsrm.dev.azure.com" in org_url:
        return org_url
    return org_url.replace("dev.azure.com", "vsrm.dev.azure.com")


def api_get(url: str, headers: Dict, params: Dict = None,
            debug: bool = False) -> Optional[Any]:
    try:
        r = requests.get(url, headers=headers, params=params, timeout=40)
        if r.status_code >= 400 and debug:
            print(f"[DEBUG] HTTP {r.status_code} {url}\n{r.text[:300]}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if debug:
            print(f"[DEBUG] {url}: {e}")
        return None


def api_get_text(url: str, headers: Dict,
                 debug: bool = False) -> Optional[str]:
    try:
        r = requests.get(url, headers=headers, timeout=40)
        if r.status_code >= 400 and debug:
            print(f"[DEBUG] HTTP {r.status_code} {url}")
        r.raise_for_status()
        return r.text
    except Exception as e:
        if debug:
            print(f"[DEBUG] {url}: {e}")
        return None


def _print(msg: str = "") -> None:
    if RICH and console:
        console.print(msg)
    else:
        print(re.sub(r"\[/?[a-zA-Z0-9_# =]+\]", "", str(msg)))


def normalize_name(name: str) -> str:
    return (name or "").lower().replace(" ", "").replace("-", "") \
        .replace("_", "")


# ═══════════════════════════════════════════════════════════════════════════════
# API: definiciones, releases, PRs
# ═══════════════════════════════════════════════════════════════════════════════
def get_release_defs_list(org, project, headers, debug) -> List[Dict]:
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/definitions"
    data = api_get(url, headers, {"api-version": API_VERSION_DEF,
                                   "$top": 500}, debug)
    return data.get("value", []) if data else []


def get_def_detail(org, project, def_id, headers, debug) -> Optional[Dict]:
    url = (f"{vsrm(org)}/{quote(project, safe='')}"
           f"/_apis/release/definitions/{def_id}")
    return api_get(url, headers, {"api-version": API_VERSION_DEF}, debug)


def get_releases(org, project, def_id, top, headers, debug) -> List[Dict]:
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/releases"
    data = api_get(url, headers, {
        "api-version": API_VERSION_REL,
        "definitionId": def_id, "$top": top,
        "$expand": "environments,artifacts",
    }, debug)
    return data.get("value", []) if data else []


def get_release_detail(org, project, rel_id, headers, debug) -> Optional[Dict]:
    url = (f"{vsrm(org)}/{quote(project, safe='')}"
           f"/_apis/release/releases/{rel_id}")
    return api_get(url, headers, {"api-version": API_VERSION_REL}, debug)


def get_repositories(org, project, headers, debug) -> List[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories"
    data = api_get(url, headers, {"api-version": API_VERSION}, debug)
    return data.get("value", []) if data else []


def get_pull_request(org, project, repo_id, pr_id, headers,
                     debug) -> Optional[Dict]:
    """PR por id en el repo del componente."""
    if not repo_id or not pr_id:
        return None
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(str(repo_id), safe='')}/pullrequests/{pr_id}")
    return api_get(url, headers, {"api-version": API_VERSION}, debug)


def pr_definitive_commit(pr: Optional[Dict]) -> str:
    return ((pr or {}).get("lastMergeCommit") or {}).get("commitId", "") or ""


def find_pr_for_commit(org, project, repo_id, commit, headers, debug,
                       target_branch: str = "") -> Optional[Dict]:
    """Scan paginado de PRs completados cuyo lastMergeCommit coincida,
    filtrando por la rama destino (ej: master)."""
    if not repo_id or not commit:
        return None
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(repo_id, safe='')}/pullrequests")
    base = {"api-version": API_VERSION,
            "searchCriteria.status": "completed",
            "$top": TOP_PR_SEARCH}
    if target_branch:
        base["searchCriteria.targetRefName"] = f"refs/heads/{target_branch}"
    for page in range(MAX_PR_PAGES):
        base["$skip"] = page * TOP_PR_SEARCH
        data = api_get(url, headers, base, debug)
        values = (data or {}).get("value", []) or []
        for pr in values:
            c = pr_definitive_commit(pr)
            if c and c.lower() == commit.lower():
                return pr
        if len(values) < TOP_PR_SEARCH:
            break
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Artifacts del release (Build + Git source) — misma logica de la opcion 47
# ═══════════════════════════════════════════════════════════════════════════════
def extract_artifacts(rel: Dict) -> Tuple[Optional[Dict], List[Dict]]:
    """(build_art, [git_arts]) del release."""
    build_art = None
    git_arts = []
    for a in rel.get("artifacts", []) or []:
        t = (a.get("type") or "").lower()
        if t == "build" and build_art is None:
            build_art = a
        elif t in GIT_ARTIFACT_TYPES:
            git_arts.append(a)
    if build_art is None:
        arts = rel.get("artifacts", []) or []
        if arts:
            build_art = arts[0]
    return build_art, git_arts


def build_artifact_info(art: Optional[Dict]) -> Dict[str, str]:
    """Build artifact: build_id, build_number, branch (refs/pull/N/merge)."""
    info = {"build_id": "", "build_number": "", "branch": ""}
    if not art:
        return info
    ref = art.get("definitionReference", {}) or {}
    ver = ref.get("version") or {}
    info["build_id"] = str(ver.get("id", "") or "")
    info["build_number"] = ver.get("name", "") or ""
    br = (ref.get("branch") or {}).get("id", "") \
        or (ref.get("branches") or {}).get("id", "")
    info["branch"] = br
    return info


def git_artifact_info(art: Optional[Dict]) -> Dict[str, str]:
    """Git artifact: repo del componente + commit de los fuentes + rama."""
    info = {"repo_id": "", "repo_name": "", "commit": "", "branch": ""}
    if not art:
        return info
    ref = art.get("definitionReference", {}) or {}
    repo = ref.get("repository") or (ref.get("definition") or {})
    info["repo_id"] = repo.get("id", "") or ""
    info["repo_name"] = repo.get("name", "") or ""
    ver = ref.get("version") or {}
    info["commit"] = ver.get("id", "") \
        or (ref.get("sourceVersion") or {}).get("id", "") or ""
    info["branch"] = (ref.get("branch") or {}).get("id", "") \
        or (ref.get("branches") or {}).get("id", "")
    return info


def pr_id_from_build_branch(branch_ref: str) -> Optional[int]:
    """refs/pull/176004/merge → 176004 (PR a master que disparo el CI)."""
    m = re.match(r"refs/pull/(\d+)/(?:merge|head)", branch_ref or "")
    return int(m.group(1)) if m else None


# ═══════════════════════════════════════════════════════════════════════════════
# Filtro de CDs: artifact tipo Git con branch master
# ═══════════════════════════════════════════════════════════════════════════════
def cd_master_git_artifact(def_detail: Dict,
                           master_branch: str) -> Optional[Dict]:
    """Artifact Git del CD cuyo branch es master (el source repository)."""
    for a in def_detail.get("artifacts", []) or []:
        if (a.get("type") or "").lower() not in GIT_ARTIFACT_TYPES:
            continue
        gi = git_artifact_info(a)
        if gi["branch"].lower() == (master_branch or "").lower():
            return gi
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Stages del release (Deep Dive compacto)
# ═══════════════════════════════════════════════════════════════════════════════
def stage_env(rel: Dict, stage_name: str) -> Optional[Dict]:
    target = normalize_name(stage_name)
    for env in rel.get("environments", []) or []:
        if normalize_name(env.get("name", "")) == target:
            return env
    return None


def stage_snapshot(rel: Dict) -> List[Tuple[str, str, str]]:
    """[(stage, status, attempts)] para el snapshot estilo Deep Dive."""
    out = []
    for env in rel.get("environments", []) or []:
        steps = env.get("deploySteps", []) or []
        out.append((env.get("name", "?"), env.get("status", ""),
                    str(len(steps))))
    return out


def prod_installed(prod_env: Optional[Dict]) -> bool:
    """Production instalado: algun deployStep exitoso."""
    if not prod_env:
        return False
    ok = ("succeeded", "partiallysucceeded")
    for step in prod_env.get("deploySteps", []) or []:
        if (step.get("deploymentStatus") or "").lower() in ok:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Health score del CD (formula opcion 3)
# ═══════════════════════════════════════════════════════════════════════════════
def parse_azdo_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def analyze_prod_deploy(releases: List[Dict],
                        prod_stage: str) -> Dict[str, Any]:
    """Ultimo deploy exitoso a prod + intentos del release mas reciente."""
    result = {"last_prod_deploy": None, "prod_ever_deployed": False,
              "last_attempts": None}
    if not releases or not prod_stage:
        return result
    prod_norm = normalize_name(prod_stage)
    ok = {"succeeded", "partiallysucceeded"}
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    latest = releases[0]
    for env in latest.get("environments", []) or []:
        if normalize_name(env.get("name", "")) == prod_norm:
            result["last_attempts"] = len(env.get("deploySteps", []) or [])
            break
    for rel in releases:
        for env in rel.get("environments", []) or []:
            if normalize_name(env.get("name", "")) != prod_norm:
                continue
            for step in reversed(env.get("deploySteps", []) or []):
                if (step.get("deploymentStatus") or "").lower() in ok:
                    dt = parse_azdo_date(step.get("lastModifiedOn")
                                         or step.get("requestedOn"))
                    result["prod_ever_deployed"] = True
                    if dt and dt >= one_year_ago:
                        result["last_prod_deploy"] = dt
                    return result
    return result


def compute_score(last_prod_deploy, prod_attempts, modified_on) -> Dict:
    """Score 0-100: recencia (0-70) + estabilidad deploy (0-20) +
    estabilidad definicion (0-10). Nunca desplegado → 0."""
    if last_prod_deploy is None:
        return {"total": 0, "recency": 0, "stability": 0, "definition": 0,
                "days": None, "ever": False}
    days = max(0, (datetime.now(timezone.utc) - last_prod_deploy).days)
    recency = max(0.0, 70.0 * (1.0 - days / 365.0))
    attempts = max(1, prod_attempts or 1)
    stability = max(0.0, 20.0 - (attempts - 1) * 7.0)
    if modified_on:
        days_mod = max(0, (datetime.now(timezone.utc) - modified_on).days)
        definition = min(10.0, 10.0 * days_mod / 180.0)
    else:
        definition = 0.0
    total = min(100, round(recency + stability + definition))
    return {"total": total, "recency": round(recency),
            "stability": round(stability), "definition": round(definition),
            "days": days, "ever": True}


def get_rating(score: int, ever: bool) -> Tuple[str, str]:
    if not ever or score == 0:
        return "🔴", "Nunca"
    if score >= 90:
        return "🟢", "Excelente"
    if score >= 70:
        return "🔵", "Bueno"
    if score >= 40:
        return "🟡", "Regular"
    return "🟠", "Bajo"


# ═══════════════════════════════════════════════════════════════════════════════
# Validator: logs de tareas → violaciones (logica opcion 44 + genericos)
# ═══════════════════════════════════════════════════════════════════════════════
_LOG_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ?")
_LOG_LINE = re.compile(r"^##\[(warning|error)\](.*)$")
_LOG_HEAD = re.compile(r"^\s*\S*\s*\[([A-Z]+)\]\s+([A-Z][A-Z0-9_]*)\s*$")
_KV = re.compile(r"^([A-Za-z][A-Za-z_-]*):\s*(.*)$")


def parse_log(text: str, task_name: str) -> List[Dict]:
    """Reglas estructuradas ##[sev] [SEVERITY] RULE (formato opcion 44)."""
    violations, cur = [], None

    def finish():
        nonlocal cur
        if cur:
            violations.append(cur)
            cur = None

    for raw in text.split("\n"):
        line = _LOG_TS.sub("", raw.rstrip("\r"))
        m = _LOG_LINE.match(line)
        if not m:
            finish()
            continue
        body = m.group(2)
        head = _LOG_HEAD.match(body)
        if head:
            finish()
            cur = {"severity": head.group(1), "rule": head.group(2),
                   "environment": "", "variable": "", "reason": "",
                   "detail": "", "task": task_name, "generic": False}
            continue
        if cur is None or not body.startswith((" ", "\t")):
            finish()
            continue
        b = body.strip()
        kv = _KV.match(b)
        if kv and kv.group(1).lower() in ("environment", "variable", "reason"):
            cur[kv.group(1).lower()] = kv.group(2).strip().strip("'")
        elif b:
            cur["detail"] = b if not cur["detail"] \
                else cur["detail"] + " | " + b
    finish()
    return violations


def parse_generic_issues(text: str, task_name: str,
                         limit: int = 5) -> List[Dict]:
    """##[warning]/##[error] sueltos que no siguen el formato de regla
    (ej: 'variable not found: X' de replacetokens). Las lineas de
    continuacion de una regla estructurada (##[sev] [SEV] RULE + cuerpo
    indentado) se excluyen, igual que en parse_log."""
    out = []
    in_rule = False
    for raw in text.split("\n"):
        line = _LOG_TS.sub("", raw.rstrip("\r"))
        m = _LOG_LINE.match(line)
        if not m:
            in_rule = False
            continue
        body = m.group(2)
        if _LOG_HEAD.match(body):
            in_rule = True
            continue
        b = body.strip()
        if in_rule and (body.startswith((" ", "\t"))
                        or _KV.match(b)):
            continue  # continuation de la regla — no es issue generico
        in_rule = False
        sev = "ERROR" if m.group(1) == "error" else "WARNING"
        out.append({"severity": sev, "rule": "TASK_ISSUE",
                    "environment": "", "variable": "", "reason": "",
                    "detail": b[:160], "task": task_name, "generic": True})
        if len(out) >= limit:
            break
    return out


def validator_task_logs(rel: Dict, validator_env: Optional[Dict],
                        headers, debug) -> Tuple[List[Dict], List[str]]:
    """Logs de todas las tareas del ultimo intento del stage Validator.
    Solo si el stage existe y fue ejecutado (deploySteps con fases).
    Retorna (violaciones, errores_de_fetch)."""
    if not validator_env:
        return [], []
    steps = validator_env.get("deploySteps", []) or []
    if not steps:
        return [], []
    step = max(steps, key=lambda s: s.get("attempt", 0))
    tasks = []
    for ph in step.get("releaseDeployPhases", []) or []:
        for job in ph.get("deploymentJobs", []) or []:
            for t in job.get("tasks", []) or []:
                if t.get("status") in ("skipped", "pending"):
                    continue
                log_url = t.get("logUrl")
                if log_url:
                    tasks.append((t.get("name", "task"), log_url))
    violations = []
    errors = []
    for name, url in tasks:
        text = api_get_text(url, headers, debug)
        if text is None:
            errors.append(name)
            continue
        violations.extend(parse_log(text, name))
        violations.extend(parse_generic_issues(text, name))
    # dedup + orden por severidad
    seen, unique = set(), []
    for v in sorted(violations, key=lambda v: (SEV_RANK.get(v["severity"], 5),
                                              v["rule"], v["environment"])):
        key = (v["severity"], v["rule"], v["environment"], v["variable"],
               v["reason"], v["detail"])
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique, errors


def violations_summary(violations: List[Dict]) -> Dict[str, int]:
    """Conteo por severidad: {'CRITICAL': n, 'HIGH': n, ...}."""
    out: Dict[str, int] = {}
    for v in violations:
        out[v["severity"]] = out.get(v["severity"], 0) + 1
    return out


def props_commit_from_logs(violations: List[Dict]) -> str:
    """Commit de properties impreso por la tarea 'Obtener commit
    Properties' del Validator (Commit actual en prod: <sha>)."""
    for v in violations:
        if "commit actual en prod" in (v.get("detail", "") or "").lower():
            m = re.search(r"\b([0-9a-f]{40})\b", v["detail"])
            if m:
                return m.group(1)
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# Variables del release
# ═══════════════════════════════════════════════════════════════════════════════
def release_vars(rel: Dict) -> Dict[str, str]:
    out = {}
    for name, v in (rel.get("variables") or {}).items():
        out[name.upper()] = str((v or {}).get("value", "") or "") \
            if isinstance(v, dict) else str(v)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Rollback: release apuntado por RELEASE_ID
# ═══════════════════════════════════════════════════════════════════════════════
def rollback_info(org, project, rel, vars_, headers, debug) -> Dict[str, Any]:
    """Info del release de rollback (RELEASE_ID/RELASE_ID): build id,
    commit del artifact Git y commit de properties que aplican."""
    rb_id = vars_.get("RELEASE_ID") or vars_.get("RELASE_ID") or ""
    out = {"release_id": rb_id, "build_id": "", "build_number": "",
           "git_commit": "", "props_commit": "", "valid": False}
    if not rb_id.isdigit() or int(rb_id) == rel.get("id"):
        return out  # vacio o apunta a si mismo → Validator no lo valido
    rb = get_release_detail(org, project, rb_id, headers, debug)
    if not rb:
        return out
    build_art, git_arts = extract_artifacts(rb)
    bi = build_artifact_info(build_art)
    out["build_id"] = bi["build_id"]
    out["build_number"] = bi["build_number"]
    for ga in git_arts:
        gi = git_artifact_info(ga)
        if gi["commit"]:
            out["git_commit"] = gi["commit"]
            break
    rb_vars = release_vars(rb)
    out["props_commit"] = rb_vars.get("COMMITPROPERTIESROLLBACK", "")
    out["valid"] = True
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Proceso por CD
# ═══════════════════════════════════════════════════════════════════════════════
def process_cd(org, project, cd, def_detail, args, headers, repos_by_id) \
        -> Dict[str, Any]:
    """Analiza un CD con artifact Git master y devuelve sus releases
    pendientes de Production con toda la info del PR a master."""
    result = {"cd_id": cd.get("id"), "cd_name": cd.get("name", ""),
              "rows": [], "score": 0, "rating": ("🔴", "Nunca"),
              "error": ""}
    gi = cd_master_git_artifact(def_detail, args.master_branch)
    if not gi:
        result["error"] = "sin artifact Git master"
        return result

    releases = get_releases(org, project, cd.get("id"),
                            args.top_releases, headers, args.debug)
    if not releases:
        result["error"] = "sin releases"
        return result

    # score del CD (formula opcion 3)
    dep = analyze_prod_deploy(releases, args.prod_stage)
    modified_on = parse_azdo_date(def_detail.get("modifiedOn"))
    score_data = compute_score(dep["last_prod_deploy"],
                               dep["last_attempts"], modified_on)
    result["score"] = score_data["total"]
    result["rating"] = get_rating(score_data["total"],
                                 dep["prod_ever_deployed"])
    result["score_data"] = score_data

    for rel in releases:
        prod_env = stage_env(rel, args.prod_stage)
        if prod_installed(prod_env):
            continue  # ya instalado en Production → excluir

        build_art, git_arts = extract_artifacts(rel)
        bi = build_artifact_info(build_art)
        src_gi = git_artifact_info(git_arts[0] if git_arts else None)
        vars_ = release_vars(rel)

        # PR a master: id desde la rama del build (refs/pull/N/merge)
        pr_id = pr_id_from_build_branch(bi["branch"])
        pr = None
        repo_lookup = src_gi["repo_id"] or gi["repo_id"]
        if pr_id:
            pr = get_pull_request(org, project, repo_lookup, pr_id,
                                  headers, args.debug)
        if pr is None and src_gi["commit"]:
            pr = find_pr_for_commit(org, project, repo_lookup,
                                    src_gi["commit"], headers, args.debug,
                                    target_branch=args.master_branch)

        # Validator: logs de tareas (si existe / fue ejecutado)
        validator_env = stage_env(rel, args.validator_stage)
        validator_ran = bool(validator_env
                              and (validator_env.get("deploySteps") or []))
        violations, log_errors = ([], [])
        if validator_ran:
            violations, log_errors = validator_task_logs(
                rel, validator_env, headers, args.debug)

        # commit de properties: variable → logs del Validator
        props_commit = vars_.get("COMMITPROPERTIESROLLBACK", "") \
            or props_commit_from_logs(violations)

        rb = rollback_info(org, project, rel, vars_, headers, args.debug)

        prod_status = (prod_env or {}).get("status", "—")
        prod_attempts = len((prod_env or {}).get("deploySteps", []) or [])

        result["rows"].append({
            "cd_id": cd.get("id"),
            "cd_name": cd.get("name", ""),
            "release_id": rel.get("id"),
            "release_name": rel.get("name", ""),
            "created_on": rel.get("createdOn", ""),
            "repo": src_gi["repo_name"] or gi["repo_name"],
            "repo_id": repo_lookup,
            "pr_id": (pr or {}).get("pullRequestId") or pr_id,
            "pr_title": (pr or {}).get("title", ""),
            "pr_target": (pr or {}).get("targetRefName", ""),
            "build_id": bi["build_id"],
            "build_number": bi["build_number"],
            "git_commit": src_gi["commit"],
            "score": result["score"],
            "rating": result["rating"],
            "props_commit": props_commit,
            "rb_release_id": rb["release_id"],
            "rb_build_id": rb["build_id"],
            "rb_build_number": rb["build_number"],
            "rb_git_commit": rb["git_commit"],
            "rb_props_commit": rb["props_commit"],
            "rb_valid": rb["valid"],
            "validator_ran": validator_ran,
            "violations": violations,
            "log_errors": log_errors,
            "prod_status": prod_status,
            "prod_attempts": prod_attempts,
            "stages": stage_snapshot(rel),
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Render
# ═══════════════════════════════════════════════════════════════════════════════
def _viol_cell(violations: List[Dict]) -> str:
    if not violations:
        return f"{ICON_OK} sin hallazgos" if RICH else "OK"
    parts = []
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "WARNING", "ERROR",
                "LOW", "INFO"):
        n = sum(1 for v in violations if v["severity"] == sev)
        if n:
            style = SEV_STYLE.get(sev, "white")
            parts.append(f"[{style}]{n} {sev[:4]}[/]" if RICH
                         else f"{n} {sev[:4]}")
    return " ".join(parts) if parts else f"{len(violations)} reglas"


def _score_cell(score: int, rating: Tuple[str, str]) -> str:
    emoji, label = rating
    if RICH:
        color = ("green" if score >= 70 else
                 "cyan" if score >= 40 else "yellow" if score > 0 else "red")
        return f"[{color}]{score:>3}[/] {emoji}"
    return f"{score} {label}"


def _stage_icon(status: str) -> str:
    s = (status or "").lower()
    if s in ("succeeded",):
        return ICON_OK
    if s in ("partiallysucceeded",):
        return ICON_WARN
    if s in ("failed", "canceled", "rejected"):
        return ICON_ERR
    if s in ("inprogress",):
        return ICON_PEND
    return ICON_SKIP


def _short(sha: str, n: int = 8) -> str:
    return (sha or "—")[:n] if sha else "—"


def print_main_table(rows: List[Dict]) -> None:
    if RICH and console:
        t = Table(title="🛡️ PRs a master pendientes de instalar en "
                        "Production", box=box.ROUNDED)
        t.add_column("CD PIPELINE", style="cyan", no_wrap=True)
        t.add_column("RELEASE", style="magenta")
        t.add_column("PR → MASTER", style="green", no_wrap=True)
        t.add_column("REPO", style="dim")
        t.add_column("BUILD ID", style="yellow", no_wrap=True)
        t.add_column("COMMIT GIT", style="magenta", no_wrap=True)
        t.add_column("SCORE", justify="center")
        t.add_column("COMMIT PROPS", style="cyan", no_wrap=True)
        t.add_column("ROLLBACK", style="dim")
        t.add_column("VALIDATOR", no_wrap=True)
        t.add_column("PROD", justify="center")
        for r in rows:
            rb = (f"rel {r['rb_release_id']}\n"
                  f"build {r['rb_build_id'] or '—'}"
                  f" ({r['rb_build_number'] or '—'})\n"
                  f"git {_short(r['rb_git_commit'])}\n"
                  f"props {_short(r['rb_props_commit'])}") \
                if r["rb_valid"] else "sin validar"
            t.add_row(
                r["cd_name"][:34],
                f"{r['release_name']}\n#{r['release_id']}",
                f"#{r['pr_id'] or '?'}\n{(r['pr_title'] or '?')[:26]}",
                r["repo"][:22],
                f"{r['build_id'] or '—'}\n{r['build_number'] or '—'}",
                _short(r["git_commit"]),
                _score_cell(r["score"], r["rating"]),
                _short(r["props_commit"]),
                rb,
                _viol_cell(r["violations"]),
                f"{_stage_icon(r['prod_status'])} "
                f"{r['prod_status'][:9]}",
            )
        console.print(t)
    else:
        for r in rows:
            print(f"{r['cd_name']} | {r['release_name']} | "
                  f"PR#{r['pr_id']} | build {r['build_id']} | "
                  f"git {_short(r['git_commit'])} | score {r['score']} | "
                  f"props {_short(r['props_commit'])} | "
                  f"prod {r['prod_status']}")


def _validator_cell(r: Dict) -> str:
    if not r["validator_ran"]:
        return f"{ICON_SKIP} sin ejecutar"
    if not r["violations"]:
        return f"{ICON_OK} limpio"
    return _viol_cell(r["violations"])


def _rollback_cell(r: Dict) -> str:
    if not r["rb_valid"]:
        return "sin validar"
    return (f"rel {r['rb_release_id']} | "
            f"build {r['rb_build_id'] or '—'} ({r['rb_build_number'] or '—'}) | "
            f"git {_short(r['rb_git_commit'])} | "
            f"props {_short(r['rb_props_commit'])}")


def _stages_cell(r: Dict) -> str:
    return " → ".join(
        f"{_stage_icon(st)}{name}" for name, st, _ in r["stages"])


def print_row_details(rows: List[Dict], args) -> None:
    """Detalle por release EN TABLA: snapshot de stages (Deep Dive) +
    rollback + estado del Validator; y tabla de hallazgos del Validator
    (reglas opcion 44 + issues de tarea)."""
    findings = [(r, v) for r in rows for v in r["violations"]]

    if RICH and console:
        # ── Tabla de detalle por release ──
        t = Table(title="Detalle por release — stages / rollback / validator",
                  box=box.ROUNDED)
        t.add_column("RELEASE", style="magenta", no_wrap=True)
        t.add_column("STAGES", style="dim")
        t.add_column("PROD", justify="center", no_wrap=True)
        t.add_column("PR → MASTER", style="green")
        t.add_column("BUILD", style="yellow", no_wrap=True)
        t.add_column("COMMIT GIT", style="magenta", no_wrap=True)
        t.add_column("COMMIT PROPS", style="cyan", no_wrap=True)
        t.add_column("ROLLBACK", style="dim")
        t.add_column("VALIDATOR", no_wrap=True)
        for r in rows:
            t.add_row(
                f"{r['release_name']}\n#{r['release_id']} — {r['cd_name'][:24]}",
                _stages_cell(r),
                f"{_stage_icon(r['prod_status'])} {r['prod_status'][:9]}\n"
                f"{r['prod_attempts']} intentos",
                f"#{r['pr_id'] or '?'}\n{(r['pr_title'] or '?')[:30]}",
                f"{r['build_id'] or '—'}\n{r['build_number'] or '—'}",
                _short(r["git_commit"]),
                _short(r["props_commit"]),
                _rollback_cell(r),
                _validator_cell(r),
            )
        console.print(t)

        # ── Tabla de hallazgos del Validator ──
        if findings:
            ft = Table(title="Hallazgos del stage Validator",
                       box=box.ROUNDED)
            ft.add_column("RELEASE", style="magenta", no_wrap=True)
            ft.add_column("SEVERIDAD", no_wrap=True)
            ft.add_column("REGLA", style="cyan")
            ft.add_column("STAGE", style="dim")
            ft.add_column("VARIABLE", style="yellow")
            ft.add_column("RAZÓN", style="dim")
            ft.add_column("DETALLE", style="dim")
            for r, v in findings:
                style = SEV_STYLE.get(v["severity"], "white")
                ft.add_row(
                    f"{r['release_name']}",
                    f"[{style}]{v['severity']}[/]",
                    v["rule"],
                    v["environment"] or "—",
                    v["variable"] or "—",
                    (v["reason"] or "—")[:40],
                    (v["detail"] or "—")[:80],
                )
            console.print(ft)
        else:
            console.print(f"[green]{ICON_OK} Sin hallazgos del Validator "
                          "en los releases pendientes.[/]")

        # Logs no legibles
        errs = [(r["release_name"], e) for r in rows for e in r["log_errors"]]
        if errs:
            et = Table(title="Logs de tareas no legibles", box=box.ROUNDED)
            et.add_column("RELEASE", style="magenta")
            et.add_column("TAREA", style="yellow")
            for rel_name, e in errs:
                et.add_row(rel_name, e)
            console.print(et)
    else:
        for r in rows:
            print(f"\n=== {r['release_name']} — {r['cd_name']} ===")
            print(f"Stages: {_stages_cell(r)}")
            print(f"Production: {r['prod_status']} "
                  f"({r['prod_attempts']} intentos)")
            print(f"PR a master: #{r['pr_id'] or '?'} {r['pr_title']}")
            print(f"Build: {r['build_id']} ({r['build_number']}) | "
                  f"Commit Git: {r['git_commit'][:12]}")
            print(f"Commit properties: {r['props_commit'] or '—'}")
            print(f"Rollback: {_rollback_cell(r)}")
            print(f"Validator: {_validator_cell(r)}")
            for v in r["violations"]:
                ctx = (f" env={v['environment']}" if v["environment"] else "") + \
                      (f" var={v['variable']}" if v["variable"] else "") + \
                      (f" reason={v['reason']}" if v["reason"] else "")
                print(f"  [{v['severity']}] {v['rule']}{ctx}")
                if v["detail"]:
                    print(f"    {v['detail'][:150]}")
            for e in r["log_errors"]:
                print(f"  No se pudo leer el log de: {e}")


def export_row(r: Dict) -> Dict:
    """Fila plana para exportación (JSON/HTML/Excel)."""
    return {
        "cd_pipeline": r["cd_name"],
        "cd_id": r["cd_id"],
        "release": r["release_name"],
        "release_id": r["release_id"],
        "created_on": r["created_on"],
        "repo": r["repo"],
        "pr_id": r["pr_id"],
        "pr_title": r["pr_title"],
        "pr_target": r["pr_target"],
        "build_id": r["build_id"],
        "build_number": r["build_number"],
        "git_commit": r["git_commit"],
        "score": r["score"],
        "rating": r["rating"][1],
        "props_commit": r["props_commit"],
        "rollback_release_id": r["rb_release_id"],
        "rollback_build_id": r["rb_build_id"],
        "rollback_build_number": r["rb_build_number"],
        "rollback_git_commit": r["rb_git_commit"],
        "rollback_props_commit": r["rb_props_commit"],
        "rollback_valid": r["rb_valid"],
        "prod_status": r["prod_status"],
        "prod_attempts": r["prod_attempts"],
        "stages": " → ".join(f"{n}:{s}" for n, s, _ in r["stages"]),
        "validator_ran": r["validator_ran"],
        "violations_count": len(r["violations"]),
        "violations": "; ".join(
            f"[{v['severity']}] {v['rule']}"
            + (f" env={v['environment']}" if v["environment"] else "")
            + (f" var={v['variable']}" if v["variable"] else "")
            + (f" — {v['detail']}" if v["detail"] else "")
            for v in r["violations"]),
        "log_errors": ", ".join(r["log_errors"]),
    }


def print_summary(cd_results: List[Dict], rows: List[Dict],
                   total_defs: int = 0) -> None:
    total_cds = sum(1 for c in cd_results if not c["error"])
    pend = len(rows)
    with_viol = sum(1 for r in rows if r["violations"])
    crit = sum(1 for r in rows for v in r["violations"]
               if v["severity"] == "CRITICAL")
    high = sum(1 for r in rows for v in r["violations"]
               if v["severity"] == "HIGH")
    if RICH and console:
        console.print(f"\n[bold]CDs con artifact Git master[/]: {total_cds} "
                      f"[dim]de {total_defs or len(cd_results)} "
                      "definiciones[/]")
        console.print(f"[bold]Releases pendientes de Production[/]: {pend}")
        console.print(f"[bold]Con hallazgos del Validator[/]: {with_viol} "
                      f"[red]({crit} CRITICAL, {high} HIGH)[/]")
    else:
        print(f"\nCDs con artifact Git master: {total_cds} "
              f"de {total_defs or len(cd_results)} definiciones")
        print(f"Releases pendientes de Production: {pend}")
        print(f"Con hallazgos del Validator: {with_viol} "
              f"({crit} CRITICAL, {high} HIGH)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    args = get_args()
    headers = make_headers(args.pat)
    org = args.org.rstrip("/")
    project = args.project

    _print("[bold cyan]🛡️ Production Pre-Install Validator — "
           "PRs a master pendientes de Production[/]")

    # 1. Definiciones CD (spinner)
    if RICH and console:
        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      console=console) as p:
            t = p.add_task("Obteniendo definiciones CD…", total=None)
            cds = get_release_defs_list(org, project, headers, args.debug)
            p.update(t, description=f"✅ {len(cds)} definiciones CD")
    else:
        print("Obteniendo definiciones CD…", end=" ", flush=True)
        cds = get_release_defs_list(org, project, headers, args.debug)
        print(f"{len(cds)}")
    if not cds:
        _print("[red]❌ No se encontraron pipeline CD.[/]")
        return 1
    _print(f"[dim]{len(cds)} definiciones CD — filtrando artifact Git "
           f"branch {args.master_branch}…[/]")

    # 2. Detalles de definicion en paralelo (barra de progreso)
    def fetch_detail(cd):
        d = get_def_detail(org, project, cd.get("id"), headers, args.debug)
        return cd, d

    details = []
    if RICH and console:
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console) as p:
            t = p.add_task(f"Descargando detalle de {len(cds)} definiciones…",
                           total=len(cds))
            with ThreadPoolExecutor(
                    max_workers=max(1, args.threads)) as ex:
                futs = {ex.submit(fetch_detail, cd): cd for cd in cds}
                for fut in as_completed(futs):
                    cd = futs[fut]
                    try:
                        details.append(fut.result())
                    except Exception:
                        details.append((cd, None))
                    p.update(t, description=(
                        f"Detalle CD [cyan]{cd.get('name', '?')[:40]}[/]"))
                    p.advance(t)
    else:
        print(f"Descargando detalle de {len(cds)} definiciones…",
              end=" ", flush=True)
        with ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
            details = list(ex.map(fetch_detail, cds))
        print("listo")

    # solo CDs con artifact Git branch master
    master_cds = []
    for cd, detail in details:
        if detail and cd_master_git_artifact(detail, args.master_branch):
            master_cds.append((cd, detail))
    if not master_cds:
        _print(f"[red]❌ Ningún CD tiene artifact tipo Git en rama "
               f"{args.master_branch}.[/]")
        return 1

    # ── Paso 1: listar TODOS los CDs candidatos antes de procesar ──
    if RICH and console:
        ct = Table(title=f"CDs con artifact Git en rama "
                         f"{args.master_branch} ({len(master_cds)})",
                   box=box.ROUNDED)
        ct.add_column("#", justify="right", style="dim")
        ct.add_column("CD PIPELINE", style="cyan", no_wrap=True)
        ct.add_column("ID", style="dim", justify="right")
        ct.add_column("REPO (artifact Git)", style="magenta")
        ct.add_column("RAMA", style="green")
        for i, (cd, detail) in enumerate(master_cds, 1):
            gi = cd_master_git_artifact(detail, args.master_branch) or {}
            ct.add_row(str(i), cd.get("name", ""), str(cd.get("id")),
                       gi.get("repo_name", "?"), gi.get("branch", "?"))
        console.print(ct)
        console.print()
    else:
        print(f"\nCDs con artifact Git en rama {args.master_branch} "
              f"({len(master_cds)}):")
        for i, (cd, detail) in enumerate(master_cds, 1):
            gi = cd_master_git_artifact(detail, args.master_branch) or {}
            print(f"  {i:>3}. {cd.get('name')} (id {cd.get('id')}) "
                  f"— {gi.get('repo_name', '?')} [{gi.get('branch', '?')}]")

    # 3. Repositorios del proyecto (spinner)
    if RICH and console:
        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      console=console) as p:
            t = p.add_task("Obteniendo repositorios…", total=None)
            repos = get_repositories(org, project, headers, args.debug)
            p.update(t, description=f"✅ {len(repos)} repositorios")
    else:
        print("Obteniendo repositorios…", end=" ", flush=True)
        repos = get_repositories(org, project, headers, args.debug)
        print(f"{len(repos)}")
    repos_by_id = {r.get("id"): r for r in repos}

    # 4. Analisis por CD EN PARALELO (barra de progreso)
    #    cada worker resuelve releases + logs Validator + rollback del CD
    cd_results = [None] * len(master_cds)

    def _work(idx_cd):
        idx, (cd, detail) = idx_cd
        return idx, process_cd(org, project, cd, detail, args, headers,
                               repos_by_id)

    if RICH and console:
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console) as p:
            t = p.add_task(f"Analizando {len(master_cds)} CDs "
                           f"({args.threads} workers)…",
                           total=len(master_cds))
            with ThreadPoolExecutor(
                    max_workers=max(1, args.threads)) as ex:
                futs = {ex.submit(_work, (i, cd_d))
                        for i, cd_d in enumerate(master_cds)}
                for fut in as_completed(futs):
                    idx, res = fut.result()
                    cd_results[idx] = res
                    p.update(t, description=(
                        f"✔ [cyan]{res['cd_name'][:50]}[/] — "
                        f"{len(res['rows'])} pendiente(s)"))
                    p.advance(t)
            p.update(t, description="✅ Análisis de CDs completado")
    else:
        print(f"Analizando {len(master_cds)} CDs "
              f"({args.threads} workers)…", flush=True)
        done = 0
        with ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
            futs = {ex.submit(_work, (i, cd_d))
                    for i, cd_d in enumerate(master_cds)}
            for fut in as_completed(futs):
                idx, res = fut.result()
                cd_results[idx] = res
                done += 1
                print(f"  [{done}/{len(master_cds)}] {res['cd_name']} — "
                      f"{len(res['rows'])} pendiente(s)", flush=True)

    rows = [r for c in cd_results for r in c["rows"]]

    # ── Salida por defecto: JSON + HTML + Excel en outcome/ ──
    try:
        from azdo_default_export import write_default_reports
        write_default_reports(
            "prod_preinstall_validator", __version__,
            [export_row(r) for r in rows],
            summary={"cds_git_master": len(master_cds),
                     "pendientes_production": len(rows),
                     "con_hallazgos": sum(1 for r in rows if r["violations"])},
            organization=org, project=project,
            title="Production Pre-Install Validator", excel=True)
    except Exception:
        pass

    if not rows:
        _print("[green]✅ Ningún release pendiente de Production en los "
               "CDs con artifact Git master.[/]")
        return 0

    print_main_table(rows)
    print_row_details(rows, args)
    print_summary(cd_results, rows, total_defs=len(cds))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
