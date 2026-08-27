# 📊 Guía de Monitoreo DevSecOps - Índice

**Versión:** 1.2.0  
**Fecha:** 27 de Agosto de 2026  
**Última actualización:** 27 de Agosto de 2026 (v1.2.0)  
**Objetivo:** Guía completa de monitoreo multi-cloud (GCP, Azure, AWS, AZDO) con herramientas integradas

---

## 🧭 Cómo Navegar en el DevSecOps Toolbox

El punto de entrada único para todas las herramientas es:

```bash
python scm/main.py
```

Al ejecutar este comando se muestra el **menú principal** con las siguientes opciones:

| Opción | Plataforma | Descripción |
|--------|-----------|-------------|
| **1** | ☁️ GCP (Google Cloud Platform) | Herramientas SRE: monitoreo, IAM, networking, K8s, Cloud Run, inventario |
| **2** | ☁️ AZURE (Azure Cloud Platform) | Herramientas: monitoreo, IAM, AKS, App Service, SQL, networking |
| **3** | ☁️ AWS (Amazon Web Services) | IAM, RDS, VPC, EKS, ECR, EC2, Lambda, CloudWatch |
| **4** | 🔷 AZDO (Azure DevOps) | PRs, políticas de rama, releases, drift, inventario, health score |
| **5** | 🐧 TERMINAL | Scripts shell agnósticos: TLS, DB, K8s deployments |
| **6** | 📊 KPI Analyzer Pro | Análisis KPI, Health Score DORA, Dashboards |
| **Q** | 🚪 Salir | Salir del launcher |

### Ruta de Navegación para Herramientas de Monitoreo

Para llegar a cualquier herramienta de monitoreo, sigue esta ruta:

```
python scm/main.py
    │
    ├─ Selecciona: 1 (GCP)  →  Selecciona el número de herramienta GCP
    ├─ Selecciona: 2 (AZURE) →  Selecciona el número de herramienta Azure
    ├─ Selecciona: 3 (AWS)  →  Selecciona el número de herramienta AWS
    └─ Selecciona: 4 (AZDO) →  Selecciona el número de herramienta AZDO
```

### Tabla de Navegación Rápida — Herramientas de Monitoreo

| Herramienta | Plataforma | Ruta en el Menú |
|-------------|-----------|-----------------|
| Monitoreo de Recursos GCP | GCP | `main.py → 1 (GCP) → 1` |
| GKE Cluster Checker | GCP | `main.py → 1 (GCP) → 14` |
| GKE Node Resources Monitor | GCP | `main.py → 1 (GCP) → 24` |
| GKE Pod Resources Monitor | GCP | `main.py → 1 (GCP) → 25` |
| Certificate Manager Checker | GCP | `main.py → 1 (GCP) → 5` |
| Cloud SQL Disk Monitor | GCP | `main.py → 1 (GCP) → 7` |
| IP Addresses Checker | GCP | `main.py → 1 (GCP) → 13` |
| Cloud Run Health Analyzer | GCP | `main.py → 1 (GCP) → 28` |
| Deployments Off Analyzer | GCP | `main.py → 1 (GCP) → 40` |
| Event Tracker | GCP | `main.py → 1 (GCP) → 39` |
| Pub/Sub Monitor | GCP | `main.py → 1 (GCP) → 41` |
| Release CD Health | AZDO | `main.py → 4 (AZDO) → 3` |
| Pipeline Drift Analyzer | AZDO | `main.py → 4 (AZDO) → 4` |
| CICD Inventory | AZDO | `main.py → 4 (AZDO) → 9` |
| Pending Approvals | AZDO | `main.py → 4 (AZDO) → 11` |
| Pipeline Health Score | AZDO | `main.py → 4 (AZDO) → 16` |
| Pipeline Status | AZDO | `main.py → 4 (AZDO) → 18` |
| IAM Users & Policies Checker | AWS | `main.py → 3 (AWS) → 1` |
| CloudWatch Alarms Checker | AWS | `main.py → 3 (AWS) → 13` |
| CloudWatch Metrics Monitor | AWS | `main.py → 3 (AWS) → 20` |
| AWS Inventory Generator | AWS | `main.py → 3 (AWS) → 19` |

> **💡 Tip:** También puedes ejecutar directamente el launcher de cada plataforma:
> - `python scm/gcp/tools.py` — Herramientas GCP
> - `python scm/azure/tools.py` — Herramientas Azure
> - `python scm/aws/tools.py` — Herramientas AWS
> - `python scm/azdo/tools.py` — Herramientas AZDO

---

## 📚 Documentos Disponibles

