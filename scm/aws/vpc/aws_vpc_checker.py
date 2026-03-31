#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS VPC Networks Checker

Visualiza VPCs, subnets, route tables, NAT gateways e internet gateways.

Uso:
    python aws_vpc_checker.py --profile default --region us-east-1
    python aws_vpc_checker.py -o json
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
    parser = argparse.ArgumentParser(description="AWS VPC Networks Checker")
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


def get_name_tag(tags: List[Dict]) -> str:
    for tag in tags or []:
        if tag.get("Key") == "Name":
            return tag.get("Value", "")
    return ""


def analyze_vpcs(ec2_client, vpc_filter: str = "") -> List[Dict]:
    results = []
    
    filters = []
    if vpc_filter:
        filters.append({"Name": "vpc-id", "Values": [vpc_filter]})
    
    vpcs = ec2_client.describe_vpcs(Filters=filters if filters else [])["Vpcs"]
    
    for vpc in vpcs:
        vpc_id = vpc["VpcId"]
        vpc_data = {
            "vpc_id": vpc_id,
            "name": get_name_tag(vpc.get("Tags", [])),
            "cidr_block": vpc.get("CidrBlock", ""),
            "state": vpc.get("State", ""),
            "is_default": vpc.get("IsDefault", False),
            "tenancy": vpc.get("InstanceTenancy", ""),
            "subnets": [],
            "route_tables": [],
            "internet_gateways": [],
            "nat_gateways": [],
            "vpn_gateways": [],
            "tags": {tag["Key"]: tag["Value"] for tag in vpc.get("Tags", [])}
        }
        
        subnets = ec2_client.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
        for subnet in subnets:
            vpc_data["subnets"].append({
                "subnet_id": subnet["SubnetId"],
                "name": get_name_tag(subnet.get("Tags", [])),
                "cidr_block": subnet.get("CidrBlock", ""),
                "availability_zone": subnet.get("AvailabilityZone", ""),
                "available_ips": subnet.get("AvailableIpAddressCount", 0),
                "map_public_ip": subnet.get("MapPublicIpOnLaunch", False),
                "state": subnet.get("State", "")
            })
        
        route_tables = ec2_client.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["RouteTables"]
        for rt in route_tables:
            routes = []
            for route in rt.get("Routes", []):
                routes.append({
                    "destination": route.get("DestinationCidrBlock") or route.get("DestinationIpv6CidrBlock", ""),
                    "target": route.get("GatewayId") or route.get("NatGatewayId") or route.get("NetworkInterfaceId", ""),
                    "state": route.get("State", "")
                })
            vpc_data["route_tables"].append({
                "route_table_id": rt["RouteTableId"],
                "name": get_name_tag(rt.get("Tags", [])),
                "associations": len(rt.get("Associations", [])),
                "routes": routes
            })
        
        igws = ec2_client.describe_internet_gateways(Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}])["InternetGateways"]
        for igw in igws:
            vpc_data["internet_gateways"].append({
                "igw_id": igw["InternetGatewayId"],
                "name": get_name_tag(igw.get("Tags", [])),
                "state": igw.get("Attachments", [{}])[0].get("State", "") if igw.get("Attachments") else ""
            })
        
        nat_gws = ec2_client.describe_nat_gateways(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["NatGateways"]
        for nat in nat_gws:
            if nat.get("State") != "deleted":
                vpc_data["nat_gateways"].append({
                    "nat_id": nat["NatGatewayId"],
                    "name": get_name_tag(nat.get("Tags", [])),
                    "state": nat.get("State", ""),
                    "subnet_id": nat.get("SubnetId", ""),
                    "connectivity_type": nat.get("ConnectivityType", "")
                })
        
        results.append(vpc_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_vpcs_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "vpcs": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_vpcs_{timestamp}.csv"
        rows = []
        for vpc in results:
            rows.append({
                "vpc_id": vpc["vpc_id"], "name": vpc["name"], "cidr": vpc["cidr_block"],
                "state": vpc["state"], "subnets": len(vpc["subnets"]),
                "route_tables": len(vpc["route_tables"]), "nat_gateways": len(vpc["nat_gateways"])
            })
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    for vpc in results:
        vpc_name = vpc["name"] or vpc["vpc_id"]
        tree = Tree(f"[bold cyan]🌐 VPC: {vpc_name}[/bold cyan] ({vpc['vpc_id']})")
        tree.add(f"[dim]CIDR:[/dim] {vpc['cidr_block']}")
        tree.add(f"[dim]Estado:[/dim] {vpc['state']}")
        tree.add(f"[dim]Default:[/dim] {'Sí' if vpc['is_default'] else 'No'}")
        
        if vpc["subnets"]:
            subnets_branch = tree.add(f"[yellow]📦 Subnets ({len(vpc['subnets'])})[/yellow]")
            for subnet in vpc["subnets"]:
                subnet_name = subnet["name"] or subnet["subnet_id"]
                public = "🌍" if subnet["map_public_ip"] else "🔒"
                subnets_branch.add(f"{public} {subnet_name} | {subnet['cidr_block']} | {subnet['availability_zone']} | IPs: {subnet['available_ips']}")
        
        if vpc["internet_gateways"]:
            igw_branch = tree.add(f"[green]🚪 Internet Gateways ({len(vpc['internet_gateways'])})[/green]")
            for igw in vpc["internet_gateways"]:
                igw_branch.add(f"{igw['igw_id']} | {igw.get('name', '-')}")
        
        if vpc["nat_gateways"]:
            nat_branch = tree.add(f"[magenta]🔀 NAT Gateways ({len(vpc['nat_gateways'])})[/magenta]")
            for nat in vpc["nat_gateways"]:
                nat_branch.add(f"{nat['nat_id']} | {nat.get('name', '-')} | {nat['state']}")
        
        if vpc["route_tables"]:
            rt_branch = tree.add(f"[blue]🛤️ Route Tables ({len(vpc['route_tables'])})[/blue]")
            for rt in vpc["route_tables"]:
                rt_name = rt["name"] or rt["route_table_id"]
                rt_branch.add(f"{rt_name} | Routes: {len(rt['routes'])} | Associations: {rt['associations']}")
        
        console.print(tree)
        console.print()


def display_results_plain(results: List[Dict]):
    print("\n=== VPC Networks ===\n")
    for vpc in results:
        print(f"VPC: {vpc['name'] or vpc['vpc_id']}")
        print(f"  CIDR: {vpc['cidr_block']} | State: {vpc['state']}")
        print(f"  Subnets: {len(vpc['subnets'])} | Route Tables: {len(vpc['route_tables'])}")
        print(f"  IGWs: {len(vpc['internet_gateways'])} | NAT GWs: {len(vpc['nat_gateways'])}")
        print()


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS VPC Networks Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="🌐 VPC Checker"
        ))
    else:
        print(f"AWS VPC Networks Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    ec2_client = session.client('ec2')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando VPCs y componentes de red...", total=None)
            results = analyze_vpcs(ec2_client, args.vpc_id)
        console.print(f"✅ VPCs encontradas: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando VPCs...")
        results = analyze_vpcs(ec2_client, args.vpc_id)
        print(f"VPCs encontradas: {len(results)}")
    
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
    
    total_subnets = sum(len(v["subnets"]) for v in results)
    total_nats = sum(len(v["nat_gateways"]) for v in results)
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Total VPCs:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Total Subnets:[/bold] [cyan]{total_subnets}[/cyan] | [bold]NAT Gateways:[/bold] [magenta]{total_nats}[/magenta]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nVPCs: {len(results)} | Subnets: {total_subnets} | NAT GWs: {total_nats}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
