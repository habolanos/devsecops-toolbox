# 🔍 Análisis Técnico: Deployments No Running en GCP

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Objetivo:** Implementar herramienta para listar deployments no running con diagnóstico automático

---

## 📋 Resumen Ejecutivo

Se requiere crear una **herramienta de diagnóstico avanzada** que identifique y analice todos los deployments en estado no running en GCP (GKE), proporcionando:

- ✅ Listado completo de deployments con estado != Running
- ✅ Análisis de causa raíz automático
- ✅ Logs de eventos del cluster y pods
- ✅ Recomendaciones de remediación
- ✅ Exportación en múltiples formatos (JSON, CSV, HTML)

**Valor DevSecOps:** Reducir MTTR (Mean Time To Recovery) en incidentes de deployment

---

## 🏗️ Arquitectura de Solución

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│         GCP Deployments Diagnostics Tool                    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  GKE Cluster     │  │  Cloud Logging   │                │
│  │  API             │  │  API             │                │
│  └────────┬─────────┘  └────────┬─────────┘                │
│           │                     │                           │
│           └──────────┬──────────┘                           │
│                      │                                      │
│           ┌──────────▼──────────┐                          │
│           │  Deployment         │                          │
│           │  Analyzer           │                          │
│           │  (Core Logic)       │                          │
│           └──────────┬──────────┘                          │
│                      │                                      │
│    ┌─────────────────┼─────────────────┐                  │
│    │                 │                 │                  │
│    ▼                 ▼                 ▼                  │
│ ┌────────┐      ┌────────┐      ┌────────┐              │
│ │ JSON   │      │  CSV   │      │ HTML   │              │
│ │ Export │      │ Export │      │ Report │              │
│ └────────┘      └────────┘      └────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

```
1. Obtener Deployments
   └─→ kubectl get deployments -A
   └─→ Filtrar: status.replicas != status.readyReplicas

2. Analizar Cada Deployment
   ├─→ Obtener Pod Status
   ├─→ Obtener Events
   ├─→ Obtener Logs
   └─→ Analizar Causas

3. Clasificar Problemas
   ├─→ Image Pull Errors
   ├─→ CrashLoopBackOff
   ├─→ Pending (recursos insuficientes)
   ├─→ ImagePullBackOff
   ├─→ CreateContainerConfigError
   └─→ Otros

4. Generar Reporte
   └─→ Exportar en formato solicitado
```

---

## 🔧 Análisis Técnico Detallado

### 1. Obtención de Datos

#### 1.1 Deployments No Running

```python
# Método 1: Usando kubectl
kubectl get deployments -A -o json | \
  jq '.items[] | select(.status.replicas != .status.readyReplicas)'

# Método 2: Usando Python + kubernetes client
from kubernetes import client, config

def get_non_running_deployments(cluster_name, project_id):
    """
    Obtiene todos los deployments con replicas no ready
    """
    config.load_kube_config()
    v1 = client.AppsV1Api()
    
    non_running = []
    for ns in client.CoreV1Api().list_namespace().items:
        deployments = v1.list_namespaced_deployment(ns.metadata.name)
        for dep in deployments.items:
            if dep.status.replicas != dep.status.ready_replicas:
                non_running.append({
                    'namespace': ns.metadata.name,
                    'name': dep.metadata.name,
                    'desired': dep.status.replicas,
                    'ready': dep.status.ready_replicas,
                    'updated': dep.status.updated_replicas,
                    'available': dep.status.available_replicas
                })
    return non_running
```

#### 1.2 Eventos del Cluster

```python
def get_deployment_events(namespace, deployment_name):
    """
    Obtiene eventos asociados a un deployment
    """
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace)
    
    relevant_events = [
        event for event in events.items
        if deployment_name in event.involved_object.name
        and event.involved_object.kind in ['Pod', 'Deployment']
    ]
    
    return sorted(
        relevant_events,
        key=lambda x: x.last_timestamp,
        reverse=True
    )[:10]  # Últimos 10 eventos
```

#### 1.3 Logs de Pods

```python
def get_pod_logs(namespace, pod_name, tail_lines=100):
    """
    Obtiene logs del pod para diagnóstico
    """
    v1 = client.CoreV1Api()
    try:
        logs = v1.read_namespaced_pod_log(
            pod_name,
            namespace,
            tail_lines=tail_lines
        )
        return logs
    except Exception as e:
        return f"Error obteniendo logs: {str(e)}"
```

#### 1.4 Cloud Logging (Stackdriver)

```python
from google.cloud import logging_v2

def get_deployment_logs_from_stackdriver(project_id, deployment_name, hours=1):
    """
    Obtiene logs de Cloud Logging para análisis
    """
    client = logging_v2.Client(project=project_id)
    
    filter_str = f"""
    resource.type="k8s_deployment"
    resource.labels.deployment_name="{deployment_name}"
    severity >= ERROR
    timestamp >= "{hours} hours ago"
    """
    
    entries = client.list_entries(filter_=filter_str)
    return list(entries)
```

---

### 2. Análisis de Causa Raíz

#### 2.1 Clasificación de Estados

