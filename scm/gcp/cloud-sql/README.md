# GCP Cloud SQL Tools

Herramientas SCM para Cloud SQL en Google Cloud Platform: monitoreo de disco y comparación de instancias.

> **Nota:** El connectivity checker fue movido a `gcp/connectivity/pod_connectivity_checker.py`

## 📋 Contenido

| Archivo | Descripción |
|---------|-------------|
| `gcp_disk_checker.py` | Monitorea el uso de disco de instancias Cloud SQL |
| `gcp_sql_comparator.py` | Compara versiones y atributos entre proyectos GCP |
| `requirements.txt` | Dependencias de Python |

---

## 🔍 Cloud SQL Disk Checker

Herramienta para monitorear el uso de disco de bases de datos Cloud SQL en proyectos GCP.

### Características

- **Monitoreo en tiempo real** - Consulta la API de Cloud Monitoring para obtener el uso actual del disco
- **Ejecución paralela** - Procesa múltiples instancias simultáneamente con ThreadPoolExecutor
- **Medición de tiempo** - Muestra tabla de tiempo de ejecución al finalizar (inicio, fin, duración)
- **Sistema de Semáforo SCM** - Indicadores visuales de estado:
  - 🟢 **HEALTHY** - Operación normal
  - 🔵 **MANUAL OK** - Auto-resize deshabilitado pero saludable
  - 🟡 **WARNING** - Utilización ≥ 75%
  - 🔴 **CRITICAL** - Utilización ≥ 90%
- **Detección de auto-resize** - Muestra si el auto-resize de almacenamiento está habilitado
- **Salida enriquecida** - Tablas formateadas con colores usando Rich
- **Solo gcloud** - No requiere librerías de Google Cloud Python, usa gcloud CLI y API REST
- **Resumen ejecutivo** - Panel con conteo de estados (CRITICAL, WARNING, HEALTHY)
- **Exportación CSV/JSON** - Genera reportes en carpeta `outcome/` para integración con dashboards

### Requisitos

- Python 3.8+
- `gcloud` CLI instalado y autenticado
- `curl` disponible en el sistema
- Permisos IAM requeridos:
  - `cloudsql.instances.list`
  - `monitoring.timeSeries.list`

### Instalación

```bash
pip install rich
```

### Uso

```bash
# Proyecto por defecto
python gcp_disk_checker.py

# Especificar proyecto
python gcp_disk_checker.py --project YOUR_PROJECT_ID

# Modo debug (muestra comandos ejecutados)
python gcp_disk_checker.py --debug

# Exportar a CSV
python gcp_disk_checker.py --output csv

# Exportar a JSON
python gcp_disk_checker.py -o json
```

### Argumentos

| Argumento | Descripción | Default |
|-----------|-------------|---------|
| `--project` | ID del proyecto GCP | `cpl-xxxx-yyyy-zzzz-99999999` |
| `--debug` | Activa modo debug para diagnóstico | `False` |
| `--output`, `-o` | Exporta resultados (`csv` o `json`) | `None` |
| `--parallel` | Activa ejecución paralela | `True` |
| `--no-parallel` | Desactiva ejecución paralela | `False` |
| `--max-workers` | Número máximo de workers paralelos | `4` |
| `--timezone`, `-tz` | Zona horaria para mostrar fechas | `America/Mazatlan` (Culiacán) |
| `--help`, `-h` | Muestra documentación completa | - |

### Ejemplo de Salida

```
📡 Iniciando escaneo de Base de Datos en: cpl-xxxx-yyyy-zzzz-99999999
🕐 Fecha y hora de revisión: 2026-02-16 14:07:35 (America/Mazatlan)
⚡ Modo: Paralelo (4 workers)

                         📊 Database Storage Health: cpl-xxxx-yyyy-zzzz-99999999
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Instancia DB                    ┃   Motor   ┃ Capacidad ┃ Uso actual (%) ┃ Auto-Resize ┃ Semaforo SCM ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ csql-mssql-prod-01              │ SQLSERVER │  40715 GB │         65.32% │   ENABLED   │  HEALTHY ✅  │
│ csql-mysql-prod-01              │   MYSQL   │    300 GB │         78.45% │   ENABLED   │  WARNING ⚠️  │
│ csql-postgresql-prod-01         │ POSTGRES  │    352 GB │         92.10% │   DISABLED  │  CRITICAL 🚨 │
└─────────────────────────────────┴───────────┴───────────┴────────────────┴─────────────┴──────────────┘
╭──────────────────────── 📊 Resumen Ejecutivo ────────────────────────╮
│ 🚨 CRITICAL: 1  ⚠️ WARNING: 1  ℹ️ MANUAL OK: 0  ✅ HEALTHY: 1  | Total: 3 │
╰──────────────────────────────────────────────────────────────────────╯

📁 Archivo exportado: outcome/disk_check_my-project_20260128_124530.csv

Tip: Las alertas se disparan basándose en la métrica de 'utilization' de Cloud Monitoring.
```

