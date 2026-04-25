#!/usr/bin/env python3
"""
Branches Created Reporter v1.0.0
Obtiene ramas creadas desde una fecha específica en Azure DevOps
usando la Pushes API con filtro de fecha directo.

Uso:
    python branches_created.py --org Coppel-Retail --project Compras.RMI
    python branches_created.py --org Coppel-Retail --project Compras.RMI --since 2026-01-01

Autor: Harold Adrian (migrado desde Comercial/scripts/ramasCreadasV2.py)
"""

import os
import sys
import base64
import requests
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
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

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    print("❌ openpyxl no instalado. Ejecuta: pip install openpyxl")
    sys.exit(1)

load_dotenv(Path(__file__).parent.parent / ".env")

# ─── Configuración por defecto ───────────────────────────────────────
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECT = "Compras.RMI"
API_VERSION = "7.1"
DEFAULT_SINCE = "2026-01-01"
MAX_WORKERS = 10


def get_headers(pat: str):
    """Genera headers de autenticación."""
    token_b64 = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {token_b64}",
        "Content-Type": "application/json"
    }


def normalize_org(org: str) -> str:
    """Extrae el nombre de la organización desde una URL completa o nombre simple."""
    if org.startswith("http"):
        return org.rstrip("/").split("/")[-1]
    return org


def get_repositories(org: str, project: str, headers: dict):
    """Obtiene lista de repositorios del proyecto."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories"
    params = {"api-version": API_VERSION}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("value", [])


def get_pushes_for_repo(repo_id: str, since_date: str, org: str, project: str, headers: dict):
    """Obtiene pushes de un repo desde la fecha indicada."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/pushes"
    params = {
        "api-version": API_VERSION,
        "searchCriteria.fromDate": since_date,
        "$top": 100
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])
    except Exception as e:
        print(f"   ⚠️ Error en pushes de repo {repo_id}: {e}")
        return []


def process_repo(repo: dict, since_date: str, org: str, project: str, headers: dict):
    """Procesa un repositorio y retorna ramas nuevas detectadas."""
    repo_id = repo.get("id")
    repo_name = repo.get("name", "unknown")
    
    pushes = get_pushes_for_repo(repo_id, since_date, org, project, headers)
    
    branches = []
    seen_refs = set()
    
    for push in pushes:
        ref_updates = push.get("refUpdates", [])
        for ref in ref_updates:
            ref_name = ref.get("name", "")
            if ref_name.startswith("refs/heads/"):
                branch_name = ref_name.replace("refs/heads/", "")
                if branch_name not in seen_refs:
                    seen_refs.add(branch_name)
                    branches.append({
                        "repo_name": repo_name,
                        "branch_name": branch_name,
                        "created_date": push.get("date", "")[:10] if push.get("date") else "unknown",
                        "created_by": push.get("pushedBy", {}).get("displayName", "unknown"),
                        "push_id": push.get("pushId")
                    })
    
    return repo_name, branches


