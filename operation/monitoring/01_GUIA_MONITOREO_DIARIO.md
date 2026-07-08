# 📅 Guía de Monitoreo Diario DevSecOps

**Versión:** 1.0.0  
**Objetivo:** Ejecutar monitoreo diario de ambientes GCP y AZDO con interpretación DevSecOps

---

## 🎯 Resumen Ejecutivo

Este documento proporciona un **plan diario de monitoreo** que debe ejecutarse en tres momentos:
- **08:00 - Monitoreo Matutino** (Baseline de salud)
- **14:00 - Monitoreo Vespertino** (Anomalías)
- **22:00 - Monitoreo Nocturno** (Cambios y auditoría)

**Tiempo Total:** ~45 minutos (automatizable)

---

## 📊 MONITOREO MATUTINO (08:00)

### Objetivo
Establecer baseline de salud de infraestructura y pipelines (GCP, AWS, AZDO)

### Ejecución

#### Paso 1: Recursos GCP (5 min)
```bash
# Terminal 1: Monitoreo de recursos GCP
cd scm/gcp
python tools.py
# Seleccionar [1] - Monitoreo de Recursos GCP
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ CPU promedio < 70%
- ✅ Memoria promedio < 80%
- ✅ Disco disponible > 20%
- ⚠️ Alertar si alguno > 85%

**Interpretación DevSecOps:**
```
SI CPU > 85%:
├─ Posible ataque DDoS
├─ Aplicación con memory leak
└─ Necesario escalado horizontal

SI MEMORIA > 85%:
├─ Posible memory leak en aplicación
├─ Necesario aumentar recursos
└─ Revisar logs de aplicación

SI DISCO > 90%:
├─ Crítico - Riesgo de caída
├─ Limpiar logs/datos temporales
└─ Aumentar capacidad inmediatamente
```

---

#### Paso 2: Clusters GKE (5 min)
```bash
# Terminal 2: Monitoreo de clusters GKE
cd scm/gcp
python tools.py
# Seleccionar [14] - GKE Cluster Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Todos los nodos en estado "Ready"
- ✅ Versión de Kubernetes actualizada
- ✅ Pods corriendo > 95%
- ⚠️ Alertar si hay nodos NotReady

**Interpretación DevSecOps:**
```
SI NODO NotReady:
├─ Posible fallo de hardware
├─ Revisar logs del nodo
├─ Considerar recrear nodo
└─ Escalar a infraestructura

SI PODS PENDING > 5%:
├─ Posible falta de recursos
├─ Revisar requests/limits
├─ Considerar escalado
└─ Revisar eventos del cluster

SI VERSIÓN DESACTUALIZADA:
├─ Riesgo de seguridad
├─ Planificar actualización
└─ Revisar breaking changes
```

---

#### Paso 3: Pipeline Status AZDO (5 min)
```bash
# Terminal 3: Estado de pipelines
cd scm/azdo
python tools.py
# Seleccionar [18] - Pipeline Status
# Output: json
```

**Qué buscar:**
- ✅ CI pipelines: success rate > 90%
- ✅ CD pipelines: success rate > 95%
- ✅ Pipelines activos > 80%
- ⚠️ Alertar si success rate < 80%

**Interpretación DevSecOps:**
```
SI CI SUCCESS < 90%:
├─ Problemas en código o tests
├─ Revisar últimos commits
├─ Ejecutar Tool 7 (Pipeline Logs Scanner)
└─ Notificar al equipo de desarrollo

SI CD SUCCESS < 95%:
├─ Problemas en deployment
├─ Ejecutar Tool 5 (Release Deep Dive)
├─ Revisar configuración de release
└─ Considerar rollback

SI PIPELINES INACTIVOS > 20%:
├─ Posible deuda técnica
├─ Revisar si son necesarios
├─ Considerar deprecar
└─ Documentar razón de inactividad
```

---

#### Paso 4: Release Health (5 min)
```bash
# Terminal 4: Salud de releases
cd scm/azdo
python tools.py
# Seleccionar [3] - Release CD Health
# Output: json
```

**Qué buscar:**
- ✅ Health score > 80
- ✅ Releases recientes (últimas 7 días)
- ✅ Estabilidad > 90%
- ⚠️ Alertar si score < 70

