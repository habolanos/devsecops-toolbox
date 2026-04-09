# 🔐 DevSecOps Toolbox

[![Version](https://img.shields.io/badge/version-1.5.2-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GNUv3-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)

> **Caja de herramientas DevSecOps unificada para operaciones multi-cloud.**
> 
> Soporta **Google Cloud Platform (GCP)**, **Azure DevOps (AZDO)** y **Amazon Web Services (AWS)** con un launcher centralizado, testing profesional y distribución Docker.

---

## 📑 Tabla de Contenidos

- [🚀 Características Principales](#-características-principales)
- [📦 Instalación](#-instalación)
- [🎯 Uso Rápido](#-uso-rápido)
- [🐳 Docker](#-docker)
- [☁️ Plataformas Soportadas](#️-plataformas-soportadas)
- [⚙️ Configuración](#️-configuración)
- [🧪 Testing](#-testing)
- [📁 Estructura del Proyecto](#-estructura-del-proyecto)
- [📝 Contribuir](#-contribuir)
- [📜 Licencia](#-licencia)
- [📚 Historial de Cambios](#-historial-de-cambios)

---

## 🚀 Características Principales

| Característica | Descripción |
|---------------|-------------|
| 🎯 **Launcher Unificado** | Punto de entrada único para todas las plataformas cloud |
| 🐳 **Docker Ready** | Contenedor optimizado con todas las herramientas CLI (Azure, AWS, GCP, Kubernetes, Terraform) |
| 🧪 **Testing Profesional** | Suite completa de tests unitarios e integración con pytest (70%+ cobertura) |
| 🔐 **Configuración Segura** | Gestión centralizada de credenciales vía `config.json` (excluido de git) |
| 📊 **Reportes** | Generación de reportes y análisis de arquitectura |
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

### Launcher Principal

```bash
cd scm/
python main.py
```

### Acceso Directo a Plataformas

```bash
cd scm/
python gcp/tools.py      # Herramientas GCP
python azdo/tools.py     # Herramientas Azure DevOps
python aws/tools.py      # Herramientas AWS
```

### Con Docker

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
│   └── sync-gcp.ps1             # Sincronización entre repos
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

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-04-08 | 1.5.2 | **Docker Container**: Dockerfile slim con Azure/AWS/GCP CLI, kubectl, Helm, Terraform, netshoot. Docker Compose con 3 servicios. Entrypoint script con auto-configuración. |
| 2026-04-02 | 1.5.1 | **Testing Suite**: Arquitectura profesional de testing con pytest, cobertura 70%+, mocks para GCP/AZDO/AWS, CI/CD con GitHub Actions. Tests unitarios e integración con 500+ assertions. |
| 2026-04-02 | 1.5.0 | **Config Unificado**: Template `config.json.template` para gestión centralizada de tokens/credenciales de AZDO, GCP y AWS. Variables de entorno automáticas al lanzar plataformas. |
| 2026-03-31 | 1.4.1 | **AWS Toolbox**: 13 herramientas DevSecOps para AWS (IAM, RDS, VPC, EKS, ECR, EC2, Lambda, CloudWatch) |
| 2026-03-31 | 1.1.1 | **Análisis Pro**: Reporte completo de arquitectura con 15+ mejoras priorizadas |
| 2026-03-26 | 1.0.0 | Versión inicial - Launcher unificado para GCP y Azure DevOps |

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