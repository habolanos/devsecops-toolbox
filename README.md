# 🔐 DevSecOps Toolbox

[![Version](https://img.shields.io/badge/version-1.6.21-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GNUv3-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)

> **Caja de herramientas DevSecOps unificada para operaciones multi-cloud.**
> 
> Soporta **Google Cloud Platform (GCP)**, **Azure DevOps (AZDO)** y **Amazon Web Services (AWS)** con un launcher centralizado, testing profesional y distribución Docker.

---

##  Tabla de Contenidos

- [🚀 Características Principales](#-características-principales)
- [📦 Instalación](#-instalación)
- [🎯 Uso Rápido](#-uso-rápido)
- [📊 Dashboard Matutino](#-dashboard-matutino)
- [🐳 Docker](#-docker)
- [☁️ Plataformas Soportadas](#️-plataformas-soportadas)
- [⚙️ Configuración](#️-configuración)
- [🧪 Testing](#-testing)
- [📁 Estructura del Proyecto](#-estructura-del-proyecto)
- [🏷️ Versionado Semántico](#️-versionado-semántico)
- [📝 Contribuir](#-contribuir)
- [📜 Licencia](#-licencia)
- [📚 Historial de Cambios](README.version.md)

---

## 🚀 Características Principales

| Característica | Descripción |
|---------------|-------------|
| 🎯 **Launcher Unificado** | Punto de entrada único para todas las plataformas cloud |
| � **KPI Analyzer** | Análisis de métricas DevSecOps con modelo de madurez de 6 niveles y dashboards interactivos |
| �� **Docker Ready** | Contenedor optimizado con todas las herramientas CLI (Azure, AWS, GCP, Kubernetes, Terraform) |
| 🧪 **Testing Profesional** | Suite completa de tests unitarios e integración con pytest (70%+ cobertura) |
| 🔐 **Configuración Segura** | Gestión centralizada de credenciales vía `config.json` (excluido de git) |
| � **Reportes** | Generación de reportes y análisis de arquitectura |
| 🌐 **Multi-Cloud** | Soporte nativo para GCP, Azure DevOps y AWS |
| 🏷️ **SemVer** | Versionado semántico automatizado |

---

## 📦 Instalación

### Opción 1: Clonar Repositorio

```bash
git clone https://github.com/habolanos/devsecops-toolbox.git
cd devsecops-toolbox
```

### Opción 2: Usar Docker (Recomendado)

```bash
# Descargar imagen
docker pull devsecops-toolbox:latest

# O construir localmente
docker build -t devsecops-toolbox:latest .
```

### Requisitos

- **Python**: 3.11+
- **Docker** (opcional): 20.10+
- **Docker Compose** (opcional): 2.0+

---

## 🎯 Uso Rápido

### ⭐ Opción Recomendada: Launcher Principal

```bash
# Desde la raíz del proyecto
python scm/main.py
```

**Esto te abrirá un menú interactivo con todas las opciones:**

```
╔═══════════════════════════════════════════════════════════════╗
║          🔐 DevSecOps Toolbox - Launcher Principal           ║
╚═══════════════════════════════════════════════════════════════╝

[1] 🔷 AZDO (Azure DevOps)
[2] ☁️  GCP (Google Cloud Platform)
[3] 🟠 AWS (Amazon Web Services)
[4] 🐧 Terminal (Scripts Universales)
[5] 📊 KPI Analyzer Pro
[6] 📈 Dashboard Matutino

[A] 🚀 Ejecutar Todas las Herramientas
[B] ⚡ Ejecutar Todo + JSON (Dashboard Feed)
[Q] 🚪 Salir

Selecciona una opción [1-6, A, B, Q]:
```

---

### 📋 Opciones Disponibles

#### **Opción 1: AZDO (Azure DevOps)** 🔷
Herramientas para gestión de repositorios, pipelines y releases en Azure DevOps:
- PR Master Checker
- Branch Policy Checker
- Release CD Health
- Pipeline Drift Analyzer
- Task Validator
- **[21] Pipeline Updater** - Actualización masiva de pipelines con templates YAML
- **[22] Pipeline Rollback** - Rollback con 3 métodos (Full Backup, Hybrid, Manual Revision)
  - **Opción 6: Redo** ⭐ NUEVO - Volver a versión previa del pipeline basado en definition_id
- **[40] Health Probe Masivo Validator** ⭐ NUEVO

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 1 (AZDO)
# Luego seleccionar herramienta específica (1-40)
```

#### **Opción 2: GCP (Google Cloud Platform)** ☁️
Herramientas especializadas para operaciones SRE en GCP:
- Service Account Checker
- Cloud SQL Manager
- GKE Cluster Manager
- Cloud Run Tools Suite
- Connectivity Checkers

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 2 (GCP)
```

#### **Opción 3: AWS (Amazon Web Services)** 🟠
Herramientas DevSecOps para AWS:
- IAM Analyzer
- RDS Manager
- VPC Manager
- EKS Manager
- ECR Scanner
- Lambda Manager

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 3 (AWS)
```

#### **Opción 4: Terminal (Scripts Universales)** 🐧
Scripts agnósticos de cloud provider para cualquier cluster Kubernetes:
- Certificate TLS Report
- Database Connections Checker
- Deployments Last News
- Deployments Last Update

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 4 (Terminal)
```

#### **Opción 5: KPI Analyzer Pro** 📊
Análisis de métricas DevSecOps con modelo de madurez y dashboards:
- Health Score DORA
- Exporter (JSON, CSV, HTML, Excel)
- Consolidator (multi-fuente)
- Generator (dashboards HTML)
- Scheduler (planificación automática)

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 5 (KPI Analyzer Pro)
```

#### **Opción 6: Dashboard Matutino** 📈
Dashboard automatizado que consolida el estado de repositorios, pipelines y servicios:
- Ejecución automática diaria
- Consolidación multi-cloud
- Visualización web interactiva
- Notificaciones inteligentes

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 6 (Dashboard Matutino)
```

#### **Opción A: Ejecutar Todas las Herramientas** 🚀
Ejecuta todas las herramientas con la misma configuración (sin Deep Dive):

```bash
python scm/main.py
# Seleccionar: A
```

#### **Opción B: Ejecutar Todo + JSON** ⚡
Ejecuta TODAS las herramientas forzando salida JSON en `outcome/` (ideal para Dashboard):

```bash
python scm/main.py
# Seleccionar: B
```

---

### 🚀 Acceso Directo a Plataformas (Avanzado)

Si prefieres acceder directamente a una plataforma sin pasar por el menú principal:

```bash
# Herramientas GCP
python scm/gcp/tools.py

# Herramientas Azure DevOps
python scm/azdo/tools.py

# Herramientas AWS
python scm/aws/tools.py

# Herramientas KPI Analyzer
python scm/kpi_analyzer/tools.py
```

---

### 🐳 Con Docker

```bash
# Ejecutar toolbox interactivo
docker-compose up -d toolbox
docker-compose exec toolbox bash

# Ejecutar comando específico
docker run --rm devsecops-toolbox:latest az version
docker run --rm devsecops-toolbox:latest aws --version
docker run --rm devsecops-toolbox:latest gcloud version
```

---

### 💡 Ejemplos Prácticos

#### Ejemplo 1: Validar Health Probes en Kubernetes
```bash
python scm/main.py
# Seleccionar: 1 (AZDO)
# Seleccionar: 40 (Health Probe Masivo Validator)
# Ingresar: deployment-web-prod,deployment-api-prod
```

#### Ejemplo 2: Ejecutar Análisis de KPI
```bash
python scm/main.py
# Seleccionar: 5 (KPI Analyzer Pro)
# Seleccionar herramienta específica
```

#### Ejemplo 3: Generar Dashboard Completo
```bash
python scm/main.py
# Seleccionar: B (Ejecutar Todo + JSON)
# Esperar a que se ejecuten todas las herramientas
# Los JSONs se guardarán en outcome/
```

---

## 📊 Dashboard Matutino

**⭐ NUEVO:** Dashboard automatizado que consolida el estado de repositorios, pipelines, servicios e infraestructura.

### Características

- ✅ **Ejecución Automática Diaria** - Se ejecuta cada mañana a las 7:00 AM
- ✅ **Consolidación Multi-Cloud** - Datos de AZDO, GCP y AWS en un único dashboard
- ✅ **Visualización Web Interactiva** - HTML con gráficos, tablas y alertas
- ✅ **Notificaciones Inteligentes** - Email, Slack, Teams (configurable)
- ✅ **Análisis de Tendencias** - Histórico de 90 días para análisis
- ✅ **80% Reutilización** - Aprovecha herramientas existentes

### Métricas Incluidas

| Métrica | Descripción |
|---------|-------------|
| **Repositorios** | Total, con CI/CD, sin pipeline |
| **Health Score** | Score DORA/SRE (0-100) |
| **Branch Compliance** | % de cumplimiento de políticas |
| **Pull Requests** | Tiempo promedio a merge, SLA compliance |
| **Servicios** | Estado GCP/AWS, alertas críticas |
| **Bases de Datos** | Uso de disco, instancias con alertas |

### Inicio Rápido

```bash
# 1. Leer documentación
cat DASHBOARD_README.md

# 2. Ejecutar orquestador (Tool 26)
python scm/azdo/dashboard_consolidator.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT"

# 3. Generar dashboard web (Tool 27)
python scm/dashboard/dashboard_generator.py \
  --input "outcome/dashboard/dashboard_data_*.json"

# 4. Ver resultado
open outcome/dashboard/dashboard.html
```

### Documentación Completa

- 📖 **[DASHBOARD_README.md](DASHBOARD_README.md)** - Índice de documentación
- 📋 **[DASHBOARD_EXECUTIVE_SUMMARY.md](DASHBOARD_EXECUTIVE_SUMMARY.md)** - Resumen ejecutivo
- 🏗️ **[DASHBOARD_ARCHITECTURE.md](DASHBOARD_ARCHITECTURE.md)** - Arquitectura técnica
- 📊 **[DASHBOARD_REUSABILITY_MATRIX.md](DASHBOARD_REUSABILITY_MATRIX.md)** - Matriz de reutilización
- 🎯 **[DASHBOARD_ACTION_PLAN.md](DASHBOARD_ACTION_PLAN.md)** - Plan de acción
- 💻 **[DASHBOARD_CODE_EXAMPLES.md](DASHBOARD_CODE_EXAMPLES.md)** - Ejemplos de código

---

## 🐳 Docker

El proyecto incluye una imagen Docker optimizada (~400MB) con todas las herramientas CLI necesarias.

### Herramientas Incluidas

| Herramienta | Descripción |
|-------------|-------------|
| **Azure CLI** | Gestión de Azure Portal y Azure DevOps |
| **AWS CLI v2** | Gestión de recursos AWS |
| **Google Cloud SDK** | Gestión de GCP (gcloud) |
| **kubectl** | Gestión de clusters Kubernetes |
| **Helm** | Package manager para Kubernetes |
| **Terraform** | Infraestructura como código |
| **Netshoot** | ping, dig, traceroute, tcpdump, nmap, netcat, etc. |

### Uso con Docker Compose

```bash
# 1. Configurar credenciales
cp .env.example .env
# Editar .env con tus credenciales

# 2. Iniciar servicios
docker-compose up -d toolbox

# 3. Acceder al contenedor
docker-compose exec toolbox bash
```

### Servicios Disponibles

| Servicio | Uso | Comando |
|----------|-----|---------|
| `toolbox` | Uso interactivo | `docker-compose up -d toolbox` |
| `toolbox-dev` | Desarrollo con live reload | `docker-compose --profile dev up -d toolbox-dev` |
| `toolbox-cmd` | CI/CD - ejecuta y sale | `docker-compose --profile cmd run --rm toolbox-cmd` |

**Ver documentación completa de Docker en:** [`scm/README.md`](scm/README.md#-docker-container)

---

## ☁️ Plataformas Soportadas

### Google Cloud Platform (GCP)

Herramientas especializadas para operaciones SRE en GCP:

- Artifact Registry Manager
- Certificate Manager
- Cloud Armor Configurator
- Cloud SQL Manager
- GKE Cluster Manager
- Gateway Services Manager
- Monitoring & Logging
- Reports Viewer
- Roles & Permisos
- Secrets & ConfigMaps
- VPC Networks Manager
- Connectivity Checkers (Pods, Dependencies, DNS)

### Azure DevOps (AZDO)

Herramientas para gestión de proyectos Azure DevOps:

- Project Analyzer
- Pipeline Manager
- Repository Manager
- Work Item Manager
- Build & Release Tools

### Amazon Web Services (AWS)

Herramientas DevSecOps para AWS:

- IAM Analyzer
- RDS Manager
- VPC Manager
- EKS Manager
- ECR Scanner
- EC2 Manager
- Lambda Manager
- CloudWatch Monitor
- Security Analyzer
- Cost Optimizer
- Compliance Checker
- Network Tester
- Secrets Manager

### Terminal / Scripts Universales 🔧

Scripts shell **agnósticos de cloud provider** que funcionan con cualquier cluster Kubernetes (GKE, EKS, AKS, OpenShift, on-premise):

- **Certificate TLS Report** - Valida certificados SSL/TLS remotos desde cualquier cluster K8s (CN, emisor, expiración, chain, TLS version, cipher reales)
- **Database Connections Checker** - Valida conectividad a múltiples instancias PostgreSQL usando netcat
- **Deployments Last News** - Muestra deployments más recientes ordenados por fecha de creación
- **Deployments Last Update** - Muestra deployments ordenados por último rollout (ReplicaSet)
- **Deployments Recent Events** - Muestra eventos recientes relacionados con Deployments

> **Nota:** Estos scripts requieren un entorno Linux/Unix (WSL, Git Bash, o Linux nativo).

---

## ⚙️ Configuración

### Configuración Inicial

```bash
# 1. Copiar el template
cp scm/config.json.template scm/config.json

# 2. Editar con tus credenciales
nano scm/config.json
```

### Estructura del config.json

```json
{
  "azdo": {
    "enabled": true,
    "organization_url": "https://dev.azure.com/TU_ORGANIZACION",
    "project": "TU_PROYECTO",
    "pat": "TU_PAT_TOKEN"
  },
  "gcp": {
    "enabled": true,
    "project_id": "TU_PROJECT_ID",
    "region": "us-central1",
    "credentials": {
      "type": "adc",
      "service_account_key_path": ""
    }
  },
  "aws": {
    "enabled": true,
    "profile": "default",
    "region": "us-east-1",
    "credentials": {
      "type": "profile"
    }
  },
  "global": {
    "debug": false,
    "output_dir": "outcome"
  }
}
```

> ⚠️ **IMPORTANTE**: El archivo `config.json` está en `.gitignore`. Nunca lo subas al repositorio.

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Tests unitarios
pytest scm/tests/unit/ -v

# Tests de integración
pytest scm/tests/integration/ -v

# Todos los tests con cobertura
pytest scm/tests/ -v --cov=scm --cov-report=html

# Ver reporte de cobertura
open htmlcov/index.html
```

### Testing en Docker

```bash
# Ejecutar tests en contenedor
docker-compose --profile dev up -d toolbox-dev
docker-compose exec toolbox-dev pytest scm/tests/ -v
```

**Ver guía completa de testing en:** [`scm/README.md`](scm/README.md#-testing)

---

## 📁 Estructura del Proyecto

```
devsecops-toolbox/
├── scm/                          # Código fuente principal
│   ├── main.py                   # Launcher principal
│   ├── gcp/                      # Herramientas GCP
│   ├── azdo/                     # Herramientas AZDO
│   ├── aws/                      # Herramientas AWS
│   ├── terminal/                 # Scripts universales (agnostic cloud)
│   ├── tests/                    # Tests (unitarios e integración)
│   ├── config.json.template      # Template de configuración
│   └── README.md                 # Documentación detallada
├── Dockerfile                    # Imagen Docker
├── docker-compose.yml            # Orquestación Docker
├── docker-entrypoint.sh          # Script de inicio Docker
├── .env.example                  # Template de variables de entorno
├── .dockerignore                 # Exclusiones de Docker build
├── pytest.ini                   # Configuración de pytest
├── pyproject.toml               # Metadatos del proyecto
├── VERSION                      # Versión actual (SemVer)
├── scripts/                     # Scripts de utilidad
│   ├── bump_version.py          # Gestión de versiones SemVer
│   └── sync-gcp.ps1             # Sincronización GCP entre repos (PowerShell)
├── sync_repos.py                 # Sincronización completa toolbox ↔ azdo (Python)
└── README.md                     # Este archivo
```

---

## 🏷️ Versionado Semántico (SemVer)

El proyecto sigue [Semantic Versioning 2.0.0](https://semver.org/lang/es/):

```
VERSION = MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

MAJOR  - Cambios incompatibles
MINOR  - Nuevas funcionalidades
PATCH  - Correcciones de bugs
```

### Gestión de Versiones

```bash
# Incrementar versión patch
python scripts/bump_version.py --patch

# Incrementar versión minor
python scripts/bump_version.py --minor

# Establecer versión explícita
python scripts/bump_version.py 2.0.0

# Validar consistencia
python scripts/bump_version.py --validate
```

---

## 📝 Contribuir

1. Fork el repositorio
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'feat: agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

### Guías de Contribución

- Seguir [Conventional Commits](https://www.conventionalcommits.org/)
- Mantener cobertura de tests > 70%
- Documentar nuevas funcionalidades en README
- Actualizar versiones usando `scripts/bump_version.py`

---

## 📜 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

---

## 📚 Historial de Cambios

**Ver historial completo y detallado en:** [`README.version.md`](README.version.md)

---

## 👤 Autor

**Harold Adrian**

- GitHub: [@habolanos](https://github.com/habolanos)
- Repositorio: [devsecops-toolbox](https://github.com/habolanos/devsecops-toolbox)

---

<p align="center">
  <b>🔐 DevSecOps Toolbox - Multi-Cloud DevOps Made Simple</b>
</p>

## 📊 Estadísticas del repositorio

![GitHub stars](https://img.shields.io/github/stars/habolanos/devsecops-toolbox?style=social)
![GitHub forks](https://img.shields.io/github/forks/habolanos/devsecops-toolbox?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/habolanos/devsecops-toolbox?style=social)