**Interpretación DevSecOps:**
```
SI HEALTH SCORE < 70:
├─ Releases inestables
├─ Ejecutar Tool 5 (Release Deep Dive)
├─ Revisar cambios recientes
├─ Considerar rollback
└─ Implementar quality gates

SI ESTABILIDAD < 90%:
├─ Demasiados fallos
├─ Revisar configuración
├─ Aumentar testing
└─ Implementar canary deployments

SI SIN RELEASES RECIENTES:
├─ Posible bloqueo en pipeline
├─ Revisar aprobaciones pendientes
├─ Ejecutar Tool 11 (Pending Approvals)
└─ Desbloquear si es seguro
```

---

#### Paso 5: Monitoreo AWS (5 min)
```bash
# Terminal 5: Monitoreo de AWS
cd scm/aws
python tools.py
# Seleccionar [1] - IAM Users & Policies Checker
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Todos los usuarios con MFA habilitado
- ✅ Sin access keys > 90 días
- ✅ Roles con permisos correctos
- ⚠️ Alertar si hay usuarios sin MFA

**Interpretación DevSecOps:**
```
SI USUARIO SIN MFA:
├─ Riesgo de seguridad crítico
├─ Habilitar MFA inmediatamente
├─ Usar hardware keys si es posible
└─ Auditar acceso anterior

SI ACCESS KEY > 90 DÍAS:
├─ Riesgo de seguridad
├─ Rotar key inmediatamente
└─ Implementar key rotation policy
```

Luego ejecutar:
```bash
# Seleccionar [13] - CloudWatch Alarms Checker
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Todas las alarmas activas
- ✅ Sin alarmas en estado ALARM
- ⚠️ Alertar si hay alarmas fallando

---

#### Paso 6: Generar Dashboard Matutino (5 min)
```bash
# Consolidar resultados
cat > outcome/daily_morning_report_$(date +%Y%m%d).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gcp_resources": { /* Resultado Tool 1 */ },
  "gke_clusters": { /* Resultado Tool 14 */ },
  "aws_iam": { /* Resultado AWS Tool 1 */ },
  "aws_cloudwatch": { /* Resultado AWS Tool 13 */ },
  "azdo_pipeline_status": { /* Resultado Tool 18 */ },
  "azdo_release_health": { /* Resultado Tool 3 */ },
  "alerts": [ /* Alertas críticas */ ]
}
EOF
```

**Salida esperada:**
```
✅ MONITOREO MATUTINO COMPLETADO
├─ GCP Resources: OK (CPU 45%, Mem 62%, Disk 35%)
├─ GKE Clusters: OK (3 nodos Ready, 150 pods running)
├─ AWS IAM: OK (Todos con MFA, keys < 90 días)
├─ AWS CloudWatch: OK (Todas las alarmas activas)
├─ Pipeline Status: OK (CI 92%, CD 96%)
├─ Release Health: OK (Score 85)
└─ Alertas: 0 críticas

Reporte guardado: outcome/daily_morning_report_20260708.json
```

---

## 📊 MONITOREO VESPERTINO (14:00)

### Objetivo
Detectar anomalías y problemas que surgieron durante el día

### Ejecución

#### Paso 1: Pods con Alto Uso (5 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [25] - GKE Pod Resources Monitor
# Proyecto: cpl-corp-cial-prod-17042024
# Namespace: production
# Sort: cpu
# Top: 10
# Output: json
```

**Qué buscar:**
- ✅ Pods con CPU < 80%
- ✅ Pods con memoria < 85%
- ⚠️ Alertar si alguno > 90%

**Interpretación DevSecOps:**
```
SI POD CPU > 90%:
├─ Posible ataque o carga anormal
├─ Revisar logs del pod
├─ Considerar HPA (Horizontal Pod Autoscaler)
├─ Revisar código de aplicación
└─ Escalar si es legítimo

SI POD MEMORIA > 90%:
├─ Memory leak probable
├─ Reiniciar pod
├─ Revisar código de aplicación
├─ Aumentar límite de memoria
└─ Monitorear próximas horas

SI MÚLTIPLES PODS AFECTADOS:
├─ Problema sistémico
├─ Revisar cambios recientes
├─ Ejecutar Tool 4 (Pipeline Drift Analyzer)
├─ Considerar rollback
└─ Escalar a equipo de infraestructura
```

---

#### Paso 2: Aprobaciones Pendientes (3 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [11] - Pending Approvals
# Output: json
```

