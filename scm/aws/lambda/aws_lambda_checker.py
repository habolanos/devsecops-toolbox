#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Lambda Functions Checker

Lista funciones Lambda, runtime, memoria, timeouts y configuración.

Uso:
    python aws_lambda_checker.py --profile default --region us-east-1
    python aws_lambda_checker.py -o json
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

DEPRECATED_RUNTIMES = ["python2.7", "python3.6", "python3.7", "nodejs10.x", "nodejs12.x", "ruby2.5", "dotnetcore2.1", "dotnetcore3.1"]


def get_args():
    parser = argparse.ArgumentParser(description="AWS Lambda Functions Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--filter", "-f", default="", help="Filter by function name")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_functions(lambda_client, name_filter: str = "") -> List[Dict]:
    results = []
    
    paginator = lambda_client.get_paginator('list_functions')
    
    for page in paginator.paginate():
        for func in page['Functions']:
            func_name = func['FunctionName']
            
            if name_filter and name_filter.lower() not in func_name.lower():
                continue
            
            func_data = {
                "name": func_name,
                "arn": func.get("FunctionArn", ""),
                "runtime": func.get("Runtime", ""),
                "handler": func.get("Handler", ""),
                "code_size_mb": round(func.get("CodeSize", 0) / (1024 * 1024), 2),
                "memory_mb": func.get("MemorySize", 128),
                "timeout_sec": func.get("Timeout", 3),
                "last_modified": func.get("LastModified", ""),
                "role": func.get("Role", "").split("/")[-1],
                "description": func.get("Description", ""),
                "vpc_config": bool(func.get("VpcConfig", {}).get("VpcId")),
                "layers": len(func.get("Layers", [])),
                "environment_vars": len(func.get("Environment", {}).get("Variables", {})),
                "architecture": func.get("Architectures", ["x86_64"])[0],
                "package_type": func.get("PackageType", "Zip"),
                "state": func.get("State", ""),
                "findings": [],
                "tags": {}
            }
            
            runtime = func_data["runtime"]
            if runtime in DEPRECATED_RUNTIMES:
                func_data["findings"].append(f"Runtime deprecado: {runtime}")
            
            if func_data["timeout_sec"] >= 900:
                func_data["findings"].append("Timeout máximo (15 min)")
            
            if func_data["memory_mb"] >= 3008:
                func_data["findings"].append("Memoria alta (>3GB)")
            
            if not func_data["description"]:
                func_data["findings"].append("Sin descripción")
            
            try:
                tags = lambda_client.list_tags(Resource=func["FunctionArn"])
                func_data["tags"] = tags.get("Tags", {})
            except ClientError:
                pass
            
            results.append(func_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_lambda_functions_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "functions": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_lambda_functions_{timestamp}.csv"
        rows = [{
            "name": f["name"], "runtime": f["runtime"], "memory_mb": f["memory_mb"],
            "timeout_sec": f["timeout_sec"], "code_size_mb": f["code_size_mb"],
            "vpc": f["vpc_config"], "findings": len(f["findings"])
        } for f in results]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]Lambda Functions Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Función", style="cyan", max_width=35)
    table.add_column("Runtime", justify="center")
    table.add_column("Memoria", justify="right")
    table.add_column("Timeout", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("VPC", justify="center")
    table.add_column("Findings", justify="center")
    
    for func in sorted(results, key=lambda x: x["name"]):
        runtime = func["runtime"]
        runtime_color = "red" if runtime in DEPRECATED_RUNTIMES else "green"
        vpc = "✅" if func["vpc_config"] else "❌"
        findings = f"[red]⚠️ {len(func['findings'])}[/red]" if func["findings"] else "[green]✅[/green]"
        
        table.add_row(
            func["name"][:35],
            f"[{runtime_color}]{runtime}[/{runtime_color}]",
            f"{func['memory_mb']} MB",
            f"{func['timeout_sec']}s",
            f"{func['code_size_mb']} MB",
            vpc,
            findings
        )
    
    console.print(table)


def display_results_plain(results: List[Dict]):
    print("\n=== Lambda Functions ===\n")
    print(f"{'Función':<35} {'Runtime':<15} {'Memoria':<10} {'Timeout':<10}")
    print("-" * 75)
    for func in sorted(results, key=lambda x: x["name"]):
        print(f"{func['name'][:35]:<35} {func['runtime']:<15} {func['memory_mb']:<10} {func['timeout_sec']}s")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS Lambda Functions Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="⚡ Lambda Checker"
        ))
    else:
        print(f"AWS Lambda Functions Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    lambda_client = session.client('lambda')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando funciones Lambda...", total=None)
            results = analyze_functions(lambda_client, args.filter)
        console.print(f"✅ Funciones encontradas: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando funciones Lambda...")
        results = analyze_functions(lambda_client, args.filter)
        print(f"Funciones encontradas: {len(results)}")
    
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
    
    deprecated = sum(1 for f in results if f["runtime"] in DEPRECATED_RUNTIMES)
    in_vpc = sum(1 for f in results if f["vpc_config"])
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total funciones:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Con runtime deprecado:[/bold] [red]{deprecated}[/red] | [bold]En VPC:[/bold] [cyan]{in_vpc}[/cyan]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(results)} | Deprecados: {deprecated} | En VPC: {in_vpc}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
