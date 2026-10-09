#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Deployments Report — Tool 2

Reporte detallado de despliegues en clusters AKS, equivalente a
gke_deployments_report / aws_eks_deployments_report:

- Por cluster: deployments con replicas ready/desired/available
- Imágenes desplegadas por deployment
- Detección de deployments degradados o sin réplicas
- Export JSON/CSV

Uso:
    python aks_deployments_report.py --subscription <id>
    python aks_deployments_report.py --cluster aks-prod \\
        --resource-group rg -o csv
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    setup_aks_kubeconfig, kubectl_json, resolve_subscription,
    rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"


def deployments_of(kube_ready: bool) -> List[Dict]:
    if not kube_ready:
        return []
    try:
        items = kubectl_json(
            ["get", "deployments", "-A"]).get("items", [])
    except Exception:
        return []
    out = []
    for d in items:
        meta, spec, status = (d.get("metadata", {}),
                              d.get("spec", {}),
                              d.get("status", {}))
        containers = (spec.get("template", {})
                      .get("spec", {}).get("containers", []))
        out.append({
            "namespace": meta.get("namespace"),
            "name": meta.get("name"),
            "desired": spec.get("replicas", 0),
            "ready": status.get("readyReplicas", 0),
            "available": status.get("availableReplicas", 0),
            "updated": status.get("updatedReplicas", 0),
            "images": ";".join(c.get("image", "?")
                               for c in containers),
            "labels": ",".join(
                f"{k}={v}" for k, v in
                (meta.get("labels") or {}).items())[:80],
        })
    return out


def get_args():
    p = argparse.ArgumentParser(
        description="Reporte de deployments AKS")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", default="",
                   help="Cluster AKS (vacío = todos)")
    p.add_argument("--resource-group", default="")
    p.add_argument("--namespace", default="")
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

    rows = []
    for c in clusters:
        rg = rg_of(c)
        _print(f"Conectando a {c['name']}...", "dim")
        ok = setup_aks_kubeconfig(c["name"], rg, sub)
        if not ok:
            _print(f"  ⚠ No se pudo configurar kubeconfig "
                   f"para {c['name']}", "yellow")
        for d in deployments_of(ok):
            d["cluster"] = c["name"]
            d["resource_group"] = rg
            rows.append(d)

    degraded = [r for r in rows if r["ready"] < r["desired"]]
    drained = [r for r in rows if r["desired"] == 0]

    if console:
        from rich.table import Table
        table = Table(title="AKS Deployments Report",
                      header_style="bold cyan")
        for col in ["Cluster", "NS", "Deployment", "Ready/Des",
                    "Imagen"]:
            table.add_column(col)
        for r in rows:
            color = "green" if r["ready"] == r["desired"] and \
                r["desired"] > 0 else \
                "yellow" if r["desired"] == 0 else "red"
            table.add_row(
                r["cluster"][:20], r["namespace"][:15],
                r["name"][:35],
                f"[{color}]{r['ready']}/{r['desired']}"
                f"[/{color}]", r["images"][:45])
        console.print(table)
    else:
        for r in rows:
            print(f"{r['cluster']}/{r['namespace']}/"
                  f"{r['name']}: {r['ready']}/{r['desired']}")

    _print(f"\nDeployments: {len(rows)} | degradados: "
           f"{len(degraded)} | drained: {len(drained)}",
           "red" if degraded else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"aks_deployments_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "deployments": rows})
        else:
            export_csv(out, ["cluster", "resource_group",
                             "namespace", "name", "desired",
                             "ready", "available", "images"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
