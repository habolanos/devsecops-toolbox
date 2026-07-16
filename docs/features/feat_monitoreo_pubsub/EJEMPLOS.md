# 📚 Ejemplos y Casos de Uso - Monitoreo Pub/Sub GCP

**Versión**: 1.0  
**Fecha**: 16 de Julio de 2026

---

## 📋 Tabla de Contenidos

1. [Configuración Básica](#configuración-básica)
2. [Casos de Uso](#casos-de-uso)
3. [Ejemplos de Código](#ejemplos-de-código)
4. [Escenarios de Alerta](#escenarios-de-alerta)
5. [Troubleshooting](#troubleshooting)

---

## ⚙️ Configuración Básica

### Archivo config.json

```json
{
  "gcp": {
    "projects": [
      {
        "project_id": "prod-project",
        "region": "us-central1",
        "credentials": "~/.config/gcloud/prod-credentials.json"
      },
      {
        "project_id": "staging-project",
        "region": "us-east1",
        "credentials": "~/.config/gcloud/staging-credentials.json"
      },
      {
        "project_id": "dev-project",
        "region": "us-west1",
        "credentials": "~/.config/gcloud/dev-credentials.json"
      }
    ]
  },
  "monitoring": {
    "cache_ttl_hours": 1,
    "metrics_lookback_days": 90,
    "alert_check_interval_minutes": 5
  },
  "alerts": {
    "enabled": true,
    "thresholds": {
      "capacity": {
        "backlog_messages_critical": 100000,
        "backlog_messages_warning": 50000,
        "oldest_message_age_critical": 60,
        "error_rate_critical": 5
      },
      "performance": {
        "latency_p95_critical_ms": 5000,
        "throughput_warning_percent": 70,
        "discard_rate_critical": 1
      },
      "configuration": {
        "require_dead_letter": true,
        "require_retry_policy": true,
        "min_ttl_hours": 1
      }
    },
    "notifications": {
      "email": {
        "enabled": true,
        "recipients": ["ops@company.com", "devops@company.com"]
      },
      "slack": {
        "enabled": true,
        "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
      },
      "pagerduty": {
        "enabled": true,
        "integration_key": "YOUR_PAGERDUTY_KEY"
      }
    }
  },
  "output": {
    "format": ["html", "json", "excel"],
    "directory": "outcome/pubsub_monitor",
    "retention_days": 90
  }
}
```

---

## 🎯 Casos de Uso

### Caso 1: Monitoreo de Producción

**Objetivo**: Supervisión continua de Pub/Sub en ambiente de producción

**Configuración**:
```bash
# Ejecutar cada 5 minutos
*/5 * * * * /usr/local/bin/pubsub-monitor --config config.json --mode production
```

**Alertas Esperadas**:
- Backlog crítico
- Tasa de error elevada
- Latencia P95 elevada
- Cambios en IAM

**Acciones**:
- Notificación inmediata a ops@company.com
- Mensaje en Slack #alerts-critical
- Incident en PagerDuty si es crítico

---

### Caso 2: Análisis de Tendencias

**Objetivo**: Identificar patrones de uso y predecir problemas

**Configuración**:
```bash
# Ejecutar diariamente a las 6 AM
0 6 * * * /usr/local/bin/pubsub-monitor --config config.json --mode analysis --days 90
```

**Análisis**:
- Tendencia de backlog (últimos 90 días)
- Patrones de consumo por hora/día
- Predicción de picos de carga
- Identificación de anomalías

**Salida**:
- Dashboard HTML con gráficos de tendencias
- Reporte JSON con predicciones
- Reporte Excel para ejecutivos

---

### Caso 3: Auditoría de Seguridad

**Objetivo**: Validar configuraciones de seguridad

**Configuración**:
```bash
# Ejecutar semanalmente
0 0 * * 0 /usr/local/bin/pubsub-monitor --config config.json --mode security
```

**Validaciones**:
- Acceso público detectado
- Cambios en IAM sin auditoría
- Encriptación no habilitada
- Políticas de retención insuficientes

**Salida**:
- Reporte de cumplimiento
- Recomendaciones de seguridad
- Matriz de riesgos

---

### Caso 4: Optimización de Costos

**Objetivo**: Identificar oportunidades de ahorro

**Configuración**:
```bash
# Ejecutar mensualmente
0 0 1 * * /usr/local/bin/pubsub-monitor --config config.json --mode cost
```

**Análisis**:
- Subscriptions inactivas (> 30 días)
- Topics sin consumidores
- Incremento de costo vs mes anterior
- Oportunidades de consolidación

**Salida**:
- Reporte de costos por proyecto
- Recomendaciones de ahorro
- Estimación de ROI

---

### Caso 5: Troubleshooting

**Objetivo**: Diagnóstico rápido de problemas

**Comando**:
```bash
# Análisis inmediato de un proyecto
pubsub-monitor --config config.json --project prod-project --mode debug
```

**Información Recopilada**:
- Estado actual de todos los topics/subscriptions
- Métricas de últimas 24 horas
- Alertas activas
- Logs de error recientes
- Recomendaciones de resolución

**Salida**:
- Reporte detallado en JSON
- Sugerencias de acciones correctivas

---

## 💻 Ejemplos de Código

### Ejemplo 1: Recopilar Datos de un Proyecto

```python
from pubsub_collector import PubSubCollector

# Configurar collector
config = {
    "project_id": "prod-project",
    "region": "us-central1",
    "credentials": "~/.config/gcloud/credentials.json"
}

collector = PubSubCollector([config])

# Recopilar topics
topics = collector.collect_topics("prod-project")
for topic in topics:
    print(f"Topic: {topic['display_name']}")
    print(f"  Created: {topic['created_at']}")
    print(f"  TTL: {topic['message_retention_duration']}")
    print()

# Recopilar subscriptions
subscriptions = collector.collect_subscriptions("prod-project")
for sub in subscriptions:
    print(f"Subscription: {sub['display_name']}")
    print(f"  Topic: {sub['topic']}")
    print(f"  Ack Deadline: {sub['ack_deadline_seconds']}s")
    print()

# Recopilar métricas
metrics = collector.collect_metrics("prod-project", "pubsub_subscription")
for resource_id, metric_data in metrics.items():
    print(f"Subscription: {resource_id}")
    for metric_name, values in metric_data.items():
        print(f"  {metric_name}: {values['latest']}")
```

### Ejemplo 2: Calcular Health Score

```python
from metrics_analyzer import MetricsAnalyzer

analyzer = MetricsAnalyzer(metrics_data)

# Calcular salud de un topic
topic_data = {
    "name": "projects/prod/topics/orders",
    "publish_rate": 1000,  # msgs/min
    "avg_message_size": 512,  # bytes
    "oldest_message_age": 30,  # seconds
    "error_rate": 0.1  # %
}

health = analyzer.calculate_topic_health(topic_data)
print(f"Topic: {health['topic_id']}")
print(f"Health Score: {health['health_score']}/100")
print(f"Status: {health['status']}")
print(f"Issues: {health['issues']}")

# Calcular salud de una subscription
sub_data = {
    "name": "projects/prod/subscriptions/orders-processor",
    "backlog_messages": 5000,
    "backlog_bytes": 5242880,
    "ack_rate": 95.5,
    "nack_rate": 2.1,
    "delivery_latency_p95": 2.5
}

health = analyzer.calculate_subscription_health(sub_data)
print(f"Subscription: {health['subscription_id']}")
print(f"Health Score: {health['health_score']}/100")
print(f"Status: {health['status']}")
```

### Ejemplo 3: Evaluar Alertas

```python
from alert_engine import AlertEngine

alert_engine = AlertEngine(config)

# Evaluar alertas de capacidad
subscription = {
    "name": "my-subscription",
    "backlog_messages": 150000,
    "oldest_unacked_message_age": 120,
    "error_rate": 8.5
}

alerts = alert_engine.evaluate_capacity_alerts(subscription)
for alert in alerts:
    print(f"[{alert['severity']}] {alert['message']}")
    print(f"  Metric: {alert['metric']}")
    print(f"  Value: {alert['value']}")
    print(f"  Threshold: {alert['threshold']}")
    print(f"  Recommendation: {alert['recommendation']}")
    print()

# Evaluar alertas de configuración
config_alerts = alert_engine.evaluate_configuration_alerts(subscription)
for alert in config_alerts:
    print(f"[{alert['severity']}] {alert['message']}")
    print(f"  Recommendation: {alert['recommendation']}")
```

### Ejemplo 4: Generar Dashboard

```python
from dashboard_generator import DashboardGenerator

# Preparar datos
results = {
    "timestamp": "2026-07-16T10:30:00Z",
    "projects": {
        "prod-project": {
            "total_topics": 25,
            "total_subscriptions": 50,
            "healthy_topics": 23,
            "healthy_subscriptions": 48,
            "delivery_success_rate": 99.0,
            "avg_latency_ms": 250,
            "alerts": [...]
        }
    }
}

# Generar dashboard
dashboard = DashboardGenerator(results)
html_path = dashboard.generate_dashboard("outcome/dashboard.html")
json_path = dashboard.generate_json_report("outcome/report.json")
excel_path = dashboard.generate_excel_report("outcome/report.xlsx")

print(f"Dashboard: {html_path}")
print(f"JSON Report: {json_path}")
print(f"Excel Report: {excel_path}")
```

### Ejemplo 5: Ejecutar Análisis Completo

```python
from pubsub_monitor import PubSubMonitor

# Crear monitor
monitor = PubSubMonitor("config.json")

# Ejecutar análisis completo
results = monitor.run_full_analysis()

# Generar reportes
reports = monitor.generate_reports(results, "outcome/pubsub_monitor")

print("Análisis Completado")
print(f"Dashboard: {reports['html']}")
print(f"JSON: {reports['json']}")
print(f"Excel: {reports['excel']}")

# Mostrar resumen
for project_id, project_data in results["projects"].items():
    print(f"\nProyecto: {project_id}")
    print(f"  Topics: {len(project_data['topics'])}")
    print(f"  Subscriptions: {len(project_data['subscriptions'])}")
    print(f"  Alertas: {len(project_data['alerts'])}")
```

---

## 🚨 Escenarios de Alerta

### Escenario 1: Backlog Crítico

**Situación**: Subscription con 150,000 mensajes sin entregar

**Alertas Generadas**:
1. **CRITICAL**: Backlog Crítico Detectado
   - Value: 150,000 mensajes
   - Threshold: 100,000
   - Recommendation: Aumentar workers

2. **WARNING**: Retraso de Entrega Elevado
   - Oldest message: 90 segundos
   - Threshold: 60 segundos

**Notificaciones**:
- Email a ops@company.com
- Slack en #alerts-critical
- PagerDuty incident creado

**Acciones Recomendadas**:
1. Verificar salud del consumidor
2. Aumentar número de workers
3. Revisar logs de error
4. Escalar recursos si es necesario

---

### Escenario 2: Tasa de Error Elevada

**Situación**: 8.5% de mensajes siendo rechazados

**Alertas Generadas**:
1. **CRITICAL**: Tasa de Error Crítica
   - Value: 8.5%
   - Threshold: 5%

2. **WARNING**: Configuración de Retry Insuficiente
   - Recommendation: Revisar retry policy

**Notificaciones**:
- Email a devops@company.com
- Slack en #alerts-warning

**Acciones Recomendadas**:
1. Revisar logs de aplicación
2. Verificar formato de mensajes
3. Aumentar retry policy
4. Validar dependencias externas

---

### Escenario 3: Configuración de Seguridad

**Situación**: Topic sin encriptación CMEK

**Alertas Generadas**:
1. **WARNING**: Encriptación No Habilitada
   - Recommendation: Habilitar CMEK

**Notificaciones**:
- Email a security@company.com
- Slack en #alerts-security

**Acciones Recomendadas**:
1. Crear Cloud KMS key
2. Habilitar CMEK en topic
3. Auditar acceso
4. Documentar cambio

---

## 🔧 Troubleshooting

### Problema: "No se pueden recopilar métricas"

**Causa Posible**: Permisos insuficientes

**Solución**:
```bash
# Verificar permisos
gcloud projects get-iam-policy prod-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount@*"

# Otorgar permisos necesarios
gcloud projects add-iam-policy-binding prod-project \
  --member=serviceAccount:monitor@prod-project.iam.gserviceaccount.com \
  --role=roles/monitoring.metricReader
```

### Problema: "Alertas no se envían"

**Causa Posible**: Webhook de Slack inválido

**Solución**:
```bash
# Probar webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Actualizar config.json con webhook correcto
```

### Problema: "Dashboard no se genera"

**Causa Posible**: Falta de permisos en directorio de salida

**Solución**:
```bash
# Crear directorio
mkdir -p outcome/pubsub_monitor

# Dar permisos
chmod 755 outcome/pubsub_monitor

# Ejecutar de nuevo
pubsub-monitor --config config.json
```

---

**Versión**: 1.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ Ejemplos Completados

