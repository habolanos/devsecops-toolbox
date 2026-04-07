# DevSecOps Toolbox - SCM

Punto de entrada unificado para herramientas de múltiples plataformas cloud y DevOps.

## 📋 Contenido

| Directorio/Archivo | Descripción |
|--------------------|-------------|
| `main.py` | Launcher principal - punto de entrada unificado |
| `gcp/` | Herramientas SRE para Google Cloud Platform |
| `azdo/` | Herramientas para Azure DevOps |
| `aws/` | Herramientas DevSecOps para Amazon Web Services |
| [Testing](#-testing) | Guía paso a paso para ejecutar tests |
| [Compilar](#-compilar-distribuible) | Guía para crear el ZIP distribuible |

---

## 🚀 Uso Rápido

```bash
# Ejecutar el launcher principal
python main.py

# O acceder directamente a una plataforma
python gcp/tools.py
python azdo/tools.py
python aws/tools.py
```

---

## ⚙️ Configuración

El toolbox utiliza un archivo `config.json` para gestionar tokens y credenciales de todas las plataformas.

### Configuración Inicial

```bash
# 1. Copiar el template
cp config.json.template config.json

# 2. Editar con tus credenciales
nano config.json  # o tu editor preferido
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

### Variables de Entorno Exportadas

Al lanzar cada plataforma, el launcher configura automáticamente:

| Plataforma | Variables |
|------------|-----------|
| **AZDO** | `AZDO_ORG_URL`, `AZDO_PROJECT`, `AZDO_PAT`, `AZDO_TIMEZONE` |
| **GCP** | `GCP_PROJECT_ID`, `GCP_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`, `GKE_CLUSTER_NAME` |
| **AWS** | `AWS_PROFILE`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |

### Comandos de Configuración

En el menú principal:
- Escriba `config` para ver el estado detallado de configuración
- El estado se muestra automáticamente: ✅ configurado, ⚠️ incompleto, ❌ sin configurar

> ⚠️ **IMPORTANTE**: Nunca subas `config.json` al repositorio. Ya está en `.gitignore`.

---

## 🎯 Plataformas Disponibles

### ☁️ Google Cloud Platform (GCP)

| # | Herramienta | Descripción |
|---|-------------|-------------|
| 19+ | SRE Tools | Monitoreo, IAM, Networking, Kubernetes, Database, Reports |

**Grupos de herramientas:**
- 📊 Monitoreo
- 🔐 IAM & Security
- 💾 Database
- 🌐 Networking
- ☸️ Kubernetes
- 📦 Artifacts
- 📈 Reports

### 🔷 Azure DevOps (AZDO)

| # | Herramienta | Descripción |
|---|-------------|-------------|
| 4+ | DevOps Tools | PRs, políticas de rama, releases, drift analysis |

**Grupos de herramientas:**
- 📬 Pull Requests
- 🔒 Políticas de Rama
- 🚀 Release Pipelines
- 🔍 Drift Analysis

### 🟠 Amazon Web Services (AWS)

| # | Herramienta | Descripción |
|---|-------------|-------------|
| 13 | DevSecOps Tools | IAM, RDS, VPC, EKS, ECR, EC2, Lambda, CloudWatch |

**Grupos de herramientas:**
- 🔐 IAM & Security (Users, Roles, ACM)
- 💾 Database (RDS Instance, Storage)
- 🌐 Networking (VPC, Security Groups, Load Balancers)
- ☸️ Kubernetes (EKS Clusters)
- 📦 Artifacts (ECR Repositories)
- 💻 Compute (EC2, Lambda)
- 📊 Monitoring (CloudWatch Alarms)

---

## 📦 Requisitos

- Python 3.8 o superior
- Rich (opcional, para interfaz moderna)

```bash
pip install rich
```

---

## 🖥️ Interfaz

El launcher principal muestra un menú interactivo:

```
╔══════════════════════════════════════════════════════════════╗
║                   🛡️  DevSecOps Toolbox  🛡️                   ║
║                  v1.0.0 | by Harold Adrian                   ║
║             DevSecOps Toolbox - Launcher Principal           ║
╚══════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────┐
│                  🚀 Seleccione una Plataforma                │
├────┬────────┬─────────────────────────┬──────────────────────┤
│ #  │ Estado │ Plataforma              │ Descripción          │
├────┼────────┼─────────────────────────┼──────────────────────┤
│ 1  │ 🟢     │ ☁️ Google Cloud Platform │ Herramientas SRE...  │
│ 2  │ 🟢     │ 🔷 Azure DevOps          │ PRs, políticas...    │
│ 3  │ �     │ 🟠 Amazon Web Services   │ IAM, RDS, VPC...     │
│ Q  │ 🚪     │ 🚪 Salir                 │ Salir del launcher   │
└────┴────────┴─────────────────────────┴──────────────────────┘
```

---

## 📁 Estructura

```
scm/
├── main.py              # Launcher principal
├── README.md            # Este archivo
├── gcp/                 # Google Cloud Platform
│   ├── tools.py         # Launcher GCP (v1.7.0)
│   ├── cloud-run/       # Cloud Run Checker
│   ├── load-balancer/   # Load Balancer Checker
│   ├── monitoring/      # Monitoreo GCP/GKE
│   ├── vpc-networks/    # VPC Networks Checker
│   └── ...              # +15 directorios de herramientas
├── azdo/                # Azure DevOps
│   ├── tools.py         # Launcher AZDO (v1.0.0)
│   ├── azdo_pr_master_checker.py
│   ├── azdo_branch_policy_checker.py
│   └── ...
└── aws/                 # Amazon Web Services
    ├── tools.py         # Launcher AWS (v1.0.0)
    ├── iam/             # IAM Users & Roles Checker
    ├── acm/             # ACM Certificate Checker
    ├── rds/             # RDS Instance & Storage Checker
    ├── vpc/             # VPC & Security Groups Checker
    ├── elb/             # Load Balancer Checker
    ├── eks/             # EKS Cluster Checker
    ├── ecr/             # ECR Repository Checker
    ├── ec2/             # EC2 Instances Checker
    ├── lambda/          # Lambda Functions Checker
    └── cloudwatch/      # CloudWatch Alarms Checker
```

---

## 💡 Tips

- Escriba `info` en el menú principal para ver información adicional
- Use `Ctrl+C` para volver al menú anterior o salir
- Los launchers de cada plataforma manejan sus propias dependencias

---

## 🧪 Testing

El proyecto incluye una suite de tests completa con pytest.

### Estructura de Tests

```
tests/
├── conftest.py              # Fixtures globales
├── unit/                    # Tests unitarios
│   ├── test_main.py         # Tests del launcher principal
│   ├── gcp/
│   ├── azdo/
│   └── aws/
├── integration/             # Tests de integración
│   └── test_cloud_apis.py   # Tests de APIs cloud con mocks
├── mocks/                   # Mocks reutilizables
│   ├── gcp_mock.py          # Mock para GCP
│   ├── azdo_mock.py         # Mock para Azure DevOps
│   └── aws_mock.py          # Mock para AWS
└── fixtures/                # Datos de prueba
    ├── config_samples/
    ├── gcp_responses/
    ├── azdo_responses/
    └── aws_responses/
```

### 📝 Paso a Paso: Ejecutar Tests

#### 1. Instalar dependencias de testing

```bash
# Desde el directorio raíz del proyecto
pip install pytest pytest-cov pytest-mock
```

#### 2. Ejecutar todos los tests

```bash
# Ejecutar todos los tests (unitarios + integración)
python -m pytest tests

# O simplemente
pytest
```

#### 3. Ejecutar tests por categoría

```bash
# Solo tests unitarios
pytest tests/unit -v

# Solo tests de integración (requiere ALLOW_INTEGRATION_TESTS=true en Linux/Mac)
$env:ALLOW_INTEGRATION_TESTS="true"; pytest tests/integration -v

# Tests específicos por plataforma cloud
pytest -m gcp      # Tests de GCP
pytest -m azdo     # Tests de Azure DevOps
pytest -m aws      # Tests de AWS
pytest -m unit     # Solo tests unitarios
pytest -m "not slow"  # Excluir tests lentos
```

#### 4. Ejecutar tests con cobertura

```bash
# Reporte de cobertura en consola
pytest --cov=scm

# Reporte HTML detallado
pytest --cov=scm --cov-report=html:outcome/coverage_html

# Abrir reporte HTML (Windows)
start outcome/coverage_html/index.html
```

#### 5. Ver resultados detallados

```bash
# Mostrar traceback corto
pytest -v --tb=short

# Mostrar solo errores
pytest --tb=line -q

# Verbose máximo
pytest -vvv
```

### Markers Disponibles

| Marker | Descripción |
|--------|-------------|
| `@pytest.mark.unit` | Tests unitarios (rápidos, sin dependencias externas) |
| `@pytest.mark.integration` | Tests de integración (usan mocks de APIs) |
| `@pytest.mark.e2e` | Tests end-to-end (flujos completos) |
| `@pytest.mark.slow` | Tests que toman más tiempo |
| `@pytest.mark.gcp` | Tests específicos de GCP |
| `@pytest.mark.azdo` | Tests específicos de Azure DevOps |
| `@pytest.mark.aws` | Tests específicos de AWS |

### Fixtures Principales

| Fixture | Descripción |
|---------|-------------|
| `sample_config_data` | Configuración de ejemplo válida |
| `temp_config_file` | Archivo de configuración temporal |
| `mock_azdo_env` | Variables de entorno mock para AZDO |
| `mock_gcp_env` | Variables de entorno mock para GCP |
| `mock_aws_env` | Variables de entorno mock para AWS |
| `clean_env` | Limpieza de variables de entorno |

### Mocks de APIs Cloud

Los mocks están en `tests/mocks/` y proporcionan:

- **GCPMock**: Simula Projects, GKE, Compute, Cloud Run, Service Accounts
- **AZDOMock**: Simula Projects, Repos, PRs, Pipelines, Releases, Policies
- **AWSMock**: Simula STS, IAM, EC2, RDS, Lambda, EKS, S3, ACM

Ejemplo de uso:

```python
from mocks.gcp_mock import GCPMock

def test_gcp_project():
    gcp_mock = GCPMock()
    project = gcp_mock.mock_project_response("my-project")
    assert project["lifecycleState"] == "ACTIVE"
```

---

## 📦 Compilar Distribuible

El proyecto incluye un script PowerShell (`make_dist.ps1`) para generar un ZIP distribuible.

### 📝 Paso a Paso: Crear Distribuible

#### 1. Verificar ubicación

```powershell
# Navegar al directorio raíz del proyecto
cd c:\Users\harold.bolanos\repos-publics\devsecops-toolbox
```

#### 2. Ejecutar script de empaquetado

```powershell
# Empaquetado básico (salida en outcome/)
.\make_dist.ps1

# Empaquetado con nombre personalizado
.\make_dist.ps1 -ZipPrefix "devsecops-toolbox_v1.5.1"

# Empaquetado mostrando archivos excluidos
.\make_dist.ps1 -ShowExcluded

# Empaquetado en directorio alternativo
.\make_dist.ps1 -OutputDir "C:\\entregas"
```

#### 3. Verificar resultado

```powershell
# Listar archivos generados en outcome/
ls outcome\*.zip

# Ver contenido del ZIP (sin extraer)
Expand-Archive -Path "outcome\devsecops-toolbox_dist_*.zip" -DestinationPath "temp_extract" -WhatIf
```

#### 4. Publicar en GitHub (opcional)

```powershell
# Crear release y subir ZIP (requiere token)
.\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.5.1" -ReleaseTitle "Release 1.5.1" -ReleaseNotes "Nueva versión con testing suite"

# Crear como borrador
.\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.5.1" -Draft

# Crear como pre-release
.\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.5.1-beta" -Prerelease
```

### Archivos Excluidos del Distribuible

El ZIP de distribución **NO incluye**:
- `.git/`, `.github/` - Control de versiones
- `tests/`, `__tests__/` - Tests (código de desarrollo)
- `.venv/`, `venv/` - Entornos virtuales
- `outcome/` - Archivos de salida
- `config.json` - Credenciales (solo se distribuye `config.json.template`)
- `make_dist.ps1` - Script de empaquetado
- Archivos temporales: `*.pyc`, `*.log`, `__pycache__/`

### Estructura del ZIP Generado

```
devsecops-toolbox_dist_YYYYMMDD_HHMMSS.zip
├── scm/
│   ├── main.py              # Launcher principal
│   ├── config.json.template # Template de configuración
│   ├── gcp/                 # Herramientas GCP
│   ├── azdo/                # Herramientas AZDO
│   └── aws/                 # Herramientas AWS
├── pyproject.toml           # Metadatos del proyecto
└── pytest.ini              # Configuración de tests
```

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-04-02 | 1.5.1 | **Testing Suite**: Arquitectura profesional de testing con pytest, cobertura 70%+, mocks para GCP/AZDO/AWS, CI/CD con GitHub Actions. Tests unitarios e integración con 500+ assertions. |
| 2026-04-02 | 1.5.0 | **Config Unificado**: Template `config.json.template` para gestión centralizada de tokens/credenciales de AZDO, GCP y AWS. Variables de entorno automáticas al lanzar plataformas. |
| 2026-03-31 | 1.4.1 | **AWS Toolbox**: 13 herramientas DevSecOps para AWS (IAM, RDS, VPC, EKS, ECR, EC2, Lambda, CloudWatch) |
| 2026-03-31 | 1.1.1 | **Análisis Pro**: Reporte completo de arquitectura con 15+ mejoras priorizadas (ver `ARCHITECTURE_ANALYSIS_PRO.md`) |
| 2026-03-26 | 1.0.0 | Versión inicial - Launcher unificado para GCP y Azure DevOps |

---

## Autor

**Harold Adrian**
