# DevSecOps Toolbox - SCM

Punto de entrada unificado para herramientas de múltiples plataformas cloud y DevOps.

## 📋 Contenido

| Directorio/Archivo | Descripción |
|--------------------|-------------|
| `main.py` | Launcher principal - punto de entrada unificado |
| `gcp/` | Herramientas SRE para Google Cloud Platform |
| `azdo/` | Herramientas para Azure DevOps |
| `aws/` | Herramientas DevSecOps para Amazon Web Services |

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

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-04-02 | 1.5.0 | **Config Unificado**: Template `config.json.template` para gestión centralizada de tokens/credenciales de AZDO, GCP y AWS. Variables de entorno automáticas al lanzar plataformas. |
| 2026-03-31 | 1.4.1 | **AWS Toolbox**: 13 herramientas DevSecOps para AWS (IAM, RDS, VPC, EKS, ECR, EC2, Lambda, CloudWatch) |
| 2026-03-31 | 1.1.1 | **Análisis Pro**: Reporte completo de arquitectura con 15+ mejoras priorizadas (ver `ARCHITECTURE_ANALYSIS_PRO.md`) |
| 2026-03-26 | 1.0.0 | Versión inicial - Launcher unificado para GCP y Azure DevOps |

---

## Autor

**Harold Adrian**
