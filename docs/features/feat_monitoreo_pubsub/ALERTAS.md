# 🚨 Sistema de Alertas Preventivas - Pub/Sub Monitor

**Versión**: 1.0  
**Fecha**: 16 de Julio de 2026

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Categorías de Alertas](#categorías-de-alertas)
3. [Umbrales y Reglas](#umbrales-y-reglas)
4. [Configuración](#configuración)
5. [Notificaciones](#notificaciones)
6. [Escalado de Alertas](#escalado-de-alertas)

---

## 🎯 Visión General

### Propósito
Detectar proactivamente problemas en Pub/Sub antes de que afecten a usuarios finales.

### Principios
- ✅ **Preventivo**: Alertar antes del problema crítico
- ✅ **Inteligente**: Reducir falsos positivos
- ✅ **Contextual**: Proporcionar contexto y recomendaciones
- ✅ **Escalable**: Soportar múltiples proyectos y recursos

---

## 🚨 Categorías de Alertas

### 1. ALERTAS DE CAPACIDAD 🔴

Detectan problemas de capacidad y saturación.

#### 1.1 Backlog Crítico

**Métrica**: `num_undelivered_messages`

```yaml
Nombre: "Backlog Crítico Detectado"
Severidad: CRITICAL
Condición: backlog_messages > 100,000
Ventana: 5 minutos
Acción: Inmediata

Descripción: |
  El backlog de mensajes sin entregar ha superado 100,000.
  Esto indica que los consumidores no pueden procesar
  mensajes lo suficientemente rápido.

Recomendaciones:
  1. Aumentar número de workers de consumo
  2. Optimizar lógica de procesamiento
  3. Verificar logs de error en subscriptions
  4. Escalar recursos de compute

Impacto:
  - Latencia de entrega aumentada
  - Posible pérdida de mensajes
  - Degradación de servicio
```

#### 1.2 Backlog Elevado

**Métrica**: `num_undelivered_messages`

```yaml
Nombre: "Backlog Elevado"
Severidad: WARNING
Condición: backlog_messages > 50,000 AND < 100,000
Ventana: 10 minutos
Acción: Investigación

Descripción: |
  El backlog ha alcanzado niveles elevados.
  Requiere investigación para prevenir escalada.

Recomendaciones:
  1. Monitorear tendencia de backlog
  2. Revisar tasa de consumo
  3. Verificar cambios recientes en código
  4. Preparar plan de escalado
```

#### 1.3 Retraso de Entrega Crítico

**Métrica**: `oldest_unacked_message_age`

```yaml
Nombre: "Retraso de Entrega Crítico"
Severidad: CRITICAL
Condición: oldest_message_age > 60 segundos
Ventana: 5 minutos
Acción: Inmediata

Descripción: |
  El mensaje más antiguo sin confirmar tiene más de 60 segundos.
  Indica que el consumidor está bloqueado o muerto.

Recomendaciones:
  1. Verificar salud del consumidor
  2. Revisar logs de aplicación
  3. Reiniciar workers si es necesario
  4. Aumentar ack_deadline_seconds si es apropiado
```

#### 1.4 Tasa de Error Crítica

**Métrica**: `nack_message_operation_count` / `pull_message_operation_count`

```yaml
Nombre: "Tasa de Error Crítica"
Severidad: CRITICAL
Condición: error_rate > 5%
Ventana: 5 minutos
Acción: Inmediata

Descripción: |
  Más del 5% de mensajes están siendo rechazados.
  Indica problema en lógica de procesamiento.

Recomendaciones:
  1. Revisar logs de error de aplicación
  2. Verificar cambios recientes
  3. Validar formato de mensajes
  4. Revisar configuración de retry policy
```

---

### 2. ALERTAS DE RENDIMIENTO 🟡

Detectan problemas de rendimiento y latencia.

#### 2.1 Latencia P95 Elevada

**Métrica**: `pull_message_operation_count` (latencia)

```yaml
Nombre: "Latencia P95 Elevada"
Severidad: WARNING
Condición: latency_p95 > 5000ms
Ventana: 10 minutos
Acción: Investigación

Descripción: |
  El percentil 95 de latencia ha superado 5 segundos.
  Indica degradación de rendimiento.

Recomendaciones:
  1. Analizar tendencia de latencia
  2. Verificar carga de sistema
  3. Revisar tamaño de mensajes
  4. Optimizar procesamiento
```

#### 2.2 Throughput Bajo

**Métrica**: `publish_message_operation_count`

```yaml
Nombre: "Throughput Bajo"
Severidad: WARNING
Condición: throughput < 50% de baseline
Ventana: 15 minutos
Acción: Investigación

Descripción: |
  El throughput ha caído por debajo del 50% del esperado.
  Puede indicar problema en publishers o red.

Recomendaciones:
  1. Verificar salud de publishers
  2. Revisar conectividad de red
  3. Analizar logs de aplicación
  4. Verificar cuotas de API
```

#### 2.3 Tasa de Descarte Elevada

**Métrica**: `drop_message_operation_count`

```yaml
Nombre: "Tasa de Descarte Elevada"
Severidad: WARNING
Condición: discard_rate > 1%
Ventana: 5 minutos
Acción: Investigación

Descripción: |
  Más del 1% de mensajes están siendo descartados.
  Indica problema de capacidad o configuración.

Recomendaciones:
  1. Aumentar ack_deadline_seconds
  2. Revisar dead-letter policy
  3. Optimizar procesamiento
  4. Escalar recursos
```

---

### 3. ALERTAS DE CONFIGURACIÓN 🟠

Detectan problemas de configuración y mejores prácticas.

#### 3.1 Sin Dead-Letter Policy

**Métrica**: Configuración de subscription

```yaml
Nombre: "Dead-Letter Policy No Configurada"
Severidad: WARNING
Condición: dead_letter_policy == null
Ventana: Una vez
Acción: Configuración

Descripción: |
  La subscription no tiene dead-letter policy configurada.
  Los mensajes fallidos se perderán después de reintentos.

Recomendaciones:
  1. Crear topic para dead-letter
  2. Configurar dead-letter policy
  3. Monitorear dead-letter topic
  4. Implementar alertas para dead-letter
```

#### 3.2 TTL de Mensajes Bajo

**Métrica**: `message_retention_duration`

```yaml
Nombre: "TTL de Mensajes Muy Bajo"
Severidad: INFO
Condición: ttl < 1 hora
Ventana: Una vez
Acción: Revisión

Descripción: |
  El TTL de mensajes es menor a 1 hora.
  Puede causar pérdida de mensajes en caso de retraso.

Recomendaciones:
  1. Aumentar message_retention_duration a mínimo 24 horas
  2. Considerar 7 días para mayor resiliencia
  3. Revisar requisitos de negocio
```

#### 3.3 Sin Retry Policy

**Métrica**: Configuración de subscription

```yaml
Nombre: "Retry Policy No Configurada"
Severidad: WARNING
Condición: retry_policy == null
Ventana: Una vez
Acción: Configuración

Descripción: |
  La subscription no tiene retry policy configurada.
  Los mensajes fallidos no serán reintentados.

Recomendaciones:
  1. Configurar retry policy
  2. Establecer min_backoff = 10s
  3. Establecer max_backoff = 600s
  4. Probar con datos de prueba
```

#### 3.4 Encriptación No Habilitada

**Métrica**: `kms_key_name`

```yaml
Nombre: "Encriptación No Habilitada"
Severidad: WARNING
Condición: kms_key_name == null
Ventana: Una vez
Acción: Seguridad

Descripción: |
  El topic no está encriptado con CMEK.
  Los datos están encriptados con claves de Google.

Recomendaciones:
  1. Crear Cloud KMS key ring
  2. Crear Cloud KMS key
  3. Otorgar permisos a Pub/Sub
  4. Habilitar CMEK en topic
```

---

### 4. ALERTAS DE SEGURIDAD 🔐

Detectan problemas de seguridad y acceso.

#### 4.1 Acceso Público Detectado

**Métrica**: Política IAM

```yaml
Nombre: "Acceso Público Detectado"
Severidad: CRITICAL
Condición: "allUsers" en IAM policy
Ventana: Una vez
Acción: Inmediata

Descripción: |
  El topic o subscription está disponible públicamente.
  Cualquier persona puede acceder a los datos.

Recomendaciones:
  1. Remover "allUsers" de IAM policy
  2. Remover "allAuthenticatedUsers"
  3. Usar service accounts específicos
  4. Auditar acceso reciente
```

#### 4.2 Cambios en IAM Sin Auditoría

**Métrica**: Cloud Audit Logs

```yaml
Nombre: "Cambios en IAM Detectados"
Severidad: WARNING
Condición: IAM policy changed
Ventana: Una vez
Acción: Auditoría

Descripción: |
  Se detectó cambio en la política IAM.
  Requiere auditoría para cumplimiento.

Recomendaciones:
  1. Revisar cambios en Cloud Audit Logs
  2. Verificar autorización del cambio
  3. Documentar razón del cambio
  4. Notificar a equipo de seguridad
```

---

### 5. ALERTAS DE COSTO 💰

Detectan problemas de costo y uso ineficiente.

#### 5.1 Incremento de Costo Significativo

**Métrica**: Costo estimado

```yaml
Nombre: "Incremento de Costo Significativo"
Severidad: WARNING
Condición: cost_increase > 20% vs mes anterior
Ventana: Diaria
Acción: Investigación

Descripción: |
  El costo estimado ha aumentado más del 20%.
  Requiere investigación de causa raíz.

Recomendaciones:
  1. Analizar cambios en volumen de mensajes
  2. Revisar nuevos topics/subscriptions
  3. Optimizar tamaño de mensajes
  4. Considerar cambios en arquitectura
```

#### 5.2 Subscription Inactiva

**Métrica**: `pull_message_operation_count`

```yaml
Nombre: "Subscription Inactiva"
Severidad: INFO
Condición: no messages pulled en 30 días
Ventana: Diaria
Acción: Limpieza

Descripción: |
  La subscription no ha procesado mensajes en 30 días.
  Puede ser un recurso no utilizado.

Recomendaciones:
  1. Verificar si subscription aún es necesaria
  2. Contactar al propietario
  3. Eliminar si no se usa
  4. Documentar razón de eliminación
```

#### 5.3 Topic Sin Consumidores

**Métrica**: Subscriptions del topic

```yaml
Nombre: "Topic Sin Consumidores"
Severidad: INFO
Condición: topic.subscriptions.count == 0
Ventana: Una vez
Acción: Revisión

Descripción: |
  El topic no tiene subscriptions asociadas.
  Los mensajes publicados se descartarán.

Recomendaciones:
  1. Verificar si topic aún es necesario
  2. Crear subscriptions si es necesario
  3. Eliminar si no se usa
  4. Documentar razón
```

---

## 📊 Umbrales y Reglas

### Tabla de Umbrales

| Categoría | Métrica | Crítico | Warning | Info |
|-----------|---------|---------|---------|------|
| **Capacidad** | Backlog Mensajes | > 100k | > 50k | > 10k |
| **Capacidad** | Edad Mensaje | > 60s | > 30s | > 10s |
| **Capacidad** | Tasa Error | > 5% | > 2% | > 0.5% |
| **Rendimiento** | Latencia P95 | > 5s | > 2s | > 1s |
| **Rendimiento** | Throughput | < 50% | < 70% | < 90% |
| **Rendimiento** | Tasa Descarte | > 1% | > 0.5% | > 0.1% |
| **Configuración** | TTL Mensajes | < 1h | < 6h | < 24h |
| **Seguridad** | Acceso Público | Sí | - | - |
| **Costo** | Incremento | > 20% | > 10% | > 5% |

---

## ⚙️ Configuración

### Archivo de Configuración (alerts.yaml)

```yaml
alerts:
  enabled: true
  check_interval_minutes: 5
  
  categories:
    capacity:
      enabled: true
      thresholds:
        backlog_messages_critical: 100000
        backlog_messages_warning: 50000
        oldest_message_age_critical: 60
        oldest_message_age_warning: 30
        error_rate_critical: 5
        error_rate_warning: 2
    
    performance:
      enabled: true
      thresholds:
        latency_p95_critical_ms: 5000
        latency_p95_warning_ms: 2000
        throughput_warning_percent: 70
        discard_rate_critical: 1
        discard_rate_warning: 0.5
    
    configuration:
      enabled: true
      checks:
        require_dead_letter: true
        require_retry_policy: true
        require_encryption: false
        min_ttl_hours: 1
    
    security:
      enabled: true
      checks:
        check_public_access: true
        check_iam_changes: true
        require_cmek: false
    
    cost:
      enabled: true
      thresholds:
        cost_increase_percent: 20
        min_daily_messages: 1000
        inactivity_days: 30

  notifications:
    enabled: true
    channels:
      email:
        enabled: true
        recipients:
          - ops@company.com
          - devops@company.com
      slack:
        enabled: true
        webhook_url: "https://hooks.slack.com/..."
        channels:
          critical: "#alerts-critical"
          warning: "#alerts-warning"
      pagerduty:
        enabled: true
        integration_key: "..."
        severity_mapping:
          critical: "critical"
          warning: "warning"
```

---

## 📢 Notificaciones

### Canales Soportados

#### Email
```
To: ops@company.com
Subject: [CRITICAL] Backlog Crítico en prod-project/my-subscription
Body: Descripción completa + recomendaciones
```

#### Slack
```
Channel: #alerts-critical
Message:
  🚨 CRITICAL: Backlog Crítico
  Project: prod-project
  Resource: my-subscription
  Value: 150,000 mensajes
  Threshold: 100,000
  Recommendation: Aumentar workers
```

#### PagerDuty
```
Incident:
  Title: Backlog Crítico en my-subscription
  Severity: critical
  Service: Pub/Sub Monitor
  Details: Descripción completa
```

---

## 📈 Escalado de Alertas

### Matriz de Escalado

```
Severidad    | Ventana | Acción              | Escalado
-------------|---------|---------------------|----------
CRITICAL     | 5 min   | Notificación        | Inmediato
             | 10 min  | Escalado            | On-call
             | 15 min  | Escalado            | Manager
             | 30 min  | Escalado            | Director
             |         |                     |
WARNING      | 10 min  | Notificación        | Inmediato
             | 30 min  | Escalado            | On-call
             | 1 hora  | Escalado            | Manager
             |         |                     |
INFO         | -       | Notificación        | Diaria
```

### Procedimiento de Escalado

1. **Nivel 1**: Notificación automática (5 min)
2. **Nivel 2**: Escalado a on-call (10 min)
3. **Nivel 3**: Escalado a manager (15 min)
4. **Nivel 4**: Escalado a director (30 min)

---

## 🔍 Validación de Alertas

### Pruebas Recomendadas

```bash
# Test de alerta de backlog
gcloud pubsub subscriptions pull my-subscription \
  --auto-ack --limit=1000000 &
# Esperar a que se acumule backlog
# Verificar que alerta se dispara

# Test de alerta de error
# Publicar mensajes inválidos
# Verificar que alerta se dispara

# Test de notificación
# Enviar alerta de prueba
# Verificar que se recibe en todos los canales
```

---

**Versión**: 1.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ Sistema de Alertas Completo

