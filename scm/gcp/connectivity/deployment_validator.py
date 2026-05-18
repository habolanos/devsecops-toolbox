#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deployment Validator
====================
Herramienta completa para validar deployments de Kubernetes:
- Valida existencia y contenido de ConfigMaps y Secrets referenciados
- Detecta valores vacíos, placeholders o mal configurados
- Extrae cadenas de conexión a bases de datos
- Valida conectividad TCP usando pod temporal con nettools
- Genera reportes detallados con recomendaciones

Uso:
    python deployment_validator.py --deployment <nombre> [--namespace <ns>] [--validate all]
"""

import argparse
import subprocess
import json
import os
import re
import sys
import base64
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple, Any, Set
from urllib.parse import urlparse
from dataclasses import dataclass, field
from enum import Enum

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
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.0.2"
__author__ = "Harold Adrian"

DEFAULT_PROJECT_ID = "cpl-corp-cial-prod-17042024"
DEFAULT_CLUSTER_ID = "gke-corp-cial-prod-01"
DEFAULT_REGION = "us-central1"
DEFAULT_DEPLOYMENT = "ds-ppm-pricing-discount"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_PROBE_IMAGE = "jrecord/nettools:latest"
DEFAULT_TIMEOUT = 5

# Patrones para detectar cadenas de conexión
URL_PATTERN = re.compile(
    r"(jdbc:)?((?P<engine>postgres(?:ql)?|mysql|mssql|sqlserver|oracle|mongodb|redis|cockroachdb)://[^\s'\"`]+)",
    re.IGNORECASE
)
HOST_PORT_PATTERN = re.compile(r"([a-zA-Z0-9.-]+):(\d{2,5})")

# Puertos por defecto por motor de BD — usados cuando la URL no incluye puerto explícito
# Ej: jdbc:postgresql://host/db  →  postgresql default = 5432
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

# Valores considerados como placeholders o no configurados
PLACEHOLDER_VALUES = {
    "", "changeme", "change_me", "todo", "fixme", "placeholder",
    "xxx", "yyy", "zzz", "example", "your_value_here", "set_me",
    "replace_me", "update_this", "configure_me", "pending",
    "null", "none", "undefined", "<value>", "[value]", "{value}"
}

# Claves sensibles que requieren valores
SENSITIVE_KEY_PATTERNS = [
    r"password", r"passwd", r"secret", r"token", r"api[_-]?key",
    r"credentials?", r"auth", r"private[_-]?key", r"connection[_-]?string"
]


class Severity(Enum):
    """Niveles de severidad para hallazgos."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    OK = "OK"


@dataclass
class Finding:
    """Representa un hallazgo de validación."""
    category: str
    resource_type: str  # ConfigMap, Secret
    resource_name: str
    key: str
    severity: Severity
    message: str
    value_preview: str = ""
    remediation: str = ""


@dataclass
class ConnectionEndpoint:
    """Representa un endpoint de conexión detectado."""
    source_type: str  # ConfigMap o Secret
    source_name: str
    key: str
    host: str
    port: int
    db_type: str
    raw_value: str
    status: str = "PENDING"
    message: str = ""
    latency_ms: float = 0.0
    db_probe_status: str = ""   # Nivel 2: ALIVE / FAILED / SKIPPED / UNSUPPORTED
    db_probe_message: str = ""  # Detalle del probe de protocolo DB
    lb_name: str = ""           # Nombre del K8s Service si el host es un LB
    lb_status: str = ""         # OK | PENDING | N/A


@dataclass
class ValidationReport:
    """Reporte completo de validación."""
    project: str
    deployment: str
    namespace: str
    timestamp: str
    findings: List[Finding] = field(default_factory=list)
    endpoints: List[ConnectionEndpoint] = field(default_factory=list)
    configmaps_found: List[str] = field(default_factory=list)
    secrets_found: List[str] = field(default_factory=list)
    configmaps_missing: List[str] = field(default_factory=list)
    secrets_missing: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES UTILITARIAS
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Deployment Validator - Valida ConfigMaps, Secrets y conectividad de un Deployment",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        default=DEFAULT_PROJECT_ID,
        help=f"ID del proyecto GCP (Default: {DEFAULT_PROJECT_ID})"
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
        help=f"Nombre del deployment a validar (Default: {DEFAULT_DEPLOYMENT})"
    )
    parser.add_argument(
        "--namespace", "-n",
        type=str,
        default="",
        help="Namespace del deployment (auto-detecta si se omite)"
    )
    parser.add_argument(
        "--validate",
        type=str,
        choices=["all", "secrets", "configmaps", "connectivity"],
        default="all",
        help="Tipo de validación: all, secrets, configmaps, connectivity (Default: all)"
    )
    parser.add_argument(
        "--probe-image",
        type=str,
        default=DEFAULT_PROBE_IMAGE,
        help=f"Imagen para pod de pruebas (Default: {DEFAULT_PROBE_IMAGE})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout en segundos para pruebas de conectividad (Default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "csv"],
        help="Exportar resultados a archivo (json o csv)"
    )
    parser.add_argument(
        "--severity",
        type=str,
        choices=["critical", "warning", "info", "all"],
        default="all",
        help="Filtrar hallazgos por severidad mínima (Default: all)"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default=DEFAULT_TIMEZONE,
        help=f"Zona horaria para timestamps (Default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--db-probe",
        action="store_true",
        help=(
            "Verificación nivel 2: después del check TCP envia un paquete del protocolo "
            "nativo del motor DB (PostgreSQL/MySQL/Redis) para descartar falsos positivos "
            "de load balancers que responden TCP pero tienen la BD apagada"
        )
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug: muestra comandos ejecutados"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra esta ayuda"
    )
    return parser.parse_args()


def run_command(cmd: List[str], debug: bool = False, timeout: Optional[int] = None) -> Tuple[int, str, str]:
    """Ejecuta un comando y retorna código, stdout, stderr."""
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
            print(f"[DEBUG] Timeout {timeout}s en comando")
        stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = f"Timeout tras {timeout}s"
        return 124, stdout.strip(), stderr
    except FileNotFoundError:
        return 127, "", "Comando no encontrado"


