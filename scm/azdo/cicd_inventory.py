#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CICD Inventory Reporter v1.0.0
Genera inventario completo de repos, CI pipelines (YAML builds) y CD pipelines (classic releases)
en Azure DevOps, con relación Repo ↔ CI ↔ CD.

Uso:
    python cicd_inventory.py --org Coppel-Retail --project "Compras.RMI"
    python cicd_inventory.py --org Coppel-Retail --project "Compras.RMI" --limit 50

Autor: Harold Adrian (migrado desde Comercial/scripts/inventarioV4.PY)
"""

import os
import sys
import re
import time
import shutil
import subprocess
import tempfile
import requests
import pandas as pd
import argparse
from datetime import datetime
from base64 import b64encode
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *a, **k: None  # noqa: E731

try:
    from rich.progress import Progress, SpinnerColumn, BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir, resolve_output_path
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
    from datetime import datetime as _dt
    _FMT_EXT = {"excel": ".xlsx", "csv": ".csv", "json": ".json"}
    def resolve_output_path(output_arg, base_name, default_format="excel"):
        output_dir = get_output_dir("outcome")
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = _FMT_EXT.get(default_format, ".xlsx")
        if not output_arg:
            return str(output_dir / f"{base_name}_{_dt.now().strftime('%Y%m%d_%H%M%S')}{ext}")
        if output_arg.lower() in _FMT_EXT:
            ext = _FMT_EXT[output_arg.lower()]
            return str(output_dir / f"{base_name}_{_dt.now().strftime('%Y%m%d_%H%M%S')}{ext}")
        p = _Path(output_arg)
        if p.suffix == "":
            p = p.with_suffix(ext)
        return str(p.resolve())
# -------------------------------------------------------------------

load_dotenv(Path(__file__).parent.parent / ".env")

# ==========================================================
# CONFIGURACIÓN POR DEFECTO
# ==========================================================
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECTS = ["Compras.RMI"]
API_VERSION = "7.1"
DEFAULT_WORKERS = 30

# 🔒 LÍMITE GLOBAL (None = sin límite)
GLOBAL_LIMIT = None


def _progress_context():
    """Retorna un contexto Rich Progress que escribe al terminal real (no TeeWriter)."""
    if RICH_AVAILABLE:
        console = Console(file=sys.__stdout__)
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=console,
        )
    return None


class _SimpleProgress:
    """Fallback: imprime progreso como texto simple."""
    def __init__(self, desc, total):
        self.desc = desc
        self.total = total
        self.completed = 0
        self._last_pct = -1

    def advance(self, n=1):
        self.completed += n
        pct = int(self.completed / self.total * 100) if self.total else 100
        if pct != self._last_pct and pct % 10 == 0:
            print(f"  {self.desc}: {self.completed}/{self.total} ({pct}%)")
            self._last_pct = pct

    def finish(self, msg):
        print(f"  ✅ {msg}")


class TeeWriter:
    """Escribe stdout a consola Y archivo de log simultáneamente."""
    def __init__(self, log_path):
        self.terminal = sys.__stdout__
        self.log = open(log_path, "w", encoding="utf-8")
        self.log_path = log_path
        self._paused = False  # Cuando True, solo escribe al archivo log

    def write(self, message):
        self.log.write(message)
        if not self._paused:
            self.terminal.write(message)

    def flush(self):
        self.log.flush()
        if not self._paused:
            self.terminal.flush()

    def close(self):
        self.log.close()

    def pause_terminal(self):
        """Pausa escritura al terminal (Rich toma control)."""
        self._paused = True

    def resume_terminal(self):
        """Reanuda escritura al terminal."""
        self._paused = False


def setup_logging(script_name):
    """Configura TeeWriter para que stdout vaya a consola + archivo log en outcome."""
    output_dir = get_output_dir("outcome")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    tee = TeeWriter(log_path)
    sys.stdout = tee
    print(f"📝 Log: {log_path.resolve()}")
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    return tee


def teardown_logging(tee):
    """Restaura stdout y cierra archivo de log."""
    print(f"\n📝 Log guardado: {tee.log_path.resolve()}")
    sys.stdout = tee.terminal
    tee.close()


def get_headers(pat: str):
    """Genera headers de autenticación para Azure DevOps."""
    auth = b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }


def az_get(url, headers, params=None, max_retries=5):
    """GET con retry y backoff exponencial para errores transitorios (5xx/red)."""
    params = params or {}
    params["api-version"] = API_VERSION
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code >= 500:
                wait = 2 ** attempt
                print(f"⚠️  {r.status_code} en {url[:60]}... retry {attempt+1}/{max_retries} (espera {wait}s)")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            # 4xx = client error, no reintentar
            raise
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"⚠️  Error en {url[:60]}... retry {attempt+1}/{max_retries}: {e}")
            time.sleep(wait)
    return {}


def safe_az_get(url, headers, params=None):
    """GET que nunca falla — retorna {} en caso de error (loggea el error)."""
    try:
        return az_get(url, headers, params)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}


def apply_limit(items, limit):
    """Aplica límite si está definido."""
    if limit and isinstance(items, list):
        return items[:limit]
    return items


def normalize_org(org: str) -> str:
    """Extrae el nombre de la organización desde una URL completa o nombre simple.

    Acepta tanto 'Coppel-Retail' como 'https://dev.azure.com/Coppel-Retail'.
    """
    if org.startswith("http"):
        # https://dev.azure.com/Coppel-Retail → Coppel-Retail
        return org.rstrip("/").split("/")[-1]
    return org


def normalize_repo_name(name):
    """Normaliza nombre de repo para matching."""
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    return name


def parse_app_repo_from_yaml_text(yaml_text):
    """Extrae nombre de repo de app desde YAML de pipeline."""
    if not yaml_text:
        return None
    patterns = [
        r'repositories:\s*\n\s*-\s*repository:\s*([^\n]+)',
        r'repository:\s*([^\n]+)',
        r'name:\s*([^\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, yaml_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def clone_pipelines_projects(org, project, pat, clone_dir=None):
    """Clona el repo pipelines-projects (shallow, single-branch master) a un directorio temporal.
    Retorna la ruta del directorio del clone o None si falla.
    Si clone_dir ya existe, hace git pull en lugar de git clone.
    """
    repo_url = f"https://{pat}@dev.azure.com/{org}/{project}/_git/pipelines-projects"
    public_url = f"https://dev.azure.com/{org}/{project}/_git/pipelines-projects"
    
    if clone_dir is None:
        clone_dir = os.path.join(tempfile.gettempdir(), f"pipelines-projects-{org}-{project}")
    
    clone_path = os.path.join(clone_dir, "pipelines-projects")
    
    try:
        if os.path.isdir(os.path.join(clone_path, ".git")):
            # Ya existe: hacer pull + limpiar PAT del remote
            print(f"  🔄 git pull pipelines-projects (cache)...")
            subprocess.run(
                ["git", "remote", "set-url", "origin", repo_url],
                cwd=clone_path, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=clone_path, check=True, capture_output=True,
            )
            # Limpiar PAT del remote
            subprocess.run(
                ["git", "remote", "set-url", "origin", public_url],
                cwd=clone_path, check=True, capture_output=True,
            )
        else:
            # Clone nuevo
            print(f"  📥 git clone pipelines-projects (shallow)...")
            os.makedirs(clone_dir, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", "--branch", "master", repo_url, clone_path],
                cwd=clone_dir, check=True, capture_output=True,
            )
            # Limpiar PAT del remote inmediatamente
            subprocess.run(
                ["git", "remote", "set-url", "origin", public_url],
                cwd=clone_path, check=True, capture_output=True,
            )
        return clone_path
    except FileNotFoundError:
        print("  ⚠️ git no encontrado en PATH. Se usará API como fallback.")
        return None
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else str(e)
        if "not found" in stderr.lower() or "does not exist" in stderr.lower():
            print(f"  ℹ️ Repo pipelines-projects no existe en este proyecto. Se omite clone.")
        else:
            print(f"  ⚠️ Error en git clone/pull: {stderr[:200]}")
        return None


def read_yaml_local(clone_path, yaml_path):
    """Lee un archivo YAML desde el clone local de pipelines-projects."""
    if not clone_path or not yaml_path:
        return None
    full_path = os.path.join(clone_path, yaml_path.lstrip("/"))
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def get_yaml_file_text(org, project, repo_id, path, headers):
    """Obtiene contenido de archivo YAML desde repo (fallback API)."""
    if not repo_id or not path:
        return None
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/items"
    params = {
        "path": path,
        "includeContent": "true",
        "api-version": API_VERSION
    }
    data = safe_az_get(url, headers, params)
    return data.get("content")


# ==========================================================
# REPOS
# ==========================================================
def _fetch_repo_commits(repo_info, org, project, headers):
    """Worker: obtiene info de commits para un repo (usado por ThreadPoolExecutor)."""
    repo_id = repo_info.get("id")
    repo_name = repo_info.get("name")
    repo_url = repo_info.get("webUrl")
    default_branch = repo_info.get("defaultBranch", "refs/heads/master")
    
    first_commit = None
    last_commit = None
    total_commits = 0
    
    if default_branch:
        branch_name = default_branch.replace("refs/heads/", "")
        commits_url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/commits"
        commits = safe_az_get(
            commits_url, 
            headers,
            {"searchCriteria.itemVersion.version": branch_name, "$top": 1}
        )
        c_last = commits.get("value", [{}])[0] if commits else None
        if c_last:
            last_date = c_last.get("author", {}).get("date")
            last_commit = last_date[:10] if last_date else None
        
        # Primer commit (usar commitCount del primer resultado si hay)
        all_items = commits.get("value", []) if commits else []
        total_commits = commits.get("count", len(all_items))
        
        c_first = all_items[0] if all_items else None
        first_date = c_first.get("author", {}).get("date") if c_first else None
        first_commit = first_date[:10] if first_date else None
    
    return {
        "project": project,
        "repo_id": repo_id,
        "repo_name": repo_name,
        "repo_url": repo_url,
        "default_branch": default_branch.replace("refs/heads/", "") if default_branch else None,
        "first_commit_date": first_commit,
        "last_commit_date": last_commit,
        "total_commits": total_commits,
    }


def get_repos(org, project, headers, workers=DEFAULT_WORKERS, tee=None):
    """Obtiene lista de repositorios Git del proyecto (commits en paralelo)."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories"
    data = az_get(url, headers)
    repos = apply_limit(data.get("value", []), GLOBAL_LIMIT)
    total = len(repos)
    
    rows = []
    progress = _progress_context()
    
    if progress:
        if tee: tee.pause_terminal()
        with progress:
            task = progress.add_task("📦 Repositorios", total=total)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_fetch_repo_commits, r, org, project, headers): r for r in repos}
                for fut in as_completed(futures):
                    try:
                        rows.append(fut.result())
                    except Exception as e:
                        repo_name = futures[fut].get("name", "?")
                        print(f"   ⚠️ Error en repo {repo_name}: {e}")
                    progress.advance(task)
        if tee: tee.resume_terminal()
    else:
        sp = _SimpleProgress("📦 Repositorios", total)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_repo_commits, r, org, project, headers): r for r in repos}
            for fut in as_completed(futures):
                try:
                    rows.append(fut.result())
                except Exception as e:
                    repo_name = futures[fut].get("name", "?")
                    print(f"   ⚠️ Error en repo {repo_name}: {e}")
                sp.advance()
        sp.finish(f"{len(rows)}/{total} repositorios procesados")
    
    rows.sort(key=lambda x: x.get("repo_name", ""))
    return rows


