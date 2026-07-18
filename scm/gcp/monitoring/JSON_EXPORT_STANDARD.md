# 📋 Estándar de Exportación JSON - GCP Monitor

**Versión**: 1.7.1  
**Fecha**: 18 de Julio de 2026  
**Estado**: ✅ IMPLEMENTADO

---

## 📊 Resumen Ejecutivo

Se ha implementado un **estándar de exportación JSON** que soporta:

1. **Exportación Consolidada** (múltiples proyectos)
2. **Exportación de Proyecto Individual**
3. **Estructura Estándar del Proyecto**
4. **Metadatos Completos**

---

## 🏗️ Estructura JSON - Exportación Consolidada

### **Archivo**: `gcp_report_consolidated_YYYYMMDD_HHMMSS.json`

```json
{
  "report_metadata": {
    "tool_name": "GCP Monitor",
    "version": "1.7.1",
    "report_type": "consolidated",
    "generated_at": "2026-07-18T14:30:45.123456-07:00",
    "timezone": "America/Mazatlan",
    "timestamp_utc": "2026-07-18T21:30:45.123456+00:00"
  },
  "summary": {
    "total_projects": 3,
    "total_services": 125,
    "total_gke_clusters": 15,
    "total_sql_instances": 25,
    "total_compute_instances": 95,
    "total_cloud_run_services": 12,
    "total_pubsub_topics": 8,
    "projects": {
      "cpl-cs-wms-dev-30112023": {
        "total_services": 45,
        "total_gke_clusters": 3,
        "total_sql_instances": 8,
        "total_compute_instances": 35,
        "total_cloud_run_services": 4,
        "total_pubsub_topics": 2
      },
      "cpl-cs-wms-qa-30112023": {
        "total_services": 40,
        "total_gke_clusters": 3,
        "total_sql_instances": 8,
        "total_compute_instances": 30,
        "total_cloud_run_services": 4,
        "total_pubsub_topics": 3
      },
      "cpl-cs-wms-stag-09042025": {
        "total_services": 40,
        "total_gke_clusters": 3,
        "total_sql_instances": 9,
        "total_compute_instances": 30,
        "total_cloud_run_services": 4,
        "total_pubsub_topics": 3
      }
    }
  },
  "data": {
    "cpl-cs-wms-dev-30112023": {
      "enabled_services": [...],
      "gke_clusters": [...],
      "sql_instances": [...],
      "compute_instances": [...],
      "cloud_run": [...],
      "pubsub_topics": [...]
    },
    "cpl-cs-wms-qa-30112023": {
      "enabled_services": [...],
      "gke_clusters": [...],
      "sql_instances": [...],
      "compute_instances": [...],
      "cloud_run": [...],
      "pubsub_topics": [...]
    },
    "cpl-cs-wms-stag-09042025": {
      "enabled_services": [...],
      "gke_clusters": [...],
      "sql_instances": [...],
      "compute_instances": [...],
      "cloud_run": [...],
      "pubsub_topics": [...]
    }
  }
}
```

---

## 🏗️ Estructura JSON - Exportación Individual

### **Archivo**: `gcp_report_{project_id}_YYYYMMDD_HHMMSS.json`

```json
{
  "report_metadata": {
    "tool_name": "GCP Monitor",
    "version": "1.7.1",
    "report_type": "single_project",
    "project_id": "cpl-cs-wms-dev-30112023",
    "generated_at": "2026-07-18T14:30:45.123456-07:00",
    "timezone": "America/Mazatlan",
    "timestamp_utc": "2026-07-18T21:30:45.123456+00:00"
  },
  "summary": {
    "total_services": 45,
    "total_gke_clusters": 3,
    "total_sql_instances": 8,
    "total_compute_instances": 35,
    "total_cloud_run_services": 4,
    "total_pubsub_topics": 2
  },
  "data": {
    "cpl-cs-wms-dev-30112023": {
      "enabled_services": [...],
      "gke_clusters": [...],
      "sql_instances": [...],
      "compute_instances": [...],
      "cloud_run": [...],
      "pubsub_topics": [...]
    }
  }
}
```

---

## 📋 Secciones Principales

### **1. `report_metadata`**

Información sobre el reporte generado.

| Campo | Tipo | Descripción |
|-------|------|------------|
| `tool_name` | string | Nombre de la herramienta ("GCP Monitor") |
| `version` | string | Versión de la herramienta (ej: "1.7.1") |
| `report_type` | string | Tipo de reporte ("consolidated" o "single_project") |
| `project_id` | string | ID del proyecto (solo en single_project) |
| `generated_at` | ISO 8601 | Fecha/hora de generación (zona local) |
| `timezone` | string | Zona horaria usada (ej: "America/Mazatlan") |
| `timestamp_utc` | ISO 8601 | Fecha/hora en UTC |

