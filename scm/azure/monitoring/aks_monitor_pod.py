#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Pod Resources Monitor — Tool 30

Uso de CPU/memoria por pod (`kubectl top pods -A`), equivalente a
gke_monitor_pod / aws_eks_pod_checker:

- Top N pods por CPU o memoria (--sort cpu|mem --top N)
- Filtro por namespace
- Pods sin métricas (metrics-server ausente o pods nuevos)

Uso:
    python aks_monitor_pod.py --cluster aks --resource-group rg
    python aks_monitor_pod.py --namespace prod --sort mem --top 20
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    console, _print, az_available, run_kubectl,
    setup_aks_kubeconfig, resolve_subscription)

__version__ = "1.0.0"


def parse_top_pods(text: str) -> List[Dict]:
    """`kubectl top pods -A` → [{ns,name,cpu,mem}]."""
    rows = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4:
            rows.append({"namespace": parts[0],
                         "pod": parts[1],
                         "cpu": parts[2], "memory": parts[3]})
    return rows


def to_millicores(v: str) -> int:
    v = v.strip()
    if v.endswith("m"):
        try:
            return int(v[:-1])
        except ValueError:
            return 0
    return int(v) * 1000 if v.isdigit() else 0


def to_mi(v: str) -> int:
    if v.endswith("Mi"):
        return int(v[:-2])
    if v.endswith("Gi"):
        return int(v[:-2]) * 1024
    if v.endswith("Ki"):
        return int(v[:-2]) // 1024
    return 0


def get_args():
    p = argparse.ArgumentParser(
        description="CPU/memoria por pod en AKS")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("--namespace", default="")
    p.add_argument("--sort", choices=["cpu", "mem"],
                   default="cpu")
    p.add_argument("--top", type=int, default=15)
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

    kargs = ["top", "pods"]
    kargs += ["-n", args.namespace] if args.namespace else ["-A"]
    try:
        rows = parse_top_pods(run_kubectl(kargs))
    except Exception as e:
        _print(f"⚠ kubectl top pods falló: {e}", "yellow")
        rows = []

    key = to_millicores if args.sort == "cpu" else to_mi
    rows.sort(key=lambda r: -key(r[
        "cpu" if args.sort == "cpu" else "memory"]))
    top = rows[:args.top]

    if console:
        from rich.table import Table
        table = Table(title=f"Top {args.top} pods por "
                            f"{args.sort.upper()} — {args.cluster}",
                      header_style="bold cyan")
        for col in ["#", "Namespace", "Pod", "CPU", "Mem"]:
            table.add_column(col)
        for i, r in enumerate(top, 1):
            table.add_row(str(i), r["namespace"][:20],
                          r["pod"][:50], r["cpu"], r["memory"])
        console.print(table)
    else:
        for r in top:
            print(f"{r['namespace']}/{r['pod']}: "
                  f"cpu={r['cpu']} mem={r['memory']}")

    _print(f"\nPods con métricas: {len(rows)} | top mostrado: "
           f"{len(top)}", "green" if rows else "yellow")


if __name__ == "__main__":
    main()
