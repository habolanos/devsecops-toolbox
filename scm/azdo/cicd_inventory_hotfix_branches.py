#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotfix Branches Inventory v1.0.0
Inventario de ramas hotfix con creador, fecha de creación y actividad del repositorio.

Uso:
    python hotfix_branches_inventory.py --org Coppel-Retail --project "Cadena_de_Suministros"
    python hotfix_branches_inventory.py --org Coppel-Retail --project "Compras.RMI" --pattern "hotfix/*"

Autor: Harold Adrian (migrado desde Comercial/scripts/ramasV3.py)
"""

import requests
import pandas as pd
import time
import os
import argparse
import sys
from base64 import b64encode
from datetime import datetime
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

# ======================================================
# CONFIGURACIÓN POR DEFECTO
# ======================================================
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECT = "Cadena_de_Suministros"
DEFAULT_PATTERN = "hotfix"
API_VERSION = "7.0"


def get_headers(pat: str):
    """Genera headers de autenticación."""
    auth = b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }


def azure_get(url: str, headers: dict, params=None, retries=5, timeout=15):
    """GET con retry para errores 503."""
    for attempt in range(retries):
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        
        if r.status_code == 503:
            wait = 2 * (attempt + 1)
            print(f"⚠️ 503 Service Unavailable → retry {attempt+1}/{retries} (wait {wait}s)")
            time.sleep(wait)
            continue
        
        r.raise_for_status()
        return r.json()
    
    raise Exception(f"Max retries ({retries}) exceeded for {url}")


def normalize_org(org: str) -> str:
    """Extrae el nombre de la organización desde una URL completa o nombre simple."""
    if org.startswith("http"):
        return org.rstrip("/").split("/")[-1]
    return org


def get_repositories(org: str, project: str, headers: dict):
    """Obtiene lista de repositorios."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories"
    params = {"api-version": API_VERSION}
    data = azure_get(url, headers, params)
    return data.get("value", [])


