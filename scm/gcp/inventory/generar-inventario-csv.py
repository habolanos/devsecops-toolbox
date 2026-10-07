#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Inventario GCP (GKE · Cloud SQL · Cloud Run · Pub/Sub) - Generador CSV

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

# --- Config global: DEVSECOPS_* env > scm/config.json > scm/outcome ---
try:
    from utils import (get_output_dir, resolve_outcome_dir, global_flag,
                       log_command)
except ImportError:
    import os as _os
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt

    _SCM_ROOT = _Path(__file__).resolve().parents[2]  # inventory -> gcp -> scm

    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        p = _Path(env) if env else _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _load_global_config():
        try:
            cfg_file = _SCM_ROOT / "config.json"
            if cfg_file.exists():
                section = _json.loads(
                    cfg_file.read_text(encoding="utf-8")).get("global")
                return section if isinstance(section, dict) else {}
        except Exception:
            pass
        return {}

    def resolve_outcome_dir(default="outcome"):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
        else:
            p = _Path(_load_global_config().get("output_dir") or default)
            if not p.is_absolute():
                p = _SCM_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p.resolve()

    def global_flag(name):
        env_val = _os.getenv(f"DEVSECOPS_{name.upper()}")
        if env_val is not None:
            return env_val.strip().lower() in {"1", "true", "yes", "on"}
        return bool(_load_global_config().get(name))

    def log_command(cmd, status="EXEC", platform_name="GCP"):
        if not global_flag("log_commands"):
            return
        log_dir = resolve_outcome_dir()
        ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        today = _dt.now().strftime("%Y%m%d")
        cmd_str = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
        try:
            with open(log_dir / f"commands_{today}.log", "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{platform_name}] [{status}] {cmd_str}\n")
        except OSError:
            pass
# -------------------------------------------------------------------

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
OUTCOME_DIR = resolve_outcome_dir()
TOTAL_STEPS = 10

# Flags de configuración global (se setean en main() desde args/env/config)
_DEBUG = False
_VERBOSE = False
_CONSOLE = None      # Console Rich activa (para prints thread-safe)
_PRINT_LOCK = None   # Lock compartido para prints durante Progress

STEP_NAMES = {
    1: "clusters",
    2: "deployments",
    3: "services",
    4: "cloudsql",
    5: "clouddatabases",
    6: "ingress",
    7: "cloudrun",
    8: "pubsub",
    9: "gateways",
    10: "httproutes",
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
    9: "🚪",
    10: "🛤️",
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
    9: "blue",
    10: "blue",
}

# ═══════════════════════════════════════════════════════════════════════════════
# LECTURA DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════


try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

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

def _emit(msg: str) -> None:
    """Print thread-safe de mensajes debug/verbose (usa la Console Rich si existe)."""
    if _CONSOLE is not None and _PRINT_LOCK is not None:
        with _PRINT_LOCK:
            _CONSOLE.print(msg)
    else:
        print(msg)


def run_cmd(cmd: list, env: dict = None, capture: bool = True) -> str:
    """Ejecuta un comando y retorna su stdout."""
    log_command(cmd)
    if _DEBUG:
        _emit(f"[dim]→ {' '.join(cmd)}[/dim]" if _CONSOLE else f"→ {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            env=env, timeout=300
        )
        if result.returncode != 0:
            log_command(cmd, "ERROR")
            if _VERBOSE:
                stderr = (result.stderr or "").strip()
                hint = stderr.splitlines()[0][:200] if stderr else "sin stderr"
                _emit(f"  [yellow]⚠ rc={result.returncode}[/yellow] [dim]{' '.join(cmd)}[/dim]"
                      f"\n    [dim]{hint}[/dim]" if _CONSOLE else
                      f"  ⚠ rc={result.returncode} {' '.join(cmd)}\n    {hint}")
        return result.stdout if capture else ""
    except subprocess.TimeoutExpired:
        log_command(cmd, "TIMEOUT")
        if _VERBOSE:
            _emit(f"  [yellow]⏱ timeout (300s)[/yellow] [dim]{' '.join(cmd)}[/dim]"
                  if _CONSOLE else f"  ⏱ timeout (300s) {' '.join(cmd)}")
        return ""
    except Exception as e:
        log_command(cmd, "ERROR")
        if _VERBOSE:
            _emit(f"  [red]✘ {e}[/red] [dim]{' '.join(cmd)}[/dim]"
                  if _CONSOLE else f"  ✘ {e} {' '.join(cmd)}")
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


