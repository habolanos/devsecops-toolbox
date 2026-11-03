#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_release_diagnostic.py — Release Diagnostic & Folio Generator

A partir de un `--release-id` de un pipeline CD diagnostica la coherencia
install ↔ rollback y genera el folio en formato Service Desk:

  1. Artifacts del release (Build id/number + Git source repo/commit)
  2. Build ↔ commit del PR del git source (refs/pull/N/merge → lastMergeCommit)
  3. Log del stage Validator → imagen a instalar / en producción,
     excepto-a, instrucción kubectl apply→delete, props commit en log
  4. Variables commitPropertiesRollback y RELEASE_ID/RELASE_ID
  5. commitPropertiesRollback vs último commit del folder <componente>
     en el repo de properties
  6. Mismo diagnóstico para el release de rollback (RELEASE_ID)
  7. Comparativo lado a lado → TODO EN ORDEN / REVISAR
  8. Folio copiable + exports JSON/HTML/Excel en outcome/

Solo lectura. Reutiliza los extractores probados de la opción 47 y el
fetch de logs del Validator de la opción 48.

Autor: Harold Adrian
"""

import argparse
import base64
import re
import sys
from pathlib import Path
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Tuple

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
    from rich.progress import (BarColumn, Progress, SpinnerColumn,
                               TaskProgressColumn, TextColumn)
    from rich.table import Table
    from rich import box
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None

try:
    import requests
except ImportError:
    requests = None

__version__ = "1.0.3"
__author__ = "Harold Adrian"

API_VERSION = "7.1"
GIT_ARTIFACT_TYPES = ("git", "github", "externalgit", "tfvc")
IMAGE_HOST_RE = re.compile(
    r"(?:gcr\.io|pkg\.dev|harbor|artifact\.coppel\.io|docker\.io"
    r"|azurecr\.io|ecr\.amazonaws\.com)[\w./-]*:[\w.-]+",
    re.IGNORECASE)


def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="azdo_release_diagnostic",
        description="Diagnóstico install↔rollback de un release CD y "
                    "generación de folio Service Desk.")
    p.add_argument("--release-id", type=int, required=True,
                   help="Id del release a diagnosticar")
    p.add_argument("--pat", required=True)
    p.add_argument("--org",
                   default="https://dev.azure.com/Coppel-Retail")
    p.add_argument("--project", default="Cadena_de_Suministros")
    p.add_argument("--validator-stage", default="Validator",
                   help="Stage validador (default: Validator)")
    p.add_argument("--properties-repo", default="",
                   help="Hint del repo de properties (default autodetect)")
    p.add_argument("--branch", default="master",
                   help="Rama del repo properties (default: master)")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP helpers
# ═══════════════════════════════════════════════════════════════════════════════
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


def strip_userinfo(url: str) -> str:
    return re.sub(r"//[^/@]+@", "//", url or "")


def _short(sha: str, n: int = 10) -> str:
    return (sha or "")[:n] or "—"


# ═══════════════════════════════════════════════════════════════════════════════
# Release / artifacts (patrones de la opción 47)
# ═══════════════════════════════════════════════════════════════════════════════
def get_release_detail(org, project, rel_id, headers,
                       debug) -> Optional[Dict]:
    url = (f"{vsrm(org)}/{quote(project, safe='')}"
           f"/_apis/release/releases/{rel_id}")
    return api_get(url, headers, {"api-version": API_VERSION,
                                  "$expand": "environments,artifacts"},
                   debug)


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
    """Build artifact: build_id, build_number, branch (refs/pull/N/merge),
    artifact_name y ci_repo_name (repo del YAML CI — NUNCA el componente)."""
    info = {"build_id": "", "build_number": "", "branch": "",
            "artifact_name": "", "ci_repo_name": ""}
    if not art:
        return info
    ref = art.get("definitionReference", {}) or {}
    ver = ref.get("version") or {}
    info["build_id"] = str(ver.get("id", "") or "")
    info["build_number"] = ver.get("name", "") or ""
    info["artifact_name"] = (art.get("name") or art.get("alias") or "")
    info["ci_repo_name"] = (ref.get("repository") or {}).get("name", "")
    info["branch"] = (ref.get("branch") or {}).get("id", "") \
        or (ref.get("branches") or {}).get("id", "")
    return info


def git_artifact_info(art: Optional[Dict]) -> Dict[str, str]:
    """Git artifact: repo componente + commit + branch."""
    info = {"repo_id": "", "repo_name": "", "commit": "", "url": "",
            "branch": ""}
    if not art:
        return info
    ref = art.get("definitionReference", {}) or {}
    repo = ref.get("repository") or {}
    info["repo_id"] = repo.get("id", "") or ""
    info["repo_name"] = repo.get("name", "") or ""
    info["url"] = strip_userinfo(repo.get("url", "")
                                 or repo.get("remoteUrl", "") or "")
    ver = ref.get("version") or {}
    info["commit"] = ver.get("id", "") \
        or (ref.get("sourceVersion") or {}).get("id", "") or ""
    info["branch"] = (ref.get("branch") or {}).get("id", "") \
        or (ref.get("branches") or {}).get("id", "")
    return info


def is_properties_artifact(art: Dict) -> bool:
    alias = (art.get("alias") or "").lower()
    name = (art.get("name") or "").lower()
    return "properties" in alias or "properties" in name


def source_git_artifact(git_arts: List[Dict]) -> Optional[Dict]:
    for a in git_arts:
        if not is_properties_artifact(a):
            return a
    return git_arts[0] if git_arts else None


def classify_git_artifacts(git_arts: List[Dict]) -> Tuple[Dict, Dict]:
    src, props = {}, {}
    for ga in git_arts:
        gi = git_artifact_info(ga)
        if not gi["repo_name"] and not gi["commit"]:
            continue
        if "properties" in gi["repo_name"].lower():
            props = props or gi
        else:
            src = src or gi
    return src, props


def stage_env(rel: Dict, stage_name: str) -> Optional[Dict]:
    target = (stage_name or "").lower().replace(" ", "")
    for env in rel.get("environments", []) or []:
        if (env.get("name", "") or "").lower().replace(" ", "") == target:
            return env
    return None


def stage_snapshot(rel: Dict) -> List[Tuple[str, str]]:
    return [(e.get("name", "?"), e.get("status", ""))
            for e in rel.get("environments", []) or []]


def release_variables(rel: Dict) -> Dict[str, str]:
    out = {}
    for name, v in (rel.get("variables") or {}).items():
        if isinstance(v, dict):
            out[name.upper()] = str(v.get("value", "") or "")
        else:
            out[name.upper()] = str(v)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# PR / repos / properties (patrones de la opción 47)
# ═══════════════════════════════════════════════════════════════════════════════
def pr_id_from_build_branch(branch_ref: str) -> Optional[int]:
    m = re.match(r"refs/pull/(\d+)/(merge|head)", branch_ref or "")
    return int(m.group(1)) if m else None


def get_pull_request(org, project, repo_id, pr_id, headers,
                     debug) -> Optional[Dict]:
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(repo_id, safe='')}/pullrequests/{pr_id}")
    return api_get(url, headers, {"api-version": API_VERSION}, debug)


def pr_definitive_commit(pr: Optional[Dict]) -> str:
    if not pr:
        return ""
    return (pr.get("lastMergeCommit") or {}).get("commitId", "") or ""


def find_pr_for_commit(org, project, repo_id, commit, headers, debug,
                       target_branch: str = "master",
                       top: int = 200) -> Optional[Dict]:
    """Fallback: scan de PRs completados del repo filtrados por rama
    destino; el PR cuyo lastMergeCommit == commit."""
    if not commit:
        return None
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(repo_id, safe='')}/pullrequests")
    params = {"api-version": API_VERSION,
              "searchCriteria.status": "completed",
              "searchCriteria.targetRefName":
                  f"refs/heads/{target_branch}",
              "$top": top}
    for page in range(5):
        params["$skip"] = page * top
        data = api_get(url, headers, params, debug)
        values = (data or {}).get("value", []) or []
        for pr in values:
            c = pr_definitive_commit(pr)
            if c and c.lower() == commit.lower():
                return pr
        if len(values) < top:
            break
    return None


def get_repositories(org, project, headers, debug) -> List[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories"
    data = api_get(url, headers, {"api-version": API_VERSION}, debug)
    return (data or {}).get("value", []) if data else []


def find_properties_repo(repos: List[Dict], hint: str) -> Optional[Dict]:
    if hint:
        for r in repos:
            if r.get("name", "").lower() == hint.lower():
                return r
        for r in repos:
            if hint.lower() in r.get("name", "").lower():
                return r
    for r in repos:
        if "properties" in r.get("name", "").lower():
            return r
    return None


def folder_commits(org, project, repo_id, path, branch, headers,
                   debug, top: int = 100) -> List[Dict]:
    """Commits que tocaron el folder `path` en `branch` (más reciente
    primero)."""
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(repo_id, safe='')}/commits")
    data = api_get(url, headers, {
        "api-version": API_VERSION,
        "searchCriteria.itemPath": path,
        "searchCriteria.itemVersion.version": branch,
        "searchCriteria.itemVersion.versionType": "branch",
        "$top": top}, debug)
    return (data or {}).get("value", []) if data else []


def _parse_iso(s: str) -> Optional[Any]:
    from datetime import datetime
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def commit_matching_date(commits: List[Dict],
                         date_iso: str) -> Optional[Dict]:
    """Último commit del folder en o antes de la fecha dada (fecha del
    release de rollback). Si ninguno es anterior → el más antiguo."""
    if not commits:
        return None
    target = _parse_iso(date_iso)
    if not target:
        return commits[0]
    best, best_d = None, None
    for c in commits:
        d = _parse_iso((c.get("author") or {}).get("date", "")
                       or (c.get("committer") or {}).get("date", ""))
        if d and d <= target and (best_d is None or d > best_d):
            best, best_d = c, d
    return best or commits[-1]


def relase_id_matches_rollback(value: str, rollback_name: str,
                               rollback_id) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    rid = str(rollback_id or "")
    return (v == rid or v.lstrip("0") == rid.lstrip("0")
            or v.lower() == (rollback_name or "").lower())


# ── Resolución del repo fuente (cadena de la opción 47) ──
def get_build(org, project, build_id, headers, debug) -> Optional[Dict]:
    url = (f"{org}/{quote(project, safe='')}/_apis/build/builds/"
           f"{build_id}")
    return api_get(url, headers, {"api-version": API_VERSION}, debug)


def build_source_entries(build: Optional[Dict]) -> List[Dict[str, str]]:
    """build.sourceRepositories → {alias, repo_id, repo_name, url,
    commit, branch}."""
    out = []
    for sr in (build or {}).get("sourceRepositories", []) or []:
        repo = sr.get("repository") or {}
        out.append({
            "alias": (sr.get("alias") or repo.get("alias") or "").lower(),
            "repo_id": repo.get("id", "") or "",
            "repo_name": repo.get("name", "") or "",
            "url": strip_userinfo(repo.get("url", "")
                                  or repo.get("remoteUrl", "") or ""),
            "commit": sr.get("sourceVersion", "") or "",
            "branch": (sr.get("sourceBranch") or sr.get("ref")
                       or sr.get("refName") or ""),
        })
    return out


def clean_component_name(name: str) -> str:
    """artifact.name suele ser '_repo-xxx-CI': limpia '_' y -CI/-CD."""
    n = (name or "").strip().lstrip("_")
    n = re.sub(r"-CI$|-CD$", "", n, flags=re.IGNORECASE)
    return n or (name or "")


def repo_prefix_candidates(name: str) -> List[str]:
    parts = [p for p in (name or "").split("-") if p]
    return ["-".join(parts[:i]) for i in range(len(parts), 0, -1)]


def resolve_repo_by_prefix(cleaned: str, repos_by_name: Dict) \
        -> Optional[Dict]:
    for cand in repo_prefix_candidates(cleaned):
        hit = repos_by_name.get(cand.lower())
        if hit:
            return hit
    return None


def find_source_entry(entries: List[Dict], artifact_name: str,
                      exclude: str = "") -> Optional[Dict]:
    """Repo fuente del componente en sourceRepositories del build."""
    pool = [e for e in entries
            if e["repo_name"].lower() != (exclude or "").lower()]
    for e in pool:
        if e["repo_name"].lower() == (artifact_name or "").lower():
            return e
    for e in pool:
        if e["alias"] in ("sources", "source"):
            return e
    cleaned = clean_component_name(artifact_name)
    if cleaned:
        for cand in repo_prefix_candidates(cleaned):
            for e in pool:
                if e["repo_name"].lower() == cand.lower():
                    return e
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Log del stage Validator (patrón de la opción 48) + parsers nuevos
# ═══════════════════════════════════════════════════════════════════════════════
def validator_log_texts(rel: Dict, validator_env: Optional[Dict],
                        headers, debug) -> Tuple[List[Tuple[str, str]],
                                                 List[str]]:
    """[(task_name, log_text)] de todas las tareas del último intento
    del stage Validator; solo si existe y fue ejecutado."""
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
                if t.get("logUrl"):
                    tasks.append((t.get("name", "task"), t["logUrl"]))
    texts, errors = [], []
    for name, url in tasks:
        text = api_get_text(url, headers, debug)
        if text is None:
            errors.append(name)
        else:
            texts.append((name, text))
    return texts, errors


def extract_images_from_log(text: str) -> Dict[str, str]:
    """{install_image, prod_image} del texto de un log.
    Patrones: 'image actual/nueva', 'IMAGE_ACTUAL/NUEVA=',
    líneas 'set image'/'kubectl apply' con host de registry conocido."""
    out = {"install_image": "", "prod_image": ""}
    if not text:
        return out
    new_pats = [
        r"image\s+nueva\s*[:=]\s*(\S+)",
        r"image_nueva\s*[:=]\s*(\S+)",
        r"new.?image\s*[:=]\s*(\S+)",
        r"imagen\s+nueva\s*[:=]\s*(\S+)",
        r"set\s+image\s+.*?=(\S+:\S+)",
    ]
    old_pats = [
        r"image\s+actual\s*[:=]\s*(\S+)",
        r"image_actual\s*[:=]\s*(\S+)",
        r"current.?image\s*[:=]\s*(\S+)",
        r"old.?image\s*[:=]\s*(\S+)",
        r"imagen\s+actual\s*[:=]\s*(\S+)",
        r"image\s+in\s+production\s*[:=]\s*(\S+)",
        r"production.?image\s*[:=]\s*(\S+)",
    ]
    for pat in new_pats:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            out["install_image"] = m.group(1).strip()
            break
    for pat in old_pats:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            out["prod_image"] = m.group(1).strip()
            break
    # fallback: primeras imágenes del registry en el log
    if not out["install_image"]:
        hosts = IMAGE_HOST_RE.findall(text)
        if hosts:
            out["install_image"] = hosts[0]
            if len(hosts) > 1 and not out["prod_image"]:
                out["prod_image"] = hosts[-1] if hosts[-1] != hosts[0] \
                    else ""
    return out


def extract_excepto(text: str) -> str:
    """'excepto a: X' del log; N/A si no aparece."""
    if not text:
        return "N/A"
    m = re.search(r"excepto\s*a\s*[:=]?\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else "N/A"


def detect_kubectl_apply(text: str) -> bool:
    """El log muestra un apply/deploy de manifiesto → instrucción
    'apply por delete'."""
    if not text:
        return False
    return bool(re.search(
        r"kubectl\s+(apply|create|replace|patch)\b"
        r"|kubectl-apply"
        r"|k8.?manifest|show.?manifest",
        text, re.IGNORECASE))


def extract_props_commit_from_log(text: str) -> str:
    """commitPropertiesRollback impreso en el log
    ('##vso[task.setvariable variable=commitPropertiesRollback]sha' o
    'commitPropertiesRollback=<sha>')."""
    if not text:
        return ""
    m = re.search(
        r"task\.setvariable\s+variable=commitPropertiesRollback\]?"
        r"\s*([0-9a-f]{7,40})",
        text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"commitPropertiesRollback\s*[:=]\s*([0-9a-f]{7,40})",
                  text, re.IGNORECASE)
    return m.group(1) if m else ""


def aggregate_validator(texts: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Une los parsers sobre TODOS los logs del Validator."""
    out = {"install_image": "", "prod_image": "", "excepto": "N/A",
           "kubectl_apply": False, "props_commit_log": ""}
    for _, text in texts:
        img = extract_images_from_log(text)
        out["install_image"] = out["install_image"] \
            or img["install_image"]
        out["prod_image"] = out["prod_image"] or img["prod_image"]
        if out["excepto"] == "N/A":
            out["excepto"] = extract_excepto(text)
        out["kubectl_apply"] = out["kubectl_apply"] \
            or detect_kubectl_apply(text)
        out["props_commit_log"] = out["props_commit_log"] \
            or extract_props_commit_from_log(text)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Diagnóstico de UN release (install o rollback)
