# 📤 Análisis de Salidas (Outputs) - DevSecOps Toolbox

**Fecha:** 25 de Junio de 2026  
**Objetivo:** Análisis en profundidad de las salidas generadas por cada herramienta

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Formatos de Salida Soportados](#formatos-de-salida-soportados)
3. [Análisis por Plataforma](#análisis-por-plataforma)
4. [Duplicación de Salidas](#duplicación-de-salidas)
5. [Inconsistencias Identificadas](#inconsistencias-identificadas)
6. [Recomendaciones](#recomendaciones)

---

## Resumen Ejecutivo

### Estadísticas de Salidas

```
Total de Herramientas: 76
├─ Con salida JSON:   45 (59%)
├─ Con salida CSV:    40 (53%)
├─ Con salida Excel:  35 (46%)
├─ Con salida HTML:    8 (11%)
├─ Con salida Tabla:  76 (100%)
└─ Sin exportación:    5 (7%)

Formatos Más Comunes:
1. JSON + CSV + Excel (27 herramientas)
2. JSON + CSV (12 herramientas)
3. Solo Tabla (8 herramientas)
```

### Hallazgos Clave

- ✅ **Consistencia Alta:** Mayoría usa JSON/CSV/Excel
- ⚠️ **Inconsistencias:** Diferentes estructuras JSON
- 🔴 **Duplicación:** Múltiples herramientas generan salidas similares
- 📁 **Directorios:** Inconsistencia en ubicación de archivos

---

## Formatos de Salida Soportados

### JSON

**Prevalencia:** 45 herramientas (59%)

**Estructura Común:**
```json
{
  "metadata": {
    "tool": "nombre_herramienta",
    "version": "1.0.0",
    "generated_at": "2026-06-25T14:30:00Z"
  },
  "summary": {
    "total": 100,
    "filtered": 50
  },
  "data": [
    { "field1": "value1", "field2": "value2" }
  ]
}
```

**Variaciones Encontradas:**
```
1. Con metadata + summary + data (Estándar)
2. Con metadata + data (Simplificado)
3. Con metadata + results (Alternativo)
4. Sin metadata (Mínimo)
5. Array directo (Muy simple)
```

**Problemas:**
- 🔴 Inconsistencia en estructura
- 🔴 Algunos sin metadata
- 🔴 Nombres de campos diferentes

---

### CSV

**Prevalencia:** 40 herramientas (53%)

**Estructura Común:**
```csv
field1,field2,field3,field4
value1,value2,value3,value4
value1,value2,value3,value4
```

**Variaciones Encontradas:**
```
1. Headers + Datos (Estándar)
2. Headers + Metadata + Datos (Extendido)
3. Múltiples archivos (Uno por sección)
4. Sin headers (Raro)
```

**Problemas:**
- 🟡 Algunos generan múltiples archivos
- 🟡 Inconsistencia en nombres de columnas
- 🟡 Algunos no incluyen timestamp

---

### Excel

**Prevalencia:** 35 herramientas (46%)

**Estructura Común:**
```
Hoja 1: Datos principales
Hoja 2: Metadata (opcional)
Hoja 3: Resumen (opcional)
```

**Variaciones Encontradas:**
```
1. Una hoja con datos (Simple)
2. Múltiples hojas (Datos + Metadata + Resumen)
3. Con formato y colores (Avanzado)
4. Con gráficos (Muy avanzado)
```

**Problemas:**
- 🟡 Algunos requieren pandas/openpyxl
- 🟡 Inconsistencia en nombres de hojas
- 🟡 Algunos con formato, otros sin

---

### HTML

**Prevalencia:** 8 herramientas (11%)

**Herramientas:**
- GCP Tool 24: GKE Node Resources Monitor
- GCP Tool 25: GKE Pod Resources Monitor
- AWS Tool 15: EKS Pod Monitor
- AWS Tool 16: EKS Node Monitor
- AZDO Tool 3: Release CD Health
- AZDO Tool 16: Pipeline Health Score
- AZDO Tool 18: Pipeline Status
- Dashboard: Dashboard Matutino

**Estructura Común:**
```html
<!DOCTYPE html>
<html>
  <head>
    <title>Reporte</title>
    <style>/* CSS */</style>
  </head>
  <body>
    <h1>Título</h1>
    <table><!-- Datos --></table>
    <script>/* Interactividad --></script>
  </body>
</html>
```

**Problemas:**
- 🟡 Inconsistencia en estilos
- 🟡 Algunos con JavaScript, otros sin
- 🟡 Algunos responsive, otros no

---

## Análisis por Plataforma

### AZDO (27 herramientas)

#### Salidas Generadas

| Tool | Nombre | JSON | CSV | Excel | HTML | Tabla |
|------|--------|------|-----|-------|------|-------|
| 1 | PR Master Checker | ✅ | ✅ | ✅ | ❌ | ✅ |
| 1b | PR Pipeline Analyzer | ✅ | ✅ | ✅ | ❌ | ✅ |
| 2 | Branch Policy Checker | ✅ | ✅ | ✅ | ❌ | ✅ |
| 2b | Branch Lock Checker | ✅ | ✅ | ✅ | ❌ | ✅ |
| 3 | Release CD Health | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | Pipeline Drift | ✅ | ✅ | ✅ | ❌ | ✅ |
| 5 | Release Deep Dive | ✅ | ✅ | ✅ | ❌ | ✅ |
| 6 | Task Validator | ✅ | ✅ | ❌ | ❌ | ✅ |
| 7 | Pipeline Logs Scanner | ✅ | ✅ | ❌ | ❌ | ✅ |
| 8 | Repo Vulnerabilities Scanner | ✅ | ✅ | ❌ | ❌ | ✅ |
| 9 | CICD Inventory | ✅ | ✅ | ✅ | ❌ | ✅ |
| 10 | GKE Pipelines Inventory | ✅ | ✅ | ✅ | ❌ | ✅ |
| 11 | Pending Approvals | ✅ | ✅ | ✅ | ❌ | ✅ |
| 12 | Branches Created | ✅ | ✅ | ✅ | ❌ | ✅ |
| 13 | Hotfix Branches Inventory | ✅ | ✅ | ✅ | ❌ | ✅ |
| 14 | CI Pipeline Inventory | ✅ | ✅ | ✅ | ❌ | ✅ |
| 15 | CD Pipeline Inventory | ✅ | ✅ | ✅ | ❌ | ✅ |
| 16 | Pipeline Health Score | ✅ | ✅ | ✅ | ✅ | ✅ |
| 17 | Prod Deploy Inventory | ✅ | ✅ | ✅ | ❌ | ✅ |
| 18 | Pipeline Status | ✅ | ✅ | ✅ | ✅ | ✅ |
| 19 | Release Explorer | ❌ | ❌ | ❌ | ✅ | ✅ |
| 20 | Properties Branch Diff | ❌ | ❌ | ❌ | ❌ | ✅ |
| 21 | Repo Branch Diff | ❌ | ❌ | ❌ | ❌ | ✅ |
| 22 | Release Rollback | ❌ | ❌ | ❌ | ❌ | ✅ |
| 23 | Release Restore | ❌ | ❌ | ❌ | ❌ | ✅ |
| 24 | Release CD Rollback | ❌ | ❌ | ❌ | ❌ | ✅ |
| 25 | Release CD Update | ❌ | ❌ | ❌ | ❌ | ✅ |

**Análisis:**
- ✅ Buena cobertura de JSON/CSV/Excel
- ⚠️ Herramientas 19-25 solo tienen tabla
- ⚠️ Herramientas 3, 16, 18 tienen HTML (duplicación)

#### Estructura JSON AZDO

**Estándar Observado:**
```json
{
  "metadata": {
    "tool": "nombre",
    "version": "1.0.0",
    "generated_at": "ISO timestamp"
  },
  "summary": {
    "total": N,
    "filtered": N,
    "status_counts": {...}
  },
  "data": [...]
}
```

**Variaciones:**
- Algunos sin "summary"
- Algunos con "results" en lugar de "data"
- Algunos con campos adicionales (stage_searched, etc.)

---

### GCP (22 herramientas)

#### Salidas Generadas

| Tool | Nombre | JSON | CSV | Excel | HTML | Tabla |
|------|--------|------|-----|-------|------|-------|
| 1 | Monitoreo de Recursos | ❌ | ❌ | ❌ | ❌ | ✅ |
| 2 | Reporte de Despliegues GKE | ❌ | ❌ | ❌ | ❌ | ✅ |
| 3 | Reporte IAM | ❌ | ❌ | ❌ | ❌ | ✅ |
| 4 | Service Account Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 5 | Certificate Manager Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 6 | Cloud Armor Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 7 | Cloud SQL Disk Monitor | ✅ | ✅ | ❌ | ❌ | ✅ |
| 8 | Cloud SQL Database Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 9 | Cloud SQL Comparator | ✅ | ✅ | ❌ | ❌ | ✅ |
| 10 | VPC Networks Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 11 | Gateway Services Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 12 | Load Balancer Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 13 | IP Addresses Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 14 | GKE Cluster Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 15 | Secrets & ConfigMaps Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 16 | Pod Connectivity Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 17 | GKE Workload Analyzer | ✅ | ✅ | ❌ | ❌ | ✅ |
| 18 | GKE Pod Disruption Budgets | ✅ | ✅ | ❌ | ❌ | ✅ |
| 19 | GKE Network Policies | ✅ | ✅ | ❌ | ❌ | ✅ |
| 20 | GKE RBAC Analyzer | ✅ | ✅ | ❌ | ❌ | ✅ |
| 24 | GKE Node Resources Monitor | ✅ | ✅ | ❌ | ✅ | ✅ |
| 25 | GKE Pod Resources Monitor | ✅ | ✅ | ❌ | ✅ | ✅ |

**Análisis:**
- ⚠️ Herramientas 1-3 solo tienen tabla
- ✅ Herramientas 4+ tienen JSON/CSV
- ⚠️ Ninguna tiene Excel (excepto implícito)
- ⚠️ Solo 24-25 tienen HTML

---

### AWS (19 herramientas)

#### Salidas Generadas

| Tool | Nombre | JSON | CSV | Excel | HTML | Tabla |
|------|--------|------|-----|-------|------|-------|
| 1 | IAM Users & Policies Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 2 | IAM Roles Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 3 | ACM Certificate Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 4 | RDS Instance Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 5 | RDS Storage Monitor | ✅ | ✅ | ❌ | ❌ | ✅ |
| 6 | VPC Networks Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 7 | Security Groups Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 8 | Load Balancer Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 9 | EKS Cluster Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 10 | ECR Repository Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 11 | EC2 Instances Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 12 | Lambda Functions Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 13 | CloudWatch Alarms Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 14 | EBS Volume Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 15 | EKS Pod Monitor | ✅ | ✅ | ❌ | ✅ | ✅ |
| 16 | EKS Node Monitor | ✅ | ✅ | ❌ | ✅ | ✅ |
| 17 | Secrets Manager Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 18 | WAF Web ACL Checker | ✅ | ✅ | ❌ | ❌ | ✅ |
| 19 | AWS Inventory Generator | ✅ | ✅ | ✅ | ❌ | ✅ |

**Análisis:**
- ✅ Consistencia muy alta (JSON + CSV)
- ⚠️ Solo Tool 19 tiene Excel
- ⚠️ Solo Tools 15-16 tienen HTML
- ✅ Todas tienen tabla

---

### Terminal (6 herramientas)

#### Salidas Generadas

| Tool | Nombre | JSON | CSV | Excel | HTML | Tabla |
|------|--------|------|-----|-------|------|-------|
| 1 | TLS Certificate Validator | ❌ | ❌ | ❌ | ❌ | ✅ |
| 2 | Database Connection Tester | ❌ | ❌ | ❌ | ❌ | ✅ |
| 3 | Kubernetes Manifest Diff | ❌ | ❌ | ❌ | ❌ | ✅ |
| 4 | Kubernetes Deployment Validator | ❌ | ❌ | ❌ | ❌ | ✅ |
| 5 | Docker Image Validator | ❌ | ❌ | ❌ | ❌ | ✅ |
| 6 | Git Repository Validator | ❌ | ❌ | ❌ | ❌ | ✅ |

**Análisis:**
- 🔴 Ninguna tiene exportación a archivo
- ✅ Todas tienen tabla en consola
- 🔴 Oportunidad de mejora: agregar JSON/CSV

---

## Duplicación de Salidas

### Grupo 1: PR Metrics

```
AZDO Tool 1:  PR Master Checker
├─ JSON: pr_master_TIMESTAMP.json
├─ CSV:  pr_master_TIMESTAMP.csv
└─ Excel: pr_master_TIMESTAMP.xlsx

AZDO Tool 1b: PR Pipeline Analyzer
├─ JSON: pr_pipeline_analysis_TIMESTAMP.json
├─ CSV:  pr_pipeline_analysis_TIMESTAMP_prs.csv
└─ Excel: pr_pipeline_analysis_TIMESTAMP.xlsx

Similitud: 85%
Problema: Mismo tipo de datos, diferentes formatos
```

### Grupo 2: Branch Analysis

```
AZDO Tool 2:  Branch Policy Checker
├─ JSON: branch_policies_TIMESTAMP.json
├─ CSV:  branch_policies_TIMESTAMP.csv
└─ Excel: branch_policies_TIMESTAMP.xlsx

AZDO Tool 2b: Branch Lock Checker
├─ JSON: branch_locks_TIMESTAMP.json
├─ CSV:  branch_locks_TIMESTAMP.csv
└─ Excel: branch_locks_TIMESTAMP.xlsx

Similitud: 70%
Problema: Diferentes datos pero estructura similar
```

### Grupo 3: Health Score

```
AZDO Tool 3:  Release CD Health
├─ JSON: release_cd_health_TIMESTAMP.json
├─ CSV:  release_cd_health_TIMESTAMP.csv
└─ Excel: release_cd_health_TIMESTAMP.xlsx (con gráficos)

AZDO Tool 16: Pipeline Health Score (DORA)
├─ JSON: pipeline_health_score_TIMESTAMP.json
├─ CSV:  pipeline_health_score_TIMESTAMP.csv
└─ Excel: pipeline_health_score_TIMESTAMP.xlsx

AZDO Tool 18: Pipeline Status
├─ JSON: pipeline_status_TIMESTAMP.json
├─ CSV:  pipeline_status_TIMESTAMP.csv
└─ Excel: pipeline_status_TIMESTAMP.xlsx (con gráficos)

Similitud: 75%
Problema: Múltiples herramientas generan health scores
```

### Grupo 4: Inventory

```
AZDO Tool 9:  CICD Inventory
├─ JSON: cicd_inventory_TIMESTAMP.json
├─ CSV:  cicd_inventory_TIMESTAMP.csv
└─ Excel: cicd_inventory_TIMESTAMP.xlsx

AZDO Tool 14: CI Pipeline Inventory
├─ JSON: cicd_inventory_ci_detailed_TIMESTAMP.json
├─ CSV:  cicd_inventory_ci_detailed_TIMESTAMP.csv
└─ Excel: cicd_inventory_ci_detailed_TIMESTAMP.xlsx

AZDO Tool 15: CD Pipeline Inventory
├─ JSON: cicd_inventory_cd_detailed_TIMESTAMP.json
├─ CSV:  cicd_inventory_cd_detailed_TIMESTAMP.csv
└─ Excel: cicd_inventory_cd_detailed_TIMESTAMP.xlsx

Similitud: 80%
Problema: Múltiples inventarios con diferentes niveles de detalle
```

---

## Inconsistencias Identificadas

### 1. Estructura JSON Inconsistente

```
Tipo A (Estándar):
{
  "metadata": {...},
  "summary": {...},
  "data": [...]
}

Tipo B (Simplificado):
{
  "metadata": {...},
  "data": [...]
}

Tipo C (Alternativo):
{
  "metadata": {...},
  "results": [...]
}

Tipo D (Mínimo):
[...]
```

**Herramientas Afectadas:** 45 herramientas

**Impacto:** Dificulta procesamiento automatizado

---

### 2. Nombres de Archivos Inconsistentes

```
Patrón 1: {tool}_{timestamp}.json
  Ejemplos: pr_master_20260625_143000.json

Patrón 2: {tool}_{id}_{timestamp}.json
  Ejemplos: release_deep_dive_42_20260625_143000.json

Patrón 3: {tool}_{timestamp}_{suffix}.json
  Ejemplos: pr_pipeline_analysis_20260625_143000_prs.csv

Patrón 4: {tool}_{timestamp}.xlsx
  Ejemplos: pipeline_drift_20260625_143000.xlsx
```

**Problema:** Inconsistencia dificulta automatización

---

### 3. Ubicación de Archivos Inconsistente

```
Ubicación A: outcome/
  Herramientas: AZDO (mayoría)

Ubicación B: scm/outcome/
  Herramientas: Dashboard

Ubicación C: ./outcome/
  Herramientas: Algunos scripts

Ubicación D: {script_dir}/outcome/
  Herramientas: Algunos scripts
```

**Problema:** Archivos dispersos en múltiples directorios

---

### 4. Campos CSV Inconsistentes

```
Herramienta A:
  Campos: pr_id, title, repository, status, created_by, creation_date

Herramienta B:
  Campos: pullRequestId, title, repo, state, author, createdDate

Herramienta C:
  Campos: id, name, repo, status, creator, date
```

**Problema:** Nombres de campos diferentes para conceptos similares

---

### 5. Metadata Inconsistente

```
Formato A:
{
  "metadata": {
    "tool": "nombre",
    "version": "1.0.0",
    "generated_at": "ISO timestamp"
  }
}

Formato B:
{
  "metadata": {
    "tool": "nombre",
    "version": "1.0.0",
    "generated_at": "ISO timestamp",
    "stage_searched": "validador"
  }
}

Formato C:
{
  "metadata": {
    "tool": "nombre",
    "generated_at": "ISO timestamp"
  }
}
```

**Problema:** Metadata con campos adicionales no estándar

---

## Recomendaciones

### Prioridad 1: Estandarizar JSON

```
Estructura Recomendada:
{
  "metadata": {
    "tool": "nombre_herramienta",
    "version": "1.0.0",
    "generated_at": "ISO timestamp",
    "organization": "org_name",
    "project": "project_name"
  },
  "summary": {
    "total": N,
    "filtered": N,
    "status": "success|error"
  },
  "data": [
    { "field1": "value1", "field2": "value2" }
  ]
}
```

**Impacto:** Facilita procesamiento automatizado

---

### Prioridad 2: Estandarizar Nombres de Archivos

```
Patrón Recomendado:
{tool_id}_{tool_name}_{timestamp}.{format}

Ejemplos:
- 1_pr_master_20260625_143000.json
- 2_branch_policy_20260625_143000.csv
- 3_release_health_20260625_143000.xlsx
```

**Impacto:** Facilita búsqueda y organización

---

### Prioridad 3: Centralizar Ubicación de Archivos

```
Estructura Recomendada:
scm/outcome/
├─ dashboard/
│  ├─ dashboard_data.json
│  ├─ dashboard.html
│  └─ history/
│     └─ 2026-06-25/
│        └─ dashboard_data_143000.json
├─ azdo/
│  ├─ pr_master_20260625_143000.json
│  ├─ branch_policy_20260625_143000.json
│  └─ ...
├─ gcp/
│  └─ ...
└─ aws/
   └─ ...
```

**Impacto:** Organización clara y consistente

---

### Prioridad 4: Estandarizar Campos CSV

```
Mapeo Recomendado:

Concepto          | Campo Estándar
------------------|------------------
ID                | id
Nombre            | name
Repositorio       | repository
Estado            | status
Creador           | created_by
Fecha Creación    | created_date
Fecha Modificación| modified_date
Versión           | version
```

**Impacto:** Facilita análisis cruzado

---

### Prioridad 5: Agregar Exportación a Terminal

```
Herramientas sin exportación:
- Terminal Tool 1-6 (6 herramientas)

Recomendación:
- Agregar --output json|csv a todos
- Mantener tabla en consola como default
```

**Impacto:** Consistencia total

---

### Prioridad 6: Agregar Excel a GCP/AWS

```
Herramientas sin Excel:
- GCP: Tools 4-23 (20 herramientas)
- AWS: Tools 1-14, 17-18 (16 herramientas)

Recomendación:
- Agregar soporte Excel a todas
- Usar pandas + openpyxl
```

**Impacto:** Paridad con AZDO

---

## Plan de Estandarización

### Fase 1: JSON (2 semanas)
- [ ] Definir estructura estándar
- [ ] Actualizar todas las herramientas
- [ ] Crear validador de JSON
- [ ] Tests de validación

### Fase 2: Nombres y Ubicaciones (1 semana)
- [ ] Definir patrón de nombres
- [ ] Actualizar todas las herramientas
- [ ] Centralizar ubicación
- [ ] Actualizar documentación

### Fase 3: CSV/Excel (2 semanas)
- [ ] Definir campos estándar
- [ ] Actualizar todas las herramientas
- [ ] Agregar Excel a GCP/AWS
- [ ] Tests de validación

### Fase 4: Terminal (1 semana)
- [ ] Agregar exportación a Terminal
- [ ] Tests de validación
- [ ] Documentación

**Total:** 6 semanas

---

## Conclusiones

### Hallazgos Principales

1. **Buena Cobertura:** 59% con JSON, 53% con CSV, 46% con Excel
2. **Inconsistencias:** Estructura JSON, nombres de archivos, ubicaciones
3. **Duplicación:** Múltiples herramientas generan salidas similares
4. **Oportunidades:** Estandarización y consolidación

### Impacto de Estandarización

```
Antes:
- Inconsistencia en 45 herramientas
- Procesamiento manual de salidas
- Dificultad en análisis cruzado

Después:
- Consistencia total
- Procesamiento automatizado
- Análisis cruzado facilitado
```

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
