# 📋 Especificación del Reporte

## 1. Estructura General del Reporte

```
┌─────────────────────────────────────────────────────┐
│              REPORTE DE EVENTOS                      │
│         Componente: my-cloud-run-service             │
│         Período: 2026-07-13 a 2026-07-14             │
└─────────────────────────────────────────────────────┘

1. RESUMEN EJECUTIVO
   ├─ Total de eventos
   ├─ Eventos críticos
   ├─ Duración del incidente
   └─ Causa raíz

2. TIMELINE
   ├─ Evento 1: 10:30:00 - Error
   ├─ Evento 2: 10:31:00 - Reinicio
   ├─ Evento 3: 10:32:00 - Recuperación
   └─ ...

3. EVENTOS DETALLADOS
   ├─ Evento 1
   │  ├─ Timestamp
   │  ├─ Tipo
   │  ├─ Severidad
   │  ├─ Mensaje
   │  └─ Fuente
   └─ ...

4. CORRELACIONES
   ├─ Grupo 1: Error → Reinicio → Recuperación
   ├─ Grupo 2: Cambio de config → Error
   └─ ...

5. ANÁLISIS
   ├─ Causa raíz
   ├─ Impacto
   ├─ Duración
   └─ Recomendaciones

6. MÉTRICAS
   ├─ Eventos por fuente
   ├─ Eventos por severidad
   ├─ Eventos por tipo
   └─ Timeline de eventos
```

---

## 2. Resumen Ejecutivo

### 2.1 Campos

```json
{
  "summary": {
    "component_name": "my-cloud-run-service",
    "period": {
      "start": "2026-07-13T00:00:00Z",
      "end": "2026-07-14T00:00:00Z"
    },
    "total_events": 245,
    "critical_events": 5,
    "warning_events": 23,
    "info_events": 217,
    "incident_detected": true,
    "incident_duration": "00:15:30",
    "incident_start": "2026-07-13T10:30:00Z",
    "incident_end": "2026-07-13T10:45:30Z",
    "root_cause": "Out of memory error in container",
    "impact": "Service unavailable for 15 minutes",
    "affected_users": "~1000",
    "affected_requests": 5234
  }
}
```

### 2.2 Interpretación

- **total_events**: Número total de eventos encontrados
- **critical_events**: Eventos de severidad crítica
- **incident_detected**: Si se detectó un incidente
- **incident_duration**: Duración del incidente
- **root_cause**: Causa raíz identificada automáticamente
- **impact**: Impacto estimado

---

## 3. Timeline

### 3.1 Formato

```json
{
  "timeline": [
    {
      "timestamp": "2026-07-13T10:30:00Z",
      "event_number": 1,
      "component": "my-cloud-run-service",
      "type": "error",
      "severity": "critical",
      "message": "Container out of memory",
      "source": "cloud_logging",
      "details": {
        "memory_used": "512 MB",
        "memory_limit": "512 MB",
        "exit_code": 137
      }
    },
    {
      "timestamp": "2026-07-13T10:31:00Z",
      "event_number": 2,
      "component": "my-cloud-run-service",
      "type": "restart",
      "severity": "warning",
      "message": "Container restarted",
      "source": "kubernetes_events",
      "details": {
        "restart_count": 1,
        "reason": "OOMKilled"
      }
    },
    {
      "timestamp": "2026-07-13T10:32:00Z",
      "event_number": 3,
      "component": "my-cloud-run-service",
      "type": "recovery",
      "severity": "info",
      "message": "Service recovered",
      "source": "cloud_monitoring",
      "details": {
        "status": "healthy",
        "response_time": "150ms"
      }
    }
  ]
}
```

### 3.2 Visualización en HTML

```html
<div class="timeline">
  <div class="timeline-item critical">
    <div class="time">10:30:00</div>
    <div class="event">Container out of memory</div>
    <div class="source">Cloud Logging</div>
  </div>
  <div class="timeline-item warning">
    <div class="time">10:31:00</div>
    <div class="event">Container restarted</div>
    <div class="source">Kubernetes Events</div>
  </div>
  <div class="timeline-item info">
    <div class="time">10:32:00</div>
    <div class="event">Service recovered</div>
    <div class="source">Cloud Monitoring</div>
  </div>
</div>
```

---

## 4. Eventos Detallados

### 4.1 Formato JSON

```json
{
  "events": [
    {
      "id": "event_001",
      "timestamp": "2026-07-13T10:30:00Z",
      "component_name": "my-cloud-run-service",
      "event_type": "error",
      "severity": "critical",
      "message": "Container out of memory",
      "source": "cloud_logging",
      "source_details": {
        "log_name": "projects/my-project/logs/run.googleapis.com%2Fstderr",
        "resource_type": "cloud_run_revision",
        "resource_labels": {
          "service_name": "my-cloud-run-service",
          "revision_name": "my-cloud-run-service-001"
        }
      },
      "metadata": {
        "pod_name": "my-cloud-run-service-001-abc123",
        "namespace": "default",
        "container": "my-cloud-run-service",
        "exit_code": 137,
        "memory_used": "512 MB",
        "memory_limit": "512 MB"
      },
      "raw_log": "java.lang.OutOfMemoryError: Java heap space\n  at java.util.Arrays.copyOf(Arrays.java:3210)\n  at java.lang.StringBuilder.append(StringBuilder.java:415)"
    }
  ]
}
```

### 4.2 Formato CSV

```csv
timestamp,component_name,event_type,severity,message,source,pod_name,namespace,exit_code
2026-07-13T10:30:00Z,my-cloud-run-service,error,critical,Container out of memory,cloud_logging,my-cloud-run-service-001-abc123,default,137
2026-07-13T10:31:00Z,my-cloud-run-service,restart,warning,Container restarted,kubernetes_events,my-cloud-run-service-001-abc123,default,0
2026-07-13T10:32:00Z,my-cloud-run-service,recovery,info,Service recovered,cloud_monitoring,my-cloud-run-service-001-abc123,default,0
```

