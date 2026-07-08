#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GCP Deployments Off Analyzer

Analiza todos los deployments en estado no running en un cluster GKE,
proporcionando diagnóstico automático y recomendaciones.

Uso:
    python gcp_deployments_off_analyzer.py --project PROJECT_ID --cluster CLUSTER_NAME
    python gcp_deployments_off_analyzer.py --project PROJECT_ID --cluster CLUSTER_NAME -o json
    python gcp_deployments_off_analyzer.py --project PROJECT_ID --cluster CLUSTER_NAME --namespace production
"""

import argparse
import json
import csv
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Rich para UI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn
from rich.text import Text

# Kubernetes
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentAnalyzer:
    """
    Analiza deployments no running en GKE
    """
    
    PROBLEM_PATTERNS = {
        'ImagePullBackOff': {
            'keywords': ['image', 'pull', 'failed', 'unauthorized'],
            'severity': 'HIGH',
            'category': 'Image Registry'
        },
        'CrashLoopBackOff': {
            'keywords': ['crash', 'exit code', 'panic'],
            'severity': 'CRITICAL',
            'category': 'Application Error'
        },
        'Pending': {
            'keywords': ['insufficient', 'resource', 'memory', 'cpu'],
            'severity': 'HIGH',
            'category': 'Resource Constraint'
        },
        'CreateContainerConfigError': {
            'keywords': ['config', 'secret', 'configmap', 'mount'],
            'severity': 'HIGH',
            'category': 'Configuration Error'
        },
        'ImagePullError': {
            'keywords': ['image', 'not found', 'repository'],
            'severity': 'CRITICAL',
            'category': 'Image Registry'
        }
    }
    
    def __init__(self, project_id: str, cluster_name: str, namespace: Optional[str] = None, debug: bool = False):
        self.project_id = project_id
        self.cluster_name = cluster_name
        self.namespace = namespace
        self.console = Console()
        self.debug = debug
        
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Inicializar clientes
        self._init_kubernetes_client()
    
    def _init_kubernetes_client(self):
        """Inicializa cliente de Kubernetes"""
        try:
            config.load_incluster_config()
            self.console.print("[green]✓ Usando in-cluster config[/green]")
        except:
            try:
                config.load_kube_config()
                self.console.print("[green]✓ Usando kubeconfig local[/green]")
            except Exception as e:
                self.console.print(f"[red]✗ Error inicializando Kubernetes client: {e}[/red]")
                sys.exit(1)
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
    
    def analyze_all_deployments(self) -> List[Dict]:
        """
        Analiza todos los deployments no running
        """
        results = []
        
        with Progress(
            SpinnerColumn(),
            BarColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "[cyan]Analizando deployments...",
                total=None
            )
            
            # Obtener namespaces
            namespaces = self._get_namespaces()
            
            for ns in namespaces:
                progress.update(task, description=f"[cyan]Analizando {ns}...")
                
                # Obtener deployments no running
                non_running = self._get_non_running_deployments(ns)
                
                for dep in non_running:
                    # Analizar cada deployment
                    analysis = self._analyze_deployment(ns, dep)
                    results.append(analysis)
            
            progress.update(task, completed=True)
        
        return results
    
    def _get_namespaces(self) -> List[str]:
        """Obtiene lista de namespaces"""
        if self.namespace:
            return [self.namespace]
        
        try:
            namespaces = self.v1.list_namespace()
            return [ns.metadata.name for ns in namespaces.items]
        except ApiException as e:
            logger.error(f"Error obteniendo namespaces: {e}")
            return []
    
    def _get_non_running_deployments(self, namespace: str) -> List[Dict]:
        """Obtiene deployments con replicas no ready"""
        non_running = []
        
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace)
            
            for dep in deployments.items:
                desired = dep.status.replicas or 0
                ready = dep.status.ready_replicas or 0
                
                if ready < desired or desired == 0:
                    non_running.append({
                        'name': dep.metadata.name,
                        'namespace': namespace,
                        'desired': desired,
                        'ready': ready,
                        'updated': dep.status.updated_replicas or 0,
                        'available': dep.status.available_replicas or 0,
                        'conditions': dep.status.conditions or []
                    })
        
        except ApiException as e:
            logger.error(f"Error en namespace {namespace}: {e}")
        
        return non_running
    
    def _analyze_deployment(self, namespace: str, deployment: Dict) -> Dict:
        """Realiza análisis completo de un deployment"""
        
        analysis = {
            'namespace': namespace,
            'deployment': deployment['name'],
            'timestamp': datetime.utcnow().isoformat(),
            'replica_status': {
                'desired': deployment['desired'],
                'ready': deployment['ready'],
                'updated': deployment['updated'],
                'available': deployment['available']
            },
            'pods': self._analyze_pods(namespace, deployment['name']),
            'events': self._get_events(namespace, deployment['name']),
            'root_causes': [],
            'recommendations': [],
            'severity': 'LOW'
        }
        
        # Analizar causas
        analysis['root_causes'] = self._identify_root_causes(
            namespace,
            deployment['name'],
            analysis['pods'],
            analysis['events']
        )
        
        # Generar recomendaciones
        analysis['recommendations'] = self._generate_recommendations(
            analysis['root_causes']
        )
        
        # Calcular severidad
        analysis['severity'] = self._calculate_severity(analysis['root_causes'])
        
        return analysis
    
    def _analyze_pods(self, namespace: str, deployment_name: str) -> List[Dict]:
        """Analiza pods del deployment"""
        pods_info = []
        
        try:
            pods = self.v1.list_namespaced_pod(namespace)
            
            for pod in pods.items:
                if deployment_name in pod.metadata.name:
                    pod_info = {
                        'name': pod.metadata.name,
                        'phase': pod.status.phase,
                        'conditions': [],
                        'container_statuses': [],
                        'restart_count': 0
                    }
                    
                    # Condiciones
                    if pod.status.conditions:
                        pod_info['conditions'] = [
                            {
                                'type': c.type,
                                'status': c.status,
                                'reason': c.reason,
                                'message': c.message
                            }
                            for c in pod.status.conditions
                        ]
                    
                    # Estado de contenedores
                    if pod.status.container_statuses:
                        for cs in pod.status.container_statuses:
                            pod_info['container_statuses'].append({
                                'name': cs.name,
                                'ready': cs.ready,
                                'restart_count': cs.restart_count,
                                'state': self._get_container_state(cs)
                            })
                            pod_info['restart_count'] = max(
                                pod_info['restart_count'],
                                cs.restart_count
                            )
                    
                    pods_info.append(pod_info)
        
        except ApiException as e:
            logger.error(f"Error analizando pods: {e}")
        
        return pods_info
    
    def _get_container_state(self, container_status) -> Dict:
        """Extrae estado del contenedor"""
        if container_status.state.running:
            return {'type': 'Running'}
        elif container_status.state.waiting:
            return {
                'type': 'Waiting',
                'reason': container_status.state.waiting.reason,
                'message': container_status.state.waiting.message
            }
        elif container_status.state.terminated:
            return {
                'type': 'Terminated',
                'exit_code': container_status.state.terminated.exit_code,
                'reason': container_status.state.terminated.reason,
                'message': container_status.state.terminated.message
            }
        return {'type': 'Unknown'}
    
    def _get_events(self, namespace: str, deployment_name: str) -> List[Dict]:
        """Obtiene eventos del deployment"""
        events = []
        
        try:
            k8s_events = self.v1.list_namespaced_event(namespace)
            
            for event in k8s_events.items:
                if deployment_name in event.involved_object.name:
                    events.append({
                        'timestamp': event.last_timestamp.isoformat() if event.last_timestamp else None,
                        'reason': event.reason,
                        'message': event.message,
                        'type': event.type,
                        'count': event.count
                    })
            
            # Ordenar por timestamp descendente
            events.sort(
                key=lambda x: x['timestamp'] or '',
                reverse=True
            )
        
        except ApiException as e:
            logger.error(f"Error obteniendo eventos: {e}")
        
        return events[:10]  # Últimos 10 eventos
    
    def _identify_root_causes(self, namespace: str, deployment_name: str,
                             pods: List[Dict], events: List[Dict]) -> List[Dict]:
        """Identifica causas raíz del problema"""
        causes = []
        
        # Analizar eventos
        for event in events:
            cause = self._classify_event(event)
            if cause:
                causes.append(cause)
        
        # Analizar estado de pods
        for pod in pods:
            for condition in pod.get('conditions', []):
                if condition['status'] != 'True':
                    causes.append({
                        'type': condition['type'],
                        'reason': condition['reason'],
                        'message': condition['message'],
                        'source': 'Pod Condition'
                    })
            
            for cs in pod.get('container_statuses', []):
                if cs['state']['type'] != 'Running':
                    causes.append({
                        'type': cs['state']['type'],
                        'reason': cs['state'].get('reason', 'Unknown'),
                        'message': cs['state'].get('message', ''),
                        'source': 'Container State'
                    })
        
        # Eliminar duplicados
        unique_causes = []
        seen = set()
        for cause in causes:
            key = (cause['type'], cause['reason'])
            if key not in seen:
                unique_causes.append(cause)
                seen.add(key)
        
        return unique_causes
    
    def _classify_event(self, event: Dict) -> Optional[Dict]:
        """Clasifica un evento"""
        reason = event['reason']
        message = event['message']
        
        classifications = {
            'ImagePullBackOff': 'Image Registry',
            'ImagePullError': 'Image Registry',
            'ErrImagePull': 'Image Registry',
            'CrashLoopBackOff': 'Application Error',
            'BackOff': 'Application Error',
            'Failed': 'Application Error',
            'FailedScheduling': 'Resource Constraint',
            'Pending': 'Resource Constraint',
            'Insufficient': 'Resource Constraint',
            'FailedCreatePodSandbox': 'Infrastructure Error',
            'FailedMount': 'Configuration Error',
            'ConfigError': 'Configuration Error'
        }
        
        for key, category in classifications.items():
            if key in reason:
                return {
                    'type': reason,
                    'category': category,
                    'message': message,
                    'source': 'Event'
                }
        
        return None
    
    def _generate_recommendations(self, causes: List[Dict]) -> List[Dict]:
        """Genera recomendaciones basadas en causas"""
        recommendations = []
        seen_types = set()
        
        for cause in causes:
            cause_type = cause['type']
            
            if cause_type in seen_types:
                continue
            
            seen_types.add(cause_type)
            
            if 'ImagePull' in cause_type:
                recommendations.append({
                    'action': 'Verificar imagen Docker',
                    'priority': 'HIGH',
                    'steps': [
                        'Validar que la imagen existe en el registry',
                        'Verificar credenciales de acceso (imagePullSecrets)',
                        'Revisar política de pull de imágenes (imagePullPolicy)',
                        'Considerar usar imagePullPolicy: IfNotPresent',
                        'Verificar que el registry es accesible desde el cluster'
                    ]
                })
            
            elif 'CrashLoopBackOff' in cause_type or 'BackOff' in cause_type:
                recommendations.append({
                    'action': 'Analizar logs de aplicación',
                    'priority': 'CRITICAL',
                    'steps': [
                        'Ejecutar: kubectl logs POD_NAME -n NAMESPACE',
                        'Revisar logs del pod para errores',
                        'Verificar configuración de aplicación',
                        'Validar variables de entorno',
                        'Revisar health checks (liveness/readiness probes)',
                        'Considerar aumentar initialDelaySeconds'
                    ]
                })
            
            elif 'FailedScheduling' in cause_type or 'Insufficient' in cause_type:
                recommendations.append({
                    'action': 'Aumentar recursos del cluster',
                    'priority': 'HIGH',
                    'steps': [
                        'Revisar requests/limits del deployment',
                        'Ejecutar: kubectl top nodes',
                        'Escalar nodos del cluster',
                        'Considerar usar Horizontal Pod Autoscaler',
                        'Revisar node selectors y affinities',
                        'Considerar usar pod disruption budgets'
                    ]
                })
            
            elif 'FailedMount' in cause_type or 'ConfigError' in cause_type:
                recommendations.append({
                    'action': 'Verificar configuración',
                    'priority': 'HIGH',
                    'steps': [
                        'Verificar que Secrets existen: kubectl get secrets -n NAMESPACE',
                        'Verificar que ConfigMaps existen: kubectl get configmaps -n NAMESPACE',
                        'Revisar permisos de acceso',
                        'Validar rutas de mount en el deployment',
                        'Considerar usar subPath para archivos específicos'
                    ]
                })
        
        return recommendations
    
    def _calculate_severity(self, causes: List[Dict]) -> str:
        """Calcula severidad general"""
        if not causes:
            return 'LOW'
        
        critical_keywords = ['CrashLoop', 'ImagePull', 'FailedScheduling']
        
        for cause in causes:
            for keyword in critical_keywords:
                if keyword in cause['type']:
                    return 'CRITICAL'
        
        return 'HIGH' if causes else 'LOW'
    
    def print_results_table(self, results: List[Dict]):
        """Imprime tabla de resultados"""
        if not results:
            self.console.print("[green]✓ No hay deployments no running[/green]")
            return
        
        table = Table(title="Deployments No Running", show_header=True, header_style="bold cyan")
        table.add_column("Namespace", style="magenta")
        table.add_column("Deployment", style="cyan")
        table.add_column("Severity", style="red")
        table.add_column("Desired", style="yellow")
        table.add_column("Ready", style="yellow")
        table.add_column("Root Cause", style="white")
        
        for result in results:
            severity_color = "red" if result['severity'] == 'CRITICAL' else "yellow"
            causes = '; '.join([c['type'] for c in result['root_causes']]) or 'Unknown'
            
            table.add_row(
                result['namespace'],
                result['deployment'],
                f"[{severity_color}]{result['severity']}[/{severity_color}]",
                str(result['replica_status']['desired']),
                str(result['replica_status']['ready']),
                causes[:50]
            )
        
        self.console.print(table)


class ReportExporter:
    """Exporta resultados en múltiples formatos"""
    
    @staticmethod
    def export_json(results: List[Dict], output_file: str):
        """Exporta a JSON"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_deployments': len(results),
            'critical_count': len([r for r in results if r['severity'] == 'CRITICAL']),
            'high_count': len([r for r in results if r['severity'] == 'HIGH']),
            'deployments': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
    
    @staticmethod
    def export_csv(results: List[Dict], output_file: str):
        """Exporta a CSV"""
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'namespace',
                'deployment',
                'severity',
                'desired_replicas',
                'ready_replicas',
                'root_causes',
                'recommendations'
            ])
            
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'namespace': result['namespace'],
                    'deployment': result['deployment'],
                    'severity': result['severity'],
                    'desired_replicas': result['replica_status']['desired'],
                    'ready_replicas': result['replica_status']['ready'],
                    'root_causes': '; '.join([c['type'] for c in result['root_causes']]),
                    'recommendations': '; '.join([r['action'] for r in result['recommendations']])
                })