### 1. 📋 [Análisis de Herramientas Disponibles](00_ANALISIS_HERRAMIENTAS_DISPONIBLES.md)
**Duración:** 30 min lectura  
**Objetivo:** Entender qué herramientas tenemos y cómo usarlas

**Contenido:**
- ✅ Inventario de herramientas GCP (40+ herramientas)
- ✅ Inventario de 21 herramientas AZDO
- ✅ Matriz de cobertura DevSecOps
- ✅ Escenarios de monitoreo integrado
- ✅ Casos de uso por grupo de herramientas

**Cuándo leer:**
- Primera vez que usas el toolbox
- Necesitas entender capacidades disponibles
- Planificando estrategia de monitoreo

---

### 1b. ☁️ [Análisis de Herramientas AWS](04_ANALISIS_HERRAMIENTAS_AWS.md)
**Duración:** 20 min lectura  
**Objetivo:** Entender herramientas AWS y cómo integrarlas

**Contenido:**
- ✅ Inventario de 19 herramientas AWS
- ✅ Análisis detallado por grupo
- ✅ Matriz de cobertura Multi-Cloud
- ✅ Escenarios de monitoreo AWS
- ✅ Casos de integración Multi-Cloud

**Cuándo leer:**
- Si usas AWS en tu infraestructura
- Necesitas monitoreo multi-cloud
- Planificando auditoría integrada

---

### 2. 📅 [Guía de Monitoreo Diario](01_GUIA_MONITOREO_DIARIO.md)
**Duración:** ~135 minutos/día  
**Objetivo:** Ejecutar monitoreo diario de ambientes multi-cloud

**Contenido:**
- ✅ Monitoreo Matutino (08:00) - 60 min (11 pasos)
- ✅ Monitoreo Vespertino (14:00) - 35 min (9 pasos)
- ✅ Monitoreo Nocturno (22:00) - 40 min (8 pasos)
- ✅ Descripción fundamental de cada monitoreo
- ✅ Qué busca prevenir cada monitoreo
- ✅ Matriz de alertas (Crítica, Alta, Media)
- ✅ Checklist diario detallado (28 pasos)
- ✅ Automatización recomendada
- ✅ Interpretación de resultados

**Herramientas Usadas (25 herramientas):**
- **GCP (10):** Tool 1, 5, 7, 13, 14, 24, 25, 28, 40 — Navegación: `main.py → 1 (GCP) → <tool>`
- **AWS (5):** Tool 1, 5, 13, 15, 19 — Navegación: `main.py → 3 (AWS) → <tool>`
- **AZDO (5):** Tool 3, 4, 9, 11, 18 — Navegación: `main.py → 4 (AZDO) → <tool>`

**Cuándo usar:**
- Todos los días
- Establecer baseline de salud
- Detectar anomalías temprano
- Preparar reportes consolidados
- Auditar cambios diarios

---

### 3. 🔐 [Guía de Auditoría Semanal](02_GUIA_AUDITORIA_SEMANAL.md)
**Duración:** 2 horas/semana  
**Objetivo:** Auditoría completa de seguridad y compliance

**Contenido:**
- ✅ Lunes: Seguridad & IAM (60 min)
- ✅ Miércoles: Compliance & Políticas (60 min)
- ✅ Viernes: Governance & Reporte (60 min)
- ✅ KPIs de auditoría
- ✅ Checklist semanal

**Herramientas Usadas:**
- GCP: Tool 3, 4, 5, 6, 29, 35
- AWS: Tool 1, 2, 3, 6, 7, 14, 17, 18, 19
- AZDO: Tool 2, 7, 8, 9, 16, 18

**Cuándo usar:**
- Todos los lunes, miércoles y viernes
- Auditoría de seguridad
- Validar compliance
- Generar reportes ejecutivos

---

### 4. 🚀 [Guía de Pre-Deploy Validation](03_GUIA_PRE_DEPLOY_VALIDATION.md)
**Duración:** 35 minutos/deployment  
**Objetivo:** Validar que un deployment es seguro

**Contenido:**
- ✅ Fase 1: Validación de Configuración (5 min)
- ✅ Fase 2: Validación de Seguridad (10 min)
- ✅ Fase 3: Validación de Dependencias (10 min)
- ✅ Fase 4: Validación de Calidad (5 min)
- ✅ Fase 5: Aprobación Final (5 min)
- ✅ Fase 6: Deployment (después de aprobación)
- ✅ Rollback Plan

**Herramientas Usadas:**
- GCP: Tool 15, 16, 17, 18, 19, 3, 10
- AWS: Tool 7, 9, 16
- AZDO: Tool 6, 20