# ═══════════════════════════════════════════════════════════════════════════════
def diagnose_release(org: str, project: str, rel: Dict, headers,
                     args, props_repo: Optional[Dict],
                     repos: List[Dict],
                     props_by_date: bool = False) -> Dict[str, Any]:
    """Extrae TODA la info diagnóstica de un release.
    `props_by_date=True` (rollback): el commit del folder properties es
    el vigente a la fecha del release — lo que realmente aplicaría."""
    detail = get_release_detail(org, project, rel.get("id"), headers,
                                args.debug) or rel
    build_art, git_arts = extract_artifacts(detail)
    bi = build_artifact_info(build_art)
    src_art, _ = classify_git_artifacts(git_arts)
    if not src_art:
        src_gi = git_artifact_info(source_git_artifact(git_arts))
    else:
        src_gi = src_art

    # ── Resolución del repo fuente (cadena de la opción 47): si el Git
    # source artifact no trae repo, se resuelve via build.sourceRepositories
    # → prefijo del artifact.name contra los repos del proyecto ──
    repos_by_name = {r.get("name", "").lower(): r for r in repos}
    if not src_gi["repo_name"] and bi["build_id"]:
        build = get_build(org, project, bi["build_id"], headers,
                          args.debug)
        entries = build_source_entries(build)
        source_e = find_source_entry(entries, bi["artifact_name"],
                                     exclude=bi["ci_repo_name"]) or {}
        if source_e.get("repo_name"):
            src_gi["repo_id"] = source_e["repo_id"]
            src_gi["repo_name"] = source_e["repo_name"]
            src_gi["url"] = source_e["url"]
            if not src_gi["commit"]:
                src_gi["commit"] = source_e["commit"]
    if not src_gi["repo_name"]:
        cleaned = clean_component_name(bi["artifact_name"])
        hit = resolve_repo_by_prefix(cleaned, repos_by_name)
        if hit and (hit.get("name", "").lower()
                    != bi["ci_repo_name"].lower()):
            src_gi["repo_id"] = hit.get("id", "") or ""
            src_gi["repo_name"] = hit.get("name", "") or ""
            src_gi["url"] = strip_userinfo(
                hit.get("remoteUrl", "") or hit.get("webUrl", ""))
    component = src_gi["repo_name"] \
        or clean_component_name(bi["artifact_name"]) or "component"
    vars_ = release_variables(detail)

    out: Dict[str, Any] = {
        "release_id": detail.get("id"), "release_name": detail.get("name",
                                                                 ""),
        "component": component,
        "build_id": bi["build_id"], "build_number": bi["build_number"],
        "git_commit": src_gi["commit"], "git_branch": src_gi["branch"],
        "repo_url": src_gi["url"],
        "props_artifact_commit": git_artifact_info(
            next((a for a in git_arts if is_properties_artifact(a)),
                 None))["commit"],
        "props_commit_var": vars_.get("COMMITPROPERTIESROLLBACK", ""),
        "relase_id_var": vars_.get("RELEASE_ID")
        or vars_.get("RELASE_ID") or "",
        "url": f"{org}/{quote(project, safe='')}/_releaseProgress"
               f"?_a=release-pipeline-progress&releaseId="
               f"{detail.get('id')}",
        "stages": stage_snapshot(detail),
    }

    # ── Build ↔ PR del git source ──
    pr_id = pr_id_from_build_branch(bi["branch"])
    pr = None
    if pr_id and src_gi["repo_id"]:
        pr = get_pull_request(org, project, src_gi["repo_id"], pr_id,
                              headers, args.debug)
    if pr is None and src_gi["commit"] and src_gi["repo_id"]:
        pr = find_pr_for_commit(org, project, src_gi["repo_id"],
                                src_gi["commit"], headers, args.debug,
                                target_branch=args.branch)
    out["pr"] = pr
    out["pr_commit"] = pr_definitive_commit(pr)
    out["pr_matches"] = bool(out["pr_commit"]
                             and out["pr_commit"].lower()
                             == (src_gi["commit"] or "").lower())

    # ── Log del Validator ──
    venv = stage_env(detail, args.validator_stage)
    texts, log_errors = validator_log_texts(detail, venv, headers,
                                            args.debug)
    vinfo = aggregate_validator(texts)
    out["validator_ran"] = bool(texts)
    out["validator_errors"] = log_errors
    out.update(vinfo)

    # ── Properties repo: folder <componente> ──
    out["props_folder_commit"] = ""
    out["props_folder_path"] = component
    out["created_on"] = detail.get("createdOn", "")
    if props_repo:
        commits = folder_commits(org, project, props_repo.get("id", ""),
                                 f"/{component}", args.branch, headers,
                                 args.debug)
        pick = (commit_matching_date(commits, out["created_on"])
                if props_by_date else (commits[0] if commits else None))
        if pick:
            out["props_folder_commit"] = pick.get("commitId", "")
        out["props_folder_commits"] = [{
            "commitId": c.get("commitId", ""),
            "author": (c.get("author") or {}).get("name", "")
            or (c.get("committer") or {}).get("name", ""),
            "date": ((c.get("author") or {}).get("date", "")
                     or (c.get("committer") or {}).get("date", ""))[:19],
            "picked": bool(pick and c.get("commitId")
                           == pick.get("commitId"))}
            for c in commits[:15]]
    else:
        out["props_folder_commits"] = []
    # props_commit efectivo: variable → log → folder
    out["props_commit"] = (out["props_commit_var"]
                           or out["props_commit_log"]
                           or out["props_folder_commit"])
    out["props_match"] = bool(
        out["props_commit_var"] and out["props_folder_commit"]
        and out["props_commit_var"].lower()
        == out["props_folder_commit"].lower())
    out["props_evaluable"] = bool(out["props_commit_var"]
                                  and out["props_folder_commit"])
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Comparativo y folio
# ═══════════════════════════════════════════════════════════════════════════════
def build_checks(install: Dict[str, Any],
                 rollback: Optional[Dict[str, Any]]) -> List[Dict]:
    """Checks de coherencia install↔rollback."""
    checks = []
    checks.append({
        "check": "Build ↔ commit del PR (git source)",
        "install": _short(install["pr_commit"]) or "—",
        "rollback": _short((rollback or {}).get("pr_commit", "")) or "—",
        "ok": install["pr_matches"] if install["pr_commit"]
        else None,
        "detail": (f"install PR #{install['pr'].get('pullRequestId')}"
                   if install.get("pr") else "install: PR no encontrado")
        + (" | "
           + (f"rollback PR #{(rollback or {}).get('pr', {}).get('pullRequestId')}"
              if rollback and rollback.get("pr")
              else ("rollback: PR no encontrado" if rollback else "")))})
    props_ok = None
    props_detail = f"folder /{install['props_folder_path']}"
    if install["props_evaluable"]:
        props_ok = install["props_match"]
    elif not install["props_commit_var"]:
        props_detail += " — variable commitPropertiesRollback vacía"
    else:
        props_detail += " — folder sin commits (¿nombre incorrecto?)"
    checks.append({
        "check": "commitPropertiesRollback == folder properties",
        "install": _short(install["props_commit_var"]) or "—",
        "rollback": _short((rollback or {}).get("props_commit_var",
                                               "")) or "—",
        "ok": props_ok,
        "detail": props_detail})
    rid_ok = None
    if install["relase_id_var"] and rollback:
        rid_ok = relase_id_matches_rollback(
            install["relase_id_var"], rollback["release_name"],
            rollback["release_id"])
    checks.append({
        "check": "RELEASE_ID → apunta al rollback",
        "install": install["relase_id_var"] or "—",
        "rollback": str((rollback or {}).get("release_id", "—")),
        "ok": rid_ok, "detail": "variable vs release rollback"})
    img_ok = None
    img_detail = f"prod: {install['prod_image'] or '—'}"
    if install["install_image"] and install["prod_image"]:
        if install["install_image"] != install["prod_image"]:
            img_ok = True
        else:
            img_detail += " (misma imagen en install y prod)"
    elif install["install_image"]:
        img_detail += " — imagen de producción no detectada en el log"
    checks.append({
        "check": "Imagen install ≠ producción (cambio real)",
        "install": install["install_image"] or "—",
        "rollback": (rollback or {}).get("install_image", "") or "—",
        "ok": img_ok,
        "detail": img_detail})
    return checks