### Formato de Exportación

**CSV** - Columnas: `project`, `instance`, `engine`, `capacity_gb`, `utilization_pct`, `auto_resize`, `status`, `revision_time`

**JSON** - Array de objetos con los mismos campos

## Autenticación

Asegúrate de tener credenciales GCP válidas:

```bash
# Login con gcloud (recomendado para Cloud Shell)
gcloud auth login

# Verificar proyecto activo
gcloud config get-value project

# Cambiar proyecto si es necesario
gcloud config set project YOUR_PROJECT_ID
```

## Cómo Funciona

1. Usa `gcloud sql instances list` para obtener las instancias de Cloud SQL
2. Obtiene token de acceso con `gcloud auth print-access-token`
3. Consulta la API REST de Cloud Monitoring (`monitoring.googleapis.com/v3`) con `curl`
4. Procesa la métrica `cloudsql.googleapis.com/database/disk/utilization`
5. Muestra resultados en tabla formateada con Rich

---

## � Cloud SQL Comparator

Herramienta para comparar **versiones** de instancias Cloud SQL entre dos proyectos GCP.

### Características

- **Comparación de versiones por defecto** - Compara `POSTGRES_15`, `MYSQL_8_0`, etc.
- **Comparación de atributos opcional** - Edition, Type, Port, Public/Private IP
- **Listado automático** - Lista todas las instancias de ambos proyectos
- **Sistema de Semáforos** - Indicadores visuales:
  - ✅ **OK** - Valores coinciden
  - 🚧 **DIFFERS** - Valores difieren (no crítico)
  - ⛔ **MISMATCH** - Valores difieren (crítico: type, port)
- **Detección de instancias faltantes** - Muestra instancias que solo existen en un proyecto
- **Exportación CSV/JSON** - Reportes en carpeta `outcome/`

### Uso

```bash
# Comparar solo VERSIONES (por defecto)
python gcp_sql_comparator.py -p1 <PROJECT_1> -p2 <PROJECT_2>

# Comparar TODOS los atributos
python gcp_sql_comparator.py -p1 <PROJECT_1> -p2 <PROJECT_2> --all

# Comparar atributos específicos
python gcp_sql_comparator.py -p1 <PROJECT_1> -p2 <PROJECT_2> --attributes edition public_ip

# Filtrar por instancia
python gcp_sql_comparator.py -p1 <PROJECT_1> -p2 <PROJECT_2> --instance db-main

# Exportar a JSON
python gcp_sql_comparator.py -p1 <PROJECT_1> -p2 <PROJECT_2> --output json
```

### Argumentos

| Argumento | Alias | Requerido | Descripción |
|-----------|-------|-----------|-------------|
| `--project1` | `-p1` | ✅ | ID del primer proyecto GCP (referencia) |
| `--project2` | `-p2` | ✅ | ID del segundo proyecto GCP (a comparar) |
| `--instance` | `-i` | ❌ | Filtrar por nombre de instancia específica |
| `--all` | `-a` | ❌ | Muestra comparación de TODOS los atributos |
| `--attributes` | - | ❌ | Atributos: `edition`, `type`, `port`, `public_ip`, `private_ip` |
| `--output` | `-o` | ❌ | Exporta resultados (`csv` o `json`) |
| `--timezone` | `-tz` | ❌ | Zona horaria (default: America/Mazatlan) |
| `--debug` | - | ❌ | Modo debug para ver comandos ejecutados |
| `--help` | `-h` | ❌ | Muestra documentación completa |

### Ejemplo de Salida (Versiones)

