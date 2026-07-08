# 📅 Guía de Auditoría Semanal DevSecOps

**Versión:** 1.0.0  
**Objetivo:** Auditoría completa de seguridad, compliance y governance

---

## 🎯 Resumen Ejecutivo

Auditoría semanal que cubre:
- **Lunes:** Seguridad & IAM
- **Miércoles:** Compliance & Políticas
- **Viernes:** Governance & Reporte

**Tiempo Total:** ~2 horas (distribuidas)

---

## 🔐 LUNES - AUDITORÍA DE SEGURIDAD & IAM

### Objetivo
Validar que el acceso y permisos cumplen con principios de seguridad

### Ejecución

#### Paso 1: Roles y Permisos IAM (15 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [3] - Reporte de Roles y Permisos IAM
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Roles asignados a usuarios específicos (no grupos)
- ✅ Sin roles "Owner" asignados a usuarios
- ✅ Sin roles "Editor" asignados a usuarios
- ✅ Principio de menor privilegio aplicado
- ⚠️ Alertar si hay roles excesivos

**Interpretación DevSecOps:**
```
SI USUARIO CON ROLE "Owner":
├─ Riesgo de seguridad crítico
├─ Cambiar a rol específico
├─ Usar grupos para acceso
├─ Implementar MFA
└─ Auditar acceso anterior

SI USUARIO CON ROLE "Editor":
├─ Riesgo de seguridad alto
├─ Cambiar a rol específico
├─ Usar principio de menor privilegio
├─ Implementar approval process
└─ Documentar razón de acceso

SI GRUPO CON PERMISOS EXCESIVOS:
├─ Revisar miembros del grupo
├─ Reducir permisos del grupo
├─ Crear grupos más específicos
└─ Implementar governance

RECOMENDACIÓN:
├─ Usar Custom Roles para casos específicos
├─ Implementar Conditional Access
├─ Usar Service Accounts para aplicaciones
└─ Revisar trimestralmente
```

---

#### Paso 2: Service Accounts Audit (15 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [4] - Service Account Checker
# Output: json
```

**Qué buscar:**
- ✅ Todas las SAs con descripción clara
- ✅ Keys rotadas < 90 días
- ✅ Sin SAs deshabilitadas sin razón
- ✅ Sin SAs con permisos excesivos
- ⚠️ Alertar si hay anomalías

**Interpretación DevSecOps:**
```
SI SA SIN DESCRIPCIÓN:
├─ Riesgo de governance
├─ Agregar descripción clara
├─ Documentar propósito
└─ Revisar si es necesaria

SI SA CON MÚLTIPLES KEYS:
├─ Riesgo de seguridad
├─ Mantener solo 1-2 keys activas
├─ Rotar keys regularmente
├─ Eliminar keys antiguas
└─ Implementar key rotation policy

SI SA NUNCA USADA:
├─ Riesgo de deuda técnica
├─ Verificar si es necesaria
├─ Considerar eliminar
├─ Documentar razón de inactividad
└─ Revisar logs de acceso

SI SA CON PERMISOS CRÍTICOS:
├─ Revisar principio de menor privilegio
├─ Reducir permisos
├─ Implementar approval process
├─ Auditar acceso
└─ Documentar cambios

RECOMENDACIÓN:
├─ Implementar key rotation automática
├─ Usar Workload Identity cuando sea posible
├─ Auditar acceso mensualmente
└─ Documentar todas las SAs
```

---

#### Paso 3: Cloud Armor Audit (15 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [6] - Cloud Armor Checker
# Proyecto: cpl-corp-cial-prod-17042024
# View: audit
# Output: json
```

**Qué buscar:**
- ✅ Todas las políticas de seguridad activas
- ✅ Cobertura de backends > 95%
- ✅ Reglas actualizadas (< 30 días)
- ✅ Sin reglas duplicadas
- ⚠️ Alertar si hay gaps de cobertura

