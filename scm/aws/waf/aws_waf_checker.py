#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS WAF Checker

Analiza Web ACLs de AWS WAF v2: reglas, grupos, métricas y asociaciones
con ALB, API Gateway, CloudFront y AppSync.
Detecta Web ACLs sin reglas, sin logging o sin asociaciones activas.

Equivalente AWS de: cloud-armor/ (GCP Cloud Armor Policies)

Uso:
    python aws_waf_checker.py --profile default --region us-east-1
    python aws_waf_checker.py --scope CLOUDFRONT --region us-east-1
    python aws_waf_checker.py -o json

Nota: Para CloudFront, usar --region us-east-1 (WAF es global para CF).

Autor: Harold Adrian
"""

import sys
import json
import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time

# --- Directorio de salida centralizado ---
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
    from rich.tree import Tree
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS WAF Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--scope", choices=["REGIONAL", "CLOUDFRONT"], default="REGIONAL",
                        help="Scope: REGIONAL (ALB/APIGW) o CLOUDFRONT (default: REGIONAL)")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_web_acls(wafv2_client, scope: str) -> List[Dict]:
    results = []

    try:
        paginator = wafv2_client.get_paginator("list_web_acls")
        acl_pages = paginator.paginate(Scope=scope)
    except ClientError as e:
        if RICH_AVAILABLE:
            console.print(f"[yellow]⚠️  No se puede listar Web ACLs: {e}[/yellow]")
        return results

    for page in acl_pages:
        for acl_summary in page.get("WebACLs", []):
            acl_id = acl_summary.get("Id", "")
            acl_name = acl_summary.get("Name", "")
            lock_token = acl_summary.get("LockToken", "")

            try:
                acl_detail = wafv2_client.get_web_acl(
                    Name=acl_name, Scope=scope, Id=acl_id
                ).get("WebACL", {})
            except ClientError:
                acl_detail = {}

            rules = acl_detail.get("Rules", [])
            default_action = list(acl_detail.get("DefaultAction", {}).keys())
            visibility = acl_detail.get("VisibilityConfig", {})
            logging_enabled = bool(acl_detail.get("LoggingConfiguration"))
            capacity = acl_detail.get("Capacity", 0)

            # Analizar reglas
            rule_details = []
            for rule in rules:
                action = rule.get("Action", rule.get("OverrideAction", {}))
                action_type = list(action.keys())[0] if action else "unknown"
                rule_details.append({
                    "name": rule.get("Name", ""),
                    "priority": rule.get("Priority", 0),
                    "action": action_type,
                    "managed": "ManagedRuleGroupStatement" in str(rule.get("Statement", {})),
                    "cloudwatch_metrics": rule.get("VisibilityConfig", {}).get("CloudWatchMetricsEnabled", False),
                })

            # Recursos asociados
            resources = []
            try:
                resp = wafv2_client.list_resources_for_web_acl(WebACLArn=acl_summary.get("ARN", ""), ResourceType="APPLICATION_LOAD_BALANCER")
                resources.extend(resp.get("ResourceArns", []))
            except ClientError:
                pass
            try:
                resp = wafv2_client.list_resources_for_web_acl(WebACLArn=acl_summary.get("ARN", ""), ResourceType="API_GATEWAY")
                resources.extend(resp.get("ResourceArns", []))
            except ClientError:
                pass

            findings = []
            if not rules:
                findings.append("Sin reglas configuradas")
            if not logging_enabled:
                findings.append("Logging deshabilitado")
            if not resources:
                findings.append("Sin recursos asociados")
            if default_action == ["Allow"] and not rules:
                findings.append("Allow por defecto sin reglas")
            managed_rules = sum(1 for r in rule_details if r["managed"])
            if managed_rules == 0 and rules:
                findings.append("Sin Managed Rule Groups")

            results.append({
                "name": acl_name,
                "id": acl_id,
                "arn": acl_summary.get("ARN", ""),
                "scope": scope,
                "default_action": default_action[0] if default_action else "unknown",
                "rules_count": len(rules),
                "managed_rules_count": managed_rules,
                "capacity_units": capacity,
                "logging_enabled": logging_enabled,
                "cloudwatch_metrics": visibility.get("CloudWatchMetricsEnabled", False),
                "sampled_requests": visibility.get("SampledRequestsEnabled", False),
                "resources": resources,
                "rules": rule_details,
                "findings": findings,
            })

    return results


def analyze_rule_groups(wafv2_client, scope: str) -> List[Dict]:
    """Lista Rule Groups disponibles en la cuenta."""
    results = []
    try:
        paginator = wafv2_client.get_paginator("list_rule_groups")
        for page in paginator.paginate(Scope=scope):
            for rg in page.get("RuleGroups", []):
                results.append({
                    "name": rg.get("Name", ""),
                    "id": rg.get("Id", ""),
                    "arn": rg.get("ARN", ""),
                    "description": rg.get("Description", ""),
                    "capacity": rg.get("Capacity", 0),
                })
    except ClientError:
        pass
    return results


def display_table_rich(web_acls: List[Dict]):
    if not web_acls:
        console.print("[yellow]⚠️  No se encontraron Web ACLs.[/yellow]")
        return

    table = Table(
        title=f"🛡️  AWS WAF Web ACLs ({len(web_acls)})",
        header_style="bold white on dark_red",
        show_lines=True,
    )
    table.add_column("Nombre", style="cyan", min_width=25)
    table.add_column("Scope", width=10)
    table.add_column("Default", width=8)
    table.add_column("Reglas", justify="right", width=7)
    table.add_column("Managed", justify="right", width=8)
    table.add_column("Capacidad", justify="right", width=9)
    table.add_column("Logging", width=8, justify="center")
    table.add_column("Recursos", justify="right", width=8)
    table.add_column("Findings", min_width=30)

    for acl in web_acls:
        log_icon = "✅" if acl["logging_enabled"] else "❌"
        findings_str = "; ".join(acl["findings"]) if acl["findings"] else "✅ OK"
        findings_color = "red" if any("Sin reglas" in f or "Allow por defecto" in f for f in acl["findings"]) \
            else "yellow" if acl["findings"] else "green"
        action_color = "green" if acl["default_action"] == "Block" else "yellow"

        table.add_row(
            acl["name"],
            acl["scope"],
            f"[{action_color}]{acl['default_action']}[/{action_color}]",
            str(acl["rules_count"]),
            str(acl["managed_rules_count"]),
            str(acl["capacity_units"]),
            log_icon,
            str(len(acl["resources"])),
            f"[{findings_color}]{findings_str}[/{findings_color}]",
        )

    console.print(table)
    console.print()

    for acl in web_acls:
        if acl["rules"]:
            tree = Tree(f"[bold cyan]📋 Reglas: {acl['name']}[/bold cyan]")
            for rule in sorted(acl["rules"], key=lambda x: x["priority"]):
                action_color = "red" if rule["action"] == "Block" else "green" if rule["action"] == "Allow" else "yellow"
                managed_tag = "[dim][Managed][/dim]" if rule["managed"] else ""
                tree.add(
                    f"[dim]{rule['priority']:02d}[/dim] {rule['name']} → "
                    f"[{action_color}]{rule['action']}[/{action_color}] {managed_tag}"
                )
            console.print(tree)
            console.print()


def display_table_plain(web_acls: List[Dict]):
    print(f"\n{'NOMBRE':<30} {'SCOPE':<10} {'REGLAS':>6} {'LOG':<6} {'RECURSOS':>8} {'FINDINGS'}")
    print("-" * 90)
    for acl in web_acls:
        print(f"{acl['name']:<30} {acl['scope']:<10} {acl['rules_count']:>6} "
              f"{'Sí' if acl['logging_enabled'] else 'No':<6} {len(acl['resources']):>8} "
              f"{'; '.join(acl['findings']) or 'OK'}")


def export_results(web_acls: List[Dict], output_format: str):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    OUTCOME_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format == "json":
        fp = OUTCOME_DIR / f"aws_waf_{ts}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "web_acls": web_acls}, f, indent=2)
        print(f"\n✅ JSON exportado: {fp}")
    elif output_format == "csv":
        fp = OUTCOME_DIR / f"aws_waf_{ts}.csv"
        fields = ["name", "id", "scope", "default_action", "rules_count", "managed_rules_count",
                  "capacity_units", "logging_enabled", "cloudwatch_metrics", "findings"]
        rows = [{**acl, "findings": "; ".join(acl.get("findings", [])),
                 "resources": len(acl.get("resources", []))} for acl in web_acls]
        with open(fp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n✅ CSV exportado: {fp}")


def main():
    start_time = time.time()
    args = get_args()

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS WAF Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow] | "
            f"Scope: [yellow]{args.scope}[/yellow]",
            title="🛡️  WAF Checker"
        ))
    else:
        print(f"AWS WAF Checker | Profile: {args.profile} | Region: {args.region} | Scope: {args.scope}")

    session = get_session(args.profile, args.region)
    wafv2_client = session.client("wafv2")

    try:
        if RICH_AVAILABLE:
            with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True, console=console) as p:
                p.add_task(f"Analizando Web ACLs [{args.scope}]...", total=None)
                web_acls = analyze_web_acls(wafv2_client, args.scope)
        else:
            print("Analizando Web ACLs...")
            web_acls = analyze_web_acls(wafv2_client, args.scope)
    except ClientError as e:
        if RICH_AVAILABLE:
            console.print(f"[red]❌ Error AWS: {e}[/red]")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    m, s = divmod(int(elapsed), 60)
    time_str = f"{m}m {s}s" if m else f"{s}s"

    if args.output == "table":
        if RICH_AVAILABLE:
            display_table_rich(web_acls)
        else:
            display_table_plain(web_acls)
    else:
        export_results(web_acls, args.output)

    with_findings = sum(1 for a in web_acls if a["findings"])
    with_logging = sum(1 for a in web_acls if a["logging_enabled"])

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Web ACLs:[/bold] [green]{len(web_acls)}[/green] | "
            f"[bold]Con logging:[/bold] [green]{with_logging}[/green] | "
            f"[bold]Con findings:[/bold] [yellow]{with_findings}[/yellow]\n"
            f"[bold]Tiempo:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\nWeb ACLs: {len(web_acls)} | Con logging: {with_logging} | Con findings: {with_findings} | {time_str}")


if __name__ == "__main__":
    main()
