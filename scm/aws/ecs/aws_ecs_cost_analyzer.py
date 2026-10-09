#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Cost Analyzer — Tool 46

Costos estimados de servicios Fargate, equivalente a Cloud Run Cost
Analyzer de GCP:

- Por servicio: tasks running × vCPU/GB de la task definition
- Estimación mensual: vCPU-h ($0.04048/h) + GB-h ($0.004445/h)
- Servicios sobredimensionados (desired alto con recursos grandes)
- Servicios draineados (desired=0) y clusters vacíos

Uso:
    python aws_ecs_cost_analyzer.py --profile p --region us-east-1
    python aws_ecs_cost_analyzer.py -o json
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
    get_task_definition, task_cpu_memory, is_fargate)

__version__ = "1.0.0"

# Precios Fargate us-east-1 referenciales
VCPU_PER_HOUR = 0.04048
GB_PER_HOUR = 0.004445
HOURS_MONTH = 730


def estimate_service_cost(svc: Dict, taskdef: Dict) -> Dict:
    """Estimación mensual de un servicio Fargate."""
    res = task_cpu_memory(taskdef)
    vcpu = res["cpu_units"] / 1024.0
    gb = res["memory_mb"] / 1024.0
    tasks = svc.get("runningCount", 0)
    monthly = tasks * (vcpu * VCPU_PER_HOUR + gb * GB_PER_HOUR) \
        * HOURS_MONTH
    return {"vcpu_per_task": round(vcpu, 2),
            "gb_per_task": round(gb, 2), "tasks": tasks,
            "monthly_estimate": round(monthly, 2)}


def get_args():
    p = argparse.ArgumentParser(description="Costos Fargate ECS")
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

    results = []
    for cluster in clusters:
        for svc in describe_services(
                ecs, cluster, list_services(ecs, cluster)):
            taskdef = get_task_definition(
                ecs, svc.get("taskDefinition", "")) or {}
            cost = estimate_service_cost(svc, taskdef)
            recs = []
            if not is_fargate(svc):
                recs.append("EC2 launch — fuera de estimación "
                            "Fargate")
            if svc.get("desiredCount", 0) == 0:
                recs.append("desired=0 — candidato a eliminar")
            if cost["monthly_estimate"] > 100:
                recs.append("costo >$100/mes — revisar sizing")
            results.append({
                "service": svc["serviceName"], "cluster": cluster,
                "launch_type": svc.get("launchType")
                or "capacity-provider",
                "desired": svc.get("desiredCount", 0),
                **cost, "recommendations": recs})

    results.sort(key=lambda r: -r["monthly_estimate"])
    total = round(sum(r["monthly_estimate"] for r in results), 2)

    if console:
        from rich.table import Table
        table = Table(title="ECS Fargate Cost (mensual est.)",
                      header_style="bold cyan")
        for col in ["Servicio", "Tasks", "vCPU", "GB", "$/mes"]:
            table.add_column(col)
        for r in results[:30]:
            color = "red" if r["monthly_estimate"] > 100 else \
                    "yellow" if r["monthly_estimate"] > 20 else "green"
            table.add_row(r["service"][:35], str(r["tasks"]),
                          str(r["vcpu_per_task"]),
                          str(r["gb_per_task"]),
                          f"[{color}]${r['monthly_estimate']}"
                          f"[/{color}]")
        console.print(table)
        for r in results:
            for rec in r["recommendations"]:
                console.print(f"  [yellow]💡 {r['service']}:[/yellow] "
                              f"[dim]{rec}[/dim]")
        console.print(f"\n[bold]Total estimado: ${total}/mes[/bold] "
                      "[dim](precios referenciales us-east-1)[/dim]")
    else:
        for r in results:
            print(f"{r['service']}: ${r['monthly_estimate']}/mes")
        print(f"TOTAL: ${total}/mes")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"ecs_cost_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "total_monthly": total, "services": results},
                indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "service", "cluster", "tasks", "vcpu_per_task",
                    "gb_per_task", "monthly_estimate"])
                w.writeheader()
                for r in results:
                    w.writerow({k: r[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
