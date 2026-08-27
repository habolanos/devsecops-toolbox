# 🚀 Guía de Pre-Deploy Validation DevSecOps

**Versión:** 1.1.0  
**Objetivo:** Validar que un deployment es seguro antes de ejecutarlo

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

Checklist de validación pre-deploy que cubre:
- **Validación de Configuración** (5 min)
- **Validación de Seguridad** (10 min)
- **Validación de Dependencias** (10 min)
- **Validación de Calidad** (5 min)
- **Aprobación Final** (5 min)

**Tiempo Total:** ~35 minutos

---

## ✅ FASE 1: VALIDACIÓN DE CONFIGURACIÓN (5 min)

### Objetivo
Validar que la configuración del deployment es correcta

### Ejecución

#### Paso 1: Validar Secrets y ConfigMaps
```bash
# Navegación: python scm/main.py → 1 (GCP) → 15
# Herramienta: Secrets & ConfigMaps Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: gke-corp-cial-prod-01
# Output: json
```

**Checklist:**
- [ ] Todos los Secrets referenciados existen
- [ ] Todos los ConfigMaps referenciados existen
- [ ] Sin referencias a Secrets/ConfigMaps inexistentes
- [ ] Secrets con permisos correctos
- [ ] ConfigMaps con datos correctos

**Qué hacer si falla:**
```
❌ Secret no encontrado:
├─ Crear Secret en cluster
├─ Usar Secret Manager si es sensible
├─ Verificar nombre exacto
└─ Bloquear deployment

❌ ConfigMap no encontrado:
├─ Crear ConfigMap en cluster
├─ Verificar nombre exacto
├─ Validar datos
└─ Bloquear deployment

❌ Permisos incorrectos:
├─ Revisar RBAC
├─ Ajustar permisos
├─ Probar acceso
└─ Bloquear deployment
```

---

#### Paso 2: Validar Deployment Validator
```bash
# Navegación: python scm/main.py → 1 (GCP) → 19
# Herramienta: Deployment Validator
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: gke-corp-cial-prod-01
# Deployment: [nombre del deployment]
# Namespace: production
# Validate: all
# Output: json
```

**Checklist:**
- [ ] ConfigMaps validados
- [ ] Secrets validados
- [ ] Conectividad a BD validada
- [ ] Recursos suficientes
- [ ] Sin errores críticos

**Qué hacer si falla:**
```
❌ Recurso insuficiente:
├─ Aumentar requests/limits
├─ Escalar cluster si es necesario
├─ Revisar HPA
└─ Bloquear deployment

❌ Conectividad fallida:
├─ Verificar firewall rules
├─ Verificar DNS
├─ Verificar credenciales
├─ Probar conectividad manual
└─ Bloquear deployment

❌ Error crítico:
├─ Revisar logs
├─ Ejecutar Deep Dive
├─ Corregir problema
└─ Bloquear deployment
```

---

## 🔐 FASE 2: VALIDACIÓN DE SEGURIDAD (10 min)

### Objetivo
Validar que el deployment cumple con estándares de seguridad

### Ejecución

#### Paso 1: Validar Imagen de Contenedor
```bash
# Navegación: python scm/main.py → 1 (GCP) → 18
# Herramienta: Cloud Run Checker (o revisar manualmente)
# Proyecto: cpl-corp-cial-prod-17042024
# View: security
# Output: json
```

**Checklist:**
- [ ] Imagen de contenedor escaneada
- [ ] Sin vulnerabilidades críticas
- [ ] Sin vulnerabilidades altas no remediadas
- [ ] Imagen firmada
- [ ] Imagen de base actualizada

**Qué hacer si falla:**
```
❌ Vulnerabilidad crítica:
├─ Actualizar imagen
├─ Usar imagen base segura
├─ Escanear nuevamente
└─ Bloquear deployment

❌ Vulnerabilidad alta:
├─ Evaluar riesgo
├─ Si es aceptable, documentar
├─ Si no, actualizar imagen
└─ Bloquear si no se acepta

❌ Imagen no firmada:
├─ Firmar imagen
├─ Usar Binary Authorization
├─ Verificar firma
└─ Bloquear deployment

❌ Imagen base antigua:
├─ Actualizar imagen base
├─ Reconstruir imagen
├─ Probar cambios
└─ Bloquear deployment
```

---

