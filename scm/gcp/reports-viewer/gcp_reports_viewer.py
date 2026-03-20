#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Reports Viewer v3.0 - Dashboard con Chart.js (Sin dependencias de gráficos)

Genera dashboards HTML interactivos usando Chart.js desde CDN.
No requiere instalación de Plotly ni otras librerías de gráficos.

Autor: Harold Adrian
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

__version__ = "3.2.0"

# Intentar importar rich (opcional)
try:
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Configuración base
BASE_DIR = Path(__file__).parent.parent.absolute()
OUTCOME_DIRS = [
    "outcome",
    "certificate-manager/outcome",
    "cloud-sql/outcome",
    "cluster-gke/outcome",
    "gateway-services/outcome",
    "load-balancer/outcome",
    "monitoring/outcome",
    "secrets-configmaps/outcome",
    "service-account/outcome",
    "vpc-networks/outcome",
    "reports-viewer/outcome"
]

# Patrones a excluir
EXCLUDE_PATTERNS = ['config', 'webhook', 'settings', 'package', 'tsconfig', 'eslint']

# Colores del tema
COLORS = {
    "primary": "#667eea",
    "secondary": "#764ba2",
    "success": "#28a745",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#17a2b8",
    "dark": "#343a40",
    "light": "#f8f9fa"
}


def get_args():
    parser = argparse.ArgumentParser(description="GCP Reports Viewer - Dashboard HTML")
    parser.add_argument("--input", "-i", type=str, help="Archivo JSON o directorio")
    parser.add_argument("--output", "-o", type=str, default="outcome/dashboard.html",
                        help="Archivo HTML de salida")
    parser.add_argument("--title", type=str, default="GCP Infrastructure Dashboard",
                        help="Título del dashboard")
    return parser.parse_args()


def find_json_reports(input_path: Optional[str] = None) -> List[Path]:
    """Encuentra todos los reportes JSON disponibles."""
    reports = []
    
    if input_path:
        path = Path(input_path)
        if path.is_file() and path.suffix == '.json':
            return [path]
        elif path.is_dir():
            return list(path.glob("**/*.json"))
    
    print("Buscando en directorios outcome...")
    for outcome_dir in OUTCOME_DIRS:
        full_path = BASE_DIR / outcome_dir
        if full_path.exists():
            found = list(full_path.glob("*.json"))
            if found:
                print(f"  [{len(found)}] {outcome_dir}")
            reports.extend(found)
    
    if not reports:
        print("  Búsqueda recursiva...")
        reports = list(BASE_DIR.rglob("*.json"))
        reports = [r for r in reports if not any(x in str(r) for x in ['.venv', 'node_modules', '__pycache__'])]
    
    # Excluir archivos de configuración
    reports = [r for r in reports if not any(p in r.stem.lower() for p in EXCLUDE_PATTERNS)]
    
    return sorted(reports, key=lambda x: x.stat().st_mtime, reverse=True)


def extract_tool_info(filepath: Path) -> tuple:
    """Extrae información del tool desde el nombre del archivo."""
    stem = filepath.stem.lower()
    
    tool_mapping = {
        'cert': ('Certificate Manager', 'certificates'),
        'disk': ('Cloud SQL Disk', 'instances'),
        'cluster': ('GKE Cluster', 'clusters'),
        'gateway': ('Gateway Services', 'gateways'),
        'lb_': ('Load Balancer', 'load_balancers'),
        'secrets': ('Secrets & ConfigMaps', 'references'),
        'sa_': ('Service Account', 'service_accounts'),
        'vpc': ('VPC Networks', 'networks'),
        'deployment': ('GKE Deployments', 'deployments'),
    }
    
    for pattern, (tool_name, data_key) in tool_mapping.items():
        if pattern in stem:
            return tool_name, data_key
    
    return filepath.stem.replace('_', ' ').title(), 'data'


