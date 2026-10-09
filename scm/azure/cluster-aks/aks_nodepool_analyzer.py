#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Node Pool Analyzer — Tool 14

Análisis de node pools en clusters AKS:

- Por cluster/pool: VM size, count, autoscaling (min/max),
  spot instances, mode (System/User), SO
- Hallazgos: pools sin autoscale, system pool único,
  versión desactualizada vs control plane, spot sin tolerations

Uso:
    python aks_nodepool_analyzer.py --subscription <id>
    python aks_nodepool_analyzer.py --cluster aks -o json
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


def analyze_pool(cluster: str, cluster_version: str,
                 pool: Dict) -> Dict:
    findings = []
    name = pool.get("name", "?")
    if not pool.get("enableAutoScaling"):
        findings.append("🟡 Sin autoscaling")
    if pool.get("mode") == "System" and \
            pool.get("count", 0) < 2:
        findings.append("🔴 System pool con <2 nodos — SPOF")
    if cluster_version and pool.get("orchestratorVersion") and \
            pool["orchestratorVersion"] != cluster_version:
        findings.append("🟡 Versión distinta al control plane "
                        f"({pool['orchestratorVersion']} vs "
                        f"{cluster_version})")
    if pool.get("scaleSetPriority") == "Spot" and \
            not pool.get("nodeTaints"):
        findings.append("🟡 Spot pool sin taints — pods "
                        "cualquiera pueden caer aquí")
    return {
        "cluster": cluster, "pool": name,
        "vm_size": pool.get("vmSize"),
        "count": pool.get("count"),
        "autoscale": pool.get("enableAutoScaling", False),
        "min": pool.get("minCount"), "max": pool.get("maxCount"),
        "mode": pool.get("mode", "User"),
        "os": pool.get("osType"),
        "priority": pool.get("scaleSetPriority", "Regular"),
        "version": pool.get("orchestratorVersion"),
        "state": pool.get("provisioningState"),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Análisis de node pools AKS")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", default="")
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
    clusters = try_az(["aks", "list"], sub, default=[]) or []
    if args.cluster:
        clusters = [c for c in clusters
                    if c["name"] == args.cluster]
    if args.resource_group:
        clusters = [c for c in clusters
                    if rg_of(c) == args.resource_group]

    pools = []
    for c in clusters:
        rg = rg_of(c)
        plist = try_az(["aks", "nodepool", "list",
                        "--cluster-name", c["name"],
                        "--resource-group", rg], sub,
                       default=[]) or []
        for p in plist:
            pools.append(analyze_pool(
                c["name"], c.get("kubernetesVersion", ""), p))

    critical = [p for p in pools
                if any("🔴" in f for f in p["findings"])]

    if console:
        from rich.table import Table
        table = Table(title="AKS Node Pools",
                      header_style="bold cyan")
        for col in ["Cluster", "Pool", "Size", "Count",
                    "Autoscale", "Mode", "Findings"]:
            table.add_column(col)
        for p in pools:
            bad = any("🔴" in f for f in p["findings"])
            table.add_row(
                p["cluster"][:20], p["pool"][:18],
                str(p["vm_size"])[:15],
                str(p["count"]),
                f"{p['min']}-{p['max']}" if p["autoscale"]
                else "[yellow]✗[/yellow]",
                p["mode"],
                f"[{'red' if bad else 'green'}]"
                f"{len(p['findings'])}"
                f"[/{'red' if bad else 'green'}]")
        console.print(table)
        for p in pools:
            for f in p["findings"]:
                console.print(
                    f"  {f} [dim]({p['cluster']}/{p['pool']})"
                    f"[/dim]")
    else:
        for p in pools:
            print(f"{p['cluster']}/{p['pool']}: {p['vm_size']} "
                  f"x{p['count']} {p['findings']}")

    _print(f"\nPools: {len(pools)} | críticos: {len(critical)}",
           "red" if critical else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"aks_nodepools_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "node_pools": pools})
        else:
            rows = [{k: p[k] for k in
                     ("cluster", "pool", "vm_size", "count",
                      "autoscale", "min", "max", "mode",
                      "version")}
                    | {"findings": "; ".join(p["findings"])}
                    for p in pools]
            export_csv(out, list(rows[0]) if rows else
                       ["cluster"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
