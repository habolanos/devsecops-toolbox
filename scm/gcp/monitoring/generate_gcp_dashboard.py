#!/usr/bin/env python3
"""
GCP Infrastructure Dashboard Generator
Genera un dashboard HTML interactivo a partir de archivos JSON consolidados de GCP Monitor.

El dashboard replica en HTML todas las dimensiones que muestra gcp_monitor.py en la
terminal mediante un sistema de pestañas (tabs):
  - Servicios Habilitados (resumen por proyecto)
  - Clusters GKE (capacidad, uso, versiones, pods)
  - Capacidad de Red GKE (subred, CIDRs, uso de IPs)
  - Instancias Cloud SQL (con conteo de bases de datos)
  - Instancias Compute Engine (specs y disco raiz)
  - Servicios Cloud Run (URL, limits, ingress)
  - Topics Pub/Sub
  - Inventario Completo (consolidado con filtros y postura de seguridad)

Cada tabla es interactiva: filtros por columna, ordenamiento por columna,
filtros globales, badges de color por estado y paginacion (50 filas + cargar mas).

Versión: 1.7.69
Fecha: 9 de Septiembre de 2026
Autor: Harold Adrian
"""

import json
import argparse
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Advertencia: pandas no disponible. Algunas funciones pueden ser limitadas.")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    # No imprimir advertencia aquí, se maneja en la función principal


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    'bg_dark': '#0f1419',
    'bg_card': '#1a1f26',
    'border': '#2d3748',
    'text_primary': '#e2e8f0',
    'text_secondary': '#a0aec0',
    'success': '#48bb78',
    'warning': '#ed8936',
    'danger': '#f56565',
    'info': '#4299e1',
    'gray': '#718096',
}

ENVIRONMENT_KEYWORDS = {
    'dev': ['dev', 'development'],
    'qa': ['qa', 'test', 'testing'],
    'stag': ['stag', 'stage', 'staging'],
    'prod': ['prod', 'production'],
}

# Especificaciones estimadas de RAM (GB) por vCPU para familias de maquinas comunes.
# Usado para estimar la capacidad total de clusters GKE e instancias Compute Engine
# a partir del tipo de maquina (misma logica que get_machine_specs de gcp_monitor.py).
MACHINE_GB_PER_CPU = {
    ('e2', 'standard'): 4.0,
    ('e2', 'highmem'): 8.0,
    ('e2', 'highcpu'): 1.0,
    ('n1', 'standard'): 3.75,
    ('n1', 'highmem'): 6.5,
    ('n1', 'highcpu'): 1.8,
    ('n2', 'standard'): 4.0,
    ('n2', 'highmem'): 8.0,
    ('n2', 'highcpu'): 0.5,
    ('n2d', 'standard'): 4.0,
    ('n2d', 'highmem'): 8.0,
    ('n2d', 'highcpu'): 0.5,
    ('n3', 'standard'): 4.0,
    ('n3', 'highmem'): 8.0,
    ('n3', 'highcpu'): 0.5,
    ('c2', 'standard'): 4.0,
    ('c2d', 'standard'): 4.0,
    ('c2d', 'highmem'): 8.0,
    ('c2d', 'highcpu'): 2.0,
    ('c3', 'standard'): 4.0,
    ('c3', 'highmem'): 8.0,
    ('c3', 'highcpu'): 2.0,
    ('c3d', 'standard'): 4.0,
    ('c3d', 'highmem'): 8.0,
    ('c3d', 'highcpu'): 1.0,
    ('t2d', 'standard'): 4.0,
    ('t2d', 'highmem'): 8.0,
    ('t2d', 'highcpu'): 2.0,
}

FIXED_MACHINE_SPECS = {
    'e2-medium': {'cpu': 2, 'memory': 4.0},
    'e2-small': {'cpu': 2, 'memory': 2.0},
    'e2-micro': {'cpu': 2, 'memory': 1.0},
    'f1-micro': {'cpu': 1, 'memory': 0.6},
    'g1-small': {'cpu': 1, 'memory': 1.7},
}

DASHBOARD_VERSION = '1.7.69'

# Tamano de pagina para la paginacion de tablas en el dashboard (JS).
PAGE_SIZE = 50


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════════════════════

def infer_environment(project_name: str) -> str:
    """Infiere el ambiente desde el nombre del proyecto."""
    if not project_name:
        return 'desconocido'

    project_lower = project_name.lower()
    for env, keywords in ENVIRONMENT_KEYWORDS.items():
        if any(keyword in project_lower for keyword in keywords):
            return env

    return 'desconocido'


def sanitize_value(value: Any, field_name: str = '') -> str:
    """Sanitiza valores sensibles antes de mostrar en HTML."""
    sensitive_patterns = [
        'cert', 'certificate', 'key', 'secret', 'password', 'token',
        'credential', 'auth', 'private', 'encrypted', 'blob'
    ]

    field_lower = field_name.lower()
    if any(pattern in field_lower for pattern in sensitive_patterns):
        return '***REDACTADO***'

    if isinstance(value, str):
        # Redactar IPs
        if any(c.isdigit() for c in value) and value.count('.') >= 3:
            return '***REDACTADO***'

        # Redactar URLs internas
        if 'http' in value.lower() or 'dns' in value.lower():
            return '***REDACTADO***'

    return str(value) if value is not None else 'N/A'


def safe_get(obj: Dict, path: str, default=None) -> Any:
    """Acceso seguro a diccionarios anidados."""
    try:
        keys = path.split('.')
        result = obj
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return default
        return result if result is not None else default
    except (KeyError, TypeError, AttributeError):
        return default


def format_pct(value: Any) -> str:
    """Formatea un porcentaje o devuelve N/A."""
    if value is None:
        return 'N/A'
    try:
        return "{:.1f}%".format(float(value))
    except (TypeError, ValueError):
        return 'N/A'


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE GKE (misma logica que gcp_monitor.py, sin modificarlo)
# ═══════════════════════════════════════════════════════════════════════════════

def get_machine_specs(machine_type: str) -> Dict[str, Any]:
    """Obtiene especificaciones estimadas de CPU y memoria para un tipo de maquina.

    Soporta tipos estandar ({familia}-{perfil}-{cpu}), tipos custom
    ({familia}-custom-{cpu}-{mem_mb}) y maquinas compartidas (e2-medium, etc.).
    """
    if not machine_type:
        return {'cpu': 0, 'memory': 0.0}

    machine_type = str(machine_type).strip()
    if '/' in machine_type:
        machine_type = machine_type.split('/')[-1]

    # Tipos personalizados: {familia}-custom-{cpu}-{memory_mb}
    custom_match = re.match(r'^([a-z0-9]+)-custom-(\d+)-(\d+)$', machine_type)
    if custom_match:
        return {'cpu': int(custom_match.group(2)),
                'memory': round(int(custom_match.group(3)) / 1024.0, 1)}

    # Tipos estandar: {familia}-{perfil}-{cpu}
    std_match = re.match(r'^(e2|n1|n2|n2d|n3|c2|c2d|c3|c3d|t2d)-(standard|highmem|highcpu)-(\d+)$',
                         machine_type)
    if std_match:
        family = std_match.group(1)
        profile = std_match.group(2)
        cpu = int(std_match.group(3))
        gb_per_cpu = MACHINE_GB_PER_CPU.get((family, profile))
        if gb_per_cpu:
            return {'cpu': cpu, 'memory': round(cpu * gb_per_cpu, 1)}

    if machine_type in FIXED_MACHINE_SPECS:
        return dict(FIXED_MACHINE_SPECS[machine_type])

    return {'cpu': 0, 'memory': 0.0}


def estimate_cluster_capacity(cluster: Dict[str, Any]) -> Tuple[Optional[int], Optional[float]]:
    """Estima la capacidad total (vCPU, GB de RAM) de un cluster GKE desde sus node pools.

    Devuelve (None, None) cuando no hay suficiente informacion para estimar.
    """
    pools = cluster.get('nodePools') or []
    cpu_total = 0
    memory_total = 0.0

    for pool in pools:
        if not isinstance(pool, dict):
            continue
        count = pool.get('initialNodeCount') or 0
        specs = get_machine_specs((pool.get('config') or {}).get('machineType', ''))
        if count and specs['cpu'] > 0:
            cpu_total += int(count) * specs['cpu']
            memory_total += count * specs['memory']

    if cpu_total <= 0:
        # Fallback: currentNodeCount con el machine type del primer pool
        node_count = cluster.get('currentNodeCount') or 0
        if pools and node_count:
            first_pool = pools[0] if isinstance(pools[0], dict) else {}
            specs = get_machine_specs((first_pool.get('config') or {}).get('machineType', ''))
            if specs['cpu'] > 0:
                cpu_total = int(node_count) * specs['cpu']
                memory_total = node_count * specs['memory']

    if cpu_total <= 0:
        return None, None
    return cpu_total, round(memory_total, 1)


