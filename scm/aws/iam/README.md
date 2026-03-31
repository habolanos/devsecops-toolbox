# AWS IAM Checkers

Herramientas para análisis de seguridad IAM en AWS.

## Herramientas

| Script | Descripción |
|--------|-------------|
| `aws_iam_checker.py` | Analiza usuarios IAM, MFA, access keys y políticas |
| `aws_roles_checker.py` | Lista roles IAM, trust policies y permisos |

## Uso

```bash
# Analizar usuarios IAM
python aws_iam_checker.py --profile default --region us-east-1

# Exportar a JSON
python aws_iam_checker.py -o json

# Analizar roles IAM
python aws_roles_checker.py --profile default

# Filtrar roles por nombre
python aws_roles_checker.py --filter lambda
```

## Argumentos

| Argumento | Descripción | Default |
|-----------|-------------|---------|
| `--profile`, `-p` | AWS CLI profile | `default` |
| `--region`, `-r` | AWS region | `us-east-1` |
| `--output`, `-o` | Formato de salida (json, csv, table) | `table` |
| `--filter`, `-f` | Filtrar por nombre (solo roles) | - |
| `--debug`, `-d` | Modo debug | `false` |

## Análisis de Seguridad

El checker de usuarios identifica:
- ❌ Usuarios sin MFA habilitado
- ⚠️ Access keys con más de 90 días
- ⚠️ Múltiples access keys activas
- ❌ Usuarios sin políticas ni grupos

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