**Cuándo usar:**
- Antes de cada deployment a producción
- Validar cambios de código
- Verificar seguridad
- Obtener aprobaciones

---

## 🎯 Matriz de Uso Rápido

### Por Rol

#### 👨‍💼 Gerente/Líder
```
DIARIO:
├─ Revisar Dashboard Matutino (5 min)
└─ Revisar alertas críticas (5 min)

SEMANAL:
├─ Leer reporte de auditoría (15 min)
├─ Revisar KPIs (10 min)
└─ Presentar a stakeholders (30 min)
```

#### 👨‍💻 Ingeniero DevOps
```
DIARIO:
├─ Ejecutar Monitoreo Matutino (25 min)
├─ Ejecutar Monitoreo Vespertino (10 min)
└─ Ejecutar Monitoreo Nocturno (10 min)

SEMANAL:
├─ Ejecutar Auditoría Semanal (120 min)
└─ Consolidar hallazgos (30 min)

POR DEPLOYMENT:
└─ Ejecutar Pre-Deploy Validation (35 min)
```

#### 👨‍💻 Ingeniero de Aplicaciones
```
POR DEPLOYMENT:
├─ Revisar Pre-Deploy Validation (10 min)
├─ Corregir problemas si es necesario (variable)
└─ Obtener aprobación (5 min)

SEMANAL:
└─ Revisar hallazgos de seguridad (15 min)
```

#### 🔐 Ingeniero de Seguridad
```
SEMANAL:
├─ Ejecutar Auditoría de Seguridad (60 min)
├─ Ejecutar Auditoría de Compliance (60 min)
└─ Generar reporte de seguridad (30 min)

MENSUAL:
└─ Revisar tendencias y recomendaciones (60 min)
```

---

### Por Escenario

#### Monitoreo Diario Multi-Cloud
```
Documentos: 01_GUIA_MONITOREO_DIARIO.md
Tiempo: ~135 min/día (Matutino 60 + Vespertino 35 + Nocturno 40)
Herramientas: 25 herramientas (GCP: 10, AWS: 5, AZDO: 5)
Pasos: 28 pasos (Matutino 11 + Vespertino 9 + Nocturno 8)
Frecuencia: Diaria (08:00, 14:00, 22:00)
Nubes: GCP + AWS + AZDO
Reportes: 3 reportes JSON consolidados
```

#### Auditoría Semanal Multi-Cloud
```
Documentos: 02_GUIA_AUDITORIA_SEMANAL.md
Tiempo: 2 horas/semana
Herramientas: 22 herramientas (GCP: 6, AWS: 9, AZDO: 7)
Frecuencia: Semanal (L, M, V)
Nubes: GCP + AWS + AZDO
```

#### Pre-Deploy Validation Multi-Cloud
```
Documentos: 03_GUIA_PRE_DEPLOY_VALIDATION.md
Tiempo: 35 min/deployment
Herramientas: 16 herramientas (GCP: 7, AWS: 3, AZDO: 2)
Frecuencia: Por cada deployment
Nubes: GCP + AWS + AZDO
```

#### Investigación de Incidente
```
Documentos: 00_ANALISIS_HERRAMIENTAS_DISPONIBLES.md (referencia)
Tiempo: Variable
Herramientas: Según el incidente
Frecuencia: Según sea necesario
```

---

## 🚀 Guía de Inicio Rápido

### Día 1: Configuración Inicial Multi-Cloud
```
1. Leer: 00_ANALISIS_HERRAMIENTAS_DISPONIBLES.md (30 min)
2. Leer: 04_ANALISIS_HERRAMIENTAS_AWS.md (20 min)
3. Entender: Qué herramientas tenemos (GCP + AWS + AZDO)
4. Planificar: Estrategia de monitoreo multi-cloud
5. Configurar: Credenciales y acceso (GCP, AWS, AZDO)
```

### Día 2: Monitoreo Matutino Multi-Cloud
```
1. Leer: 01_GUIA_MONITOREO_DIARIO.md - Sección Matutino (10 min)
2. Ejecutar: GCP Tools (1, 5, 7, 13, 14, 28) (30 min)
3. Ejecutar: AWS Tools (1, 13) (10 min)
4. Ejecutar: AZDO Tools (18, 3) (10 min)
5. Generar: Dashboard Matutino Multi-Cloud
6. Revisar: Alertas críticas
7. Documentar: Hallazgos en reporte
```

