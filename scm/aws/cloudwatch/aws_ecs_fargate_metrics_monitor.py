#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Fargate Metrics Monitor - Tool 41

Obtiene información y métricas de uso de servicios ECS Fargate:
- Request count (últimos 5 min)
- Latencia p95 (ms)
- CPU utilization (%)
- Memory utilization (%)
- Error rate (%)

Homologación de GCP Cloud Run Monitoring.

Uso:
    python aws_ecs_fargate_metrics_monitor.py --profile default --region us-east-1 --cluster my-cluster
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

# Agregar parent directory al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudwatch.aws_cloudwatch_metrics import (
    get_ecs_fargate_metrics_parallel,
    _format_percentage
)

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

__version__ = "1.0.0"
__description__ = "Monitorea métricas de ECS Fargate (homologo a GCP Cloud Run)"


def get_ecs_services(profile: str, region: str, cluster: str) -> List[Dict[str, Any]]:
    """Lista los servicios ECS de un cluster."""
    try:
        session = boto3.Session(profile_name=profile)
        ecs = session.client("ecs", region_name=region)
        response = ecs.list_services(cluster=cluster, maxResults=100, launchType="FARGATE")

        services = []
        for arn in response.get("serviceArns", []):
            # Extraer el nombre del servicio del ARN
            name = arn.split("/")[-1]
            services.append({"name": name, "arn": arn})

        return services
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error al listar servicios ECS: {e}[/red]")
        else:
            print(f"❌ Error al listar servicios ECS: {e}")
        return []


def get_service_info(profile: str, region: str, cluster: str, service_name: str) -> Dict[str, Any]:
    """Obtiene información básica de un servicio ECS."""
    try:
        session = boto3.Session(profile_name=profile)
        ecs = session.client("ecs", region_name=region)
        response = ecs.describe_services(cluster=cluster, services=[service_name])

        for svc in response.get("services", []):
            deployment_config = svc.get("deploymentConfiguration", {})
            desired = svc.get("desiredCount", 0)
            running = svc.get("runningCount", 0)
            pending = svc.get("pendingCount", 0)

            return {
                "name": svc.get("serviceName", service_name),
                "desired": desired,
                "running": running,
                "pending": pending,
                "launch_type": svc.get("launchType", "FARGATE"),
                "status": svc.get("status", "N/A"),
                "task_definition": svc.get("taskDefinition", "N/A").split("/")[-1].split(":")[0]
            }

        return {"name": service_name}
    except Exception:
        return {"name": service_name}


def print_table(cluster: str, region: str, services_info: Dict[str, Any], metrics: Dict[str, Any]):
    """Imprime la tabla de métricas."""
    if RICH_AVAILABLE and console:
        table = Table(
            title=f"ECS Fargate Metrics - Cluster: {cluster} Region: {region}",
            title_style="bold cyan"
        )
        table.add_column("Servicio", style="bold")
        table.add_column("Deseadas")
        table.add_column("Corriendo")
        table.add_column("Pendientes")
        table.add_column("Requests")
        table.add_column("Lat p95", justify="right")
        table.add_column("CPU%", justify="right")
        table.add_column("Mem%", justify="right")
        table.add_column("Errores%", justify="right")

        for name, info in services_info.items():
            m = metrics.get(name, {})
            table.add_row(
                info.get("name", name),
                str(info.get("desired", "N/A")),
                str(info.get("running", "N/A")),
                str(info.get("pending", "N/A")),
                str(m.get("request_count", "N/A")),
                f"{m.get('latency_p95_ms', 'N/A')} ms" if m.get('latency_p95_ms') is not None else "N/A",
                _format_percentage(m.get("cpu_percent")),
                _format_percentage(m.get("memory_percent")),
                _format_percentage(m.get("error_rate_percent"))
            )

        console.print(table)
    else:
        print(f"\nECS Fargate Metrics - Cluster: {cluster} Region: {region}")
        print("-" * 80)
        for name, info in services_info.items():
            m = metrics.get(name, {})
            print(f"{info.get('name', name):30} | "
                  f"D:{info.get('desired', 'N/A'):<4} R:{info.get('running', 'N/A'):<4} "
                  f"Req:{m.get('request_count', 'N/A'):<6} "
                  f"CPU:{_format_percentage(m.get('cpu_percent')):<7} "
                  f"Mem:{_format_percentage(m.get('memory_percent')):<7}")


def main():
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--profile", default="default", help="AWS profile")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--cluster", required=True, help="Nombre del cluster ECS")
    parser.add_argument("-o", "--output", choices=["json", "table"], default="table", help="Output format")
    parser.add_argument("--debug", action="store_true", help="Debug mode")

    args = parser.parse_args()

    services = get_ecs_services(args.profile, args.region, args.cluster)
    if not services:
        print("No se encontraron servicios Fargate en el cluster.")
        sys.exit(0)

    metrics = get_ecs_fargate_metrics_parallel(
        cluster=args.cluster,
        services=services,
        profile=args.profile,
        region=args.region
    )

    services_info = {
        s["name"]: get_service_info(args.profile, args.region, args.cluster, s["name"])
        for s in services
    }

    if args.output == "json":
        output = {
            "cluster": args.cluster,
            "region": args.region,
            "services": [
                {
                    **services_info.get(s["name"], {}),
                    "metrics": metrics.get(s["name"], {})
                }
                for s in services
            ]
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print_table(args.cluster, args.region, services_info, metrics)


if __name__ == "__main__":
    main()
