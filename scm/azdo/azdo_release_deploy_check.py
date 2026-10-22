#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_release_deploy_check.py

Analisis de despliegue CD: compara el release que se va a instalar contra
su release de rollback para un Pipeline CD de Azure DevOps.

Flujo interactivo:
  1. Lista los releases del pipeline CD (ultimo deploy a produccion +
     los mas recientes) y pregunta cual se instala y cual es el rollback.
  2. Por cada release consulta el artifact primario (build id, numero de
     compilacion, commit sourceVersion) y el repo Git vinculado.
  3. Consulta el build para validar que el PR que lo origino corresponde
     con el commit empaquetado en el release.
  4. Lee la variable RELASE_ID / RELEASE_ID del release a instalar y la
     compara contra el release de rollback (verde = coincide).
  5. Consulta el repositorio de propiedades y muestra el ultimo commit
     del folder con el nombre del componente.
  6. Imprime el comparativo listo para evidencia.

Autor: Harold Adrian
"""

import argparse
import base64
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

try:
    from utils import get_output_dir
except ImportError:
    def get_output_dir(default="."):
        env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None

__version__ = "1.0.7"
__author__ = "Harold Adrian"

DEFAULT_ORG_URL = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT = "Cadena_de_Suministros"
API_VERSION = "7.1"
API_VERSION_REL = "7.2-preview.8"
API_VERSION_DEF = "7.2-preview.4"
API_VERSION_BUILD = "7.1"
PROD_KEYWORDS = ("prod", "prd", "production")
TOP_RELEASES = 50
TOP_PR_SEARCH = 60
# Releases con mas de N dias se muestran tenues (ya no son validos)
STALE_DAYS = 30


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS / HTTP / HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Comparativo release a instalar vs rollback para un CD")
    p.add_argument("--pat", required=True)
    p.add_argument("--org", default=DEFAULT_ORG_URL)
    p.add_argument("--project", default=DEFAULT_PROJECT)
    p.add_argument("--definition-id", "--id", dest="definition_id", type=int,
                   required=True)
    p.add_argument("--properties-repo", default="",
                   help="Nombre del repo de propiedades (default: autodetectar "
                        "repo que contenga 'properties')")
    p.add_argument("--branch", default="master",
                   help="Rama para consultar commits del repo de propiedades")
    p.add_argument("--top", type=int, default=TOP_RELEASES,
                   help="Max releases a listar")
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
            print(f"[DEBUG] HTTP {r.status_code} {url}\n{r.text[:400]}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if debug:
            print(f"[DEBUG] {url}: {e}")
        return None


def _print(msg: str = "", markup: bool = True) -> None:
    if RICH and console:
        console.print(msg, markup=markup)
    else:
        import re
        print(re.sub(r"\[/?[a-zA-Z0-9_# =]+\]", "", str(msg)))


def _is_prod_env(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in PROD_KEYWORDS)


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _fmt_date(s: str) -> str:
    d = _parse_iso(s)
    return d.strftime("%Y-%m-%d %H:%M") if d else "—"


# ═══════════════════════════════════════════════════════════════════════════════
# RELEASE DATA
# ═══════════════════════════════════════════════════════════════════════════════
def get_definition(org, project, def_id, headers, debug) -> Optional[Dict]:
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/definitions/{def_id}"
    return api_get(url, headers, {"api-version": API_VERSION_DEF}, debug)


def get_releases(org, project, def_id, headers, top, debug) -> List[Dict]:
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
    return api_get(url, headers, {"api-version": API_VERSION_REL,
                                  "$expand": "artifacts"}, debug)


def release_prod_status(rel: Dict) -> Tuple[str, str]:
    """(status, fecha) del environment de produccion mas reciente."""
    best = ("", "")
    for env in rel.get("environments", []) or []:
        if not _is_prod_env(env.get("name", "")):
            continue
        status = env.get("status", "")
        when = ""
        for step in env.get("deploySteps", []) or []:
            if step.get("deploymentStatus") in ("succeeded",
                                                "partiallySucceeded"):
                when = step.get("finishedOn", "") or when
        if not when:
            when = env.get("modifiedOn", "")
        return status or "?", when
    return best


def extract_primary_artifact(rel: Dict) -> Optional[Dict]:
    """Artifact primario tipo Build (o el primero disponible)."""
    arts = rel.get("artifacts", []) or []
    if not arts:
        return None
    arts = sorted(arts, key=lambda a: not a.get("isPrimary", False))
    for a in arts:
        if a.get("type") == "Build":
            return a
    return arts[0]


def artifact_info(art: Optional[Dict]) -> Dict[str, str]:
    """Extrae build_id, build_number, commit sourceVersion y el nombre
    del artifact (artifact.name = nombre del componente/repo fuente)."""
    info = {"build_id": "", "build_number": "", "commit": "",
            "artifact_name": "", "ci_repo_name": ""}
    if not art:
        return info
    ref = art.get("definitionReference", {}) or {}
    ver = ref.get("version") or {}
    info["build_id"] = str(ver.get("id", "") or "")
    info["build_number"] = ver.get("name", "") or ""
    sv = ref.get("sourceVersion") or {}
    info["commit"] = sv.get("id", "") or ""
    # artifact.name = nombre del CI/artifact; definitionReference.
    # repository = repo del YAML CI (ej: pipelines-projects) — NUNCA es
    # el repo fuente del componente, se usa para excluirlo.
    info["artifact_name"] = (art.get("name") or art.get("alias") or "")
    ci_repo = ref.get("repository") or {}
    info["ci_repo_name"] = ci_repo.get("name", "") or ""
    return info


def release_variables(rel: Dict) -> Dict[str, str]:
    out = {}
    for name, v in (rel.get("variables") or {}).items():
        if isinstance(v, dict):
            out[name.upper()] = str(v.get("value", "") or "")
        else:
            out[name.upper()] = str(v)
    return out


def relase_id_matches_rollback(value: str, rollback_name: str,
                               rollback_id) -> bool:
    """True si la variable RELASE_ID del release a instalar apunta al
    release de rollback (por id numerico o nombre Release-N)."""
    v = (value or "").strip()
    if not v:
        return False
    rid = str(rollback_id or "")
    return (v == rid or v.lstrip("0") == rid.lstrip("0")
            or v.lower() == (rollback_name or "").lower())


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD / PR / GIT
# ═══════════════════════════════════════════════════════════════════════════════
def get_build(org, project, build_id, headers, debug) -> Optional[Dict]:
    """GET build — primero con api 7.2-preview.1 (expone
    sourceRepositories en pipelines multi-checkout); fallback a 7.1."""
    url = f"{org}/{quote(project, safe='')}/_apis/build/builds/{build_id}"
    data = api_get(url, headers, {"api-version": "7.2-preview.1"}, debug)
    if data is None:
        data = api_get(url, headers,
                       {"api-version": API_VERSION_BUILD}, debug)
    return data


def get_build_changes(org, project, build_id, headers,
                      debug) -> List[Dict]:
    """GET builds/{id}/changes — commits asociados a la compilacion; cada
    change.location trae .../repositories/{repoId}/commits/{sha}, lo que
    permite resolver el repo fuente cuando sourceRepositories no viene."""
    url = (f"{org}/{quote(project, safe='')}/_apis/build/builds/"
           f"{build_id}/changes")
    data = api_get(url, headers, {"api-version": API_VERSION_BUILD,
                                  "$top": 200}, debug)
    return data.get("value", []) if data else []


def repo_id_from_location(location: str) -> str:
    """Extrae el repoId de una URL .../repositories/{id}/commits/..."""
    import re
    m = re.search(r"/repositories/([^/]+)/commits/", location or "")
    return m.group(1) if m else ""


def get_repository(org, project, repo_id, headers,
                   debug) -> Optional[Dict]:
    if not repo_id:
        return None
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(str(repo_id), safe='')}")
    return api_get(url, headers, {"api-version": API_VERSION}, debug)


def clean_component_name(name: str) -> str:
    """artifact.name suele ser el nombre del CI: '_repo-xxx-CI'.
    Limpia prefijo '_' y sufijos -CI/-CD para dejar el componente."""
    import re
    n = (name or "").strip().lstrip("_")
    n = re.sub(r"-CI$|-CD$", "", n, flags=re.IGNORECASE)
    return n or (name or "")


def get_repositories(org, project, headers, debug) -> List[Dict]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories"
    data = api_get(url, headers, {"api-version": API_VERSION}, debug)
    return data.get("value", []) if data else []


def get_pull_request(org, project, repo_id, pr_id, headers,
                     debug) -> Optional[Dict]:
    """Consulta un PR por id en el repo fuente."""
    if not repo_id or not pr_id:
        return None
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(str(repo_id), safe='')}/pullrequests/{pr_id}")
    return api_get(url, headers, {"api-version": API_VERSION}, debug)


def pr_commit_info(pr: Optional[Dict]) -> Dict[str, str]:
    """Commit 'definitivo' del PR: merge commit (destino) y ultimo commit
    del source branch."""
    pr = pr or {}
    return {
        "merge": (pr.get("lastMergeCommit") or {}).get("commitId", "")
                 or "",
        "source": (pr.get("lastMergeSourceCommit") or {})
                  .get("commitId", "") or "",
        "target": (pr.get("lastMergeTargetCommit") or {})
                  .get("commitId", "") or "",
    }


def pr_matches_commit(pr: Optional[Dict], commit: str) -> bool:
    if not pr or not commit:
        return False
    c = commit.lower()
    info = pr_commit_info(pr)
    return any(v and v.lower() == c for v in info.values())


def find_pr_for_commit(org, project, repo_id, commit, headers,
                       debug) -> Optional[Dict]:
    """Busca el PR cuyo merge commit coincide con el commit del release.

    Compara lastMergeCommit / lastMergeTargetCommit /
    lastMergeSourceCommit de los PRs completados mas recientes.
    """
    if not repo_id or not commit:
        return None
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(repo_id, safe='')}/pullrequests")
    data = api_get(url, headers, {
        "api-version": API_VERSION,
        "searchCriteria.status": "completed",
        "$top": TOP_PR_SEARCH,
    }, debug)
    for pr in (data or {}).get("value", []) or []:
        for key in ("lastMergeCommit", "lastMergeTargetCommit",
                    "lastMergeSourceCommit"):
            c = (pr.get(key) or {}).get("commitId", "")
            if c and c.lower() == commit.lower():
                return pr
    return None


def last_commit_in_path(org, project, repo_id, path, branch, headers,
                        debug) -> Optional[Dict]:
    """Ultimo commit que toco el folder `path` en `branch`."""
    url = (f"{org}/{quote(project, safe='')}/_apis/git/repositories/"
           f"{quote(repo_id, safe='')}/commits")
    data = api_get(url, headers, {
        "api-version": API_VERSION,
        "searchCriteria.itemPath": path,
        "searchCriteria.itemVersion.version": branch,
        "searchCriteria.itemVersion.versionType": "branch",
        "$top": 1,
    }, debug)
    commits = (data or {}).get("value", []) if data else []
    return commits[0] if commits else None


def find_properties_repo(repos: List[Dict], hint: str) -> Optional[Dict]:
    """Repo de propiedades: match exacto con hint, o nombre que contenga
    'properties'."""
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


def strip_userinfo(url: str) -> str:
    """Quita el 'user@' embebido en remoteUrl
    (https://org@dev.azure.com/... → https://dev.azure.com/...)."""
    if "//" in url and "@" in url.split("//", 1)[1].split("/", 1)[0]:
        scheme, rest = url.split("//", 1)
        return f"{scheme}//{rest.split('@', 1)[1]}"
    return url


def build_source_entries(build: Optional[Dict]) -> List[Dict[str, str]]:
    """Normaliza build.sourceRepositories (la seccion 'Repositories' del
    build): alias del recurso (self/sources/archetype/properties), repo,
    branch/ref y sourceVersion (commit de la compilacion por repo)."""
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


def repo_prefix_candidates(name: str) -> List[str]:
    """Prefijos del nombre cortados en '-' de mayor a menor longitud.
    La convencion CI/CD es '_{repo}-{stack}-CI', asi que el repo suele ser
    un prefijo (ej: oms-com-order-springboot-java17-... → oms-com-order)."""
    parts = [p for p in (name or "").split("-") if p]
    return ["-".join(parts[:i]) for i in range(len(parts), 0, -1)]


def resolve_repo_by_prefix(cleaned: str, repos_by_name: Dict) \
        -> Optional[Dict]:
    """Repo del proyecto cuyo nombre es el prefijo mas largo del nombre
    limpio del artifact (convencion '_{repo}-{stack}-CI')."""
    for cand in repo_prefix_candidates(cleaned):
        hit = repos_by_name.get(cand.lower())
        if hit:
            return hit
    return None


def find_source_entry(entries: List[Dict], artifact_name: str,
                      exclude: str = "") -> Optional[Dict]:
    """Entrada del repo fuente del componente dentro de
    sourceRepositories: nombre == artifact.name, alias 'sources', o repo
    cuyo nombre sea prefijo del artifact.name limpio.

    `exclude` = nombre del repo del YAML CI (definitionReference.
    repository): puede venir como 'sources' aunque no sea el componente,
    asi que se ignora aqui — solo se usa como ultimo recurso fuera."""
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


def find_props_entry(entries: List[Dict]) -> Optional[Dict]:
    """Entrada del repo de propiedades en sourceRepositories
    (alias 'properties' o nombre que contenga 'properties')."""
    for e in entries:
        if e["alias"] == "properties" or "properties" in \
                e["repo_name"].lower():
            return e
    return None


def props_source_from_build(build: Optional[Dict]) -> Dict[str, str]:
    """Compat: commit del repo de propiedades en la compilacion."""
    e = find_props_entry(build_source_entries(build)) or {}
    return {"repo_id": e.get("repo_id", ""),
            "repo_name": e.get("repo_name", ""),
            "commit": e.get("commit", "")}


def pr_id_from_ref(ref: str) -> Optional[int]:
    """Extrae el id del PR de refs/pull/{id}/merge|head."""
    import re
    m = re.match(r"refs/pull/(\d+)/(merge|head)", ref or "")
    return int(m.group(1)) if m else None


# ═══════════════════════════════════════════════════════════════════════════════
# UI — seleccion de releases
# ═══════════════════════════════════════════════════════════════════════════════
def choose_release(releases: List[Dict], prompt_label: str,
                   exclude_id: int = 0) -> Optional[Dict]:
    """Lista los releases y pide elegir uno por numero/nombre."""
    while True:
        if RICH and console:
            console.print(f"\n[bold cyan]{prompt_label}[/] "
                          "[dim](numero de la lista, nombre Release-N "
                          "o id — 'q' para salir)[/]")
        else:
            print(f"\n{prompt_label} (numero, nombre Release-N o id — "
                  f"'q' para salir):")
        val = input("> ").strip()
        if val.lower() in ("q", "quit", "exit"):
            return None
        if not val:
            continue
        # numero de la lista
        if val.isdigit():
            idx = int(val)
            if 1 <= idx <= len(releases):
                pick = releases[idx - 1]
                if exclude_id and pick.get("id") == exclude_id:
                    _print("[red]No puede ser el mismo release que el "
                           "anterior — elige otro.[/]")
                    continue
                return pick
        # nombre Release-N
        for rel in releases:
            if rel.get("name", "").lower() == val.lower():
                if exclude_id and rel.get("id") == exclude_id:
                    _print("[red]No puede ser el mismo release — "
                           "elige otro.[/]")
                    break
                return rel
        # id numerico
        if val.isdigit():
            for rel in releases:
                if rel.get("id") == int(val):
                    if exclude_id and rel.get("id") == exclude_id:
                        _print("[red]No puede ser el mismo release — "
                               "elige otro.[/]")
                        break
                    return rel
        _print("[yellow]Seleccion no valida — intenta de nuevo.[/]")


def print_releases_table(releases: List[Dict], tz_note: str = "") -> None:
    if RICH and console:
        t = Table(title=f"🚀 Releases del pipeline CD {tz_note}",
                  box=box.ROUNDED)
        t.add_column("#", style="dim", justify="right")
        t.add_column("RELEASE", style="cyan", no_wrap=True, min_width=11)
        t.add_column("ID", style="magenta", justify="right")
        t.add_column("CREADO", style="yellow", no_wrap=True)
        t.add_column("STATUS", justify="center")
        t.add_column("PROD", justify="center")
        t.add_column("PROD FECHA", style="green", no_wrap=True)
        t.add_column("BUILD", style="cyan", no_wrap=True)
        now = datetime.now(timezone.utc)
        for i, rel in enumerate(releases, 1):
            pst, pdate = release_prod_status(rel)
            art = extract_primary_artifact(rel)
            ai = artifact_info(art)
            prod_fmt = (f"[green]{pst}[/]" if pst in
                        ("succeeded", "partiallySucceeded")
                        else (f"[red]{pst}[/]" if pst else "—"))
            status = rel.get("status", "")
            status_fmt = (f"[yellow]{status}[/]"
                          if status.lower() == "inprogress" else status)
            created = _parse_iso(rel.get("createdOn", ""))
            stale = bool(created
                         and (now - created).days > STALE_DAYS)
            t.add_row(str(i), rel.get("name", ""), str(rel.get("id", "")),
                      _fmt_date(rel.get("createdOn", "")),
                      status_fmt, prod_fmt,
                      _fmt_date(pdate), ai["build_number"] or "—",
                      style="dim" if stale else "")
        console.print(t)
    else:
        for i, rel in enumerate(releases, 1):
            pst, pdate = release_prod_status(rel)
            print(f"{i:>3}. {rel.get('name',''):<14} "
                  f"id={rel.get('id','')} {rel.get('status','')} "
                  f"prod={pst or '-'} {_fmt_date(pdate)}")


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE COMPARATIVO
# ═══════════════════════════════════════════════════════════════════════════════
def release_block(org, project, rel, defn_name, headers, props_repo,
                  repos_by_name, branch, debug) -> Dict[str, Any]:
    """Arma el bloque de datos de un release para el comparativo."""
    rel_id = rel.get("id")
    detail = get_release_detail(org, project, rel_id, headers, debug) or rel
    art = extract_primary_artifact(detail)
    ai = artifact_info(art)

    # El build es el que vincula todo. Su seccion 'Repositories'
    # (sourceRepositories) trae, por alias, el repo fuente del componente
    # ('sources'), el del YAML CI ('self'), el archetype y el repo de
    # propiedades ('properties') — cada uno con su sourceVersion.
    build = get_build(org, project, ai["build_id"], headers, debug) \
        if ai["build_id"] else None
    entries = build_source_entries(build)
    # El repo del YAML CI (definitionReference.repository) se excluye:
    # puede venir como 'sources' aunque no sea el componente.
    ci_repo_name = ai["ci_repo_name"]
    source_e = find_source_entry(entries, ai["artifact_name"],
                                 exclude=ci_repo_name) or {}
    props_e = find_props_entry(entries) or {}
    build_repo = (build or {}).get("repository") or {}

    src_repo_id = source_e.get("repo_id", "")
    src_repo_name = source_e.get("repo_name", "")
    src_url = source_e.get("url", "")
    # Commit de la compilacion del repo fuente (entry 'sources'); fallback
    # al sourceVersion global del build.
    build_commit = (source_e.get("commit")
                    or (build or {}).get("sourceVersion", "") or "")

    # Sin sourceRepositories: resolver el repo fuente buscando el commit
    # del release entre los 'changes' del build. OJO: en builds
    # multi-checkout los changes pueden traer commits de VARIOS repos —
    # se recolectan todos los matches y se prefiere uno que NO sea el
    # repo del YAML CI.
    if not src_repo_id and ai["commit"]:
        target = ai["commit"].lower()
        change_repo_ids = []
        for ch in get_build_changes(org, project, ai["build_id"],
                                    headers, debug):
            if (ch.get("id", "") or "").lower() != target:
                continue
            rid = repo_id_from_location(ch.get("location", ""))
            if rid and rid not in change_repo_ids:
                change_repo_ids.append(rid)
        for rid in change_repo_ids:
            repo = get_repository(org, project, rid, headers,
                                  debug) or {}
            if (repo.get("name", "") or "").lower() == \
                    ci_repo_name.lower():
                continue
            src_repo_id = rid
            src_repo_name = repo.get("name", "") or ""
            src_url = strip_userinfo(
                repo.get("remoteUrl", "") or repo.get("webUrl", ""))
            break

    # Ultimo recurso: el nombre del repo es prefijo del artifact.name
    # limpio (convencion '_{repo}-{stack}-CI') → match sobre los repos
    # del proyecto sin llamadas extra. El repo del YAML CI no califica.
    cleaned = clean_component_name(ai["artifact_name"])
    if not src_repo_id and cleaned:
        hit = resolve_repo_by_prefix(cleaned, repos_by_name) or {}
        if hit and hit.get("name", "").lower() != ci_repo_name.lower():
            src_repo_id = hit.get("id", "") or ""
            src_repo_name = hit.get("name", "") or ""
            src_url = strip_userinfo(hit.get("remoteUrl", "")
                                     or hit.get("webUrl", ""))

    # De verdad ultimo recurso: algun pipeline puede tener su YAML en el
    # repo del componente — solo ahi se acepta el repo del CI.
    if not src_repo_id:
        source_e = find_source_entry(entries, ai["artifact_name"]) or {}
        src_repo_id = source_e.get("repo_id", "")
        src_repo_name = source_e.get("repo_name", "")
        src_url = source_e.get("url", "")

    # Componente = el repo fuente resuelto (el verdadero componente);
    # si no se resolvio, el artifact.name limpio.
    component = src_repo_name or cleaned or "N/A"

    # Ruta del repo: entry 'sources' → repo resuelto por changes →
    # build.repository (self/YAML CI como ultimo recurso) → remoteUrl.
    repo_entry = repos_by_name.get((src_repo_name or "").lower()) \
        or repos_by_name.get((component or "").lower()) or {}
    repo_url = (src_url
                or strip_userinfo(repo_entry.get("remoteUrl", ""))
                or "")
    repo_id = src_repo_id or repo_entry.get("id", "") or ""
    component_matches = bool(src_repo_name)

    # PR asociado al commit del artifact: primero por ref
    # refs/pull/{id}/merge|head (del entry 'sources' o del build), y si
    # no, scan de PRs completados en el repo FUENTE resuelto.
    pr, pr_ref = None, ""
    cand_refs = [source_e.get("branch", ""),
                 (build or {}).get("sourceBranch", "")] \
        + [e.get("branch", "") for e in entries]
    for cand_ref in cand_refs:
        pid = pr_id_from_ref(cand_ref)
        if pid:
            pr = get_pull_request(org, project, repo_id, pid, headers,
                                  debug)
            pr_ref = cand_ref
            break
    if not pr:
        pr = find_pr_for_commit(org, project, repo_id, ai["commit"],
                                headers, debug)
    prc = pr_commit_info(pr)
    pr_def_commit = prc["merge"] or prc["source"]

    # Commit Properties = sourceVersion del repo de propiedades en el
    # build (commit de la compilacion); se contrasta con el ultimo
    # commit del folder con el nombre del repo fuente/componente.
    props_commit = props_e.get("commit", "")
    props_rid = props_e.get("repo_id") or (props_repo or {}).get("id", "")
    props_folder_commit, props_folder = "", ""
    folder_candidates = [src_repo_name, cleaned] \
        + repo_prefix_candidates(cleaned)[1:] \
        + [ai["artifact_name"]]
    if props_rid:
        for folder in dict.fromkeys(
                n for n in folder_candidates if n and n != "N/A"):
            c = last_commit_in_path(org, project, props_rid,
                                    f"/{folder}", branch, headers,
                                    debug)
            if c and c.get("commitId"):
                props_folder_commit = c["commitId"]
                props_folder = folder
                break
    props_match = (bool(props_commit and props_folder_commit)
                   and props_commit.lower() == props_folder_commit.lower())

    url = (f"{org}/{quote(project, safe='')}/_releaseProgress?"
           f"releaseId={rel_id}&_a=release-pipeline-progress")

    return {
        "component": component,
        "artifact_clean": cleaned,
        "src_repo_name": src_repo_name,
        "component_matches_build_repo": component_matches,
        "release_name": detail.get("name", rel.get("name", "")),
        "release_id": rel_id,
        "pipeline": defn_name,
        "url": url,
        "build_id": ai["build_id"],
        "build_number": ai["build_number"],
        "commit": ai["commit"],
        "commit_short": (ai["commit"] or "")[:8],
        "build_commit": build_commit,
        "commit_matches_build": bool(
            ai["commit"] and build_commit
            and ai["commit"].lower() == build_commit.lower()),
        "pr": pr,
        "pr_ref": pr_ref,
        "pr_commit": pr_def_commit,
        "pr_commit_short": (pr_def_commit or "")[:8],
        "pr_commit_matches": pr_matches_commit(pr, ai["commit"]),
        "props_commit": props_commit,
        "props_folder_commit": props_folder_commit,
        "props_match": props_match,
        "props_folder": props_folder or component,
        "repo_url": repo_url,
        "variables": release_variables(detail),
        "excepto_a": (release_variables(detail).get("EXCEPTO_A")
                      or release_variables(detail).get("EXCEPTOA")
                      or "N/A"),
    }


def print_block(b: Dict[str, Any], org_project_label: str,
                rollback_match: Optional[bool] = None,
                release_id_var: str = "") -> None:
    """Imprime el bloque del comparativo en el formato pedido."""
    lines = []
    if b.get("src_repo_name"):
        comp_note = "[green]✔ repo del build[/]"
        ac = b.get("artifact_clean", "")
        if ac and ac != b["component"]:
            comp_note += f" [dim](CI: {ac})[/]"
    else:
        comp_note = "[yellow]⚠ repo fuente no resuelto[/]"
    lines.append(f"Nombre del componente: {b['component']} {comp_note}")
    lines.append(f"Nombre Organización: {org_project_label}")
    lines.append(f"Nombre del Release: {b['release_name']}")
    lines.append(f"Pipeline de CD: {b['pipeline']}")
    lines.append(b["url"])
    lines.append(f"No. compilación: {b['build_number'] or 'N/A'}")
    lines.append(f"Commit Release: {b['commit_short'] or 'N/A'}")
    lines.append(f"Commit Properties: {b['props_commit'] or 'N/A'}")
    folder_commit = b.get("props_folder_commit") or ""
    if folder_commit:
        if b.get("props_commit"):
            mark = ("[green]✔ coincide con compilación[/]"
                    if b.get("props_match")
                    else "[red]✘ difiere de la compilación[/]")
        else:
            mark = "[dim](build sin commit de compilación)[/]"
        lines.append(
            f"Commit Properties Folder /{b.get('props_folder', '')}: "
            f"{folder_commit} {mark}")
    lines.append(f"Ruta del Repositorio en Azure: {b['repo_url'] or 'N/A'}")
    lines.append(f"Excepto a: {b['excepto_a']}")
    if release_id_var:
        mark = ("[green]✔ coincide con el rollback[/]"
                if rollback_match else
                "[red]✘ NO coincide con el rollback[/]")
        lines.append(f"Variable RELASE_ID: {release_id_var} {mark}")
    pr = b.get("pr")
    if pr:
        pr_title = pr.get("title", "")[:60]
        lines.append(
            f"PR asociado: #{pr.get('pullRequestId')} {pr_title}")
        match = ("[green]✔ coincide con el release[/]"
                 if b.get("pr_commit_matches")
                 else "[red]✘ difiere del commit del release[/]")
        lines.append(
            f"Commit definitivo del PR: "
            f"{b.get('pr_commit_short') or 'N/A'} {match}")
    elif b.get("commit"):
        lines.append("PR asociado: no encontrado para el commit "
                     "[yellow]⚠[/]")
    if b.get("build_commit"):
        ok = b["commit_matches_build"]
        lines.append(
            f"Commit build {b['build_commit'][:8]}: "
            + ("[green]✔ coincide con artifact[/]" if ok else
               "[red]✘ difiere del artifact[/]"))
    if RICH and console:
        console.print(Panel("\n".join(lines), box=box.ROUNDED))
    else:
        print("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    args = get_args()
    headers = make_headers(args.pat)
    org = args.org.rstrip("/")
    project = args.project

    _print(f"[bold cyan]🔎 Release Deploy Check — pipeline "
           f"{args.definition_id}[/]")

    defn = get_definition(org, project, args.definition_id, headers,
                          args.debug)
    if not defn:
        _print("[red]❌ No se encontro la definicion del pipeline "
               f"{args.definition_id}[/]")
        return 1
    defn_name = defn.get("name", "")
    _print(f"[dim]Pipeline CD: {defn_name}[/]")

    releases = get_releases(org, project, args.definition_id, headers,
                            args.top, args.debug)
    if not releases:
        _print("[red]❌ El pipeline no tiene releases.[/]")
        return 1

    print_releases_table(releases)

    rel_install = choose_release(releases,
                                 "¿Cuál release se va a INSTALAR?")
    if rel_install is None:
        _print("[yellow]Cancelado.[/]")
        return 0
    rel_rollback = choose_release(releases,
                                  "¿Cuál es el release de ROLLBACK?",
                                  exclude_id=rel_install.get("id", 0))
    if rel_rollback is None:
        _print("[yellow]Cancelado.[/]")
        return 0

    _print("\n[dim]Consultando artifacts, builds, PRs y repositorios…[/]")

    repos = get_repositories(org, project, headers, args.debug)
    repos_by_name = {r.get("name", "").lower(): r for r in repos}
    props_repo = find_properties_repo(repos, args.properties_repo)

    org_label = project.replace("_", " ")

    b_install = release_block(org, project, rel_install, defn_name,
                              headers, props_repo, repos_by_name,
                              args.branch, args.debug)
    b_rollback = release_block(org, project, rel_rollback, defn_name,
                               headers, props_repo, repos_by_name,
                               args.branch, args.debug)

    # RELASE_ID / RELEASE_ID del release a instalar vs rollback
    rel_var = (b_install["variables"].get("RELASE_ID")
               or b_install["variables"].get("RELEASE_ID") or "")
    rb_name = str(b_rollback["release_name"])
    rb_id = str(b_rollback["release_id"])
    rollback_match = (relase_id_matches_rollback(rel_var, rb_name, rb_id)
                      if rel_var else None)

    _print("\n[bold green]══════════ RELEASE A INSTALAR "
           "══════════[/]")
    print_block(b_install, org_label, rollback_match=rollback_match,
                release_id_var=rel_var)

    _print("\n[bold yellow]══════════ ROLLBACK "
           "══════════[/]")
    print_block(b_rollback, org_label)

    # Resumen de validacion
    _print("\n[bold cyan]── Validaciones ──[/]")
    if rel_var:
        if rollback_match:
            _print(f"[green]✔ RELASE_ID={rel_var} coincide con el "
                   f"rollback {rb_name}[/]")
        else:
            _print(f"[red]✘ RELASE_ID={rel_var} NO coincide con el "
                   f"rollback {rb_name} (id {rb_id})[/]")
    else:
        _print("[dim]El release a instalar no tiene variable "
               "RELASE_ID/RELEASE_ID.[/]")
    for tag, b in (("instalar", b_install), ("rollback", b_rollback)):
        if b["pr"] and b["pr_commit_matches"]:
            _print(f"[green]✔ Release a {tag}: PR "
                   f"#{b['pr'].get('pullRequestId')} — commit definitivo "
                   f"{b['pr_commit_short']} corresponde al release "
                   f"{b['commit_short']}[/]")
        elif b["pr"]:
            _print(f"[red]✘ Release a {tag}: PR "
                   f"#{b['pr'].get('pullRequestId')} — commit definitivo "
                   f"{b['pr_commit_short']} difiere del release "
                   f"{b['commit_short']}[/]")
        elif b["commit"]:
            _print(f"[yellow]⚠ Release a {tag}: no se encontro PR "
                   f"para el commit {b['commit_short']}[/]")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
