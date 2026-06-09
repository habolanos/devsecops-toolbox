# KPIs y Frameworks DevSecOps — Documento Maestro

> **Versión**: 1.0.0  
> **Última actualización**: 2026-06-09  
> **Autor**: Harold Adrian Bolaños Rodríguez

---

## Resumen Ejecutivo

Este documento define un catálogo completo de **30 KPIs (Key Performance Indicators)** para evaluar la madurez DevSecOps de una organización, alineados con los frameworks líderes de la industria: **DORA**, **Google SRE**, **ITIL 4**, **CALMS**, **ISO/IEC 20000**, y **NIST Cybersecurity Framework**.

### Propósito

- **Medir objetivamente** el desempeño DevSecOps en 6 dimensiones clave
- **Comparar** contra benchmarks de industria (Elite, High, Medium, Low)
- **Identificar gaps** y oportunidades de mejora
- **Trazar roadmaps** basados en datos para evolucionar de nivel de madurez
- **Automatizar** la recolección y análisis de métricas desde salidas JSON del toolbox

### Alcance

El análisis cubre **67 herramientas** del DevSecOps Toolbox que generan salidas JSON estructuradas en 4 plataformas:
- **GCP** (Google Cloud Platform): 25 herramientas
- **AZDO** (Azure DevOps): 17 herramientas
- **AWS** (Amazon Web Services): 19 herramientas
- **Terminal** (Scripts universales): 6 herramientas

### Metodología

1. **Descubrimiento automático** de archivos JSON en `outcome/`
2. **Extracción** de campos relevantes según esquema YAML
3. **Cálculo** de KPIs aplicando fórmulas definidas
4. **Evaluación** contra benchmarks de industria
5. **Determinación** del nivel de madurez DevSecOps (0-5)
6. **Generación** de reportes (JSON, CSV, HTML) y dashboards interactivos

---

## Marco Teórico

### DORA (DevOps Research and Assessment)

**Origen**: Investigación de Google Cloud y DORA (2014-presente)  
**Enfoque**: Métricas de entrega de software y rendimiento organizacional

**4 Métricas Clave**:
1. **Deployment Frequency**: Frecuencia de deployments a producción
2. **Lead Time for Changes**: Tiempo desde commit hasta producción
3. **Change Failure Rate**: Porcentaje de deployments que fallan
4. **Mean Time to Recovery (MTTR)**: Tiempo para recuperarse de incidentes

**Niveles de Rendimiento** (DORA 2024):
- **Elite**: Deployment frequency on-demand, MTTR < 1h, CFR < 5%
- **High**: Deployment frequency semanal-diario, MTTR < 1d, CFR 5-15%
- **Medium**: Deployment frequency mensual-semanal, MTTR < 1 semana, CFR 15-30%
- **Low**: Deployment frequency < mensual, MTTR > 1 semana, CFR > 30%

### Google SRE (Site Reliability Engineering)

**Origen**: Google (2003-presente), "Site Reliability Engineering" book (2016)  
**Enfoque**: Confiabilidad, disponibilidad, y operaciones escalables

**Conceptos Clave**:
- **SLI (Service Level Indicator)**: Métrica cuantitativa de un aspecto del servicio (ej: latencia, disponibilidad)
- **SLO (Service Level Objective)**: Objetivo para un SLI (ej: 99.9% uptime)
- **Error Budget**: Margen de error permitido (100% - SLO)
- **Toil**: Trabajo operativo manual, repetitivo, automatizable

**Principios**:
- Availability > 99.9% (4 nines) para servicios críticos
- Error budgets como mecanismo de balance entre velocidad y estabilidad
- Automatización para reducir toil < 50% del tiempo
- Postmortems blameless para aprendizaje continuo

### ITIL 4 (Information Technology Infrastructure Library)

**Origen**: AXELOS (evolución desde 1980s, ITIL 4 desde 2019)  
**Enfoque**: Gestión de servicios IT y creación de valor

**Principios Guía**:
1. Enfoque en el valor
2. Comenzar donde estás
3. Progresar iterativamente con feedback
4. Colaborar y promover visibilidad
5. Pensar y trabajar holísticamente
6. Mantener simple y práctico
7. Optimizar y automatizar