def get_version_status(current_version: Any, release_channel: Optional[Dict]) -> str:
    """Determina el estado de la version del cluster (logica de gcp_monitor.py)."""
    if not current_version:
        return 'UNKNOWN'
    version_parts = str(current_version).split('.')
    if len(version_parts) >= 2 and version_parts[1].isdigit():
        minor_version = int(version_parts[1])
        if minor_version < 27:
            return 'OUTDATED'
        elif minor_version < 29:
            return 'UPDATE_AVAILABLE'
    if release_channel and release_channel.get('channel') == 'UNSPECIFIED':
        return 'NO_CHANNEL'
    return 'CURRENT'


def get_status_summary_text(cluster_status: str, version_status: str, autopilot: bool) -> str:
    """Semoforo SRE de clusters GKE en texto plano (logica de gcp_monitor.py)."""
    if cluster_status != 'RUNNING':
        return 'NOT_RUNNING'
    if version_status == 'OUTDATED':
        return 'OUTDATED'
    if version_status == 'UPDATE_AVAILABLE':
        return 'UPDATE'
    if version_status == 'NO_CHANNEL':
        return 'NO_CHANNEL'
    if autopilot:
        return 'AUTOPILOT'
    return 'HEALTHY'


def calculate_total_ips(cidr: Any) -> int:
    """Calcula el total de IPs disponibles en un rango CIDR."""
    if not cidr or not isinstance(cidr, str) or '/' not in cidr:
        return 0
    try:
        mask = int(cidr.split('/')[1])
        if mask < 0 or mask > 32:
            return 0
        return (2 ** (32 - mask)) - 2
    except (ValueError, IndexError):
        return 0


def get_ip_status(pods_pct: Optional[float], services_pct: Optional[float]) -> str:
    """Determina el estado de alerta por utilizacion de IPs (logica de gcp_monitor.py).

    Si no hay ningun porcentaje disponible devuelve N/A; si al menos uno esta
    disponible, evalua los umbrales con los datos existentes.
    """
    if pods_pct is None and services_pct is None:
        return 'N/A'
    if services_pct is not None and services_pct > 90:
        return 'CRITICAL'
    if pods_pct is not None and pods_pct > 80:
        return 'WARNING'
    return 'OK'


