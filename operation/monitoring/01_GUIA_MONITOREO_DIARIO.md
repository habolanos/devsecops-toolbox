# 📅 Guía de Monitoreo Diario DevSecOps

**Versión:** 1.1.0  
**Objetivo:** Ejecutar monitoreo diario de ambientes GCP, Azure, AWS y AZDO con interpretación DevSecOps

---

## 🧭 Cómo Navegar a las Herramientas

 Todas las herramientas se acceden desde el **menú principal**:

```bash
python scm/main.py
```

| Plataforma | Opción del Menú |
|-----------|----------------|
| GCP | `main.py → 1 (GCP) → <número de herramienta>` |
| Azure | `main.py → 2 (AZURE) → <número de herramienta>` |
| AWS | `main.py → 3 (AWS) → <número de herramienta>` |
| AZDO | `main.py → 4 (AZDO) → <número de herramienta>` |

> **💡 Tip:** También puedes ejecutar directamente: `python scm/gcp/tools.py`, `python scm/aws/tools.py`, `python scm/azdo/tools.py`

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

**Descripción fundamental:**
El monitoreo matutino es el punto de partida del día. Se ejecuta a primera hora para establecer un baseline de salud de toda la infraestructura multi-cloud (GCP, AWS, AZDO). Este monitoreo es crítico porque:
- Detecta problemas que ocurrieron durante la noche
- Valida que todos los sistemas estén operacionales
- Identifica cambios no autorizados
- Proporciona contexto para el día

**Qué busca prevenir:**
- 🛡️ Caídas de servicios no detectadas
- 🛡️ Degradación de performance sin notificación
- 🛡️ Certificados expirados que causen interrupciones
- 🛡️ Agotamiento de recursos sin escalado
- 🛡️ Pipelines fallidos que bloqueen releases
- 🛡️ Problemas de seguridad sin auditoría
- 🛡️ Cambios no autorizados en infraestructura

**Qué se busca detectar:**
- ✅ Problemas de recursos (CPU, memoria, disco)
- ✅ Problemas de certificados y seguridad
- ✅ Problemas de almacenamiento en bases de datos
- ✅ Problemas de capacidad de red
- ✅ Problemas de salud en servicios Cloud Run
- ✅ Problemas en clusters GKE
- ✅ Problemas en pipelines CI/CD
- ✅ Problemas en releases CD

**Herramientas ejecutadas:**
- Tool 1: Monitoreo de Recursos GCP
- Tool 14: GKE Cluster Checker
- Tool 5: Certificate Manager Checker
- Tool 7: Cloud SQL Disk Monitor
- Tool 13: IP Addresses Checker
- Tool 28: Cloud Run Health Analyzer
- Tool 18: Pipeline Status AZDO
- Tool 3: Release CD Health AZDO
- AWS Tool 1: IAM Users & Policies Checker
- AWS Tool 13: CloudWatch Alarms Checker

### Ejecución

#### Paso 1: Recursos GCP (5 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 1
# O directo: python scm/gcp/tools.py → 1
# Herramienta: Monitoreo de Recursos GCP
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
# Navegación: python scm/main.py → 1 (GCP) → 14
# O directo: python scm/gcp/tools.py → 14
# Herramienta: GKE Cluster Checker
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

#### Paso 3: Certificados SSL/TLS (3 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 5
# Herramienta: Certificate Manager Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Todos los certificados válidos
- ✅ Certificados con validez > 30 días
- ✅ Sin certificados expirados
- ⚠️ Alertar si certificado vence < 30 días

**Interpretación DevSecOps:**
```
SI CERTIFICADO VENCE < 30 DÍAS:
├─ Riesgo de interrupción de servicio
├─ Renovar certificado inmediatamente
├─ Validar en staging primero
└─ Documentar cambios

SI CERTIFICADO EXPIRADO:
├─ Crítico - Acción inmediata
├─ Reemplazar certificado
├─ Verificar servicios afectados
└─ Notificar a stakeholders

SI MÚLTIPLES CERTIFICADOS VENCIENDO:
├─ Problema de governance
├─ Implementar sistema de alertas
└─ Crear proceso de renovación automática
```

