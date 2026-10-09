#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS VPC IP Addresses Checker — Tool 25

Analiza la capacidad de red de VPCs y subnets:

- Por cada subnet: CIDR, IPs totales, IPs disponibles
  (AvailableIpAddressCount), % utilización
- Reserva AWS: 5 IPs por subnet (network, router, DNS, reserved,
  broadcast)
- Semáforo por subnet: OK (<70%) / WARNING (≥70%) / CRITICAL (≥85%)
  / EXHAUSTED (0 disponibles)
- Resumen por VPC y alertas agregadas

Equivalente a GCP Tool: IP Addresses Checker
(vpc-networks/gcp_ip_addresses_checker.py — capacidad pods/services GKE).

Uso:
    python aws_vpc_ip_addresses_checker.py --profile p --region us-east-1
    python aws_vpc_ip_addresses_checker.py --region us-east-1 --vpc vpc-123 -o json
"""

import argparse
import csv
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

AWS_RESERVED_IPS = 5          # por subnet
WARN_THRESHOLD = 70.0
CRITICAL_THRESHOLD = 85.0


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Análisis
# ═══════════════════════════════════════════════════════════════════════════════

def cidr_total_ips(cidr: str) -> int:
    """IPs totales de un CIDR (todas las direcciones, no solo hosts)."""
    try:
        return ipaddress.ip_network(cidr).num_addresses
    except ValueError:
        return 0


def subnet_status(available: int, usable: int) -> str:
    """Semáforo por % de utilización sobre IPs usables."""
    if available == 0:
        return "EXHAUSTED"
    if usable <= 0:
        return "UNKNOWN"
    pct = 100.0 * (usable - available) / usable
    if pct >= CRITICAL_THRESHOLD:
        return "CRITICAL"
    if pct >= WARN_THRESHOLD:
        return "WARNING"
    return "OK"


def analyze_subnet(subnet: Dict) -> Dict:
    total = cidr_total_ips(subnet.get("CidrBlock", ""))
    usable = max(0, total - AWS_RESERVED_IPS)
    available = subnet.get("AvailableIpAddressCount", 0)
    used_pct = round(100.0 * (usable - available) / usable, 1) \
        if usable else 0.0
    name = next((t["Value"] for t in subnet.get("Tags", [])
                 if t["Key"] == "Name"), subnet["SubnetId"])
    return {
        "subnet_id": subnet["SubnetId"],
        "name": name,
        "vpc_id": subnet["VpcId"],
        "az": subnet.get("AvailabilityZone", ""),
        "cidr": subnet.get("CidrBlock", ""),
        "total_ips": total,
        "usable_ips": usable,
        "available_ips": available,
        "used_pct": used_pct,
        "status": subnet_status(available, usable),
        "public": subnet.get("MapPublicIpOnLaunch", False),
    }


def collect_subnets(ec2, vpc_filter: str = "") -> Tuple[List[Dict],
                                                      Dict[str, Dict]]:
    """Subnets analizadas + mapa {vpc_id: {name, cidr}}."""
    params = {}
    if vpc_filter:
        params["Filters"] = [{"Name": "vpc-id",
                              "Values": [vpc_filter]}]
    subnets = []
    paginator = ec2.get_paginator("describe_subnets")
    for page in paginator.paginate(**params):
        for s in page.get("Subnets", []):
            subnets.append(analyze_subnet(s))

    vpcs = {}
    vpc_ids = {s["vpc_id"] for s in subnets}
    if vpc_ids:
        for vpc in ec2.describe_vpcs(
                VpcIds=list(vpc_ids)).get("Vpcs", []):
            name = next((t["Value"] for t in vpc.get("Tags", [])
                         if t["Key"] == "Name"), vpc["VpcId"])
            vpcs[vpc["VpcId"]] = {
                "name": name, "cidr": vpc.get("CidrBlock", ""),
                "total_ips": cidr_total_ips(vpc.get("CidrBlock", ""))}
    return subnets, vpcs


def aggregate_alerts(subnets: List[Dict]) -> List[str]:
    alerts = []
    for s in subnets:
        if s["status"] == "EXHAUSTED":
            alerts.append(f"🔴 {s['name']} ({s['cidr']}): SIN IPs "
                          "disponibles — los pods/nodos no pueden "
                          "asignar IP")
        elif s["status"] == "CRITICAL":
            alerts.append(f"🟠 {s['name']} ({s['cidr']}): "
                          f"{s['used_pct']}% usado, "
                          f"{s['available_ips']} IPs libres")
        elif s["status"] == "WARNING":
            alerts.append(f"🟡 {s['name']} ({s['cidr']}): "
                          f"{s['used_pct']}% usado")
    return alerts


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

STATUS_STYLE = {"OK": "green", "WARNING": "yellow",
                "CRITICAL": "red", "EXHAUSTED": "red bold",
                "UNKNOWN": "dim"}


def get_args():
    parser = argparse.ArgumentParser(
        description="Analiza capacidad de IPs en VPCs/subnets AWS")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--vpc", default="",
                        help="Filtrar por VPC ID")
    parser.add_argument("--warn-threshold", type=float,
                        default=WARN_THRESHOLD)
    parser.add_argument("--critical-threshold", type=float,
                        default=CRITICAL_THRESHOLD)
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()
    global WARN_THRESHOLD, CRITICAL_THRESHOLD
    WARN_THRESHOLD = args.warn_threshold
    CRITICAL_THRESHOLD = args.critical_threshold

    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)

    try:
        session = boto3.Session(profile_name=args.profile,
                                region_name=args.region)
        ec2 = session.client("ec2")
        subnets, vpcs = collect_subnets(ec2, args.vpc)
    except Exception as e:
        _print(f"❌ Error consultando AWS: {e}", "red")
        sys.exit(1)

    if not subnets:
        _print("⚠ Sin subnets encontradas", "yellow")
        sys.exit(0)

    if console:
        table = Table(title="Capacidad de IPs por Subnet",
                      header_style="bold cyan")
        for col in ["VPC", "Subnet", "AZ", "CIDR", "Total",
                    "Libres", "Usado %", "Estado"]:
            table.add_column(col)
        for s in sorted(subnets, key=lambda x: -x["used_pct"]):
            vpc = vpcs.get(s["vpc_id"], {})
            color = STATUS_STYLE.get(s["status"], "")
            table.add_row(
                vpc.get("name", s["vpc_id"])[:25],
                s["name"][:30], s["az"], s["cidr"],
                str(s["total_ips"]), str(s["available_ips"]),
                f"{s['used_pct']}%",
                f"[{color}]{s['status']}[/{color}]")
        console.print(table)

        alerts = aggregate_alerts(subnets)
        if alerts:
            console.print(Panel("\n".join(alerts),
                                title="⚠️ Alertas de capacidad",
                                border_style="yellow"))
    else:
        for s in subnets:
            print(f"{s['name']} {s['cidr']}: {s['available_ips']}/"
                  f"{s['usable_ips']} libres ({s['used_pct']}%) "
                  f"[{s['status']}]")

    critical = len([s for s in subnets
                    if s["status"] in ("CRITICAL", "EXHAUSTED")])
    warn = len([s for s in subnets if s["status"] == "WARNING"])
    _print(f"\nSubnets: {len(subnets)} | "
           f"⚠️ {warn} | 🔴 {critical}",
           "red" if critical else ("yellow" if warn else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"vpc_ip_capacity_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region,
                "thresholds": {"warn": WARN_THRESHOLD,
                               "critical": CRITICAL_THRESHOLD},
                "vpcs": vpcs, "subnets": subnets,
            }, indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "vpc_id", "subnet_id", "name", "az", "cidr",
                    "total_ips", "available_ips", "used_pct", "status"])
                w.writeheader()
                for s in subnets:
                    w.writerow({k: s[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