def compute_health_status(cpu_percent: Any, memory_percent: Any,
                          warning_threshold: float = 75.0,
                          critical_threshold: float = 90.0) -> str:
    """Estado de salud del cluster basado en CPU y memoria (umbrales de gcp_monitor.py)."""
    if cpu_percent is None or memory_percent is None:
        return 'SIN DATOS'
    try:
        cpu_pct = float(cpu_percent)
        memory_pct = float(memory_percent)
    except (TypeError, ValueError):
        return 'SIN DATOS'
    if cpu_pct <= 1:
        cpu_pct *= 100
    if memory_pct <= 1:
        memory_pct *= 100
    max_util = max(cpu_pct, memory_pct)
    if max_util >= critical_threshold:
        return 'CRÍTICO'
    if max_util >= warning_threshold:
        return 'ADVERTENCIA'
    return 'OK'


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZACIÓN DE RECURSOS (Inventario consolidado + postura de seguridad)
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_resources(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normaliza recursos heterogéneos a un modelo tabular común."""
    normalized = []
    resource_id = 0

    for project_id, proj_data in data.get('data', {}).items():
        # Cloud SQL
        for sql in proj_data.get('sql_instances', []) or []:
            normalized.append({
                'id': resource_id,
                'resource_type': 'Cloud SQL',
                'resource_name': safe_get(sql, 'name', 'N/A'),
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'region_or_zone': safe_get(sql, 'region', 'N/A'),
                'status': safe_get(sql, 'state', 'UNKNOWN'),
                'created_at': safe_get(sql, 'createTime', 'N/A'),
                'posture': evaluate_sql_posture(sql),
                'findings': evaluate_sql_findings(sql),
                'raw_data': sql
            })
            resource_id += 1

        # GKE
        for gke in proj_data.get('gke_clusters', []) or []:
            normalized.append({
                'id': resource_id,
                'resource_type': 'GKE',
                'resource_name': safe_get(gke, 'name', 'N/A'),
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'region_or_zone': safe_get(gke, 'location', 'N/A'),
                'status': safe_get(gke, 'status', 'UNKNOWN'),
                'created_at': safe_get(gke, 'createTime', 'N/A'),
                'posture': evaluate_gke_posture(gke),
                'findings': evaluate_gke_findings(gke),
                'raw_data': gke
            })
            resource_id += 1

        # Compute Engine
        for ce in proj_data.get('compute_instances', []) or []:
            normalized.append({
                'id': resource_id,
                'resource_type': 'Compute Engine',
                'resource_name': safe_get(ce, 'name', 'N/A'),
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'region_or_zone': safe_get(ce, 'zone', 'N/A').split('/')[-1] if safe_get(ce, 'zone') else 'N/A',
                'status': safe_get(ce, 'status', 'UNKNOWN'),
                'created_at': safe_get(ce, 'creationTimestamp', 'N/A'),
                'posture': evaluate_ce_posture(ce),
                'findings': evaluate_ce_findings(ce),
                'raw_data': ce
            })
            resource_id += 1

        # Cloud Run
        for cr in proj_data.get('cloud_run', []) or []:
            normalized.append({
                'id': resource_id,
                'resource_type': 'Cloud Run',
                'resource_name': safe_get(cr, 'metadata.name', safe_get(cr, 'name', 'N/A')),
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'region_or_zone': safe_get(cr, 'metadata.namespace', 'N/A'),
                'status': 'ACTIVE',
                'created_at': safe_get(cr, 'metadata.creationTimestamp', 'N/A'),
                'posture': 'Conforme',
                'findings': [],
                'raw_data': cr
            })
            resource_id += 1

        # Pub/Sub
        for ps in proj_data.get('pubsub_topics', []) or []:
            normalized.append({
                'id': resource_id,
                'resource_type': 'Pub/Sub',
                'resource_name': safe_get(ps, 'name', 'N/A').split('/')[-1],
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'region_or_zone': 'Global',
                'status': 'ACTIVE',
                'created_at': 'N/A',
                'posture': 'Conforme',
                'findings': [],
                'raw_data': ps
            })
            resource_id += 1

    return normalized


def _slim_resource(resource: Dict[str, Any]) -> Dict[str, Any]:
    """Proyeccion liviana de un recurso para embeber en el HTML (sin raw_data)."""
    return {
        'id': resource.get('id'),
        'resource_type': resource.get('resource_type'),
        'resource_name': resource.get('resource_name'),
        'project_id': resource.get('project_id'),
        'environment': resource.get('environment'),
        'region_or_zone': resource.get('region_or_zone'),
        'status': resource.get('status'),
        'posture': resource.get('posture'),
        'findings': resource.get('findings') or [],
    }


def evaluate_sql_posture(sql: Dict) -> str:
    """Evalúa la postura de Cloud SQL."""
    findings = evaluate_sql_findings(sql)
    if not findings:
        return 'Conforme'

    has_critical = any(f.get('severity') == 'Crítico' for f in findings)
    return 'Crítico' if has_critical else 'Advertencia'


def evaluate_sql_findings(sql: Dict) -> List[Dict]:
    """Evalúa hallazgos en Cloud SQL."""
    findings = []

    if safe_get(sql, 'state') != 'RUNNABLE':
        findings.append({'severity': 'Crítico', 'finding': f"Estado: {safe_get(sql, 'state')}"})

    if not safe_get(sql, 'settings.backupConfiguration.enabled', False):
        findings.append({'severity': 'Advertencia', 'finding': 'Backups deshabilitados'})

    if not safe_get(sql, 'settings.backupConfiguration.pointInTimeRecoveryEnabled', False):
        findings.append({'severity': 'Advertencia', 'finding': 'PITR deshabilitado'})

    if not safe_get(sql, 'settings.deletionProtectionEnabled', False):
        findings.append({'severity': 'Advertencia', 'finding': 'Protección contra eliminación deshabilitada'})

    if safe_get(sql, 'settings.ipConfiguration.ipv4Enabled', False):
        findings.append({'severity': 'Advertencia', 'finding': 'IPv4 habilitado'})

    if safe_get(sql, 'settings.ipConfiguration.requireSsl', False) is False:
        findings.append({'severity': 'Advertencia', 'finding': 'SSL no exigido'})

    return findings


def evaluate_gke_posture(gke: Dict) -> str:
    """Evalúa la postura de GKE."""
    findings = evaluate_gke_findings(gke)
    if not findings:
        return 'Conforme'

    has_critical = any(f.get('severity') == 'Crítico' for f in findings)
    return 'Crítico' if has_critical else 'Advertencia'


def evaluate_gke_findings(gke: Dict) -> List[Dict]:
    """Evalúa hallazgos en GKE."""
    findings = []

    if safe_get(gke, 'status') != 'RUNNING':
        findings.append({'severity': 'Crítico', 'finding': f"Estado: {safe_get(gke, 'status')}"})

    if not safe_get(gke, 'privateClusterConfig.enablePrivateNodes', False):
        findings.append({'severity': 'Advertencia', 'finding': 'Nodos privados deshabilitados'})

    if not safe_get(gke, 'shieldedNodes.enabled', False):
        findings.append({'severity': 'Advertencia', 'finding': 'Shielded Nodes deshabilitado'})

    if safe_get(gke, 'binaryAuthorization.evaluationMode') == 'DISABLED':
        findings.append({'severity': 'Advertencia', 'finding': 'Binary Authorization deshabilitado'})

    if safe_get(gke, 'databaseEncryption.state') == 'DECRYPTED':
        findings.append({'severity': 'Advertencia', 'finding': 'Cifrado de BD deshabilitado'})

    # Verificar node pools
    for pool in safe_get(gke, 'nodePools', []) or []:
        if not safe_get(pool, 'management.autoRepair', False):
            findings.append({'severity': 'Advertencia', 'finding': f"Pool {safe_get(pool, 'name')}: AutoRepair deshabilitado"})

        if not safe_get(pool, 'management.autoUpgrade', False):
            findings.append({'severity': 'Advertencia', 'finding': f"Pool {safe_get(pool, 'name')}: AutoUpgrade deshabilitado"})

    # Métricas de telemetría
    metrics_status = safe_get(gke, 'usage_metrics.status')
    if metrics_status == 'unavailable':
        findings.append({'severity': 'Info', 'finding': 'Telemetría no disponible'})

    return findings


def evaluate_ce_posture(ce: Dict) -> str:
    """Evalúa la postura de Compute Engine."""
    findings = evaluate_ce_findings(ce)
    if not findings:
        return 'Conforme'

    has_critical = any(f.get('severity') == 'Crítico' for f in findings)
    return 'Crítico' if has_critical else 'Advertencia'


def evaluate_ce_findings(ce: Dict) -> List[Dict]:
    """Evalúa hallazgos en Compute Engine."""
    findings = []

    if safe_get(ce, 'status') != 'RUNNING':
        findings.append({'severity': 'Crítico', 'finding': f"Estado: {safe_get(ce, 'status')}"})

    if not safe_get(ce, 'deletionProtection', False):
        findings.append({'severity': 'Advertencia', 'finding': 'Protección contra eliminación deshabilitada'})

    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE DIMENSIONES POR TAB (desde el JSON consolidado de gcp_monitor.py)
# ═══════════════════════════════════════════════════════════════════════════════

def _iter_projects(json_data: Dict[str, Any]):
    """Itera (project_id, proj_data) del JSON consolidado de forma segura."""
    for project_id, proj_data in (json_data.get('data', {}) or {}).items():
        if isinstance(proj_data, dict):
            yield project_id, proj_data


def build_services_rows(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye las filas del resumen de Servicios Habilitados por proyecto."""
    rows = []
    for project_id, proj_data in _iter_projects(json_data):
        services = proj_data.get('services')
        if services is None:
            services = proj_data.get('enabled_services')
        services = services or []

        enabled = sum(1 for svc in services
                     if isinstance(svc, dict) and svc.get('state', 'ENABLED') == 'ENABLED')
        total = len(services)

        if total and enabled == total:
            estado, estado_text = 'TODOS', 'Todos habilitados'
        elif enabled > 0:
            estado, estado_text = 'PARCIAL', '{} con estado distinto'.format(total - enabled)
        else:
            estado, estado_text = 'NINGUNO', 'Sin servicios'

        rows.append({
            'project_id': project_id,
            'environment': infer_environment(project_id),
            'resource_type': 'APIs',
            'enabled': enabled,
            'total': total,
            'estado': estado,
            'estado_text': estado_text,
            'status': 'ENABLED' if enabled else 'NONE',
        })
    return rows


def build_gke_rows(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye las filas de la tabla de Clusters GKE (metricas + enriquecimiento)."""
    rows = []
    for project_id, proj_data in _iter_projects(json_data):
        for cluster in proj_data.get('gke_clusters', []) or []:
            if not isinstance(cluster, dict):
                continue
            rows.append(_build_gke_row(project_id, cluster))
    return rows


def _build_gke_row(project_id: str, cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Construye una fila de cluster GKE con todas las dimensiones del monitor."""
    name = cluster.get('name', 'N/A') or 'N/A'
    location = cluster.get('location', 'N/A') or 'N/A'
    cluster_status = cluster.get('status', 'UNKNOWN') or 'UNKNOWN'
    master_version = cluster.get('currentMasterVersion', 'N/A') or 'N/A'
    release_channel_dict = cluster.get('releaseChannel') or {}
    release_channel = release_channel_dict.get('channel', 'UNSPECIFIED')
    autopilot = bool((cluster.get('autopilot') or {}).get('enabled', False))

    version_status = get_version_status(master_version, release_channel_dict)
    status_summary = get_status_summary_text(cluster_status, version_status, autopilot)

    # Capacidad estimada desde node pools + uso desde usage_metrics (si existe)
    cpu_total, memory_total = estimate_cluster_capacity(cluster)
    metrics = cluster.get('usage_metrics') or {}
    cpu_used_pct = metrics.get('cpu_used_percent')
    memory_used_pct = metrics.get('memory_used_percent')
    health = compute_health_status(cpu_used_pct, memory_used_pct)

    # Pods (disponible si el JSON fue enriquecido con ellos)
    pods_running = cluster.get('pods_running')
    pods_not_running = cluster.get('pods_not_running')

    return {
        'project_id': project_id,
        'environment': infer_environment(project_id),
        'resource_type': 'GKE',
        'cluster': name,
        'location': location,
        'node_count': cluster.get('currentNodeCount'),
        'cpu_total': '{} vCPU'.format(cpu_total) if cpu_total else 'N/A',
        'memory_total': '{} GB'.format(memory_total) if memory_total else 'N/A',
        'cpu_used': format_pct(cpu_used_pct),
        'memory_used': format_pct(memory_used_pct),
        'health': health,
        'release_channel': release_channel,
        'autopilot': 'Sí' if autopilot else 'No',
        'master_version': master_version,
        'version_status': version_status,
        'status_summary': status_summary,
        'pods': pods_running if pods_running is not None else 'N/A',
        'not_running': pods_not_running if pods_not_running is not None else 'N/A',
        'status': cluster_status,
    }


def build_network_rows(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye las filas de la tabla de Capacidad de Red de clusters GKE."""
    rows = []
    for project_id, proj_data in _iter_projects(json_data):
        for cluster in proj_data.get('gke_clusters', []) or []:
            if not isinstance(cluster, dict):
                continue
            rows.append(_build_network_row(project_id, cluster))
    return rows


def _build_network_row(project_id: str, cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Construye una fila de capacidad de red de un cluster GKE."""
    name = cluster.get('name', 'N/A') or 'N/A'
    location = cluster.get('location', 'N/A') or 'N/A'

    ip_policy = cluster.get('ipAllocationPolicy') or {}
    pods_cidr = ip_policy.get('clusterIpv4CidrBlock') or 'N/A'
    services_cidr = ip_policy.get('servicesIpv4CidrBlock') or 'N/A'

    network_config = cluster.get('networkConfig') or {}
    subnet = network_config.get('subnetwork') or cluster.get('subnetwork') or 'N/A'
    if '/' in str(subnet):
        subnet = str(subnet).split('/')[-1]

    pods_total = calculate_total_ips(pods_cidr)
    services_total = calculate_total_ips(services_cidr)

    # Uso de IPs (disponible si el JSON fue enriquecido con pods_running/services_used)
    pods_used = cluster.get('pods_running')
    services_used = None
    for key in ('services_used', 'services_count', 'services_used_count'):
        if cluster.get(key) is not None:
            services_used = cluster.get(key)
            break

    pods_pct = (pods_used / pods_total * 100) if (pods_used is not None and pods_total > 0) else None
    services_pct = (services_used / services_total * 100) if (services_used is not None and services_total > 0) else None

    if pods_total > 0 and pods_used is not None:
        pods_ips = '{}/{} ({:.2f}%)'.format(pods_used, pods_total, pods_pct)
    else:
        pods_ips = 'N/A'

    if services_total > 0 and services_used is not None:
        services_ips = '{}/{} ({:.2f}%)'.format(services_used, services_total, services_pct)
    else:
        services_ips = 'N/A'

    ip_status = get_ip_status(pods_pct, services_pct)

    return {
        'project_id': project_id,
        'environment': infer_environment(project_id),
        'resource_type': 'GKE',
        'cluster': name,
        'location': location,
        'subnet': subnet,
        'pods_cidr': pods_cidr,
        'services_cidr': services_cidr,
        'pods_ips': pods_ips,
        'services_ips': services_ips,
        'ip_status': ip_status,
        'status': ip_status,
    }


def _sql_database_count(instance: Dict[str, Any]) -> Optional[int]:
    """Obtiene el conteo de bases de datos de una instancia Cloud SQL del JSON.

    Busca el campo 'databases' (lista o numero) o claves de conteo equivalentes
    que pueda haber agregado gcp_monitor.py al exportar.
    """
    if 'databases' in instance:
        databases = instance.get('databases')
        if isinstance(databases, list):
            return len(databases)
        if isinstance(databases, bool):
            return None
        if isinstance(databases, (int, float)):
            return int(databases)
    for key in ('database_count', 'databases_count', 'db_count', 'dbs'):
        value = instance.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def build_sql_rows(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye las filas de la tabla de Instancias Cloud SQL (con BDs)."""
    rows = []
    for project_id, proj_data in _iter_projects(json_data):
        for instance in proj_data.get('sql_instances', []) or []:
            if not isinstance(instance, dict):
                continue
            settings = instance.get('settings') or {}
            state = instance.get('state', 'UNKNOWN') or 'UNKNOWN'
            databases = _sql_database_count(instance)
            rows.append({
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'resource_type': 'Cloud SQL',
                'name': instance.get('name', 'N/A') or 'N/A',
                'state': state,
                'databaseVersion': instance.get('databaseVersion', 'N/A') or 'N/A',
                'tier': settings.get('tier', 'N/A') or 'N/A',
                'disk_gb': settings.get('dataDiskSizeGb', 'N/A'),
                'databases': databases if databases is not None else 'N/A',
                'status': state,
            })
    return rows


def build_compute_rows(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye las filas de la tabla de Instancias Compute Engine."""
    rows = []
    for project_id, proj_data in _iter_projects(json_data):
        for vm in proj_data.get('compute_instances', []) or []:
            if not isinstance(vm, dict):
                continue

            machine = str(vm.get('machineType') or '').split('/')[-1] or 'N/A'
            zone = str(vm.get('zone') or '').split('/')[-1] or 'N/A'
            specs = get_machine_specs(machine)
            cpus = specs['cpu'] if specs['cpu'] > 0 else 'N/A'
            memory = '{} GB'.format(specs['memory']) if specs['memory'] > 0 else 'N/A'

            # Disco raiz (boot disk)
            root_disk = 'N/A'
            disks = vm.get('disks') or []
            if disks:
                boot_disk = next((d for d in disks if isinstance(d, dict) and d.get('boot')), disks[0])
                if isinstance(boot_disk, dict):
                    disk_gb = boot_disk.get('sizeGb', 'N/A')
                    root_disk = '{} GB'.format(disk_gb) if disk_gb != 'N/A' else 'N/A'

            status = vm.get('status', 'UNKNOWN') or 'UNKNOWN'
            rows.append({
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'resource_type': 'Compute Engine',
                'name': vm.get('name', 'N/A') or 'N/A',
                'status': status,
                'machine_type': machine,
                'zone': zone,
                'cpus': cpus,
                'memory': memory,
                'root_disk': root_disk,
            })
    return rows


def build_run_rows(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye las filas de la tabla de Servicios Cloud Run."""
    rows = []
    for project_id, proj_data in _iter_projects(json_data):
        for svc in proj_data.get('cloud_run', []) or []:
            if not isinstance(svc, dict):
                continue

            metadata = svc.get('metadata') or {}
            spec = svc.get('spec') or {}
            template = spec.get('template') or {}
            tspec = template.get('spec') or {}
            containers = tspec.get('containers') or []
            annotations = metadata.get('annotations') or {}

            cpu_limit = 'N/A'
            mem_limit = 'N/A'
            if containers and isinstance(containers[0], dict):
                limits = (containers[0].get('resources') or {}).get('limits') or {}
                cpu_limit = limits.get('cpu', 'N/A')
                mem_limit = limits.get('memory', 'N/A')

            rows.append({
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'resource_type': 'Cloud Run',
                'name': metadata.get('name', 'N/A') or 'N/A',
                'region': metadata.get('namespace', 'N/A') or 'N/A',
                'url': (svc.get('status') or {}).get('url') or 'N/A',
                'concurrency': tspec.get('containerConcurrency', 'N/A'),
                'cpu_limit': cpu_limit,
                'mem_limit': mem_limit,
                'ingress': annotations.get('run.googleapis.com/ingress', 'all'),
                'status': 'ACTIVE',
            })
    return rows


def build_pubsub_rows(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye las filas de la tabla de Topics Pub/Sub."""
    rows = []
    for project_id, proj_data in _iter_projects(json_data):
        for topic in proj_data.get('pubsub_topics', []) or []:
            if not isinstance(topic, dict):
                continue
            name = topic.get('name') or 'N/A'
            if '/' in str(name):
                name = str(name).split('/')[-1]
            rows.append({
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'resource_type': 'Pub/Sub',
                'name': name,
                'status': 'ACTIVE',
            })
    return rows


def _to_int(value: Any) -> Optional[int]:
    """Convierte un valor numerico (o string numerico) a int de forma segura."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_kpis(json_data: Dict[str, Any], resources: List[Dict[str, Any]],
               services_rows: List[Dict[str, Any]], gke_rows: List[Dict[str, Any]],
               sql_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula los KPIs del dashboard (existentes + servicios habilitados, BDs y pods)."""
    summary = json_data.get('summary', {}) or {}
    data = json_data.get('data', {}) or {}

    def _count(key: str) -> int:
        return sum(len((d or {}).get(key) or []) for d in data.values())

    def _pick(summary_key: str, fallback: Any) -> Any:
        value = summary.get(summary_key)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else fallback

    total_enabled = 0
    for row in services_rows:
        value = _to_int(row.get('enabled'))
        if value is not None:
            total_enabled += value

    total_databases = 0
    for row in sql_rows:
        value = _to_int(row.get('databases'))
        if value is not None:
            total_databases += value

    total_pods = 0
    for row in gke_rows:
        value = _to_int(row.get('pods'))
        if value is not None:
            total_pods += value

    return {
        'total_projects': _pick('total_projects', len(data)),
        'total_resources': len(resources),
        'total_enabled_services': total_enabled,
        'total_gke_clusters': int(_pick('total_gke_clusters', _count('gke_clusters'))),
        'total_sql_instances': int(_pick('total_sql_instances', _count('sql_instances'))),
        'total_compute_instances': int(_pick('total_compute_instances', _count('compute_instances'))),
        'total_cloud_run_services': int(_pick('total_cloud_run_services', _count('cloud_run'))),
        'total_pubsub_topics': int(_pick('total_pubsub_topics', _count('pubsub_topics'))),
        'total_databases': total_databases,
        'total_pods': total_pods,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _json_for_html(obj: Any) -> str:
    """Serializa a JSON seguro para embeber dentro de un tag <script>."""
    return json.dumps(obj, ensure_ascii=False, default=str).replace('</', '<\\/')


def _css_variables() -> str:
    """Genera las variables CSS a partir del diccionario COLORS."""
    return (
        ':root {\n'
        '    --bg-dark: ' + COLORS['bg_dark'] + ';\n'
        '    --bg-card: ' + COLORS['bg_card'] + ';\n'
        '    --border: ' + COLORS['border'] + ';\n'
        '    --text-primary: ' + COLORS['text_primary'] + ';\n'
        '    --text-secondary: ' + COLORS['text_secondary'] + ';\n'
        '    --success: ' + COLORS['success'] + ';\n'
        '    --warning: ' + COLORS['warning'] + ';\n'
        '    --danger: ' + COLORS['danger'] + ';\n'
        '    --info: ' + COLORS['info'] + ';\n'
        '    --gray: ' + COLORS['gray'] + ';\n'
        '}\n'
    )


_DASHBOARD_CSS = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-primary);
    line-height: 1.6;
}

.container {
    max-width: 1500px;
    margin: 0 auto;
    padding: 20px;
}

header {
    margin-bottom: 30px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 20px;
}

h1 {
    font-size: 2.2em;
    margin-bottom: 10px;
    color: var(--info);
}

.header-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    color: var(--text-secondary);
    font-size: 0.9em;
}

.filters {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.filters h3 {
    color: var(--info);
    margin-bottom: 15px;
    font-size: 1.05em;
}

.filter-group {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 15px;
}

.filter-label {
    display: block;
    margin-bottom: 5px;
    font-size: 0.85em;
    color: var(--text-secondary);
}

select, input {
    background-color: var(--bg-dark);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 10px;
    font-size: 0.9em;
    width: 100%;
}

select:focus, input:focus {
    outline: none;
    border-color: var(--info);
    box-shadow: 0 0 5px rgba(66, 153, 225, 0.3);
}

.btn-reset {
    background-color: var(--info);
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    cursor: pointer;
    font-size: 0.9em;
    transition: background-color 0.3s ease;
    width: 100%;
}

.btn-reset:hover {
    background-color: #3182ce;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
}

.kpi-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.kpi-card:hover {
    border-color: var(--info);
    box-shadow: 0 0 10px rgba(66, 153, 225, 0.2);
}

.kpi-label {
    color: var(--text-secondary);
    font-size: 0.78em;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.kpi-value {
    font-size: 1.9em;
    font-weight: bold;
    color: var(--info);
}

.tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 24px;
}

.tab {
    background-color: var(--bg-card);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 8px 16px;
    cursor: pointer;
    font-size: 0.88em;
    transition: all 0.2s ease;
}

.tab:hover {
    border-color: var(--info);
    color: var(--text-primary);
}

.tab.active {
    background-color: rgba(66, 153, 225, 0.15);
    border-color: var(--info);
    color: var(--info);
    font-weight: 600;
}

.tab-count {
    background-color: rgba(66, 153, 225, 0.15);
    border-radius: 10px;
    padding: 1px 8px;
    font-size: 0.8em;
    margin-left: 6px;
    color: var(--info);
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

.table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    background-color: var(--bg-card);
}

table.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88em;
}

table.data-table th {
    background-color: var(--bg-dark);
    padding: 12px;
    text-align: left;
    font-weight: 600;
    color: var(--info);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
}

table.data-table th .th-label {
    cursor: pointer;
    user-select: none;
}

table.data-table th .th-label:hover {
    text-decoration: underline;
}

table.data-table th.sorted .th-label {
    color: var(--text-primary);
}

.sort-indicator {
    margin-left: 4px;
    font-size: 0.8em;
    color: var(--info);
}

.filter-row th {
    padding: 6px 8px;
    background-color: var(--bg-dark);
    border-bottom: 1px solid var(--border);
}

.filter-row input.col-filter {
    width: 100%;
    min-width: 70px;
    padding: 6px 8px;
    font-size: 0.82em;
    background-color: var(--bg-dark);
}

table.data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    max-width: 340px;
    overflow: hidden;
    text-overflow: ellipsis;
}

table.data-table tbody tr:hover td {
    background-color: rgba(66, 153, 225, 0.08);
}

.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.empty-row {
    text-align: center;
    color: var(--text-secondary);
    padding: 30px !important;
    white-space: normal !important;
}

.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.82em;
    font-weight: 500;
    white-space: nowrap;
}

.badge-ok {
    background-color: rgba(72, 187, 120, 0.2);
    color: var(--success);
}

.badge-warn {
    background-color: rgba(237, 137, 54, 0.2);
    color: var(--warning);
}

.badge-bad {
    background-color: rgba(245, 101, 101, 0.2);
    color: var(--danger);
}

.badge-info {
    background-color: rgba(66, 153, 225, 0.2);
    color: var(--info);
}

.badge-muted {
    background-color: rgba(113, 128, 150, 0.2);
    color: var(--gray);
}

.table-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 12px 0 30px 0;
    flex-wrap: wrap;
    gap: 10px;
}

