#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Node Resources Monitor — Tool 29

Uso de CPU/memoria por nodo (`kubectl top nodes`), equivalente a
gke_monitor_node / aws_eks_node_checker. Exporta reporte HTML.

Uso:
    python aks_monitor_node.py --cluster aks --resource-group rg
    python aks_monitor_node.py --subscription <id> --output html
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, run_kubectl,
    setup_aks_kubeconfig, kubectl_json, resolve_subscription,
    now_ts)

__version__ = "1.0.0"


def parse_top_nodes(text: str) -> List[Dict]:
    """Salida `kubectl top nodes` → [{name,cpu_cores,cpu_pct,
    mem_bytes,mem_pct}]."""
    rows = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 5:
            rows.append({
                "node": parts[0],
                "cpu": parts[1],
                "cpu_pct": int(parts[2].rstrip("%")),
                "memory": parts[3],
                "mem_pct": int(parts[4].rstrip("%")),
            })
    return rows


def top_nodes() -> List[Dict]:
    try:
        return parse_top_nodes(run_kubectl(["top", "nodes"]))
    except Exception:
        return []


def node_capacity() -> Dict[str, Dict]:
    """Capacidad allocatable por nodo (contexto)."""
    try:
        items = kubectl_json(["get", "nodes"]).get("items", [])
    except Exception:
        return {}
    out = {}
    for n in items:
        st = n.get("status", {})
        out[n["metadata"]["name"]] = {
            "cpu_capacity": st.get("capacity", {}).get("cpu"),
            "mem_capacity": st.get("capacity", {}).get("memory"),
            "conditions": {c["type"]: c["status"] for c in
                           st.get("conditions", [])
                           if c["type"] in ("Ready", "MemoryPressure",
                                            "DiskPressure",
                                            "PIDPressure")},
        }
    return out


HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>AKS Node Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{font-family:system-ui;background:#0f1419;color:#eee;
margin:2em}}h1{{color:#58a6ff}}.ok{{color:#56d364}}
.warn{{color:#f2cc60}}.bad{{color:#ff7b72}}</style></head><body>
<h1>☸️ AKS Node Report — {cluster}</h1>
<p>Generado: {ts} | Nodos: {count} | CPU max: {cpu_max}% |
MEM max: {mem_max}%</p>
<canvas id="c" width="900" height="380"></canvas>
<script>
const labels={labels}, cpu={cpu}, mem={mem};
new Chart(document.getElementById('c'),{{type:'bar',data:{{labels,
datasets:[{{label:'CPU %',data:cpu,backgroundColor:'#58a6ff'}},
{{label:'MEM %',data:mem,backgroundColor:'#f2cc60'}}]}},
options:{{scales:{{y:{{max:100}}}}}}}});
</script><pre>{table}</pre></body></html>"""


def get_args():
    p = argparse.ArgumentParser(
        description="Uso de CPU/memoria por nodo AKS")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("--output", choices=["html", "json"],
                   default="html")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    if not setup_aks_kubeconfig(args.cluster,
                                args.resource_group, sub):
        _print("❌ kubeconfig no configurado", "red")
        sys.exit(1)

    rows = top_nodes()
    capacity = node_capacity()
    if not rows:
        _print("⚠ metrics-server no disponible (kubectl top "
               "falló)", "yellow")
    for r in rows:
        r.update(capacity.get(r["node"], {}))

    cpu_max = max((r["cpu_pct"] for r in rows), default=0)
    mem_max = max((r["mem_pct"] for r in rows), default=0)

    if console:
        from rich.table import Table
        table = Table(title=f"AKS Nodes — {args.cluster}",
                      header_style="bold cyan")
        for col in ["Nodo", "CPU", "CPU%", "MEM", "MEM%",
                    "Ready"]:
            table.add_column(col)
        for r in rows:
            c = "red" if r["cpu_pct"] > 80 else \
                "yellow" if r["cpu_pct"] > 60 else "green"
            m = "red" if r["mem_pct"] > 85 else \
                "yellow" if r["mem_pct"] > 70 else "green"
            ready = (r.get("conditions") or {}).get("Ready", "?")
            table.add_row(r["node"][:45], r["cpu"],
                          f"[{c}]{r['cpu_pct']}%[/{c}]",
                          r["memory"],
                          f"[{m}]{r['mem_pct']}%[/{m}]",
                          str(ready))
        console.print(table)
    else:
        for r in rows:
            print(f"{r['node']}: cpu={r['cpu_pct']}% "
                  f"mem={r['mem_pct']}%")

    OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
    if args.output == "html":
        out = OUTCOME_DIR / f"aks_nodes_{now_ts()}.html"
        import json
        out.write_text(HTML.format(
            cluster=args.cluster,
            ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
            count=len(rows), cpu_max=cpu_max, mem_max=mem_max,
            labels=json.dumps([r["node"][:20] for r in rows]),
            cpu=json.dumps([r["cpu_pct"] for r in rows]),
            mem=json.dumps([r["mem_pct"] for r in rows]),
            table="\n".join(
                f"{r['node']:<45} {r['cpu']:<8} {r['cpu_pct']:>3}% "
                f"{r['memory']:<10} {r['mem_pct']:>3}%"
                for r in rows)),
            encoding="utf-8")
        _print(f"✓ HTML: {out}", "green")
    elif args.output == "json":
        import json
        out = OUTCOME_DIR / f"aks_nodes_{now_ts()}.json"
        out.write_text(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "cluster": args.cluster, "nodes": rows},
            indent=2, default=str), encoding="utf-8")
        _print(f"✓ JSON: {out}", "green")

    sys.exit(1 if mem_max > 85 or cpu_max > 90 else 0)


if __name__ == "__main__":
    main()
