# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS RDS Database Checker - Tool 22

Lista bases de datos por instancia RDS
Equivalente a GCP Tool 8: Cloud SQL Database Checker

Uso:
    python aws_rds_database_checker.py --profile default --region us-east-1 -o json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

__version__ = "1.0.0"
__author__ = "DevSecOps Team"
__description__ = "Lista bases de datos por instancia RDS"


class RDSDatabaseChecker:
    """Verifica bases de datos en RDS."""
    
    def __init__(self, profile: str = "default", region: str = "us-east-1", debug: bool = False):
        """Inicializa el checker."""
        self.profile = profile
        self.region = region
        self.debug = debug
        
        try:
            session = boto3.Session(profile_name=profile)
            self.rds = session.client("rds", region_name=region)
        except Exception as e:
            if RICH_AVAILABLE and console:
                console.print(f"[red]❌ Error al conectar con AWS: {e}[/red]")
            else:
                print(f"❌ Error al conectar con AWS: {e}")
            sys.exit(1)
    
    def get_databases(self) -> Dict[str, Any]:
        """Obtiene bases de datos por instancia."""
        try:
            instances = self.rds.describe_db_instances()
            databases = {
                "timestamp": datetime.utcnow().isoformat(),
                "profile": self.profile,
                "region": self.region,
                "total_instances": len(instances.get("DBInstances", [])),
                "instances": []
            }
            
            for instance in instances.get("DBInstances", []):
                instance_data = {
                    "db_instance_identifier": instance["DBInstanceIdentifier"],
                    "engine": instance["Engine"],
                    "engine_version": instance["EngineVersion"],
                    "status": instance["DBInstanceStatus"],
                    "allocated_storage": instance["AllocatedStorage"],
                    "storage_type": instance["StorageType"],
                    "databases": []
                }
                
                # Intentar obtener lista de bases de datos
                try:
                    if instance["Engine"] in ["mysql", "mariadb", "postgres"]:
                        # Para bases de datos relacionales
                        instance_data["databases"] = self._get_db_list(instance)
                except:
                    pass
                
                databases["instances"].append(instance_data)
            
            return databases
        except ClientError as e:
            return {"error": str(e)}
    
    def _get_db_list(self, instance: Dict) -> List[str]:
        """Obtiene lista de bases de datos de una instancia."""
        # Nota: RDS no proporciona API para listar bases de datos
        # Esto sería necesario hacer a través de conexión directa
        return ["(Requiere conexión directa a la instancia)"]
    
    def print_report(self, databases: Dict[str, Any]):
        """Imprime el reporte."""
        if RICH_AVAILABLE and console:
            console.print(f"[bold cyan]RDS Database Checker[/bold cyan]")
            console.print(f"Profile: {self.profile} | Region: {self.region}\n")
            
            for instance in databases.get("instances", []):
                console.print(f"[bold green]{instance['db_instance_identifier']}[/bold green]")
                console.print(f"  Engine: {instance['engine']} {instance['engine_version']}")
                console.print(f"  Status: {instance['status']}")
                console.print(f"  Storage: {instance['allocated_storage']} GB ({instance['storage_type']})")
        else:
            print(json.dumps(databases, indent=2, default=str))


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--profile", default="default", help="AWS profile")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("-o", "--output", choices=["json", "csv"], help="Output format")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    
    args = parser.parse_args()
    
    checker = RDSDatabaseChecker(
        profile=args.profile,
        region=args.region,
        debug=args.debug
    )
    
    databases = checker.get_databases()
    
    if args.output == "json":
        print(json.dumps(databases, indent=2, default=str))
    else:
        checker.print_report(databases)


if __name__ == "__main__":
    main()

