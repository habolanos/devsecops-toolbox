#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Compliance Report — Tool 23

Reporte de cumplimiento normativo, usando Azure Policy como
fuente (az policy state list) + estado de recursos clave:

- Políticas no conformes (NonCompliant) agrupadas por definición
- Recursos no conformes por tipo
- Resumen ejecutivo con score de compliance
- Export HTML con gráficos + JSON/CSV

Uso:
    python azure_compliance_report.py --subscription <id>
    python azure_compliance_report.py -o html
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


def collect(sub: str) -> Dict:
    states = try_az(
        ["policy", "state", "list",
         "--filter", "complianceState eq 'NonCompliant'"],
        sub, default=[]) or []
    by_policy = Counter(
        s.get("policyDefinitionName", "?")[:8]
        for s in states)
    by_type = Counter(
        (s.get("resourceType") or "?").split("/")[-1]
        for s in states)
    by_rg = Counter(s.get("resourceGroup", "?")
                    for s in states)
    details = [{
        "resource": (s.get("resourceId") or "")
        .rsplit("/", 1)[-1],
        "type": (s.get("resourceType") or "")
        .split("/")[-1],
        "policy": s.get("policyDefinitionName", "?")[:8],
        "rg": s.get("resourceGroup"),
    } for s in states]
    return {
        "noncompliant": len(states),
        "by_policy": dict(by_policy.most_common(15)),
        "by_type": dict(by_type.most_common(12)),
        "by_rg": dict(by_rg.most_common(10)),
        "details": details,
    }


HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Azure Compliance Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{font-family:system-ui;background:#0f1419;color:#eee;
margin:2em}}h1{{color:#58a6ff}}.card{{background:#1c2128;
border-radius:8px;padding:1em;margin:1em 0}}</style></head><body>
<h1>📋 Azure Compliance Report</h1>
<p>Generado: {ts} | No conformes: <b>{nc}</b></p>
<div class="card"><h2>Por tipo de recurso</h2>
<canvas id="t" width="800" height="360"></canvas></div>
<div class="card"><h2>Detalle</h2><pre>{detail}</pre></div>
<script>new Chart(document.getElementById('t'),{{type:'bar',
data:{{labels:{labels},datasets:[{{data:{vals},
backgroundColor:'#ff7b72'}}]}},
options:{{indexAxis:'y'}}}});</script></body></html>"""


def get_args():
    p = argparse.ArgumentParser(
        description="Reporte de compliance Azure Policy")
    p.add_argument("--subscription", default="")
    p.add_argument("-o", "--output",
                   choices=["html", "json", "csv"],
                   default="html")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    data = collect(sub)

    _print(f"Recursos no conformes: {data['noncompliant']}",
           "red" if data["noncompliant"] else "green")
    if console and data["by_type"]:
        from rich.table import Table
        t = Table(title="Por tipo", header_style="bold red")
        t.add_column("Tipo")
        t.add_column("Count", justify="right")
        for k, v in data["by_type"].items():
            t.add_row(k, str(v))
        console.print(t)

    OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTCOME_DIR / f"compliance_{now_ts()}.{args.output}"
    if args.output == "json":
        export_json(out, {
            "timestamp": datetime.utcnow().isoformat(),
            **data})
    elif args.output == "csv":
        export_csv(out, ["resource", "type", "policy", "rg"],
                   data["details"])
    else:
        import json
        out.write_text(HTML.format(
            ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
            nc=data["noncompliant"],
            labels=json.dumps(list(data["by_type"])),
            vals=json.dumps(list(data["by_type"].values())),
            detail="\n".join(
                f"{d['resource']:<40} {d['type']:<25} "
                f"{d['policy']}" for d in
                data["details"][:200])),
            encoding="utf-8")
    _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
