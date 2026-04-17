#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inventario GKE + Cloud SQL - Generador CSV

Versión Python con interfaz Rich: spinners, progreso por hilo,
barra de avance global y salida colorida.

Reemplaza generar-inventario-csv.sh con funcionalidad equivalente.

Uso:
    python generar-inventario-csv.py [opciones] [PROYECTO1 ...]

Opciones:
    --delimiter CHAR   Separador CSV (default: ;)
    --threads N        Hilos paralelos (default: 4)
    --sequential       Deshabilitar paralelismo
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.box import ROUNDED, HEAVY
    from rich.style import Style
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "generar-inventario-csv.config"
OUTCOME_DIR = SCRIPT_DIR / "outcome"
TOTAL_STEPS = 8

STEP_NAMES = {
    1: "clusters",
    2: "deployments",
    3: "services",
    4: "cloudsql",
    5: "clouddatabases",
    6: "ingress",
    7: "cloudrun",
    8: "pubsub",
}

STEP_ICONS = {
    1: "☁️",
    2: "📦",
    3: "🔌",
    4: "🗄️",
    5: "💾",
    6: "🌐",
    7: "🏃",
    8: "📨",
}

STEP_COLORS = {
    1: "cyan",
    2: "cyan",
    3: "cyan",
    4: "magenta",
    5: "magenta",
    6: "blue",
    7: "yellow",
    8: "yellow",
}

