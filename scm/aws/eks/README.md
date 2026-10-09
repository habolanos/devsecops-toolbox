# AWS EKS Cluster Checker

Monitoreo de clusters Amazon EKS, node groups, addons y seguridad.

## Uso

```bash
python aws_eks_checker.py --profile default --region us-east-1
python aws_eks_checker.py --cluster my-cluster -o json
```

## Análisis de Seguridad

- ⚠️ Endpoint público abierto a 0.0.0.0/0
- ⚠️ Sin acceso privado al endpoint
- ⚠️ Sin encryption de secrets
- ⚠️ Logging de cluster no habilitado

## Herramientas de conectividad y despliegue (paridad GCP)

Requieren AWS CLI + `kubectl` instalados. El contexto se configura con
`aws eks update-kubeconfig --name <cluster> --region <region> [--profile <p>]`;

si `--cluster` está vacío se usa el contexto kubectl actual.

| Opción | Script | Descripción |
|--------|--------|-------------|
| 21 | `aws_eks_deployments_report.py` | Reporte de deployments del cluster |
| 26 | `aws_eks_pod_connectivity_checker.py` | Cadena completa pod→RDS: deployment, cluster, VPC, Security Groups, IRSA, LoadBalancers y test TCP desde pod probe |
| 27 | `aws_eks_deployment_validator.py` | Valida ConfigMaps/Secrets referenciados (existencia, placeholders, masking), endpoints y conectividad (`--validate all\|configmaps\|secrets\|connectivity`) |
| 35 | `aws_eks_deployments_off_analyzer.py` | Detecta deployments con ready<desired, clasifica causa raíz (ImagePull/CrashLoop/scheduling/config), severidad y recomendaciones |
| 39 | `aws_eks_deploy_dependency_checker.py` | Extrae endpoints del deployment (ConfigMaps/Secrets, URLs JDBC, host:port) y referencias AWS Secrets Manager; prueba TCP local o vía pod probe |

```bash
# Conectividad pod → RDS
python aws_eks_pod_connectivity_checker.py --profile p --region us-east-1 \
    --cluster my-eks --deployment my-app --rds-instance my-db -o json

# Validación de un deployment
python aws_eks_deployment_validator.py --cluster my-eks \
    --deployment my-app --namespace prod --validate all

# Deployments no running (causa raíz + recomendaciones)
python aws_eks_deployments_off_analyzer.py --cluster my-eks -o json

# Dependencias de un deployment (endpoints + test TCP)
python aws_eks_deploy_dependency_checker.py --cluster my-eks \
    --deployment my-app -o json
```

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-10-09 | 1.0.0 | Implementación real de tools 26/27/35/39 (antes stubs): connectivity checker EKS→RDS, deployment validator, deployments-off analyzer y deploy dependency checker — port de `gcp/connectivity` y `gcp/deployments_off` usando `kubectl -o json` (sin dep `kubernetes`) |
| 2026-03-31 | 1.0.0 | Versión inicial |
