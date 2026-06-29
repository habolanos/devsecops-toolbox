# 📋 Guía de Estandarización JSON y Nombres de Archivos

**Fecha:** 25 de Junio de 2026  
**Objetivo:** Implementar estandarización de JSON y nombres de archivos en todas las herramientas

---

## 📊 Resumen Ejecutivo

### Cambios Principales

```
1. Estructura JSON Estandarizada
   - Metadata consistente
   - Summary consistente
   - Data array consistente

2. Nombres de Archivos Estandarizados
   - Patrón: {tool_name}_{timestamp}.{format}
   - Timestamp: YYYYMMDD_HHMMSS
   - Formato: json, csv, xlsx

3. Ubicación Centralizada
   - Todos en: scm/outcome/
   - Respeta DEVSECOPS_OUTPUT_DIR
   - Estructura por plataforma (opcional)
```

---

## 🔧 Módulo Centralizado: export_manager.py

### Ubicación
```
scm/export_manager.py
```

### Características

```python
class ExportManager:
    """Gestor centralizado de exportación"""
    
    def __init__(tool_name, tool_version):
        """Inicializa con nombre y versión de herramienta"""
    
    def export_json(data, metadata, summary, org, project, tz):
        """Exporta a JSON estandarizado"""
    
    def export_csv(data, fieldnames):
        """Exporta a CSV estandarizado"""
    
    def export_excel(data, sheet_name, metadata, summary):
        """Exporta a Excel estandarizado"""
    
    def export_all(data, formats, ...):
        """Exporta a múltiples formatos"""
```

### Funciones Simplificadas

```python
# Para JSON
export_json_simple(data, tool_name, tool_version, org, project, tz, metadata, summary)

# Para CSV
export_csv_simple(data, tool_name, fieldnames)

# Para Excel
export_excel_simple(data, tool_name, sheet_name, metadata, summary)
```

---

## 📝 Estructura JSON Estandarizada

### Formato Completo

```json
{
  "metadata": {
    "tool": "nombre_herramienta",
    "version": "1.0.0",
    "generated_at": "2026-06-25T18:02:00+00:00",
    "organization": "org_name",
    "project": "project_name"
  },
  "summary": {
    "total": 100,
    "filtered": 50,
    "status": "success"
  },
  "data": [
    {
      "field1": "value1",
      "field2": "value2",
      "field3": "value3"
    }
  ]
}
```

### Campos Obligatorios

```
metadata:
  - tool (string): Nombre de la herramienta
  - version (string): Versión de la herramienta
  - generated_at (ISO timestamp): Fecha/hora de generación

summary:
  - total (integer): Total de registros
  - filtered (integer): Registros filtrados
  - status (string): success|error|empty

data:
  - array de objetos con los datos
```

### Campos Opcionales

```
metadata:
  - organization (string): Nombre de la organización
  - project (string): Nombre del proyecto
  - custom_field (any): Campos adicionales específicos

summary:
  - custom_metric (any): Métricas adicionales específicas
```

---

## 📁 Nombres de Archivos Estandarizados

### Patrón

```
{tool_name}_{timestamp}.{format}

Donde:
  - tool_name: Nombre de la herramienta (snake_case)
  - timestamp: YYYYMMDD_HHMMSS
  - format: json, csv, xlsx
```

### Ejemplos

```
JSON:
  pr_master_checker_20260625_180200.json
  branch_policy_checker_20260625_180200.json
  release_cd_health_20260625_180200.json

CSV:
  pr_master_checker_20260625_180200.csv
  branch_policy_checker_20260625_180200.csv
  release_cd_health_20260625_180200.csv

Excel:
  pr_master_checker_20260625_180200.xlsx
  branch_policy_checker_20260625_180200.xlsx
  release_cd_health_20260625_180200.xlsx
```

### Convención de Nombres de Herramientas

