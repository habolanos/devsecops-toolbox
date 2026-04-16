# Google Cloud Platform Tools

Este directorio contiene herramientas y scripts para interactuar con Google Cloud Platform (GCP) y automatizar tareas comunes de operaciones en la nube.

## 📋 Contenido

| Directorio/Archivo | Descripción |
|--------------------|-------------|
| **[artifact-registry/](artifact-registry/README.md)** | Extractor de imágenes Docker de Artifact Registry con filtrado y exportación a Excel |
| **[cloud-sql/](cloud-sql/README.md)** | Herramientas para Cloud SQL: verificación de conectividad y monitoreo de disco |
| **[monitoring/](monitoring/README.md)** | Monitoreo de recursos GCP/GKE y generación de reportes de deployments |
| **[notification/](notification/README.md)** | Scripts de notificaciones y alertas vía webhooks de Google Chat |
| **[rolesypermisos/](rolesypermisos/README.md)** | Reportes detallados de roles y permisos IAM en proyectos GCP |
| **[vpc-networks/](vpc-networks/README.md)** | Visualización de VPC Networks: subnets, IPs, CIDR, firewall y rutas |
| **[gateway-services/](gateway-services/README.md)** | Monitoreo de Gateways, Routes, Services y Policies en GKE |
| **[load-balancer/](load-balancer/README.md)** | Análisis de Load Balancers, Backend Services, Health Checks y SSL |
| **[service-account/](service-account/README.md)** | Lista y analiza Service Accounts, keys y roles IAM |
| **[connectivity/](connectivity/README.md)** | Validación de conectividad Pod GKE → Cloud SQL |
| **[cluster-gke/](cluster-gke/README.md)** | Monitoreo de clusters GKE con métricas de recursos |
| **[certificate-manager/](certificate-manager/README.md)** | Monitoreo de certificados en Certificate Manager |
| **[secrets-configmaps/](secrets-configmaps/README.md)** | Análisis de Secrets y ConfigMaps en GKE |
| **[reports-viewer/](reports-viewer/README.md)** | Visualizador de reportes JSON con gráficos HTML interactivos |
| **[cloud-run/](cloud-run/README.md)** | Checker de Cloud Run: services, revisions, jobs, IAM y networking |
| **[cloud-armor/](cloud-armor/README.md)** | Auditoría de Security Policies (WAF/DDoS), cobertura de backends y gaps de seguridad |
| **[inventory/](inventory/README.md)** | Inventario consolidado de recursos GCP (GKE, Cloud SQL, Cloud Run, Pub/Sub) con Excel y gráficos radar |
| **[tools.py](tools.py)** | Lanzador unificado de herramientas GCP con menú interactivo |

## 🚀 GCP Tools Launcher

El archivo `tools.py` proporciona una interfaz de menú interactivo para ejecutar las herramientas desde un solo lugar:

```bash
python tools.py
```

### Herramientas disponibles en el launcher

| Opción | Grupo | Herramienta | Descripción |
|--------|-------|-------------|-------------|
| 1 | Monitoreo | Monitoreo de Recursos GCP | Monitorea CPU, memoria, SQL, etc. |
| 2 | Monitoreo | Reporte de Despliegues GKE | Genera reporte detallado de deployments en GKE |
| 3 | IAM & Security | Reporte de Roles y Permisos IAM | Genera reporte de roles y permisos IAM del proyecto |
| 4 | IAM & Security | Service Account Checker | Lista y analiza Service Accounts, keys y roles IAM |
| 5 | IAM & Security | Certificate Manager Checker | Monitorea certificados SSL/TLS en Certificate Manager |
| 6 | Security | Cloud Armor Checker | Audita Security Policies (WAF/DDoS), cobertura de backends |
| 7 | Database | Cloud SQL Disk Monitor | Monitorea uso de disco en instancias Cloud SQL |
| 8 | Database | Cloud SQL Database Checker | Lista bases de datos por instancia de Cloud SQL |
| 9 | Database | Cloud SQL Comparator | Compara instancias Cloud SQL entre dos proyectos GCP |
| 10 | Networking | VPC Networks Checker | Visualiza VPC, subnets, IPs, CIDR, firewall y rutas |
| 11 | Networking | Gateway Services Checker | Monitorea Gateways, Routes, Services y Policies en GKE |
| 12 | Networking | Load Balancer Checker | Analiza Load Balancers, Backend Services, Health Checks y SSL |
| 13 | Networking | IP Addresses Checker | Analiza capacidad de red de clusters GKE (IPs de pods y servicios) |
| 14 | Kubernetes | GKE Cluster Checker | Monitorea clusters GKE, versiones, nodos y pods |
| 15 | Kubernetes | Secrets & ConfigMaps Checker | Valida referencias de Secrets y ConfigMaps en GKE |
| 16 | Kubernetes | Pod Connectivity Checker | Valida conectividad desde un Pod GKE hasta Cloud SQL |
| 17 | Kubernetes | Deploy Dependency Checker | Analiza ConfigMaps de un deployment y valida conexiones a BD |
| 18 | Kubernetes | Cloud Run Checker | Analiza servicios Cloud Run, revisiones, Jobs, IAM y networking |
| 19 | Kubernetes | **Deployment Validator** | **Valida ConfigMaps, Secrets y conectividad de un Deployment** |
| 20 | Artifacts | Artifact Registry Tag Filter | Filtra y exporta imágenes de Artifact Registry a Excel |
| 22 | Inventory | Inventario GKE + Cloud SQL | Genera inventario consolidado de recursos GCP (CSV + Excel con gráficos radar) |
| 21 | Reports | Visualizar Reportes JSON | Genera dashboard HTML con gráficos desde reportes JSON |
| A | Sistema | Ejecutar Todos (Checkers) | Corre automáticamente los checkers soportados |
| Q | Sistema | Salir | Cierra el menú (atajo Q/q) |

