# Amazon Web Services Tools

[![Toolbox Version](../../README.version.md)](../../README.version.md)

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
| **[cloudwatch/](cloudwatch/README.md)** | Alarmas CloudWatch y métricas de ECS Fargate |
| **[secretsmanager/](secretsmanager/)** | Secrets Manager y SSM Parameter Store |
| **[waf/](waf/)** | AWS WAF v2: Web ACLs, reglas y logging |
| **[inventory/](inventory/)** | Inventario completo multi-servicio y multi-región |
| **[notification/](notification/)** | Notificaciones EKS workloads a Google Chat |
| **[cloudtrail/](cloudtrail/)** | Rastreo de eventos CloudTrail |
| **[sqs/](sqs/)** | Monitor de colas SQS y topics SNS |
| **[ecs/](ecs/README.md)** | Suite ECS: salud, seguridad, costos, despliegues, tráfico, dependencias, IPs y dashboard |
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
| 20 | Monitoring | **CloudWatch Metrics Monitor** *(nuevo)* | gcp_monitor | Métricas de EC2, RDS, EKS, Lambda |
| 41 | Monitoring | **ECS Fargate Metrics Monitor** *(nuevo)* | cloud-run | Requests, latencia p95, CPU%, memoria% y errores de ECS Fargate |
| 13 | Monitoring | CloudWatch Alarms Checker | gcp_monitor | Alarmas, estado, acciones |
| 14 | Database | **EBS Volume Checker** *(nuevo)* | gcp_disk_checker | Volúmenes EBS: cifrado, snapshots, adjuntos |
| 15 | Kubernetes | **EKS Pod Monitor** *(nuevo)* | gke_monitor_pod | CPU/memoria por pod (kubectl top pods) |
| 16 | Kubernetes | **EKS Node Monitor** *(nuevo)* | gke_monitor_node | Estado y recursos de nodos EKS |
| 17 | Security | **Secrets Manager & SSM** *(nuevo)* | gcp_secrets_configmaps_checker | Secretos, rotación, parámetros SSM |
| 18 | Networking | **WAF Web ACL Checker** *(nuevo)* | cloud-armor | WAF v2: Web ACLs, reglas, logging |
| 19 | Inventory | **AWS Inventory Generator** *(nuevo)* | generar-inventario-csv | Inventario EKS/RDS/EC2/ELB/Lambda/S3 |
| 42 | Reports | **CloudTrail Event Tracker** *(nuevo)* | gcp_event_tracker | Rastreo de eventos CloudTrail por usuario/recurso/acción con severidad |
| 43 | Monitoring | **SQS/SNS Monitor** *(nuevo)* | gcp_pubsub_monitor | Backlog, edad, DLQ de colas SQS y suscripciones SNS |
| 44 | ECS | **ECS Health Analyzer** *(nuevo)* | gcp_cloudrun_health_analyzer | Desired vs running, rollouts, stopped tasks |
| 45 | ECS | **ECS Security Auditor** *(nuevo)* | gcp_cloudrun_security_auditor | IP pública, secretos en env, privileged, root, EFS |
| 46 | ECS | **ECS Cost Analyzer** *(nuevo)* | gcp_cloudrun_cost_analyzer | Estimación mensual Fargate (vCPU + GB) |
| 47 | ECS | **ECS Deployment Validator** *(nuevo)* | gcp_cloudrun_deployment_validator | Circuit breaker, health grace, imagen ECR, healthcheck |
| 48 | ECS | **ECS Dependency Mapper** *(nuevo)* | gcp_cloudrun_dependency_mapper | Servicio → TG → LB → subnets/SGs |
| 49 | ECS | **ECS Traffic Analyzer** *(nuevo)* | gcp_cloudrun_traffic_analyzer | Deployments PRIMARY/ACTIVE, rollouts, RequestCount |
| 50 | ECS | **ECS VPC IP Diagnostic** *(nuevo)* | gcp_cloudrun_vpc_ip_diagnostic | IPs disponibles por subnet vs desired tasks |
| 51 | ECS | **ECS Executive Dashboard** *(nuevo)* | gcp_cloudrun_executive_dashboard | KPIs de flota, export HTML con gráficos |
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
├── cloudwatch/             # CloudWatch Alarms + ECS Fargate metrics (≈ gcp_monitor GCP) ← NUEVO
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
├── tools.py                # Launcher principal (20+ herramientas)
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
| 2026-10-09 | **1.8.64** | **feat(aws): suite ECS (Cloud Run equiv.) + CloudTrail + SQS/SNS** — Opciones 42 CloudTrail Event Tracker (equiv. Event Tracker GCP) y 43 SQS/SNS Monitor (equiv. Pub/Sub). Suite ECS 44-51 (equiv. Cloud Run): 44 Health, 45 Security Auditor, 46 Cost, 47 Deployment Validator, 48 Dependency Mapper, 49 Traffic Analyzer, 50 VPC IP Diagnostic, 51 Executive Dashboard + `ecs/aws_ecs_common.py` compartido. Grupo `ecs` en tools.py, prompt `--service`, 47 excluida de run-all. 49 tests nuevos (suite AWS: 269 passed). | `ecs/` (9 + README), `cloudtrail/aws_cloudtrail_event_tracker.py`, `sqs/aws_sqs_sns_monitor.py`, `tools.py`, `tests/unit/test_aws_ecs_tools.py` |
| 2026-10-09 | **1.8.63** | **feat(aws): paridad — 14 stubs restantes → implementaciones reales** — 23 RDS Comparator (regiones/profiles, semáforos), 24 API Gateway Checker (v1+v2, métodos sin auth, stages sin logging), 25 VPC IP Addresses (capacidad subnets, umbrales), 28/31/34/36 Lambda suite (analyzer, cost, health score, security auditor), 29 ECR Image Filter (semver heredado GCP), 30 Reports Viewer (HTML Chart.js), 32 Infrastructure Consolidator (LB→TG→targets, huérfanos), 33 Unified Dashboard (KPIs+alertas+score, HTML), 40 Inventory Consolidator (multi-región), 37-38 SLR checker/reporter (huérfanos + matriz multi-cuenta). `tools.py`: prompts para region1/2, regions, instance, function, view, period, severity, csv-file. 59 tests nuevos. | `rds/aws_rds_comparator.py`, `vpc/aws_api_gateway_checker.py`, `vpc/aws_vpc_ip_addresses_checker.py`, `lambda/` (4), `ecr/aws_ecr_image_filter.py`, `inventory/` (4), `iam/` (2), `tools.py`, `tests/unit/test_aws_stub_tools.py` |
| 2026-10-09 | **1.8.62** | **feat(aws): paridad EKS — 4 stubs → implementaciones reales (port GCP)** — Tool 26 Pod Connectivity Checker (cadena EKS→RDS→VPC→SGs→IRSA→LB→test TCP), Tool 27 Deployment Validator (ConfigMaps/Secrets, placeholders, masking, connectivity), Tool 35 Deployments Off Analyzer (causas raíz, severidad, recomendaciones), Tool 39 Deploy Dependency Checker (endpoints, AWS Secrets Manager, TCP local/pod). Kubectl vía `aws eks update-kubeconfig` + `-o json`. `tools.py`: prompts para `--deployment`/`--rds-instance`/`--validate`. 93 tests nuevos. | `eks/aws_eks_pod_connectivity_checker.py`, `eks/aws_eks_deployment_validator.py`, `eks/aws_eks_deployments_off_analyzer.py`, `eks/aws_eks_deploy_dependency_checker.py`, `tools.py`, `tests/unit/test_aws_eks_tools.py` |
| 2026-08-31 | **1.7.52** | **feat(aws): Reporte consolidado multi-región + guard TTY** — `aws_cloudwatch_metrics_monitor.py` ahora soporta `--consolidated --regions` con Rich Table de totales y fila **TOTAL** en negrita. Homologación del consolidated report de GCP. Agregado `_is_tty()` para deshabilitar Rich spinners cuando stdout es un pipe. 6 tests unitarios nuevos. | `cloudwatch/aws_cloudwatch_metrics_monitor.py`, `tests/test_aws_cloudwatch_metrics_monitor.py`, `README.md` |
| 2026-08-31 | **1.7.51** | **feat(aws): Homologación de Cloud Run Monitoring a ECS Fargate** — Tool 41: `aws_ecs_fargate_metrics_monitor.py` con métricas de requests, latencia p95, CPU%, memoria% y error rate. Módulo base `cloudwatch/aws_cloudwatch_metrics.py` con `get_ecs_fargate_usage_metrics` y `get_ecs_fargate_metrics_parallel`. 17 tests unitarios nuevos. | `cloudwatch/aws_cloudwatch_metrics.py`, `cloudwatch/aws_ecs_fargate_metrics_monitor.py`, `tools.py`, `tests/test_aws_cloudwatch_metrics.py`, `tests/test_aws_ecs_fargate_monitor.py`, `README.md` |
| 2026-06-04 | **1.6.8** | `aws/tools.py` homologado visualmente con `gcp/tools.py` — mismos colores, emojis, nombres en español y estructura del menú Rich | `tools.py` |
| 2026-05-03 | 1.0.2 | feat: log_commands global — log_command() registra comandos ejecutados en scm/outcome/commands_YYYYMMDD.log cuando DEVSECOPS_LOG_COMMANDS=1 | tools.py |
| 2026-05-03 | 1.0.1 | +6 herramientas nuevas replicadas de GCP: EBS (14), EKS Pod Monitor (15), EKS Node Monitor (16), Secrets Manager+SSM (17), WAF (18), Inventory Generator (19). Directorios: secretsmanager/, waf/, inventory/, notification/ | tools.py, ec2/aws_ebs_checker.py, eks/aws_eks_pod_checker.py, eks/aws_eks_node_checker.py, secretsmanager/aws_secrets_checker.py, waf/aws_waf_checker.py, inventory/aws_inventory_generator.py, notification/aws_notify.sh |
| 2026-03-31 | 1.0.0 | Versión inicial - 13 herramientas DevSecOps | Todos |

> 📋 **Historial completo del toolbox**: ver [README.version.md](../../README.version.md)

---

## Autor

**Harold Adrian** — AWS DevSecOps Toolbox

API Reference: [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