def _kubectl_env_for_cluster(project_id: str, cluster_name: str, location: str) -> tuple:
    """Crea kubeconfig aislado por cluster y obtiene credenciales.

    Retorna (env, kubeconfig_path). El kubeconfig aislado evita el
    read-modify-write no atómico de ~/.kube/config cuando los proyectos
    corren en paralelo.
    """
    _fd, kubeconfig = tempfile.mkstemp(prefix=f"kubeconfig-inv-{project_id}-")
    os.close(_fd)
    os.unlink(kubeconfig)
    env = os.environ.copy()
    env["KUBECONFIG"] = kubeconfig
    run_cmd([
        "gcloud", "container", "clusters", "get-credentials", cluster_name,
        "--location", location, "--project", project_id, "--quiet"
    ], env=env, capture=False)
    return env, kubeconfig


def _rm_quiet(path) -> None:
    """Elimina un archivo ignorando errores (kubeconfig temporal)."""
    try:
        os.unlink(path)
    except OSError:
        pass


def _kubectl_json(project_id: str, cluster_name: str, location: str,
                  resource: str) -> list:
    """Ejecuta `kubectl get <resource> -A -o json` con kubeconfig aislado.

    Retorna la lista de items ([] si el cluster no tiene el CRD, kubectl
    falla, o el JSON no parsea).
    """
    env, kubeconfig = _kubectl_env_for_cluster(project_id, cluster_name, location)
    try:
        output = run_cmd(
            ["kubectl", "get", resource, "--all-namespaces", "-o", "json"],
            env=env,
        )
    finally:
        _rm_quiet(kubeconfig)
    data = output.strip()
    if not data:
        return []
    try:
        return json.loads(data).get("items", [])
    except (json.JSONDecodeError, AttributeError):
        return []


def _iso_short(ts: str) -> str:
    """RFC3339 → 'YYYY-MM-DD HH:MM' (legible en Excel). Vacío si no hay valor."""
    return ts.replace("T", " ")[:16] if ts else ""


def _obj_dates(item: dict) -> tuple:
    """(created, updated) de un objeto K8s / recurso GCP con metadata.

    updated = max(metadata.managedFields[].time) — la última escritura
    registrada del objeto (spec o status). Fallback: el mayor
    status.conditions[].lastTransitionTime (Cloud Run y recursos sin
    managedFields).
    """
    meta = item.get("metadata", {})
    created = _iso_short(meta.get("creationTimestamp", ""))
    times = [f.get("time") for f in meta.get("managedFields", [])
             if isinstance(f, dict) and f.get("time")]
    if not times:
        times = [c.get("lastTransitionTime")
                 for c in item.get("status", {}).get("conditions", [])
                 if isinstance(c, dict) and c.get("lastTransitionTime")]
    return created, _iso_short(max(times)) if times else ""


