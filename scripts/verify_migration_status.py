#!/usr/bin/env python3
"""Script para verificar el estado actual de la migración y qué falta."""

import os
import re
from pathlib import Path
from collections import defaultdict

def check_tool_status(filepath):
    """Verifica el estado de migración de una herramienta."""
    if not os.path.exists(filepath):
        return {
            'exists': False,
            'has_export_results': False,
            'has_import': False,
            'uses_export_manager': False,
            'has_fallback': False,
            'status': 'NOT_FOUND'
        }
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        has_export_results = 'def export_results(' in content
        has_import = 'from export_manager import ExportManager' in content or 'EXPORT_MANAGER_AVAILABLE' in content
        
        if not has_export_results:
            return {
                'exists': True,
                'has_export_results': False,
                'has_import': False,
                'uses_export_manager': False,
                'has_fallback': False,
                'status': 'NO_EXPORT_RESULTS'
            }
        
        uses_export_manager = 'manager = ExportManager' in content
        has_fallback = 'if not EXPORT_MANAGER_AVAILABLE:' in content
        
        if uses_export_manager and has_fallback:
            status = 'FULLY_MIGRATED'
        elif has_import and uses_export_manager:
            status = 'PARTIAL_MIGRATED'
        elif has_import:
            status = 'IMPORT_ONLY'
        else:
            status = 'NOT_MIGRATED'
        
        return {
            'exists': True,
            'has_export_results': has_export_results,
            'has_import': has_import,
            'uses_export_manager': uses_export_manager,
            'has_fallback': has_fallback,
            'status': status
        }
    except Exception as e:
        return {
            'exists': True,
            'has_export_results': False,
            'has_import': False,
            'uses_export_manager': False,
            'has_fallback': False,
            'status': 'ERROR'
        }

# Lista de todas las herramientas principales
all_tools = {
    'AZDO': [
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
    ],
    'AWS': [
        'scm/aws/acm/aws_acm_checker.py',
        'scm/aws/cloudwatch/aws_cloudwatch_checker.py',
        'scm/aws/ec2/aws_ebs_checker.py',
        'scm/aws/ec2/aws_ec2_checker.py',
        'scm/aws/ecr/aws_ecr_checker.py',
        'scm/aws/eks/aws_eks_checker.py',
        'scm/aws/eks/aws_eks_node_checker.py',
        'scm/aws/eks/aws_eks_pod_checker.py',
        'scm/aws/elb/aws_load_balancer_checker.py',
        'scm/aws/iam/aws_iam_checker.py',
        'scm/aws/iam/aws_roles_checker.py',
        'scm/aws/lambda/aws_lambda_checker.py',
        'scm/aws/rds/aws_rds_checker.py',
        'scm/aws/rds/aws_rds_storage_checker.py',
        'scm/aws/secretsmanager/aws_secrets_checker.py',
        'scm/aws/vpc/aws_security_groups_checker.py',
        'scm/aws/vpc/aws_vpc_checker.py',
        'scm/aws/waf/aws_waf_checker.py',
    ],
    'GCP': [
        'scm/gcp/connectivity/deploy_dependency_checker.py',
        'scm/gcp/connectivity/pod_connectivity_checker.py',
    ],
}

print("=" * 100)
print("VERIFICACIÓN DE ESTADO DE MIGRACIÓN - FASE 2: ESTANDARIZACIÓN JSON")
print("=" * 100)

status_by_platform = defaultdict(lambda: defaultdict(list))
total_stats = defaultdict(int)

for platform, tools in all_tools.items():
    print(f"\n{'='*100}")
    print(f"PLATAFORMA: {platform}")
    print(f"{'='*100}")
    
    for tool in sorted(tools):
        status_info = check_tool_status(tool)
        tool_name = os.path.basename(tool)
        status = status_info['status']
        
        status_by_platform[platform][status].append(tool_name)
        total_stats[status] += 1
        
        # Iconos según estado
        if status == 'FULLY_MIGRATED':
            icon = "✅"
        elif status == 'PARTIAL_MIGRATED':
            icon = "⏳"
        elif status == 'IMPORT_ONLY':
            icon = "⚠️"
        elif status == 'NOT_MIGRATED':
            icon = "❌"
        elif status == 'NO_EXPORT_RESULTS':
            icon = "⊘"
        else:
            icon = "❓"
        
        print(f"{icon} {tool_name:50} {status:20} | Import: {status_info['has_import']!s:5} | Manager: {status_info['uses_export_manager']!s:5} | Fallback: {status_info['has_fallback']!s:5}")

print(f"\n{'='*100}")
print("RESUMEN POR PLATAFORMA")
print(f"{'='*100}")