### Día 3: Monitoreo Completo Multi-Cloud
```
1. Ejecutar: Monitoreo Matutino (60 min)
   - GCP: Tool 1, 5, 7, 13, 14, 28
   - AWS: Tool 1, 13
   - AZDO: Tool 18, 3
   
2. Ejecutar: Monitoreo Vespertino (35 min)
   - GCP: Tool 25, 24, 7, 13, 40
   - AWS: Tool 5, 15
   - AZDO: Tool 11
   
3. Ejecutar: Monitoreo Nocturno (40 min)
   - GCP: Tool 4, 8, 28
   - AWS: Tool 1, 19
   - AZDO: Tool 9, 4
   
4. Consolidar: 3 reportes diarios multi-cloud
5. Revisar: Anomalías y cambios del día
```

### Semana 1: Auditoría Semanal Multi-Cloud
```
1. Lunes: Auditoría de Seguridad & IAM (60 min)
   - GCP: Tool 3, 4, 6
   - AWS: Tool 1, 2, 3
   - AZDO: Tool 2

2. Miércoles: Auditoría de Compliance (60 min)
   - GCP: Tool 5, 29
   - AWS: Tool 6, 7, 14, 17, 18
   - AZDO: Tool 7, 8

3. Viernes: Governance & Reporte (60 min)
   - GCP: Tool 35
   - AWS: Tool 19
   - AZDO: Tool 9, 16, 18
   - Consolidar: Reporte ejecutivo multi-cloud
```

### Deployment: Pre-Deploy Validation Multi-Cloud
```
1. Leer: 03_GUIA_PRE_DEPLOY_VALIDATION.md (10 min)
2. Validación GCP (15 min)
   - Tool 15, 16, 17, 18, 19, 3, 10
3. Validación AWS (10 min)
   - Tool 7, 9, 16
4. Validación AZDO (10 min)
   - Tool 6, 20
5. Obtener: Aprobación Final (5 min)
6. Ejecutar: Deployment Multi-Cloud
```

---

## 📊 Herramientas por Documento

### 00_ANALISIS_HERRAMIENTAS_DISPONIBLES.md
- GCP: Todas (1-38)
- AWS: Todas (1-19)
- AZDO: Todas (1-25)

### 01_GUIA_MONITOREO_DIARIO.md
- GCP: 1, 5, 7, 13, 14, 24, 25, 28, 40 (10 herramientas)
- AWS: 1, 5, 13, 15, 19 (5 herramientas)
- AZDO: 3, 4, 9, 11, 18 (5 herramientas)
- **Total: 25 herramientas**

### 02_GUIA_AUDITORIA_SEMANAL.md
- GCP: 3, 4, 5, 6, 29, 35
- AWS: 1, 2, 3, 6, 7, 14, 17, 18, 19
- AZDO: 2, 7, 8, 9, 16, 18

### 03_GUIA_PRE_DEPLOY_VALIDATION.md
- GCP: 3, 10, 15, 16, 17, 18, 19
- AWS: 7, 9, 16
- AZDO: 6, 20

### 04_ANALISIS_HERRAMIENTAS_AWS.md
- AWS: Todas (1-19)

---

## 🎯 KPIs de Monitoreo

| KPI | Target | Frecuencia | Documento |
|-----|--------|-----------|-----------|
| Hallazgos Críticos | 0 | Semanal | 02 |
| Hallazgos Altos | < 5 | Semanal | 02 |
| Health Score | > 80 | Semanal | 02 |
| CI Success Rate | > 90% | Diaria | 01 |
| CD Success Rate | > 95% | Diaria | 01 |
| Deployment Success | 100% | Por deploy | 03 |
| Pre-Deploy Validation Pass | 100% | Por deploy | 03 |

---

## 📞 Escalación

### Alertas Críticas
```
Severidad: 🔴 CRITICAL
Tiempo: Inmediato
Acción: Llamar al on-call
Documento: 01 (Matriz de Alertas)
```

### Alertas Altas
```
Severidad: 🟠 HIGH
Tiempo: 15 minutos
Acción: Slack + email
Documento: 01 (Matriz de Alertas)
```

### Hallazgos de Auditoría
```
Severidad: 🟡 MEDIUM
Tiempo: 24 horas
Acción: Ticket + plan de remediación
Documento: 02 (Auditoría Semanal)
```

---

## 🤖 Automatización

### Scripts Recomendados

#### daily_monitoring.sh
```bash
#!/bin/bash
# Ejecutar monitoreo diario automáticamente

# 08:00 - Monitoreo Matutino
0 8 * * * /path/to/morning_monitoring.sh

# 14:00 - Monitoreo Vespertino
0 14 * * * /path/to/afternoon_monitoring.sh

# 22:00 - Monitoreo Nocturno
0 22 * * * /path/to/night_monitoring.sh
```

