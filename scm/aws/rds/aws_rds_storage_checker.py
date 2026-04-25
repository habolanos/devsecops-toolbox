#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS RDS Storage Monitor

Monitorea uso de almacenamiento en instancias RDS con alertas de capacidad.

Uso:
    python aws_rds_storage_checker.py --profile default --region us-east-1
    python aws_rds_storage_checker.py --threshold 80 -o json
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
    parser = argparse.ArgumentParser(description="AWS RDS Storage Monitor")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--threshold", "-t", type=int, default=80, help="Alert threshold percentage (default: 80)")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def get_storage_metrics(rds_client, cloudwatch_client, threshold: int) -> List[Dict]:
    results = []
    instances = []
    
    paginator = rds_client.get_paginator('describe_db_instances')
    for page in paginator.paginate():
        instances.extend(page['DBInstances'])
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=6)
    
    for instance in instances:
        identifier = instance['DBInstanceIdentifier']
        allocated_gb = instance.get('AllocatedStorage', 0)
        max_allocated = instance.get('MaxAllocatedStorage')
        
        storage_data = {
            "identifier": identifier,
            "engine": instance.get("Engine", ""),
            "instance_class": instance.get("DBInstanceClass", ""),
            "status": instance.get("DBInstanceStatus", ""),
            "storage_type": instance.get("StorageType", ""),
            "allocated_gb": allocated_gb,
            "max_allocated_gb": max_allocated,
            "autoscaling_enabled": max_allocated is not None and max_allocated > allocated_gb,
            "free_storage_gb": None,
            "used_storage_gb": None,
            "used_percentage": None,
            "alert_level": "ok"
        }
        
        try:
            response = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='FreeStorageSpace',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': identifier}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average', 'Minimum']
            )
            
            if response['Datapoints']:
                sorted_points = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
                latest = sorted_points[0]
                
                free_bytes = latest['Average']
                storage_data["free_storage_gb"] = round(free_bytes / (1024**3), 2)
                storage_data["used_storage_gb"] = round(allocated_gb - storage_data["free_storage_gb"], 2)
                
                if allocated_gb > 0:
                    used_pct = (storage_data["used_storage_gb"] / allocated_gb) * 100
                    storage_data["used_percentage"] = round(used_pct, 1)
                    
                    if used_pct >= 95:
                        storage_data["alert_level"] = "critical"
                    elif used_pct >= threshold:
                        storage_data["alert_level"] = "warning"
        except ClientError:
            pass
        
        results.append(storage_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_rds_storage_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "instances": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_rds_storage_{timestamp}.csv"
        pd.DataFrame(results).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict], threshold: int):
    table = Table(title="[bold]RDS Storage Monitor[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Instancia", style="cyan", max_width=30)
    table.add_column("Engine", justify="center")
    table.add_column("Tipo", justify="center")
    table.add_column("Allocated", justify="right")
    table.add_column("Used", justify="right")
    table.add_column("Free", justify="right")
    table.add_column("% Used", justify="center")
    table.add_column("AutoScale", justify="center")
    
    sorted_results = sorted(results, key=lambda x: x.get("used_percentage") or 0, reverse=True)
    
    for r in sorted_results:
        used_pct = r.get("used_percentage")
        
        if r["alert_level"] == "critical":
            pct_style = "[bold red]"
            pct_end = "[/bold red]"
            indicator = "🔴"
        elif r["alert_level"] == "warning":
            pct_style = "[yellow]"
            pct_end = "[/yellow]"
            indicator = "🟡"
        else:
            pct_style = "[green]"
            pct_end = "[/green]"
            indicator = "🟢"
        
        pct_display = f"{pct_style}{indicator} {used_pct}%{pct_end}" if used_pct is not None else "-"
        autoscale = "✅" if r["autoscaling_enabled"] else "❌"
        
        table.add_row(
            r["identifier"][:30],
            r["engine"],
            r["storage_type"],
            f"{r['allocated_gb']} GB",
            f"{r.get('used_storage_gb', '-')} GB" if r.get('used_storage_gb') else "-",
            f"{r.get('free_storage_gb', '-')} GB" if r.get('free_storage_gb') else "-",
            pct_display,
            autoscale
        )
    
    console.print(table)


def display_results_plain(results: List[Dict]):
    print("\n=== RDS Storage Monitor ===\n")
    print(f"{'Instancia':<30} {'Allocated':<12} {'Used':<12} {'Free':<12} {'% Used':<10}")
    print("-" * 80)
    for r in sorted(results, key=lambda x: x.get("used_percentage") or 0, reverse=True):
        pct = f"{r.get('used_percentage', '-')}%" if r.get('used_percentage') else "-"
        print(f"{r['identifier'][:30]:<30} {r['allocated_gb']:<12} "
              f"{r.get('used_storage_gb', '-'):<12} {r.get('free_storage_gb', '-'):<12} {pct:<10}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS RDS Storage Monitor[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]\n"
            f"Alert threshold: [magenta]{args.threshold}%[/magenta]",
            title="💾 Storage Monitor"
        ))
    else:
        print(f"AWS RDS Storage Monitor\nProfile: {args.profile} | Region: {args.region}\nThreshold: {args.threshold}%\n")
    
    session = get_session(args.profile, args.region)
    rds_client = session.client('rds')
    cloudwatch_client = session.client('cloudwatch')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Obteniendo métricas de almacenamiento...", total=None)
            results = get_storage_metrics(rds_client, cloudwatch_client, args.threshold)
        console.print(f"✅ Instancias analizadas: [bold green]{len(results)}[/bold green]")
    else:
        print("Obteniendo métricas de almacenamiento...")
        results = get_storage_metrics(rds_client, cloudwatch_client, args.threshold)
        print(f"Instancias analizadas: {len(results)}")
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    if args.output == "table":
        if RICH_AVAILABLE:
            display_results_rich(results, args.threshold)
        else:
            display_results_plain(results)
    else:
        export_results(results, args.output)
    
    critical = sum(1 for r in results if r["alert_level"] == "critical")
    warning = sum(1 for r in results if r["alert_level"] == "warning")
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total instancias:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Críticas (>95%):[/bold] [red]{critical}[/red] | [bold]Advertencia (>{args.threshold}%):[/bold] [yellow]{warning}[/yellow]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(results)} | Críticas: {critical} | Advertencia: {warning}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