def load_report(filepath: Path) -> Optional[Dict]:
    """Carga un reporte JSON y normaliza su estructura."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Si es un array, convertir a dict con metadata
        if isinstance(raw_data, list):
            tool_name, data_key = extract_tool_info(filepath)
            data = {
                'report_metadata': {
                    'tool_name': tool_name,
                    'version': 'legacy',
                    'project_id': 'unknown',
                    'generated_at': datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
                    'file_path': str(filepath)
                },
                'summary': calculate_summary(raw_data),
                data_key: raw_data
            }
        else:
            data = raw_data
            if 'report_metadata' not in data:
                tool_name, _ = extract_tool_info(filepath)
                data['report_metadata'] = {
                    'tool_name': tool_name,
                    'version': 'legacy',
                    'project_id': 'unknown',
                    'generated_at': datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
                }
            if 'summary' not in data:
                data['summary'] = extract_summary_from_data(data)
        
        data['report_metadata']['file_path'] = str(filepath)
        return data
    except Exception as e:
        print(f"  ⚠ Error: {filepath.name}: {e}")
        return None


def calculate_summary(items: list) -> Dict:
    """Calcula summary desde una lista de items."""
    summary = {'total': len(items), 'healthy': 0, 'warning': 0, 'critical': 0}
    for item in items:
        if isinstance(item, dict):
            status = str(item.get('status', '')).upper()
            if status in ['RUNNING', 'HEALTHY', 'ACTIVE', 'OK', 'VALID']:
                summary['healthy'] += 1
            elif status in ['WARNING', 'PENDING', 'ATTENTION']:
                summary['warning'] += 1
            elif status in ['CRITICAL', 'ERROR', 'FAILED', 'MISSING', 'TERMINATED']:
                summary['critical'] += 1
            else:
                summary['healthy'] += 1
    return summary


def extract_summary_from_data(data: Dict) -> Dict:
    """Extrae summary de los datos del reporte."""
    summary = {'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0}
    
    for key, value in data.items():
        if key == 'report_metadata':
            continue
        if isinstance(value, list):
            sub = calculate_summary(value)
            summary['total'] += sub['total']
            summary['healthy'] += sub['healthy']
            summary['warning'] += sub['warning']
            summary['critical'] += sub['critical']
    
    return summary


def extract_metrics(reports_data: List[Dict]) -> Dict:
    """Extrae métricas agregadas de todos los reportes."""
    metrics = {
        'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0,
        'projects': set(), 'project_names': set(), 'tools': set(), 'last_scan': None,
        'by_tool': defaultdict(lambda: {'healthy': 0, 'warning': 0, 'critical': 0})
    }
    
    for report in reports_data:
        meta = report.get('report_metadata', {})
        summary = report.get('summary', {})
        tool = meta.get('tool_name', 'Unknown')
        
        project_id = meta.get('project_id', 'unknown')
        metrics['projects'].add(project_id)
        metrics['project_names'].add(project_id)
        metrics['tools'].add(tool)
        
        ts = meta.get('generated_at', '')
        if ts and (not metrics['last_scan'] or ts > metrics['last_scan']):
            metrics['last_scan'] = ts
        
        h = summary.get('healthy', 0)
        w = summary.get('warning', 0)
        c = summary.get('critical', 0)
        
        metrics['healthy'] += h
        metrics['warning'] += w
        metrics['critical'] += c
        metrics['total'] += h + w + c
        
        metrics['by_tool'][tool]['healthy'] += h
        metrics['by_tool'][tool]['warning'] += w
        metrics['by_tool'][tool]['critical'] += c
    
    metrics['projects'] = len(metrics['projects'])
    metrics['tools'] = len(metrics['tools'])
    
    return metrics


def extract_components_timeline(reports_data: List[Dict]) -> List[Dict]:
    """Extrae todos los componentes individuales con su estado para el timeline/semáforo."""
    components = []
    
    for report in reports_data:
        meta = report.get('report_metadata', {})
        tool = meta.get('tool_name', 'Unknown')
        project = meta.get('project_id', 'unknown')
        ts = meta.get('generated_at', '')
        
        # Procesar diferentes tipos de datos según el checker
        data_keys = ['instances', 'certificates', 'clusters', 'gateways', 'load_balancers',
                     'service_accounts', 'networks', 'deployments', 'references', 'pods']
        
        for key in data_keys:
            items = report.get(key, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                name = (item.get('name') or item.get('instance') or 
                        item.get('cluster_name') or item.get('deployment') or
                        item.get('service_account') or item.get('network_name') or
                        item.get('certificate_name') or 'unknown')
                
                status_raw = str(item.get('status', '')).upper()
                
                # Determinar estado del semáforo
                if status_raw in ['RUNNING', 'HEALTHY', 'ACTIVE', 'OK', 'VALID', 'PROVISIONING']:
                    status = 'healthy'
                elif status_raw in ['WARNING', 'PENDING', 'ATTENTION', 'DEGRADED']:
                    status = 'warning'
                elif status_raw in ['CRITICAL', 'ERROR', 'FAILED', 'MISSING', 'TERMINATED', 'EXPIRED']:
                    status = 'critical'
                else:
                    # Verificar métricas específicas
                    util = item.get('utilization_pct', item.get('disk_utilization', 0))
                    days = item.get('days_until_expiry', 999)
                    restarts = item.get('restarts', 0)
                    
                    if util and util >= 90 or days <= 7 or restarts >= 10:
                        status = 'critical'
                    elif util and util >= 75 or days <= 30 or restarts >= 5:
                        status = 'warning'
                    else:
                        status = 'healthy'
                
                components.append({
                    'name': str(name)[:40],
                    'type': key.replace('_', ' ').title(),
                    'tool': tool,
                    'project': project,
                    'status': status,
                    'timestamp': ts[:16] if ts else '',
                    'details': status_raw or 'OK'
                })
    
    # Ordenar: críticos primero, luego warnings, luego healthy
    order = {'critical': 0, 'warning': 1, 'healthy': 2}
    components.sort(key=lambda x: (order.get(x['status'], 3), x['name']))
    
    return components


def extract_alerts(reports_data: List[Dict]) -> List[Dict]:
    """Extrae alertas de los reportes."""
    alerts = []
    
    for report in reports_data:
        meta = report.get('report_metadata', {})
        tool = meta.get('tool_name', 'Unknown')
        summary = report.get('summary', {})
        
        if summary.get('critical', 0) > 0:
            alerts.append({
                'severity': 'critical',
                'tool': tool,
                'message': f"{summary['critical']} recursos en estado CRITICAL",
                'timestamp': meta.get('generated_at', '')[:16] if meta.get('generated_at') else ''
            })
        
        if summary.get('warning', 0) > 0:
            alerts.append({
                'severity': 'warning',
                'tool': tool,
                'message': f"{summary['warning']} recursos en estado WARNING",
                'timestamp': meta.get('generated_at', '')[:16] if meta.get('generated_at') else ''
            })
        
        # Alertas específicas de disco
        for inst in report.get('instances', []):
            util = inst.get('utilization_pct', inst.get('disk_utilization', 0))
            if util and util >= 90:
                alerts.append({
                    'severity': 'critical',
                    'tool': tool,
                    'message': f"Disco {inst.get('instance', 'unknown')}: {util:.1f}%",
                    'timestamp': meta.get('generated_at', '')[:16] if meta.get('generated_at') else ''
                })
        
        # Alertas de certificados
        for cert in report.get('certificates', []):
            days = cert.get('days_until_expiry', 999)
            if days <= 30:
                alerts.append({
                    'severity': 'critical' if days <= 7 else 'warning',
                    'tool': tool,
                    'message': f"Cert {cert.get('name', 'unknown')}: expira en {days}d",
                    'timestamp': meta.get('generated_at', '')[:16] if meta.get('generated_at') else ''
                })
    
    # Ordenar por severidad
    severity_order = {'critical': 0, 'warning': 1}
    alerts.sort(key=lambda x: severity_order.get(x['severity'], 2))
    
    return alerts[:15]


def generate_dashboard_html(reports_data: List[Dict], title: str) -> str:
    """Genera el dashboard HTML completo con Chart.js."""
    
    metrics = extract_metrics(reports_data)
    alerts = extract_alerts(reports_data)
    components = extract_components_timeline(reports_data)
    
    last_update = metrics['last_scan'][:16] if metrics['last_scan'] else datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Obtener nombres de proyectos para el título
    project_names = sorted([p for p in metrics['project_names'] if p != 'unknown'])
    projects_display = ', '.join(project_names[:3]) if project_names else 'Sin proyectos'
    if len(project_names) > 3:
        projects_display += f' (+{len(project_names)-3} más)'
    
    # Preparar datos para Chart.js
    by_tool = dict(metrics['by_tool'])
    tool_labels = json.dumps(list(by_tool.keys()))
    tool_healthy = json.dumps([by_tool[t]['healthy'] for t in by_tool])
    tool_warning = json.dumps([by_tool[t]['warning'] for t in by_tool])
    tool_critical = json.dumps([by_tool[t]['critical'] for t in by_tool])
    
    # Generar timeline/semáforo de componentes
    timeline_html = ""
    for comp in components:
        if comp['status'] == 'critical':
            icon, color, bg = '🔴', COLORS['danger'], '#f8d7da'
        elif comp['status'] == 'warning':
            icon, color, bg = '🟡', COLORS['warning'], '#fff3cd'
        else:
            icon, color, bg = '🟢', COLORS['success'], '#d4edda'
        
        timeline_html += f'''
        <div class="timeline-item" style="background: {bg}; border-left: 4px solid {color};">
            <div class="timeline-icon">{icon}</div>
            <div class="timeline-content">
                <div class="timeline-name">{comp['name']}</div>
                <div class="timeline-meta">
                    <span class="timeline-type">{comp['type']}</span>
                    <span class="timeline-tool">{comp['tool']}</span>
                    <span class="timeline-status">{comp['details']}</span>
                </div>
            </div>
        </div>'''
    
    # Generar HTML de alertas
    alerts_html = ""
    if alerts:
        for alert in alerts:
            icon = "🔴" if alert['severity'] == 'critical' else "🟡"
            color = COLORS['danger'] if alert['severity'] == 'critical' else COLORS['warning']
            alerts_html += f'''
            <div class="alert-item" style="border-left: 4px solid {color};">
                <span class="alert-icon">{icon}</span>
                <div class="alert-content">
                    <div class="alert-message">{alert['message']}</div>
                    <div class="alert-meta">{alert['tool']} · {alert['timestamp']}</div>
                </div>
            </div>'''
    else:
        alerts_html = '''
        <div class="alert-item" style="border-left: 4px solid #28a745;">
            <span class="alert-icon">✅</span>
            <div class="alert-content">
                <div class="alert-message">No hay alertas críticas</div>
                <div class="alert-meta">Todos los sistemas operando normalmente</div>
            </div>
        </div>'''
    
    # Generar timeline horizontal compacto por herramienta
    horizontal_timeline_html = ""
    for tool_name, tool_data in by_tool.items():
        total = tool_data['healthy'] + tool_data['warning'] + tool_data['critical']
        if total == 0:
            continue
        h_pct = (tool_data['healthy'] / total * 100) if total > 0 else 0
        w_pct = (tool_data['warning'] / total * 100) if total > 0 else 0
        c_pct = (tool_data['critical'] / total * 100) if total > 0 else 0
        
        # Determinar estado actual
        if tool_data['critical'] > 0:
            status_icon = '🔴'
        elif tool_data['warning'] > 0:
            status_icon = '🟡'
        else:
            status_icon = '🟢'
        
        horizontal_timeline_html += f'''
        <div class="h-timeline-row">
            <div class="h-timeline-label">
                <span class="h-timeline-icon">{status_icon}</span>
                <span class="h-timeline-name">{tool_name[:25]}</span>
            </div>
            <div class="h-timeline-bar">
                <div class="h-bar-segment h-bar-healthy" style="width: {h_pct}%;" title="Healthy: {tool_data['healthy']}"></div>
                <div class="h-bar-segment h-bar-warning" style="width: {w_pct}%;" title="Warning: {tool_data['warning']}"></div>
                <div class="h-bar-segment h-bar-critical" style="width: {c_pct}%;" title="Critical: {tool_data['critical']}"></div>
            </div>
            <div class="h-timeline-counts">
                <span class="h-count-healthy">{tool_data['healthy']}</span>
                <span class="h-count-warning">{tool_data['warning']}</span>
                <span class="h-count-critical">{tool_data['critical']}</span>
            </div>
        </div>'''
    
    # Generar tabla de reportes
    reports_table = ""
    for report in reports_data:
        meta = report.get('report_metadata', {})
        summary = report.get('summary', {})
        tool = meta.get('tool_name', 'Unknown')
        project = meta.get('project_id', 'unknown')
        ts = meta.get('generated_at', '')[:16] if meta.get('generated_at') else ''
        h = summary.get('healthy', 0)
        w = summary.get('warning', 0)
        c = summary.get('critical', 0)
        
        status_badge = ""
        if c > 0:
            status_badge = f'<span class="badge badge-danger">{c} Critical</span>'
        elif w > 0:
            status_badge = f'<span class="badge badge-warning">{w} Warning</span>'
        else:
            status_badge = f'<span class="badge badge-success">{h} Healthy</span>'
        
        reports_table += f'''
        <tr>
            <td><strong>{tool}</strong></td>
            <td>{project}</td>
            <td>{ts}</td>
            <td>{status_badge}</td>
        </tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
            color: white;
            padding: 25px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 1.8em; font-weight: 600; }}
        .header-meta {{ text-align: right; opacity: 0.9; font-size: 0.9em; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 25px; }}
        
        /* KPI Cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }}
        .kpi-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
        }}
        .kpi-value {{
            font-size: 2.5em;
            font-weight: 700;
            margin: 10px 0;
        }}
        .kpi-label {{ color: #666; font-size: 0.9em; }}
        .kpi-healthy {{ color: {COLORS['success']}; }}
        .kpi-warning {{ color: {COLORS['warning']}; }}
        .kpi-critical {{ color: {COLORS['danger']}; }}
        .kpi-info {{ color: {COLORS['info']}; }}
        
        /* Sections */
        .section {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .section-title {{
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 20px;
            color: {COLORS['dark']};
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        
        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 25px;
        }}
        .chart-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .chart-title {{
            font-weight: 600;
            margin-bottom: 15px;
            color: {COLORS['dark']};
        }}
        
        /* Alerts */
        .alert-item {{
            display: flex;
            align-items: flex-start;
            padding: 12px 15px;
            background: #fafafa;
            border-radius: 8px;
            margin-bottom: 10px;
        }}
        .alert-icon {{ font-size: 1.2em; margin-right: 12px; }}
        .alert-message {{ font-weight: 500; }}
        .alert-meta {{ font-size: 0.85em; color: #666; margin-top: 4px; }}
        
        /* Table */
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
        tr:hover {{ background: #f8f9fa; }}
        
        /* Badges */
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        
        /* Timeline/Semáforo */
        .timeline-container {{
            max-height: 500px;
            overflow-y: auto;
            padding-right: 10px;
        }}
        .timeline-item {{
            display: flex;
            align-items: center;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 8px;
        }}
        .timeline-icon {{ font-size: 1.3em; margin-right: 12px; }}
        .timeline-content {{ flex: 1; }}
        .timeline-name {{ font-weight: 600; font-size: 0.95em; }}
        .timeline-meta {{ font-size: 0.8em; color: #555; margin-top: 3px; }}
        .timeline-meta span {{ margin-right: 12px; }}
        .timeline-type {{ background: #e9ecef; padding: 2px 8px; border-radius: 4px; }}
        .timeline-tool {{ color: #666; }}
        .timeline-status {{ font-weight: 500; }}
        .timeline-filters {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 6px 14px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{ opacity: 0.8; }}
        .filter-btn.active {{ box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        .filter-all {{ background: #e9ecef; color: #333; }}
        .filter-critical {{ background: #f8d7da; color: #721c24; }}
        .filter-warning {{ background: #fff3cd; color: #856404; }}
        .filter-healthy {{ background: #d4edda; color: #155724; }}
        
        /* Timeline Horizontal Compacto */
        .h-timeline-row {{
            display: flex;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .h-timeline-row:last-child {{ border-bottom: none; }}
        .h-timeline-label {{
            width: 200px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .h-timeline-icon {{ font-size: 1em; }}
        .h-timeline-name {{ font-size: 0.85em; font-weight: 500; color: #333; }}
        .h-timeline-bar {{
            flex: 1;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            display: flex;
            overflow: hidden;
            margin: 0 15px;
        }}
        .h-bar-segment {{ height: 100%; transition: width 0.3s; }}
        .h-bar-healthy {{ background: {COLORS['success']}; }}
        .h-bar-warning {{ background: {COLORS['warning']}; }}
        .h-bar-critical {{ background: {COLORS['danger']}; }}
        .h-timeline-counts {{
            display: flex;
            gap: 8px;
            font-size: 0.75em;
            min-width: 90px;
        }}
        .h-count-healthy {{ color: {COLORS['success']}; font-weight: 600; }}
        .h-count-warning {{ color: #856404; font-weight: 600; }}
        .h-count-critical {{ color: {COLORS['danger']}; font-weight: 600; }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📊 {title}</h1>
            <div style="opacity: 0.8; margin-top: 5px;">🏢 {projects_display}</div>
        </div>
        <div class="header-meta">
            <div>GCP Reports Viewer v{__version__}</div>
            <div>Última actualización: {last_update}</div>
            <div>{metrics['tools']} herramientas · {metrics['projects']} proyectos</div>
        </div>
    </div>
    
    <div class="container">
        <!-- KPI Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">✅ Healthy</div>
                <div class="kpi-value kpi-healthy">{metrics['healthy']}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">⚠️ Warning</div>
                <div class="kpi-value kpi-warning">{metrics['warning']}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">🔴 Critical</div>
                <div class="kpi-value kpi-critical">{metrics['critical']}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">📦 Total Recursos</div>
                <div class="kpi-value kpi-info">{metrics['total']}</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">📈 Distribución de Estados</div>
                <canvas id="pieChart" height="250"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">📊 Estado por Herramienta</div>
                <canvas id="barChart" height="250"></canvas>
            </div>
        </div>
        
        <!-- Timeline/Semáforo de Componentes -->
        <div class="section">
            <div class="section-title">🚦 Semáforo de Componentes ({len(components)})</div>
            <div class="timeline-filters">
                <button class="filter-btn filter-all active" onclick="filterTimeline('all')">Todos ({len(components)})</button>
                <button class="filter-btn filter-critical" onclick="filterTimeline('critical')">🔴 Críticos ({len([c for c in components if c['status']=='critical'])})</button>
                <button class="filter-btn filter-warning" onclick="filterTimeline('warning')">🟡 Warning ({len([c for c in components if c['status']=='warning'])})</button>
                <button class="filter-btn filter-healthy" onclick="filterTimeline('healthy')">🟢 Healthy ({len([c for c in components if c['status']=='healthy'])})</button>
            </div>
            <div class="timeline-container" id="timelineContainer">
                {timeline_html if timeline_html else '<div style="color:#666;padding:20px;text-align:center;">No hay componentes individuales para mostrar</div>'}
            </div>
        </div>
        
        <!-- Timeline Horizontal Compacto -->
        <div class="section">
            <div class="section-title">📊 Resumen por Herramienta</div>
            <div class="h-timeline-legend" style="display:flex;gap:20px;margin-bottom:15px;font-size:0.8em;">
                <span>🟢 Healthy</span>
                <span>🟡 Warning</span>
                <span>🔴 Critical</span>
            </div>
            {horizontal_timeline_html if horizontal_timeline_html else '<div style="color:#666;padding:20px;text-align:center;">No hay datos de herramientas</div>'}
        </div>
        
        <!-- Alerts -->
        <div class="section">
            <div class="section-title">🚨 Alertas Recientes</div>
            {alerts_html}
        </div>
        
        <!-- Reports Table -->
        <div class="section">
            <div class="section-title">📋 Reportes Cargados ({len(reports_data)})</div>
            <table>
                <thead>
                    <tr>
                        <th>Herramienta</th>
                        <th>Proyecto</th>
                        <th>Fecha</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {reports_table}
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="footer">
        Generado por GCP Reports Viewer v{__version__} · {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
    
    <script>
        // Pie Chart
        new Chart(document.getElementById('pieChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Healthy', 'Warning', 'Critical'],
                datasets: [{{
                    data: [{metrics['healthy']}, {metrics['warning']}, {metrics['critical']}],
                    backgroundColor: ['{COLORS['success']}', '{COLORS['warning']}', '{COLORS['danger']}'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
        
        // Bar Chart
        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: {tool_labels},
                datasets: [
                    {{ label: 'Healthy', data: {tool_healthy}, backgroundColor: '{COLORS['success']}' }},
                    {{ label: 'Warning', data: {tool_warning}, backgroundColor: '{COLORS['warning']}' }},
                    {{ label: 'Critical', data: {tool_critical}, backgroundColor: '{COLORS['danger']}' }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{ x: {{ stacked: true }}, y: {{ stacked: true }} }},
                plugins: {{ legend: {{ position: 'bottom' }} }}
            }}
        }});
        
        // Filtrado del Timeline
        function filterTimeline(status) {{
            const items = document.querySelectorAll('.timeline-item');
            const buttons = document.querySelectorAll('.filter-btn');
            
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            items.forEach(item => {{
                const bg = item.style.background;
                let itemStatus = 'healthy';
                if (bg.includes('f8d7da')) itemStatus = 'critical';
                else if (bg.includes('fff3cd')) itemStatus = 'warning';
                
                if (status === 'all' || itemStatus === status) {{
                    item.style.display = 'flex';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>'''
    
    return html


def main():
    args = get_args()
    
    if RICH_AVAILABLE:
        console = Console()
        console.print(Panel.fit(
            f"[bold blue]GCP Reports Viewer v{__version__}[/]\n"
            "[dim]Dashboard con Chart.js - Sin dependencias de gráficos[/]"
        ))
    else:
        print(f"\n=== GCP Reports Viewer v{__version__} ===\n")
    
    # Buscar reportes
    print("Buscando reportes JSON...")
    reports = find_json_reports(args.input)
    
    if not reports:
        print("❌ No se encontraron reportes JSON.")
        print("Ejecute los checkers con -o json para generar reportes.")
        return 1
    
    print(f"\nEncontrados {len(reports)} reportes:")
    
    # Cargar reportes
    reports_data = []
    for report_path in reports:
        data = load_report(report_path)
        if data:
            reports_data.append(data)
            tool = data['report_metadata'].get('tool_name', 'Unknown')
            print(f"  ✓ {report_path.name} ({tool})")
    
    if not reports_data:
        print("❌ No se pudieron cargar reportes válidos.")
        return 1
    
    # Generar dashboard
    print(f"\nGenerando dashboard...")
    html = generate_dashboard_html(reports_data, args.title)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Determinar ruta de salida
    if args.output == "outcome/dashboard.html":
        # Usar nombre por defecto con timestamp
        output_filename = f"dashboard_{timestamp}.html"
        output_path = Path(__file__).parent / "outcome" / output_filename
    else:
        # Usuario especificó ruta, agregar timestamp al nombre
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = Path(__file__).parent / output_path
        # Insertar timestamp en el nombre
        stem = output_path.stem
        output_path = output_path.parent / f"{stem}_{timestamp}{output_path.suffix}"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard generado: {output_path}")
    print("Abra el archivo en un navegador para ver el dashboard.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