# ═══════════════════════════════════════════════════════════════════════════════
# LECTURA DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def read_config(config_path: Path):
    """Lee proyectos y namespaces excluidos del archivo .config."""
    projects = []
    exclude_ns = []

    if not config_path.exists():
        return projects, exclude_ns

    in_exclude = False
    with open(config_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.split("#")[0].strip()
            if not line:
                continue
            if line == "[exclude-namespaces]":
                in_exclude = True
                continue
            if line.startswith("["):
                in_exclude = False
                continue
            if in_exclude:
                exclude_ns.append(line)
            else:
                projects.append(line)

    return projects, exclude_ns


def filter_namespaces(lines: list, exclude_ns: list) -> list:
    """Filtra namespaces excluidos de una lista de líneas."""
    if not exclude_ns:
        return lines
    pattern = re.compile(r"^\s*(" + "|".join(re.escape(ns) for ns in exclude_ns) + r")\s")
    return [line for line in lines if not pattern.match(line)]


def format_time(seconds: float) -> str:
    """Formatea segundos a cadena legible."""
    if seconds >= 60:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    return f"{int(seconds)}s"


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE INVENTARIO (una por paso)
# ═══════════════════════════════════════════════════════════════════════════════

def run_cmd(cmd: list, env: dict = None, capture: bool = True) -> str:
    """Ejecuta un comando y retorna su stdout."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            env=env, timeout=300
        )
        return result.stdout if capture else ""
    except (subprocess.TimeoutExpired, Exception):
        return ""


def get_clusters(project_id: str) -> list:
    """Obtiene lista de clusters (name, location) para un proyecto."""
    output = run_cmd([
        "gcloud", "container", "clusters", "list",
        "--project", project_id, "--format=value(name,location)", "--quiet"
    ])
    clusters = []
    for line in output.strip().splitlines():
        parts = line.strip().split("\t")
        if len(parts) >= 2:
            clusters.append((parts[0], parts[1]))
    return clusters


def step_clusters(project_id: str, out_dir: Path, delim: str) -> None:
    """1. Clusters GKE → clusters.csv"""
    output = run_cmd([
        "gcloud", "container", "clusters", "list",
        "--project", project_id, "--format=json", "--quiet"
    ])
    with open(out_dir / "clusters.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delim, quoting=csv.QUOTE_ALL)
        w.writerow(["NAME", "LOCATION", "VERSION", "CURRENT_VERSION", "STATUS", "MACHINE_TYPE"])
        data = output.strip()
        if data:
            try:
                for c in json.loads(data):
                    pools = c.get("nodePools") or []
                    mt = "|".join(p.get("config", {}).get("machineType", "") for p in pools)
                    w.writerow([
                        c.get("name", ""), c.get("location", ""),
                        c.get("currentMasterVersion", ""), c.get("currentMasterVersion", ""),
                        c.get("status", ""), mt
                    ])
            except (json.JSONDecodeError, Exception):
                pass


def step_deployments(project_id: str, out_dir: Path, delim: str, clusters: list, exclude_ns: list) -> None:
    """2. Deployments → deployments.csv"""
    with open(out_dir / "deployments.csv", "w", newline="", encoding="utf-8") as f:
        f.write(f"NAMESPACE{delim}CLUSTER{delim}DEPLOYMENT{delim}IMAGES\n")

    for cluster_name, location in clusters:
        kubeconfig = tempfile.mktemp(prefix=f"kubeconfig-inv-{project_id}-")
        env = os.environ.copy()
        env["KUBECONFIG"] = kubeconfig

        run_cmd([
            "gcloud", "container", "clusters", "get-credentials", cluster_name,
            "--location", location, "--project", project_id, "--quiet"
        ], env=env, capture=False)

        output = run_cmd([
            "kubectl", "get", "deployments", "--all-namespaces",
            "-o", "custom-columns=NAMESPACE:.metadata.namespace,DEPLOYMENT:.metadata.name,IMAGES:.spec.template.spec.containers[*].image",
            "--no-headers"
        ], env=env)

        lines = filter_namespaces(output.strip().splitlines(), exclude_ns)
        with open(out_dir / "deployments.csv", "a", newline="", encoding="utf-8") as f:
            for line in lines:
                parts = line.strip().split(None, 2)
                if len(parts) >= 3:
                    ns, deploy, images = parts[0], parts[1], parts[2]
                    images_clean = images.replace(",", ";").replace('"', "")
                    f.write(f'"{ns}"{delim}"{cluster_name}"{delim}"{deploy}"{delim}"{images_clean}"\n')

        try:
            os.unlink(kubeconfig)
        except OSError:
            pass


def step_services(project_id: str, out_dir: Path, delim: str, clusters: list, exclude_ns: list) -> None:
    """3. Services → services.csv"""
    with open(out_dir / "services.csv", "w", newline="", encoding="utf-8") as f:
        f.write(f"NAMESPACE{delim}CLUSTER{delim}NAME{delim}TYPE{delim}CLUSTER-IP{delim}EXTERNAL-IP{delim}PORTS\n")

    for cluster_name, location in clusters:
        kubeconfig = tempfile.mktemp(prefix=f"kubeconfig-inv-{project_id}-")
        env = os.environ.copy()
        env["KUBECONFIG"] = kubeconfig

        run_cmd([
            "gcloud", "container", "clusters", "get-credentials", cluster_name,
            "--location", location, "--project", project_id, "--quiet"
        ], env=env, capture=False)

        output = run_cmd([
            "kubectl", "get", "services", "--all-namespaces",
            "-o", "custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,EXTERNAL-IP:.status.loadBalancer.ingress[*].ip,PORTS:.spec.ports[*].port",
            "--no-headers"
        ], env=env)

        lines = filter_namespaces(output.strip().splitlines(), exclude_ns)
        with open(out_dir / "services.csv", "a", newline="", encoding="utf-8") as f:
            for line in lines:
                parts = line.strip().split(None, 5)
                if len(parts) >= 6:
                    ns, name, stype, cip, eip, ports = parts
                    eip_clean = eip.replace(",", ";").replace('"', "")
                    ports_clean = ports.replace(",", ";").replace('"', "")
                    f.write(f'"{ns}"{delim}"{cluster_name}"{delim}"{name}"{delim}"{stype}"{delim}"{cip}"{delim}"{eip_clean}"{delim}"{ports_clean}"\n')

        try:
            os.unlink(kubeconfig)
        except OSError:
            pass


def step_cloudsql(project_id: str, out_dir: Path, delim: str) -> int:
    """4. Cloud SQL → cloudsql.csv. Retorna cantidad de instancias."""
    instances_output = run_cmd([
        "gcloud", "sql", "instances", "list",
        "--project", project_id, "--quiet", "--format=value(name)"
    ])
    instance_count = len([l for l in instances_output.strip().splitlines() if l.strip()])

    header = f"NAME{delim}DATABASE_VERSION{delim}REGION{delim}TIER{delim}STATE{delim}PUBLIC_IP{delim}PRIVATE_IP{delim}AUTO_RESIZE{delim}BACKUP_ENABLED"

    if instance_count == 0:
        with open(out_dir / "cloudsql.csv", "w", encoding="utf-8") as f:
            f.write(header + "\n")
            f.write(f"Sin instancias{delim}-{delim}-{delim}-{delim}-{delim}-{delim}-{delim}-{delim}-\n")
        return 0

    csv_output = run_cmd([
        "gcloud", "sql", "instances", "list",
        "--project", project_id,
        f"--format=csv[no-heading,separator={delim}](name,databaseVersion,region,settings.tier,state,settings.ipConfiguration.ipv4Enabled,ipAddresses[0].ipAddress,settings.storageAutoResize,settings.backupConfiguration.enabled)",
        "--quiet"
    ])

    with open(out_dir / "cloudsql.csv", "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for line in csv_output.strip().splitlines():
            if line.strip():
                f.write(line + "\n")

    return instance_count


def step_clouddatabases(project_id: str, out_dir: Path, delim: str, instance_count: int) -> None:
    """5. Cloud SQL Databases → clouddatabases.csv"""
    with open(out_dir / "clouddatabases.csv", "w", encoding="utf-8") as f:
        f.write(f"INSTANCE{delim}DATABASE{delim}CHARSET{delim}COLLATION\n")

    if instance_count <= 0:
        with open(out_dir / "clouddatabases.csv", "a", encoding="utf-8") as f:
            f.write(f"Sin instancias{delim}-{delim}-{delim}-\n")
        return

    instances_output = run_cmd([
        "gcloud", "sql", "instances", "list",
        "--project", project_id, "--quiet", "--format=value(name)"
    ])

    for inst_name in instances_output.strip().splitlines():
        inst_name = inst_name.strip()
        if not inst_name:
            continue
        db_output = run_cmd([
            "gcloud", "sql", "databases", "list",
            "--instance", inst_name, "--project", project_id,
            f"--format=csv[no-heading,separator={delim}](name,charset,collation)",
            "--quiet"
        ])
        with open(out_dir / "clouddatabases.csv", "a", encoding="utf-8") as f:
            for line in db_output.strip().splitlines():
                if line.strip():
                    f.write(f'"{inst_name}"{delim}{line}\n')


def step_ingress(project_id: str, out_dir: Path, delim: str, clusters: list, exclude_ns: list) -> None:
    """6. Ingress → ingress.csv"""
    with open(out_dir / "ingress.csv", "w", encoding="utf-8") as f:
        f.write(f"NAMESPACE{delim}CLUSTER{delim}NAME{delim}HOSTS{delim}ADDRESS{delim}PORTS\n")

    for cluster_name, location in clusters:
        kubeconfig = tempfile.mktemp(prefix=f"kubeconfig-inv-{project_id}-")
        env = os.environ.copy()
        env["KUBECONFIG"] = kubeconfig

        run_cmd([
            "gcloud", "container", "clusters", "get-credentials", cluster_name,
            "--location", location, "--project", project_id, "--quiet"
        ], env=env, capture=False)

        output = run_cmd([
            "kubectl", "get", "ingress", "--all-namespaces",
            "-o", "custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,HOSTS:.spec.rules[*].host,ADDRESS:.status.loadBalancer.ingress[*].ip,PORTS:.spec.tls[*].secretName",
            "--no-headers"
        ], env=env)

        lines = filter_namespaces(output.strip().splitlines(), exclude_ns)
        with open(out_dir / "ingress.csv", "a", encoding="utf-8") as f:
            for line in lines:
                parts = line.strip().split(None, 4)
                if len(parts) >= 5:
                    ns, name, hosts, addr, ports = parts
                    hosts_clean = hosts.replace(",", ";").replace('"', "")
                    addr_clean = addr.replace(",", ";").replace('"', "")
                    ports_clean = ports.replace(",", ";").replace('"', "")
                    f.write(f'"{ns}"{delim}"{cluster_name}"{delim}"{name}"{delim}"{hosts_clean}"{delim}"{addr_clean}"{delim}"{ports_clean}"\n')

        try:
            os.unlink(kubeconfig)
        except OSError:
            pass

    # Limpiar líneas vacías
    csv_path = out_dir / "ingress.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(l for l in content.splitlines() if l.strip()))


def step_cloudrun(project_id: str, out_dir: Path, delim: str) -> None:
    """7. Cloud Run → cloudrun.csv"""
    output = run_cmd([
        "gcloud", "run", "services", "list",
        "--project", project_id, "--platform=managed", "--format=json", "--quiet"
    ])
    with open(out_dir / "cloudrun.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delim, quoting=csv.QUOTE_ALL)
        w.writerow(["NAME", "REGION", "URL", "LAST_DEPLOYED", "IMAGE"])
        data = output.strip()
        if data:
            try:
                for s in json.loads(data):
                    name = s.get("metadata", {}).get("name", "")
                    url = s.get("status", {}).get("url", "")
                    region = ""
                    m = re.search(r"\.([a-z]+[0-9]-[a-z]+[0-9]*)\.run\.app", url)
                    if m:
                        region = m.group(1)
                    ts = s.get("metadata", {}).get("creationTimestamp", "")
                    ctnrs = s.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                    image = ctnrs[0].get("image", "") if ctnrs else ""
                    w.writerow([name, region, url, ts, image])
            except (json.JSONDecodeError, Exception):
                pass


def step_pubsub(project_id: str, out_dir: Path, delim: str) -> None:
    """8. Pub/Sub → pubsub.csv"""
    output = run_cmd([
        "gcloud", "pubsub", "topics", "list",
        "--project", project_id, "--format=json", "--quiet"
    ])
    with open(out_dir / "pubsub.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delim, quoting=csv.QUOTE_ALL)
        w.writerow(["NAME", "LABELS"])
        data = output.strip()
        if data:
            try:
                for t in json.loads(data):
                    name = t.get("name", "").split("/")[-1]
                    if not name or name.startswith("pubsub_"):
                        continue
                    labels = t.get("labels") or {}
                    lbl = "|".join(f"{k}={v}" for k, v in labels.items())
                    w.writerow([name, lbl])
            except (json.JSONDecodeError, Exception):
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE PROYECTO
# ═══════════════════════════════════════════════════════════════════════════════

def process_project(project_id: str, delim: str, exclude_ns: list,
                    progress: Progress, task_id: int, console: Console,
                    print_lock: Lock) -> dict:
    """Procesa un proyecto completo (8 pasos). Retorna resumen."""
    project_start = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTCOME_DIR / f"inventario-{project_id}-{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {"project": project_id, "steps": {}, "time": 0, "out_dir": str(out_dir)}

    # Obtener clusters (necesario para pasos 2,3,6)
    clusters = get_clusters(project_id)

    # Definir pasos
    steps = [
        (1, lambda: step_clusters(project_id, out_dir, delim)),
        (2, lambda: step_deployments(project_id, out_dir, delim, clusters, exclude_ns)),
        (3, lambda: step_services(project_id, out_dir, delim, clusters, exclude_ns)),
        (4, lambda: step_cloudsql(project_id, out_dir, delim)),
        (5, lambda: step_clouddatabases(project_id, out_dir, delim, 0)),  # se actualiza después
        (6, lambda: step_ingress(project_id, out_dir, delim, clusters, exclude_ns)),
        (7, lambda: step_cloudrun(project_id, out_dir, delim)),
        (8, lambda: step_pubsub(project_id, out_dir, delim)),
    ]

    instance_count = 0

    for step_num, step_fn in steps:
        step_start = time.time()
        step_name = STEP_NAMES[step_num]
        icon = STEP_ICONS[step_num]
        color = STEP_COLORS[step_num]

        # Actualizar barra de progreso
        progress.update(task_id, description=f"[{color}]{icon}[/{color}] [{color}]{project_id}[/{color}] {step_name}.csv")

        try:
            if step_num == 4:
                instance_count = step_fn()
                # Actualizar paso 5 con instance_count real
                steps[4] = (5, lambda ic=instance_count: step_clouddatabases(project_id, out_dir, delim, ic))
            else:
                step_fn()
            elapsed = time.time() - step_start
            results["steps"][step_num] = {"status": "ok", "time": elapsed}

            with print_lock:
                console.print(
                    f"  [{color}]{icon}[/{color}] [{color}]{project_id}[/{color}] "
                    f"[dim]{step_name}.csv[/dim] [yellow]{format_time(elapsed)}[/yellow]"
                )
        except Exception as e:
            elapsed = time.time() - step_start
            results["steps"][step_num] = {"status": "error", "time": elapsed, "error": str(e)}
            with print_lock:
                console.print(f"  [red]✘[/red] [{color}]{project_id}[/{color}] {step_name}: [red]{e}[/red]")

        progress.advance(task_id)

    total_time = time.time() - project_start
    results["time"] = total_time

    with print_lock:
        console.print(
            f"[bold green]✅[/bold green] [bold]{project_id}[/bold] "
            f"Completado en [yellow]{format_time(total_time)}[/yellow] → [dim]{out_dir}/[/dim]"
        )

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFAZ RICH
# ═══════════════════════════════════════════════════════════════════════════════

def print_header_rich(console: Console, projects: list, exclude_ns: list,
                      delimiter: str, max_parallel: int, sequential: bool):
    """Muestra header con Rich Panel."""
    content = Text()
    content.append("📋 INVENTARIO GKE + CLOUD SQL\n\n", style="bold white")
    content.append("Separador    : ", style="dim")
    content.append(f"'{delimiter}'\n", style="yellow")
    content.append("Proyectos    : ", style="dim")
    content.append(f"{len(projects)}\n", style="white")
    for p in projects:
        content.append(f"    • {p}\n", style="dim")
    content.append("NS excluidos : ", style="dim")
    content.append(f"{', '.join(exclude_ns) if exclude_ns else 'ninguno'}\n", style="dim")
    content.append("Hilos        : ", style="dim")
    content.append(f"{'1 (secuencial)' if sequential else str(max_parallel)}\n", style="blue")
    content.append("Output       : ", style="dim")
    content.append("outcome/\n", style="green")

    panel = Panel(content, border_style="cyan", box=HEAVY, padding=(1, 2), expand=False)
    console.print(panel)
    console.print()


def print_summary_rich(console: Console, results: list, total_time: float, max_parallel: int):
    """Muestra resumen final con Rich."""
    content = Text()
    content.append("🎉 ¡Proceso COMPLETO finalizado exitosamente!\n\n", style="bold white")
    content.append("Tiempo total : ", style="dim")
    content.append(f"{format_time(total_time)}\n", style="yellow")
    content.append("Hilos usados : ", style="dim")
    content.append(f"{max_parallel}\n", style="blue")
    content.append("Proyectos    : ", style="dim")
    content.append(f"{len(results)}\n", style="white")
    content.append("Carpeta       : ", style="dim")
    content.append("outcome/\n", style="cyan")

    # Detalle por proyecto
    content.append("\n", style="")
    for r in results:
        status = "✅" if all(s["status"] == "ok" for s in r["steps"].values()) else "⚠️"
        content.append(f"  {status} {r['project']}", style="green" if status == "✅" else "yellow")
        content.append(f" — {format_time(r['time'])}\n", style="yellow")

    panel = Panel(content, border_style="green", box=HEAVY, padding=(1, 2), expand=False)
    console.print(panel)


# ═══════════════════════════════════════════════════════════════════════════════
# MODO FALLBACK (sin Rich)
# ═══════════════════════════════════════════════════════════════════════════════

def print_header_fallback(projects, exclude_ns, delimiter, max_parallel, sequential):
    print("=" * 60)
    print("  INVENTARIO GKE + CLOUD SQL - CSV")
    print(f"  Separador    : '{delimiter}'")
    print(f"  Proyectos    : {len(projects)}")
    for p in projects:
        print(f"    • {p}")
    print(f"  NS excluidos : {', '.join(exclude_ns) if exclude_ns else 'ninguno'}")
    print(f"  Hilos        : {'1 (secuencial)' if sequential else max_parallel}")
    print(f"  Output       : outcome/")
    print("=" * 60)


def print_summary_fallback(results, total_time, max_parallel):
    print()
    print("=" * 60)
    print("  ¡Proceso COMPLETO finalizado exitosamente!")
    print(f"  Tiempo total : {format_time(total_time)}")
    print(f"  Hilos usados : {max_parallel}")
    print(f"  Proyectos    : {len(results)}")
    print(f"  Carpeta       : outcome/")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Inventario GKE + Cloud SQL - Generador CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("projects", nargs="*", help="IDs de proyectos GCP")
    parser.add_argument("--delimiter", default=";", help="Separador CSV (default: ;)")
    parser.add_argument("--threads", type=int, default=4, help="Hilos paralelos (default: 4)")
    parser.add_argument("--sequential", action="store_true", help="Deshabilitar paralelismo")
    args = parser.parse_args()

    # Leer configuración
    projects = list(args.projects)
    exclude_ns = []

    if not projects:
        projects, exclude_ns = read_config(CONFIG_FILE)
        if not projects:
            print(f"❌ No se encontraron proyectos en {CONFIG_FILE}")
            sys.exit(1)

    # También leer exclude_ns si se pasaron proyectos por CLI
    if not exclude_ns:
        _, exclude_ns = read_config(CONFIG_FILE)

    OUTCOME_DIR.mkdir(parents=True, exist_ok=True)

    if RICH_AVAILABLE:
        console = Console()
        print_header_rich(console, projects, exclude_ns, args.delimiter, args.threads, args.sequential)

        start_total = time.time()
        results = []
        print_lock = Lock()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Una tarea por proyecto (8 pasos c/u)
            project_tasks = {}
            for p in projects:
                task_id = progress.add_task(f"[cyan]{p}[/cyan]", total=TOTAL_STEPS)
                project_tasks[p] = task_id

            if args.sequential:
                for p in projects:
                    r = process_project(p, args.delimiter, exclude_ns,
                                       progress, project_tasks[p], console, print_lock)
                    results.append(r)
            else:
                with ThreadPoolExecutor(max_workers=args.threads) as executor:
                    futures = {}
                    for p in projects:
                        future = executor.submit(
                            process_project, p, args.delimiter, exclude_ns,
                            progress, project_tasks[p], console, print_lock
                        )
                        futures[future] = p

                    for future in as_completed(futures):
                        try:
                            r = future.result()
                            results.append(r)
                        except Exception as e:
                            p = futures[future]
                            console.print(f"[red]✘ {p}: {e}[/red]")
                            results.append({"project": p, "steps": {}, "time": 0, "error": str(e)})

        total_time = time.time() - start_total
        console.print()
        print_summary_rich(console, results, total_time, args.threads)

    else:
        # Modo fallback sin Rich
        print_header_fallback(projects, exclude_ns, args.delimiter, args.threads, args.sequential)
        start_total = time.time()
        results = []

        for p in projects:
            project_start = time.time()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = OUTCOME_DIR / f"inventario-{p}-{timestamp}"
            out_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n▶ [{p}] Iniciando inventario...")
            clusters = get_clusters(p)
            instance_count = 0

            step_fns = [
                lambda: step_clusters(p, out_dir, args.delimiter),
                lambda: step_deployments(p, out_dir, args.delimiter, clusters, exclude_ns),
                lambda: step_services(p, out_dir, args.delimiter, clusters, exclude_ns),
                lambda: step_cloudsql(p, out_dir, args.delimiter),
                lambda: step_clouddatabases(p, out_dir, args.delimiter, instance_count),
                lambda: step_ingress(p, out_dir, args.delimiter, clusters, exclude_ns),
                lambda: step_cloudrun(p, out_dir, args.delimiter),
                lambda: step_pubsub(p, out_dir, args.delimiter),
            ]

            for i, fn in enumerate(step_fns, 1):
                step_start = time.time()
                step_name = STEP_NAMES[i]
                print(f"  → [{p}] {step_name}.csv")
                try:
                    if i == 4:
                        instance_count = fn()
                        step_fns[4] = lambda ic=instance_count: step_clouddatabases(p, out_dir, args.delimiter, ic)
                    else:
                        fn()
                    elapsed = time.time() - step_start
                    print(f"   └─ [{p}] {step_name}: {format_time(elapsed)}")
                except Exception as e:
                    print(f"   └─ [{p}] {step_name}: ERROR {e}")

            total = time.time() - project_start
            print(f"✓ [{p}] Completado en {format_time(total)} → {out_dir}/")
            results.append({"project": p, "steps": {}, "time": total})

        total_time = time.time() - start_total
        print_summary_fallback(results, total_time, args.threads)


if __name__ == "__main__":
    main()
