# 💡 Ejemplos Prácticos

## 1. Caso de Uso 1: Investigación de Caída de Servicio

### Escenario

El servicio Cloud Run `payment-api` cayó hace 2 horas. Necesitas investigar qué sucedió.

### Comando

```bash
python event_tracker.py \
  --component-name "payment-api" \
  --start-time "2026-07-13T08:00:00Z" \
  --end-time "2026-07-13T10:00:00Z" \
  --output-format html \
  --output-file payment-api-incident.html
```

### Reporte Generado

```
REPORTE DE EVENTOS - payment-api
Período: 2026-07-13 08:00:00 a 2026-07-13 10:00:00

RESUMEN EJECUTIVO
================
Total de eventos: 245
Eventos críticos: 5
Duración del incidente: 00:15:30
Causa raíz: Out of memory error

TIMELINE
========
08:45:00 - [CRITICAL] Memory usage reached 100%
08:45:05 - [CRITICAL] Container killed by OOMKiller
08:45:10 - [WARNING] Pod restarted (restart count: 1)
08:45:15 - [WARNING] Pod restarted (restart count: 2)
08:45:20 - [WARNING] Pod restarted (restart count: 3)
08:45:25 - [ERROR] CrashLoopBackOff detected
08:50:00 - [INFO] Manual intervention: Increased memory limit
08:50:05 - [INFO] Pod started successfully
08:50:10 - [INFO] Service recovered

CAUSA RAÍZ
==========
Out of memory error en contenedor

EVIDENCIA
=========
1. Cloud Logging: "java.lang.OutOfMemoryError: Java heap space"
2. Kubernetes Events: "OOMKilled"
3. Cloud Monitoring: Memory usage 100% at 08:45:00
4. Audit Logs: Memory limit changed from 1GB to 512MB at 08:40:00

ANÁLISIS
========
El incidente fue causado por:
1. Cambio de configuración: Memory limit reducido de 1GB a 512MB
2. Aumento de tráfico: Requests aumentaron 300%
3. Memory leak: Aplicación tiene memory leak en versión 2.1.0

RECOMENDACIONES
===============
1. [CRÍTICO] Revertir memory limit a 1GB
2. [ALTO] Investigar memory leak en v2.1.0
3. [ALTO] Implementar alertas de memory usage
4. [MEDIO] Realizar load testing antes de cambios
5. [MEDIO] Implementar circuit breaker para sobrecarga
```

---

## 2. Caso de Uso 2: Análisis de Rendimiento

### Escenario

Tu servicio Kubernetes `api-gateway` ha tenido latencia alta durante el día. Quieres identificar la causa.

### Comando

```bash
python event_tracker.py \
  --component-name "api-gateway" \
  --start-time "2026-07-13T00:00:00Z" \
  --end-time "2026-07-13T23:59:59Z" \
  --include-metrics \
  --output-format json \
  --output-file api-gateway-analysis.json
```

### Reporte Generado (JSON)

```json
{
  "summary": {
    "component_name": "api-gateway",
    "period": {
      "start": "2026-07-13T00:00:00Z",
      "end": "2026-07-13T23:59:59Z"
    },
    "total_events": 1245,
    "critical_events": 0,
    "warning_events": 45,
    "info_events": 1200,
    "performance_issues": [
      {
        "time": "2026-07-13T12:00:00Z",
        "latency_p99": "850ms",
        "normal_latency": "150ms",
        "increase": "467%",
        "cause": "Database connection pool exhausted"
      },
      {
        "time": "2026-07-13T18:00:00Z",
        "latency_p99": "1200ms",
        "normal_latency": "150ms",
        "increase": "700%",
        "cause": "Deployment of new version with inefficient query"
      }
    ]
  },
  "correlations": [
    {
      "group_id": "group_001",
      "title": "Database Connection Pool Exhaustion",
      "events": [234, 235, 236, 237, 238],
      "timeline": {
        "start": "2026-07-13T12:00:00Z",
        "end": "2026-07-13T12:30:00Z",
        "duration": "00:30:00"
      },
      "impact": {
        "affected_requests": 5234,
        "error_rate": "15%",
        "latency_increase": "467%"
      }
    }
  ],
  "analysis": {
    "root_causes": [
      {
        "cause": "Database connection pool exhausted",
        "confidence": 0.95,
        "evidence": [
          "Cloud Monitoring: Connection pool at 100%",
          "Cloud Logging: 'Connection pool timeout'",
          "Kubernetes Events: High CPU on database pod"
        ],
        "recommendations": [
          "Increase connection pool size",
          "Implement connection pooling on application side",
          "Add database read replicas"
        ]
      },
      {
        "cause": "Inefficient database query in new deployment",
        "confidence": 0.87,
        "evidence": [
          "Deployment at 18:00:00 correlates with latency spike",
          "Cloud Trace: Query execution time increased from 50ms to 500ms",
          "Cloud Logging: 'SELECT * FROM large_table' detected"
        ],
        "recommendations": [
          "Rollback to previous version",
          "Add database indexes",
          "Optimize query"
        ]
      }
    ]
  }
}
```

