#!/usr/bin/env python3
"""
GKE Pod Resources Monitor v1.0.0
Muestra uso de CPU/memoria por pod en un cluster GKE, con selección interactiva
de proyecto, cluster, namespace y ordenamiento.
Solo lectura — no modifica ningún recurso.

Uso:
    python gke_pod_monitor.py
    python gke_pod_monitor.py --project mi-proyecto-id
    python gke_pod_monitor.py --project mi-proyecto-id --namespace mi-ns
    python gke_pod_monitor.py --project mi-proyecto-id --sort cpu --top 20

Autor: Harold Adrian (migrado desde Comercial/scripts/4.py)
"""

import subprocess
import json
import sys
import argparse
import time
from datetime import datetime
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, IntPrompt
except ImportError:
    print("⚠️  Rich no instalado. Ejecuta: pip install rich")
    sys.exit(1)

console = Console()
VERSION = "1.0.0"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def run_cmd(cmd: list[str]) -> tuple[str, str, int]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def run_json(cmd: list[str]) -> Optional[dict | list]:
    stdout, stderr, rc = run_cmd(cmd)
    if rc != 0:
        console.print(f"  ⚠️  Error: {stderr[:200]}", style="red")
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        console.print(f"  ⚠️  JSON inválido: {stdout[:200]}", style="red")
        return None


def pct_color(value: float) -> str:
    if value > 80:
        return "red"
    elif value > 50:
        return "yellow"
    else:
        return "green"


def parse_cpu(cpu_str: str) -> float:
    """Convierte CPU string a millicores float. Ej: '250m' -> 250, '1' -> 1000."""
    try:
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1])
        elif cpu_str.endswith("n"):
            return float(cpu_str[:-1]) / 1_000_000
        else:
            return float(cpu_str) * 1000
    except (ValueError, TypeError):
        return 0.0


def parse_mem(mem_str: str) -> float:
    """Convierte memoria string a Mi float. Ej: '128Mi' -> 128, '1Gi' -> 1024."""
    try:
        if mem_str.endswith("Ki"):
            return float(mem_str[:-2]) / 1024
        elif mem_str.endswith("Mi"):
            return float(mem_str[:-2])
        elif mem_str.endswith("Gi"):
            return float(mem_str[:-2]) * 1024
        elif mem_str.endswith("Ti"):
            return float(mem_str[:-2]) * 1024 * 1024
        elif mem_str.endswith("K") or mem_str.endswith("k"):
            return float(mem_str[:-1]) / 1024
        elif mem_str.endswith("M"):
            return float(mem_str[:-1])
        elif mem_str.endswith("G"):
            return float(mem_str[:-1]) * 1024
        else:
            # Bytes
            return float(mem_str) / (1024 * 1024)
    except (ValueError, TypeError):
        return 0.0


def format_mem(mi: float) -> str:
    """Formatea Mi a string legible."""
    if mi >= 1024:
        return f"{mi / 1024:.1f}Gi"
    elif mi >= 1:
        return f"{mi:.0f}Mi"
    else:
        return f"{mi * 1024:.0f}Ki"


# ─────────────────────────────────────────────
# GKE functions
# ─────────────────────────────────────────────

def get_cluster_list(project: Optional[str] = None) -> list[dict]:
    cmd = ["gcloud", "container", "clusters", "list", "--format=json"]
    if project:
        cmd += ["--project", project]
    data = run_json(cmd)
    return data if data else []


def get_credentials(cluster_name: str, location: str, project: Optional[str] = None) -> bool:
    cmd = [
        "gcloud", "container", "clusters", "get-credentials",
        cluster_name, "--zone", location, "--quiet"
    ]
    if project:
        cmd += ["--project", project]
    _, stderr, rc = run_cmd(cmd)
    if rc != 0:
        console.print(f"  ⚠️  No se pudieron obtener credenciales: {stderr[:150]}", style="red")
    return rc == 0


