# Modelo de Madurez DevSecOps — 6 Niveles

> **Versión**: 1.0.0  
> **Última actualización**: 2026-06-09  
> **Basado en**: DORA, Google SRE, ITIL 4, NIST CSF, ISO/IEC 20000

---

## Resumen Ejecutivo

Este modelo de madurez DevSecOps define **6 niveles progresivos** (0-5) que integran las mejores prácticas de los frameworks líderes de la industria. Cada nivel representa un salto cualitativo en capacidades técnicas, culturales y organizacionales.

**Propósito**: Proporcionar una escala objetiva y cuantificable para evaluar la madurez DevSecOps de una organización, identificar gaps, y trazar un roadmap de mejora continua.

---

## Niveles de Madurez

### Nivel 0: Caótico

**Descripción**: Sin procesos formales. Operaciones manuales, reactivas y ad-hoc. Alta dependencia de individuos clave.

**Características Clave**:
- ❌ Sin CI/CD automatizado
- ❌ Sin monitoreo proactivo
- ❌ Sin políticas de seguridad documentadas
- ❌ Deployments manuales con alta tasa de fallos
- ❌ Sin versionado de infraestructura
- ❌ Sin tests automatizados

**Indicadores Cuantitativos**:
| Dimensión | Métrica | Valor Típico |
|-----------|---------|--------------|
| Entrega Continua | Deployment Frequency | < 1/mes |
| Entrega Continua | Change Failure Rate | > 50% |
| Confiabilidad | MTTR | > 7 días |
| Confiabilidad | Availability | < 95% |
| Seguridad | Vulnerabilities Remediation | > 90 días |
| Observabilidad | Monitoring Coverage | < 20% |

**Riesgos**: Outages frecuentes, incidentes de seguridad, pérdida de conocimiento, burnout del equipo.

---

### Nivel 1: Inicial

**Descripción**: Procesos básicos documentados. CI/CD en etapa temprana. Monitoreo reactivo. Seguridad como afterthought.

**Características Clave**:
- ✅ CI/CD básico (build + deploy manual)
- ✅ Documentación mínima de procesos
- ⚠️ Monitoreo básico (logs, alertas simples)
- ⚠️ Políticas de seguridad definidas pero no aplicadas consistentemente
- ⚠️ Tests unitarios parciales
- ❌ Sin rollback automatizado

**Indicadores Cuantitativos**:
| Dimensión | Métrica | Valor Típico |
|-----------|---------|--------------|
| Entrega Continua | Deployment Frequency | 1-2/mes |
| Entrega Continua | Change Failure Rate | 30-50% |
| Entrega Continua | Lead Time for Changes | > 1 mes |
| Confiabilidad | MTTR | 2-7 días |
| Confiabilidad | Availability | 95-98% |
| Seguridad | MFA Coverage | < 50% |
| Seguridad | Secret Rotation | Manual, > 180 días |
| Observabilidad | Monitoring Coverage | 20-40% |
| Cumplimiento | Policy Adherence | < 50% |
| Eficiencia | Resource Utilization | < 40% |

**Mejoras Requeridas para Nivel 2**:
1. Automatizar deployments completos (CI + CD)
2. Implementar rollback automatizado
3. Establecer métricas DORA básicas
4. Cobertura de tests > 50%
5. Monitoreo de servicios críticos

---

### Nivel 2: Gestionado

**Descripción**: Procesos repetibles y medibles. CI/CD automatizado. Monitoreo básico. Políticas de seguridad aplicadas.

**Características Clave**:
- ✅ CI/CD completamente automatizado
- ✅ Rollback automatizado
- ✅ Tests automatizados (unit + integration)
- ✅ Monitoreo de servicios críticos
- ✅ Políticas de seguridad aplicadas (branch policies, approvals)
- ✅ Versionado de infraestructura (IaC básico)
- ⚠️ Métricas DORA básicas recolectadas

