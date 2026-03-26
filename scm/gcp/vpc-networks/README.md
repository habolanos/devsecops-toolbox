## Herramientas Disponibles

### 1. gcp_vpc_networks_checker.py
Herramienta SCM para visualizar información detallada de VPC Networks en Google Cloud Platform.

### 2. gcp_ip_addresses_checker.py
Herramienta SCM para analizar la capacidad de red de clusters GKE, verificando la utilización de IPs para pods y servicios.

---

# GCP VPC Networks Checker

Herramienta SCM para visualizar información detallada de VPC Networks en Google Cloud Platform.

## Descripción

Esta herramienta permite obtener una vista completa de la infraestructura de red en GCP, incluyendo:

- **Redes VPC**: Configuración, modo de subnets, MTU, routing mode y peerings
- **Subnets**: Rangos CIDR primarios y secundarios, IPs disponibles, propósito
- **Direcciones IP**: IPs internas y externas, estado de uso, propósito
- **Firewall Rules**: Reglas de ingreso/egreso, protocolos, puertos, prioridades
- **Rutas**: Rutas personalizadas, next hops, prioridades

## Requisitos

- Python 3.8+
- Google Cloud SDK (`gcloud`) instalado y configurado
- Permisos de lectura en Compute Engine

### Permisos IAM Necesarios

#### En el Service Project (proyecto de servicio)
```
compute.addresses.list          # Listar direcciones IP estáticas
compute.instances.list          # Listar VMs para obtener IPs efímeras
compute.subnetworks.listUsable  # Listar subnets usables en Shared VPC
```

#### En el Host Project (proyecto host de Shared VPC)
```
compute.networks.list           # Listar redes VPC
compute.subnetworks.list        # Listar subnets con detalle completo
compute.firewalls.list          # Listar reglas de firewall
compute.routes.list             # Listar rutas
```

#### Detección automática de Shared VPC
```
compute.projects.get            # Detectar si el proyecto es parte de Shared VPC
```

#### Roles predefinidos recomendados

| Rol | Descripción | Proyecto |
|-----|-------------|----------|
| `roles/compute.networkViewer` | Ver recursos de red | Host Project |
| `roles/compute.viewer` | Ver recursos de compute | Service Project |

> **Nota**: Si no tienes permisos en el Host Project, la herramienta mostrará información limitada usando fallbacks (subnets inferidas desde IPs, sin firewall/routes).

## Instalación

```bash
cd gcp/vpc-networks
pip install -r requirements.txt
```

## Uso

### Vista completa (todas las secciones)

```bash
python gcp_vpc_networks_checker.py --project <PROJECT_ID>
```

### Vistas específicas

```bash
# Solo redes VPC
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --view networks

# Solo subnets
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --view subnets

# Solo direcciones IP
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --view ips

# Solo reglas de firewall
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --view firewall

# Solo rutas
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --view routes
```

### Filtros

```bash
# Filtrar por red específica
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --network my-vpc

# Filtrar por región
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --region us-central1

# Combinar filtros
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --network my-vpc --region us-central1
```

### Exportar resultados

```bash
# Exportar a CSV
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --output csv

# Exportar a JSON
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --output json
```

### Modo debug

```bash
python gcp_vpc_networks_checker.py --project <PROJECT_ID> --debug
```

## Argumentos

| Argumento | Descripción | Valor por defecto |
|-----------|-------------|-------------------|
| `--project` | ID del proyecto GCP | Proyecto configurado en gcloud |
| `--view` | Vista específica: all, networks, subnets, ips, firewall, routes | all |
| `--network` | Filtrar por nombre de red VPC | - |
| `--region` | Filtrar por región | - |
| `--host-project` | ID del proyecto host en Shared VPC | - |
| `--all-ips` | Muestra todas las IPs incluyendo efímeras de VMs | false |
| `--output`, `-o` | Formato de exportación: csv, json | - |
| `--timezone`, `-tz` | Zona horaria para mostrar fechas | America/Mazatlan (Culiacán) |
| `--debug` | Modo debug para ver comandos ejecutados | false |
| `--help`, `-h` | Mostrar esta documentación | - |

## Salida

### Tabla de Redes VPC

| Columna | Descripción |
|---------|-------------|
| Nombre Red | Nombre de la red VPC |
| Modo Subnet | AUTO (subnets automáticas) o CUSTOM (subnets personalizadas) |
| MTU | Maximum Transmission Unit configurado |
| Routing Mode | REGIONAL o GLOBAL |
| Peerings | Número de VPC peerings configurados |
| Descripción | Descripción de la red |

