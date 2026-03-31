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

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