**Indicadores Cuantitativos**:
| Dimensión | Métrica | Valor Típico |
|-----------|---------|--------------|
| Entrega Continua | Deployment Frequency | 1/semana |
| Entrega Continua | Change Failure Rate | 15-30% |
| Entrega Continua | Lead Time for Changes | 1-4 semanas |
| Confiabilidad | MTTR | 1-2 días |
| Confiabilidad | Availability | 98-99% |
| Confiabilidad | MTBF | > 30 días |
| Seguridad | MFA Coverage | 50-80% |
| Seguridad | Certificate Expiry Monitoring | ✅ |
| Seguridad | Vulnerability Scan Frequency | Semanal |
| Observabilidad | Monitoring Coverage | 40-60% |
| Observabilidad | Alerting Response Time | < 1 hora |
| Cumplimiento | Policy Adherence | 50-70% |
| Cumplimiento | Approval Workflow Coverage | > 80% |
| Eficiencia | Resource Utilization | 40-60% |
| Eficiencia | Cost Optimization Actions | Manual |

**Mejoras Requeridas para Nivel 3**:
1. Deployment frequency > 1/día
2. Change failure rate < 15%
3. MTTR < 24 horas
4. Cobertura de tests > 70%
5. Monitoreo de SLIs/SLOs
6. Secret rotation automatizada

---

### Nivel 3: Definido

**Descripción**: Procesos estandarizados y optimizados. Métricas DORA completas. SLIs/SLOs definidos. Seguridad integrada (shift-left).

**Características Clave**:
- ✅ Deployment frequency diaria o superior
- ✅ Change failure rate < 15%
- ✅ MTTR < 24 horas
- ✅ Cobertura de tests > 70%
- ✅ SLIs/SLOs definidos y monitoreados
- ✅ Security scanning automatizado (SAST/DAST)
- ✅ Secret rotation automatizada
- ✅ IaC completo (Terraform/Pulumi)
- ✅ Observabilidad distribuida (tracing, logs, metrics)

**Indicadores Cuantitativos**:
| Dimensión | Métrica | Valor Típico |
|-----------|---------|--------------|
| Entrega Continua | Deployment Frequency | 1/día - 1/semana |
| Entrega Continua | Change Failure Rate | 5-15% |
| Entrega Continua | Lead Time for Changes | < 1 semana |
| Entrega Continua | Deployment Success Rate | > 85% |
| Confiabilidad | MTTR | < 24 horas |
| Confiabilidad | Availability | 99-99.5% |
| Confiabilidad | MTBF | > 60 días |
| Confiabilidad | Error Budget Tracking | ✅ |
| Seguridad | MFA Coverage | > 90% |
| Seguridad | Secret Rotation Frequency | < 90 días |
| Seguridad | Vulnerability Remediation | < 30 días (critical) |
| Seguridad | IAM Over-Permissioning | < 10% |
| Observabilidad | Monitoring Coverage | 60-80% |
| Observabilidad | SLO Compliance | > 95% |
| Observabilidad | Distributed Tracing | ✅ |
| Cumplimiento | Policy Adherence | 70-90% |
| Cumplimiento | Drift Detection | Semanal |
| Eficiencia | Resource Utilization | 60-75% |
| Eficiencia | Cost Optimization | Automatizado básico |

**Mejoras Requeridas para Nivel 4**:
1. Deployment on-demand (múltiples/día)
2. Change failure rate < 5%
3. MTTR < 1 hora
4. Error budgets activos con alertas
5. Chaos engineering básico
6. Auto-scaling avanzado

---

### Nivel 4: Cuantificado

**Descripción**: Métricas avanzadas. Error budgets activos. Auto-healing. Seguridad predictiva. Optimización continua basada en datos.

**Características Clave**:
- ✅ Deployment on-demand (múltiples/día)
- ✅ Change failure rate < 5%
- ✅ MTTR < 1 hora
- ✅ Error budgets con alertas y políticas de freeze
- ✅ Auto-healing de incidentes comunes
- ✅ Chaos engineering (GameDays)
- ✅ Security posture management automatizado
- ✅ Predictive analytics (anomaly detection)
- ✅ Cost optimization automatizado
- ✅ Canary deployments / Blue-Green