```python
class DeploymentDiagnoser:
    """
    Analiza y diagnostica problemas en deployments
    """
    
    PROBLEM_PATTERNS = {
        'ImagePullBackOff': {
            'keywords': ['image', 'pull', 'failed', 'unauthorized'],
            'severity': 'HIGH',
            'category': 'Image Registry'
        },
        'CrashLoopBackOff': {
            'keywords': ['crash', 'exit code', 'panic', 'segfault'],
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
    
    def diagnose_deployment(self, deployment_info, events, logs):
        """
        Realiza diagnóstico completo del deployment
        """
        diagnosis = {
            'deployment': deployment_info['name'],
            'namespace': deployment_info['namespace'],
            'status': self._determine_status(deployment_info),
            'root_cause': self._analyze_root_cause(events, logs),
            'recommendations': self._generate_recommendations(events, logs),
            'severity': self._calculate_severity(events, logs)
        }
        return diagnosis
    
    def _determine_status(self, deployment_info):
        """Determina el estado específico del deployment"""
        desired = deployment_info.get('desired', 0)
        ready = deployment_info.get('ready', 0)
        
        if ready == 0 and desired > 0:
            return 'NO_REPLICAS_READY'
        elif ready < desired:
            return 'PARTIAL_REPLICAS'
        else:
            return 'UNKNOWN'
    
    def _analyze_root_cause(self, events, logs):
        """Analiza eventos y logs para identificar causa raíz"""
        causes = []
        
        # Analizar eventos
        for event in events:
            reason = event.reason
            message = event.message
            
            for problem, pattern in self.PROBLEM_PATTERNS.items():
                if any(kw in message.lower() for kw in pattern['keywords']):
                    causes.append({
                        'type': problem,
                        'message': message,
                        'timestamp': event.last_timestamp,
                        'severity': pattern['severity']
                    })
        
        # Analizar logs
        if logs:
            for problem, pattern in self.PROBLEM_PATTERNS.items():
                if any(kw in logs.lower() for kw in pattern['keywords']):
                    causes.append({
                        'type': problem,
                        'source': 'Pod Logs',
                        'severity': pattern['severity']
                    })
        
        return causes
    
    def _generate_recommendations(self, events, logs):
        """Genera recomendaciones basadas en el diagnóstico"""
        recommendations = []
        
        # Analizar cada causa y generar recomendación
        for event in events:
            if 'ImagePullBackOff' in event.reason:
                recommendations.append({
                    'action': 'Verificar imagen Docker',
                    'steps': [
                        'Validar que la imagen existe en el registry',
                        'Verificar credenciales de acceso',
                        'Revisar política de pull de imágenes',
                        'Considerar usar imagePullPolicy: IfNotPresent'
                    ]
                })
            elif 'CrashLoopBackOff' in event.reason:
                recommendations.append({
                    'action': 'Analizar logs de aplicación',
                    'steps': [
                        'Revisar logs del pod para errores',
                        'Verificar configuración de aplicación',
                        'Validar variables de entorno',
                        'Revisar health checks'
                    ]
                })
            elif 'Pending' in event.reason:
                recommendations.append({
                    'action': 'Aumentar recursos del cluster',
                    'steps': [
                        'Revisar requests/limits del deployment',
                        'Escalar nodos del cluster',
                        'Considerar usar Horizontal Pod Autoscaler',
                        'Revisar node selectors y affinities'
                    ]
                })
        
        return recommendations
    
    def _calculate_severity(self, events, logs):
        """Calcula severidad general del problema"""
        severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        max_severity = 'LOW'
        
        for event in events:
            for problem, pattern in self.PROBLEM_PATTERNS.items():
                if problem in event.reason:
                    if severities.index(pattern['severity']) > severities.index(max_severity):
                        max_severity = pattern['severity']
        
        return max_severity
```

---

### 3. Exportación de Datos

#### 3.1 JSON Export

```python
import json
from datetime import datetime

def export_to_json(diagnosis_results, output_file):
    """Exporta resultados a JSON"""
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_deployments_checked': len(diagnosis_results),
        'non_running_count': len([d for d in diagnosis_results if d['status'] != 'RUNNING']),
        'critical_count': len([d for d in diagnosis_results if d['severity'] == 'CRITICAL']),
        'deployments': diagnosis_results
    }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
```

#### 3.2 CSV Export

```python
import csv

def export_to_csv(diagnosis_results, output_file):
    """Exporta resultados a CSV"""
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'namespace',
            'deployment',
            'status',
            'severity',
            'root_cause',
            'recommendations'
        ])
        
        writer.writeheader()
        for result in diagnosis_results:
            writer.writerow({
                'namespace': result['namespace'],
                'deployment': result['deployment'],
                'status': result['status'],
                'severity': result['severity'],
                'root_cause': '; '.join([c['type'] for c in result['root_cause']]),
                'recommendations': '; '.join([r['action'] for r in result['recommendations']])
            })
```

#### 3.3 HTML Report