def get_branches(org: str, project: str, repo_id: str, headers: dict):
    """Obtiene ramas de un repositorio."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/refs"
    params = {
        "api-version": API_VERSION,
        "filter": "heads/",
        "includeStatuses": "true"
    }
    data = azure_get(url, headers, params)
    return data.get("value", [])


def get_branch_creator(org: str, project: str, repo_id: str, branch_name: str, headers: dict):
    """Obtiene información del creador de una rama."""
    try:
        # Usar pushes para encontrar el primer push a esa rama
        url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/pushes"
        params = {
            "api-version": API_VERSION,
            "searchCriteria.refName": f"refs/heads/{branch_name}",
            "$top": 1
        }
        data = azure_get(url, headers, params)
        pushes = data.get("value", [])
        
        if pushes:
            first_push = pushes[-1]  # El más antiguo
            return {
                "creator": first_push.get("pushedBy", {}).get("displayName", "Unknown"),
                "date": first_push.get("date", "")[:10] if first_push.get("date") else "Unknown",
                "push_id": first_push.get("pushId")
            }
    except Exception as e:
        print(f"   ⚠️ Error obteniendo creador de {branch_name}: {e}")
    
    return {"creator": "Unknown", "date": "Unknown", "push_id": None}


def process_repository(org: str, project: str, repo: dict, pattern: str, headers: dict):
    """Procesa un repositorio y retorna ramas hotfix."""
    repo_id = repo.get("id")
    repo_name = repo.get("name")
    
    branches = get_branches(org, project, repo_id, headers)
    hotfix_branches = []
    
    for branch in branches:
        branch_name = branch.get("name", "").replace("refs/heads/", "")
        
        if pattern.lower() in branch_name.lower():
            creator_info = get_branch_creator(org, project, repo_id, branch_name, headers)
            
            hotfix_branches.append({
                "repo_name": repo_name,
                "branch_name": branch_name,
                "creator": creator_info["creator"],
                "created_date": creator_info["date"],
                "is_locked": branch.get("isLocked", False),
                "creator_id": creator_info["push_id"]
            })
    
    return hotfix_branches


def export_to_excel(data: list, org: str, project: str, output_file: str = None):
    """Exporta a Excel."""
    if not output_file:
        output_dir = get_output_dir()
        default_name = f"hotfix_branches_{org}_{project}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_file = str(output_dir / default_name)
    
    df = pd.DataFrame(data)
    
    # Agregar columna de antigüedad
    df['days_since_creation'] = pd.to_datetime(df['created_date'], errors='coerce').apply(
        lambda x: (datetime.now() - x).days if pd.notna(x) else None
    )
    
    # Reordenar columnas
    cols = ['repo_name', 'branch_name', 'creator', 'created_date', 'days_since_creation', 'is_locked']
    df = df[cols]
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Hotfix Branches', index=False)
        
        # Hoja de resumen
        summary = df.groupby('repo_name').size().reset_index(name='hotfix_count')
        summary.to_excel(writer, sheet_name='Summary by Repo', index=False)
        
        creator_summary = df.groupby('creator').size().reset_index(name='branches_created')
        creator_summary.to_excel(writer, sheet_name='Summary by Creator', index=False)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Hotfix Branches Inventory - Ramas hotfix con creador y fecha",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python hotfix_branches_inventory.py
  python hotfix_branches_inventory.py --org Coppel-Retail --project "Cadena_de_Suministros"
  python hotfix_branches_inventory.py --org Coppel-Retail --project "Compras.RMI" --pattern "hotfix"
        """
    )
    parser.add_argument("--org", default=DEFAULT_ORG,
                       help=f"Organización Azure DevOps (default: {DEFAULT_ORG})")
    parser.add_argument("--project", "-p", default=DEFAULT_PROJECT,
                       help=f"Proyecto (default: {DEFAULT_PROJECT})")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN,
                       help=f"Patrón para filtrar ramas (default: {DEFAULT_PATTERN})")
    parser.add_argument("--pat", default=None,
                       help="PAT de Azure DevOps (default: env AZURE_PAT)")
    parser.add_argument("--output", "-o", default=None,
                       help="Nombre del archivo Excel de salida")
    
    args = parser.parse_args()
    
    # Obtener PAT
    pat = args.pat or os.getenv("AZURE_PAT", "")
    if not pat:
        print("❌ ERROR: Variable AZURE_PAT no definida")
        sys.exit(1)
    
    headers = get_headers(pat)
    
    org = normalize_org(args.org)

    print(f"🔍 Buscando ramas con patrón '{args.pattern}'...")
    print(f"   Org: {org}")
    print(f"   Project: {args.project}")
    print(f"   API: {API_VERSION}")
    print("=" * 60)
    
    repos = get_repositories(org, args.project, headers)
    print(f"📦 {len(repos)} repositorios encontrados\n")
    
    all_hotfix_branches = []
    
    for i, repo in enumerate(repos, 1):
        repo_name = repo.get("name")
        print(f"  [{i}/{len(repos)}] Analizando: {repo_name}...")
        
        try:
            hotfix_branches = process_repository(org, args.project, repo, args.pattern, headers)
            if hotfix_branches:
                all_hotfix_branches.extend(hotfix_branches)
                print(f"      ✅ {len(hotfix_branches)} ramas hotfix encontradas")
            else:
                print(f"      ℹ️ Sin ramas hotfix")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Pausa anti-throttling
        time.sleep(0.5)
    
    if not all_hotfix_branches:
        print(f"\nℹ️ No se encontraron ramas con patrón '{args.pattern}'")
        sys.exit(0)
    
    print(f"\n✅ Total ramas hotfix: {len(all_hotfix_branches)}")
    
    output_file = export_to_excel(all_hotfix_branches, org, args.project, args.output)
    print(f"\n💾 Archivo generado: {output_file}")


if __name__ == "__main__":
    main()