### Características del launcher

- **UI moderna con Rich**: Paneles, tablas con colores, semáforos y emojis
- **Grupos de herramientas**: Organización por categorías (Monitoreo, IAM, Database, Network, etc.) con orden consistente del menú
- **Indicadores de estado**: Semáforos visuales (🟢 Listo, 🟡 Advertencia, 🔴 Error)
- Crea automáticamente un entorno virtual en `.venv/`
- Instala dependencias de cada herramienta automáticamente
- Caché de dependencias instaladas para ejecución más rápida

### Instalación de dependencias del launcher

Para habilitar la interfaz moderna con Rich (opcional pero recomendado):

```bash
pip install -r requirements.txt
```

> **Nota**: Si Rich no está instalado, el launcher funcionará con una interfaz básica de texto.

## 🔧 Requisitos

- Cuenta de Google Cloud Platform
- Google Cloud SDK instalado y configurado (`gcloud`)
- Python 3.8 o superior
- `kubectl` (para herramientas de GKE)
- Permisos de lectura en los proyectos de GCP a monitorear

## 📦 Estructura de Directorios

```
gcp/
├── .venv/                    # Entorno virtual (creado automáticamente)
├── artifact-registry/        # Extractor de imágenes de Artifact Registry
├── cloud-sql/                # Herramientas de Cloud SQL
├── monitoring/               # Monitoreo y reportes GKE
├── notification/             # Webhooks y notificaciones
├── outcome/                  # Directorio de salida de reportes
├── rolesypermisos/           # Reportes IAM
├── service-account/          # Service accounts (templates)
├── vpc-networks/             # Checker de VPC Networks, subnets, IPs, CIDR
├── gateway-services/         # Checker de Gateway API (Gateways, Routes, Services, Policies)
├── cloud-armor/              # Checker de Cloud Armor
├── inventory/                # Inventario consolidado GKE + Cloud SQL (CSV + Excel)
├── gcp_tools_launcher.py     # Launcher principal
└── README.md                 # Este archivo
```

## 📄 Documentación Adicional

- [Documentación de Google Cloud](https://cloud.google.com/docs)
- [Google Cloud Python Client Libraries](https://cloud.google.com/python/docs/reference)

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-04-16 | 1.9.0 | Nueva herramienta: Inventario GKE + Cloud SQL - Genera inventario consolidado de recursos GCP (CSV + Excel con gráficos radar) |
| 2026-03-26 | 1.8.0 | Nueva herramienta: Deployment Validator - Valida ConfigMaps, Secrets y conectividad de Deployments |
| 2026-03-25 | 1.7.0 | Nueva herramienta: Cloud Run Checker para analizar servicios, revisiones, jobs, IAM y networking |
| 2026-03-09 | 1.6.1 | Menú reorganizado por grupos (Monitoreo → Sistema) y documentación actualizada (Deploy Dependency Checker) |
| 2026-02-25 | 1.6.0 | Nueva herramienta: Cloud SQL Database Checker para listar bases de datos por instancia |
| 2026-02-25 | 1.5.0 | UI modernizada con Rich: paneles, tablas con grupos, semáforos, emojis. Agregada metadata (versión, autor) |
| 2025-02-13 | 1.4.0 | Nueva herramienta: Gateway Services Checker para monitorear Gateways, Routes, Services y Policies en GKE |
| 2026-02-13 | 1.3.1 | Renombrado script gcp_vpc_checker.py a gcp_vpc_networks_checker.py |
| 2026-02-13 | 1.3.0 | Nueva herramienta: VPC Networks Checker para visualizar redes, subnets, IPs, CIDR, firewall y rutas |
| 2026-01-12 | 1.2.0 | Launcher actualizado: agregadas herramientas Cloud SQL Connectivity Checker, Cloud SQL Disk Monitor y Artifact Registry Tag Filter |
| 2026-01-12 | 1.1.0 | Actualización de documentación: tabla de contenidos, estructura de directorios, detalle del launcher |
| 2025-01-01 | 1.0.0 | Versión inicial del README |

---

## Autor

**Harold Adrian**
