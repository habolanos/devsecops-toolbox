#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Infrastructure Consolidator — Tool 32

Consolida la infraestructura AWS con mapeo de relaciones:

- ALB/NLB → listeners → target groups → targets (EC2/IP/Lambda)
- Lambda functions referenciadas como targets
- RDS instances y su estado
- Recursos huérfanos: target groups sin targets healthy,
  LBs sin listeners, Lambdas no referenciadas
- Salud general del mapa (healthy/unhealthy targets)

Equivalente a GCP Tool: Infrastructure Consolidator
(consolidation/gcp_infrastructure_consolidator.py).

Uso:
    python aws_infrastructure_consolidator.py --profile p \\
        --region us-east-1 -o json
    python aws_infrastructure_consolidator.py --view orphans
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Recolección
# ═══════════════════════════════════════════════════════════════════════════════

def collect_load_balancers(elbv2) -> List[Dict]:
    lbs = []
    for page in elbv2.get_paginator(
            "describe_load_balancers").paginate():
        lbs.extend(page.get("LoadBalancers", []))
    return lbs


def collect_target_groups(elbv2) -> List[Dict]:
    tgs = []
    for page in elbv2.get_paginator(
            "describe_target_groups").paginate():
        tgs.extend(page.get("TargetGroups", []))
    return tgs


def collect_listeners(elbv2, lb_arn: str) -> List[Dict]:
    try:
        return elbv2.describe_listeners(
            LoadBalancerArn=lb_arn).get("Listeners", [])
    except ClientError:
        return []


def collect_target_health(elbv2, tg_arn: str) -> List[Dict]:
    try:
        return elbv2.describe_target_health(
            TargetGroupArn=tg_arn).get("TargetHealthDescriptions", [])
    except ClientError:
        return []


