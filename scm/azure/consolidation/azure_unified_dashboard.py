#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Unified Infrastructure Dashboard — Tool 25

Dashboard ejecutivo unificado de la suscripción, equivalente a
gcp_unified_infrastructure_dashboard /
aws_unified_infrastructure_dashboard:

- KPIs: recursos totales, VMs, App Services, AKS, SQL,
  Storage, Key Vaults
- Alertas consolidadas: recursos parados, sin HA, públicos
- Health score global
- Export HTML con gráficos Chart.js + JSON

Uso:
    python azure_unified_dashboard.py --subscription <id>
    python azure_unified_dashboard.py -o html
"""

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json)

__version__ = "1.0.0"


def collect(sub: str) -> Dict:
    """KPIs + alertas de toda la suscripción."""
    resources = try_az(["resource", "list"], sub,
                       default=[]) or []
    by_type = Counter(r["type"].split("/")[-1]
                      for r in resources)

    vms = try_az(["vm", "list", "-d",
                  "--query", "[].{n:name,p:powerState}"],
                 sub, default=[]) or []
    webapps = try_az(["webapp", "list",
                      "--query", "[].{n:name,s:state,"
                      "h:httpsOnly}"], sub, default=[]) or []
    aks = try_az(["aks", "list",
                  "--query", "[].{n:name,s:provisioningState,"
                  "p:powerState.code}"], sub, default=[]) or []
    vaults = try_az(["keyvault", "list"], sub,
                    default=[]) or []
    sql = try_az(["sql", "server", "list"], sub,
                 default=[]) or []
    nsgs = try_az(["network", "nsg", "list"], sub,
                  default=[]) or []

    alerts = []
    vm_stopped = len([v for v in vms
                      if v.get("p") == "VM deallocated"])
    if vm_stopped:
        alerts.append(f"{vm_stopped} VMs deallocated")
    web_stopped = len([w for w in webapps
                       if w.get("s") != "Running"])
    if web_stopped:
        alerts.append(f"{web_stopped} App Services detenidos")
    no_https = len([w for w in webapps if not w.get("h")])
    if no_https:
        alerts.append(f"{no_https} apps sin httpsOnly")
    aks_down = [a for a in aks if a.get("p") == "Stopped"]
    if aks_down:
        alerts.append(f"{len(aks_down)} clusters AKS "
                      "detenidos")
    sql_public = [s for s in sql
                  if s.get("publicNetworkAccess") ==
                  "Enabled"]
    if sql_public:
        alerts.append(f"{len(sql_public)} SQL servers "
                      "con acceso público")

    total = len(resources)
    problems = vm_stopped + web_stopped + no_https + \
        len(aks_down) + len(sql_public)
    health = max(0, 100 - problems * 5)

    return {
        "total_resources": total,
        "vms": {"total": len(vms), "stopped": vm_stopped},
        "webapps": {"total": len(webapps),
                    "stopped": web_stopped,
                    "no_https": no_https},
        "aks": {"total": len(aks),
                "stopped": len(aks_down)},
        "sql_servers": len(sql),
        "key_vaults": len(vaults),
        "nsgs": len(nsgs),
        "top_types": dict(by_type.most_common(10)),
        "alerts": alerts, "health_score": health,
    }


HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Azure Unified Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{font-family:system-ui;background:#0f1419;color:#eee;
margin:2em}}h1{{color:#58a6ff}}.grid{{display:grid;
grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
gap:1em}}.kpi{{background:#1c2128;border-radius:8px;padding:1em;
text-align:center}}.kpi b{{font-size:2em;color:#58a6ff;
display:block}}.card{{background:#1c2128;border-radius:8px;
padding:1em;margin:1em 0}}</style></head><body>
<h1>☁️ Azure Unified Dashboard</h1>
<p>Generado: {ts} | Health Score: <b>{score}</b></p>
<div class="grid">{kpis}</div>
<div class="card"><h2>Top recursos por tipo</h2>
<canvas id="t" width="800" height="340"></canvas></div>
<div class="card"><h2>Alertas</h2><pre>{alerts}</pre></div>
<script>new Chart(document.getElementById('t'),{{type:'bar',
data:{{labels:{labels},datasets:[{{data:{vals},
backgroundColor:'#58a6ff'}}]}},options:{{indexAxis:'y'}}}});
</script></body></html>"""


def get_args():
    p = argparse.ArgumentParser(
        description="Dashboard unificado Azure")
    p.add_argument("--subscription", default="")
    p.add_argument("-o", "--output",
                   choices=["html", "json"], default="html")
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
        from rich.panel import Panel
        console.print(Panel.fit(
            f"Health: [bold]{data['health_score']}[/bold] | "
            f"Recursos: {data['total_resources']} | "
            f"VMs: {data['vms']['total']} | "
            f"WebApps: {data['webapps']['total']} | "
            f"AKS: {data['aks']['total']} | "
            f"SQL: {data['sql_servers']} | "
            f"KV: {data['key_vaults']}",
            title="☁️ Azure Dashboard"))
        for a in data["alerts"]:
            console.print(f"  [yellow]⚠ {a}[/yellow]")
    else:
        print(f"health={data['health_score']} "
              f"alerts={len(data['alerts'])}")

    OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTCOME_DIR / f"azure_dashboard_{now_ts()}." \
                        f"{args.output}"
    if args.output == "json":
        export_json(out, {
            "timestamp": datetime.utcnow().isoformat(),
            **data})
    else:
        import json
        kpis = "".join(
            f"<div class='kpi'><b>{v}</b>{k}</div>" for k, v in [
                ("Recursos", data["total_resources"]),
                ("VMs", data["vms"]["total"]),
                ("WebApps", data["webapps"]["total"]),
                ("AKS", data["aks"]["total"]),
                ("SQL", data["sql_servers"]),
                ("KeyVault", data["key_vaults"]),
                ("Alertas", len(data["alerts"]))])
        out.write_text(HTML.format(
            ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
            score=data["health_score"], kpis=kpis,
            labels=json.dumps(list(data["top_types"])),
            vals=json.dumps(list(data["top_types"].values())),
            alerts="\n".join(f"⚠ {a}"
                             for a in data["alerts"]) or
            "Sin alertas"),
            encoding="utf-8")
    _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