# ==========================================================
# CI PIPELINES (YAML BUILDS)
# ==========================================================
def _fetch_ci_pipeline(d, org, project, headers, pipelines_clone_path=None):
    """Worker: obtiene detalle + último build de un CI pipeline."""
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions"
    builds_url = f"https://dev.azure.com/{org}/{project}/_apis/build/builds"
    definition_id = d.get("id")
    
    try:
        detail_url = f"{base_url}/{definition_id}"
        detail = az_get(detail_url, headers)
    except requests.exceptions.HTTPError as e:
        return {
            "project": project,
            "ci_pipeline_id": definition_id,
            "ci_pipeline_name": d.get("name"),
            "repo_name": None,
            "repo_yaml": None,
            "yaml_path": None,
            "last_run_id": None,
            "last_run_date": None,
            "last_run_status": "ERROR",
            "last_run_result": str(e)[:200],
            "last_run_user": None,
            "ci_pipeline_url": f"https://dev.azure.com/{org}/{project}/_build?definitionId={definition_id}"
        }
    
    repo = detail.get("repository", {})
    repo_yaml_name = repo.get("name")
    repo_yaml_id = repo.get("id")
    yaml_path = detail.get("process", {}).get("yamlFilename")
    
    app_repo_name = None
    
    if repo_yaml_name and repo_yaml_name.lower() != "pipelines-projects":
        app_repo_name = repo_yaml_name
    else:
        # Intentar lectura local desde clone, fallback a API
        yaml_text = read_yaml_local(pipelines_clone_path, yaml_path)
        if yaml_text is None:
            yaml_text = get_yaml_file_text(org, project, repo_yaml_id, yaml_path, headers)
        app_repo_name = parse_app_repo_from_yaml_text(yaml_text)
    
    # Último build
    last_run_id = None
    last_run_date = None
    last_run_status = None
    last_run_result = None
    last_run_user = None
    
    try:
        builds_data = safe_az_get(
            builds_url,
            headers,
            {"definitions": definition_id, "$top": 1, "queryOrder": "finishTimeDescending"}
        )
        b = builds_data.get("value", [{}])[0] if builds_data else None
        if b:
            last_run_id = b.get("id")
            last_run_date = b.get("finishTime", "")[:10] if b.get("finishTime") else None
            last_run_status = b.get("status")
            last_run_result = b.get("result")
            last_run_user = (b.get("requestedFor") or {}).get("displayName")
    except Exception as e:
        print(f"   ⚠️ Error consultando builds: {e}")
    
    return {
        "project": project,
        "ci_pipeline_id": definition_id,
        "ci_pipeline_name": detail.get("name"),
        "repo_name": app_repo_name,
        "repo_yaml": repo_yaml_name,
        "yaml_path": yaml_path,
        "last_run_id": last_run_id,
        "last_run_date": last_run_date,
        "last_run_status": last_run_status,
        "last_run_result": last_run_result,
        "last_run_user": last_run_user,
        "ci_pipeline_url": f"https://dev.azure.com/{org}/{project}/_build?definitionId={definition_id}"
    }