**Ejemplo**:
```json
{
  "tool_name": "GCP Monitor",
  "version": "1.7.1",
  "report_type": "consolidated",
  "generated_at": "2026-07-18T14:30:45.123456-07:00",
  "timezone": "America/Mazatlan",
  "timestamp_utc": "2026-07-18T21:30:45.123456+00:00"
}
```

---

### **2. `summary`**

Resumen de recursos encontrados.

#### **Para Exportación Consolidada**:
```json
{
  "total_projects": 3,
  "total_services": 125,
  "total_gke_clusters": 15,
  "total_sql_instances": 25,
  "total_compute_instances": 95,
  "total_cloud_run_services": 12,
  "total_pubsub_topics": 8,
  "projects": {
    "project_id_1": {
      "total_services": 45,
      "total_gke_clusters": 3,
      ...
    },
    "project_id_2": {
      "total_services": 40,
      "total_gke_clusters": 3,
      ...
    }
  }
}
```

#### **Para Exportación Individual**:
```json
{
  "total_services": 45,
  "total_gke_clusters": 3,
  "total_sql_instances": 8,
  "total_compute_instances": 35,
  "total_cloud_run_services": 4,
  "total_pubsub_topics": 2
}
```

---

### **3. `data`**

Datos detallados de recursos organizados por proyecto.

#### **Estructura**:
```json
{
  "data": {
    "project_id_1": {
      "enabled_services": [
        {
          "name": "compute.googleapis.com",
          "title": "Compute Engine API",
          "state": "ENABLED"
        },
        ...
      ],
      "gke_clusters": [
        {
          "name": "gke-cs-wms-dev-01",
          "location": "us-central1",
          "status": "RUNNING",
          "currentMasterVersion": "1.34.8-gke.1126",
          "currentNodeCount": 16,
          "nodePools": [...]
        },
        ...
      ],
      "sql_instances": [
        {
          "name": "psql-cs-wms-dev-01",
          "state": "RUNNABLE",
          "databaseVersion": "POSTGRES_17",
          "tier": "db-custom-8-32768",
          "currentDiskSize": "500"
        },
        ...
      ],
      "compute_instances": [
        {
          "name": "gke-gke-cs-wms-dev-0-pool-cs-w",
          "status": "RUNNING",
          "machineType": "zones/us-central1-a/machineTypes/n2d-standard-4",
          "zone": "us-central1-a",
          "disks": [...]
        },
        ...
      ],
      "cloud_run": [
        {
          "name": "service-name",
          "status": "ACTIVE",
          "region": "us-central1"
        },
        ...
      ],
      "pubsub_topics": [
        {
          "name": "projects/project-id/topics/topic-name"
        },
        ...
      ]
    },
    "project_id_2": {
      ...
    }
  }
}
```

---

## 🔄 Flujo de Exportación

### **Caso 1: Un Proyecto**
```
python gcp_monitor.py --project proj1 --output json
    ↓
Exportar a: gcp_report_proj1_20260718_143045.json
Tipo: single_project
Estructura: {report_metadata, summary, data: {proj1: {...}}}
```

### **Caso 2: Múltiples Proyectos**
```
python gcp_monitor.py --project proj1,proj2,proj3 --output json
    ↓
Exportar a: gcp_report_consolidated_20260718_143045.json
Tipo: consolidated
Estructura: {report_metadata, summary: {total_projects, projects: {...}}, data: {proj1, proj2, proj3}}
```

---

## 📊 Ejemplo Completo - Exportación Consolidada

