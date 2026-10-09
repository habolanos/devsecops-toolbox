#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Deployment Validator — Tool 47

Valida la configuración de despliegue de servicios ECS, equivalente a
Cloud Run Deployment Validator de GCP:

- Deployment config: circuit breaker, min healthy / max percent
- Health check grace period con LB configurado
- Imágenes: tag `latest` (mutable), imagen existe en ECR
- Container essentials: memoria CPU límites razonables, healthCheck
- Placement strategies y capacity providers
- Hallazgos con severidad + remediación

Uso:
    python aws_ecs_deployment_validator.py --profile p \\
        --region us-east-1 --service my-svc --cluster prod
    python aws_ecs_deployment_validator.py --cluster prod -o json
"""

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session,
    list_clusters, list_services, describe_services,
    get_task_definition, service_lb_targets)

__version__ = "1.0.0"


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    severity: Severity
    service: str
    check: str
    message: str
    remediation: str = ""


def image_uri(container: Dict) -> str:
    return container.get("image", "")


def validate_service(ecs, ecr, svc: Dict) -> List[Finding]:
    findings = []
    name = svc["serviceName"]

    # Circuit breaker
    dc = svc.get("deploymentConfiguration", {})
    if not dc.get("deploymentCircuitBreaker", {}).get("enable"):
        findings.append(Finding(
            Severity.WARNING, name, "circuit_breaker",
            "Deployment circuit breaker deshabilitado — deploys "
            "fallidos no hacen rollback",
            "Habilitar enable+rollback en deploymentConfiguration"))

    # Health check grace con LB
    if service_lb_targets(svc) and not svc.get(
            "healthCheckGracePeriodSeconds"):
        findings.append(Finding(
            Severity.WARNING, name, "health_grace",
            "Servicio con LB sin healthCheckGracePeriodSeconds — "
            "tasks pueden ser drenados antes de estar sanos",
            "--health-check-grace-period-seconds ≥60"))

    taskdef = get_task_definition(ecs, svc.get("taskDefinition", ""))
    if not taskdef:
        findings.append(Finding(
            Severity.CRITICAL, name, "taskdef",
            "Task definition no accesible"))
        return findings

    for c in taskdef.get("containerDefinitions", []):
        img = image_uri(c)
        cname = c.get("name", "?")
        if img.endswith(":latest") or ":" not in img:
            findings.append(Finding(
                Severity.WARNING, name, "image_tag",
                f"Container '{cname}' usa tag mutable: {img}",
                "Fijar versión/tag inmutable"))
        if ".dkr.ecr." in img and ecr:
            repo_tag = img.split("/", 1)[-1]
            repo, _, tag = repo_tag.partition(":")
            try:
                ecr.describe_images(repositoryName=repo,
                                    imageIds=[{"imageTag": tag}])
            except Exception:
                findings.append(Finding(
                    Severity.CRITICAL, name, "image_missing",
                    f"Imagen {repo}:{tag or 'latest'} NO existe en "
                    f"ECR",
                    "Verificar push/pipeline de la imagen"))
        if c.get("essential", True) and not c.get("healthCheck"):
            findings.append(Finding(
                Severity.INFO, name, "healthcheck",
                f"Container essential '{cname}' sin HEALTHCHECK",
                "Definir healthCheck en la task definition"))
        if c.get("memory") is None and \
                c.get("memoryReservation") is None and \
                not taskdef.get("memory"):
            findings.append(Finding(
                Severity.WARNING, name, "memory",
                f"Container '{cname}' sin límite de memoria",
                "Definir memory o memoryReservation"))

    if not svc.get("capacityProviderStrategy") and \
            not svc.get("launchType"):
        findings.append(Finding(
            Severity.WARNING, name, "launch",
            "Sin launchType ni capacityProviderStrategy"))
    return findings


def get_args():
    p = argparse.ArgumentParser(
        description="Valida despliegues de servicios ECS")
    p.add_argument("--profile", "-p", default="default")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("--cluster", "-c", required=True)
    p.add_argument("--service", "-s", default="",
                   help="Validar solo este servicio (vacío = todos)")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    session = make_session(args.profile, args.region)
    ecs = session.client("ecs")
    ecr = session.client("ecr")

    names = [args.service] if args.service else \
        list_services(ecs, args.cluster)
    services = describe_services(ecs, args.cluster, names)

    findings: List[Finding] = []
    for svc in services:
        findings.extend(validate_service(ecs, ecr, svc))

    visible = sorted(findings,
                     key=lambda f: SEV_ORDER[f.severity.value])
    if console:
        from rich.table import Table
        table = Table(title=f"ECS Deployment Validation — "
                            f"{args.cluster}", header_style="bold cyan")
        for col in ["Sev", "Servicio", "Check", "Hallazgo"]:
            table.add_column(col)
        style = {"critical": "red", "warning": "yellow",
                 "info": "dim"}
        for f in visible[:60]:
            table.add_row(
                f"[{style[f.severity.value]}]{f.severity.value}"
                f"[/{style[f.severity.value]}]",
                f.service[:30], f.check, f.message[:60])
        console.print(table)
        for f in visible:
            if f.remediation and f.severity != Severity.INFO:
                console.print(f"  [dim]💡 {f.service}/{f.check}: "
                              f"{f.remediation}[/dim]")
    else:
        for f in visible:
            print(f"[{f.severity.value}] {f.service}/{f.check}: "
                  f"{f.message}")

    crit = len([f for f in findings
                if f.severity == Severity.CRITICAL])
    _print(f"\nServicios: {len(services)} | critical: {crit} | "
           f"findings: {len(findings)}",
           "red" if crit else ("yellow" if findings else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"ecs_deploy_validation_{ts}.{args.output}"
        data = [{"severity": f.severity.value,
                 "service": f.service, "check": f.check,
                 "message": f.message,
                 "remediation": f.remediation} for f in findings]
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "cluster": args.cluster,
                "services": len(services), "findings": data},
                indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as fo:
                w = csv.DictWriter(fo, fieldnames=[
                    "severity", "service", "check", "message"])
                w.writeheader()
                for d in data:
                    w.writerow({k: d[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if crit else 0)


if __name__ == "__main__":
    main()
