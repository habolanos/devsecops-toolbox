#!/usr/bin/env python3
"""
Script para agregar función export_results() a todas las herramientas que no la tienen.
"""

import os
import re
from pathlib import Path

# Lista de herramientas sin export_results()
tools_without_export = [
    'scm/azdo/azdo_release_explorer_rich.py',
    'scm/azdo/cicd_inventory.py',
    'scm/azdo/cicd_inventory_branches_created.py',
    'scm/azdo/cicd_inventory_gke_pipelines.py',
    'scm/azdo/cicd_inventory_health_score.py',
    'scm/azdo/cicd_inventory_hotfix_branches.py',
    'scm/azdo/cicd_inventory_pending_approvals.py',
    'scm/azdo/interactive_search.py',
    'scm/azdo/pipeline-cd-rollback-pipeline.py',
    'scm/azdo/pipeline-cd-update-branchconfig.py',
    'scm/azdo/pipeline_cd_new_re_release.py',
    'scm/azdo/pipeline_cd_restore_release.py',
    'scm/aws/inventory/aws_inventory_generator.py',
    'scm/gcp/artifact-registry/tag_filter.py',
    'scm/gcp/certificate-manager/gcp_certificate_checker.py',
    'scm/gcp/cloud-armor/gcp_cloud_armor_checker.py',
    'scm/gcp/cloud-run/gcp_cloudrun_checker.py',
    'scm/gcp/cloud-sql/gcp_database_checker.py',
    'scm/gcp/cloud-sql/gcp_disk_checker.py',
    'scm/gcp/cloud-sql/gcp_sql_comparator.py',
    'scm/gcp/cluster-gke/gcp_cluster_checker.py',
    'scm/gcp/connectivity/deployment_validator.py',
    'scm/gcp/gateway-services/gcp_gateway_checker.py',
    'scm/gcp/inventory/generar-inventario-csv-combinar-a-excel.py',
    'scm/gcp/inventory/generar-inventario-csv.py',
    'scm/gcp/inventory/run_inventory.py',
    'scm/gcp/load-balancer/gcp_load_balancer_checker.py',
    'scm/gcp/monitoring/gcp_monitor.py',
    'scm/gcp/monitoring/gke_deployments_report.py',
    'scm/gcp/monitoring/gke_monitor_node.py',
    'scm/gcp/monitoring/gke_monitor_pod.py',
    'scm/gcp/reports-viewer/gcp_reports_viewer.py',
    'scm/gcp/rolesypermisos/gcp_iam_roles_report.py',
    'scm/gcp/secrets-configmaps/gcp_secrets_configmaps_checker.py',
    'scm/gcp/service-account/gcp_service_account_checker.py',
    'scm/gcp/vpc-networks/gcp_ip_addresses_checker.py',
    'scm/gcp/vpc-networks/gcp_vpc_networks_checker.py',
]

def add_export_manager_import(content):
    """Agrega el import de ExportManager si no existe"""
    if 'from export_manager import ExportManager' in content:
        return content
    
    if 'EXPORT_MANAGER_AVAILABLE' in content:
        return content
    
    # Buscar dónde agregar el import (después de otros imports)
    lines = content.split('\n')
    insert_pos = 0
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_pos = i + 1
        elif line.startswith('try:') and 'import' in '\n'.join(lines[i:i+5]):
            # Encontrar el final del bloque try-except
            j = i
            while j < len(lines) and not (lines[j].startswith('def ') or lines[j].startswith('class ')):
                j += 1
            insert_pos = j
            break
    
    # Agregar import de ExportManager
    import_block = """
try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False
"""
    
    lines.insert(insert_pos, import_block)
    return '\n'.join(lines)

def add_export_results_function(content, tool_name):
    """Agrega función export_results() al final del archivo"""
    
    # Crear función genérica
    export_function = f"""

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    \"\"\"Exporta resultados usando ExportManager centralizado con fallback.\"\"\"
    
    from pathlib import Path
    import json
    import csv
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = output_path / f"{tool_name}_{{ts}}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({{"generated_at": datetime.now().isoformat(), "data": data}}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"{tool_name}_{{ts}}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        
        print(f"✅ Resultados exportados a: {{filepath}}")
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("{tool_name}", "1.0.0")
    
    summary = {{"total_items": len(data) if isinstance(data, list) else 1}}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
"""
    
    return content + export_function

def process_tool(filepath):
    """Procesa una herramienta para agregar export_results()"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Si ya tiene export_results, saltar
        if 'def export_results(' in content:
            return False
        
        tool_name = Path(filepath).stem
        
        # Agregar import de ExportManager
        content = add_export_manager_import(content)
        
        # Agregar función export_results()
        content = add_export_results_function(content, tool_name)
        
        # Escribir archivo
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"  Error en {filepath}: {e}")
        return False

print("=" * 80)
print("AGREGAR export_results() A TODAS LAS HERRAMIENTAS SIN ELLA")
print("=" * 80)

added = 0
skipped = 0
failed = 0

for tool in sorted(tools_without_export):
    if os.path.exists(tool):
        if process_tool(tool):
            print(f"✅ {os.path.basename(tool)}")
            added += 1
        else:
            print(f"⏭️  {os.path.basename(tool)}")
            skipped += 1
    else:
        print(f"❌ {os.path.basename(tool)} - NO ENCONTRADO")
        failed += 1

print("\n" + "=" * 80)
print(f"RESULTADOS:")
print(f"  ✅ Agregadas:  {added}")
print(f"  ⏭️  Omitidas:   {skipped}")
print(f"  ❌ Fallidas:   {failed}")
print("=" * 80)