def get_ci_pipelines(org, project, headers, workers=DEFAULT_WORKERS, pipelines_clone_path=None, tee=None):
    """Obtiene pipelines CI (YAML builds) del proyecto (en paralelo)."""
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions"
    
    data = az_get(base_url, headers)
    definitions = apply_limit(data.get("value", []), GLOBAL_LIMIT)
    total = len(definitions)
    
    rows = []
    progress = _progress_context()
    
    if progress:
        if tee: tee.pause_terminal()
        with progress:
            task = progress.add_task("🔧 CI Pipelines", total=total)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_fetch_ci_pipeline, d, org, project, headers, pipelines_clone_path): d for d in definitions}
                for fut in as_completed(futures):
                    try:
                        rows.append(fut.result())
                    except Exception as e:
                        def_name = futures[fut].get("name", "?")
                        print(f"   ⚠️ Error en CI pipeline {def_name}: {e}")
                    progress.advance(task)
        if tee: tee.resume_terminal()
    else:
        sp = _SimpleProgress("🔧 CI Pipelines", total)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_ci_pipeline, d, org, project, headers, pipelines_clone_path): d for d in definitions}
            for fut in as_completed(futures):
                try:
                    rows.append(fut.result())
                except Exception as e:
                    def_name = futures[fut].get("name", "?")
                    print(f"   ⚠️ Error en CI pipeline {def_name}: {e}")
                sp.advance()
        sp.finish(f"{len(rows)}/{total} CI pipelines procesados")
    
    rows.sort(key=lambda x: x.get("ci_pipeline_name", ""))
    return rows


