# AWS ACM Certificate Checker

Monitoreo de certificados SSL/TLS en AWS Certificate Manager.

## Uso

```bash
python aws_acm_checker.py --profile default --region us-east-1
python aws_acm_checker.py --days 60 -o json
```

## Alertas de Expiración

| Estado | Condición | Indicador |
|--------|-----------|-----------|
| OK | >30 días | 🟢 |
| Warning | 8-30 días | 🟡 |
| Critical | 1-7 días | 🔴 |
| Expired | <0 días | 🔴 EXPIRADO |

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