def export_to_excel(branches: list, org: str, project: str, since_date: str, output_file: str = None):
    """Exporta ramas a Excel con resumen."""
    if not output_file:
        output_file = f"branches_created_{org}_{project}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    wb = Workbook()
    
    # Hoja 1: Ramas
    ws1 = wb.active
    ws1.title = "Ramas Creadas"
    headers = ["Repositorio", "Rama", "Fecha Creación", "Creado por", "Push ID"]
    ws1.append(headers)
    
    for branch in branches:
        ws1.append([
            branch["repo_name"],
            branch["branch_name"],
            branch["created_date"],
            branch["created_by"],
            branch["push_id"]
        ])
    
    # Hoja 2: Resumen por Repo
    ws2 = wb.create_sheet("Resumen por Repo")
    ws2.append(["Repositorio", "Total Ramas Nuevas"])
    
    repo_counts = Counter(b["repo_name"] for b in branches)
    for repo, count in sorted(repo_counts.items(), key=lambda x: x[1], reverse=True):
        ws2.append([repo, count])
    
    # Hoja 3: Resumen por Creador
    ws3 = wb.create_sheet("Resumen por Creador")
    ws3.append(["Creador", "Total Ramas Creadas"])
    
    creator_counts = Counter(b["created_by"] for b in branches)
    for creator, count in sorted(creator_counts.items(), key=lambda x: x[1], reverse=True):
        ws3.append([creator, count])
    
    # Estilos
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", fgColor="4472C4")
    
    for ws in [ws1, ws2, ws3]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Ajustar anchos
    ws1.column_dimensions["A"].width = 30
    ws1.column_dimensions["B"].width = 35
    ws1.column_dimensions["C"].width = 18
    ws1.column_dimensions["D"].width = 25
    ws1.column_dimensions["E"].width = 15
    
    wb.save(output_file)
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Branches Created Reporter - Ramas creadas desde fecha específica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python branches_created.py
  python branches_created.py --org Coppel-Retail --project Compras.RMI
  python branches_created.py --org Coppel-Retail --project Compras.RMI --since 2025-01-01
  python branches_created.py --org Coppel-Retail --project Compras.RMI --workers 5
        """
    )
    parser.add_argument("--org", default=DEFAULT_ORG,
                       help=f"Organización Azure DevOps (default: {DEFAULT_ORG})")
    parser.add_argument("--project", "-p", default=DEFAULT_PROJECT,
                       help=f"Proyecto (default: {DEFAULT_PROJECT})")
    parser.add_argument("--since", "-s", default=DEFAULT_SINCE,
                       help=f"Fecha desde (ISO format, default: {DEFAULT_SINCE})")
    parser.add_argument("--workers", "-w", type=int, default=MAX_WORKERS,
                       help=f"Workers concurrentes (default: {MAX_WORKERS})")
    parser.add_argument("--pat", default=None,
                       help="PAT de Azure DevOps (default: env AZURE_PAT)")
    parser.add_argument("--output", "-o", default=None,
                       help="Nombre del archivo Excel de salida")
    parser.add_argument("--repo-limit", type=int, default=None,
                       help="Limitar número de repos a procesar (para pruebas)")
    
    args = parser.parse_args()
    
    # Obtener PAT
    pat = args.pat or os.getenv("AZURE_PAT", "")
    if not pat:
        print("❌ ERROR: Variable AZURE_PAT no definida")
        print("   Ejecuta: export AZURE_PAT='tu_token'")
        sys.exit(1)
    
    headers = get_headers(pat)
    since_dt = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    
    org = normalize_org(args.org)

    print(f"🔍 Analizando ramas creadas desde: {args.since}")
    print(f"   Org: {org}")
    print(f"   Project: {args.project}")
    print(f"   API: {API_VERSION} | Workers: {args.workers}")
    print("=" * 60)
    
    repos = get_repositories(org, args.project, headers)
    
    if args.repo_limit:
        repos = repos[:args.repo_limit]
        print(f"*** MODO PRUEBA: limitado a {args.repo_limit} repos ***")
    
    all_branches = []
    print(f"\n📦 Consultando {len(repos)} repositorios (concurrente)...\n")
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_repo, r, args.since, org, args.project, headers): r for r in repos}
        done = 0
        
        for f in as_completed(futures):
            done += 1
            repo_name, branches = f.result()
            count = len(branches)
            if count > 0:
                print(f"  [{done}/{len(repos)}] {repo_name}: {count} ramas nuevas")
            else:
                print(f"  [{done}/{len(repos)}] {repo_name}: 0")
            all_branches.extend(branches)
    
    if not all_branches:
        print(f"\nℹ️ No se encontraron ramas creadas desde {args.since}")
        sys.exit(0)
    
    print(f"\n✅ Total ramas nuevas encontradas: {len(all_branches)}")
    
    output_file = export_to_excel(all_branches, org, args.project, args.since, args.output)
    print(f"\n💾 Archivo generado: {output_file}")


if __name__ == "__main__":
    main()
