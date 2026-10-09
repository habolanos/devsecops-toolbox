#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS App Runner Checker — Tool 52

Equivalente de GCP Cloud Run Checker: inventario y salud de servicios
App Runner (el servicio AWS más análogo a Cloud Run):

- Servicios: estado (RUNNING/PAUSED/CREATE_FAILED...), URL, edad
- Fuente: imagen ECR (privada/pública) vs código GitHub, auto-deploys
- Egress: conector VPC vs público
- Health check, instancia (vCPU/mem), autoscaling config
- Hallazgos: no RUNNING, CREATE_FAILED, auto-deploy deshabilitado,
  health check débil

Uso:
    python aws_apprunner_checker.py --profile p --region us-east-1
    python aws_apprunner_checker.py -o json
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / "ecs"))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session)

__version__ = "1.0.0"


def list_services(client) -> List[Dict]:
    """list_services paginado → summaries."""
    out = []
    for page in client.get_paginator("list_services").paginate():
        out.extend(page.get("ServiceSummaryList", []))
    return out


def describe_service(client, arn: str) -> Dict:
    try:
        return client.describe_service(ServiceArn=arn)["Service"]
    except Exception as e:
        return {"ServiceName": arn.rsplit("/", 1)[-2],
                "Status": "DESCRIBE_ERROR", "_error": str(e)}


def source_info(svc: Dict) -> Dict:
    src = svc.get("SourceConfiguration", {})
    img = src.get("ImageRepository")
    code = src.get("CodeRepository")
    auto = src.get("AutoDeploymentsEnabled", False)
    if img:
        repo_type = img.get("ImageRepositoryType", "?")
        return {"type": f"image/{repo_type}",
                "ref": img.get("ImageIdentifier", "?"),
                "auto_deploy": auto}
    if code:
        return {"type": "code/github",
                "ref": code.get("RepositoryUrl", "?"),
                "auto_deploy": auto}
    return {"type": "?", "ref": "?", "auto_deploy": auto}


def analyze(svc: Dict) -> Dict:
    """Normaliza el servicio + hallazgos."""
    name = svc.get("ServiceName", "?")
    status = svc.get("Status", "?")
    src = source_info(svc)
    net = svc.get("NetworkConfiguration", {})
    egress = net.get("EgressConfiguration", {})
    egress_type = egress.get("EgressType", "DEFAULT")
    inst = svc.get("InstanceConfiguration", {})
    hc = svc.get("HealthCheckConfiguration", {})

    findings = []
    if status == "CREATE_FAILED":
        findings.append("🔴 CREATE_FAILED — último deploy falló")
    elif status not in ("RUNNING", "OPERATION_IN_PROGRESS",
                        "PAUSED"):
        findings.append(f"🟡 Estado inusual: {status}")
    if status == "PAUSED":
        findings.append("🟡 Pausado — posible servicio olvidado")
    if src["type"].startswith("image") and not src["auto_deploy"]:
        findings.append("🟡 Auto-deploys deshabilitados en imagen — "
                        "deploy manual requerido")
    if egress_type == "DEFAULT":
        findings.append("ℹ️ Egress público (sin VPC connector)")
    if hc.get("Protocol") in (None, "TCP") and \
            hc.get("Interval", 5) > 10:
        findings.append("🟡 Health check con intervalo largo")

    age_days = None
    created = svc.get("CreatedAt")
    if created:
        if not created.tzinfo:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created).days

    return {
        "service": name, "status": status,
        "url": svc.get("ServiceUrl", ""),
        "source": src, "egress": egress_type,
        "vcpu": inst.get("Cpu"), "memory": inst.get("Memory"),
        "health_protocol": hc.get("Protocol", "TCP"),
        "age_days": age_days,
        "observability": bool(
            svc.get("ObservabilityConfiguration", {})
            .get("ObservabilityEnabled")),
        "findings": findings,
        "error": svc.get("_error"),
    }


def get_args():
    p = argparse.ArgumentParser(description="App Runner checker")
    p.add_argument("--profile", "-p", default="default")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    client = make_session(args.profile, args.region) \
        .client("apprunner")

    summaries = list_services(client)
    services = [analyze(describe_service(
        client, s["ServiceArn"])) for s in summaries]

    # VPC connectors (contexto adicional)
    try:
        vpcs = client.list_vpc_connectors() \
            .get("VpcConnectors", [])
        vpc_names = [v["VpcConnectorName"] for v in vpcs]
    except Exception:
        vpc_names = []

    issues = [s for s in services if s["status"] == "CREATE_FAILED"
              or s.get("error")]

    if console:
        from rich.table import Table
        table = Table(title="App Runner Services",
                      header_style="bold cyan")
        for col in ["Servicio", "Estado", "Fuente", "Egress",
                    "URL"]:
            table.add_column(col)
        style = {"RUNNING": "green", "PAUSED": "yellow",
                 "CREATE_FAILED": "red"}
        for s in services:
            color = style.get(s["status"], "dim")
            table.add_row(
                s["service"][:35],
                f"[{color}]{s['status']}[/{color}]",
                f"{s['source']['type']}"
                f"{' ↻' if s['source']['auto_deploy'] else ''}",
                s["egress"], (s["url"] or "—")[:40])
        console.print(table)
        for s in services:
            for f in s["findings"]:
                console.print(f"  {f} [dim]({s['service']})[/dim]")
        if vpc_names:
            console.print(f"[dim]VPC connectors: "
                          f"{', '.join(vpc_names[:5])}[/dim]")
    else:
        for s in services:
            print(f"{s['service']}: {s['status']} {s['url']}")

    _print(f"\nServicios: {len(services)} | con problemas: "
           f"{len(issues)}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"apprunner_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "services": services,
                "vpc_connectors": vpc_names}, indent=2, default=str),
                encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["service", "status", "url",
                            "source_type", "source_ref",
                            "auto_deploy", "egress", "findings"])
                for s in services:
                    w.writerow([s["service"], s["status"], s["url"],
                                s["source"]["type"],
                                s["source"]["ref"],
                                s["source"]["auto_deploy"],
                                s["egress"],
                                "; ".join(s["findings"])])
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
