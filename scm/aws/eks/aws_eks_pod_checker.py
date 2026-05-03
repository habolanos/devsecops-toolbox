#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Pod Resources Monitor

Muestra uso de CPU/memoria por pod en clusters EKS usando kubectl.
Permite selección de cluster, namespace y ordenamiento.
Solo lectura — no modifica ningún recurso.

Equivalente AWS de: gke_monitor_pod.py (GKE Pod Resources Monitor)

Uso:
    python aws_eks_pod_checker.py
    python aws_eks_pod_checker.py --cluster my-cluster
    python aws_eks_pod_checker.py --cluster my-cluster --namespace my-ns
    python aws_eks_pod_checker.py --cluster my-cluster --sort cpu --top 20 -o json

Requisitos: kubectl y aws eks update-kubeconfig configurados.

Autor: Harold Adrian
"""

import sys
import json
import argparse
import subprocess
import csv
from datetime import datetime
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
    from rich.prompt import Prompt, IntPrompt
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS EKS Pod Resources Monitor")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--cluster", "-c", default="", help="Nombre del cluster EKS")
    parser.add_argument("--namespace", "-n", default="", help="Namespace (vacío = todos)")
    parser.add_argument("--sort", choices=["cpu", "memory", "name"], default="cpu",
                        help="Ordenar por (default: cpu)")
    parser.add_argument("--top", type=int, default=0, help="Mostrar sólo N pods (0 = todos)")
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
        eks = session.client("eks", region_name=region)
        return eks.list_clusters().get("clusters", [])
    except ClientError as e:
        return []


def update_kubeconfig(profile: str, region: str, cluster: str, debug: bool = False) -> bool:
    """Actualiza kubeconfig para el cluster EKS."""
    cmd = ["aws", "eks", "update-kubeconfig",
           "--name", cluster,
           "--region", region,
           "--profile", profile]
    if debug:
        print(f"DEBUG: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ update-kubeconfig falló: {result.stderr[:200]}[/red]")
        else:
            print(f"ERROR update-kubeconfig: {result.stderr[:200]}")
        return False
    return True


def run_kubectl(cmd: List[str], debug: bool = False) -> Optional[dict]:
    if debug:
        print(f"DEBUG kubectl: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def pct_color(value: float) -> str:
    if value > 80:
        return "red"
    if value > 60:
        return "yellow"
    return "green"


def parse_cpu_millicores(cpu_str: str) -> float:
    """Convierte CPU string (100m, 0.5) a millicores."""
    if not cpu_str or cpu_str == "<unknown>":
        return 0.0
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1])
    try:
        return float(cpu_str) * 1000
    except ValueError:
        return 0.0


def parse_memory_mib(mem_str: str) -> float:
    """Convierte memoria string a MiB."""
    if not mem_str or mem_str == "<unknown>":
        return 0.0
    if mem_str.endswith("Ki"):
        return float(mem_str[:-2]) / 1024
    if mem_str.endswith("Mi"):
        return float(mem_str[:-2])
    if mem_str.endswith("Gi"):
        return float(mem_str[:-2]) * 1024
    if mem_str.endswith("Ti"):
        return float(mem_str[:-2]) * 1024 * 1024
    try:
        return float(mem_str) / (1024 * 1024)
    except ValueError:
        return 0.0


def get_pod_metrics(namespace: str = "", debug: bool = False) -> List[Dict]:
    """Obtiene métricas de pods vía kubectl top pods."""
    cmd = ["kubectl", "top", "pods", "--no-headers", "--all-namespaces", "-o", "json"]
    if namespace:
        cmd = ["kubectl", "top", "pods", "--no-headers", "-n", namespace, "-o", "json"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        cmd_plain = cmd[:-2] if "-o" in cmd else cmd
        result = subprocess.run(cmd_plain, capture_output=True, text=True)
        if result.returncode != 0:
            return []
        return _parse_top_plain(result.stdout, namespace)

    try:
        data = json.loads(result.stdout)
        return _parse_top_json(data)
    except json.JSONDecodeError:
        return _parse_top_plain(result.stdout, namespace)


def _parse_top_plain(output: str, default_ns: str = "") -> List[Dict]:
    rows = []
    for line in output.strip().splitlines():
        parts = line.split()
        if len(parts) == 3:
            ns_name, cpu_str, mem_str = parts
            if "/" in ns_name:
                ns, name = ns_name.split("/", 1)
            else:
                ns, name = default_ns, ns_name
        elif len(parts) == 4:
            ns, name, cpu_str, mem_str = parts
        else:
            continue
        rows.append({
            "namespace": ns,
            "name": name,
            "cpu_millicores": parse_cpu_millicores(cpu_str),
            "memory_mib": parse_memory_mib(mem_str),
            "cpu_raw": cpu_str,
            "memory_raw": mem_str,
        })
    return rows


def _parse_top_json(data: dict) -> List[Dict]:
    rows = []
    for item in data.get("items", []):
        meta = item.get("metadata", {})
        containers = item.get("containers", [])
        total_cpu = sum(parse_cpu_millicores(c.get("usage", {}).get("cpu", "0m")) for c in containers)
        total_mem = sum(parse_memory_mib(c.get("usage", {}).get("memory", "0Mi")) for c in containers)
        rows.append({
            "namespace": meta.get("namespace", ""),
            "name": meta.get("name", ""),
            "cpu_millicores": total_cpu,
            "memory_mib": total_mem,
            "cpu_raw": f"{int(total_cpu)}m",
            "memory_raw": f"{total_mem:.0f}Mi",
        })
    return rows


def get_pod_specs(namespace: str = "") -> Dict[str, Dict]:
    """Obtiene requests/limits de pods para calcular % de uso."""
    cmd = ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"]
    if namespace:
        cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    specs = {}
    for item in data.get("items", []):
        meta = item.get("metadata", {})
        key = f"{meta.get('namespace', '')}/{meta.get('name', '')}"
        total_cpu_req = 0.0
        total_mem_req = 0.0
        for c in item.get("spec", {}).get("containers", []):
            reqs = c.get("resources", {}).get("requests", {})
            total_cpu_req += parse_cpu_millicores(reqs.get("cpu", "0m"))
            total_mem_req += parse_memory_mib(reqs.get("memory", "0Mi"))
        specs[key] = {
            "node": item.get("spec", {}).get("nodeName", ""),
            "status": item.get("status", {}).get("phase", ""),
            "cpu_request_m": total_cpu_req,
            "mem_request_mib": total_mem_req,
        }
    return specs


def display_table_rich(pods: List[Dict], specs: Dict[str, Dict]):
    table = Table(
        title=f"🐳 EKS Pod Resources ({len(pods)} pods)",
        header_style="bold white on dark_blue",
        show_lines=False,
        box=box.SIMPLE_HEAVY,
    )
    table.add_column("Namespace", style="cyan", min_width=20)
    table.add_column("Pod", style="white", min_width=35)
    table.add_column("CPU (m)", justify="right", width=9)
    table.add_column("MEM (Mi)", justify="right", width=10)
    table.add_column("CPU Req", justify="right", width=9)
    table.add_column("MEM Req", justify="right", width=10)
    table.add_column("Node", style="dim", width=20)
    table.add_column("Status", width=10)

    for pod in pods:
        key = f"{pod['namespace']}/{pod['name']}"
        spec = specs.get(key, {})
        cpu_req = spec.get("cpu_request_m", 0)
        mem_req = spec.get("mem_request_mib", 0)

        cpu_pct = (pod["cpu_millicores"] / cpu_req * 100) if cpu_req > 0 else 0
        mem_pct = (pod["memory_mib"] / mem_req * 100) if mem_req > 0 else 0

        cpu_str = f"[{pct_color(cpu_pct)}]{pod['cpu_raw']}[/{pct_color(cpu_pct)}]"
        mem_str = f"[{pct_color(mem_pct)}]{pod['memory_raw']}[/{pct_color(mem_pct)}]"
        cpu_req_str = f"{int(cpu_req)}m" if cpu_req else "—"
        mem_req_str = f"{mem_req:.0f}Mi" if mem_req else "—"
        status = spec.get("status", "")
        status_color = "green" if status == "Running" else "yellow" if status == "Pending" else "red"

        table.add_row(
            pod["namespace"], pod["name"],
            cpu_str, mem_str,
            cpu_req_str, mem_req_str,
            spec.get("node", "")[:20],
            f"[{status_color}]{status}[/{status_color}]" if status else "",
        )

    console.print(table)


def display_table_plain(pods: List[Dict]):
    print(f"\n{'NAMESPACE':<25} {'POD':<40} {'CPU':>8} {'MEM':>10}")
    print("-" * 90)
    for pod in pods:
        print(f"{pod['namespace']:<25} {pod['name']:<40} {pod['cpu_raw']:>8} {pod['memory_raw']:>10}")


def export_results(pods: List[Dict], specs: Dict[str, Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    enriched = []
    for pod in pods:
        key = f"{pod['namespace']}/{pod['name']}"
        spec = specs.get(key, {})
        enriched.append({**pod, **spec})

    if output_format == "json":
        fp = OUTCOME_DIR / f"aws_eks_pods_{ts}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "pods": enriched}, f, indent=2)
        print(f"\n✅ JSON exportado: {fp}")
    elif output_format == "csv":
        fp = OUTCOME_DIR / f"aws_eks_pods_{ts}.csv"
        fields = ["namespace", "name", "cpu_raw", "memory_raw", "cpu_millicores", "memory_mib",
                  "cpu_request_m", "mem_request_mib", "node", "status"]
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
            f"[bold cyan]AWS EKS Pod Resources Monitor[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="🐳 Pod Monitor"
        ))
    else:
        print(f"AWS EKS Pod Monitor | Profile: {args.profile} | Region: {args.region}")

    session = get_session(args.profile, args.region)

    # Seleccionar cluster
    cluster = args.cluster
    if not cluster:
        clusters = list_eks_clusters(session, args.region)
        if not clusters:
            if RICH_AVAILABLE:
                console.print("[red]No se encontraron clusters EKS.[/red]")
            else:
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
            print("Clusters disponibles:")
            for i, c in enumerate(clusters, 1):
                print(f"  {i}. {c}")
            idx = int(input("Seleccione: ")) - 1
            cluster = clusters[max(0, min(idx, len(clusters) - 1))]

    # Actualizar kubeconfig
    if RICH_AVAILABLE:
        console.print(f"[dim]Configurando kubeconfig para: [cyan]{cluster}[/cyan][/dim]")
    if not update_kubeconfig(args.profile, args.region, cluster, args.debug):
        sys.exit(1)

    # Obtener métricas
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True, console=console) as p:
            p.add_task(f"Obteniendo métricas de pods [{cluster}]...", total=None)
            pods = get_pod_metrics(args.namespace, args.debug)
            specs = get_pod_specs(args.namespace)
    else:
        print("Obteniendo métricas de pods...")
        pods = get_pod_metrics(args.namespace, args.debug)
        specs = get_pod_specs(args.namespace)

    if not pods:
        if RICH_AVAILABLE:
            console.print("[yellow]⚠️  No se obtuvieron métricas. Verifica que metrics-server esté instalado.[/yellow]")
        else:
            print("WARNING: Sin métricas. Verifica metrics-server.")
        sys.exit(0)

    # Ordenar
    sort_key = {"cpu": "cpu_millicores", "memory": "memory_mib", "name": "name"}[args.sort]
    reverse = args.sort in ("cpu", "memory")
    pods.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse)

    if args.top > 0:
        pods = pods[:args.top]

    elapsed = time.time() - start_time
    m, s = divmod(int(elapsed), 60)
    time_str = f"{m}m {s}s" if m else f"{s}s"

    if args.output == "table":
        if RICH_AVAILABLE:
            display_table_rich(pods, specs)
        else:
            display_table_plain(pods)
    else:
        export_results(pods, specs, args.output)

    total_cpu = sum(p["cpu_millicores"] for p in pods)
    total_mem = sum(p["memory_mib"] for p in pods)

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Cluster:[/bold] [cyan]{cluster}[/cyan] | [bold]Pods:[/bold] [green]{len(pods)}[/green]\n"
            f"[bold]CPU Total:[/bold] [yellow]{total_cpu:.0f}m[/yellow] | [bold]MEM Total:[/bold] [yellow]{total_mem:.0f}Mi[/yellow]\n"
            f"[bold]Tiempo:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\nCluster: {cluster} | Pods: {len(pods)} | CPU: {total_cpu:.0f}m | MEM: {total_mem:.0f}Mi | {time_str}")


if __name__ == "__main__":
    main()
