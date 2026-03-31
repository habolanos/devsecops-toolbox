# AWS RDS Checkers

Herramientas para monitoreo y análisis de Amazon RDS.

## Herramientas

| Script | Descripción |
|--------|-------------|
| `aws_rds_checker.py` | Analiza instancias RDS: estado, backups, encryption, seguridad |
| `aws_rds_storage_checker.py` | Monitorea uso de almacenamiento con alertas |

## Uso

```bash
# Analizar todas las instancias RDS
python aws_rds_checker.py --profile default --region us-east-1

# Filtrar por identificador
python aws_rds_checker.py --instance my-database

# Monitor de almacenamiento con threshold personalizado
python aws_rds_storage_checker.py --threshold 75 -o json
```

## Análisis de Seguridad

El checker identifica:
- ❌ Storage no encriptado
- ⚠️ Instancia públicamente accesible
- ⚠️ Backup retention bajo (<7 días)
- ❌ Sin protección contra eliminación
- ⚠️ Sin Multi-AZ (alta disponibilidad)

## Alertas de Storage

| Nivel | Umbral | Indicador |
|-------|--------|-----------|
| OK | <80% | 🟢 |
| Warning | ≥80% | 🟡 |
| Critical | ≥95% | 🔴 |

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
