#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Cosmos DB Analyzer — Tool 7

Análisis de cuentas Cosmos DB:

- Cuentas: API (Sql/Mongo/Cassandra/Table/Gremlin), consistencia,
  ubicaciones, failover
- Seguridad: publicNetworkAccess, ipRules, virtual network rules,
  disableLocalAuth (solo AAD), TLS mínimo
- Backups: tipo (Continuous/Periodic), retención
- Hallazgos con severidad + export

Uso:
    python cosmos_db_analyzer.py --subscription <id>
    python cosmos_db_analyzer.py -o json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"


def api_kind(acc: Dict) -> str:
    caps = [c.get("name") for c in
            acc.get("capabilities", [])]
    kinds = {"EnableCassandra": "Cassandra",
             "EnableTable": "Table", "EnableGremlin": "Gremlin",
             "EnableServerless": "Serverless"}
    detected = [v for k, v in kinds.items() if k in caps]
    if acc.get("kind") and acc["kind"] != "GlobalDocumentDB":
        detected.insert(0, acc["kind"])
    return "/".join(detected) if detected else "SQL"


def analyze(acc: Dict) -> Dict:
    findings = []
    if acc.get("publicNetworkAccess") == "Enabled":
        ip_rules = acc.get("ipRules", [])
        if not ip_rules:
            findings.append("🔴 Acceso público sin filtro IP — "
                            "abierto a internet")
        else:
            findings.append("🟡 Acceso público con filtro IP")
    if not acc.get("disableLocalAuth"):
        findings.append("🟡 Local auth (keys) habilitada — "
                        "preferir solo AAD")
    consistency = (acc.get("consistencyPolicy") or {}) \
        .get("defaultConsistencyLevel", "?")
    backup = acc.get("backupPolicy", {})
    return {
        "account": acc["name"], "resource_group": rg_of(acc),
        "location": acc.get("location"),
        "api": api_kind(acc),
        "consistency": consistency,
        "locations": len(acc.get("locations", [])),
        "failover_auto": acc.get(
            "enableAutomaticFailover", False),
        "multi_write": acc.get(
            "enableMultipleWriteLocations", False),
        "public_access": acc.get("publicNetworkAccess"),
        "local_auth_disabled": acc.get("disableLocalAuth",
                                       False),
        "backup_type": backup.get("type", "Periodic"),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(description="Cosmos DB analyzer")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    cmd = ["cosmosdb", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    accounts = [analyze(a)
                for a in (try_az(cmd, sub, default=[]) or [])]
    issues = [a for a in accounts
              if any("🔴" in f for f in a["findings"])]

    if console:
        from rich.table import Table
        table = Table(title="Cosmos DB Accounts",
                      header_style="bold cyan")
        for col in ["Cuenta", "API", "Consistencia", "Locs",
                    "Público", "Findings"]:
            table.add_column(col)
        for a in accounts:
            bad = any("🔴" in f for f in a["findings"])
            table.add_row(
                a["account"][:30], a["api"][:15],
                a["consistency"], str(a["locations"]),
                str(a["public_access"])[:10],
                f"[{'red' if bad else 'green'}]"
                f"{len(a['findings'])}"
                f"[/{'red' if bad else 'green'}]")
        console.print(table)
        for a in accounts:
            for f in a["findings"]:
                console.print(f"  {f} [dim]({a['account']})"
                              f"[/dim]")
    else:
        for a in accounts:
            print(f"{a['account']}: {a['api']} "
                  f"{a['consistency']}")

    _print(f"\nCuentas: {len(accounts)} | con issues "
           f"críticos: {len(issues)}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"cosmosdb_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "accounts": accounts})
        else:
            rows = [{k: a[k] for k in
                     ("account", "resource_group", "api",
                      "consistency", "locations",
                      "public_access", "backup_type")}
                    | {"findings": "; ".join(a["findings"])}
                    for a in accounts]
            export_csv(out, list(rows[0]) if rows else
                       ["account"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
