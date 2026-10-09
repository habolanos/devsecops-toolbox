#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS IAM Service Linked Roles Reporter — Tool 38

Reporte multi-cuenta de Service Linked Roles:

- Itera los profiles configurados (o --profiles p1,p2)
- Lista SLRs por cuenta con su servicio
- Matriz cuenta × rol: qué SLRs tiene cada cuenta, cuáles faltan
- Detecta cuentas sin SLRs estándar (EC2, ELB, RDS…)
- Export JSON/CSV a outcome/

Equivalente a GCP Tool: Service Account Multi-Project Reporter
(service-accounts/gcp_sa_multi_project_reporter.py).

Uso:
    python aws_service_linked_roles_reporter.py --profiles dev,qa,prod
    python aws_service_linked_roles_reporter.py   # todos los profiles
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

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

SLR_PREFIX = "/aws-service-role/"

# SLRs que toda cuenta activa debería tener si usa esos servicios
EXPECTED_SLRS = {
    "AWSServiceRoleForEC2": "ec2.amazonaws.com",
    "AWSServiceRoleForElasticLoadBalancing":
        "elasticloadbalancing.amazonaws.com",
    "AWSServiceRoleForRDS": "rds.amazonaws.com",
    "AWSServiceRoleForAutoScaling": "autoscaling.amazonaws.com",
    "AWSServiceRoleForAmazonEKS": "eks.amazonaws.com",
    "AWSServiceRoleForECS": "ecs.amazonaws.com",
    "AWSServiceRoleForElasticCache": "elasticache.amazonaws.com",
}


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Profiles y SLRs
# ═══════════════════════════════════════════════════════════════════════════════

def list_profiles() -> List[str]:
    """Profiles del shared config de AWS."""
    try:
        code, out, _ = _run(["aws", "configure", "list-profiles"])
        if code == 0 and out:
            return [p.strip() for p in out.splitlines() if p.strip()]
    except Exception:
        pass
    return ["default"]


def _run(cmd: List[str], timeout: int = 15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def account_slrs(profile: str) -> Dict:
    """SLRs + account ID de un profile."""
    session = boto3.Session(profile_name=profile)
    account_id = ""
    try:
        account_id = session.client("sts") \
            .get_caller_identity()["Account"]
    except Exception:
        pass
    iam = session.client("iam")
    roles = []
    for page in iam.get_paginator("list_roles").paginate(
            PathPrefix=SLR_PREFIX):
        for role in page.get("Roles", []):
            roles.append({"name": role["RoleName"],
                          "created": str(role.get("CreateDate", ""))})
    return {"account_id": account_id, "roles": roles,
            "role_names": {r["name"] for r in roles}}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Reporte multi-cuenta de Service Linked Roles")
    parser.add_argument("--profiles", "-p", default="",
                        help="CSV de profiles (vacío = todos los "
                             "configurados)")
    parser.add_argument("--profile", default="",
                        help="Profile único (alias del launcher)")
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)

    profiles = ([args.profile] if args.profile else
                (list_profiles() if args.profiles.strip().lower()
                 in ("", "all") else
                 [p.strip() for p in args.profiles.split(",")
                  if p.strip()]))

    accounts = {}
    for profile in profiles:
        try:
            accounts[profile] = account_slrs(profile)
            _print(f"  {profile}: {len(accounts[profile]['roles'])} "
                   f"SLRs (acct {accounts[profile]['account_id']})",
                   "dim")
        except Exception as e:
            accounts[profile] = {"account_id": "?", "roles": [],
                                 "role_names": set(), "error": str(e)}
            _print(f"  {profile}: ❌ {str(e)[:80]}", "red")

    # Matriz: rol × cuenta
    all_roles: Set[str] = set()
    for a in accounts.values():
        all_roles |= a["role_names"]

    # SLRs esperados faltantes por cuenta
    gaps = {}
    for profile, data in accounts.items():
        missing = [r for r in EXPECTED_SLRS
                   if r not in data["role_names"]]
        if missing:
            gaps[profile] = missing

    if console:
        table = Table(title="Matriz SLR × cuenta",
                      header_style="bold cyan")
        table.add_column("Rol")
        for p in accounts:
            table.add_column(p[:20])
        for role in sorted(all_roles):
            row = [role]
            for p in accounts:
                row.append("✅" if role in accounts[p]["role_names"]
                           else "—")
            table.add_row(*row)
        console.print(table)
        if gaps:
            console.print("[yellow]SLRs esperados faltantes:"
                          "[/yellow]")
            for p, missing in gaps.items():
                console.print(f"  {p}: {', '.join(missing)}")
    else:
        for role in sorted(all_roles):
            presence = {p: role in a["role_names"]
                        for p, a in accounts.items()}
            print(f"{role}: {presence}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"slr_report_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "accounts": {p: {
                    "account_id": a["account_id"],
                    "error": a.get("error"),
                    "slr_count": len(a["roles"]),
                    "roles": a["roles"],
                } for p, a in accounts.items()},
                "expected_missing": gaps,
            }, indent=2, default=str), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["role"] + list(accounts))
                for role in sorted(all_roles):
                    w.writerow([role] + [
                        "yes" if role in a["role_names"] else ""
                        for a in accounts.values()])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
