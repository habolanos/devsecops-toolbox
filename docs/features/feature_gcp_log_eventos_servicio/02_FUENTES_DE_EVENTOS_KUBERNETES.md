# 🐳 Fuentes de Eventos en Kubernetes

## 1. Kubernetes Events API

### Descripción
API nativa de Kubernetes que registra eventos de Pod, Node, Deployment, etc.

### Tipos de Eventos

#### 1.1 Pod Events
```
type: Normal | Warning | Error
reason: Started | Failed | CrashLoopBackOff | ImagePullBackOff | Pending
involvedObject.kind: Pod
involvedObject.name: my-pod
```

**Información capturada**:
- Inicio/parada de Pod
- Errores de imagen
- Problemas de recursos
- Eventos de salud

#### 1.2 Node Events
```
type: Normal | Warning | Error
reason: NodeNotReady | NodeReady | KubeletNotReady | KubeletReady
involvedObject.kind: Node
involvedObject.name: node-1
```

**Información capturada**:
- Estado del nodo
- Problemas de conectividad
- Eventos de hardware
- Cambios de capacidad

#### 1.3 Deployment Events
```
type: Normal | Warning
reason: ScalingReplicaSet | DeploymentGeneration
involvedObject.kind: Deployment
involvedObject.name: my-deployment
```

**Información capturada**:
- Escalado automático
- Cambios de versión
- Problemas de actualización
- Eventos de replicación

### API de Kubernetes Events

**Endpoint**: `https://kubernetes.default.svc/api/v1/namespaces/{namespace}/events`

**Métodos principales**:

```bash
# Listar eventos de un namespace
kubectl get events -n default

# Listar eventos de un pod específico
kubectl describe pod my-pod -n default

# Listar eventos ordenados por tiempo
kubectl get events -n default --sort-by='.lastTimestamp'

# Listar eventos con más detalles
kubectl get events -n default -o wide

# Listar eventos de todos los namespaces
kubectl get events -A

# Filtrar por tipo
kubectl get events -n default --field-selector type=Warning

# Filtrar por razón
kubectl get events -n default --field-selector reason=CrashLoopBackOff
```

**Filtros útiles**:

```bash
# Por Pod
kubectl get events -n default --field-selector involvedObject.name=my-pod

# Por Node
kubectl get events -n default --field-selector involvedObject.name=node-1

# Por tipo de evento
kubectl get events -n default --field-selector type=Warning

# Por razón
kubectl get events -n default --field-selector reason=Failed

# Combinado
kubectl get events -n default \
  --field-selector involvedObject.name=my-pod,type=Warning
```

### API REST de Kubernetes

```python
# Listar eventos
GET /api/v1/namespaces/{namespace}/events

# Obtener evento específico
GET /api/v1/namespaces/{namespace}/events/{eventName}

# Listar eventos de todos los namespaces
GET /api/v1/events
```

**Respuesta JSON**:

```json
{
  "apiVersion": "v1",
  "kind": "Event",
  "metadata": {
    "name": "my-pod.17a8c8f2c8c8f2c8",
    "namespace": "default",
    "creationTimestamp": "2026-07-13T10:30:00Z"
  },
  "involvedObject": {
    "apiVersion": "v1",
    "kind": "Pod",
    "name": "my-pod",
    "namespace": "default"
  },
  "reason": "Failed",
  "message": "Error: ImagePullBackOff",
  "source": {
    "component": "kubelet",
    "host": "node-1"
  },
  "firstTimestamp": "2026-07-13T10:30:00Z",
  "lastTimestamp": "2026-07-13T10:35:00Z",
  "count": 5,
  "type": "Warning"
}
```

---

## 2. Pod Logs

### Descripción
Logs de stdout/stderr de contenedores dentro de Pods.

### Acceso a Logs

```bash
# Logs actuales
kubectl logs my-pod -n default

# Logs de contenedor específico
kubectl logs my-pod -c my-container -n default

# Logs anteriores (si el pod fue reiniciado)
kubectl logs my-pod -n default --previous

# Logs en tiempo real
kubectl logs my-pod -n default -f

# Últimas N líneas
kubectl logs my-pod -n default --tail=100

# Logs desde hace X minutos
kubectl logs my-pod -n default --since=10m

# Logs con timestamps
kubectl logs my-pod -n default --timestamps=true
```

