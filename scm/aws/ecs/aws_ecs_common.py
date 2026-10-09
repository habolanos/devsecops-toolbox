#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Common — helpers compartidos para la suite ECS (tools 44-51).

Equivalente a los helpers internos de gcp/cloud-run/: listado de
clusters/servicios, task definitions y target health.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

SECRET_KEY_PATTERN = (
    "pass", "secret", "token", "api_key", "apikey",
    "private_key", "credential", "pwd",
)

EOL_PLATFORMS = {"1.3.0", "1.4.0"}


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


def make_session(profile: str, region: str):
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 no instalado")
    return boto3.Session(profile_name=profile, region_name=region)


def list_clusters(ecs) -> List[str]:
    arns = []
    for page in ecs.get_paginator("list_clusters").paginate():
        arns.extend(page.get("clusterArns", []))
    return [a.rsplit("/", 1)[-1] for a in arns]


def list_services(ecs, cluster: str) -> List[str]:
    arns = []
    for page in ecs.get_paginator("list_services").paginate(
            cluster=cluster):
        arns.extend(page.get("serviceArns", []))
    return [a.rsplit("/", 1)[-1] for a in arns]


def describe_services(ecs, cluster: str,
                      services: List[str]) -> List[Dict]:
    """describe_services por lotes de 10 (límite API)."""
    described = []
    for i in range(0, len(services), 10):
        resp = ecs.describe_services(
            cluster=cluster, services=services[i:i + 10])
        described.extend(resp.get("services", []))
    return described


def get_task_definition(ecs, arn: str) -> Optional[Dict]:
    try:
        return ecs.describe_task_definition(
            taskDefinition=arn)["taskDefinition"]
    except ClientError:
        return None


def all_services(ecs, clusters: Optional[List[str]] = None
                 ) -> List[Dict]:
    """Todos los servicios de todos los clusters (o de los dados)."""
    result = []
    for cluster in clusters or list_clusters(ecs):
        services = list_services(ecs, cluster)
        for svc in describe_services(ecs, cluster, services):
            svc["_cluster"] = cluster
            result.append(svc)
    return result


def env_secrets(taskdef: Dict) -> List[str]:
    """Nombres de env vars con patrones de secreto en una task def."""
    found = []
    for c in taskdef.get("containerDefinitions", []):
        for env in c.get("environment", []):
            name = env.get("name", "").lower()
            if any(p in name for p in SECRET_KEY_PATTERN):
                found.append(env["name"])
    return found


def service_status(svc: Dict) -> str:
    desired = svc.get("desiredCount", 0)
    running = svc.get("runningCount", 0)
    status = svc.get("status", "")
    if status != "ACTIVE":
        return "INACTIVE"
    if desired == 0:
        return "DRAINED"
    if running == 0:
        return "CRITICAL"
    if running < desired:
        return "DEGRADED"
    return "HEALTHY"


def service_lb_targets(svc: Dict) -> List[str]:
    """Target group ARNs asociados al servicio."""
    return [lb["targetGroupArn"] for lb in
            svc.get("loadBalancers", []) if lb.get("targetGroupArn")]


def events_summary(svc: Dict, limit: int = 5) -> List[Dict]:
    return [{"time": str(e.get("createdAt", ""))[:19],
             "message": e.get("message", "")}
            for e in svc.get("events", [])[:limit]]


def is_fargate(svc: Dict) -> bool:
    if svc.get("launchType") == "FARGATE":
        return True
    return any("FARGATE" in cp.get("capacityProvider", "")
               for cp in svc.get("capacityProviderStrategy", []))


def task_cpu_memory(taskdef: Dict) -> Dict:
    """CPU (units) y memoria (MB) a nivel task o suma de containers."""
    cpu = taskdef.get("cpu")
    mem = taskdef.get("memory")
    if cpu is None or mem is None:
        cpu = sum(int(c.get("cpu", 0)) for c in
                  taskdef.get("containerDefinitions", []))
        mem = sum(int(c.get("memory", 0) or c.get(
            "memoryReservation", 0)) for c in
            taskdef.get("containerDefinitions", []))
    return {"cpu_units": int(cpu or 0),
            "memory_mb": int(mem or 0)}