def get_namespaces(context: str) -> list[str]:
    """Retorna lista de namespaces, filtrando los de sistema/GKE."""
    SYSTEM_NAMESPACES = {
        "kube-system", "kube-public", "kube-node-lease",
        "default", "datadog",
        "gke-managed-cim", "gke-managed-dpv2-observability",
        "gke-managed-system", "gke-managed-volumepopulator",
        "gmp-system", "gmp-public",
    }
    cmd = [
        "kubectl", "get", "namespaces", "--context", context,
        "-o", "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}"
    ]
    stdout, _, rc = run_cmd(cmd)
    if rc != 0:
        return []
    return [ns for ns in stdout.splitlines() if ns.strip() and ns.strip() not in SYSTEM_NAMESPACES]


def get_pods_info(context: str, namespace: Optional[str] = None) -> list[dict]:
    """Retorna info básica de pods (nombre, namespace, estado, nodo, restarts, age)."""
    ns_flag = ["-n", namespace] if namespace else ["--all-namespaces"]
    cmd = [
        "kubectl", "get", "pods", *ns_flag,
        "--context", context,
        "-o", "json"
    ]
    data = run_json(cmd)
    if not data:
        return []

    pods = []
    for item in data.get("items", []):
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        status = item.get("status", {})

        name = metadata.get("name", "unknown")
        ns = metadata.get("namespace", "unknown")
        node = spec.get("nodeName", "N/A")
        phase = status.get("phase", "Unknown")

        # Restarts y estado real del container
        restarts = 0
        container_state = phase
        container_statuses = status.get("containerStatuses", [])
        for cs in container_statuses:
            restarts += cs.get("restartCount", 0)
            state = cs.get("state", {})
            if "waiting" in state:
                container_state = state["waiting"].get("reason", "Waiting")
            elif "terminated" in state:
                container_state = state["terminated"].get("reason", "Terminated")

        # Requests y limits
        cpu_req = "0m"
        mem_req = "0Mi"
        cpu_lim = "N/A"
        mem_lim = "N/A"
        containers = spec.get("containers", [])
        total_cpu_req = 0.0
        total_mem_req = 0.0
        total_cpu_lim = 0.0
        total_mem_lim = 0.0
        has_cpu_lim = False
        has_mem_lim = False

        for c in containers:
            resources = c.get("resources", {})
            req = resources.get("requests", {})
            lim = resources.get("limits", {})
            total_cpu_req += parse_cpu(req.get("cpu", "0"))
            total_mem_req += parse_mem(req.get("memory", "0"))
            if "cpu" in lim:
                total_cpu_lim += parse_cpu(lim["cpu"])
                has_cpu_lim = True
            if "memory" in lim:
                total_mem_lim += parse_mem(lim["memory"])
                has_mem_lim = True

        cpu_req = f"{total_cpu_req:.0f}m" if total_cpu_req > 0 else "0m"
        mem_req = format_mem(total_mem_req) if total_mem_req > 0 else "0Mi"
        cpu_lim = f"{total_cpu_lim:.0f}m" if has_cpu_lim else "N/A"
        mem_lim = format_mem(total_mem_lim) if has_mem_lim else "N/A"

        pods.append({
            "name": name,
            "namespace": ns,
            "node": node,
            "status": container_state,
            "restarts": restarts,
            "cpu_req": cpu_req,
            "mem_req": mem_req,
            "cpu_lim": cpu_lim,
            "mem_lim": mem_lim,
            "cpu_req_val": total_cpu_req,
            "mem_req_val": total_mem_req,
            "cpu_used_val": 0.0,
            "mem_used_val": 0.0,
            "cpu_used": "N/A",
            "mem_used": "N/A",
        })

    return pods


