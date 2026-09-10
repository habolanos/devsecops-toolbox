# GCP Monitoring Tools

Herramientas para monitoreo de recursos GCP y generación de reportes de GKE.

## 📋 Contenido

| Archivo | Descripción |
|---------|-------------|
| `gcp_monitor.py` | Monitoreo general de recursos GCP (multi-proyecto, GKE, Cloud SQL, Compute, Cloud Run, Pub/Sub) |
| `generate_gcp_dashboard.py` | Generador de dashboard HTML interactivo con tabs por tipo de recurso |
| `gke_deployments_report.py` | Reporte detallado de deployments en GKE |
| `gke_monitor_node.py` | Monitoreo de nodos de GKE |
| `gke_monitor_pod.py` | Monitoreo de pods de GKE |
| `requirements.txt` | Dependencias de Python |
| `outcome/` | Directorio de salida para reportes generados |

---

## 🖥️ GCP Monitor

Script de monitoreo de recursos GCP que genera reportes de estatus, consumo y uso de disco.

### Características

- **Servicios Habilitados**: resumen por proyecto con conteo de APIs habilitadas y estado general (✅/⚠️/❌)
- **Clusters GKE**: tabla enriquecida con Release Channel, Autopilot, Master Version, Version Status, Status Summary, Pods, Not Running, CPU/memoria total y promedio, estado de salud
- **Capacidad de Red GKE**: tabla con subred, CIDR de pods, CIDR de services, IPs usadas/totales/%, estado de alerta (OK/WARNING/CRITICAL)
- **Instancias Cloud SQL**: nombre, estado (con color: STOPPED rojo, RUNNABLE verde), versión, tier, disco (GB), conteo de bases de datos por instancia
- **Instancias Compute Engine**: nombre, estado (con color), tipo de máquina, zona, CPUs, memoria, disco raíz
- **Servicios Cloud Run**: nombre, región, URL, concurrencia, CPU/mem limits, ingress
- **Topics Pub/Sub**: nombre del topic por proyecto
- **Estados con color**: STOPPED/TERMINATED/SUSPENDED en rojo, RUNNING/RUNNABLE/ACTIVE en verde (vía `format_status_color`)
- **Formato legible de tiempo**: `format_duration()` convierte segundos a `Xs`, `Xm Ys`, `Xh Ym Zs` automáticamente
- **Paralelización**: `get_gke_metrics_parallel`, `build_gke_cluster_enrichment` y `_ensure_cluster_credentials` (con cache) ejecutan en paralelo con `ThreadPoolExecutor`
- **Timeouts**: kubectl (30s) y gcloud (60-120s) con captura de `subprocess.TimeoutExpired` para evitar cuelgues
- **Reporte consolidado multi-proyecto** con tablas Rich

### Uso

```bash
# Usa proyecto por defecto
python gcp_monitor.py

# Especificar proyecto
python gcp_monitor.py --project YOUR_PROJECT_ID

# Con archivo de credenciales (opcional)
python gcp_monitor.py --project YOUR_PROJECT_ID --credentials /path/to/sa.json
```

### Salida

Los reportes se guardan en: `outcome/gcp_report_<project_id>_<timestamp>.txt`

---

## �️ Generate GCP Dashboard

Genera un dashboard HTML **interactivo y self-contained** (CSS y JS inline, sin CDNs externos) a partir de los archivos JSON consolidados que exporta `gcp_monitor.py`.

### Características del dashboard

El dashboard replica en HTML todas las dimensiones que muestra `gcp_monitor.py` en la terminal mediante un **sistema de pestañas (tabs)**:

| Tab | Dimensiones |
|-----|-------------|
| 📌 Servicios Habilitados | Proyecto, Habilitados, Estado |
| ☸️ Clusters GKE | Proyecto, Cluster, Ubicación, CPU Total, Memoria Total, CPU Prom., Memoria Prom., Estado, Release Channel, Autopilot, Master Version, Version Status, Status Summary, Pods, Not Running |
| 🌐 Capacidad de Red GKE | Proyecto, Cluster, Ubicación, Subred, CIDR Pods, CIDR Services, Pods IPs, Services IPs, Estado |
| 🗄️ Instancias Cloud SQL | Proyecto, Nombre, Estado, Versión, Tier, Disco (GB), BDs |
| 💻 Instancias Compute Engine | Proyecto, Nombre, Estado, Tipo, Zona, CPUs, Memoria, Disco Raíz |
| 🚀 Servicios Cloud Run | Proyecto, Nombre, Región, URL, Concurrencia, CPU Lim, Mem Lim, Ingress |
| 📨 Topics Pub/Sub | Proyecto, Nombre |
| 📋 Inventario Completo | Tipo, Nombre, Proyecto, Ambiente, Región/Zona, Estado, Postura, Hallazgos |

