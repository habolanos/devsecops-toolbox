# GCP Reports Viewer v2.0

Dashboard avanzado para visualización de reportes JSON generados por los checkers GCP.

## Características

- **Dashboard Profesional** - Diseño moderno con KPIs, alertas y timeline
- **Panel de Alertas** - Detecta automáticamente issues críticos y warnings
- **Timeline de Ejecuciones** - Historial visual de todos los scans
- **Gráficos de Tendencias** - Curvas temporales de recursos y estados
- **KPI Cards** - Health Score, Critical Issues, Warnings, Total Resources
- **Métricas por Categoría** - Certificados, Clusters, Cloud SQL, Service Accounts
- **Múltiples tipos de gráficos**:
  - Donut chart de distribución de estados
  - Barras apiladas por herramienta
  - Barras de utilización con umbrales (Cloud SQL disk)
  - Líneas de tendencia temporal
- **Detección de alertas automática**:
  - Disco crítico (≥90%) y warning (≥75%)
  - Certificados expirando (≤7 días crítico, ≤30 días warning)
  - Keys de Service Account antiguas (≥90 días warning, ≥180 días crítico)
  - Referencias de Secrets/ConfigMaps faltantes

## Requisitos

```bash
pip install plotly rich
```

> **Nota**: Si Plotly no está instalado, se genera un HTML básico con tablas.

## Uso

```bash
# Generar dashboard con todos los reportes disponibles
python gcp_reports_viewer.py

# Usar solo los reportes más recientes de cada tipo
python gcp_reports_viewer.py --latest

# Usar un archivo JSON específico
python gcp_reports_viewer.py -i path/to/report.json

# Especificar archivo de salida
python gcp_reports_viewer.py -o mi_dashboard.html

# Ver ayuda
python gcp_reports_viewer.py -h
```

## Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--input`, `-i` | Archivo JSON o directorio con reportes | Auto-detecta |
| `--output`, `-o` | Archivo HTML de salida | `outcome/dashboard.html` |
| `--latest` | Usar solo reportes más recientes | `False` |
| `--help`, `-h` | Muestra ayuda | - |

## Tipos de Gráficos por Checker

| Checker | Tipo de Gráfico | Descripción |
|---------|-----------------|-------------|
| Certificate Manager | Pie chart | Estados de certificados |
| Cloud SQL Disk | Barras | Utilización % con líneas de umbral |
| GKE Clusters | Pie chart | Estados de clusters |
| Gateway Services | Barras | Conteo por tipo de recurso |
| Load Balancers | Indicadores | Resumen de componentes |
| Monitoring | Indicadores | Conteo de recursos |
| Secrets/ConfigMaps | Pie chart | FOUND vs MISSING |
| Service Accounts | Barras | Activos, deshabilitados, keys |
| VPC Networks | Indicadores | Resumen de componentes |

## Estructura del Dashboard

```
┌──────────────────────────────────────────────────────────┐
│                  GCP Reports Dashboard                    │
│              Generado: 2026-02-20 14:30:00               │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │ Cert Manager│ │ Cloud SQL   │ │ GKE Clusters│        │
│  │ Proyecto... │ │ Proyecto... │ │ Proyecto... │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
├──────────────────────────────────────────────────────────┤
│  ┌───────────────────────┐ ┌───────────────────────┐    │
│  │   [Pie Chart]         │ │   [Bar Chart]         │    │
│  │   Certificados        │ │   Cloud SQL Disk      │    │
│  └───────────────────────┘ └───────────────────────┘    │
│  ┌───────────────────────┐ ┌───────────────────────┐    │
│  │   [Pie Chart]         │ │   [Indicators]        │    │
│  │   GKE Clusters        │ │   Service Accounts    │    │
│  └───────────────────────┘ └───────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

## Formato de Reportes JSON Soportado

El visualizador espera reportes con la siguiente estructura:

```json
{
  "report_metadata": {
    "tool_name": "GCP Certificate Manager Checker",
    "version": "1.2.0",
    "project_id": "my-project",
    "generated_at": "2026-02-20T14:30:00-07:00",
    "timezone": "America/Mazatlan",
    "timestamp_utc": "2026-02-20T21:30:00+00:00"
  },
  "summary": {
    "total_certificates": 10,
    "healthy": 7,
    "warning": 2,
    "critical": 1
  },
  "certificates": [...]
}
```

## Ejemplo de Salida

El dashboard HTML generado incluye:

1. **Encabezado** con fecha de generación
2. **Tarjetas de metadata** por cada reporte
3. **Gráficos interactivos** con hover tooltips
4. **Responsive design** para diferentes tamaños de pantalla

## Integración con el Launcher

Este visualizador está disponible como opción **14** en `gcp_tools_launcher.py`:

```bash
python gcp_tools_launcher.py
# Seleccionar opción 14: Visualizar Reportes JSON
```

## Archivos de Salida

Los dashboards se generan en `reports-viewer/outcome/`:

```
reports-viewer/
├── outcome/
│   ├── dashboard.html          # Dashboard por defecto
│   └── dashboard_20260220.html # Dashboards con fecha
├── gcp_reports_viewer.py
└── README.md
```

---

## Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-02-20 | 3.2.0 | Proyecto en título, timeline horizontal compacto por herramienta |
| 2026-02-20 | 3.1.0 | Timeline/Semáforo de componentes con filtros, timestamp en nombre de archivo |
| 2026-02-20 | 3.0.0 | **Sin dependencias** - Usa Chart.js desde CDN, eliminada dependencia de Plotly |
| 2026-02-20 | 2.1.0 | Soporte para reportes legacy (arrays), normalización automática, métricas de deployments |
| 2026-02-20 | 2.0.0 | Dashboard avanzado con timeline, alertas, tendencias y KPIs |
| 2026-02-20 | 1.0.0 | Versión inicial con soporte para todos los checkers |

---

## Autor

**Harold Adrian**

---

## Licencia

Internal SRE Tool - Softtek
