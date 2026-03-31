# AWS CloudWatch Alarms Checker

Monitoreo de alarmas CloudWatch, estado y configuración.

## Uso

```bash
python aws_cloudwatch_checker.py --profile default --region us-east-1
python aws_cloudwatch_checker.py --state ALARM -o json
```

## Estados

| Estado | Indicador |
|--------|-----------|
| OK | 🟢 |
| ALARM | 🔴 |
| INSUFFICIENT_DATA | 🟡 |

## Análisis

- ⚠️ Acciones deshabilitadas
- ⚠️ Sin acciones de alarma configuradas
- ⚠️ Datos insuficientes para evaluar

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