```json
{
  "report_metadata": {
    "tool_name": "GCP Monitor",
    "version": "1.7.1",
    "report_type": "consolidated",
    "generated_at": "2026-07-18T14:30:45.123456-07:00",
    "timezone": "America/Mazatlan",
    "timestamp_utc": "2026-07-18T21:30:45.123456+00:00"
  },
  "summary": {
    "total_projects": 2,
    "total_services": 85,
    "total_gke_clusters": 6,
    "total_sql_instances": 16,
    "total_compute_instances": 65,
    "total_cloud_run_services": 8,
    "total_pubsub_topics": 5,
    "projects": {
      "cpl-cs-wms-dev-30112023": {
        "total_services": 45,
        "total_gke_clusters": 3,
        "total_sql_instances": 8,
        "total_compute_instances": 35,
        "total_cloud_run_services": 4,
        "total_pubsub_topics": 2
      },
      "cpl-cs-wms-qa-30112023": {
        "total_services": 40,
        "total_gke_clusters": 3,
        "total_sql_instances": 8,
        "total_compute_instances": 30,
        "total_cloud_run_services": 4,
        "total_pubsub_topics": 3
      }
    }
  },
  "data": {
    "cpl-cs-wms-dev-30112023": {
      "enabled_services": [
        {
          "name": "compute.googleapis.com",
          "title": "Compute Engine API",
          "state": "ENABLED"
        },
        {
          "name": "container.googleapis.com",
          "title": "Kubernetes Engine API",
          "state": "ENABLED"
        }
      ],
      "gke_clusters": [
        {
          "name": "gke-cs-wms-dev-01",
          "location": "us-central1",
          "status": "RUNNING",
          "currentMasterVersion": "1.34.8-gke.1126",
          "currentNodeCount": 16,
          "nodePools": [
            {
              "name": "default-pool",
              "initialNodeCount": 3,
              "currentNodeCount": 16,
              "config": {
                "machineType": "n2d-standard-4"
              }
            }
          ]
        }
      ],
      "sql_instances": [
        {
          "name": "psql-cs-wms-dev-01",
          "state": "RUNNABLE",
          "databaseVersion": "POSTGRES_17",
          "tier": "db-custom-8-32768",
          "currentDiskSize": "500"
        }
      ],
      "compute_instances": [
        {
          "name": "gke-gke-cs-wms-dev-0-pool-cs-w",
          "status": "RUNNING",
          "machineType": "zones/us-central1-a/machineTypes/n2d-standard-4",
          "zone": "us-central1-a",
          "disks": [
            {
              "boot": true,
              "sizeGb": "100"
            }
          ]
        }
      ],
      "cloud_run": [
        {
          "name": "service-api",
          "status": "ACTIVE",
          "region": "us-central1"
        }
      ],
      "pubsub_topics": [
        {
          "name": "projects/cpl-cs-wms-dev-30112023/topics/events"
        }
      ]
    },
    "cpl-cs-wms-qa-30112023": {
      "enabled_services": [...],
      "gke_clusters": [...],
      "sql_instances": [...],
      "compute_instances": [...],
      "cloud_run": [...],
      "pubsub_topics": [...]
    }
  }
}
```

---

## ✅ Características del Estándar

| Característica | Descripción |
|---|---|
| **Metadatos Completos** | Versión, tipo, timestamps, zona horaria |
| **Resumen Automático** | Conteos por tipo de recurso |
| **Consolidación** | Múltiples proyectos en un archivo |
| **Estructura Jerárquica** | Datos organizados por proyecto |
| **Timestamps ISO 8601** | Fecha/hora en formato estándar |
| **Zona Horaria** | Soporte para múltiples zonas horarias |
| **Formato Legible** | JSON con indentación (2 espacios) |
| **Codificación UTF-8** | Soporte para caracteres especiales |

---

## 🔍 Validación del JSON

### **Herramientas Recomendadas**

```bash
# Validar JSON con jq
jq . gcp_report_consolidated_20260718_143045.json

# Contar recursos
jq '.summary.total_gke_clusters' gcp_report_consolidated_20260718_143045.json

# Listar proyectos
jq '.summary.projects | keys' gcp_report_consolidated_20260718_143045.json

# Obtener datos de un proyecto específico
jq '.data."cpl-cs-wms-dev-30112023"' gcp_report_consolidated_20260718_143045.json
```

---

## 📝 Ejemplos de Uso

### **Exportar Múltiples Proyectos**
```bash
python gcp_monitor.py \
  --project cpl-cs-wms-dev-30112023,cpl-cs-wms-qa-30112023,cpl-cs-wms-stag-09042025 \
  --output json
```

**Resultado**: `gcp_report_consolidated_20260718_143045.json`

### **Exportar Un Proyecto**
```bash
python gcp_monitor.py \
  --project cpl-cs-wms-dev-30112023 \
  --output json
```

**Resultado**: `gcp_report_cpl-cs-wms-dev-30112023_20260718_143045.json`

---

## 🔄 Integración con Otros Sistemas

### **Procesar JSON en Python**
```python
import json

with open('gcp_report_consolidated_20260718_143045.json', 'r') as f:
    data = json.load(f)

# Acceder a metadatos
version = data['report_metadata']['version']
total_projects = data['summary']['total_projects']

# Iterar sobre proyectos
for project_id, project_data in data['data'].items():
    print(f"Proyecto: {project_id}")
    print(f"  Clusters GKE: {len(project_data['gke_clusters'])}")
    print(f"  Instancias SQL: {len(project_data['sql_instances'])}")
```

### **Procesar JSON en Bash**
```bash
# Extraer resumen
jq '.summary' gcp_report_consolidated_20260718_143045.json

# Contar recursos por tipo
jq '.data | to_entries | map({project: .key, clusters: (.value.gke_clusters | length)})' \
  gcp_report_consolidated_20260718_143045.json
```

---

## ✅ Validación Implementada

- ✅ Exportación consolidada de múltiples proyectos
- ✅ Exportación individual de proyectos
- ✅ Metadatos completos (versión, timestamps, zona horaria)
- ✅ Resumen automático de recursos
- ✅ Estructura jerárquica por proyecto
- ✅ Formato JSON estándar (indent=2, UTF-8)
- ✅ Timestamps en ISO 8601
- ✅ Soporte para múltiples zonas horarias

---

**Implementación completada**: ✅ 18 de Julio de 2026