def verdict(checks: List[Dict]) -> Tuple[bool, int]:
    """(todo_ok, n_fallados) — solo cuenta checks evaluables."""
    fails = [c for c in checks if c["ok"] is False]
    return (len(fails) == 0, len(fails))


def build_folio(install: Dict[str, Any],
                rollback: Optional[Dict[str, Any]]) -> str:
    """Bloque de texto del folio Service Desk (formato literal)."""
    lines = [
        f"Componente: {install['component']}",
        f"* Release: {install['release_name']}",
        f"* URL Release: {install['url']}",
        f"* Commit: {install['git_commit']}",
        f"* Version Build: {install['build_number']}",
        f"* Commit properties deploy: {install['props_commit']}",
        "* Folio PR master : N/A",
        f"Excepto a: {install['excepto']}",
        "Rollback:",
    ]
    if rollback:
        rb_comp = rollback["component"]
        note = ""
        lines += [
            f"Componente: {rb_comp}{note}",
            f"• Release Rollback {rollback['release_name']}",
            f"• URL Release Rollback: {rollback['url']}",
            f"• Commit Rollback Release: {rollback['git_commit']}",
            f"• Version Build: {rollback['build_number']}",
            f"• Commit properties Rollback : "
            f"{rollback['props_commit']}",
        ]
    else:
        lines += [
            "Componente: N/A (estrategia release 0 primera vez que "
            "se instala)",
            "• Release Rollback N/A",
            "• URL Release Rollback: N/A",
            "• Commit Rollback Release: N/A",
            "• Version Build: N/A",
            "• Commit properties Rollback : N/A",
        ]
    if install.get("kubectl_apply"):
        lines.append("Actualizar kubectl apply se cambia el comando "
                     "apply por delete y hacer el deploy")
    return "\n".join(lines)