def get_pods_usage(context: str, namespace: Optional[str] = None) -> dict:
    """Retorna uso actual de CPU/mem por pod via kubectl top pods."""
    ns_flag = ["-n", namespace] if namespace else ["--all-namespaces"]
    cmd = [
        "kubectl", "top", "pods", *ns_flag,
        "--context", context, "--no-headers"
    ]
    stdout, _, rc = run_cmd(cmd)
    if rc != 0:
        return {}

    usage = {}
    for line in stdout.splitlines():
        parts = line.split()
        if namespace:
            # formato: NAME CPU MEM
            if len(parts) >= 3:
                usage[f"{namespace}/{parts[0]}"] = {
                    "cpu": parts[1],
                    "mem": parts[2],
                }
        else:
            # formato: NAMESPACE NAME CPU MEM
            if len(parts) >= 4:
                usage[f"{parts[0]}/{parts[1]}"] = {
                    "cpu": parts[2],
                    "mem": parts[3],
                }

    return usage


# ─────────────────────────────────────────────
# Selección interactiva
# ─────────────────────────────────────────────

def select_cluster(clusters: list[dict]) -> Optional[dict]:
    """Menú interactivo para seleccionar cluster. Retorna None si elige TODOS."""
    console.print()
    table = Table(
        title="☸️  Clusters disponibles",
        box=box.ROUNDED, show_header=True, header_style="bold white",
        padding=(0, 1),
    )
    table.add_column("#", style="bold yellow", justify="right")
    table.add_column("Cluster", style="cyan")
    table.add_column("Ubicación", justify="center")
    table.add_column("Nodos", justify="center")
    table.add_column("Estado", justify="center")

    table.add_row("0", "[bold]TODOS (all clusters)[/]", "", "", "")
    for i, c in enumerate(clusters, 1):
        st = c.get("status", "UNKNOWN")
        st_icon = "✅" if st == "RUNNING" else "⚠️"
        table.add_row(
            str(i),
            c.get("name", "?"),
            c.get("location", "?"),
            str(c.get("currentNodeCount", 0)),
            st_icon,
        )

    console.print(table)

    while True:
        try:
            choice = IntPrompt.ask(
                "\n[bold]Selecciona el número del cluster (0 = todos)[/]",
                console=console,
                default=0,
            )
            if choice == 0:
                return None
            if 1 <= choice <= len(clusters):
                return clusters[choice - 1]
            console.print(f"  ⚠️  Ingresa un número entre 0 y {len(clusters)}", style="yellow")
        except (ValueError, KeyboardInterrupt):
            console.print("\n👋 Cancelado.", style="dim")
            sys.exit(0)


def select_namespace(namespaces: list[str]) -> Optional[str]:
    """Menú interactivo para seleccionar namespace o todos."""
    console.print()
    table = Table(
        title="📁 Namespaces disponibles",
        box=box.ROUNDED, show_header=True, header_style="bold white",
        padding=(0, 1),
    )
    table.add_column("#", style="bold yellow", justify="right")
    table.add_column("Namespace", style="cyan")

    table.add_row("0", "[bold]TODOS (all namespaces)[/]")
    for i, ns in enumerate(namespaces, 1):
        table.add_row(str(i), ns)

    console.print(table)

    while True:
        try:
            choice = IntPrompt.ask(
                "\n[bold]Selecciona namespace (0 = todos)[/]",
                console=console,
                default=0,
            )
            if choice == 0:
                return None
            if 1 <= choice <= len(namespaces):
                return namespaces[choice - 1]
            console.print(f"  ⚠️  Ingresa un número entre 0 y {len(namespaces)}", style="yellow")
        except (ValueError, KeyboardInterrupt):
            console.print("\n👋 Cancelado.", style="dim")
            sys.exit(0)


# ─────────────────────────────────────────────
# Display
# ─────────────────────────────────────────────