**Interpretación DevSecOps:**
```
SI BACKEND SIN COBERTURA:
├─ Riesgo de ataque DDoS
├─ Crear política de seguridad
├─ Aplicar a backend
├─ Probar reglas
└─ Documentar cambios

SI REGLA ANTIGUA (> 30 DÍAS):
├─ Posible regla inefectiva
├─ Revisar si sigue siendo necesaria
├─ Actualizar si es necesario
├─ Eliminar si no se usa
└─ Documentar razón

SI MÚLTIPLES REGLAS SIMILARES:
├─ Consolidar reglas
├─ Mejorar eficiencia
├─ Reducir complejidad
└─ Documentar cambios

SI TASA DE BLOQUEO ALTA:
├─ Revisar reglas
├─ Validar falsos positivos
├─ Ajustar umbrales
├─ Comunicar a usuarios
└─ Monitorear impacto

RECOMENDACIÓN:
├─ Implementar WAF rules estándar
├─ Usar threat intelligence
├─ Revisar logs semanalmente
├─ Auditar cambios mensualmente
└─ Documentar todas las reglas
```

---

#### Paso 4: Branch Policies Audit (15 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [2] - Branch Policy Checker
# Output: json
```

**Qué buscar:**
- ✅ Master/main con políticas estrictas
- ✅ Require PR reviews > 1
- ✅ Require successful builds
- ✅ Require passing tests
- ⚠️ Alertar si hay gaps

**Interpretación DevSecOps:**
```
SI RAMA PRINCIPAL SIN POLÍTICAS:
├─ Riesgo de código defectuoso
├─ Implementar políticas
├─ Require PR reviews
├─ Require successful builds
└─ Require passing tests

SI PR REVIEW POLICY < 2:
├─ Riesgo de calidad
├─ Aumentar a 2+ reviewers
├─ Usar code owners
├─ Implementar CODEOWNERS file
└─ Documentar estándares

SI SIN REQUIRE SUCCESSFUL BUILD:
├─ Riesgo de código defectuoso
├─ Habilitar build requirement
├─ Configurar CI pipeline
├─ Implementar quality gates
└─ Documentar estándares

SI SIN REQUIRE PASSING TESTS:
├─ Riesgo de regresiones
├─ Habilitar test requirement
├─ Configurar test suite
├─ Implementar coverage gates
└─ Documentar estándares

RECOMENDACIÓN:
├─ Implementar política estándar
├─ Usar branch protection rules
├─ Require status checks
├─ Require code reviews
├─ Require signed commits
├─ Require up-to-date branches
└─ Auditar cambios mensualmente
```

---

#### Paso 5: Generar Reporte Lunes (10 min)
```bash
cat > outcome/weekly_security_audit_$(date +%Y%m%d).json << 'EOF'
{
  "week": "$(date +%Y-W%V)",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "iam_audit": { /* Resultado Tool 3 */ },
  "service_accounts": { /* Resultado Tool 4 */ },
  "cloud_armor": { /* Resultado Tool 6 */ },
  "branch_policies": { /* Resultado Tool 2 */ },
  "findings": {
    "critical": [ /* Hallazgos críticos */ ],
    "high": [ /* Hallazgos altos */ ],
    "medium": [ /* Hallazgos medios */ ]
  },
  "recommendations": [ /* Recomendaciones */ ]
}
EOF
```

---

## ✅ MIÉRCOLES - AUDITORÍA DE COMPLIANCE & POLÍTICAS

### Objetivo
Validar que la infraestructura cumple con políticas y estándares

### Ejecución

#### Paso 1: Certificados SSL/TLS (15 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [5] - Certificate Manager Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Todos los certificados válidos
- ✅ Certificados con > 30 días de vigencia
- ✅ Sin certificados auto-firmados en producción
- ✅ Algoritmo de encriptación moderno
- ⚠️ Alertar si certificado < 30 días

**Interpretación DevSecOps:**
```
SI CERTIFICADO < 30 DÍAS:
├─ Riesgo de expiración
├─ Renovar inmediatamente
├─ Implementar renovación automática
├─ Configurar alertas
└─ Documentar proceso

SI CERTIFICADO EXPIRADO:
├─ Crítico - Servicio caído
├─ Renovar inmediatamente
├─ Investigar causa raíz
├─ Implementar alertas
└─ Documentar incidente

SI CERTIFICADO AUTO-FIRMADO:
├─ Riesgo de seguridad
├─ Reemplazar con certificado válido
├─ Usar CA confiable
├─ Implementar validación
└─ Documentar cambios

