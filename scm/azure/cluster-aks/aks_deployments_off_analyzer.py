#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Deployments Off Analyzer — Tool 37

Detecta deployments con réplicas insuficientes en AKS y clasifica la
causa raíz, equivalente a gcp_deployments_off_analyzer /
aws_eks_deployments_off_analyzer:

- Deployments con ready < desired o desired = 0
- Causa raíz: ImagePullBackOff, CrashLoop, scheduling, config
  (ConfigMap/Secret faltante), probes, OOM, etc.
- Severidad (critical/high/medium/low) + recomendaciones
- Export JSON/CSV

Uso:
    python aks_deployments_off_analyzer.py --subscription <id> \\
        --cluster aks --resource-group rg
    python aks_deployments_off_analyzer.py --namespace prod -o json
"""

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available,
    setup_aks_kubeconfig, kubectl_json, resolve_subscription,
    rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"

# Orden por longitud descendente — las causas específicas deben
# matchear antes que las genéricas (FailedScheduling antes de Failed)
CAUSES = [
    ("ImagePullBackOff", "Image Pull Error", "critical"),
    ("ErrImagePull", "Image Pull Error", "critical"),
    ("InvalidImageName", "Image Pull Error", "critical"),
    ("CrashLoopBackOff", "Application Error", "critical"),
    ("FailedScheduling", "Resource Constraint", "critical"),
    ("Unschedulable", "Resource Constraint", "critical"),
    ("CreateContainerConfigError", "Config Error", "high"),
    ("CreateContainerError", "Config Error", "high"),
    ("MountVolume.SetUp failed", "Volume/Config Error", "high"),
    ("configmap", "Config Error", "high"),
    ("secret", "Config Error", "high"),
    ("Insufficient", "Resource Constraint", "high"),
    ("OOMKilled", "Resource Constraint", "high"),
    ("Failed", "Generic Failure", "medium"),
    ("Unhealthy", "Probe Failure", "medium"),
    ("Back-off", "Application Error", "medium"),
]

REMEDIATION = {
    "Image Pull Error": "Verificar imagen/tag y credenciales ACR",
    "Application Error": "Revisar logs: kubectl logs <pod> "
                         "--previous",
    "Resource Constraint": "Escalar nodepool o ajustar requests",
    "Config Error": "Verificar ConfigMap/Secret referenciado",
    "Volume/Config Error": "Verificar volúmenes y montajes",
    "Probe Failure": "Revisar readiness/liveness probes",
    "Generic Failure": "kubectl describe pod para detalles",
}


def _classify(reason: str) -> str:
    """Primera causa cuyo patrón aparece en `reason` (claves
    largas primero)."""
    for key, category, _ in CAUSES:
        if key in reason:
            return category
    return "Unknown"


def _severity(reason: str) -> str:
    for key, _, sev in CAUSES:
        if key in reason:
            return sev
    return "medium"


def collect_reasons(pods: List[Dict],
                    namespace: str,
                    owner_name: str) -> List[str]:
    """Razones de fallo de los pods de un deployment."""
    reasons = []
    for p in pods:
        meta, status = (p.get("metadata", {}),
                        p.get("status", {}))
        if meta.get("namespace") != namespace:
            continue
        owner = meta.get("ownerReferences", [{}])[0] \
            .get("name", "")
        # ReplicaSet del deployment = deployment-<hash>
        if not owner.startswith(owner_name):
            continue
        for cs in status.get("containerStatuses", []) + \
                status.get("initContainerStatuses", []):
            st = cs.get("state", {})
            if "waiting" in st:
                reasons.append(
                    st["waiting"].get("reason", "Waiting"))
            elif "terminated" in st and \
                    st["terminated"].get("exitCode") != 0:
                term = st["terminated"]
                reasons.append(term.get(
                    "reason", f"exitCode:{term.get('exitCode')}"))
        for cond in status.get("conditions", []):
            if cond.get("type") == "PodScheduled" and \
                    cond.get("status") == "False":
                reasons.append(cond.get("reason",
                                        "FailedScheduling"))
    return reasons


def analyze(items: List[Dict], pods: List[Dict]) -> List[Dict]:
    out = []
    for d in items:
        meta, spec, status = (d.get("metadata", {}),
                              d.get("spec", {}),
                              d.get("status", {}))
        desired = spec.get("replicas", 0)
        ready = status.get("readyReplicas", 0)
        if desired > 0 and ready >= desired:
            continue
        reasons = collect_reasons(
            pods, meta.get("namespace", ""), meta.get("name", ""))
        if desired == 0 and not reasons:
            category, severity, detail = ("Drained", "info",
                                          "desired=0 (escalado "
                                          "manualmente)")
        elif reasons:
            reason_text = " | ".join(sorted(set(reasons)))
            category = _classify(reason_text)
            severity = _severity(reason_text)
            detail = reason_text[:200]
        else:
            category, severity, detail = (
                "Unknown", "high",
                "sin pods de fallo visibles — revisar events")
        out.append({
            "namespace": meta.get("namespace"),
            "deployment": meta.get("name"),
            "desired": desired, "ready": ready,
            "category": category, "severity": severity,
            "detail": detail,
            "remediation": REMEDIATION.get(category, ""),
        })
    return out


SEV_ORDER = {"critical": 0, "high": 1, "medium": 2,
             "low": 3, "info": 4}


def get_args():
    p = argparse.ArgumentParser(
        description="Deployments no running en AKS con causa "
                    "raíz")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", required=True)
    p.add_argument("--resource-group", required=True)
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
    if not setup_aks_kubeconfig(args.cluster,
                                args.resource_group, sub):
        _print("❌ kubeconfig no configurado", "red")
        sys.exit(1)

    ns_args = ["-n", args.namespace] if args.namespace else ["-A"]
    try:
        deploys = kubectl_json(["get", "deployments",
                                *ns_args]).get("items", [])
        pods = kubectl_json(["get", "pods",
                             *ns_args]).get("items", [])
    except Exception as e:
        _print(f"❌ kubectl falló: {e}", "red")
        sys.exit(1)

    results = sorted(analyze(deploys, pods),
                     key=lambda r: SEV_ORDER[r["severity"]])
    counts = Counter(r["severity"] for r in results)

    if console:
        from rich.table import Table
        table = Table(title=f"AKS Deployments Off — "
                            f"{args.cluster}",
                      header_style="bold cyan")
        for col in ["NS", "Deployment", "Ready/Des", "Causa",
                    "Sev"]:
            table.add_column(col)
        style = {"critical": "red bold", "high": "red",
                 "medium": "yellow", "low": "dim",
                 "info": "dim"}
        for r in results:
            table.add_row(
                r["namespace"][:15], r["deployment"][:40],
                f"{r['ready']}/{r['desired']}",
                r["category"][:25],
                f"[{style[r['severity']]}]{r['severity']}"
                f"[/{style[r['severity']]}]")
        console.print(table)
        for r in results:
            if r["remediation"]:
                console.print(f"  💡 {r['deployment']}: "
                              f"[dim]{r['remediation']}[/dim]")
    else:
        for r in results:
            print(f"[{r['severity']}] {r['namespace']}/"
                  f"{r['deployment']} {r['ready']}/"
                  f"{r['desired']} → {r['category']}")

    _print(f"\nAnalizados: {len(deploys)} | con problemas: "
           f"{len(results)} ({dict(counts)})",
           "red" if counts.get("critical") else
           ("yellow" if results else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"aks_deployments_off_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "cluster": args.cluster,
                "deployments": results})
        else:
            export_csv(out, ["namespace", "deployment",
                             "desired", "ready", "category",
                             "severity", "detail",
                             "remediation"], results)
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if counts.get("critical") else 0)


if __name__ == "__main__":
    main()
