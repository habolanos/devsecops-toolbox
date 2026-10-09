#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Pod Security Audit — Tool 16

Auditoría de seguridad a nivel pod/containers en AKS (equivalente a
Pod Security Standards / auditoría de seguridad de workloads en GKE):

- Containers privileged / allowPrivilegeEscalation
- runAsUser 0 (root) o sin runAsNonRoot
- readOnlyRootFilesystem ausente
- hostNetwork/hostPID/hostIPC
- Capabilities: ALL o SYS_ADMIN
- Sin resource limits

Uso:
    python pod_security_audit.py --cluster aks --resource-group rg
    python pod_security_audit.py --namespace default -o json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available,
    setup_aks_kubeconfig, kubectl_json, resolve_subscription,
    now_ts, export_json, export_csv)

__version__ = "1.0.0"

SYSTEM_NAMESPACES = {"kube-system", "gatekeeper-system",
                     "azure-extensions-usage-system"}


def audit_container(pod_name: str, ns: str, c: Dict,
                    pod_sc: Dict) -> List[Dict]:
    """Findings de un container."""
    findings = []
    sc = c.get("securityContext", {}) or {}
    name = c.get("name", "?")
    ref = f"{ns}/{pod_name}/{name}"
    if sc.get("privileged"):
        findings.append({"sev": "critical", "type": "privileged",
                         "resource": ref})
    if sc.get("allowPrivilegeEscalation"):
        findings.append({"sev": "high", "type": "priv_escalation",
                         "resource": ref})
    if sc.get("runAsUser") == 0 or (
            sc.get("runAsUser") is None and
            not sc.get("runAsNonRoot") and
            not pod_sc.get("runAsNonRoot")):
        findings.append({"sev": "medium", "type": "root_or_unset",
                         "resource": ref})
    if not sc.get("readOnlyRootFilesystem"):
        findings.append({"sev": "low", "type": "rootfs_rw",
                         "resource": ref})
    caps = (sc.get("capabilities") or {}).get("add", [])
    if "ALL" in caps or "SYS_ADMIN" in caps:
        findings.append({"sev": "high", "type": "dangerous_caps",
                         "resource": ref})
    if not c.get("resources", {}).get("limits"):
        findings.append({"sev": "info", "type": "no_limits",
                         "resource": ref})
    return findings


def audit_pods(namespace: str = "") -> List[Dict]:
    args = ["get", "pods"]
    args += ["-n", namespace] if namespace else ["-A"]
    try:
        items = kubectl_json(args).get("items", [])
    except Exception:
        return []
    findings = []
    for p in items:
        meta, spec = p.get("metadata", {}), p.get("spec", {})
        ns = meta.get("namespace", "")
        if ns in SYSTEM_NAMESPACES:
            continue
        pod_sc = spec.get("securityContext", {}) or {}
        name = meta.get("name", "?")
        if spec.get("hostNetwork") or spec.get("hostPID") or \
                spec.get("hostIPC"):
            findings.append({"sev": "high", "type": "host_ns",
                             "resource": f"{ns}/{name}"})
        for c in spec.get("containers", []) + \
                spec.get("initContainers", []):
            findings.extend(
                audit_container(name, ns, c, pod_sc))
    return findings


SEV_ORDER = {"critical": 0, "high": 1, "medium": 2,
             "low": 3, "info": 4}


def get_args():
    p = argparse.ArgumentParser(
        description="Auditoría de seguridad de pods AKS")
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
        _print("❌ No se pudo configurar kubeconfig", "red")
        sys.exit(1)

    findings = sorted(audit_pods(args.namespace),
                      key=lambda f: SEV_ORDER[f["sev"]])
    counts = {}
    for f in findings:
        counts[f["sev"]] = counts.get(f["sev"], 0) + 1

    if console:
        from rich.table import Table
        table = Table(title="AKS Pod Security Audit",
                      header_style="bold red")
        for col in ["Sev", "Tipo", "Recurso"]:
            table.add_column(col)
        style = {"critical": "red bold", "high": "red",
                 "medium": "yellow", "low": "dim",
                 "info": "dim"}
        for f in findings[:60]:
            table.add_row(f"[{style[f['sev']]}]{f['sev']}"
                          f"[/{style[f['sev']]}]",
                          f["type"], f["resource"][:70])
        console.print(table)
    else:
        for f in findings:
            print(f"[{f['sev']}] {f['type']} {f['resource']}")

    _print(f"\nFindings: {len(findings)} | critical: "
           f"{counts.get('critical', 0)} | high: "
           f"{counts.get('high', 0)}",
           "red" if counts.get("critical") else
           ("yellow" if findings else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"aks_pod_security_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "cluster": args.cluster, "summary": counts,
                "findings": findings})
        else:
            export_csv(out, ["sev", "type", "resource"], findings)
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if counts.get("critical") else 0)


if __name__ == "__main__":
    main()