def export_check_rows(checks: List[Dict]) -> List[Dict]:
    return [{"check": c["check"], "install": c["install"],
             "rollback": c["rollback"],
             "resultado": ("OK" if c["ok"] else
                           ("REVISAR" if c["ok"] is False else "N/A")),
             "detalle": c["detail"]} for c in checks]


def print_compare(install: Dict[str, Any],
                  rollback: Optional[Dict[str, Any]],
                  checks: List[Dict]) -> None:
    _print("\n[bold]═══ Comparativo Install ↔ Rollback ═══[/]")
    if RICH and console:
        t = Table(box=box.ROUNDED)
        for col in ("CHECK", "INSTALL", "ROLLBACK", "RESULTADO",
                    "DETALLE"):
            t.add_column(col)
        for c in checks:
            mark = ("[green]✔[/]" if c["ok"] else
                    ("[red]✘[/]" if c["ok"] is False else "[dim]—[/]"))
            t.add_row(c["check"], str(c["install"]), str(c["rollback"]),
                      mark, c["detail"])
        console.print(t)
    else:
        for c in checks:
            mark = "✔" if c["ok"] else ("✘" if c["ok"] is False else "—")
            print(f"  {c['check']} | {c['install']} | {c['rollback']} "
                  f"| {mark} | {c['detail']}")