**Prácticas Relevantes para DevSecOps**:
- **Change Control**: Gestión de cambios con aprobaciones y rollback
- **Incident Management**: Respuesta y resolución de incidentes
- **Problem Management**: Análisis de causa raíz
- **Service Level Management**: Definición y monitoreo de SLAs
- **Continuous Improvement**: Mejora continua basada en métricas

### CALMS Framework

**Origen**: Jez Humble y otros (2010s)  
**Enfoque**: Cultura y prácticas DevOps

**5 Pilares**:
- **C**ulture: Colaboración, confianza, blameless postmortems
- **A**utomation: CI/CD, IaC, testing automatizado
- **L**ean: Eliminar desperdicio, optimizar flujo de valor
- **M**easurement: Métricas para decisiones basadas en datos
- **S**haring: Compartir conocimiento, herramientas, responsabilidades

### ISO/IEC 20000

**Origen**: ISO (2005, revisado 2018)  
**Enfoque**: Sistema de gestión de servicios IT (ITSM)

**Requisitos Clave**:
- Políticas documentadas y comunicadas
- Gestión de cambios con aprobaciones
- Gestión de configuración y activos
- Gestión de incidentes y problemas
- Auditorías internas y mejora continua
- Gestión de proveedores y SLAs

### NIST Cybersecurity Framework

**Origen**: NIST (2014, actualizado 2018)  
**Enfoque**: Gestión de riesgos de ciberseguridad

**5 Funciones**:
1. **Identify**: Gestión de activos, riesgos, y vulnerabilidades
2. **Protect**: Controles de acceso, protección de datos, seguridad de procesos
3. **Detect**: Monitoreo continuo, detección de anomalías
4. **Respond**: Planificación de respuesta, comunicación, análisis
5. **Recover**: Planificación de recuperación, mejoras post-incidente

---

## Inventario de Fuentes JSON

Ver documento completo: [`docs/kpi_sources_inventory.md`](kpi_sources_inventory.md)

**Resumen**:
- **67 scripts** generan salidas JSON estructuradas
- **Ubicación estándar**: `outcome/<tool_name>_YYYYMMDD_HHMMSS.json`
- **Metadata común**: `script`, `version`, `generated_at`, `platform`, `project_id`
- **Estructura común**: `metadata`, `summary`, `data[]`

---

## Catálogo de KPIs

### Dimensión 1: Entrega Continua (20%)

#### EC-001: Deployment Frequency

**Definición**: Frecuencia de deployments exitosos a producción

**Fórmula**:
```
count(deployments where status='success' and environment='prod' in last 7 days) / 7
```

**Unidad**: deploys/día

**Frameworks**: DORA

**Fuentes JSON**:
- `azdo/cicd_inventory_prod_deploy.py` → `deployments[].status`, `deployments[].environment`, `deployments[].timestamp`
- `azdo/cicd_pipeline_status.py` → `pipelines[].last_run`, `pipelines[].status`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | ≥ 1 | Al menos 1 deploy/día |
| High | 0.14-1 | 1/semana a 1/día |
| Medium | 0.03-0.14 | 1/mes a 1/semana |
| Low | < 0.03 | Menos de 1/mes |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (≥ 1 deploy/día)

---

#### EC-002: Change Failure Rate

**Definición**: Porcentaje de deployments que resultan en fallo o requieren rollback

**Fórmula**:
```
count(deployments where status='failed' or rollback=true) / count(total_deployments) * 100
```

**Unidad**: %

**Frameworks**: DORA

**Fuentes JSON**:
- `azdo/cicd_inventory_prod_deploy.py` → `deployments[].status`, `deployments[].rollback`
- `azdo/cicd_pipeline_status.py` → `pipelines[].failure_count_7d`, `pipelines[].total_runs_7d`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | < 5% | Menos del 5% fallan |
| High | 5-15% | Entre 5% y 15% |
| Medium | 15-30% | Entre 15% y 30% |
| Low | > 30% | Más del 30% fallan |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (< 5%)

---

#### EC-003: Lead Time for Changes

**Definición**: Tiempo desde commit hasta deploy en producción

**Fórmula**:
```
avg(deployment_timestamp - commit_timestamp)
```