#### Paso 2: Validar IAM y Permisos
```bash
# Navegación: python scm/main.py → 1 (GCP) → 3
# Herramienta: Reporte de Roles y Permisos IAM
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Checklist:**
- [ ] Service Account con permisos mínimos
- [ ] Sin roles "Owner" o "Editor"
- [ ] Permisos específicos para la aplicación
- [ ] Sin permisos heredados
- [ ] Sin permisos temporales

**Qué hacer si falla:**
```
❌ Permisos excesivos:
├─ Reducir permisos
├─ Usar Custom Roles
├─ Implementar menor privilegio
└─ Bloquear deployment

❌ Rol "Owner" asignado:
├─ Cambiar a rol específico
├─ Usar Service Account
├─ Implementar MFA
└─ Bloquear deployment

❌ Permisos heredados:
├─ Revisar herencia
├─ Remover si no es necesario
├─ Documentar razón
└─ Bloquear si es riesgo
```

---

#### Paso 3: Validar Networking
```bash
# Navegación: python scm/main.py → 1 (GCP) → 10
# Herramienta: VPC Networks Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Output: json
```

**Checklist:**
- [ ] Firewall rules correctas
- [ ] Sin puertos expuestos innecesariamente
- [ ] VPC correcta
- [ ] Subnet correcta
- [ ] Network policies aplicadas

**Qué hacer si falla:**
```
❌ Firewall rule incorrecta:
├─ Revisar regla
├─ Ajustar si es necesario
├─ Probar conectividad
└─ Bloquear deployment

❌ Puerto expuesto:
├─ Revisar si es intencional
├─ Restringir acceso si es posible
├─ Documentar razón
└─ Bloquear si es riesgo

❌ VPC incorrecta:
├─ Cambiar a VPC correcta
├─ Verificar conectividad
├─ Probar acceso
└─ Bloquear deployment
```

---

## 🔗 FASE 3: VALIDACIÓN DE DEPENDENCIAS (10 min)

### Objetivo
Validar que el deployment puede conectarse a sus dependencias

### Ejecución

#### Paso 1: Validar Conectividad a BD
```bash
# Navegación: python scm/main.py → 1 (GCP) → 16
# Herramienta: Pod Connectivity Checker
# Deployment: [nombre del deployment]
# SQL Instance: [nombre de instancia Cloud SQL]
# Output: json
```

**Checklist:**
- [ ] Conectividad TCP a BD establecida
- [ ] Credenciales correctas
- [ ] BD accesible desde pod
- [ ] Sin errores de conexión
- [ ] Latencia aceptable

**Qué hacer si falla:**
```
❌ Conectividad TCP fallida:
├─ Verificar firewall rules
├─ Verificar Cloud SQL Proxy
├─ Verificar VPC
├─ Probar manualmente
└─ Bloquear deployment

❌ Credenciales incorrectas:
├─ Verificar credenciales
├─ Actualizar Secret
├─ Probar conexión
└─ Bloquear deployment

❌ BD no accesible:
├─ Verificar BD está activa
├─ Verificar permisos
├─ Verificar conectividad
└─ Bloquear deployment

❌ Latencia alta:
├─ Revisar red
├─ Revisar BD performance
├─ Considerar optimización
└─ Bloquear si es crítico
```

---

#### Paso 2: Validar Dependencias de Deployment
```bash
# Navegación: python scm/main.py → 1 (GCP) → 17
# Herramienta: Deploy Dependency Checker
# Proyecto: cpl-corp-cial-prod-17042024
# Cluster: gke-corp-cial-prod-01
# Deployment: [nombre del deployment]
# Namespace: production
# Probe mode: tcp
# Output: json
```

**Checklist:**
- [ ] Todas las dependencias accesibles
- [ ] ConfigMaps correctos
- [ ] Secrets correctos
- [ ] Conectividad a servicios externos
- [ ] Sin dependencias faltantes

**Qué hacer si falla:**
```
❌ Dependencia no accesible:
├─ Verificar servicio
├─ Verificar DNS
├─ Verificar firewall
├─ Probar conectividad
└─ Bloquear deployment

❌ ConfigMap incorrecto:
├─ Revisar datos
├─ Actualizar ConfigMap
├─ Probar cambios
└─ Bloquear deployment

❌ Secret incorrecto:
├─ Revisar datos
├─ Actualizar Secret
├─ Probar acceso
└─ Bloquear deployment

