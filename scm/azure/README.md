# Azure Tools Launcher

Conjunto completo de **39 herramientas** SRE/DevSecOps para Microsoft Azure, con paridad funcional respecto a las suites de `scm/gcp` y `scm/aws`.

## Características

- ✅ **39 herramientas** implementadas (todas las opciones del menú ejecutan código real)
- ✅ **Backend Azure CLI** — las herramientas usan `az ... -o json` (no requieren SDK `azure-mgmt-*`)
- ✅ **AKS vía `az aks get-credentials` + `kubectl -o json`** (sin dep `kubernetes`)
- ✅ **Monitoreo integral** de recursos Azure
- ✅ **Seguridad y compliance** (RBAC, WAF, Key Vault, auditoría)
- ✅ **Kubernetes (AKS)** - Monitoreo, validación, análisis de causa raíz
- ✅ **Bases de datos** - Azure SQL, Cosmos DB, backups
- ✅ **Networking** - VNets, NSGs, Application Gateway, connectivity E2E
- ✅ **App Service & Functions** - Monitoreo, seguridad, costos, tráfico
- ✅ **Inventario y reportes** - Recursos, compliance Policy, Service Bus
- ✅ **Event Tracker** - Rastreo de eventos Activity Log/Service Health
- ✅ **Dashboards HTML** - Unified dashboard, compliance, métricas con Chart.js
- ✅ **Multi-suscripción** - Reporter de Service Principals entre suscripciones

## Arquitectura

```
scm/azure/
├── tools.py               # Launcher unificado (menú + ejecución real)
├── azure_common.py        # Helper compartido: run_az/try_az, kubectl,
│                          #   resolve_subscription, rg_of, exports, outcome/
├── monitoring/            # Azure monitor, AKS deployments, node/pod metrics
├── cluster-aks/           # Cluster, nodepools, WI, pod security, validator, ACR
├── connectivity/          # VNet, NSG, AppGW, connectivity checker
├── azure-sql/             # SQL monitor, Cosmos, backup validator
├── rolesypermisos/        # Roles audit, access validator
├── service-accounts/      # SP analyzer, multi-subscription reporter
├── security/              # WAF / Front Door checker
├── secrets-configmaps/    # Key Vault + secrets checker
├── app-service/           # Monitor, security, validator, health, cost, traffic
├── container-apps/        # Container Apps metrics monitor
├── connectivity/          # Networking
├── inventory/             # Resource inventory
├── reports-viewer/        # Compliance report (Policy states)
├── event-tracker/         # Activity Log / Service Health tracker
├── consolidation/         # Unified dashboard, functions analyzer, consolidator
├── artifacts/             # ACR image filter
└── servicebus/            # Service Bus monitor (colas/topics/DLQ)
```

Las herramientas comparten `azure_common.py`: resolución de suscripción
(`--subscription` → `config.json` → `az account show`), ejecución
tolerante a errores (`try_az`), `kubectl` para AKS, export JSON/CSV/HTML
en `outcome/` y consola Rich opcional con UTF-8 en Windows.

## Instalación

### Requisitos

- Python 3.8+
- Azure CLI (`az` command)
- Credenciales de Azure configuradas

### Setup

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar credenciales Azure
az login