### Tabla de Subnets

| Columna | Descripción |
|---------|-------------|
| Subnet | Nombre de la subnet |
| Red | Red VPC a la que pertenece |
| Región | Región de GCP |
| CIDR Primario | Rango de IPs principal |
| IPs Disp. | Número de IPs disponibles (descontando reservadas) |
| Propósito | PRIVATE, ILB, PROXY, PSC |
| Rangos Sec. | Número de rangos secundarios |
| Private Google | Acceso privado a Google APIs |

### Tabla de Direcciones IP

| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre de la dirección reservada |
| Dirección IP | IP asignada |
| Tipo | INTERNAL o EXTERNAL |
| Propósito | Uso específico de la IP |
| Región | Región (o GLOBAL) |
| Subnetwork | Subnet asociada |
| Estado | IN_USE o RESERVED |
| Usuario | Recurso que usa la IP |

### Tabla de Firewall Rules

| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre de la regla |
| Red | Red VPC |
| Dir | INGRESS o EGRESS |
| Acción | ALLOW o DENY |
| Prioridad | Prioridad de la regla (menor = mayor prioridad) |
| Protocolos/Puertos | Protocolos y puertos afectados |
| Origen/Destino | Rangos de IP o tags |
| Habilitada | Estado de la regla |

### Tabla de Rutas

| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre de la ruta |
| Red | Red VPC |
| Destino CIDR | Rango de destino |
| Next Hop | Siguiente salto (gateway, instancia, IP, peering, ILB) |
| Prioridad | Prioridad de la ruta |
| Tags | Tags de red aplicables |

## Archivos de Salida

Los archivos se generan en la carpeta `outcome/` con el formato:

```
vpc_<tipo>_<proyecto>_<timestamp>.<formato>
```

Ejemplo:
- `vpc_subnets_my-project_20240115_143022.csv`
- `vpc_firewall_my-project_20240115_143022.json`

## Ejemplos de Uso

### Auditoría de seguridad de firewall

```bash
python gcp_vpc_checker.py --project prod-project --view firewall --output csv
```

### Inventario de IPs de una red específica

```bash
python gcp_vpc_checker.py --project prod-project --network vpc-prod --view ips
```

### Revisar subnets en una región

```bash
python gcp_vpc_networks_checker.py --project prod-project --region us-east1 --view subnets
```

### Shared VPC: Ver networks/subnets del host project

```bash
# Cuando el proyecto es un service project de Shared VPC
python gcp_vpc_networks_checker.py --project service-project --host-project host-project-id
```

## Solución de Problemas

### Error: No se encontró gcloud
Asegúrate de tener Google Cloud SDK instalado y en el PATH.

### Error: Permisos insuficientes
Verifica que tu cuenta tenga los permisos IAM necesarios listados arriba.

### No se muestran datos
- Verifica que el proyecto tenga recursos de red
- Usa `--debug` para ver los comandos ejecutados
- Verifica la autenticación con `gcloud auth list`

---

# GCP IP Addresses Checker

Herramienta SCM para analizar la capacidad de red de clusters GKE, verificando la utilización de IPs para pods y servicios.

## Descripción

Esta herramienta analiza la utilización de IPs en clusters GKE para identificar riesgos de agotamiento de capacidad de red:

- **Metadatos de Red**: Obtiene rangos CIDR para pods y servicios desde GCP
- **Conteo de Pods**: Cuenta pods activos con IP asignada usando kubectl
- **Conteo de Servicios**: Cuenta servicios con ClusterIP asignada
- **Análisis de Utilización**: Calcula porcentajes y genera alertas
- **Detección de Riesgos**: Identifica cuando se acerca a los límites de capacidad

## Requisitos

- Python 3.8+
- Google Cloud SDK (`gcloud`) instalado y configurado
- `kubectl` instalado y configurado
- Permisos de lectura en GKE y Compute Engine

### Permisos IAM Necesarios

```
container.clusters.get        # Obtener metadatos del cluster
container.clusters.getCredentials # Obtener credenciales kubectl
compute.networks.list         # Acceso a información de VPC
```

## Instalación

```bash
cd gcp/vpc-networks
pip install -r requirements.txt
```

## Uso

