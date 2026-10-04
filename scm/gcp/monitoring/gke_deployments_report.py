#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gke_deployments_report.py

Genera un reporte detallado de Deployments en GKE, incluyendo:

- cluster
- namespace
- deployment
- cantidad de pods (ready/desired)
- status (Running/Pending/Failed/Unknown)
- cantidad de restarts (suma de todos los pods)
- age (desde creationTimestamp)
- cpu y memory usados (a nivel de pods, requiere metrics-server)
- requests/limits de CPU y memoria
- timestamp de generación, tanto en el TXT como dentro de cada objeto JSON
- resúmenes:
  - por STATUS
  - por STATUS + LIMITS (CPU/MEMORY)
"""

import argparse
import csv
import json
import os
import sys
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from collections import Counter, defaultdict

from kubernetes import client, config
from kubernetes.client import ApiException
from tabulate import tabulate

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.spinner import Spinner
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import (get_output_dir, gke_kube_env, gke_context_name,
                       gke_location_flag, ensure_gke_cluster_credentials,
                       is_live_terminal)
except ImportError:
    import os as _os
    import sys as _sys
    import atexit as _ax
    import shutil as _sh
    import tempfile as _tf
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
    def is_live_terminal():
        if _sys.stdout.isatty():
            return True
        return _os.environ.get("TTY_COMPATIBLE", "").strip().lower() in {
            "1", "true", "yes", "on"}
    _KCFG_DIR = _Path(_tf.mkdtemp(prefix="gke-kubeconfig-"))
    _ax.register(lambda: _sh.rmtree(_KCFG_DIR, ignore_errors=True))
    def gke_kube_env(cluster_name, project_id=""):
        env = _os.environ.copy()
        key = f"{project_id}-{cluster_name}" if project_id else cluster_name
        env["KUBECONFIG"] = str(_KCFG_DIR / f"{key}.yaml")
        return env
    def gke_context_name(project_id, location, cluster_name):
        return f"gke_{project_id}_{location}_{cluster_name}"
    def gke_location_flag(location):
        return f"--zone={location}" if location.count("-") == 2 else f"--region={location}"
    def ensure_gke_cluster_credentials(project_id, cluster_name, location,
                                       timeout=60, debug=False, logger=None):
        cmd = (f"gcloud container clusters get-credentials {cluster_name} "
               f"--project={project_id} {gke_location_flag(location)} --quiet")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               timeout=timeout, env=gke_kube_env(cluster_name, project_id))
            return r.returncode == 0
        except Exception:
            return False
# -------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Utilidades de parsing de recursos (CPU/Memoria) de Kubernetes
# ---------------------------------------------------------------------------


try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


def setup_logger(output_dir: str = "outcome") -> logging.Logger:
    """Configura el logger para registrar comandos ejecutados."""
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = output_path / f"gke_deployments_report_{timestamp}.log"
    
    logger = logging.getLogger("gke_deployments_report")
    logger.setLevel(logging.INFO)
    
    handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def tabulate_to_rich_table(tabulate_output, title="Datos"):
    """Convierte salida de tabulate a tabla Rich."""
    lines = tabulate_output.strip().split('\n')
    if len(lines) < 2:
        return None
    
    # Encontrar la línea de headers (primera línea con | que contiene texto, no solo separadores)
    header_idx = -1
    for i, line in enumerate(lines):
        if '|' in line:
            # Verificar si tiene contenido (no es solo separadores)
            content = [c.strip() for c in line.split('|') if c.strip() and c.strip() not in ['-', '=']]
            if content:
                header_idx = i
                break
    
    if header_idx == -1:
        return None
    
    headers = [h.strip() for h in lines[header_idx].split('|') if h.strip() and h.strip() not in ['-', '=']]
    if not headers:
        return None
    
    table = Table(title=title, show_header=True, header_style="bold cyan")
    
    for header in headers:
        table.add_column(header, style="white")
    
    # Procesar líneas de datos (después de la línea de separación que sigue a headers)
    data_start = header_idx + 2
    for line in lines[data_start:]:
        if '|' in line:
            # Verificar si es una línea de separador (solo contiene -, =, |)
            if all(c in '|-=┃┏┓┗┛┣┫┳┻━' for c in line):
                continue
            
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c]
            
            if len(cells) > 0:
                # Rellenar o truncar para que coincida con el número de headers
                if len(cells) < len(headers):
                    cells.extend([''] * (len(headers) - len(cells)))
                elif len(cells) > len(headers):
                    cells = cells[:len(headers)]
                
                table.add_row(*cells)
    
    return table


def print_execution_summary(start_time, end_time, log_file, console):
    """Imprime resumen de ejecución con Rich."""
    duration = end_time - start_time
    
    if RICH_AVAILABLE and console:
        table = Table(title="⏱️ Resumen de Ejecución", box=None)
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Tiempo de ejecución", f"{duration:.2f}s")
        table.add_row("Archivo de log", str(log_file))
        
        console.print()
        console.print(Panel(table, border_style="blue"))
    else:
        print(f"\n⏱️ Tiempo de ejecución: {duration:.2f}s")
        print(f"📝 Archivo de log: {log_file}")


def parse_cpu_to_cores(cpu_str):
    """
    Convierte una cadena de CPU de Kubernetes a núcleos (float).
    Ejemplos:
      "100m" -> 0.1
      "250m" -> 0.25
      "1"    -> 1.0
      "2"    -> 2.0
    """
    if cpu_str is None:
        return None
    cpu_str = str(cpu_str).strip()
    if cpu_str.endswith("m"):
        try:
            return float(cpu_str[:-1]) / 1000.0
        except ValueError:
            return None
    else:
        try:
            return float(cpu_str)
        except ValueError:
            return None


def parse_memory_to_mebibytes(mem_str):
    """
    Convierte una cadena de memoria de Kubernetes a MiB (float).
    Ejemplos:
      "128974848" -> 128974848 / (1024^2)
      "129M"      -> 129 * 10^6 / (1024^2)
      "123Mi"     -> 123 MiB
      "1Gi"       -> 1024 MiB
      "1G"        -> (10^9) / (1024^2)
    """
    if mem_str is None:
        return None
    mem_str = str(mem_str).strip()

    # Si son bytes puros
    if mem_str.isdigit():
        try:
            return float(mem_str) / (1024.0 ** 2)
        except ValueError:
            return None

    suffixes = {
        "Ki": 1024 ** 1,
        "Mi": 1024 ** 2,
        "Gi": 1024 ** 3,
        "Ti": 1024 ** 4,
        "Pi": 1024 ** 5,
        "Ei": 1024 ** 6,
        "K": 10 ** 3,
        "M": 10 ** 6,
        "G": 10 ** 9,
        "T": 10 ** 12,
        "P": 10 ** 15,
        "E": 10 ** 18,
    }

    for suf, factor in suffixes.items():
        if mem_str.endswith(suf):
            num_part = mem_str[: -len(suf)]
            try:
                bytes_val = float(num_part) * factor
                return bytes_val / (1024.0 ** 2)
            except ValueError:
                return None

    try:
        val = float(mem_str)
        return val / (1024.0 ** 2)
    except ValueError:
        return None


def format_cpu(cores):
    if cores is None:
        return "N/A"
    return f"{cores:.2f} cores"


def format_memory(mib):
    if mib is None:
        return "N/A"
    return f"{mib:.0f} Mi"


# ---------------------------------------------------------------------------
# Lógica principal para obtener información de Deployments y Pods
# ---------------------------------------------------------------------------

def list_gke_clusters(project_id: str, logger=None) -> list:
    """Lista clusters GKE del proyecto: [(name, location), ...]."""
    cmd = f'gcloud container clusters list --project={project_id} --format=json'
    if logger:
        logger.info(f"Ejecutando: {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            if logger:
                logger.error(f"clusters list falló para {project_id}: {r.stderr[:200]}")
            return []
        return [(c.get('name', ''), c.get('location', '')) for c in json.loads(r.stdout)]
    except Exception as e:
        if logger:
            logger.error(f"Excepción listando clusters de {project_id}: {e}")
        return []


def get_deployments_report(project_id: str, cluster_name: str, location: str, logger=None):
    """
    Devuelve una lista de dicts con la información de cada Deployment:

      - project
      - cluster
      - namespace
      - deployment
      - pods (ready/desired)
      - pod_count (desired)
      - status
      - restarts
      - age
      - cpu (uso total de pods)
      - memory (uso total de pods)
      - request_cpu (suma requests containers)
      - request_memory (suma requests containers)
      - limit_cpu (suma limits containers)
      - limit_memory (suma limits containers)
    """
    if not ensure_gke_cluster_credentials(project_id, cluster_name, location, logger=logger):
        raise RuntimeError(
            f"get-credentials falló para {cluster_name} ({project_id}, {location})")

    # KUBECONFIG aislado por (proyecto, cluster) — seguro en paralelo
    # (no toca ~/.kube/config ni pisa credenciales de clusters homónimos)
    kubeconfig_path = gke_kube_env(cluster_name, project_id)["KUBECONFIG"]
    context = gke_context_name(project_id, location, cluster_name)

    api_client = config.new_client_from_config(
        config_file=kubeconfig_path, context=context
    )
    apps_v1 = client.AppsV1Api(api_client)
    core_v1 = client.CoreV1Api(api_client)
    custom_api = client.CustomObjectsApi(api_client)

    try:
        ns_list = core_v1.list_namespace(_request_timeout=10)
        namespaces = [ns.metadata.name for ns in ns_list.items]
    except Exception as e:
        short = str(e).splitlines()[0][:200]
        print(f"[ERROR] No se pudo conectar al cluster {cluster_name} "
              f"({project_id}, {location}): {short}")
        raise

    report_rows = []

    for ns in namespaces:
        try:
            deployments = apps_v1.list_namespaced_deployment(namespace=ns, _request_timeout=10)
        except ApiException as e:
            print(f"[WARN] No se pudieron listar deployments en namespace {ns}: {e}")
            continue

        for dep in deployments.items:
            dep_name = dep.metadata.name
            creation_ts = dep.metadata.creation_timestamp
            age = calc_age_days(creation_ts)

            desired_replicas = dep.spec.replicas or 0

            match_labels = dep.spec.selector.match_labels or {}
            label_selector = ",".join(f"{k}={v}" for k, v in match_labels.items())

            try:
                pods = core_v1.list_namespaced_pod(
                    namespace=ns, label_selector=label_selector, _request_timeout=10
                )
            except ApiException as e:
                print(f"[WARN] No se pudieron listar pods para {dep_name} en {ns}: {e}")
                continue

            ready_pods = 0
            total_restarts = 0
            pod_statuses = set()

            for pod in pods.items:
                phase = pod.status.phase or "Unknown"
                pod_statuses.add(phase)

                pod_ready = False
                if pod.status.conditions:
                    for cond in pod.status.conditions:
                        if cond.type == "Ready" and cond.status == "True":
                            pod_ready = True
                            break
                if pod_ready:
                    ready_pods += 1

                if pod.status.container_statuses:
                    for cstat in pod.status.container_statuses:
                        total_restarts += cstat.restart_count or 0

            # Métricas de uso (metrics-server / metrics.k8s.io)
            total_cpu_usage_cores = 0.0
            total_mem_usage_mib = 0.0
            got_any_usage = False

            try:
                pod_metrics = custom_api.list_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace=ns,
                    plural="pods",
                    _request_timeout=10
                )
            except ApiException as e:
                pod_metrics = None
                print(
                    f"[INFO] No se pudieron obtener métricas (metrics-server) "
                    f"para namespace {ns}: {e}"
                )

            if pod_metrics and "items" in pod_metrics:
                metrics_by_pod = {
                    item["metadata"]["name"]: item for item in pod_metrics["items"]
                }
                for pod in pods.items:
                    p_name = pod.metadata.name
                    if p_name not in metrics_by_pod:
                        continue
                    m_item = metrics_by_pod[p_name]
                    for c in m_item.get("containers", []):
                        usage = c.get("usage", {})
                        cpu_u = parse_cpu_to_cores(usage.get("cpu"))
                        mem_u = parse_memory_to_mebibytes(usage.get("memory"))
                        if cpu_u is not None:
                            total_cpu_usage_cores += cpu_u
                            got_any_usage = True
                        if mem_u is not None:
                            total_mem_usage_mib += mem_u
                            got_any_usage = True

            if not got_any_usage:
                total_cpu_usage_cores = None
                total_mem_usage_mib = None

            (sum_req_cpu, sum_req_mem, sum_lim_cpu, sum_lim_mem) = sum_deployment_requests_limits(dep)

            status_str = determine_deployment_status(pod_statuses, desired_replicas, ready_pods)

            row = {
                "project": project_id,
                "cluster": cluster_name,
                "namespace": ns,
                "deployment": dep_name,
                "pods": f"{ready_pods}/{desired_replicas}",
                "pod_count": desired_replicas,
                "status": status_str,
                "restarts": total_restarts,
                "age": f"{age}d",
                "cpu": format_cpu(total_cpu_usage_cores),
                "memory": format_memory(total_mem_usage_mib),
                "request_cpu": format_cpu(sum_req_cpu),
                "request_memory": format_memory(sum_req_mem),
                "limit_cpu": format_cpu(sum_lim_cpu),
                "limit_memory": format_memory(sum_lim_mem),
            }

            report_rows.append(row)

    return report_rows


def calc_age_days(creation_timestamp):
    if not creation_timestamp:
        return "N/A"
    if not creation_timestamp.tzinfo:
        creation_timestamp = creation_timestamp.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - creation_timestamp
    return delta.days


def sum_deployment_requests_limits(dep):
    sum_req_cpu = 0.0
    sum_req_mem = 0.0
    sum_lim_cpu = 0.0
    sum_lim_mem = 0.0

    got_req_cpu = False
    got_req_mem = False
    got_lim_cpu = False
    got_lim_mem = False

    tmpl = dep.spec.template
    if not tmpl or not tmpl.spec or not tmpl.spec.containers:
        return (None, None, None, None)

    for c in tmpl.spec.containers:
        resources = c.resources or {}
        requests = resources.requests or {}
        limits = resources.limits or {}

        cpu_req = parse_cpu_to_cores(requests.get("cpu"))
        mem_req = parse_memory_to_mebibytes(requests.get("memory"))
        cpu_lim = parse_cpu_to_cores(limits.get("cpu"))
        mem_lim = parse_memory_to_mebibytes(limits.get("memory"))

        if cpu_req is not None:
            sum_req_cpu += cpu_req
            got_req_cpu = True
        if mem_req is not None:
            sum_req_mem += mem_req
            got_req_mem = True
        if cpu_lim is not None:
            sum_lim_cpu += cpu_lim
            got_lim_cpu = True
        if mem_lim is not None:
            sum_lim_mem += mem_lim
            got_lim_mem = True

    if not got_req_cpu:
        sum_req_cpu = None
    if not got_req_mem:
        sum_req_mem = None
    if not got_lim_cpu:
        sum_lim_cpu = None
    if not got_lim_mem:
        sum_lim_mem = None

    return (sum_req_cpu, sum_req_mem, sum_lim_cpu, sum_lim_mem)


def determine_deployment_status(pod_statuses, desired, ready):
    if desired == 0:
        return "ScaledToZero"

    if ready == desired and pod_statuses == {"Running"}:
        return "Running"

    if "Failed" in pod_statuses:
        return "Degraded"

    if "Pending" in pod_statuses and ready < desired:
        return "Progressing"

    if not pod_statuses:
        return "Unknown"

    if "Unknown" in pod_statuses:
        return "Unknown"

    return ",".join(sorted(pod_statuses))


# ---------------------------------------------------------------------------
# Formateo de tablas y resúmenes
# ---------------------------------------------------------------------------

def restart_level(restarts) -> str:
    """Severidad por restarts: 'high' >10, 'warn' >4, 'ok' el resto."""
    try:
        n = int(restarts)
    except (TypeError, ValueError):
        return "ok"
    if n > 10:
        return "high"
    if n > 4:
        return "warn"
    return "ok"


def restart_markup(restarts) -> str:
    """Celda de restarts con markup Rich: blanco/rojo >10, negro/amarillo >4."""
    level = restart_level(restarts)
    if level == "high":
        return f"[white on red] {restarts} [/]"
    if level == "warn":
        return f"[black on yellow] {restarts} [/]"
    return str(restarts)


def build_detailed_rich_table(report_data):
    """Tabla Rich del detalle con la columna Restarts resaltada por severidad.

    (tabulate_to_rich_table no permite estilos por celda: se construye nativa)
    """
    headers = [
        "Project", "Cluster", "Namespace", "Deployment",
        "Pods (ready/desired)", "Status", "Restarts", "Age",
        "CPU usage", "Memory usage", "Req CPU", "Req Mem", "Lim CPU", "Lim Mem",
    ]
    table = Table(title="📊 Reporte Detallado de Deployments",
                  show_header=True, header_style="bold cyan")
    for h in headers:
        table.add_column(h, style="white")
    keys = ["project", "cluster", "namespace", "deployment", "pods", "status",
            "restarts", "age", "cpu", "memory", "request_cpu", "request_memory",
            "limit_cpu", "limit_memory"]
    for r in report_data:
        row = [restart_markup(r["restarts"]) if k == "restarts" else str(r[k])
               for k in keys]
        table.add_row(*row)
    return table


def format_detailed_table(report_data):
    headers = [
        "Project",
        "Cluster",
        "Namespace",
        "Deployment",
        "Pods (ready/desired)",
        "Status",
        "Restarts",
        "Age",
        "CPU usage",
        "Memory usage",
        "Req CPU",
        "Req Mem",
        "Lim CPU",
        "Lim Mem",
    ]
    rows = []
    for r in report_data:
        rows.append(
            [
                r["project"],
                r["cluster"],
                r["namespace"],
                r["deployment"],
                r["pods"],
                r["status"],
                r["restarts"],
                r["age"],
                r["cpu"],
                r["memory"],
                r["request_cpu"],
                r["request_memory"],
                r["limit_cpu"],
                r["limit_memory"],
            ]
        )

    return tabulate(rows, headers=headers, tablefmt="github")


def format_cluster_errors(cluster_errors):
    """Tabla de clusters no accesibles (proyecto, cluster, ubicación, error)."""
    if not cluster_errors:
        return ""
    headers = ["Project", "Cluster", "Location", "Error"]
    rows = [
        [e["project"], e["cluster"], e["location"], e["error"][:160]]
        for e in cluster_errors
    ]
    return tabulate(rows, headers=headers, tablefmt="github")


def format_status_summary(report_data):
    """Resumen por Proyecto + Status."""
    counter = Counter((r.get("project", "N/A"), r["status"]) for r in report_data)
    rows = [
        [project, status, count]
        for (project, status), count in sorted(counter.items())
    ]
    return tabulate(
        rows, headers=["Project", "Status", "Deployments"], tablefmt="github"
    )


def format_limits_status_summary(report_data):
    """
    Resumen por DEPLOYMENTS + LIMIT_CPU + LIMIT_MEM + STATUS:
    Ordenado descendentemente por DEPLOYMENTS
    """
    groups = defaultdict(lambda: {"deployments": 0, "pods_ready": 0, "restarts": 0})

    for r in report_data:
        project = r.get("project", "N/A")
        status = r["status"]
        lim_cpu = r["limit_cpu"]
        lim_mem = r["limit_memory"]
        pods_field = r["pods"]  # "ready/desired"
        restarts = r["restarts"]

        try:
            ready_str, _ = pods_field.split("/", 1)
            ready_int = int(ready_str)
        except Exception:
            ready_int = 0

        key = (project, status, lim_cpu, lim_mem)
        groups[key]["deployments"] += 1
        groups[key]["pods_ready"] += ready_int
        groups[key]["restarts"] += restarts

    rows = []
    for (project, status, lim_cpu, lim_mem), agg in sorted(
        groups.items(),
        key=lambda x: (x[0][0], -x[1]["deployments"], x[0][1], x[0][2], x[0][3]),
    ):
        rows.append(
            [
                project,
                agg["deployments"],
                lim_cpu,
                lim_mem,
                agg["pods_ready"],
                agg["restarts"],
                status,
            ]
        )

    title = "RESUMEN POR STATUS + LIMITS (CPU/MEMORY)"
    if not rows:
        return title + "\n(No hay datos)"

    table = tabulate(
        rows,
        headers=[
            "PROJECT",
            "DEPLOYMENTS",
            "LIMIT_CPU",
            "LIMIT_MEM",
            "PODS_READY",
            "RESTARTS",
            "STATUS",
        ],
        tablefmt="github",
    )

    # Para que se parezca al formato que te gustó (con título y línea abajo)
    return f"{title}\n{table}"


# ---------------------------------------------------------------------------
# Escritura de archivos
# ---------------------------------------------------------------------------

def write_csv(report_data, filepath):
    fieldnames = [
        "project",
        "cluster",
        "namespace",
        "deployment",
        "pods",
        "pod_count",
        "status",
        "restarts",
        "age",
        "cpu",
        "memory",
        "request_cpu",
        "request_memory",
        "limit_cpu",
        "limit_memory",
        "generated_at",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in report_data:
            writer.writerow(row)


def write_json(report_data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Reporte HTML (estilo equivalente al dashboard de la opcion 1)
# ---------------------------------------------------------------------------

_REPORT_CSS = """
:root {
    --bg-dark: #0f1419;
    --bg-card: #1a1f26;
    --border: #2d3748;
    --text-primary: #e2e8f0;
    --text-secondary: #a0aec0;
    --success: #48bb78;
    --warning: #ed8936;
    --danger: #f56565;
    --info: #4299e1;
    --gray: #718096;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-primary);
    line-height: 1.6;
}