❌ Servicio externo no accesible:
├─ Verificar servicio
├─ Verificar credenciales
├─ Verificar firewall
└─ Bloquear deployment
```

---

## 📊 FASE 4: VALIDACIÓN DE CALIDAD (5 min)

### Objetivo
Validar que el código y configuración cumplen con estándares de calidad

### Ejecución

#### Paso 1: Validar Cambios de Código
```bash
# Navegación: python scm/main.py → 4 (AZDO) → 20
# Herramienta: Repo Branch Diff
# Proyecto: [proyecto]
# Repo: [repositorio]
# Source: develop
# Target: master
# Output: json
```

**Checklist:**
- [ ] Score de cambios > 70
- [ ] Sin cambios CRITICAL
- [ ] Sin cambios HIGH sin justificación
- [ ] Tests pasando
- [ ] Documentación actualizada

**Qué hacer si falla:**
```
❌ Score < 70:
├─ Revisar cambios
├─ Ejecutar análisis detallado
├─ Corregir problemas
└─ Bloquear deployment

❌ Cambios CRITICAL:
├─ Revisar impacto
├─ Considerar rollback
├─ Corregir problema
└─ Bloquear deployment

❌ Tests fallando:
├─ Revisar logs de tests
├─ Corregir código
├─ Ejecutar tests nuevamente
└─ Bloquear deployment

❌ Documentación faltante:
├─ Agregar documentación
├─ Actualizar README
├─ Documentar cambios
└─ Bloquear deployment
```

---

#### Paso 2: Validar Task Validator AZDO
```bash
# Navegación: python scm/main.py → 4 (AZDO) → 6
# Herramienta: Task Validator
# Release ID: [ID del release]
# Output: json
```

**Checklist:**
- [ ] Imágenes Docker válidas
- [ ] Rollback strategy definida
- [ ] Credenciales GIT seguras
- [ ] ConfigMap vs Repo sincronizados
- [ ] Sin errores críticos

**Qué hacer si falla:**
```
❌ Imagen Docker inválida:
├─ Verificar imagen
├─ Reconstruir si es necesario
├─ Probar imagen
└─ Bloquear deployment

❌ Rollback strategy faltante:
├─ Definir estrategia
├─ Documentar pasos
├─ Probar rollback
└─ Bloquear deployment

❌ Credenciales inseguras:
├─ Rotar credenciales
├─ Usar Secret Manager
├─ Auditar acceso
└─ Bloquear deployment

❌ ConfigMap desincronizado:
├─ Sincronizar ConfigMap
├─ Verificar datos
├─ Probar cambios
└─ Bloquear deployment
```

---

## ✅ FASE 5: APROBACIÓN FINAL (5 min)

### Objetivo
Obtener aprobación final antes de ejecutar deployment

### Ejecución

#### Paso 1: Generar Reporte de Validación
```bash
cat > outcome/pre_deploy_validation_$(date +%Y%m%d_%H%M%S).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment": {
    "name": "[nombre del deployment]",
    "namespace": "production",
    "cluster": "gke-corp-cial-prod-01",
    "project": "cpl-corp-cial-prod-17042024"
  },
  "validations": {
    "configuration": {
      "secrets_configmaps": "✅ PASS",
      "deployment_validator": "✅ PASS"
    },
    "security": {
      "container_image": "✅ PASS",
      "iam_permissions": "✅ PASS",
      "networking": "✅ PASS"
    },
    "dependencies": {
      "database_connectivity": "✅ PASS",
      "deployment_dependencies": "✅ PASS"
    },
    "quality": {
      "code_changes": "✅ PASS",
      "task_validator": "✅ PASS"
    }
  },
  "overall_status": "✅ APPROVED",
  "approved_by": "[nombre del aprobador]",
  "approved_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "notes": "[notas adicionales]"
}
EOF
```

---

#### Paso 2: Checklist Final
```
ANTES DE DESPLEGAR:

CONFIGURACIÓN:
- [ ] Secrets validados
- [ ] ConfigMaps validados
- [ ] Deployment Validator pasó

SEGURIDAD:
- [ ] Imagen sin vulnerabilidades críticas
- [ ] Permisos correctos
- [ ] Networking correcto

DEPENDENCIAS:
- [ ] Conectividad a BD validada
- [ ] Todas las dependencias accesibles
- [ ] Sin dependencias faltantes

CALIDAD:
- [ ] Score de cambios > 70
- [ ] Tests pasando
- [ ] Documentación actualizada

APROBACIÓN:
- [ ] Reporte de validación generado
- [ ] Aprobador revisó cambios
- [ ] Aprobación registrada
- [ ] Rollback plan documentado
```

---

#### Paso 3: Obtener Aprobación
```
PROCESO DE APROBACIÓN:

1. Enviar reporte a aprobador
   ├─ Email con resumen
   ├─ Adjuntar reporte JSON
   └─ Incluir link a PR

2. Aprobador revisa
   ├─ Revisa cambios
   ├─ Revisa validaciones
   └─ Verifica rollback plan

