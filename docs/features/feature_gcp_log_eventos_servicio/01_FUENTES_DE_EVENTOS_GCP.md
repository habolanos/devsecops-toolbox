# 📊 Fuentes de Eventos en GCP

## 1. Cloud Logging (Stackdriver Logging)

### Descripción
Sistema centralizado de logging que captura logs de todas las aplicaciones y servicios en GCP.

### Tipos de Logs

#### 1.1 Application Logs
```
resource.type = "cloud_run_revision"
resource.labels.service_name = "my-service"
severity >= ERROR
```

**Información capturada**:
- Mensajes de error
- Stack traces
- Eventos de aplicación
- Timestamps exactos

#### 1.2 System Logs
```
resource.type = "cloud_run_revision"
protoPayload.serviceName = "run.googleapis.com"
```

**Información capturada**:
- Inicios/paradas de contenedor
- Cambios de estado
- Errores de sistema
- Eventos de infraestructura

#### 1.3 Infrastructure Logs
```
resource.type = "gce_instance"
resource.labels.instance_id = "instance-id"
```

**Información capturada**:
- Eventos de VM
- Cambios de estado
- Problemas de hardware
- Eventos de red

### API de Cloud Logging

**Endpoint**: `https://logging.googleapis.com/v2/projects/{projectId}/logs`

**Métodos principales**:

```python
# Listar logs
GET /v2/projects/{projectId}/logs

# Buscar entries
POST /v2/projects/{projectId}:listLogEntries
{
  "resourceNames": ["projects/{projectId}"],
  "filter": "resource.type='cloud_run_revision' AND resource.labels.service_name='my-service'",
  "pageSize": 100,
  "orderBy": "timestamp desc"
}

# Obtener log específico
GET /v2/projects/{projectId}/logs/{logName}
```

**Filtros útiles**:

```
# Cloud Run
resource.type = "cloud_run_revision"
resource.labels.service_name = "my-service"

# Kubernetes
resource.type = "k8s_container"
resource.labels.pod_name = "my-pod"
resource.labels.namespace_name = "default"

# Errores
severity >= ERROR

# Rango de tiempo
timestamp >= "2026-07-13T00:00:00Z"
timestamp <= "2026-07-14T00:00:00Z"

# Combinado
resource.type = "cloud_run_revision"
AND resource.labels.service_name = "my-service"
AND severity >= ERROR
AND timestamp >= "2026-07-13T00:00:00Z"
```

---

## 2. Cloud Monitoring (Stackdriver Monitoring)

### Descripción
Sistema de monitoreo que captura métricas de rendimiento y eventos de alertas.

### Tipos de Métricas

#### 2.1 Cloud Run Metrics
```
run.googleapis.com/request_count
run.googleapis.com/request_latencies
run.googleapis.com/container_memory_utilization
run.googleapis.com/container_cpu_utilization
```

#### 2.2 Kubernetes Metrics
```
kubernetes.io/container/cpu/core_usage_time
kubernetes.io/container/memory/used_bytes
kubernetes.io/pod/network/received_bytes_count
kubernetes.io/pod/uptime
```

#### 2.3 Eventos de Alertas
```
monitoring.googleapis.com/uptime_check/check_passed
monitoring.googleapis.com/uptime_check/check_failed
```

### API de Cloud Monitoring

**Endpoint**: `https://monitoring.googleapis.com/v3/projects/{projectId}`

**Métodos principales**:

```python
# Listar series de tiempo
GET /v3/projects/{projectId}/timeSeries
?filter=metric.type="run.googleapis.com/request_count"
AND resource.labels.service_name="my-service"

# Obtener datos de métrica
POST /v3/projects/{projectId}/timeSeries:query
{
  "name": "projects/{projectId}",
  "query": "fetch cloud_run_revision | metric 'run.googleapis.com/request_count' | filter resource.service_name == 'my-service'"
}

# Listar alertas
GET /v3/projects/{projectId}/alertPolicies
```

**Rango de tiempo**:

```python
{
  "interval": {
    "startTime": "2026-07-13T00:00:00Z",
    "endTime": "2026-07-14T00:00:00Z"
  }
}
```

---

## 3. Cloud Audit Logs

### Descripción
Registra acciones administrativas y cambios de configuración en GCP.

### Tipos de Audit Logs

#### 3.1 Admin Activity Logs
```
protoPayload.methodName = "run.projects.locations.services.create"
protoPayload.methodName = "run.projects.locations.services.update"
protoPayload.methodName = "run.projects.locations.services.delete"
```

**Información capturada**:
- Quién hizo el cambio
- Cuándo se hizo
- Qué cambió
- Valores anteriores y nuevos

#### 3.2 Data Access Logs
```
protoPayload.methodName = "storage.objects.get"
protoPayload.methodName = "storage.objects.list"
```

**Información capturada**:
- Acceso a datos
- Quién accedió
- Cuándo
- Qué datos

