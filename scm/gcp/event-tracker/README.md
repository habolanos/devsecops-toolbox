# 🔍 GCP Event Tracker

Herramienta para rastrear eventos, caídas de servicio e interrupciones en componentes Cloud Run y Kubernetes en Google Cloud Platform.

## Características

✅ **Búsqueda Multi-Fuente**
- Cloud Logging
- Cloud Monitoring
- Cloud Audit Logs
- Kubernetes Events
- Pod Logs

✅ **Procesamiento Inteligente**
- Normalización automática
- Deduplicación
- Correlación de eventos
- Análisis de causa raíz

✅ **Reportería Completa**
- JSON (datos completos)
- CSV (análisis en Excel)
- HTML (visual interactivo)
- Markdown (documentación)

## Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar credenciales GCP
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Configurar acceso a Kubernetes
gcloud container clusters get-credentials CLUSTER_NAME --zone ZONE
```

## Uso

### Línea de Comandos

```bash
python event_tracker.py \
  --component-name "my-service" \
  --project-id "my-project" \
  --start-time "2026-07-13T00:00:00Z" \
  --end-time "2026-07-14T00:00:00Z" \
  --output-format html \
  --output-file report.html
```

### Desde Python

```python
from event_tracker import EventTracker

tracker = EventTracker(project_id="my-project")
events = tracker.search_component_events(
    component_name="my-service",
    start_time="2026-07-13T00:00:00Z",
    end_time="2026-07-14T00:00:00Z"
)

report = tracker.generate_report(events, format="html")
print(report)
```

## Parámetros

### Requeridos

- `--component-name`: Nombre del componente a rastrear
- `--project-id`: ID del proyecto GCP
- `--start-time`: Hora de inicio (ISO 8601)
- `--end-time`: Hora de fin (ISO 8601)

### Opcionales

- `--output-format`: Formato del reporte (json, csv, html, markdown) [default: json]
- `--output-file`: Archivo de salida (si no se especifica, se imprime en consola)
- `--credentials-file`: Ruta al archivo de credenciales de Service Account

## Ejemplos

### Investigar caída de servicio

```bash
python event_tracker.py \
  --component-name "payment-api" \
  --project-id "my-project" \
  --start-time "2026-07-13T08:00:00Z" \
  --end-time "2026-07-13T10:00:00Z" \
  --output-format html \
  --output-file payment-api-incident.html
```

### Análisis de rendimiento

```bash
python event_tracker.py \
  --component-name "api-gateway" \
  --project-id "my-project" \
  --start-time "2026-07-13T00:00:00Z" \
  --end-time "2026-07-13T23:59:59Z" \
  --output-format json \
  --output-file api-gateway-analysis.json
```

### Auditoría de cambios

```bash
python event_tracker.py \
  --component-name "payment-processor" \
  --project-id "my-project" \
  --start-time "2026-06-13T00:00:00Z" \
  --end-time "2026-07-13T23:59:59Z" \
  --output-format csv \
  --output-file payment-processor-audit.csv
```

## Permisos Requeridos

### GCP

```
roles/logging.viewer
roles/monitoring.viewer
roles/container.viewer
roles/compute.viewer
```

### Kubernetes

```
get events
get pods
get nodes
get deployments
list events
```

## Troubleshooting

### "No events found"

- Aumentar rango de tiempo
- Verificar nombre del componente
- Verificar que el componente existe

### "Permission denied"

- Verificar credenciales GCP
- Verificar permisos de usuario
- Configurar kubeconfig

### "Connection timeout"

- Verificar conectividad a Kubernetes
- Verificar kubeconfig
- Verificar credenciales

## Documentación Completa

Ver documentación completa en:
`docs/features/feature_gcp_log_eventos_servicio/`

- 00_INICIO_AQUI.md - Resumen ejecutivo
- 01_FUENTES_DE_EVENTOS_GCP.md - Fuentes GCP
- 02_FUENTES_DE_EVENTOS_KUBERNETES.md - Fuentes Kubernetes
- 03_ARQUITECTURA_SOLUCION.md - Arquitectura
- 04_ESPECIFICACION_REPORTE.md - Especificación del reporte
- 05_PLAN_IMPLEMENTACION.md - Plan de implementación
- 06_EJEMPLOS_PRACTICOS.md - Ejemplos prácticos

## Versión

1.0.0

## Autor

DevSecOps Team