.row-count {
    color: var(--text-secondary);
    font-size: 0.85em;
}

.load-more {
    background-color: var(--bg-card);
    color: var(--info);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 8px 16px;
    cursor: pointer;
    font-size: 0.85em;
    transition: all 0.2s ease;
}

.load-more:hover {
    border-color: var(--info);
}

.url-link {
    color: var(--info);
    text-decoration: none;
}

.url-link:hover {
    text-decoration: underline;
}

.findings-link {
    color: var(--info);
    text-decoration: underline;
    cursor: pointer;
}

.muted {
    color: var(--gray);
}

.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    z-index: 1000;
    overflow-y: auto;
}

.modal-content {
    background-color: var(--bg-card);
    margin: 50px auto;
    padding: 30px;
    border-radius: 8px;
    max-width: 640px;
    border: 1px solid var(--border);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.modal-close {
    background-color: var(--danger);
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    cursor: pointer;
}

.finding-item {
    padding: 15px;
    margin-bottom: 10px;
    border-radius: 4px;
}

.footer {
    text-align: center;
    color: var(--text-secondary);
    font-size: 0.85em;
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
}

@media (max-width: 768px) {
    .kpi-grid {
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    }

    h1 {
        font-size: 1.6em;
    }

    .header-meta {
        flex-direction: column;
        gap: 5px;
    }
}
"""

# Nota: el JS se define como cadena plana (sin f-strings) para evitar el escape de
# llaves; los datos dinamicos se inyectan en un <script> previo (var DASH = ...).
_DASHBOARD_JS = r"""
var PAGE_SIZE = 50;
var activeTab = 'servicios';
var tabState = {};

var BADGE_CLASSES = {
    'RUNNING': 'ok', 'RUNNABLE': 'ok', 'ACTIVE': 'ok', 'ENABLED': 'ok',
    'OK': 'ok', 'HEALTHY': 'ok', 'CURRENT': 'ok', 'AUTOPILOT': 'ok',
    'CONFORME': 'ok', 'TODOS': 'ok', 'SI': 'ok', 'SÍ': 'ok',
    'STOPPED': 'bad', 'TERMINATED': 'bad', 'SUSPENDED': 'bad', 'CRITICAL': 'bad',
    'OUTDATED': 'bad', 'NOT_RUNNING': 'bad', 'NINGUNO': 'bad',
    'CRITICO': 'bad', 'CRÍTICO': 'bad',
    'WARNING': 'warn', 'ADVERTENCIA': 'warn', 'UPDATE': 'warn',
    'UPDATE_AVAILABLE': 'warn', 'PARCIAL': 'warn',
    'NO_CHANNEL': 'info',
    'N/A': 'muted', 'SIN_DATOS': 'muted', 'UNKNOWN': 'muted', 'NO': 'muted'
};

var TABS = {
    servicios: {
        label: 'Servicios Habilitados',
        dataKey: 'services',
        columns: [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'enabled', label: 'Habilitados', right: true },
            { key: 'estado_text', label: 'Estado', badge: 'estado' }
        ]
    },
    gke: {
        label: 'Clusters GKE',
        dataKey: 'gke',
        columns: [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'cluster', label: 'Cluster' },
            { key: 'location', label: 'Ubicación' },
            { key: 'cpu_total', label: 'CPU Total', right: true },
            { key: 'memory_total', label: 'Memoria Total', right: true },
            { key: 'cpu_used', label: 'CPU Prom.', right: true },
            { key: 'memory_used', label: 'Memoria Prom.', right: true },
            { key: 'health', label: 'Estado', badge: true },
            { key: 'release_channel', label: 'Release Channel' },
            { key: 'autopilot', label: 'Autopilot', badge: true },
            { key: 'master_version', label: 'Master Version' },
            { key: 'version_status', label: 'Version Status', badge: true },
            { key: 'status_summary', label: 'Status Summary', badge: true },
            { key: 'pods', label: 'Pods', right: true },
            { key: 'not_running', label: 'Not Running', right: true, danger: true }
        ]
    },
    red: {
        label: 'Capacidad de Red GKE',
        dataKey: 'network',
        columns: [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'cluster', label: 'Cluster' },
            { key: 'location', label: 'Ubicación' },
            { key: 'subnet', label: 'Subred' },
            { key: 'pods_cidr', label: 'CIDR Pods' },
            { key: 'services_cidr', label: 'CIDR Services' },
            { key: 'pods_ips', label: 'Pods IPs' },
            { key: 'services_ips', label: 'Services IPs' },
            { key: 'ip_status', label: 'Estado', badge: true }
        ]
    },
    sql: {
        label: 'Instancias Cloud SQL',
        dataKey: 'sql',
        columns: [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'name', label: 'Nombre' },
            { key: 'state', label: 'Estado', badge: true },
            { key: 'databaseVersion', label: 'Versión' },
            { key: 'tier', label: 'Tier' },
            { key: 'disk_gb', label: 'Disco (GB)', right: true },
            { key: 'databases', label: 'BDs', right: true }
        ]
    },
    compute: {
        label: 'Instancias Compute Engine',
        dataKey: 'compute',
        columns: [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'name', label: 'Nombre' },
            { key: 'status', label: 'Estado', badge: true },
            { key: 'machine_type', label: 'Tipo' },
            { key: 'zone', label: 'Zona' },
            { key: 'cpus', label: 'CPUs', right: true },
            { key: 'memory', label: 'Memoria', right: true },
            { key: 'root_disk', label: 'Disco Raíz', right: true }
        ]
    },
    run: {
        label: 'Servicios Cloud Run',
        dataKey: 'run',
        columns: [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'name', label: 'Nombre' },
            { key: 'region', label: 'Región' },
            { key: 'url', label: 'URL', type: 'url' },
            { key: 'concurrency', label: 'Concurrencia', right: true },
            { key: 'cpu_limit', label: 'CPU Lim', right: true },
            { key: 'mem_limit', label: 'Mem Lim', right: true },
            { key: 'ingress', label: 'Ingress' }
        ]
    },
    pubsub: {
        label: 'Topics Pub/Sub',
        dataKey: 'pubsub',
        columns: [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'name', label: 'Nombre' }
        ]
    },
    inventario: {
        label: 'Inventario Completo',
        dataKey: 'resources',
        columns: [
            { key: 'resource_type', label: 'Tipo' },
            { key: 'resource_name', label: 'Nombre' },
            { key: 'project_id', label: 'Proyecto' },
            { key: 'environment', label: 'Ambiente' },
            { key: 'region_or_zone', label: 'Región/Zona' },
            { key: 'status', label: 'Estado', badge: true },
            { key: 'posture', label: 'Postura', badge: true },
            { key: 'findings', label: 'Hallazgos', type: 'findings' }
        ]
    }
};