# ==========================================================
# CD PIPELINES (CLASSIC RELEASES)
# ==========================================================
def _fetch_cd_pipeline(d, org, project, headers):
    """Worker: obtiene detalle + último release de un CD pipeline."""
    base_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions"
    releases_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases"
    definition_id = d.get("id")
    
    try:
        detail_url = f"{base_url}/{definition_id}"
        detail = az_get(detail_url, headers)
    except requests.exceptions.HTTPError as e:
        return {
            "project": project,
            "cd_pipeline_id": definition_id,
            "cd_pipeline_name": d.get("name"),
            "repo_name": None,
            "last_release_id": None,
            "last_release_date": None,
            "last_release_status": "ERROR",
            "last_release_user": None,
            "cd_pipeline_url": f"https://dev.azure.com/{org}/{project}/_release?_a=definitions&definitionId={definition_id}"
        }
    
    # Extraer repo desde artefactos
    artifacts = detail.get("artifacts", [])
    repo_name = None
    for art in artifacts:
        if art.get("type") == "Git":
            ref = art.get("definitionReference", {})
            full_repo = ref.get("definition", {}).get("name", "")
            if full_repo:
                repo_name = full_repo.split("/")[-1] if "/" in full_repo else full_repo
            break
    
    # Último release
    last_release_id = None
    last_release_date = None
    last_release_status = None
    last_release_user = None
    
    try:
        rel_data = safe_az_get(
            releases_url,
            headers,
            {"definitionId": definition_id, "$top": 1}
        )
        rel = rel_data.get("value", [{}])[0] if rel_data else None
        if rel:
            last_release_id = rel.get("id")
            last_release_date = rel.get("createdOn", "")[:10] if rel.get("createdOn") else None
            last_release_status = rel.get("status")
            last_release_user = (rel.get("createdBy") or {}).get("displayName")
    except Exception as e:
        print(f"   ⚠️ Error consultando releases: {e}")
    
    return {
        "project": project,
        "cd_pipeline_id": definition_id,
        "cd_pipeline_name": detail.get("name"),
        "repo_name": repo_name,
        "last_release_id": last_release_id,
        "last_release_date": last_release_date,
        "last_release_status": last_release_status,
        "last_release_user": last_release_user,
        "cd_pipeline_url": f"https://dev.azure.com/{org}/{project}/_release?_a=definitions&definitionId={definition_id}"
    }


