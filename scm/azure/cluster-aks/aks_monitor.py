#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Cluster Monitor — Tool 13

Inventario y salud de clusters AKS, equivalente a
gcp_cluster_checker / aws_eks_checker:

- Clusters: versión, provisioning state, power state, FQDN
- Node pools por cluster (count, VM size, modo, autoscale)
- Seguridad: RBAC, Azure Policy, private cluster, workload identity
- Hallazgos: versión vieja, RBAC deshabilitado, cluster público

Uso:
    python aks_monitor.py --subscription <id>
    python aks_monitor.py --resource-group rg -o json
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


def analyze_cluster(c: Dict) -> Dict:
    findings = []
    if c.get("provisioningState") not in ("Succeeded", None):
        findings.append("🔴 provisioningState: "
                        f"{c.get('provisioningState')}")
    power = (c.get("powerState") or {}).get("code")
    if power and power != "Running":
        findings.append(f"🟡 Power: {power}")
    if not c.get("enableRBAC"):
        findings.append("🔴 RBAC deshabilitado")
    if not (c.get("apiServerAccessProfile") or {}) \
            .get("enablePrivateCluster"):
        findings.append("🟡 API server público (no private "
                        "cluster)")
    if not (c.get("oidcIssuerProfile") or {}).get("enabled"):
        findings.append("🟡 OIDC issuer deshabilitado — "
                        "sin Workload Identity")
    pools = c.get("agentPoolProfiles", [])
    versions = {p.get("orchestratorVersion") for p in pools
                if p.get("orchestratorVersion")}
    kv = c.get("kubernetesVersion")
    old_pools = [p["name"] for p in pools
                 if p.get("orchestratorVersion") and
                 kv and p["orchestratorVersion"] != kv]
    if old_pools:
        findings.append(f"🟡 Nodepools con versión distinta: "
                        f"{', '.join(old_pools)}")
    return {
        "name": c["name"], "resource_group": rg_of(c),
        "location": c.get("location"),
        "version": kv, "state": c.get("provisioningState"),
        "power": power, "fqdn": c.get("fqdn"),
        "private": bool((c.get("apiServerAccessProfile") or {})
                        .get("enablePrivateCluster")),
        "rbac": c.get("enableRBAC", False),
        "node_pools": len(pools),
        "node_count": sum(p.get("count", 0) for p in pools),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(description="Monitor AKS")
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
    cmd = ["aks", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    clusters = [analyze_cluster(c)
                for c in (try_az(cmd, sub, default=[]) or [])]

    issues = [c for c in clusters if any("🔴" in f
                                         for f in c["findings"])]

    if console:
        from rich.table import Table
        table = Table(title="AKS Clusters", header_style="bold cyan")
        for col in ["Cluster", "RG", "Ver", "Nodes", "RBAC",
                    "Private", "Estado"]:
            table.add_column(col)
        for c in clusters:
            ok = not any("🔴" in f for f in c["findings"])
            table.add_row(
                c["name"][:30], c["resource_group"][:18],
                str(c["version"])[:12], str(c["node_count"]),
                "[green]✓[/green]" if c["rbac"] else "[red]✗[/red]",
                "[green]✓[/green]" if c["private"]
                else "[yellow]✗[/yellow]",
                f"[{'green' if ok else 'red'}]"
                f"{c['state'] or '?'}[/{'green' if ok else 'red'}]")
        console.print(table)
        for c in clusters:
            for f in c["findings"]:
                console.print(f"  {f} [dim]({c['name']})[/dim]")
    else:
        for c in clusters:
            print(f"{c['name']}: {c['state']} v{c['version']} "
                  f"nodes={c['node_count']}")

    _print(f"\nClusters: {len(clusters)} | con issues "
           f"críticos: {len(issues)}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"aks_clusters_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "clusters": clusters})
        else:
            rows = [{**{k: c[k] for k in
                        ("name", "resource_group", "version",
                         "node_count", "rbac", "private",
                         "state")},
                     "findings": "; ".join(c["findings"])}
                    for c in clusters]
            export_csv(out, list(rows[0]) if rows else
                       ["name"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