Cada tabla es **interactiva**:
- **Filtros globales**: por proyecto, ambiente, tipo de recurso, estado y búsqueda de texto
- **Filtros por columna**: input de texto en cada header para filtrar individualmente
- **Ordenamiento**: clic en cualquier header para ordenar asc/desc
- **Badges de color**: verde (RUNNING/ENABLED), rojo (STOPPED/TERMINATED), amarillo (advertencia), gris (N/A)
- **Paginación**: muestra 50 filas inicialmente, botón "Cargar más" para ver el resto
- **Modal de hallazgos**: clic en "N hallazgo(s)" para ver detalles de seguridad por recurso

KPIs incluidos: Proyectos, Servicios Habilitados, Recursos Totales, Clusters GKE, Pods Running, Bases de Datos, Cloud SQL, Compute Engine, Cloud Run, Pub/Sub.

### Uso

```bash
# Desde un archivo JSON individual
python generate_gcp_dashboard.py -i outcome/gcp_report_xxx.json -o outcome/dashboard.html

# Desde un directorio con múltiples snapshots JSON
python generate_gcp_dashboard.py -d outcome/ -o outcome/dashboard.html
```

### Argumentos

| Argumento | Descripción |
|-----------|-------------|
| `--input`, `-i` | Archivo JSON de entrada |
| `--input-dir`, `-d` | Directorio con múltiples snapshots JSON |
| `--output`, `-o` | Archivo HTML de salida (default: `gcp_infrastructure_dashboard.html`) |

### Requisitos

- Python 3.8+
- `pandas` (opcional, para análisis avanzado)
- `plotly` (opcional, para gráficos)

---

## �📊 GKE Deployments Report

Script en Python para generar reportes detallados de **Deployments en Google Kubernetes Engine (GKE)**, incluyendo métricas de uso en tiempo real, recursos definidos (requests/limits), y resúmenes agrupados por status y configuración de límites.

---

## 📋 Características

* **Reporte detallado por Deployment** con las siguientes columnas:

  * `cluster`: Nombre del cluster GKE

  * `namespace`: Namespace del deployment

  * `deployment`: Nombre del deployment

  * `pods`: Pods listos/deseados (ej. `3/3`)

  * `status`: Estado agregado (`Running`, `Pending`, `Failed`, `Mixed`)

  * `restarts`: Total de restarts de todos los pods del deployment

  * `age`: Antigüedad del deployment (ej. `45d`, `12h`, `30m`)

  * `cpu`: Uso promedio de CPU en tiempo real (vía metrics-server)

  * `memory`: Uso promedio de memoria en tiempo real (vía metrics-server)

  * `request_cpu`: Suma de CPU requests definidos en el manifiesto

  * `request_memory`: Suma de memoria requests definidos en el manifiesto

  * `limit_cpu`: Suma de CPU limits definidos en el manifiesto

  * `limit_memory`: Suma de memoria limits definidos en el manifiesto

  * `generated_at`: Timestamp UTC de generación del reporte (ISO 8601)

* **Resúmenes agregados**:

  * **Por status**: Cantidad de deployments, pods listos y restarts agrupados por estado.

  * **Por status + limits**: Agrupación adicional por configuración de límites de CPU/memoria.

* **Múltiples formatos de salida**:

  * **TXT**: Tabla alineada con resúmenes incluidos

  * **CSV**: Todas las filas con headers

  * **JSON**: Array de objetos con todos los campos

---

## 🛠️ Requisitos

### 1\. Python 3.8+

### 2\. Dependencias

Instalar las librerías necesarias:

```bash
pip install kubernetes --break-system-packages
```

O si usas un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
pip install kubernetes
```

### 3\. Configuración de `kubectl`

El script usa tu configuración local de `kubectl` (archivo `~/.kube/config`).

Asegúrate de tener el contexto del cluster configurado:

```bash
gcloud container clusters get-credentials NOMBRE_CLUSTER \
  --region REGION \
  --project PROYECTO_ID