---

## 3. Caso de Uso 3: Auditoría de Cambios

### Escenario

Necesitas auditar todos los cambios realizados a tu servicio `payment-processor` durante el último mes.

### Comando

```bash
python event_tracker.py \
  --component-name "payment-processor" \
  --start-time "2026-06-13T00:00:00Z" \
  --end-time "2026-07-13T23:59:59Z" \
  --include-audit-logs \
  --output-format csv \
  --output-file payment-processor-audit.csv
```

### Reporte Generado (CSV)

```csv
timestamp,event_type,action,user,resource,old_value,new_value,impact
2026-06-15T10:30:00Z,change,update,john@company.com,memory_limit,512MB,1GB,Service recovered
2026-06-18T14:20:00Z,change,update,jane@company.com,cpu_limit,500m,1000m,Improved performance
2026-06-20T09:15:00Z,change,deploy,ci-cd@company.com,image,v1.2.0,v1.3.0,New features added
2026-06-22T16:45:00Z,change,update,john@company.com,replica_count,2,5,Increased availability
2026-06-25T11:00:00Z,change,update,jane@company.com,environment_var,PROD,STAGING,Reduced to staging
2026-06-25T11:05:00Z,change,update,jane@company.com,environment_var,STAGING,PROD,Restored to production
2026-07-01T13:30:00Z,change,deploy,ci-cd@company.com,image,v1.3.0,v2.0.0,Major version update
2026-07-05T10:00:00Z,change,update,john@company.com,memory_limit,1GB,512MB,Cost optimization
2026-07-05T10:15:00Z,error,outofmemory,system,payment-processor,N/A,N/A,Service crashed
2026-07-05T10:20:00Z,change,update,john@company.com,memory_limit,512MB,1GB,Incident recovery
```

---

## 4. Caso de Uso 4: Troubleshooting de Pod Crash

### Escenario

Tu Pod de Kubernetes `worker-job` está en `CrashLoopBackOff`. Necesitas investigar por qué.

### Comando

```bash
python event_tracker.py \
  --component-name "worker-job" \
  --start-time "2026-07-13T10:00:00Z" \
  --end-time "2026-07-13T11:00:00Z" \
  --include-pod-logs \
  --output-format markdown \
  --output-file worker-job-crash.md
```

### Reporte Generado (Markdown)

```markdown
# Análisis de Crash - worker-job

## Resumen
- **Componente**: worker-job
- **Período**: 2026-07-13 10:00:00 a 2026-07-13 11:00:00
- **Estado**: CrashLoopBackOff
- **Restart Count**: 5

## Timeline

### 10:00:00 - Pod Started
```
Pod worker-job-abc123 started in namespace default
```

### 10:00:05 - Application Started
```
2026-07-13T10:00:05Z INFO Application started
2026-07-13T10:00:06Z INFO Loading configuration
2026-07-13T10:00:07Z INFO Connecting to database
```

### 10:00:10 - Connection Error
```
2026-07-13T10:00:10Z ERROR Failed to connect to database
2026-07-13T10:00:10Z ERROR Connection refused: 127.0.0.1:5432
2026-07-13T10:00:10Z ERROR Stack trace:
  at DatabaseConnection.connect()
  at Application.initialize()
  at main()
```

### 10:00:11 - Pod Crashed
```
Pod exited with code 1
Container killed
```

### 10:00:15 - Pod Restarted
```
Kubernetes restarted pod (restart count: 1)
```

### 10:00:20 - Same Error
```
Same error repeated
Pod crashed again
```

## Causa Raíz

**Database Connection Failed**

El Pod intenta conectarse a una base de datos en `127.0.0.1:5432` pero no hay servicio disponible en esa dirección.

## Evidencia

1. **Pod Logs**:
   ```
   ERROR Failed to connect to database
   Connection refused: 127.0.0.1:5432
   ```

2. **Kubernetes Events**:
   ```
   BackOff: Back-off 5m0s restarting failed container
   ```

3. **Cloud Logging**:
   ```
   Connection refused error repeated 5 times
   ```

## Soluciones Recomendadas

### Opción 1: Usar Service DNS (Recomendado)
Cambiar la dirección de conexión de `127.0.0.1:5432` a `postgres-service:5432`

```yaml
env:
- name: DATABASE_HOST
  value: postgres-service  # En lugar de 127.0.0.1
- name: DATABASE_PORT
  value: "5432"