```python
from jinja2 import Template

def export_to_html(diagnosis_results, output_file):
    """Exporta resultados a reporte HTML interactivo"""
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GCP Deployments Diagnostics Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .critical { background-color: #ff6b6b; color: white; }
            .high { background-color: #ffa500; }
            .medium { background-color: #ffeb3b; }
            .low { background-color: #4caf50; color: white; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #333; color: white; }
            .summary { background-color: #f0f0f0; padding: 15px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>GCP Deployments Diagnostics Report</h1>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total Deployments: {{ total }}</p>
            <p>Non-Running: {{ non_running }}</p>
            <p>Critical Issues: {{ critical }}</p>
        </div>
        
        <table>
            <tr>
                <th>Namespace</th>
                <th>Deployment</th>
                <th>Status</th>
                <th>Severity</th>
                <th>Root Cause</th>
                <th>Recommendations</th>
            </tr>
            {% for deployment in deployments %}
            <tr class="{{ deployment.severity.lower() }}">
                <td>{{ deployment.namespace }}</td>
                <td>{{ deployment.deployment }}</td>
                <td>{{ deployment.status }}</td>
                <td>{{ deployment.severity }}</td>
                <td>
                    {% for cause in deployment.root_cause %}
                    <div>{{ cause.type }}: {{ cause.message }}</div>
                    {% endfor %}
                </td>
                <td>
                    {% for rec in deployment.recommendations %}
                    <div>{{ rec.action }}</div>
                    {% endfor %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    template = Template(html_template)
    html_content = template.render(
        total=len(diagnosis_results),
        non_running=len([d for d in diagnosis_results if d['status'] != 'RUNNING']),
        critical=len([d for d in diagnosis_results if d['severity'] == 'CRITICAL']),
        deployments=diagnosis_results
    )
    
    with open(output_file, 'w') as f:
        f.write(html_content)
```

---

## 📊 Matriz de Problemas Comunes

| Problema | Causa | Síntomas | Solución |
|----------|-------|----------|----------|
| **ImagePullBackOff** | Imagen no existe o credenciales inválidas | Pod pending, eventos de pull fallido | Verificar registry, credenciales, imagePullPolicy |
| **CrashLoopBackOff** | Aplicación se reinicia continuamente | Pod restart count alto, exit codes | Revisar logs, configuración, health checks |
| **Pending** | Recursos insuficientes | Pod no puede ser scheduled | Escalar cluster, revisar requests/limits |
| **CreateContainerConfigError** | Configuración inválida (Secrets, ConfigMaps) | Pod no inicia, errores de mount | Verificar Secrets/ConfigMaps, permisos |
| **ImagePullError** | Imagen no encontrada en registry | Pull fallido, imagen no existe | Verificar nombre de imagen, registry |
| **OOMKilled** | Memoria insuficiente | Pod termina con exit code 137 | Aumentar memory limit, revisar aplicación |
| **Evicted** | Presión de recursos en nodo | Pod removido del nodo | Escalar cluster, revisar resource usage |

---

## 🔐 Consideraciones de Seguridad

### 1. Acceso a Credenciales

```python
# ✅ CORRECTO: Usar Service Account con permisos mínimos
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deployment-diagnostics
  namespace: kube-system

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: deployment-diagnostics
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods", "events"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: deployment-diagnostics
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: deployment-diagnostics
subjects:
- kind: ServiceAccount
  name: deployment-diagnostics
  namespace: kube-system
```

### 2. Manejo de Logs Sensibles

```python
# Sanitizar logs antes de exportar
def sanitize_logs(logs):
    """Elimina información sensible de logs"""
    sensitive_patterns = [
        r'password["\']?\s*[:=]\s*["\']?[^"\']*["\']?',
        r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\']*["\']?',
        r'token["\']?\s*[:=]\s*["\']?[^"\']*["\']?',
    ]
    
    import re
    sanitized = logs
    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern, 'REDACTED', sanitized, flags=re.IGNORECASE)
    
    return sanitized
```

---

## 📈 Métricas de Éxito

| Métrica | Target | Beneficio |
|---------|--------|----------|
| **MTTR (Mean Time To Recovery)** | < 15 min | Reducir downtime |
| **Detección Automática** | 100% de problemas | Visibilidad completa |
| **Precisión de Diagnóstico** | > 95% | Confianza en recomendaciones |
| **Cobertura de Clusters** | 100% | Monitoreo integral |
| **Tiempo de Análisis** | < 30 seg | Respuesta rápida |

---

## 🚀 Roadmap de Implementación

### Fase 1: MVP (2 semanas)
- ✅ Obtener deployments no running
- ✅ Análisis básico de eventos
- ✅ Exportación JSON

### Fase 2: Análisis Avanzado (2 semanas)
- ✅ Análisis de logs
- ✅ Clasificación de problemas
- ✅ Recomendaciones automáticas

### Fase 3: Integración (1 semana)
- ✅ Exportación CSV/HTML
- ✅ Integración con alertas
- ✅ Dashboard web

### Fase 4: Optimización (1 semana)
- ✅ Machine Learning para predicción
- ✅ Histórico de problemas
- ✅ Análisis de tendencias

---

**Análisis Técnico Completado** ✅

**Próximo:** Diseño de Implementación