---

#### Paso 4: Cloud SQL Disk Monitor (3 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 7
# Herramienta: Cloud SQL Disk Monitor
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Uso de disco < 70%
- ✅ Crecimiento de disco predecible
- ⚠️ Alertar si uso > 80%
- ⚠️ Alertar si crecimiento anómalo

**Interpretación DevSecOps:**
```
SI USO > 80%:
├─ Riesgo de agotamiento
├─ Revisar tamaño de base de datos
├─ Aumentar almacenamiento
└─ Monitorear próximas horas

SI CRECIMIENTO ANÓMALO:
├─ Posible fuga de datos
├─ Revisar logs de aplicación
└─ Documentar causa raíz

SI ESPACIO CRÍTICO:
├─ Acción inmediata
├─ Aumentar almacenamiento
└─ Notificar a stakeholders
```

---

#### Paso 5: IP Addresses Checker (3 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 13
# Herramienta: IP Addresses Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: prod-gke-cluster
# Region: us-central1
# Output: json
```

**Qué buscar:**
- ✅ Disponibilidad de IPs > 30%
- ✅ Sin agotamiento de IPs
- ⚠️ Alertar si disponibilidad < 20%
- ⚠️ Alertar si agotamiento próximo

**Interpretación DevSecOps:**
```
SI DISPONIBILIDAD < 20%:
├─ Riesgo de agotamiento
├─ Planificar expansión de CIDR
├─ Revisar uso de IPs
└─ Escalar a infraestructura

SI AGOTAMIENTO PRÓXIMO:
├─ Crítico - Acción inmediata
├─ Expandir rango de IPs
├─ Revisar pods innecesarios
└─ Implementar IP management policy

SI DISTRIBUCIÓN DESIGUAL:
├─ Posible problema de scheduling
├─ Revisar node selectors
└─ Rebalancear si es necesario
```

---

#### Paso 6: Cloud Run Health Analyzer (5 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 28
# Herramienta: Cloud Run Health Analyzer
# Proyecto: cpl-corp-cial-prod-17042024
# Region: us-central1
# Output: json
```

**Qué buscar:**
- ✅ Latencia < 500ms
- ✅ Error rate < 1%
- ✅ Disponibilidad > 99.5%
- ⚠️ Alertar si latencia > 1000ms
- ⚠️ Alertar si error rate > 5%

**Interpretación DevSecOps:**
```
SI LATENCIA > 1000ms:
├─ Posible problema de performance
├─ Revisar código de aplicación
├─ Revisar dependencias externas
└─ Considerar aumentar recursos

SI ERROR RATE > 5%:
├─ Problema crítico
├─ Revisar logs: Cloud Logging
├─ Considerar rollback
└─ Implementar fix

SI DISPONIBILIDAD < 99%:
├─ Problema de confiabilidad
├─ Revisar eventos de error
├─ Implementar circuit breaker
└─ Monitorear próximas horas

SI RECURSOS > 80%:
├─ Posible escalado necesario
├─ Revisar límites de memoria/CPU
└─ Implementar auto-scaling
```

---

#### Paso 7: Pipeline Status AZDO (5 min)
```bash
# Navegación: python scm/main.py → 4 (AZDO) → 18
# Herramienta: Pipeline Status
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

#### Paso 8: Release Health (5 min)
```bash
# Navegación: python scm/main.py → 4 (AZDO) → 3
# Herramienta: Release CD Health
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

