# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Deployments Report - Tool 21

Genera reporte detallado de deployments en EKS
Equivalente a GCP Tool 2: Reporte de Despliegues GKE

Uso:
    python aws_eks_deployments_report.py --profile default --region us-east-1 --cluster my-cluster -o json
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
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

__version__ = "1.0.0"
__author__ = "DevSecOps Team"
__description__ = "Genera reporte detallado de deployments en EKS"


class EKSDeploymentsReporter:
    """Genera reportes de deployments en EKS."""
    
    def __init__(self, profile: str = "default", region: str = "us-east-1", cluster: str = None, debug: bool = False):
        """Inicializa el reporter."""
        self.profile = profile
        self.region = region
        self.cluster = cluster
        self.debug = debug
        
        try:
            session = boto3.Session(profile_name=profile)
            self.eks = session.client("eks", region_name=region)
            self.ec2 = session.client("ec2", region_name=region)
        except Exception as e:
            if RICH_AVAILABLE and console:
                console.print(f"[red]❌ Error al conectar con AWS: {e}[/red]")
            else:
                print(f"❌ Error al conectar con AWS: {e}")
            sys.exit(1)
    
    def get_clusters(self) -> List[str]:
        """Obtiene lista de clusters EKS."""
        try:
            response = self.eks.list_clusters()
            return response.get("clusters", [])
        except ClientError as e:
            return []
    
    def get_cluster_details(self, cluster_name: str) -> Dict[str, Any]:
        """Obtiene detalles de un cluster."""
        try:
            response = self.eks.describe_cluster(name=cluster_name)
            cluster = response["cluster"]
            
            return {
                "name": cluster["name"],
                "status": cluster["status"],
                "version": cluster["version"],
                "endpoint": cluster["endpoint"],
                "created_at": cluster["createdAt"].isoformat(),
                "arn": cluster["arn"],
                "platform_version": cluster.get("platformVersion", "N/A")
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def get_node_groups(self, cluster_name: str) -> List[Dict[str, Any]]:
        """Obtiene node groups de un cluster."""
        try:
            response = self.eks.list_nodegroups(clusterName=cluster_name)
            node_groups = []
            
            for ng_name in response.get("nodegroups", []):
                ng = self.eks.describe_nodegroup(
                    clusterName=cluster_name,
                    nodegroupName=ng_name
                )["nodegroup"]
                
                node_groups.append({
                    "name": ng["nodegroupName"],
                    "status": ng["status"],
                    "desired_size": ng["scalingConfig"]["desiredSize"],
                    "min_size": ng["scalingConfig"]["minSize"],
                    "max_size": ng["scalingConfig"]["maxSize"],
                    "instance_types": ng.get("instanceTypes", []),
                    "created_at": ng["createdAt"].isoformat()
                })
            
            return node_groups
        except ClientError as e:
            return []
    
    def generate_report(self) -> Dict[str, Any]:
        """Genera reporte completo."""
        clusters = self.get_clusters()
        
        if self.cluster:
            clusters = [c for c in clusters if c == self.cluster]
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "profile": self.profile,
            "region": self.region,
            "total_clusters": len(clusters),
            "clusters": []
        }
        
        for cluster_name in clusters:
            cluster_details = self.get_cluster_details(cluster_name)
            node_groups = self.get_node_groups(cluster_name)
            
            report["clusters"].append({
                "details": cluster_details,
                "node_groups": node_groups,
                "total_node_groups": len(node_groups)
            })
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Imprime el reporte."""
        if RICH_AVAILABLE and console:
            console.print(Panel(
                f"[bold cyan]EKS Deployments Report[/bold cyan]\n"
                f"Profile: {self.profile} | Region: {self.region}",
                border_style="cyan"
            ))
            
            for cluster in report.get("clusters", []):
                details = cluster.get("details", {})
                if "error" not in details:
                    console.print(f"\n[bold green]Cluster: {details.get('name')}[/bold green]")
                    console.print(f"  Status: {details.get('status')}")
                    console.print(f"  Version: {details.get('version')}")
                    console.print(f"  Node Groups: {cluster.get('total_node_groups')}")
        else:
            print(json.dumps(report, indent=2, default=str))


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--profile", default="default", help="AWS profile")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--cluster", help="Cluster name (optional)")
    parser.add_argument("-o", "--output", choices=["json", "csv"], help="Output format")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    
    args = parser.parse_args()
    
    reporter = EKSDeploymentsReporter(
        profile=args.profile,
        region=args.region,
        cluster=args.cluster,
        debug=args.debug
    )
    
    report = reporter.generate_report()
    
    if args.output == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        reporter.print_report(report)


if __name__ == "__main__":
    main()