def get_cd_pipelines(org, project, headers, workers=DEFAULT_WORKERS, tee=None):
    """Obtiene pipelines CD (classic releases) del proyecto (en paralelo)."""
    base_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions"
    
    data = az_get(base_url, headers)
    definitions = apply_limit(data.get("value", []), GLOBAL_LIMIT)
    total = len(definitions)
    
    rows = []
    progress = _progress_context()
    
    if progress:
        if tee: tee.pause_terminal()
        with progress:
            task = progress.add_task("🚀 CD Pipelines", total=total)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_fetch_cd_pipeline, d, org, project, headers): d for d in definitions}
                for fut in as_completed(futures):
                    try:
                        rows.append(fut.result())
                    except Exception as e:
                        def_name = futures[fut].get("name", "?")
                        print(f"   ⚠️ Error en CD pipeline {def_name}: {e}")
                    progress.advance(task)
        if tee: tee.resume_terminal()
    else:
        sp = _SimpleProgress("🚀 CD Pipelines", total)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_cd_pipeline, d, org, project, headers): d for d in definitions}
            for fut in as_completed(futures):
                try:
                    rows.append(fut.result())
                except Exception as e:
                    def_name = futures[fut].get("name", "?")
                    print(f"   ⚠️ Error en CD pipeline {def_name}: {e}")
                sp.advance()
        sp.finish(f"{len(rows)}/{total} CD pipelines procesados")
    
    rows.sort(key=lambda x: x.get("cd_pipeline_name", ""))
    return rows