def print_props_commits(install: Dict[str, Any],
                        rollback: Optional[Dict[str, Any]]) -> None:
    """Listado de commits del folder /<componente> en repo properties
    (install y rollback), con el commit elegido marcado."""
    _print("\n[bold]═══ Listado Properties de componente ═══[/]")
    if RICH and console:
        t = Table(box=box.ROUNDED)
        for col in ("LADO", "PATH", "COMMIT", "USUARIO", "FECHA", "ELEGIDO"):
            t.add_column(col)
        for tag, r in (("INSTALL", install),
                       ("ROLLBACK", rollback)):
            if not r:
                continue
            rows = r.get("props_folder_commits") or []
            if not rows:
                t.add_row(tag, f"/{r['props_folder_path']}", "—", "—",
                          "—", "[dim]sin commits[/]")
            for c in rows:
                mark = "[green]◀[/]" if c["picked"] else ""
                t.add_row(tag, f"/{r['props_folder_path']}",
                          c["commitId"], c["author"], c["date"], mark)
        console.print(t)
    else:
        for tag, r in (("INSTALL", install),
                       ("ROLLBACK", rollback)):
            if not r:
                continue
            for c in r.get("props_folder_commits") or []:
                mark = " ◀" if c["picked"] else ""
                print(f"  [{tag}] /{r['props_folder_path']} "
                      f"{c['commitId']} {c['author']} {c['date']}{mark}")