**Qué buscar:**
- ✅ Sin aprobaciones pendientes
- ⚠️ Alertar si > 3 aprobaciones pendientes
- ⚠️ Alertar si pendiente > 4 horas

**Interpretación DevSecOps:**
```
SI APROBACIÓN PENDIENTE > 4 HORAS:
├─ Posible bloqueo de release
├─ Contactar a aprobador
├─ Revisar si es crítico
├─ Considerar escalación
└─ Documentar razón de retraso

SI MÚLTIPLES APROBACIONES PENDIENTES:
├─ Posible cuello de botella
├─ Revisar proceso de aprobación
├─ Considerar automatizar
├─ Aumentar número de aprobadores
└─ Implementar SLA de aprobación
```

---

#### Paso 3: Anomalías de Recursos (5 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [24] - GKE Node Resources Monitor
# Proyecto: cpl-corp-cial-prod-17042024
# Output: html
```

**Qué buscar:**
- ✅ Distribución uniforme de carga entre nodos
- ⚠️ Alertar si algún nodo > 85%
- ⚠️ Alertar si distribución desigual > 30%

**Interpretación DevSecOps:**
```
SI NODO > 85%:
├─ Posible pod mal distribuido
├─ Revisar afinidad de pods
├─ Considerar rebalanceo
└─ Escalar nodo si es necesario

SI DISTRIBUCIÓN DESIGUAL:
├─ Posible problema de scheduling
├─ Revisar node selectors
├─ Revisar pod disruption budgets
├─ Considerar pod affinity rules
└─ Ejecutar rebalanceo manual

SI NODO NUEVO CON BAJO USO:
├─ Posible nodo recién agregado
├─ Esperar a que se estabilice
├─ Revisar si hay pods pendientes
└─ Considerar drenar nodos antiguos
```

---

#### Paso 4: Deployments No Running (5 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [40] - Deployments Off Analyzer
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: prod-gke-cluster
# Namespace: production
# Output: json
```

**Qué buscar:**
- ✅ Sin deployments en estado no running
- ⚠️ Alertar si hay deployments con replicas < desired
- ⚠️ Alertar si severidad = CRITICAL

**Interpretación DevSecOps:**
```
SI DEPLOYMENT NO RUNNING:
├─ Causa raíz identificada automáticamente
├─ Revisar recomendaciones generadas
├─ Ejecutar acciones recomendadas
├─ Monitorear recuperación
└─ Documentar incidente

SI SEVERIDAD CRITICAL:
├─ Escalar inmediatamente
├─ Ejecutar kubectl logs para más detalles
├─ Considerar rollback si es reciente
├─ Notificar al equipo de aplicaciones
└─ Crear ticket de incidente

CAUSAS COMUNES:
├─ ImagePullBackOff → Verificar registry
├─ CrashLoopBackOff → Revisar logs
├─ Pending → Escalar cluster
├─ ConfigError → Verificar Secrets/ConfigMaps
└─ FailedScheduling → Recursos insuficientes
```

---

#### Paso 5: Monitoreo AWS Vespertino (3 min)
```bash
cd scm/aws
python tools.py
# Seleccionar [5] - RDS Storage Monitor
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Almacenamiento RDS < 80%
- ⚠️ Alertar si > 85%

Luego:
```bash
# Seleccionar [15] - EKS Pod Monitor
# Profile: default
# Cluster: [nombre del cluster]
# Output: json
```

**Qué buscar:**
- ✅ Pods con CPU < 80%
- ✅ Pods con memoria < 85%
- ⚠️ Alertar si alguno > 90%

---

#### Paso 5: Generar Reporte Vespertino (2 min)
```bash
cat > outcome/daily_afternoon_report_$(date +%Y%m%d).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gcp_pod_resources": { /* Resultado GCP Tool 25 */ },
  "aws_rds_storage": { /* Resultado AWS Tool 5 */ },
  "aws_eks_pods": { /* Resultado AWS Tool 15 */ },
  "pending_approvals": { /* Resultado AZDO Tool 11 */ },
  "node_resources": { /* Resultado GCP Tool 24 */ },
  "anomalies": [ /* Anomalías detectadas */ ],
  "actions_taken": [ /* Acciones tomadas */ ]
}
EOF
```

---

## 📊 MONITOREO NOCTURNO (22:00)

### Objetivo
Auditar cambios del día y preparar reporte para mañana

### Ejecución

#### Paso 1: Service Accounts (5 min)
```bash
cd scm/gcp
python tools.py
# Seleccionar [4] - Service Account Checker
# Output: json
```

**Qué buscar:**
- ✅ Todas las SAs con keys activas < 90 días
- ✅ Sin SAs deshabilitadas
- ⚠️ Alertar si key > 90 días
- ⚠️ Alertar si SA deshabilitada

**Interpretación DevSecOps:**
```
SI KEY > 90 DÍAS:
├─ Riesgo de seguridad
├─ Rotación de keys necesaria
├─ Generar nueva key
├─ Actualizar aplicación
└─ Eliminar key antigua

