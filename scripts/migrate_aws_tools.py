#!/usr/bin/env python3
"""
Script para migrar todas las herramientas AWS a usar ExportManager.
"""

import os
import re
from pathlib import Path

# Lista de herramientas AWS a migrar
aws_tools = [
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
]

def migrate_aws_tool(filepath):
    """Migra una herramienta AWS a usar ExportManager."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que tiene los requisitos
        if 'EXPORT_MANAGER_AVAILABLE' not in content:
            return False
        
        if 'def export_results(' not in content:
            return False
        
        # Si ya está completamente migrada, saltar
        if 'manager = ExportManager' in content:
            return False
        
        # Extraer el nombre de la herramienta
        tool_name = Path(filepath).stem
        
        # Buscar __version__
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        version = version_match.group(1) if version_match else "1.0.0"
        
        # Encontrar la función export_results
        pattern = r'def export_results\([^)]*\):[^\n]*\n([ \t]*"""[^"]*""")?'
        match = re.search(pattern, content)
        
        if not match:
            return False
        
        # Crear la nueva función migrada
        new_function = f'''def export_results(results: List[Dict], output_format: str):

    """Exporta resultados usando ExportManager centralizado con fallback."""

    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = OUTCOME_DIR / f"{tool_name}_{{timestamp}}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({{"generated_at": datetime.now().isoformat(), "data": results}}, f, indent=2)
        elif output_format == "csv":
            try:
                import pandas as pd
                filepath = OUTCOME_DIR / f"{tool_name}_{{timestamp}}.csv"
                pd.DataFrame(results).to_csv(filepath, index=False)
            except ImportError:
                print("ERROR: Instala pandas para exportar a CSV")
                return
        else:
            return
        
        print(f"\\n✅ Resultados exportados a: {{filepath}}")
        return
    
    # Usar ExportManager
    manager = ExportManager("{tool_name}", "{version}")
    
    summary = {{"total_items": len(results)}}
    
    if output_format == "json":
        manager.export_json(results, summary=summary)
    elif output_format == "csv":
        manager.export_csv(results)
    elif output_format == "excel":
        manager.export_excel(results, sheet_name="Results", summary=summary)
'''
        
        # Encontrar el inicio y fin de la función
        start = match.start()
        
        # Encontrar el final de la función
        lines = content[start:].split('\n')
        indent_level = len(lines[0]) - len(lines[0].lstrip())
        
        end_line = 1
        for i in range(1, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith(' ' * (indent_level + 1)):
                if line.startswith('def ') or line.startswith('class '):
                    end_line = i
                    break
            if i == len(lines) - 1:
                end_line = i + 1
        
        end = start + len('\n'.join(lines[:end_line]))
        
        # Reemplazar
        new_content = content[:start] + new_function + content[end:]
        
        # Escribir
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"  Error en {filepath}: {e}")
        return False

print("=" * 80)
print("MIGRACIÓN DE HERRAMIENTAS AWS A EXPORTMANAGER")
print("=" * 80)

migrated = 0
skipped = 0
failed = 0

for tool in sorted(aws_tools):
    if os.path.exists(tool):
        if migrate_aws_tool(tool):
            print(f"✅ {os.path.basename(tool)}")
            migrated += 1
        else:
            print(f"⏭️  {os.path.basename(tool)}")
            skipped += 1
    else:
        print(f"❌ {os.path.basename(tool)} - NO ENCONTRADO")
        failed += 1

print("\n" + "=" * 80)
print(f"RESULTADOS:")
print(f"  ✅ Migradas:  {migrated}")
print(f"  ⏭️  Omitidas:  {skipped}")
print(f"  ❌ Fallidas:  {failed}")
print("=" * 80)
