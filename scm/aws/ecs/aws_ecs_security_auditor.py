#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Security Auditor — Tool 45

Auditoría de seguridad de servicios ECS/Fargate, equivalente a Cloud
Run Security Auditor de GCP:

- IPs públicas asignadas a tasks (assignPublicIp=ENABLED)
- Secretos en env vars de la task definition (patrones)
- EFS sin cifrado en tránsito, root filesystem de solo-lectura
- enableExecuteCommand activo (vector de acceso interactivo)
- Contenedores privilegiados, usuario root (sin user definido)
- Logging deshabilitado en containers

Uso:
    python aws_ecs_security_auditor.py --profile p --region us-east-1
    python aws_ecs_security_auditor.py --severity critical -o json
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session,
    list_clusters, list_services, describe_services,
    get_task_definition, env_secrets)

__version__ = "1.0.0"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Finding:
    severity: Severity
    service: str
    check: str
    message: str
    remediation: str = ""


def audit_service(ecs, svc: Dict) -> List[Finding]:
    findings = []
    name = svc["serviceName"]

    net = svc.get("networkConfiguration", {}) \
        .get("awsvpcConfiguration", {})
    if net.get("assignPublicIp") == "ENABLED":
        findings.append(Finding(
            Severity.HIGH, name, "public_ip",
            "Tasks con IP pública asignada",
            "Usar subnets privadas + NAT"))

    if svc.get("enableExecuteCommand"):
        findings.append(Finding(
            Severity.MEDIUM, name, "exec_command",
            "ECS Exec habilitado (acceso interactivo a containers)",
            "Restringir via IAM condition o deshabilitar"))

    taskdef = get_task_definition(ecs, svc.get("taskDefinition", ""))
    if not taskdef:
        return findings

    secrets = env_secrets(taskdef)
    if secrets:
        findings.append(Finding(
            Severity.CRITICAL, name, "env_secrets",
            f"{len(secrets)} env var(s) con patrón de secreto: "
            f"{', '.join(secrets[:5])}",
            "Usar secrets.valueFrom → Secrets Manager"))

    for c in taskdef.get("containerDefinitions", []):
        cname = c.get("name", "?")
        if c.get("privileged"):
            findings.append(Finding(
                Severity.CRITICAL, name, "privileged",
                f"Container '{cname}' privileged=true",
                "Quitar privileged"))
        if not c.get("user"):
            findings.append(Finding(
                Severity.LOW, name, "root_user",
                f"Container '{cname}' sin user definido (root)",
                "Definir user no-root"))
        if not c.get("readonlyRootFilesystem"):
            findings.append(Finding(
                Severity.LOW, name, "rootfs_rw",
                f"Container '{cname}' root filesystem escribible",
                "readonlyRootFilesystem=true"))
        log = c.get("logConfiguration", {})
        if log.get("logDriver") in (None, "none"):
            findings.append(Finding(
                Severity.MEDIUM, name, "logging",
                f"Container '{cname}' sin log driver",
                "awslogs → CloudWatch"))

    for vol in taskdef.get("volumes", []):
        efs = vol.get("efsVolumeConfiguration", {})
        if efs and efs.get("transitEncryption") != "ENABLED":
            findings.append(Finding(
                Severity.MEDIUM, name, "efs_encryption",
                f"Vol EFS '{vol['name']}' sin cifrado en tránsito",
                "transitEncryption=ENABLED"))
    return findings


def get_args():
    p = argparse.ArgumentParser(description="Auditoría ECS")
    p.add_argument("--profile", "-p", default="default")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("--cluster", "-c", default="")
    p.add_argument("--severity", choices=["critical", "high",
                                          "medium", "low", "all"],
                   default="all")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    ecs = make_session(args.profile, args.region).client("ecs")
    clusters = [args.cluster] if args.cluster else list_clusters(ecs)

    findings: List[Finding] = []
    svc_count = 0
    for cluster in clusters:
        for svc in describe_services(
                ecs, cluster, list_services(ecs, cluster)):
            svc_count += 1
            findings.extend(audit_service(ecs, svc))

    sev = SEV_ORDER.get(args.severity, 99)
    visible = sorted(
        [f for f in findings if SEV_ORDER[f.severity.value] <= sev],
        key=lambda f: SEV_ORDER[f.severity.value])

    if console:
        from rich.table import Table
        table = Table(title="ECS Security Audit",
                      header_style="bold red")
        for col in ["Sev", "Servicio", "Check", "Hallazgo"]:
            table.add_column(col)
        style = {"critical": "red bold", "high": "red",
                 "medium": "yellow", "low": "dim"}
        for f in visible[:60]:
            table.add_row(f"[{style[f.severity.value]}]"
                          f"{f.severity.value}[/{style[f.severity.value]}]",
                          f.service[:30], f.check, f.message[:60])
        console.print(table)
    else:
        for f in visible:
            print(f"[{f.severity.value}] {f.service}/{f.check}: "
                  f"{f.message}")

    counts = {s.value: len([f for f in findings
                           if f.severity == s]) for s in Severity}
    _print(f"\nServicios: {svc_count} | critical: "
           f"{counts['critical']} | high: {counts['high']} | "
           f"medium: {counts['medium']} | low: {counts['low']}",
           "red" if counts["critical"] else
           ("yellow" if counts["high"] else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"ecs_security_{ts}.{args.output}"
        data = [{"severity": f.severity.value, "service": f.service,
                 "check": f.check, "message": f.message,
                 "remediation": f.remediation} for f in findings]
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "summary": counts, "findings": data},
                indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as fo:
                w = csv.DictWriter(fo, fieldnames=[
                    "severity", "service", "check", "message"])
                w.writeheader()
                for d in data:
                    w.writerow({k: d[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if counts["critical"] else 0)


if __name__ == "__main__":
    main()
