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
import re
import time
import requests
import pandas as pd
import argparse
from datetime import datetime
from base64 import b64encode
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *a, **k: None  # noqa: E731

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

load_dotenv(Path(__file__).parent.parent / ".env")

# ==========================================================
# CONFIGURACIÓN POR DEFECTO
# ==========================================================
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECTS = ["Compras.RMI"]
API_VERSION = "7.1"

# 🔒 LÍMITE GLOBAL (None = sin límite)
GLOBAL_LIMIT = None


def get_headers(pat: str):
    """Genera headers de autenticación para Azure DevOps."""
    auth = b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }


def az_get(url, headers, params=None, max_retries=5):
    """GET con retry y backoff exponencial para errores transitorios."""
    params = params or {}
    params["api-version"] = API_VERSION
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 503:
                wait = 2 ** attempt
                print(f"⚠️  503 en {url[:60]}... retry {attempt+1}/{max_retries} (espera {wait}s)")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"⚠️  Error en {url[:60]}... retry {attempt+1}/{max_retries}: {e}")
            time.sleep(wait)
    return {}


def safe_az_get(url, headers, params=None):
    """GET que nunca falla — retorna {} en caso de error."""
    try:
        return az_get(url, headers, params)
    except Exception as e:
        print(f"   ❌ Error silenciado: {e}")
        return {}


def apply_limit(items, limit):
    """Aplica límite si está definido."""
    if limit and isinstance(items, list):
        return items[:limit]
    return items


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


