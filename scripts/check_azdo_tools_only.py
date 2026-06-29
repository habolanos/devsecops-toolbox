#!/usr/bin/env python3
"""Script para verificar el estado de migración de herramientas AZDO principales."""

import os
import re

# Lista de herramientas AZDO principales
azdo_tools = [
    'scm/azdo/azdo_branch_lock_checker.py',
    'scm/azdo/azdo_branch_policy_checker.py',
    'scm/azdo/azdo_pipeline_drift.py',
    'scm/azdo/azdo_pr_master_checker.py',
    'scm/azdo/azdo_pr_pipeline_analyzer.py',
    'scm/azdo/azdo_release_cd_health.py',
    'scm/azdo/azdo_release_deep_dive.py',
    'scm/azdo/azdo_repo_branch_diff.py',
    'scm/azdo/azdo_repo_properties_branch_diff.py',
    'scm/azdo/azdo_scan_pipeline_logs.py',
    'scm/azdo/azdo_scan_repos_vulnerabilities.py',
    'scm/azdo/azdo_task_validator.py',
    'scm/azdo/cicd_inventory_cd_detailed.py',
    'scm/azdo/cicd_inventory_ci_detailed.py',
    'scm/azdo/cicd_inventory_prod_deploy.py',
    'scm/azdo/cicd_pipeline_status.py',
]

def check_migration_status(filepath):
    """Verifica el estado de migración de una herramienta."""
    if not os.path.exists(filepath):
        return "NOT_FOUND"
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        has_import = 'from export_manager import ExportManager' in content
        has_export_results = 'def export_results(' in content
        
        if not has_export_results:
            return "NO_EXPORT_RESULTS"
        
        # Buscar si usa ExportManager en export_results
        export_pattern = r'def export_results\([^)]*\):[^}]*?(?=\ndef |\Z)'
        match = re.search(export_pattern, content, re.DOTALL)
        
        if match:
            export_func = match.group(0)
            uses_export_manager = 'manager = ExportManager' in export_func
            has_fallback = 'if not EXPORT_MANAGER_AVAILABLE:' in export_func
            
            if uses_export_manager and has_fallback:
                return "FULLY_MIGRATED"
            elif has_import and not uses_export_manager:
                return "IMPORT_ONLY"
            else:
                return "PARTIAL"
        
        return "UNKNOWN"
    except Exception as e:
        return f"ERROR"

print("=" * 80)
print("ESTADO DE MIGRACIÓN - HERRAMIENTAS AZDO PRINCIPALES")
print("=" * 80)

status_counts = {
    "FULLY_MIGRATED": [],
    "PARTIAL": [],
    "IMPORT_ONLY": [],
    "NO_EXPORT_RESULTS": [],
    "NOT_FOUND": [],
    "UNKNOWN": [],
}

for tool in sorted(azdo_tools):
    status = check_migration_status(tool)
    tool_name = os.path.basename(tool)
    
    status_counts[status].append(tool_name)
    
    icon = "✅" if status == "FULLY_MIGRATED" else "⏳" if status == "PARTIAL" else "⚠️" if status == "IMPORT_ONLY" else "❌" if status in ["NO_EXPORT_RESULTS", "NOT_FOUND"] else "❓"
    print(f"{icon} {tool_name:50} {status}")

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"✅ Completamente migradas:     {len(status_counts['FULLY_MIGRATED'])}")
print(f"⏳ Parcialmente migradas:      {len(status_counts['PARTIAL'])}")
print(f"⚠️  Solo importes:             {len(status_counts['IMPORT_ONLY'])}")
print(f"❌ Sin export_results:         {len(status_counts['NO_EXPORT_RESULTS'])}")
print(f"❌ No encontradas:             {len(status_counts['NOT_FOUND'])}")
print(f"❓ Desconocido:                {len(status_counts['UNKNOWN'])}")

print("\n" + "=" * 80)
print("HERRAMIENTAS PENDIENTES DE MIGRACIÓN")
print("=" * 80)

pending = status_counts['PARTIAL'] + status_counts['IMPORT_ONLY']
if pending:
    for tool in sorted(pending):
        print(f"  - {tool}")
else:
    print("  ✅ Todas las herramientas AZDO están completamente migradas")

print("\n" + "=" * 80)
