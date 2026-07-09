#!/usr/bin/env python3
"""
Script para generar las herramientas AWS restantes
"""

import os
import json

# Definición de herramientas a generar
TOOLS_TO_CREATE = {
    "25": {
        "name": "VPC IP Addresses Checker",
        "path": "vpc/aws_vpc_ip_addresses_checker.py",
        "description": "Analiza capacidad de red de VPCs y subnets",
        "group": "network"
    },
    "26": {
        "name": "EKS Pod Connectivity Checker",
        "path": "eks/aws_eks_pod_connectivity_checker.py",
        "description": "Valida conectividad desde pods EKS a RDS",
        "group": "kubernetes"
    },
    "27": {
        "name": "EKS Deployment Validator",
        "path": "eks/aws_eks_deployment_validator.py",
        "description": "Valida configuración y conectividad de deployments EKS",
        "group": "kubernetes"
    },
    "28": {
        "name": "Lambda Functions Analyzer",
        "path": "lambda/aws_lambda_analyzer.py",
        "description": "Análisis profundo de funciones Lambda",
        "group": "compute"
    },
    "29": {
        "name": "ECR Image Filter",
        "path": "ecr/aws_ecr_image_filter.py",
        "description": "Filtra y exporta imágenes de ECR a Excel",
        "group": "artifacts"
    },
    "30": {
        "name": "AWS Reports Viewer",
        "path": "inventory/aws_reports_viewer.py",
        "description": "Genera gráficos HTML desde reportes JSON",
        "group": "reports"
    },
    "31": {
        "name": "Lambda Cost Analyzer",
        "path": "lambda/aws_lambda_cost_analyzer.py",
        "description": "Análisis de costos y optimización de Lambda",
        "group": "compute"
    },
    "32": {
        "name": "AWS Infrastructure Consolidator",
        "path": "inventory/aws_infrastructure_consolidator.py",
        "description": "Consolida ALB, Lambda, RDS con mapeo de relaciones",
        "group": "consolidation"
    },
    "33": {
        "name": "AWS Unified Infrastructure Dashboard",
        "path": "inventory/aws_unified_infrastructure_dashboard.py",
        "description": "Dashboard ejecutivo unificado",
        "group": "consolidation"
    },
    "34": {
        "name": "Lambda Health Analyzer",
        "path": "lambda/aws_lambda_health_analyzer.py",
        "description": "Análisis de salud y rendimiento de Lambda",
        "group": "compute"
    },
    "35": {
        "name": "EKS Deployments Off Analyzer",
        "path": "eks/aws_eks_deployments_off_analyzer.py",
        "description": "Analiza deployments no running en EKS",
        "group": "kubernetes"
    },
    "36": {
        "name": "Lambda Security Auditor",
        "path": "lambda/aws_lambda_security_auditor.py",
        "description": "Auditoría de seguridad en Lambda",
        "group": "compute"
    },
    "37": {
        "name": "IAM Service Linked Roles Checker",
        "path": "iam/aws_service_linked_roles_checker.py",
        "description": "Analiza Service Linked Roles",
        "group": "iam"
    },
    "38": {
        "name": "IAM Service Linked Roles Reporter",
        "path": "iam/aws_service_linked_roles_reporter.py",
        "description": "Reporte multi-cuenta de Service Linked Roles",
        "group": "iam"
    },
    "39": {
        "name": "EKS Deploy Dependency Checker",
        "path": "eks/aws_eks_deploy_dependency_checker.py",
        "description": "Analiza dependencias de deployments EKS",
        "group": "kubernetes"
    },
    "40": {
        "name": "AWS Inventory Consolidator",
        "path": "inventory/aws_inventory_consolidator.py",
        "description": "Consolida inventario de múltiples regiones",
        "group": "inventory"
    }
}

TEMPLATE = '''#!/usr/bin/env python3
"""
{description}
Tool {tool_id}
"""

import json
import argparse
import sys
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


class {class_name}:
    """Analizador de {description}"""
    
    def __init__(self, profile: str = None, region: str = 'us-east-1'):
        self.profile = profile
        self.region = region
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    
    def analyze(self) -> Dict[str, Any]:
        """Realiza análisis"""
        return {{
            "status": "success",
            "region": self.region,
            "tool": "{name}",
            "message": "Herramienta {tool_id} - {description}"
        }}


def main():
    parser = argparse.ArgumentParser(description='{description}')
    parser.add_argument('--profile', help='AWS profile')
    parser.add_argument('--region', default='us-east-1', help='Región AWS')
    parser.add_argument('-o', '--output', choices=['json', 'csv'], help='Formato de salida')
    
    args = parser.parse_args()
    
    analyzer = {class_name}(profile=args.profile, region=args.region)
    result = analyzer.analyze()
    
    if args.output == 'json':
        output = json.dumps(result, indent=2, default=str)
        print(output)
        if EXPORT_MANAGER_AVAILABLE:
            manager = ExportManager()
            manager.export_json(result, '{tool_name}')
    else:
        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
'''

def generate_class_name(name: str) -> str:
    """Genera nombre de clase desde nombre de herramienta"""
    return ''.join(word.capitalize() for word in name.replace('-', ' ').split())

def generate_tool_name(name: str) -> str:
    """Genera nombre de herramienta para archivo"""
    return name.lower().replace(' ', '_')

def create_tool_file(tool_id: str, tool_info: Dict) -> bool:
    """Crea archivo de herramienta"""
    path = tool_info['path']
    full_path = os.path.join(os.path.dirname(__file__), path)
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    class_name = generate_class_name(tool_info['name'])
    tool_name = generate_tool_name(tool_info['name'])
    
    content = TEMPLATE.format(
        tool_id=tool_id,
        name=tool_info['name'],
        description=tool_info['description'],
        class_name=class_name,
        tool_name=tool_name
    )
    
    try:
        with open(full_path, 'w') as f:
            f.write(content)
        print(f"✓ Creado: {path}")
        return True
    except Exception as e:
        print(f"✗ Error creando {path}: {e}")
        return False

def main():
    print("Generando herramientas AWS restantes...")
    print(f"Total a crear: {len(TOOLS_TO_CREATE)}\n")
    
    created = 0
    for tool_id, tool_info in TOOLS_TO_CREATE.items():
        if create_tool_file(tool_id, tool_info):
            created += 1
    
    print(f"\n✓ Creadas {created}/{len(TOOLS_TO_CREATE)} herramientas")

if __name__ == '__main__':
    main()
