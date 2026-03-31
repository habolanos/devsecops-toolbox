#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EC2 Instances Checker

Analiza instancias EC2: estado, tipo, volúmenes, networking y seguridad.

Uso:
    python aws_ec2_checker.py --profile default --region us-east-1
    python aws_ec2_checker.py --state running -o json
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
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

BASE_DIR = Path(__file__).parent.parent.absolute()
OUTCOME_DIR = BASE_DIR / "outcome"
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS EC2 Instances Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--state", "-s", default="", help="Filter by state (running, stopped, etc.)")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def get_name_tag(tags: List[Dict]) -> str:
    for tag in tags or []:
        if tag.get("Key") == "Name":
            return tag.get("Value", "")
    return ""


def analyze_instances(ec2_client, state_filter: str = "") -> List[Dict]:
    results = []
    
    filters = []
    if state_filter:
        filters.append({"Name": "instance-state-name", "Values": [state_filter]})
    
    paginator = ec2_client.get_paginator('describe_instances')
    
    for page in paginator.paginate(Filters=filters if filters else []):
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_data = {
                    "instance_id": instance['InstanceId'],
                    "name": get_name_tag(instance.get("Tags", [])),
                    "type": instance.get("InstanceType", ""),
                    "state": instance.get("State", {}).get("Name", ""),
                    "platform": instance.get("PlatformDetails", "Linux/UNIX"),
                    "architecture": instance.get("Architecture", ""),
                    "vpc_id": instance.get("VpcId", ""),
                    "subnet_id": instance.get("SubnetId", ""),
                    "private_ip": instance.get("PrivateIpAddress", ""),
                    "public_ip": instance.get("PublicIpAddress", ""),
                    "security_groups": [sg["GroupId"] for sg in instance.get("SecurityGroups", [])],
                    "iam_role": instance.get("IamInstanceProfile", {}).get("Arn", "").split("/")[-1] if instance.get("IamInstanceProfile") else "",
                    "key_name": instance.get("KeyName", ""),
                    "launch_time": instance.get("LaunchTime", "").isoformat() if instance.get("LaunchTime") else None,
                    "ebs_optimized": instance.get("EbsOptimized", False),
                    "monitoring": instance.get("Monitoring", {}).get("State", ""),
                    "root_device_type": instance.get("RootDeviceType", ""),
                    "volumes": [],
                    "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
                    "findings": []
                }
                
                for bdm in instance.get("BlockDeviceMappings", []):
                    ebs = bdm.get("Ebs", {})
                    instance_data["volumes"].append({
                        "device": bdm.get("DeviceName", ""),
                        "volume_id": ebs.get("VolumeId", ""),
                        "status": ebs.get("Status", ""),
                        "delete_on_termination": ebs.get("DeleteOnTermination", False)
                    })
                
                if instance_data["public_ip"]:
                    instance_data["findings"].append("Instancia con IP pública")
                
                if not instance_data["iam_role"]:
                    instance_data["findings"].append("Sin IAM Role asignado")
                
                if instance_data["monitoring"] != "enabled":
                    instance_data["findings"].append("Monitoring detallado no habilitado")
                
                if not instance_data["key_name"] and instance_data["state"] == "running":
                    instance_data["findings"].append("Sin key pair (posible acceso alternativo)")
                
                results.append(instance_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_ec2_instances_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "instances": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_ec2_instances_{timestamp}.csv"
        rows = [{
            "id": i["instance_id"], "name": i["name"], "type": i["type"], "state": i["state"],
            "private_ip": i["private_ip"], "public_ip": i["public_ip"] or "-",
            "findings": len(i["findings"])
        } for i in results]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]EC2 Instances Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("ID", style="cyan", max_width=20)
    table.add_column("Nombre", max_width=25)
    table.add_column("Tipo", justify="center")
    table.add_column("Estado", justify="center")
    table.add_column("Private IP", justify="center")
    table.add_column("Public IP", justify="center")
    table.add_column("Findings", justify="center")
    
    for inst in results:
        state = inst["state"]
        state_color = {"running": "green", "stopped": "red", "pending": "yellow", "stopping": "yellow"}.get(state, "white")
        findings = f"[red]⚠️ {len(inst['findings'])}[/red]" if inst["findings"] else "[green]✅[/green]"
        
        table.add_row(
            inst["instance_id"],
            inst["name"][:25] or "-",
            inst["type"],
            f"[{state_color}]{state}[/{state_color}]",
            inst["private_ip"] or "-",
            inst["public_ip"] or "-",
            findings
        )
    
    console.print(table)


def display_results_plain(results: List[Dict]):
    print("\n=== EC2 Instances ===\n")
    print(f"{'ID':<20} {'Nombre':<20} {'Tipo':<12} {'Estado':<10} {'Private IP':<15}")
    print("-" * 80)
    for inst in results:
        print(f"{inst['instance_id']:<20} {(inst['name'] or '-')[:20]:<20} {inst['type']:<12} {inst['state']:<10} {inst['private_ip'] or '-':<15}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS EC2 Instances Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="💻 EC2 Checker"
        ))
    else:
        print(f"AWS EC2 Instances Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    ec2_client = session.client('ec2')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando instancias EC2...", total=None)
            results = analyze_instances(ec2_client, args.state)
        console.print(f"✅ Instancias encontradas: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando instancias EC2...")
        results = analyze_instances(ec2_client, args.state)
        print(f"Instancias encontradas: {len(results)}")
    
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
    
    running = sum(1 for i in results if i["state"] == "running")
    stopped = sum(1 for i in results if i["state"] == "stopped")
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total instancias:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Running:[/bold] [green]{running}[/green] | [bold]Stopped:[/bold] [red]{stopped}[/red]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(results)} | Running: {running} | Stopped: {stopped}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