def display_pods(pods: list[dict], cluster_name: str, namespace: Optional[str],
                 sort_by: str, top_n: Optional[int],
                 consoles: list[Console] = None):
    """Muestra tabla de pods con recursos. Imprime en todas las consolas dadas."""
    if consoles is None:
        consoles = [console]

    def cprint(*args, **kwargs):
        for c in consoles:
            c.print(*args, **kwargs)

    # Ordenar
    if sort_by == "mem":
        pods.sort(key=lambda p: p["mem_used_val"], reverse=True)
    elif sort_by == "cpu":
        pods.sort(key=lambda p: p["cpu_used_val"], reverse=True)
    elif sort_by == "restarts":
        pods.sort(key=lambda p: p["restarts"], reverse=True)
    else:
        pods.sort(key=lambda p: (p["namespace"], p["name"]))

    # Top N
    total_pods = len(pods)
    if top_n and top_n < len(pods):
        pods = pods[:top_n]

    ns_label = namespace or "todos"
    title = f"📊 Pods en [cyan]{cluster_name}[/] — Namespace: [cyan]{ns_label}[/] — Total: {total_pods}"
    if top_n and top_n < total_pods:
        title += f" (mostrando top {top_n})"

    cprint()
    cprint(title)
    cprint("─" * 80)

    # ── Construir filas (se reusan para cada consola) ─────────
    rows = []
    for p in pods:
        st = p["status"]
        if st == "Running":
            st_styled = f"[green]{st}[/]"
        elif st in ("CrashLoopBackOff", "Error", "OOMKilled"):
            st_styled = f"[red bold]{st}[/]"
        elif st in ("Pending", "ContainerCreating", "Waiting"):
            st_styled = f"[yellow]{st}[/]"
        elif st in ("Completed", "Succeeded"):
            st_styled = f"[dim]{st}[/]"
        else:
            st_styled = f"[yellow]{st}[/]"

        r = p["restarts"]
        if r > 10:
            r_styled = f"[red bold]{r}[/]"
        elif r > 0:
            r_styled = f"[yellow]{r}[/]"
        else:
            r_styled = f"[green]{r}[/]"

        cpu_used = p["cpu_used"]
        if p["cpu_used_val"] > 0 and p["cpu_req_val"] > 0:
            cpu_pct = (p["cpu_used_val"] / p["cpu_req_val"]) * 100
            cpu_color = pct_color(cpu_pct)
            cpu_styled = f"[{cpu_color}]{cpu_used}[/]"
        else:
            cpu_styled = cpu_used

        mem_used = p["mem_used"]
        if p["mem_used_val"] > 0 and p["mem_req_val"] > 0:
            mem_pct = (p["mem_used_val"] / p["mem_req_val"]) * 100
            mem_color = pct_color(mem_pct)
            mem_styled = f"[{mem_color}]{mem_used}[/]"
        else:
            mem_styled = mem_used

        row = []
        if not namespace:
            row.append(p["namespace"])
        row.extend([
            p["name"], st_styled, r_styled, cpu_styled,
            p["cpu_req"], p["cpu_lim"], mem_styled, p["mem_req"], p["mem_lim"],
        ])
        rows.append(row)

    # ── Imprimir tabla en cada consola ─────────────────────────
    for c in consoles:
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold white",
                      padding=(0, 1), expand=False)
        if not namespace:
            table.add_column("Namespace", style="dim", max_width=25)
        table.add_column("Pod", style="cyan", max_width=55)
        table.add_column("Estado", justify="center")
        table.add_column("Restarts", justify="right")
        table.add_column("CPU Usado", justify="right")
        table.add_column("CPU Req", justify="right", style="dim")
        table.add_column("CPU Lim", justify="right", style="dim")
        table.add_column("Mem Usada", justify="right")
        table.add_column("Mem Req", justify="right", style="dim")
        table.add_column("Mem Lim", justify="right", style="dim")
        for row in rows:
            table.add_row(*row)
        c.print(table)

    # ── Resumen de estados ────────────────────────────────────
    status_count = {}
    for p in pods:
        st = p["status"]
        status_count[st] = status_count.get(st, 0) + 1

    for c in consoles:
        c.print()
        st_table = Table(title="📋 Resumen de Estados", box=box.ROUNDED,
                         show_header=True, header_style="bold white", padding=(0, 1))
        st_table.add_column("Estado", style="cyan")
        st_table.add_column("Cantidad", justify="right")
        st_table.add_column("", justify="center")
        for st, count in sorted(status_count.items(), key=lambda x: -x[1]):
            if st == "Running":
                icon = "✅"
            elif st in ("CrashLoopBackOff", "Error", "OOMKilled"):
                icon = "🔴"
            elif st in ("Pending", "ContainerCreating"):
                icon = "🟡"
            else:
                icon = "⚪"
            st_table.add_row(st, str(count), icon)
        c.print(st_table)

    # ── Top 5 memoria ─────────────────────────────────────────
    by_mem = sorted(pods, key=lambda p: p["mem_used_val"], reverse=True)[:5]
    if by_mem and by_mem[0]["mem_used_val"] > 0:
        for c in consoles:
            c.print()
            mem_top = Table(title="🔥 Top 5 — Mayor consumo de Memoria", box=box.ROUNDED,
                            show_header=True, header_style="bold white", padding=(0, 1))
            mem_top.add_column("Pod", style="cyan", max_width=55)
            mem_top.add_column("Namespace", style="dim")
            mem_top.add_column("Mem Usada", justify="right")
            mem_top.add_column("Mem Req", justify="right", style="dim")
            for p in by_mem:
                if p["mem_used_val"] > 0:
                    mem_top.add_row(p["name"], p["namespace"], p["mem_used"], p["mem_req"])
            c.print(mem_top)

    # ── Top 5 CPU ─────────────────────────────────────────────
    by_cpu = sorted(pods, key=lambda p: p["cpu_used_val"], reverse=True)[:5]
    if by_cpu and by_cpu[0]["cpu_used_val"] > 0:
        for c in consoles:
            c.print()
            cpu_top = Table(title="🔥 Top 5 — Mayor consumo de CPU", box=box.ROUNDED,
                            show_header=True, header_style="bold white", padding=(0, 1))
            cpu_top.add_column("Pod", style="cyan", max_width=55)
            cpu_top.add_column("Namespace", style="dim")
            cpu_top.add_column("CPU Usado", justify="right")
            cpu_top.add_column("CPU Req", justify="right", style="dim")
            for p in by_cpu:
                if p["cpu_used_val"] > 0:
                    cpu_top.add_row(p["name"], p["namespace"], p["cpu_used"], p["cpu_req"])
            c.print(cpu_top)

    # ── Pods problemáticos ────────────────────────────────────
    problematic = [p for p in pods if p["status"] in ("CrashLoopBackOff", "Error", "OOMKilled", "Pending") or p["restarts"] > 5]
    if problematic:
        for c in consoles:
            c.print()
            prob_table = Table(title="🚨 Pods Problemáticos (estado malo o +5 restarts)",
                               box=box.ROUNDED, show_header=True, header_style="bold white", padding=(0, 1))
            prob_table.add_column("Pod", style="red", max_width=55)
            prob_table.add_column("Namespace", style="dim")
            prob_table.add_column("Estado", justify="center")
            prob_table.add_column("Restarts", justify="right")
            prob_table.add_column("Nodo", style="dim")
            for p in sorted(problematic, key=lambda x: -x["restarts"]):
                prob_table.add_row(p["name"], p["namespace"], p["status"], str(p["restarts"]), p["node"])
            c.print(prob_table)


