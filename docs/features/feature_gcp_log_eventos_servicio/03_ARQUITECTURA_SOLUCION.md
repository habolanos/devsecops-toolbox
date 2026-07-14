# 🏗️ Arquitectura de la Solución

## 1. Visión General

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event Tracker CLI                             │
│  gcp_event_tracker.py --component-name my-service               │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌──────────┐
    │   GCP   │    │   GCP   │    │Kubernetes│
    │ Logging │    │Monitoring│   │  Events  │
    └────┬────┘    └────┬────┘    └────┬─────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
         ┌──────────────▼──────────────┐
         │   Event Aggregator          │
         │  - Normalización            │
         │  - Deduplicación            │
         │  - Correlación              │
         └──────────────┬──────────────┘
                        │
         ┌──────────────▼──────────────┐
         │   Report Generator          │
         │  - JSON / CSV / HTML        │
         │  - Timeline                 │
         │  - Análisis                 │
         └──────────────┬──────────────┘
                        │
         ┌──────────────▼──────────────┐
         │   Output                    │
         │  - Archivo                  │
         │  - Consola                  │
         │  - Email                    │
         └─────────────────────────────┘
```

---

## 2. Componentes Principales

### 2.1 Event Collector

**Responsabilidad**: Recopilar eventos de todas las fuentes.

```python
class EventCollector:
    def __init__(self, project_id, credentials):
        self.project_id = project_id
        self.credentials = credentials
        
    def collect_from_cloud_logging(self, component_name, start_time, end_time):
        """Recopila logs de Cloud Logging"""
        # Implementación
        
    def collect_from_cloud_monitoring(self, component_name, start_time, end_time):
        """Recopila métricas de Cloud Monitoring"""
        # Implementación
        
    def collect_from_audit_logs(self, component_name, start_time, end_time):
        """Recopila audit logs"""
        # Implementación
        
    def collect_from_kubernetes(self, component_name, start_time, end_time):
        """Recopila eventos de Kubernetes"""
        # Implementación
        
    def collect_from_cloud_events(self, component_name, start_time, end_time):
        """Recopila Cloud Events"""
        # Implementación
```

**Fuentes**:
- Cloud Logging API
- Cloud Monitoring API
- Cloud Audit Logs API
- Kubernetes Events API
- Cloud Events API

---

### 2.2 Event Normalizer

**Responsabilidad**: Normalizar eventos de diferentes fuentes a un formato común.

```python
class EventNormalizer:
    def normalize(self, raw_event, source_type):
        """Normaliza un evento a formato estándar"""
        return {
            'timestamp': event.timestamp,
            'component_name': event.component_name,
            'event_type': event.type,
            'severity': event.severity,
            'message': event.message,
            'source': source_type,
            'metadata': event.metadata,
            'raw': raw_event
        }
```

**Formato Normalizado**:

```python
{
    'timestamp': '2026-07-13T10:30:00Z',
    'component_name': 'my-service',
    'event_type': 'error',
    'severity': 'high',
    'message': 'Application crashed',
    'source': 'cloud_logging',
    'metadata': {
        'pod_name': 'my-service-abc123',
        'namespace': 'default',
        'container': 'my-service',
        'exit_code': 1
    },
    'raw': {...}
}
```

---

### 2.3 Event Deduplicator

**Responsabilidad**: Eliminar eventos duplicados de múltiples fuentes.

```python
class EventDeduplicator:
    def deduplicate(self, events):
        """Elimina eventos duplicados"""
        seen = {}
        unique_events = []
        
        for event in events:
            key = self._generate_key(event)
            if key not in seen:
                seen[key] = event
                unique_events.append(event)
        
        return unique_events
    
    def _generate_key(self, event):
        """Genera clave única para un evento"""
        return (
            event['timestamp'],
            event['component_name'],
            event['event_type'],
            event['message']
        )
```

---

### 2.4 Event Correlator

**Responsabilidad**: Correlacionar eventos relacionados.

```python
class EventCorrelator:
    def correlate(self, events):
        """Correlaciona eventos relacionados"""
        correlations = []
        
        for i, event1 in enumerate(events):
            for event2 in events[i+1:]:
                if self._are_related(event1, event2):
                    correlations.append({
                        'event1': event1,
                        'event2': event2,
                        'relationship': self._get_relationship(event1, event2)
                    })
        
        return correlations
    
    def _are_related(self, event1, event2):
        """Determina si dos eventos están relacionados"""
        # Mismo componente
        if event1['component_name'] != event2['component_name']:
            return False
        
        # Timestamps cercanos (dentro de 5 minutos)
        time_diff = abs(
            datetime.fromisoformat(event1['timestamp']) -
            datetime.fromisoformat(event2['timestamp'])
        )
        if time_diff > timedelta(minutes=5):
            return False
        
        return True
```

---

### 2.5 Report Generator

**Responsabilidad**: Generar reportes en múltiples formatos.

```python
class ReportGenerator:
    def generate_json(self, events, correlations):
        """Genera reporte en JSON"""
        return {
            'summary': self._generate_summary(events),
            'timeline': self._generate_timeline(events),
            'events': events,
            'correlations': correlations,
            'analysis': self._analyze(events)
        }
    
    def generate_csv(self, events):
        """Genera reporte en CSV"""
        # Implementación
        
    def generate_html(self, events, correlations):
        """Genera reporte en HTML"""
        # Implementación
        
    def generate_markdown(self, events, correlations):
        """Genera reporte en Markdown"""
        # Implementación
```

---

## 3. Flujo de Datos

```
1. INPUT
   └─ component_name: "my-service"
   └─ start_time: "2026-07-13T00:00:00Z"
   └─ end_time: "2026-07-14T00:00:00Z"

