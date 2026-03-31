#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Load Balancer Checker (ALB/NLB/CLB)

Analiza Application, Network y Classic Load Balancers con listeners, target groups y health checks.

Uso:
    python aws_load_balancer_checker.py --profile default --region us-east-1
    python aws_load_balancer_checker.py -o json
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


def get_args():
    parser = argparse.ArgumentParser(description="AWS Load Balancer Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--type", "-t", choices=["all", "alb", "nlb"], default="all", help="LB type filter")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_load_balancers(elbv2_client, lb_type: str = "all") -> List[Dict]:
    results = []
    
    lbs = elbv2_client.describe_load_balancers()["LoadBalancers"]
    
    for lb in lbs:
        lb_arn = lb["LoadBalancerArn"]
        lb_type_actual = lb.get("Type", "application")
        
        if lb_type != "all":
            if lb_type == "alb" and lb_type_actual != "application":
                continue
            if lb_type == "nlb" and lb_type_actual != "network":
                continue
        
        lb_data = {
            "name": lb.get("LoadBalancerName", ""),
            "arn": lb_arn,
            "type": lb_type_actual,
            "scheme": lb.get("Scheme", ""),
            "state": lb.get("State", {}).get("Code", ""),
            "dns_name": lb.get("DNSName", ""),
            "vpc_id": lb.get("VpcId", ""),
            "availability_zones": [az["ZoneName"] for az in lb.get("AvailabilityZones", [])],
            "security_groups": lb.get("SecurityGroups", []),
            "ip_address_type": lb.get("IpAddressType", ""),
            "created_time": lb.get("CreatedTime", "").isoformat() if lb.get("CreatedTime") else None,
            "listeners": [],
            "target_groups": [],
            "findings": []
        }
        
        try:
            listeners = elbv2_client.describe_listeners(LoadBalancerArn=lb_arn)["Listeners"]
            for listener in listeners:
                listener_data = {
                    "port": listener.get("Port", 0),
                    "protocol": listener.get("Protocol", ""),
                    "ssl_policy": listener.get("SslPolicy", ""),
                    "certificates": len(listener.get("Certificates", []))
                }
                lb_data["listeners"].append(listener_data)
                
                if listener.get("Protocol") == "HTTP" and listener.get("Port") == 80:
                    has_https = any(l.get("Protocol") == "HTTPS" for l in listeners)
                    if not has_https:
                        lb_data["findings"].append("Solo HTTP sin HTTPS")
        except ClientError:
            pass
        
        try:
            tgs = elbv2_client.describe_target_groups(LoadBalancerArn=lb_arn)["TargetGroups"]
            for tg in tgs:
                tg_arn = tg["TargetGroupArn"]
                tg_data = {
                    "name": tg.get("TargetGroupName", ""),
                    "protocol": tg.get("Protocol", ""),
                    "port": tg.get("Port", 0),
                    "target_type": tg.get("TargetType", ""),
                    "health_check_path": tg.get("HealthCheckPath", ""),
                    "healthy_threshold": tg.get("HealthyThresholdCount", 0),
                    "targets": []
                }
                
                try:
                    health = elbv2_client.describe_target_health(TargetGroupArn=tg_arn)
                    for target in health.get("TargetHealthDescriptions", []):
                        tg_data["targets"].append({
                            "id": target.get("Target", {}).get("Id", ""),
                            "port": target.get("Target", {}).get("Port", 0),
                            "health": target.get("TargetHealth", {}).get("State", ""),
                            "reason": target.get("TargetHealth", {}).get("Reason", "")
                        })
                    
                    unhealthy = sum(1 for t in tg_data["targets"] if t["health"] != "healthy")
                    if unhealthy > 0:
                        lb_data["findings"].append(f"Target Group {tg_data['name']}: {unhealthy} targets unhealthy")
                except ClientError:
                    pass
                
                lb_data["target_groups"].append(tg_data)
        except ClientError:
            pass
        
        if lb_data["scheme"] == "internet-facing" and not lb_data["security_groups"]:
            lb_data["findings"].append("Internet-facing sin Security Groups")
        
        results.append(lb_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_load_balancers_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "load_balancers": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_load_balancers_{timestamp}.csv"
        rows = [{
            "name": lb["name"], "type": lb["type"], "scheme": lb["scheme"], "state": lb["state"],
            "listeners": len(lb["listeners"]), "target_groups": len(lb["target_groups"]),
            "findings": len(lb["findings"])
        } for lb in results]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]Load Balancers Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Nombre", style="cyan", max_width=30)
    table.add_column("Tipo", justify="center")
    table.add_column("Scheme", justify="center")
    table.add_column("Estado", justify="center")
    table.add_column("Listeners", justify="center")
    table.add_column("TGs", justify="center")
    table.add_column("AZs", justify="center")
    table.add_column("Findings", justify="center")
    
    for lb in results:
        type_color = "blue" if lb["type"] == "application" else "magenta"
        state_color = "green" if lb["state"] == "active" else "yellow"
        findings = f"[red]⚠️ {len(lb['findings'])}[/red]" if lb["findings"] else "[green]✅[/green]"
        
        table.add_row(
            lb["name"][:30],
            f"[{type_color}]{lb['type'].upper()[:3]}[/{type_color}]",
            lb["scheme"],
            f"[{state_color}]{lb['state']}[/{state_color}]",
            str(len(lb["listeners"])),
            str(len(lb["target_groups"])),
            str(len(lb["availability_zones"])),
            findings
        )
    
    console.print(table)
    
    lbs_with_findings = [lb for lb in results if lb["findings"]]
    if lbs_with_findings:
        console.print("\n[bold red]⚠️ Load Balancers con hallazgos:[/bold red]")
        for lb in lbs_with_findings:
            console.print(f"  [yellow]{lb['name']}[/yellow]:")
            for finding in lb["findings"]:
                console.print(f"    - {finding}")


def display_results_plain(results: List[Dict]):
    print("\n=== Load Balancers Analysis ===\n")
    print(f"{'Nombre':<30} {'Tipo':<8} {'Scheme':<15} {'Estado':<10} {'Listeners':<10}")
    print("-" * 80)
    for lb in results:
        print(f"{lb['name'][:30]:<30} {lb['type'][:7]:<8} {lb['scheme']:<15} {lb['state']:<10} {len(lb['listeners']):<10}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS Load Balancer Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="⚖️ ELB Checker"
        ))
    else:
        print(f"AWS Load Balancer Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    elbv2_client = session.client('elbv2')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando Load Balancers...", total=None)
            results = analyze_load_balancers(elbv2_client, args.type)
        console.print(f"✅ Load Balancers encontrados: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando Load Balancers...")
        results = analyze_load_balancers(elbv2_client, args.type)
        print(f"Load Balancers encontrados: {len(results)}")
    
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
    
    albs = sum(1 for lb in results if lb["type"] == "application")
    nlbs = sum(1 for lb in results if lb["type"] == "network")
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total LBs:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]ALBs:[/bold] [blue]{albs}[/blue] | [bold]NLBs:[/bold] [magenta]{nlbs}[/magenta]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(results)} | ALBs: {albs} | NLBs: {nlbs}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
