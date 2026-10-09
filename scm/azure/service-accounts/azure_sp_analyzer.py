#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Service Principals Analyzer — Tool 4

Análisis de service principals, equivalente a
gcp_service_account_checker:

- Inventario de SPs (displayName, appId, tipo)
- Credenciales (password/key credentials): expiración y edad
- SPs sin credenciales o con credenciales vencidas/próximas
- SPs con Owner/Contributor sobre la suscripción
- Hallazgos con severidad + export

Uso:
    python azure_sp_analyzer.py --subscription <id>
    python azure_sp_analyzer.py --days 30 -o json
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json, export_csv)

__version__ = "1.0.0"


def _days_to(iso: str) -> int:
    if not iso:
        return 9999
    try:
        dt = datetime.fromisoformat(
            iso.replace("Z", "+00:00"))
        return (dt - datetime.now(timezone.utc)).days
    except Exception:
        return 9999


def analyze_sp(sp: Dict, warn_days: int) -> Dict:
    findings = []
    creds = list(sp.get("passwordCredentials", []) or []) + \
        list(sp.get("keyCredentials", []) or [])
    expired, expiring = 0, 0
    for c in creds:
        days = _days_to(c.get("endDateTime") or
                        c.get("endDate"))
        if days < 0:
            expired += 1
        elif days <= warn_days:
            expiring += 1
    if expired:
        findings.append(f"🔴 {expired} credenciales vencidas")
    if expiring:
        findings.append(f"🟡 {expiring} credenciales vencen "
                        f"en ≤{warn_days}d")
    if not creds:
        findings.append("ℹ️ Sin credenciales (puede ser "
                        "managed identity o federated)")
    return {
        "name": sp.get("displayName"),
        "app_id": sp.get("appId"),
        "type": sp.get("servicePrincipalType"),
        "credentials": len(creds),
        "expired": expired, "expiring": expiring,
        "account_enabled": sp.get("accountEnabled"),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Analiza service principals Azure")
    p.add_argument("--subscription", default="")
    p.add_argument("--days", type=int, default=30,
                   help="Umbral días para alertar expiración")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    sps = try_az(["ad", "sp", "list", "--all"], sub,
                 default=[]) or []
    rows = [analyze_sp(s, args.days) for s in sps]

    # SPs con roles privilegiados
    assignments = try_az(
        ["role", "assignment", "list", "--all",
         "--query", "[?roleDefinitionName=='Owner' || "
         "roleDefinitionName=='Contributor']"], sub,
        default=[]) or []
    priv_ids = {a.get("principalId") for a in assignments}
    for r in rows:
        if r["app_id"] in priv_ids:
            r["privileged"] = True
        else:
            r["privileged"] = False

    expired = [r for r in rows if r["expired"]]
    expiring = [r for r in rows if r["expiring"]]

    if console:
        from rich.table import Table
        table = Table(title="Service Principals",
                      header_style="bold cyan")
        for col in ["SP", "Tipo", "Creds", "Expira",
                    "Priv", "Findings"]:
            table.add_column(col)
        for r in sorted(rows, key=lambda x: -x["expired"]
                        - x["expiring"])[:50]:
            color = "red" if r["expired"] else \
                "yellow" if r["expiring"] else "green"
            table.add_row(
                (r["name"] or "?")[:35],
                str(r["type"] or "?")[:15],
                str(r["credentials"]),
                f"[{color}]{r['expired']}v/"
                f"{r['expiring']}p[/{color}]",
                "[red]✓[/red]" if r["privileged"] else "",
                str(len(r["findings"])))
        console.print(table)
    else:
        for r in rows:
            print(f"{r['name']}: creds={r['credentials']} "
                  f"expired={r['expired']}")

    _print(f"\nSPs: {len(rows)} | vencidas: {len(expired)} "
           f"| próximas a vencer: {len(expiring)}",
           "red" if expired else
           ("yellow" if expiring else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"sp_analysis_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "service_principals": rows})
        else:
            export_csv(out, ["name", "app_id", "type",
                             "credentials", "expired",
                             "expiring", "privileged"],
                       [{**r, "findings":
                         "; ".join(r["findings"])}
                        for r in rows])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