def configure_kubectl_context(project: str, cluster: str, region: str, 
                               console: Optional[Any] = None, debug: bool = False) -> bool:
    """Configura el contexto de kubectl para el cluster GKE especificado."""
    if RICH_AVAILABLE and console:
        console.print(f"[dim]⚙️ Configurando contexto kubectl para cluster {cluster}...[/]")
    else:
        print(f"⚙️ Configurando kubectl para cluster {cluster}...", flush=True)
    
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
        print(f"✅ Contexto kubectl configurado", flush=True)
    
    return True


def is_placeholder_value(value: str) -> bool:
    """Verifica si un valor es un placeholder o no configurado."""
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized in PLACEHOLDER_VALUES


def is_sensitive_key(key: str) -> bool:
    """Verifica si una clave es sensible (password, token, etc.)."""
    key_lower = key.lower()
    return any(re.search(pattern, key_lower) for pattern in SENSITIVE_KEY_PATTERNS)


def mask_value(value: str, visible_chars: int = 4) -> str:
    """Enmascara un valor sensible mostrando solo los primeros caracteres."""
    if not value or len(value) <= visible_chars:
        return "****"
    return value[:visible_chars] + "*" * min(8, len(value) - visible_chars)


def parse_connection_string(value: str) -> List[Tuple[str, int, str, str]]:
    """Extrae endpoints de conexión de una cadena."""
    results: List[Tuple[str, int, str, str]] = []
    if not value:
        return results
    
    # URLs tipo jdbc:/postgresql, mongodb://, etc.
    for match in URL_PATTERN.finditer(value):
        raw_url = match.group(2)
        db_type = match.group('engine') or 'unknown'
        normalized = raw_url
        if normalized.lower().startswith('jdbc:'):
            normalized = normalized[5:]
        try:
            parsed = urlparse(normalized)
            host = parsed.hostname
            # Usar puerto explícito de la URL; si omitido, usar default por engine
            port = parsed.port or DB_DEFAULT_PORTS.get(db_type.lower())
            if host and port:
                results.append((host, port, raw_url, db_type.lower()))
        except Exception:
            pass
    
    # Patrones host:puerto planos
    for match in HOST_PORT_PATTERN.findall(value):
        host, port_str = match
        try:
            port = int(port_str)
            if 0 < port < 65536:
                # Evitar duplicados
                if not any(r[0] == host and r[1] == port for r in results):
                    results.append((host, port, f"{host}:{port}", 'unknown'))
        except ValueError:
            continue
    
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE KUBERNETES
# ═══════════════════════════════════════════════════════════════════════════════

def get_deployment_manifest(deployment: str, namespace: str, debug: bool = False) -> Optional[Dict]:
    """Obtiene el manifiesto de un deployment."""
    if namespace:
        cmd = ['kubectl', 'get', 'deployment', deployment, '-n', namespace, '-o', 'json']
        code, stdout, stderr = run_command(cmd, debug, timeout=30)
        if code == 0 and stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return None
        return None
    
    # Sin namespace: buscar en todos (puede tardar en clusters grandes)
    cmd = ['kubectl', 'get', 'deployment', '-A', '-o', 'json']
    code, stdout, stderr = run_command(cmd, debug, timeout=60)
    if code != 0 or not stdout:
        return None
    
    try:
        data = json.loads(stdout)
        items = data.get('items', []) if isinstance(data, dict) else []
        for item in items:
            if item.get('metadata', {}).get('name') == deployment:
                return item
    except json.JSONDecodeError:
        pass
    return None


def extract_resource_refs(deployment: Dict) -> Tuple[str, str, Set[str], Set[str]]:
    """Extrae referencias a ConfigMaps y Secrets del deployment."""
    metadata = deployment.get('metadata', {})
    namespace = metadata.get('namespace', 'default')
    
    spec = deployment.get('spec', {}).get('template', {}).get('spec', {})
    service_account = spec.get('serviceAccountName', 'default')
    
    configmaps: Set[str] = set()
    secrets: Set[str] = set()
    
    containers = spec.get('containers', []) + spec.get('initContainers', [])
    
    for container in containers:
        # envFrom
        for env_from in container.get('envFrom', []):
            if cm_ref := env_from.get('configMapRef', {}).get('name'):
                configmaps.add(cm_ref)
            if secret_ref := env_from.get('secretRef', {}).get('name'):
                secrets.add(secret_ref)
        
        # env con valueFrom
        for env in container.get('env', []):
            value_from = env.get('valueFrom', {})
            if cm_key := value_from.get('configMapKeyRef', {}).get('name'):
                configmaps.add(cm_key)
            if secret_key := value_from.get('secretKeyRef', {}).get('name'):
                secrets.add(secret_key)
    
    # Volumes
    for volume in spec.get('volumes', []):
        if cm := volume.get('configMap', {}).get('name'):
            configmaps.add(cm)
        if secret := volume.get('secret', {}).get('secretName'):
            secrets.add(secret)
    
    return namespace, service_account, configmaps, secrets


def get_configmap_data(name: str, namespace: str, debug: bool = False) -> Optional[Dict[str, str]]:
    """Obtiene los datos de un ConfigMap."""
    cmd = ['kubectl', 'get', 'configmap', name, '-n', namespace, '-o', 'json']
    code, stdout, stderr = run_command(cmd, debug, timeout=30)
    if code != 0 or not stdout:
        return None
    try:
        cm = json.loads(stdout)
        return cm.get('data', {}) or {}
    except json.JSONDecodeError:
        return None