```
AZDO:
  - pr_master_checker
  - pr_pipeline_analyzer
  - branch_policy_checker
  - branch_lock_checker
  - release_cd_health
  - pipeline_drift
  - release_deep_dive
  - task_validator
  - pipeline_logs_scanner
  - repo_vulnerabilities_scanner
  - cicd_inventory
  - gke_pipelines_inventory
  - pending_approvals
  - branches_created
  - hotfix_branches_inventory
  - ci_pipeline_inventory
  - cd_pipeline_inventory
  - pipeline_health_score
  - prod_deploy_inventory
  - pipeline_status
  - release_explorer
  - properties_branch_diff
  - repo_branch_diff
  - release_rollback
  - release_restore
  - release_cd_rollback
  - release_cd_update

GCP:
  - gcp_monitor_resources
  - gcp_gke_deployments_report
  - gcp_iam_roles_report
  - gcp_service_account_checker
  - gcp_certificate_manager_checker
  - gcp_cloud_armor_checker
  - gcp_cloud_sql_disk_monitor
  - gcp_cloud_sql_database_checker
  - gcp_cloud_sql_comparator
  - gcp_vpc_networks_checker
  - gcp_gateway_services_checker
  - gcp_load_balancer_checker
  - gcp_ip_addresses_checker
  - gcp_gke_cluster_checker
  - gcp_secrets_configmaps_checker
  - gcp_pod_connectivity_checker
  - gcp_gke_workload_analyzer
  - gcp_gke_pod_disruption_budgets
  - gcp_gke_network_policies
  - gcp_gke_rbac_analyzer
  - gcp_gke_node_resources_monitor
  - gcp_gke_pod_resources_monitor

AWS:
  - aws_iam_users_policies_checker
  - aws_iam_roles_checker
  - aws_acm_certificate_checker
  - aws_rds_instance_checker
  - aws_rds_storage_monitor
  - aws_vpc_networks_checker
  - aws_security_groups_checker
  - aws_load_balancer_checker
  - aws_eks_cluster_checker
  - aws_ecr_repository_checker
  - aws_ec2_instances_checker
  - aws_lambda_functions_checker
  - aws_cloudwatch_alarms_checker
  - aws_ebs_volume_checker
  - aws_eks_pod_monitor
  - aws_eks_node_monitor
  - aws_secrets_manager_checker
  - aws_waf_web_acl_checker
  - aws_inventory_generator

Terminal:
  - terminal_tls_certificate_validator
  - terminal_database_connection_tester
  - terminal_kubernetes_manifest_diff
  - terminal_kubernetes_deployment_validator
  - terminal_docker_image_validator
  - terminal_git_repository_validator
```

---

## 🚀 Cómo Usar export_manager.py

### Opción 1: Usar la Clase ExportManager

```python
from export_manager import ExportManager

# Crear instancia
manager = ExportManager("pr_master_checker", "1.0.0")

# Exportar a JSON
json_file = manager.export_json(
    data=rows,
    organization="Coppel-Retail",
    project="MiProyecto",
    summary={"active": 50, "completed": 30},
    timezone="America/Mexico_City"
)

# Exportar a CSV
csv_file = manager.export_csv(rows)

# Exportar a Excel
excel_file = manager.export_excel(
    rows,
    sheet_name="Pull Requests",
    summary={"active": 50, "completed": 30}
)

# Exportar a todos los formatos
results = manager.export_all(
    data=rows,
    formats=["json", "csv", "excel"],
    organization="Coppel-Retail",
    project="MiProyecto",
    summary={"active": 50, "completed": 30}
)

print(f"JSON: {results['json']}")
print(f"CSV: {results['csv']}")
print(f"Excel: {results['excel']}")
```

### Opción 2: Usar Funciones Simplificadas

```python
from export_manager import export_json_simple, export_csv_simple, export_excel_simple

# Exportar a JSON
json_file = export_json_simple(
    data=rows,
    tool_name="pr_master_checker",
    tool_version="1.0.0",
    organization="Coppel-Retail",
    project="MiProyecto"
)

# Exportar a CSV
csv_file = export_csv_simple(
    data=rows,
    tool_name="pr_master_checker"
)

# Exportar a Excel
excel_file = export_excel_simple(
    data=rows,
    tool_name="pr_master_checker",
    sheet_name="Pull Requests"
)
```

---

## 📋 Checklist de Migración

### Paso 1: Actualizar Imports

```python
# Agregar al inicio del archivo
from export_manager import ExportManager, export_json_simple, export_csv_simple, export_excel_simple
```

### Paso 2: Reemplazar Función export_results