SI SA DESHABILITADA:
├─ Verificar si es intencional
├─ Si no, habilitar inmediatamente
├─ Auditar acceso anterior
└─ Documentar razón de deshabilitación

SI SA CON PERMISOS EXCESIVOS:
├─ Revisar principio de menor privilegio
├─ Reducir permisos
├─ Crear SA específica si es necesario
└─ Documentar cambios
```

---

#### Paso 2: Inventario CICD (5 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [9] - CICD Inventory
# Output: json
```

**Qué buscar:**
- ✅ Todos los repos con CI pipeline
- ✅ Todos los CI pipelines con CD pipeline
- ⚠️ Alertar si repo sin CI
- ⚠️ Alertar si CI sin CD

**Interpretación DevSecOps:**
```
SI REPO SIN CI:
├─ Riesgo de calidad
├─ Crear CI pipeline
├─ Implementar quality gates
└─ Documentar estándares

SI CI SIN CD:
├─ Riesgo de deployment manual
├─ Crear CD pipeline
├─ Implementar automatización
└─ Documentar proceso

SI REPO OBSOLETO:
├─ Verificar si es necesario
├─ Considerar deprecar
├─ Documentar razón
└─ Archivar si no se usa
```

---

#### Paso 3: Cambios y Drift (5 min)
```bash
cd scm/azdo
python tools.py
# Seleccionar [4] - Pipeline Drift Analyzer
# Output: json
```

**Qué buscar:**
- ✅ Sin drift en pipelines
- ⚠️ Alertar si drift MEDIUM
- ⚠️ Alertar si drift CRITICAL

**Interpretación DevSecOps:**
```
SI DRIFT CRITICAL:
├─ Cambios no autorizados
├─ Investigar inmediatamente
├─ Ejecutar Tool 5 (Release Deep Dive)
├─ Considerar rollback
└─ Implementar change control

SI DRIFT MEDIUM:
├─ Cambios menores
├─ Revisar si son intencionales
├─ Documentar cambios
├─ Actualizar snapshot
└─ Implementar approval process

SI DRIFT RECURRENTE:
├─ Posible falta de governance
├─ Implementar change control
├─ Aumentar auditoría
├─ Capacitar al equipo
└─ Considerar automatización
```

---

#### Paso 4: Auditoría AWS Nocturna (5 min)
```bash
cd scm/aws
python tools.py
# Seleccionar [1] - IAM Users & Policies Checker
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Todos los usuarios con MFA
- ✅ Sin access keys > 90 días
- ⚠️ Alertar si hay cambios

Luego:
```bash
# Seleccionar [19] - AWS Inventory Generator
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Inventario completo de recursos
- ✅ Identificar recursos huérfanos
- ⚠️ Alertar si hay cambios

---

#### Paso 5: Generar Reporte Nocturno (5 min)
```bash
cat > outcome/daily_night_report_$(date +%Y%m%d).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gcp_service_accounts": { /* Resultado GCP Tool 4 */ },
  "aws_iam_audit": { /* Resultado AWS Tool 1 */ },
  "aws_inventory": { /* Resultado AWS Tool 19 */ },
  "cicd_inventory": { /* Resultado AZDO Tool 9 */ },
  "pipeline_drift": { /* Resultado AZDO Tool 4 */ },
  "security_findings": [ /* Hallazgos de seguridad */ ],
  "recommendations": [ /* Recomendaciones */ ]
}
EOF
```

---

## 🔧 HERRAMIENTAS GCP DISPONIBLES

### Tool 5: Certificate Manager Checker (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [5]  
**Objetivo:** Monitorea certificados SSL/TLS en Certificate Manager

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [5] - Certificate Manager Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Todos los certificados válidos
- ✅ Certificados con validez > 30 días
- ✅ Sin certificados expirados
- ⚠️ Alertar si certificado vence < 30 días
- ⚠️ Alertar si certificado expirado

