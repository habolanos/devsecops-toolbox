#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS VPC IP Diagnostic — Tool 50

Diagnóstico de capacidad de IPs para servicios ECS (awsvpc mode =
Fargate), equivalente a Cloud Run VPC IP Diagnostic de GCP:

- Por servicio: subnets configuradas → IPs disponibles vs desired tasks
- Diagnóstico: subnet saturada puede impedir lanzar tasks
  (síntoma típico: tasks atascados en PROVISIONING)
- Tasks actuales vs headroom por subnet
- Recomendaciones cuando available < desired

Uso:
    python aws_ecs_vpc_ip_diagnostic.py --profile p \\
        --region us-east-1 --cluster prod
"""

import argparse
import csv
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session,
    list_clusters, list_services, describe_services)

__version__ = "1.0.0"

AWS_RESERVED_IPS = 5


def diagnose_service(svc: Dict, subnets_map: Dict) -> Dict:
    net = svc.get("networkConfiguration", {}) \
        .get("awsvpcConfiguration", {})
    subnet_ids = net.get("subnets", [])
    desired = svc.get("desiredCount", 0)
    running = svc.get("runningCount", 0)

    detail, min_headroom = [], None
    for sid in subnet_ids:
        sn = subnets_map.get(sid)
        if not sn:
            detail.append({"subnet": sid, "error": "no encontrada"})
            continue
        usable = sn["usable"]
        available = sn["available"]
        headroom = available - max(0, desired - running)
        min_headroom = headroom if min_headroom is None else \
            min(min_headroom, headroom)
        detail.append({"subnet": sid, "cidr": sn["cidr"],
                       "available": available, "usable": usable,
                       "headroom": headroom})

    issues = []
    if not subnet_ids:
        issues.append("servicio sin awsvpcConfiguration (EC2/bridge)")
    if min_headroom is not None:
        if min_headroom < 0:
            issues.append(f"🔴 IPs insuficientes: headroom "
                          f"{min_headroom} — tasks no podrán "
                          "obtener ENI/IP")
        elif min_headroom < 10:
            issues.append(f"🟡 Headroom bajo: {min_headroom} IPs")
    return {
        "service": svc["serviceName"],
        "cluster": svc.get("_cluster", ""),
        "desired": desired, "running": running,
        "subnets": detail, "issues": issues,
        "status": "CRITICAL" if any("🔴" in i for i in issues)
                  else ("WARNING" if issues else "OK"),
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Diagnóstico de IPs para servicios ECS")
    p.add_argument("--profile", "-p", default="default")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("--cluster", "-c", default="")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    session = make_session(args.profile, args.region)
    ecs = session.client("ecs")
    ec2 = session.client("ec2")
    clusters = [args.cluster] if args.cluster else list_clusters(ecs)

    services = []
    for cluster in clusters:
        for svc in describe_services(
                ecs, cluster, list_services(ecs, cluster)):
            svc["_cluster"] = cluster
            services.append(svc)

    # Mapa de subnets
    subnet_ids = {sid for svc in services
                  for sid in svc.get("networkConfiguration", {})
                  .get("awsvpcConfiguration", {})
                  .get("subnets", [])}
    subnets_map = {}
    if subnet_ids:
        for sn in ec2.describe_subnets(
                SubnetIds=list(subnet_ids)).get("Subnets", []):
            total = ipaddress.ip_network(
                sn["CidrBlock"]).num_addresses
            subnets_map[sn["SubnetId"]] = {
                "cidr": sn["CidrBlock"], "total": total,
                "usable": max(0, total - AWS_RESERVED_IPS),
                "available": sn.get("AvailableIpAddressCount", 0)}

    results = [diagnose_service(s, subnets_map) for s in services]
    issues = [r for r in results if r["status"] != "OK"]

    if console:
        from rich.table import Table
        table = Table(title="ECS VPC IP Diagnostic",
                      header_style="bold cyan")
        for col in ["Servicio", "Run/Des", "Subnets",
                    "Min headroom", "Estado"]:
            table.add_column(col)
        style = {"OK": "green", "WARNING": "yellow",
                 "CRITICAL": "red"}
        for r in results:
            headroom = min((s.get("headroom", 9999)
                            for s in r["subnets"]), default=None)
            color = style.get(r["status"], "")
            table.add_row(r["service"][:35],
                          f"{r['running']}/{r['desired']}",
                          str(len(r["subnets"])),
                          str(headroom) if headroom is not None
                          else "—",
                          f"[{color}]{r['status']}[/{color}]")
        console.print(table)
        for r in results:
            for i in r["issues"]:
                console.print(f"  {i} [dim]({r['service']})[/dim]")
    else:
        for r in results:
            print(f"{r['service']}: {r['status']} {r['issues']}")

    _print(f"\nServicios: {len(results)} | con issues: "
           f"{len(issues)}",
           "red" if any(r["status"] == "CRITICAL" for r in results)
           else ("yellow" if issues else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"ecs_vpc_ip_diag_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "services": results}, indent=2, default=str),
                encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["service", "cluster", "desired",
                            "running", "subnets", "status"])
                for r in results:
                    w.writerow([r["service"], r["cluster"],
                                r["desired"], r["running"],
                                len(r["subnets"]), r["status"]])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
