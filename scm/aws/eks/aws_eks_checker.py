#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Cluster Checker

Monitorea clusters EKS, node groups, versiones, addons y configuración de seguridad.

Uso:
    python aws_eks_checker.py --profile default --region us-east-1
    python aws_eks_checker.py --cluster my-cluster -o json
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import time

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 no instalado. Ejecute: pip install boto3")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

BASE_DIR = Path(__file__).parent.parent.absolute()
OUTCOME_DIR = BASE_DIR / "outcome"
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS EKS Cluster Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--cluster", "-c", default="", help="Filter by cluster name")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_clusters(eks_client, cluster_filter: str = "") -> List[Dict]:
    results = []
    
    clusters = eks_client.list_clusters()["clusters"]
    
    for cluster_name in clusters:
        if cluster_filter and cluster_filter.lower() not in cluster_name.lower():
            continue
        
        try:
            cluster = eks_client.describe_cluster(name=cluster_name)["cluster"]
            
            cluster_data = {
                "name": cluster_name,
                "arn": cluster.get("arn", ""),
                "version": cluster.get("version", ""),
                "status": cluster.get("status", ""),
                "endpoint": cluster.get("endpoint", ""),
                "role_arn": cluster.get("roleArn", ""),
                "vpc_id": cluster.get("resourcesVpcConfig", {}).get("vpcId", ""),
                "subnet_ids": cluster.get("resourcesVpcConfig", {}).get("subnetIds", []),
                "security_group_ids": cluster.get("resourcesVpcConfig", {}).get("securityGroupIds", []),
                "cluster_security_group_id": cluster.get("resourcesVpcConfig", {}).get("clusterSecurityGroupId", ""),
                "endpoint_public_access": cluster.get("resourcesVpcConfig", {}).get("endpointPublicAccess", False),
                "endpoint_private_access": cluster.get("resourcesVpcConfig", {}).get("endpointPrivateAccess", False),
                "public_access_cidrs": cluster.get("resourcesVpcConfig", {}).get("publicAccessCidrs", []),
                "encryption_config": cluster.get("encryptionConfig", []),
                "logging": cluster.get("logging", {}),
                "platform_version": cluster.get("platformVersion", ""),
                "created_at": cluster.get("createdAt", "").isoformat() if cluster.get("createdAt") else None,
                "node_groups": [],
                "fargate_profiles": [],
                "addons": [],
                "findings": [],
                "tags": cluster.get("tags", {})
            }
            
            if cluster_data["endpoint_public_access"] and "0.0.0.0/0" in cluster_data["public_access_cidrs"]:
                cluster_data["findings"].append("Endpoint público abierto a 0.0.0.0/0")
            
            if not cluster_data["endpoint_private_access"]:
                cluster_data["findings"].append("Sin acceso privado al endpoint")
            
            if not cluster_data["encryption_config"]:
                cluster_data["findings"].append("Sin encryption de secrets configurada")
            
            logging_types = cluster_data["logging"].get("clusterLogging", [])
            enabled_logs = []
            for log_config in logging_types:
                if log_config.get("enabled"):
                    enabled_logs.extend(log_config.get("types", []))
            if not enabled_logs:
                cluster_data["findings"].append("Logging de cluster no habilitado")
            
            try:
                node_groups = eks_client.list_nodegroups(clusterName=cluster_name)["nodegroups"]
                for ng_name in node_groups:
                    ng = eks_client.describe_nodegroup(clusterName=cluster_name, nodegroupName=ng_name)["nodegroup"]
                    cluster_data["node_groups"].append({
                        "name": ng_name,
                        "status": ng.get("status", ""),
                        "instance_types": ng.get("instanceTypes", []),
                        "ami_type": ng.get("amiType", ""),
                        "capacity_type": ng.get("capacityType", ""),
                        "scaling_config": ng.get("scalingConfig", {}),
                        "disk_size": ng.get("diskSize", 0),
                        "health": ng.get("health", {})
                    })
            except ClientError:
                pass
            
            try:
                addons = eks_client.list_addons(clusterName=cluster_name)["addons"]
                for addon_name in addons:
                    addon = eks_client.describe_addon(clusterName=cluster_name, addonName=addon_name)["addon"]
                    cluster_data["addons"].append({
                        "name": addon_name,
                        "version": addon.get("addonVersion", ""),
                        "status": addon.get("status", "")
                    })
            except ClientError:
                pass
            
            results.append(cluster_data)
        except ClientError as e:
            results.append({"name": cluster_name, "error": str(e)})
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_eks_clusters_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "clusters": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_eks_clusters_{timestamp}.csv"
        rows = [{
            "name": c["name"], "version": c.get("version", ""), "status": c.get("status", ""),
            "node_groups": len(c.get("node_groups", [])), "addons": len(c.get("addons", [])),
            "findings": len(c.get("findings", []))
        } for c in results if "error" not in c]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    for cluster in [c for c in results if "error" not in c]:
        tree = Tree(f"[bold cyan]☸️ Cluster: {cluster['name']}[/bold cyan]")
        tree.add(f"[dim]Versión:[/dim] {cluster['version']} ({cluster['platform_version']})")
        tree.add(f"[dim]Estado:[/dim] {'🟢' if cluster['status'] == 'ACTIVE' else '🟡'} {cluster['status']}")
        tree.add(f"[dim]VPC:[/dim] {cluster['vpc_id']}")
        
        access = []
        if cluster["endpoint_public_access"]:
            access.append("🌍 Público")
        if cluster["endpoint_private_access"]:
            access.append("🔒 Privado")
        tree.add(f"[dim]Acceso:[/dim] {' | '.join(access)}")
        
        if cluster["node_groups"]:
            ng_branch = tree.add(f"[yellow]📦 Node Groups ({len(cluster['node_groups'])})[/yellow]")
            for ng in cluster["node_groups"]:
                scaling = ng.get("scaling_config", {})
                ng_branch.add(f"{ng['name']} | {ng['status']} | {', '.join(ng['instance_types'])} | "
                             f"min:{scaling.get('minSize', 0)} max:{scaling.get('maxSize', 0)}")
        
        if cluster["addons"]:
            addons_branch = tree.add(f"[green]🧩 Addons ({len(cluster['addons'])})[/green]")
            for addon in cluster["addons"]:
                addons_branch.add(f"{addon['name']} v{addon['version']} | {addon['status']}")
        
        if cluster["findings"]:
            findings_branch = tree.add(f"[red]⚠️ Findings ({len(cluster['findings'])})[/red]")
            for finding in cluster["findings"]:
                findings_branch.add(f"[red]{finding}[/red]")
        
        console.print(tree)
        console.print()


