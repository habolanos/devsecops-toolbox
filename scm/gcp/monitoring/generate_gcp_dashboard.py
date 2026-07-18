#!/usr/bin/env python3
"""
GCP Infrastructure Dashboard Generator
Genera un dashboard HTML interactivo a partir de archivos JSON consolidados de GCP Monitor.

Versión: 1.7.2
Fecha: 18 de Julio de 2026
Autor: Harold Adrian
"""

import json
import argparse
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
    print("⚠️ Advertencia: pandas no disponible. Algunas funciones pueden ser limitadas.")

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


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZACIÓN DE RECURSOS
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_resources(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normaliza recursos heterogéneos a un modelo tabular común."""
    normalized = []
    
    for project_id, proj_data in data.get('data', {}).items():
        # Cloud SQL
        for sql in proj_data.get('sql_instances', []):
            normalized.append({
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
        
        # GKE
        for gke in proj_data.get('gke_clusters', []):
            normalized.append({
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
        
        # Compute Engine
        for ce in proj_data.get('compute_instances', []):
            normalized.append({
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
        
        # Cloud Run
        for cr in proj_data.get('cloud_run', []):
            normalized.append({
                'resource_type': 'Cloud Run',
                'resource_name': safe_get(cr, 'metadata.name', safe_get(cr, 'name', 'N/A')),
                'project_id': project_id,
                'environment': infer_environment(project_id),
                'region_or_zone': safe_get(cr, 'metadata.namespace', 'N/A'),
                'status': safe_get(cr, 'status', 'UNKNOWN'),
                'created_at': safe_get(cr, 'metadata.creationTimestamp', 'N/A'),
                'posture': 'Conforme',
                'findings': [],
                'raw_data': cr
            })
        
        # Pub/Sub
        for ps in proj_data.get('pubsub_topics', []):
            normalized.append({
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
    
    return normalized


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
    for pool in safe_get(gke, 'nodePools', []):
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
# GENERACIÓN DE HTML
# ═══════════════════════════════════════════════════════════════════════════════

def generate_html_dashboard(json_data: Dict[str, Any], output_file: str) -> str:
    """Genera el dashboard HTML completo."""
    
    # Normalizar recursos
    resources = normalize_resources(json_data)
    
    # Metadata
    metadata = json_data.get('report_metadata', {})
    summary = json_data.get('summary', {})
    
    # Crear DataFrame para análisis
    df = pd.DataFrame(resources) if PANDAS_AVAILABLE else None
    
    # Generar HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP Infrastructure Overview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: {COLORS['bg_dark']};
            color: {COLORS['text_primary']};
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            margin-bottom: 40px;
            border-bottom: 1px solid {COLORS['border']};
            padding-bottom: 20px;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            color: {COLORS['info']};
        }}
        
        .header-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: {COLORS['text_secondary']};
            font-size: 0.9em;
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .kpi-card {{
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .kpi-card:hover {{
            border-color: {COLORS['info']};
            box-shadow: 0 0 10px rgba(66, 153, 225, 0.2);
        }}
        
        .kpi-label {{
            color: {COLORS['text_secondary']};
            font-size: 0.85em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .kpi-value {{
            font-size: 2em;
            font-weight: bold;
            color: {COLORS['info']};
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid {COLORS['info']};
            color: {COLORS['info']};
        }}
        
        .chart-container {{
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        
        .filters {{
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        
        .filter-group {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        
        select, input {{
            background-color: {COLORS['bg_dark']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 10px;
            font-size: 0.9em;
        }}
        
        select:focus, input:focus {{
            outline: none;
            border-color: {COLORS['info']};
            box-shadow: 0 0 5px rgba(66, 153, 225, 0.3);
        }}
        
        button {{
            background-color: {COLORS['info']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background-color 0.3s ease;
        }}
        
        button:hover {{
            background-color: #3182ce;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        
        .status-running {{
            background-color: rgba(72, 187, 120, 0.2);
            color: {COLORS['success']};
        }}
        
        .status-warning {{
            background-color: rgba(237, 137, 54, 0.2);
            color: {COLORS['warning']};
        }}
        
        .status-critical {{
            background-color: rgba(245, 101, 101, 0.2);
            color: {COLORS['danger']};
        }}
        
        .status-unknown {{
            background-color: rgba(113, 128, 150, 0.2);
            color: {COLORS['gray']};
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th {{
            background-color: {COLORS['bg_dark']};
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: {COLORS['info']};
            border-bottom: 1px solid {COLORS['border']};
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid {COLORS['border']};
        }}
        
        tr:hover {{
            background-color: rgba(66, 153, 225, 0.1);
        }}
        
        .footer {{
            text-align: center;
            color: {COLORS['text_secondary']};
            font-size: 0.85em;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid {COLORS['border']};
        }}
        
        @media (max-width: 768px) {{
            .kpi-grid {{
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
            
            .header-meta {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏗️ GCP Infrastructure Overview</h1>
            <div class="header-meta">
                <span>Generado: {metadata.get('generated_at', 'N/A')}</span>
                <span>Zona horaria: {metadata.get('timezone', 'N/A')}</span>
                <span>Versión: {metadata.get('version', 'N/A')}</span>
            </div>
        </header>
        
        <!-- FILTROS -->
        <div class="filters">
            <h3 style="margin-bottom: 15px; color: {COLORS['info']};">🔍 Filtros Globales</h3>
            <div class="filter-group">
                <div>
                    <label style="display: block; margin-bottom: 5px; font-size: 0.9em; color: {COLORS['text_secondary']};">Proyecto</label>
                    <select id="filterProject" onchange="applyFilters()">
                        <option value="">Todos los proyectos</option>
                        {generate_project_options(json_data)}
                    </select>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 5px; font-size: 0.9em; color: {COLORS['text_secondary']};">Ambiente</label>
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
                    <label style="display: block; margin-bottom: 5px; font-size: 0.9em; color: {COLORS['text_secondary']};">Tipo de Recurso</label>
                    <select id="filterResourceType" onchange="applyFilters()">
                        <option value="">Todos los tipos</option>
                        <option value="Cloud SQL">Cloud SQL</option>
                        <option value="GKE">GKE</option>
                        <option value="Compute Engine">Compute Engine</option>
                        <option value="Cloud Run">Cloud Run</option>
                        <option value="Pub/Sub">Pub/Sub</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 5px; font-size: 0.9em; color: {COLORS['text_secondary']};">Estado</label>
                    <select id="filterStatus" onchange="applyFilters()">
                        <option value="">Todos los estados</option>
                        <option value="RUNNING">Ejecutándose</option>
                        <option value="RUNNABLE">Ejecutable</option>
                        <option value="ACTIVE">Activo</option>
                        <option value="STOPPED">Detenido</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 5px; font-size: 0.9em; color: {COLORS['text_secondary']};">Búsqueda</label>
                    <input type="text" id="filterSearch" placeholder="Nombre del recurso..." onkeyup="applyFilters()">
                </div>
                <div style="display: flex; align-items: flex-end;">
                    <button onclick="resetFilters()" style="width: 100%;">🔄 Restablecer</button>
                </div>
            </div>
        </div>
        
        <!-- KPIs -->
        <div class="section">
            <div class="kpi-grid">
                <div class="kpi-card" onclick="filterByProject('')">
                    <div class="kpi-label">📊 Proyectos</div>
                    <div class="kpi-value">{summary.get('total_projects', 0)}</div>
                </div>
                <div class="kpi-card" onclick="filterByResourceType('')">
                    <div class="kpi-label">🔧 Recursos Totales</div>
                    <div class="kpi-value">{len(resources)}</div>
                </div>
                <div class="kpi-card" onclick="filterByResourceType('GKE')">
                    <div class="kpi-label">☸️ Clusters GKE</div>
                    <div class="kpi-value">{summary.get('total_gke_clusters', 0)}</div>
                </div>
                <div class="kpi-card" onclick="filterByResourceType('Cloud SQL')">
                    <div class="kpi-label">🗄️ Cloud SQL</div>
                    <div class="kpi-value">{summary.get('total_sql_instances', 0)}</div>
                </div>
                <div class="kpi-card" onclick="filterByResourceType('Compute Engine')">
                    <div class="kpi-label">💻 Compute Engine</div>
                    <div class="kpi-value">{summary.get('total_compute_instances', 0)}</div>
                </div>
                <div class="kpi-card" onclick="filterByResourceType('Cloud Run')">
                    <div class="kpi-label">🚀 Cloud Run</div>
                    <div class="kpi-value">{summary.get('total_cloud_run_services', 0)}</div>
                </div>
                <div class="kpi-card" onclick="filterByResourceType('Pub/Sub')">
                    <div class="kpi-label">📨 Pub/Sub</div>
                    <div class="kpi-value">{summary.get('total_pubsub_topics', 0)}</div>
                </div>
            </div>
        </div>
        
        <!-- TABLA DE RECURSOS -->
        <div class="section">
            <h2 class="section-title">📋 Inventario de Recursos</h2>
            <div style="overflow-x: auto;">
                <table id="resourceTable">
                    <thead>
                        <tr>
                            <th>Tipo</th>
                            <th>Nombre</th>
                            <th>Proyecto</th>
                            <th>Ambiente</th>
                            <th>Región/Zona</th>
                            <th>Estado</th>
                            <th>Postura</th>
                            <th>Hallazgos</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
                        {generate_table_rows(resources)}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- MODAL DE HALLAZGOS -->
        <div id="findingsModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.7); z-index: 1000; overflow-y: auto;">
            <div style="background-color: {COLORS['bg_card']}; margin: 50px auto; padding: 30px; border-radius: 8px; max-width: 600px; border: 1px solid {COLORS['border']};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="color: {COLORS['info']}; margin: 0;">📋 Detalles de Hallazgos</h2>
                    <button onclick="closeModal()" style="background-color: {COLORS['danger']}; padding: 8px 16px; cursor: pointer;">✕ Cerrar</button>
                </div>
                <div id="modalContent" style="color: {COLORS['text_primary']};">
                </div>
            </div>
        </div>
        
        <footer class="footer">
            <p>GCP Infrastructure Dashboard v1.7.2 | Generado automáticamente por GCP Monitor</p>
        </footer>
    </div>
    
    <script>
        const allResources = {json.dumps(resources)};
        
        function applyFilters() {{
            const projectFilter = document.getElementById('filterProject').value;
            const environmentFilter = document.getElementById('filterEnvironment').value;
            const resourceTypeFilter = document.getElementById('filterResourceType').value;
            const statusFilter = document.getElementById('filterStatus').value;
            const searchFilter = document.getElementById('filterSearch').value.toLowerCase();
            
            const filtered = allResources.filter(resource => {{
                const matchProject = !projectFilter || resource.project_id === projectFilter;
                const matchEnvironment = !environmentFilter || resource.environment === environmentFilter;
                const matchResourceType = !resourceTypeFilter || resource.resource_type === resourceTypeFilter;
                const matchStatus = !statusFilter || resource.status === statusFilter;
                const matchSearch = !searchFilter || resource.resource_name.toLowerCase().includes(searchFilter);
                
                return matchProject && matchEnvironment && matchResourceType && matchStatus && matchSearch;
            }});
            
            updateTable(filtered);
        }}
        
        function updateTable(resources) {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            resources.forEach((resource, index) => {{
                const row = document.createElement('tr');
                const statusClass = getStatusClass(resource.status);
                const postureClass = getPostureClass(resource.posture);
                const findingsCount = resource.findings ? resource.findings.length : 0;
                
                row.innerHTML = `
                    <td>${{resource.resource_type}}</td>
                    <td>${{resource.resource_name}}</td>
                    <td>${{resource.project_id}}</td>
                    <td>${{resource.environment}}</td>
                    <td>${{resource.region_or_zone}}</td>
                    <td><span class="status-badge ${{statusClass}}">${{resource.status}}</span></td>
                    <td><span class="status-badge ${{postureClass}}">${{resource.posture}}</span></td>
                    <td><a href="javascript:void(0)" onclick="showFindings(${{index}}, '${{resource.resource_name}}')" style="color: {COLORS['info']}; text-decoration: underline; cursor: pointer;">${{findingsCount}} hallazgo(s)</a></td>
                `;
                tbody.appendChild(row);
            }});
        }}
        
        function showFindings(index, resourceName) {{
            const resource = allResources[index];
            const findings = resource.findings || [];
            
            let html = `<div style="margin-bottom: 20px;">`;
            html += `<h3 style="color: {COLORS['info']}; margin-top: 0;">🔍 ${{resourceName}}</h3>`;
            html += `<p style="color: {COLORS['text_secondary']}; margin: 10px 0;">Tipo: <strong>${{resource.resource_type}}</strong></p>`;
            html += `<p style="color: {COLORS['text_secondary']}; margin: 10px 0;">Proyecto: <strong>${{resource.project_id}}</strong></p>`;
            html += `<p style="color: {COLORS['text_secondary']}; margin: 10px 0;">Postura: <strong>${{resource.posture}}</strong></p>`;
            html += `</div>`;
            
            if (findings.length === 0) {{
                html += `<div style="background-color: rgba(72, 187, 120, 0.1); border-left: 4px solid {COLORS['success']}; padding: 15px; border-radius: 4px;">`;
                html += `<p style="color: {COLORS['success']}; margin: 0;">✅ No se detectaron hallazgos</p>`;
                html += `</div>`;
            }} else {{
                html += `<div style="margin-top: 20px;">`;
                findings.forEach(finding => {{
                    const severityColor = finding.severity === 'Crítico' ? '{COLORS['danger']}' : 
                                         finding.severity === 'Advertencia' ? '{COLORS['warning']}' : 
                                         '{COLORS['gray']}';
                    const severityBg = finding.severity === 'Crítico' ? 'rgba(245, 101, 101, 0.1)' : 
                                      finding.severity === 'Advertencia' ? 'rgba(237, 137, 54, 0.1)' : 
                                      'rgba(113, 128, 150, 0.1)';
                    
                    html += `<div style="background-color: ${{severityBg}}; border-left: 4px solid ${{severityColor}}; padding: 15px; margin-bottom: 10px; border-radius: 4px;">`;
                    html += `<p style="color: ${{severityColor}}; margin: 0 0 5px 0; font-weight: bold;">[${{finding.severity}}] ${{finding.finding}}</p>`;
                    html += `</div>`;
                }});
                html += `</div>`;
            }}
            
            document.getElementById('modalContent').innerHTML = html;
            document.getElementById('findingsModal').style.display = 'block';
        }}
        
        function closeModal() {{
            document.getElementById('findingsModal').style.display = 'none';
        }}
        
        function getStatusClass(status) {{
            if (status === 'RUNNING' || status === 'RUNNABLE' || status === 'ACTIVE') return 'status-running';
            if (status === 'STOPPED' || status === 'TERMINATED') return 'status-critical';
            return 'status-unknown';
        }}
        
        function getPostureClass(posture) {{
            if (posture === 'Conforme') return 'status-running';
            if (posture === 'Advertencia') return 'status-warning';
            if (posture === 'Crítico') return 'status-critical';
            return 'status-unknown';
        }}
        
        function filterByProject(project) {{
            document.getElementById('filterProject').value = project;
            applyFilters();
        }}
        
        function filterByResourceType(type) {{
            document.getElementById('filterResourceType').value = type;
            applyFilters();
        }}
        
        function resetFilters() {{
            document.getElementById('filterProject').value = '';
            document.getElementById('filterEnvironment').value = '';
            document.getElementById('filterResourceType').value = '';
            document.getElementById('filterStatus').value = '';
            document.getElementById('filterSearch').value = '';
            applyFilters();
        }}
        
        // Cargar tabla inicial
        updateTable(allResources);
    </script>
</body>
</html>
"""
    
    return html_content


def generate_project_options(json_data: Dict) -> str:
    """Genera opciones de proyecto para el filtro."""
    projects = set()
    for project_id in json_data.get('data', {}).keys():
        projects.add(project_id)
    
    return '\n'.join(f'<option value="{p}">{p}</option>' for p in sorted(projects))


def generate_table_rows(resources: List[Dict]) -> str:
    """Genera filas de la tabla."""
    rows = []
    for resource in resources:
        status_class = 'status-running' if resource['status'] in ['RUNNING', 'RUNNABLE', 'ACTIVE'] else 'status-critical' if resource['status'] in ['STOPPED', 'TERMINATED'] else 'status-unknown'
        posture_class = 'status-running' if resource['posture'] == 'Conforme' else 'status-warning' if resource['posture'] == 'Advertencia' else 'status-critical'
        
        row = f"""
        <tr>
            <td>{resource['resource_type']}</td>
            <td>{resource['resource_name']}</td>
            <td>{resource['project_id']}</td>
            <td>{resource['environment']}</td>
            <td>{resource['region_or_zone']}</td>
            <td><span class="status-badge {status_class}">{resource['status']}</span></td>
            <td><span class="status-badge {posture_class}">{resource['posture']}</span></td>
            <td>{len(resource['findings'])} hallazgo(s)</td>
        </tr>
        """
        rows.append(row)
    
    return '\n'.join(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

def load_json_file(filepath: str) -> Optional[Dict]:
    """Carga un archivo JSON."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error cargando {filepath}: {e}")
        return None


def process_json_files(input_path: str) -> Optional[Dict]:
    """Procesa uno o múltiples archivos JSON."""
    if os.path.isfile(input_path):
        return load_json_file(input_path)
    elif os.path.isdir(input_path):
        # Procesar directorio
        json_files = list(Path(input_path).glob('*.json'))
        if not json_files:
            print(f"❌ No se encontraron archivos JSON en {input_path}")
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
        print(f"❌ Ruta no válida: {input_path}")
        return None


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Genera un dashboard HTML interactivo a partir de JSON de GCP Monitor'
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
        print("❌ No se pudo procesar el archivo JSON")
        return 1
    
    # Generar HTML
    print(f"📊 Generando dashboard...")
    html_content = generate_html_dashboard(json_data, args.output)
    
    # Guardar HTML
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Dashboard generado: {args.output}")
        return 0
    except Exception as e:
        print(f"❌ Error guardando HTML: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
