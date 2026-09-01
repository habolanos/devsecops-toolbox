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


def _is_tty() -> bool:
    """Retorna True si stdout es un terminal interactivo."""
    try:
        return sys.stdout.isatty()
    except Exception:
        return False

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

console = Console() if RICH_AVAILABLE and _is_tty() else (Console(force_terminal=False, no_color=True) if RICH_AVAILABLE else None)

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
        """Obtiene todas las métricas de la región actual."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "profile": self.profile,
            "region": self.region,
            "ec2": self.get_ec2_metrics(),
            "rds": self.get_rds_metrics(),
            "eks": self.get_eks_metrics(),
            "lambda": self.get_lambda_metrics()
        }
    
    def generate_consolidated_report(
        self,
        regions: List[str] = None
    ) -> Dict[str, Any]:
        """Genera reporte consolidado multi-región.
        
        Args:
            regions: Lista de regiones a consultar. Default: ['us-east-1'].
        
        Returns:
            Dict con per-region results y grand totals.
        """
        if not regions:
            regions = [self.region]
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "profile": self.profile,
            "regions": [],
            "skipped_regions": [],
            "totals": {
                "ec2_total": 0,
                "ec2_running": 0,
                "rds_total": 0,
                "eks_total": 0,
                "lambda_total": 0
            }
        }
        
        session = boto3.Session(profile_name=self.profile)
        
        for region in regions:
            try:
                ec2 = session.client("ec2", region_name=region)
                rds = session.client("rds", region_name=region)
                eks = session.client("eks", region_name=region)
                lambda_client = session.client("lambda", region_name=region)
                
                ec2_data = self._count_ec2(ec2)
                rds_data = self._count_rds(rds)
                eks_data = self._count_eks(eks)
                lambda_data = self._count_lambda(lambda_client)
                
                region_report = {
                    "region": region,
                    "ec2_total": ec2_data["total"],
                    "ec2_running": ec2_data["running"],
                    "rds_total": rds_data["total"],
                    "eks_total": eks_data["total"],
                    "lambda_total": lambda_data["total"]
                }
                
                report["regions"].append(region_report)
                report["totals"]["ec2_total"] += ec2_data["total"]
                report["totals"]["ec2_running"] += ec2_data["running"]
                report["totals"]["rds_total"] += rds_data["total"]
                report["totals"]["eks_total"] += eks_data["total"]
                report["totals"]["lambda_total"] += lambda_data["total"]
            except Exception as e:
                if self.debug:
                    if RICH_AVAILABLE and console:
                        console.print(f"[yellow]⚠️  {region}: {e}[/yellow]")
                    else:
                        print(f"⚠️  {region}: {e}")
                report["skipped_regions"].append({"region": region, "reason": str(e)})
        
        return report
    
    def _count_ec2(self, ec2) -> Dict[str, int]:
        total = 0
        running = 0
        try:
            instances = ec2.describe_instances()
            for reservation in instances.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    total += 1
                    if instance["State"]["Name"] == "running":
                        running += 1
        except ClientError:
            pass
        return {"total": total, "running": running}
    
    def _count_rds(self, rds) -> Dict[str, int]:
        try:
            instances = rds.describe_db_instances()
            return {"total": len(instances.get("DBInstances", []))}
        except ClientError:
            return {"total": 0}
    
    def _count_eks(self, eks) -> Dict[str, int]:
        try:
            clusters = eks.list_clusters()
            return {"total": len(clusters.get("clusters", []))}
        except ClientError:
            return {"total": 0}
    
    def _count_lambda(self, lambda_client) -> Dict[str, int]:
        try:
            functions = lambda_client.list_functions()
            return {"total": len(functions.get("Functions", []))}
        except ClientError:
            return {"total": 0}
    
    def print_consolidated_table(self, report: Dict[str, Any]):
        """Imprime reporte consolidado con Rich Table."""
        if RICH_AVAILABLE and console:
            console.print(Panel(
                f"[bold cyan]AWS Consolidated Report[/bold cyan]\n"
                f"Profile: {report['profile']} | Regiones: {len(report['regions'])}",
                border_style="cyan"
            ))
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Región")
            table.add_column("EC2", justify="right")
            table.add_column("Running", justify="right")
            table.add_column("RDS", justify="right")
            table.add_column("EKS", justify="right")
            table.add_column("Lambda", justify="right")
            
            for region in report.get("regions", []):
                table.add_row(
                    region["region"],
                    str(region["ec2_total"]),
                    str(region["ec2_running"]),
                    str(region["rds_total"]),
                    str(region["eks_total"]),
                    str(region["lambda_total"])
                )
            
            totals = report.get("totals", {})
            table.add_row(
                "[bold]TOTAL[/bold]",
                str(totals.get("ec2_total", 0)),
                str(totals.get("ec2_running", 0)),
                str(totals.get("rds_total", 0)),
                str(totals.get("eks_total", 0)),
                str(totals.get("lambda_total", 0)),
                style="bold"
            )
            
            console.print(table)
            
            skipped = report.get("skipped_regions", [])
            if skipped:
                console.print("\n[bold yellow]Regiones omitidas:[/bold yellow]")
                for s in skipped:
                    console.print(f"  • {s['region']}: {s['reason']}")
        else:
            print(json.dumps(report, indent=2, default=str))
    
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
    parser.add_argument("--regions", help="Lista de regiones separadas por coma (modo consolidado)")
    parser.add_argument("--consolidated", action="store_true", help="Reporte consolidado multi-región en Rich Table")
    parser.add_argument("-o", "--output", choices=["json", "csv"], help="Output format")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    
    args = parser.parse_args()
    
    monitor = CloudWatchMetricsMonitor(
        profile=args.profile,
        region=args.region,
        debug=args.debug
    )
    
    if args.consolidated:
        regions = [r.strip() for r in args.regions.split(",")] if args.regions else [args.region]
        report = monitor.generate_consolidated_report(regions)
        if args.output == "json":
            print(json.dumps(report, indent=2, default=str))
        else:
            monitor.print_consolidated_table(report)
    else:
        metrics = monitor.get_all_metrics()
        
        if args.output == "json":
            print(json.dumps(metrics, indent=2, default=str))
        else:
            monitor.print_report(metrics)


if __name__ == "__main__":
    main()

