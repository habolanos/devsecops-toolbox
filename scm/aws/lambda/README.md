# AWS Lambda Functions Checker

Análisis de funciones AWS Lambda, runtime, memoria y configuración.

## Uso

```bash
python aws_lambda_checker.py --profile default --region us-east-1
python aws_lambda_checker.py --filter my-func -o json
```

## Análisis

- ⚠️ Runtime deprecado (python3.7, nodejs12.x, etc.)
- ⚠️ Timeout máximo (15 min)
- ⚠️ Memoria alta (>3GB)
- ⚠️ Sin descripción

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