def _display_pods_dual(pods, cluster_name, namespace, sort_by, top_n, console1, console2):
    """Wrapper para imprimir en ambas consolas."""
    display_pods(pods, cluster_name, namespace, sort_by, top_n, [console1, console2])


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GKE Pod Resources Monitor")
    parser.add_argument("--project", help="GCP Project ID")
    parser.add_argument("--namespace", "-n", help="Filtrar por namespace (omitir = selección interactiva)")
    parser.add_argument("--sort", choices=["name", "cpu", "mem", "restarts"], default="mem",
                        help="Ordenar pods por (default: mem)")
    parser.add_argument("--top", type=int, help="Mostrar solo los top N pods")
    args = parser.parse_args()

    start_time = time.time()

    # ── Proyectos conocidos ───────────────────────────────────
    PROYECTOS = [
        "cpl-corp-cial-dev-17072024",
        "cpl-corp-cial-qa-06082024",
        "cpl-corp-cial-prod-01082024",
    ]

    # ── Proyecto ──────────────────────────────────────────────
    project = args.project
    if not project:
        out, _, rc = run_cmd(["gcloud", "config", "get-value", "project"])
        current = out if rc == 0 and out else None

        console.print()
        proj_table = Table(
            title="📁 Proyectos disponibles",
            box=box.ROUNDED, show_header=True, header_style="bold white",
            padding=(0, 1),
        )
        proj_table.add_column("#", style="bold yellow", justify="right")
        proj_table.add_column("Proyecto", style="cyan")
        proj_table.add_column("", justify="center")

        proj_table.add_row("0", f"{current or 'N/A'}", "[green]← activo[/]" if current else "")
        for i, p in enumerate(PROYECTOS, 1):
            marker = "[green]← activo[/]" if p == current else ""
            proj_table.add_row(str(i), p, marker)

        console.print(proj_table)

        while True:
            try:
                choice = IntPrompt.ask(
                    "\n[bold]Selecciona proyecto (0 = usar el activo)[/]",
                    console=console,
                    default=0,
                )
                if choice == 0:
                    project = current
                    break
                elif 1 <= choice <= len(PROYECTOS):
                    project = PROYECTOS[choice - 1]
                    run_cmd(["gcloud", "config", "set", "project", project])
                    break
                else:
                    console.print(f"  ⚠️  Ingresa un número entre 0 y {len(PROYECTOS)}", style="yellow")
            except (ValueError, KeyboardInterrupt):
                console.print("\n👋 Cancelado.", style="dim")
                sys.exit(0)

    # ── Header ────────────────────────────────────────────────
    console.print(Panel(
        f"[bold]GKE Pod Resources Monitor v{VERSION}[/]\n"
        f"Proyecto: [cyan]{project or 'desconocido'}[/]",
        border_style="cyan",
    ))

    account, _, _ = run_cmd(["gcloud", "config", "get-value", "account"])
    console.print(f"✓ Cuenta activa: [cyan]{account}[/]")
    console.print(f"✓ Proyecto válido: [cyan]{project}[/]")

    # ── Clusters ──────────────────────────────────────────────
    CLUSTERS_IGNORADOS = [
        "us-central1-cial-corp-compo-16cc48c9-gke",
        "us-central1-cial-corp-compo-e0b3ed5c-gke",
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        task = progress.add_task("Obteniendo clusters...", total=None)
        clusters = get_cluster_list(project)
        progress.update(task, description="✓ Clusters obtenidos")

    if not clusters:
        console.print("❌ No se encontraron clusters o no hay permisos.", style="red")
        sys.exit(1)

    clusters = [c for c in clusters if c.get("name") not in CLUSTERS_IGNORADOS]

    # ── Selección de cluster ──────────────────────────────────
    cluster = select_cluster(clusters)

    # ── Preparar lista de clusters a procesar ─────────────────
    if cluster is None:
        clusters_to_process = clusters
        console.print(f"\n✓ Procesando [bold cyan]TODOS[/] los clusters ({len(clusters_to_process)})")
    else:
        clusters_to_process = [cluster]
        console.print(f"\n✓ Cluster seleccionado: [bold cyan]{cluster.get('name', 'unknown')}[/]")

    # ── Reporte (grabado para exportar) ─────────────────────
    from io import StringIO
    export_console = Console(record=True, width=160, file=StringIO())

    total_pods_all = 0

    for cl in clusters_to_process:
        cluster_name = cl.get("name", "unknown")
        location = cl.get("location", cl.get("zone", "unknown"))

        # ── Credenciales ──────────────────────────────────────
        context = f"gke_{project or 'default'}_{location}_{cluster_name}"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console, transient=True,
        ) as progress:
            task = progress.add_task(f"Conectando a {cluster_name}...", total=None)
            ok = get_credentials(cluster_name, location, project)

        if not ok:
            console.print(f"❌ No se pudieron obtener credenciales para {cluster_name}.", style="red")
            continue

        # ── Selección de namespace (solo si es 1 cluster) ─────
        namespace = args.namespace
        if not namespace and len(clusters_to_process) == 1:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console, transient=True,
            ) as progress:
                task = progress.add_task("Obteniendo namespaces...", total=None)
                namespaces = get_namespaces(context)

            if namespaces:
                namespace = select_namespace(namespaces)
            else:
                console.print("⚠️  No se pudieron obtener namespaces, consultando todos.", style="yellow")

        ns_label = namespace or "todos"
        console.print(f"✓ Namespace: [cyan]{ns_label}[/] — Cluster: [cyan]{cluster_name}[/]")

        # ── Obtener pods + uso ────────────────────────────────
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console, transient=True,
        ) as progress:
            task = progress.add_task(f"Obteniendo pods de {cluster_name}...", total=None)
            pods = get_pods_info(context, namespace)
            progress.update(task, description=f"✓ {len(pods)} pods encontrados — obteniendo métricas...")
            usage = get_pods_usage(context, namespace)
            progress.update(task, description=f"✓ {len(pods)} pods con métricas")

        # Cruzar uso real con pods
        for p in pods:
            key = f"{p['namespace']}/{p['name']}"
            if key in usage:
                p["cpu_used"] = usage[key]["cpu"]
                p["mem_used"] = usage[key]["mem"]
                p["cpu_used_val"] = parse_cpu(usage[key]["cpu"])
                p["mem_used_val"] = parse_mem(usage[key]["mem"])

        total_pods_all += len(pods)

        # Mostrar en pantalla Y grabar al mismo tiempo
        for c in [console, export_console]:
            c.print()
            c.print("=" * 80)
            c.print(
                f"📊 [bold]REPORTE DE PODS GKE[/] — Proyecto: [cyan]{project}[/]\n"
                f"☸️  Cluster: [cyan]{cluster_name}[/]\n"
                f"🕐 Fecha: [cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]\n"
                f"📦 Versión: [cyan]{VERSION}[/]"
            )
            c.print("=" * 80)

        _display_pods_dual(pods, cluster_name, namespace, args.sort, args.top,
                           console, export_console)

    # ── Resumen ejecución ─────────────────────────────────────
    elapsed = time.time() - start_time
    clusters_label = ", ".join(cl.get("name", "?") for cl in clusters_to_process)

    exec_table = Table(box=box.ROUNDED, show_header=True, header_style="bold white",
                       title="⏱️ Resumen de Ejecución", padding=(0, 1))
    exec_table.add_column("Métrica", style="cyan")
    exec_table.add_column("Valor")
    exec_table.add_row("Proyecto", project or "N/A")
    exec_table.add_row("Clusters", clusters_label)
    exec_table.add_row("Pods analizados", str(total_pods_all))
    exec_table.add_row("Tiempo de ejecución", f"{elapsed:.2f}s")

    for c in [console, export_console]:
        c.print()
        c.print(Panel(exec_table, border_style="cyan"))

    # ── Exportar HTML ─────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    proyecto_clean = (project or "sin-proyecto").replace("/", "-")
    if len(clusters_to_process) == 1:
        filename = f"pods_{proyecto_clean}_{clusters_to_process[0].get('name', 'cluster')}_{ts}.html"
    else:
        filename = f"pods_{proyecto_clean}_ALL-CLUSTERS_{ts}.html"

    html = export_console.export_html()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    console.print()
    console.print(f"📁 Reporte guardado en: [bold cyan]{filename}[/]")
    console.print("[dim]   Ábrelo en el navegador para ver con colores exactos.[/]")

    console.print()
    console.input("[dim]Presione Enter para continuar...[/]")


if __name__ == "__main__":
    main()