```

Verifica el contexto activo:

```bash
kubectl config current-context
```

### 4\. Metrics Server (opcional, pero recomendado)

Para obtener métricas de CPU y memoria en tiempo real, el cluster debe tener **metrics-server** instalado.

Si no está instalado, las columnas `cpu` y `memory` mostrarán `N/A`.

Para instalar metrics-server (requiere permisos de administrador del cluster):

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Verifica que esté corriendo:

```bash
kubectl get deployment metrics-server -n kube-system
```

### 5\. Permisos de Kubernetes

Tu usuario o service account necesita permisos de lectura en el cluster:

* `apps/v1/deployments` (list, get)

* `v1/pods` (list, get)

* `metrics.k8s.io/v1beta1/pods` (get) — para métricas en tiempo real

Si usas RBAC, asegúrate de tener el rol `view` o `cluster-reader` asignado.

---

## 🚀 Uso

### Ejecución básica

```bash
python3 gke_deployments_report.py
```

Esto generará los reportes en el directorio `outcome/` (se crea automáticamente si no existe).

### Especificar directorio de salida

```bash
python3 gke_deployments_report.py --output-dir reportes
```

### Ayuda

```bash
python3 gke_deployments_report.py --help
```

---

## 📂 Archivos generados

Cada ejecución genera 3 archivos con timestamp en el nombre:

```
outcome/
├── gke_deployments_report_20251215_120530.txt
├── gke_deployments_report_20251215_120530.csv
└── gke_deployments_report_20251215_120530.json
```

### Ejemplo de salida TXT

```text
================================================================================
REPORTE DE DEPLOYMENTS EN GKE
Generado (UTC): 2025-12-15T17:05:23.456789+00:00
================================================================================

================================================================================
CLUSTER              NAMESPACE      DEPLOYMENT           PODS   STATUS    RESTARTS  AGE   CPU          MEMORY    REQ_CPU       REQ_MEM    LIMIT_CPU     LIMIT_MEM   
================================================================================
gke-prod-cluster     default        api-gateway          3/3    Running   0         45d   0.15 cores   256 Mi    0.50 cores    512 Mi     1.00 cores    1024 Mi     
gke-prod-cluster     default        frontend-web         5/5    Running   2         45d   0.08 cores   512 Mi    0.25 cores    256 Mi     0.50 cores    512 Mi      

gke-prod-cluster     prod           orders-service       4/4    Running   1         30d   0.25 cores   1024 Mi   0.80 cores    768 Mi     1.00 cores    1024 Mi     
gke-prod-cluster     prod           payments-service     2/3    Pending   5         15d   0.10 cores   512 Mi    0.50 cores    512 Mi     1.00 cores    1024 Mi     

================================================================================

[RESÚMENES GENERADOS (UTC): 2025-12-15T17:05:23.456789+00:00]

RESUMEN POR STATUS
------------------
STATUS        DEPLOYMENTS   PODS_READY    RESTARTS  
-------------------------------------------------------
Pending       1             2             5         
Running       3             12            3         