```python
# ANTES (Antiguo)
def export_results(rows, output_format, script_dir, stage_name, tz_name):
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"pr_master_{ts}.json")
        payload = {
            "metadata": {...},
            "total": len(rows),
            "data": rows,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath
    # ... más código

# DESPUÉS (Nuevo)
def export_results(rows, output_format, organization, project, timezone):
    manager = ExportManager("pr_master_checker", __version__)
    
    if output_format == "json":
        return manager.export_json(
            rows,
            organization=organization,
            project=project,
            timezone=timezone,
            summary={"total": len(rows)}
        )
    elif output_format == "csv":
        return manager.export_csv(rows)
    elif output_format == "excel":
        return manager.export_excel(rows, sheet_name="Pull Requests")
```

### Paso 3: Actualizar Llamadas a export_results

```python
# ANTES
if args.output:
    filepath = export_results(all_rows, args.output, script_dir, args.stage_name, tz_name)

# DESPUÉS
if args.output:
    filepath = export_results(all_rows, args.output, args.org, args.project, tz_name)
```

### Paso 4: Actualizar Argumentos

```python
# Asegurar que los argumentos incluyan org y project
parser.add_argument("--org", "-g", default=DEFAULT_ORG_URL, help="...")
parser.add_argument("--project", "-p", default=DEFAULT_PROJECT, help="...")
parser.add_argument("--output", "-o", choices=["json", "csv", "excel"], default=None, help="...")
parser.add_argument("--timezone", "-tz", default=DEFAULT_TIMEZONE, help="...")
```

---

## 🔄 Orden de Migración Recomendado

### Fase 1: AZDO (Semana 1)
```
Prioridad Alta (Herramientas más usadas):
1. pr_master_checker (Tool 1)
2. branch_policy_checker (Tool 2)
3. release_cd_health (Tool 3)
4. pipeline_drift (Tool 4)
5. release_deep_dive (Tool 5)

Prioridad Media:
6. task_validator (Tool 6)
7. pipeline_logs_scanner (Tool 7)
8. repo_vulnerabilities_scanner (Tool 8)
9. cicd_inventory (Tool 9)
10. gke_pipelines_inventory (Tool 10)
```

### Fase 2: AWS (Semana 2)
```
Todas las herramientas AWS (19 total)
- Todas ya tienen JSON/CSV
- Solo necesitan actualizar estructura
```

### Fase 3: GCP (Semana 3)
```
Herramientas con exportación (19 total)
- Agregar exportación a las que no tienen
- Actualizar estructura
```

### Fase 4: Terminal (Semana 4)
```
Agregar exportación a todas (6 total)
- Implementar export_json_simple
- Implementar export_csv_simple
```

---

## ✅ Validación

### Validar Estructura JSON

```python
def validate_json_structure(filepath):
    """Valida que un JSON tenga la estructura estandarizada"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Validar metadata
    assert "metadata" in data, "Falta 'metadata'"
    assert "tool" in data["metadata"], "Falta 'metadata.tool'"
    assert "version" in data["metadata"], "Falta 'metadata.version'"
    assert "generated_at" in data["metadata"], "Falta 'metadata.generated_at'"
    
    # Validar summary
    assert "summary" in data, "Falta 'summary'"
    assert "total" in data["summary"], "Falta 'summary.total'"
    assert "filtered" in data["summary"], "Falta 'summary.filtered'"
    assert "status" in data["summary"], "Falta 'summary.status'"
    
    # Validar data
    assert "data" in data, "Falta 'data'"
    assert isinstance(data["data"], list), "'data' debe ser un array"
    
    print(f"✅ {filepath} es válido")
```

### Validar Nombre de Archivo

```python
import re

def validate_filename(filename):
    """Valida que el nombre de archivo siga el patrón estandarizado"""
    pattern = r'^[a-z_]+_\d{8}_\d{6}\.(json|csv|xlsx)$'
    if re.match(pattern, filename):
        print(f"✅ {filename} es válido")
    else:
        print(f"❌ {filename} no cumple el patrón")
```

---

## 📊 Impacto Esperado

### Antes de Migración
```
- 45 herramientas con JSON inconsistente
- 4 patrones de nombres diferentes
- Procesamiento manual requerido
- Dificultad en análisis cruzado
```

### Después de Migración
```
- 45 herramientas con JSON consistente
- 1 patrón de nombres único
- Procesamiento automatizado posible
- Análisis cruzado facilitado
```

---

## 🔗 Referencias

- Módulo: `scm/export_manager.py`
- Guía: `GUIA_ESTANDARIZACION_JSON.md`
- Análisis: `ANALISIS_SALIDAS_OUTPUTS.md`

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
