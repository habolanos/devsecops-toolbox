#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Dependency Checker

Analiza los ConfigMaps referenciados por un Deployment de GKE para identificar
cadenas de conexión a bases de datos y validar la conectividad TCP hacia cada host:puerto detectado.
Soporta referencias a GCP Secret Manager para obtener credenciales de conexión de forma segura.
"""

from __future__ import annotations

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

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Type hint fallback - won't be used at runtime if Rich is available
    Console = type(None)

DEFAULT_PROJECT_ID = "cpl-corp-cial-prod-17042024"
DEFAULT_CLUSTER_ID = "gke-corp-cial-prod-01"
DEFAULT_REGION = "us-central1"
DEFAULT_DEPLOYMENT = "ds-ppm-pricing-discount"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_PROBE_IMAGE = "jrecord/nettools:latest"
__version__ = "1.0.5"

URL_PATTERN = re.compile(r"(jdbc:)?((?P<engine>postgres(?:ql)?|mysql|mssql|sqlserver|oracle|mongodb|redis|cockroachdb)://[^\s'\"` ]+)", re.IGNORECASE)
HOST_PORT_PATTERN = re.compile(r"([a-zA-Z0-9.-]+):(\d{2,5})")

# Puertos por defecto por motor de BD — usados cuando la URL no incluye puerto explícito
DB_DEFAULT_PORTS: Dict[str, int] = {
    'postgresql': 5432,
    'postgres':   5432,
    'mysql':      3306,
    'mssql':      1433,
    'sqlserver':  1433,
    'oracle':     1521,
    'mongodb':    27017,
    'redis':      6379,
    'cockroachdb': 26257,
}


def get_args():
    parser = argparse.ArgumentParser(
        description="SRE Tool: Deploy Dependency Checker (kubectl)",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        default=DEFAULT_PROJECT_ID,
        help=f"ID del proyecto de GCP (Default: {DEFAULT_PROJECT_ID})"
    )
    parser.add_argument(
        "--cluster", "-c",
        type=str,
        default=DEFAULT_CLUSTER_ID,
        help=f"Nombre del cluster GKE (Default: {DEFAULT_CLUSTER_ID})"
    )
    parser.add_argument(
        "--region", "-r",
        type=str,
        default=DEFAULT_REGION,
        help=f"Región del cluster GKE (Default: {DEFAULT_REGION})"
    )
    parser.add_argument(
        "--deployment", "-d",
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
        "--db-probe",
        action="store_true",
        help=(
            "Verificación nivel 2: después del check TCP envía protocolo nativo del motor DB "
            "(PostgreSQL SSL-request, MySQL greeting, Redis PING) para detectar falsos positivos "
            "de load balancers que aceptan TCP pero tienen la BD apagada. "
            "Solo aplica en --probe-mode=pod."
        )
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


def configure_kubectl_context(project: str, cluster: str, region: str, 
                               console: Optional[Console] = None, debug: bool = False) -> bool:
    """Configura el contexto de kubectl para el cluster GKE especificado."""
    if RICH_AVAILABLE and console:
        console.print(f"[dim]⚙️ Configurando contexto kubectl para cluster {cluster}...[/]")
    else:
        print(f"⚙️ Configurando kubectl para cluster {cluster}...")
    
    cmd = [
        'gcloud', 'container', 'clusters', 'get-credentials', cluster,
        '--region', region,
        '--project', project
    ]
    
    code, stdout, stderr = run_command(cmd, debug, timeout=60)
    
    if code != 0:
        error_msg = stderr or stdout or "Error configurando kubectl"
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ {error_msg}[/]")
        else:
            print(f"❌ {error_msg}")
        return False
    
    if RICH_AVAILABLE and console:
        console.print(f"[dim]✅ Contexto kubectl configurado[/]")
    else:
        print(f"✅ Contexto kubectl configurado")
    
    return True


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
        # Limpiar parámetros JDBC de SQL Server (;param=value)
        if ';' in normalized:
            normalized = normalized.split(';')[0]
        parsed = urlparse(normalized)
        host = parsed.hostname
        # Usar puerto explícito; si omitido, usar default por engine
        port = parsed.port or DB_DEFAULT_PORTS.get(db_type.lower())
        if host and port:
            results.append((host, port, raw_url, db_type.lower()))
    # host:puerto planos (formato estandar host:port)
    for match in HOST_PORT_PATTERN.findall(value):
        host, port = match
        try:
            port_int = int(port)
        except ValueError:
            continue
        if 0 < port_int < 65536:
            results.append((host, port_int, f"{host}:{port}", 'unknown'))
    # SQL Server connection strings: Server=hostname,port;Database=...
    sqlserver_pattern = re.compile(
        r'Server\s*=\s*([^,;\s]+)\s*,\s*(\d{2,5})',
        re.IGNORECASE
    )
    for match in sqlserver_pattern.finditer(value):
        host = match.group(1).strip()
        port_str = match.group(2).strip()
        try:
            port_int = int(port_str)
        except ValueError:
            continue
        if 0 < port_int < 65536:
            raw_conn = f"Server={host},{port_int}"
            results.append((host, port_int, raw_conn, 'mssql'))
    return results


def parse_secret_manager_references(value: str) -> List[Dict]:
    """Parsea referencias a Secret Manager desde un valor de ConfigMap (YAML)."""
    if not value or 'secretManager' not in value:
        return []

    # Intentar usar PyYAML si está disponible
    try:
        import yaml
        data = yaml.safe_load(value)
        if not isinstance(data, dict):
            return []
        sm = data.get('secretManager')
        if not isinstance(sm, dict):
            return []
        project_id = sm.get('projectId', '')
        secrets = sm.get('secrets', {})
        if not isinstance(secrets, dict):
            return []
        results: List[Dict] = []
        for key, cfg in secrets.items():
            if isinstance(cfg, dict):
                results.append({
                    'connection_key': key,
                    'project_id': str(project_id),
                    'secret_name': str(cfg.get('name', '')),
                    'secret_version': str(cfg.get('version', 'latest')),
                })
        return results
    except Exception:
        pass

    # Fallback: parsing con regex cuando yaml no está disponible
    results: List[Dict] = []
    project_match = re.search(r'projectId\s*:\s*([^\s\n]+)', value)
    project_id = project_match.group(1) if project_match else ''

    pattern = re.compile(
        r'(\w+)\s*:\s*\n\s+name\s*:\s*([^\s\n]+)\s*\n\s+version\s*:\s*([^\s\n]+)',
        re.MULTILINE
    )
    for m in pattern.finditer(value):
        results.append({
            'connection_key': m.group(1),
            'project_id': project_id,
            'secret_name': m.group(2),
            'secret_version': m.group(3),
        })
    return results


def fetch_gcp_secret(project_id: str, secret_name: str, version: str, debug: bool = False) -> Optional[Dict]:
    """Obtiene el valor de un secreto de GCP Secret Manager vía gcloud."""
    if not secret_name or not project_id:
        return None
    cmd = [
        'gcloud', 'secrets', 'versions', 'access', version,
        '--secret', secret_name,
        '--project', project_id,
    ]
    code, stdout, stderr = run_command(cmd, debug, timeout=30)
    if code != 0 or not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {'raw': stdout}


def get_current_namespace(debug: bool = False) -> str:
    cmd = ['kubectl', 'config', 'view', '--minify', '--output', 'jsonpath={..namespace}']
    code, stdout, stderr = run_command(cmd, debug)
    if code != 0:
        return 'default'
    ns = stdout.strip() or 'default'
    return ns


def _make_connection_dict(
    configmap: str, key: str, host: str, port, raw_value: str,
    status: str, message: str, db_type: str = 'unknown',
    source_type: str = 'configmap', secret_project: str = '',
    secret_name: str = '', secret_version: str = '', sm_key: str = ''
) -> Dict:
    """Helper para construir un diccionario de conexión uniforme."""
    return {
        'configmap':      configmap,
        'key':            key,
        'host':           host,
        'port':           port,
        'db_type':        db_type,
        'raw_value':      raw_value,
        'status':         status,
        'message':        message,
        'elapsed':        0.0,
        'db_probe_status':  '',
        'db_probe_message': '',
        'lb_name':          '',
        'lb_status':        '',
        'source_type':      source_type,
        'secret_project':   secret_project,
        'secret_name':      secret_name,
        'secret_version':   secret_version,
        'sm_key':           sm_key,
    }


def collect_connections(configmaps: List[str], namespace: str, debug: bool = False) -> List[Dict]:
    connections: List[Dict] = []
    for cm in configmaps:
        data = get_configmap_data(cm, namespace, debug)
        if data is None:
            connections.append(_make_connection_dict(
                cm, '-', '-', '-', 'ConfigMap no accesible',
                'ERROR', 'kubectl no pudo obtener el ConfigMap'
            ))
            continue
        for key, value in data.items():
            # 1) Cadenas de conexión tradicionales (JDBC, host:puerto, etc.)
            for host, port, raw, db_type in parse_connection_values(value):
                connections.append(_make_connection_dict(
                    cm, key, host, port, raw,
                    'PENDING', 'Pendiente de validación', db_type
                ))

            # 2) Referencias a Secret Manager
            for sm_ref in parse_secret_manager_references(value):
                secret_name = sm_ref.get('secret_name', '')
                secret_version = sm_ref.get('secret_version', 'latest')
                secret_project = sm_ref.get('project_id', '')
                connection_key = sm_ref.get('connection_key', '')

                secret_value = fetch_gcp_secret(secret_project, secret_name, secret_version, debug)

                if secret_value is None:
                    connections.append(_make_connection_dict(
                        cm, key, '-', '-',
                        f"SecretManager ref: {connection_key} -> {secret_name}:{secret_version} (project: {secret_project})",
                        'ERROR', f"No se pudo obtener el secreto {secret_name} del proyecto {secret_project}",
                        'unknown', 'secretmanager', secret_project, secret_name, secret_version, connection_key
                    ))
                    continue

                if isinstance(secret_value, dict):
                    host = secret_value.get('host', '')
                    port = secret_value.get('port')
                    db_type = secret_value.get('type', 'unknown')
                    if host and port:
                        try:
                            port_int = int(port)
                        except (ValueError, TypeError):
                            port_int = DB_DEFAULT_PORTS.get(str(db_type).lower())
                        if port_int:
                            connections.append(_make_connection_dict(
                                cm, key, host, port_int, json.dumps(secret_value),
                                'PENDING', 'Pendiente de validación', str(db_type).lower(),
                                'secretmanager', secret_project, secret_name, secret_version, connection_key
                            ))
                        continue
                    # Secreto obtenido pero no tiene host/puerto
                    connections.append(_make_connection_dict(
                        cm, key, '-', '-', json.dumps(secret_value),
                        'SKIPPED', 'Secreto obtenido pero no contiene host/puerto',
                        'unknown', 'secretmanager', secret_project, secret_name, secret_version, connection_key
                    ))
                else:
                    # Valor raw (string): intentar parsear como cadena de conexión
                    found = False
                    for host, port, raw, db_type in parse_connection_values(str(secret_value)):
                        found = True
                        connections.append(_make_connection_dict(
                            cm, key, host, port, raw,
                            'PENDING', 'Pendiente de validación', db_type,
                            'secretmanager', secret_project, secret_name, secret_version, connection_key
                        ))
                    if not found:
                        connections.append(_make_connection_dict(
                            cm, key, '-', '-', str(secret_value),
                            'SKIPPED', 'Secreto obtenido pero no contiene cadena de conexión reconocible',
                            'unknown', 'secretmanager', secret_project, secret_name, secret_version, connection_key
                        ))
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


def _clean_kubectl_stderr(stderr: str) -> str:
    """Elimina líneas informativas de kubectl del stderr (e.g. 'Defaulted container...')."""
    skip_prefixes = ('Defaulted container', "If you don't see a command prompt")
    lines = [l for l in stderr.splitlines()
             if not any(l.startswith(p) for p in skip_prefixes)]
    return '\n'.join(lines).strip()


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
    clean_err = _clean_kubectl_stderr(stderr or '') or (stdout or '').strip() or f"nc exit code {code}"
    return 'ERROR', clean_err, elapsed


# Scripts de probe de protocolo DB por motor.
# Se ejecutan via: kubectl exec POD -- python3 -c "SCRIPT"
# Usan solo la stdlib de Python 3 (sin dependencias extra).
_DB_PROBE_SCRIPTS: Dict[str, str] = {
    'postgresql': (
        "import socket,struct,sys\n"
        "try:\n"
        "  s=socket.create_connection(('{host}',{port}),timeout={timeout})\n"
        "  s.send(struct.pack('!ii',8,80877103))\n"
        "  r=s.recv(1)\n"
        "  s.close()\n"
        "  print('ALIVE' if r in(b'N',b'S',b'E') else 'UNEXPECTED:'+repr(r))\n"
        "except Exception as e:\n"
        "  print('FAILED:'+str(e))\n"
        "  sys.exit(1)\n"
    ),
    'mysql': (
        "import socket,sys\n"
        "try:\n"
        "  s=socket.create_connection(('{host}',{port}),timeout={timeout})\n"
        "  r=s.recv(5)\n"
        "  s.close()\n"
        "  print('ALIVE' if len(r)>=4 else 'UNEXPECTED:'+repr(r))\n"
        "except Exception as e:\n"
        "  print('FAILED:'+str(e))\n"
        "  sys.exit(1)\n"
    ),
    'redis': (
        "import socket,sys\n"
        "try:\n"
        "  s=socket.create_connection(('{host}',{port}),timeout={timeout})\n"
        "  s.send(b'*1\\r\\n$4\\r\\nPING\\r\\n')\n"
        "  r=s.recv(16)\n"
        "  s.close()\n"
        "  print('ALIVE' if b'PONG' in r or r.startswith(b'+') else 'UNEXPECTED:'+repr(r))\n"
        "except Exception as e:\n"
        "  print('FAILED:'+str(e))\n"
        "  sys.exit(1)\n"
    ),
}
_DB_PROBE_SCRIPTS['postgres'] = _DB_PROBE_SCRIPTS['postgresql']
_DB_PROBE_SCRIPTS['mssql']     = _DB_PROBE_SCRIPTS['mysql']
_DB_PROBE_SCRIPTS['sqlserver'] = _DB_PROBE_SCRIPTS['mysql']


# Fallback shell-based probe scripts para imágenes sin python3 (e.g. jrecord/nettools).
# Se ejecutan via: kubectl exec POD -- sh -c "SCRIPT"
# Requieren: nc, printf, od, head, tr  (disponibles en Alpine/busybox)
_DB_PROBE_SCRIPTS_SH: Dict[str, str] = {
    'postgresql': (
        # Envía SSL-request (8 bytes), verifica respuesta N/S/E (0x4e/0x53/0x45)
        "r=$(printf '\\000\\000\\000\\010\\004\\322\\026\\057' "
        "| nc -w {timeout} {host} {port} 2>/dev/null "
        "| head -c1 | od -An -tx1 | tr -d ' \\n'); "
        "case $r in 4e|53|45) echo ALIVE;; "
        "'') echo FAILED:no-response;; "
        "*) echo FAILED:unexpected_$r;; esac"
    ),
    'mysql': (
        # MySQL envía greeting inmediatamente al conectar
        "r=$(nc -w {timeout} {host} {port} 2>/dev/null | head -c5 | wc -c | tr -d ' '); "
        "[ \"${{r:-0}}\" -ge 4 ] 2>/dev/null && echo ALIVE || echo FAILED:recv=$r"
    ),
    'redis': (
        # Envía PING RESP, espera +PONG o *PONG
        "r=$(printf '*1\\r\\n$4\\r\\nPING\\r\\n' "
        "| nc -w {timeout} {host} {port} 2>/dev/null "
        "| head -c16); "
        "case \"$r\" in *PONG*) echo ALIVE;; *) echo FAILED;; esac"
    ),
}
_DB_PROBE_SCRIPTS_SH['postgres']   = _DB_PROBE_SCRIPTS_SH['postgresql']
_DB_PROBE_SCRIPTS_SH['mssql']      = _DB_PROBE_SCRIPTS_SH['mysql']
_DB_PROBE_SCRIPTS_SH['sqlserver']  = _DB_PROBE_SCRIPTS_SH['mysql']


def test_db_probe_via_pod(
    pod_name: str, namespace: str,
    host: str, port: int, db_type: str,
    timeout: int, debug: bool = False
) -> Tuple[str, str]:
    """
    Verificación de conectividad nivel 2 (protocolo nativo DB).
    Intenta primero con python3; si no está disponible en el pod (código 127),
    usa fallback shell (sh + nc + printf) para imágenes sin python3 (e.g. nettools).
    Returns (status, message): ALIVE / FAILED / UNEXPECTED / SKIPPED
    """
    engine = db_type.lower()
    script_template = _DB_PROBE_SCRIPTS.get(engine)
    if not script_template:
        return 'SKIPPED', f"Motor '{db_type}' sin probe implementado (soportados: postgresql, mysql, redis)"

    def _parse_output(out: str, code: int) -> Tuple[str, str]:
        if 'ALIVE' in out:
            return 'ALIVE', f"Motor {db_type.upper()} respondió al protocolo nativo"
        elif out.startswith('FAILED:'):
            return 'FAILED', out[7:] or "Conexión rechazada por el motor"
        elif out.startswith('UNEXPECTED:'):
            return 'UNEXPECTED', f"Respuesta no reconocida: {out[11:]}"
        elif code == 124:
            return 'FAILED', f"Timeout {timeout}s — motor no respondió"
        return None, None  # caller decides

    # ── Intento 1: python3 ──────────────────────────────────────────────────
    script = script_template.format(host=host, port=port, timeout=timeout)
    exec_cmd = ['kubectl', 'exec', pod_name, '-n', namespace, '--', 'python3', '-c', script]
    code, stdout, stderr = run_command(exec_cmd, debug, timeout=timeout + 15)
    output = (stdout or stderr or '').strip()

    status, msg = _parse_output(output, code)
    if status:
        return status, msg

    py3_missing = (code == 127 or
                   'not found' in output.lower() or
                   'no such file' in output.lower())

    # ── Intento 2: fallback sh/nc (para imágenes sin python3) ───────────────
    if py3_missing:
        sh_template = _DB_PROBE_SCRIPTS_SH.get(engine)
        if sh_template:
            if debug:
                print(f"[DEBUG] python3 no disponible, usando fallback sh para {engine}")
            sh_script = sh_template.format(host=host, port=port, timeout=timeout)
            exec_cmd = ['kubectl', 'exec', pod_name, '-n', namespace, '--', 'sh', '-c', sh_script]
            code, stdout, stderr = run_command(exec_cmd, debug, timeout=timeout + 15)
            output = (stdout or stderr or '').strip()
            status, msg = _parse_output(output, code)
            if status:
                return status, msg
            if code == 127 or 'not found' in output.lower():
                return 'SKIPPED', "nc/sh no disponible en el pod de prueba"
            return 'FAILED', output or f"Sin respuesta sh (código {code})"
        return 'SKIPPED', "python3 no disponible y sin fallback sh para este motor"

    return 'FAILED', output or f"Sin respuesta (código {code})"


def build_services_map(namespace: str, debug: bool = False) -> Dict:
    """Construye mapa {IP/hostname → info} con K8s Services del namespace para detectar LBs."""
    cmd = ['kubectl', 'get', 'svc', '-n', namespace, '-o', 'json']
    code, stdout, _ = run_command(cmd, debug)
    if code != 0 or not stdout:
        return {}
    try:
        items = json.loads(stdout).get('items', [])
    except json.JSONDecodeError:
        return {}
    svc_map: Dict = {}
    for svc in items:
        meta       = svc.get('metadata', {})
        spec       = svc.get('spec', {})
        status     = svc.get('status', {})
        name       = meta.get('name', '')
        ns         = meta.get('namespace', namespace)
        svc_type   = spec.get('type', 'ClusterIP')
        cluster_ip = spec.get('clusterIP', '')
        ingress    = status.get('loadBalancer', {}).get('ingress', [])
        ext_ip     = (ingress[0].get('ip') or ingress[0].get('hostname', '')) if ingress else ''
        lb_status  = 'OK' if ext_ip else ('PENDING' if svc_type == 'LoadBalancer' else 'N/A')
        info = {'name': name, 'namespace': ns, 'type': svc_type,
                'lb_status': lb_status, 'external_ip': ext_ip, 'cluster_ip': cluster_ip}
        if cluster_ip and cluster_ip not in ('None', ''):
            svc_map[cluster_ip] = info
        if ext_ip:
            svc_map[ext_ip] = info
        for dns in [name, f"{name}.{ns}", f"{name}.{ns}.svc",
                    f"{name}.{ns}.svc.cluster.local"]:
            if dns:
                svc_map[dns] = info
    return svc_map


def resolve_lb_for_host(host: str, svc_map: Dict) -> Tuple[str, str]:
    """Determina si un host es un K8s Service/LB. Returns (lb_label, lb_status)."""
    if not svc_map or not host:
        return ('', 'N/A')
    info = svc_map.get(host)
    if not info:
        try:
            import socket as _sock
            resolved = _sock.gethostbyname(host)
            info = svc_map.get(resolved)
        except Exception:
            pass
    if info:
        return (f"{info['name']} ({info['type']})", info['lb_status'])
    return ('', 'N/A')


def export_results(connections: List[Dict], filepath: str, export_format: str, metadata: Dict):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if export_format == 'csv':
        import csv
        fieldnames = [
            'project', 'deployment', 'namespace', 'configmap', 'key', 'db_type',
            'host', 'port', 'tcp_status', 'message', 'elapsed', 'raw_value',
            'lb_name', 'lb_status',
            'db_probe_status', 'db_probe_message',
            'source_type', 'secret_project', 'secret_name', 'secret_version', 'sm_key',
            'timestamp',
        ]
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in connections:
                payload = {**metadata, **row, 'tcp_status': row.get('status', '')}
                writer.writerow(payload)
    else:
        total = len(connections)
        summary = {
            'total':           total,
            'tcp_ok':          sum(1 for c in connections if c.get('status') == 'OK'),
            'tcp_timeout':     sum(1 for c in connections if c.get('status') == 'TIMEOUT'),
            'tcp_error':       sum(1 for c in connections if c.get('status') in ('ERROR', 'UNREACHABLE')),
            'lb_ok':           sum(1 for c in connections if c.get('lb_status') == 'OK'),
            'lb_pending':      sum(1 for c in connections if c.get('lb_status') == 'PENDING'),
            'db_probe_alive':  sum(1 for c in connections if c.get('db_probe_status') == 'ALIVE'),
            'db_probe_failed': sum(1 for c in connections if c.get('db_probe_status') == 'FAILED'),
            'skipped':         sum(1 for c in connections if c.get('status') == 'SKIPPED'),
        }
        export_data = {
            'metadata':    metadata,
            'summary':     summary,
            'connections': [
                {
                    'configmap':        c.get('configmap', ''),
                    'key':              c.get('key', ''),
                    'host':             c.get('host', ''),
                    'port':             c.get('port'),
                    'db_type':          c.get('db_type', 'unknown'),
                    'raw_value':        c.get('raw_value', ''),
                    'tcp_status':       c.get('status', ''),
                    'tcp_message':      c.get('message', ''),
                    'elapsed_s':        c.get('elapsed', 0.0),
                    'lb_name':          c.get('lb_name') or None,
                    'lb_status':        c.get('lb_status') or None,
                    'db_probe_status':  c.get('db_probe_status') or None,
                    'db_probe_message': c.get('db_probe_message') or None,
                    'source_type':      c.get('source_type', 'configmap'),
                    'secret_project':   c.get('secret_project') or None,
                    'secret_name':      c.get('secret_name') or None,
                    'secret_version':   c.get('secret_version') or None,
                    'sm_key':           c.get('sm_key') or None,
                    'timestamp':        c.get('timestamp', ''),
                }
                for c in connections
            ],
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)


def get_connection_type(raw_value: str) -> str:
    """Detecta el tipo de conexión basado en la cadena de conexión."""
    if not raw_value:
        return "unknown"
    raw_lower = raw_value.lower()
    if raw_lower.startswith("jdbc:"):
        return "JDBC"
    elif raw_lower.startswith(("http://", "https://")):
        return "HTTP"
    elif raw_lower.startswith(("mongodb://", "mongodb+srv://")):
        return "MongoDB"
    elif raw_lower.startswith("redis://"):
        return "Redis"
    elif raw_lower.startswith("amqp://"):
        return "AMQP"
    elif raw_lower.startswith(("postgres://", "postgresql://")):
        return "PostgreSQL"
    elif raw_lower.startswith("mysql://"):
        return "MySQL"
    elif raw_lower.startswith("sqlserver://"):
        return "SQLServer"
    elif "server=" in raw_lower and "," in raw_value:
        # SQL Server connection string: Server=host,port
        return "SQLServer"
    elif ":" in raw_value and raw_value.replace(".", "").split(":")[0].isdigit():
        return "TCP"
    return "TCP"


def _probe_badge(status: str) -> str:
    """Retorna badge Rich para el estado del DB probe."""
    mapping = {
        'ALIVE':    '[green]✅ ALIVE[/]',
        'FAILED':   '[red]🔴 FAILED[/]',
        'UNEXPECTED': '[yellow]⚠️  UNX[/]',
        'SKIPPED':  '[dim]⏭ SKIP[/]',
    }
    return mapping.get(status, f'[dim]{status or "—"}[/]')


def print_results(console: Optional[Console], connections: List[Dict]):
    if RICH_AVAILABLE and console:
        has_db_probe = any(c.get('db_probe_status') for c in connections)
        has_lb       = any(c.get('lb_name') for c in connections)
        has_sm       = any(c.get('source_type') == 'secretmanager' for c in connections)
        title_parts  = ["TCP"]
        if has_lb:       title_parts.append("LB")
        if has_db_probe: title_parts.append("DB Probe")
        if has_sm:       title_parts.append("Secret Manager")
        title = f"\U0001f50c Resultados de Conectividad ({' + '.join(title_parts)})"
        table = Table(title=title, title_style="bold magenta", header_style="bold cyan", border_style="dim")
        table.add_column("ConfigMap",  style="white")
        table.add_column("Key",        style="white")
        if has_sm:
            table.add_column("Source",     justify="center", width=10)
        table.add_column("Conexi\u00f3n",   justify="center", width=10)
        table.add_column("Tipo DB",    justify="left")
        table.add_column("Host",       justify="left")
        table.add_column("Puerto",     justify="center")
        table.add_column("TCP (L4)",    justify="center", width=12)
        table.add_column("Mensaje",    justify="left", max_width=40)
        if has_lb:
            table.add_column("Load Balancer", justify="center", width=18)
        if has_db_probe:
            table.add_column("DB Probe", justify="center", width=12)
        for conn in connections:
            # TCP column: siempre muestra resultado L4 real (preservado en tcp_status)
            # conn['status'] puede ser DB_PROBE_FAIL/WARN — no debe aparecer en esta columna
            tcp_raw   = conn.get('tcp_status', conn['status'])
            db_probe_s = conn.get('db_probe_status', '')
            if tcp_raw == 'OK' and db_probe_s == 'FAILED':
                tcp_cell = '[yellow]\u26a0\ufe0f  OK[/]'   # TCP OK pero BD no responde al protocolo
            elif tcp_raw == 'OK':
                tcp_cell = '[green]OK[/]'
            elif tcp_raw == 'TIMEOUT':
                tcp_cell = '[yellow]TIMEOUT[/]'
            else:
                tcp_cell = f'[red]{tcp_raw}[/]'
            conn_type = get_connection_type(conn.get('raw_value', ''))
            source_type = conn.get('source_type', 'configmap')
            source_icon = '🔐' if source_type == 'secretmanager' else '📋'
            source_label = 'SM' if source_type == 'secretmanager' else 'CM'
            
            row = [
                conn['configmap'],
                conn['key'],
            ]
            if has_sm:
                row.append(f"[magenta]{source_icon} {source_label}[/]")
            row.extend([
                f"[cyan]{conn_type}[/]",
                conn.get('db_type', 'unknown'),
                conn['host'],
                str(conn['port']),
                tcp_cell,
                conn['message'],
            ])
            if has_lb:
                lb_name   = conn.get('lb_name', '')
                lb_status = conn.get('lb_status', '')
                if lb_name:
                    lb_style = 'green' if lb_status == 'OK' else 'yellow' if lb_status == 'PENDING' else 'dim'
                    lb_icon  = '\u2705' if lb_status == 'OK' else '\u26a0\ufe0f' if lb_status == 'PENDING' else '\u2796'
                    row.append(f"[{lb_style}]{lb_icon} {lb_name}[/{lb_style}]")
                else:
                    row.append("[dim]\u2014[/]")
            if has_db_probe:
                row.append(_probe_badge(conn.get('db_probe_status', '')))
            table.add_row(*row)
        console.print(table)
        if has_lb:
            console.print(
                "[dim]\U0001f507 Load Balancer: K8s Service detectado como intermediario. "
                "OK = IP externa asignada. PENDING = LB en aprovisionamiento.[/]"
            )
        if has_db_probe:
            console.print(
                "[dim]\U0001f52c DB Probe: protocolo nativo del motor. "
                "ALIVE = motor responde. FAILED = TCP OK pero BD no responde al protocolo. "
                "\u26a0\ufe0f OK en TCP(L4) = red accesible pero motor con problemas.[/]"
            )
    else:
        print("ConfigMap\tKey\tConexi\u00f3n\tTipo\tHost\tPort\tTCP_Status\tLB\tDB_Probe\tMessage")
        for conn in connections:
            conn_type = get_connection_type(conn.get('raw_value', ''))
            print(
                f"{conn['configmap']}\t{conn['key']}\t{conn_type}\t"
                f"{conn.get('db_type', 'unknown')}\t{conn['host']}\t{conn['port']}\t"
                f"{conn['status']}\t{conn.get('lb_status', '')}\t"
                f"{conn.get('db_probe_status', '')}\t{conn['message']}"
            )


def print_summary_counts(console: Optional[Console], connections: List[Dict]):
    total = len(connections)
    counts = {
        'OK':      sum(1 for c in connections if c['status'] == 'OK'),
        'TIMEOUT': sum(1 for c in connections if c['status'] == 'TIMEOUT'),
        'ERROR':   sum(1 for c in connections if c['status'] in ('ERROR', 'DB_PROBE_FAIL')),
        'SKIPPED': sum(1 for c in connections if c['status'] == 'SKIPPED'),
    }
    probe_alive  = sum(1 for c in connections if c.get('db_probe_status') == 'ALIVE')
    probe_failed = sum(1 for c in connections if c.get('db_probe_status') == 'FAILED')
    summary_text = (
        f"[bold green]TCP OK: {counts['OK']}[/]  "
        f"[bold yellow]TIMEOUT: {counts['TIMEOUT']}[/]  "
        f"[bold red]ERROR: {counts['ERROR']}[/]  "
        f"[dim]SKIPPED: {counts['SKIPPED']}[/]"
    )
    if probe_alive or probe_failed:
        summary_text += (
            f"  │  [bold green]DB ALIVE: {probe_alive}[/]  "
            f"[bold red]DB FAIL: {probe_failed}[/]"
        )
    if RICH_AVAILABLE and console:
        console.print(Panel(summary_text + f"  | Total: {total}", title="Resumen Validaciones", border_style="blue", expand=False))
    else:
        print(f"Resumen -> TCP OK:{counts['OK']} TIMEOUT:{counts['TIMEOUT']} ERROR:{counts['ERROR']} SKIPPED:{counts['SKIPPED']} DB_ALIVE:{probe_alive} DB_FAIL:{probe_failed} Total:{total}")


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
    
    # Intentar crear console - forzar Rich incluso en subprocesos
    console = None
    if RICH_AVAILABLE:
        try:
            # Forzar terminal con color y unicode para subprocesos
            console = Console(
                force_terminal=True,
                force_interactive=False,
                color_system="auto",
                legacy_windows=False
            )
            if args.debug:
                console.print("[bold green][DEBUG] Rich Console creado exitosamente ✓[/]")
                console.print(f"[dim]Terminal: {console.is_terminal}, Color: {console.color_system}[/]")
        except Exception as e:
            if args.debug:
                print(f"[DEBUG] Error creando Console: {e}")
            console = None
    else:
        if args.debug:
            print(f"[DEBUG] RICH_AVAILABLE=False - Rich no está disponible")

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

        # Configurar contexto kubectl para el cluster
        if not configure_kubectl_context(project_id, args.cluster, args.region, console, args.debug):
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

        # ── Pre-resolución de Load Balancers (una sola llamada kubectl) ────────
        svc_map = build_services_map(namespace, args.debug)
        if svc_map and RICH_AVAILABLE and console:
            console.print(f"[dim]\U0001f50d Detectados {len(svc_map)} K8s Services para correlaci\u00f3n LB[/]")

        for conn in connections:
            host = conn.get('host')
            port = conn.get('port')
            if host == '-' or port in ('-', None):
                conn['status'] = 'SKIPPED'
                conn['message'] = conn.get('raw_value', 'No se pudo interpretar host/puerto')
                continue
            # ── LB lookup ────────────────────────────────────────
            conn['lb_name'], conn['lb_status'] = resolve_lb_for_host(host, svc_map)
            if probe_mode == "pod" and probe_pod_name:
                status, message, elapsed = test_connectivity_via_pod(probe_pod_name, namespace, host, int(port), timeout, args.debug)
            else:
                status, message, elapsed = test_tcp_connectivity(host, int(port), timeout)
            conn['status']    = status
            conn['message']   = message
            conn['elapsed']   = round(elapsed, 3)
            conn['timestamp'] = datetime.now(timezone.utc).isoformat()
            conn['project']   = project_id
            conn['deployment']= deployment
            conn['namespace'] = namespace

            conn['tcp_status'] = status  # L4 puro — nunca sobreescribir con resultado DB probe

            # ── Nivel 2: DB probe (solo si TCP OK, modo pod y flag activo) ──────────
            if args.db_probe and status == 'OK' and probe_mode == 'pod' and probe_pod_name:
                if RICH_AVAILABLE and console:
                    console.print(
                        f"[dim]  🔬 DB probe [{conn.get('db_type','?').upper()}] "
                        f"{host}:{port}...[/]"
                    )
                probe_status, probe_msg = test_db_probe_via_pod(
                    probe_pod_name, namespace, host, int(port),
                    conn.get('db_type', 'unknown'), timeout, args.debug
                )
                conn['db_probe_status']  = probe_status
                conn['db_probe_message'] = probe_msg
                if probe_status == 'FAILED':
                    conn['status']  = 'DB_PROBE_FAIL'
                    conn['message'] = f"TCP OK pero motor no responde: {probe_msg}"
                elif probe_status == 'UNEXPECTED':
                    conn['status']  = 'DB_PROBE_WARN'
                    conn['message'] = f"TCP OK, respuesta inesperada: {probe_msg}"

        print_results(console, connections)
        print_summary_counts(console, connections)

        if args.output:
            outcome_dir = get_output_dir("outcome")
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"deploy_dependency_{deployment}_{timestamp}.{args.output}"
            filepath = os.path.join(str(outcome_dir), filename)
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