def main():
    parser = argparse.ArgumentParser(
        description='Analiza deployments no running en GCP GKE'
    )
    
    parser.add_argument(
        '--project',
        required=True,
        help='ID del proyecto GCP'
    )
    
    parser.add_argument(
        '--cluster',
        required=True,
        help='Nombre del cluster GKE'
    )
    
    parser.add_argument(
        '--namespace',
        default=None,
        help='Namespace específico (opcional)'
    )
    
    parser.add_argument(
        '-o', '--output',
        choices=['json', 'csv'],
        default='json',
        help='Formato de salida'
    )
    
    parser.add_argument(
        '--output-file',
        default=None,
        help='Archivo de salida (opcional)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Modo debug'
    )
    
    args = parser.parse_args()
    
    console = Console()
    
    try:
        # Crear analizador
        analyzer = DeploymentAnalyzer(
            args.project,
            args.cluster,
            args.namespace,
            args.debug
        )
        
        # Analizar deployments
        results = analyzer.analyze_all_deployments()
        
        # Mostrar resultados en tabla
        analyzer.print_results_table(results)
        
        # Mostrar resumen
        console.print(Panel(
            f"[bold]Total Deployments No Running: {len(results)}[/bold]\n"
            f"Critical: {len([r for r in results if r['severity'] == 'CRITICAL'])}\n"
            f"High: {len([r for r in results if r['severity'] == 'HIGH'])}",
            title="Analysis Summary"
        ))
        
        # Exportar
        exporter = ReportExporter()
        
        if args.output == 'json':
            output_file = args.output_file or f"outcome/deployments_off_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            exporter.export_json(results, output_file)
            console.print(f"[green]✓ Reporte JSON exportado a: {output_file}[/green]")
        
        elif args.output == 'csv':
            output_file = args.output_file or f"outcome/deployments_off_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            exporter.export_csv(results, output_file)
            console.print(f"[green]✓ Reporte CSV exportado a: {output_file}[/green]")
    
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
