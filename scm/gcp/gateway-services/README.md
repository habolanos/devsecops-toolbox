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
```

### Exportar Resultados

```bash
# Exportar a CSV
python gcp_gateway_checker.py --output csv

# Exportar a JSON
python gcp_gateway_checker.py --output json
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
| `--view` | Vista específica (all, gateways, routes, services, policies) | all |
| `--debug` | Activa modo debug para ver comandos gcloud | False |
| `--output, -o` | Exporta a archivo (csv, json) | - |
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
| 2026-02-20 | 2.1.0 | Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-19 | 2.0.1 | Validación de conexión GCP al inicio (check_gcp_connection) |
| 2026-02-16 | 2.0.0 | Ejecución paralela (recursos y endpoints), Live display con progreso dinámico, timezone configurable |
| 2025-02-13 | 1.1.0 | Agregado soporte para --project y --cluster, escaneo de múltiples clusters |
| 2025-02-13 | 1.0.0 | Versión inicial con soporte para Gateways, Routes, Services y Policies |

---

## Autor

**Harold Adrian**