**Indicadores Cuantitativos**:
| Dimensión | Métrica | Valor Típico |
|-----------|---------|--------------|
| Entrega Continua | Deployment Frequency | > 1/día (on-demand) |
| Entrega Continua | Change Failure Rate | 0-5% |
| Entrega Continua | Lead Time for Changes | < 1 día |
| Entrega Continua | Deployment Success Rate | > 95% |
| Confiabilidad | MTTR | < 1 hora |
| Confiabilidad | Availability | 99.5-99.9% (3 nines) |
| Confiabilidad | MTBF | > 90 días |
| Confiabilidad | Error Budget Burn Rate | Monitoreado activamente |
| Confiabilidad | Auto-Healing Coverage | > 50% incidentes |
| Seguridad | MFA Coverage | 100% |
| Seguridad | Secret Rotation Frequency | < 30 días |
| Seguridad | Vulnerability Remediation | < 7 días (critical) |
| Seguridad | Zero-Trust Implementation | Parcial |
| Seguridad | Security Posture Score | > 80/100 |
| Observabilidad | Monitoring Coverage | 80-95% |
| Observabilidad | SLO Compliance | > 99% |
| Observabilidad | Anomaly Detection | ✅ |
| Observabilidad | Distributed Tracing Coverage | > 80% |
| Cumplimiento | Policy Adherence | > 90% |
| Cumplimiento | Drift Detection | Diaria + auto-remediation |
| Eficiencia | Resource Utilization | 75-85% |
| Eficiencia | Cost Optimization Savings | > 20% anual |
| Eficiencia | Auto-Scaling Effectiveness | > 90% |

**Mejoras Requeridas para Nivel 5**:
1. MTTR < 15 minutos
2. Availability > 99.9% (4 nines)
3. Chaos engineering continuo
4. Zero-trust completo
5. AIOps / ML-driven operations
6. Self-service platform

---

### Nivel 5: Optimizado

**Descripción**: Mejora continua automatizada. AIOps. Zero-trust. Chaos engineering continuo. Organización de alto rendimiento (Elite DORA).

**Características Clave**:
- ✅ Deployment on-demand con confianza extrema
- ✅ Change failure rate < 1%
- ✅ MTTR < 15 minutos
- ✅ Availability > 99.9% (4 nines o superior)
- ✅ Chaos engineering continuo (automated)
- ✅ AIOps / ML-driven incident response
- ✅ Zero-trust architecture completa
- ✅ Self-healing avanzado (> 80% incidentes)
- ✅ Predictive capacity planning
- ✅ Developer self-service platform
- ✅ FinOps culture (cost as code)

**Indicadores Cuantitativos**:
| Dimensión | Métrica | Valor Elite |
|-----------|---------|-------------|
| Entrega Continua | Deployment Frequency | On-demand (múltiples/hora) |
| Entrega Continua | Change Failure Rate | < 1% |
| Entrega Continua | Lead Time for Changes | < 1 hora |
| Entrega Continua | Deployment Success Rate | > 99% |
| Confiabilidad | MTTR | < 15 minutos |
| Confiabilidad | Availability | > 99.9% (4+ nines) |
| Confiabilidad | MTBF | > 180 días |
| Confiabilidad | Error Budget Utilization | < 10% |
| Confiabilidad | Auto-Healing Coverage | > 80% incidentes |
| Seguridad | MFA Coverage | 100% + hardware keys |
| Seguridad | Secret Rotation Frequency | < 7 días (automated) |
| Seguridad | Vulnerability Remediation | < 24 horas (critical) |
| Seguridad | Zero-Trust Implementation | Completo |
| Seguridad | Security Posture Score | > 95/100 |
| Observabilidad | Monitoring Coverage | > 95% |
| Observabilidad | SLO Compliance | > 99.9% |
| Observabilidad | Anomaly Detection Accuracy | > 95% |
| Observabilidad | Distributed Tracing Coverage | > 95% |
| Cumplimiento | Policy Adherence | > 95% |
| Cumplimiento | Drift Detection | Real-time + auto-remediation |
| Eficiencia | Resource Utilization | 85-95% (optimal) |
| Eficiencia | Cost Optimization Savings | > 30% anual |
| Eficiencia | Auto-Scaling Effectiveness | > 98% |
| Eficiencia | FinOps Maturity | Advanced |

**Características de Organizaciones Elite**:
- Cultura de experimentación y aprendizaje
- Blameless postmortems
- Continuous improvement como hábito
- Developer experience como prioridad
- Platform engineering team
- SRE principles embedded
- Observability-driven development

---

## Dimensiones y Pesos

Cada nivel se evalúa en 6 dimensiones con pesos específicos:

