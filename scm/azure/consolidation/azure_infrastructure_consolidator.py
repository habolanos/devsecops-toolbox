#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Infrastructure Consolidator — Tool 35

Consolida Application Gateways, App Services y Azure Functions
con mapeo de relaciones, equivalente a
gcp_infrastructure_consolidator /
aws_infrastructure_consolidator:

- AppGW → listeners → routing rules → backend pools → backends
- Backends mapeados a App Services / Functions (por hostname)
- Detección: backends huérfanos (app no existe), apps sin
  gateway, pools vacíos
- Vistas: summary/mapping/orphans

Uso:
    python azure_infrastructure_consolidator.py \\
        --subscription <id>
    python azure_infrastructure_consolidator.py --view orphans
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"


def backend_addresses(pool: Dict) -> List[str]:
    out = []
    for b in pool.get("backendAddresses", []):
        out.append(b.get("fqdn") or b.get("ipAddress") or "?")
    return out


def consolidate(sub: str) -> Dict:
    gws = try_az(["network", "application-gateway", "list"],
                 sub, default=[]) or []
    webapps = try_az(["webapp", "list"], sub,
                     default=[]) or []
    funcs = try_az(["functionapp", "list"], sub,
                   default=[]) or []
    app_hosts = {a.get("defaultHostName"): a["name"]
                 for a in webapps + funcs
                 if a.get("defaultHostName")}

    mappings, orphans = [], []
    covered_apps: Set[str] = set()
    for gw in gws:
        gw_name = gw["name"]
        pools = {p["name"]: p for p in
                 gw.get("backendAddressPools", [])}
        for pool_name, pool in pools.items():
            addrs = backend_addresses(pool)
            if not addrs:
                orphans.append({
                    "type": "empty_pool", "gateway": gw_name,
                    "detail": f"pool {pool_name} sin backends"})
            for addr in addrs:
                app = app_hosts.get(addr)
                if app:
                    covered_apps.add(app)
                    mappings.append({
                        "gateway": gw_name,
                        "pool": pool_name,
                        "backend": addr, "app": app,
                        "status": "matched"})
                else:
                    mappings.append({
                        "gateway": gw_name,
                        "pool": pool_name,
                        "backend": addr, "app": None,
                        "status": "external_or_missing"})
                    orphans.append({
                        "type": "unknown_backend",
                        "gateway": gw_name,
                        "detail": f"{addr} no es app de la "
                                  "suscripción"})
    exposed = covered_apps
    unexposed = [a["name"] for a in webapps + funcs
                 if a["name"] not in covered_apps and
                 a.get("defaultHostName")]
    return {
        "gateways": len(gws), "apps": len(webapps) + len(funcs),
        "mappings": mappings, "orphans": orphans,
        "exposed_apps": sorted(exposed),
        "unexposed_apps": sorted(unexposed),
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Consolida AppGW↔AppService/Functions")
    p.add_argument("--subscription", default="")
    p.add_argument("--view",
                   choices=["summary", "mapping", "orphans"],
                   default="summary")
    p.add_argument("--output", choices=["json", "csv"],
                   default="")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--timezone", default="")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    data = consolidate(sub)

    if console:
        from rich.table import Table
        if args.view in ("summary", "mapping"):
            t = Table(title="Gateway → Backend → App",
                      header_style="bold cyan")
            for col in ["Gateway", "Pool", "Backend", "App"]:
                t.add_column(col)
            for m in data["mappings"]:
                color = "green" if m["status"] == "matched" \
                    else "yellow"
                t.add_row(
                    m["gateway"][:25], m["pool"][:20],
                    m["backend"][:40],
                    f"[{color}]{m['app'] or '✗'}[/{color}]")
            console.print(t)
        if args.view in ("summary", "orphans"):
            for o in data["orphans"]:
                console.print(f"  [yellow]⚠ {o['type']}:[/"
                              f"yellow] {o['detail']} "
                              f"[dim]({o['gateway']})[/dim]")
            if data["unexposed_apps"]:
                console.print(
                    f"[dim]Apps sin gateway: "
                    f"{len(data['unexposed_apps'])}[/dim]")
    else:
        for m in data["mappings"]:
            print(f"{m['gateway']}→{m['backend']}→{m['app']}")

    _print(f"\nGateways: {data['gateways']} | apps: "
           f"{data['apps']} | mappings: "
           f"{len(data['mappings'])} | huérfanos: "
           f"{len(data['orphans'])}",
           "yellow" if data["orphans"] else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"infra_consolidated_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                **data})
        else:
            export_csv(out, ["gateway", "pool", "backend",
                             "app", "status"],
                       data["mappings"])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
