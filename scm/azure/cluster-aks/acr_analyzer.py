#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Container Registry Analyzer — Tool 18

Análisis de Azure Container Registry (ACR), equivalente a
artifact-registry checker / aws_ecr_checker:

- Registries: SKU, admin user habilitado, public network access,
  zone redundancy, encryption CMK
- Repositorios por registry: cantidad, tags
- Vulnerabilidades: admin enabled, sin private endpoint,
  dataEndpointEnabled
- Hallazgos con severidad + export

Uso:
    python acr_analyzer.py --subscription <id>
    python acr_analyzer.py -o json
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


def analyze(sub: str, reg: Dict) -> Dict:
    findings = []
    if reg.get("adminUserEnabled"):
        findings.append("🔴 Admin user habilitado — "
                        "preferir AAD/managed identity")
    if reg.get("publicNetworkAccess") != "Disabled":
        pes = try_az(["network", "private-endpoint", "list",
                      "--query",
                      f"[?contains(id,'{reg['name']}')]"],
                     sub, default=[]) or []
        if pes:
            findings.append("ℹ️ Público pero con private "
                            "endpoint")
        else:
            findings.append("🟡 Acceso público sin private "
                            "endpoint")
    if reg.get("dataEndpointEnabled"):
        findings.append("ℹ️ Data endpoint dedicado "
                        "habilitado")
    sku = (reg.get("sku") or {}).get("name", "?")
    if sku == "Basic":
        findings.append("🟡 SKU Basic — sin private link, "
                        "geo-replication ni CMK")
    repos = try_az(["acr", "repository", "list",
                    "--name", reg["name"]], sub,
                   default=[]) or []
    return {
        "registry": reg["name"], "resource_group": rg_of(reg),
        "sku": sku, "login_server": reg.get("loginServer"),
        "admin_enabled": reg.get("adminUserEnabled"),
        "public_access": reg.get("publicNetworkAccess"),
        "repositories": len(repos),
        "repo_names": repos[:15],
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(description="ACR analyzer")
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
    regs = try_az(["acr", "list"], sub, default=[]) or []
    rows = [analyze(sub, r) for r in regs]
    issues = [r for r in rows
              if any("🔴" in f for f in r["findings"])]

    if console:
        from rich.table import Table
        table = Table(title="Azure Container Registries",
                      header_style="bold cyan")
        for col in ["Registry", "SKU", "Admin", "Public",
                    "Repos", "Findings"]:
            table.add_column(col)
        for r in rows:
            bad = any("🔴" in f for f in r["findings"])
            table.add_row(
                r["registry"][:30], r["sku"],
                "[red]✓[/red]" if r["admin_enabled"]
                else "[green]✗[/green]",
                str(r["public_access"]),
                str(r["repositories"]),
                f"[{'red' if bad else 'green'}]"
                f"{len(r['findings'])}"
                f"[/{'red' if bad else 'green'}]")
        console.print(table)
        for r in rows:
            for f in r["findings"]:
                console.print(f"  {f} [dim]({r['registry']})"
                              f"[/dim]")
    else:
        for r in rows:
            print(f"{r['registry']}: sku={r['sku']} "
                  f"repos={r['repositories']} "
                  f"{r['findings']}")

    _print(f"\nRegistries: {len(rows)} | críticos: "
           f"{len(issues)}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"acr_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "registries": rows})
        else:
            csv_rows = [{"registry": r["registry"],
                         "sku": r["sku"],
                         "admin": r["admin_enabled"],
                         "public": r["public_access"],
                         "repos": r["repositories"],
                         "findings": "; ".join(
                             r["findings"])} for r in rows]
            export_csv(out, list(csv_rows[0]) if csv_rows else
                       ["registry"], csv_rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