| Dimensión | Peso | Descripción |
|-----------|------|-------------|
| **Entrega Continua** | 20% | Deployment frequency, lead time, change failure rate, deployment success rate |
| **Confiabilidad** | 20% | MTTR, MTBF, availability, error budget, auto-healing |
| **Seguridad** | 20% | MFA, secret rotation, vulnerability remediation, IAM hygiene, zero-trust |
| **Observabilidad** | 15% | Monitoring coverage, SLI/SLO compliance, distributed tracing, anomaly detection |
| **Cumplimiento** | 15% | Policy adherence, approval workflows, drift detection, audit trail |
| **Eficiencia Operativa** | 10% | Resource utilization, cost optimization, auto-scaling, FinOps |

**Cálculo del Nivel Global**:
```
Nivel Global = Σ (Dimensión_Score × Peso)
```

Donde `Dimensión_Score` es el nivel (0-5) alcanzado en cada dimensión.

---

## Matriz de Transición

Para avanzar de un nivel a otro, se requiere cumplir **al menos el 80%** de los indicadores cuantitativos del nivel objetivo en **al menos 5 de las 6 dimensiones**.

| Desde | Hacia | Tiempo Estimado | Esfuerzo | Inversión |
|-------|-------|-----------------|----------|-----------|
| 0 → 1 | Inicial | 3-6 meses | Alto | Media |
| 1 → 2 | Gestionado | 6-12 meses | Alto | Media-Alta |
| 2 → 3 | Definido | 12-18 meses | Medio-Alto | Alta |
| 3 → 4 | Cuantificado | 18-24 meses | Medio | Alta |
| 4 → 5 | Optimizado | 24-36 meses | Medio | Media |

---

## Roadmap de Mejora por Nivel

### De Nivel 0 a Nivel 1
**Prioridad**: Establecer fundamentos
1. Implementar CI básico (build automatizado)
2. Documentar procesos críticos
3. Configurar monitoreo básico (logs, uptime)
4. Definir políticas de seguridad
5. Establecer versionado de código

### De Nivel 1 a Nivel 2
**Prioridad**: Automatización y repetibilidad
1. Automatizar deployments completos
2. Implementar rollback automatizado
3. Cobertura de tests > 50%
4. Monitoreo de servicios críticos
5. Aplicar políticas de seguridad (branch policies)
6. IaC básico (Terraform/CloudFormation)

### De Nivel 2 a Nivel 3
**Prioridad**: Estandarización y métricas
1. Deployment frequency > 1/día
2. Definir SLIs/SLOs
3. Security scanning automatizado
4. Secret rotation automatizada
5. Observabilidad distribuida (tracing)
6. Error budget tracking

### De Nivel 3 a Nivel 4
**Prioridad**: Optimización y predictibilidad
1. Deployment on-demand
2. Error budgets con políticas de freeze
3. Auto-healing de incidentes comunes
4. Chaos engineering (GameDays)
5. Predictive analytics
6. Canary deployments

### De Nivel 4 a Nivel 5
**Prioridad**: Excelencia operacional
1. AIOps / ML-driven operations
2. Zero-trust completo
3. Chaos engineering continuo
4. Self-service platform
5. FinOps culture
6. Developer experience optimization

---

## Referencias

- **DORA State of DevOps Report 2024**: https://dora.dev/research/
- **Google SRE Book**: https://sre.google/sre-book/table-of-contents/
- **ITIL 4 Foundation**: https://www.axelos.com/certifications/itil-service-management
- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework
- **ISO/IEC 20000**: https://www.iso.org/standard/70636.html
- **CALMS Framework**: https://www.atlassian.com/devops/frameworks/calms-framework

---

## Uso en KPI Analyzer

Este modelo de madurez se integra en el KPI Analyzer de las siguientes formas:

1. **Evaluación Automática**: El script `analyze_kpis.py` calcula el nivel de madurez actual basándose en las métricas recolectadas de las salidas JSON.

2. **Visualización**: Los dashboards (HTML y Streamlit) muestran:
   - Nivel global (0-5) con gauge circular
   - Nivel por dimensión con radar chart
   - Gap analysis: qué KPIs mejorar para subir de nivel
   - Roadmap visual con acciones priorizadas

3. **Benchmarking**: Comparación con valores de referencia de industria (Elite, High, Medium, Low).

4. **Roadmap Generado**: Basándose en el nivel actual y el objetivo, el sistema genera un roadmap personalizado con acciones priorizadas por impacto.