def print_snapshot(install: Dict[str, Any],
                   rollback: Optional[Dict[str, Any]]) -> None:
    def _line(r, tag):
        snap = " → ".join(f"{n}:{s or '?'}" for n, s in r["stages"])
        _print(f"  [{tag}] {r['release_name']} "
               f"(id {r['release_id']}) — {snap}")
    _line(install, "INSTALL")
    if rollback:
        _line(rollback, "ROLLBACK")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    if requests is None:
        print("❌ Falta 'requests' (pip install requests)")
        return 2
    args = get_args()
    org = args.org.rstrip("/")
    project = args.project
    headers = make_headers(args.pat)

    # ── release + repos/properties (contexto) ──
    if RICH and console:
        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      console=console) as p:
            t = p.add_task(f"Release {args.release_id} + contexto…",
                           total=None)
            rel = get_release_detail(org, project, args.release_id,
                                     headers, args.debug)
            repos = get_repositories(org, project, headers, args.debug)
            props_repo = find_properties_repo(
                repos, args.properties_repo)
            p.update(t, description="✅ Contexto")
    else:
        rel = get_release_detail(org, project, args.release_id,
                                 headers, args.debug)
        repos = get_repositories(org, project, headers, args.debug)
        props_repo = find_properties_repo(repos, args.properties_repo)
        print("Contexto listo")

    if not rel:
        _print(f"[red]❌ Release {args.release_id} no encontrado.[/]")
        return 1

    # ── diagnóstico install ──
    _print(f"\n[bold cyan]═══ Release Diagnostic — "
           f"{args.release_id} ═══[/]")
    install = diagnose_release(org, project, rel, headers, args,
                               props_repo, repos)
    _print(f"  Componente: {install['component']}  |  "
           f"Release: {install['release_name']}  |  "
           f"Build: {install['build_number']} "
           f"(id {install['build_id']})")
    if not install["validator_ran"]:
        _print(f"  [yellow]⚠ Stage '{args.validator_stage}' sin log "
               f"disponible — campos derivados: N/A[/]")
    for name in install["validator_errors"]:
        _print(f"  [yellow]⚠ log no legible: {name}[/]")

    # ── diagnóstico rollback (RELEASE_ID) ──
    rollback = None
    rb_id = install["relase_id_var"]
    if rb_id and rb_id.isdigit() and int(rb_id) != install["release_id"]:
        rb_rel = get_release_detail(org, project, int(rb_id), headers,
                                    args.debug)
        if rb_rel:
            rollback = diagnose_release(org, project, rb_rel, headers,
                                        args, props_repo, repos,
                                        props_by_date=True)
        else:
            _print(f"  [yellow]⚠ RELEASE_ID={rb_id} no resuelve un "
                   f"release[/]")
    elif rb_id:
        _print("  [yellow]⚠ RELEASE_ID vacío o apunta a sí mismo — "
               "rollback: N/A[/]")

    # ── comparativo ──
    print_snapshot(install, rollback)
    print_props_commits(install, rollback)
    checks = build_checks(install, rollback)
    print_compare(install, rollback, checks)
    ok, nfail = verdict(checks)
    _print(f"\n[bold]{'[green]✅ TODO EN ORDEN[/]' if ok else f'[red]⚠ REVISAR {nfail} ítem(s)[/]'}[/]")

    # ── folio ──
    folio = build_folio(install, rollback)
    _print("\n[bold]═══ Folio (copiar a Service Desk) ═══[/]")
    if RICH and console:
        console.print(Panel(folio, box=box.ROUNDED,
                            title="Folio", expand=False))
    else:
        print(folio)

    # ── exports al final ──
    try:
        from azdo_default_export import write_default_reports
        rows = export_check_rows(checks)
        rows.append({"check": "Folio", "install": folio[:120],
                     "rollback": "", "resultado": "OK" if ok
                     else "REVISAR", "detalle": ""})
        outdir = get_output_dir("outcome")
        folio_path = outdir / f"release_diagnostic_{args.release_id}.txt"
        folio_path.write_text(folio + "\n", encoding="utf-8")
        write_default_reports(
            "release_diagnostic", __version__, rows,
            metadata={"organization": org, "project": project,
                      "release_id": args.release_id,
                      "rollback_release_id":
                          (rollback or {}).get("release_id", "")},
            summary={"checks": len(checks), "ok": ok,
                     "fallados": nfail,
                     "componente": install["component"]},
            organization=org, project=project,
            title="Release Diagnostic", excel=True)
        try:
            print(f"   📄 FOLIO: {folio_path.resolve()}")
        except UnicodeEncodeError:
            print(f"   [OK] FOLIO: {folio_path.resolve()}")
    except Exception as e:
        if args.debug:
            print(f"[DEBUG] export: {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
