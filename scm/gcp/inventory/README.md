# SCM - Inventario GKE y Cloud SQL

Scripts para generar inventarios consolidados de recursos GCP (GKE clusters, deployments, services, Cloud SQL) y exportarlos a Excel con análisis visual.

## Scripts

### `generar-inventario-csv.sh`
Script Bash que ejecuta en paralelo la generación de inventarios CSV por proyecto GCP.

**Características:**
- Ejecución paralela con `xargs -P`
- Aislamiento de kubeconfig por proceso (`/tmp/kubeconfig-inventario-{PROJECT}-{PID}`)
- Genera CSV robustos usando JSON parsing y `csv.writer` de Python
- Manejo de machine types múltiples separados por `|`

**Salida:** `outcome/*.csv` (un archivo por proyecto y tipo de recurso)

### `generar-inventario-csv-combinar-a-excel.py`
Script Python que consolida los CSV en un workbook Excel con múltiples hojas de análisis y gráficos.

**Dependencias:**
```bash
pip install pandas openpyxl
```

**Estructura del archivo Excel:**

#### Hojas de datos
- **CLUSTERS**: Inventario de clusters GKE
- **DEPLOYMENTS**: Inventario de deployments K8s
- **SERVICES**: Inventario de services K8s
- **CLOUDSQL**: Inventario de instancias Cloud SQL
- **CLOUDSQL_DATABASES**: Bases de datos dentro de cada instancia Cloud SQL
- **INGRESS**: Controladores Ingress K8s (rutas HTTP/S, dominios, TLS)
- **CLOUDRUN**: Servicios Cloud Run serverless
- **PUBSUB**: Topics Pub/Sub para mensajería

#### Hojas de análisis

##### 1. RESUMEN
**Tabla:** Recurso | DEV | QA | STAG | TOTAL  
**Gráfico:** Barras agrupadas (clustered) por entorno  
Muestra cantidades de cada tipo de recurso (CLUSTERS/DEPLOYMENTS/SERVICES/CLOUDSQL) desglosadas por entorno.

##### 2. POR ENTORNO
**Tabla:** Entorno | CLUSTERS | DEPLOYMENTS | SERVICES | CLOUDSQL | TOTAL  
**Gráfico:** Barras agrupadas por tipo de recurso  
Consolida todos los recursos por entorno (DEV/QA/STAG/PROD/OTRO).

##### 3. POR PROYECTO
**Tabla resumen:** Proyecto | CLUSTERS_DEV | CLUSTERS_QA | CLUSTERS_STAG | CLUSTERS_TOTAL | ... | TOTAL  
**Tabla detalle:** Proyecto | Entorno | CLUSTERS | DEPLOYMENTS | SERVICES | CLOUDSQL  
**Gráfico:** Líneas con series por tipo de recurso (CLUSTERS/DEPLOYMENTS/SERVICES/CLOUDSQL)  
Permite ver cómo cada proyecto se distribuye en los entornos DEV/QA/STAG por tipo de recurso.

##### 4. MACHINE TYPE
**Tabla:** Machine Type | DEV | QA | STAG | TOTAL  
**Gráfico:** Barras apiladas (stacked) por entorno  
Distribuye los tipos de máquina (e2-medium, n1-standard-1, etc.) por entorno.

##### 5. SERVICE TYPE
**Tabla principal:** Service Type | DEV | QA | STAG | TOTAL  
**Gráfico:** Barras apiladas por entorno  
**Tabla por proyecto:** Service Type | Proyecto | DEV | QA | STAG | TOTAL  
Muestra la distribución de tipos de service (ClusterIP, LoadBalancer, etc.) por entorno y proyecto.

##### 6. RADAR PROYECTO
**Tabla:** Recurso | DEV | QA | STAG (una por proyecto base)  
**Gráfico:** Radar con ejes=CLUSTERS/DEPLOYMENTS/SERVICES/CLOUDSQL, series=DEV/QA/STAG (líneas)  
Un radar por cada proyecto base, consolidando totales de cada entorno. Las líneas (no rellenas) permiten comparar visualmente el equilibrio entre entornos.

## Uso

### Desde el launcher (recomendado)

Seleccionar la opción **22 – Inventario GKE + Cloud SQL** en el menú de `tools.py`:

```bash
cd scm/gcp
python tools.py
# Seleccionar opción 22
```

