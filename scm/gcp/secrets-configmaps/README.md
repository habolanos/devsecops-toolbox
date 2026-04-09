# GCP Secrets & ConfigMaps Checker

Herramienta SRE para identificar y validar referencias de Secrets y ConfigMaps en Deployments de GKE.

## 🔍 Características

- **Análisis de Deployments** - Escanea todos los deployments en busca de referencias
- **Detección de Secrets** - Identifica secrets referenciados via env, envFrom y volumes
- **Detección de ConfigMaps** - Identifica configmaps referenciados via env, envFrom y volumes
- **Validación de existencia** - Verifica si los secrets/configmaps referenciados existen
- **Multi-cluster** - Puede analizar todos los clusters del proyecto
- **Filtro por namespace** - Opción para analizar namespaces específicos
- **Resumen ejecutivo** - Panel con conteo de estados
- **Resumen de referencias** - Tabla con cantidad de referencias por secret/configmap en orden descendente
- **Modo detalle** - Opción `--details` para ver qué deployments referencian cada recurso
- **Exportación CSV/JSON** - Genera reportes en carpeta `outcome/`

## 📋 Requisitos

- Python 3.8+
- `gcloud` CLI instalado y autenticado
- `kubectl` instalado y configurado
- Permisos IAM requeridos:
  - `container.clusters.list`
  - `container.clusters.get`
  - Acceso a recursos de Kubernetes (secrets, configmaps, deployments)

## 🛠️ Instalación

```bash
pip install rich
```

## 🚀 Uso

```bash
# Analizar todos los clusters del proyecto
python gcp_secrets_configmaps_checker.py

# Especificar proyecto
python gcp_secrets_configmaps_checker.py --project YOUR_PROJECT_ID

# Analizar un cluster específico
python gcp_secrets_configmaps_checker.py --cluster my-cluster

# Analizar un namespace específico
python gcp_secrets_configmaps_checker.py --namespace production

# Modo debug
python gcp_secrets_configmaps_checker.py --debug

# Exportar a CSV
python gcp_secrets_configmaps_checker.py --output csv

# Ver detalle de deployments que referencian cada secret/configmap
python gcp_secrets_configmaps_checker.py --details
```

## 📝 Argumentos

| Argumento | Descripción | Default |
|-----------|-------------|---------|
| `--project` | ID del proyecto GCP | `cpl-corp-cial-prod-17042024` |
| `--cluster` | Nombre del cluster GKE específico | Todos los clusters |
| `--namespace` | Namespace específico a analizar | Todos los namespaces |
| `--debug` | Activa modo debug para diagnóstico | `False` |
| `--output`, `-o` | Exporta resultados (`csv` o `json`) | `None` |
| `--details` | Muestra deployments que referencian cada secret/configmap | `False` |
| `--help`, `-h` | Muestra documentación completa | - |

## 📊 Ejemplo de Salida

```
🔍 Iniciando análisis de Secrets y ConfigMaps en: my-project
🕐 Fecha y hora de revisión: 2026-02-04 15:20:00

☸️  Procesando cluster: gke-prod-cluster

              🔐 Referencias de Secrets y ConfigMaps en Deployments
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
┃ Cluster         ┃ Namespace   ┃ Deployment      ┃   Tipo    ┃ Nombre Ref      ┃  Key  ┃   Uso   ┃ Estado  ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
│ gke-prod        │ production  │ api-service     │  SECRET   │ db-credentials  │ pass  │   env   │  FOUND  │
│ gke-prod        │ production  │ api-service     │ CONFIGMAP │ app-config      │   *   │ envFrom │  FOUND  │
│ gke-prod        │ production  │ web-frontend    │  SECRET   │ tls-cert        │   *   │ volume  │ MISSING │
└─────────────────┴─────────────┴─────────────────┴───────────┴─────────────────┴───────┴─────────┴─────────┘
╭──────────────────────────── 📊 Resumen Ejecutivo ────────────────────────────╮
│ 📦 Deployments: 2  🔐 Secrets: 2  📄 ConfigMaps: 1  ✅ Found: 2  ❌ Missing: 1 │
╰──────────────────────────────────────────────────────────────────────────────╯

⚠️  Se encontraron 1 referencias faltantes!

           🔐 Secrets - Cantidad de Referencias
┏━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Secret           ┃ Refs ┃ Barra                ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ db-credentials   │   12 │ ████████████████████ │
│ tls-cert         │    3 │ █████░░░░░░░░░░░░░░░ │
└──────────────────┴──────┴──────────────────────┘

           📄 ConfigMaps - Cantidad de Referencias
┏━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ ConfigMap        ┃ Refs ┃ Barra                ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ app-config       │    5 │ ████████████████████ │
└──────────────────┴──────┴──────────────────────┘
```

## 🔍 Modo Detalle (`--details`)

Con el parámetro `--details` se muestra una columna adicional indicando qué deployments referencian cada secret/configmap y el tipo de uso:

```
           � Secrets - Cantidad de Referencias
┏━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Secret           ┃ Refs ┃ Barra                ┃ Referenciado por (tipo)               ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ db-credentials   │   12 │ ████████████████████ │ prod/api-svc (env), prod/web (envFrom) │
│ tls-cert         │    3 │ █████░░░░░░░░░░░░░░░ │ prod/ingress (volume)                  │
└──────────────────┴──────┴──────────────────────┴───────────────────────────────────────┘
```

## � Tipos de Referencias Detectadas

| Tipo | Descripción |
|------|-------------|
| **env** | Variable de entorno con `secretKeyRef` o `configMapKeyRef` |
| **envFrom** | Todas las keys via `secretRef` o `configMapRef` |
| **volume** | Montaje como volumen |

## 📁 Formato de Exportación

**CSV** - Columnas: `cluster`, `namespace`, `deployment`, `ref_type`, `ref_name`, `ref_key`, `usage_type`, `container`, `status`, `revision_time`

**JSON** - Array de objetos con los mismos campos

## 🎯 Estados

| Estado | Descripción |
|--------|-------------|
| **FOUND** | El Secret/ConfigMap existe en el namespace |
| **MISSING** | El Secret/ConfigMap NO existe (error potencial) |

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-02-20 | 1.1.0 | Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-04 | 1.0.4 | Agregada columna Namespace a las tablas de resumen de Secrets y ConfigMaps |
| 2026-02-04 | 1.0.3 | Agregado semáforo (ALTO/MEDIO/BAJO) en tablas de resumen según cantidad de referencias |
| 2026-02-04 | 1.0.2 | Agregado parámetro --details para ver deployments que referencian cada secret/configmap |
| 2026-02-04 | 1.1.0 | Agregado resumen de referencias por secret/configmap en orden descendente |
| 2026-02-04 | 1.0.0 | Versión inicial con análisis de secrets y configmaps |

---

## Autor

**Harold Adrian**

---

## Licencia

Internal SRE Tool - Softtek