RESUMEN POR STATUS + LIMITS (CPU/MEMORY)
-----------------------------------------
STATUS        LIMIT_CPU          LIMIT_MEM          DEPLOYMENTS   PODS_READY    RESTARTS  
------------------------------------------------------------------------------------------
Pending       1.00 cores         1024 Mi            1             2             5         
Running       0.50 cores         512 Mi             1             5             2         
Running       1.00 cores         1024 Mi            2             7             1         
```

### Ejemplo de salida CSV

```csv
cluster,namespace,deployment,pods,status,restarts,age,cpu,memory,request_cpu,request_memory,limit_cpu,limit_memory,generated_at
gke-prod-cluster,default,api-gateway,3/3,Running,0,45d,0.15 cores,256 Mi,0.50 cores,512 Mi,1.00 cores,1024 Mi,2025-12-15T17:05:23.456789+00:00
gke-prod-cluster,prod,orders-service,4/4,Running,1,30d,0.25 cores,1024 Mi,0.80 cores,768 Mi,1.00 cores,1024 Mi,2025-12-15T17:05:23.456789+00:00
```

### Ejemplo de salida JSON

```json
[
  {
    "cluster": "gke-prod-cluster",
    "namespace": "default",
    "deployment": "api-gateway",
    "pods": "3/3",
    "status": "Running",
    "restarts": 0,
    "age": "45d",
    "cpu": "0.15 cores",
    "memory": "256 Mi",
    "request_cpu": "0.50 cores",
    "request_memory": "512 Mi",
    "limit_cpu": "1.00 cores",
    "limit_memory": "1024 Mi",
    "pod_count": 3,
    "generated_at": "2025-12-15T17:05:23.456789+00:00"
  },
  {
    "cluster": "gke-prod-cluster",
    "namespace": "prod",
    "deployment": "orders-service",
    "pods": "4/4",
    "status": "Running",
    "restarts": 1,
    "age": "30d",
    "cpu": "0.25 cores",
    "memory": "1024 Mi",
    "request_cpu": "0.80 cores",
    "request_memory": "768 Mi",
    "limit_cpu": "1.00 cores",
    "limit_memory": "1024 Mi",
    "pod_count": 4,
    "generated_at": "2025-12-15T17:05:23.456789+00:00"
  }
]
```

---

## 🔍 Interpretación de los datos

### Columnas de uso en tiempo real

* **cpu** / **memory**: Uso promedio actual de todos los pods del deployment (requiere metrics-server).

* Si aparece `N/A`, significa que:

  * No hay metrics-server instalado.

  * Los pods no están en estado `Running`.

  * Hubo un error al consultar las métricas.

### Columnas de configuración del manifiesto

* **request_cpu** / **request_memory**: Recursos solicitados (garantizados) por el deployment.

* **limit_cpu** / **limit_memory**: Límites máximos de recursos que puede consumir el deployment.

* Si aparece `N/A`, significa que no hay `requests` o `limits` definidos en el manifiesto del deployment.

### Status

* **Running**: Todos los pods están en estado `Running`.

* **Pending**: Al menos un pod está en estado `Pending`.

* **Failed**: Al menos un pod está en estado `Failed`.

* **Mixed**: Combinación de estados diferentes.

* **Unknown**: No se pudo determinar el estado (sin pods o sin selector).

### Restarts

* Suma total de restarts de todos los containers de todos los pods del deployment.

* Un número alto puede indicar problemas de estabilidad (CrashLoopBackOff, OOMKilled, etc.).

### Age

* Antigüedad del deployment desde su creación.

* Formato: `Xd` (días), `Xh` (horas), `Xm` (minutos).

---

## 📊 Resúmenes

### Resumen por Status

Agrupa todos los deployments por su estado (`Running`, `Pending`, `Failed`, etc.) y muestra:

* Cantidad de deployments en ese estado.

* Total de pods listos (suma de `ready` de todos los deployments).

* Total de restarts.

### Resumen por Status + Limits

Agrupa por combinación de `(status, limit_cpu, limit_memory)` para identificar patrones de configuración y su relación con el estado de los deployments.

Útil para:

* Detectar deployments con la misma configuración de límites que están fallando.

* Identificar configuraciones comunes en producción.

* Auditar consistencia de configuración de recursos.

---

## 🔧 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'kubernetes'`

Instala la dependencia:

```bash
pip install kubernetes
```

### Error: `Unable to connect to the server`

Verifica que tu contexto de `kubectl` esté configurado correctamente:

```bash
kubectl config current-context
kubectl get nodes
```

Si no tienes acceso, configura las credenciales del cluster:

```bash
gcloud container clusters get-credentials NOMBRE_CLUSTER \
  --region REGION \
  --project PROYECTO_ID
```

### CPU y Memory aparecen como `N/A`

Esto significa que metrics-server no está disponible o no está funcionando.

Verifica:

```bash
kubectl get deployment metrics-server -n kube-system
```

Si no está instalado, instálalo:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Error: `403 Forbidden` o permisos insuficientes

Tu usuario o service account no tiene permisos suficientes en el cluster.

Solicita al administrador del cluster que te asigne el rol `view` o `cluster-reader`:

```bash
kubectl create clusterrolebinding USER-view \
  --clusterrole=view \
  --user=TU_EMAIL@example.com
```

### Algunos deployments no aparecen

El script lista **todos los deployments de todos los namespaces** del cluster actual.

Si no aparecen, verifica:

```bash
kubectl get deployments --all-namespaces
```

---

## 🌐 Múltiples clusters

Si quieres generar reportes para varios clusters, puedes hacer un loop:

```bash
#!/bin/bash

CLUSTERS=("cluster-prod" "cluster-stage" "cluster-dev")
REGION="us-central1"
PROJECT="mi-proyecto-gcp"

for cluster in "${CLUSTERS[@]}"; do
  echo "Generando reporte para $cluster..."
  gcloud container clusters get-credentials "$cluster" \
    --region "$REGION" \
    --project "$PROJECT"
  
  python3 gke_deployments_report.py --output-dir "reportes/$cluster"
done

echo "✅ Reportes generados para todos los clusters"
```

---

## 📝 Notas adicionales

* El script **no modifica** ningún recurso del cluster, solo lee información.

* Los timestamps están en formato **UTC ISO 8601** para facilitar la trazabilidad y comparación entre reportes.

* El campo `generated_at` en JSON/CSV permite identificar exactamente cuándo se generó cada fila del reporte.

