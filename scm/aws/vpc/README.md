# AWS VPC & Networking Checkers

Herramientas para análisis de VPCs y configuraciones de red en AWS.

## Herramientas

| Script | Descripción |
|--------|-------------|
| `aws_vpc_checker.py` | Analiza VPCs, subnets, route tables, IGWs y NAT GWs |
| `aws_security_groups_checker.py` | Analiza Security Groups y detecta reglas riesgosas |

## Uso

```bash
# Analizar todas las VPCs
python aws_vpc_checker.py --profile default --region us-east-1

# Filtrar por VPC específica
python aws_vpc_checker.py --vpc-id vpc-12345678

# Analizar Security Groups
python aws_security_groups_checker.py -o json
```

## Detección de Riesgos en Security Groups

El checker detecta automáticamente:
- ⚠️ Puertos sensibles abiertos a 0.0.0.0/0 (SSH, RDP, MySQL, etc.)
- ⚠️ Todos los puertos abiertos a internet
- ⚠️ Rango completo de puertos abierto
- ⚠️ Reglas abiertas a todo IPv6 (::/0)

### Puertos Monitoreados

| Puerto | Servicio |
|--------|----------|
| 22 | SSH |
| 3389 | RDP |
| 3306 | MySQL |
| 5432 | PostgreSQL |
| 1433 | MSSQL |
| 27017 | MongoDB |
| 6379 | Redis |

## Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-03-31 | 1.0.0 | Versión inicial |