SI ALGORITMO DÉBIL:
├─ Riesgo de seguridad
├─ Actualizar a algoritmo moderno
├─ Usar SHA-256 o superior
├─ Usar RSA 2048+ o ECDSA
└─ Documentar cambios

RECOMENDACIÓN:
├─ Usar Google-managed certificates
├─ Implementar renovación automática
├─ Auditar certificados mensualmente
├─ Usar Certificate Transparency logs
└─ Documentar todas las certs
```

---

#### Paso 2: Cloud Run Security (15 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [29] - Cloud Run Security Auditor
# Proyecto: cpl-corp-cial-prod-17042024
# Severity: critical
# Output: json
```

**Qué buscar:**
- ✅ Todos los servicios con autenticación
- ✅ Sin servicios públicos sin razón
- ✅ Secrets configurados correctamente
- ✅ Imágenes de contenedor seguras
- ⚠️ Alertar si hay vulnerabilidades

**Interpretación DevSecOps:**
```
SI SERVICIO PÚBLICO SIN AUTENTICACIÓN:
├─ Riesgo de acceso no autorizado
├─ Requerir autenticación
├─ Usar Cloud IAM
├─ Documentar razón si es intencional
└─ Auditar acceso

SI SECRETS EN VARIABLES DE ENTORNO:
├─ Riesgo de exposición
├─ Usar Secret Manager
├─ Rotar secrets
├─ Auditar acceso
└─ Documentar cambios

SI IMAGEN CON VULNERABILIDADES:
├─ Riesgo de seguridad
├─ Actualizar imagen
├─ Usar imagen base segura
├─ Escanear imágenes
└─ Implementar scanning automático

SI PERMISOS EXCESIVOS:
├─ Riesgo de escalación de privilegios
├─ Reducir permisos
├─ Usar principio de menor privilegio
├─ Usar Service Accounts específicas
└─ Documentar cambios

RECOMENDACIÓN:
├─ Implementar Binary Authorization
├─ Usar Container Analysis
├─ Auditar servicios mensualmente
├─ Implementar vulnerability scanning
└─ Documentar todas las configuraciones
```

---

#### Paso 3: Pipeline Logs Scanner (15 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [7] - Pipeline Logs Scanner
# Search terms: axios,crypto-js,vulnerable
# Top runs: 50
# Output: json
```

**Qué buscar:**
- ✅ Sin términos de vulnerabilidad en logs
- ✅ Sin dependencias vulnerables
- ✅ Sin credenciales en logs
- ⚠️ Alertar si hay hallazgos

**Interpretación DevSecOps:**
```
SI DEPENDENCIA VULNERABLE ENCONTRADA:
├─ Actualizar dependencia
├─ Revisar changelog
├─ Probar cambios
├─ Desplegar actualización
└─ Documentar cambios

SI CREDENCIAL EN LOGS:
├─ Crítico - Rotar credencial
├─ Revocar acceso anterior
├─ Auditar uso anterior
├─ Implementar secret scanning
└─ Documentar incidente

SI PATRÓN SOSPECHOSO:
├─ Investigar causa
├─ Revisar código fuente
├─ Ejecutar análisis de seguridad
├─ Considerar rollback
└─ Documentar hallazgo

RECOMENDACIÓN:
├─ Implementar secret scanning
├─ Usar dependency scanning
├─ Auditar logs semanalmente
├─ Implementar alertas automáticas
└─ Documentar todas las vulnerabilidades
```

---

#### Paso 4: Repo Vulnerabilities Scanner (15 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [8] - Repo Vulnerabilities Scanner
# Branches: main,develop,master
# Output: json
```

**Qué buscar:**
- ✅ Sin dependencias vulnerables críticas
- ✅ Sin dependencias obsoletas
- ✅ package.json actualizado
- ⚠️ Alertar si hay vulnerabilidades

**Interpretación DevSecOps:**
```
SI VULNERABILIDAD CRÍTICA:
├─ Actualizar dependencia inmediatamente
├─ Revisar changelog
├─ Probar cambios exhaustivamente
├─ Desplegar actualización
└─ Documentar cambios

SI DEPENDENCIA OBSOLETA:
├─ Actualizar a versión moderna
├─ Revisar breaking changes
├─ Actualizar código si es necesario
├─ Probar cambios
└─ Documentar cambios

SI MÚLTIPLES VULNERABILIDADES:
├─ Crear plan de remediation
├─ Priorizar por severidad
├─ Actualizar dependencias
├─ Probar cambios
└─ Documentar plan

RECOMENDACIÓN:
├─ Usar npm audit regularmente
├─ Implementar Dependabot
├─ Auditar dependencias mensualmente
├─ Usar versiones pinned
├─ Documentar todas las dependencias
```