def display_results_plain(results: List[Dict]):
    print("\n=== EKS Clusters ===\n")
    for cluster in [c for c in results if "error" not in c]:
        print(f"Cluster: {cluster['name']}")
        print(f"  Versión: {cluster['version']} | Estado: {cluster['status']}")
        print(f"  Node Groups: {len(cluster['node_groups'])} | Addons: {len(cluster['addons'])}")
        print(f"  Findings: {len(cluster['findings'])}")
        print()


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS EKS Cluster Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="☸️ EKS Checker"
        ))
    else:
        print(f"AWS EKS Cluster Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    eks_client = session.client('eks')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando clusters EKS...", total=None)
            results = analyze_clusters(eks_client, args.cluster)
        console.print(f"✅ Clusters encontrados: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando clusters EKS...")
        results = analyze_clusters(eks_client, args.cluster)
        print(f"Clusters encontrados: {len(results)}")
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    if args.output == "table":
        if RICH_AVAILABLE:
            display_results_rich(results)
        else:
            display_results_plain(results)
    else:
        export_results(results, args.output)
    
    valid = [c for c in results if "error" not in c]
    total_ngs = sum(len(c.get("node_groups", [])) for c in valid)
    with_findings = sum(1 for c in valid if c.get("findings"))
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Total clusters:[/bold] [green]{len(valid)}[/green]\n"
            f"[bold]Node Groups:[/bold] [cyan]{total_ngs}[/cyan] | [bold]Con findings:[/bold] [yellow]{with_findings}[/yellow]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nClusters: {len(valid)} | Node Groups: {total_ngs} | Con findings: {with_findings}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
