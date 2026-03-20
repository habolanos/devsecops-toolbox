#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Dependency Checker

Analiza los ConfigMaps referenciados por un Deployment de GKE para identificar
cadenas de conexión a bases de datos y validar la conectividad TCP hacia cada host:puerto detectado.
"""

import argparse
import subprocess
import json
import os
import re
import socket
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

DEFAULT_PROJECT_ID = "cpl-xxxx-yyyy-zzzz-99999999"
DEFAULT_DEPLOYMENT = "ds-ppm-pricing-discount"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_PROBE_IMAGE = "jrecord/nettools:latest"
__version__ = "1.0.0"

URL_PATTERN = re.compile(r"(jdbc:)?((?P<engine>postgres(?:ql)?|mysql|mssql|sqlserver|oracle|mongodb|redis|cockroachdb)://[^\s'\"`]+)", re.IGNORECASE)
HOST_PORT_PATTERN = re.compile(r"([a-zA-Z0-9.-]+):(\d{2,5})")


def get_args():
    parser = argparse.ArgumentParser(
        description="SRE Tool: Deploy Dependency Checker (kubectl)",
        add_help=False
    )
    parser.add_argument(
        "--project",
        type=str,
        default=DEFAULT_PROJECT_ID,
        help=f"ID del proyecto de GCP (Default: {DEFAULT_PROJECT_ID})"
    )
    parser.add_argument(
        "--deployment",
        type=str,
        default=DEFAULT_DEPLOYMENT,
        help=f"Nombre del deployment a analizar (Default: {DEFAULT_DEPLOYMENT})"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="",
        help="Namespace del deployment (si se omite se buscará en todos)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Timeout (segundos) para validar conectividad TCP (Default: 5)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["csv", "json"],
        help="Exporta resultados a archivo (csv o json) en carpeta outcome/"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default=DEFAULT_TIMEZONE,
        help=f"Zona horaria para las marcas de tiempo (Default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--probe-mode",
        type=str,
        choices=["local", "pod"],
        default="pod",
        help="Modo de validación: 'local' usa sockets desde el host, 'pod' crea un pod temporal (Default: pod)"
    )
    parser.add_argument(
        "--probe-image",
        type=str,
        default=DEFAULT_PROBE_IMAGE,
        help=f"Imagen contenedora para el pod temporal (Default: {DEFAULT_PROBE_IMAGE})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug para ver los comandos ejecutados"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra la documentación completa del script"
    )
    return parser.parse_args()


def show_help(console: Optional[Console]):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    section = "# Pod Connectivity Checker"
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        if RICH_AVAILABLE and console:
            console.print(Markdown(content))
        else:
            print(content)
    else:
        msg = "README.md no encontrado en connectivty/"
        if RICH_AVAILABLE and console:
            console.print(f"[yellow]{msg}[/]")
        else:
            print(msg)


def run_command(cmd: List[str], debug: bool = False, timeout: Optional[int] = None) -> Tuple[int, str, str]:
    if debug:
        print(f"[DEBUG] Ejecutando: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if debug and stderr:
            print(f"[DEBUG] stderr: {stderr[:400]}")
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired as exc:
        if debug:
            print(f"[DEBUG] Timeout {timeout}s en comando: {' '.join(cmd)}")
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or f"Timeout tras {timeout}s")
        return 124, stdout, stderr


def check_gcp_connection(project_id: str, console: Optional[Console], debug: bool = False) -> bool:
    try:
        auth_cmd = ['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)']
        code, stdout, stderr = run_command(auth_cmd, debug)
        if code != 0 or not stdout:
            msg = "❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login"
            if RICH_AVAILABLE and console:
                console.print(f"[red]{msg}[/]")
            else:
                print(msg)
            return False
        active_account = stdout.splitlines()[0]
        if RICH_AVAILABLE and console:
            console.print(f"[dim]🔐 Cuenta activa: {active_account}[/]")
        else:
            print(f"🔐 Cuenta activa: {active_account}")

        project_cmd = ['gcloud', 'projects', 'describe', project_id, '--format=value(projectId)']
        code, stdout, stderr = run_command(project_cmd, debug)
        if code != 0:
            error_msg = stderr or stdout or "Error desconocido"
            msg = f"❌ Error accediendo al proyecto {project_id}: {error_msg}"
            if RICH_AVAILABLE and console:
                console.print(f"[red]{msg}[/]")
            else:
                print(msg)
            return False
        if RICH_AVAILABLE and console:
            console.print(f"[dim]✅ Conexión verificada al proyecto: {project_id}[/]")
        else:
            print(f"✅ Conexión verificada al proyecto: {project_id}")
        return True
    except FileNotFoundError:
        msg = "❌ gcloud no está instalado o no está en el PATH"
        if RICH_AVAILABLE and console:
            console.print(f"[red]{msg}[/]")
        else:
            print(msg)
        return False


def get_deployment_manifest(deployment: str, namespace: str, debug: bool = False) -> Optional[Dict]:
    if namespace:
        cmd = ['kubectl', 'get', 'deployment', deployment, '-n', namespace, '-o', 'json']
        code, stdout, stderr = run_command(cmd, debug)
        if code != 0 or not stdout:
            return None
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None

    # Sin namespace explícito: obtener todos y buscar coincidencia por nombre
    cmd = ['kubectl', 'get', 'deployment', '-A', '-o', 'json']
    code, stdout, stderr = run_command(cmd, debug)
    if code != 0 or not stdout:
        return None
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    items = data.get('items', []) if isinstance(data, dict) else []
    for item in items:
        if item.get('metadata', {}).get('name') == deployment:
            return item
    return None


def extract_configmap_names(deployment: Dict) -> Tuple[str, str, List[str]]:
    namespace = deployment.get('metadata', {}).get('namespace', 'default')
    spec = deployment.get('spec', {}).get('template', {}).get('spec', {})
    service_account = spec.get('serviceAccountName', 'default')
    containers = spec.get('containers', [])
    configmaps = set()
    for container in containers:
        for env_from in container.get('envFrom', []):
            cm_ref = env_from.get('configMapRef', {})
            if cm_ref.get('name'):
                configmaps.add(cm_ref['name'])
        for env in container.get('env', []):
            value_from = env.get('valueFrom', {})
            cm_key_ref = value_from.get('configMapKeyRef', {})
            if cm_key_ref.get('name'):
                configmaps.add(cm_key_ref['name'])
    for volume in spec.get('volumes', []):
        cm = volume.get('configMap', {})
        if cm.get('name'):
            configmaps.add(cm['name'])
    return namespace or 'default', service_account or 'default', sorted(configmaps)


def get_configmap_data(configmap: str, namespace: str, debug: bool = False) -> Optional[Dict[str, str]]:
    cmd = ['kubectl', 'get', 'configmap', configmap, '-n', namespace, '-o', 'json']
    code, stdout, stderr = run_command(cmd, debug)
    if code != 0 or not stdout:
        return None
    try:
        cm_json = json.loads(stdout)
        return cm_json.get('data', {}) or {}
    except json.JSONDecodeError:
        return None


def parse_connection_values(value: str) -> List[Tuple[str, int, str, str]]:
    results: List[Tuple[str, int, str, str]] = []
    if not value:
        return results
    # URLs tipo jdbc:/postgresql etc.
    for match in URL_PATTERN.finditer(value):
        raw_url = match.group(2)
        db_type = match.group('engine') or 'unknown'
        normalized = raw_url
        if normalized.lower().startswith('jdbc:'):
            normalized = normalized[5:]
        parsed = urlparse(normalized)
        host = parsed.hostname
        port = parsed.port
        if host and port:
            results.append((host, port, raw_url, db_type.lower()))
    # host:puerto planos
    for match in HOST_PORT_PATTERN.findall(value):
        host, port = match
        try:
            port_int = int(port)
        except ValueError:
            continue
        if 0 < port_int < 65536:
            results.append((host, port_int, f"{host}:{port}", 'unknown'))
    return results


def get_current_namespace(debug: bool = False) -> str:
    cmd = ['kubectl', 'config', 'view', '--minify', '--output', 'jsonpath={..namespace}']
    code, stdout, stderr = run_command(cmd, debug)
    if code != 0:
        return 'default'
    ns = stdout.strip() or 'default'
    return ns


def collect_connections(configmaps: List[str], namespace: str, debug: bool = False) -> List[Dict]:
    connections: List[Dict] = []
    for cm in configmaps:
        data = get_configmap_data(cm, namespace, debug)
        if data is None:
            connections.append({
                'configmap': cm,
                'key': '-',
                'host': '-',
                'port': '-',
                'raw_value': 'ConfigMap no accesible',
                'status': 'ERROR',
                'message': 'kubectl no pudo obtener el ConfigMap',
                'elapsed': 0.0
            })
            continue
        for key, value in data.items():
            for host, port, raw, db_type in parse_connection_values(value):
                connections.append({
                    'configmap': cm,
                    'key': key,
                    'host': host,
                    'port': port,
                    'db_type': db_type,
                    'raw_value': raw,
                    'status': 'PENDING',
                    'message': 'Pendiente de validación',
                    'elapsed': 0.0
                })
    return connections


def test_tcp_connectivity(host: str, port: int, timeout: int = 5) -> Tuple[str, str, float]:
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = time.time() - start
            return 'OK', f"Conexión exitosa en {elapsed:.2f}s", elapsed
    except socket.timeout:
        elapsed = time.time() - start
        return 'TIMEOUT', f"Timeout tras {timeout}s", elapsed
    except Exception as exc:
        elapsed = time.time() - start
        return 'ERROR', str(exc), elapsed


def create_probe_pod(namespace: str, service_account: str, image: str, console: Optional[Console], debug: bool = False) -> Tuple[Optional[str], Optional[str]]:
    pod_name = f"nettools-sre-{int(time.time())}"
    cmd = [
        'kubectl', 'run', pod_name,
        '--image', image,
        '--restart=Never',
        '-n', namespace,
        '--command', '--', 'sh', '-c', 'sleep 3600'
    ]
    if service_account:
        cmd.extend(['--serviceaccount', service_account])

    code, stdout, stderr = run_command(cmd, debug)
    if code != 0:
        error_msg = stderr or stdout or "Error creando pod de pruebas"
        return None, error_msg

    wait_cmd = ['kubectl', 'wait', '--for=condition=Ready', f'pod/{pod_name}', '-n', namespace, '--timeout=90s']
    code, stdout, stderr = run_command(wait_cmd, debug)
    if code != 0:
        error_msg = stderr or stdout or "El pod de pruebas no quedó listo"
        delete_probe_pod(pod_name, namespace, debug)
        return None, error_msg

    if RICH_AVAILABLE and console:
        console.print(f"[dim]🧪 Pod temporal listo: {pod_name} (ns: {namespace})[/]")
    return pod_name, None


def delete_probe_pod(pod_name: str, namespace: str, debug: bool = False):
    run_command(['kubectl', 'delete', 'pod', pod_name, '-n', namespace, '--ignore-not-found'], debug)


def test_connectivity_via_pod(pod_name: str, namespace: str, host: str, port: int, timeout: int, debug: bool = False) -> Tuple[str, str, float]:
    start = time.time()
    command = f"nc -z -w {timeout} {host} {port}"
    exec_cmd = ['kubectl', 'exec', pod_name, '-n', namespace, '--', 'sh', '-c', command]
    code, stdout, stderr = run_command(exec_cmd, debug, timeout=timeout + 5)
    elapsed = time.time() - start
    if code == 0:
        return 'OK', f"Conexión desde pod en {elapsed:.2f}s", elapsed
    if code == 124:
        return 'TIMEOUT', f"Timeout tras {timeout}s desde pod", elapsed
    return 'ERROR', (stderr or stdout or 'Error ejecutando nc'), elapsed


def export_results(connections: List[Dict], filepath: str, export_format: str, metadata: Dict):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if export_format == 'csv':
        import csv
        fieldnames = ['project', 'deployment', 'namespace', 'configmap', 'key', 'db_type', 'host', 'port', 'status', 'message', 'elapsed', 'raw_value', 'timestamp']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in connections:
                payload = {**metadata, **row}
                writer.writerow(payload)
    else:
        export_data = {
            'metadata': metadata,
            'connections': connections
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)


def print_results(console: Optional[Console], connections: List[Dict]):
    if RICH_AVAILABLE and console:
        table = Table(title="🔌 Resultados de Conectividad", title_style="bold magenta", header_style="bold cyan", border_style="dim")
        table.add_column("ConfigMap", style="white")
        table.add_column("Key", style="white")
        table.add_column("Tipo", justify="left")
        table.add_column("Host", justify="left")
        table.add_column("Puerto", justify="center")
        table.add_column("Estado", justify="center")
        table.add_column("Mensaje", justify="left", max_width=50)
        for conn in connections:
            status_style = 'green' if conn['status'] == 'OK' else 'yellow' if conn['status'] == 'TIMEOUT' else 'red'
            table.add_row(
                conn['configmap'],
                conn['key'],
                conn.get('db_type', 'unknown'),
                conn['host'],
                str(conn['port']),
                f"[{status_style}]{conn['status']}[/{status_style}]",
                conn['message']
            )
        console.print(table)
    else:
        print("ConfigMap\tKey\tHost\tPort\tStatus\tMessage")
        for conn in connections:
            print(f"{conn['configmap']}\t{conn['key']}\t{conn['host']}\t{conn['port']}\t{conn['status']}\t{conn['message']}")


def print_summary_counts(console: Optional[Console], connections: List[Dict]):
    total = len(connections)
    counts = {
        'OK': sum(1 for c in connections if c['status'] == 'OK'),
        'TIMEOUT': sum(1 for c in connections if c['status'] == 'TIMEOUT'),
        'ERROR': sum(1 for c in connections if c['status'] == 'ERROR'),
        'SKIPPED': sum(1 for c in connections if c['status'] == 'SKIPPED')
    }
    summary_text = (
        f"[bold green]OK: {counts['OK']}[/]  "
        f"[bold yellow]TIMEOUT: {counts['TIMEOUT']}[/]  "
        f"[bold red]ERROR: {counts['ERROR']}[/]  "
        f"[dim]SKIPPED: {counts['SKIPPED']}[/]"
    )
    if RICH_AVAILABLE and console:
        console.print(Panel(summary_text + f"  | Total: {total}", title="Resumen Validaciones", border_style="blue", expand=False))
    else:
        print(f"Resumen -> OK:{counts['OK']} TIMEOUT:{counts['TIMEOUT']} ERROR:{counts['ERROR']} SKIPPED:{counts['SKIPPED']} Total:{total}")


def print_execution_time(start_time: float, console: Optional[Console], tz_name: str):
    end_time = time.time()
    duration = end_time - start_time
    tz = ZoneInfo(tz_name)
    start_dt = datetime.fromtimestamp(start_time, tz)
    end_dt = datetime.fromtimestamp(end_time, tz)
    duration_str = f"{duration:.2f}s"
    if RICH_AVAILABLE and console:
        panel = Table(title="⏱️ Tiempo de Ejecución", title_style="bold cyan", border_style="dim")
        panel.add_column("Métrica", style="white")
        panel.add_column("Valor", style="green")
        panel.add_row("Inicio", start_dt.strftime(f"%Y-%m-%d %H:%M:%S ({tz_name})"))
        panel.add_row("Fin", end_dt.strftime(f"%Y-%m-%d %H:%M:%S ({tz_name})"))
        panel.add_row("Duración", duration_str)
        console.print("\n")
        console.print(panel)
    else:
        print(f"⏱️ Tiempo total: {duration_str}")


def main():
    start_time = time.time()
    args = get_args()
    console = Console() if RICH_AVAILABLE else None

    if args.help:
        show_help(console)
        return 0

    project_id = args.project
    deployment = args.deployment
    namespace_arg = args.namespace.strip()
    timeout = max(1, args.timeout)
    tz_name = args.timezone
    probe_mode = args.probe_mode
    probe_image = args.probe_image
    probe_pod_name: Optional[str] = None
    probe_namespace: Optional[str] = None

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz_name = DEFAULT_TIMEZONE
        tz = ZoneInfo(tz_name)
        if RICH_AVAILABLE and console:
            console.print(f"[yellow]⚠️ Zona horaria inválida. Usando {DEFAULT_TIMEZONE}[/]")
        else:
            print(f"⚠️ Zona horaria inválida. Usando {DEFAULT_TIMEZONE}")

    if RICH_AVAILABLE and console:
        console.print(Panel(f"📦 Deployment: [white]{deployment}[/]\n📍 Proyecto: [white]{project_id}[/]", title="Deploy Dependency Checker", border_style="blue"))
    else:
        print(f"Analizando deployment {deployment} en proyecto {project_id}")

    try:
        if not check_gcp_connection(project_id, console, args.debug):
            return 1

        effective_namespace = namespace_arg or get_current_namespace(args.debug)
        if not namespace_arg and RICH_AVAILABLE and console:
            console.print(f"[dim]📛 Namespace detectado automáticamente: {effective_namespace}[/]")

        deployment_manifest = get_deployment_manifest(deployment, effective_namespace, args.debug)
        if not deployment_manifest and not namespace_arg:
            # Intento automático sin namespace ya realizado dentro de get_deployment_manifest
            # pero si se encontró en otro namespace, ajuste effective_namespace
            deployment_manifest = get_deployment_manifest(deployment, "", args.debug)
            if deployment_manifest:
                detected_ns = deployment_manifest.get('metadata', {}).get('namespace')
                if detected_ns and RICH_AVAILABLE and console:
                    console.print(f"[dim]📛 Namespace detectado automáticamente: {detected_ns}[/]")
                effective_namespace = detected_ns or effective_namespace

        if not deployment_manifest:
            msg = f"❌ No se pudo obtener el deployment {deployment}. Verifica que exista y que kubectl tenga acceso."
            if RICH_AVAILABLE and console:
                console.print(f"[red]{msg}[/]")
            else:
                print(msg)
            return 1

        namespace, service_account, configmaps = extract_configmap_names(deployment_manifest)
        probe_namespace = namespace
        if not configmaps:
            msg = "⚠️ El deployment no hace referencia a ningún ConfigMap."
            if RICH_AVAILABLE and console:
                console.print(f"[yellow]{msg}[/]")
            else:
                print(msg)
            return 0

        if RICH_AVAILABLE and console:
            console.print(f"[dim]📄 ConfigMaps detectados ({namespace}): {', '.join(configmaps)}[/]")
        else:
            print(f"ConfigMaps detectados ({namespace}): {', '.join(configmaps)}")

        with (Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console)
              if RICH_AVAILABLE and console else nullcontext()) as progress:
            if RICH_AVAILABLE and console:
                task = progress.add_task("Recolectando ConfigMaps...", total=None)
            connections = collect_connections(configmaps, namespace, args.debug)
            if RICH_AVAILABLE and console:
                progress.update(task, completed=True)

        if not connections:
            msg = "⚠️ No se detectaron cadenas de conexión en los ConfigMaps."
            if RICH_AVAILABLE and console:
                console.print(f"[yellow]{msg}[/]")
            else:
                print(msg)
            return 0

        if probe_mode == "pod":
            probe_pod_name, error_msg = create_probe_pod(namespace, service_account, probe_image, console, args.debug)
            if not probe_pod_name:
                warning_msg = f"⚠️ No se pudo crear pod temporal ({error_msg}). Reintentando en modo local."
                if RICH_AVAILABLE and console:
                    console.print(f"[yellow]{warning_msg}[/]")
                else:
                    print(warning_msg)
                probe_mode = "local"

        for conn in connections:
            host = conn.get('host')
            port = conn.get('port')
            if host == '-' or port in ('-', None):
                conn['status'] = 'SKIPPED'
                conn['message'] = conn.get('raw_value', 'No se pudo interpretar host/puerto')
                continue
            if probe_mode == "pod" and probe_pod_name:
                status, message, elapsed = test_connectivity_via_pod(probe_pod_name, namespace, host, int(port), timeout, args.debug)
            else:
                status, message, elapsed = test_tcp_connectivity(host, int(port), timeout)
            conn['status'] = status
            conn['message'] = message
            conn['elapsed'] = round(elapsed, 3)
            conn['timestamp'] = datetime.now(timezone.utc).isoformat()
            conn['project'] = project_id
            conn['deployment'] = deployment
            conn['namespace'] = namespace

        print_results(console, connections)
        print_summary_counts(console, connections)

        if args.output:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            outcome_dir = os.path.join(script_dir, 'outcome')
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"deploy_dependency_{deployment}_{timestamp}.{args.output}"
            filepath = os.path.join(outcome_dir, filename)
            metadata = {
                'project': project_id,
                'deployment': deployment,
                'namespace': namespace,
                'timestamp': datetime.now(tz).strftime(f"%Y-%m-%d %H:%M:%S ({tz_name})")
            }
            export_results(connections, filepath, args.output, metadata)
            msg = f"📁 Archivo exportado: {filepath}"
            if RICH_AVAILABLE and console:
                console.print(f"[bold green]{msg}[/]")
            else:
                print(msg)

        return 0

    except KeyboardInterrupt:
        interrupt_msg = "⚠️ Ejecución interrumpida por el usuario. Iniciando limpieza..."
        if RICH_AVAILABLE and console:
            console.print(f"[yellow]{interrupt_msg}[/]")
        else:
            print(interrupt_msg)
        return 130
    except Exception as exc:
        error_msg = f"❌ Error inesperado: {exc}"
        if RICH_AVAILABLE and console:
            console.print(f"[red]{error_msg}[/]")
        else:
            print(error_msg)
        return 1

    finally:
        if probe_pod_name and probe_namespace:
            if RICH_AVAILABLE and console:
                console.print(f"[dim]🧽 Eliminando pod temporal: {probe_pod_name}[/]")
            delete_probe_pod(probe_pod_name, probe_namespace, args.debug)
        print_execution_time(start_time, console, tz_name)


if __name__ == "__main__":
    main()
