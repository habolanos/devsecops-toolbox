# 🏗️ Diseño de Implementación: Deployments Off Analyzer

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Objetivo:** Especificación técnica para implementación de herramienta

---

## 📋 Resumen de Diseño

### Nombre de la Herramienta
**GCP Deployments Off Analyzer** (Tool 40)

### Ubicación en Proyecto
```
scm/gcp/deployments_off/
├── gcp_deployments_off_analyzer.py    (Script principal)
├── requirements.txt                    (Dependencias)
└── README.md                          (Documentación)
```

### Integración en tools.py
```python
"40": {
    "name": "Deployments Off Analyzer",
    "description": "Analiza deployments no running con diagnóstico automático",
    "path": "deployments_off/gcp_deployments_off_analyzer.py",
    "args": ["--project", "--cluster", "--namespace", "-o", "--format"],
    "requirements": None,
    "group": "kubernetes",
    "status": "ready"
}
```

---

## 🔧 Especificación Técnica

### 1. Estructura del Script

```python
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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Rich para UI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn
from rich.text import Text

# Kubernetes
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

# Google Cloud
from google.cloud import logging_v2
from google.auth import default

# Logging
import logging
```

### 2. Clases Principales

#### 2.1 DeploymentAnalyzer

```python
class DeploymentAnalyzer:
    """
    Analiza deployments no running en GKE
    """
    
    def __init__(self, project_id: str, cluster_name: str, namespace: Optional[str] = None):
        self.project_id = project_id
        self.cluster_name = cluster_name
        self.namespace = namespace
        self.console = Console()
        self.logger = logging.getLogger(__name__)
        
        # Inicializar clientes
        self._init_kubernetes_client()
        self._init_logging_client()
    
    def _init_kubernetes_client(self):
        """Inicializa cliente de Kubernetes"""
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
    
    def _init_logging_client(self):
        """Inicializa cliente de Cloud Logging"""
        try:
            self.logging_client = logging_v2.Client(project=self.project_id)
        except Exception as e:
            self.logger.warning(f"No se pudo inicializar Cloud Logging: {e}")
            self.logging_client = None
    
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
            self.logger.error(f"Error obteniendo namespaces: {e}")
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
            self.logger.error(f"Error en namespace {namespace}: {e}")
        
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
            self.logger.error(f"Error analizando pods: {e}")
        
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
            self.logger.error(f"Error obteniendo eventos: {e}")
        
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
```

### 3. Funciones de Exportación

```python
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
    
    @staticmethod
    def export_html(results: List[Dict], output_file: str):
        """Exporta a HTML interactivo"""
        # Implementación similar al análisis técnico
        pass
```

### 4. Función Main

```python
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
        choices=['json', 'csv', 'html'],
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
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console = Console()
    
    try:
        # Crear analizador
        analyzer = DeploymentAnalyzer(
            args.project,
            args.cluster,
            args.namespace
        )
        
        # Analizar deployments
        results = analyzer.analyze_all_deployments()
        
        # Mostrar resultados
        console.print(Panel(
            f"[bold]Total Deployments No Running: {len(results)}[/bold]",
            title="Analysis Results"
        ))
        
        # Exportar
        exporter = ReportExporter()
        
        if args.output == 'json':
            output_file = args.output_file or f"deployments_off_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            exporter.export_json(results, output_file)
        elif args.output == 'csv':
            output_file = args.output_file or f"deployments_off_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            exporter.export_csv(results, output_file)
        elif args.output == 'html':
            output_file = args.output_file or f"deployments_off_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            exporter.export_html(results, output_file)
        
        console.print(f"[green]✓ Reporte exportado a: {output_file}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

---

## 📦 Dependencias

```
# requirements.txt
kubernetes>=20.0.0
google-cloud-logging>=3.0.0
google-auth>=2.0.0
rich>=10.0.0
jinja2>=3.0.0
```

---

## 🧪 Casos de Prueba

### Test 1: Deployment con ImagePullBackOff
```bash
python gcp_deployments_off_analyzer.py \
  --project my-project \
  --cluster my-cluster \
  --namespace default \
  -o json
```

**Resultado esperado:**
- Detectar deployment con ImagePullBackOff
- Identificar causa: imagen no encontrada
- Recomendar: verificar registry y credenciales

### Test 2: Deployment con CrashLoopBackOff
```bash
python gcp_deployments_off_analyzer.py \
  --project my-project \
  --cluster my-cluster \
  -o html
```

**Resultado esperado:**
- Detectar deployment con CrashLoopBackOff
- Identificar causa: aplicación se reinicia
- Recomendar: revisar logs y configuración

### Test 3: Exportación CSV
```bash
python gcp_deployments_off_analyzer.py \
  --project my-project \
  --cluster my-cluster \
  -o csv \
  --output-file report.csv
```

**Resultado esperado:**
- Generar archivo CSV con todos los deployments
- Incluir severidad y recomendaciones

---

## 📊 Salida Esperada

### JSON Format
```json
{
  "timestamp": "2026-07-08T14:30:00",
  "total_deployments": 3,
  "critical_count": 1,
  "high_count": 2,
  "deployments": [
    {
      "namespace": "production",
      "deployment": "api-server",
      "severity": "CRITICAL",
      "replica_status": {
        "desired": 3,
        "ready": 0,
        "updated": 0,
        "available": 0
      },
      "root_causes": [
        {
          "type": "CrashLoopBackOff",
          "category": "Application Error",
          "message": "Back-off restarting failed container",
          "source": "Event"
        }
      ],
      "recommendations": [
        {
          "action": "Analizar logs de aplicación",
          "priority": "CRITICAL",
          "steps": [...]
        }
      ]
    }
  ]
}
```

---

**Diseño de Implementación Completado** ✅

**Próximo:** Plan de Integración
