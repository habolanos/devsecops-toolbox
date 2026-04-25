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
from datetime import datetime, timezone
from collections import Counter, defaultdict

from kubernetes import client, config
from kubernetes.client import ApiException
from tabulate import tabulate

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
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


# ---------------------------------------------------------------------------
# Utilidades de parsing de recursos (CPU/Memoria) de Kubernetes
# ---------------------------------------------------------------------------

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

def load_kube_config():
    try:
        config.load_kube_config()
    except Exception as e:
        raise RuntimeError(
            f"No se pudo cargar la configuración de Kubernetes: {e}\n"
            "Asegúrate de tener un contexto válido en ~/.kube/config y de "
            "que puedes ejecutar 'kubectl get pods' sin problemas."
        )


def get_deployments_report():
    """
    Devuelve una lista de dicts con la información de cada Deployment:

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
    load_kube_config()

    contexts, active_context = config.list_kube_config_contexts()
    if not active_context:
        raise RuntimeError("No se encontró un contexto activo en kubeconfig.")
    cluster_name = active_context.get("name", "desconocido")

    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()

    ns_list = core_v1.list_namespace()
    namespaces = [ns.metadata.name for ns in ns_list.items]

    report_rows = []

    for ns in namespaces:
        try:
            deployments = apps_v1.list_namespaced_deployment(namespace=ns)
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
                    namespace=ns, label_selector=label_selector
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

def format_detailed_table(report_data):
    headers = [
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


def format_status_summary(report_data):
    counter = Counter(r["status"] for r in report_data)
    rows = [[status, count] for status, count in sorted(counter.items())]
    return tabulate(rows, headers=["Status", "Deployments"], tablefmt="github")


def format_limits_status_summary(report_data):
    """
    Resumen por STATUS + LIMIT_CPU + LIMIT_MEM:

    STATUS   LIMIT_CPU   LIMIT_MEM   DEPLOYMENTS   PODS_READY   RESTARTS
    """
    groups = defaultdict(lambda: {"deployments": 0, "pods_ready": 0, "restarts": 0})

    for r in report_data:
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

        key = (status, lim_cpu, lim_mem)
        groups[key]["deployments"] += 1
        groups[key]["pods_ready"] += ready_int
        groups[key]["restarts"] += restarts

    rows = []
    for (status, lim_cpu, lim_mem), agg in sorted(
        groups.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])
    ):
        rows.append(
            [
                status,
                lim_cpu,
                lim_mem,
                agg["deployments"],
                agg["pods_ready"],
                agg["restarts"],
            ]
        )

    title = "RESUMEN POR STATUS + LIMITS (CPU/MEMORY)"
    if not rows:
        return title + "\n(No hay datos)"

    table = tabulate(
        rows,
        headers=[
            "STATUS",
            "LIMIT_CPU",
            "LIMIT_MEM",
            "DEPLOYMENTS",
            "PODS_READY",
            "RESTARTS",
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
# main()
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Genera reporte detallado de Deployments en GKE "
            "(TXT + CSV + JSON + resúmenes por status y por limits)."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directorio donde guardar el reporte (default: outcome)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("🔍 GENERANDO REPORTE DE DEPLOYMENTS EN GKE")
    print("=" * 80)
    print()

    try:
        generated_at = datetime.now(timezone.utc).isoformat()

        print("[INFO] Consultando deployments en el cluster...")
        report_data = get_deployments_report()
        print(f"[INFO] Se encontraron {len(report_data)} deployments")
        print()

        for row in report_data:
            row["generated_at"] = generated_at

        detailed = format_detailed_table(report_data)
        summary_status = format_status_summary(report_data)
        summary_limits = format_limits_status_summary(report_data)

        print(detailed)
        print()
        print(summary_status)
        print(summary_limits)

        output_dir = get_output_dir(args.output_dir or "outcome")
        ts_for_filename = datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_path = os.path.join(
            args.output_dir, f"gke_deployments_report_{ts_for_filename}.txt"
        )
        csv_path = os.path.join(
            args.output_dir, f"gke_deployments_report_{ts_for_filename}.csv"
        )
        json_path = os.path.join(
            args.output_dir, f"gke_deployments_report_{ts_for_filename}.json"
        )

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

        write_csv(report_data, csv_path)
        write_json(report_data, json_path)

        print(f"📁 Reporte TXT guardado en: {txt_path}")
        print(f"📁 Reporte CSV guardado en: {csv_path}")
        print(f"📁 Reporte JSON guardado en: {json_path}")

    except Exception as e:
        print(f"❌ Error generando el reporte: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())