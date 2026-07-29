# GCP Gateway Services Checker

Herramienta SRE para monitorear y diagnosticar **Gateways, Routes, Services y Policies** en clusters GKE usando la API de Kubernetes Gateway.

## Descripción

Esta herramienta proporciona una vista consolidada de los recursos de Gateway API en GKE, permitiendo identificar problemas de configuración, conectividad y estado de salud de los servicios.

### Recursos Monitoreados

| Recurso | Descripción |
|---------|-------------|
| **Gateways** | Load balancers que definen puertos, protocolos y configuración TLS |
| **HTTPRoutes** | Rutas que definen cómo las solicitudes HTTP/HTTPS se dirigen a Services |
| **Services** | Endpoints de red para Pods con discovery y load balancing |
| **Policies** | HealthCheckPolicies y GCPBackendPolicies adjuntas a recursos |

## Requisitos

- Python 3.8+
- `kubectl` configurado con acceso al cluster GKE
- Permisos de lectura sobre los recursos de Gateway API

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### Uso Básico

```bash
# Escanear todos los clusters del proyecto por defecto
python gcp_gateway_checker.py

# Escanear un proyecto específico
python gcp_gateway_checker.py --project mi-proyecto-gcp

# Escanear solo un cluster específico
python gcp_gateway_checker.py --project mi-proyecto-gcp --cluster gke-corp-cial-prod-01

# Escanear un namespace específico
python gcp_gateway_checker.py --namespace importacion

# Ver solo Gateways
python gcp_gateway_checker.py --view gateways

# Ver solo Routes
python gcp_gateway_checker.py --view routes

# Ver solo Services
python gcp_gateway_checker.py --view services

# Ver solo Policies
python gcp_gateway_checker.py --view policies

# Detectar HTTPRoutes duplicadas/conflictivas por Gateway
python gcp_gateway_checker.py --view duplicates
```

### Exportar Resultados

```bash
# Exportar a CSV
python gcp_gateway_checker.py --output csv

# Exportar a JSON
python gcp_gateway_checker.py --output json

# Exportar a HTML (dashboard interactivo)
python gcp_gateway_checker.py --output html
```

> **Nota:** El dashboard HTML se genera **por defecto** en cada ejecución, sin necesidad de especificar `--output html`. Se guarda en `outcome/gateway_dashboard_<timestamp>.html`.

### Dashboard HTML Interactivo

El dashboard HTML se genera **por defecto** en cada ejecución y incluye:

- **Tarjetas resumen**: Gateways healthy, HTTPRoutes healthy, Services healthy, Policies, Duplicates CRITICAL
- **Pestañas**: Gateways, HTTPRoutes, Services, Policies, Duplicates
- **Tablas ordenables**: Click en cualquier columna para ordenar
- **Busqueda en vivo**: Filtra resultados por texto en cada tabla
- **Pills de estado**: Colores semaforicos (verde=healthy, rojo=unhealthy, amarillo=degraded)
- **Deteccion de duplicados**: Conflictos CRITICAL/HIGH/MEDIUM con detalles de rutas conflictivas
- **Columna Revisión**: Fecha/hora de revision en cada fila de todas las tablas
- **Fecha de generacion**: Timestamp de cuando se genero el dashboard (en header y footer)
- **Carga de JSON**: Boton "Cargar JSON" para importar archivos JSON exportados y actualizar el dashboard dinamicamente
- **Diseño responsive**: Funciona en desktop y movil
- **Tema oscuro**: Interfaz moderna con colores oscuros

El archivo se guarda en `outcome/gateway_dashboard_<timestamp>.html`.

### Deteccion de HTTPRoutes Duplicadas

Usa `--view duplicates` para identificar conflictos entre HTTPRoutes:

- **CRITICAL**: Mismo hostname + path + method en mismo gateway/listener
- **HIGH**: Paths solapados (PathPrefix) en mismo hostname/gateway
- **MEDIUM**: Mismo hostname en mismo gateway desde routes diferentes sin sectionName especifico

```bash
python gcp_gateway_checker.py --view duplicates
```

### Modo Debug

```bash
python gcp_gateway_checker.py --debug
```

## Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--project` | ID del proyecto GCP | cpl-corp-cial-prod-17042024 |
| `--cluster` | Nombre del cluster GKE específico | Todos los clusters |
| `--namespace` | Namespace específico | Todos |
| `--view` | Vista específica (all, gateways, routes, services, policies, duplicates) | all |
| `--debug` | Activa modo debug para ver comandos gcloud | False |
| `--output, -o` | Exporta a archivo (csv, json, html) | html (dashboard por defecto) |
| `--timezone`, `-tz` | Zona horaria para mostrar fechas | America/Mazatlan (Culiacán) |
| `--parallel` | Ejecuta procesamiento en paralelo | True |
| `--no-parallel` | Desactiva procesamiento paralelo | False |
| `--max-workers` | Número máximo de workers paralelos | 4 |
| `--help, -h` | Muestra esta ayuda | - |

## Semáforo SRE

### Gateways

| Estado | Significado |
|--------|-------------|
| 🟢 **HEALTHY** | Gateway programado y funcionando correctamente |
| 🟡 **ACCEPTED** | Gateway aceptado pero pendiente de programación |
| 🔴 **UNHEALTHY** | Gateway con problemas de configuración |

### Routes

| Estado | Significado |
|--------|-------------|
| 🟢 **HEALTHY** | Route con gateway adjunto y reglas configuradas |
| 🟡 **NO RULES** | Route sin reglas de enrutamiento |
| 🔴 **NO GATEWAY** | Route sin gateway adjunto |