**Interpretación DevSecOps:**
```
SI CERTIFICADO VENCE < 30 DÍAS:
├─ Riesgo de interrupción de servicio
├─ Renovar certificado inmediatamente
├─ Validar en staging primero
├─ Planificar rotación
└─ Documentar cambios

SI CERTIFICADO EXPIRADO:
├─ Crítico - Acción inmediata
├─ Reemplazar certificado
├─ Verificar servicios afectados
├─ Notificar a stakeholders
├─ Implementar alertas automáticas
└─ Documentar incidente

SI MÚLTIPLES CERTIFICADOS VENCIENDO:
├─ Problema de governance
├─ Implementar sistema de alertas
├─ Crear proceso de renovación
├─ Automatizar si es posible
└─ Capacitar al equipo
```

---

### Tool 7: Cloud SQL Disk Monitor (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [7]  
**Objetivo:** Monitorea uso de disco en instancias Cloud SQL

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [7] - Cloud SQL Disk Monitor
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Uso de disco < 70%
- ✅ Crecimiento de disco predecible
- ✅ Sin alertas de espacio
- ⚠️ Alertar si uso > 80%
- ⚠️ Alertar si crecimiento anómalo

**Interpretación DevSecOps:**
```
SI USO > 80%:
├─ Riesgo de agotamiento
├─ Revisar tamaño de base de datos
├─ Considerar limpieza de datos
├─ Aumentar almacenamiento
├─ Monitorear próximas horas
└─ Implementar políticas de retención

SI CRECIMIENTO ANÓMALO:
├─ Posible fuga de datos
├─ Revisar logs de aplicación
├─ Ejecutar análisis de tablas
├─ Identificar tabla problemática
├─ Implementar solución
└─ Documentar causa raíz

SI ESPACIO CRÍTICO:
├─ Acción inmediata
├─ Aumentar almacenamiento
├─ Revisar backups
├─ Notificar a stakeholders
├─ Implementar alertas
└─ Documentar incidente
```

---

### Tool 8: Cloud SQL Database Checker (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [8]  
**Objetivo:** Lista bases de datos por instancia de Cloud SQL

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [8] - Cloud SQL Database Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Todas las bases de datos documentadas
- ✅ Sin bases de datos huérfanas
- ✅ Permisos de acceso correctos
- ⚠️ Alertar si base de datos desconocida
- ⚠️ Alertar si permisos excesivos

**Interpretación DevSecOps:**
```
SI BASE DE DATOS DESCONOCIDA:
├─ Investigar origen
├─ Verificar si es necesaria
├─ Revisar permisos de acceso
├─ Considerar eliminar si no se usa
└─ Documentar propósito

SI PERMISOS EXCESIVOS:
├─ Riesgo de seguridad
├─ Revisar principio de menor privilegio
├─ Reducir permisos
├─ Crear usuario específico si es necesario
├─ Validar funcionamiento
└─ Documentar cambios

SI MÚLTIPLES BASES DE DATOS:
├─ Revisar consolidación
├─ Evaluar si se pueden combinar
├─ Considerar separación por ambiente
├─ Documentar arquitectura
└─ Implementar políticas de naming
```

---

### Tool 13: IP Addresses Checker (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [13]  
**Objetivo:** Analiza capacidad de red de clusters GKE (IPs de pods y servicios)

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [13] - IP Addresses Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: prod-gke-cluster
# Region: us-central1
# Output: json
```

**Qué buscar:**
- ✅ Disponibilidad de IPs > 30%
- ✅ Sin agotamiento de IPs
- ✅ Distribución uniforme entre subnets
- ⚠️ Alertar si disponibilidad < 20%
- ⚠️ Alertar si agotamiento próximo

**Interpretación DevSecOps:**
```
SI DISPONIBILIDAD < 20%:
├─ Riesgo de agotamiento
├─ Planificar expansión de CIDR
├─ Revisar uso de IPs
├─ Considerar IP secundarias
└─ Escalar a infraestructura

SI AGOTAMIENTO PRÓXIMO:
├─ Crítico - Acción inmediata
├─ Expandir rango de IPs
├─ Revisar pods innecesarios
├─ Considerar consolidación
└─ Implementar IP management policy

