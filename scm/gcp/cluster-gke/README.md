# GCP GKE Cluster Checker

Herramienta SRE para monitorear clusters de Google Kubernetes Engine (GKE).

## ☸️ Características

- **Monitoreo de clusters** - Lista todos los clusters GKE del proyecto
- **Información de versión** - Muestra versión actual y estado de actualización
- **Detección de modo** - Identifica clusters Autopilot vs Standard
- **Release Channel** - Muestra el canal de actualizaciones configurado
- **Ejecución paralela** - Procesa múltiples clusters simultáneamente con ThreadPoolExecutor
- **Medición de tiempo** - Muestra duración de ejecución al finalizar
- **Sistema de Semáforo SRE** - Indicadores visuales de estado:
  - 🟢 **HEALTHY** - Cluster funcionando correctamente
  - ✨ **AUTOPILOT** - Cluster Autopilot saludable
  - 🔵 **NO CHANNEL** - Sin Release Channel configurado
  - 🟡 **UPDATE** - Actualización disponible
  - 🔴 **OUTDATED** - Versión muy antigua
  - 🔴 **NOT RUNNING** - Cluster no está corriendo
- **Resumen ejecutivo** - Panel con conteo de estados
- **Detalle de pods problemáticos** - Tabla adicional con pods no running (namespace, owner, pod, reason)
- **Exportación CSV/JSON** - Genera reportes en carpeta `outcome/`

## 📋 Requisitos

- Python 3.8+
- `gcloud` CLI instalado y autenticado
- Permisos IAM requeridos:
  - `container.clusters.list`
  - `container.clusters.get`

## 🛠️ Instalación

```bash
pip install rich
```

## 🚀 Uso

```bash
# Proyecto por defecto
python gcp_cluster_checker.py

# Especificar proyecto
python gcp_cluster_checker.py --project YOUR_PROJECT_ID

# Modo debug (muestra comandos ejecutados)
python gcp_cluster_checker.py --debug

# Exportar a CSV
python gcp_cluster_checker.py --output csv

# Exportar a JSON
python gcp_cluster_checker.py -o json

# Ejecutar en modo secuencial (sin paralelismo)
python gcp_cluster_checker.py --no-parallel

# Especificar número de workers paralelos
python gcp_cluster_checker.py --max-workers 8
```

## 📝 Argumentos

| Argumento | Descripción | Default |
|-----------|-------------|---------|
| `--project` | ID del proyecto GCP | `cpl-xxxx-yyyy-zzzz-99999999` |
| `--debug` | Activa modo debug para diagnóstico | `False` |
| `--output`, `-o` | Exporta resultados (`csv` o `json`) | `None` |
| `--parallel` | Ejecuta procesamiento en paralelo | `True` |
| `--no-parallel` | Desactiva procesamiento paralelo | `False` |
| `--max-workers` | Número máximo de workers paralelos | `4` |
| `--timezone`, `-tz` | Zona horaria para mostrar fechas | `America/Mazatlan` (Culiacán) |
| `--help`, `-h` | Muestra documentación completa | - |

## 📊 Ejemplo de Salida

```
☸️  Iniciando escaneo de Clusters GKE en: my-project
🕐 Fecha y hora de revisión: 2026-02-16 14:00:00 (America/Mazatlan)

                           ☸️  GKE Clusters: my-project
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Cluster            ┃ Ubicación      ┃   Modo    ┃  Versión   ┃ Nodos ┃ Estado  ┃  Channel  ┃ Semáforo SRE   ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ gke-prod-cluster   │ us-central1    │ AUTOPILOT │ 1.29.1-gke │     0 │ RUNNING │  REGULAR  │ AUTOPILOT ✨   │
│ gke-staging        │ us-east1-b     │ STANDARD  │ 1.28.5-gke │    12 │ RUNNING │  RAPID    │ HEALTHY ✅     │
│ gke-legacy         │ us-west1-a     │ STANDARD  │ 1.25.0-gke │     6 │ RUNNING │UNSPECIFIED│ OUTDATED 🚨    │
└────────────────────┴────────────────┴───────────┴────────────┴───────┴─────────┴───────────┴────────────────┘
╭─────────────────────────────── 📊 Resumen Ejecutivo ───────────────────────────────╮
│ 🚨 NOT RUNNING: 0  ⏰ OUTDATED: 1  ⚠️ UPDATE: 0  📢 NO CHANNEL: 0  ✅ HEALTHY: 2   │
╰────────────────────────────────────────────────────────────────────────────────────╯

Tip: Mantén tus clusters en un Release Channel para actualizaciones automáticas.
```

## 🔧 Cómo Funciona

1. Usa `gcloud container clusters list` para obtener los clusters
2. Extrae información de versión, modo, nodos y estado
3. Evalúa la versión contra las recomendaciones actuales
4. Aplica lógica de semáforo SRE basada en estado y versión
5. Muestra resultados en tabla formateada con Rich

## 📁 Formato de Exportación

**CSV** - Columnas: `project`, `cluster`, `location`, `mode`, `version`, `node_count`, `cluster_status`, `release_channel`, `status`, `revision_time`

**JSON** - Array de objetos con los mismos campos

## 🎯 Release Channels

| Channel | Descripción |
|---------|-------------|
| **RAPID** | Actualizaciones más frecuentes, primeras versiones |
| **REGULAR** | Balance entre estabilidad y nuevas features |
| **STABLE** | Mayor estabilidad, actualizaciones menos frecuentes |
| **UNSPECIFIED** | Sin canal, requiere actualizaciones manuales |

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-02-20 | 2.3.0 | Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-19 | 2.2.1 | Validación de conexión GCP al inicio (check_gcp_connection) |
| 2026-02-16 | 2.2.0 | Timezone configurable con Culiacán (America/Mazatlan) como default, tabla de tiempos de ejecución |
| 2026-02-16 | 2.1.0 | Tabla adicional con detalle de pods no running (namespace, owner, pod, reason) |
| 2026-02-16 | 2.0.0 | Ejecución paralela con ThreadPoolExecutor, medición de tiempo de ejecución |
| 2026-01-28 | 1.3.0 | Agregada escala a valores de CPU (cores/mCores) y Memory (GB/MB/KB) |
| 2026-01-28 | 1.2.0 | Agregada columna de conteo de Pods (running/not running) |
| 2026-01-28 | 1.1.0 | Agregadas métricas de CPU/Memory utilization (Request/Limit) |
| 2026-01-28 | 1.0.0 | Versión inicial con monitoreo de clusters GKE |

---

## Autor

**Harold Adrian**

---

## Licencia

Internal SRE Tool - Softtek
