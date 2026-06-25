# ✅ Checklist de Depuración - DevSecOps Toolbox

**Objetivo:** Guía paso a paso para depurar duplicados y consolidar herramientas

---

## 📋 Checklist de Consolidación

### Fase 1: Duplicados Críticos (Semana 1)

#### [ ] 1. AZDO Tool 1 + 1b → "PR & Release Analyzer"

**Herramientas Actuales:**
- Tool 1: PR Master Checker (PRs hacia master con pipeline CD)
- Tool 1b: PR Pipeline Analyzer (PRs de múltiples ramas + CD pipelines)

**Análisis:**
```
Similitud: 85%
Diferencia: Scope (master vs multi-branch)
Impacto: Consolidación reducirá 1 herramienta
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta "PR & Release Analyzer"
- [ ] Agregar opción `--scope` (master|multi|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar Tool 1b
- [ ] Commit: `feat: Consolidate PR analyzers into single tool`

**Estimado:** 4 horas

---

#### [ ] 2. AZDO Tool 2 + 2b → "Branch Management Auditor"

**Herramientas Actuales:**
- Tool 2: Branch Policy Checker (audita políticas)
- Tool 2b: Branch Lock Checker (lista ramas con lock)

**Análisis:**
```
Similitud: 70%
Diferencia: Tipo de análisis (políticas vs locks)
Impacto: Consolidación reducirá 1 herramienta
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta "Branch Management Auditor"
- [ ] Agregar opción `--check` (policies|locks|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar Tool 2b
- [ ] Commit: `feat: Consolidate branch checkers into single tool`

**Estimado:** 4 horas

---

#### [ ] 3. GCP Tool 24 + 25 → "GKE Resources Monitor"

**Herramientas Actuales:**
- Tool 24: GKE Node Resources Monitor
- Tool 25: GKE Pod Resources Monitor

**Análisis:**
```
Similitud: 90%
Diferencia: Scope (nodos vs pods)
Impacto: Consolidación reducirá 1 herramienta
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta "GKE Resources Monitor"
- [ ] Agregar opción `--resource` (nodes|pods|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar Tool 25
- [ ] Commit: `feat: Consolidate GKE monitors into single tool`

**Estimado:** 3 horas

---

#### [ ] 4. AWS Tool 15 + 16 → "EKS Resources Monitor"

**Herramientas Actuales:**
- Tool 15: EKS Pod Monitor
- Tool 16: EKS Node Monitor

**Análisis:**
```
Similitud: 90%
Diferencia: Scope (pods vs nodos)
Impacto: Consolidación reducirá 1 herramienta
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta "EKS Resources Monitor"
- [ ] Agregar opción `--resource` (pods|nodes|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar Tool 16
- [ ] Commit: `feat: Consolidate EKS monitors into single tool`

**Estimado:** 3 horas

---

**Fase 1 Total:** ~14 horas | **Reducción:** 4 herramientas

---

### Fase 2: Solapamientos Significativos (Semana 2)

#### [ ] 5. AZDO Tool 3 + 16 + 18 → "Pipeline Health Analyzer"

**Herramientas Actuales:**
- Tool 3: Release CD Health (recencia + estabilidad)
- Tool 16: Pipeline Health Score (DORA metrics)
- Tool 18: Pipeline Status (reporte consolidado)

**Análisis:**
```
Similitud: 75%
Diferencia: Métrica (health vs dora vs status)
Impacto: Consolidación reducirá 2 herramientas
Complejidad: Alta
```

**Pasos:**
- [ ] Revisar código de las 3 herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta "Pipeline Health Analyzer"
- [ ] Agregar opción `--metric` (health|dora|status|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar Tool 16 y 18
- [ ] Commit: `feat: Consolidate pipeline health tools`

**Estimado:** 8 horas

---

#### [ ] 6. AZDO Tool 9 + 14 + 15 → "CICD Inventory"

**Herramientas Actuales:**
- Tool 9: CICD Inventory (básico)
- Tool 14: CI Pipeline Inventory (Detailed)
- Tool 15: CD Pipeline Inventory (Detailed)

**Análisis:**
```
Similitud: 80%
Diferencia: Nivel de detalle
Impacto: Consolidación reducirá 2 herramientas
Complejidad: Alta
```

**Pasos:**
- [ ] Revisar código de las 3 herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta "CICD Inventory"
- [ ] Agregar opción `--detail` (basic|ci-detailed|cd-detailed|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar Tool 14 y 15
- [ ] Commit: `feat: Consolidate CICD inventory tools`

**Estimado:** 8 horas

---

#### [ ] 7. GCP Tool 10 + AWS Tool 6 → "VPC Networks Auditor"

**Herramientas Actuales:**
- GCP Tool 10: VPC Networks Checker
- AWS Tool 6: VPC Networks Checker

**Análisis:**
```
Similitud: 85%
Diferencia: Plataforma (GCP vs AWS)
Impacto: Crear herramienta agnóstica
Complejidad: Media
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta agnóstica "VPC Networks Auditor"
- [ ] Agregar opción `--platform` (gcp|aws|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar GCP Tool 10 y AWS Tool 6
- [ ] Commit: `feat: Create multi-cloud VPC Networks Auditor`

**Estimado:** 6 horas

---

#### [ ] 8. GCP Tool 12 + AWS Tool 8 → "Load Balancer Auditor"

**Herramientas Actuales:**
- GCP Tool 12: Load Balancer Checker
- AWS Tool 8: Load Balancer Checker (ALB/NLB)

**Análisis:**
```
Similitud: 80%
Diferencia: Plataforma (GCP vs AWS)
Impacto: Crear herramienta agnóstica
Complejidad: Media
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta agnóstica "Load Balancer Auditor"
- [ ] Agregar opción `--platform` (gcp|aws|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar GCP Tool 12 y AWS Tool 8
- [ ] Commit: `feat: Create multi-cloud Load Balancer Auditor`

**Estimado:** 6 horas

---

**Fase 2 Total:** ~28 horas | **Reducción:** 6 herramientas

---

### Fase 3: Revisiones Medias (Semana 3)

#### [ ] 9. GCP Tool 3 + AWS Tool 1/2 → "IAM Auditor"

**Herramientas Actuales:**
- GCP Tool 3: Reporte de Roles y Permisos IAM
- AWS Tool 1: IAM Users & Policies Checker
- AWS Tool 2: IAM Roles Checker

**Análisis:**
```
Similitud: 75%
Diferencia: Plataforma (GCP vs AWS)
Impacto: Crear herramienta agnóstica
Complejidad: Media
```

**Pasos:**
- [ ] Revisar código de las 3 herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta agnóstica "IAM Auditor"
- [ ] Agregar opción `--platform` (gcp|aws|all)
- [ ] Agregar opción `--check` (users|roles|policies|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar GCP Tool 3, AWS Tool 1 y 2
- [ ] Commit: `feat: Create multi-cloud IAM Auditor`

**Estimado:** 8 horas

---

#### [ ] 10. GCP Tool 5 + AWS Tool 3 → "Certificate Monitor"

**Herramientas Actuales:**
- GCP Tool 5: Certificate Manager Checker
- AWS Tool 3: ACM Certificate Checker

**Análisis:**
```
Similitud: 85%
Diferencia: Plataforma (GCP vs AWS)
Impacto: Crear herramienta agnóstica
Complejidad: Baja
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta agnóstica "Certificate Monitor"
- [ ] Agregar opción `--platform` (gcp|aws|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar GCP Tool 5 y AWS Tool 3
- [ ] Commit: `feat: Create multi-cloud Certificate Monitor`

**Estimado:** 5 horas

---

#### [ ] 11. GCP Tool 6 + AWS Tool 18 → "WAF Auditor"

**Herramientas Actuales:**
- GCP Tool 6: Cloud Armor Checker
- AWS Tool 18: WAF Web ACL Checker

**Análisis:**
```
Similitud: 80%
Diferencia: Plataforma (GCP vs AWS)
Impacto: Crear herramienta agnóstica
Complejidad: Media
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta agnóstica "WAF Auditor"
- [ ] Agregar opción `--platform` (gcp|aws|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar GCP Tool 6 y AWS Tool 18
- [ ] Commit: `feat: Create multi-cloud WAF Auditor`

**Estimado:** 6 horas

---

#### [ ] 12. AZDO Tool 7 + 8 → "Vulnerability Scanner"

**Herramientas Actuales:**
- Tool 7: Pipeline Logs Scanner
- Tool 8: Repo Vulnerabilities Scanner

**Análisis:**
```
Similitud: 70%
Diferencia: Tipo (logs vs repos)
Impacto: Consolidación reducirá 1 herramienta
Complejidad: Media
```

**Pasos:**
- [ ] Revisar código de ambas herramientas
- [ ] Identificar diferencias funcionales
- [ ] Crear nueva herramienta "Vulnerability Scanner"
- [ ] Agregar opción `--scan` (logs|repos|all)
- [ ] Migrar tests
- [ ] Actualizar documentación
- [ ] Deprecar Tool 8
- [ ] Commit: `feat: Consolidate vulnerability scanners`

**Estimado:** 6 horas

---

**Fase 3 Total:** ~31 horas | **Reducción:** 7 herramientas

---

### Fase 4: Herramientas Faltantes (Semana 4)

#### [ ] 13. GCP: Agregar "Artifact Registry Checker"

**Justificación:** AWS tiene ECR, GCP debe tener equivalente

**Pasos:**
- [ ] Revisar AWS Tool 10 (ECR Repository Checker)
- [ ] Crear GCP equivalente "Artifact Registry Checker"
- [ ] Implementar funcionalidad similar
- [ ] Agregar tests
- [ ] Documentar
- [ ] Commit: `feat: Add GCP Artifact Registry Checker`

**Estimado:** 4 horas

---

#### [ ] 14. GCP: Agregar "Compute Instances Checker"

**Justificación:** AWS tiene EC2, GCP debe tener equivalente

**Pasos:**
- [ ] Revisar AWS Tool 11 (EC2 Instances Checker)
- [ ] Crear GCP equivalente "Compute Instances Checker"
- [ ] Implementar funcionalidad similar
- [ ] Agregar tests
- [ ] Documentar
- [ ] Commit: `feat: Add GCP Compute Instances Checker`

**Estimado:** 4 horas

---

#### [ ] 15. Dashboard: Integrar más métricas de AZDO

**Justificación:** Dashboard solo consolida 5 métricas, podría tener más

**Pasos:**
- [ ] Revisar dashboard_consolidator.py
- [ ] Identificar métricas adicionales disponibles
- [ ] Agregar lectura de JSON adicionales
- [ ] Actualizar dashboard_generator.py
- [ ] Agregar tests
- [ ] Documentar
- [ ] Commit: `feat: Add additional metrics to Dashboard`

**Estimado:** 6 horas

---

**Fase 4 Total:** ~14 horas | **Adiciones:** 3 herramientas

---

## 📊 Resumen de Esfuerzo

| Fase | Tareas | Horas | Reducción | Adiciones |
|------|--------|-------|-----------|-----------|
| **Fase 1** | 4 | 14 | 4 | 0 |
| **Fase 2** | 4 | 28 | 6 | 0 |
| **Fase 3** | 4 | 31 | 7 | 0 |
| **Fase 4** | 3 | 14 | 0 | 3 |
| **TOTAL** | **15** | **87** | **17** | **3** |

---

## 🎯 Impacto Esperado

```
Antes:
- 76 herramientas
- 8 duplicados
- 8 solapamientos
- Mantenibilidad: Baja

Después:
- 62 herramientas (reducción 18%)
- 0 duplicados
- 0 solapamientos
- Mantenibilidad: Alta
- UX: Mejorada (menos opciones confusas)
```

---

## 📝 Notas Importantes

### Deprecación de Herramientas

Cuando depreces una herramienta:

1. **Mantener compatibilidad hacia atrás** por 2 versiones
2. **Mostrar advertencia** al ejecutar herramienta deprecada
3. **Documentar migración** en README
4. **Actualizar tests** para usar nueva herramienta
5. **Comunicar cambio** en release notes

### Testing

Para cada consolidación:

1. **Crear tests** para nueva herramienta
2. **Verificar** que cubre todos los casos de ambas herramientas
3. **Ejecutar tests** de ambas herramientas originales
4. **Verificar** que resultados son equivalentes

### Documentación

Para cada consolidación:

1. **Actualizar README** de la plataforma
2. **Actualizar tools.py** con nueva herramienta
3. **Agregar ejemplos** de uso con nuevas opciones
4. **Documentar deprecación** de herramientas antiguas

---

## ✅ Validación Final

Después de completar todas las fases:

- [ ] Todas las herramientas consolidadas funcionan correctamente
- [ ] No hay duplicados en el código
- [ ] Tests pasan al 100%
- [ ] Documentación está actualizada
- [ ] README refleja cambios
- [ ] Release notes documentan cambios
- [ ] Usuarios notificados de deprecaciones
- [ ] Versión bumped correctamente (patch)

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
