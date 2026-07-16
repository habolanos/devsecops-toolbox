# 🔧 Especificación Técnica - Monitoreo Pub/Sub GCP

**Versión**: 1.0  
**Fecha**: 16 de Julio de 2026  
**Autor**: DevSecOps Team

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Módulos Técnicos](#módulos-técnicos)
3. [APIs Utilizadas](#apis-utilizadas)
4. [Estructura de Datos](#estructura-de-datos)
5. [Algoritmos](#algoritmos)
6. [Configuración](#configuración)
7. [Integración](#integración)

---

## 🎯 Visión General

### Objetivo
Crear un sistema de monitoreo profesional para Google Cloud Pub/Sub que:
- Recopile datos de múltiples proyectos GCP
- Analice métricas en tiempo real
- Genere alertas preventivas automáticas
- Produzca dashboards y reportes ejecutivos

### Scope
- **Plataforma**: Google Cloud Platform (GCP)
- **Servicio**: Cloud Pub/Sub
- **Proyectos**: Múltiples (configurable)
- **Métricas**: 20+ KPIs por proyecto
- **Alertas**: 5 categorías, 25+ reglas
- **Salida**: Dashboard, JSON, Excel, HTML

---

## 🏗️ Módulos Técnicos

### 1. pubsub_collector.py (~400 líneas)

**Responsabilidad**: Recopilación de datos de Pub/Sub

```python
class PubSubCollector:
    """Recopila datos de Pub/Sub de múltiples proyectos."""
    
    def __init__(self, projects: List[Dict]):
        """
        Args:
            projects: Lista de configuraciones de proyectos
                [
                    {
                        "project_id": "prod-project",
                        "region": "us-central1",
                        "credentials": "path/to/creds.json"
                    }
                ]
        """
        self.projects = projects
        self.cache = {}
        self.cache_ttl = 3600  # 1 hora
    
    def collect_topics(self, project_id: str) -> List[Dict]:
        """
        Recopila información de todos los topics.
        
        Returns:
            [
                {
                    "name": "projects/proj/topics/topic-name",
                    "display_name": "topic-name",
                    "message_retention_duration": "604800s",
                    "labels": {"env": "prod"},
                    "kms_key_name": "...",
                    "created_at": "2026-01-01T00:00:00Z"
                }
            ]
        """
        pass
    
    def collect_subscriptions(self, project_id: str) -> List[Dict]:
        """
        Recopila información de todas las subscriptions.
        
        Returns:
            [
                {
                    "name": "projects/proj/subscriptions/sub-name",
                    "topic": "projects/proj/topics/topic-name",
                    "push_config": {...},
                    "ack_deadline_seconds": 60,
                    "message_retention_duration": "604800s",
                    "dead_letter_policy": {...},
                    "retry_policy": {...},
                    "created_at": "2026-01-01T00:00:00Z"
                }
            ]
        """
        pass
    
    def collect_metrics(self, project_id: str, 
                       resource_type: str) -> Dict:
        """
        Recopila métricas de Cloud Monitoring.
        
        Args:
            project_id: ID del proyecto
            resource_type: "pubsub_topic" o "pubsub_subscription"
        
        Returns:
            {
                "resource_id": {
                    "metric_name": {
                        "values": [1000, 1100, 1200],
                        "timestamps": ["2026-01-01T00:00:00Z", ...],
                        "latest": 1200,
                        "average": 1100,
                        "max": 1200,
                        "min": 1000
                    }
                }
            }
        """
        pass
    
    def get_cached_data(self, key: str) -> Optional[Dict]:
        """Obtiene datos del caché si están vigentes."""
        pass
    
    def set_cached_data(self, key: str, data: Dict) -> None:
        """Almacena datos en caché con TTL."""
        pass
```

**Métricas a Recopilar**:
- `pubsub.googleapis.com/subscription/num_undelivered_messages`
- `pubsub.googleapis.com/subscription/oldest_unacked_message_age`
- `pubsub.googleapis.com/subscription/backlog_bytes`
- `pubsub.googleapis.com/subscription/pull_message_operation_count`
- `pubsub.googleapis.com/topic/publish_message_operation_count`
- `pubsub.googleapis.com/topic/publish_message_sizes`

---

### 2. metrics_analyzer.py (~350 líneas)

**Responsabilidad**: Análisis de métricas y cálculo de KPIs

```python
class MetricsAnalyzer:
    """Analiza métricas de Pub/Sub."""
    
    def __init__(self, metrics_data: Dict):
        self.metrics = metrics_data
        self.kpis = {}
    
    def calculate_topic_health(self, topic_data: Dict) -> Dict:
        """
        Calcula salud de un topic.
        
        Returns:
            {
                "topic_id": "topic-name",
                "health_score": 85,  # 0-100
                "status": "healthy",  # healthy, warning, critical
                "metrics": {
                    "publish_rate": 1000,  # msgs/min
                    "avg_message_size": 512,  # bytes
                    "oldest_message_age": 30,  # seconds
                    "error_rate": 0.1  # %
                },
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Mensaje antiguo detectado"
                    }
                ]
            }
        """
        pass
    
    def calculate_subscription_health(self, 
                                     sub_data: Dict) -> Dict:
        """
        Calcula salud de una subscription.
        
        Returns:
            {
                "subscription_id": "sub-name",
                "health_score": 75,  # 0-100
                "status": "warning",
                "metrics": {
                    "backlog_messages": 5000,
                    "backlog_bytes": 5242880,  # 5 MB
                    "ack_rate": 95.5,  # %
                    "nack_rate": 2.1,  # %
                    "delivery_latency_p95": 2.5  # seconds
                },
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Backlog elevado"
                    }
                ]
            }
        """
        pass
    
    def detect_anomalies(self, historical_data: List[Dict]) -> List[Dict]:
        """
        Detecta anomalías usando análisis estadístico.
        
        Returns:
            [
                {
                    "resource_id": "topic-name",
                    "metric": "publish_rate",
                    "expected_value": 1000,
                    "actual_value": 5000,
                    "deviation_percent": 400,
                    "severity": "critical"
                }
            ]
        """
        pass
    
    def calculate_project_summary(self, 
                                 project_id: str) -> Dict:
        """
        Calcula resumen del proyecto.
        
        Returns:
            {
                "project_id": "prod-project",
                "total_topics": 25,
                "total_subscriptions": 50,
                "healthy_topics": 23,
                "healthy_subscriptions": 48,
                "total_messages_published": 1000000,
                "total_messages_delivered": 990000,
                "delivery_success_rate": 99.0,
                "avg_latency_ms": 250,
                "cost_estimate_monthly": 1500
            }
        """
        pass
```

---

### 3. alert_engine.py (~300 líneas)

**Responsabilidad**: Evaluación de alertas y detección de patrones

```python
class AlertEngine:
    """Motor de alertas para Pub/Sub."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.alerts = []
        self.thresholds = self._load_thresholds()
    
    def _load_thresholds(self) -> Dict:
        """Carga umbrales de configuración."""
        return {
            "capacity": {
                "backlog_messages_critical": 100000,
                "backlog_messages_warning": 50000,
                "delivery_latency_critical": 60,  # seconds
                "error_rate_critical": 5  # %
            },
            "performance": {
                "latency_p95_critical": 5000,  # ms
                "throughput_warning": 50,  # % of expected
                "discard_rate_critical": 1  # %
            },
            "configuration": {
                "min_ttl_hours": 1,
                "require_dead_letter": True,
                "require_retry_policy": True
            },
            "security": {
                "require_encryption": True,
                "require_kms": False
            },
            "cost": {
                "cost_increase_percent": 20,
                "min_daily_messages": 1000
            }
        }
    
    def evaluate_capacity_alerts(self, 
                                subscription_data: Dict) -> List[Dict]:
        """Evalúa alertas de capacidad."""
        alerts = []
        
        backlog = subscription_data.get("backlog_messages", 0)
        if backlog > self.thresholds["capacity"]["backlog_messages_critical"]:
            alerts.append({
                "category": "capacity",
                "severity": "critical",
                "metric": "backlog_messages",
                "value": backlog,
                "threshold": self.thresholds["capacity"]["backlog_messages_critical"],
                "message": f"Backlog crítico: {backlog} mensajes",
                "recommendation": "Aumentar tasa de consumo o escalar workers"
            })
        
        return alerts
    
    def evaluate_performance_alerts(self, 
                                   metrics: Dict) -> List[Dict]:
        """Evalúa alertas de rendimiento."""
        pass
    
    def evaluate_configuration_alerts(self, 
                                     resource_config: Dict) -> List[Dict]:
        """Evalúa alertas de configuración."""
        alerts = []
        
        # Verificar dead-letter policy
        if self.thresholds["configuration"]["require_dead_letter"]:
            if not resource_config.get("dead_letter_policy"):
                alerts.append({
                    "category": "configuration",
                    "severity": "warning",
                    "message": "Dead-letter policy no configurada",
                    "recommendation": "Habilitar dead-letter topic para mensajes fallidos"
                })
        
        return alerts
    
    def evaluate_security_alerts(self, 
                                resource_config: Dict) -> List[Dict]:
        """Evalúa alertas de seguridad."""
        pass
    
    def evaluate_cost_alerts(self, 
                            cost_data: Dict) -> List[Dict]:
        """Evalúa alertas de costo."""
        pass
    
    def generate_alert_report(self, 
                             all_alerts: List[Dict]) -> Dict:
        """
        Genera reporte de alertas.
        
        Returns:
            {
                "total_alerts": 15,
                "critical": 3,
                "warning": 7,
                "info": 5,
                "by_category": {
                    "capacity": 5,
                    "performance": 4,
                    "configuration": 3,
                    "security": 2,
                    "cost": 1
                },
                "alerts": [...]
            }
        """
        pass
```

---

### 4. dashboard_generator.py (~400 líneas)

**Responsabilidad**: Generación de dashboards y reportes

```python
class DashboardGenerator:
    """Genera dashboards HTML interactivos."""
    
    def __init__(self, data: Dict):
        self.data = data
        self.html_template = self._load_template()
    
    def generate_dashboard(self, output_path: str) -> str:
        """
        Genera dashboard HTML completo.
        
        Returns:
            Ruta del archivo HTML generado
        """
        html = self._build_html_structure()
        html += self._add_header()
        html += self._add_summary_section()
        html += self._add_projects_section()
        html += self._add_alerts_section()
        html += self._add_metrics_section()
        html += self._add_charts_section()
        html += self._add_footer()
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        return output_path
    
    def _add_summary_section(self) -> str:
        """Sección de resumen ejecutivo."""
        return """
        <section class="summary">
            <h2>Resumen Ejecutivo</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Proyectos Monitoreados</h3>
                    <p class="metric-value">{projects_count}</p>
                </div>
                <div class="metric-card">
                    <h3>Topics Totales</h3>
                    <p class="metric-value">{total_topics}</p>
                </div>
                <div class="metric-card">
                    <h3>Subscriptions Totales</h3>
                    <p class="metric-value">{total_subscriptions}</p>
                </div>
                <div class="metric-card">
                    <h3>Tasa de Entrega</h3>
                    <p class="metric-value">{delivery_rate}%</p>
                </div>
            </div>
        </section>
        """
    
    def _add_alerts_section(self) -> str:
        """Sección de alertas con tabla interactiva."""
        pass
    
    def _add_charts_section(self) -> str:
        """Sección de gráficos con Plotly."""
        pass
    
    def generate_json_report(self, output_path: str) -> str:
        """Genera reporte en formato JSON."""
        pass
    
    def generate_excel_report(self, output_path: str) -> str:
        """Genera reporte en formato Excel con múltiples hojas."""
        pass
```

---

### 5. pubsub_monitor.py (~200 líneas)

**Responsabilidad**: Orquestación principal

```python
class PubSubMonitor:
    """Orquestador principal del sistema de monitoreo."""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.collector = PubSubCollector(self.config["gcp"]["projects"])
        self.analyzer = MetricsAnalyzer({})
        self.alert_engine = AlertEngine(self.config)
        self.dashboard = DashboardGenerator({})
    
    def run_full_analysis(self) -> Dict:
        """
        Ejecuta análisis completo.
        
        Flujo:
        1. Recopila datos de todos los proyectos
        2. Analiza métricas
        3. Evalúa alertas
        4. Genera reportes
        5. Almacena resultados
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "projects": {}
        }
        
        for project in self.config["gcp"]["projects"]:
            project_id = project["project_id"]
            
            # Recopilación
            topics = self.collector.collect_topics(project_id)
            subscriptions = self.collector.collect_subscriptions(project_id)
            metrics = self.collector.collect_metrics(project_id, "pubsub_topic")
            
            # Análisis
            topic_health = [
                self.analyzer.calculate_topic_health(t) 
                for t in topics
            ]
            sub_health = [
                self.analyzer.calculate_subscription_health(s) 
                for s in subscriptions
            ]
            
            # Alertas
            alerts = []
            for sub in subscriptions:
                alerts.extend(self.alert_engine.evaluate_capacity_alerts(sub))
                alerts.extend(self.alert_engine.evaluate_configuration_alerts(sub))
            
            results["projects"][project_id] = {
                "topics": topic_health,
                "subscriptions": sub_health,
                "alerts": alerts,
                "summary": self.analyzer.calculate_project_summary(project_id)
            }
        
        return results
    
    def generate_reports(self, results: Dict, 
                        output_dir: str) -> Dict:
        """Genera todos los reportes."""
        self.dashboard.data = results
        
        return {
            "html": self.dashboard.generate_dashboard(
                f"{output_dir}/dashboard.html"
            ),
            "json": self.dashboard.generate_json_report(
                f"{output_dir}/report.json"
            ),
            "excel": self.dashboard.generate_excel_report(
                f"{output_dir}/report.xlsx"
            )
        }
```

---

## 🔌 APIs Utilizadas

### Google Cloud Pub/Sub API

```python
from google.cloud import pubsub_v1

# Listar topics
publisher = pubsub_v1.PublisherClient()
project_path = publisher.project_path(project_id)
topics = publisher.list_topics(request={"project": project_path})

# Listar subscriptions
subscriber = pubsub_v1.SubscriberClient()
subscriptions = subscriber.list_subscriptions(
    request={"project": project_path}
)
```

### Cloud Monitoring API

```python
from google.cloud import monitoring_v3

# Leer métricas
query = monitoring_v3.QueryTimeSeriesRequest(
    name=project_name,
    query="fetch pubsub_subscription | metric 'pubsub.googleapis.com/subscription/num_undelivered_messages'"
)
results = client.query_time_series(request=query)
```

### Cloud Logging API

```python
from google.cloud import logging_v2

# Leer logs
client = logging_v2.Client()
entries = client.list_entries(
    filter_=f"resource.type=pubsub_subscription AND resource.labels.project_id={project_id}"
)
```

---

## 📊 Estructura de Datos

### Configuración (config.json)

```json
{
  "gcp": {
    "projects": [
      {
        "project_id": "prod-project",
        "region": "us-central1",
        "credentials": "path/to/credentials.json"
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
        "backlog_messages_warning": 50000
      }
    },
    "notifications": {
      "email": ["ops@company.com"],
      "slack": "https://hooks.slack.com/...",
      "pagerduty": "https://events.pagerduty.com/..."
    }
  },
  "output": {
    "format": ["html", "json", "excel"],
    "directory": "outcome/pubsub_monitor"
  }
}
```

### Estructura de Alerta

```json
{
  "id": "alert_123456",
  "timestamp": "2026-07-16T10:30:00Z",
  "project_id": "prod-project",
  "resource_type": "pubsub_subscription",
  "resource_id": "my-subscription",
  "category": "capacity",
  "severity": "critical",
  "metric": "backlog_messages",
  "current_value": 150000,
  "threshold": 100000,
  "message": "Backlog crítico detectado",
  "recommendation": "Aumentar tasa de consumo",
  "status": "open",
  "created_at": "2026-07-16T10:30:00Z",
  "acknowledged_at": null,
  "resolved_at": null
}
```

---

## 🧮 Algoritmos

### Cálculo de Health Score

```
Health Score = (W1 * Delivery Rate) + (W2 * Latency Score) + 
               (W3 * Error Rate Score) + (W4 * Config Score)

Donde:
- W1 = 0.4 (peso de tasa de entrega)
- W2 = 0.3 (peso de latencia)
- W3 = 0.2 (peso de tasa de error)
- W4 = 0.1 (peso de configuración)

Delivery Rate Score = (delivered_messages / published_messages) * 100
Latency Score = max(0, 100 - (latency_ms / 50))
Error Rate Score = max(0, 100 - (error_rate * 20))
Config Score = (configured_features / total_features) * 100
```

### Detección de Anomalías

```
Usa Z-Score para detectar desviaciones:

Z-Score = (X - μ) / σ

Donde:
- X = valor actual
- μ = media histórica
- σ = desviación estándar

Umbral de anomalía: |Z-Score| > 2.5
```

---

## 🔐 Seguridad

- ✅ Autenticación con Google Cloud Service Account
- ✅ Encriptación de credenciales en config.json
- ✅ Validación de permisos IAM
- ✅ Auditoría de accesos
- ✅ Sanitización de datos sensibles en reportes

---

**Versión**: 1.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ Especificación Completa