#### weekly_audit.sh
```bash
#!/bin/bash
# Ejecutar auditoría semanal automáticamente

# Lunes 09:00 - Auditoría de Seguridad
0 9 * * 1 /path/to/security_audit.sh

# Miércoles 09:00 - Auditoría de Compliance
0 9 * * 3 /path/to/compliance_audit.sh

# Viernes 14:00 - Governance & Reporte
0 14 * * 5 /path/to/governance_report.sh
```

---

## 📈 Mejora Continua

### Cada Semana
- [ ] Revisar hallazgos de auditoría
- [ ] Implementar recomendaciones
- [ ] Actualizar documentación
- [ ] Capacitar al equipo

### Cada Mes
- [ ] Revisar KPIs
- [ ] Analizar tendencias
- [ ] Planificar mejoras
- [ ] Revisar procesos

### Cada Trimestre
- [ ] Auditoría completa
- [ ] Revisión de políticas
- [ ] Actualización de estándares
- [ ] Planificación estratégica

---

## 📚 Referencias

### Documentos Relacionados
- `operation/monitoring/00_ANALISIS_HERRAMIENTAS_DISPONIBLES.md`
- `operation/monitoring/01_GUIA_MONITOREO_DIARIO.md`
- `operation/monitoring/02_GUIA_AUDITORIA_SEMANAL.md`
- `operation/monitoring/03_GUIA_PRE_DEPLOY_VALIDATION.md`
- `operation/monitoring/04_ANALISIS_HERRAMIENTAS_AWS.md`

### Herramientas GCP
- `scm/gcp/tools.py` - Launcher de herramientas GCP
- `scm/gcp/monitoring/` - Scripts de monitoreo
- `scm/gcp/rolesypermisos/` - Scripts de IAM

### Herramientas AWS
- `scm/aws/tools.py` - Launcher de herramientas AWS
- `scm/aws/` - Scripts de AWS

### Herramientas AZDO
- `scm/azdo/tools.py` - Launcher de herramientas AZDO
- `scm/azdo/` - Scripts de AZDO

### Configuración
- `scm/config.json` - Configuración centralizada
- `scm/config.json.template` - Template de configuración

---

## 🆘 Soporte

### Problemas Comunes

#### Herramienta no funciona
```
1. Revisar credenciales en config.json
2. Verificar permisos de acceso
3. Revisar logs de error
4. Ejecutar con --debug
5. Contactar al equipo de infraestructura
```

#### Alertas falsas
```
1. Revisar umbral de alerta
2. Validar métrica
3. Ajustar alerta si es necesario
4. Documentar cambio
5. Comunicar al equipo
```

#### Deployment fallido
```
1. Revisar logs de deployment
2. Ejecutar Pre-Deploy Validation nuevamente
3. Considerar rollback
4. Investigar causa raíz
5. Documentar incidente
```

---

## 📞 Contacto

Para preguntas o sugerencias sobre esta guía:
- 📧 Email: devsecops@empresa.com
- 💬 Slack: #devsecops-monitoring
- 📋 Issues: GitHub Issues

---

**Guía de Monitoreo DevSecOps v1.2.0**  
**Última actualización:** 27 de Agosto de 2026  
**Cambios en v1.2.0:**
- ✅ Agregada sección "Cómo Navegar en el DevSecOps Toolbox" con tabla de navegación rápida
- ✅ Agregada tabla de navegación rápida para todas las herramientas de monitoreo
- ✅ Actualizadas referencias a Tool 21 (removida del AZDO)
- ✅ Actualizado conteo de herramientas AZDO (25 → 21)
- ✅ Corregidos paths de documentos (`docs/monitoring/` → `operation/monitoring/`)
- ✅ Agregada plataforma Azure Cloud (opción 2 del menú principal)

**Cambios en v1.1.0:**
- ✅ Agregadas 8 herramientas GCP nuevas (5, 7, 8, 13, 28, 40)
- ✅ Agregada herramienta AWS Tool 19 (AWS Inventory)
- ✅ Agregada herramienta AZDO Tool 4 (Pipeline Drift)
- ✅ Actualizado Monitoreo Matutino: 25 min → 60 min (11 pasos)
- ✅ Actualizado Monitoreo Vespertino: 10 min → 35 min (9 pasos)
- ✅ Actualizado Monitoreo Nocturno: 10 min → 40 min (8 pasos)

**Próxima revisión:** 27 de Noviembre de 2026
