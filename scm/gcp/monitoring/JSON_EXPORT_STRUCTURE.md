# 📊 Estructura del JSON Export - Fase 2 Completa

**Versión**: 1.7.2  
**Fecha**: 18 de Julio de 2026  
**Status**: ✅ Implementado

---

## 📋 Resumen

El JSON export ahora incluye **toda la información de las tablas**, incluyendo:
- ✅ Capacidad (CPU Total, Memoria Total, Disco Raíz)
- ✅ Uso Actual (CPU Usado %, Memoria Usada %, Disco Usado %)
- ✅ Metadatos (versión, timestamps, timezone)
- ✅ Resumen consolidado (conteos por tipo de recurso)

---

## 🏗️ Estructura General

```json
{
  "report_metadata": {
    "tool_name": "GCP Monitor",
    "version": "1.7.2",
    "report_type": "consolidated|single_project",
    "generated_at": "2026-07-18T15:30:45.123456-07:00",
    "timezone": "America/Mazatlan",
    "timestamp_utc": "2026-07-18T22:30:45.123456+00:00"
  },
  "summary": {
    "total_projects": 2,
    "total_services": 45,
    "total_gke_clusters": 8,
    "total_sql_instances": 12,
    "total_compute_instances": 35,
    "total_cloud_run_services": 5,
    "total_pubsub_topics": 10,
    "projects": {
      "project-1": { ... },
      "project-2": { ... }
    }
  },
  "data": {
    "project-1": { ... },
    "project-2": { ... }
  }
}
```

---

## 📊 Estructura de Datos por Proyecto

### **GKE Clusters**

```json
{
  "gke_clusters": [
    {
      "name": "gke-cs-wms-dev-01",
      "location": "us-central1",
      "status": "RUNNING",
      "currentMasterVersion": "1.28.5",
      "currentNodeCount": 16,
      "nodePools": [
        {
          "name": "default-pool",
          "config": {
            "machineType": "n2d-standard-4"
          },
          "currentNodeCount": 16,
          "initialNodeCount": 3
        }
      ],
      "usage_metrics": {
        "cpu_used_percent": 45.2,
        "memory_used_percent": 62.1,
        "status": "success"
      }
    }
  ]
}
```

**Campos de Capacidad**:
- `nodePools[].config.machineType`: Tipo de máquina (n2d-standard-4)
- `nodePools[].currentNodeCount`: Número de nodos activos
- CPU Total = machineType.cpu × currentNodeCount
- Memoria Total = machineType.memory × currentNodeCount

**Campos de Uso** (Fase 2):
- `usage_metrics.cpu_used_percent`: CPU usado en porcentaje (45.2%)
- `usage_metrics.memory_used_percent`: Memoria usada en porcentaje (62.1%)
- `usage_metrics.status`: Estado de la métrica (success|error|unavailable)

---

### **Compute Engine Instances**

```json
{
  "compute_instances": [
    {
      "name": "instance-01",
      "status": "RUNNING",
      "zone": "us-central1-a",
      "machineType": "zones/us-central1-a/machineTypes/n1-standard-4",
      "disks": [
        {
          "boot": true,
          "sizeGb": "100"
        }
      ],
      "usage_metrics": {
        "cpu_used_percent": 35.2,
        "memory_used_percent": 58.1,
        "disk_used_percent": 72.3,
        "status": "success"
      }
    }
  ]
}
```

**Campos de Capacidad**:
- `machineType`: Tipo de máquina (n1-standard-4)
- `disks[0].sizeGb`: Tamaño del disco raíz en GB
- CPU = machineType.cpu
- Memoria = machineType.memory
- Disco Raíz = disks[0].sizeGb

**Campos de Uso** (Fase 2):
- `usage_metrics.cpu_used_percent`: CPU usado en porcentaje (35.2%)
- `usage_metrics.memory_used_percent`: Memoria usada en porcentaje (58.1%)
- `usage_metrics.disk_used_percent`: Disco usado en porcentaje (72.3%)
- `usage_metrics.status`: Estado de la métrica (success|error|unavailable)

---

### **Cloud SQL Instances**

```json
{
  "sql_instances": [
    {
      "name": "cloudsql-prod-01",
      "state": "RUNNABLE",
      "databaseVersion": "MYSQL_8_0",
      "settings": {
        "tier": "db-n1-standard-4",
        "dataDiskSizeGb": "100"
      }
    }
  ]
}
```

---

### **Cloud Run Services**

```json
{
  "cloud_run": [
    {
      "name": "api-service",
      "status": "ACTIVE",
      "location": "us-central1"
    }
  ]
}
```

---

### **Pub/Sub Topics**

```json
{
  "pubsub_topics": [
    {
      "name": "projects/project-id/topics/topic-name",
      "messageRetentionDuration": "604800s"
    }
  ]
}
```

---

## 📈 Ejemplo Completo (Consolidado)