# 3. Ejecutar launcher
python tools.py
```

## Herramientas Disponibles

### Monitoreo (1-2)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 1 | Monitoreo de Recursos Azure | Monitorea VMs, App Service, SQL, etc. |
| 2 | Reporte de Despliegues AKS | Reporte detallado de despliegues en AKS |

### IAM & Security (3-5)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 3 | Auditoría de Roles y Permisos | Audita roles y permisos RBAC |
| 4 | Service Principals Analyzer | Analiza service principals y credenciales |
| 5 | Access Control Validator | Valida controles de acceso |

### Database (6-8)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 6 | Azure SQL Database Monitor | Monitorea Azure SQL |
| 7 | Cosmos DB Analyzer | Analiza Cosmos DB |
| 8 | Database Backup Validator | Valida backups |

### Networking (9-12)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 9 | Virtual Network Analyzer | Analiza VNets |
| 10 | Network Security Groups Audit | Audita NSGs |
| 11 | Application Gateway Monitor | Monitorea App Gateway |
| 12 | Connectivity Checker | Verifica conectividad |

### Kubernetes - AKS (13-18)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 13 | AKS Cluster Monitor | Monitorea clusters AKS |
| 14 | AKS Node Pool Analyzer | Analiza node pools |
| 15 | Workload Identity Validator | Valida Workload Identity |
| 16 | Pod Security Policy Audit | Audita políticas de seguridad |
| 17 | AKS Deployment Validator | Valida despliegues |
| 18 | Azure Container Registry Analyzer | Analiza ACR |

### App Service (19-21, 26, 31-33)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 19 | App Service Monitor | Monitorea App Services |
| 20 | App Service Security Auditor | Audita seguridad (TLS, CORS, auth, IP restrictions) |
| 21 | App Service Deployment Validator | Valida AlwaysOn, health check, slots, backups |
| 26 | Azure Container Apps Metrics Monitor | Métricas de Container Apps (homólogo a Cloud Run) |
| 31 | App Service Health Analyzer | Score 0-100 con métricas 5xx/CPU/memoria |
| 32 | App Service Cost Analyzer | Costos por plan, recomendaciones de SKU |
| 33 | App Service Traffic Analyzer | Tráfico, error rate, distribución por slots |

### Inventory & Reports (22-25, 34-35, 38)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 22 | Azure Resource Inventory | Inventario completo de recursos |
| 23 | Azure Compliance Report | Recursos NonCompliant de Azure Policy |
| 24 | Event Tracker | Activity Log + Service Health con severidad |
| 25 | Azure Unified Dashboard | Dashboard HTML ejecutivo con health score |
| 34 | Azure Functions Analyzer | Funciones, triggers, seguridad, CORS |
| 35 | Infrastructure Consolidator | AppGW→backends→apps con detección de huérfanos |
| 38 | Service Bus Monitor | Colas/topics, DLQ, capacidad, multi-suscripción |

### Security & Artifacts (27-28, 36-37, 39)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 27 | Azure Front Door / WAF Checker | Políticas WAF, modo Detection, endpoints sin WAF |
| 28 | ACR Image Filter | Filtra imágenes ACR por tag semver/regex → CSV/Excel |
| 29 | AKS Node Resources Monitor | CPU/memoria por nodo (HTML) |
| 30 | AKS Pod Resources Monitor | CPU/memoria por pod (`kubectl top`) |
| 36 | SP Multi-Subscription Reporter | Service Principals entre suscripciones |
| 37 | AKS Deployments Off Analyzer | Deployments no-running con causa raíz |
| 39 | Key Vault Secrets Checker | Vaults RBAC/soft-delete + secretos por vencer |

## Configuración

### Variables de Entorno

Se inyectan automáticamente desde `config.json`:

```
AZURE_SUBSCRIPTION_ID      # ID de suscripción
AZURE_TENANT_ID            # ID del tenant
AZURE_REGION               # Región por defecto
AZURE_CLIENT_ID            # Client ID (si usa service principal)
AZURE_CLIENT_SECRET        # Client secret (si usa service principal)
AKS_CLUSTER_NAME           # Nombre del cluster AKS
AKS_CLUSTER_REGION         # Región del cluster
AZURE_RESOURCE_GROUP       # Grupo de recursos por defecto
```

### Configuración en config.json

```json
{
  "azure": {
    "enabled": true,
    "subscription_id": "<TU_SUBSCRIPTION_ID>",
    "tenant_id": "<TU_TENANT_ID>",
    "region": "eastus",
    "credentials": {
      "type": "cli",
      "client_id": "",
      "client_secret": "",
      "certificate_path": ""
    },
    "kubernetes": {
      "cluster_name": "",
      "cluster_region": "eastus",
      "resource_group": ""
    },
    "defaults": {
      "timezone": "America/Mazatlan",
      "output_format": "json"
    }
  }
}
```

## Autenticación Automática

El launcher valida automáticamente la autenticación:

```bash
# Verifica si está autenticado
az account show

# Si no está autenticado, ejecuta
az login
```

Configurable en `config.json`:

```json
{
  "auth": {
    "login": {
      "azure": {
        "enabled": true,
        "auto_login": true,
        "timeout_seconds": 30
      }
    }
  }
}
```

## Uso

### Desde el Launcher Principal

```bash
# Ejecutar desde scm/
python main.py