#### Paso 9: Monitoreo AWS (5 min)
```bash
# Navegación: python scm/main.py → 3 (AWS) → 1
# Herramienta: IAM Users & Policies Checker
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
# Navegación: python scm/main.py → 3 (AWS) → 13
# Herramienta: CloudWatch Alarms Checker
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Todas las alarmas activas
- ✅ Sin alarmas en estado ALARM
- ⚠️ Alertar si hay alarmas fallando

---

#### Paso 10: Generar Dashboard Matutino (5 min)
```bash
# Consolidar resultados de todos los pasos
cat > outcome/daily_morning_report_$(date +%Y%m%d).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gcp_resources": { /* Resultado Tool 1 - CPU, Memoria, Disco */ },
  "gke_clusters": { /* Resultado Tool 14 - Nodos, Versión, Pods */ },
  "certificates": { /* Resultado Tool 5 - Certificados SSL/TLS */ },
  "cloud_sql_disk": { /* Resultado Tool 7 - Uso de disco Cloud SQL */ },
  "ip_addresses": { /* Resultado Tool 13 - Capacidad de red GKE */ },
  "cloud_run_health": { /* Resultado Tool 28 - Latencia, Error Rate, Disponibilidad */ },
  "azdo_pipeline_status": { /* Resultado Tool 18 - CI/CD Success Rate */ },
  "azdo_release_health": { /* Resultado Tool 3 - Health Score, Estabilidad */ },
  "aws_iam": { /* Resultado AWS Tool 1 - Usuarios, MFA, Keys */ },
  "aws_cloudwatch": { /* Resultado AWS Tool 13 - Alarmas activas */ },
  "alerts": [ /* Alertas críticas consolidadas */ ],
  "summary": {
    "total_checks": 10,
    "passed": 0,
    "warnings": 0,
    "critical": 0
  }
}
EOF
```

**Salida esperada:**
```
✅ MONITOREO MATUTINO COMPLETADO
├─ GCP Resources (Tool 1): OK (CPU 45%, Mem 62%, Disk 35%)
├─ GKE Clusters (Tool 14): OK (3 nodos Ready, 150 pods running)
├─ Certificates (Tool 5): OK (Todos válidos, vencimiento > 30 días)
├─ Cloud SQL Disk (Tool 7): OK (Uso 65%, crecimiento normal)
├─ IP Addresses (Tool 13): OK (Disponibilidad 45%, distribución uniforme)
├─ Cloud Run Health (Tool 28): OK (Latencia 250ms, Error Rate 0.5%)
├─ Pipeline Status (Tool 18): OK (CI 92%, CD 96%)
├─ Release Health (Tool 3): OK (Score 85, Estabilidad 94%)
├─ AWS IAM (Tool 1): OK (Todos con MFA, keys < 90 días)
├─ AWS CloudWatch (Tool 13): OK (Todas las alarmas activas)
└─ Alertas: 0 críticas

