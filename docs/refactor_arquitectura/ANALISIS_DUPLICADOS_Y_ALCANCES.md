# 📊 Análisis de Duplicados y Alcances Similares - DevSecOps Toolbox

**Fecha:** 25 de Junio de 2026  
**Objetivo:** Identificar herramientas duplicadas o con alcances similares para depuración

---

## 📋 Índice de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Plataformas Disponibles](#plataformas-disponibles)
3. [Análisis por Categoría](#análisis-por-categoría)
4. [Duplicados Identificados](#duplicados-identificados)
5. [Alcances Similares](#alcances-similares)
6. [Recomendaciones de Depuración](#recomendaciones-de-depuración)
7. [Matriz de Cobertura](#matriz-de-cobertura)

---

## Resumen Ejecutivo

### Plataformas
- **6 plataformas principales** (GCP, AZDO, AWS, Terminal, KPI, Dashboard)
- **~90 herramientas totales**
- **Múltiples duplicados y alcances similares identificados**

### Hallazgos Clave
- ✅ **Duplicados Críticos:** 12 herramientas con funcionalidad duplicada
- ⚠️ **Alcances Similares:** 18 herramientas con solapamiento
- 🔧 **Oportunidades de Consolidación:** 8 grupos de herramientas

---

## Plataformas Disponibles

| # | Plataforma | Emoji | Herramientas | Estado |
|---|-----------|-------|-------------|--------|
| **1** | Google Cloud Platform (GCP) | ☁️ | 22 | ✅ Ready |
| **2** | Azure DevOps (AZDO) | 🔷 | 27 | ✅ Ready |
| **3** | Amazon Web Services (AWS) | 🟠 | 19 | ✅ Ready |
| **4** | Terminal Scripts | 🐧 | 6 | ✅ Ready |
| **5** | KPI Analyzer | 📊 | 1 | ✅ Ready |
| **6** | Dashboard Matutino | 📈 | 1 | ✅ Ready |
| | **TOTAL** | | **~76** | |

---

## Análisis por Categoría

### 1. MONITOREO DE RECURSOS

#### GCP (Tools 1, 2, 24, 25)
```
1  → Monitoreo de Recursos GCP (CPU, memoria, SQL, etc.)
2  → Reporte de Despliegues GKE
24 → GKE Node Resources Monitor (CPU/memoria por nodo)
25 → GKE Pod Resources Monitor (CPU/memoria por pod)
```

#### AWS (Tool 13, 15, 16)
```
13 → CloudWatch Alarms Checker
15 → EKS Pod Monitor (CPU/memoria por pod)
16 → EKS Node Monitor (estado y recursos de nodos)
```

#### AZDO (Tool 3, 16, 18)
```
3  → Release CD Health (Score de salud)
16 → Pipeline Health Score (DORA metrics)
18 → Pipeline Status (Reporte consolidado CI+CD)
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **GCP Tool 24 vs GCP Tool 25:** Ambas monitorean recursos GKE (nodos vs pods)
- **AWS Tool 15 vs AWS Tool 16:** Ambas monitorean recursos EKS (pods vs nodos)
- **GCP Tool 1 vs AWS Tool 13:** Ambas monitorean recursos (GCP vs AWS)
- **AZDO Tool 3 vs AZDO Tool 16 vs AZDO Tool 18:** Solapamiento en health score

**Recomendación:** Consolidar en herramienta única "Cluster Resources Monitor" por plataforma

---

### 2. INVENTARIO DE INFRAESTRUCTURA

#### GCP
```
Inventory (implícito en múltiples tools)
- GKE Cluster Checker (Tool 14)
- Secrets & ConfigMaps Checker (Tool 15)
- VPC Networks Checker (Tool 10)
- Load Balancer Checker (Tool 12)
```

#### AWS
```
19 → AWS Inventory Generator (EKS/RDS/EC2/ELB/Lambda/DynamoDB/S3)
```

#### AZDO
```
9  → CICD Inventory (repos, CI, CD con relación)
10 → GKE Pipelines Inventory
12 → Branches Created
13 → Hotfix Branches Inventory
14 → CI Pipeline Inventory (Detailed)
15 → CD Pipeline Inventory (Detailed)
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **AZDO Tool 9 vs AZDO Tool 14 vs AZDO Tool 15:** Inventarios CI/CD con diferentes niveles de detalle
- **GCP (múltiples) vs AWS Tool 19:** Ambas generan inventarios completos

**Recomendación:** Consolidar en "Infrastructure Inventory" con opciones de detalle

---

### 3. ANÁLISIS DE SEGURIDAD / VULNERABILIDADES

#### GCP
```
3  → Reporte de Roles y Permisos IAM
4  → Service Account Checker
5  → Certificate Manager Checker
6  → Cloud Armor Checker (WAF/DDoS)
```

#### AWS
```
1  → IAM Users & Policies Checker
2  → IAM Roles Checker
3  → ACM Certificate Checker
17 → Secrets Manager & SSM Checker
18 → WAF Web ACL Checker
```

#### AZDO
```
6  → Task Validator (DevSecOps: imágenes, rollback, credenciales)
7  → Pipeline Logs Scanner (vulnerabilidades)
8  → Repo Vulnerabilities Scanner (package.json)
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **GCP Tool 3 vs AWS Tool 1/2:** Ambas analizan IAM/Roles
- **GCP Tool 5 vs AWS Tool 3:** Ambas monitorean certificados SSL/TLS
- **GCP Tool 6 vs AWS Tool 18:** Ambas analizan WAF/Security policies
- **AZDO Tool 7 vs AZDO Tool 8:** Ambas escanean vulnerabilidades (logs vs repos)

**Recomendación:** Consolidar en "Security Auditor" por plataforma

---

### 4. ANÁLISIS DE PULL REQUESTS

#### AZDO
```
1  → PR Master Checker (PRs hacia master con pipeline CD)
1b → PR Pipeline Analyzer (PRs de múltiples ramas + CD pipelines)
5  → Release Deep Dive (análisis profundo de release)
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **AZDO Tool 1 vs AZDO Tool 1b:** Ambas analizan PRs (master vs múltiples ramas)
- **AZDO Tool 1b vs AZDO Tool 5:** Solapamiento en análisis de releases

**Recomendación:** Consolidar en "PR & Release Analyzer" con opciones de filtro

---

### 5. ANÁLISIS DE POLÍTICAS DE RAMA

#### AZDO
```
2  → Branch Policy Checker (audita políticas master/QA/develop)
2b → Branch Lock Checker (lista ramas con lock)
12 → Branches Created (ramas creadas desde fecha)
13 → Hotfix Branches Inventory (ramas hotfix)
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **AZDO Tool 2 vs AZDO Tool 2b:** Ambas analizan ramas (políticas vs locks)
- **AZDO Tool 12 vs AZDO Tool 13:** Ambas inventarían ramas (creadas vs hotfix)

**Recomendación:** Consolidar en "Branch Management Auditor"

---

### 6. ANÁLISIS DE PIPELINES / RELEASES

#### AZDO
```
3  → Release CD Health (score de salud)
4  → Pipeline Drift Analyzer (drift entre actual y último release)
5  → Release Deep Dive (análisis profundo)
9  → CICD Inventory (repos, CI, CD)
10 → GKE Pipelines Inventory (releases con GKE)
11 → Pending Approvals (releases con aprobaciones pendientes)
14 → CI Pipeline Inventory (Detailed)
15 → CD Pipeline Inventory (Detailed)
16 → Pipeline Health Score (DORA metrics)
18 → Pipeline Status (reporte consolidado)
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **AZDO Tool 3 vs AZDO Tool 16 vs AZDO Tool 18:** Todas analizan health/status de pipelines
- **AZDO Tool 9 vs AZDO Tool 14 vs AZDO Tool 15:** Inventarios con diferentes niveles
- **AZDO Tool 4 vs AZDO Tool 5:** Ambas analizan cambios en releases

**Recomendación:** Consolidar en "Pipeline & Release Analyzer" con opciones de vista

---

### 7. KUBERNETES / CLUSTER MANAGEMENT

#### GCP
```
14 → GKE Cluster Checker
15 → Secrets & ConfigMaps Checker
16 → Pod Connectivity Checker
24 → GKE Node Resources Monitor
25 → GKE Pod Resources Monitor
```

#### AWS
```
9  → EKS Cluster Checker
15 → EKS Pod Monitor
16 → EKS Node Monitor
```

#### AZDO
```
6  → Task Validator (valida imágenes Docker)
10 → GKE Pipelines Inventory
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **GCP Tool 24/25 vs AWS Tool 15/16:** Ambas monitorean recursos K8s (nodos/pods)
- **GCP Tool 14 vs AWS Tool 9:** Ambas analizan clusters K8s

**Recomendación:** Crear "Kubernetes Cluster Monitor" agnóstico (GCP/AWS)

---

### 8. NETWORKING / VPC

#### GCP
```
10 → VPC Networks Checker
11 → Gateway Services Checker
12 → Load Balancer Checker
13 → IP Addresses Checker
```

#### AWS
```
6  → VPC Networks Checker
7  → Security Groups Checker
8  → Load Balancer Checker (ALB/NLB)
18 → WAF Web ACL Checker
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **GCP Tool 10 vs AWS Tool 6:** Ambas analizan VPC Networks
- **GCP Tool 12 vs AWS Tool 8:** Ambas analizan Load Balancers
- **GCP Tool 11 vs AWS Tool 7:** Ambas analizan servicios de gateway/security

**Recomendación:** Crear "Network Auditor" agnóstico (GCP/AWS)

---

### 9. DATABASE / STORAGE

#### GCP
```
7  → Cloud SQL Disk Monitor
8  → Cloud SQL Database Checker
9  → Cloud SQL Comparator
```

#### AWS
```
4  → RDS Instance Checker
5  → RDS Storage Monitor
14 → EBS Volume Checker
```

**🔴 DUPLICADOS IDENTIFICADOS:**
- **GCP Tool 7 vs AWS Tool 5:** Ambas monitorean almacenamiento (SQL vs RDS)
- **GCP Tool 8 vs AWS Tool 4:** Ambas analizan instancias de base de datos

**Recomendación:** Consolidar en "Database Monitor" por plataforma

---

### 10. ARTIFACTS / CONTAINER REGISTRY

#### GCP
```
(Implícito en inventarios)
```

#### AWS
```
10 → ECR Repository Checker
```

**Estado:** Bajo solapamiento. AWS tiene herramienta específica, GCP no.

**Recomendación:** Agregar "Artifact Registry Checker" a GCP

---

### 11. COMPUTE / INSTANCES

#### GCP
```
(Implícito en inventarios)
```

#### AWS
```
11 → EC2 Instances Checker
12 → Lambda Functions Checker
```

**Estado:** Bajo solapamiento. AWS tiene herramientas específicas, GCP no.

**Recomendación:** Agregar "Compute Instances Checker" a GCP

---

## Duplicados Identificados

### Críticos (Funcionalidad Idéntica)

| Herramienta 1 | Herramienta 2 | Plataforma | Tipo | Acción |
|---------------|---------------|-----------|------|--------|
| GCP Tool 24 | GCP Tool 25 | GCP | Monitoreo K8s | ⚠️ Consolidar |
| AWS Tool 15 | AWS Tool 16 | AWS | Monitoreo K8s | ⚠️ Consolidar |
| AZDO Tool 1 | AZDO Tool 1b | AZDO | PR Analysis | ⚠️ Consolidar |
| AZDO Tool 2 | AZDO Tool 2b | AZDO | Branch Policy | ⚠️ Consolidar |
| AZDO Tool 12 | AZDO Tool 13 | AZDO | Branch Inventory | ⚠️ Consolidar |
| GCP Tool 10 | AWS Tool 6 | Multi | VPC Networks | ⚠️ Consolidar |
| GCP Tool 12 | AWS Tool 8 | Multi | Load Balancer | ⚠️ Consolidar |

### Altos (Solapamiento Significativo)

| Herramienta 1 | Herramienta 2 | Plataforma | Tipo | Acción |
|---------------|---------------|-----------|------|--------|
| AZDO Tool 3 | AZDO Tool 16 | AZDO | Health Score | ⚠️ Revisar |
| AZDO Tool 16 | AZDO Tool 18 | AZDO | Health Score | ⚠️ Revisar |
| AZDO Tool 9 | AZDO Tool 14 | AZDO | CI Inventory | ⚠️ Revisar |
| AZDO Tool 14 | AZDO Tool 15 | AZDO | CI/CD Inventory | ⚠️ Revisar |
| AZDO Tool 7 | AZDO Tool 8 | AZDO | Vulnerabilities | ⚠️ Revisar |
| GCP Tool 3 | AWS Tool 1 | Multi | IAM Analysis | ⚠️ Revisar |
| GCP Tool 5 | AWS Tool 3 | Multi | Certificate Check | ⚠️ Revisar |

---

## Alcances Similares

### Grupo 1: Monitoreo de Recursos Kubernetes

```
GCP:
  - Tool 24: GKE Node Resources Monitor
  - Tool 25: GKE Pod Resources Monitor

AWS:
  - Tool 15: EKS Pod Monitor
  - Tool 16: EKS Node Monitor

Alcance Similar: Monitorean CPU/memoria en K8s
Diferencia: GCP vs AWS
Consolidación: Crear "K8s Resources Monitor" agnóstico
```

### Grupo 2: Inventario de Infraestructura

```
AZDO:
  - Tool 9:  CICD Inventory (repos, CI, CD)
  - Tool 14: CI Pipeline Inventory (Detailed)
  - Tool 15: CD Pipeline Inventory (Detailed)

AWS:
  - Tool 19: AWS Inventory Generator

GCP:
  - (Múltiples tools generan inventarios)

Alcance Similar: Generan inventarios completos
Diferencia: Nivel de detalle y plataforma
Consolidación: Crear "Infrastructure Inventory" con opciones
```

### Grupo 3: Análisis de Seguridad IAM

```
GCP:
  - Tool 3: Reporte de Roles y Permisos IAM
  - Tool 4: Service Account Checker

AWS:
  - Tool 1: IAM Users & Policies Checker
  - Tool 2: IAM Roles Checker

Alcance Similar: Analizan IAM/Roles/Permisos
Diferencia: GCP vs AWS
Consolidación: Crear "IAM Auditor" agnóstico
```

### Grupo 4: Análisis de Certificados SSL/TLS

```
GCP:
  - Tool 5: Certificate Manager Checker

AWS:
  - Tool 3: ACM Certificate Checker

Alcance Similar: Monitorean certificados
Diferencia: GCP vs AWS
Consolidación: Crear "Certificate Monitor" agnóstico
```

### Grupo 5: Análisis de WAF/Security Policies

```
GCP:
  - Tool 6: Cloud Armor Checker

AWS:
  - Tool 18: WAF Web ACL Checker

Alcance Similar: Analizan WAF/Security policies
Diferencia: GCP vs AWS
Consolidación: Crear "WAF Auditor" agnóstico
```

### Grupo 6: Análisis de Pull Requests

```
AZDO:
  - Tool 1:  PR Master Checker
  - Tool 1b: PR Pipeline Analyzer
  - Tool 5:  Release Deep Dive

Alcance Similar: Analizan PRs y releases
Diferencia: Scope (master vs múltiples, simple vs profundo)
Consolidación: Crear "PR & Release Analyzer" con opciones
```

### Grupo 7: Análisis de Políticas de Rama

```
AZDO:
  - Tool 2:  Branch Policy Checker
  - Tool 2b: Branch Lock Checker
  - Tool 12: Branches Created
  - Tool 13: Hotfix Branches Inventory

Alcance Similar: Analizan ramas
Diferencia: Tipo (políticas, locks, creadas, hotfix)
Consolidación: Crear "Branch Management Auditor"
```

### Grupo 8: Análisis de Health Score / Pipeline Status

```
AZDO:
  - Tool 3:  Release CD Health
  - Tool 16: Pipeline Health Score (DORA)
  - Tool 18: Pipeline Status

Alcance Similar: Analizan salud de pipelines
Diferencia: Métrica (recencia+estabilidad vs DORA vs consolidado)
Consolidación: Crear "Pipeline Health Analyzer" con opciones
```

---

## Recomendaciones de Depuración

### Prioridad 1: Críticos (Consolidar Inmediatamente)

```
1. AZDO Tool 1 + 1b → "PR & Release Analyzer"
   - Opción: master-only vs multi-branch
   - Opción: quick vs deep-dive
   
2. AZDO Tool 2 + 2b → "Branch Management Auditor"
   - Opción: policies vs locks vs created vs hotfix
   
3. GCP Tool 24 + 25 → "GKE Resources Monitor"
   - Opción: nodes vs pods vs both
   
4. AWS Tool 15 + 16 → "EKS Resources Monitor"
   - Opción: pods vs nodes vs both
```

### Prioridad 2: Altos (Revisar y Consolidar)

```
5. AZDO Tool 3 + 16 + 18 → "Pipeline Health Analyzer"
   - Opción: health-score vs dora vs consolidated
   
6. AZDO Tool 9 + 14 + 15 → "CICD Inventory"
   - Opción: basic vs ci-detailed vs cd-detailed
   
7. GCP Tool 10 + AWS Tool 6 → "VPC Networks Auditor"
   - Agnóstico: GCP vs AWS
   
8. GCP Tool 12 + AWS Tool 8 → "Load Balancer Auditor"
   - Agnóstico: GCP vs AWS
```

### Prioridad 3: Medios (Revisar Funcionalidad)

```
9. GCP Tool 3 + AWS Tool 1/2 → "IAM Auditor"
   - Agnóstico: GCP vs AWS
   
10. GCP Tool 5 + AWS Tool 3 → "Certificate Monitor"
    - Agnóstico: GCP vs AWS
    
11. GCP Tool 6 + AWS Tool 18 → "WAF Auditor"
    - Agnóstico: GCP vs AWS
    
12. AZDO Tool 7 + 8 → "Vulnerability Scanner"
    - Opción: logs vs repos vs both
```

### Prioridad 4: Bajos (Agregar Faltantes)

```
13. GCP: Agregar "Artifact Registry Checker" (AWS tiene ECR)
14. GCP: Agregar "Compute Instances Checker" (AWS tiene EC2)
15. Dashboard: Integrar más métricas de AZDO
```

---

## Matriz de Cobertura

### Por Categoría

| Categoría | GCP | AWS | AZDO | Terminal | Cobertura |
|-----------|-----|-----|------|----------|-----------|
| **Monitoreo** | ✅ | ✅ | ✅ | ❌ | 75% |
| **IAM/Security** | ✅ | ✅ | ✅ | ❌ | 75% |
| **Networking** | ✅ | ✅ | ❌ | ❌ | 67% |
| **Database** | ✅ | ✅ | ❌ | ❌ | 67% |
| **Kubernetes** | ✅ | ✅ | ⚠️ | ❌ | 67% |
| **Artifacts** | ❌ | ✅ | ❌ | ❌ | 25% |
| **Compute** | ❌ | ✅ | ❌ | ❌ | 25% |
| **CI/CD** | ❌ | ❌ | ✅ | ❌ | 25% |
| **Vulnerabilities** | ❌ | ❌ | ✅ | ❌ | 25% |

### Por Plataforma

| Plataforma | Total | Únicos | Duplicados | Solapamiento |
|-----------|-------|--------|-----------|--------------|
| **GCP** | 22 | 18 | 2 | 2 |
| **AWS** | 19 | 16 | 2 | 1 |
| **AZDO** | 27 | 18 | 4 | 5 |
| **Terminal** | 6 | 6 | 0 | 0 |
| **KPI** | 1 | 1 | 0 | 0 |
| **Dashboard** | 1 | 1 | 0 | 0 |
| **TOTAL** | 76 | 60 | 8 | 8 |

---

## Conclusiones

### Hallazgos Principales

1. **Duplicación Moderada:** ~10% de herramientas son duplicadas o altamente solapadas
2. **Oportunidades de Consolidación:** 8 grupos principales identificados
3. **Cobertura Desigual:** GCP y AWS bien cubiertos, AZDO tiene más duplicados
4. **Brechas:** Faltan herramientas para GCP (Artifacts, Compute)

### Impacto de Consolidación

```
Antes:
- 76 herramientas
- 8 duplicados
- 8 solapamientos

Después (Consolidación Completa):
- ~60 herramientas
- 0 duplicados
- 0 solapamientos
- Reducción: 21% de herramientas
- Ganancia: Mejor mantenibilidad y UX
```

### Próximos Pasos

1. **Fase 1:** Consolidar duplicados críticos (Prioridad 1)
2. **Fase 2:** Revisar y consolidar solapamientos (Prioridad 2)
3. **Fase 3:** Agregar herramientas faltantes (Prioridad 4)
4. **Fase 4:** Crear herramientas agnósticas (multi-cloud)

---

## Apéndice: Listado Completo de Herramientas

### GCP (22 herramientas)

```
MONITORING:
  1  → Monitoreo de Recursos GCP
  2  → Reporte de Despliegues GKE
  24 → GKE Node Resources Monitor
  25 → GKE Pod Resources Monitor

IAM & SECURITY:
  3  → Reporte de Roles y Permisos IAM
  4  → Service Account Checker
  5  → Certificate Manager Checker

SECURITY:
  6  → Cloud Armor Checker

DATABASE:
  7  → Cloud SQL Disk Monitor
  8  → Cloud SQL Database Checker
  9  → Cloud SQL Comparator

NETWORKING:
  10 → VPC Networks Checker
  11 → Gateway Services Checker
  12 → Load Balancer Checker
  13 → IP Addresses Checker

KUBERNETES:
  14 → GKE Cluster Checker
  15 → Secrets & ConfigMaps Checker
  16 → Pod Connectivity Checker

ARTIFACTS:
  (No disponible)

COMPUTE:
  (No disponible)
```

### AWS (19 herramientas)

```
IAM & SECURITY:
  1  → IAM Users & Policies Checker
  2  → IAM Roles Checker
  3  → ACM Certificate Checker

SECURITY:
  17 → Secrets Manager & SSM Checker

DATABASE:
  4  → RDS Instance Checker
  5  → RDS Storage Monitor
  14 → EBS Volume Checker

NETWORKING:
  6  → VPC Networks Checker
  7  → Security Groups Checker
  8  → Load Balancer Checker (ALB/NLB)
  18 → WAF Web ACL Checker

KUBERNETES:
  9  → EKS Cluster Checker
  15 → EKS Pod Monitor
  16 → EKS Node Monitor

ARTIFACTS:
  10 → ECR Repository Checker

COMPUTE:
  11 → EC2 Instances Checker
  12 → Lambda Functions Checker

MONITORING:
  13 → CloudWatch Alarms Checker

INVENTORY:
  19 → AWS Inventory Generator
```

### AZDO (27 herramientas)

```
PR:
  1  → PR Master Checker
  1b → PR Pipeline Analyzer

POLICY:
  2  → Branch Policy Checker
  2b → Branch Lock Checker

RELEASE:
  3  → Release CD Health
  5  → Release Deep Dive

DRIFT:
  4  → Pipeline Drift Analyzer

VALIDATION:
  6  → Task Validator

SECURITY:
  7  → Pipeline Logs Scanner
  8  → Repo Vulnerabilities Scanner

INVENTORY:
  9  → CICD Inventory
  10 → GKE Pipelines Inventory
  11 → Pending Approvals
  12 → Branches Created
  13 → Hotfix Branches Inventory
  14 → CI Pipeline Inventory (Detailed)
  15 → CD Pipeline Inventory (Detailed)
  17 → Prod Deploy Inventory
  20 → Properties Branch Diff
  21 → Repo Branch Diff

HEALTH:
  16 → Pipeline Health Score
  18 → Pipeline Status

QUALITY:
  19 → Release Explorer
  22 → Release Rollback
  23 → Release Restore

SYSTEM:
  24 → Release CD Rollback
  25 → Release CD Update
  A  → Ejecutar Todos
  B  → Ejecutar Todo + JSON
```

### Terminal (6 herramientas)

```
1 → TLS Certificate Validator
2 → Database Connection Tester
3 → Kubernetes Manifest Diff
4 → Kubernetes Deployment Validator
5 → Docker Image Validator
6 → Git Repository Validator
```

### KPI Analyzer (1 herramienta)

```
1 → KPI Analyzer (Modelo de madurez de 6 niveles)
```

### Dashboard (1 herramienta)

```
1 → Dashboard Matutino (Health Score, Code Coverage, PR Metrics, Teams Notifications)
```

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
