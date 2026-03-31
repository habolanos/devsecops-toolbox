# Amazon Web Services Tools

Herramientas DevSecOps para análisis y monitoreo de recursos AWS.

## 📋 Contenido

| Directorio | Descripción |
|------------|-------------|
| **[iam/](iam/README.md)** | Análisis de usuarios IAM, roles, políticas y MFA |
| **[acm/](acm/README.md)** | Monitoreo de certificados SSL/TLS en ACM |
| **[rds/](rds/README.md)** | Análisis de instancias RDS y monitoreo de storage |
| **[vpc/](vpc/README.md)** | VPCs, subnets, route tables y Security Groups |
| **[elb/](elb/README.md)** | Application y Network Load Balancers |
| **[eks/](eks/README.md)** | Clusters EKS, node groups y addons |
| **[ecr/](ecr/README.md)** | Repositorios ECR, imágenes y lifecycle policies |
| **[ec2/](ec2/README.md)** | Instancias EC2, estado y configuración |
| **[lambda/](lambda/README.md)** | Funciones Lambda, runtime y memoria |
| **[cloudwatch/](cloudwatch/README.md)** | Alarmas CloudWatch y estado |
| **[tools.py](tools.py)** | Lanzador unificado con menú interactivo |

## 🚀 AWS Tools Launcher

```bash
python tools.py
python tools.py --profile my-profile --region us-west-2
```

### Herramientas disponibles

| # | Grupo | Herramienta | Descripción |
|---|-------|-------------|-------------|
| 1 | IAM & Security | IAM Users Checker | Usuarios IAM, MFA, access keys |
| 2 | IAM & Security | IAM Roles Checker | Roles, trust policies, permisos |
| 3 | IAM & Security | ACM Certificate Checker | Certificados SSL/TLS, expiración |
| 4 | Database | RDS Instance Checker | Instancias RDS, backups, encryption |
| 5 | Database | RDS Storage Monitor | Uso de almacenamiento RDS |
| 6 | Networking | VPC Networks Checker | VPCs, subnets, NAT gateways |
| 7 | Networking | Security Groups Checker | Reglas de entrada/salida, riesgos |
| 8 | Networking | Load Balancer Checker | ALB/NLB, listeners, target groups |
| 9 | Kubernetes | EKS Cluster Checker | Clusters, node groups, addons |
| 10 | Artifacts | ECR Repository Checker | Repositorios, imágenes, policies |
| 11 | Compute | EC2 Instances Checker | Instancias, estado, networking |
| 12 | Compute | Lambda Functions Checker | Funciones, runtime, memoria |
| 13 | Monitoring | CloudWatch Alarms Checker | Alarmas, estado, acciones |
| A | Sistema | Ejecutar Todos | Corre todos los checkers |
| Q | Sistema | Salir | Salir del menú |

## 🔧 Requisitos

- Cuenta AWS con credenciales configuradas
- AWS CLI instalado y configurado (`aws configure`)
- Python 3.8 o superior
- boto3 >= 1.34.0

## 📦 Instalación

```bash
cd devsecops-toolbox/scm/aws
pip install -r requirements.txt
```

## ⚙️ Configuración

Crear `config.json` basado en la plantilla:

```bash
cp config.json.template config.json
```

Editar con tus valores:

```json
{
    "aws": {
        "profile": "default",
        "region": "us-east-1",
        "account_id": "123456789012"
    },
    "defaults": {
        "output_format": "json",
        "output_dir": "outcome"
    }
}
```

## 🔐 Permisos IAM Requeridos

Para ejecutar todas las herramientas, el usuario/rol necesita permisos de lectura:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:List*",
                "iam:Get*",
                "rds:Describe*",
                "ec2:Describe*",
                "eks:Describe*",
                "eks:List*",
                "ecr:Describe*",
                "ecr:Get*",
                "ecr:List*",
                "elasticloadbalancing:Describe*",
                "lambda:List*",
                "lambda:Get*",
                "cloudwatch:Describe*",
                "cloudwatch:Get*",
                "acm:Describe*",
                "acm:List*"
            ],
            "Resource": "*"
        }
    ]
}
```

## 📁 Estructura

```
aws/
├── acm/                    # Certificate Manager
├── cloudwatch/             # CloudWatch Alarms
├── ec2/                    # EC2 Instances
├── ecr/                    # Container Registry
├── eks/                    # Elastic Kubernetes Service
├── elb/                    # Load Balancers
├── iam/                    # IAM Users & Roles
├── lambda/                 # Lambda Functions
├── rds/                    # RDS Databases
├── vpc/                    # VPC & Security Groups
├── outcome/                # Reportes generados
├── config.json             # Configuración local
├── config.json.template    # Plantilla de configuración
├── requirements.txt        # Dependencias Python
├── tools.py                # Launcher principal
└── README.md               # Este archivo
```

## 🎨 Características

- **UI moderna con Rich**: Paneles, tablas con colores, indicadores visuales
- **Detección de riesgos**: Análisis automático de configuraciones inseguras
- **Exportación flexible**: JSON, CSV o tabla en consola
- **Barras de progreso**: Feedback visual durante el análisis
- **Tiempo de ejecución**: Muestra duración de cada análisis

## 📖 Uso Individual

Cada herramienta puede ejecutarse de forma independiente:

```bash
# IAM Users
python iam/aws_iam_checker.py --profile prod --region us-east-1 -o json

# RDS Storage
python rds/aws_rds_storage_checker.py --threshold 75 -o csv

# Security Groups
python vpc/aws_security_groups_checker.py --vpc-id vpc-12345678

# EKS Clusters
python eks/aws_eks_checker.py --cluster my-cluster -o json
```

## 📊 Indicadores de Estado

| Indicador | Significado |
|-----------|-------------|
| 🟢 | OK / Sin problemas |
| 🟡 | Advertencia / Revisar |
| 🔴 | Crítico / Requiere acción |
| ✅ | Habilitado / Configurado |
| ❌ | Deshabilitado / Falta configuración |

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción | Archivos |
|-------|---------|-------------|----------|
| 2026-03-31 | 1.0.0 | Versión inicial - 13 herramientas DevSecOps | Todos |

---

## Autor

**Harold Adrian** — AWS DevSecOps Toolbox

API Reference: [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