Reporte guardado: outcome/daily_morning_report_20260708.json
```

---

## 📊 MONITOREO VESPERTINO (14:00)

### Objetivo
Detectar anomalías y problemas que surgieron durante el día

**Descripción fundamental:**
El monitoreo vespertino se ejecuta a mitad del día para detectar anomalías que surgieron después del monitoreo matutino. Este monitoreo es esencial porque:
- Identifica problemas en tiempo real durante el horario de trabajo
- Detecta cambios de carga anormal en aplicaciones
- Valida que los deployments estén funcionando correctamente
- Permite intervención rápida antes de que afecte a usuarios
- Monitorea cambios que ocurrieron durante el día

**Qué busca prevenir:**
- 🛡️ Outages de servicios durante horario laboral
- 🛡️ Degradación de performance no detectada
- 🛡️ Deployments fallidos sin notificación
- 🛡️ Agotamiento de recursos durante picos de uso
- 🛡️ Bloqueos en releases que afecten el flujo
- 🛡️ Problemas de conectividad sin escalado
- 🛡️ Pérdida de datos por almacenamiento lleno

**Qué se busca detectar:**
- ✅ Pods con alto uso de recursos
- ✅ Aprobaciones de releases bloqueadas
- ✅ Distribución desigual de carga en nodos
- ✅ Deployments no running o con problemas
- ✅ Problemas de almacenamiento en Cloud SQL
- ✅ Agotamiento de capacidad de red
- ✅ Problemas en almacenamiento RDS
- ✅ Problemas en pods de EKS

**Herramientas ejecutadas:**
- Tool 25: GKE Pod Resources Monitor
- Tool 11: Pending Approvals AZDO
- Tool 24: GKE Node Resources Monitor
- Tool 40: Deployments Off Analyzer
- Tool 7: Cloud SQL Disk Monitor
- Tool 13: IP Addresses Checker
- AWS Tool 5: RDS Storage Monitor
- AWS Tool 15: EKS Pod Monitor

### Ejecución

#### Paso 1: Pods con Alto Uso (5 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 25
# Herramienta: GKE Pod Resources Monitor
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
# Navegación: python scm/main.py → 4 (AZDO) → 11
# Herramienta: Pending Approvals
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
# Navegación: python scm/main.py → 1 (GCP) → 24
# Herramienta: GKE Node Resources Monitor
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
# Navegación: python scm/main.py → 1 (GCP) → 40
# Herramienta: Deployments Off Analyzer
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

#### Paso 5: Cloud SQL Disk Monitor (3 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 7
# Herramienta: Cloud SQL Disk Monitor
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Qué buscar:**
- ✅ Uso de disco < 70%
- ✅ Crecimiento de disco predecible
- ⚠️ Alertar si uso > 80%
- ⚠️ Alertar si crecimiento anómalo

**Interpretación DevSecOps:**
```
SI USO > 80%:
├─ Riesgo de agotamiento
├─ Revisar tamaño de base de datos
├─ Aumentar almacenamiento
└─ Monitorear próximas horas

SI CRECIMIENTO ANÓMALO:
├─ Posible fuga de datos
├─ Revisar logs de aplicación
├─ Ejecutar análisis de tablas
└─ Documentar causa raíz

SI ESPACIO CRÍTICO:
├─ Acción inmediata
├─ Aumentar almacenamiento
└─ Notificar a stakeholders
```

---

#### Paso 6: IP Addresses Checker (3 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 13
# Herramienta: IP Addresses Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: prod-gke-cluster
# Region: us-central1
# Output: json
```

**Qué buscar:**
- ✅ Disponibilidad de IPs > 30%
- ✅ Sin agotamiento de IPs
- ⚠️ Alertar si disponibilidad < 20%
- ⚠️ Alertar si agotamiento próximo

**Interpretación DevSecOps:**
```
SI DISPONIBILIDAD < 20%:
├─ Riesgo de agotamiento
├─ Planificar expansión de CIDR
├─ Revisar uso de IPs
└─ Escalar a infraestructura

SI AGOTAMIENTO PRÓXIMO:
├─ Crítico - Acción inmediata
├─ Expandir rango de IPs
├─ Revisar pods innecesarios
└─ Implementar IP management policy

SI DISTRIBUCIÓN DESIGUAL:
├─ Posible problema de scheduling
├─ Revisar node selectors
└─ Rebalancear si es necesario
```

---

