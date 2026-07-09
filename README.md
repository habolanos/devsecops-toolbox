# 🔐 DevSecOps Toolbox

[![Version](https://img.shields.io/badge/version-1.9.5-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GNUv3-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)

> **Caja de herramientas DevSecOps unificada para operaciones multi-cloud.**
> 
> Soporta **Google Cloud Platform (GCP)**, **Azure DevOps (AZDO)** y **Amazon Web Services (AWS)** con un launcher centralizado, testing profesional y distribución Docker.

---

## 📝 Historial de Cambios (v1.9.5)

| Versión | Fecha | Cambios |
|---------|-------|---------|
| **1.9.5** | 2026-07-09 | 🚀 **Implementación Completa de Herramientas AWS**: 18 nuevas herramientas AWS (Tools 23-40) para lograr paridad con GCP. Incluye RDS Comparator, API Gateway Checker, VPC IP Checker, EKS Pod Connectivity, Lambda Analyzer, ECR Image Filter, Infrastructure Consolidator, Unified Dashboard, Inventory Consolidator, Service Linked Roles, etc. + 9 guías de actualización de pipelines CD (3,344 líneas) + Tests unitarios + Documentación de API completa. |
| 1.6.16 | 2026-07-08 | ✨ Tool 4 & Tool 38 Enhancements: Soporte para múltiples proyectos GCP con visualización Rich (spinners, tablas, progreso). Tool 4 carga proyectos desde config.json por defecto. Tool 38 mejorada con procesamiento paralelo (5 workers) y tablas de resultados por proyecto. |
| 1.6.15 | 2026-07-05 | 🔧 Mejoras en herramientas GCP |
| **1.6.13** | 2026-07-03 | 🚀 Cloud Run Tools Suite (7 herramientas): Health Analyzer, Security Auditor, Cost Analyzer, Deployment Validator, Traffic Analyzer, Dependency Mapper, Executive Dashboard. IDs 28-34. Validación de _system_options completada. Grupo "cloudrun" agregado a TOOL_GROUPS. Tests unitarios creados. |
| 1.6.12 | 2026-06-29 | ✨ Dinamización de menús: Eliminar hardcode en opciones A, B, Q. Generación dinámica con _system_options, get_auto_tools(), build_system_options(). Reducción 50% de código (113→56 líneas). Implementado en todas las plataformas |
| 1.6.11 | 2026-06-29 | 📋 Análisis exhaustivo de refactorización: hardcode en menús (113 líneas), búsqueda interactiva (17% cobertura), propuestas de solución con documentación completa |
| 1.6.10 | 2026-06-25 | 🆙 Nuevo grupo "updatepipe" para herramientas de actualización/rollback de Release Pipelines |
| 1.6.9 | 2026-06-22 | 🔧 Dashboard ejecuta scripts AZDO directamente, lee config.json, pasa DEVSECOPS_OUTPUT_DIR |
| 1.6.8 | 2026-06-22 | ✨ Dashboard Matutino con ejecución paralela, Rich UI y barras de progreso |
| 1.6.7 | 2026-06-20 | Dashboard Matutino inicial |
| 1.6.6 | 2026-06-15 | KPI Analyzer mejorado |

### v1.6.16 - Tool 4 & Tool 38 Enhancements - Múltiples Proyectos GCP

**Cambios Principales:**
- ✅ **Tool 4 (Service Account Checker)**: Soporte para múltiples proyectos GCP
  - Carga proyectos desde `config.json` por defecto
  - Permite override con `--projects=proj1,proj2,proj3`
  - Procesamiento paralelo con 5 workers
  - Tabla de resultados por proyecto
  - Spinner animado y barra de progreso

- ✅ **Tool 38 (Service Accounts Multi-Project Reporter)**: Visualización profesional
  - Spinners y progreso con Rich library
  - Tabla de extracción por proyecto con columna de proyecto
  - Tabla de resumen final con duración
  - Procesamiento paralelo (5 workers)
  - Fallback a print() si Rich no disponible

- ✅ **Integración tools.py**: Tool 4 no pregunta por proyecto
  - Cambio: `"args": ["--project", "-o"]` → `"args": ["-o"]`
  - Permite carga automática desde config.json

**Características Nuevas:**
- 🎯 Múltiples proyectos procesados en paralelo
- 📊 Tablas Rich con columna de proyecto
- ⏱️ Duración total de ejecución
- 🔄 Fallback automático sin Rich
- 📋 Carga desde config.json por defecto

**Commits Realizados:**
- `fd4d71e`: feat: Agregar visualización profesional con Rich a Tool 38
- `c64033f`: feat: Agregar soporte para múltiples proyectos a Tool 4
- `f3e68a5`: feat: Tool 4 carga proyectos desde config.json por defecto
- `e19a373`: fix: Tool 4 no pregunta por proyecto, carga desde config.json

---

### v1.6.12 - Dinamización de Menús - Eliminar Hardcode

**Cambios Principales:**
- ✅ Estructura `_system_options`: Diccionario de configuración para opciones de sistema
- ✅ Función `get_auto_tools()`: Genera lista de herramientas dinámicamente
- ✅ Función `build_system_options()`: Construye opciones finales desde configuración
- ✅ Inicialización automática: `_init_system_options()` al cargar módulo
- ✅ Implementado en todas las plataformas: AZDO, GCP, AWS, Terminal, KPI

**Reducción de Código:**
- Líneas de hardcode: 113 → 56 (50% ↓)
- Mapeos duplicados: 6 → 1 (83% ↓)
- Puntos de cambio: Centralizados
- Mantenibilidad: Mejorada significativamente

**Plataformas Actualizadas:**
- 🔷 AZDO: Opciones A, B, Q dinámicas
- ☁️ GCP: Opciones A, Q dinámicas
- 🟠 AWS: Opciones A, Q dinámicas
- 🐧 Terminal: Opción Q dinámica
- 📊 KPI: Opción Q dinámica

**Beneficios:**
- 🎯 Código más mantenible
- 📊 Escalabilidad mejorada
- 🔄 Consistencia entre plataformas
- ✅ Totalmente retrocompatible

---

### v1.6.11 - Análisis Exhaustivo de Refactorización de Menús y Búsqueda Interactiva

**Cambios Principales:**
- ✅ Análisis exhaustivo de hardcode en menús: 113 líneas identificadas en 6 archivos
- ✅ Propuesta de solución: generación dinámica con `_system_options` y funciones reutilizables
- ✅ Reducción estimada: 50% de código (113 → 56 líneas)
- ✅ Análisis de búsqueda interactiva: módulo `interactive_search.py` en AZDO (328 líneas)
- ✅ Problema: solo en AZDO (17% cobertura)
- ✅ Propuesta: módulo centralizado `scm/search_module.py` para 100% cobertura
- ✅ Documentación completa en `docs/refactor_arquitectura/`

**Documentos Generados:**
- 📄 `ANALISIS_DINAMIZACION_MENUS.md` (630 líneas)
- 📄 `ANALISIS_COMPLETO_HARDCODE_MENUS.md` (571 líneas)
- 📄 `ANALISIS_BUSQUEDA_INTERACTIVA.md` (479 líneas)

**Beneficios:**
- 🎯 Identifica problemas de mantenibilidad
- 📊 Propone soluciones concretas y medibles
- 📋 Proporciona checklists de implementación
- 🔄 Facilita refactorización futura

---

### v1.6.13 - Cloud Run Tools Suite & Validación de _system_options

**Cambios Principales:**
- ✅ Implementación de 7 nuevas herramientas Cloud Run (IDs 28-34):
  - Tool 28: Cloud Run Health Analyzer - Análisis profundo de salud y rendimiento
  - Tool 29: Cloud Run Security Auditor - Auditoría completa de seguridad
  - Tool 30: Cloud Run Cost Analyzer - Análisis de costos y optimización
  - Tool 31: Cloud Run Deployment Validator - Validación de configuración pre-deploy
  - Tool 32: Cloud Run Traffic Analyzer - Análisis de tráfico y distribución
  - Tool 33: Cloud Run Dependency Mapper - Mapeo de dependencias y conectividad
  - Tool 34: Cloud Run Executive Dashboard - Dashboard ejecutivo consolidado
- ✅ Creación de módulos base:
  - `cloudrun_base.py`: Utilidades compartidas (gcloud execution, export, console printing)
  - `cloudrun_metrics.py`: Cálculos de métricas (health score, cost, SLA)
  - `cloudrun_alerts.py`: Gestión de alertas (severidad, tipos, seguridad, costos)
- ✅ Validación completa de `_system_options`:
  - Confirmado: Implementación dinámica correcta en todos los launchers
  - Documento de validación creado: `docs/VALIDACION_SYSTEM_OPTIONS.md`
  - Flujo de procesamiento documentado y verificado
- ✅ Corrección de duplicados de IDs:
  - Renumeración de Cloud Run tools: 19-27 → 28-34
  - Documento de corrección: `docs/CORRECCION_DUPLICADOS_TOOLS.md`
- ✅ Agregación del grupo "cloudrun" a TOOL_GROUPS:
  - Emoji: 🚀 Cloud Run
  - Color: bright_cyan
  - Las herramientas ahora aparecen correctamente en el menú
- ✅ Tests unitarios creados:
  - `tests/test_cloudrun_base.py`: 100+ tests para módulos base
  - Cobertura de validación de conexión, métricas y alertas

**Archivos Modificados:**
- `scm/gcp/tools.py`: Agregadas 7 herramientas, grupo "cloudrun" a TOOL_GROUPS
- `scm/gcp/cloud-run/cloudrun_base.py`: Módulo base creado
- `scm/gcp/cloud-run/cloudrun_metrics.py`: Módulo de métricas creado
- `scm/gcp/cloud-run/cloudrun_alerts.py`: Módulo de alertas creado
- `scm/gcp/cloud-run/gcp_cloudrun_health_analyzer.py`: Tool 28
- `scm/gcp/cloud-run/gcp_cloudrun_security_auditor.py`: Tool 29
- `scm/gcp/cloud-run/gcp_cloudrun_cost_analyzer.py`: Tool 30
- `scm/gcp/cloud-run/gcp_cloudrun_deployment_validator.py`: Tool 31
- `scm/gcp/cloud-run/gcp_cloudrun_traffic_analyzer.py`: Tool 32
- `scm/gcp/cloud-run/gcp_cloudrun_dependency_mapper.py`: Tool 33
- `scm/gcp/cloud-run/gcp_cloudrun_executive_dashboard.py`: Tool 34
- `tests/test_cloudrun_base.py`: Tests unitarios creados

**Documentación Generada:**
- � `docs/feature_cloudrun/IMPLEMENTACION_COMPLETADA.md` - Resumen de implementación
- 📄 `docs/VALIDACION_SYSTEM_OPTIONS.md` - Validación de _system_options
- 📄 `docs/CORRECCION_DUPLICADOS_TOOLS.md` - Documentación de corrección de duplicados
- 📄 `docs/SOLUCION_HERRAMIENTAS_NO_VISIBLES.md` - Solución de visibilidad en menú

**Beneficios:**
- 🎯 Suite completa de herramientas para Cloud Run
- 📊 Análisis profundo de salud, seguridad, costos y tráfico
- 🔄 Validación confirmada de sistema dinámico de opciones
- ✅ Menú actualizado con nuevas herramientas visibles
- 📈 Documentación exhaustiva de cambios y validaciones

**Compatibilidad:**
- ✅ Totalmente retrocompatible
- ✅ No afecta herramientas existentes
- ✅ Integración transparente con arquitectura existente

---

### v1.6.12 - Dashboard Independiente y Configurable

**Nuevas Características:**
- ✅ Dashboard ejecuta scripts AZDO directamente (no lanza a opción 2)
- ✅ Lee directorio de salida desde `config.json` (dashboard.output.directory)
- ✅ Pasa `DEVSECOPS_OUTPUT_DIR` como variable de entorno a scripts AZDO
- ✅ Ejecuta solo herramientas necesarias para Dashboard:
  - `azdo_pr_master_checker.py` (PR Metrics)
  - `azdo_branch_policy_checker.py` (Branch Compliance)
  - `azdo_release_cd_health.py` (Health Score)
  - `azdo_pipeline_drift.py` (Pipeline Status)
  - `cicd_inventory_health_score.py` (Health Score DORA)
  - `cicd_pipeline_status.py` (Pipeline Status)
- ✅ Timeout de 600 segundos por herramienta
- ✅ Progreso visible de cada herramienta ejecutada
- ✅ Manejo robusto de errores

**Mejoras:**
- 🚀 Más rápido: solo 6 herramientas vs 15+ (opción B)
- 🎯 Específico para Dashboard
- 📁 Respeta configuración en `config.json`
- � Independiente de `azdo/tools.py`

**Compatibilidad:**
- ✅ Compatible con Rich library (interfaz moderna)
- ✅ Fallback sin Rich (interfaz simple)
- ✅ Windows, macOS y Linux

---

## 📑 Tabla de Contenidos

- [🚀 Características Principales](#-características-principales)
- [📦 Instalación](#-instalación)
- [🎯 Uso Rápido](#-uso-rápido)
- [� Dashboard Matutino](#-dashboard-matutino) ⭐ NUEVO
- [� Docker](#-docker)
- [☁️ Plataformas Soportadas](#️-plataformas-soportadas)
- [⚙️ Configuración](#️-configuración)
- [🧪 Testing](#-testing)
- [📁 Estructura del Proyecto](#-estructura-del-proyecto)
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

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-06-22 | **1.7.0** | ⭐ Nuevo: Dashboard Matutino (Tools 26-29) con consolidación multi-cloud, visualización web y automatización diaria |
| 2026-06-04 | **1.6.10** | Ver historial completo en [README.version.md](README.version.md) |

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