**Unidad**: horas

**Frameworks**: DORA

**Fuentes JSON**:
- `azdo/cicd_inventory.py` → `repos[].last_commit_date`
- `azdo/cicd_inventory_prod_deploy.py` → `deployments[].timestamp`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | < 24h | Menos de 1 día |
| High | 24-168h | 1-7 días |
| Medium | 168-720h | 1-4 semanas |
| Low | > 720h | Más de 1 mes |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (< 24h)

---

### Dimensión 2: Confiabilidad (20%)

#### CONF-001: Mean Time to Recovery (MTTR)

**Definición**: Tiempo promedio para recuperarse de un incidente

**Fórmula**:
```
avg(time_resolved - time_detected)
```

**Unidad**: minutos

**Frameworks**: DORA, SRE, ITIL

**Fuentes JSON**:
- `azdo/cicd_inventory_health_score.py` → `pipelines[].mttr_minutes`
- `azdo/cicd_pipeline_status.py` → `pipelines[].last_failure_timestamp`, `pipelines[].last_success_timestamp`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | < 60min | Menos de 1 hora |
| High | 60-1440min | 1-24 horas |
| Medium | 1440-10080min | 1-7 días |
| Low | > 10080min | Más de 7 días |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (< 1h)

---

#### CONF-002: Service Availability

**Definición**: Porcentaje de uptime de servicios críticos

**Fórmula**:
```
sum(uptime_minutes) / sum(total_minutes) * 100
```

**Unidad**: %

**Frameworks**: SRE, ITIL

**Fuentes JSON**:
- `gcp/load-balancer/gcp_load_balancer_checker.py` → `load_balancers[].backends[].healthy_count`, `load_balancers[].backends[].total_count`
- `aws/elb/aws_load_balancer_checker.py` → `load_balancers[].healthy_targets`, `load_balancers[].total_targets`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | > 99.9% | 4 nines |
| High | 99.5-99.9% | 3 nines |
| Medium | 99.0-99.5% | 2 nines |
| Low | < 99.0% | Menos de 99% |

**Nivel de Madurez Requerido**: 4 (Cuantificado)

**Periodicidad**: Horaria

**Meta Sugerida**: Elite (> 99.9%)

---

### Dimensión 3: Seguridad (20%)

#### SEG-001: MFA Coverage

**Definición**: Porcentaje de usuarios con MFA habilitado

**Fórmula**:
```
count(users where mfa_enabled=true) / count(total_users) * 100
```

**Unidad**: %

**Frameworks**: NIST CSF, ISO 20000

**Fuentes JSON**:
- `aws/iam/aws_iam_checker.py` → `users[].mfa_enabled`
- `gcp/service-account/gcp_service_account_checker.py` → `service_accounts[].mfa_enabled`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | 100% | Todos con MFA |
| High | 90-100% | 90% o más |
| Medium | 70-90% | 70-90% |
| Low | < 70% | Menos del 70% |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (100%)

---

#### SEG-002: Certificate Expiry Risk

**Definición**: Porcentaje de certificados que expiran en < 30 días

**Fórmula**:
```
count(certs where days_to_expiry < 30) / count(total_certs) * 100
```

**Unidad**: %

**Frameworks**: NIST CSF, ITIL

**Fuentes JSON**:
- `gcp/certificate-manager/gcp_certificate_checker.py` → `certificates[].days_to_expiry`
- `aws/acm/aws_acm_checker.py` → `certificates[].days_to_expiry`
- `terminal/certificate-tls-report.sh` → `certificates[].days_remaining`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | 0% | Ninguno expirando |
| High | 0-5% | Menos del 5% |
| Medium | 5-15% | 5-15% |
| Low | > 15% | Más del 15% |

**Nivel de Madurez Requerido**: 2 (Gestionado)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (0%)

---

### Dimensión 4: Observabilidad (15%)

#### OBS-001: Monitoring Coverage

**Definición**: Porcentaje de servicios con monitoreo activo

**Fórmula**:
```
count(services where monitoring_enabled=true) / count(total_services) * 100
```

**Unidad**: %

**Frameworks**: SRE

