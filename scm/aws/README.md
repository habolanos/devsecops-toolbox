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
| **[eks/](eks/README.md)** | Clusters EKS, node groups, pods y nodos |
| **[ecr/](ecr/README.md)** | Repositorios ECR, imágenes y lifecycle policies |
| **[ec2/](ec2/README.md)** | Instancias EC2, estado y volúmenes EBS |
| **[lambda/](lambda/README.md)** | Funciones Lambda, runtime y memoria |
| **[cloudwatch/](cloudwatch/README.md)** | Alarmas CloudWatch y estado |
| **[secretsmanager/](secretsmanager/)** | Secrets Manager y SSM Parameter Store |
| **[waf/](waf/)** | AWS WAF v2: Web ACLs, reglas y logging |
| **[inventory/](inventory/)** | Inventario completo multi-servicio y multi-región |
| **[notification/](notification/)** | Notificaciones EKS workloads a Google Chat |
| **[tools.py](tools.py)** | Lanzador unificado con menú interactivo |

## 🚀 AWS Tools Launcher

```bash
python tools.py
python tools.py --profile my-profile --region us-west-2
```

### Herramientas disponibles

| # | Grupo | Herramienta | GCP Equivalente | Descripción |
|---|-------|-------------|-----------------|-------------|
| 1 | IAM & Security | IAM Users Checker | gcp_iam_roles_report | Usuarios IAM, MFA, access keys |
| 2 | IAM & Security | IAM Roles Checker | gcp_iam_roles_report | Roles, trust policies, permisos |
| 3 | IAM & Security | ACM Certificate Checker | certificate-manager | Certificados SSL/TLS, expiración |
| 4 | Database | RDS Instance Checker | gcp_database_checker | Instancias RDS, backups, encryption |
| 5 | Database | RDS Storage Monitor | gcp_database_checker | Uso de almacenamiento RDS |
| 6 | Networking | VPC Networks Checker | vpc-networks | VPCs, subnets, NAT gateways |
| 7 | Networking | Security Groups Checker | cloud-armor | Reglas de entrada/salida, riesgos |
| 8 | Networking | Load Balancer Checker | load-balancer | ALB/NLB, listeners, target groups |
| 9 | Kubernetes | EKS Cluster Checker | gcp_cluster_checker | Clusters, node groups, addons |
| 10 | Artifacts | ECR Repository Checker | artifact-registry | Repositorios, imágenes, policies |
| 11 | Compute | EC2 Instances Checker | gcp_monitor | Instancias, estado, networking |
| 12 | Compute | Lambda Functions Checker | cloud-run | Funciones, runtime, memoria |
| 13 | Monitoring | CloudWatch Alarms Checker | gcp_monitor | Alarmas, estado, acciones |
| 14 | Database | **EBS Volume Checker** *(nuevo)* | gcp_disk_checker | Volúmenes EBS: cifrado, snapshots, adjuntos |
| 15 | Kubernetes | **EKS Pod Monitor** *(nuevo)* | gke_monitor_pod | CPU/memoria por pod (kubectl top pods) |
| 16 | Kubernetes | **EKS Node Monitor** *(nuevo)* | gke_monitor_node | Estado y recursos de nodos EKS |
| 17 | Security | **Secrets Manager & SSM** *(nuevo)* | gcp_secrets_configmaps_checker | Secretos, rotación, parámetros SSM |
| 18 | Networking | **WAF Web ACL Checker** *(nuevo)* | cloud-armor | WAF v2: Web ACLs, reglas, logging |
| 19 | Inventory | **AWS Inventory Generator** *(nuevo)* | generar-inventario-csv | Inventario EKS/RDS/EC2/ELB/Lambda/S3 |
| A | Sistema | Ejecutar Todos | — | Corre todos los checkers automáticamente |
| Q | Sistema | Salir | — | Salir del menú |

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
                "acm:List*",
                "secretsmanager:ListSecrets",
                "secretsmanager:DescribeSecret",
                "ssm:DescribeParameters",
                "ssm:GetParameter",
                "wafv2:ListWebACLs",
                "wafv2:GetWebACL",
                "wafv2:ListResourcesForWebACL",
                "wafv2:ListRuleGroups",
                "dynamodb:ListTables",
                "dynamodb:DescribeTable",
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:GetBucketEncryption"
            ],
            "Resource": "*"
        }
    ]
}
```

## 📁 Estructura

```
aws/
├── acm/                    # Certificate Manager (≈ certificate-manager GCP)
├── cloudwatch/             # CloudWatch Alarms (≈ gcp_monitor GCP)
├── ec2/                    # EC2 Instances + EBS Volumes (≈ gcp_disk_checker GCP)
├── ecr/                    # Container Registry (≈ artifact-registry GCP)
├── eks/                    # EKS: Clusters, Pods, Nodes (≈ cluster-gke + monitoring GCP)
├── elb/                    # Load Balancers (≈ load-balancer GCP)
├── iam/                    # IAM Users & Roles (≈ rolesypermisos GCP)
├── inventory/              # Inventario multi-servicio (≈ inventory GCP) ← NUEVO
├── lambda/                 # Lambda Functions (≈ cloud-run GCP)
├── notification/           # Notificaciones EKS → Chat (≈ notification GCP) ← NUEVO
├── rds/                    # RDS Databases (≈ cloud-sql GCP)
├── secretsmanager/         # Secrets Manager + SSM (≈ secrets-configmaps GCP) ← NUEVO
├── vpc/                    # VPC & Security Groups (≈ vpc-networks GCP)
├── waf/                    # AWS WAF v2 (≈ cloud-armor GCP) ← NUEVO
├── outcome/                # Reportes generados
├── config.json             # Configuración local (gitignored)
├── config.json.template    # Plantilla de configuración
├── requirements.txt        # Dependencias Python
├── tools.py                # Launcher principal (19 herramientas)
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
| 2026-05-03 | 1.0.1 | +6 herramientas nuevas replicadas de GCP: EBS (14), EKS Pod Monitor (15), EKS Node Monitor (16), Secrets Manager+SSM (17), WAF (18), Inventory Generator (19). Directorios: secretsmanager/, waf/, inventory/, notification/ | tools.py, ec2/aws_ebs_checker.py, eks/aws_eks_pod_checker.py, eks/aws_eks_node_checker.py, secretsmanager/aws_secrets_checker.py, waf/aws_waf_checker.py, inventory/aws_inventory_generator.py, notification/aws_notify.sh |
| 2026-03-31 | 1.0.0 | Versión inicial - 13 herramientas DevSecOps | Todos |

---

## Autor

**Harold Adrian** — AWS DevSecOps Toolbox

API Reference: [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