# ==========================================================
# RELACIÓN REPO ↔ CI ↔ CD
# ==========================================================
def build_repo_ci_cd_relation(repos_rows, ci_rows, cd_rows):
    """Construye matriz de relación entre repos, CI y CD."""
    ci_by_repo = {}
    for ci in ci_rows:
        name = normalize_repo_name(ci.get("repo_name"))
        if name:
            ci_by_repo.setdefault(name, []).append(ci)
    
    cd_by_repo = {}
    for cd in cd_rows:
        name = normalize_repo_name(cd.get("repo_name"))
        if name:
            cd_by_repo.setdefault(name, []).append(cd)
    
    relations = []
    for repo in repos_rows:
        repo_name = repo.get("repo_name")
        repo_norm = normalize_repo_name(repo_name)
        project = repo.get("project")
        
        cis = ci_by_repo.get(repo_norm, [])
        cds = cd_by_repo.get(repo_norm, [])
        
        if not cis and not cds:
            relations.append({
                "project": project,
                "repo_name": repo_name,
                "ci_pipeline": None,
                "cd_pipeline": None,
            })
            continue
        
        for ci in cis or [None]:
            for cd in cds or [None]:
                relations.append({
                    "project": project,
                    "repo_name": repo_name,
                    "repo_name_normalized": repo_norm,
                    "ci_pipeline": ci.get("ci_pipeline_name") if ci else None,
                    "ci_pipeline_id": ci.get("ci_pipeline_id") if ci else None,
                    "ci_last_run": ci.get("last_run_date") if ci else None,
                    "ci_last_status": ci.get("last_run_status") if ci else None,
                    "cd_pipeline": cd.get("cd_pipeline_name") if cd else None,
                    "cd_pipeline_id": cd.get("cd_pipeline_id") if cd else None,
                    "cd_last_release": cd.get("last_release_date") if cd else None,
                    "cd_last_status": cd.get("last_release_status") if cd else None,
                })
    
    return relations


