#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Executive Dashboard — Tool 51

Dashboard ejecutivo de la flota ECS, equivalente a Cloud Run
Executive Dashboard de GCP:

- KPIs: clusters, servicios, tasks running/desired/pending
- Distribución por estado (HEALTHY/DEGRADED/CRITICAL/DRAINED)
- Deployments fallidos y en curso
- Top servicios por tamaño (desired) y por antigüedad
- Export HTML con Chart.js + JSON

Uso:
    python aws_ecs_executive_dashboard.py --profile p \\
        --region us-east-1 -o html
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session,
    list_clusters, list_services, describe_services,
    service_status)

__version__ = "1.0.0"


def collect(ecs) -> Dict:
    clusters = list_clusters(ecs)
    services = []
    for cluster in clusters:
        for svc in describe_services(
                ecs, cluster, list_services(ecs, cluster)):
            services.append({
                "service": svc["serviceName"], "cluster": cluster,
                "status": service_status(svc),
                "desired": svc.get("desiredCount", 0),
                "running": svc.get("runningCount", 0),
                "pending": svc.get("pendingCount", 0),
                "failed_rollouts": len([
                    d for d in svc.get("deployments", [])
                    if d.get("rolloutState") == "FAILED"]),
                "created": str(svc.get("createdAt", ""))[:10],
            })
    status_count = Counter(s["status"] for s in services)
    return {
        "clusters": len(clusters), "services": services,
        "status_counts": dict(status_count),
        "total_desired": sum(s["desired"] for s in services),
        "total_running": sum(s["running"] for s in services),
        "total_pending": sum(s["pending"] for s in services),
        "failed_rollouts": sum(s["failed_rollouts"]
                               for s in services),
    }


HTML = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>ECS Executive Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{font-family:system-ui;background:#0f1419;color:#e6e6e6;
margin:2em}}h1{{color:#58a6ff}}.grid{{display:grid;
grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:1em}}
.kpi{{background:#1c2128;border-radius:8px;padding:1em;
text-align:center}}.kpi b{{font-size:2em;color:#58a6ff;display:block}}
.card{{background:#1c2128;border-radius:8px;padding:1em;margin:1em 0}}
</style></head><body>
<h1>🚀 ECS Executive Dashboard</h1><p>Generado: {ts} | {region}</p>
<div class="grid">{kpis}</div>
<div class="card"><h2>Estado de servicios</h2>
<canvas id="chart"></canvas></div>
<div class="card"><h2>Servicios</h2><pre>{table}</pre></div>
<script>new Chart(document.getElementById('chart'),{{type:'doughnut',
data:{{labels:{labels},datasets:[{{data:{vals},
backgroundColor:['#56d364','#f2cc60','#ff7b72','#8b949e','#79c0ff']
}}]}}}});</script></body></html>"""


def get_args():
    p = argparse.ArgumentParser(
        description="Dashboard ejecutivo ECS")
    p.add_argument("--profile", "-p", default="default")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("-o", "--output", choices=["html", "json"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    ecs = make_session(args.profile, args.region).client("ecs")
    data = collect(ecs)

    healthy = data["status_counts"].get("HEALTHY", 0)
    critical = data["status_counts"].get("CRITICAL", 0)

    if console:
        from rich.table import Table
        from rich.panel import Panel
        console.print(Panel.fit(
            f"Clusters: [bold]{data['clusters']}[/bold] | "
            f"Servicios: [bold]{len(data['services'])}[/bold] | "
            f"Tasks: {data['total_running']}/{data['total_desired']}\n"
            f"✅ {healthy} | "
            f"[red]🔴 {critical}[/red] | "
            f"rollouts fallidos: {data['failed_rollouts']}",
            title="🚀 ECS Executive"))
        table = Table(header_style="bold cyan")
        for col in ["Servicio", "Cluster", "Run/Des", "Estado"]:
            table.add_column(col)
        for s in sorted(data["services"],
                        key=lambda x: x["status"] != "HEALTHY",
                        reverse=True)[:30]:
            color = {"HEALTHY": "green", "DEGRADED": "yellow",
                     "CRITICAL": "red"}.get(s["status"], "dim")
            table.add_row(s["service"][:40], s["cluster"][:18],
                          f"{s['running']}/{s['desired']}",
                          f"[{color}]{s['status']}[/{color}]")
        console.print(table)
    else:
        print(f"clusters={data['clusters']} "
              f"services={len(data['services'])} "
              f"healthy={healthy} critical={critical}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if args.output == "json":
            out = OUTCOME_DIR / f"ecs_dashboard_{ts}.json"
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                **data}, indent=2, default=str), encoding="utf-8")
        else:
            out = OUTCOME_DIR / f"ecs_dashboard_{ts}.html"
            kpis = "".join(
                f"<div class='kpi'><b>{v}</b>{k}</div>"
                for k, v in [("Clusters", data["clusters"]),
                             ("Servicios", len(data["services"])),
                             ("Tasks", data["total_running"]),
                             ("Healthy", healthy),
                             ("Critical", critical),
                             ("Failed rollouts",
                              data["failed_rollouts"])])
            rows = "\n".join(
                f"{s['service']:<40} {s['cluster']:<20} "
                f"{s['running']}/{s['desired']} {s['status']}"
                for s in data["services"])
            out.write_text(HTML.format(
                ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
                region=args.region, kpis=kpis, table=rows,
                labels=json.dumps(list(data["status_counts"])),
                vals=json.dumps(list(data["status_counts"]
                                       .values()))),
                encoding="utf-8")
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
