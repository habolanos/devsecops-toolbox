# Cloud Run VPC IP Diagnostic

Herramienta SRE para **diagnosticar saturación de IPs en VPC Connectors de Cloud Run** y **planificar rangos CIDR óptimos** por ambiente (Dev/QA/Stg/Prod).

## 🎯 Objetivo

- Detectar conectores VPC saturados o en riesgo de saturación
- Calcular proyección de uso de IPs por ambiente
- Recomendar rangos CIDR apropiados (/28 → /24 → /22 → /20)
- Generar plan de migración accionable

## 🚀 Uso Rápido

### Escenario típico: 4 ambientes, mismo Host Project (Shared VPC)

```bash
python gcp_cloudrun_vpc_ip_diagnostic.py \
  --projects cpl-corp-cial-dev,cpl-corp-cial-qa,cpl-corp-cial-stg,cpl-corp-cial-prod \
  --host-project cpl-corp-cial-host-prod \
  --region us-central1 \
  -o html
```

### Escenario: Host Projects diferentes por ambiente

```bash
python gcp_cloudrun_vpc_ip_diagnostic.py \
  --projects dev-proj,qa-proj,stg-proj,prod-proj \
  --host-projects dev-host,qa-host,stg-host,prod-host \
  --region us-central1 \
  -o json
```

## 📋 Parámetros

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--projects` | ✅ | 1-4 proyectos GCP separados por coma (dev,qa,stg,prod), o alias de equipo: `CMANAGER`, `CSC`, `WMS`, `OMS` |
| `--host-project` | ✅* | Proyecto host Shared VPC (uno para todos) |
| `--host-projects` | ✅* | 4 host projects separados por coma (uno por ambiente) |
| `--region` | ❌ | Región a analizar (default: us-central1) |
| `--output, -o` | ❌ | Formato: `json`, `csv`, `html` |
| `--debug` | ❌ | Modo debug verbose |
| `--parallel` | ❌ | Ejecución paralela (default: true) |
| `--max-workers` | ❌ | Workers paralelos (default: 4) |
| `--timezone, -tz` | ❌ | Timezone (default: America/Mazatlan) |
| `--help, -h` | ❌ | Muestra ayuda completa |

* Debe proporcionar **uno** de: `--host-project` O `--host-projects`

## 📊 Qué Analiza

### 1. Servicios Cloud Run por ambiente
- Lista todos los servicios en el proyecto
- Detecta cuáles usan VPC Connector vs Direct VPC Egress vs sin VPC
- Extrae min/max instances, CPU, memoria, ingress

### 2. VPC Connectors en Host Project
- Obtiene todos los connectors en la región
- Lee CIDR range, min/max instances del connector
- Identifica servicios conectados a cada connector

### 3. Cálculo de Saturación
```
IPs usables = Total CIDR - 4 (reservadas GCP)
Estimado usado = Σ(min_instances) + 30% × Σ(max_instances - min_instances) × growth_factor
Utilización = Estimado / IPs usables × 100
```

Las tablas de resumen y de conectores muestran **`IPs actuales / total`** (por ejemplo, `12/252`) y el **CIDR** asociado.
Cuando el servicio usa Direct VPC Egress, el resumen obtiene la subred desde `run.googleapis.com/network-interfaces` y consulta su CIDR en el Host Project. La cantidad actual corresponde a la estimación de instancias activas/proyectadas calculada por la herramienta; el total corresponde a las IPs utilizables del CIDR después de descontar las 4 IPs reservadas por GCP.

El diagnóstico utiliza un spinner animado compatible con WSL y terminales Linux mediante actualización explícita de la misma línea (`\r`), evitando que cada refresco se imprima como una línea independiente.

### 4. Niveles de Riesgo
| Estado | Umbral | Acción |
|--------|--------|--------|
| 🟢 **OK** | < 70% | Monitorear |
| 🟡 **WARNING** | 70-89% | Planificar ampliación |
| 🔴 **CRITICAL** | ≥ 90% | Migración urgente |

## 🎯 Configuración por Ambiente (Built-in)

| Ambiente | Growth Factor | CIDR Recomendado | IPs Usables | Min/Max Inst Default |
|----------|---------------|------------------|-------------|---------------------|
| **Dev** | 1.5x | `/24` | 252 | 1 / 10 |
| **QA** | 2.0x | `/24` | 252 | 2 / 20 |
| **Stg** | 2.5x | `/23` | 508 | 3 / 30 |
| **Prod** | 3.0x | `/22` | 1020 | 5 / 100 |

## 📤 Formatos de Salida

### JSON (`-o json`)
```json
{
  "metadata": { "tool": "CloudRunVPCDiagnostic", "version": "1.0.0", ... },
  "summary": { "total_services": 45, "critical_environments": 1, ... },
  "diagnostics": [
    {
      "environment": "prod",
      "project_id": "cpl-corp-cial-prod",
      "host_project_id": "cpl-corp-host-prod",
      "services": [...],
      "connectors": [...],
      "recommendations": [...],
      "risk_level": "CRITICAL"
    }
  ]
}
```

### HTML (`-o html`) - **Recomendado y formato por defecto desde el launcher**
Reporte interactivo con:
- Dashboard resumen multi-ambiente
- Tablas detalladas por ambiente (Connectors, Servicios, Recomendaciones)
- Badges de color por severidad (CRITICAL/HIGH/MEDIUM/LOW)
- Acciones copy-pasteables

### CSV (`-o csv`)
Exporta tabla plana con todos los datos para análisis en Excel/Sheets.

## 💡 Recomendaciones Típicas Generadas

| Tipo | Prioridad | Ejemplo |
|------|-----------|---------|
| `vpc_connector_cidr` | HIGH | "Migrar connector `/28` (16 IPs) → `/24` (252 IPs)" |
| `connector_saturation` | CRITICAL | "Connector prod-us-central1 al 95% - 15 servicios afectados" |
| `services_without_vpc` | MEDIUM | "8 servicios sin VPC - no acceden a Cloud SQL/Memorystore" |
| `subnet_capacity` | MEDIUM | "Verificar subnet host project tenga rango ≥ /20" |

## 🔧 Plan de Migración Típico

```bash
# 1. Crear NUEVO connector con rango mayor (en host project)
gcloud compute networks vpc-access connectors create cloudrun-connector-prod-new \
  --network=shared-vpc-network \
  --region=us-central1 \
  --range=10.8.0.0/22 \
  --min-instances=5 \
  --max-instances=100 \
  --project=cpl-corp-host-prod

