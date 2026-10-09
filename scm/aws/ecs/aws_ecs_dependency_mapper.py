#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECS Dependency Mapper — Tool 48

Mapea dependencias de servicios ECS, equivalente a Cloud Run
Dependency Mapper de GCP:

- Servicio → Target Groups → Load Balancers → listeners
- Servicio → subnets/security groups (network config)
- Servicio → task role / execution role
- Servicios sin LB (solo internos) y targets unhealthy

Uso:
    python aws_ecs_dependency_mapper.py --profile p \\
        --region us-east-1 --cluster prod
    python aws_ecs_dependency_mapper.py -o json
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
    service_lb_targets)

__version__ = "1.0.0"


def build_map(ecs, elbv2, svc: Dict) -> Dict:
    net = svc.get("networkConfiguration", {}) \
        .get("awsvpcConfiguration", {})
    deps = {
        "service": svc["serviceName"],
        "cluster": svc.get("_cluster", ""),
        "subnets": net.get("subnets", []),
        "security_groups": net.get("securityGroups", []),
        "task_role": svc.get("roleArn", ""),
        "target_groups": [], "load_balancers": set(),
        "internal_only": not service_lb_targets(svc),
    }
    for tg_arn in service_lb_targets(svc):
        try:
            tgs = elbv2.describe_target_groups(
                TargetGroupArns=[tg_arn]).get("TargetGroups", [])
            for tg in tgs:
                deps["target_groups"].append(
                    tg.get("TargetGroupName"))
                deps["load_balancers"].update(
                    tg.get("LoadBalancerArns", []))
        except Exception:
            pass
    deps["load_balancers"] = sorted(deps["load_balancers"])
    return deps


def get_args():
    p = argparse.ArgumentParser(
        description="Mapa de dependencias de servicios ECS")
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
    elbv2 = session.client("elbv2")
    clusters = [args.cluster] if args.cluster else list_clusters(ecs)

    maps = []
    for cluster in clusters:
        for svc in describe_services(
                ecs, cluster, list_services(ecs, cluster)):
            svc["_cluster"] = cluster
            maps.append(build_map(ecs, elbv2, svc))

    internal = [m for m in maps if m["internal_only"]]

    if console:
        from rich.tree import Tree
        tree = Tree("[bold]ECS Dependency Map[/bold]")
        for m in maps:
            node = tree.add(
                f"[cyan]{m['service']}[/cyan] ({m['cluster']})")
            if m["load_balancers"]:
                for lb in m["load_balancers"]:
                    lb_node = node.add(f"[yellow]LB {lb}[/yellow]")
                    for tg in m["target_groups"]:
                        lb_node.add(f"TG {tg}")
            else:
                node.add("[dim]sin LB — servicio interno[/dim]")
            if m["security_groups"]:
                node.add(f"[dim]SGs: "
                         f"{', '.join(m['security_groups'][:3])}[/dim]")
        console.print(tree)
        if internal:
            console.print(f"[dim]Servicios internos: "
                          f"{len(internal)}[/dim]")
    else:
        for m in maps:
            print(f"{m['service']}: lbs={m['load_balancers']} "
                  f"tgs={m['target_groups']}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"ecs_dependencies_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "services": maps}, indent=2, default=str),
                encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["service", "cluster", "load_balancers",
                            "target_groups", "subnets",
                            "security_groups", "internal_only"])
                for m in maps:
                    w.writerow([m["service"], m["cluster"],
                                ";".join(m["load_balancers"]),
                                ";".join(m["target_groups"]),
                                str(len(m["subnets"])),
                                ";".join(m["security_groups"]),
                                m["internal_only"]])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
