#!/usr/bin/env python3
"""
Pending Approvals Reporter v1.0.0
Lista releases con aprobaciones pendientes en Azure DevOps,
mostrando también el estado del stage "Validador".

Uso:
    python pending_approvals.py --org Soluciones-Corporativas --project Juridico
    python pending_approvals.py --org Coppel-Retail --project Compras.RMI

Autor: Harold Adrian (migrado desde Comercial/scripts/pending.py)
"""

import requests
import os
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    print("❌ openpyxl no instalado. Ejecuta: pip install openpyxl")
    exit(1)

# ── Configuración por defecto ─────────────────────────────────────────
DEFAULT_ORG = "Soluciones-Corporativas"
DEFAULT_PROJECT = "Juridico"
API_VERSION = "7.1"


def get_headers(pat: str):
    """Genera headers de autenticación."""
    return {"Authorization": f"Basic :{pat}"}


def get_pending_approvals(org: str, project: str, pat: str):
    """Obtiene aprobaciones pendientes del proyecto."""
    base_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release"
    url = f"{base_url}/approvals?statusFilter=pending&api-version={API_VERSION}"
    
    all_approvals = []
    next_url = url
    
    while next_url:
        resp = requests.get(next_url, auth=("", pat), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        all_approvals.extend(data.get("value", []))
        next_url = data.get("nextLink")
    
    return all_approvals


def get_release_detail(release_id: int, org: str, project: str, pat: str):
    """Obtiene detalle completo de un release."""
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases/{release_id}?api-version={API_VERSION}"
    try:
        resp = requests.get(url, auth=("", pat), timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"   ⚠️ Error obteniendo release {release_id}: {e}")
        return None


def get_validador_status(release_id: int, org: str, project: str, pat: str):
    """Busca el stage 'Validador' y retorna su estado."""
    release = get_release_detail(release_id, org, project, pat)
    if not release:
        return "Error"
    
    for env in release.get("environments", []):
        if env.get("name", "").lower() == "validador":
            return env.get("status", "notStarted")
    return "No existe"


def export_to_excel(approvals: list, org: str, project: str, pat: str, filename: str = None):
    """Exporta aprobaciones a Excel."""
    if not filename:
        filename = f"pending_approvals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Pending Approvals"
    
    # Headers
    headers = [
        "Release Name", "Release ID", "Pipeline", "Stage", "Approver",
        "Created On", "Pending Since", "Validador Status", "Approval ID"
    ]
    ws.append(headers)
    
    # Colores para Validador
    VALIDADOR_COLORS = {
        "succeeded": "C6EFCE",      # Verde
        "inProgress": "FFEB9C",     # Amarillo
        "notStarted": "B8CCE4",    # Azul claro
        "rejected": "FFC7CE",       # Rojo
        "No existe": "D9D9D9",      # Gris
        "Error": "FF0000",          # Rojo fuerte
    }
    
    # Datos
    for approval in approvals:
        release_ref = approval.get("release", {})
        release_id = release_ref.get("id")
        release_name = release_ref.get("name", "N/A")
        
        stage = approval.get("releaseEnvironment", {}).get("name", "N/A")
        pipeline = approval.get("releaseDefinition", {}).get("name", "N/A")
        approver = approval.get("approver", {}).get("displayName", "N/A")
        created_on = release_ref.get("createdOn", "")[:10] if release_ref.get("createdOn") else "N/A"
        pending_since = approval.get("createdOn", "")[:10] if approval.get("createdOn") else "N/A"
        approval_id = approval.get("id", "N/A")
        
        # Obtener estado del Validador
        validador_status = get_validador_status(release_id, org, project, pat)
        
        row = [
            release_name, release_id, pipeline, stage, approver,
            created_on, pending_since, validador_status, approval_id
        ]
        ws.append(row)
    
    # Estilos
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", fgColor="0078D4")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    for col_num, cell in enumerate(ws[1], 1):
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
    
    # Colorear columna de Validador (columna H = 8)
    for row in ws.iter_rows(min_row=2, min_col=8, max_col=8):
        for cell in row:
            status = cell.value
            if status in VALIDADOR_COLORS:
                cell.fill = PatternFill("solid", fgColor=VALIDADOR_COLORS[status])
                if status == "rejected":
                    cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    
    # Ajustar anchos
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 35
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 25
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 12
    ws.column_dimensions["H"].width = 15
    ws.column_dimensions["I"].width = 40
    
    wb.save(filename)
    return filename


def main():
    parser = argparse.ArgumentParser(
        description="Pending Approvals Reporter - Releases con aprobaciones pendientes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python pending_approvals.py
  python pending_approvals.py --org Soluciones-Corporativas --project Juridico
  python pending_approvals.py --org Coppel-Retail --project Compras.RMI --output aprobaciones.xlsx
        """
    )
    parser.add_argument("--org", default=DEFAULT_ORG,
                       help=f"Organización Azure DevOps (default: {DEFAULT_ORG})")
    parser.add_argument("--project", "-p", default=DEFAULT_PROJECT,
                       help=f"Proyecto (default: {DEFAULT_PROJECT})")
    parser.add_argument("--pat", default=None,
                       help="PAT de Azure DevOps (default: env AZURE_PAT)")
    parser.add_argument("--output", "-o", default=None,
                       help="Nombre del archivo Excel de salida")
    
    args = parser.parse_args()
    
    # Obtener PAT
    pat = args.pat or os.getenv("AZURE_PAT", "")
    if not pat:
        print("❌ ERROR: Configura tu PAT via --pat o variable de entorno AZURE_PAT")
        exit(1)
    
    print(f"🔍 Consultando aprobaciones pendientes...")
    print(f"   Org: {args.org}")
    print(f"   Project: {args.project}")
    print("=" * 60)
    
    approvals = get_pending_approvals(args.org, args.project, pat)
    
    if not approvals:
        print("\n✅ No hay aprobaciones pendientes.")
        return
    
    print(f"\n📝 {len(approvals)} aprobación(es) pendiente(s) encontrada(s)")
    
    filename = export_to_excel(approvals, args.org, args.project, pat, args.output)
    print(f"\n✅ Archivo generado: {filename}")


if __name__ == "__main__":
    main()
