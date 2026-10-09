#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Resource Monitor — Tool 1

Visión general de los recursos de la suscripción, equivalente al
gcp_monitor: conteo por tipo y estado de los servicios clave:

- Recursos por tipo (VMs, App Service, SQL, AKS, Storage...)
- Power state de VMs (az vm list -d)
- Estado de App Services (running/stopped)
- Clusters AKS y su provisioning state
- Bases SQL por servidor
- Resumen ejecutivo + export JSON/CSV

Uso:
    python azure_monitor.py --subscription <id>
    python azure_monitor.py --resource-group rg-prod -o json
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


def collect(subscription: str, rg: str = "") -> Dict:
    res_args = ["resource", "list"]
    if rg:
        res_args += ["--resource-group", rg]
    resources = try_az(res_args, subscription, default=[]) or []

    by_type = Counter(r.get("type", "?").split("/")[-1]
                      for r in resources)
    by_location = Counter(r.get("location", "?")
                          for r in resources)
    by_rg = Counter(r.get("resourceGroup", "?")
                    for r in resources)

    # VMs con power state
    vms = try_az(["vm", "list", "-d",
                  "--query", "[].{name:name,rg:resourceGroup,"
                  "power:powerState,size:hardwareProfile.vmSize}"],
                 subscription, default=[]) or []
    vm_states = Counter(v.get("power", "?") for v in vms)

    # App Services
    webapps = try_az(["webapp", "list",
                      "--query", "[].{name:name,rg:resourceGroup,"
                      "state:state,host:defaultHostName}"],
                     subscription, default=[]) or []
    web_states = Counter(w.get("state", "?") for w in webapps)

    # AKS
    aks = try_az(["aks", "list",
                  "--query", "[].{name:name,rg:resourceGroup,"
                  "state:provisioningState,version:kubernetesVersion,"
                  "power:powerState.code}"],
                 subscription, default=[]) or []

    # SQL servers + DBs
    sql_servers = try_az(["sql", "server", "list"], subscription,
                         default=[]) or []
    sql_dbs = []
    for s in sql_servers:
        dbs = try_az(["sql", "db", "list", "--server",
                      s["name"], "--resource-group",
                      s.get("resourceGroup", "")], subscription,
                     default=[]) or []
        sql_dbs.extend([{"name": d["name"],
                         "server": s["name"],
                         "status": d.get("status")} for d in dbs])

    return {
        "total_resources": len(resources),
        "by_type": dict(by_type.most_common(15)),
        "by_location": dict(by_location.most_common(8)),
        "by_resource_group": dict(by_rg.most_common(10)),
        "vms": vms, "vm_states": dict(vm_states),
        "webapps": webapps, "web_states": dict(web_states),
        "aks_clusters": aks, "sql_databases": sql_dbs,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Monitoreo general de recursos Azure")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login (az login)",
               "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    if not sub:
        _print("❌ No se pudo resolver la suscripción", "red")
        sys.exit(1)
    _print(f"Subscription: {sub}", "dim")

    data = collect(sub, args.resource_group)

    if console:
        from rich.table import Table
        from rich.panel import Panel
        console.print(Panel.fit(
            f"Recursos: [bold]{data['total_resources']}[/bold] | "
            f"VMs: {len(data['vms'])} | "
            f"WebApps: {len(data['webapps'])} | "
            f"AKS: {len(data['aks_clusters'])} | "
            f"SQL DBs: {len(data['sql_databases'])}",
            title="☁️  Azure Monitor"))
        table = Table(header_style="bold cyan")
        for col in ["Tipo", "Count"]:
            table.add_column(col)
        for t, c in data["by_type"].items():
            table.add_row(t, str(c))
        console.print(table)
        if data["vm_states"]:
            console.print(
                f"[dim]VMs: {data['vm_states']}[/dim]")
        if data["aks_clusters"]:
            for c in data["aks_clusters"]:
                color = "green" if c.get("power") == "Running" \
                    else "red"
                console.print(
                    f"  ☸️  {c['name']} v{c.get('version')} "
                    f"[{color}]{c.get('power','?')}[/{color}]")
    else:
        print(f"resources={data['total_resources']} "
              f"vms={data['vm_states']} aks={len(data['aks_clusters'])}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"azure_monitor_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {"timestamp": datetime.utcnow()
                              .isoformat(), **data})
        else:
            export_csv(out, ["type", "count"],
                       [{"type": k, "count": v}
                        for k, v in data["by_type"].items()])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