#### 3.3 System Event Logs
```
protoPayload.methodName = "compute.instances.stop"
protoPayload.methodName = "compute.instances.start"
```

**Información capturada**:
- Eventos de sistema
- Cambios de estado
- Acciones automáticas

### API de Cloud Audit Logs

**Endpoint**: `https://logging.googleapis.com/v2/projects/{projectId}/logs`

**Filtros útiles**:

```
# Cambios en Cloud Run
protoPayload.serviceName = "run.googleapis.com"
protoPayload.resourceName = "projects/{projectId}/locations/us-central1/services/my-service"

# Cambios en Kubernetes
protoPayload.serviceName = "container.googleapis.com"
protoPayload.resourceName = "projects/{projectId}/zones/us-central1-a/clusters/my-cluster"

# Acciones específicas
protoPayload.methodName = "run.projects.locations.services.update"

# Rango de tiempo
timestamp >= "2026-07-13T00:00:00Z"
```

---

## 4. Cloud Events

### Descripción
Eventos generados por servicios de GCP cuando ocurren cambios.

### Tipos de Eventos

#### 4.1 Cloud Run Events
```
type: google.cloud.run.service.v1.created
type: google.cloud.run.service.v1.updated
type: google.cloud.run.service.v1.deleted
```

#### 4.2 Kubernetes Events
```
type: io.k8s.api.core.v1.pod.created
type: io.k8s.api.core.v1.pod.deleted
type: io.k8s.api.core.v1.pod.failed
```

#### 4.3 Compute Events
```
type: google.cloud.compute.instance.v1.created
type: google.cloud.compute.instance.v1.deleted
type: google.cloud.compute.instance.v1.stopped
```

### API de Cloud Events

**Endpoint**: `https://eventarc.googleapis.com/v1/projects/{projectId}/locations/{location}/triggers`

**Métodos principales**:

```python
# Listar triggers
GET /v1/projects/{projectId}/locations/{location}/triggers

# Obtener eventos
GET /v1/projects/{projectId}/locations/{location}/triggers/{triggerId}/events
```

---

## 5. Cloud Trace

### Descripción
Rastreo distribuido de solicitudes a través de múltiples servicios.

### Información Capturada

- Latencia de solicitud
- Servicios involucrados
- Errores en la cadena de llamadas
- Timestamps exactos

### API de Cloud Trace

**Endpoint**: `https://cloudtrace.googleapis.com/v2/projects/{projectId}`

**Métodos principales**:

```python
# Listar trazas
GET /v2/projects/{projectId}/traces
?filter=startTime >= "2026-07-13T00:00:00Z"

# Obtener traza específica
GET /v2/projects/{projectId}/traces/{traceId}
```

---

## 6. Cloud Profiler

### Descripción
Análisis de rendimiento de aplicaciones en producción.

### Información Capturada

- Uso de CPU
- Uso de memoria
- Funciones lentas
- Hotspots de rendimiento

### API de Cloud Profiler

**Endpoint**: `https://cloudprofiler.googleapis.com/v2/projects/{projectId}`

**Métodos principales**:

```python
# Listar perfiles
GET /v2/projects/{projectId}/profiles
?filter=startTime >= "2026-07-13T00:00:00Z"
```

---

## 7. Cloud Error Reporting

### Descripción
Agregación automática de errores de aplicaciones.

### Información Capturada

- Mensajes de error
- Stack traces
- Frecuencia de errores
- Tendencias

### API de Cloud Error Reporting

**Endpoint**: `https://clouderrorreporting.googleapis.com/v1beta1/projects/{projectId}`

**Métodos principales**:

```python
# Listar grupos de errores
GET /v1beta1/projects/{projectId}/groupStats

# Obtener eventos de error
GET /v1beta1/projects/{projectId}/groupStats/{groupId}/events
```

---

## Resumen de Fuentes

| Fuente | Tipo | Latencia | Cobertura | Prioridad |
|--------|------|----------|-----------|-----------|
| Cloud Logging | Logs | Real-time | 100% | ⭐⭐⭐ |
| Cloud Monitoring | Métricas | 1-2 min | 95% | ⭐⭐⭐ |
| Cloud Audit Logs | Auditoría | 5-10 min | 100% | ⭐⭐⭐ |
| Cloud Events | Eventos | Real-time | 80% | ⭐⭐ |
| Cloud Trace | Trazas | 1-5 min | 70% | ⭐⭐ |
| Cloud Profiler | Profiling | 5-10 min | 50% | ⭐ |
| Error Reporting | Errores | 1-2 min | 85% | ⭐⭐⭐ |

---

## Autenticación

### Service Account

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### gcloud CLI

```bash
gcloud auth application-default login
gcloud config set project PROJECT_ID
```

### Python

```python
from google.cloud import logging
from google.cloud import monitoring_v3
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json'
)

logging_client = logging.Client(credentials=credentials)
monitoring_client = monitoring_v3.MetricServiceClient(credentials=credentials)
```

---

**Versión**: 1.0.0  
**Fecha**: 2026-07-14
