#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GCP Event Tracker - Orquestador Principal

Orquestador que integra todos los componentes para rastrear eventos
y generar reportes de caídas de servicio.
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    from google.cloud import logging as cloud_logging
    from google.cloud import monitoring_v3
    from google.oauth2 import service_account
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

try:
    from kubernetes import client, config
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False


class EventTracker:
    """Orquestador principal para rastreo de eventos."""
    
    def __init__(self, project_id: str, credentials_file: Optional[str] = None):
        """
        Inicializa el EventTracker.
        
        Args:
            project_id: ID del proyecto GCP
            credentials_file: Ruta al archivo de credenciales (opcional)
        """
        self.project_id = project_id
        self.credentials_file = credentials_file
        self.events = []
        self.correlations = []
        
        # Inicializar clientes
        self._init_gcp_clients()
        self._init_k8s_client()
    
    def _init_gcp_clients(self):
        """Inicializa clientes de GCP."""
        if not GCP_AVAILABLE:
            print("⚠️  google-cloud-logging no está instalado")
            return
        
        try:
            if self.credentials_file:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_file
                )
                self.logging_client = cloud_logging.Client(
                    project=self.project_id,
                    credentials=credentials
                )
                self.monitoring_client = monitoring_v3.MetricServiceClient(
                    credentials=credentials
                )
            else:
                self.logging_client = cloud_logging.Client(project=self.project_id)
                self.monitoring_client = monitoring_v3.MetricServiceClient()
        except Exception as e:
            print(f"❌ Error inicializando clientes GCP: {e}")
            self.logging_client = None
            self.monitoring_client = None
    
    def _init_k8s_client(self):
        """Inicializa cliente de Kubernetes."""
        if not K8S_AVAILABLE:
            print("⚠️  kubernetes no está instalado")
            return
        
        try:
            config.load_kube_config()
            self.k8s_client = client.CoreV1Api()
        except Exception as e:
            print(f"⚠️  No se pudo conectar a Kubernetes: {e}")
            self.k8s_client = None
    
    def search_component_events(
        self,
        component_name: str,
        start_time: str,
        end_time: str,
        include_metrics: bool = True,
        include_audit_logs: bool = True,
        include_pod_logs: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Busca eventos de un componente en todas las fuentes.
        
        Args:
            component_name: Nombre del componente
            start_time: Hora de inicio (ISO 8601)
            end_time: Hora de fin (ISO 8601)
            include_metrics: Incluir métricas de Cloud Monitoring
            include_audit_logs: Incluir Audit Logs
            include_pod_logs: Incluir logs de Pod
        
        Returns:
            Lista de eventos encontrados
        """
        print(f"\n🔍 Buscando eventos para: {component_name}")
        print(f"   Período: {start_time} a {end_time}\n")
        
        all_events = []
        
        # Buscar en Cloud Logging
        print("📝 Buscando en Cloud Logging...")
        logging_events = self._search_cloud_logging(
            component_name, start_time, end_time
        )
        all_events.extend(logging_events)
        print(f"   ✓ {len(logging_events)} eventos encontrados")
        
        # Buscar en Cloud Monitoring
        if include_metrics:
            print("📊 Buscando en Cloud Monitoring...")
            monitoring_events = self._search_cloud_monitoring(
                component_name, start_time, end_time
            )
            all_events.extend(monitoring_events)
            print(f"   ✓ {len(monitoring_events)} eventos encontrados")
        
        # Buscar en Audit Logs
        if include_audit_logs:
            print("🔐 Buscando en Audit Logs...")
            audit_events = self._search_audit_logs(
                component_name, start_time, end_time
            )
            all_events.extend(audit_events)
            print(f"   ✓ {len(audit_events)} eventos encontrados")
        
        # Buscar en Kubernetes Events
        print("☸️  Buscando en Kubernetes Events...")
        k8s_events = self._search_kubernetes_events(
            component_name, start_time, end_time
        )
        all_events.extend(k8s_events)
        print(f"   ✓ {len(k8s_events)} eventos encontrados")
        
        # Buscar logs de Pod
        if include_pod_logs:
            print("📋 Buscando logs de Pod...")
            pod_events = self._search_pod_logs(
                component_name, start_time, end_time
            )
            all_events.extend(pod_events)
            print(f"   ✓ {len(pod_events)} eventos encontrados")
        
        # Normalizar eventos
        print("\n⚙️  Normalizando eventos...")
        self.events = self._normalize_events(all_events)
        
        # Deduplicar
        print("🔄 Deduplicando eventos...")
        self.events = self._deduplicate_events(self.events)
        
        # Correlacionar
        print("🔗 Correlacionando eventos...")
        self.correlations = self._correlate_events(self.events)
        
        print(f"\n✅ Total de eventos únicos: {len(self.events)}")
        print(f"✅ Correlaciones encontradas: {len(self.correlations)}\n")
        
        return self.events
    
    def _search_cloud_logging(
        self, component_name: str, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """Busca eventos en Cloud Logging."""
        if not self.logging_client:
            return []
        
        try:
            filter_str = (
                f'resource.type="cloud_run_revision" OR resource.type="k8s_container" '
                f'AND (resource.labels.service_name="{component_name}" '
                f'OR resource.labels.pod_name="{component_name}") '
                f'AND timestamp>="{start_time}" AND timestamp<="{end_time}"'
            )
            
            entries = self.logging_client.list_entries(filter_=filter_str, page_size=100)
            
            events = []
            for entry in entries:
                events.append({
                    'timestamp': entry.timestamp.isoformat() if entry.timestamp else '',
                    'component_name': component_name,
                    'event_type': 'log',
                    'severity': entry.severity or 'INFO',
                    'message': entry.payload if isinstance(entry.payload, str) else str(entry.payload),
                    'source': 'cloud_logging',
                    'metadata': {
                        'log_name': entry.log_name,
                        'resource_type': entry.resource.type if entry.resource else None
                    }
                })
            
            return events
        except Exception as e:
            print(f"   ❌ Error en Cloud Logging: {e}")
            return []
    
    def _search_cloud_monitoring(
        self, component_name: str, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """Busca eventos en Cloud Monitoring."""
        if not self.monitoring_client:
            return []
        
        try:
            # Implementación básica
            return []
        except Exception as e:
            print(f"   ❌ Error en Cloud Monitoring: {e}")
            return []
    
    def _search_audit_logs(
        self, component_name: str, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """Busca eventos en Audit Logs."""
        if not self.logging_client:
            return []
        
        try:
            filter_str = (
                f'protoPayload.resourceName=~".*{component_name}.*" '
                f'AND timestamp>="{start_time}" AND timestamp<="{end_time}"'
            )
            
            entries = self.logging_client.list_entries(filter_=filter_str, page_size=50)
            
            events = []
            for entry in entries:
                events.append({
                    'timestamp': entry.timestamp.isoformat() if entry.timestamp else '',
                    'component_name': component_name,
                    'event_type': 'audit',
                    'severity': 'INFO',
                    'message': str(entry.payload),
                    'source': 'audit_logs',
                    'metadata': {}
                })
            
            return events
        except Exception as e:
            print(f"   ❌ Error en Audit Logs: {e}")
            return []
    
    def _search_kubernetes_events(
        self, component_name: str, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """Busca eventos en Kubernetes."""
        if not self.k8s_client:
            return []
        
        try:
            events = []
            
            # Buscar en todos los namespaces
            namespaces = self.k8s_client.list_namespace()
            
            for ns in namespaces.items:
                namespace = ns.metadata.name
                
                # Buscar eventos del componente
                k8s_events = self.k8s_client.list_namespaced_event(namespace)
                
                for event in k8s_events.items:
                    if component_name in event.involved_object.name:
                        events.append({
                            'timestamp': event.last_timestamp.isoformat() if event.last_timestamp else '',
                            'component_name': component_name,
                            'event_type': event.reason.lower() if event.reason else 'unknown',
                            'severity': 'WARNING' if event.type == 'Warning' else 'INFO',
                            'message': event.message or '',
                            'source': 'kubernetes_events',
                            'metadata': {
                                'pod_name': event.involved_object.name,
                                'namespace': namespace,
                                'reason': event.reason,
                                'count': event.count
                            }
                        })
            
            return events
        except Exception as e:
            print(f"   ❌ Error en Kubernetes Events: {e}")
            return []
    
    def _search_pod_logs(
        self, component_name: str, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """Busca logs de Pod."""
        if not self.k8s_client:
            return []
        
        try:
            events = []
            
            # Buscar en todos los namespaces
            namespaces = self.k8s_client.list_namespace()
            
            for ns in namespaces.items:
                namespace = ns.metadata.name
                
                # Buscar pods del componente
                pods = self.k8s_client.list_namespaced_pod(namespace)
                
                for pod in pods.items:
                    if component_name in pod.metadata.name:
                        try:
                            logs = self.k8s_client.read_namespaced_pod_log(
                                pod.metadata.name,
                                namespace,
                                tail_lines=100
                            )
                            
                            # Procesar logs
                            for line in logs.split('\n'):
                                if line.strip():
                                    events.append({
                                        'timestamp': datetime.now().isoformat(),
                                        'component_name': component_name,
                                        'event_type': 'pod_log',
                                        'severity': 'ERROR' if 'error' in line.lower() else 'INFO',
                                        'message': line,
                                        'source': 'pod_logs',
                                        'metadata': {
                                            'pod_name': pod.metadata.name,
                                            'namespace': namespace
                                        }
                                    })
                        except Exception:
                            pass
            
            return events
        except Exception as e:
            print(f"   ❌ Error en Pod Logs: {e}")
            return []
    
    def _normalize_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normaliza eventos a formato estándar."""
        normalized = []
        
        for event in events:
            normalized.append({
                'timestamp': event.get('timestamp', ''),
                'component_name': event.get('component_name', ''),
                'event_type': event.get('event_type', 'unknown'),
                'severity': event.get('severity', 'INFO'),
                'message': event.get('message', ''),
                'source': event.get('source', 'unknown'),
                'metadata': event.get('metadata', {})
            })
        
        # Ordenar por timestamp
        normalized.sort(key=lambda x: x['timestamp'])
        
        return normalized
    
    def _deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Elimina eventos duplicados."""
        seen = {}
        unique_events = []
        
        for event in events:
            key = (
                event['timestamp'],
                event['component_name'],
                event['event_type'],
                event['message'][:50]  # Primeros 50 caracteres
            )
            
            if key not in seen:
                seen[key] = True
                unique_events.append(event)
        
        return unique_events
    
    def _correlate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Correlaciona eventos relacionados."""
        correlations = []
        
        for i, event1 in enumerate(events):
            for event2 in events[i+1:]:
                # Verificar si están relacionados (mismo componente, timestamps cercanos)
                if event1['component_name'] == event2['component_name']:
                    try:
                        time1 = datetime.fromisoformat(event1['timestamp'].replace('Z', '+00:00'))
                        time2 = datetime.fromisoformat(event2['timestamp'].replace('Z', '+00:00'))
                        
                        time_diff = abs((time2 - time1).total_seconds())
                        
                        # Si están dentro de 5 minutos, están relacionados
                        if time_diff <= 300:
                            correlations.append({
                                'event1_index': i,
                                'event2_index': events.index(event2),
                                'time_diff_seconds': time_diff,
                                'relationship': 'related'
                            })
                    except Exception:
                        pass
        
        return correlations
    
    def generate_report(
        self,
        events: Optional[List[Dict[str, Any]]] = None,
        format: str = 'json'
    ) -> str:
        """
        Genera reporte en el formato especificado.
        
        Args:
            events: Lista de eventos (usa self.events si no se proporciona)
            format: Formato del reporte (json, csv, html, markdown)
        
        Returns:
            Reporte generado como string
        """
        if events is None:
            events = self.events
        
        if format == 'json':
            return self._generate_json_report(events)
        elif format == 'csv':
            return self._generate_csv_report(events)
        elif format == 'html':
            return self._generate_html_report(events)
        elif format == 'markdown':
            return self._generate_markdown_report(events)
        else:
            raise ValueError(f"Formato no soportado: {format}")
    
    def _generate_json_report(self, events: List[Dict[str, Any]]) -> str:
        """Genera reporte en JSON."""
        report = {
            'summary': {
                'total_events': len(events),
                'critical_events': len([e for e in events if e['severity'] == 'CRITICAL']),
                'warning_events': len([e for e in events if e['severity'] == 'WARNING']),
                'info_events': len([e for e in events if e['severity'] == 'INFO']),
            },
            'events': events,
            'correlations': self.correlations
        }
        
        return json.dumps(report, indent=2, default=str)
    
    def _generate_csv_report(self, events: List[Dict[str, Any]]) -> str:
        """Genera reporte en CSV."""
        if not events:
            return "timestamp,component_name,event_type,severity,message,source\n"
        
        lines = ["timestamp,component_name,event_type,severity,message,source"]
        
        for event in events:
            message = event['message'].replace(',', ';').replace('\n', ' ')[:100]
            line = f"{event['timestamp']},{event['component_name']},{event['event_type']},{event['severity']},{message},{event['source']}"
            lines.append(line)
        
        return '\n'.join(lines)
    
    def _generate_html_report(self, events: List[Dict[str, Any]]) -> str:
        """Genera reporte en HTML."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Event Tracker Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .summary { background: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .critical { background-color: #ffcccc; }
        .warning { background-color: #ffffcc; }
        .info { background-color: #ccffcc; }
    </style>
</head>
<body>
    <h1>Event Tracker Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Events:</strong> {total}</p>
        <p><strong>Critical:</strong> {critical}</p>
        <p><strong>Warning:</strong> {warning}</p>
        <p><strong>Info:</strong> {info}</p>
    </div>
    <h2>Events</h2>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Component</th>
            <th>Type</th>
            <th>Severity</th>
            <th>Message</th>
            <th>Source</th>
        </tr>
        {rows}
    </table>
</body>
</html>
        """
        
        rows = []
        for event in events:
            severity_class = event['severity'].lower()
            rows.append(f"""
        <tr class="{severity_class}">
            <td>{event['timestamp']}</td>
            <td>{event['component_name']}</td>
            <td>{event['event_type']}</td>
            <td>{event['severity']}</td>
            <td>{event['message'][:100]}</td>
            <td>{event['source']}</td>
        </tr>
            """)
        
        critical = len([e for e in events if e['severity'] == 'CRITICAL'])
        warning = len([e for e in events if e['severity'] == 'WARNING'])
        info = len([e for e in events if e['severity'] == 'INFO'])
        
        return html.format(
            total=len(events),
            critical=critical,
            warning=warning,
            info=info,
            rows='\n'.join(rows)
        )
    
    def _generate_markdown_report(self, events: List[Dict[str, Any]]) -> str:
        """Genera reporte en Markdown."""
        lines = [
            "# Event Tracker Report\n",
            "## Summary\n",
            f"- **Total Events**: {len(events)}",
            f"- **Critical**: {len([e for e in events if e['severity'] == 'CRITICAL'])}",
            f"- **Warning**: {len([e for e in events if e['severity'] == 'WARNING'])}",
            f"- **Info**: {len([e for e in events if e['severity'] == 'INFO'])}\n",
            "## Events\n",
            "| Timestamp | Component | Type | Severity | Message | Source |",
            "|-----------|-----------|------|----------|---------|--------|"
        ]
        
        for event in events:
            message = event['message'][:50].replace('|', '\\|')
            lines.append(
                f"| {event['timestamp']} | {event['component_name']} | "
                f"{event['event_type']} | {event['severity']} | {message} | {event['source']} |"
            )
        
        return '\n'.join(lines)


def main():
    """Función principal CLI."""
    parser = argparse.ArgumentParser(
        description='GCP Event Tracker - Rastreo de eventos y caídas de servicio'
    )
    
    parser.add_argument(
        '--component-name',
        required=True,
        help='Nombre del componente a rastrear'
    )
    parser.add_argument(
        '--project-id',
        required=True,
        help='ID del proyecto GCP'
    )
    parser.add_argument(
        '--start-time',
        required=True,
        help='Hora de inicio (ISO 8601, ej: 2026-07-13T00:00:00Z)'
    )
    parser.add_argument(
        '--end-time',
        required=True,
        help='Hora de fin (ISO 8601, ej: 2026-07-14T00:00:00Z)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'csv', 'html', 'markdown'],
        default='json',
        help='Formato del reporte (default: json)'
    )
    parser.add_argument(
        '--output-file',
        help='Archivo de salida (si no se especifica, se imprime en consola)'
    )
    parser.add_argument(
        '--credentials-file',
        help='Ruta al archivo de credenciales de Service Account'
    )
    
    args = parser.parse_args()
    
    # Crear tracker
    tracker = EventTracker(
        project_id=args.project_id,
        credentials_file=args.credentials_file
    )
    
    # Buscar eventos
    events = tracker.search_component_events(
        component_name=args.component_name,
        start_time=args.start_time,
        end_time=args.end_time
    )
    
    # Generar reporte
    report = tracker.generate_report(events, format=args.output_format)
    
    # Guardar o imprimir
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"✅ Reporte guardado en: {output_path}")
    else:
        print(report)


if __name__ == '__main__':
    main()
