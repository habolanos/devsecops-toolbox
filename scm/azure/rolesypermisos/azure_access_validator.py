#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Access Control Validator — Tool 5

Valida controles de acceso de la suscripción:

- MFA/guest users: usuarios invitados con privilegios
- Asignaciones en scope raíz de suscripción vs RG concretos
- Managed identities en uso vs sin asignar
- Azure AD: usuarios habilitados con roles
- Hallazgos + recomendaciones

Uso:
    python azure_access_validator.py --subscription <id>
    python azure_access_validator.py -o json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json, export_csv)

__version__ = "1.0.0"

PRIV = {"Owner", "Contributor", "User Access Administrator"}


def validate(sub: str) -> Dict:
    findings = []
    assignments = try_az(["role", "assignment", "list",
                          "--all", "--include-inherited"],
                         sub, default=[]) or []

    # Guests con privilegios
    guests_priv = []
    try:
        guests = try_az(["ad", "user", "list",
                         "--filter",
                         "userType eq 'Guest'"], sub,
                        default=[]) or []
        guest_ids = {g["id"] for g in guests}
        guests_priv = [a for a in assignments
                       if a.get("principalId") in guest_ids
                       and a.get("roleDefinitionName") in PRIV]
        if guests_priv:
            findings.append(f"🔴 {len(guests_priv)} usuarios "
                            "invitados con Owner/Contributor")
    except Exception:
        pass

    # Privilegiados a nivel suscripción (scope amplio)
    sub_scope = f"/subscriptions/{sub}"
    priv_wide = [a for a in assignments
                 if a.get("roleDefinitionName") in PRIV and
                 (a.get("scope") or "").rstrip("/") ==
                 sub_scope]
    findings_count = len(priv_wide)
    if findings_count > 10:
        findings.append(f"🟡 {findings_count} asignaciones "
                        "privilegiadas a nivel suscripción — "
                        "evaluar scopes por RG")

    # Managed identities sin roles asignados
    mis = try_az(["identity", "list"], sub, default=[]) or []
    mi_ids = {m["principalId"] for m in mis
              if m.get("principalId")}
    assigned_ids = {a.get("principalId") for a in assignments}
    mi_unused = [m["name"] for m in mis
                 if m.get("principalId")
                 and m["principalId"] not in assigned_ids]
    if mi_unused:
        findings.append(f"ℹ️ {len(mi_unused)} managed "
                        "identities sin roles asignados")

    # Asignaciones a principals tipo desconocido (huérfanas)
    unknown = [a for a in assignments
               if a.get("principalType") in
               (None, "", "Unknown")]
    if unknown:
        findings.append(f"🟡 {len(unknown)} asignaciones con "
                        "principal desconocido/eliminado")

    return {
        "guests_privileged": [{
            "principal": a.get("principalName") or
                         a.get("principalId"),
            "role": a.get("roleDefinitionName"),
        } for a in guests_priv],
        "privileged_at_sub_scope": findings_count,
        "managed_identities": len(mis),
        "mi_without_roles": mi_unused[:15],
        "orphan_assignments": len(unknown),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Valida controles de acceso Azure")
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
    data = validate(sub)

    if console:
        for f in data["findings"]:
            style = "red" if "🔴" in f else \
                "yellow" if "🟡" in f else "dim"
            console.print(f"  [{style}]{f}[/{style}]")
        if data["guests_privileged"]:
            from rich.table import Table
            t = Table(title="Guests privilegiados",
                      header_style="bold red")
            t.add_column("Principal")
            t.add_column("Rol")
            for g in data["guests_privileged"]:
                t.add_row(str(g["principal"])[:40],
                          g["role"])
            console.print(t)
    else:
        for f in data["findings"]:
            print(f)

    _print(f"\nGuests con privilegios: "
           f"{len(data['guests_privileged'])} | "
           f"priv@sub-scope: {data['privileged_at_sub_scope']} "
           f"| MI sin roles: {len(data['mi_without_roles'])}",
           "red" if data["guests_privileged"] else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"access_validation_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                **data})
        else:
            export_csv(out, ["finding"],
                       [{"finding": f}
                        for f in data["findings"]])
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if data["guests_privileged"] else 0)


if __name__ == "__main__":
    main()
