# AWS ECS Suite

Suite de herramientas para servicios **ECS / Fargate**, equivalente a
la suite Cloud Run de GCP (`scm/gcp/cloud-run/`).

## Herramientas

| Opción | Script | Descripción |
|--------|--------|-------------|
| 44 | `aws_ecs_health_analyzer.py` | Estado por servicio (HEALTHY/DEGRADED/CRITICAL/DRAINED), rollouts en curso/fallidos, stopped tasks con razón (OOM, pull, exit) |
| 45 | `aws_ecs_security_auditor.py` | IP pública asignada, secretos en env vars, containers privileged/root, rootfs escribible, EFS sin cifrado en tránsito, sin log driver, ECS Exec habilitado |
| 46 | `aws_ecs_cost_analyzer.py` | Estimación mensual por servicio Fargate: tasks running × (vCPU·$0.04048/h + GB·$0.004445/h) × 730h; detección de drained y sobredimensionados |
| 47 | `aws_ecs_deployment_validator.py` | Circuit breaker, healthCheckGracePeriod con LB, tag `latest`, existencia de imagen en ECR, healthCheck de containers, límites de memoria |
| 48 | `aws_ecs_dependency_mapper.py` | Grafo servicio → target groups → load balancers → subnets/security groups; servicios internos (sin LB) |
| 49 | `aws_ecs_traffic_analyzer.py` | Deployments PRIMARY/ACTIVE (blue/green), rollouts IN_PROGRESS/FAILED, `RequestCount` de CloudWatch por target group |
| 50 | `aws_ecs_vpc_ip_diagnostic.py` | IPs disponibles por subnet (reserva AWS de 5) vs desired tasks — diagnóstico de tasks que no pueden obtener ENI/IP |
| 51 | `aws_ecs_executive_dashboard.py` | KPIs de flota (clusters, servicios, tasks, estados, rollouts fallidos) + export HTML con Chart.js |

## Módulo compartido

`aws_ecs_common.py` centraliza: sesión boto3 (`--profile`/`--region`),
listado de clusters/servicios (paginado + `describe_services` por
lotes de 10), task definitions, `service_status`, `is_fargate`,
`task_cpu_memory`, `env_secrets`, `service_lb_targets` y la
resolución del directorio de salida (`DEVSECOPS_OUTPUT_DIR` >
`outcome/`).

## Uso

```bash
# Todos los clusters/servicios de la región
python aws_ecs_health_analyzer.py --profile prod --region us-east-1

# Solo un cluster/servicio
python aws_ecs_deployment_validator.py --cluster prod-ecs --service api

# Exports en scm/outcome/
python aws_ecs_security_auditor.py --severity critical -o json
python aws_ecs_executive_dashboard.py -o html
```

## Permisos IAM requeridos

`ecs:List*`, `ecs:Describe*`, `elasticloadbalancing:Describe*`,
`cloudwatch:GetMetricStatistics`, `ecr:DescribeImages`,
`ec2:DescribeSubnets`.

## Equivalencia con GCP

| GCP (Cloud Run) | AWS (ECS) |
|---|---|
| `gcp_cloudrun_health_analyzer` | `aws_ecs_health_analyzer` |
| `gcp_cloudrun_security_auditor` | `aws_ecs_security_auditor` |
| `gcp_cloudrun_cost_analyzer` | `aws_ecs_cost_analyzer` |
| `gcp_cloudrun_deployment_validator` | `aws_ecs_deployment_validator` |
| `gcp_cloudrun_dependency_mapper` | `aws_ecs_dependency_mapper` |
| `gcp_cloudrun_traffic_analyzer` | `aws_ecs_traffic_analyzer` |
| `gcp_cloudrun_vpc_ip_diagnostic` | `aws_ecs_vpc_ip_diagnostic` |
| `gcp_cloudrun_executive_dashboard` | `aws_ecs_executive_dashboard` |

## Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-10-09 | **1.8.64** | Creación de la suite ECS (8 herramientas + `aws_ecs_common`) como equivalente AWS de la suite Cloud Run de GCP. Tests: `scm/tests/unit/test_aws_ecs_tools.py` (49 tests). |
