#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS CloudWatch Alarms Checker

Monitorea alarmas CloudWatch, estado y configuración.

Uso:
    python aws_cloudwatch_checker.py --profile default --region us-east-1
    python aws_cloudwatch_checker.py --state ALARM -o json
"""

import sys
import json
import argparse
from datetime import datetime
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
    from rich.progress import Progress, SpinnerColumn, TextColumn
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
    parser = argparse.ArgumentParser(description="AWS CloudWatch Alarms Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--state", "-s", choices=["", "OK", "ALARM", "INSUFFICIENT_DATA"], default="", help="Filter by state")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_alarms(cloudwatch_client, state_filter: str = "") -> List[Dict]:
    results = []
    
    paginator = cloudwatch_client.get_paginator('describe_alarms')
    
    params = {}
    if state_filter:
        params["StateValue"] = state_filter
    
    for page in paginator.paginate(**params):
        for alarm in page.get('MetricAlarms', []):
            alarm_data = {
                "name": alarm['AlarmName'],
                "arn": alarm.get("AlarmArn", ""),
                "description": alarm.get("AlarmDescription", ""),
                "state": alarm.get("StateValue", ""),
                "state_reason": alarm.get("StateReason", ""),
                "state_updated": alarm.get("StateUpdatedTimestamp", "").isoformat() if alarm.get("StateUpdatedTimestamp") else None,
                "metric_name": alarm.get("MetricName", ""),
                "namespace": alarm.get("Namespace", ""),
                "statistic": alarm.get("Statistic", ""),
                "period_sec": alarm.get("Period", 0),
                "evaluation_periods": alarm.get("EvaluationPeriods", 0),
                "threshold": alarm.get("Threshold", 0),
                "comparison_operator": alarm.get("ComparisonOperator", ""),
                "actions_enabled": alarm.get("ActionsEnabled", False),
                "alarm_actions": alarm.get("AlarmActions", []),
                "ok_actions": alarm.get("OKActions", []),
                "dimensions": alarm.get("Dimensions", []),
                "treat_missing_data": alarm.get("TreatMissingData", ""),
                "findings": []
            }
            
            if not alarm_data["actions_enabled"]:
                alarm_data["findings"].append("Acciones deshabilitadas")
            
            if not alarm_data["alarm_actions"]:
                alarm_data["findings"].append("Sin acciones de alarma configuradas")
            
            if alarm_data["state"] == "INSUFFICIENT_DATA":
                alarm_data["findings"].append("Datos insuficientes para evaluar")
            
            results.append(alarm_data)
        
        for alarm in page.get('CompositeAlarms', []):
            alarm_data = {
                "name": alarm['AlarmName'],
                "arn": alarm.get("AlarmArn", ""),
                "description": alarm.get("AlarmDescription", ""),
                "state": alarm.get("StateValue", ""),
                "state_reason": alarm.get("StateReason", ""),
                "type": "composite",
                "alarm_rule": alarm.get("AlarmRule", ""),
                "actions_enabled": alarm.get("ActionsEnabled", False),
                "findings": []
            }
            results.append(alarm_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_cloudwatch_alarms_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "alarms": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_cloudwatch_alarms_{timestamp}.csv"
        rows = [{
            "name": a["name"], "state": a["state"], "metric": a.get("metric_name", ""),
            "namespace": a.get("namespace", ""), "actions_enabled": a["actions_enabled"],
            "findings": len(a["findings"])
        } for a in results]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]CloudWatch Alarms Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Alarma", style="cyan", max_width=35)
    table.add_column("Estado", justify="center")
    table.add_column("Métrica", max_width=20)
    table.add_column("Namespace", max_width=20)
    table.add_column("Acciones", justify="center")
    table.add_column("Findings", justify="center")
    
    for alarm in sorted(results, key=lambda x: (x["state"] != "ALARM", x["name"])):
        state = alarm["state"]
        state_display = {
            "OK": "[green]🟢 OK[/green]",
            "ALARM": "[red]🔴 ALARM[/red]",
            "INSUFFICIENT_DATA": "[yellow]🟡 INSUF[/yellow]"
        }.get(state, state)
        
        actions = "✅" if alarm["actions_enabled"] and alarm.get("alarm_actions") else "❌"
        findings = f"[red]⚠️ {len(alarm['findings'])}[/red]" if alarm["findings"] else "[green]✅[/green]"
        
        table.add_row(
            alarm["name"][:35],
            state_display,
            alarm.get("metric_name", "-")[:20],
            alarm.get("namespace", "-")[:20],
            actions,
            findings
        )
    
    console.print(table)


def display_results_plain(results: List[Dict]):
    print("\n=== CloudWatch Alarms ===\n")
    print(f"{'Alarma':<35} {'Estado':<15} {'Métrica':<20} {'Acciones':<10}")
    print("-" * 85)
    for alarm in sorted(results, key=lambda x: (x["state"] != "ALARM", x["name"])):
        actions = "Yes" if alarm["actions_enabled"] else "No"
        print(f"{alarm['name'][:35]:<35} {alarm['state']:<15} {alarm.get('metric_name', '-')[:20]:<20} {actions:<10}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS CloudWatch Alarms Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="📊 CloudWatch Checker"
        ))
    else:
        print(f"AWS CloudWatch Alarms Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    cloudwatch_client = session.client('cloudwatch')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando alarmas CloudWatch...", total=None)
            results = analyze_alarms(cloudwatch_client, args.state)
        console.print(f"✅ Alarmas encontradas: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando alarmas CloudWatch...")
        results = analyze_alarms(cloudwatch_client, args.state)
        print(f"Alarmas encontradas: {len(results)}")
    
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
    
    in_alarm = sum(1 for a in results if a["state"] == "ALARM")
    ok = sum(1 for a in results if a["state"] == "OK")
    insufficient = sum(1 for a in results if a["state"] == "INSUFFICIENT_DATA")
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total alarmas:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]ALARM:[/bold] [red]{in_alarm}[/red] | [bold]OK:[/bold] [green]{ok}[/green] | [bold]INSUFFICIENT:[/bold] [yellow]{insufficient}[/yellow]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(results)} | ALARM: {in_alarm} | OK: {ok} | INSUFFICIENT: {insufficient}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