def step_clusters(project_id: str, out_dir: Path, delim: str) -> None:
    """1. Clusters GKE → clusters.csv"""
    output = run_cmd([
        "gcloud", "container", "clusters", "list",
        "--project", project_id, "--format=json", "--quiet"
    ])
    with open(out_dir / "clusters.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delim, quoting=csv.QUOTE_ALL)
        w.writerow(["NAME", "LOCATION", "VERSION", "CURRENT_VERSION", "STATUS",
                    "MACHINE_TYPE", "CREATED", "UPDATED"])
        data = output.strip()
        if data:
            try:
                for c in json.loads(data):
                    pools = c.get("nodePools") or []
                    mt = "|".join(p.get("config", {}).get("machineType", "") for p in pools)
                    w.writerow([
                        c.get("name", ""), c.get("location", ""),
                        c.get("currentMasterVersion", ""), c.get("currentMasterVersion", ""),
                        c.get("status", ""), mt,
                        _iso_short(c.get("createTime", "")),
                        _iso_short(c.get("updateTime", ""))
                    ])
            except (json.JSONDecodeError, Exception):
                pass


def _deploy_containers(spec: dict) -> tuple:
    """Extrae (pares name=image, solo images) de un pod template.

    Incluye initContainers con prefijo 'init:' en los pares.
    """
    tmpl_spec = spec.get("template", {}).get("spec", {})
    pairs = []
    images = []
    for c in tmpl_spec.get("containers", []):
        pairs.append(f"{c.get('name', '?')}={c.get('image', '')}")
        images.append(c.get("image", ""))
    for c in tmpl_spec.get("initContainers", []):
        pairs.append(f"init:{c.get('name', '?')}={c.get('image', '')}")
        images.append(c.get("image", ""))
    return pairs, images


def step_deployments(project_id: str, out_dir: Path, delim: str, clusters: list, exclude_ns: list) -> None:
    """2. Deployments → deployments.csv (con READY y CONTAINERS name=image)."""
    with open(out_dir / "deployments.csv", "w", newline="", encoding="utf-8") as f:
        f.write(f"NAMESPACE{delim}CLUSTER{delim}DEPLOYMENT{delim}READY{delim}CONTAINERS{delim}IMAGES{delim}CREATED{delim}UPDATED\n")

    for cluster_name, location in clusters:
        items = _kubectl_json(project_id, cluster_name, location, "deployments")
        with open(out_dir / "deployments.csv", "a", newline="", encoding="utf-8") as f:
            for d in items:
                meta = d.get("metadata", {})
                ns = meta.get("namespace", "")
                if ns in exclude_ns:
                    continue
                spec = d.get("spec", {})
                status = d.get("status", {})
                replicas = spec.get("replicas", 1) or 0
                ready = status.get("readyReplicas", 0) or 0
                pairs, images = _deploy_containers(spec)
                created, updated = _obj_dates(d)
                f.write(
                    f'"{ns}"{delim}"{cluster_name}"{delim}"{meta.get("name", "")}"{delim}'
                    f'"{ready}/{replicas}"{delim}"{";".join(pairs)}"{delim}"{";".join(images)}"{delim}'
                    f'"{created}"{delim}"{updated}"\n'
                )


def step_services(project_id: str, out_dir: Path, delim: str, clusters: list, exclude_ns: list) -> None:
    """3. Services → services.csv"""
    with open(out_dir / "services.csv", "w", newline="", encoding="utf-8") as f:
        f.write(f"NAMESPACE{delim}CLUSTER{delim}NAME{delim}TYPE{delim}CLUSTER-IP{delim}EXTERNAL-IP{delim}PORTS{delim}CREATED{delim}UPDATED\n")

    for cluster_name, location in clusters:
        items = _kubectl_json(project_id, cluster_name, location, "services")
        with open(out_dir / "services.csv", "a", newline="", encoding="utf-8") as f:
            for s in items:
                meta = s.get("metadata", {})
                ns = meta.get("namespace", "")
                if ns in exclude_ns:
                    continue
                spec = s.get("spec", {})
                eip = ";".join(
                    i.get("ip") or i.get("hostname", "")
                    for i in s.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                )
                ports = ";".join(str(p.get("port", "")) for p in spec.get("ports", []))
                created, updated = _obj_dates(s)
                f.write(
                    f'"{ns}"{delim}"{cluster_name}"{delim}"{meta.get("name", "")}"{delim}'
                    f'"{spec.get("type", "")}"{delim}"{spec.get("clusterIP", "")}"{delim}'
                    f'"{eip}"{delim}"{ports}"{delim}"{created}"{delim}"{updated}"\n'
                )


def step_cloudsql(project_id: str, out_dir: Path, delim: str) -> int:
    """4. Cloud SQL → cloudsql.csv. Retorna cantidad de instancias."""
    output = run_cmd([
        "gcloud", "sql", "instances", "list",
        "--project", project_id, "--format=json", "--quiet"
    ])

    header = (f"NAME{delim}DATABASE_VERSION{delim}REGION{delim}TIER{delim}STATE"
              f"{delim}PUBLIC_IP{delim}PRIVATE_IP{delim}AUTO_RESIZE{delim}BACKUP_ENABLED"
              f"{delim}CREATED{delim}UPDATED")

    instances = []
    data = output.strip()
    if data:
        try:
            instances = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            instances = []

    with open(out_dir / "cloudsql.csv", "w", newline="", encoding="utf-8") as f:
        f.write(header + "\n")
        if not instances:
            f.write(f"Sin instancias{delim}-{delim}-{delim}-{delim}-{delim}"
                    f"{delim}-{delim}-{delim}-{delim}-{delim}-{delim}-\n")
            return 0
        for inst in instances:
            settings = inst.get("settings", {})
            addrs = inst.get("ipAddresses", [])
            private_ip = next(
                (a.get("ipAddress", "") for a in addrs if a.get("type") == "PRIVATE"),
                addrs[0].get("ipAddress", "") if addrs else ""
            )
            ipv4 = (settings.get("ipConfiguration") or {}).get("ipv4Enabled", "")
            backup = (settings.get("backupConfiguration") or {}).get("enabled", "")
            autores = settings.get("storageAutoResize", "")
            f.write(
                f'"{inst.get("name", "")}"{delim}"{inst.get("databaseVersion", "")}"{delim}'
                f'"{inst.get("region", "")}"{delim}"{settings.get("tier", "")}"{delim}'
                f'"{inst.get("state", "")}"{delim}"{ipv4}"{delim}"{private_ip}"{delim}'
                f'"{autores}"{delim}"{backup}"{delim}'
                f'"{_iso_short(inst.get("createTime", ""))}"{delim}'
                f'"{_iso_short(inst.get("updateTime", ""))}"\n'
            )
    return len(instances)


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
        f.write(f"NAMESPACE{delim}CLUSTER{delim}NAME{delim}HOSTS{delim}ADDRESS{delim}PORTS{delim}CREATED{delim}UPDATED\n")

    for cluster_name, location in clusters:
        items = _kubectl_json(project_id, cluster_name, location, "ingress")
        with open(out_dir / "ingress.csv", "a", newline="", encoding="utf-8") as f:
            for ing in items:
                meta = ing.get("metadata", {})
                ns = meta.get("namespace", "")
                if ns in exclude_ns:
                    continue
                spec = ing.get("spec", {})
                hosts = []
                for rule in spec.get("rules", []):
                    host = rule.get("host", "")
                    if host and host not in hosts:
                        hosts.append(host)
                addr = ";".join(
                    i.get("ip") or i.get("hostname", "")
                    for i in ing.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                )
                tls = ";".join(t.get("secretName", "") for t in spec.get("tls", []))
                created, updated = _obj_dates(ing)
                f.write(
                    f'"{ns}"{delim}"{cluster_name}"{delim}"{meta.get("name", "")}"{delim}'
                    f'"{";".join(hosts)}"{delim}"{addr}"{delim}"{tls}"{delim}'
                    f'"{created}"{delim}"{updated}"\n'
                )


def step_cloudrun(project_id: str, out_dir: Path, delim: str) -> None:
    """7. Cloud Run → cloudrun.csv"""
    output = run_cmd([
        "gcloud", "run", "services", "list",
        "--project", project_id, "--platform=managed", "--format=json", "--quiet"
    ])
    with open(out_dir / "cloudrun.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delim, quoting=csv.QUOTE_ALL)
        w.writerow(["NAME", "REGION", "URL", "LAST_DEPLOYED", "IMAGE",
                    "CREATED", "UPDATED"])
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
                    created, updated = _obj_dates(s)
                    ctnrs = s.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                    image = ctnrs[0].get("image", "") if ctnrs else ""
                    w.writerow([name, region, url, created, image,
                                created, updated])
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


def _gateway_status(gw: dict) -> str:
    """Estado del Gateway según condiciones (Programmed > Accepted > Unknown)."""
    conditions = gw.get("status", {}).get("conditions", [])
    for cond in conditions:
        if cond.get("type") == "Programmed" and cond.get("status") == "True":
            return "Programmed"
    for cond in conditions:
        if cond.get("type") == "Accepted" and cond.get("status") == "True":
            return "Accepted"
    if conditions:
        last = conditions[-1]
        return last.get("reason") or last.get("type") or "Unknown"
    return "Unknown"


def step_gateways(project_id: str, out_dir: Path, delim: str, clusters: list, exclude_ns: list) -> None:
    """9. Gateways (Gateway API) → gateways.csv

    Cluster sin los CRDs de Gateway API → kubectl falla → CSV solo header.
    """
    with open(out_dir / "gateways.csv", "w", newline="", encoding="utf-8") as f:
        f.write(f"NAMESPACE{delim}CLUSTER{delim}NAME{delim}CLASS{delim}LISTENERS{delim}ADDRESSES{delim}STATUS{delim}CREATED{delim}UPDATED\n")

    for cluster_name, location in clusters:
        items = _kubectl_json(project_id, cluster_name, location, "gateways")
        with open(out_dir / "gateways.csv", "a", newline="", encoding="utf-8") as f:
            for gw in items:
                meta = gw.get("metadata", {})
                ns = meta.get("namespace", "")
                if ns in exclude_ns:
                    continue
                spec = gw.get("spec", {})
                listeners = ";".join(
                    f"{l.get('port', '')}/{l.get('protocol', '')}"
                    for l in spec.get("listeners", [])
                )
                addresses = ";".join(
                    a.get("value", "") for a in gw.get("status", {}).get("addresses", [])
                )
                created, updated = _obj_dates(gw)
                f.write(
                    f'"{ns}"{delim}"{cluster_name}"{delim}"{meta.get("name", "")}"{delim}'
                    f'"{spec.get("gatewayClassName", "")}"{delim}"{listeners}"{delim}'
                    f'"{addresses}"{delim}"{_gateway_status(gw)}"{delim}'
                    f'"{created}"{delim}"{updated}"\n'
                )


def step_httproutes(project_id: str, out_dir: Path, delim: str, clusters: list, exclude_ns: list) -> None:
    """10. HTTPRoutes (Gateway API) → httproutes.csv"""
    with open(out_dir / "httproutes.csv", "w", newline="", encoding="utf-8") as f:
        f.write(f"NAMESPACE{delim}CLUSTER{delim}NAME{delim}HOSTNAMES{delim}GATEWAYS{delim}RULES{delim}PATHS{delim}BACKENDS{delim}CREATED{delim}UPDATED\n")

    for cluster_name, location in clusters:
        items = _kubectl_json(project_id, cluster_name, location, "httproutes")
        with open(out_dir / "httproutes.csv", "a", newline="", encoding="utf-8") as f:
            for r in items:
                meta = r.get("metadata", {})
                ns = meta.get("namespace", "")
                if ns in exclude_ns:
                    continue
                spec = r.get("spec", {})
                parents = ";".join(
                    f"{p['namespace']}/{p['name']}" if p.get("namespace") else p.get("name", "")
                    for p in spec.get("parentRefs", [])
                )
                rules = spec.get("rules", [])
                paths = []
                backends = []
                for rule in rules:
                    for match in rule.get("matches", []):
                        path = match.get("path", {}).get("value", "/")
                        if path not in paths:
                            paths.append(path)
                    for b in rule.get("backendRefs", []):
                        bname = b.get("name", "")
                        if bname and bname not in backends:
                            backends.append(bname)
                created, updated = _obj_dates(r)
                f.write(
                    f'"{ns}"{delim}"{cluster_name}"{delim}"{meta.get("name", "")}"{delim}'
                    f'"{";".join(spec.get("hostnames", []))}"{delim}"{parents}"{delim}'
                    f'"{len(rules)}"{delim}"{";".join(paths)}"{delim}"{";".join(backends)}"{delim}'
                    f'"{created}"{delim}"{updated}"\n'
                )


# ═══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE PROYECTO
# ═══════════════════════════════════════════════════════════════════════════════

def process_project(project_id: str, delim: str, exclude_ns: list,
                    progress: Progress, task_id: int, console: Console,
                    print_lock: Lock) -> dict:
    """Procesa un proyecto completo (10 pasos). Retorna resumen."""
    project_start = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTCOME_DIR / f"inventario-{project_id}-{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {"project": project_id, "steps": {}, "time": 0, "out_dir": str(out_dir)}

    # Obtener clusters (necesario para pasos 2,3,6,9,10)
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
        (9, lambda: step_gateways(project_id, out_dir, delim, clusters, exclude_ns)),
        (10, lambda: step_httproutes(project_id, out_dir, delim, clusters, exclude_ns)),
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
                      delimiter: str, max_parallel: int, sequential: bool,
                      out_dir: Path):
    """Muestra header con Rich Panel."""
    content = Text()
    content.append("📋 INVENTARIO GCP — GKE · CLOUD SQL · CLOUD RUN · PUB/SUB\n\n", style="bold white")
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
    content.append(f"{out_dir}\n", style="green")

    panel = Panel(content, border_style="cyan", box=HEAVY, padding=(1, 2), expand=False)
    console.print(panel)
    console.print()


def print_summary_rich(console: Console, results: list, total_time: float,
                       max_parallel: int, out_dir: Path):
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
    content.append(f"{out_dir}\n", style="cyan")

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

def print_header_fallback(projects, exclude_ns, delimiter, max_parallel, sequential, out_dir):
    print("=" * 60)
    print("  INVENTARIO GCP (GKE · CLOUD SQL · CLOUD RUN · PUB/SUB) - CSV")
    print(f"  Separador    : '{delimiter}'")
    print(f"  Proyectos    : {len(projects)}")
    for p in projects:
        print(f"    • {p}")
    print(f"  NS excluidos : {', '.join(exclude_ns) if exclude_ns else 'ninguno'}")
    print(f"  Hilos        : {'1 (secuencial)' if sequential else max_parallel}")
    print(f"  Output       : {out_dir}")
    print("=" * 60)


def print_summary_fallback(results, total_time, max_parallel, out_dir):
    print()
    print("=" * 60)
    print("  ¡Proceso COMPLETO finalizado exitosamente!")
    print(f"  Tiempo total : {format_time(total_time)}")
    print(f"  Hilos usados : {max_parallel}")
    print(f"  Proyectos    : {len(results)}")
    print(f"  Carpeta       : {out_dir}")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # UTF-8 stdio: consolas cp1252 (Windows) no imprimen emojis/Unicode.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Inventario GCP (GKE · Cloud SQL · Cloud Run · Pub/Sub) - Generador CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("projects", nargs="*", help="IDs de proyectos GCP")
    parser.add_argument("--delimiter", default=";", help="Separador CSV (default: ;)")
    parser.add_argument("--threads", type=int, default=4, help="Hilos paralelos (default: 4)")
    parser.add_argument("--sequential", action="store_true", help="Deshabilitar paralelismo")
    parser.add_argument("--debug", action="store_true",
                        help="Modo debug (también global.debug en config.json)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Salida detallada (también global.verbose en config.json)")
    args = parser.parse_args()

    # Flags de config global (DEVSECOPS_* env > config.json global) + CLI
    global _DEBUG, _VERBOSE, _CONSOLE, _PRINT_LOCK
    _DEBUG = args.debug or global_flag("debug")
    _VERBOSE = args.verbose or global_flag("verbose") or _DEBUG

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
        print_header_rich(console, projects, exclude_ns, args.delimiter,
                          args.threads, args.sequential, OUTCOME_DIR)

        start_total = time.time()
        results = []
        print_lock = Lock()
        _CONSOLE = console
        _PRINT_LOCK = print_lock

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
        print_summary_rich(console, results, total_time, args.threads, OUTCOME_DIR)

    else:
        # Modo fallback sin Rich
        print_header_fallback(projects, exclude_ns, args.delimiter, args.threads,
                              args.sequential, OUTCOME_DIR)
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
                lambda: step_gateways(p, out_dir, args.delimiter, clusters, exclude_ns),
                lambda: step_httproutes(p, out_dir, args.delimiter, clusters, exclude_ns),
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
        print_summary_fallback(results, total_time, args.threads, OUTCOME_DIR)


if __name__ == "__main__":
    main()


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
            filepath = output_path / f"generar-inventario-csv_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"generar-inventario-csv_{ts}.csv"
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
    manager = ExportManager("generar-inventario-csv", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