Esto ejecuta automáticamente el pipeline completo (CSV + Excel) vía `run_inventory.py`.

### Manual

```bash
# 1. Generar CSVs (paralelo)
cd scm/gcp/inventory
./generar-inventario-csv.sh

# 2. Consolidar en Excel
python3 generar-inventario-csv-combinar-a-excel.py

# O ejecutar ambos pasos con el wrapper:
python3 run_inventory.py

# Salida: outcome/Inventario_Completo_GKE_CloudSQL_YYYYMMDD_HHMMSS.xlsx
```

## Configuración

### Archivo de configuración
Editar `generar-inventario-csv.config` (basado en `generar-inventario-csv.config.template`):
```
# Proyectos GCP (uno por línea)
cpl-project-dev-12062025
cpl-project-qa-19062025

# Namespaces a excluir del inventario K8s (deployments, services, ingress)
[exclude-namespaces]
datadog
kube-system
gmp-system
```

Los namespaces bajo `[exclude-namespaces]` se filtran automáticamente de las secciones de deployments, services e ingress.

### Tipos de recursos
`generar-inventario-csv-combinar-a-excel.py`:
```python
TIPOS = {
    "clusters": "PROYECTO;NAME;LOCATION;VERSION;CURRENT_VERSION;STATUS;MACHINE_TYPE;BASE;ENTORNO",
    "deployments": "PROYECTO;NAMESPACE;NAME;READY;AVAILABLE;BASE;ENTORNO",
    "services": "PROYECTO;NAMESPACE;NAME;TYPE;CLUSTER_IP;EXTERNAL_IP;PORT_S;BASE;ENTORNO",
    "cloudsql": "PROYECTO;NAME;REGION;TIER;VERSION;STATUS;BASE;ENTORNO",
    "clouddatabases": "PROYECTO;INSTANCE;DATABASE;CHARSET;COLLATION;BASE;ENTORNO",
    "ingress": "PROYECTO;NAMESPACE;CLUSTER;NAME;HOSTS;ADDRESS;PORTS;BASE;ENTORNO",
    "cloudrun": "PROYECTO;NAME;REGION;URL;LAST_DEPLOYED;IMAGE;BASE;ENTORNO",
    "pubsub": "PROYECTO;NAME;LABELS;BASE;ENTORNO"
}
```

## Extracción de entorno y proyecto base

Los scripts extraen automáticamente:
- **ENTORNO**: DEV/QA/STAG/PROD según sufijos `-dev`, `-qa`, `-stag`, `-prod`
- **BASE**: Nombre del proyecto sin sufijo de entorno (ej: `my-app-dev` → `my-app`)

## Logs y salida

Todos los archivos generados se almacenan en `outcome/`:
- `*.csv`: CSVs individuales por proyecto y tipo
- `Inventario_Completo_*.xlsx`: Workbook consolidado

El directorio `outcome/` está incluido en `.gitignore`.

---

## History

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.9.0 | 2026-04-16 | Integración con launcher tools.py (opción 22), wrapper run_inventory.py, requirements.txt |
| 1.8.0 | 2026-04-15 | Excluir namespaces via config [exclude-namespaces] (datadog, kube-system, gmp-system) |
| 1.7.0 | 2026-04-15 | Agregar inventarios: Ingress (K8s), Cloud Run Services, Pub/Sub Topics (hojas + radar) |
| 1.6.0 | 2026-04-15 | Agregar inventario de bases de datos Cloud SQL (clouddatabases.csv + hoja CLOUDSQL_DATABASES) |
| 1.5.0 | 2026-04-15 | POR PROYECTO: desglose DEV/QA/STAG + gráfico líneas por entorno y tipo recurso |
| 1.4.0 | 2026-04-15 | MACHINE TYPE y SERVICE TYPE: columnas DEV/QA/STAG + tabla por proyecto en SERVICE TYPE |
| 1.3.0 | 2026-04-15 | RESUMEN: tabla con columnas DEV/QA/STAG + gráfico agrupado por entorno |
| 1.2.0 | 2026-04-15 | RADAR PROYECTO: ejes=tipos recurso, series=entornos (líneas, no relleno) |
| 1.1.0 | 2026-04-14 | Agregar gráfico radar por proyecto consolidando entornos dev/qa/stag |
| 1.0.0 | 2026-04-13 | Paralelización del script bash + generación Excel con 6 hojas de análisis |