def build_consolidation(session) -> Dict:
    elbv2 = session.client("elbv2")
    lam = session.client("lambda")
    rds = session.client("rds")

    # Lambdas referenciadas por TGs
    lambda_targets: Set[str] = set()
    relationships: List[Dict] = []
    orphaned_tgs, unhealthy_targets = [], []

    target_groups = collect_target_groups(elbv2)
    tg_map = {tg["TargetGroupArn"]: tg for tg in target_groups}
    attached_tgs: Set[str] = set()

    for lb in collect_load_balancers(elbv2):
        lb_name = lb["LoadBalancerName"]
        listeners = collect_listeners(elbv2, lb["LoadBalancerArn"])
        lb_node = {
            "type": lb.get("Type"),
            "scheme": lb.get("Scheme"),
            "dns": lb.get("DNSName"),
            "listeners": len(listeners),
            "target_groups": [],
        }
        for listener in listeners:
            for action in listener.get("DefaultActions", []):
                for fwd in ([action] if action.get("TargetGroupArn")
                            else action.get("ForwardConfig", {})
                            .get("TargetGroups", [])):
                    tg_arn = fwd.get("TargetGroupArn")
                    if not tg_arn:
                        continue
                    attached_tgs.add(tg_arn)
                    tg = tg_map.get(tg_arn, {})
                    health = collect_target_health(elbv2, tg_arn)
                    targets = []
                    for t in health:
                        tid = t.get("Target", {}).get("Id", "?")
                        state = t.get("TargetHealth", {}).get(
                            "State", "?")
                        targets.append({"id": tid, "state": state})
                        if state not in ("healthy", "initial"):
                            unhealthy_targets.append(
                                {"tg": tg.get("TargetGroupName"),
                                 "target": tid, "state": state})
                        if tg.get("TargetType") == "lambda":
                            lambda_targets.add(tid)
                    lb_node["target_groups"].append({
                        "name": tg.get("TargetGroupName"),
                        "type": tg.get("TargetType"),
                        "targets": targets})
        if not listeners:
            lb_node["orphan_reason"] = "sin listeners"
        relationships.append({"lb": lb_name, **lb_node})

    # TGs huérfanos (sin LB)
    for tg in target_groups:
        if tg["TargetGroupArn"] not in attached_tgs:
            orphaned_tgs.append({
                "name": tg.get("TargetGroupName"),
                "type": tg.get("TargetType"),
                "reason": "sin load balancer asociado"})

    # Lambdas
    lambdas, unreferenced = [], []
    try:
        for page in lam.get_paginator("list_functions").paginate():
            for fn in page.get("Functions", []):
                lambdas.append(fn["FunctionName"])
                if fn["FunctionArn"] not in lambda_targets and \
                        fn["FunctionName"] not in lambda_targets:
                    unreferenced.append(fn["FunctionName"])
    except ClientError:
        pass

    # RDS
    rds_instances = []
    try:
        for page in rds.get_paginator(
                "describe_db_instances").paginate():
            for inst in page.get("DBInstances", []):
                rds_instances.append({
                    "id": inst["DBInstanceIdentifier"],
                    "engine": inst["Engine"],
                    "status": inst["DBInstanceStatus"]})
    except ClientError:
        pass

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "load_balancers": relationships,
        "lambdas": {"total": len(lambdas),
                    "unreferenced": unreferenced},
        "rds": rds_instances,
        "orphaned_target_groups": orphaned_tgs,
        "unhealthy_targets": unhealthy_targets,
        "summary": {
            "load_balancers": len(relationships),
            "target_groups": len(target_groups),
            "orphaned_tgs": len(orphaned_tgs),
            "lambdas": len(lambdas),
            "unreferenced_lambdas": len(unreferenced),
            "rds_instances": len(rds_instances),
            "unhealthy_targets": len(unhealthy_targets),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Reporte
# ═══════════════════════════════════════════════════════════════════════════════

def print_consolidation(data: Dict, view: str):
    if console:
        s = data["summary"]
        console.print(Panel.fit(
            f"LBs: {s['load_balancers']} | TGs: {s['target_groups']} | "
            f"Lambdas: {s['lambdas']} | RDS: {s['rds_instances']}\n"
            f"[yellow]Huérfanos: {s['orphaned_tgs']} TGs, "
            f"{s['unreferenced_lambdas']} lambdas[/yellow] | "
            f"[red]Targets unhealthy: {s['unhealthy_targets']}[/red]",
            title="🔗 Consolidación"))

        if view in ("all", "map"):
            tree = Tree("[bold]Load Balancers[/bold]")
            for lb in data["load_balancers"]:
                node = tree.add(
                    f"[cyan]{lb['lb']}[/cyan] ({lb['type']}, "
                    f"{lb['scheme']}) — {lb['dns']}")
                if lb.get("orphan_reason"):
                    node.add(f"[red]⚠ {lb['orphan_reason']}[/red]")
                for tg in lb["target_groups"]:
                    tgn = node.add(
                        f"[yellow]TG {tg['name']}[/yellow] "
                        f"({tg['type']})")
                    for t in tg["targets"]:
                        color = "green" if t["state"] == "healthy" \
                            else "red"
                        tgn.add(f"[{color}]{t['id']} — "
                                f"{t['state']}[/{color}]")
            console.print(tree)

        if view in ("all", "orphans"):
            if data["orphaned_target_groups"]:
                table = Table(title="Target Groups huérfanos")
                table.add_column("Nombre"); table.add_column("Tipo")
                table.add_column("Razón")
                for tg in data["orphaned_target_groups"]:
                    table.add_row(tg["name"], str(tg["type"]),
                                  tg["reason"])
                console.print(table)
            if data["lambdas"]["unreferenced"]:
                console.print(
                    f"[yellow]Lambdas sin referencia en TGs "
                    f"({len(data['lambdas']['unreferenced'])}):[/yellow] "
                    + ", ".join(
                        data["lambdas"]["unreferenced"][:15]))
    else:
        print(json.dumps(data["summary"], indent=2))
        for lb in data["load_balancers"]:
            print(f"LB {lb['lb']}: {len(lb['target_groups'])} TGs")


def get_args():
    parser = argparse.ArgumentParser(
        description="Consolida ALB/Lambda/RDS con relaciones")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--view", choices=["all", "map", "orphans"],
                        default="all")
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    try:
        session = boto3.Session(profile_name=args.profile,
                                region_name=args.region)
        data = build_consolidation(session)
    except Exception as e:
        _print(f"❌ Error: {e}", "red")
        sys.exit(1)

    print_consolidation(data, args.view)

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"infrastructure_consolidation_{ts}." \
                            f"{args.output}"
        if args.output == "json":
            out.write_text(json.dumps(data, indent=2, default=str),
                           encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["lb", "type", "scheme", "listeners",
                            "target_groups"])
                for lb in data["load_balancers"]:
                    w.writerow([lb["lb"], lb["type"], lb["scheme"],
                                lb["listeners"],
                                len(lb["target_groups"])])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
