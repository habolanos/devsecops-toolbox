# 🏗️ Arquitectura - Monitoreo Pub/Sub GCP

**Versión**: 1.0  
**Fecha**: 16 de Julio de 2026

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Componentes](#componentes)
3. [Flujos de Datos](#flujos-de-datos)
4. [Integración](#integración)
5. [Escalabilidad](#escalabilidad)
6. [Resiliencia](#resiliencia)

---

## 🎯 Visión General

### Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                      GCP Multi-Project                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Prod Project │  │ Staging Proj │  │  Dev Project │          │
│  │              │  │              │  │              │          │
│  │ • Topics     │  │ • Topics     │  │ • Topics     │          │
│  │ • Subs       │  │ • Subs       │  │ • Subs       │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│                    ┌──────▼──────┐                             │
│                    │ Pub/Sub API  │                             │
│                    │ Monitoring   │                             │
│                    │ Logging      │                             │
│                    └──────┬──────┘                             │
│                           │                                    │
└───────────────────────────┼────────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Monitor App   │
                    │  (Local/Cloud) │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐      ┌──────▼──────┐      ┌────▼────┐
   │ Collector│      │  Analyzer   │      │ Alerter │
   │          │      │             │      │         │
   │ • Topics │      │ • Health    │      │ • Email │
   │ • Subs   │      │ • Metrics   │      │ • Slack │
   │ • Metrics│      │ • Anomalies │      │ • PD    │
   └────┬─────┘      └──────┬──────┘      └────┬────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐      ┌──────▼──────┐      ┌────▼────┐
   │Dashboard │      │   Reports   │      │  Logs   │
   │  (HTML)  │      │ (JSON/Excel)│      │ (Cloud) │
   └──────────┘      └─────────────┘      └─────────┘
```

---

## 🔧 Componentes

### 1. Collector (Recopilador)

**Responsabilidad**: Recopilar datos de Pub/Sub

```
┌─────────────────────────────────────┐
│      PubSubCollector                │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Multi-Project Manager        │  │
│  │ • Iterate projects           │  │
│  │ • Manage credentials         │  │
│  │ • Handle errors              │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Topics Collector             │  │
│  │ • List topics                │  │
│  │ • Get topic config           │  │
│  │ • Extract metadata           │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Subscriptions Collector      │  │
│  │ • List subscriptions         │  │
│  │ • Get subscription config    │  │
│  │ • Extract policies           │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Metrics Collector            │  │
│  │ • Query Cloud Monitoring     │  │
│  │ • Aggregate metrics          │  │
│  │ • Cache results              │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Cache Manager                │  │
│  │ • 1-hour TTL                 │  │
│  │ • Reduce API calls           │  │
│  │ • Improve performance        │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**Entrada**: Configuración de proyectos  
**Salida**: Datos crudos de Pub/Sub + métricas

---

### 2. Analyzer (Analizador)

**Responsabilidad**: Analizar datos y calcular KPIs

```
┌─────────────────────────────────────┐
│      MetricsAnalyzer                │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Health Calculator            │  │
│  │ • Delivery rate              │  │
│  │ • Latency score              │  │
│  │ • Error rate score           │  │
│  │ • Config score               │  │
│  │ • Overall health (0-100)     │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Metrics Aggregator           │  │
│  │ • Calculate averages         │  │
│  │ • Calculate percentiles      │  │
│  │ • Trend analysis             │  │
│  │ • Baseline comparison        │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Anomaly Detector             │  │
│  │ • Z-score analysis           │  │
│  │ • Deviation detection        │  │
│  │ • Pattern recognition        │  │
│  │ • Threshold comparison       │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Issue Identifier             │  │
│  │ • Identify problems          │  │
│  │ • Categorize issues          │  │
│  │ • Suggest solutions          │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**Entrada**: Datos crudos + métricas  
**Salida**: Health scores + anomalías + problemas identificados

---

### 3. Alert Engine (Motor de Alertas)

**Responsabilidad**: Evaluar alertas y generar notificaciones

```
┌─────────────────────────────────────┐
│      AlertEngine                    │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Threshold Evaluator          │  │
│  │ • Load thresholds            │  │
│  │ • Compare values             │  │
│  │ • Determine severity         │  │
│  │ • Generate alerts            │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Alert Deduplicator           │  │
│  │ • Track active alerts        │  │
│  │ • Prevent duplicates         │  │
│  │ • Manage alert lifecycle     │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Notification Manager         │  │
│  │ • Format messages            │  │
│  │ • Route to channels          │  │
│  │ • Handle failures            │  │
│  │ • Retry logic                │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Escalation Manager           │  │
│  │ • Track alert age            │  │
│  │ • Escalate if needed         │  │
│  │ • Notify on-call             │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**Entrada**: Health scores + anomalías  
**Salida**: Alertas + notificaciones

---

### 4. Dashboard Generator (Generador de Dashboards)

**Responsabilidad**: Generar reportes y dashboards

```
┌─────────────────────────────────────┐
│      DashboardGenerator             │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐  │
│  │ HTML Generator               │  │
│  │ • Build HTML structure       │  │
│  │ • Add CSS styling            │  │
│  │ • Embed charts (Plotly)      │  │
│  │ • Add interactivity          │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ JSON Reporter                │  │
│  │ • Serialize data             │  │
│  │ • Pretty print               │  │
│  │ • Validate schema            │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Excel Exporter               │  │
│  │ • Create workbook            │  │
│  │ • Multiple sheets            │  │
│  │ • Format cells               │  │
│  │ • Add charts                 │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Chart Builder                │  │
│  │ • Time series                │  │
│  │ • Bar charts                 │  │
│  │ • Pie charts                 │  │
│  │ • Heatmaps                   │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**Entrada**: Análisis completo + alertas  
**Salida**: Dashboard HTML + JSON + Excel

---

### 5. Orchestrator (Orquestador)

**Responsabilidad**: Coordinar todos los componentes

```
┌─────────────────────────────────────┐
│      PubSubMonitor                  │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Configuration Manager        │  │
│  │ • Load config.json           │  │
│  │ • Validate settings          │  │
│  │ • Manage secrets             │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Workflow Orchestrator        │  │
│  │ • Coordinate components      │  │
│  │ • Handle errors              │  │
│  │ • Manage state               │  │
│  │ • Log execution              │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ CLI Interface                │  │
│  │ • Interactive menu           │  │
│  │ • Command execution          │  │
│  │ • Progress display           │  │
│  │ • Result formatting          │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Scheduler                    │  │
│  │ • Schedule runs              │  │
│  │ • Manage cron jobs           │  │
│  │ • Track execution history    │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**Entrada**: Configuración  
**Salida**: Reportes + alertas + logs

---

## 📊 Flujos de Datos

### Flujo Principal (Full Analysis)

```
START
  │
  ├─► Load Configuration
  │     │
  │     └─► Validate Projects
  │
  ├─► Collect Data (Paralelo)
  │     ├─► Collector.collect_topics()
  │     ├─► Collector.collect_subscriptions()
  │     └─► Collector.collect_metrics()
  │
  ├─► Analyze Data
  │     ├─► Analyzer.calculate_health()
  │     ├─► Analyzer.detect_anomalies()
  │     └─► Analyzer.identify_issues()
  │
  ├─► Evaluate Alerts
  │     ├─► AlertEngine.evaluate_capacity()
  │     ├─► AlertEngine.evaluate_performance()
  │     ├─► AlertEngine.evaluate_configuration()
  │     ├─► AlertEngine.evaluate_security()
  │     └─► AlertEngine.evaluate_cost()
  │
  ├─► Generate Notifications
  │     ├─► Send Email
  │     ├─► Send Slack
  │     └─► Send PagerDuty
  │
  ├─► Generate Reports
  │     ├─► Generate HTML Dashboard
  │     ├─► Generate JSON Report
  │     └─► Generate Excel Report
  │
  ├─► Store Results
  │     ├─► Save to Cloud Storage
  │     ├─► Update Cloud Monitoring
  │     └─► Log to Cloud Logging
  │
  └─► END
```

### Flujo de Alerta

```
Alert Triggered
  │
  ├─► Evaluate Severity
  │     ├─► CRITICAL
  │     ├─► WARNING
  │     └─► INFO
  │
  ├─► Check Deduplication
  │     ├─► Is new alert?
  │     └─► Update existing?
  │
  ├─► Format Message
  │     ├─► Title
  │     ├─► Description
  │     ├─► Metrics
  │     └─► Recommendations
  │
  ├─► Send Notifications
  │     ├─► Email
  │     ├─► Slack
  │     └─► PagerDuty
  │
  ├─► Track Alert
  │     ├─► Store in database
  │     ├─► Set escalation timer
  │     └─► Monitor for resolution
  │
  └─► Alert Resolved
       ├─► Send resolution notification
       └─► Close alert
```

---

## 🔌 Integración

### Integración con GCP

```python
# Pub/Sub API
from google.cloud import pubsub_v1
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Cloud Monitoring API
from google.cloud import monitoring_v3
query_client = monitoring_v3.QueryServiceClient()

# Cloud Logging API
from google.cloud import logging_v2
logging_client = logging_v2.Client()

# Cloud Storage (para reportes)
from google.cloud import storage
storage_client = storage.Client()
```

### Integración con Servicios Externos

```python
# Email (SendGrid)
import sendgrid
from sendgrid.helpers.mail import Mail

# Slack
import slack_sdk
client = slack_sdk.WebClient(token=slack_token)

# PagerDuty
import pdpyras
session = pdpyras.APISession(token=pagerduty_token)
```

---

## 📈 Escalabilidad

### Escalabilidad Horizontal

```
┌─────────────────────────────────────┐
│      Load Balancer                  │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────┐  ┌──────────┐        │
│  │ Monitor  │  │ Monitor  │        │
│  │ Instance │  │ Instance │  ...   │
│  │    1     │  │    2     │        │
│  └──────────┘  └──────────┘        │
│                                     │
│  Shared:                            │
│  • Cloud Firestore (state)          │
│  • Cloud Storage (cache)            │
│  • Cloud Pub/Sub (events)           │
│                                     │
└─────────────────────────────────────┘
```

### Escalabilidad Vertical

- Aumentar CPU/memoria de instancia
- Optimizar queries a APIs
- Implementar caché distribuido
- Usar batch processing

---

## 🛡️ Resiliencia

### Manejo de Errores

```
┌─────────────────────────────────────┐
│      Error Handler                  │
├─────────────────────────────────────┤
│                                     │
│  API Error                          │
│    ├─► Retry (exponential backoff)  │
│    ├─► Fallback to cache            │
│    └─► Alert if persistent          │
│                                     │
│  Network Error                      │
│    ├─► Retry with timeout           │
│    ├─► Use cached data              │
│    └─► Continue with partial data   │
│                                     │
│  Data Error                         │
│    ├─► Log error                    │
│    ├─► Skip invalid data            │
│    └─► Alert on data quality        │
│                                     │
│  Configuration Error                │
│    ├─► Use defaults                 │
│    ├─► Log warning                  │
│    └─► Alert admin                  │
│                                     │
└─────────────────────────────────────┘
```

### Recuperación

- Caché de 24 horas para datos
- Snapshots periódicos de estado
- Logs detallados para debugging
- Alertas de health check

---

**Versión**: 1.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ Arquitectura Completa