for platform in ['AZDO', 'AWS', 'GCP']:
    print(f"\n{platform}:")
    total_tools = len(all_tools[platform])
    fully = len(status_by_platform[platform]['FULLY_MIGRATED'])
    partial = len(status_by_platform[platform]['PARTIAL_MIGRATED'])
    import_only = len(status_by_platform[platform]['IMPORT_ONLY'])
    not_migrated = len(status_by_platform[platform]['NOT_MIGRATED'])
    no_export = len(status_by_platform[platform]['NO_EXPORT_RESULTS'])
    
    print(f"  ✅ Completamente migradas:  {fully:2}/{total_tools} ({100*fully/total_tools:5.1f}%)")
    print(f"  ⏳ Parcialmente migradas:   {partial:2}/{total_tools} ({100*partial/total_tools:5.1f}%)")
    print(f"  ⚠️  Solo importes:          {import_only:2}/{total_tools} ({100*import_only/total_tools:5.1f}%)")
    print(f"  ❌ No migradas:             {not_migrated:2}/{total_tools} ({100*not_migrated/total_tools:5.1f}%)")
    print(f"  ⊘  Sin export_results:      {no_export:2}/{total_tools} ({100*no_export/total_tools:5.1f}%)")

print(f"\n{'='*100}")
print("RESUMEN GLOBAL")
print(f"{'='*100}")

total_tools = sum(len(tools) for tools in all_tools.values())
fully = total_stats['FULLY_MIGRATED']
partial = total_stats['PARTIAL_MIGRATED']
import_only = total_stats['IMPORT_ONLY']
not_migrated = total_stats['NOT_MIGRATED']
no_export = total_stats['NO_EXPORT_RESULTS']

print(f"\n✅ Completamente migradas:  {fully:2}/{total_tools} ({100*fully/total_tools:5.1f}%)")
print(f"⏳ Parcialmente migradas:   {partial:2}/{total_tools} ({100*partial/total_tools:5.1f}%)")
print(f"⚠️  Solo importes:          {import_only:2}/{total_tools} ({100*import_only/total_tools:5.1f}%)")
print(f"❌ No migradas:             {not_migrated:2}/{total_tools} ({100*not_migrated/total_tools:5.1f}%)")
print(f"⊘  Sin export_results:      {no_export:2}/{total_tools} ({100*no_export/total_tools:5.1f}%)")

print(f"\n{'='*100}")
print("QUÉ FALTA POR HACER")
print(f"{'='*100}")

pending_full = []
pending_partial = []
pending_import = []
pending_not = []

for platform, tools in all_tools.items():
    for tool in tools:
        status_info = check_tool_status(tool)
        tool_name = os.path.basename(tool)
        
        if status_info['status'] == 'NOT_MIGRATED':
            pending_not.append(tool_name)
        elif status_info['status'] == 'IMPORT_ONLY':
            pending_import.append(tool_name)
        elif status_info['status'] == 'PARTIAL_MIGRATED':
            pending_partial.append(tool_name)

if pending_not:
    print(f"\n❌ HERRAMIENTAS SIN MIGRAR ({len(pending_not)}):")
    for tool in sorted(pending_not):
        print(f"   - {tool}")

if pending_import:
    print(f"\n⚠️  HERRAMIENTAS CON SOLO IMPORTES ({len(pending_import)}):")
    for tool in sorted(pending_import):
        print(f"   - {tool}")

if pending_partial:
    print(f"\n⏳ HERRAMIENTAS PARCIALMENTE MIGRADAS ({len(pending_partial)}):")
    for tool in sorted(pending_partial):
        print(f"   - {tool}")

if not pending_not and not pending_import and not pending_partial:
    print("\n✅ ¡TODAS LAS HERRAMIENTAS ESTÁN COMPLETAMENTE MIGRADAS!")

print(f"\n{'='*100}")
print("PRÓXIMOS PASOS")
print(f"{'='*100}")

if pending_not:
    print(f"\n1. Migrar {len(pending_not)} herramientas sin migrar")
    print(f"   Comando: python scripts/migrate_all_tools.py")

if pending_import:
    print(f"\n2. Completar migración de {len(pending_import)} herramientas con solo importes")
    print(f"   Comando: python scripts/complete_export_migration.py")

if pending_partial:
    print(f"\n3. Completar migración de {len(pending_partial)} herramientas parcialmente migradas")
    print(f"   Comando: python scripts/complete_export_migration.py")

if not pending_not and not pending_import and not pending_partial:
    print("\n✅ FASE 2 COMPLETADA - Listo para Fase 3: Arquitectura Unificada")

print(f"\n{'='*100}\n")
