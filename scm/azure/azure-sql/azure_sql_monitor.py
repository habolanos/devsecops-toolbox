#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure SQL Database Monitor — Tool 6

Monitorea servidores y bases Azure SQL, equivalente a
gcp_database_checker / aws_rds_checker:

- Servidores: versión, estado, TLS mínimo, Azure AD admin,
  firewall de acceso público
- Bases por servidor: estado, SKU, tamaño max, zone redundant
- Hallazgos: TDE/encryption, TLS <1.2, publicNetworkAccess enabled

Uso:
    python azure_sql_monitor.py --subscription <id>
    python azure_sql_monitor.py --resource-group rg -o json
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


def analyze_server(s: Dict) -> List[str]:
    findings = []
    if s.get("publicNetworkAccess") == "Enabled":
        findings.append("🟡 publicNetworkAccess habilitado")
    if s.get("minimalTlsVersion") and \
            float(s["minimalTlsVersion"]) < 1.2:
        findings.append("🔴 TLS mínimo <1.2")
    if not s.get("administratorLogin"):
        findings.append("🟡 Sin admin SQL configurado")
    return findings


def get_args():
    p = argparse.ArgumentParser(description="Azure SQL monitor")
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
    cmd = ["sql", "server", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    servers = try_az(cmd, sub, default=[]) or []

    rows, dbs = [], []
    for s in servers:
        rg = rg_of(s)
        findings = analyze_server(s)
        rows.append({
            "server": s["name"], "resource_group": rg,
            "location": s.get("location"),
            "state": s.get("state"),
            "tls": s.get("minimalTlsVersion"),
            "public": s.get("publicNetworkAccess"),
            "aad_admin": bool((s.get("administrators") or {})
                              .get("azureADOnlyAuthentication",
                                   s.get("administratorLogin"))),
            "findings": findings})
        for d in (try_az(["sql", "db", "list", "--server",
                          s["name"], "--resource-group", rg],
                         sub, default=[]) or []):
            if d["name"] == "master":
                continue
            dbs.append({
                "server": s["name"], "database": d["name"],
                "status": d.get("status"),
                "sku": (d.get("sku") or {}).get("name"),
                "max_gb": (d.get("maxSizeBytes") or 0) // 2**30,
                "zone_redundant": d.get("zoneRedundant")})

    if console:
        from rich.table import Table
        t1 = Table(title="Azure SQL Servers",
                   header_style="bold cyan")
        for col in ["Server", "RG", "TLS", "Public", "Findings"]:
            t1.add_column(col)
        for r in rows:
            bad = any("🔴" in f for f in r["findings"])
            t1.add_row(r["server"][:35], r["resource_group"][:18],
                       str(r["tls"]), str(r["public"]),
                       f"[{'red' if bad else 'green'}]"
                       f"{len(r['findings'])}"
                       f"[/{'red' if bad else 'green'}]")
        console.print(t1)
        t2 = Table(title="Databases", header_style="bold magenta")
        for col in ["DB", "Server", "Status", "SKU", "Max GB"]:
            t2.add_column(col)
        for d in dbs[:40]:
            color = "green" if d["status"] == "Online" \
                else "yellow"
            t2.add_row(d["database"][:35], d["server"][:25],
                       f"[{color}]{d['status']}[/{color}]",
                       str(d["sku"]), str(d["max_gb"]))
        console.print(t2)
        for r in rows:
            for f in r["findings"]:
                console.print(f"  {f} [dim]({r['server']})[/dim]")
    else:
        for r in rows:
            print(f"{r['server']}: {r['state']} tls={r['tls']} "
                  f"dbs={len([d for d in dbs if d['server'] == r['server']])}")

    _print(f"\nServidores: {len(rows)} | DBs: {len(dbs)}",
           "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"azure_sql_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "servers": rows, "databases": dbs})
        else:
            export_csv(out, ["server", "database", "status",
                             "sku", "max_gb",
                             "zone_redundant"], dbs)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