---

## 5. Correlaciones

### 5.1 Formato

```json
{
  "correlations": [
    {
      "group_id": "group_001",
      "title": "Out of Memory Error → Restart → Recovery",
      "events": [1, 2, 3],
      "relationship": "cause-effect",
      "confidence": 0.95,
      "description": "Container ran out of memory, was killed by Kubernetes, and then restarted successfully",
      "timeline": {
        "start": "2026-07-13T10:30:00Z",
        "end": "2026-07-13T10:32:00Z",
        "duration": "00:02:00"
      }
    },
    {
      "group_id": "group_002",
      "title": "Configuration Change → Error",
      "events": [4, 5],
      "relationship": "cause-effect",
      "confidence": 0.87,
      "description": "Memory limit was reduced from 1GB to 512MB, causing OOM error",
      "timeline": {
        "start": "2026-07-13T10:25:00Z",
        "end": "2026-07-13T10:30:00Z",
        "duration": "00:05:00"
      }
    }
  ]
}
```

---

## 6. Análisis

### 6.1 Causa Raíz

```json
{
  "analysis": {
    "root_cause": {
      "primary": "Out of memory error in container",
      "secondary_causes": [
        "Memory limit was reduced from 1GB to 512MB",
        "Application has memory leak in version 2.1.0",
        "Increased traffic caused higher memory usage"
      ],
      "confidence": 0.92,
      "evidence": [
        "Cloud Logging: 'java.lang.OutOfMemoryError'",
        "Kubernetes Events: 'OOMKilled'",
        "Cloud Monitoring: Memory usage reached 100%",
        "Audit Logs: Memory limit changed at 10:25:00"
      ]
    },
    "impact": {
      "service_unavailable": true,
      "duration": "00:15:30",
      "affected_users": "~1000",
      "affected_requests": 5234,
      "error_rate": "100%"
    },
    "timeline": {
      "change_applied": "2026-07-13T10:25:00Z",
      "error_started": "2026-07-13T10:30:00Z",
      "time_to_error": "00:05:00",
      "recovery_time": "00:10:30"
    },
    "recommendations": [
      {
        "priority": "critical",
        "action": "Increase memory limit back to 1GB",
        "estimated_impact": "Resolves immediate issue"
      },
      {
        "priority": "high",
        "action": "Investigate memory leak in application v2.1.0",
        "estimated_impact": "Prevents future OOM errors"
      },
      {
        "priority": "medium",
        "action": "Implement memory monitoring alerts",
        "estimated_impact": "Early warning of memory issues"
      },
      {
        "priority": "medium",
        "action": "Add memory limits to pod requests",
        "estimated_impact": "Better resource management"
      }
    ]
  }
}
```

---

## 7. Métricas

### 7.1 Eventos por Fuente

```json
{
  "metrics": {
    "events_by_source": {
      "cloud_logging": 150,
      "cloud_monitoring": 45,
      "audit_logs": 12,
      "kubernetes_events": 78,
      "cloud_events": 23,
      "total": 308
    },
    "events_by_severity": {
      "critical": 5,
      "warning": 23,
      "info": 217,
      "total": 245
    },
    "events_by_type": {
      "error": 28,
      "restart": 5,
      "recovery": 3,
      "warning": 18,
      "info": 191,
      "total": 245
    },
    "deduplication": {
      "total_raw_events": 308,
      "duplicates_removed": 63,
      "unique_events": 245
    }
  }
}
```

### 7.2 Gráficos en HTML

```html
<div class="metrics">
  <div class="chart">
    <h3>Eventos por Fuente</h3>
    <canvas id="events-by-source"></canvas>
  </div>
  <div class="chart">
    <h3>Eventos por Severidad</h3>
    <canvas id="events-by-severity"></canvas>
  </div>
  <div class="chart">
    <h3>Timeline de Eventos</h3>
    <canvas id="timeline-chart"></canvas>
  </div>
</div>
```

---

## 8. Formatos de Salida

### 8.1 JSON

```bash
python event_tracker.py \
  --component-name my-service \
  --output-format json \
  --output-file report.json
```

**Contenido**: Estructura completa con todos los detalles.

### 8.2 CSV

```bash
python event_tracker.py \
  --component-name my-service \
  --output-format csv \
  --output-file report.csv
```

**Contenido**: Tabla de eventos con columnas principales.

### 8.3 HTML

```bash
python event_tracker.py \
  --component-name my-service \
  --output-format html \
  --output-file report.html
```

**Contenido**: Reporte visual interactivo con gráficos.

### 8.4 Markdown

```bash
python event_tracker.py \
  --component-name my-service \
  --output-format markdown \
  --output-file report.md
```

**Contenido**: Reporte en formato Markdown para documentación.

---

## 9. Validación de Datos

### 9.1 Campos Obligatorios

```python
required_fields = {
    'timestamp': str,
    'component_name': str,
    'event_type': str,
    'severity': str,
    'message': str,
    'source': str
}
```

### 9.2 Valores Válidos

```python
valid_severities = ['critical', 'warning', 'info', 'debug']
valid_sources = [
    'cloud_logging',
    'cloud_monitoring',
    'audit_logs',
    'kubernetes_events',
    'cloud_events'
]
valid_event_types = [
    'error',
    'warning',
    'info',
    'restart',
    'recovery',
    'change',
    'alert'
]
```

---

**Versión**: 1.0.0  
**Fecha**: 2026-07-14