```
🔍 Cloud SQL Instance Comparator
🕐 Fecha y hora de revisión: 2026-03-20 11:30:00 (America/Mazatlan)
📌 Proyecto 1: cpl-xxxx-yyyy-zzzz-99999999
📌 Proyecto 2: cpl-aaaa-bbbb-cccc-11111111

📊 Instancias encontradas: 3 en P1, 2 en P2

╭─────────────── 📦 Comparación de Versiones de Base de Datos ───────────────╮
│ # │ Instancia     │ 📌 cpl-xxxx...      │ 📌 cpl-aaaa...      │ Check │
├───┼───────────────┼─────────────────────┼─────────────────────┼───────┤
│ 1 │ db-main       │ POSTGRES_15         │ POSTGRES_15         │  ✅   │
│ 2 │ db-analytics  │ POSTGRES_14         │ POSTGRES_15         │  ⛔   │
│ 3 │ db-legacy     │ MYSQL_8_0           │ ❌ NO EXISTE        │  🚧   │
╰────────────────────────────────────────────────────────────────────────────╯
   Versiones: ✅ Iguales: 1 | ⛔ Diferentes: 2 | Total: 3
```

### Casos de Uso

1. **Validación pre-migración** - Comparar configuración antes de migrar datos
2. **Auditoría de seguridad** - Verificar que producción tenga IP pública deshabilitada
3. **Consistencia de ambientes** - Asegurar que staging refleje producción
4. **Documentación de diferencias** - Exportar comparaciones para reportes

---

## �🔌 Cloud SQL Connectivity Checker

Herramienta para validar la conectividad desde un Pod de GKE hasta una instancia de Cloud SQL, verificando todos los elementos de la cadena de conectividad.

> 📖 **Documentación completa**: Ver [CONNECTIVITY-CHECKER.md](CONNECTIVITY-CHECKER.md)

### Uso Rápido

```bash
# Modo simplificado (autodiscovery)
python connectivity-checker.py --deployment my-app --sql-instance my-database

# Modo completo
python connectivity-checker.py \
  --sql-instance my-database \
  --project my-project \
  --gke-cluster my-cluster \
  --namespace backend
```

### Fases de Validación

| Fase | Descripción |
|------|-------------|
| 0. Discovery | Descubrimiento automático de project, cluster, namespace, KSA, GSA |
| 1. Cloud SQL | Valida instancia existe y está activa |
| 2. GKE Cluster | Valida configuración del cluster (VPC-native, Workload Identity) |
| 3. VPC & PSC | Valida red y Private Service Connection |
| 4. Firewall | Valida reglas de firewall para puertos SQL |
| 5. IAM | Valida permisos del Google Service Account |
| 6. Workload Identity | Valida binding KSA ↔ GSA |
| 7. Cloud SQL Proxy | Verifica si hay proxy desplegado (opcional) |
| 8. Load Balancers | Valida servicios de Kubernetes |
| 9. Connectivity Test | Prueba de conectividad de red |

### Parámetros Principales

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--sql-instance, -s` | ✅ | Nombre de la instancia Cloud SQL |
| `--deployment, -d` | ❌ | Nombre del deployment (habilita discovery) |
| `--project, -p` | ❌ | ID del proyecto GCP |
| `--namespace, -n` | ❌ | Namespace de Kubernetes |
| `--verbose, -v` | ❌ | Mostrar comandos ejecutados |

---

## Autor

**Harold Adrian**

---

## Licencia

Internal SCM Tool - Softtek

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-03-20 | 3.0.0 | Nuevo: gcp_sql_comparator.py para comparar versiones y atributos entre proyectos |
| 2026-02-20 | 2.3.1 | Spinner con barra de progreso durante procesamiento paralelo de instancias |
| 2026-02-20 | 2.3.0 | Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-19 | 2.2.1 | Validación de conexión GCP al inicio (check_gcp_connection) en ambos scripts |
| 2026-02-16 | 2.2.0 | Disk checker: timezone configurable con Culiacán (America/Mazatlan) como default |
| 2026-02-16 | 2.0.0 | Disk checker: ejecución paralela con ThreadPoolExecutor, medición de tiempo de ejecución, fecha UTC |
| 2026-01-28 | 1.5.0 | Disk checker: nueva columna Uso (GB) con cálculo de espacio utilizado |
| 2026-01-28 | 1.4.0 | Disk checker: caché de token para optimizar rendimiento |
| 2026-01-28 | 1.3.0 | Disk checker: exportación CSV/JSON, resumen ejecutivo, fecha/hora de revisión |
| 2026-01-12 | 1.2.0 | Actualización de documentación: integración de connectivity-checker, tabla de contenido |
| 2025-12-01 | 1.1.0 | Añadido connectivity-checker.py para validación de conectividad GKE → Cloud SQL |
| 2025-01-01 | 1.0.0 | Versión inicial con gcp_disk_checker.py |