3. Aprobador aprueba o rechaza
   ├─ Si aprueba: proceder con deployment
   ├─ Si rechaza: corregir problemas
   └─ Si pide cambios: implementar

4. Registrar aprobación
   ├─ Guardar aprobación
   ├─ Documentar razón
   └─ Registrar timestamp
```

---

## 🚀 FASE 6: DEPLOYMENT (Después de Aprobación)

### Objetivo
Ejecutar deployment de forma segura

### Ejecución

#### Paso 1: Ejecutar Deployment
```bash
# Ejecutar deployment
kubectl apply -f deployment.yaml -n production

# Verificar deployment
kubectl rollout status deployment/[nombre] -n production
```

---

#### Paso 2: Monitorear Deployment
```bash
# Navegación: python scm/main.py → 1 (GCP) → 25
# Herramienta: GKE Pod Resources Monitor
# Namespace: production
# Top: 10

# Navegación: python scm/main.py → 1 (GCP) → 1
# Herramienta: Monitoreo de Recursos GCP
```

**Checklist:**
- [ ] Pods corriendo
- [ ] Recursos dentro de límites
- [ ] Sin errores en logs
- [ ] Conectividad funcionando
- [ ] Sin alertas críticas

---

#### Paso 3: Validar Deployment
```bash
# Verificar que la aplicación funciona
curl https://[servicio]/health

# Revisar logs
kubectl logs -f deployment/[nombre] -n production

# Verificar métricas
kubectl top pods -n production
```

---

#### Paso 4: Generar Reporte de Deployment
```bash
cat > outcome/deployment_report_$(date +%Y%m%d_%H%M%S).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment": {
    "name": "[nombre del deployment]",
    "status": "✅ SUCCESS",
    "duration": "X minutos"
  },
  "validation": {
    "pods_running": "✅ PASS",
    "resources_normal": "✅ PASS",
    "no_errors": "✅ PASS",
    "connectivity_ok": "✅ PASS"
  },
  "monitoring": {
    "cpu_usage": "45%",
    "memory_usage": "62%",
    "error_rate": "0%"
  },
  "rollback_plan": {
    "status": "Ready",
    "procedure": "[pasos para rollback]",
    "estimated_time": "5 minutos"
  }
}
EOF
```

---

## 🔄 ROLLBACK PLAN

### Si algo falla durante o después del deployment:

```bash
# 1. Identificar problema
kubectl describe pod [pod-name] -n production
kubectl logs [pod-name] -n production

# 2. Ejecutar rollback
kubectl rollout undo deployment/[nombre] -n production

# 3. Verificar rollback
kubectl rollout status deployment/[nombre] -n production

# 4. Validar que funciona
curl https://[servicio]/health

# 5. Documentar incidente
cat > outcome/rollback_report_$(date +%Y%m%d_%H%M%S).json << 'EOF'
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment": "[nombre del deployment]",
  "status": "🔄 ROLLED BACK",
  "reason": "[razón del rollback]",
  "duration": "X minutos",
  "impact": "[impacto del incidente]",
  "root_cause": "[causa raíz]",
  "lessons_learned": "[lecciones aprendidas]"
}
EOF
```

---

## 📋 Checklist Completo Pre-Deploy

### Antes de Iniciar
- [ ] Cambios revisados y aprobados
- [ ] Tests pasando
- [ ] Documentación actualizada
- [ ] Rollback plan documentado

### Fase 1: Configuración
- [ ] Secrets validados
- [ ] ConfigMaps validados
- [ ] Deployment Validator pasó

### Fase 2: Seguridad
- [ ] Imagen sin vulnerabilidades críticas
- [ ] Permisos correctos
- [ ] Networking correcto

### Fase 3: Dependencias
- [ ] Conectividad a BD validada
- [ ] Todas las dependencias accesibles
- [ ] Sin dependencias faltantes

### Fase 4: Calidad
- [ ] Score de cambios > 70
- [ ] Tests pasando
- [ ] Documentación actualizada

### Fase 5: Aprobación
- [ ] Reporte generado
- [ ] Aprobador revisó
- [ ] Aprobación registrada

### Fase 6: Deployment
- [ ] Deployment ejecutado
- [ ] Pods corriendo
- [ ] Recursos normales
- [ ] Sin errores

### Post-Deployment
- [ ] Monitoreo activo
- [ ] Alertas configuradas
- [ ] Reporte generado
- [ ] Rollback plan listo

---

**Guía de Pre-Deploy Validation v1.1.0**  
**Próximo:** Documento Índice de Monitoreo