* Los resúmenes son útiles para dashboards, alertas y análisis de tendencias.

---

## 🤝 Contribuciones

Si encuentras algún bug o tienes sugerencias de mejora, por favor:

1. Abre un issue describiendo el problema o la mejora.

2. Si tienes un fix, crea un pull request con los cambios.

---

## 📄 Licencia

Este script es de uso libre para fines internos y educativos.

---

## 👤 Autor

**Harold Adrian**

Desarrollado para monitoreo y auditoría de recursos en clusters GKE.

**Contacto**: DevSecOps Team

---

## 🔗 Referencias

* [Kubernetes Python Client](https://github.com/kubernetes-client/python)

* [Metrics Server](https://github.com/kubernetes-sigs/metrics-server)

* [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)

* [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-09-09 | 1.7.70 | generate_gcp_dashboard.py: GKE mueve Estado/Status Summary al final; Red GKE colorea Pods/SVCS IPs por semáforo; Compute fix diskSizeGb y Estado al final; Cloud Run agrega VPC y Estado (PUBLIC_URL rojo si ingress=all) |
| 2026-09-09 | 1.7.69 | generate_gcp_dashboard.py: Dashboard HTML interactivo con sistema de pestañas (tabs) por tipo de recurso, filtros globales y por columna, ordenamiento, badges de color, paginación y modal de hallazgos. 8 dimensiones: Servicios, GKE, Red GKE, Cloud SQL, Compute, Cloud Run, Pub/Sub, Inventario |
| 2026-09-09 | 1.7.68 | gcp_monitor.py: Columna BDs (conteo de bases de datos) en tabla Cloud SQL, obtenido en paralelo con ThreadPoolExecutor |
| 2026-09-09 | 1.7.67 | gcp_monitor.py: Tabla Servicios Habilitados convertida en resumen por proyecto (conteo + estado) en vez de listado individual |
| 2026-09-09 | 1.7.66 | gcp_monitor.py: Estados con color (format_status_color): STOPPED rojo, RUNNING verde en tablas Cloud SQL y Compute Engine |
| 2026-09-09 | 1.7.65 | gcp_monitor.py: format_duration() para tiempo legible (s/min/h) + retiro de columnas CPU/Memoria/Disco Usado de Compute Engine |
| 2026-09-09 | 1.7.64 | gcp_monitor.py: Retiro de columnas PODS IPs, SERVICES IPs, IP STATUS de tabla Clusters GKE (siguen en tabla Capacidad de Red) |
| 2026-09-09 | 1.7.63 | gcp_monitor.py: Paralelizar get_gke_metrics_parallel con ThreadPoolExecutor(max_workers=6) |
| 2026-09-09 | 1.7.62 | gcp_monitor.py: Paralelizar build_gke_cluster_enrichment + cache de get-credentials (_ensure_cluster_credentials) |
| 2026-09-09 | 1.7.61 | gcp_monitor.py: Timeouts en kubectl/gcloud (30s-120s) + parsing de gcloud describe como texto (no JSON) |
| 2026-09-09 | 1.7.60 | gcp_monitor.py: Enriquecer opción 1 con GKE Cluster Checker (opción 14) e IP Addresses Checker (opción 13) |
| 2026-08-31 | 3.1.3 | gcp_monitor.py: Monitoreo Cloud Run con info (URL, concurrencia, limits, ingress) + métricas (requests, latencia p95, CPU%, mem%) |
| 2026-08-31 | 3.1.2 | gcp_monitor.py: Fix métricas Compute Engine usando instance_id numérico, reporte consolidado con Rich Table, fix spinners en pipe |
| 2026-02-20 | 3.1.0 | gcp_monitor.py: Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-20 | 3.0.0 | gcp_monitor.py: Refactorizado para usar gcloud CLI, monitoreo de GKE, Cloud SQL, Compute Engine, Cloud Run, Pub/Sub |
| 2026-02-19 | 2.1.0 | gcp_monitor.py: Export CSV/JSON, show_help(), get_args(), fallback sin Rich, --max-workers |
| 2026-02-19 | 2.0.0 | gcp_monitor.py: Validación conexión GCP, paralelización, tablas Rich, --project opcional |
| 2026-01-12 | 1.2.0 | Actualización de documentación: integración de gcp_monitor.py, tabla de contenido |
| 2025-12-15 | 1.1.0 | Mejoras en gke_deployments_report.py: resúmenes por status y limits |
| 2025-01-01 | 1.0.0 | Versión inicial con gke_deployments_report.py |