SI DISTRIBUCIÓN DESIGUAL:
├─ Posible problema de scheduling
├─ Revisar node selectors
├─ Revisar pod affinity
├─ Rebalancear si es necesario
└─ Monitorear próximas horas
```

---

### Tool 14: GKE Cluster Checker (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [14]  
**Objetivo:** Monitorea clusters GKE, versiones, nodos y pods

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [14] - GKE Cluster Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Todos los nodos en estado "Ready"
- ✅ Versión de Kubernetes actualizada
- ✅ Pods corriendo > 95%
- ✅ Sin nodos NotReady
- ⚠️ Alertar si nodo NotReady
- ⚠️ Alertar si versión desactualizada

**Interpretación DevSecOps:**
```
SI NODO NotReady:
├─ Posible fallo de hardware
├─ Revisar logs del nodo: kubectl describe node
├─ Ejecutar kubectl logs para detalles
├─ Considerar recrear nodo
├─ Escalar a infraestructura
└─ Documentar incidente

SI PODS PENDING > 5%:
├─ Posible falta de recursos
├─ Ejecutar Tool 24 (Node Resources Monitor)
├─ Revisar requests/limits
├─ Considerar escalado
├─ Revisar eventos: kubectl get events
└─ Ejecutar Tool 40 (Deployments Off Analyzer)

SI VERSIÓN DESACTUALIZADA:
├─ Riesgo de seguridad
├─ Planificar actualización
├─ Revisar breaking changes
├─ Validar en staging
├─ Ejecutar en ventana de mantenimiento
└─ Documentar cambios

SI MÚLTIPLES PROBLEMAS:
├─ Problema sistémico
├─ Ejecutar diagnóstico completo
├─ Revisar cambios recientes
├─ Considerar rollback
└─ Escalar a equipo de infraestructura
```

---

### Tool 24: GKE Node Resources Monitor (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [24]  
**Objetivo:** Monitorea recursos de nodos GKE (CPU, memoria, disco)

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [24] - GKE Node Resources Monitor
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: prod-gke-cluster
# Output: html
```

**Qué buscar:**
- ✅ Distribución uniforme de carga entre nodos
- ✅ CPU promedio < 70% por nodo
- ✅ Memoria promedio < 75% por nodo
- ⚠️ Alertar si algún nodo > 85%
- ⚠️ Alertar si distribución desigual > 30%

**Interpretación DevSecOps:**
```
SI NODO > 85%:
├─ Posible pod mal distribuido
├─ Revisar afinidad de pods
├─ Ejecutar kubectl top node
├─ Considerar rebalanceo
├─ Escalar nodo si es necesario
└─ Monitorear próximas horas

SI DISTRIBUCIÓN DESIGUAL:
├─ Posible problema de scheduling
├─ Revisar node selectors
├─ Revisar pod disruption budgets
├─ Revisar pod affinity rules
├─ Considerar pod affinity rules
└─ Ejecutar rebalanceo manual

SI NODO NUEVO CON BAJO USO:
├─ Posible nodo recién agregado
├─ Esperar a que se estabilice
├─ Revisar si hay pods pendientes
├─ Ejecutar Tool 40 (Deployments Off Analyzer)
└─ Considerar drenar nodos antiguos

SI MÚLTIPLES NODOS AFECTADOS:
├─ Problema sistémico
├─ Revisar cambios recientes
├─ Revisar eventos del cluster
├─ Considerar rollback
└─ Escalar a infraestructura
```

---

### Tool 28: Cloud Run Health Analyzer (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [28]  
**Objetivo:** Análisis profundo de salud y rendimiento de servicios Cloud Run

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [28] - Cloud Run Health Analyzer
# Proyecto: cpl-corp-cial-prod-17042024
# Region: us-central1
# Service: [nombre del servicio, opcional]
# Output: json
```

**Qué buscar:**
- ✅ Latencia < 500ms
- ✅ Error rate < 1%
- ✅ Disponibilidad > 99.5%
- ✅ Recursos utilizados < 80%
- ⚠️ Alertar si latencia > 1000ms
- ⚠️ Alertar si error rate > 5%

**Interpretación DevSecOps:**
```
SI LATENCIA > 1000ms:
├─ Posible problema de performance
├─ Revisar código de aplicación
├─ Revisar dependencias externas
├─ Considerar aumentar recursos
├─ Ejecutar profiling
└─ Implementar optimizaciones

SI ERROR RATE > 5%:
├─ Problema crítico
├─ Revisar logs: Cloud Logging
├─ Revisar configuración de servicio
├─ Considerar rollback
├─ Implementar fix
└─ Validar en staging

