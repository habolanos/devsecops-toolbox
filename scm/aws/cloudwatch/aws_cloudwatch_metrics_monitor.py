# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS CloudWatch Metrics Monitor - Tool 20

Monitorea métricas de CloudWatch para recursos AWS (EC2, RDS, EKS, Lambda, etc.)
Equivalente a GCP Tool 1: Monitoreo de Recursos GCP

Uso:
    python aws_cloudwatch_metrics_monitor.py --profile default --region us-east-1 -o json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

# Agregar parent directory al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

__version__ = "1.0.0"
__author__ = "DevSecOps Team"
__description__ = "Monitorea métricas de CloudWatch para recursos AWS"


class CloudWatchMetricsMonitor:
    """Monitorea métricas de CloudWatch."""
    
    def __init__(self, profile: str = "default", region: str = "us-east-1", debug: bool = False):
        """Inicializa el monitor."""
        self.profile = profile
        self.region = region
        self.debug = debug
        
        try:
            session = boto3.Session(profile_name=profile)
            self.cloudwatch = session.client("cloudwatch", region_name=region)
            self.ec2 = session.client("ec2", region_name=region)
            self.rds = session.client("rds", region_name=region)
            self.eks = session.client("eks", region_name=region)
            self.lambda_client = session.client("lambda", region_name=region)
        except Exception as e:
            if RICH_AVAILABLE and console:
                console.print(f"[red]❌ Error al conectar con AWS: {e}[/red]")
            else:
                print(f"❌ Error al conectar con AWS: {e}")
            sys.exit(1)
    
    def get_ec2_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de instancias EC2."""
        try:
            instances = self.ec2.describe_instances()
            metrics = {
                "total_instances": 0,
                "running": 0,
                "stopped": 0,
                "instances": []
            }
            
            for reservation in instances.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    metrics["total_instances"] += 1
                    state = instance["State"]["Name"]
                    
                    if state == "running":
                        metrics["running"] += 1
                    elif state == "stopped":
                        metrics["stopped"] += 1
                    
                    metrics["instances"].append({
                        "instance_id": instance["InstanceId"],
                        "state": state,
                        "instance_type": instance["InstanceType"],
                        "launch_time": instance["LaunchTime"].isoformat()
                    })
            
            return metrics
        except ClientError as e:
            return {"error": str(e)}
    
    def get_rds_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de instancias RDS."""
        try:
            instances = self.rds.describe_db_instances()
            metrics = {
                "total_instances": len(instances.get("DBInstances", [])),
                "instances": []
            }
            
            for instance in instances.get("DBInstances", []):
                metrics["instances"].append({
                    "db_instance_identifier": instance["DBInstanceIdentifier"],
                    "db_instance_class": instance["DBInstanceClass"],
                    "engine": instance["Engine"],
                    "engine_version": instance["EngineVersion"],
                    "db_instance_status": instance["DBInstanceStatus"],
                    "allocated_storage": instance["AllocatedStorage"],
                    "storage_type": instance["StorageType"]
                })
            
            return metrics
        except ClientError as e:
            return {"error": str(e)}
    
    def get_eks_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de clusters EKS."""
        try:
            clusters = self.eks.list_clusters()
            metrics = {
                "total_clusters": len(clusters.get("clusters", [])),
                "clusters": []
            }
            
            for cluster_name in clusters.get("clusters", []):
                cluster = self.eks.describe_cluster(name=cluster_name)["cluster"]
                metrics["clusters"].append({
                    "name": cluster["name"],
                    "status": cluster["status"],
                    "version": cluster["version"],
                    "endpoint": cluster["endpoint"],
                    "created_at": cluster["createdAt"].isoformat()
                })
            
            return metrics
        except ClientError as e:
            return {"error": str(e)}
    
    def get_lambda_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de funciones Lambda."""
        try:
            functions = self.lambda_client.list_functions()
            metrics = {
                "total_functions": len(functions.get("Functions", [])),
                "functions": []
            }
            
            for func in functions.get("Functions", []):
                metrics["functions"].append({
                    "function_name": func["FunctionName"],
                    "runtime": func.get("Runtime", "N/A"),
                    "memory_size": func["MemorySize"],
                    "timeout": func["Timeout"],
                    "last_modified": func["LastModified"]
                })
            
            return metrics
        except ClientError as e:
            return {"error": str(e)}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Obtiene todas las métricas."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "profile": self.profile,
            "region": self.region,
            "ec2": self.get_ec2_metrics(),
            "rds": self.get_rds_metrics(),
            "eks": self.get_eks_metrics(),
            "lambda": self.get_lambda_metrics()
        }
    
    def print_report(self, metrics: Dict[str, Any]):
        """Imprime el reporte de métricas."""
        if RICH_AVAILABLE and console:
            console.print(Panel(
                f"[bold cyan]CloudWatch Metrics Monitor[/bold cyan]\n"
                f"Profile: {self.profile} | Region: {self.region}",
                border_style="cyan"
            ))
            
            # EC2
            ec2_data = metrics.get("ec2", {})
            if "error" not in ec2_data:
                console.print(f"\n[bold green]EC2 Instances:[/bold green]")
                console.print(f"  Total: {ec2_data.get('total_instances', 0)}")
                console.print(f"  Running: {ec2_data.get('running', 0)}")
                console.print(f"  Stopped: {ec2_data.get('stopped', 0)}")
            
            # RDS
            rds_data = metrics.get("rds", {})
            if "error" not in rds_data:
                console.print(f"\n[bold green]RDS Instances:[/bold green]")
                console.print(f"  Total: {rds_data.get('total_instances', 0)}")
            
            # EKS
            eks_data = metrics.get("eks", {})
            if "error" not in eks_data:
                console.print(f"\n[bold green]EKS Clusters:[/bold green]")
                console.print(f"  Total: {eks_data.get('total_clusters', 0)}")
            
            # Lambda
            lambda_data = metrics.get("lambda", {})
            if "error" not in lambda_data:
                console.print(f"\n[bold green]Lambda Functions:[/bold green]")
                console.print(f"  Total: {lambda_data.get('total_functions', 0)}")
        else:
            print(json.dumps(metrics, indent=2, default=str))


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
    
    monitor = CloudWatchMetricsMonitor(
        profile=args.profile,
        region=args.region,
        debug=args.debug
    )
    
    metrics = monitor.get_all_metrics()
    
    if args.output == "json":
        print(json.dumps(metrics, indent=2, default=str))
    else:
        monitor.print_report(metrics)


if __name__ == "__main__":
    main()

