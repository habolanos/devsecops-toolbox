# AWS EC2 Instances Checker

Análisis de instancias Amazon EC2, estado, networking y seguridad.

## Uso

```bash
python aws_ec2_checker.py --profile default --region us-east-1
python aws_ec2_checker.py --state running -o json
```

## Análisis de Seguridad

- ⚠️ Instancia con IP pública
- ⚠️ Sin IAM Role asignado
- ⚠️ Monitoring detallado no habilitado
- ⚠️ Sin key pair

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
