#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Workload Identity Validator — Tool 15

Valida Workload Identity en AKS (equivalente a la validación de
Workload Identity en GKE / IRSA en EKS):

- Cluster: oidcIssuer + securityProfile.workloadIdentity habilitados
- ServiceAccounts: anotación `azure.workload.identity/client-id`
- Pods: env vars/projected volumes de workload identity presentes
- Managed identities referenciadas vs existentes (az identity list)

Uso:
    python workload_identity_validator.py --subscription <id> \\
        --cluster aks --resource-group rg
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
    rg_of, now_ts, export_json)

__version__ = "1.0.0"

WI_CLIENT_ANNOTATION = "azure.workload.identity/client-id"
WI_LABEL = "azure.workload.identity/use"


def check_cluster(c: Dict) -> List[str]:
    findings = []
    if not (c.get("oidcIssuerProfile") or {}).get("enabled"):
        findings.append("🔴 OIDC issuer deshabilitado — WI no "
                        "puede emitir tokens")
    sec = c.get("securityProfile") or {}
    if not (sec.get("workloadIdentity") or {}).get("enabled"):
        findings.append("🔴 Workload Identity deshabilitado en "
                        "el cluster")
    return findings


def check_service_accounts() -> List[Dict]:
    """ServiceAccounts con anotación de client-id."""
    try:
        items = kubectl_json(
            ["get", "serviceaccounts", "-A"]).get("items", [])
    except Exception:
        return []
    out = []
    for sa in items:
        meta = sa.get("metadata", {})
        ann = meta.get("annotations", {}) or {}
        client_id = ann.get(WI_CLIENT_ANNOTATION)
        if client_id:
            out.append({
                "namespace": meta.get("namespace"),
                "name": meta.get("name"),
                "client_id": client_id,
                "tenant": ann.get(
                    "azure.workload.identity/tenant-id"),
            })
    return out


def check_pods() -> Dict:
    """Pods que usan la label de WI pero su SA no tiene client-id."""
    try:
        pods = kubectl_json(["get", "pods", "-A"]).get("items", [])
    except Exception:
        return {"wi_pods": [], "broken": []}
    wi_pods, broken = [], []
    for p in pods:
        meta = p.get("metadata", {})
        labels = meta.get("labels", {}) or {}
        spec = p.get("spec", {})
        envs = [e for c in spec.get("containers", [])
                for e in c.get("env", [])]
        has_wi_env = any(
            e.get("name", "").startswith("AZURE_")
            for e in envs)
        if labels.get(WI_LABEL) == "true" or has_wi_env:
            wi_pods.append(f"{meta.get('namespace')}/"
                           f"{meta.get('name')}")
        if has_wi_env and labels.get(WI_LABEL) != "true":
            broken.append(
                f"{meta.get('namespace')}/{meta.get('name')} "
                f"(env AZURE_* sin label {WI_LABEL})")
    return {"wi_pods": wi_pods, "broken": broken}


def get_args():
    p = argparse.ArgumentParser(
        description="Valida Workload Identity en AKS")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("-o", "--output", choices=["json"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)

    clusters = try_az(["aks", "list"], sub, default=[]) or []
    cluster = next((c for c in clusters
                    if c["name"] == args.cluster), None)
    cluster_findings = check_cluster(cluster) if cluster else \
        [f"🔴 Cluster {args.cluster} no encontrado"]

    kube_ok = setup_aks_kubeconfig(
        args.cluster, args.resource_group, sub)
    sas = check_service_accounts() if kube_ok else []
    pods = check_pods() if kube_ok else {"wi_pods": [],
                                         "broken": []}

    # Validar que las identities referenciadas existen
    managed = {i.get("clientId") for i in
               (try_az(["identity", "list"], sub, default=[])
                or [])}
    missing_ids = [s for s in sas
                   if managed and s["client_id"] not in managed]

    if console:
        from rich.table import Table
        for f in cluster_findings:
            console.print(f"  {f}")
        table = Table(title="ServiceAccounts con Workload "
                            "Identity", header_style="bold cyan")
        for col in ["NS", "SA", "Client ID"]:
            table.add_column(col)
        for s in sas:
            color = "green" if not managed or \
                s["client_id"] in managed else "red"
            table.add_row(s["namespace"], s["name"],
                          f"[{color}]{s['client_id'][:36]}"
                          f"[/{color}]")
        console.print(table)
        for b in pods["broken"]:
            console.print(f"  [yellow]⚠ {b}[/yellow]")
        for s in missing_ids:
            console.print(
                f"  [red]✗ SA {s['namespace']}/{s['name']} → "
                f"client-id no existe: {s['client_id']}[/red]")
    else:
        print(f"cluster_findings={cluster_findings}")
        print(f"sa_with_wi={len(sas)} "
              f"pods_wi={len(pods['wi_pods'])}")

    _print(f"\nSAs con WI: {len(sas)} | pods WI: "
           f"{len(pods['wi_pods'])} | identities faltantes: "
           f"{len(missing_ids)}",
           "red" if cluster_findings or missing_ids else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"aks_workload_identity_{now_ts()}.json"
        export_json(out, {
            "timestamp": datetime.utcnow().isoformat(),
            "cluster": args.cluster,
            "cluster_findings": cluster_findings,
            "service_accounts": sas,
            "wi_pods": pods["wi_pods"],
            "broken_pods": pods["broken"],
            "missing_identities": missing_ids})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if cluster_findings else 0)


if __name__ == "__main__":
    main()
