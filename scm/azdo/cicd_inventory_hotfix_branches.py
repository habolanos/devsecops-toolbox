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
import os
import argparse
import sys
from base64 import b64encode
from datetime import datetime
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


class TeeWriter:
    """Escribe stdout a consola Y archivo de log simultáneamente."""
    def __init__(self, log_path):
        self.terminal = sys.__stdout__
        self.log = open(log_path, "w", encoding="utf-8")
        self.log_path = log_path
        self._paused = False

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


def _progress_context():
    """Retorna contexto Rich Progress que escribe al terminal real."""
    if not RICH_AVAILABLE:
        return None
    console = Console(file=sys.__stdout__)
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


# ======================================================
# CONFIGURACIÓN POR DEFECTO
# ======================================================
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECT = "Cadena_de_Suministros"
DEFAULT_PATTERN = "hotfix"
API_VERSION = "7.1"
DEFAULT_WORKERS = 30


def get_headers(pat: str):
    """Genera headers de autenticación."""
    auth = b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }


def azure_get(url: str, headers: dict, params=None, max_retries=5, timeout=30):
    """GET con retry y backoff exponencial para errores transitorios (5xx/red)."""
    params = params or {}
    params["api-version"] = API_VERSION

    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code >= 500:
                wait = 2 ** attempt
                print(f"⚠️  {r.status_code} en {url[:60]}... retry {attempt+1}/{max_retries} (espera {wait}s)")
                import time; time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            import time; time.sleep(wait)
    return {}


def normalize_org(org: str) -> str:
    """Extrae el nombre de la organización desde una URL completa o nombre simple."""
    if org.startswith("http"):
        return org.rstrip("/").split("/")[-1]
    return org


def safe_az_get(url, headers, params=None):
    """GET que nunca falla — retorna {} en caso de error (loggea el error)."""
    try:
        return azure_get(url, headers, params)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}


def get_repositories(org: str, project: str, headers: dict):
    """Obtiene lista de repositorios."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories"
    data = azure_get(url, headers)
    return data.get("value", [])


def get_hotfix_branches(org: str, project: str, repo_id: str, pattern: str, headers: dict):
    """Obtiene ramas hotfix de un repo filtrando en la API (mucho más rápido)."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/refs"
    params = {
        "filter": f"heads/{pattern}",
        "includeStatuses": "true",
    }
    data = safe_az_get(url, headers, params)
    return data.get("value", [])


def get_pushes_for_branch(org: str, project: str, repo_id: str, branch_name: str, headers: dict):
    """Obtiene el primer push de una rama para determinar creador y fecha."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/pushes"
    params = {
        "searchCriteria.refName": f"refs/heads/{branch_name}",
        "searchCriteria.includeRefUpdates": "true",
        "$top": 1,
    }
    data = safe_az_get(url, headers, params)
    pushes = data.get("value", [])
    if pushes:
        first_push = pushes[-1]
        return {
            "creator": first_push.get("pushedBy", {}).get("displayName", "Unknown"),
            "date": first_push.get("date", "")[:10] if first_push.get("date") else "Unknown",
            "push_id": first_push.get("pushId"),
        }
    return {"creator": "Unknown", "date": "Unknown", "push_id": None}


def _process_repo(org: str, project: str, repo: dict, pattern: str, headers: dict):
    """Worker: procesa un repositorio y retorna (repo_name, hotfix_branches)."""
    repo_id = repo.get("id")
    repo_name = repo.get("name", "unknown")

    branches = get_hotfix_branches(org, project, repo_id, pattern, headers)
    hotfix_branches = []

    for branch in branches:
        branch_name = branch.get("name", "").replace("refs/heads/", "")
        creator_info = get_pushes_for_branch(org, project, repo_id, branch_name, headers)

        hotfix_branches.append({
            "repo_name": repo_name,
            "branch_name": branch_name,
            "creator": creator_info["creator"],
            "created_date": creator_info["date"],
            "is_locked": branch.get("isLocked", False),
            "creator_id": creator_info["push_id"],
        })

    return repo_name, hotfix_branches


def export_to_excel(data: list, org: str, project: str, output_file: str = None):
    """Exporta a Excel."""
    if not output_file or output_file.lower() in ("excel", "csv", "json"):
        output_file = resolve_output_path(output_file, f"hotfix_branches_{org}_{project}")
    
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
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_WORKERS,
                       help=f"Workers concurrentes (default: {DEFAULT_WORKERS})")
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
    
    # Configurar logging a archivo en outcome
    tee = setup_logging("cicd_inventory_hotfix_branches")
    
    org = normalize_org(args.org)

    print(f"🔍 Buscando ramas con patrón '{args.pattern}'...")
    print(f"   Org: {org}")
    print(f"   Project: {args.project}")
    print(f"   API: {API_VERSION}")
    print("=" * 60)
    
    repos = get_repositories(org, args.project, headers)
    total = len(repos)
    print(f"📦 {total} repositorios encontrados")
    
    all_hotfix_branches = []
    progress = _progress_context()
    
    if progress:
        tee.pause_terminal()
        with progress:
            task = progress.add_task("🔥 Hotfix Branches", total=total)
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(_process_repo, org, args.project, r, args.pattern, headers): r for r in repos}
                for f in as_completed(futures):
                    try:
                        repo_name, branches = f.result()
                        all_hotfix_branches.extend(branches)
                    except Exception as e:
                        repo_name = futures[f].get("name", "?")
                        print(f"   ⚠️ Error en repo {repo_name}: {e}")
                    progress.advance(task)
        tee.resume_terminal()
    else:
        sp = _SimpleProgress("🔥 Hotfix Branches", total)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(_process_repo, org, args.project, r, args.pattern, headers): r for r in repos}
            for f in as_completed(futures):
                try:
                    repo_name, branches = f.result()
                    all_hotfix_branches.extend(branches)
                except Exception as e:
                    repo_name = futures[f].get("name", "?")
                    print(f"   ⚠️ Error en repo {repo_name}: {e}")
                sp.advance()
        sp.finish(f"{len(all_hotfix_branches)} hotfix branches en {total} repos")
    
    if not all_hotfix_branches:
        print(f"\nℹ️ No se encontraron ramas con patrón '{args.pattern}'")
        sys.exit(0)
    
    print(f"\n✅ Total ramas hotfix: {len(all_hotfix_branches)}")
    
    output_file = export_to_excel(all_hotfix_branches, org, args.project, args.output)
    excel_path = Path(output_file).resolve()
    print(f"\n💾 Archivo generado: {excel_path}")
    
    teardown_logging(tee)


if __name__ == "__main__":
    main()