def get_secret_data(name: str, namespace: str, debug: bool = False) -> Optional[Dict[str, str]]:
    """Obtiene los datos de un Secret (decodificados de base64)."""
    cmd = ['kubectl', 'get', 'secret', name, '-n', namespace, '-o', 'json']
    code, stdout, stderr = run_command(cmd, debug, timeout=30)
    if code != 0 or not stdout:
        return None
    try:
        secret = json.loads(stdout)
        raw_data = secret.get('data', {}) or {}
        decoded_data = {}
        for key, value_b64 in raw_data.items():
            try:
                decoded_data[key] = base64.b64decode(value_b64).decode('utf-8')
            except Exception:
                decoded_data[key] = "<binary-data>"
        return decoded_data
    except json.JSONDecodeError:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# POD TEMPORAL PARA CONECTIVIDAD
# ═══════════════════════════════════════════════════════════════════════════════

def create_probe_pod(namespace: str, service_account: str, image: str, 
                     console: Optional[Console], debug: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Crea un pod temporal para pruebas de conectividad."""
    pod_name = f"validator-probe-{int(time.time())}"
    
    cmd = [
        'kubectl', 'run', pod_name,
        '--image', image,
        '--restart=Never',
        '-n', namespace,
        '--command', '--', 'sh', '-c', 'sleep 3600'
    ]
    if service_account and service_account != 'default':
        cmd.extend(['--overrides', json.dumps({
            "spec": {"serviceAccountName": service_account}
        })])
    
    code, stdout, stderr = run_command(cmd, debug)
    if code != 0:
        return None, stderr or stdout or "Error creando pod"
    
    # Esperar a que el pod esté listo
    wait_cmd = ['kubectl', 'wait', '--for=condition=Ready', f'pod/{pod_name}', 
                '-n', namespace, '--timeout=90s']
    code, stdout, stderr = run_command(wait_cmd, debug)
    if code != 0:
        delete_probe_pod(pod_name, namespace, debug)
        return None, stderr or "Pod no quedó listo"
    
    if RICH_AVAILABLE and console:
        console.print(f"[dim]🧪 Pod temporal listo: {pod_name}[/]")
    
    return pod_name, None


def delete_probe_pod(pod_name: str, namespace: str, debug: bool = False):
    """Elimina el pod temporal."""
    run_command(['kubectl', 'delete', 'pod', pod_name, '-n', namespace, 
                 '--ignore-not-found', '--wait=false'], debug)


def test_connectivity_via_pod(pod_name: str, namespace: str, host: str, port: int,
                               timeout: int, debug: bool = False) -> Tuple[str, str, float]:
    """Prueba conectividad TCP desde el pod temporal usando nc."""
    start = time.time()
    command = f"nc -z -w {timeout} {host} {port}"
    exec_cmd = ['kubectl', 'exec', pod_name, '-n', namespace, '--', 'sh', '-c', command]
    
    code, stdout, stderr = run_command(exec_cmd, debug, timeout=timeout + 10)
    elapsed_ms = (time.time() - start) * 1000
    
    if code == 0:
        return 'OK', f"Conexión exitosa ({elapsed_ms:.0f}ms)", elapsed_ms
    elif code == 124:
        return 'TIMEOUT', f"Timeout tras {timeout}s", elapsed_ms
    else:
        return 'UNREACHABLE', stderr or stdout or 'No se pudo conectar', elapsed_ms


# Scripts de probe de protocolo DB por motor.
# Se ejecutan via: kubectl exec POD -- python3 -c "SCRIPT"
# Usan solo la stdlib de Python 3 (sin dependencias extra).
# Protocolo PostgreSQL: envía SSL-request (8 bytes), espera respuesta 'N'/'S'/'E'.
# Protocolo MySQL:      espera greeting packet (>= 4 bytes al conectar).
# Protocolo Redis:      envía PING RESP y espera +PONG.
_DB_PROBE_SCRIPTS: Dict[str, str] = {
    'postgresql': (
        "import socket,struct,sys\n"
        "try:\n"
        "  s=socket.create_connection(('{host}',{port}),timeout={timeout})\n"
        "  s.send(struct.pack('!ii',8,80877103))\n"   # SSL request packet
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
        "  r=s.recv(5)\n"   # MySQL sends greeting immediately on connect
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
_DB_PROBE_SCRIPTS['mssql']    = _DB_PROBE_SCRIPTS['mysql']   # similar greeting
_DB_PROBE_SCRIPTS['sqlserver']= _DB_PROBE_SCRIPTS['mysql']


def test_db_probe_via_pod(
    pod_name: str, namespace: str,
    host: str, port: int, db_type: str,
    timeout: int, debug: bool = False
) -> Tuple[str, str]:
    """
    Verificación de conectividad nivel 2 (protocolo nativo DB).

    Envía un paquete del protocolo real del motor de base de datos desde el pod
    temporal y verifica que el motor responde correctamente.
    Esto descarta falsos positivos donde un load balancer acepta el TCP handshake
    pero el servidor de BD real está apagado o no disponible.

    Returns:
        (status, message) donde status es uno de:
        - ALIVE        : el motor DB respondió con el protocolo esperado
        - FAILED       : el motor no respondió o cerró la conexión
        - UNEXPECTED   : TCP conectó pero la respuesta no coincide con el protocolo
        - SKIPPED      : motor no soportado o python3 no disponible en el pod
    """
    engine = db_type.lower()
    script_template = _DB_PROBE_SCRIPTS.get(engine)
    if not script_template:
        return 'SKIPPED', f"Motor '{db_type}' sin probe de protocolo implementado (soportados: postgresql, mysql, redis)"

    script = script_template.format(host=host, port=port, timeout=timeout)
    exec_cmd = ['kubectl', 'exec', pod_name, '-n', namespace, '--', 'python3', '-c', script]
    code, stdout, stderr = run_command(exec_cmd, debug, timeout=timeout + 15)

    output = (stdout or stderr or '').strip()

    if 'ALIVE' in output:
        return 'ALIVE', f"Motor {db_type.upper()} respondió al protocolo nativo"
    elif output.startswith('FAILED:'):
        return 'FAILED', output[7:] or "Conexión rechazada por el motor"
    elif output.startswith('UNEXPECTED:'):
        return 'UNEXPECTED', f"Respuesta no reconocida: {output[11:]}"
    elif code == 127 or 'not found' in output.lower():
        return 'SKIPPED', "python3 no disponible en el pod de prueba"
    elif code == 124:
        return 'FAILED', f"Timeout {timeout}s — motor no respondió"
    else:
        return 'FAILED', output or f"Sin respuesta (código {code})"


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIONES
# ═══════════════════════════════════════════════════════════════════════════════

def validate_configmaps(configmap_names: Set[str], namespace: str, 
                        report: ValidationReport, debug: bool = False) -> List[ConnectionEndpoint]:
    """Valida ConfigMaps y extrae endpoints de conexión."""
    endpoints: List[ConnectionEndpoint] = []
    
    for cm_name in sorted(configmap_names):
        data = get_configmap_data(cm_name, namespace, debug)
        
        if data is None:
            report.configmaps_missing.append(cm_name)
            report.findings.append(Finding(
                category="ConfigMap",
                resource_type="ConfigMap",
                resource_name=cm_name,
                key="*",
                severity=Severity.CRITICAL,
                message=f"ConfigMap '{cm_name}' no existe o no es accesible",
                remediation=f"kubectl create configmap {cm_name} -n {namespace} --from-literal=key=value"
            ))
            continue
        
        report.configmaps_found.append(cm_name)
        
        for key, value in data.items():
            # Verificar valores vacíos o placeholder
            if is_placeholder_value(value):
                report.findings.append(Finding(
                    category="ConfigMap",
                    resource_type="ConfigMap",
                    resource_name=cm_name,
                    key=key,
                    severity=Severity.WARNING,
                    message=f"Valor vacío o placeholder detectado",
                    value_preview=value[:50] if value else "<vacío>",
                    remediation=f"kubectl edit configmap {cm_name} -n {namespace}"
                ))
            
            # Extraer endpoints de conexión
            for host, port, raw, db_type in parse_connection_string(value):
                endpoints.append(ConnectionEndpoint(
                    source_type="ConfigMap",
                    source_name=cm_name,
                    key=key,
                    host=host,
                    port=port,
                    db_type=db_type,
                    raw_value=raw
                ))
    
    return endpoints


def validate_secrets(secret_names: Set[str], namespace: str, 
                     report: ValidationReport, debug: bool = False) -> List[ConnectionEndpoint]:
    """Valida Secrets y extrae endpoints de conexión."""
    endpoints: List[ConnectionEndpoint] = []
    
    for secret_name in sorted(secret_names):
        data = get_secret_data(secret_name, namespace, debug)
        
        if data is None:
            report.secrets_missing.append(secret_name)
            report.findings.append(Finding(
                category="Secret",
                resource_type="Secret",
                resource_name=secret_name,
                key="*",
                severity=Severity.CRITICAL,
                message=f"Secret '{secret_name}' no existe o no es accesible",
                remediation=f"kubectl create secret generic {secret_name} -n {namespace} --from-literal=key=value"
            ))
            continue
        
        report.secrets_found.append(secret_name)
        
        for key, value in data.items():
            # Verificar valores vacíos
            if is_placeholder_value(value):
                severity = Severity.CRITICAL if is_sensitive_key(key) else Severity.WARNING
                report.findings.append(Finding(
                    category="Secret",
                    resource_type="Secret",
                    resource_name=secret_name,
                    key=key,
                    severity=severity,
                    message=f"{'Clave sensible' if is_sensitive_key(key) else 'Clave'} con valor vacío o placeholder",
                    value_preview="<vacío>" if not value else mask_value(value),
                    remediation=f"kubectl patch secret {secret_name} -n {namespace} -p '{{\"stringData\":{{\"{key}\":\"NUEVO_VALOR\"}}}}'"
                ))
            
            # Verificar datos binarios
            if value == "<binary-data>":
                report.findings.append(Finding(
                    category="Secret",
                    resource_type="Secret",
                    resource_name=secret_name,
                    key=key,
                    severity=Severity.INFO,
                    message="Contiene datos binarios (no decodificable como UTF-8)",
                    value_preview="<binary>"
                ))
            
            # Extraer endpoints de conexión (si hay strings de conexión en secrets)
            if value and value != "<binary-data>":
                for host, port, raw, db_type in parse_connection_string(value):
                    endpoints.append(ConnectionEndpoint(
                        source_type="Secret",
                        source_name=secret_name,
                        key=key,
                        host=host,
                        port=port,
                        db_type=db_type,
                        raw_value=mask_value(raw, 20)
                    ))
    
    return endpoints


def validate_connectivity(endpoints: List[ConnectionEndpoint], namespace: str,
                          service_account: str, probe_image: str, timeout: int,
                          console: Optional[Console], debug: bool = False,
                          db_probe: bool = False) -> None:
    """
    Valida conectividad a todos los endpoints desde un pod temporal.

    Nivel 1 (siempre): TCP via nc -z — verifica que el puerto está accesible.
    Nivel 2 (--db-probe): protocolo nativo del motor DB — verifica que el motor
        real responde, descartando falsos positivos de load balancers que aceptan
        TCP pero tienen la BD apagada.
    """
    if not endpoints:
        return

    pod_name, error = create_probe_pod(namespace, service_account, probe_image, console, debug)

    if not pod_name:
        if RICH_AVAILABLE and console:
            console.print(f"[yellow]⚠️ No se pudo crear pod temporal: {error}[/]")
        for ep in endpoints:
            ep.status = "SKIPPED"
            ep.message = f"Pod temporal no disponible: {error}"
        return

    # ── Pre-resolución de Load Balancers (una sola llamada kubectl) ─────────
    svc_map = build_services_map(namespace, debug)
    if svc_map and RICH_AVAILABLE and console:
        console.print(f"[dim]🔍 Detectados {len(svc_map)} K8s Services para correlación LB[/]")

    try:
        for ep in endpoints:
            # ── Nivel 0: K8s Service / LB lookup ───────────────────────
            ep.lb_name, ep.lb_status = resolve_lb_for_host(ep.host, svc_map)

            # ── Nivel 1: TCP ────────────────────────────────────────────
            status, message, latency = test_connectivity_via_pod(
                pod_name, namespace, ep.host, ep.port, timeout, debug
            )
            ep.status = status
            ep.message = message
            ep.latency_ms = latency

            # ── Nivel 2: protocolo DB (solo si TCP OK y flag activo) ────
            if db_probe and status == 'OK':
                if RICH_AVAILABLE and console:
                    console.print(
                        f"[dim]  🔬 DB probe [{ep.db_type.upper()}] {ep.host}:{ep.port}...[/]"
                    )
                probe_status, probe_msg = test_db_probe_via_pod(
                    pod_name, namespace, ep.host, ep.port, ep.db_type, timeout, debug
                )
                ep.db_probe_status  = probe_status
                ep.db_probe_message = probe_msg
                # Si el motor no responde al protocolo, escalar el status TCP
                if probe_status == 'FAILED':
                    ep.status  = 'DB_PROBE_FAIL'
                    ep.message = f"TCP OK pero motor no responde: {probe_msg}"
                elif probe_status == 'UNEXPECTED':
                    ep.status  = 'DB_PROBE_WARN'
                    ep.message = f"TCP OK, respuesta inesperada del motor: {probe_msg}"
    finally:
        if RICH_AVAILABLE and console:
            console.print(f"[dim]🧹 Eliminando pod temporal: {pod_name}[/]")
        delete_probe_pod(pod_name, namespace, debug)


def build_services_map(namespace: str, debug: bool = False) -> Dict[str, Dict]:
    """
    Construye un mapa {IP/hostname → info} con todos los K8s Services del namespace.
    Usado para detectar si un endpoint de BD está detrás de un Load Balancer.
    """
    cmd = ['kubectl', 'get', 'svc', '-n', namespace, '-o', 'json']
    code, stdout, _ = run_command(cmd, debug, timeout=15)
    if code != 0 or not stdout:
        return {}
    try:
        items = json.loads(stdout).get('items', [])
    except json.JSONDecodeError:
        return {}

    svc_map: Dict[str, Dict] = {}
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

        info = {
            'name': name, 'namespace': ns, 'type': svc_type,
            'lb_status': lb_status, 'external_ip': ext_ip, 'cluster_ip': cluster_ip,
        }
        if cluster_ip and cluster_ip not in ('None', ''):
            svc_map[cluster_ip] = info
        if ext_ip:
            svc_map[ext_ip] = info
        for dns in [name, f"{name}.{ns}", f"{name}.{ns}.svc",
                    f"{name}.{ns}.svc.cluster.local"]:
            if dns:
                svc_map[dns] = info
    return svc_map


def resolve_lb_for_host(host: str, svc_map: Dict[str, Dict]) -> Tuple[str, str]:
    """
    Determina si un host es un K8s Service / LB.
    Returns (lb_label, lb_status): lb_label="" y lb_status="N/A" si no hay match.
    """
    if not svc_map or not host:
        return ('', 'N/A')
    info = svc_map.get(host)
    if not info:
        try:
            resolved = socket.gethostbyname(host)
            info = svc_map.get(resolved)
        except Exception:
            pass
    if info:
        return (f"{info['name']} ({info['type']})", info['lb_status'])
    return ('', 'N/A')


# ═══════════════════════════════════════════════════════════════════════════════
# PRESENTACIÓN DE RESULTADOS
# ═══════════════════════════════════════════════════════════════════════════════

def get_severity_style(severity: Severity) -> str:
    """Retorna el estilo de color para una severidad."""
    styles = {
        Severity.CRITICAL: "bold red",
        Severity.WARNING: "yellow",
        Severity.INFO: "cyan",
        Severity.OK: "green"
    }
    return styles.get(severity, "white")


def get_severity_emoji(severity: Severity) -> str:
    """Retorna el emoji para una severidad."""
    emojis = {
        Severity.CRITICAL: "🔴",
        Severity.WARNING: "🟡",
        Severity.INFO: "🔵",
        Severity.OK: "🟢"
    }
    return emojis.get(severity, "⚪")


def print_findings_table(console: Console, findings: List[Finding], severity_filter: str):
    """Imprime tabla de hallazgos."""
    # Filtrar por severidad si aplica
    if severity_filter != "all":
        severity_map = {"critical": Severity.CRITICAL, "warning": Severity.WARNING, "info": Severity.INFO}
        min_severity = severity_map.get(severity_filter, Severity.INFO)
        severity_order = [Severity.CRITICAL, Severity.WARNING, Severity.INFO]
        min_idx = severity_order.index(min_severity)
        findings = [f for f in findings if severity_order.index(f.severity) <= min_idx]
    
    if not findings:
        console.print(Panel("✅ No se encontraron hallazgos", style="green"))
        return
    
    table = Table(
        title="📋 Hallazgos de Validación",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="dim"
    )
    table.add_column("Sev", justify="center", width=4)
    table.add_column("Tipo", style="white", width=10)
    table.add_column("Recurso", style="white", width=25)
    table.add_column("Clave", style="white", width=20)
    table.add_column("Mensaje", style="white", max_width=45)
    
    for f in sorted(findings, key=lambda x: [Severity.CRITICAL, Severity.WARNING, Severity.INFO].index(x.severity)):
        style = get_severity_style(f.severity)
        emoji = get_severity_emoji(f.severity)
        table.add_row(
            emoji,
            f.resource_type,
            f.resource_name,
            f.key,
            f"[{style}]{f.message}[/{style}]"
        )
    
    console.print(table)


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
    elif ":" in raw_value and raw_value.replace(".", "").split(":")[0].isdigit():
        return "TCP"
    return "TCP"


def _probe_status_style(status: str) -> Tuple[str, str]:
    """Retorna (estilo_rich, emoji) para el estado de un DB probe."""
    mapping = {
        'ALIVE':        ('green',  '✅'),
        'FAILED':       ('red',    '🔴'),
        'UNEXPECTED':   ('yellow', '⚠️ '),
        'SKIPPED':      ('dim',    '⏭️ '),
        'DB_PROBE_FAIL':('red',    '🔴'),
        'DB_PROBE_WARN':('yellow', '⚠️ '),
    }
    return mapping.get(status, ('dim', '➖'))


def print_connectivity_table(console: Console, endpoints: List[ConnectionEndpoint]):
    """Imprime tabla de conectividad (nivel 1 TCP + nivel 2 DB probe si disponible)."""
    if not endpoints:
        console.print(Panel("ℹ️ No se detectaron endpoints de conexión", style="cyan"))
        return

    has_db_probe = any(ep.db_probe_status for ep in endpoints)
    has_lb       = any(ep.lb_name for ep in endpoints)

    title_parts = ["TCP"]
    if has_lb:       title_parts.append("LB")
    if has_db_probe: title_parts.append("DB Probe")
    title = f"🔌 Validación de Conectividad ({' + '.join(title_parts)})"

    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan", border_style="dim")
    table.add_column("Origen",   style="white",  width=10)
    table.add_column("Recurso",  style="white",  width=18)
    table.add_column("Conexión", justify="center", width=10)
    table.add_column("Tipo DB",  justify="center", width=10)
    table.add_column("Host",     style="white",  width=25)
    table.add_column("Puerto",   justify="center", width=6)
    table.add_column("TCP",      justify="center", width=12)
    table.add_column("Latencia", justify="right",  width=8)
    if has_lb:
        table.add_column("Load Balancer", justify="center", width=18)
    if has_db_probe:
        table.add_column("DB Probe", justify="center", width=12)

    for ep in endpoints:
        tcp_style = (
            "green"  if ep.status == 'OK' else
            "yellow" if ep.status in ('TIMEOUT', 'DB_PROBE_WARN') else
            "red"
        )
        latency_str = f"{ep.latency_ms:.0f}ms" if ep.latency_ms > 0 else "-"
        conn_type = get_connection_type(ep.raw_value)

        row = [
            ep.source_type,
            ep.source_name,
            f"[cyan]{conn_type}[/]",
            ep.db_type,
            ep.host,
            str(ep.port),
            f"[{tcp_style}]{ep.status}[/{tcp_style}]",
            latency_str,
        ]
        if has_lb:
            if ep.lb_name:
                lb_style = (
                    "green"  if ep.lb_status == 'OK' else
                    "yellow" if ep.lb_status == 'PENDING' else
                    "dim"
                )
                lb_icon  = "✅" if ep.lb_status == 'OK' else "⚠️" if ep.lb_status == 'PENDING' else "➖"
                row.append(f"[{lb_style}]{lb_icon} {ep.lb_name}[/{lb_style}]")
            else:
                row.append("[dim]—[/]")
        if has_db_probe:
            ps, pe = _probe_status_style(ep.db_probe_status)
            probe_label = ep.db_probe_status or '—'
            row.append(f"[{ps}]{pe} {probe_label}[/{ps}]")

        table.add_row(*row)

    console.print(table)

    if has_lb:
        console.print(
            "[dim]🔇 Load Balancer: K8s Service detectado como intermediario. "
            "OK = IP externa asignada. PENDING = LB en aprovisionamiento.[/]"
        )
    if has_db_probe:
        console.print(
            "[dim]🔬 DB Probe: protocolo nativo del motor. "
            "ALIVE = motor responde. FAILED = TCP OK pero BD no responde (posible falso positivo de LB).[/]"
        )


def print_summary(console: Console, report: ValidationReport):
    """Imprime resumen del reporte."""
    # Contar por severidad
    critical = sum(1 for f in report.findings if f.severity == Severity.CRITICAL)
    warnings = sum(1 for f in report.findings if f.severity == Severity.WARNING)
    info = sum(1 for f in report.findings if f.severity == Severity.INFO)
    
    # Contar conectividad (TCP + DB probe)
    conn_ok        = sum(1 for e in report.endpoints if e.status == "OK")
    conn_fail      = sum(1 for e in report.endpoints if e.status in ("TIMEOUT", "UNREACHABLE", "DB_PROBE_FAIL"))
    conn_probe_ok  = sum(1 for e in report.endpoints if e.db_probe_status == "ALIVE")
    conn_probe_fail= sum(1 for e in report.endpoints if e.db_probe_status == "FAILED")
    conn_skip      = sum(1 for e in report.endpoints if e.status == "SKIPPED")
    
    summary_parts = []
    summary_parts.append(f"[bold cyan]ConfigMaps:[/] {len(report.configmaps_found)} ✓ / {len(report.configmaps_missing)} ✗")
    summary_parts.append(f"[bold cyan]Secrets:[/] {len(report.secrets_found)} ✓ / {len(report.secrets_missing)} ✗")
    summary_parts.append(f"[bold red]Critical:[/] {critical}")
    summary_parts.append(f"[bold yellow]Warnings:[/] {warnings}")
    summary_parts.append(f"[bold cyan]Info:[/] {info}")
    if report.endpoints:
        summary_parts.append(f"[bold green]TCP OK:[/] {conn_ok}/{len(report.endpoints)}")
    if conn_probe_ok or conn_probe_fail:
        summary_parts.append(
            f"[bold green]DB Alive:[/] {conn_probe_ok} "
            f"[bold red]DB Failed:[/] {conn_probe_fail}"
        )
    
    console.print(Panel(
        " | ".join(summary_parts),
        title="📊 Resumen de Validación",
        border_style="blue"
    ))
    
    # Estado final
    if critical > 0 or len(report.configmaps_missing) > 0 or len(report.secrets_missing) > 0:
        console.print(Panel("❌ HAY PROBLEMAS CRÍTICOS QUE REQUIEREN ATENCIÓN", style="bold red"))
    elif warnings > 0 or conn_fail > 0:
        console.print(Panel("⚠️ HAY ADVERTENCIAS A REVISAR", style="yellow"))
    else:
        console.print(Panel("✅ TODAS LAS VALIDACIONES PASARON", style="green"))


def export_report(report: ValidationReport, filepath: str, format: str):
    """Exporta el reporte a archivo."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    if format == "json":
        export_data = {
            "metadata": {
                "project": report.project,
                "deployment": report.deployment,
                "namespace": report.namespace,
                "timestamp": report.timestamp,
                "version": __version__
            },
            "summary": {
                "configmaps_found": report.configmaps_found,
                "configmaps_missing": report.configmaps_missing,
                "secrets_found": report.secrets_found,
                "secrets_missing": report.secrets_missing
            },
            "findings": [
                {
                    "category": f.category,
                    "resource_type": f.resource_type,
                    "resource_name": f.resource_name,
                    "key": f.key,
                    "severity": f.severity.value,
                    "message": f.message,
                    "remediation": f.remediation
                }
                for f in report.findings
            ],
            "connectivity": [
                {
                    "source_type":      e.source_type,
                    "source_name":      e.source_name,
                    "host":             e.host,
                    "port":             e.port,
                    "db_type":          e.db_type,
                    "tcp_status":       e.status,
                    "tcp_message":      e.message,
                    "latency_ms":       e.latency_ms,
                    "lb_name":          e.lb_name   or None,
                    "lb_status":        e.lb_status or None,
                    "db_probe_status":  e.db_probe_status  or None,
                    "db_probe_message": e.db_probe_message or None,
                }
                for e in report.endpoints
            ]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    else:
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Type", "Category", "Resource", "Key", "Severity", "Message",
                "TCP_Status", "Host", "Port",
                "LB_Name", "LB_Status",
                "DB_Probe_Status", "DB_Probe_Message"
            ])
            for finding in report.findings:
                writer.writerow([
                    "Finding", finding.category, finding.resource_name, finding.key,
                    finding.severity.value, finding.message,
                    "", "", "", "", "", "", ""
                ])
            for ep in report.endpoints:
                writer.writerow([
                    "Connectivity", ep.source_type, ep.source_name, ep.key,
                    "", "", ep.status, ep.host, ep.port,
                    ep.lb_name or "", ep.lb_status or "",
                    ep.db_probe_status or "", ep.db_probe_message or ""
                ])


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    start_time = time.time()
    args = get_args()
    console = Console() if RICH_AVAILABLE else None
    
    if args.help:
        if RICH_AVAILABLE and console:
            console.print(Panel(
                "[bold]Deployment Validator[/]\n\n"
                "Valida ConfigMaps, Secrets y conectividad de un Deployment de Kubernetes.\n\n"
                "[cyan]Uso:[/]\n"
                "  python deployment_validator.py --deployment <nombre> [opciones]\n\n"
                "[cyan]Ejemplos:[/]\n"
                "  python deployment_validator.py -d my-app -n production\n"
                "  python deployment_validator.py -d my-app --validate secrets\n"
                "  python deployment_validator.py -d my-app -o json",
                title="Ayuda",
                border_style="cyan"
            ))
        return 0
    
    project_id = args.project
    cluster_id = args.cluster
    region = args.region
    deployment = args.deployment
    validate_type = args.validate
    
    # Banner inicial
    if RICH_AVAILABLE and console:
        console.print(Panel(
            f"🅿️ Proyecto: [bold white]{project_id}[/]\n"
            f"☸️ Cluster: [bold white]{cluster_id}[/] ({region})\n"
            f"🚀 Deployment: [bold white]{deployment}[/]\n"
            f"🔍 Validación: [bold white]{validate_type}[/]",
            title="🛡️ Deployment Validator",
            border_style="blue"
        ))
    else:
        print(f"Proyecto: {project_id} | Cluster: {cluster_id} | Deployment: {deployment}")
    
    # Configurar contexto kubectl
    if not configure_kubectl_context(project_id, cluster_id, region, console, args.debug):
        return 1
    
    # Obtener manifiesto del deployment
    if RICH_AVAILABLE and console:
        console.print("[dim]⏳ Obteniendo manifiesto del deployment...[/]")
    else:
        print("⏳ Obteniendo manifiesto del deployment...", flush=True)
    
    manifest = get_deployment_manifest(deployment, args.namespace, args.debug)
    if not manifest:
        msg = f"❌ No se pudo obtener el deployment '{deployment}'"
        if RICH_AVAILABLE and console:
            console.print(f"[red]{msg}[/]")
        else:
            print(msg)
        return 1
    
    # Extraer referencias
    namespace, service_account, configmap_refs, secret_refs = extract_resource_refs(manifest)
    
    if RICH_AVAILABLE and console:
        console.print(f"[dim]📍 Namespace: {namespace}[/]")
        console.print(f"[dim]👤 Service Account: {service_account}[/]")
        console.print(f"[dim]📄 ConfigMaps referenciados: {len(configmap_refs)}[/]")
        console.print(f"[dim]🔐 Secrets referenciados: {len(secret_refs)}[/]")
    else:
        print(f"✅ Deployment encontrado", flush=True)
        print(f"   📍 Namespace: {namespace}", flush=True)
        print(f"   👤 Service Account: {service_account}", flush=True)
        print(f"   📄 ConfigMaps: {len(configmap_refs)}", flush=True)
        print(f"   🔐 Secrets: {len(secret_refs)}", flush=True)
    
    # Crear reporte
    tz = ZoneInfo(args.timezone)
    report = ValidationReport(
        project=project_id,
        deployment=deployment,
        namespace=namespace,
        timestamp=datetime.now(tz).strftime(f"%Y-%m-%d %H:%M:%S ({args.timezone})")
    )
    
    all_endpoints: List[ConnectionEndpoint] = []
    
    # Validar ConfigMaps
    if validate_type in ("all", "configmaps"):
        if RICH_AVAILABLE and console:
            console.print("\n[bold cyan]━━━ Validando ConfigMaps ━━━[/]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"Analizando {len(configmap_refs)} ConfigMaps...", total=None)
                cm_endpoints = validate_configmaps(configmap_refs, namespace, report, args.debug)
                all_endpoints.extend(cm_endpoints)
            # Mostrar hallazgos de ConfigMaps
            cm_findings = [f for f in report.findings if f.resource_type == "ConfigMap"]
            if cm_findings:
                console.print(f"  [dim]📋 {len(report.configmaps_found)} encontrados, {len(report.configmaps_missing)} faltantes[/]")
                for finding in cm_findings:
                    emoji = get_severity_emoji(finding.severity)
                    style = get_severity_style(finding.severity)
                    console.print(f"  {emoji} [{style}]{finding.resource_name}[/]: {finding.message}")
            else:
                console.print(f"  [green]✅ {len(report.configmaps_found)} ConfigMaps validados sin problemas[/]")
            if cm_endpoints:
                console.print(f"  [dim]🔗 {len(cm_endpoints)} endpoints de conexión detectados[/]")
        else:
            print(f"\n📄 Validando {len(configmap_refs)} ConfigMaps...", flush=True)
            cm_endpoints = validate_configmaps(configmap_refs, namespace, report, args.debug)
            all_endpoints.extend(cm_endpoints)
    
    # Validar Secrets
    if validate_type in ("all", "secrets"):
        if RICH_AVAILABLE and console:
            console.print("\n[bold cyan]━━━ Validando Secrets ━━━[/]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"Analizando {len(secret_refs)} Secrets...", total=None)
                secret_endpoints = validate_secrets(secret_refs, namespace, report, args.debug)
                all_endpoints.extend(secret_endpoints)
            # Mostrar hallazgos de Secrets
            secret_findings = [f for f in report.findings if f.resource_type == "Secret"]
            if secret_findings:
                console.print(f"  [dim]📋 {len(report.secrets_found)} encontrados, {len(report.secrets_missing)} faltantes[/]")
                for finding in secret_findings:
                    emoji = get_severity_emoji(finding.severity)
                    style = get_severity_style(finding.severity)
                    console.print(f"  {emoji} [{style}]{finding.resource_name}/{finding.key}[/]: {finding.message}")
            else:
                console.print(f"  [green]✅ {len(report.secrets_found)} Secrets validados sin problemas[/]")
            if secret_endpoints:
                console.print(f"  [dim]🔗 {len(secret_endpoints)} endpoints de conexión detectados[/]")
        else:
            print(f"\n🔐 Validando {len(secret_refs)} Secrets...", flush=True)
            secret_endpoints = validate_secrets(secret_refs, namespace, report, args.debug)
            all_endpoints.extend(secret_endpoints)
    
    # Validar Conectividad
    if validate_type in ("all", "connectivity") and all_endpoints:
        if RICH_AVAILABLE and console:
            console.print("\n[bold cyan]━━━ Validando Conectividad ━━━[/]")
            console.print(f"  [dim]🔌 Probando {len(all_endpoints)} endpoints...[/]")
        else:
            print(f"\n🔌 Validando conectividad de {len(all_endpoints)} endpoints...", flush=True)
        validate_connectivity(
            all_endpoints, namespace, service_account,
            args.probe_image, args.timeout, console, args.debug,
            db_probe=args.db_probe,
        )
        # Mostrar resumen de conectividad
        if RICH_AVAILABLE and console:
            ok_count = sum(1 for e in all_endpoints if e.status == "OK")
            error_count = sum(1 for e in all_endpoints if e.status == "ERROR")
            timeout_count = sum(1 for e in all_endpoints if e.status == "TIMEOUT")
            probe_count = sum(1 for e in all_endpoints if e.db_probe_status)
            probe_fail = sum(1 for e in all_endpoints if e.db_probe_status == 'FAILED')
            if error_count > 0 or timeout_count > 0 or probe_fail > 0:
                probe_str = f" | [red]🔬 DB probe FAIL: {probe_fail}[/]" if probe_fail else ""
                console.print(
                    f"  [green]✅ OK: {ok_count}[/] | [red]❌ ERROR: {error_count}[/] | "
                    f"[yellow]⏱️ TIMEOUT: {timeout_count}[/]{probe_str}"
                )
            else:
                probe_str = f" (🔬 DB probe: {probe_count} confirmados)" if probe_count else ""
                console.print(f"  [green]✅ Todos los {ok_count} endpoints conectan correctamente{probe_str}[/]")
    
    report.endpoints = all_endpoints
    
    # Mostrar resultados
    if RICH_AVAILABLE and console:
        console.print()
        print_findings_table(console, report.findings, args.severity)
        console.print()
        print_connectivity_table(console, report.endpoints)
        console.print()
        print_summary(console, report)
    else:
        print(f"\nHallazgos: {len(report.findings)}")
        for f in report.findings:
            print(f"  [{f.severity.value}] {f.resource_type}/{f.resource_name}: {f.message}")
        print(f"\nEndpoints: {len(report.endpoints)}")
        for e in report.endpoints:
            probe_info = f" | DB probe: {e.db_probe_status}" if e.db_probe_status else ""
            print(f"  {e.host}:{e.port} -> {e.status}{probe_info}")
    
    # Exportar si se solicita
    if args.output:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        outcome_dir = os.path.join(script_dir, 'outcome')
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"deployment_validation_{deployment}_{timestamp}.{args.output}"
        filepath = os.path.join(outcome_dir, filename)
        export_report(report, filepath, args.output)
        if RICH_AVAILABLE and console:
            console.print(f"\n[bold green]📁 Reporte exportado: {filepath}[/]")
        else:
            print(f"Reporte exportado: {filepath}")
    
    # Tiempo de ejecución
    elapsed = time.time() - start_time
    if RICH_AVAILABLE and console:
        console.print(f"\n[dim]⏱️ Tiempo de ejecución: {elapsed:.2f}s[/]")
    
    # Exit code basado en hallazgos críticos
    critical_count = sum(1 for f in report.findings if f.severity == Severity.CRITICAL)
    return 1 if critical_count > 0 else 0


if __name__ == "__main__":
    exit(main())
