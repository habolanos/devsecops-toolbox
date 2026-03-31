#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Security Groups Checker

Analiza Security Groups, reglas de entrada/salida y detecta configuraciones riesgosas.

Uso:
    python aws_security_groups_checker.py --profile default --region us-east-1
    python aws_security_groups_checker.py -o json
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
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

BASE_DIR = Path(__file__).parent.parent.absolute()
OUTCOME_DIR = BASE_DIR / "outcome"
console = Console() if RICH_AVAILABLE else None

RISKY_PORTS = {22: "SSH", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL", 1433: "MSSQL", 27017: "MongoDB", 6379: "Redis"}


def get_args():
    parser = argparse.ArgumentParser(description="AWS Security Groups Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--vpc-id", "-v", default="", help="Filter by VPC ID")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_rule(rule: Dict, direction: str) -> Dict:
    result = {
        "direction": direction,
        "protocol": rule.get("IpProtocol", "all"),
        "from_port": rule.get("FromPort", 0),
        "to_port": rule.get("ToPort", 65535),
        "sources": [],
        "risks": []
    }
    
    if result["protocol"] == "-1":
        result["protocol"] = "all"
        result["from_port"] = 0
        result["to_port"] = 65535
    
    for ip_range in rule.get("IpRanges", []):
        cidr = ip_range.get("CidrIp", "")
        result["sources"].append(cidr)
        
        if cidr == "0.0.0.0/0":
            if direction == "inbound":
                port = result["to_port"]
                if port in RISKY_PORTS:
                    result["risks"].append(f"{RISKY_PORTS[port]} abierto a internet (0.0.0.0/0)")
                elif result["protocol"] == "all":
                    result["risks"].append("Todos los puertos abiertos a internet")
                elif result["from_port"] == 0 and result["to_port"] == 65535:
                    result["risks"].append("Rango completo de puertos abierto a internet")
    
    for ip_range in rule.get("Ipv6Ranges", []):
        cidr = ip_range.get("CidrIpv6", "")
        result["sources"].append(cidr)
        if cidr == "::/0" and direction == "inbound":
            result["risks"].append("Abierto a todo IPv6")
    
    for sg in rule.get("UserIdGroupPairs", []):
        result["sources"].append(f"sg:{sg.get('GroupId', '')}")
    
    return result


def analyze_security_groups(ec2_client, vpc_filter: str = "") -> List[Dict]:
    results = []
    
    filters = []
    if vpc_filter:
        filters.append({"Name": "vpc-id", "Values": [vpc_filter]})
    
    paginator = ec2_client.get_paginator('describe_security_groups')
    
    for page in paginator.paginate(Filters=filters if filters else []):
        for sg in page['SecurityGroups']:
            sg_data = {
                "group_id": sg["GroupId"],
                "group_name": sg.get("GroupName", ""),
                "description": sg.get("Description", ""),
                "vpc_id": sg.get("VpcId", ""),
                "inbound_rules": [],
                "outbound_rules": [],
                "total_risks": 0,
                "risk_details": [],
                "tags": {tag["Key"]: tag["Value"] for tag in sg.get("Tags", [])}
            }
            
            for rule in sg.get("IpPermissions", []):
                analyzed = analyze_rule(rule, "inbound")
                sg_data["inbound_rules"].append(analyzed)
                sg_data["risk_details"].extend(analyzed["risks"])
            
            for rule in sg.get("IpPermissionsEgress", []):
                analyzed = analyze_rule(rule, "outbound")
                sg_data["outbound_rules"].append(analyzed)
            
            sg_data["total_risks"] = len(sg_data["risk_details"])
            results.append(sg_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_security_groups_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "security_groups": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_security_groups_{timestamp}.csv"
        rows = [{
            "group_id": sg["group_id"], "name": sg["group_name"], "vpc_id": sg["vpc_id"],
            "inbound_rules": len(sg["inbound_rules"]), "outbound_rules": len(sg["outbound_rules"]),
            "risks": sg["total_risks"]
        } for sg in results]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]Security Groups Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("ID", style="cyan", max_width=25)
    table.add_column("Nombre", max_width=30)
    table.add_column("VPC", max_width=25)
    table.add_column("Inbound", justify="center")
    table.add_column("Outbound", justify="center")
    table.add_column("Riesgos", justify="center")
    
    sorted_results = sorted(results, key=lambda x: x["total_risks"], reverse=True)
    
    for sg in sorted_results:
        risk_display = f"[red]⚠️ {sg['total_risks']}[/red]" if sg["total_risks"] > 0 else "[green]✅[/green]"
        
        table.add_row(
            sg["group_id"],
            sg["group_name"][:30],
            sg["vpc_id"],
            str(len(sg["inbound_rules"])),
            str(len(sg["outbound_rules"])),
            risk_display
        )
    
    console.print(table)
    
    risky_sgs = [sg for sg in results if sg["total_risks"] > 0]
    if risky_sgs:
        console.print("\n[bold red]⚠️ Security Groups con riesgos:[/bold red]")
        for sg in risky_sgs:
            console.print(f"  [yellow]{sg['group_id']}[/yellow] ({sg['group_name']}):")
            for risk in sg["risk_details"]:
                console.print(f"    - {risk}")


def display_results_plain(results: List[Dict]):
    print("\n=== Security Groups Analysis ===\n")
    print(f"{'ID':<25} {'Nombre':<25} {'Inbound':<10} {'Outbound':<10} {'Riesgos'}")
    print("-" * 80)
    for sg in sorted(results, key=lambda x: x["total_risks"], reverse=True):
        print(f"{sg['group_id']:<25} {sg['group_name'][:25]:<25} "
              f"{len(sg['inbound_rules']):<10} {len(sg['outbound_rules']):<10} {sg['total_risks']}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS Security Groups Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="🔒 Security Groups"
        ))
    else:
        print(f"AWS Security Groups Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    ec2_client = session.client('ec2')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando Security Groups...", total=None)
            results = analyze_security_groups(ec2_client, args.vpc_id)
        console.print(f"✅ Security Groups encontrados: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando Security Groups...")
        results = analyze_security_groups(ec2_client, args.vpc_id)
        print(f"Security Groups encontrados: {len(results)}")
    
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
    
    risky_count = sum(1 for sg in results if sg["total_risks"] > 0)
    total_risks = sum(sg["total_risks"] for sg in results)
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total Security Groups:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Con riesgos:[/bold] [red]{risky_count}[/red] | [bold]Total hallazgos:[/bold] [yellow]{total_risks}[/yellow]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(results)} | Con riesgos: {risky_count} | Hallazgos: {total_risks}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