# 2. Migrar servicios progresivamente (en cada service project)
gcloud run services update mi-servicio \
  --vpc-connector=projects/cpl-corp-host-prod/locations/us-central1/connectors/cloudrun-connector-prod-new \
  --region=us-central1 \
  --project=cpl-corp-cial-prod

# 3. Validar conectividad
# 4. Eliminar connector viejo tras confirmar migración completa
```

## ⚠️ Prerrequisitos

- **Permisos en Service Projects**: `roles/run.viewer` + `roles/iam.securityReviewer`
- **Permisos en Host Project**: `roles/compute.networkViewer` (para listar connectors/subnets)
- **gcloud CLI** autenticado: `gcloud auth login`
- **Python 3.8+** con `rich` instalado

## 📁 Archivos Relacionados

```
scm/gcp/cloud-run/
├── gcp_cloudrun_vpc_ip_diagnostic.py    # ← Esta herramienta
├── gcp_cloudrun_checker.py              # Checker general Cloud Run
├── gcp_cloudrun_security_auditor.py     # Auditoría seguridad
├── cloudrun_base.py                     # Clase base compartida
├── cloudrun_alerts.py                   # Sistema de alertas
└── cloudrun_metrics.py                  # Cálculo de métricas
```

## 🔗 Integración con Launcher

Disponible como **Opción 35** en el grupo **Cloud Run** (🚀):

```bash
cd scm/gcp
python tools.py
# Seleccionar: 35 → Cloud Run VPC IP Diagnostic
```

## 📈 Ejemplo de Salida (Terminal)

```
╭──────────────────────────────────────────────────────────────────────────────╮
│                     📊 Cloud Run VPC IP Diagnostic - Resumen                 │
├───────────┬────────────────────┬────────────────┬────────┬────────┬─────────┬────────┬─────────────┤
│ Ambiente  │ Proyecto           │ Host Project   │ Servicios│ Con VPC│Connectors│ Riesgo  │Recomendaciones│
├───────────┼────────────────────┼────────────────┼────────┼────────┼─────────┼────────┼─────────────┤
│ DEV       │ cpl-corp-cial-dev  │ cpl-corp-host  │ 12     │ 10     │ 1       │ 🟢 OK   │ 1           │
│ QA        │ cpl-corp-cial-qa   │ cpl-corp-host  │ 18     │ 15     │ 1       │ 🟡 WARNING│ 2           │
│ STG       │ cpl-corp-cial-stg  │ cpl-corp-host  │ 22     │ 20     │ 1       │ 🟡 WARNING│ 3           │
│ PROD      │ cpl-corp-cial-prod │ cpl-corp-host  │ 35     │ 32     │ 2       │ 🔴 CRITICAL│ 4           │
╰───────────┴────────────────────┴────────────────┴────────┴────────┴─────────┴────────┴─────────────╯

╭───────────────────────────── VPC Connectors - PROD ╮
│ Connector           │ Red       │ CIDR     │ Tot │ Usad │ Disp │ Uso% │ Estado  │ Servicios              │
├─────────────────────┼───────────┼──────────┼─────┼──────┼──────┼──────┼─────────┼──────────────────────┤
│ cloudrun-prod-old   │ shared-vpc│ 10.8.0/28│ 12  │ 11   │ 1    │ 92%  │ 🔴 CRITICAL│ api-gw, worker, ...  │
│ cloudrun-prod-new   │ shared-vpc│ 10.8.1/24│ 252 │ 45   │ 207  │ 18%  │ 🟢 OK    │ (vacío - nuevo)       │
╰─────────────────────┴───────────┴──────────┴─────┴──────┴──────┴──────┴─────────┴──────────────────────╯

╭────────────────────── Recomendaciones - PROD ╮
│ Prioridad │ Tipo                      │ Título                              │ Actual      │ Recomendado     │ Acción                                    │
├───────────┼───────────────────────────┼─────────────────────────────────────┼─────────────┼─────────────────┼─────────────────────────────────────────┤
│ 🔴 CRITICAL│ connector_saturation      │ Connector saturado: cloudrun-prod-old│ 10.8.0/28   │ Migrar a /22    │ Crear connector nuevo y migrar servicios │
│ 🟠 HIGH    │ vpc_connector_cidr        │ Rango CIDR recomendado (PROD)       │ 10.8.0/28   │ 10.8.0/22       │ --range=10.8.0.0/22 en host project       │
│ 🟡 MEDIUM  │ services_without_vpc      │ 3 servicios sin VPC Connector       │ Sin VPC     │ Asignar nuevo   │ gcloud run services update --vpc-connector│
╰───────────┴───────────────────────────┴─────────────────────────────────────┴─────────────┴─────────────────┴─────────────────────────────────────────╯
```

## 🏷️ Versionado

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0.0 | 2026-09-15 | Versión inicial con diagnóstico multi-ambiente, cálculo CIDR, reporte HTML |

## ✍️ Autor

**Harold Adrian** - DevSecOps Toolbox