#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Traffic Analyzer — Tool 49

Análisis de tráfico y despliegues de servicios ECS, equivalente a
Cloud Run Traffic Analyzer de GCP (que analiza traffic split entre
revisions):

- Deployments activos por servicio: PRIMARY vs ACTIVE (blue/green)
- Distribución: running tasks por deployment y su task definition
- Rollouts en curso vs completados vs fallidos
- Request counts vía CloudWatch (target groups ALB) si hay LBs

Uso:
    python aws_ecs_traffic_analyzer.py --profile p \\
        --region us-east-1 --cluster prod
    python aws_ecs_traffic_analyzer.py -o json
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session,
    list_clusters, list_services, describe_services,
    service_lb_targets)

__version__ = "1.0.0"


def tg_requests(cw, tg_arn: str, lb_arn: str, hours: int) -> float:
    """RequestCount de un target group en la ventana.

    Dimensiones CW: LoadBalancer="app/<name>/<id>",
    TargetGroup="targetgroup/<name>/<id>" — extraídas de los ARNs.
    """
    lb_dim = lb_arn.split("loadbalancer/")[-1]      # app/name/id
    tg_dim = f"targetgroup/{tg_arn.split('targetgroup/')[-1]}"
    end = datetime.now(timezone.utc)
    try:
        resp = cw.get_metric_statistics(
            Namespace="AWS/ApplicationELB",
            MetricName="RequestCount",
            Dimensions=[{"Name": "LoadBalancer", "Value": lb_dim},
                        {"Name": "TargetGroup", "Value": tg_dim}],
            StartTime=end - timedelta(hours=hours), EndTime=end,
            Period=3600, Statistics=["Sum"])
        return sum(p["Sum"] for p in resp.get("Datapoints", []))
    except Exception:
        return 0.0


def tg_lb_arn(elbv2, tg_arn: str) -> str:
    """LB ARN asociado a un target group."""
    try:
        tgs = elbv2.describe_target_groups(
            TargetGroupArns=[tg_arn]).get("TargetGroups", [])
        for tg in tgs:
            for arn in tg.get("LoadBalancerArns", []):
                return arn
    except Exception:
        pass
    return ""


def analyze_service(cw, elbv2, svc: Dict, hours: int) -> Dict:
    deployments = []
    for d in svc.get("deployments", []):
        deployments.append({
            "id": d.get("id", "").rsplit("/", 1)[-1],
            "status": d.get("status"),          # PRIMARY/ACTIVE
            "rollout": d.get("rolloutState"),
            "desired": d.get("desiredCount", 0),
            "running": d.get("runningCount", 0),
            "taskdef": d.get("taskDefinition", "")
            .rsplit("/", 1)[-1],
        })
    requests = 0.0
    for lb in svc.get("loadBalancers", []):
        tg_arn = lb.get("targetGroupArn")
        if not tg_arn:
            continue
        lb_arn = tg_lb_arn(elbv2, tg_arn)
        if lb_arn:
            requests += tg_requests(cw, tg_arn, lb_arn, hours)
    return {
        "service": svc["serviceName"],
        "cluster": svc.get("_cluster", ""),
        "deployments": deployments,
        "active_rollouts": len([d for d in deployments
                                if d["rollout"] == "IN_PROGRESS"]),
        "failed_rollouts": len([d for d in deployments
                                if d["rollout"] == "FAILED"]),
        "traffic_requests": int(requests),
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Análisis de tráfico/despliegues ECS")
    p.add_argument("--profile", "-p", default="default")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("--cluster", "-c", default="")
    p.add_argument("--hours", type=int, default=24)
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
    cw = session.client("cloudwatch")
    elbv2 = session.client("elbv2")
    clusters = [args.cluster] if args.cluster else list_clusters(ecs)

    results = []
    for cluster in clusters:
        for svc in describe_services(
                ecs, cluster, list_services(ecs, cluster)):
            svc["_cluster"] = cluster
            results.append(
                analyze_service(cw, elbv2, svc, args.hours))

    if console:
        from rich.table import Table
        table = Table(title="ECS Traffic & Deployments",
                      header_style="bold cyan")
        for col in ["Servicio", "Cluster", "Deployments",
                    "Rollouts", "Tasks por deploy"]:
            table.add_column(col)
        for r in results:
            task_breakdown = "; ".join(
                f"{d['status']}:{d['running']}/{d['desired']}"
                for d in r["deployments"]) or "—"
            color = "red" if r["failed_rollouts"] else \
                    "yellow" if r["active_rollouts"] else "green"
            table.add_row(r["service"][:35], r["cluster"][:18],
                          str(len(r["deployments"])),
                          f"[{color}]{r['active_rollouts']}▶ "
                          f"{r['failed_rollouts']}✗[/{color}]",
                          task_breakdown)
        console.print(table)
    else:
        for r in results:
            print(f"{r['service']}: {r['deployments']}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"ecs_traffic_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "services": results}, indent=2, default=str),
                encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["service", "cluster", "deployments",
                            "active_rollouts", "failed_rollouts"])
                for r in results:
                    w.writerow([r["service"], r["cluster"],
                                len(r["deployments"]),
                                r["active_rollouts"],
                                r["failed_rollouts"]])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