# Seleccionar opción 2 (Azure)
# Se ejecutará automáticamente: az login (si es necesario)
```

### Ejecutar Herramienta Específica

```bash
# Ejemplo: Monitoreo de Recursos
python tools.py
# Seleccionar opción 1

# O directamente
python monitoring/azure_monitor.py --subscription <ID> --resource-group <RG>
```

## Ejemplos

### Monitorear Recursos Azure

```bash
python tools.py
# Seleccionar: 1 (Monitoreo de Recursos Azure)
# Ingresa: subscription-id y resource-group
```

### Auditar Roles y Permisos

```bash
python tools.py
# Seleccionar: 3 (Auditoría de Roles y Permisos)
# Genera reporte de RBAC
```

### Monitorear AKS

```bash
python tools.py
# Seleccionar: 13 (AKS Cluster Monitor)
# Monitorea estado del cluster
```

### Generar Reporte de Compliance

```bash
python tools.py
# Seleccionar: 23 (Azure Compliance Report)
# Genera reporte de cumplimiento normativo
```

## Permisos Requeridos

### Mínimos para todas las herramientas

```
Reader                          # Lectura de recursos
Monitoring Reader               # Lectura de métricas
Log Analytics Reader            # Lectura de logs
```

### Por herramienta

| Herramienta | Permisos Requeridos |
|-------------|-------------------|
| Monitoreo | Reader, Monitoring Reader |
| IAM Audit | Reader, User Access Administrator |
| Database | SQL Server Contributor, Cosmos DB Account Reader |
| Networking | Network Contributor, Reader |
| AKS | Azure Kubernetes Service Cluster Admin |
| App Service | Website Contributor, Reader |

## Troubleshooting

### Error: "az: command not found"

```bash
# Instalar Azure CLI
# Windows
choco install azure-cli

# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Error: "Not authenticated"

```bash
# Autenticar
az login

# Verificar cuenta activa
az account show

# Cambiar suscripción si es necesario
az account set --subscription <SUBSCRIPTION_ID>
```

### Error: "Insufficient permissions"

```bash
# Verificar permisos
az role assignment list --assignee <YOUR_EMAIL>

# Solicitar permisos necesarios al administrador
```

## Salida

Las herramientas generan reportes en:

```
outcome/
├── azure/
│   ├── monitoring/
│   ├── iam/
│   ├── database/
│   ├── networking/
│   ├── aks/
│   ├── app-service/
│   ├── inventory/
│   ├── reports/
│   └── events/
```

Formatos soportados: JSON, CSV, Excel, HTML, Markdown

## Historial de Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.8.33 | 2026-10-09 | **Paridad GCP/AWS**: 37 herramientas implementadas de cero (el registry tenía 38 entradas pero solo 2 archivos reales). Nuevo `azure_common.py` compartido (az CLI JSON, kubectl/AKS, suscripción, outcome/). Bloques: AKS/monitoring (10), DB/network (7), IAM/security (6), App Service (6), inventory/reporting/consolidation/ServiceBus/ACR (9). Tool 39 Key Vault nuevo. Launcher: ejecución real (antes solo mostraba el menú), prompts por arg, `required_args`, `additional_args`, run-all (A) con exclusión de tools interactivos, resumen de ejecución, venv + requirements. Registry corregido: args faltantes (`-o`, `--cluster`, `--resource-group`, `--registry`...) y 39 paths verificados. Tests: 143 nuevos en `scm/tests/unit/test_azure_*.py`; bugs corregidos detectados por tests (Unschedulable→Resource Constraint, operationName string vs dict, trigger camelCase). |
| 1.7.53 | 2026-09-01 | Homologación de GCP Cloud Run Monitoring: Tool 26 Azure Container Apps Metrics Monitor (requests, latencia p95, CPU%, memoria%, errores). 10 tests unitarios. README modernizado. |
| 1.0.0 | 2026-07-14 | Versión inicial con 25 herramientas |

## Licencia

Parte del DevSecOps Toolbox

## Soporte

Para reportar problemas o sugerencias, contacta al equipo DevSecOps.