def get_yaml_file_text(org, project, repo_id, path, headers):
    """Obtiene contenido de archivo YAML desde repo."""
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
def get_repos(org, project, headers):
    """Obtiene lista de repositorios Git del proyecto."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories"
    data = az_get(url, headers)
    repos = apply_limit(data.get("value", []), GLOBAL_LIMIT)
    
    rows = []
    for r in repos:
        repo_id = r.get("id")
        repo_name = r.get("name")
        repo_url = r.get("webUrl")
        default_branch = r.get("defaultBranch", "refs/heads/master")
        
        first_commit = None
        last_commit = None
        total_commits = 0
        
        if default_branch:
            commits_url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/commits"
            commits = safe_az_get(
                commits_url, 
                headers,
                {"searchCriteria.itemVersion.version": default_branch.replace("refs/heads/", ""), "$top": 1}
            )
            c_last = commits.get("value", [{}])[0] if commits else None
            if c_last:
                last_date = c_last.get("author", {}).get("date")
                last_commit = last_date[:10] if last_date else None
            
            # Primer commit
            params_first = {
                "searchCriteria.itemVersion.version": default_branch.replace("refs/heads/", ""),
                "$top": 1,
                "$skip": 0,
            }
            all_commits = safe_az_get(commits_url, headers, params_first)
            all_items = all_commits.get("value", []) if all_commits else []
            total_commits = len(all_items)
            
            c_first = all_items[0] if all_items else None
            first_date = c_first.get("author", {}).get("date") if c_first else None
            first_commit = first_date[:10] if first_date else None
        
        rows.append({
            "project": project,
            "repo_id": repo_id,
            "repo_name": repo_name,
            "repo_url": repo_url,
            "default_branch": default_branch.replace("refs/heads/", "") if default_branch else None,
            "first_commit_date": first_commit,
            "last_commit_date": last_commit,
            "total_commits": total_commits,
        })
    
    return rows


# ==========================================================
# CI PIPELINES (YAML BUILDS)
# ==========================================================
def get_ci_pipelines(org, project, headers):
    """Obtiene pipelines CI (YAML builds) del proyecto."""
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions"
    builds_url = f"https://dev.azure.com/{org}/{project}/_apis/build/builds"
    
    data = az_get(base_url, headers)
    definitions = apply_limit(data.get("value", []), GLOBAL_LIMIT)
    
    rows = []
    for d in definitions:
        definition_id = d.get("id")
        
        try:
            detail_url = f"{base_url}/{definition_id}"
            detail = az_get(detail_url, headers)
        except requests.exceptions.HTTPError as e:
            print(f"    ❌ Error obteniendo CI {definition_id}: {e} — se omite")
            rows.append({
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
            })
            continue
        
        repo = detail.get("repository", {})
        repo_yaml_name = repo.get("name")
        repo_yaml_id = repo.get("id")
        yaml_path = detail.get("process", {}).get("yamlFilename")
        
        app_repo_name = None
        
        if repo_yaml_name and repo_yaml_name.lower() != "pipelines-projects":
            app_repo_name = repo_yaml_name
        else:
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
        
        rows.append({
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
        })
    
    return rows


# ==========================================================
# CD PIPELINES (CLASSIC RELEASES)
# ==========================================================
def get_cd_pipelines(org, project, headers):
    """Obtiene pipelines CD (classic releases) del proyecto."""
    base_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions"
    releases_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases"
    
    data = az_get(base_url, headers)
    definitions = apply_limit(data.get("value", []), GLOBAL_LIMIT)
    
    rows = []
    for d in definitions:
        definition_id = d.get("id")
        
        try:
            detail_url = f"{base_url}/{definition_id}"
            detail = az_get(detail_url, headers)
        except requests.exceptions.HTTPError as e:
            print(f"    ❌ Error obteniendo CD {definition_id}: {e} — se omite")
            rows.append({
                "project": project,
                "cd_pipeline_id": definition_id,
                "cd_pipeline_name": d.get("name"),
                "repo_name": None,
                "last_release_id": None,
                "last_release_date": None,
                "last_release_status": "ERROR",
                "last_release_user": None,
                "cd_pipeline_url": f"https://dev.azure.com/{org}/{project}/_release?_a=definitions&definitionId={definition_id}"
            })
            continue
        
        # Extraer repo desde artefactos
        artifacts = detail.get("artifacts", [])
        repo_name = None
        for art in artifacts:
            if art.get("type") == "Git":
                alias = art.get("alias", "")
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
        
        rows.append({
            "project": project,
            "cd_pipeline_id": definition_id,
            "cd_pipeline_name": detail.get("name"),
            "repo_name": repo_name,
            "last_release_id": last_release_id,
            "last_release_date": last_release_date,
            "last_release_status": last_release_status,
            "last_release_user": last_release_user,
            "cd_pipeline_url": f"https://dev.azure.com/{org}/{project}/_release?_a=definitions&definitionId={definition_id}"
        })
    
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
    
    args = parser.parse_args()
    
    # Configurar PAT
    pat = os.getenv("AZURE_PAT", "")
    if not pat:
        print("❌ No se encontró PAT. Agrega AZURE_PAT en el archivo .env")
        exit(1)
    
    headers = get_headers(pat)
    
    # Configurar proyectos
    projects = args.project if args.project else DEFAULT_PROJECTS
    
    # Configurar límite global
    if args.limit:
        global GLOBAL_LIMIT
        GLOBAL_LIMIT = args.limit
    
    # Generar nombre de archivo
    output_file = args.output or f"inventario_cicd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    print(f"🔍 Analizando organización: {args.org}")
    print(f"📁 Proyectos: {', '.join(projects)}")
    print(f"💾 Output: {output_file}")
    print("=" * 60)
    
    repos_rows = []
    ci_rows = []
    cd_rows = []
    
    for project in projects:
        print(f"\n📦 Proyecto: {project}")
        
        print(f"\n  ── Obteniendo repositorios ──")
        repos_rows.extend(get_repos(args.org, project, headers))
        print(f"  ✅ {len(repos_rows)} repos encontrados")
        
        print(f"\n  ── Obteniendo CI pipelines ──")
        ci_rows.extend(get_ci_pipelines(args.org, project, headers))
        print(f"  ✅ {len(ci_rows)} CI pipelines encontrados")
        
        print(f"\n  ── Obteniendo CD pipelines ──")
        cd_rows.extend(get_cd_pipelines(args.org, project, headers))
        print(f"  ✅ {len(cd_rows)} CD pipelines encontrados")
    
    print(f"\n🔗 Construyendo relación Repo → CI → CD ...")
    relations_rows = build_repo_ci_cd_relation(repos_rows, ci_rows, cd_rows)
    print(f"  ✅ {len(relations_rows)} relaciones generadas")
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        pd.DataFrame(repos_rows).to_excel(writer, "Repositorios", index=False)
        pd.DataFrame(ci_rows).to_excel(writer, "CI_Pipelines", index=False)
        pd.DataFrame(cd_rows).to_excel(writer, "CD_Pipelines", index=False)
        pd.DataFrame(relations_rows).to_excel(writer, "Repo_CI_CD", index=False)
    
    print(f"\n✅ Reporte generado: {output_file}")


if __name__ == "__main__":
    main()