**Fuentes JSON**:
- `gcp/monitoring/gcp_monitor.py` → `resources[].type`, `resources[].status`
- `aws/cloudwatch/aws_cloudwatch_checker.py` → `alarms[].metric`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | > 95% | Más del 95% |
| High | 80-95% | 80-95% |
| Medium | 60-80% | 60-80% |
| Low | < 60% | Menos del 60% |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (> 95%)

---

### Dimensión 5: Cumplimiento (15%)

#### CUMP-001: Policy Adherence Rate

**Definición**: Porcentaje de recursos que cumplen políticas definidas

**Fórmula**:
```
count(resources where compliant=true) / count(total_resources) * 100
```

**Unidad**: %

**Frameworks**: ITIL, ISO 20000

**Fuentes JSON**:
- `azdo/azdo_branch_policy_checker.py` → `repos[].policies[].compliant`
- `azdo/azdo_pr_master_checker.py` → `prs[].compliant`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | > 95% | Más del 95% |
| High | 85-95% | 85-95% |
| Medium | 70-85% | 70-85% |
| Low | < 70% | Menos del 70% |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Diaria

**Meta Sugerida**: Elite (> 95%)

---

### Dimensión 6: Eficiencia Operativa (10%)

#### EFIC-001: Resource Utilization Rate

**Definición**: Porcentaje promedio de utilización de recursos (CPU/Memory)

**Fórmula**:
```
avg(used / allocated) * 100
```

**Unidad**: %

**Frameworks**: SRE

**Fuentes JSON**:
- `gcp/monitoring/gke_node_monitor.py` → `nodes[].cpu_allocatable`, `nodes[].memory_allocatable`
- `aws/eks/aws_eks_node_checker.py` → `nodes[].cpu_allocatable`, `nodes[].memory_allocatable`
- `aws/ec2/aws_ec2_checker.py` → `instances[].cpu_utilization`

**Benchmarks**:
| Nivel | Valor | Descripción |
|-------|-------|-------------|
| Elite | 75-85% | Rango óptimo |
| High | 60-90% | Bueno |
| Medium | 40-95% | Aceptable |
| Low | < 40% o > 95% | Sub/sobre utilizado |

**Nivel de Madurez Requerido**: 3 (Definido)

**Periodicidad**: Horaria

**Meta Sugerida**: Elite (75-85%)

---

## Matriz de Cobertura Frameworks × KPIs

| KPI | DORA | SRE | ITIL 4 | CALMS | ISO 20000 | NIST CSF |
|-----|------|-----|--------|-------|-----------|----------|
| Deployment Frequency | ✅ | — | — | ✅ (A) | — | — |
| Change Failure Rate | ✅ | — | ✅ | ✅ (M) | ✅ | — |
| Lead Time for Changes | ✅ | — | — | ✅ (L) | — | — |
| MTTR | ✅ | ✅ | ✅ | ✅ (M) | ✅ | ✅ |
| Service Availability | — | ✅ | ✅ | — | ✅ | — |
| Error Budget | — | ✅ | — | — | — | — |
| MFA Coverage | — | — | — | — | ✅ | ✅ |
| Certificate Expiry Risk | — | — | ✅ | — | — | ✅ |
| Secret Rotation | — | — | — | — | — | ✅ |
| IAM Over-Permissioning | — | — | — | — | — | ✅ |
| Monitoring Coverage | — | ✅ | ✅ | ✅ (M) | — | ✅ |
| SLO Compliance | — | ✅ | ✅ | — | ✅ | — |
| Policy Adherence | — | — | ✅ | — | ✅ | — |
| Pipeline Drift | — | — | ✅ | — | ✅ | — |
| Resource Utilization | — | ✅ | — | ✅ (L) | — | — |

**Leyenda CALMS**: (C)ulture, (A)utomation, (L)ean, (M)easurement, (S)haring

---

## Implementación Técnica

### Ejecución del Analizador

```bash
# Analizar todos los KPIs
python scm/kpi_analyzer/analyze_kpis.py

# Filtrar por plataforma
python scm/kpi_analyzer/analyze_kpis.py --platform gcp

# Exportar solo JSON
python scm/kpi_analyzer/analyze_kpis.py --output json

# Generar dashboard HTML
python scm/kpi_analyzer/analyze_kpis.py --dashboard

# Mostrar evaluación de madurez
python scm/kpi_analyzer/analyze_kpis.py --maturity
```