```json
{
  "report_metadata": {
    "tool_name": "GCP Monitor",
    "version": "1.7.2",
    "report_type": "consolidated",
    "generated_at": "2026-07-18T15:30:45.123456-07:00",
    "timezone": "America/Mazatlan",
    "timestamp_utc": "2026-07-18T22:30:45.123456+00:00"
  },
  "summary": {
    "total_projects": 1,
    "total_services": 45,
    "total_gke_clusters": 1,
    "total_sql_instances": 2,
    "total_compute_instances": 3,
    "total_cloud_run_services": 1,
    "total_pubsub_topics": 2,
    "projects": {
      "cpl-cmanager-dev-13072023": {
        "total_services": 45,
        "total_gke_clusters": 1,
        "total_sql_instances": 2,
        "total_compute_instances": 3,
        "total_cloud_run_services": 1,
        "total_pubsub_topics": 2
      }
    }
  },
  "data": {
    "cpl-cmanager-dev-13072023": {
      "enabled_services": [ ... ],
      "gke_clusters": [
        {
          "name": "gke-cs-wms-dev-01",
          "location": "us-central1",
          "status": "RUNNING",
          "currentMasterVersion": "1.28.5",
          "currentNodeCount": 16,
          "nodePools": [
            {
              "name": "default-pool",
              "config": {
                "machineType": "n2d-standard-4"
              },
              "currentNodeCount": 16
            }
          ],
          "usage_metrics": {
            "cpu_used_percent": 45.2,
            "memory_used_percent": 62.1,
            "status": "success"
          }
        }
      ],
      "sql_instances": [ ... ],
      "compute_instances": [
        {
          "name": "instance-01",
          "status": "RUNNING",
          "zone": "us-central1-a",
          "machineType": "zones/us-central1-a/machineTypes/n1-standard-4",
          "disks": [
            {
              "boot": true,
              "sizeGb": "100"
            }
          ],
          "usage_metrics": {
            "cpu_used_percent": 35.2,
            "memory_used_percent": 58.1,
            "disk_used_percent": 72.3,
            "status": "success"
          }
        }
      ],
      "cloud_run": [ ... ],
      "pubsub_topics": [ ... ]
    }
  }
}
```

---

## 🔄 Flujo de Generación del JSON

```
1. Ejecutar: python gcp_monitor.py --project=proj1 --output=json

2. Recopilar datos de GCP:
   ├─ Servicios habilitados
   ├─ Clusters GKE
   ├─ Instancias Cloud SQL
   ├─ Instancias Compute Engine
   ├─ Servicios Cloud Run
   └─ Topics Pub/Sub

3. Enriquecer con métricas de uso:
   ├─ Para cada cluster GKE:
   │  ├─ Obtener CPU usado (%)
   │  └─ Obtener Memoria usada (%)
   └─ Para cada instancia Compute:
      ├─ Obtener CPU usado (%)
      ├─ Obtener Memoria usada (%)
      └─ Obtener Disco usado (%)

4. Generar JSON con estructura:
   ├─ report_metadata (versión, timestamps)
   ├─ summary (conteos)
   └─ data (recursos con métricas)

5. Guardar en: outcome/gcp_report_[project]_[timestamp].json
```

---

## 📊 Comparación: Antes vs Después

### **Antes (v1.7.1)**

```json
{
  "gke_clusters": [
    {
      "name": "gke-cs-wms-dev-01",
      "location": "us-central1",
      "status": "RUNNING"
      // ❌ Sin métricas de uso
    }
  ]
}
```

### **Después (v1.7.2)**

```json
{
  "gke_clusters": [
    {
      "name": "gke-cs-wms-dev-01",
      "location": "us-central1",
      "status": "RUNNING",
      "usage_metrics": {
        "cpu_used_percent": 45.2,
        "memory_used_percent": 62.1,
        "status": "success"
      }
      // ✅ Con métricas de uso
    }
  ]
}
```

---

## 🎯 Cómo Usar el JSON

### **Leer con Python**

```python
import json

with open('outcome/gcp_report_project-id_20260718_153045.json', 'r') as f:
    data = json.load(f)

# Acceder a metadatos
print(f"Versión: {data['report_metadata']['version']}")
print(f"Generado: {data['report_metadata']['generated_at']}")

# Acceder a resumen
print(f"Total clusters: {data['summary']['total_gke_clusters']}")

# Acceder a clusters con métricas
for project_id, proj_data in data['data'].items():
    for cluster in proj_data['gke_clusters']:
        print(f"Cluster: {cluster['name']}")
        print(f"  CPU usado: {cluster['usage_metrics']['cpu_used_percent']}%")
        print(f"  Memoria usada: {cluster['usage_metrics']['memory_used_percent']}%")
```

### **Leer con jq (CLI)**

```bash
# Ver versión
jq '.report_metadata.version' gcp_report_*.json

# Ver clusters con CPU > 50%
jq '.data[].gke_clusters[] | select(.usage_metrics.cpu_used_percent > 50)' gcp_report_*.json

# Ver resumen
jq '.summary' gcp_report_*.json
```

---

## ✅ Checklist de Contenido

- ✅ Metadatos (versión, timestamps, timezone)
- ✅ Resumen consolidado (conteos por tipo)
- ✅ Datos de capacidad (CPU Total, Memoria Total, Disco)
- ✅ Datos de uso (CPU Usado %, Memoria Usada %, Disco Usado %)
- ✅ Estado de métricas (success|error|unavailable)
- ✅ Información completa de recursos
- ✅ Estructura estándar y consistente

---

## 📁 Archivos Generados

| Tipo | Nombre | Ejemplo |
|------|--------|---------|
| **Consolidado** | `gcp_report_consolidated_YYYYMMDD_HHMMSS.json` | `gcp_report_consolidated_20260718_153045.json` |
| **Individual** | `gcp_report_PROJECT_ID_YYYYMMDD_HHMMSS.json` | `gcp_report_cpl-cmanager-dev_20260718_153045.json` |

---

## 🎯 Conclusión

El JSON export ahora contiene **toda la información impresa en las tablas**:

✅ Capacidad (CPU, Memoria, Disco)  
✅ Uso Actual (CPU %, Memoria %, Disco %)  
✅ Metadatos completos  
✅ Resumen consolidado  
✅ Estructura estándar  

**Listo para usar en análisis, reportes y automatizaciones**.

---

**Implementación**: ✅ Completada  
**Commit**: f16fb54  
**Status**: Listo para producción