def main():
    parser = argparse.ArgumentParser(
        description="CICD Inventory Reporter - Inventario de repos, CI y CD pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python cicd_inventory.py
  python cicd_inventory.py --org Coppel-Retail --project "Compras.RMI"
  python cicd_inventory.py --org Coppel-Retail --project "Compras.RMI" "Otro.Proyecto"
  python cicd_inventory.py --org Coppel-Retail --limit 100
        """
    )
    parser.add_argument("--org", default=DEFAULT_ORG,
                       help=f"Organización Azure DevOps (default: {DEFAULT_ORG})")
    parser.add_argument("--project", "-p", nargs="+", default=None,
                       help=f"Proyecto(s) a analizar (default: {DEFAULT_PROJECTS})")
    parser.add_argument("--limit", type=int, default=None,
                       help="Límite de items por categoría (default: sin límite)")
    parser.add_argument("--output", "-o", default=None,
                       help="Nombre del archivo Excel de salida")
    parser.add_argument("--pat", default=None,
                       help="PAT de Azure DevOps (default: env AZURE_PAT)")

    args = parser.parse_args()

    # Configurar PAT
    pat = args.pat or os.getenv("AZURE_PAT", "")
    if not pat:
        print("❌ No se encontró PAT. Agrega AZURE_PAT en el archivo .env o usa --pat")
        exit(1)
    
    headers = get_headers(pat)
    
    # Configurar logging a archivo en outcome
    tee = setup_logging("cicd_inventory")
    
    # Configurar proyectos
    projects = args.project if args.project else DEFAULT_PROJECTS
    
    # Configurar límite global
    if args.limit:
        global GLOBAL_LIMIT
        GLOBAL_LIMIT = args.limit
    
    output_file = resolve_output_path(args.output, "inventario_cicd")
    
    # Normalizar org: aceptar tanto URL completa como nombre simple
    org = normalize_org(args.org)

    print(f"🔍 Analizando organización: {org}")
    print(f"📁 Proyectos: {', '.join(projects)}")
    print(f"💾 Output: {output_file}")
    print(f"⚡ Workers: {DEFAULT_WORKERS}")
    print("=" * 60)
    
    start_time = time.time()
    repos_rows = []
    ci_rows = []
    cd_rows = []
    
    for project in projects:
        print(f"\n📦 Proyecto: {project}")
        
        print(f"\n  ── Obteniendo repositorios ──")
        project_repos = get_repos(org, project, headers, tee=tee)
        repos_rows.extend(project_repos)
        print(f"  📊 Total repositorios: {len(project_repos)}")
        
        # Clonar pipelines-projects para lectura local de YAMLs
        print(f"\n  ── Preparando pipelines-projects ──")
        pipelines_clone_path = clone_pipelines_projects(org, project, pat)
        if pipelines_clone_path:
            print(f"  ✅ Clone local: {pipelines_clone_path}")
        else:
            print(f"  ℹ️ Se usará API para leer YAMLs de pipelines-projects")
        
        # CI y CD en paralelo (son independientes): 15 workers cada uno = 30 hilos totales
        parallel_workers = DEFAULT_WORKERS // 2
        print(f"\n  ── Obteniendo CI + CD pipelines en paralelo ({parallel_workers} hilos c/u) ──")
        with ThreadPoolExecutor(max_workers=2) as executor:
            ci_future = executor.submit(get_ci_pipelines, org, project, headers, parallel_workers, pipelines_clone_path, tee)
            cd_future = executor.submit(get_cd_pipelines, org, project, headers, parallel_workers, tee)
            project_ci = ci_future.result()
            project_cd = cd_future.result()
        ci_rows.extend(project_ci)
        cd_rows.extend(project_cd)
        print(f"  📊 Total CI pipelines: {len(project_ci)}")
        print(f"  📊 Total CD pipelines: {len(project_cd)}")
    
    print(f"\n🔗 Construyendo relación Repo → CI → CD ...")
    relations_rows = build_repo_ci_cd_relation(repos_rows, ci_rows, cd_rows)
    
    elapsed = time.time() - start_time
    
    # Resumen final
    repos_with_ci = sum(1 for r in relations_rows if r.get("ci_pipeline"))
    repos_with_cd = sum(1 for r in relations_rows if r.get("cd_pipeline"))
    repos_with_both = sum(1 for r in relations_rows if r.get("ci_pipeline") and r.get("cd_pipeline"))
    repos_no_pipeline = sum(1 for r in relations_rows if not r.get("ci_pipeline") and not r.get("cd_pipeline"))
    
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMEN")
    print(f"{'=' * 60}")
    print(f"  📦 Repositorios:       {len(repos_rows)}")
    print(f"  🔧 CI Pipelines:      {len(ci_rows)}")
    print(f"  🚀 CD Pipelines:      {len(cd_rows)}")
    print(f"  🔗 Relaciones:        {len(relations_rows)}")
    print(f"  ├─ Con CI:            {repos_with_ci}")
    print(f"  ├─ Con CD:            {repos_with_cd}")
    print(f"  ├─ Con CI + CD:       {repos_with_both}")
    print(f"  └─ Sin pipeline:      {repos_no_pipeline}")
    print(f"  ⏱️  Tiempo total:      {elapsed:.1f}s")
    print(f"{'=' * 60}")
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        pd.DataFrame(repos_rows).to_excel(writer, "Repositorios", index=False)
        pd.DataFrame(ci_rows).to_excel(writer, "CI_Pipelines", index=False)
        pd.DataFrame(cd_rows).to_excel(writer, "CD_Pipelines", index=False)
        pd.DataFrame(relations_rows).to_excel(writer, "Repo_CI_CD", index=False)
    
    excel_path = Path(output_file).resolve()
    print(f"\n✅ Reporte generado: {excel_path}")
    
    teardown_logging(tee)


if __name__ == "__main__":
    main()