### Estructura de Salidas

**JSON** (`outcome/kpi_report_YYYYMMDD_HHMMSS.json`):
```json
{
  "metadata": {
    "generated_at": "2026-06-09T10:30:00Z",
    "platform": "all",
    "analyzer_version": "1.0.0"
  },
  "dimensions": {
    "entrega_continua": {
      "name": "entrega_continua",
      "weight": 0.20,
      "kpis": [...]
    }
  },
  "kpis": [
    {
      "id": "ec_001",
      "name": "Deployment Frequency",
      "value": 0.85,
      "unit": "deploys/día",
      "benchmarks": {...},
      "frameworks": ["DORA"]
    }
  ]
}
```

**CSV** (`outcome/kpi_report_YYYYMMDD_HHMMSS.csv`):
```
ID,Name,Value,Unit,Benchmark Elite,Benchmark High,...
ec_001,Deployment Frequency,0.85,deploys/día,>= 1,0.14-1,...
```

**HTML** (`outcome/kpi_report_YYYYMMDD_HHMMSS.html`):
- Reporte visual con cards de KPIs
- Semáforos de benchmark (🔴🟡🟢💚)
- Agrupación por dimensión

---

## Roadmap de Mejoras

### Nivel Actual → Nivel Objetivo

El sistema genera automáticamente un roadmap personalizado basándose en:
1. **Nivel de madurez actual** (calculado desde KPIs)
2. **Nivel objetivo** (seleccionado por el usuario)
3. **KPIs bloqueantes** (que impiden avanzar de nivel)
4. **Impacto vs Esfuerzo** de cada acción

### Ejemplo: De Gestionado (2) a Definido (3)

**Acciones Priorizadas**:
1. ✅ Aumentar deployment frequency > 1/día (Impacto: Alto, Esfuerzo: Medio)
2. ✅ Definir SLIs/SLOs para servicios críticos (Impacto: Alto, Esfuerzo: Medio)
3. ✅ Implementar security scanning automatizado (Impacto: Alto, Esfuerzo: Alto)
4. ✅ Automatizar secret rotation (Impacto: Alto, Esfuerzo: Medio)
5. ✅ Implementar observabilidad distribuida (Impacto: Alto, Esfuerzo: Alto)

**Timeline Estimado**: 12-18 meses

---

## Apéndice

### Glosario

- **CI/CD**: Continuous Integration / Continuous Deployment
- **DORA**: DevOps Research and Assessment
- **IaC**: Infrastructure as Code
- **MTBF**: Mean Time Between Failures
- **MTTR**: Mean Time to Recovery
- **SLI**: Service Level Indicator
- **SLO**: Service Level Objective
- **SRE**: Site Reliability Engineering
- **Toil**: Trabajo operativo manual repetitivo

### Referencias Bibliográficas

1. **DORA State of DevOps Report 2024**  
   https://dora.dev/research/

2. **Google SRE Book**  
   https://sre.google/sre-book/table-of-contents/

3. **ITIL 4 Foundation**  
   https://www.axelos.com/certifications/itil-service-management

4. **NIST Cybersecurity Framework v1.1**  
   https://www.nist.gov/cyberframework

5. **ISO/IEC 20000-1:2018**  
   https://www.iso.org/standard/70636.html

6. **Accelerate: The Science of Lean Software and DevOps**  
   Nicole Forsgren, Jez Humble, Gene Kim (2018)

7. **The Phoenix Project**  
   Gene Kim, Kevin Behr, George Spafford (2013)

### Enlaces Útiles

- **DevSecOps Toolbox GitHub**: (internal repo)
- **KPI Analyzer Documentation**: `docs/kpi_sources_inventory.md`
- **Maturity Model**: `docs/DevSecOps_Maturity_Model.md`
- **Schema YAML**: `scm/kpi_analyzer/kpi_schema.yaml`

---

**Documento generado por**: DevSecOps Toolbox KPI Analyzer v1.0.0  
**Fecha**: 2026-06-09  
**Autor**: Harold Adrian Bolaños Rodríguez