### API REST de Kubernetes

```python
# Obtener logs
GET /api/v1/namespaces/{namespace}/pods/{podName}/log

# Con parámetros
GET /api/v1/namespaces/{namespace}/pods/{podName}/log?container=my-container&tailLines=100&timestamps=true
```

**Parámetros útiles**:

```
container: nombre del contenedor
tailLines: últimas N líneas
sinceSeconds: logs desde hace X segundos
sinceTime: logs desde una fecha específica
timestamps: incluir timestamps
previous: logs del contenedor anterior
```

---

## 3. Pod Status

### Descripción
Estado actual y condiciones de un Pod.

### Información de Estado

```bash
# Ver estado del pod
kubectl get pod my-pod -n default -o yaml

# Ver condiciones
kubectl describe pod my-pod -n default
```

**Condiciones de Pod**:

```yaml
status:
  conditions:
  - type: Initialized
    status: "True"
    lastProbeTime: null
    lastTransitionTime: "2026-07-13T10:30:00Z"
  - type: Ready
    status: "False"
    lastProbeTime: null
    lastTransitionTime: "2026-07-13T10:30:05Z"
    reason: "ContainerNotReady"
    message: "containers with unready status: [my-container]"
  - type: ContainersReady
    status: "False"
    lastProbeTime: null
    lastTransitionTime: "2026-07-13T10:30:05Z"
  - type: PodScheduled
    status: "True"
    lastProbeTime: null
    lastTransitionTime: "2026-07-13T10:30:00Z"
  
  containerStatuses:
  - name: my-container
    ready: false
    restartCount: 3
    state:
      waiting:
        reason: "CrashLoopBackOff"
        message: "Back-off 5m0s restarting failed container=my-container pod=my-pod_default"
    lastState:
      terminated:
        exitCode: 1
        reason: "Error"
        message: "Application failed to start"
        startedAt: "2026-07-13T10:35:00Z"
        finishedAt: "2026-07-13T10:35:05Z"
```

### API REST de Kubernetes

```python
# Obtener pod
GET /api/v1/namespaces/{namespace}/pods/{podName}

# Obtener status
GET /api/v1/namespaces/{namespace}/pods/{podName}/status
```

---

## 4. Node Status

### Descripción
Estado y condiciones de los nodos del cluster.

### Información de Estado

```bash
# Ver estado de nodos
kubectl get nodes -o wide

# Ver detalles de un nodo
kubectl describe node node-1

# Ver condiciones
kubectl get nodes -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[?(@.type=="Ready")].status
```

**Condiciones de Node**:

```yaml
status:
  conditions:
  - type: MemoryPressure
    status: "False"
    lastHeartbeatTime: "2026-07-13T10:35:00Z"
    lastTransitionTime: "2026-07-13T10:30:00Z"
  - type: DiskPressure
    status: "False"
    lastHeartbeatTime: "2026-07-13T10:35:00Z"
    lastTransitionTime: "2026-07-13T10:30:00Z"
  - type: PIDPressure
    status: "False"
    lastHeartbeatTime: "2026-07-13T10:35:00Z"
    lastTransitionTime: "2026-07-13T10:30:00Z"
  - type: Ready
    status: "True"
    lastHeartbeatTime: "2026-07-13T10:35:00Z"
    lastTransitionTime: "2026-07-13T10:30:00Z"
```

---

## 5. Deployment Status

### Descripción
Estado y condiciones de Deployments.

### Información de Estado

```bash
# Ver estado de deployment
kubectl get deployment my-deployment -n default -o yaml

# Ver rollout status
kubectl rollout status deployment/my-deployment -n default

# Ver historial de rollouts
kubectl rollout history deployment/my-deployment -n default

# Ver detalles de un rollout
kubectl rollout history deployment/my-deployment -n default --revision=2
```

**Status de Deployment**:

```yaml
status:
  observedGeneration: 3
  replicas: 3
  updatedReplicas: 3
  readyReplicas: 2
  availableReplicas: 2
  unavailableReplicas: 1
  conditions:
  - type: Progressing
    status: "False"
    lastUpdateTime: "2026-07-13T10:35:00Z"
    lastTransitionTime: "2026-07-13T10:35:00Z"
    reason: "ProgressDeadlineExceeded"
    message: "Deployment does not have minimum availability"
  - type: Available
    status: "False"
    lastUpdateTime: "2026-07-13T10:35:00Z"
    lastTransitionTime: "2026-07-13T10:35:00Z"
    reason: "MinimumReplicasUnavailable"
    message: "Deployment does not have minimum availability"
```

---

## 6. GKE-Specific Events

### Descripción
Eventos específicos de Google Kubernetes Engine.

### Tipos de Eventos GKE

```bash
# Eventos de cluster
gcloud container clusters describe my-cluster --zone=us-central1-a

# Eventos de node pool
gcloud container node-pools describe my-node-pool \
  --cluster=my-cluster \
  --zone=us-central1-a

# Operaciones del cluster
gcloud container operations list --zone=us-central1-a

# Detalles de operación
gcloud container operations describe OPERATION_ID --zone=us-central1-a
```

### API de GKE

```python
# Listar clusters
GET /v1/projects/{projectId}/zones/{zone}/clusters

# Obtener cluster
GET /v1/projects/{projectId}/zones/{zone}/clusters/{clusterName}

# Listar operaciones
GET /v1/projects/{projectId}/zones/{zone}/operations

# Obtener operación
GET /v1/projects/{projectId}/zones/{zone}/operations/{operationId}
```

---

## 7. Metrics Server

### Descripción
Métricas de recursos (CPU, memoria) de Pods y Nodes.

### Acceso a Métricas

```bash
# Métricas de pods
kubectl top pods -n default

# Métricas de un pod específico
kubectl top pod my-pod -n default

# Métricas de nodos
kubectl top nodes

# Métricas de un nodo específico
kubectl top node node-1
```

### API de Metrics

```python
# Métricas de pod
GET /apis/metrics.k8s.io/v1beta1/namespaces/{namespace}/pods/{podName}

# Métricas de nodo
GET /apis/metrics.k8s.io/v1beta1/nodes/{nodeName}
```

---

## Resumen de Fuentes Kubernetes

| Fuente | Tipo | Latencia | Cobertura | Prioridad |
|--------|------|----------|-----------|-----------|
| Events API | Eventos | Real-time | 100% | ⭐⭐⭐ |
| Pod Logs | Logs | Real-time | 100% | ⭐⭐⭐ |
| Pod Status | Estado | Real-time | 100% | ⭐⭐⭐ |
| Node Status | Estado | Real-time | 100% | ⭐⭐⭐ |
| Deployment Status | Estado | Real-time | 100% | ⭐⭐⭐ |
| GKE Events | Eventos | 1-2 min | 95% | ⭐⭐ |
| Metrics Server | Métricas | 1 min | 90% | ⭐⭐ |

---

## Autenticación

### kubectl

```bash
# Configurar acceso
gcloud container clusters get-credentials my-cluster --zone=us-central1-a

# Verificar acceso
kubectl auth can-i get events --as=system:serviceaccount:default:default
```

### Python Client

```python
from kubernetes import client, config

# Cargar configuración
config.load_kube_config()

# Crear cliente
v1 = client.CoreV1Api()

# Listar eventos
events = v1.list_namespaced_event('default')
for event in events.items:
    print(f"{event.metadata.name}: {event.reason}")
```

### Service Account

```bash
# Crear service account
kubectl create serviceaccount event-reader -n default

# Crear role
kubectl create role event-reader --verb=get,list,watch --resource=events -n default

# Crear role binding
kubectl create rolebinding event-reader \
  --clusterrole=event-reader \
  --serviceaccount=default:event-reader \
  -n default

# Obtener token
kubectl get secret $(kubectl get secret -n default | grep event-reader | awk '{print $1}') -n default -o jsonpath='{.data.token}' | base64 -d
```

---

**Versión**: 1.0.0  
**Fecha**: 2026-07-14