function stateFor(tabId) {
    if (!tabState[tabId]) {
        tabState[tabId] = { sortKey: null, sortDir: 1, visible: PAGE_SIZE, colFilters: {} };
    }
    return tabState[tabId];
}

var AMP = String.fromCharCode(38); /* '&' construido sin entidad HTML */

function esc(s) {
    return String(s === null || s === undefined ? '' : s)
        .replace(/&/g, AMP + 'amp;')
        .replace(/</g, AMP + 'lt;')
        .replace(/>/g, AMP + 'gt;')
        .replace(/"/g, AMP + 'quot;')
        .replace(/'/g, AMP + '#39;');
}

function isMissing(v) {
    return v === null || v === undefined || v === 'N/A' || v === '' ||
        (typeof v === 'number' && isNaN(v));
}

function parseNumeric(v) {
    if (typeof v === 'number') return v;
    if (typeof v !== 'string') return null;
    var m = v.match(/-?\d+(\.\d+)?/);
    return m ? parseFloat(m[0]) : null;
}

function badgeClass(value) {
    var key = String(value === null || value === undefined ? '' : value).trim().toUpperCase().replace(/\s+/g, '_');
    return BADGE_CLASSES[key] || 'muted';
}

function renderCell(row, col) {
    var value = row[col.key];
    if (col.type === 'findings') {
        var count = (row.findings && row.findings.length) ? row.findings.length : 0;
        return '<a href="javascript:void(0)" class="findings-link" onclick="showFindings(' + row.id + ')">' + count + ' hallazgo(s)</a>';
    }
    if (col.type === 'url') {
        if (isMissing(value)) return '<span class="muted">N/A</span>';
        return '<a class="url-link" href="' + esc(value) + '" target="_blank" rel="noopener noreferrer">' + esc(value) + '</a>';
    }
    if (col.danger) {
        if (isMissing(value)) return '<span class="muted">N/A</span>';
        var n = Number(value);
        if (!isNaN(n) && n > 0) return '<span class="status-badge badge-bad">' + esc(value) + '</span>';
        return esc(value);
    }
    if (col.badge) {
        if (isMissing(value)) return '<span class="muted">N/A</span>';
        var classValue = (typeof col.badge === 'string') ? row[col.badge] : value;
        return '<span class="status-badge badge-' + badgeClass(classValue) + '">' + esc(value) + '</span>';
    }
    if (isMissing(value)) return '<span class="muted">N/A</span>';
    return esc(value);
}

function rowMatchesSearch(row, search) {
    for (var key in row) {
        if (!Object.prototype.hasOwnProperty.call(row, key)) continue;
        var value = row[key];
        if (typeof value === 'string' || typeof value === 'number') {
            if (String(value).toLowerCase().indexOf(search) !== -1) return true;
        }
    }
    return false;
}

function getFilteredRows(tabId) {
    var tab = TABS[tabId];
    var rows = DASH[tab.dataKey] || [];
    var project = document.getElementById('filterProject').value;
    var environment = document.getElementById('filterEnvironment').value;
    var resourceType = document.getElementById('filterResourceType').value;
    var status = document.getElementById('filterStatus').value;
    var search = document.getElementById('filterSearch').value.trim().toLowerCase();
    var st = stateFor(tabId);
    return rows.filter(function (row) {
        if (project && row.project_id !== project) return false;
        if (environment && row.environment !== environment) return false;
        if (resourceType && row.resource_type !== resourceType) return false;
        if (status && row.status !== status) return false;
        if (search && !rowMatchesSearch(row, search)) return false;
        var colFilters = st.colFilters;
        for (var key in colFilters) {
            if (!Object.prototype.hasOwnProperty.call(colFilters, key)) continue;
            var f = colFilters[key];
            if (f) {
                var cellValue = String(row[key] === null || row[key] === undefined ? '' : row[key]).toLowerCase();
                if (cellValue.indexOf(String(f).toLowerCase()) === -1) return false;
            }
        }
        return true;
    });
}

function compareValues(a, b) {
    var aMiss = isMissing(a);
    var bMiss = isMissing(b);
    if (aMiss && bMiss) return 0;
    if (aMiss) return 1;
    if (bMiss) return -1;
    if (typeof a === 'number' && typeof b === 'number') return a - b;
    var na = parseNumeric(a);
    var nb = parseNumeric(b);
    if (na !== null && nb !== null) return na - nb;
    var sa = String(a).toLowerCase();
    var sb = String(b).toLowerCase();
    if (sa < sb) return -1;
    if (sa > sb) return 1;
    return 0;
}

function sortRows(rows, tabId) {
    var st = stateFor(tabId);
    if (!st.sortKey) return rows;
    var key = st.sortKey;
    var dir = st.sortDir;
    return rows.slice().sort(function (a, b) {
        return compareValues(a[key], b[key]) * dir;
    });
}

function buildTabSkeleton(tabId) {
    var container = document.getElementById('tab-' + tabId);
    if (!container) return;
    var tab = TABS[tabId];
    var html = '<div class="table-wrap"><table class="data-table">';
    html += '<thead><tr class="header-row">';
    tab.columns.forEach(function (col) {
        html += '<th data-key="' + esc(col.key) + '"><span class="th-label" onclick="sortBy(\'' + col.key + '\')" title="Clic para ordenar">' + esc(col.label) + '</span><span class="sort-indicator"></span></th>';
    });
    html += '</tr><tr class="filter-row">';
    tab.columns.forEach(function (col) {
        html += '<th><input type="text" class="col-filter" placeholder="Filtrar..." oninput="onColumnFilter(this, \'' + tabId + '\', \'' + col.key + '\')"></th>';
    });
    html += '</tr></thead><tbody></tbody></table></div>';
    html += '<div class="table-footer"><span class="row-count"></span><span class="load-more-slot"></span></div>';
    container.innerHTML = html;
}

function refreshTab(tabId) {
    var container = document.getElementById('tab-' + tabId);
    if (!container) return;
    var tab = TABS[tabId];
    var st = stateFor(tabId);
    var filtered = sortRows(getFilteredRows(tabId), tabId);

    var headers = container.querySelectorAll('.header-row th');
    for (var i = 0; i < headers.length; i++) {
        var th = headers[i];
        var key = th.getAttribute('data-key');
        var indicator = th.querySelector('.sort-indicator');
        if (st.sortKey === key) {
            th.classList.add('sorted');
            indicator.textContent = (st.sortDir === 1) ? '▲' : '▼';
        } else {
            th.classList.remove('sorted');
            indicator.textContent = '';
        }
    }

    var html = '';
    var visible = filtered.slice(0, st.visible);
    for (var j = 0; j < visible.length; j++) {
        var row = visible[j];
        html += '<tr>';
        tab.columns.forEach(function (col) {
            html += '<td' + (col.right ? ' class="num"' : '') + '>' + renderCell(row, col) + '</td>';
        });
        html += '</tr>';
    }
    if (!filtered.length) {
        html += '<tr><td class="empty-row" colspan="' + tab.columns.length + '">Sin resultados para los filtros aplicados</td></tr>';
    }
    container.querySelector('tbody').innerHTML = html;

    var shown = Math.min(st.visible, filtered.length);
    container.querySelector('.row-count').textContent = 'Mostrando ' + shown + ' de ' + filtered.length + ' fila(s)';

    var slot = container.querySelector('.load-more-slot');
    if (filtered.length > st.visible) {
        var remaining = filtered.length - st.visible;
        slot.innerHTML = '<button class="load-more" onclick="loadMore(\'' + tabId + '\')">⬇ Cargar más (' + remaining + ' restantes)</button>';
    } else {
        slot.innerHTML = '';
    }
}

function showTab(tabId) {
    activeTab = tabId;
    var buttons = document.querySelectorAll('.tabs .tab');
    for (var i = 0; i < buttons.length; i++) {
        buttons[i].classList.toggle('active', buttons[i].getAttribute('data-tab') === tabId);
    }
    var contents = document.querySelectorAll('.tab-content');
    for (var j = 0; j < contents.length; j++) {
        contents[j].classList.toggle('active', contents[j].id === 'tab-' + tabId);
    }
}

function applyFilters() {
    for (var tabId in TABS) {
        if (!Object.prototype.hasOwnProperty.call(TABS, tabId)) continue;
        stateFor(tabId).visible = PAGE_SIZE;
        refreshTab(tabId);
    }
}

function resetFilters() {
    document.getElementById('filterProject').value = '';
    document.getElementById('filterEnvironment').value = '';
    document.getElementById('filterResourceType').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterSearch').value = '';
    for (var tabId in TABS) {
        if (!Object.prototype.hasOwnProperty.call(TABS, tabId)) continue;
        stateFor(tabId).colFilters = {};
        var inputs = document.querySelectorAll('#tab-' + tabId + ' .col-filter');
        for (var i = 0; i < inputs.length; i++) inputs[i].value = '';
    }
    applyFilters();
}

function loadMore(tabId) {
    var st = stateFor(tabId);
    st.visible += PAGE_SIZE;
    refreshTab(tabId);
}

function onColumnFilter(input, tabId, key) {
    var st = stateFor(tabId);
    st.colFilters[key] = input.value;
    st.visible = PAGE_SIZE;
    refreshTab(tabId);
}

function sortBy(colKey) {
    var st = stateFor(activeTab);
    if (st.sortKey === colKey) {
        st.sortDir = (st.sortDir === 1) ? -1 : 1;
    } else {
        st.sortKey = colKey;
        st.sortDir = 1;
    }
    refreshTab(activeTab);
}

function kpiGo(tabId, resourceType) {
    showTab(tabId);
    var sel = document.getElementById('filterResourceType');
    if (sel) sel.value = resourceType || '';
    applyFilters();
}

function filterByProject(value) {
    document.getElementById('filterProject').value = value;
    applyFilters();
}

function filterByResourceType(value) {
    document.getElementById('filterResourceType').value = value;
    applyFilters();
}

function showFindings(id) {
    var resource = null;
    var list = DASH.resources || [];
    for (var i = 0; i < list.length; i++) {
        if (list[i].id === id) { resource = list[i]; break; }
    }
    if (!resource) return;
    var findings = resource.findings || [];

    var html = '<div style="margin-bottom: 20px;">';
    html += '<h3 style="color: var(--info); margin-top: 0;">🔍 ' + esc(resource.resource_name) + '</h3>';
    html += '<p style="color: var(--text-secondary); margin: 10px 0;">Tipo: <strong>' + esc(resource.resource_type) + '</strong></p>';
    html += '<p style="color: var(--text-secondary); margin: 10px 0;">Proyecto: <strong>' + esc(resource.project_id) + '</strong></p>';
    html += '<p style="color: var(--text-secondary); margin: 10px 0;">Postura: <strong>' + esc(resource.posture) + '</strong></p>';
    html += '</div>';

    if (findings.length === 0) {
        html += '<div style="background-color: rgba(72, 187, 120, 0.1); border-left: 4px solid var(--success); padding: 15px; border-radius: 4px;">';
        html += '<p style="color: var(--success); margin: 0;">✅ No se detectaron hallazgos</p>';
        html += '</div>';
    } else {
        html += '<div style="margin-top: 20px;">';
        for (var j = 0; j < findings.length; j++) {
            var finding = findings[j];
            var severity = String(finding.severity || '');
            var severityColor = 'var(--gray)';
            var severityBg = 'rgba(113, 128, 150, 0.1)';
            if (severity === 'Crítico') {
                severityColor = 'var(--danger)';
                severityBg = 'rgba(245, 101, 101, 0.1)';
            } else if (severity === 'Advertencia') {
                severityColor = 'var(--warning)';
                severityBg = 'rgba(237, 137, 54, 0.1)';
            }
            html += '<div class="finding-item" style="background-color: ' + severityBg + '; border-left: 4px solid ' + severityColor + ';">';
            html += '<p style="color: ' + severityColor + '; margin: 0 0 5px 0; font-weight: bold;">[' + esc(finding.severity) + '] ' + esc(finding.finding) + '</p>';
            html += '</div>';
        }
        html += '</div>';
    }

    document.getElementById('modalContent').innerHTML = html;
    document.getElementById('findingsModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('findingsModal').style.display = 'none';
}

function initDashboard() {
    for (var tabId in TABS) {
        if (!Object.prototype.hasOwnProperty.call(TABS, tabId)) continue;
        buildTabSkeleton(tabId);
        var btn = document.querySelector('.tabs .tab[data-tab="' + tabId + '"]');
        if (btn) {
            var count = (DASH[TABS[tabId].dataKey] || []).length;
            var span = btn.querySelector('.tab-count');
            if (span) span.textContent = '(' + count + ')';
        }
    }
    applyFilters();
}

initDashboard();
"""

_HTML_HEAD_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP Infrastructure Overview</title>
    <style>
{css_vars}{css}
    </style>
</head>
<body>
    <div class="container">
"""

_HTML_MODAL = """
        <!-- MODAL DE HALLAZGOS -->
        <div id="findingsModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 style="color: var(--info); margin: 0;">📋 Detalles de Hallazgos</h2>
                    <button class="modal-close" onclick="closeModal()">✕ Cerrar</button>
                </div>
                <div id="modalContent" style="color: var(--text-primary);">
                </div>
            </div>
        </div>
"""

_HTML_FOOTER_TEMPLATE = """
        <footer class="footer">
            <p>GCP Infrastructure Dashboard v{version} | Generado automáticamente por GCP Monitor</p>
        </footer>
    </div>
"""


def _render_header(metadata: Dict[str, Any]) -> str:
    """Renderiza el encabezado del dashboard con la metadata del reporte."""
    return """        <header>
            <h1>🏗️ GCP Infrastructure Overview</h1>
            <div class="header-meta">
                <span>Generado: {generated_at}</span>
                <span>Zona horaria: {timezone}</span>
                <span>Versión: {version}</span>
            </div>
        </header>
""".format(
        generated_at=metadata.get('generated_at', 'N/A'),
        timezone=metadata.get('timezone', 'N/A'),
        version=metadata.get('version', 'N/A'),
    )


def _render_filters(json_data: Dict[str, Any]) -> str:
    """Renderiza la seccion de filtros globales."""
    project_options = generate_project_options(json_data)
    return """        <!-- FILTROS GLOBALES -->
        <div class="filters">
            <h3>🔍 Filtros Globales</h3>
            <div class="filter-group">
                <div>
                    <label class="filter-label" for="filterProject">Proyecto</label>
                    <select id="filterProject" onchange="applyFilters()">
                        <option value="">Todos los proyectos</option>
                        {project_options}
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterEnvironment">Ambiente</label>
                    <select id="filterEnvironment" onchange="applyFilters()">
                        <option value="">Todos los ambientes</option>
                        <option value="dev">Desarrollo</option>
                        <option value="qa">QA</option>
                        <option value="stag">Staging</option>
                        <option value="prod">Producción</option>
                        <option value="desconocido">Desconocido</option>
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterResourceType">Tipo de Recurso</label>
                    <select id="filterResourceType" onchange="applyFilters()">
                        <option value="">Todos los tipos</option>
                        <option value="APIs">APIs / Servicios</option>
                        <option value="Cloud SQL">Cloud SQL</option>
                        <option value="GKE">GKE</option>
                        <option value="Compute Engine">Compute Engine</option>
                        <option value="Cloud Run">Cloud Run</option>
                        <option value="Pub/Sub">Pub/Sub</option>
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterStatus">Estado</label>
                    <select id="filterStatus" onchange="applyFilters()">
                        <option value="">Todos los estados</option>
                        <option value="RUNNING">Ejecutándose</option>
                        <option value="RUNNABLE">Ejecutable</option>
                        <option value="ACTIVE">Activo</option>
                        <option value="ENABLED">Habilitado</option>
                        <option value="STOPPED">Detenido</option>
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterSearch">Búsqueda</label>
                    <input type="text" id="filterSearch" placeholder="Buscar en todas las tablas..." onkeyup="applyFilters()">
                </div>
                <div style="display: flex; align-items: flex-end;">
                    <button class="btn-reset" onclick="resetFilters()">🔄 Restablecer</button>
                </div>
            </div>
        </div>
""".format(project_options=project_options)


def _render_kpis(kpis: Dict[str, Any]) -> str:
    """Renderiza las tarjetas de KPIs (existentes + servicios habilitados, BDs y pods)."""
    cards = [
        ('📊 Proyectos', kpis.get('total_projects', 0), "kpiGo('inventario', '')"),
        ('📌 Servicios Habilitados', kpis.get('total_enabled_services', 0), "kpiGo('servicios', 'APIs')"),
        ('🔧 Recursos Totales', kpis.get('total_resources', 0), "kpiGo('inventario', '')"),
        ('☸️ Clusters GKE', kpis.get('total_gke_clusters', 0), "kpiGo('gke', 'GKE')"),
        ('📦 Pods Running', kpis.get('total_pods', 0), "kpiGo('gke', 'GKE')"),
        ('💾 Bases de Datos', kpis.get('total_databases', 0), "kpiGo('sql', 'Cloud SQL')"),
        ('🗄️ Cloud SQL', kpis.get('total_sql_instances', 0), "kpiGo('sql', 'Cloud SQL')"),
        ('💻 Compute Engine', kpis.get('total_compute_instances', 0), "kpiGo('compute', 'Compute Engine')"),
        ('🚀 Cloud Run', kpis.get('total_cloud_run_services', 0), "kpiGo('run', 'Cloud Run')"),
        ('📨 Pub/Sub', kpis.get('total_pubsub_topics', 0), "kpiGo('pubsub', 'Pub/Sub')"),
    ]
    items = []
    for label, value, action in cards:
        items.append(
            '                <div class="kpi-card" onclick="{action}">\n'
            '                    <div class="kpi-label">{label}</div>\n'
            '                    <div class="kpi-value">{value}</div>\n'
            '                </div>'.format(action=action, label=label, value=value)
        )
    return (
        '        <!-- KPIs -->\n'
        '        <div class="kpi-grid">\n'
        + '\n'.join(items) + '\n'
        '        </div>\n'
    )


def _render_tabs() -> str:
    """Renderiza los botones de navegacion por pestañas y sus contenedores."""
    definitions = [
        ('servicios', '📌 Servicios'),
        ('gke', '☸️ Clusters GKE'),
        ('red', '🌐 Capacidad de Red'),
        ('sql', '🗄️ Cloud SQL'),
        ('compute', '💻 Compute Engine'),
        ('run', '🚀 Cloud Run'),
        ('pubsub', '📨 Pub/Sub'),
        ('inventario', '📋 Inventario'),
    ]

    buttons = []
    contents = []
    for index, (key, label) in enumerate(definitions):
        active = ' active' if index == 0 else ''
        buttons.append(
            '            <button class="tab{active}" data-tab="{key}" onclick="showTab(\'{key}\')">{label}<span class="tab-count"></span></button>'.format(
                active=active, key=key, label=label)
        )
        contents.append(
            '    <div id="tab-{key}" class="tab-content{active}"></div>'.format(key=key, active=active)
        )

    return (
        '        <!-- TABS DE NAVEGACION -->\n'
        '        <div class="tabs">\n'
        + '\n'.join(buttons) + '\n'
        '        </div>\n'
        '\n'
        '        <!-- CONTENIDO DE CADA TAB (llenado por JS) -->\n'
        + '\n'.join(contents) + '\n'
    )


def generate_project_options(json_data: Dict) -> str:
    """Genera opciones de proyecto para el filtro."""
    projects = set()
    for project_id in (json_data.get('data', {}) or {}).keys():
        projects.add(project_id)

    return '\n'.join('<option value="{p}">{p}</option>'.format(p=p) for p in sorted(projects))


def generate_html_dashboard(json_data: Dict[str, Any], output_file: str) -> str:
    """Genera el dashboard HTML completo con sistema de pestañas interactivas."""

    # Normalizar recursos (inventario consolidado + postura de seguridad)
    resources_full = normalize_resources(json_data)
    resources = [_slim_resource(r) for r in resources_full]

    # Extraer todas las dimensiones del JSON consolidado
    services_rows = build_services_rows(json_data)
    gke_rows = build_gke_rows(json_data)
    network_rows = build_network_rows(json_data)
    sql_rows = build_sql_rows(json_data)
    compute_rows = build_compute_rows(json_data)
    run_rows = build_run_rows(json_data)
    pubsub_rows = build_pubsub_rows(json_data)
    kpis = build_kpis(json_data, resources_full, services_rows, gke_rows, sql_rows)

    # Payload embebido en el HTML (self-contained, renderizado 100% client-side)
    dashboard_payload = {
        'resources': resources,
        'services': services_rows,
        'gke': gke_rows,
        'network': network_rows,
        'sql': sql_rows,
        'compute': compute_rows,
        'run': run_rows,
        'pubsub': pubsub_rows,
    }
    data_json = _json_for_html(dashboard_payload)

    metadata = json_data.get('report_metadata', {}) or {}

    html_head = _HTML_HEAD_TEMPLATE.format(
        css_vars=_css_variables(),
        css=_DASHBOARD_CSS,
    )

    html_sections = [
        html_head,
        _render_header(metadata),
        _render_filters(json_data),
        _render_kpis(kpis),
        _render_tabs(),
        _HTML_MODAL,
        _HTML_FOOTER_TEMPLATE.format(version=DASHBOARD_VERSION),
        '<script>',
        'var DASH = ' + data_json + ';',
        '</script>',
        '<script>',
        _DASHBOARD_JS,
        '</script>',
        '</body>',
        '</html>',
    ]

    return '\n'.join(html_sections)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

def load_json_file(filepath: str) -> Optional[Dict]:
    """Carga un archivo JSON."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print("Error cargando {}: {}".format(filepath, e))
        return None


def process_json_files(input_path: str) -> Optional[Dict]:
    """Procesa uno o múltiples archivos JSON."""
    if os.path.isfile(input_path):
        return load_json_file(input_path)
    elif os.path.isdir(input_path):
        # Procesar directorio
        json_files = list(Path(input_path).glob('*.json'))
        if not json_files:
            print("No se encontraron archivos JSON en {}".format(input_path))
            return None

        # Consolidar múltiples JSONs
        consolidated = {
            'report_metadata': {},
            'summary': {},
            'data': {}
        }

        for json_file in sorted(json_files):
            data = load_json_file(str(json_file))
            if data:
                consolidated['report_metadata'] = data.get('report_metadata', {})
                consolidated['summary'] = data.get('summary', {})
                consolidated['data'].update(data.get('data', {}))

        return consolidated if consolidated['data'] else None
    else:
        print("Ruta no válida: {}".format(input_path))
        return None


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Genera un dashboard HTML interactivo (tabs por tipo de recurso) a partir de JSON de GCP Monitor'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Archivo JSON de entrada'
    )
    parser.add_argument(
        '--input-dir', '-d',
        type=str,
        help='Directorio con múltiples snapshots JSON'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='gcp_infrastructure_dashboard.html',
        help='Archivo HTML de salida (default: gcp_infrastructure_dashboard.html)'
    )

    args = parser.parse_args()

    # Validar entrada
    if not args.input and not args.input_dir:
        parser.print_help()
        return 1

    # Procesar JSON
    input_path = args.input or args.input_dir
    json_data = process_json_files(input_path)

    if not json_data:
        print("No se pudo procesar el archivo JSON")
        return 1

    # Generar HTML
    print("Generando dashboard...")
    html_content = generate_html_dashboard(json_data, args.output)

    # Guardar HTML
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("Dashboard generado: {}".format(args.output))
        return 0
    except Exception as e:
        print("Error guardando HTML: {}".format(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())
