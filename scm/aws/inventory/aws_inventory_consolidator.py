#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Inventory Consolidator — Tool 40

Consolida el inventario de recursos AWS de múltiples regiones:

- Por región: EC2, RDS, Lambda, EKS, ECR, ELB, VPC, S3 (global una vez)
- Detalle por recurso opcional (--detailed)
- Tabla comparativa por región + totales
- Export JSON/CSV a outcome/

Equivalente a GCP Tool: Inventory Consolidator
(inventory/generar-inventario-csv + combinar-a-excel).

Uso:
    python aws_inventory_consolidator.py --profile p \\
        --regions us-east-1,us-west-2 -o json
    python aws_inventory_consolidator.py --regions all
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

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
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

SERVICES = ["ec2", "rds", "lambda", "eks", "ecr", "elb", "vpc"]


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Conteo por servicio/región
# ═══════════════════════════════════════════════════════════════════════════════

def count_ec2(session) -> int:
    ec2 = session.client("ec2")
    return sum(len(r.get("Instances", []))
               for p in ec2.get_paginator(
                   "describe_instances").paginate()
               for r in p.get("Reservations", []))


def count_rds(session) -> int:
    rds = session.client("rds")
    return sum(len(p.get("DBInstances", []))
               for p in rds.get_paginator(
                   "describe_db_instances").paginate())


def count_lambda(session) -> int:
    lam = session.client("lambda")
    return sum(len(p.get("Functions", []))
               for p in lam.get_paginator("list_functions").paginate())


def count_eks(session) -> int:
    eks = session.client("eks")
    count, token = 0, None
    while True:
        kw = {"nextToken": token} if token else {}
        resp = eks.list_clusters(**kw)
        count += len(resp.get("clusters", []))
        token = resp.get("nextToken")
        if not token:
            return count


def count_ecr(session) -> int:
    ecr = session.client("ecr")
    return sum(len(p.get("repositories", []))
               for p in ecr.get_paginator(
                   "describe_repositories").paginate())


def count_elb(session) -> int:
    elb = session.client("elbv2")
    return sum(len(p.get("LoadBalancers", []))
               for p in elb.get_paginator(
                   "describe_load_balancers").paginate())


def count_vpc(session) -> int:
    return len(session.client("ec2").describe_vpcs().get("Vpcs", []))


COUNTERS = {"ec2": count_ec2, "rds": count_rds, "lambda": count_lambda,
            "eks": count_eks, "ecr": count_ecr, "elb": count_elb,
            "vpc": count_vpc}


def list_regions(session) -> List[str]:
    ec2 = session.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in
            ec2.describe_regions(
                AllRegions=False).get("Regions", [])]


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Consolida inventario AWS multi-región")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--regions", default="",
                        help="CSV de regiones o 'all' (default: "
                             "todas las habilitadas)")
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
        base = boto3.Session(profile_name=args.profile,
                             region_name="us-east-1")
        regions = list_regions(base) \
            if args.regions.lower() in ("", "all") else \
            [r.strip() for r in args.regions.split(",") if r.strip()]
    except Exception as e:
        _print(f"❌ Error listando regiones: {e}", "red")
        sys.exit(1)

    rows = []
    for region in regions:
        sess = boto3.Session(profile_name=args.profile,
                             region_name=region)
        row = {"region": region, "counts": {}, "errors": {}}
        for svc, counter in COUNTERS.items():
            try:
                row["counts"][svc] = counter(sess)
            except Exception as e:
                row["counts"][svc] = None
                row["errors"][svc] = str(e)[:80]
        rows.append(row)
        _print(f"  {region}: {row['counts']}", "dim")

    # Totales
    totals = {svc: sum(r["counts"][svc] or 0 for r in rows)
              for svc in SERVICES}

    if console:
        table = Table(title="Inventario AWS por región",
                      header_style="bold cyan")
        table.add_column("Región")
        for svc in SERVICES:
            table.add_column(svc.upper())
        for r in rows:
            table.add_row(r["region"],
                          *[str(r["counts"][s])
                            if r["counts"][s] is not None else "ERR"
                            for s in SERVICES])
        table.add_row("[bold]TOTAL[/bold]",
                      *[f"[bold]{totals[s]}[/bold]" for s in SERVICES])
        console.print(table)
        for r in rows:
            for svc, err in r["errors"].items():
                console.print(f"  [dim]⚠ {r['region']}/{svc}: "
                              f"{err}[/dim]")
    else:
        for r in rows:
            print(f"{r['region']}: {r['counts']}")
        print(f"TOTAL: {totals}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"aws_inventory_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "profile": args.profile, "totals": totals,
                "regions": rows}, indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["region"] + SERVICES)
                for r in rows:
                    w.writerow([r["region"]] +
                               [r["counts"][s] for s in SERVICES])
                w.writerow(["TOTAL"] + [totals[s] for s in SERVICES])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
