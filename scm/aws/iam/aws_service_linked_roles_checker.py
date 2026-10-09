#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS IAM Service Linked Roles Checker — Tool 37

Analiza los Service Linked Roles (SLRs) de la cuenta:

- Lista todos los roles en /aws-service-role/
- Los contrasta con los servicios realmente en uso (EC2, RDS, EKS,
  ELB, Lambda, ECS…) → SLRs esperados vs presentes
- SLRs huérfanos: servicio sin recursos activos pero con rol
- Servicios con recursos pero sin SLR (posible fallo de permisos)
- Edad del rol (creado recientemente vs antiguo)

Equivalente a GCP Tool: Service Account Checker
(service-account/gcp_service_account_checker.py).

Uso:
    python aws_service_linked_roles_checker.py --profile p \\
        --region us-east-1 -o json
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

SLR_PREFIX = "/aws-service-role/"

# Servicio AWS → detector de "servicio en uso" (vía boto3)
SERVICE_PROBES = {
    "elasticloadbalancing.amazonaws.com":
        lambda s: bool(s.client("elbv2").describe_load_balancers()
                       .get("LoadBalancers")),
    "rds.amazonaws.com":
        lambda s: bool(s.client("rds").describe_db_instances()
                       .get("DBInstances")),
    "eks.amazonaws.com":
        lambda s: bool(s.client("eks").list_clusters()
                       .get("clusters")),
    "ec2.amazonaws.com":
        lambda s: bool(s.client("ec2").describe_instances()
                       .get("Reservations")),
    "ecs.amazonaws.com":
        lambda s: bool(s.client("ecs").list_clusters()
                       .get("clusterArns")),
    "autoscaling.amazonaws.com":
        lambda s: bool(s.client("autoscaling")
                       .describe_auto_scaling_groups()
                       .get("AutoScalingGroups")),
    "lambda.amazonaws.com":
        lambda s: bool(s.client("lambda").list_functions()
                       .get("Functions")),
}


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


def service_from_slr(role: Dict) -> str:
    """Extrae el servicio AWS de un SLR por su ARN/description."""
    desc = role.get("Description", "")
    # "Service Linked Role for ..." no siempre lleva el dominio
    path_service = role.get("Path", "").replace(SLR_PREFIX, "")
    return path_service.rstrip("/")


def list_slrs(iam) -> List[Dict]:
    roles = []
    paginator = iam.get_paginator("list_roles")
    for page in paginator.paginate(PathPrefix=SLR_PREFIX):
        for role in page.get("Roles", []):
            roles.append({
                "name": role["RoleName"],
                "arn": role["Arn"],
                "service": service_from_slr(role),
                "created": str(role.get("CreateDate", "")),
                "description": role.get("Description", "")[:80],
            })
    return roles


def analyze_slrs(session, roles: List[Dict]) -> Dict:
    """Clasifica SLRs: en-uso vs huérfano vs servicio-sin-SLR."""
    in_use, orphaned = [], []
    for role in roles:
        svc_domain = role["service"]
        probe = SERVICE_PROBES.get(svc_domain)
        try:
            active = probe(session) if probe else None
        except Exception:
            active = None
        entry = {**role, "service_in_use": active}
        if active is False:
            orphaned.append(entry)
        else:
            in_use.append(entry)

    # Servicios con recursos pero sin SLR (informativo)
    present = {r["service"] for r in roles}
    missing = []
    for svc, probe in SERVICE_PROBES.items():
        if svc in present:
            continue
        try:
            if probe(session):
                missing.append({"service": svc,
                                "note": "recursos activos sin SLR "
                                        "(podría usar rol custom)"})
        except Exception:
            pass
    return {"in_use": in_use, "orphaned": orphaned,
            "missing_slr": missing}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Analiza Service Linked Roles de la cuenta AWS")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
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
        iam = session.client("iam")
        roles = list_slrs(iam)
        analysis = analyze_slrs(session, roles)
    except Exception as e:
        _print(f"❌ Error: {e}", "red")
        sys.exit(1)

    if console:
        table = Table(title="Service Linked Roles",
                      header_style="bold cyan")
        for col in ["Rol", "Servicio", "Creado", "Estado"]:
            table.add_column(col)
        for r in analysis["in_use"]:
            estado = ("[green]en uso[/green]"
                      if r["service_in_use"] else "[dim]—[/dim]")
            table.add_row(r["name"], r["service"],
                          r["created"][:10], estado)
        for r in analysis["orphaned"]:
            table.add_row(r["name"], r["service"],
                          r["created"][:10],
                          "[yellow]huérfano[/yellow]")
        console.print(table)
        for m in analysis["missing_slr"]:
            console.print(f"  [yellow]⚠ {m['service']}:[/yellow] "
                          f"[dim]{m['note']}[/dim]")
    else:
        for r in roles:
            print(f"{r['name']}: {r['service']} "
                  f"(orphan={r in analysis['orphaned']})")

    _print(f"\nSLRs: {len(roles)} | en uso: "
           f"{len(analysis['in_use'])} | huérfanos: "
           f"{len(analysis['orphaned'])}",
           "yellow" if analysis["orphaned"] else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"slr_check_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "profile": args.profile,
                "total_slrs": len(roles), **analysis},
                indent=2, default=str), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["role", "service", "created",
                            "service_in_use"])
                for r in roles:
                    w.writerow([r["name"], r["service"],
                                r["created"],
                                r.get("service_in_use")])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
