#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS IAM Roles Checker

Lista roles IAM, trust policies, permisos adjuntos y analiza configuraciones.

Uso:
    python aws_roles_checker.py --profile default --region us-east-1
    python aws_roles_checker.py -o json
"""

import os
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
    parser = argparse.ArgumentParser(description="AWS IAM Roles Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table", help="Output format")
    parser.add_argument("--filter", "-f", default="", help="Filter roles by name pattern")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        return session
    except Exception as e:
        print(f"ERROR: No se pudo crear sesión AWS: {e}")
        sys.exit(1)


def get_iam_roles(iam_client, name_filter: str = "") -> List[Dict]:
    roles = []
    paginator = iam_client.get_paginator('list_roles')
    
    for page in paginator.paginate():
        for role in page['Roles']:
            if not name_filter or name_filter.lower() in role['RoleName'].lower():
                roles.append(role)
    
    return roles


def get_role_details(iam_client, role_name: str) -> Dict:
    details = {
        "role_name": role_name,
        "attached_policies": [],
        "inline_policies": [],
        "trust_principals": [],
        "trust_services": [],
        "is_service_role": False,
        "last_used": None
    }
    
    try:
        role_info = iam_client.get_role(RoleName=role_name)
        role_data = role_info.get("Role", {})
        
        details["arn"] = role_data.get("Arn", "")
        details["create_date"] = role_data.get("CreateDate", "").isoformat() if role_data.get("CreateDate") else None
        details["description"] = role_data.get("Description", "")
        details["max_session_duration"] = role_data.get("MaxSessionDuration", 3600)
        
        last_used = role_data.get("RoleLastUsed", {})
        if last_used.get("LastUsedDate"):
            details["last_used"] = last_used["LastUsedDate"].isoformat()
            details["last_used_region"] = last_used.get("Region", "")
        
        trust_policy = role_data.get("AssumeRolePolicyDocument", {})
        for statement in trust_policy.get("Statement", []):
            principal = statement.get("Principal", {})
            
            if isinstance(principal, str) and principal == "*":
                details["trust_principals"].append("*")
            elif isinstance(principal, dict):
                if "Service" in principal:
                    services = principal["Service"]
                    if isinstance(services, str):
                        services = [services]
                    details["trust_services"].extend(services)
                    details["is_service_role"] = True
                
                if "AWS" in principal:
                    aws_principals = principal["AWS"]
                    if isinstance(aws_principals, str):
                        aws_principals = [aws_principals]
                    details["trust_principals"].extend(aws_principals)
                
                if "Federated" in principal:
                    federated = principal["Federated"]
                    if isinstance(federated, str):
                        federated = [federated]
                    details["trust_principals"].extend([f"Federated: {f}" for f in federated])
    except ClientError as e:
        details["error"] = str(e)
    
    try:
        attached = iam_client.list_attached_role_policies(RoleName=role_name)
        details["attached_policies"] = [p["PolicyName"] for p in attached.get("AttachedPolicies", [])]
    except ClientError:
        pass
    
    try:
        inline = iam_client.list_role_policies(RoleName=role_name)
        details["inline_policies"] = inline.get("PolicyNames", [])
    except ClientError:
        pass
    
    return details


def categorize_role(role_details: Dict) -> str:
    role_name = role_details["role_name"].lower()
    
    if role_details["is_service_role"]:
        if "lambda" in role_name or "lambda.amazonaws.com" in str(role_details["trust_services"]):
            return "Lambda"
        if "ecs" in role_name or "ecs.amazonaws.com" in str(role_details["trust_services"]):
            return "ECS"
        if "eks" in role_name or "eks.amazonaws.com" in str(role_details["trust_services"]):
            return "EKS"
        if "ec2" in role_name or "ec2.amazonaws.com" in str(role_details["trust_services"]):
            return "EC2"
        return "Service"
    
    if "admin" in role_name:
        return "Admin"
    if "readonly" in role_name or "read-only" in role_name:
        return "ReadOnly"
    
    return "Custom"


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_iam_roles_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_roles": len(results),
                "roles": results
            }, f, indent=2, default=str)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_iam_roles_{timestamp}.csv"
        rows = []
        for role in results:
            rows.append({
                "role_name": role["role_name"],
                "category": role.get("category", ""),
                "is_service_role": role["is_service_role"],
                "attached_policies": len(role["attached_policies"]),
                "trust_services": ", ".join(role["trust_services"][:3]),
                "last_used": role.get("last_used", "Never")
            })
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]IAM Roles Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Rol", style="cyan", max_width=40)
    table.add_column("Categoría", justify="center")
    table.add_column("Políticas", justify="center")
    table.add_column("Trust Services", max_width=30)
    table.add_column("Último uso", justify="center")
    
    for role in results:
        category = role.get("category", "Custom")
        cat_color = {
            "Lambda": "yellow",
            "ECS": "green",
            "EKS": "blue",
            "EC2": "magenta",
            "Service": "cyan",
            "Admin": "red",
            "ReadOnly": "dim"
        }.get(category, "white")
        
        last_used = role.get("last_used", "Never")
        if last_used and last_used != "Never":
            last_used = last_used[:10]
        
        table.add_row(
            role["role_name"][:40],
            f"[{cat_color}]{category}[/{cat_color}]",
            str(len(role["attached_policies"]) + len(role["inline_policies"])),
            ", ".join(role["trust_services"][:2]) or "-",
            last_used or "Never"
        )
    
    console.print(table)


def display_results_plain(results: List[Dict]):
    print("\n=== IAM Roles Analysis ===\n")
    print(f"{'Rol':<40} {'Categoría':<12} {'Políticas':<10} {'Último uso':<12}")
    print("-" * 80)
    
    for role in results:
        category = role.get("category", "Custom")
        last_used = role.get("last_used", "Never")
        if last_used and last_used != "Never":
            last_used = last_used[:10]
        
        print(f"{role['role_name'][:40]:<40} {category:<12} "
              f"{len(role['attached_policies']) + len(role['inline_policies']):<10} {last_used or 'Never':<12}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS IAM Roles Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]"
            + (f"\nFilter: [magenta]{args.filter}[/magenta]" if args.filter else ""),
            title="🔐 Roles Checker"
        ))
    else:
        print(f"AWS IAM Roles Checker")
        print(f"Profile: {args.profile} | Region: {args.region}")
        if args.filter:
            print(f"Filter: {args.filter}")
        print()
    
    session = get_session(args.profile, args.region)
    iam_client = session.client('iam')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Obteniendo lista de roles IAM...", total=None)
            roles = get_iam_roles(iam_client, args.filter)
        console.print(f"✅ Roles encontrados: [bold green]{len(roles)}[/bold green]")
    else:
        print("Obteniendo lista de roles IAM...")
        roles = get_iam_roles(iam_client, args.filter)
        print(f"Roles encontrados: {len(roles)}")
    
    results = []
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), TimeElapsedColumn(), console=console) as progress:
            task = progress.add_task("[cyan]Analizando roles...", total=len(roles))
            for role in roles:
                role_name = role["RoleName"]
                progress.update(task, description=f"[cyan]Analizando: {role_name[:30]}...")
                details = get_role_details(iam_client, role_name)
                details["category"] = categorize_role(details)
                results.append(details)
                progress.advance(task)
    else:
        for i, role in enumerate(roles, 1):
            role_name = role["RoleName"]
            print(f"[{i}/{len(roles)}] Analizando: {role_name}")
            details = get_role_details(iam_client, role_name)
            details["category"] = categorize_role(details)
            results.append(details)
    
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
    
    service_roles = sum(1 for r in results if r["is_service_role"])
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total roles:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Service roles:[/bold] [cyan]{service_roles}[/cyan] | [bold]Custom:[/bold] [yellow]{len(results) - service_roles}[/yellow]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===")
        print(f"Total roles: {len(results)}")
        print(f"Service roles: {service_roles} | Custom: {len(results) - service_roles}")
        print(f"Tiempo de ejecución: {time_str}")


if __name__ == "__main__":
    main()