---

#### Paso 5: Generar Reporte Miércoles (10 min)
```bash
cat > outcome/weekly_compliance_audit_$(date +%Y%m%d).json << 'EOF'
{
  "week": "$(date +%Y-W%V)",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "certificates": { /* Resultado Tool 5 */ },
  "cloud_run_security": { /* Resultado Tool 29 */ },
  "pipeline_logs": { /* Resultado Tool 7 */ },
  "repo_vulnerabilities": { /* Resultado Tool 8 */ },
  "findings": {
    "critical": [ /* Hallazgos críticos */ ],
    "high": [ /* Hallazgos altos */ ],
    "medium": [ /* Hallazgos medios */ ]
  },
  "remediation_plan": [ /* Plan de remediación */ ]
}
EOF
```

---

## 📊 VIERNES - AUDITORÍA DE GOVERNANCE & REPORTE

### Objetivo
Validar governance, generar reporte ejecutivo y planificar mejoras

### Ejecución

#### Paso 1: CICD Inventory (15 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [9] - CICD Inventory
# Output: json
```

**Qué buscar:**
- ✅ Todos los repos con CI pipeline
- ✅ Todos los CI pipelines con CD pipeline
- ✅ Sin repos huérfanos
- ✅ Sin pipelines deprecados
- ⚠️ Alertar si hay gaps

**Interpretación DevSecOps:**
```
SI REPO SIN CI:
├─ Riesgo de calidad
├─ Crear CI pipeline
├─ Implementar quality gates
├─ Documentar estándares
└─ Capacitar al equipo

SI CI SIN CD:
├─ Riesgo de deployment manual
├─ Crear CD pipeline
├─ Implementar automatización
├─ Documentar proceso
└─ Capacitar al equipo

SI REPO HUÉRFANO:
├─ Riesgo de deuda técnica
├─ Verificar si es necesario
├─ Considerar deprecar
├─ Documentar razón
└─ Archivar si no se usa

SI PIPELINE DEPRECADO:
├─ Riesgo de confusión
├─ Eliminar pipeline
├─ Documentar razón
├─ Comunicar al equipo
└─ Archivar si es necesario

RECOMENDACIÓN:
├─ Implementar estándares de CI/CD
├─ Usar templates de pipeline
├─ Auditar inventario mensualmente
├─ Documentar todas las pipelines
└─ Capacitar al equipo regularmente
```

---

#### Paso 2: Pipeline Health Score (15 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [16] - Pipeline Health Score
# Output: json
```

**Qué buscar:**
- ✅ Health score > 80 para todas las pipelines
- ✅ Tendencia de mejora
- ✅ Sin pipelines con score < 70
- ⚠️ Alertar si hay regresión

**Interpretación DevSecOps:**
```
SI HEALTH SCORE < 70:
├─ Problemas significativos
├─ Ejecutar Deep Dive
├─ Crear plan de mejora
├─ Asignar recursos
└─ Monitorear progreso

SI TENDENCIA NEGATIVA:
├─ Posible degradación
├─ Investigar causa raíz
├─ Implementar mejoras
├─ Monitorear próximas semanas
└─ Documentar cambios

SI SCORE ESTABLE > 80:
├─ Buen desempeño
├─ Mantener estándares
├─ Continuar monitoreo
├─ Documentar mejores prácticas
└─ Compartir con equipo

RECOMENDACIÓN:
├─ Establecer SLA de health score
├─ Revisar score semanalmente
├─ Implementar mejoras continuas
├─ Documentar tendencias
└─ Comunicar progreso al equipo
```

---