#### Paso 7: Monitoreo AWS Vespertino (3 min)
```bash
# Navegación: python scm/main.py → 3 (AWS) → 5
# Herramienta: RDS Storage Monitor
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Almacenamiento RDS < 80%
- ⚠️ Alertar si > 85%

Luego:
```bash
# Navegación: python scm/main.py → 3 (AWS) → 15
# Herramienta: EKS Pod Monitor
# Profile: default
# Cluster: [nombre del cluster]
# Output: json
```

**Qué buscar:**
- ✅ Pods con CPU < 80%
- ✅ Pods con memoria < 85%
- ⚠️ Alertar si alguno > 90%

---

#### Paso 8: Generar Reporte Vespertino (2 min)
```bash
cat > outcome/daily_afternoon_report_$(date +%Y%m%d).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gcp_pod_resources": { /* Resultado Tool 25 - Pods con alto uso */ },
  "pending_approvals": { /* Resultado Tool 11 - Aprobaciones bloqueadas */ },
  "gke_node_resources": { /* Resultado Tool 24 - Distribución de carga */ },
  "deployments_off": { /* Resultado Tool 40 - Deployments no running */ },
  "cloud_sql_disk": { /* Resultado Tool 7 - Almacenamiento Cloud SQL */ },
  "ip_addresses": { /* Resultado Tool 13 - Capacidad de red */ },
  "aws_rds_storage": { /* Resultado AWS Tool 5 - Almacenamiento RDS */ },
  "aws_eks_pods": { /* Resultado AWS Tool 15 - Pods en EKS */ },
  "anomalies": [ /* Anomalías detectadas */ ],
  "actions_taken": [ /* Acciones tomadas */ ],
  "summary": {
    "total_checks": 8,
    "anomalies_found": 0,
    "critical_issues": 0,
    "warnings": 0
  }
}
EOF
```

**Salida esperada:**
```
✅ MONITOREO VESPERTINO COMPLETADO
├─ Pod Resources (Tool 25): OK (Top 10 pods monitoreados)
├─ Pending Approvals (Tool 11): OK (Sin aprobaciones bloqueadas)
├─ Node Resources (Tool 24): OK (Distribución uniforme)
├─ Deployments Off (Tool 40): OK (Todos running)
├─ Cloud SQL Disk (Tool 7): OK (Uso 65%)
├─ IP Addresses (Tool 13): OK (Disponibilidad 45%)
├─ RDS Storage (AWS Tool 5): OK (Uso 55%)
├─ EKS Pods (AWS Tool 15): OK (Pods saludables)
└─ Anomalías: 0 detectadas

Reporte guardado: outcome/daily_afternoon_report_20260708.json
```

---

## 📊 MONITOREO NOCTURNO (22:00)

### Objetivo
Auditar cambios del día y preparar reporte para mañana

**Descripción fundamental:**
El monitoreo nocturno se ejecuta al final del día para auditar todos los cambios que ocurrieron y preparar el reporte para el siguiente día. Este monitoreo es fundamental porque:
- Audita todos los cambios realizados durante el día
- Detecta cambios no autorizados o drift en infraestructura
- Valida la seguridad y cumplimiento normativo
- Prepara el contexto para el siguiente día
- Identifica deuda técnica y repos sin pipelines
- Consolida hallazgos de seguridad

**Qué busca prevenir:**
- 🛡️ Cambios no autorizados sin detección
- 🛡️ Drift en configuración de infraestructura
- 🛡️ Vulnerabilidades de seguridad sin auditoría
- 🛡️ Keys y credenciales vencidas
- 🛡️ Repos sin pipelines CI/CD
- 🛡️ Bases de datos huérfanas o sin documentación
- 🛡️ Recursos en AWS sin gestión
- 🛡️ Problemas de cumplimiento normativo

**Qué se busca detectar:**
- ✅ Service accounts con keys vencidas
- ✅ Bases de datos huérfanas o con problemas
- ✅ Repos sin pipelines CI/CD
- ✅ Cambios no autorizados en pipelines
- ✅ Problemas de salud en Cloud Run
- ✅ Cambios en usuarios y permisos IAM
- ✅ Recursos nuevos o huérfanos en AWS

**Herramientas ejecutadas:**
- Tool 4: Service Account Checker
- Tool 8: Cloud SQL Database Checker
- Tool 9: CICD Inventory AZDO
- Tool 4: Pipeline Drift Analyzer AZDO
- Tool 28: Cloud Run Health Analyzer
- AWS Tool 1: IAM Users & Policies Checker
- AWS Tool 19: AWS Inventory Generator

### Ejecución

#### Paso 1: Service Accounts (5 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 4
# Herramienta: Service Account Checker
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

#### Paso 2: Cloud SQL Database Checker (3 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 8
# Herramienta: Cloud SQL Database Checker
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
└─ Considerar eliminar si no se usa

SI PERMISOS EXCESIVOS:
├─ Riesgo de seguridad
├─ Revisar principio de menor privilegio
├─ Reducir permisos
└─ Crear usuario específico si es necesario

SI MÚLTIPLES BASES DE DATOS:
├─ Revisar consolidación
├─ Evaluar si se pueden combinar
└─ Documentar arquitectura
```