### Análisis básico

```bash
python gcp_ip_addresses_checker.py --project <PROJECT_ID> --cluster <CLUSTER_NAME> --region <REGION>
```

### Ejemplos

```bash
# Cluster default (cpl-xxxx-yyyy-zzzz-99999999, gke-aaaaa-bbbbb-ccccc-99, us-central1)
python gcp_ip_addresses_checker.py

# Cluster específico
python gcp_ip_addresses_checker.py --project mi-proyecto --cluster mi-cluster --region us-east1

# Exportar a JSON
python gcp_ip_addresses_checker.py --project mi-proyecto --output json

# Modo debug
python gcp_ip_addresses_checker.py --debug
```

## Argumentos

| Argumento | Descripción | Valor por defecto |
|-----------|-------------|-------------------|
| `--project` | ID del proyecto GCP | cpl-xxxx-yyyy-zzzz-99999999 |
| `--cluster` | Nombre del cluster GKE | gke-aaaaa-bbbbb-ccccc-99 |
| `--region` | Región del cluster GKE | us-central1 |
| `--output`, `-o` | Formato de exportación: csv, json | - |
| `--timezone`, `-tz` | Zona horaria para mostrar fechas | America/Mazatlan |
| `--debug` | Modo debug para ver comandos ejecutados | false |
| `--help`, `-h` | Mostrar esta documentación | - |

## Salida

### Tabla de Capacidad de Red

| Componente | Rango CIDR | Máscara | IPs Ocupadas | IPs Totales | Utilización | Estado |
|-------------|------------|---------|--------------|-------------|-------------|---------|
| 📦 Pods | 10.44.0.0/14 | /14 | 1250 | 262142 | 4.77% | ✓ |
| 🔧 Servicios | 10.32.0.0/20 | /20 | 45 | 4094 | 1.10% | ✓ |

### Panel de Alertas

El sistema genera alertas basadas en umbrales:

- **🚨 CRÍTICO**: IPs de Servicios > 90% (No se pueden desplegar más Apps)
- **⚠️ WARNING**: IPs de Pods > 80% (Cerca del límite)
- **✅ OK**: Capacidad dentro de rangos normales

## Archivos de Salida

Los archivos se generan en la carpeta `outcome/` con el formato:

```
ip_addresses_report_<project_id>_<timestamp>.<formato>
```

Ejemplo:
- `ip_addresses_report_my-project_20240220_143022.json`
- `ip_addresses_report_my-project_20240220_143022.csv`

## Solución de Problemas

### Error: No se puede acceder al cluster
- Verifica que el cluster exista y esté corriendo
- Verifica permisos de GKE con `gcloud container clusters list`
- Usa `--debug` para ver los comandos ejecutados

### Error: kubectl no encontrado
Asegúrate de tener kubectl instalado y en el PATH.

### Error: Permisos insuficientes
Verifica que tu cuenta tenga los permisos IAM necesarios listados arriba.

---

## History

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-02-26 | 1.0.0 | Versión inicial - Python equivalent del script shell gcp_ip_addresses_checker.sh |
| 2026-02-20 | 1.2.0 | Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-19 | 1.1.0 | Validación de conexión GCP al inicio (check_gcp_connection) |
| 2026-02-13 | 1.0.8 | Consolidar tablas de IPs, documentar permisos IAM completos para Shared VPC |
| 2026-02-13 | 1.0.7 | Parámetro --all-ips, resumen de IPs por subnet, tabla estilo GCP solo con estáticas por defecto |
| 2026-02-13 | 1.0.6 | Dos tablas de IPs: estáticas (original) y completa estilo GCP Console al final |
| 2026-02-13 | 1.0.5 | Tabla de IPs similar a consola GCP con VPC Network, Type, Network Tier e IPs de VMs |
| 2026-02-13 | 1.0.4 | Fallback a list-usable para subnets cuando no hay permisos en host project |
| 2026-02-13 | 1.0.3 | Detección automática del host project de Shared VPC |
| 2026-02-13 | 1.0.2 | Agregado soporte para Shared VPC con parámetro --host-project |
| 2026-02-13 | 1.0.1 | Renombrado de gcp_vpc_checker.py a gcp_vpc_networks_checker.py |
| 2026-02-13 | 1.0.0 | Versión inicial con soporte para networks, subnets, IPs, firewall y routes |

---

## Autor

**Harold Adrian**
