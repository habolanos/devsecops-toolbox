# AWS Tools API Documentation

**Versión:** 1.0.0  
**Fecha:** 9 de Julio de 2026  
**Plataforma:** AWS (Amazon Web Services)

---

## 📋 Índice

1. [Herramientas de Monitoreo](#herramientas-de-monitoreo)
2. [Herramientas de Kubernetes (EKS)](#herramientas-de-kubernetes-eks)
3. [Herramientas de Base de Datos (RDS)](#herramientas-de-base-de-datos-rds)
4. [Herramientas de Redes (VPC)](#herramientas-de-redes-vpc)
5. [Herramientas de Compute (Lambda)](#herramientas-de-compute-lambda)
6. [Herramientas de IAM](#herramientas-de-iam)
7. [Herramientas de Inventario](#herramientas-de-inventario)
8. [Herramientas de Artefactos (ECR)](#herramientas-de-artefactos-ecr)

---

## Herramientas de Monitoreo

### Tool 20: CloudWatch Metrics Monitor

**Descripción:** Monitorea métricas de CloudWatch para EC2, RDS, EKS, Lambda

**Ubicación:** `scm/aws/cloudwatch/aws_cloudwatch_metrics_monitor.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_cloudwatch_metrics_monitor.py --profile prod --region us-east-1 -o json
```

**Salida esperada:**
```json
{
  "region": "us-east-1",
  "metrics": [
    {
      "namespace": "AWS/EC2",
      "metric_name": "CPUUtilization",
      "instances": 5,
      "average": 45.2
    }
  ]
}
```

---

## Herramientas de Kubernetes (EKS)

### Tool 21: EKS Deployments Report

**Descripción:** Genera reporte detallado de deployments en EKS

**Ubicación:** `scm/aws/eks/aws_eks_deployments_report.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
--cluster    # Nombre del cluster EKS
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_eks_deployments_report.py --profile prod --cluster my-cluster -o json
```

---

### Tool 26: EKS Pod Connectivity Checker

**Descripción:** Valida conectividad desde pods EKS a RDS

**Ubicación:** `scm/aws/eks/aws_eks_pod_connectivity_checker.py`

**Parámetros:**
```bash
--profile          # AWS profile (opcional)
--region           # Región AWS (default: us-east-1)
--cluster          # Nombre del cluster EKS
--deployment       # Nombre del deployment
--rds-instance     # Instancia RDS a validar
-o, --output       # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_eks_pod_connectivity_checker.py --cluster my-cluster --deployment app --rds-instance mydb -o json
```

---

### Tool 27: EKS Deployment Validator

**Descripción:** Valida configuración y conectividad de deployments EKS

**Ubicación:** `scm/aws/eks/aws_eks_deployment_validator.py`

**Parámetros:**
```bash
--profile       # AWS profile (opcional)
--region        # Región AWS (default: us-east-1)
--cluster       # Nombre del cluster EKS
--deployment    # Nombre del deployment
--namespace     # Namespace (opcional)
--validate      # Tipo de validación (config, connectivity, all)
-o, --output    # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_eks_deployment_validator.py --cluster my-cluster --deployment app --validate all -o json
```

---

### Tool 35: EKS Deployments Off Analyzer

**Descripción:** Analiza deployments no running en EKS con diagnóstico automático

**Ubicación:** `scm/aws/eks/aws_eks_deployments_off_analyzer.py`

**Parámetros:**
```bash
--profile       # AWS profile (opcional)
--region        # Región AWS (default: us-east-1)
--cluster       # Nombre del cluster EKS
--namespace     # Namespace (opcional)
-o, --output    # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_eks_deployments_off_analyzer.py --cluster my-cluster -o json
```

---

### Tool 39: EKS Deploy Dependency Checker

**Descripción:** Analiza dependencias de deployments EKS

**Ubicación:** `scm/aws/eks/aws_eks_deploy_dependency_checker.py`

**Parámetros:**
```bash
--profile       # AWS profile (opcional)
--region        # Región AWS (default: us-east-1)
--cluster       # Nombre del cluster EKS
--deployment    # Nombre del deployment
--namespace     # Namespace (opcional)
-o, --output    # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_eks_deploy_dependency_checker.py --cluster my-cluster --deployment app -o json
```

---

## Herramientas de Base de Datos (RDS)

### Tool 22: RDS Database Checker

**Descripción:** Lista bases de datos por instancia RDS

**Ubicación:** `scm/aws/rds/aws_rds_database_checker.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_rds_database_checker.py --profile prod --region us-east-1 -o json
```

**Salida esperada:**
```json
{
  "region": "us-east-1",
  "instances": [
    {
      "name": "mydb-instance",
      "engine": "postgres",
      "databases": ["db1", "db2"]
    }
  ]
}
```

---

### Tool 23: RDS Comparator

**Descripción:** Compara instancias RDS entre regiones o cuentas

**Ubicación:** `scm/aws/rds/aws_rds_comparator.py`

**Parámetros:**
```bash
--profile     # AWS profile (opcional)
--region1     # Primera región (default: us-east-1)
--region2     # Segunda región (default: us-west-2)
--instance    # Nombre específico de instancia (opcional)
-o, --output  # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_rds_comparator.py --region1 us-east-1 --region2 us-west-2 -o json
```

---

## Herramientas de Redes (VPC)

### Tool 24: API Gateway Checker

**Descripción:** Analiza API Gateways, stages, métodos y autorizaciones

**Ubicación:** `scm/aws/vpc/aws_api_gateway_checker.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_api_gateway_checker.py --profile prod --region us-east-1 -o json
```

---

### Tool 25: VPC IP Addresses Checker

**Descripción:** Analiza capacidad de red de VPCs y subnets

**Ubicación:** `scm/aws/vpc/aws_vpc_ip_addresses_checker.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_vpc_ip_addresses_checker.py --profile prod -o json
```

---

## Herramientas de Compute (Lambda)

### Tool 28: Lambda Functions Analyzer

**Descripción:** Análisis profundo de funciones Lambda (seguridad, costos, performance)

**Ubicación:** `scm/aws/lambda/aws_lambda_analyzer.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
--function   # Nombre de función (opcional)
--view       # Tipo de vista: summary, detailed, security
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_lambda_analyzer.py --region us-east-1 --view detailed -o json
```

---

### Tool 31: Lambda Cost Analyzer

**Descripción:** Análisis de costos y optimización de funciones Lambda

**Ubicación:** `scm/aws/lambda/aws_lambda_cost_analyzer.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
--function   # Nombre de función (opcional)
--period     # Período de análisis (7d, 30d, 90d)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_lambda_cost_analyzer.py --period 30d -o json
```

---

### Tool 34: Lambda Health Analyzer

**Descripción:** Análisis de salud y rendimiento de funciones Lambda

**Ubicación:** `scm/aws/lambda/aws_lambda_health_analyzer.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
--function   # Nombre de función (opcional)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_lambda_health_analyzer.py --region us-east-1 -o json
```

---

### Tool 36: Lambda Security Auditor

**Descripción:** Auditoría completa de seguridad en funciones Lambda

**Ubicación:** `scm/aws/lambda/aws_lambda_security_auditor.py`

**Parámetros:**
```bash
--profile     # AWS profile (opcional)
--region      # Región AWS (default: us-east-1)
--function    # Nombre de función (opcional)
--severity    # Nivel de severidad: critical, high, medium, low
-o, --output  # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_lambda_security_auditor.py --severity critical -o json
```

---

## Herramientas de IAM

### Tool 37: IAM Service Linked Roles Checker

**Descripción:** Analiza Service Linked Roles y permisos

**Ubicación:** `scm/aws/iam/aws_service_linked_roles_checker.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_service_linked_roles_checker.py --profile prod -o json
```

---

### Tool 38: IAM Service Linked Roles Reporter

**Descripción:** Reporte multi-cuenta de Service Linked Roles

**Ubicación:** `scm/aws/iam/aws_service_linked_roles_reporter.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_service_linked_roles_reporter.py --profile prod -o json
```

---

## Herramientas de Inventario

### Tool 30: AWS Reports Viewer

**Descripción:** Genera gráficos HTML desde reportes JSON

**Ubicación:** `scm/aws/inventory/aws_reports_viewer.py`

**Parámetros:**
```bash
# Sin parámetros requeridos
```

**Ejemplo de uso:**
```bash
python aws_reports_viewer.py
```

---

### Tool 32: AWS Infrastructure Consolidator

**Descripción:** Consolida ALB, Lambda, RDS con mapeo de relaciones

**Ubicación:** `scm/aws/inventory/aws_infrastructure_consolidator.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--region     # Región AWS (default: us-east-1)
--view       # Tipo de vista: summary, detailed, relationships
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_infrastructure_consolidator.py --view relationships -o json
```

---

### Tool 33: AWS Unified Infrastructure Dashboard

**Descripción:** Dashboard ejecutivo unificado con alertas y recomendaciones

**Ubicación:** `scm/aws/inventory/aws_unified_infrastructure_dashboard.py`

**Parámetros:**
```bash
--profile       # AWS profile (opcional)
--region        # Región AWS (default: us-east-1)
--interactive   # Modo interactivo (true/false)
-o, --output    # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_unified_infrastructure_dashboard.py --interactive true -o json
```

---

### Tool 40: AWS Inventory Consolidator

**Descripción:** Consolida inventario de múltiples regiones y cuentas

**Ubicación:** `scm/aws/inventory/aws_inventory_consolidator.py`

**Parámetros:**
```bash
--profile    # AWS profile (opcional)
--regions    # Regiones a incluir (comma-separated)
-o, --output # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_inventory_consolidator.py --regions us-east-1,us-west-2 -o json
```

---

## Herramientas de Artefactos (ECR)

### Tool 29: ECR Image Filter

**Descripción:** Filtra y exporta imágenes de ECR a Excel

**Ubicación:** `scm/aws/ecr/aws_ecr_image_filter.py`

**Parámetros:**
```bash
--profile     # AWS profile (opcional)
--region      # Región AWS (default: us-east-1)
--csv-file    # Archivo CSV de entrada (opcional)
-o, --output  # Formato de salida: json, csv
```

**Ejemplo de uso:**
```bash
python aws_ecr_image_filter.py --region us-east-1 -o json
```

---

## Formatos de Salida

### JSON
```bash
-o json
```

Genera salida en formato JSON estructurado.

### CSV
```bash
-o csv
```

Genera salida en formato CSV para importar en Excel.

---

## Códigos de Error

| Código | Descripción |
|--------|------------|
| 0 | Éxito |
| 1 | Error general |
| 2 | Parámetros inválidos |
| 3 | Credenciales inválidas |
| 4 | Recurso no encontrado |
| 5 | Timeout |

---

## Autenticación

Todas las herramientas utilizan credenciales de AWS configuradas mediante:

1. **Variables de entorno:**
   ```bash
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   ```

2. **Archivo de configuración:**
   ```bash
   ~/.aws/credentials
   ```

3. **Perfil específico:**
   ```bash
   --profile nombre_perfil
   ```

---

## Ejemplos de Flujos Completos

### Flujo 1: Análisis de RDS
```bash
# 1. Listar bases de datos
python aws_rds_database_checker.py --region us-east-1 -o json

# 2. Comparar entre regiones
python aws_rds_comparator.py --region1 us-east-1 --region2 us-west-2 -o json
```

### Flujo 2: Análisis de EKS
```bash
# 1. Generar reporte de deployments
python aws_eks_deployments_report.py --cluster my-cluster -o json

# 2. Validar deployments
python aws_eks_deployment_validator.py --cluster my-cluster --deployment app -o json

# 3. Verificar conectividad
python aws_eks_pod_connectivity_checker.py --cluster my-cluster --deployment app --rds-instance mydb -o json
```

### Flujo 3: Análisis de Lambda
```bash
# 1. Análisis profundo
python aws_lambda_analyzer.py --view detailed -o json

# 2. Análisis de costos
python aws_lambda_cost_analyzer.py --period 30d -o json

# 3. Auditoría de seguridad
python aws_lambda_security_auditor.py --severity critical -o json
```

---

## Soporte y Documentación

- **Documentación principal:** `README.md`
- **Guías de operación:** `operation/`
- **Ejemplos:** `examples/`
- **Tests:** `scm/aws/tests/`

---

**Documentación de API AWS Tools v1.0.0**  
**Última actualización:** 9 de Julio de 2026