---

#### Paso 3: Inventario CICD (5 min)
```bash
# Navegación: python scm/main.py → 4 (AZDO) → 9
# Herramienta: CICD Inventory
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

#### Paso 4: Cambios y Drift (5 min)
```bash
# Navegación: python scm/main.py → 4 (AZDO) → 4
# Herramienta: Pipeline Drift Analyzer
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

#### Paso 5: Cloud Run Health Analyzer (5 min)
```bash
# Navegación: python scm/main.py → 1 (GCP) → 28
# Herramienta: Cloud Run Health Analyzer
# Proyecto: cpl-corp-cial-prod-17042024
# Region: us-central1
# Output: json
```

**Qué buscar:**
- ✅ Latencia < 500ms
- ✅ Error rate < 1%
- ✅ Disponibilidad > 99.5%
- ⚠️ Alertar si latencia > 1000ms
- ⚠️ Alertar si error rate > 5%

**Interpretación DevSecOps:**
```
SI LATENCIA > 1000ms:
├─ Posible problema de performance
├─ Revisar código de aplicación
├─ Revisar dependencias externas
└─ Considerar aumentar recursos

SI ERROR RATE > 5%:
├─ Problema crítico
├─ Revisar logs: Cloud Logging
├─ Considerar rollback
└─ Implementar fix

SI DISPONIBILIDAD < 99%:
├─ Problema de confiabilidad
├─ Revisar eventos de error
├─ Implementar circuit breaker
└─ Monitorear próximas horas

SI RECURSOS > 80%:
├─ Posible escalado necesario
├─ Revisar límites de memoria/CPU
└─ Implementar auto-scaling
```

---

#### Paso 6: Auditoría AWS Nocturna (5 min)
```bash
# Navegación: python scm/main.py → 3 (AWS) → 1
# Herramienta: IAM Users & Policies Checker
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Todos los usuarios con MFA
- ✅ Sin access keys > 90 días
- ⚠️ Alertar si hay cambios

Luego:
```bash
# Navegación: python scm/main.py → 3 (AWS) → 19
# Herramienta: AWS Inventory Generator
# Profile: default
# Output: json
```

**Qué buscar:**
- ✅ Inventario completo de recursos
- ✅ Identificar recursos huérfanos
- ⚠️ Alertar si hay cambios

---

#### Paso 7: Generar Reporte Nocturno (5 min)
```bash
cat > outcome/daily_night_report_$(date +%Y%m%d).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gcp_service_accounts": { /* Resultado Tool 4 - Keys, Permisos */ },
  "cloud_sql_databases": { /* Resultado Tool 8 - Bases de datos, Permisos */ },
  "cicd_inventory": { /* Resultado Tool 9 - Repos, Pipelines */ },
  "pipeline_drift": { /* Resultado Tool 4 (AZDO) - Cambios detectados */ },
  "cloud_run_health": { /* Resultado Tool 28 - Salud de servicios */ },
  "aws_iam_audit": { /* Resultado AWS Tool 1 - Usuarios, MFA, Keys */ },
  "aws_inventory": { /* Resultado AWS Tool 19 - Recursos, Huérfanos */ },
  "security_findings": [ /* Hallazgos de seguridad consolidados */ ],
  "recommendations": [ /* Recomendaciones para mañana */ ],
  "summary": {
    "total_checks": 7,
    "security_issues": 0,
    "drift_detected": false,
    "changes_found": 0
  }
}
EOF
```

**Salida esperada:**
```
✅ MONITOREO NOCTURNO COMPLETADO
├─ Service Accounts (Tool 4): OK (Keys < 90 días)
├─ SQL Databases (Tool 8): OK (Bases de datos documentadas)
├─ CICD Inventory (Tool 9): OK (Todos los repos con pipelines)
├─ Pipeline Drift (Tool 4): OK (Sin cambios no autorizados)
├─ Cloud Run Health (Tool 28): OK (Servicios saludables)
├─ AWS IAM (Tool 1): OK (Todos con MFA)
├─ AWS Inventory (Tool 19): OK (Sin recursos huérfanos)
└─ Hallazgos de seguridad: 0

