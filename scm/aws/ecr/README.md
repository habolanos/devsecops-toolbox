# AWS ECR Repository Checker

Análisis de repositorios Amazon ECR, imágenes y políticas.

## Uso

```bash
python aws_ecr_checker.py --profile default --region us-east-1
python aws_ecr_checker.py --repo my-app -o json
```

## Análisis de Seguridad

- ⚠️ Sin lifecycle policy configurada
- ⚠️ Scan on push deshabilitado
- ⚠️ Tags mutables (riesgo de sobrescritura)

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
