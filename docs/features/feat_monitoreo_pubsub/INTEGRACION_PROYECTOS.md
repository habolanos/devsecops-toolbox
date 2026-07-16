# 🔗 Integración con Proyectos Reales - Pub/Sub Monitor

**Versión**: 1.0  
**Fecha**: 16 de Julio de 2026

---

## 📋 Tabla de Contenidos

1. [Proyectos Soportados](#proyectos-soportados)
2. [Configuración por Proyecto](#configuración-por-proyecto)
3. [Integración con config.json](#integración-con-configjson)
4. [Validación de Conectividad](#validación-de-conectividad)
5. [Mapeo de Alertas](#mapeo-de-alertas)

---

## 🎯 Proyectos Soportados

### Estructura de Proyectos

El monitor soporta **12 proyectos GCP** organizados en 4 líneas de negocio:

```
CPL (Cadena de Suministro)
├── cpl-cmanager (Customer Manager)
│   ├── cpl-cmanager-dev-13072023 (Desarrollo)
│   ├── cpl-cmanager-qa-13072023 (QA)
│   └── cpl-cmanager-stag-01052025 (Staging)
│
├── cpl-cs-csc (Customer Service Center)
│   ├── cpl-cs-csc-dev-16112023 (Desarrollo)
│   ├── cpl-cs-csc-qa-16112023 (QA)
│   └── cpl-cs-csc-stag-11042025 (Staging)
│
├── cpl-cs-wms (Warehouse Management System)
│   ├── cpl-cs-wms-dev-30112023 (Desarrollo)
│   ├── cpl-cs-wms-qa-30112023 (QA)
│   └── cpl-cs-wms-stag-09042025 (Staging)
│
└── cpl-oms (Order Management System)
    ├── cpl-oms-dev-08082024 (Desarrollo)
    ├── cpl-oms-qa-08062023 (QA)
    └── cpl-oms-stag-09042025 (Staging)
```

### Detalles por Proyecto

| Proyecto | Ambiente | ID | Creado | Propósito |
|----------|----------|-----|--------|-----------|
| **cpl-cmanager** | Dev | cpl-cmanager-dev-13072023 | 13/07/2023 | Gestión de clientes |
| **cpl-cmanager** | QA | cpl-cmanager-qa-13072023 | 13/07/2023 | Testing de clientes |
| **cpl-cmanager** | Staging | cpl-cmanager-stag-01052025 | 01/05/2025 | Pre-producción |
| **cpl-cs-csc** | Dev | cpl-cs-csc-dev-16112023 | 16/11/2023 | Centro de servicio |
| **cpl-cs-csc** | QA | cpl-cs-csc-qa-16112023 | 16/11/2023 | Testing de servicio |
| **cpl-cs-csc** | Staging | cpl-cs-csc-stag-11042025 | 11/04/2025 | Pre-producción |
| **cpl-cs-wms** | Dev | cpl-cs-wms-dev-30112023 | 30/11/2023 | Almacén desarrollo |
| **cpl-cs-wms** | QA | cpl-cs-wms-qa-30112023 | 30/11/2023 | Almacén testing |
| **cpl-cs-wms** | Staging | cpl-cs-wms-stag-09042025 | 09/04/2025 | Almacén pre-prod |
| **cpl-oms** | Dev | cpl-oms-dev-08082024 | 08/08/2024 | Órdenes desarrollo |
| **cpl-oms** | QA | cpl-oms-qa-08062023 | 08/06/2023 | Órdenes testing |
| **cpl-oms** | Staging | cpl-oms-stag-09042025 | 09/04/2025 | Órdenes pre-prod |

---

## ⚙️ Configuración por Proyecto

### Configuración en config.json.template

```json
{
  "gcp": {
    "service_accounts_reporter": {
      "_info": "Configuración para el reporte multi-proyecto de service accounts (Tool 38)",
      "enabled": true,
      "_enabled_info": "Cambiar a true para habilitar el reporte de service accounts",
      
      "projects": [
        "cpl-cmanager-dev-13072023",
        "cpl-cmanager-qa-13072023",
        "cpl-cmanager-stag-01052025",
        "cpl-cs-csc-dev-16112023",
        "cpl-cs-csc-qa-16112023",
        "cpl-cs-csc-stag-11042025",
        "cpl-cs-wms-dev-30112023",
        "cpl-cs-wms-qa-30112023",
        "cpl-cs-wms-stag-09042025",
        "cpl-oms-dev-08082024",
        "cpl-oms-qa-08062023",
        "cpl-oms-stag-09042025"
      ],
      "_projects_info": "Array de nombres de proyectos GCP a analizar",
      
      "defaults": {
        "mode": "all",
        "_mode_info": "Opciones: all, security, compliance, usage",
        "output_format": "json",
        "_output_format_info": "Opciones: json, csv, excel, html",
        "include_activity": true,
        "activity_days": 30,
        "key_rotation_policy_days": 90,
        "parallel_workers": 5,
        "_parallel_workers_info": "Número de workers para paralelización",
        "timeout_seconds": 300,
        "cache_enabled": true,
        "cache_ttl_minutes": 60
      }
    }
  }
}
```

---

## 🔌 Integración con config.json

### Paso 1: Copiar Template

```bash
cp scm/config.json.template scm/config.json
```

### Paso 2: Verificar Proyectos

```bash
# Listar proyectos configurados
grep -A 15 "service_accounts_reporter" scm/config.json | grep "cpl-"
```

### Paso 3: Validar Acceso

```bash
# Verificar que gcloud tiene acceso a los proyectos
for project in cpl-cmanager-dev-13072023 cpl-cmanager-qa-13072023 cpl-cmanager-stag-01052025; do
  echo "Validando $project..."
  gcloud config set project $project
  gcloud pubsub topics list --limit=1
done
```

### Paso 4: Configurar Alertas

```json
{
  "alerts": {
    "enabled": true,
    "notifications": {
      "email": {
        "enabled": true,
        "recipients": ["ops@company.com"]
      },
      "slack": {
        "enabled": true,
        "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
      }
    }
  }
}
```

---

## ✅ Validación de Conectividad

### Script de Validación

```bash
#!/bin/bash

echo "🔍 Validando conectividad a proyectos GCP..."
echo ""

PROJECTS=(
  "cpl-cmanager-dev-13072023"
  "cpl-cmanager-qa-13072023"
  "cpl-cmanager-stag-01052025"
  "cpl-cs-csc-dev-16112023"
  "cpl-cs-csc-qa-16112023"
  "cpl-cs-csc-stag-11042025"
  "cpl-cs-wms-dev-30112023"
  "cpl-cs-wms-qa-30112023"
  "cpl-cs-wms-stag-09042025"
  "cpl-oms-dev-08082024"
  "cpl-oms-qa-08062023"
  "cpl-oms-stag-09042025"
)

SUCCESS=0
FAILED=0

for project in "${PROJECTS[@]}"; do
  echo -n "Validando $project... "
  
  if gcloud pubsub topics list --project=$project --limit=1 &>/dev/null; then
    echo "✅ OK"
    ((SUCCESS++))
  else
    echo "❌ FALLO"
    ((FAILED++))
  fi
done

echo ""
echo "═══════════════════════════════════════════════════════"
echo "Resultados: $SUCCESS OK, $FAILED FALLO"
echo "═══════════════════════════════════════════════════════"
```

### Validación en Python

```python
from google.cloud import pubsub_v1

projects = [
    "cpl-cmanager-dev-13072023",
    "cpl-cmanager-qa-13072023",
    "cpl-cmanager-stag-01052025",
    "cpl-cs-csc-dev-16112023",
    "cpl-cs-csc-qa-16112023",
    "cpl-cs-csc-stag-11042025",
    "cpl-cs-wms-dev-30112023",
    "cpl-cs-wms-qa-30112023",
    "cpl-cs-wms-stag-09042025",
    "cpl-oms-dev-08082024",
    "cpl-oms-qa-08062023",
    "cpl-oms-stag-09042025"
]

publisher = pubsub_v1.PublisherClient()

print("🔍 Validando conectividad a proyectos GCP...")
print()

success = 0
failed = 0

for project_id in projects:
    try:
        project_path = publisher.project_path(project_id)
        topics = list(publisher.list_topics(request={"project": project_path}))
        print(f"✅ {project_id}: {len(topics)} topics")
        success += 1
    except Exception as e:
        print(f"❌ {project_id}: {str(e)}")
        failed += 1

print()
print("═" * 60)
print(f"Resultados: {success} OK, {failed} FALLO")
print("═" * 60)
```

---

## 📊 Mapeo de Alertas por Proyecto

### Alertas por Línea de Negocio

#### cpl-cmanager (Customer Manager)

```yaml
Proyecto: cpl-cmanager-dev-13072023
Ambiente: Desarrollo
Alertas Críticas:
  - Backlog > 50k (warning)
  - Latencia P95 > 2s (warning)
  - Error rate > 2% (warning)

Proyecto: cpl-cmanager-qa-13072023
Ambiente: QA
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)
  - Error rate > 5% (critical)

Proyecto: cpl-cmanager-stag-01052025
Ambiente: Staging
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)
  - Error rate > 5% (critical)
```

#### cpl-cs-csc (Customer Service Center)

```yaml
Proyecto: cpl-cs-csc-dev-16112023
Ambiente: Desarrollo
Alertas Críticas:
  - Backlog > 50k (warning)
  - Latencia P95 > 2s (warning)

Proyecto: cpl-cs-csc-qa-16112023
Ambiente: QA
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)

Proyecto: cpl-cs-csc-stag-11042025
Ambiente: Staging
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)
```

#### cpl-cs-wms (Warehouse Management System)

```yaml
Proyecto: cpl-cs-wms-dev-30112023
Ambiente: Desarrollo
Alertas Críticas:
  - Backlog > 50k (warning)
  - Latencia P95 > 2s (warning)

Proyecto: cpl-cs-wms-qa-30112023
Ambiente: QA
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)

Proyecto: cpl-cs-wms-stag-09042025
Ambiente: Staging
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)
```

#### cpl-oms (Order Management System)

```yaml
Proyecto: cpl-oms-dev-08082024
Ambiente: Desarrollo
Alertas Críticas:
  - Backlog > 50k (warning)
  - Latencia P95 > 2s (warning)

Proyecto: cpl-oms-qa-08062023
Ambiente: QA
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)

Proyecto: cpl-oms-stag-09042025
Ambiente: Staging
Alertas Críticas:
  - Backlog > 100k (critical)
  - Latencia P95 > 5s (critical)
```

---

## 🎯 Configuración por Ambiente

### Desarrollo

```json
{
  "projects": [
    "cpl-cmanager-dev-13072023",
    "cpl-cs-csc-dev-16112023",
    "cpl-cs-wms-dev-30112023",
    "cpl-oms-dev-08082024"
  ],
  "thresholds": {
    "backlog_critical": 50000,
    "latency_p95_critical_ms": 2000,
    "error_rate_critical": 2
  },
  "notifications": {
    "slack": "#dev-alerts"
  }
}
```

### QA

```json
{
  "projects": [
    "cpl-cmanager-qa-13072023",
    "cpl-cs-csc-qa-16112023",
    "cpl-cs-wms-qa-30112023",
    "cpl-oms-qa-08062023"
  ],
  "thresholds": {
    "backlog_critical": 100000,
    "latency_p95_critical_ms": 5000,
    "error_rate_critical": 5
  },
  "notifications": {
    "slack": "#qa-alerts"
  }
}
```

### Staging

```json
{
  "projects": [
    "cpl-cmanager-stag-01052025",
    "cpl-cs-csc-stag-11042025",
    "cpl-cs-wms-stag-09042025",
    "cpl-oms-stag-09042025"
  ],
  "thresholds": {
    "backlog_critical": 100000,
    "latency_p95_critical_ms": 5000,
    "error_rate_critical": 5
  },
  "notifications": {
    "slack": "#staging-alerts",
    "email": ["ops@company.com"]
  }
}
```

---

## 📈 Monitoreo Multi-Proyecto

### Dashboard Consolidado

El monitor genera un dashboard que consolida datos de todos los 12 proyectos:

```
┌─────────────────────────────────────────────────────────────┐
│          Pub/Sub Monitor - Dashboard Consolidado            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Resumen General:                                           │
│  • Proyectos Monitoreados: 12                               │
│  • Topics Totales: 145                                      │
│  • Subscriptions Totales: 280                               │
│  • Tasa de Entrega: 98.5%                                   │
│  • Alertas Activas: 3                                       │
│                                                             │
│  Por Línea de Negocio:                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ cpl-cmanager    │ 45 topics │ 85 subs │ 99.2% │ ✅  │   │
│  │ cpl-cs-csc      │ 35 topics │ 70 subs │ 98.1% │ ⚠️  │   │
│  │ cpl-cs-wms      │ 40 topics │ 75 subs │ 97.8% │ ⚠️  │   │
│  │ cpl-oms         │ 25 topics │ 50 subs │ 99.0% │ ✅  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Alertas Activas:                                           │
│  1. [WARNING] cpl-cs-csc-qa: Backlog elevado (75k)         │
│  2. [WARNING] cpl-cs-wms-stag: Latencia P95 (4.8s)         │
│  3. [INFO] cpl-oms-dev: Sin dead-letter policy             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Reportes por Proyecto

```bash
# Reporte consolidado de todos los proyectos
pubsub-monitor --config config.json --mode all

# Reporte de un proyecto específico
pubsub-monitor --config config.json --project cpl-cmanager-stag-01052025

# Reporte de un ambiente específico
pubsub-monitor --config config.json --environment staging

# Reporte de una línea de negocio
pubsub-monitor --config config.json --business-unit cpl-cmanager
```

---

## 🔐 Seguridad por Proyecto

### Validación de Acceso

```bash
# Verificar permisos en cada proyecto
for project in cpl-cmanager-dev-13072023 cpl-cmanager-qa-13072023; do
  echo "Validando permisos en $project..."
  gcloud projects get-iam-policy $project \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount@*"
done
```

### Roles Requeridos por Proyecto

```yaml
Roles Necesarios:
  - roles/pubsub.viewer (Lectura de Pub/Sub)
  - roles/monitoring.metricReader (Lectura de métricas)
  - roles/logging.viewer (Lectura de logs)
  - roles/resourcemanager.organizationViewer (Multi-proyecto)

Service Account:
  - pubsub-monitor@<project>.iam.gserviceaccount.com
  - Permisos: Viewer en todos los proyectos
```

---

**Versión**: 1.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ Integración Completada

