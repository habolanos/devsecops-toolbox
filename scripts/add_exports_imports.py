#!/usr/bin/env python3
"""Script para agregar imports de ExportManager a todas las herramientas."""

import os
import re
from pathlib import Path

def add_export_manager_import(filepath):
    """Agrega import de ExportManager a un archivo."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Si ya tiene el import, saltar
    if 'from export_manager import ExportManager' in content:
        return False
    
    # Buscar dónde agregar el import
    lines = content.split('\n')
    insert_pos = 0
    
    # Buscar después del último try-except block de imports
    for i, line in enumerate(lines):
        if 'RICH_AVAILABLE' in line or 'REQUESTS_AVAILABLE' in line:
            insert_pos = i + 1
            break
    
    # Crear bloque de import
    import_block = """try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

"""
    
    lines.insert(insert_pos, import_block)
    new_content = '\n'.join(lines)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

# Herramientas AWS
aws_tools = [
    'scm/aws/secretsmanager/aws_secrets_checker.py',
    'scm/aws/waf/aws_waf_checker.py',
    'scm/aws/vpc/aws_security_groups_checker.py',
    'scm/aws/lambda/aws_lambda_checker.py',
    'scm/aws/rds/aws_rds_storage_checker.py',
    'scm/aws/rds/aws_rds_checker.py',
    'scm/aws/acm/aws_acm_checker.py',
    'scm/aws/vpc/aws_vpc_checker.py',
    'scm/aws/iam/aws_iam_checker.py',
    'scm/aws/elb/aws_load_balancer_checker.py',
    'scm/aws/eks/aws_eks_pod_checker.py',
    'scm/aws/ecr/aws_ecr_checker.py',
    'scm/aws/eks/aws_eks_checker.py',
    'scm/aws/iam/aws_roles_checker.py',
    'scm/aws/eks/aws_eks_node_checker.py',
    'scm/aws/cloudwatch/aws_cloudwatch_checker.py',
    'scm/aws/ec2/aws_ebs_checker.py',
    'scm/aws/ec2/aws_ec2_checker.py',
]

count = 0
for tool in aws_tools:
    if os.path.exists(tool):
        if add_export_manager_import(tool):
            print(f'✅ {os.path.basename(tool)}')
            count += 1
        else:
            print(f'⏭️  {os.path.basename(tool)} (ya tiene import)')

print(f'\n✅ Importes agregados a {count} herramientas AWS')
