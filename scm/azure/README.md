# Azure Tools Launcher

Conjunto completo de 25 herramientas SRE/DevOps para Google Cloud Platform (GCP).

## Características

- ✅ **25 herramientas** listas para usar
- ✅ **Monitoreo integral** de recursos Azure
- ✅ **Seguridad y compliance** (IAM, RBAC, auditoría)
- ✅ **Kubernetes (AKS)** - Monitoreo, validación, análisis
- ✅ **Bases de datos** - Azure SQL, Cosmos DB, backups
- ✅ **Networking** - VNets, NSGs, Application Gateway
- ✅ **App Service** - Monitoreo, seguridad, validación
- ✅ **Inventario y reportes** - Recursos, compliance
- ✅ **Event Tracker** - Rastreo de eventos y caídas
- ✅ **Dashboard unificado** - Consolidación multi-fuente

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

### App Service (19-21)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 19 | App Service Monitor | Monitorea App Services |
| 20 | App Service Security Auditor | Audita seguridad |
| 21 | App Service Deployment Validator | Valida despliegues |

### Inventory & Reports (22-25)

| ID | Nombre | Descripción |
|----|--------|-------------|
| 22 | Azure Resource Inventory | Inventario completo de recursos |
| 23 | Azure Compliance Report | Reporte de cumplimiento normativo |
| 24 | Event Tracker | Rastreo de eventos y caídas |
| 25 | Azure Unified Dashboard | Dashboard ejecutivo unificado |

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
| 1.0.0 | 2026-07-14 | Versión inicial con 25 herramientas |

## Licencia

Parte del DevSecOps Toolbox

## Soporte

Para reportar problemas o sugerencias, contacta al equipo DevSecOps.