SI DISPONIBILIDAD < 99%:
├─ Problema de confiabilidad
├─ Revisar eventos de error
├─ Revisar configuración
├─ Implementar circuit breaker
├─ Considerar retry logic
└─ Monitorear próximas horas

SI RECURSOS > 80%:
├─ Posible escalado necesario
├─ Revisar límites de memoria/CPU
├─ Considerar aumentar recursos
├─ Revisar código para optimizaciones
└─ Implementar auto-scaling
```

---

### Tool 40: Deployments Off Analyzer (GCP)
**Ubicación:** `scm/gcp/tools.py` → Opción [40]  
**Objetivo:** Analiza deployments no running en GKE con diagnóstico automático de causa raíz

**Uso:**
```bash
cd scm/gcp
python tools.py
# Seleccionar [40] - Deployments Off Analyzer
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: prod-gke-cluster
# Namespace: production
# Output: json
```

**Qué buscar:**
- ✅ Sin deployments en estado no running
- ✅ Todas las replicas en estado Ready
- ✅ Sin pods en CrashLoopBackOff
- ⚠️ Alertar si deployment no running
- ⚠️ Alertar si severidad = CRITICAL

**Interpretación DevSecOps:**
```
SI DEPLOYMENT NO RUNNING:
├─ Causa raíz identificada automáticamente
├─ Revisar recomendaciones generadas
├─ Ejecutar acciones recomendadas
├─ Monitorear recuperación
└─ Documentar incidente

SI SEVERIDAD CRITICAL:
├─ Escalar inmediatamente
├─ Ejecutar kubectl logs para más detalles
├─ Considerar rollback si es reciente
├─ Notificar al equipo de aplicaciones
├─ Crear ticket de incidente
└─ Implementar post-mortem

CAUSAS COMUNES Y SOLUCIONES:
├─ ImagePullBackOff → Verificar registry y credenciales
├─ CrashLoopBackOff → Revisar logs de aplicación
├─ Pending → Escalar cluster o revisar requests
├─ CreateContainerConfigError → Verificar Secrets/ConfigMaps
├─ FailedScheduling → Revisar recursos disponibles
├─ ImagePullError → Validar nombre y acceso a imagen
└─ OOMKilled → Aumentar límite de memoria

