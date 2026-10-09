#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Roles & Permissions Audit — Tool 3

Auditoría de RBAC en la suscripción, equivalente a
gcp_iam_roles_report / aws_iam_checker:

- Asignaciones por rol (Owner/Contributor/Reader/custom)
- Principales con Owner/Contributor (privilegio alto)
- Asignaciones a Service Principals vs Users vs Groups
- Custom roles definidos
- Classic administrators (deprecado)
- Hallazgos: muchos Owners, asignaciones directas a usuarios
  (mejor vía grupos)

Uso:
    python azure_roles_audit.py --subscription <id>
    python azure_roles_audit.py -o csv
"""

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json, export_csv)

__version__ = "1.0.0"

PRIVILEGED_ROLES = {"Owner", "Contributor",
                    "User Access Administrator"}
MAX_OWNERS = 3


def collect(sub: str) -> Dict:
    assignments = try_az(
        ["role", "assignment", "list", "--all",
         "--include-inherited"], sub, default=[]) or []
    custom_roles = try_az(["role", "definition", "list",
                           "--custom-role-only", "true"],
                          sub, default=[]) or []
    classic = try_az(["role", "assignment", "list",
                      "--include-classic-administrators",
                      "true"], sub, default=[]) or []

    by_role = Counter(a.get("roleDefinitionName", "?")
                      for a in assignments)
    by_type = Counter(a.get("principalType", "?")
                      for a in assignments)
    privileged = [a for a in assignments
                  if a.get("roleDefinitionName") in
                  PRIVILEGED_ROLES]
    owners = [a for a in assignments
              if a.get("roleDefinitionName") == "Owner"]

    findings = []
    if len(owners) > MAX_OWNERS:
        findings.append(
            f"🟡 {len(owners)} Owners (recomendado ≤"
            f"{MAX_OWNERS})")
    user_direct = [a for a in assignments
                   if a.get("principalType") == "User"]
    if len(assignments) and \
            len(user_direct) / len(assignments) > 0.5:
        findings.append("🟡 >50% de asignaciones son directas "
                        "a usuarios — preferir grupos")
    if classic:
        findings.append("🟡 Classic administrators "
                        "presentes (deprecado)")
    return {
        "total_assignments": len(assignments),
        "by_role": dict(by_role.most_common(15)),
        "by_principal_type": dict(by_type),
        "privileged": [{
            "principal": a.get("principalName") or
                         a.get("principalId"),
            "type": a.get("principalType"),
            "role": a.get("roleDefinitionName"),
            "scope": (a.get("scope") or "")[:80],
        } for a in privileged],
        "custom_roles": [r.get("roleName")
                         for r in custom_roles],
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Auditoría RBAC de la suscripción")
    p.add_argument("--subscription", default="")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    data = collect(sub)

    if console:
        from rich.table import Table
        from rich.panel import Panel
        console.print(Panel.fit(
            f"Asignaciones: [bold]"
            f"{data['total_assignments']}[/bold] | "
            f"Privilegiadas: {len(data['privileged'])} | "
            f"Custom roles: {len(data['custom_roles'])}",
            title="🔐 Azure RBAC Audit"))
        table = Table(header_style="bold cyan")
        for col in ["Rol", "Asignaciones"]:
            table.add_column(col)
        for r, c in data["by_role"].items():
            color = "red" if r in PRIVILEGED_ROLES else "dim"
            table.add_row(f"[{color}]{r}[/{color}]", str(c))
        console.print(table)
        t2 = Table(title="Privilegiados",
                   header_style="bold red")
        for col in ["Principal", "Tipo", "Rol", "Scope"]:
            t2.add_column(col)
        for p in data["privileged"][:25]:
            t2.add_row(str(p["principal"])[:35], p["type"],
                       p["role"], p["scope"])
        console.print(t2)
        for f in data["findings"]:
            console.print(f"  {f}")
    else:
        print(f"assignments={data['total_assignments']} "
              f"privileged={len(data['privileged'])}")
        for f in data["findings"]:
            print(f)

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"rbac_audit_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                **data})
        else:
            export_csv(out, ["principal", "type", "role",
                             "scope"], data["privileged"])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