.container { max-width: 1500px; margin: 0 auto; padding: 20px; }

header { margin-bottom: 30px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }
h1 { font-size: 2.2em; margin-bottom: 10px; color: var(--info); }
.header-meta { display: flex; flex-wrap: wrap; gap: 20px; color: var(--text-secondary); font-size: 0.9em; }

.filters { background-color: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 30px; }
.filters h3 { color: var(--info); margin-bottom: 15px; font-size: 1.05em; }
.filter-group { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }
.filter-label { display: block; margin-bottom: 5px; font-size: 0.85em; color: var(--text-secondary); }
select, input { background-color: var(--bg-dark); color: var(--text-primary); border: 1px solid var(--border); border-radius: 4px; padding: 10px; font-size: 0.9em; width: 100%; }
select:focus, input:focus { outline: none; border-color: var(--info); box-shadow: 0 0 5px rgba(66, 153, 225, 0.3); }
.btn-reset { background-color: var(--info); color: #ffffff; border: none; border-radius: 4px; padding: 10px 20px; cursor: pointer; font-size: 0.9em; transition: background-color 0.3s ease; width: 100%; }
.btn-reset:hover { background-color: #3182ce; }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 15px; margin-bottom: 30px; }
.kpi-card { background-color: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 18px; cursor: pointer; transition: all 0.3s ease; }
.kpi-card:hover { border-color: var(--info); box-shadow: 0 0 10px rgba(66, 153, 225, 0.2); }
.kpi-label { color: var(--text-secondary); font-size: 0.78em; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value { font-size: 1.9em; font-weight: bold; color: var(--info); }
.kpi-value.danger { color: var(--danger); }
.kpi-value.warn { color: var(--warning); }

.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background-color: var(--bg-card); }
table.data-table { width: 100%; border-collapse: collapse; font-size: 0.88em; }
table.data-table th { background-color: var(--bg-dark); padding: 12px; text-align: left; font-weight: 600; color: var(--info); border-bottom: 1px solid var(--border); white-space: nowrap; }
table.data-table th .th-label { cursor: pointer; user-select: none; }
table.data-table th .th-label:hover { text-decoration: underline; }
table.data-table th.sorted .th-label { color: var(--text-primary); }
.sort-indicator { margin-left: 4px; font-size: 0.8em; color: var(--info); }
table.data-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; max-width: 340px; overflow: hidden; text-overflow: ellipsis; }
table.data-table tbody tr:hover td { background-color: rgba(66, 153, 225, 0.08); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.empty-row { text-align: center; color: var(--text-secondary); padding: 30px !important; white-space: normal !important; }

.status-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.82em; font-weight: 500; white-space: nowrap; }
.badge-ok { background-color: rgba(72, 187, 120, 0.2); color: var(--success); }
.badge-warn { background-color: rgba(237, 137, 54, 0.2); color: var(--warning); }
.badge-bad { background-color: rgba(245, 101, 101, 0.2); color: var(--danger); }
.badge-muted { background-color: rgba(113, 128, 150, 0.2); color: var(--gray); }

.restarts-high { background-color: #c53030; color: #ffffff; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.restarts-warn { background-color: #ecc94b; color: #000000; font-weight: 700; padding: 2px 8px; border-radius: 4px; }

.section-title { color: var(--info); margin: 30px 0 15px 0; font-size: 1.3em; }
.row-count { color: var(--text-secondary); font-size: 0.85em; margin: 12px 0 30px 0; }
.footer { text-align: center; color: var(--text-secondary); font-size: 0.85em; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); }

@media (max-width: 768px) {
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
    h1 { font-size: 1.6em; }
    .header-meta { flex-direction: column; gap: 5px; }
}
"""

# JS plano (sin f-strings) — los datos se inyectan en var REPORT del <script> previo.
_REPORT_JS = r"""
var sortKey = null;
var sortDir = 1;

var BADGE = {
    'Running': 'ok',
    'Progressing': 'warn',
    'Degraded': 'bad',
    'Failed': 'bad',
    'ScaledToZero': 'muted',
    'Unknown': 'muted'
};

function badgeFor(status) {
    var cls = BADGE[status] || 'muted';
    return '<span class="status-badge badge-' + cls + '">' + esc(status) + '</span>';
}

function restartsCell(n) {
    if (n > 10) return '<span class="restarts-high">' + n + '</span>';
    if (n > 4) return '<span class="restarts-warn">' + n + '</span>';
    return String(n);
}

function esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function filteredRows() {
    var p = document.getElementById('filterProject').value;
    var s = document.getElementById('filterStatus').value;
    var q = document.getElementById('filterSearch').value.toLowerCase();
    var minR = parseInt(document.getElementById('filterRestarts').value || '0', 10);
    return REPORT.rows.filter(function (r) {
        if (p && r.project !== p) return false;
        if (s && r.status !== s) return false;
        if (r.restarts < minR) return false;
        if (q && JSON.stringify(r).toLowerCase().indexOf(q) === -1) return false;
        return true;
    });
}

var COLS = [
    { key: 'project', label: 'Project' },
    { key: 'cluster', label: 'Cluster' },
    { key: 'namespace', label: 'Namespace' },
    { key: 'deployment', label: 'Deployment' },
    { key: 'pods', label: 'Pods (ready/desired)' },
    { key: 'status', label: 'Status', badge: true },
    { key: 'restarts', label: 'Restarts', right: true, restarts: true },
    { key: 'age', label: 'Age' },
    { key: 'cpu', label: 'CPU usage' },
    { key: 'memory', label: 'Memory usage' },
    { key: 'request_cpu', label: 'Req CPU' },
    { key: 'request_memory', label: 'Req Mem' },
    { key: 'limit_cpu', label: 'Lim CPU' },
    { key: 'limit_memory', label: 'Lim Mem' }
];

function sortRows(rows) {
    if (!sortKey) return rows;
    return rows.slice().sort(function (a, b) {
        var va = a[sortKey], vb = b[sortKey];
        if (typeof va === 'number' && typeof vb === 'number') {
            return (va - vb) * sortDir;
        }
        return String(va).localeCompare(String(vb)) * sortDir;
    });
}

function sortBy(key) {
    if (sortKey === key) { sortDir = -sortDir; } else { sortKey = key; sortDir = 1; }
    render();
}

function render() {
    var head = '<tr>' + COLS.map(function (c) {
        var ind = sortKey === c.key ? '<span class="sort-indicator">' + (sortDir > 0 ? '▲' : '▼') + '</span>' : '';
        var cls = sortKey === c.key ? ' class="sorted"' : '';
        return '<th' + cls + '><span class="th-label" onclick="sortBy(\'' + c.key + '\')">' +
               c.label + ind + '</span></th>';
    }).join('') + '</tr>';

    var rows = sortRows(filteredRows());
    var body;
    if (!rows.length) {
        body = '<tr><td class="empty-row" colspan="' + COLS.length + '">Sin resultados</td></tr>';
    } else {
        body = rows.map(function (r) {
            return '<tr>' + COLS.map(function (c) {
                var v = r[c.key];
                var cls = c.right ? ' class="num"' : '';
                if (c.badge) return '<td>' + badgeFor(v) + '</td>';
                if (c.restarts) return '<td' + cls + '>' + restartsCell(v) + '</td>';
                return '<td' + cls + '>' + esc(v) + '</td>';
            }).join('') + '</tr>';
        }).join('');
    }

    document.getElementById('deploymentsTable').innerHTML =
        '<table class="data-table"><thead>' + head + '</thead><tbody>' + body + '</tbody></table>';
    document.getElementById('rowCount').textContent =
        rows.length + ' de ' + REPORT.rows.length + ' deployments';
}

function applyFilters() { render(); }

function resetFilters() {
    document.getElementById('filterProject').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterRestarts').value = '0';
    document.getElementById('filterSearch').value = '';
    render();
}

function kpiMinRestarts(n) {
    document.getElementById('filterRestarts').value = String(n);
    render();
}

function renderErrors() {
    var wrap = document.getElementById('errorsSection');
    if (!REPORT.errors.length) { wrap.innerHTML = ''; return; }
    var rows = REPORT.errors.map(function (e) {
        return '<tr><td>' + esc(e.project) + '</td><td>' + esc(e.cluster) + '</td><td>' +
               esc(e.location) + '</td><td>' + esc(e.error) + '</td></tr>';
    }).join('');
    wrap.innerHTML =
        '<h2 class="section-title">🔌 Clusters no accesibles (' + REPORT.errors.length + ')</h2>' +
        '<div class="table-wrap"><table class="data-table"><thead><tr>' +
        '<th>Project</th><th>Cluster</th><th>Location</th><th>Error</th>' +
        '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

renderErrors();
render();
"""


def _json_for_html(obj) -> str:
    """Serializa a JSON seguro para embeber dentro de un tag <script>."""
    return json.dumps(obj, ensure_ascii=False, default=str).replace('</', '<\\/')


def build_html_report(report_data, cluster_errors, generated_at, project_ids) -> str:
    """HTML autocontenido del reporte, equivalente al dashboard de la opcion 1."""
    total = len(report_data)
    running = sum(1 for r in report_data if r.get("status") == "Running")
    not_running = total - running
    restarts_high = sum(1 for r in report_data if restart_level(r.get("restarts")) == "high")
    restarts_warn = sum(1 for r in report_data if restart_level(r.get("restarts")) == "warn")
    clusters_ok = len({(r.get("project"), r.get("cluster")) for r in report_data})
    clusters_bad = len(cluster_errors)

    projects_sorted = sorted({r.get("project", "") for r in report_data} | set(project_ids))
    project_options = "\n".join(
        f'                        <option value="{p}">{p}</option>' for p in projects_sorted)
    statuses = sorted({r.get("status", "") for r in report_data} - {""})
    status_options = "\n".join(
        f'                        <option value="{s}">{s}</option>' for s in statuses)

    payload = _json_for_html({
        "generated_at": generated_at,
        "rows": report_data,
        "errors": cluster_errors,
    })

    kpis = [
        ("📦 Deployments", total, "kpiMinRestarts(0)", ""),
        ("✅ Running", running, "kpiMinRestarts(0)", ""),
        ("⚠️ No Running", not_running, "kpiMinRestarts(0)", "warn" if not_running else ""),
        ("🔁 Restarts &gt; 10", restarts_high, "kpiMinRestarts(11)", "danger" if restarts_high else ""),
        ("🔁 Restarts &gt; 4", restarts_warn + restarts_high, "kpiMinRestarts(5)", "warn" if (restarts_warn + restarts_high) else ""),
        ("☸️ Clusters", clusters_ok, "kpiMinRestarts(0)", ""),
        ("🔌 No accesibles", clusters_bad, "", "danger" if clusters_bad else ""),
    ]
    kpi_html = "\n".join(
        '                <div class="kpi-card" onclick="{action}">\n'
        '                    <div class="kpi-label">{label}</div>\n'
        '                    <div class="kpi-value {cls}">{value}</div>\n'
        '                </div>'.format(action=action, label=label, cls=cls, value=value)
        for label, value, action, cls in kpis)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GKE Deployments Report</title>
    <style>
{_REPORT_CSS}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>☸️ GKE Deployments Report</h1>
            <div class="header-meta">
                <span>Generado (UTC): {generated_at}</span>
                <span>Proyectos: {len(project_ids)}</span>
                <span>Clusters consultados: {clusters_ok + clusters_bad}</span>
            </div>
        </header>

        <div class="kpi-grid">
{kpi_html}
        </div>

        <div class="filters">
            <h3>🔍 Filtros</h3>
            <div class="filter-group">
                <div>
                    <label class="filter-label" for="filterProject">Proyecto</label>
                    <select id="filterProject" onchange="applyFilters()">
                        <option value="">Todos los proyectos</option>
{project_options}
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterStatus">Status</label>
                    <select id="filterStatus" onchange="applyFilters()">
                        <option value="">Todos los status</option>
{status_options}
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterRestarts">Restarts mínimos</label>
                    <select id="filterRestarts" onchange="applyFilters()">
                        <option value="0">Todos</option>
                        <option value="5">&gt; 4</option>
                        <option value="11">&gt; 10</option>
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterSearch">Búsqueda</label>
                    <input type="text" id="filterSearch" placeholder="Buscar en la tabla..." onkeyup="applyFilters()">
                </div>
                <div style="display: flex; align-items: flex-end;">
                    <button class="btn-reset" onclick="resetFilters()">🔄 Restablecer</button>
                </div>
            </div>
        </div>

        <h2 class="section-title">📊 Deployments</h2>
        <div class="table-wrap" id="deploymentsTable"></div>
        <div class="row-count" id="rowCount"></div>

        <div id="errorsSection"></div>

        <footer class="footer">
            <p>GKE Deployments Report | Generado automáticamente por DevSecOps Toolbox</p>
        </footer>
    </div>
    <script>var REPORT = {payload};</script>
    <script>{_REPORT_JS}</script>
</body>
</html>
"""


def write_html(report_data, cluster_errors, filepath, generated_at, project_ids):
    html = build_html_report(report_data, cluster_errors, generated_at, project_ids)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()
    
    parser = argparse.ArgumentParser(
        description=(
            "Genera reporte detallado de Deployments en GKE "
            "(TXT + CSV + JSON + resúmenes por status y por limits)."
        )
    )
    parser.add_argument(
        "--project-id",
        "--project",
        dest="project_id",
        default="default-gke-project",
        help="ID del proyecto GCP (default: default-gke-project)",
    )
    parser.add_argument(
        "--multi-project",
        dest="multi_project",
        default=None,
        help="IDs de multiples proyectos GCP separados por comas (ej: proj1,proj2)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directorio donde guardar el reporte (default: outcome)",
    )
    args = parser.parse_args()

    # Directorio resuelto: honra DEVSECOPS_OUTPUT_DIR / config global.output_dir
    output_dir = get_output_dir(args.output_dir or "outcome")
    logger = setup_logger(str(output_dir))
    logger.info("Iniciando generación de reporte de deployments en GKE")
    
    console = Console() if RICH_AVAILABLE else None

    print("=" * 80)
    print("🔍 GENERANDO REPORTE DE DEPLOYMENTS EN GKE")
    print("=" * 80)
    print()
    
    project_id = args.project_id or "default-gke-project"
    if args.multi_project:
        project_ids = [p.strip() for p in args.multi_project.split(",") if p.strip()]
    else:
        # El launcher ejecuta los scripts con stdin=DEVNULL: solo preguntar
        # cuando hay una terminal interactiva real.
        if sys.stdin is not None and sys.stdin.isatty():
            print("📋 Ingrese el ID del proyecto GCP")
            print(f"   (Presione Enter para usar el valor por defecto: '{project_id}')")
            try:
                user_input = input("Proyecto GCP: ").strip()
            except EOFError:
                user_input = ""
            if user_input:
                project_id = user_input
        project_ids = [project_id]

    print(f"✓ Proyecto(s) GCP: {', '.join(project_ids)}")
    logger.info(f"Proyecto(s) GCP: {', '.join(project_ids)}")
    print()

    try:
        generated_at = datetime.now(timezone.utc).isoformat()

        # Resolver todos los (proyecto, cluster) a consultar
        targets = []
        for pid in project_ids:
            clusters = list_gke_clusters(pid, logger)
            if not clusters:
                print(f"⚠️  Sin clusters GKE accesibles en {pid}")
                logger.warning(f"Sin clusters GKE accesibles en {pid}")
                continue
            for cname, cloc in clusters:
                targets.append((pid, cname, cloc))

        if not targets:
            print("❌ No se encontraron clusters GKE en los proyectos seleccionados.")
            return

        report_data = []
        cluster_errors = []

        def _collect(fut, pid, cname, cloc):
            try:
                report_data.extend(fut.result())
            except Exception as e:
                err = " ".join(str(e).split())[:300]
                cluster_errors.append({
                    "project": pid, "cluster": cname,
                    "location": cloc, "error": err,
                })
                logger.error(f"Cluster {cname} ({pid}, {cloc}) no accesible: {err}")

        msg = (f"🔍 Consultando deployments en {len(targets)} cluster(s) "
               f"de {len(project_ids)} proyecto(s)...")
        if RICH_AVAILABLE and console and is_live_terminal():
            with console.status(f"[bold cyan]{msg}[/]", spinner="dots"):
                logger.info(msg)
                with ThreadPoolExecutor(max_workers=min(6, len(targets))) as executor:
                    futures = {
                        executor.submit(get_deployments_report, pid, cname, cloc, logger): (pid, cname, cloc)
                        for pid, cname, cloc in targets
                    }
                    for fut in as_completed(futures):
                        _collect(fut, *futures[fut])
        else:
            print(f"[INFO] {msg}")
            logger.info(msg)
            with ThreadPoolExecutor(max_workers=min(6, len(targets))) as executor:
                futures = {
                    executor.submit(get_deployments_report, pid, cname, cloc, logger): (pid, cname, cloc)
                    for pid, cname, cloc in targets
                }
                for fut in as_completed(futures):
                    _collect(fut, *futures[fut])

        print(f"✓ Se encontraron {len(report_data)} deployments")
        logger.info(f"Se encontraron {len(report_data)} deployments")

        errors_txt = format_cluster_errors(cluster_errors)
        if cluster_errors:
            warn = (f"⚠️ {len(cluster_errors)} de {len(targets)} cluster(es) "
                    f"no accesibles — el reporte los detalla aparte")
            print(warn)
            logger.warning(warn)

        for row in report_data:
            row["generated_at"] = generated_at

        detailed = format_detailed_table(report_data)
        summary_status = format_status_summary(report_data)
        summary_limits = format_limits_status_summary(report_data)

        if RICH_AVAILABLE and console:
            console.print()
            console.print(build_detailed_rich_table(report_data))
            
            console.print()
            status_table = tabulate_to_rich_table(summary_status, "📈 Resumen por Status")
            if status_table:
                console.print(status_table)
            
            console.print()
            limits_table = tabulate_to_rich_table(summary_limits, "💾 Resumen por Status + Limits")
            if limits_table:
                console.print(limits_table)

            if errors_txt:
                console.print()
                errors_table = tabulate_to_rich_table(errors_txt, "🔌 Clusters no accesibles")
                if errors_table:
                    console.print(errors_table)
        else:
            print(detailed)
            print()
            print(summary_status)
            print(summary_limits)
            if errors_txt:
                print()
                print("[CLUSTERS NO ACCESIBLES]")
                print(errors_txt)

        ts_for_filename = datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_path = str(output_dir / f"gke_deployments_report_{ts_for_filename}.txt")
        csv_path = str(output_dir / f"gke_deployments_report_{ts_for_filename}.csv")
        json_path = str(output_dir / f"gke_deployments_report_{ts_for_filename}.json")
        html_path = str(output_dir / f"gke_deployments_report_{ts_for_filename}.html")

        if RICH_AVAILABLE and console and is_live_terminal():
            with console.status("[bold cyan]💾 Guardando archivos...", spinner="dots"):
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write("=" * 80 + "\n")
                    f.write("REPORTE DE DEPLOYMENTS EN GKE\n")
                    f.write(f"Generado (UTC): {generated_at}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(detailed)
                    f.write("\n\n")
                    f.write(f"[RESÚMENES GENERADOS (UTC): {generated_at}]\n\n")
                    f.write(summary_status)
                    f.write("\n\n")
                    f.write(summary_limits)
                    if errors_txt:
                        f.write("\n\n[CLUSTERS NO ACCESIBLES]\n\n")
                        f.write(errors_txt)

                write_csv(report_data, csv_path)
                write_json(report_data, json_path)
                write_html(report_data, cluster_errors, html_path, generated_at, project_ids)
            console.print("[green]✓[/green] Archivos guardados exitosamente")
        else:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("REPORTE DE DEPLOYMENTS EN GKE\n")
                f.write(f"Generado (UTC): {generated_at}\n")
                f.write("=" * 80 + "\n\n")
                f.write(detailed)
                f.write("\n\n")
                f.write(f"[RESÚMENES GENERADOS (UTC): {generated_at}]\n\n")
                f.write(summary_status)
                f.write("\n\n")
                f.write(summary_limits)
                if errors_txt:
                    f.write("\n\n[CLUSTERS NO ACCESIBLES]\n\n")
                    f.write(errors_txt)

            write_csv(report_data, csv_path)
            write_json(report_data, json_path)
            write_html(report_data, cluster_errors, html_path, generated_at, project_ids)

        if RICH_AVAILABLE and console:
            files_table = Table(title="📁 Archivos Generados", box=None)
            files_table.add_column("Tipo", style="cyan")
            files_table.add_column("Ruta", style="green")
            files_table.add_row("TXT", txt_path)
            files_table.add_row("CSV", csv_path)
            files_table.add_row("JSON", json_path)
            files_table.add_row("HTML", html_path)
            console.print()
            console.print(Panel(files_table, border_style="blue"))
        else:
            print(f"📁 Reporte TXT guardado en: {txt_path}")
            print(f"📁 Reporte CSV guardado en: {csv_path}")
            print(f"📁 Reporte JSON guardado en: {json_path}")
            print(f"📁 Reporte HTML guardado en: {html_path}")

        logger.info(f"Archivos generados: TXT, CSV, JSON, HTML")

        end_time = time.time()
        log_file = logger.handlers[0].baseFilename if logger.handlers else "N/A"
        print_execution_summary(start_time, end_time, log_file, console)
        logger.info(f"Tiempo de ejecución: {end_time - start_time:.2f}s")

    except Exception as e:
        logger.error(f"Error generando el reporte: {e}")
        print(f"❌ Error generando el reporte: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    
    from pathlib import Path
    import json
    import csv
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = output_path / f"gke_deployments_report_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"gke_deployments_report_{ts}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        
        print(f"✅ Resultados exportados a: {filepath}")
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("gke_deployments_report", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