### Services

| Estado | Significado |
|--------|-------------|
| 🟢 **HEALTHY** | Service con todos los pods ready |
| 🟡 **DEGRADED** | Service con algunos pods no ready |
| 🟡 **PENDING** | Service pendiente de asignación de IP |
| 🔴 **NO PODS** | Service sin pods backing |

### Policies

| Estado | Significado |
|--------|-------------|
| 🟢 **ATTACHED** | Policy correctamente adjunta al target |
| 🔴 **DETACHED** | Policy no adjunta o con errores |

## Problemas Comunes Detectados

### 1. Gateway sin IP asignada
- **Causa**: El load balancer no se ha provisionado
- **Acción**: Verificar quota de IPs y permisos de la cuenta de servicio

### 2. Route sin Gateway
- **Causa**: `parentRefs` no configurado o Gateway no existe
- **Acción**: Verificar que el Gateway existe y el `parentRefs` es correcto

### 3. Service con 0/0 Pods
- **Causa**: Selector no coincide con ningún Pod
- **Acción**: Verificar labels del Deployment y selector del Service

### 4. Policy Detached
- **Causa**: `targetRef` apunta a un recurso inexistente
- **Acción**: Verificar que el Service target existe en el namespace

### 5. HTTPRoutes Duplicadas por Gateway
- **Causa**: Dos o mas HTTPRoutes adjuntas al mismo Gateway declaran los mismos hostnames y paths
- **Acción**: Consolidar las routes o separar por listener (sectionName)

## Deteccion de HTTPRoutes Duplicadas

La vista `--view duplicates` analiza todas las HTTPRoutes y detecta conflictos agrupandolos por severidad:

### Niveles de Severidad

| Severidad | Criterio | Descripcion |
|-----------|---------|-------------|
| **CRITICAL** | Gateway + Hostname + Path + Method identicos | El controller no sabe a cual route enviar el request. Conflicto seguro. |
| **HIGH** | Paths solapados (PathPrefix) en mismo Gateway + Hostname | Ej: `/api` y `/api/v1` causan ambiguedad de routing. |
| **MEDIUM** | Mismo Hostname en mismo Gateway sin sectionName especifico | Ambas routes adjuntas a todos los listeners del gateway. Revisar. |

### Columnas del Reporte

| Columna | Contenido |
|---------|-----------|
| **Severity** | CRITICAL / HIGH / MEDIUM |
| **Gateway** | namespace/name del Gateway |
| **Listener** | sectionName o `*` si no especifica |
| **Hostname** | Hostname en conflicto |
| **Path** | Path(s) en conflicto |
| **Method** | Metodo HTTP o `*` |
| **Route 1** | namespace/name de la primera route |
| **Route 2** | namespace/name de la segunda route |
| **Conflict Type** | Descripcion del tipo de conflicto |

### Uso

```bash
# Detectar duplicidades en todos los clusters
python gcp_gateway_checker.py --view duplicates

# Detectar en un namespace especifico
python gcp_gateway_checker.py --view duplicates --namespace mi-namespace

# Exportar resultados de duplicidades
python gcp_gateway_checker.py --view duplicates -o csv
python gcp_gateway_checker.py --view duplicates -o json
```

## Archivos de Salida

Los archivos exportados se guardan en el directorio `outcome/`:

```
outcome/
├── gateway_gateways_20250213_143000.csv
├── gateway_routes_20250213_143000.csv
├── gateway_services_20250213_143000.csv
└── gateway_policies_20250213_143000.csv
```

## Ejemplos de Diagnóstico

### Verificar conectividad de un servicio

```bash
# 1. Listar servicios y verificar pods
python gcp_gateway_checker.py --view services --namespace mi-namespace

# 2. Si hay 0/0 pods, verificar el deployment
kubectl get deployments -n mi-namespace

# 3. Verificar HTTPRoute asociada
python gcp_gateway_checker.py --view routes --namespace mi-namespace
```

### Verificar estado de Gateway

```bash
# 1. Listar gateways
python gcp_gateway_checker.py --view gateways

# 2. Ver detalle del gateway específico
kubectl describe gateway mi-gateway -n mi-namespace
```

---

## History

| Fecha | Versión | Cambios |
|-------|---------|---------|
| 2026-07-29 | 2.3.1 | Columna Revisión en todas las tablas, fecha de generacion del dashboard, boton Cargar JSON para importar archivos JSON exportados |
| 2026-07-29 | 2.2.2 | Soporte para multiples proyectos separados por coma en --project |
| 2026-07-29 | 2.2.1 | Ajuste: prompt de cluster en tools.py ahora usa TODOS por defecto (vacio = todos) |
| 2026-07-29 | 2.2.0 | Nueva vista `--view duplicates`: deteccion de HTTPRoutes duplicadas/conflictivas por Gateway con 3 niveles de severidad (CRITICAL/HIGH/MEDIUM) |
| 2026-02-20 | 2.1.0 | Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-19 | 2.0.1 | Validación de conexión GCP al inicio (check_gcp_connection) |
| 2026-02-16 | 2.0.0 | Ejecución paralela (recursos y endpoints), Live display con progreso dinámico, timezone configurable |
| 2025-02-13 | 1.1.0 | Agregado soporte para --project y --cluster, escaneo de múltiples clusters |
| 2025-02-13 | 1.0.0 | Versión inicial con soporte para Gateways, Routes, Services y Policies |

---

## Autor

**Harold Adrian**
