#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure App Service Monitor — Tool 19

Inventario y estado de App Services / Function Apps:

- Apps: estado (Running/Stopped), plan, SKU, runtime,
  httpsOnly, kind (functionapp/api/linux)
- Hallazgos: apps detenidas, httpOnly=false, plan sin uso

Uso:
    python appservice_monitor.py --subscription <id>
    python appservice_monitor.py --resource-group rg -o json
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


def collect(sub: str, rg: str = "") -> Dict:
    cmd = ["webapp", "list"]
    if rg:
        cmd += ["--resource-group", rg]
    webapps = try_az(cmd, sub, default=[]) or []
    funcs = try_az(["functionapp", "list"] +
                   (["--resource-group", rg] if rg else []),
                   sub, default=[]) or []
    plans = try_az(["appservice", "plan", "list"] +
                   (["--resource-group", rg] if rg else []),
                   sub, default=[]) or []
    return {"webapps": webapps, "functions": funcs,
            "plans": plans}


def normalize(app: Dict, kind_hint: str = "") -> Dict:
    kind = app.get("kind", kind_hint)
    findings = []
    if app.get("state") not in ("Running", None):
        findings.append(f"🟡 Estado: {app.get('state')}")
    if not app.get("httpsOnly"):
        findings.append("🟡 httpsOnly=false — HTTP permitido")
    return {
        "name": app["name"], "resource_group": rg_of(app),
        "kind": kind, "state": app.get("state"),
        "host": app.get("defaultHostName"),
        "https_only": app.get("httpsOnly"),
        "plan": (app.get("appServicePlanId") or
                 app.get("serverFarmId") or "").rsplit(
                     "/", 1)[-1],
        "location": app.get("location"),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Monitoreo de App Services")
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
    data = collect(sub, args.resource_group)
    apps = [normalize(a, "webapp") for a in data["webapps"]]
    apps += [normalize(a, "functionapp")
             for a in data["functions"]]
    stopped = [a for a in apps if a["state"] != "Running"]
    no_https = [a for a in apps if not a["https_only"]]

    if console:
        from rich.table import Table
        table = Table(title="App Services / Functions",
                      header_style="bold cyan")
        for col in ["App", "Kind", "Plan", "Estado",
                    "HTTPS", "Findings"]:
            table.add_column(col)
        for a in apps[:60]:
            state_color = "green" if a["state"] == "Running" \
                else "red"
            table.add_row(
                a["name"][:35], a["kind"][:15],
                a["plan"][:20],
                f"[{state_color}]{a['state']}"
                f"[/{state_color}]",
                "[green]✓[/green]" if a["https_only"]
                else "[red]✗[/red]",
                str(len(a["findings"])))
        console.print(table)
        for a in apps:
            for f in a["findings"]:
                console.print(f"  {f} [dim]({a['name']})"
                              f"[/dim]")
    else:
        for a in apps:
            print(f"{a['name']}: {a['state']} https={a['https_only']}")

    _print(f"\nApps: {len(apps)} | detenidas: {len(stopped)} "
           f"| sin HTTPS-only: {len(no_https)}",
           "red" if no_https else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"appservices_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "apps": apps})
        else:
            rows = [{k: a[k] for k in
                     ("name", "resource_group", "kind",
                      "state", "plan", "https_only")}
                    | {"findings": "; ".join(a["findings"])}
                    for a in apps]
            export_csv(out, list(rows[0]) if rows else
                       ["name"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
