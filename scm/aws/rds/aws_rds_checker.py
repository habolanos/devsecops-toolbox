#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS RDS Instance Checker

Analiza instancias RDS: estado, configuración, backups, encryption y métricas.

Uso:
    python aws_rds_checker.py --profile default --region us-east-1
    python aws_rds_checker.py -o json
"""

import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List
import time

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

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
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS RDS Instance Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--instance", "-i", default="", help="Filter by instance identifier")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: No se pudo crear sesión AWS: {e}")
        sys.exit(1)


def get_rds_instances(rds_client, instance_filter: str = "") -> List[Dict]:
    instances = []
    paginator = rds_client.get_paginator('describe_db_instances')
    
    for page in paginator.paginate():
        for instance in page['DBInstances']:
            if not instance_filter or instance_filter.lower() in instance['DBInstanceIdentifier'].lower():
                instances.append(instance)
    
    return instances


def analyze_instance(instance: Dict, cloudwatch_client) -> Dict:
    identifier = instance['DBInstanceIdentifier']
    
    details = {
        "identifier": identifier,
        "engine": instance.get("Engine", ""),
        "engine_version": instance.get("EngineVersion", ""),
        "instance_class": instance.get("DBInstanceClass", ""),
        "status": instance.get("DBInstanceStatus", ""),
        "multi_az": instance.get("MultiAZ", False),
        "storage_type": instance.get("StorageType", ""),
        "allocated_storage_gb": instance.get("AllocatedStorage", 0),
        "max_allocated_storage_gb": instance.get("MaxAllocatedStorage"),
        "storage_encrypted": instance.get("StorageEncrypted", False),
        "publicly_accessible": instance.get("PubliclyAccessible", False),
        "endpoint": instance.get("Endpoint", {}).get("Address", ""),
        "port": instance.get("Endpoint", {}).get("Port", 0),
        "vpc_id": instance.get("DBSubnetGroup", {}).get("VpcId", ""),
        "subnet_group": instance.get("DBSubnetGroup", {}).get("DBSubnetGroupName", ""),
        "security_groups": [sg["VpcSecurityGroupId"] for sg in instance.get("VpcSecurityGroups", [])],
        "backup_retention_days": instance.get("BackupRetentionPeriod", 0),
        "deletion_protection": instance.get("DeletionProtection", False),
        "auto_minor_upgrade": instance.get("AutoMinorVersionUpgrade", False),
        "performance_insights": instance.get("PerformanceInsightsEnabled", False),
        "iam_auth_enabled": instance.get("IAMDatabaseAuthenticationEnabled", False),
        "create_time": instance.get("InstanceCreateTime", "").isoformat() if instance.get("InstanceCreateTime") else None,
        "tags": {tag["Key"]: tag["Value"] for tag in instance.get("TagList", [])},
        "security_findings": []
    }
    
    if not details["storage_encrypted"]:
        details["security_findings"].append("Storage no encriptado")
    if details["publicly_accessible"]:
        details["security_findings"].append("Instancia públicamente accesible")
    if details["backup_retention_days"] < 7:
        details["security_findings"].append(f"Backup retention bajo ({details['backup_retention_days']} días)")
    if not details["deletion_protection"]:
        details["security_findings"].append("Sin protección contra eliminación")
    if not details["multi_az"]:
        details["security_findings"].append("Sin Multi-AZ (no HA)")
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        cpu_response = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': identifier}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average']
        )
        if cpu_response['Datapoints']:
            details["cpu_utilization_avg"] = round(cpu_response['Datapoints'][0]['Average'], 2)
        
        storage_response = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='FreeStorageSpace',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': identifier}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average']
        )
        if storage_response['Datapoints']:
            free_bytes = storage_response['Datapoints'][0]['Average']
            details["free_storage_gb"] = round(free_bytes / (1024**3), 2)
            if details["allocated_storage_gb"] > 0:
                used_pct = ((details["allocated_storage_gb"] - details["free_storage_gb"]) / details["allocated_storage_gb"]) * 100
                details["storage_used_pct"] = round(used_pct, 1)
    except ClientError:
        pass
    
    return details


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_rds_instances_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "total_instances": len(results), "instances": results}, f, indent=2, default=str)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_rds_instances_{timestamp}.csv"
        rows = [{
            "identifier": r["identifier"], "engine": r["engine"], "version": r["engine_version"],
            "class": r["instance_class"], "status": r["status"], "multi_az": r["multi_az"],
            "storage_gb": r["allocated_storage_gb"], "encrypted": r["storage_encrypted"],
            "public": r["publicly_accessible"], "findings": len(r["security_findings"])
        } for r in results]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]RDS Instances Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Instancia", style="cyan", max_width=30)
    table.add_column("Engine", justify="center")
    table.add_column("Clase", justify="center")
    table.add_column("Estado", justify="center")
    table.add_column("Multi-AZ", justify="center")
    table.add_column("Storage", justify="center")
    table.add_column("Encrypted", justify="center")
    table.add_column("Findings", justify="center")
    
    for r in results:
        status_color = "green" if r["status"] == "available" else "yellow"
        multi_az = "✅" if r["multi_az"] else "❌"
        encrypted = "✅" if r["storage_encrypted"] else "❌"
        findings = f"[red]⚠️ {len(r['security_findings'])}[/red]" if r["security_findings"] else "✅"
        storage = f"{r['allocated_storage_gb']} GB"
        if r.get("storage_used_pct"):
            storage += f" ({r['storage_used_pct']}%)"
        
        table.add_row(
            r["identifier"][:30], f"{r['engine']} {r['engine_version'][:5]}", r["instance_class"],
            f"[{status_color}]{r['status']}[/{status_color}]", multi_az, storage, encrypted, findings
        )
    
    console.print(table)
    
    instances_with_findings = [r for r in results if r["security_findings"]]
    if instances_with_findings:
        console.print("\n[bold red]⚠️ Instancias con hallazgos de seguridad:[/bold red]")
        for r in instances_with_findings:
            console.print(f"  [yellow]{r['identifier']}[/yellow]:")
            for finding in r["security_findings"]:
                console.print(f"    - {finding}")


def display_results_plain(results: List[Dict]):
    print("\n=== RDS Instances Analysis ===\n")
    print(f"{'Instancia':<30} {'Engine':<15} {'Estado':<12} {'Multi-AZ':<10} {'Findings'}")
    print("-" * 85)
    for r in results:
        print(f"{r['identifier'][:30]:<30} {r['engine']:<15} {r['status']:<12} {'Yes' if r['multi_az'] else 'No':<10} {len(r['security_findings'])}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS RDS Instance Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="💾 RDS Checker"
        ))
    else:
        print(f"AWS RDS Instance Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    rds_client = session.client('rds')
    cloudwatch_client = session.client('cloudwatch')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Obteniendo instancias RDS...", total=None)
            instances = get_rds_instances(rds_client, args.instance)
        console.print(f"✅ Instancias encontradas: [bold green]{len(instances)}[/bold green]")
    else:
        print("Obteniendo instancias RDS...")
        instances = get_rds_instances(rds_client, args.instance)
        print(f"Instancias encontradas: {len(instances)}")
    
    results = []
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), TimeElapsedColumn(), console=console) as progress:
            task = progress.add_task("[cyan]Analizando instancias...", total=len(instances))
            for instance in instances:
                progress.update(task, description=f"[cyan]Analizando: {instance['DBInstanceIdentifier'][:25]}...")
                results.append(analyze_instance(instance, cloudwatch_client))
                progress.advance(task)
    else:
        for i, instance in enumerate(instances, 1):
            print(f"[{i}/{len(instances)}] Analizando: {instance['DBInstanceIdentifier']}")
            results.append(analyze_instance(instance, cloudwatch_client))
    
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
    
    available = sum(1 for r in results if r["status"] == "available")
    with_findings = sum(1 for r in results if r["security_findings"])
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total instancias:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Disponibles:[/bold] [green]{available}[/green] | [bold]Multi-AZ:[/bold] [cyan]{sum(1 for r in results if r['multi_az'])}[/cyan]\n"
            f"[bold]Con hallazgos:[/bold] [yellow]{with_findings}[/yellow]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(results)} | Disponibles: {available} | Con hallazgos: {with_findings}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
