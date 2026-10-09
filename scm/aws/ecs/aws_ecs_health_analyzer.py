#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Health Analyzer — Tool 44

Salud de servicios ECS/Fargate, equivalente a Cloud Run Health
Analyzer de GCP:

- Estado por servicio: HEALTHY/DEGRADED/CRITICAL/DRAINED/INACTIVE
  según desired vs running
- Deployments en curso/fallidos (rolloutState)
- Eventos recientes del servicio (timeouts de tasks, drain)
- Tareas detenidas con stoppedReason (OOM, image pull, essential
  container exited)

Uso:
    python aws_ecs_health_analyzer.py --profile p --region us-east-1
    python aws_ecs_health_analyzer.py --cluster prod-ecs -o json
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session,
    list_clusters, list_services, describe_services,
    service_status, events_summary)

__version__ = "1.0.0"

STOPPED_REASON_ALERTS = ("OutOfMemory", "CannotPullContainerError",
                         "EssentialContainerExited", "TaskFailedToStart")


def stopped_tasks(ecs, cluster: str, service: str,
                  limit: int = 5) -> List[Dict]:
    """Tareas detenidas recientes de un servicio con su razón."""
    try:
        arns = ecs.list_tasks(cluster=cluster, serviceName=service,
                              desiredStatus="STOPPED",
                              maxResults=limit).get("taskArns", [])
        if not arns:
            return []
        tasks = ecs.describe_tasks(cluster=cluster,
                                   tasks=arns).get("tasks", [])
        return [{
            "task": t["taskArn"].rsplit("/", 1)[-1],
            "reason": t.get("stoppedReason", "?"),
            "exit_code": next(
                (c.get("exitCode") for c in
                 t.get("containers", [])), None),
        } for t in tasks]
    except Exception:
        return []


def analyze_service(ecs, svc: Dict) -> Dict:
    deployments = svc.get("deployments", [])
    failed = [d for d in deployments
              if d.get("rolloutState") == "FAILED"]
    in_progress = [d for d in deployments
                   if d.get("rolloutState") == "IN_PROGRESS"]
    return {
        "service": svc["serviceName"],
        "cluster": svc.get("_cluster", ""),
        "status": service_status(svc),
        "desired": svc.get("desiredCount", 0),
        "running": svc.get("runningCount", 0),
        "pending": svc.get("pendingCount", 0),
        "launch_type": svc.get("launchType") or "capacity-provider",
        "deployments_in_progress": len(in_progress),
        "deployments_failed": len(failed),
        "stopped_tasks": stopped_tasks(
            ecs, svc.get("_cluster", ""), svc["serviceName"]),
        "recent_events": events_summary(svc),
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Salud de servicios ECS")
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
    ecs = make_session(args.profile, args.region).client("ecs")
    clusters = [args.cluster] if args.cluster else list_clusters(ecs)

    services = []
    for cluster in clusters:
        for svc in describe_services(
                ecs, cluster, list_services(ecs, cluster)):
            svc["_cluster"] = cluster
            services.append(analyze_service(ecs, svc))

    unhealthy = [s for s in services
                 if s["status"] in ("CRITICAL", "DEGRADED")]

    if console:
        from rich.table import Table
        table = Table(title="ECS Health", header_style="bold cyan")
        for col in ["Servicio", "Cluster", "Run/Des", "Deploys",
                    "Estado"]:
            table.add_column(col)
        style = {"HEALTHY": "green", "DEGRADED": "yellow",
                 "CRITICAL": "red", "DRAINED": "dim",
                 "INACTIVE": "dim"}
        for s in services:
            color = style.get(s["status"], "")
            table.add_row(s["service"][:35], s["cluster"][:20],
                          f"{s['running']}/{s['desired']}",
                          f"{s['deployments_in_progress']}▶ "
                          f"{s['deployments_failed']}✗",
                          f"[{color}]{s['status']}[/{color}]")
        console.print(table)
        for s in services:
            for t in s["stopped_tasks"]:
                if any(a in t["reason"] for a in
                       STOPPED_REASON_ALERTS):
                    console.print(
                        f"  [red]⚠ {s['service']}[/red] task "
                        f"{t['task'][:12]}: {t['reason']}"
                        + (f" (exit {t['exit_code']})"
                           if t["exit_code"] is not None else ""))
    else:
        for s in services:
            print(f"{s['service']}: {s['status']} "
                  f"{s['running']}/{s['desired']}")

    _print(f"\nServicios: {len(services)} | unhealthy: "
           f"{len(unhealthy)}",
           "red" if unhealthy else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"ecs_health_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "services": services}, indent=2, default=str),
                encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "service", "cluster", "status", "desired",
                    "running", "deployments_failed"])
                w.writeheader()
                for s in services:
                    w.writerow({k: s[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if unhealthy else 0)


if __name__ == "__main__":
    main()
