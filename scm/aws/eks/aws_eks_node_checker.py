#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Node Monitor

Monitorea nodos de clusters EKS: CPU/memoria, estado, taints, condiciones
y capacidad por node group. Usa kubectl + AWS API.
Solo lectura — no modifica ningún recurso.

Equivalente AWS de: gke_monitor_node.py (GKE Node Monitor)

Uso:
    python aws_eks_node_checker.py
    python aws_eks_node_checker.py --cluster my-cluster
    python aws_eks_node_checker.py --cluster my-cluster --sort memory -o json

Autor: Harold Adrian
"""

import sys
import json
import argparse
import subprocess
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict
import time

# --- Directorio de salida centralizado ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 no instalado. Ejecute: pip install boto3")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt
    RICH_AVAILABLE = True
try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS EKS Node Monitor")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--cluster", "-c", default="", help="Nombre del cluster EKS")
    parser.add_argument("--sort", choices=["cpu", "memory", "name", "status"], default="name",
                        help="Ordenar por (default: name)")
    parser.add_argument("--output", "-o", choices=["table", "json", "csv"], default="table")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def list_eks_clusters(session, region: str) -> List[str]:
    try:
        return session.client("eks", region_name=region).list_clusters().get("clusters", [])
    except ClientError:
        return []


def update_kubeconfig(profile: str, region: str, cluster: str) -> bool:
    cmd = ["aws", "eks", "update-kubeconfig", "--name", cluster, "--region", region, "--profile", profile]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def parse_cpu_millicores(cpu_str: str) -> float:
    if not cpu_str or cpu_str == "<unknown>":
        return 0.0
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1])
    try:
        return float(cpu_str) * 1000
    except ValueError:
        return 0.0


def parse_memory_mib(mem_str: str) -> float:
    if not mem_str or mem_str == "<unknown>":
        return 0.0
    if mem_str.endswith("Ki"):
        return float(mem_str[:-2]) / 1024
    if mem_str.endswith("Mi"):
        return float(mem_str[:-2])
    if mem_str.endswith("Gi"):
        return float(mem_str[:-2]) * 1024
    try:
        return float(mem_str) / (1024 * 1024)
    except ValueError:
        return 0.0


def get_node_metrics() -> Dict[str, Dict]:
    """kubectl top nodes"""
    cmd = ["kubectl", "top", "nodes", "--no-headers"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    metrics = {}
    if result.returncode != 0:
        return metrics
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 5:
            name = parts[0]
            metrics[name] = {
                "cpu_millicores": parse_cpu_millicores(parts[1]),
                "cpu_pct": parts[2].rstrip("%"),
                "memory_mib": parse_memory_mib(parts[3]),
                "memory_pct": parts[4].rstrip("%"),
                "cpu_raw": parts[1],
                "memory_raw": parts[3],
            }
    return metrics


def get_nodes_detail() -> List[Dict]:
    """kubectl get nodes -o json"""
    cmd = ["kubectl", "get", "nodes", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    nodes = []
    now = datetime.now(timezone.utc)
    for item in data.get("items", []):
        meta = item.get("metadata", {})
        labels = meta.get("labels", {})
        spec = item.get("spec", {})
        status = item.get("status", {})
        capacity = status.get("capacity", {})
        allocatable = status.get("allocatable", {})

        conditions = {c["type"]: c["status"] for c in status.get("conditions", [])}
        ready = conditions.get("Ready", "False") == "True"

        taints = [f"{t.get('key')}={t.get('value', '')}:{t.get('effect', '')}"
                  for t in spec.get("taints", [])]

        created = meta.get("creationTimestamp", "")
        age_days = None
        if created:
            try:
                from datetime import datetime as dt
                created_dt = dt.fromisoformat(created.replace("Z", "+00:00"))
                age_days = (now - created_dt).days
            except Exception:
                pass

        instance_type = labels.get("node.kubernetes.io/instance-type",
                                   labels.get("beta.kubernetes.io/instance-type", ""))
        zone = labels.get("topology.kubernetes.io/zone",
                          labels.get("failure-domain.beta.kubernetes.io/zone", ""))
        node_group = labels.get("eks.amazonaws.com/nodegroup", "")

        findings = []
        if not ready:
            findings.append("NotReady")
        if conditions.get("MemoryPressure") == "True":
            findings.append("MemoryPressure")
        if conditions.get("DiskPressure") == "True":
            findings.append("DiskPressure")
        if conditions.get("PIDPressure") == "True":
            findings.append("PIDPressure")
        if taints:
            findings.append(f"Taints: {len(taints)}")

        nodes.append({
            "name": meta.get("name", ""),
            "status": "Ready" if ready else "NotReady",
            "instance_type": instance_type,
            "zone": zone,
            "node_group": node_group,
            "os_image": status.get("nodeInfo", {}).get("osImage", ""),
            "kernel_version": status.get("nodeInfo", {}).get("kernelVersion", ""),
            "kubelet_version": status.get("nodeInfo", {}).get("kubeletVersion", ""),
            "capacity_cpu": parse_cpu_millicores(capacity.get("cpu", "0")) * 1000,
            "capacity_memory_mib": parse_memory_mib(capacity.get("memory", "0Ki")),
            "allocatable_cpu": parse_cpu_millicores(allocatable.get("cpu", "0")) * 1000,
            "allocatable_memory_mib": parse_memory_mib(allocatable.get("memory", "0Ki")),
            "taints": taints,
            "age_days": age_days,
            "findings": findings,
        })
    return nodes


def pct_color(value: float) -> str:
    if value > 80:
        return "red"
    if value > 60:
        return "yellow"
    return "green"


def display_table_rich(nodes: List[Dict], metrics: Dict[str, Dict]):
    table = Table(
        title=f"🖥️  EKS Nodes ({len(nodes)} nodos)",
        header_style="bold white on dark_green",
        show_lines=False,
        box=box.SIMPLE_HEAVY,
    )
    table.add_column("Nodo", style="cyan", min_width=30)
    table.add_column("Estado", width=10)
    table.add_column("Tipo", width=16)
    table.add_column("Node Group", style="dim", width=22)
    table.add_column("CPU uso", justify="right", width=9)
    table.add_column("CPU %", justify="right", width=7)
    table.add_column("MEM uso", justify="right", width=10)
    table.add_column("MEM %", justify="right", width=7)
    table.add_column("Zona", style="dim", width=14)
    table.add_column("Findings", min_width=18)

    for node in nodes:
        m = metrics.get(node["name"], {})
        cpu_raw = m.get("cpu_raw", "—")
        mem_raw = m.get("memory_raw", "—")
        cpu_pct_val = float(m.get("cpu_pct", 0) or 0)
        mem_pct_val = float(m.get("memory_pct", 0) or 0)

        status_color = "green" if node["status"] == "Ready" else "red"
        findings_str = "; ".join(node["findings"]) if node["findings"] else "✅ OK"
        findings_color = "red" if node["findings"] else "green"

        table.add_row(
            node["name"],
            f"[{status_color}]{node['status']}[/{status_color}]",
            node["instance_type"],
            node["node_group"],
            cpu_raw,
            f"[{pct_color(cpu_pct_val)}]{cpu_pct_val:.0f}%[/{pct_color(cpu_pct_val)}]",
            mem_raw,
            f"[{pct_color(mem_pct_val)}]{mem_pct_val:.0f}%[/{pct_color(mem_pct_val)}]",
            node["zone"],
            f"[{findings_color}]{findings_str}[/{findings_color}]",
        )

    console.print(table)


def display_table_plain(nodes: List[Dict], metrics: Dict[str, Dict]):
    print(f"\n{'NODO':<35} {'STATUS':<10} {'TIPO':<16} {'CPU':>8} {'MEM':>10} {'FINDINGS'}")
    print("-" * 100)
    for node in nodes:
        m = metrics.get(node["name"], {})
        print(f"{node['name']:<35} {node['status']:<10} {node['instance_type']:<16} "
              f"{m.get('cpu_raw','—'):>8} {m.get('memory_raw','—'):>10} "
              f"{'; '.join(node['findings']) or 'OK'}")


def export_results(nodes: List[Dict], metrics: Dict[str, Dict], output_format: str):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    OUTCOME_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    enriched = []
    for node in nodes:
        m = metrics.get(node["name"], {})
        row = {**node, **m}
        row["taints"] = "; ".join(row.get("taints", []))
        row["findings"] = "; ".join(row.get("findings", []))
        enriched.append(row)

    if output_format == "json":
        fp = OUTCOME_DIR / f"aws_eks_nodes_{ts}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "nodes": enriched}, f, indent=2)
        print(f"\n✅ JSON exportado: {fp}")
    elif output_format == "csv":
        fp = OUTCOME_DIR / f"aws_eks_nodes_{ts}.csv"
        fields = ["name", "status", "instance_type", "zone", "node_group", "cpu_raw", "memory_raw",
                  "cpu_pct", "memory_pct", "kubelet_version", "age_days", "taints", "findings"]
        with open(fp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(enriched)
        print(f"\n✅ CSV exportado: {fp}")


def main():
    start_time = time.time()
    args = get_args()

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS EKS Node Monitor[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="🖥️  Node Monitor"
        ))
    else:
        print(f"AWS EKS Node Monitor | Profile: {args.profile} | Region: {args.region}")

    session = get_session(args.profile, args.region)

    cluster = args.cluster
    if not cluster:
        clusters = list_eks_clusters(session, args.region)
        if not clusters:
            print("No se encontraron clusters EKS.")
            sys.exit(1)
        if len(clusters) == 1:
            cluster = clusters[0]
        elif RICH_AVAILABLE:
            console.print("[cyan]Clusters disponibles:[/cyan]")
            for i, c in enumerate(clusters, 1):
                console.print(f"  [bold]{i}[/bold]. {c}")
            idx = int(Prompt.ask("Seleccione cluster", default="1")) - 1
            cluster = clusters[max(0, min(idx, len(clusters) - 1))]
        else:
            for i, c in enumerate(clusters, 1):
                print(f"  {i}. {c}")
            idx = int(input("Seleccione: ")) - 1
            cluster = clusters[max(0, min(idx, len(clusters) - 1))]

    if RICH_AVAILABLE:
        console.print(f"[dim]Configurando kubeconfig para: [cyan]{cluster}[/cyan][/dim]")
    if not update_kubeconfig(args.profile, args.region, cluster):
        print("ERROR: update-kubeconfig falló.")
        sys.exit(1)

    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True, console=console) as p:
            p.add_task(f"Obteniendo información de nodos [{cluster}]...", total=None)
            nodes = get_nodes_detail()
            metrics = get_node_metrics()
    else:
        print("Obteniendo nodos...")
        nodes = get_nodes_detail()
        metrics = get_node_metrics()

    if not nodes:
        print("No se encontraron nodos.")
        sys.exit(0)

    sort_key = {"cpu": lambda n: float(metrics.get(n["name"], {}).get("cpu_pct", 0) or 0),
                "memory": lambda n: float(metrics.get(n["name"], {}).get("memory_pct", 0) or 0),
                "name": lambda n: n["name"],
                "status": lambda n: n["status"]}
    reverse = args.sort in ("cpu", "memory")
    nodes.sort(key=sort_key[args.sort], reverse=reverse)

    elapsed = time.time() - start_time
    m, s = divmod(int(elapsed), 60)
    time_str = f"{m}m {s}s" if m else f"{s}s"

    if args.output == "table":
        if RICH_AVAILABLE:
            display_table_rich(nodes, metrics)
        else:
            display_table_plain(nodes, metrics)
    else:
        export_results(nodes, metrics, args.output)

    ready = sum(1 for n in nodes if n["status"] == "Ready")
    with_findings = sum(1 for n in nodes if n["findings"])

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Cluster:[/bold] [cyan]{cluster}[/cyan] | [bold]Nodos:[/bold] [green]{len(nodes)}[/green]\n"
            f"[bold]Ready:[/bold] [green]{ready}[/green] | [bold]NotReady:[/bold] [red]{len(nodes)-ready}[/red] | "
            f"[bold]Con findings:[/bold] [yellow]{with_findings}[/yellow]\n"
            f"[bold]Tiempo:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\nCluster: {cluster} | Nodos: {len(nodes)} | Ready: {ready} | Findings: {with_findings} | {time_str}")


if __name__ == "__main__":
    main()