ACCIONES RECOMENDADAS:
1. Revisar logs: kubectl logs POD_NAME -n NAMESPACE
2. Revisar eventos: kubectl describe pod POD_NAME -n NAMESPACE
3. Revisar configuración: kubectl get deployment -n NAMESPACE
4. Revisar recursos: kubectl top nodes
5. Ejecutar diagnóstico: Tool 24 (Node Resources Monitor)
6. Considerar rollback si es reciente
7. Documentar incidente y causa raíz
8. Implementar prevención
```

---

## 🚨 Matriz de Alertas

### Alertas Críticas (Acción Inmediata)

| Condición | Severidad | Acción |
|-----------|-----------|--------|
| CPU > 95% | 🔴 CRITICAL | Escalar a infraestructura |
| Memoria > 95% | 🔴 CRITICAL | Reiniciar pod/nodo |
| Disco > 95% | 🔴 CRITICAL | Limpiar/aumentar capacidad |
| Nodo NotReady | 🔴 CRITICAL | Investigar/recrear nodo |
| CD Success < 70% | 🔴 CRITICAL | Ejecutar Deep Dive |
| Drift CRITICAL | 🔴 CRITICAL | Investigar/rollback |
| Key > 180 días | 🔴 CRITICAL | Rotar key inmediatamente |
| SA deshabilitada | 🔴 CRITICAL | Habilitar/investigar |

### Alertas Altas (Acción en 1 hora)

| Condición | Severidad | Acción |
|-----------|-----------|--------|
| CPU > 85% | 🟠 HIGH | Monitorear/escalar |
| Memoria > 85% | 🟠 HIGH | Revisar logs |
| Disco > 85% | 🟠 HIGH | Planificar limpieza |
| Pod Pending > 5% | 🟠 HIGH | Revisar recursos |
| CI Success < 90% | 🟠 HIGH | Revisar logs |
| Aprobación > 4h | 🟠 HIGH | Contactar aprobador |
| Key > 90 días | 🟠 HIGH | Planificar rotación |

### Alertas Medias (Acción en 24 horas)

| Condición | Severidad | Acción |
|-----------|-----------|--------|
| CPU > 70% | 🟡 MEDIUM | Monitorear tendencia |
| Memoria > 70% | 🟡 MEDIUM | Monitorear tendencia |
| Health Score < 80 | 🟡 MEDIUM | Revisar próximas 24h |
| Drift MEDIUM | 🟡 MEDIUM | Revisar cambios |
| Repo sin CI | 🟡 MEDIUM | Crear plan de acción |

---

## 📋 Checklist Diario

### Mañana (08:00)
- [ ] Ejecutar GCP Tool 1 (Resources)
- [ ] Ejecutar GCP Tool 14 (GKE Clusters)
- [ ] Ejecutar AWS Tool 1 (IAM Users)
- [ ] Ejecutar AWS Tool 13 (CloudWatch Alarms)
- [ ] Ejecutar AZDO Tool 18 (Pipeline Status)
- [ ] Ejecutar AZDO Tool 3 (Release Health)
- [ ] Generar Dashboard Matutino Multi-Cloud
- [ ] Revisar alertas críticas
- [ ] Notificar al equipo si hay problemas

### Tarde (14:00)
- [ ] Ejecutar GCP Tool 25 (Pod Resources)
- [ ] Ejecutar GCP Tool 40 (Deployments Off Analyzer)
- [ ] Ejecutar AWS Tool 5 (RDS Storage)
- [ ] Ejecutar AWS Tool 15 (EKS Pod Monitor)
- [ ] Ejecutar AZDO Tool 11 (Pending Approvals)
- [ ] Ejecutar GCP Tool 24 (Node Resources)
- [ ] Generar Reporte Vespertino Multi-Cloud
- [ ] Revisar anomalías
- [ ] Tomar acciones correctivas

### Noche (22:00)
- [ ] Ejecutar GCP Tool 4 (Service Accounts)
- [ ] Ejecutar AWS Tool 1 (IAM Audit)
- [ ] Ejecutar AWS Tool 19 (Inventory)
- [ ] Ejecutar AZDO Tool 9 (CICD Inventory)
- [ ] Ejecutar AZDO Tool 4 (Pipeline Drift)
- [ ] Generar Reporte Nocturno Multi-Cloud
- [ ] Revisar cambios del día
- [ ] Preparar reporte para mañana

---

## 🤖 Automatización Recomendada

```bash
#!/bin/bash
# daily_monitoring.sh - Ejecutar monitoreo automático

# Monitoreo Matutino (08:00)
0 8 * * * /path/to/morning_monitoring.sh

# Monitoreo Vespertino (14:00)
0 14 * * * /path/to/afternoon_monitoring.sh

# Monitoreo Nocturno (22:00)
0 22 * * * /path/to/night_monitoring.sh

# Consolidar reportes (23:00)
0 23 * * * /path/to/consolidate_reports.sh
```

---

## 📊 Interpretación de Resultados

### Escenario 1: Todo OK
```
✅ CPU < 70%, Memoria < 70%, Disco < 50%
✅ Todos los nodos Ready
✅ CI/CD success > 90%
✅ Health score > 80
✅ Sin alertas críticas

ACCIÓN: Continuar monitoreo normal
```

### Escenario 2: Anomalía Detectada
```
⚠️ CPU > 85% en pod X
⚠️ CI success < 90%
⚠️ Aprobación pendiente > 4h

ACCIÓN:
1. Investigar causa raíz
2. Ejecutar Tool específica
3. Tomar acción correctiva
4. Documentar incidente
5. Implementar prevención
```

### Escenario 3: Problema Crítico
```
🔴 CPU > 95%
🔴 Nodo NotReady
🔴 CD success < 70%

ACCIÓN:
1. Escalar inmediatamente
2. Ejecutar Deep Dive
3. Considerar rollback
4. Notificar a stakeholders
5. Implementar post-mortem
```

---

## 📞 Escalación

| Severidad | Tiempo | Acción |
|-----------|--------|--------|
| 🔴 CRITICAL | Inmediato | Llamar al on-call |
| 🟠 HIGH | 15 min | Slack + email |
| 🟡 MEDIUM | 1 hora | Email + ticket |
| 🟢 LOW | 24 horas | Ticket |

---

**Guía de Monitoreo Diario Completada**  
**Próximo:** Guía de Auditoría Semanal