Reporte guardado: outcome/daily_night_report_20260708.json
```

---

##  Matriz de Alertas

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

### 📅 MONITOREO MATUTINO (08:00) - Baseline de Salud

**Paso 1: Recursos GCP**
- [ ] Ejecutar GCP Tool 1 (Monitoreo de Recursos GCP)
- [ ] Verificar: CPU < 70%, Memoria < 80%, Disco > 20%
- [ ] Alertar si alguno > 85%

**Paso 2: Clusters GKE**
- [ ] Ejecutar GCP Tool 14 (GKE Cluster Checker)
- [ ] Verificar: Nodos Ready, Versión actualizada, Pods > 95%
- [ ] Alertar si hay nodos NotReady

**Paso 3: Certificados SSL/TLS**
- [ ] Ejecutar GCP Tool 5 (Certificate Manager Checker)
- [ ] Verificar: Certificados válidos, Validez > 30 días
- [ ] Alertar si vencimiento < 30 días

**Paso 4: Cloud SQL Disk**
- [ ] Ejecutar GCP Tool 7 (Cloud SQL Disk Monitor)
- [ ] Verificar: Uso < 70%, Crecimiento predecible
- [ ] Alertar si uso > 80%

**Paso 5: IP Addresses**
- [ ] Ejecutar GCP Tool 13 (IP Addresses Checker)
- [ ] Verificar: Disponibilidad > 30%, Distribución uniforme
- [ ] Alertar si disponibilidad < 20%

**Paso 6: Cloud Run Health**
- [ ] Ejecutar GCP Tool 28 (Cloud Run Health Analyzer)
- [ ] Verificar: Latencia < 500ms, Error rate < 1%
- [ ] Alertar si latencia > 1000ms

**Paso 7: Pipeline Status AZDO**
- [ ] Ejecutar AZDO Tool 18 (Pipeline Status)
- [ ] Verificar: CI > 90%, CD > 95%
- [ ] Alertar si success rate < 80%

**Paso 8: Release Health AZDO**
- [ ] Ejecutar AZDO Tool 3 (Release CD Health)
- [ ] Verificar: Health score > 80, Estabilidad > 90%
- [ ] Alertar si score < 70

**Paso 9: IAM Users AWS**
- [ ] Ejecutar AWS Tool 1 (IAM Users & Policies Checker)
- [ ] Verificar: Todos con MFA, Keys < 90 días
- [ ] Alertar si hay usuarios sin MFA

**Paso 10: CloudWatch Alarms AWS**
- [ ] Ejecutar AWS Tool 13 (CloudWatch Alarms Checker)
- [ ] Verificar: Todas las alarmas activas
- [ ] Alertar si hay alarmas fallando

**Paso 11: Generar Dashboard Matutino**
- [ ] Consolidar resultados de 10 herramientas
- [ ] Generar reporte JSON: outcome/daily_morning_report_YYYYMMDD.json
- [ ] Revisar alertas críticas
- [ ] Notificar al equipo si hay problemas

### 📊 MONITOREO VESPERTINO (14:00) - Detección de Anomalías

**Paso 1: Pod Resources**
- [ ] Ejecutar GCP Tool 25 (GKE Pod Resources Monitor)
- [ ] Verificar: Pods CPU < 80%, Memoria < 85%
- [ ] Alertar si alguno > 90%

**Paso 2: Pending Approvals**
- [ ] Ejecutar AZDO Tool 11 (Pending Approvals)
- [ ] Verificar: Sin aprobaciones bloqueadas
- [ ] Alertar si > 3 aprobaciones pendientes

**Paso 3: Node Resources**
- [ ] Ejecutar GCP Tool 24 (GKE Node Resources Monitor)
- [ ] Verificar: Distribución uniforme, CPU < 70%, Memoria < 75%
- [ ] Alertar si algún nodo > 85%

**Paso 4: Deployments Off**
- [ ] Ejecutar GCP Tool 40 (Deployments Off Analyzer)
- [ ] Verificar: Sin deployments no running
- [ ] Alertar si hay deployments con replicas < desired

**Paso 5: Cloud SQL Disk**
- [ ] Ejecutar GCP Tool 7 (Cloud SQL Disk Monitor)
- [ ] Verificar: Uso < 70%, Crecimiento normal
- [ ] Alertar si uso > 80%

**Paso 6: IP Addresses**
- [ ] Ejecutar GCP Tool 13 (IP Addresses Checker)
- [ ] Verificar: Disponibilidad > 30%
- [ ] Alertar si disponibilidad < 20%

**Paso 7: RDS Storage AWS**
- [ ] Ejecutar AWS Tool 5 (RDS Storage Monitor)
- [ ] Verificar: Almacenamiento < 80%
- [ ] Alertar si > 85%

**Paso 8: EKS Pod Monitor AWS**
- [ ] Ejecutar AWS Tool 15 (EKS Pod Monitor)
- [ ] Verificar: Pods CPU < 80%, Memoria < 85%
- [ ] Alertar si alguno > 90%

**Paso 9: Generar Reporte Vespertino**
- [ ] Consolidar resultados de 8 herramientas
- [ ] Generar reporte JSON: outcome/daily_afternoon_report_YYYYMMDD.json
- [ ] Revisar anomalías detectadas
- [ ] Tomar acciones correctivas inmediatas

### 🌙 MONITOREO NOCTURNO (22:00) - Auditoría y Cambios

**Paso 1: Service Accounts**
- [ ] Ejecutar GCP Tool 4 (Service Account Checker)
- [ ] Verificar: Keys < 90 días, SAs habilitadas
- [ ] Alertar si key > 90 días

**Paso 2: Cloud SQL Databases**
- [ ] Ejecutar GCP Tool 8 (Cloud SQL Database Checker)
- [ ] Verificar: Bases de datos documentadas, Permisos correctos
- [ ] Alertar si hay bases de datos desconocidas

**Paso 3: CICD Inventory**
- [ ] Ejecutar AZDO Tool 9 (CICD Inventory)
- [ ] Verificar: Todos los repos con CI pipeline
- [ ] Alertar si hay repos sin CI

**Paso 4: Pipeline Drift**
- [ ] Ejecutar AZDO Tool 4 (Pipeline Drift Analyzer)
- [ ] Verificar: Sin drift en pipelines
- [ ] Alertar si drift CRITICAL o MEDIUM

**Paso 5: Cloud Run Health**
- [ ] Ejecutar GCP Tool 28 (Cloud Run Health Analyzer)
- [ ] Verificar: Latencia < 500ms, Error rate < 1%
- [ ] Alertar si latencia > 1000ms

**Paso 6: IAM Audit AWS**
- [ ] Ejecutar AWS Tool 1 (IAM Users & Policies Checker)
- [ ] Verificar: Todos con MFA, Keys < 90 días
- [ ] Alertar si hay cambios

**Paso 7: AWS Inventory**
- [ ] Ejecutar AWS Tool 19 (AWS Inventory Generator)
- [ ] Verificar: Inventario completo, Sin recursos huérfanos
- [ ] Alertar si hay cambios

**Paso 8: Generar Reporte Nocturno**
- [ ] Consolidar resultados de 7 herramientas
- [ ] Generar reporte JSON: outcome/daily_night_report_YYYYMMDD.json
- [ ] Revisar cambios del día
- [ ] Preparar reporte para mañana
- [ ] Documentar hallazgos de seguridad

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