#### Paso 3: Consolidar Hallazgos (15 min)
```bash
# Consolidar todos los hallazgos de la semana
cat > outcome/weekly_security_summary_$(date +%Y%m%d).json << 'EOF'
{
  "week": "$(date +%Y-W%V)",
  "period": "$(date -d 'last monday' +%Y-%m-%d) to $(date +%Y-%m-%d)",
  "summary": {
    "total_findings": 0,
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "by_category": {
    "security": { /* Hallazgos de seguridad */ },
    "compliance": { /* Hallazgos de compliance */ },
    "governance": { /* Hallazgos de governance */ }
  },
  "remediation_status": {
    "completed": [ /* Hallazgos remediados */ ],
    "in_progress": [ /* Hallazgos en progreso */ ],
    "pending": [ /* Hallazgos pendientes */ ]
  },
  "recommendations": [ /* Recomendaciones */ ],
  "next_week_focus": [ /* Enfoque para próxima semana */ ]
}
EOF
```

---

#### Paso 4: Generar Reporte Ejecutivo (15 min)
```bash
cat > outcome/weekly_executive_report_$(date +%Y%m%d).md << 'EOF'
# Reporte Ejecutivo Semanal DevSecOps

**Semana:** $(date +%Y-W%V)  
**Período:** $(date -d 'last monday' +%Y-%m-%d) a $(date +%Y-%m-%d)  
**Generado:** $(date)

## 📊 Resumen

- **Hallazgos Críticos:** X
- **Hallazgos Altos:** Y
- **Hallazgos Medios:** Z
- **Hallazgos Bajos:** W

## 🔴 Hallazgos Críticos

[Listar hallazgos críticos con acciones]

## 🟠 Hallazgos Altos

[Listar hallazgos altos con acciones]

## 📈 Tendencias

[Analizar tendencias de la semana]

## ✅ Remediaciones Completadas

[Listar hallazgos remediados]

## 🎯 Próximos Pasos

[Listar acciones para próxima semana]

## 📞 Escalaciones

[Listar escalaciones si las hay]
EOF
```

---

#### Paso 5: Presentar a Stakeholders (30 min)
```
PRESENTACIÓN VIERNES 15:00:

1. Resumen Ejecutivo (5 min)
   ├─ Hallazgos críticos
   ├─ Tendencias
   └─ Impacto en negocio

2. Detalle Técnico (10 min)
   ├─ Hallazgos por categoría
   ├─ Causa raíz
   └─ Impacto técnico

3. Plan de Remediación (10 min)
   ├─ Acciones completadas
   ├─ Acciones en progreso
   └─ Acciones pendientes

4. Preguntas y Respuestas (5 min)
   ├─ Aclaraciones
   ├─ Prioridades
   └─ Recursos necesarios
```

---

## 📋 Checklist Semanal

### Lunes (Seguridad & IAM)
- [ ] Ejecutar Tool 3 (IAM Roles)
- [ ] Ejecutar Tool 4 (Service Accounts)
- [ ] Ejecutar Tool 6 (Cloud Armor)
- [ ] Ejecutar Tool 2 (Branch Policies)
- [ ] Generar reporte de seguridad
- [ ] Revisar hallazgos críticos

### Miércoles (Compliance & Políticas)
- [ ] Ejecutar Tool 5 (Certificados)
- [ ] Ejecutar Tool 29 (Cloud Run Security)
- [ ] Ejecutar Tool 7 (Pipeline Logs)
- [ ] Ejecutar Tool 8 (Repo Vulnerabilities)
- [ ] Generar reporte de compliance
- [ ] Revisar hallazgos críticos

### Viernes (Governance & Reporte)
- [ ] Ejecutar Tool 9 (CICD Inventory)
- [ ] Ejecutar Tool 16 (Health Score)
- [ ] Consolidar hallazgos
- [ ] Generar reporte ejecutivo
- [ ] Presentar a stakeholders
- [ ] Planificar próxima semana

---

## 🎯 KPIs de Auditoría

| KPI | Target | Frecuencia |
|-----|--------|-----------|
| Hallazgos Críticos | 0 | Semanal |
| Hallazgos Altos | < 5 | Semanal |
| Hallazgos Medios | < 20 | Semanal |
| Remediación Crítica | 100% en 24h | Semanal |
| Remediación Alta | 100% en 1 semana | Semanal |
| Remediación Media | 100% en 2 semanas | Semanal |
| Health Score | > 80 | Semanal |
| Cobertura de Auditoría | 100% | Semanal |

---

**Guía de Auditoría Semanal Completada**  
**Próximo:** Guía de Pre-Deploy Validation