```

### Opción 2: Usar ConfigMap
Crear un ConfigMap con la configuración correcta:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: worker-job-config
data:
  database.host: postgres-service
  database.port: "5432"
```

### Opción 3: Usar Init Container
Agregar un init container que espere a que la base de datos esté lista:

```yaml
initContainers:
- name: wait-for-db
  image: busybox
  command: ['sh', '-c', 'until nc -z postgres-service 5432; do echo waiting for db; sleep 2; done']
```

## Pasos para Resolver

1. Verificar que el servicio `postgres-service` existe:
   ```bash
   kubectl get svc postgres-service
   ```

2. Verificar conectividad desde el pod:
   ```bash
   kubectl exec -it worker-job-abc123 -- nc -zv postgres-service 5432
   ```

3. Actualizar la configuración del pod

4. Redeploy:
   ```bash
   kubectl rollout restart deployment/worker-job
   ```

5. Verificar que el pod está corriendo:
   ```bash
   kubectl get pods worker-job-abc123
   ```
```

---

## 5. Caso de Uso 5: Análisis de Escalado Automático

### Escenario

Tu Deployment `web-server` ha escalado de 2 a 10 replicas. Quieres entender por qué.

### Comando

```bash
python event_tracker.py \
  --component-name "web-server" \
  --start-time "2026-07-13T14:00:00Z" \
  --end-time "2026-07-13T15:00:00Z" \
  --include-scaling-events \
  --output-format html \
  --output-file web-server-scaling.html
```

### Reporte Generado

```
ANÁLISIS DE ESCALADO - web-server

TIMELINE DE ESCALADO
====================

14:00:00 - Replicas: 2 (Normal)
14:15:00 - Replicas: 3 (CPU 75%)
14:20:00 - Replicas: 4 (CPU 82%)
14:25:00 - Replicas: 5 (CPU 88%)
14:30:00 - Replicas: 7 (CPU 95%)
14:35:00 - Replicas: 10 (CPU 100%)
14:40:00 - Replicas: 10 (CPU 95%)
14:45:00 - Replicas: 10 (CPU 85%)
14:50:00 - Replicas: 8 (CPU 70%)
14:55:00 - Replicas: 5 (CPU 60%)
15:00:00 - Replicas: 2 (CPU 50%)

CAUSA DEL ESCALADO
==================

1. Aumento de tráfico:
   - Requests por segundo: 100 → 5000 (50x)
   - Duración: 14:15:00 a 14:40:00

2. Origen del tráfico:
   - 80% desde IP 203.0.113.0/24 (Posible DDoS)
   - 15% desde usuarios legítimos
   - 5% desde bots

3. Impacto:
   - Costo adicional: $45 (30 minutos con 10 replicas)
   - Latencia: Normal (150ms)
   - Error rate: 0.1%

RECOMENDACIONES
===============

1. [CRÍTICO] Investigar origen del tráfico
   - Verificar si es DDoS
   - Implementar rate limiting
   - Configurar WAF

2. [ALTO] Optimizar escalado automático
   - Ajustar umbrales de CPU
   - Implementar predictive scaling
   - Usar custom metrics

3. [MEDIO] Implementar protección contra DDoS
   - Cloud Armor
   - Rate limiting
   - IP whitelisting
```

---

## 6. Troubleshooting Común

### Problema 1: "No events found"

**Causa**: Rango de tiempo muy pequeño o componente no existe.

**Solución**:
```bash
# Aumentar rango de tiempo
python event_tracker.py \
  --component-name "my-service" \
  --start-time "2026-07-10T00:00:00Z" \
  --end-time "2026-07-14T00:00:00Z"

# Verificar nombre del componente
kubectl get pods | grep my-service
gcloud run services list
```

### Problema 2: "Permission denied"

**Causa**: Credenciales insuficientes.

**Solución**:
```bash
# Verificar credenciales
gcloud auth list
gcloud config get-value project

# Verificar permisos
gcloud projects get-iam-policy PROJECT_ID

# Configurar credenciales
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Problema 3: "Connection timeout"

**Causa**: Kubernetes no disponible.

**Solución**:
```bash
# Verificar conexión a Kubernetes
kubectl cluster-info

# Verificar kubeconfig
kubectl config view

# Configurar acceso
gcloud container clusters get-credentials CLUSTER_NAME --zone ZONE
```

### Problema 4: "Reporte vacío"

**Causa**: Componente no tiene eventos en el rango de tiempo.

**Solución**:
```bash
# Verificar que el componente está activo
kubectl get pods -n NAMESPACE | grep COMPONENT

# Verificar logs
kubectl logs POD_NAME -n NAMESPACE

# Aumentar rango de tiempo
```

---

**Versión**: 1.0.0  
**Fecha**: 2026-07-14