2. COLLECTION
   ├─ Cloud Logging
   │  └─ 150 eventos
   ├─ Cloud Monitoring
   │  └─ 45 eventos
   ├─ Audit Logs
   │  └─ 12 eventos
   ├─ Kubernetes Events
   │  └─ 78 eventos
   └─ Cloud Events
      └─ 23 eventos
   
   Total: 308 eventos

3. NORMALIZATION
   └─ Convertir a formato estándar
   └─ 308 eventos normalizados

4. DEDUPLICATION
   └─ Eliminar duplicados
   └─ 245 eventos únicos

5. CORRELATION
   └─ Agrupar eventos relacionados
   └─ 12 grupos de correlación

6. ANALYSIS
   ├─ Identificar causa raíz
   ├─ Calcular duración de incidente
   ├─ Generar timeline
   └─ Crear recomendaciones

7. REPORT GENERATION
   ├─ JSON
   ├─ CSV
   ├─ HTML
   └─ Markdown

8. OUTPUT
   └─ Archivo / Consola / Email
```

---

## 4. Estructura de Directorios

```
scm/gcp/event-tracker/
├── __init__.py
├── event_tracker.py              # Orquestador principal
├── collectors/
│   ├── __init__.py
│   ├── base.py                   # Clase base
│   ├── cloud_logging.py          # Cloud Logging
│   ├── cloud_monitoring.py       # Cloud Monitoring
│   ├── audit_logs.py             # Audit Logs
│   ├── kubernetes_events.py      # Kubernetes Events
│   └── cloud_events.py           # Cloud Events
├── processors/
│   ├── __init__.py
│   ├── normalizer.py             # Normalización
│   ├── deduplicator.py           # Deduplicación
│   ├── correlator.py             # Correlación
│   └── analyzer.py               # Análisis
├── reporters/
│   ├── __init__.py
│   ├── base.py                   # Clase base
│   ├── json_reporter.py          # JSON
│   ├── csv_reporter.py           # CSV
│   ├── html_reporter.py          # HTML
│   └── markdown_reporter.py      # Markdown
├── models/
│   ├── __init__.py
│   ├── event.py                  # Modelo de evento
│   └── correlation.py            # Modelo de correlación
├── utils/
│   ├── __init__.py
│   ├── time_utils.py             # Utilidades de tiempo
│   ├── auth_utils.py             # Autenticación
│   └── formatting.py             # Formateo
└── tests/
    ├── test_collectors.py
    ├── test_processors.py
    ├── test_reporters.py
    └── test_integration.py
```

---

## 5. Configuración

### 5.1 config.yaml

```yaml
gcp:
  project_id: "my-project"
  credentials_file: "service-account-key.json"
  
kubernetes:
  cluster_name: "my-cluster"
  zone: "us-central1-a"
  kubeconfig: "~/.kube/config"
  
logging:
  cloud_logging:
    enabled: true
    batch_size: 100
  cloud_monitoring:
    enabled: true
    batch_size: 50
  audit_logs:
    enabled: true
    batch_size: 50
  kubernetes_events:
    enabled: true
    batch_size: 100
  cloud_events:
    enabled: true
    batch_size: 50

processing:
  deduplication:
    enabled: true
    time_window: 60  # segundos
  correlation:
    enabled: true
    time_window: 300  # segundos
  analysis:
    enabled: true

output:
  formats:
    - json
    - csv
    - html
    - markdown
  destination: "outcome/event-reports"
  
limits:
  max_events: 10000
  max_time_range: 7  # días
```

---

## 6. Casos de Uso

### 6.1 Investigación de Incidente

```
Usuario: "Mi servicio Cloud Run cayó hace 2 horas"

Comando:
$ python event_tracker.py \
  --component-name "my-cloud-run-service" \
  --start-time "2026-07-13T08:00:00Z" \
  --end-time "2026-07-13T10:00:00Z" \
  --output-format html

Resultado:
- Timeline completo del incidente
- Eventos correlacionados
- Causa raíz identificada
- Recomendaciones
```

### 6.2 Análisis de Rendimiento

```
Usuario: "Quiero analizar por qué mi servicio tuvo latencia alta"

Comando:
$ python event_tracker.py \
  --component-name "my-service" \
  --start-time "2026-07-13T00:00:00Z" \
  --end-time "2026-07-13T23:59:59Z" \
  --include-metrics \
  --output-format json

Resultado:
- Eventos de error correlacionados con métricas
- Picos de latencia identificados
- Causas potenciales
```

### 6.3 Auditoría de Cambios

```
Usuario: "Quiero ver todos los cambios realizados a mi servicio"

Comando:
$ python event_tracker.py \
  --component-name "my-service" \
  --start-time "2026-07-01T00:00:00Z" \
  --end-time "2026-07-14T00:00:00Z" \
  --include-audit-logs \
  --output-format csv

Resultado:
- Todos los cambios de configuración
- Quién hizo cada cambio
- Cuándo se realizó
- Impacto de cada cambio
```

---

## 7. Requisitos No Funcionales

### 7.1 Performance

- Procesar 10,000 eventos en < 30 segundos
- Generar reporte HTML en < 5 segundos
- Memoria máxima: 500 MB

### 7.2 Confiabilidad

- Retry automático en caso de fallo de API
- Fallback a datos en caché si API no disponible
- Validación de datos de entrada

### 7.3 Seguridad

- Usar credenciales de Service Account
- Encriptar datos sensibles
- Auditar acceso a logs
- Validar permisos de usuario

### 7.4 Escalabilidad

- Soportar múltiples proyectos GCP
- Soportar múltiples clusters Kubernetes
- Procesamiento paralelo de fuentes

---

**Versión**: 1.0.0  
**Fecha**: 2026-07-14
