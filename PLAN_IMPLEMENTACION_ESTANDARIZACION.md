# 📋 Plan de Implementación - Estandarización JSON y Nombres de Archivos

**Fecha:** 25 de Junio de 2026  
**Objetivo:** Implementar estandarización en todas las herramientas (76 total)  
**Duración Estimada:** 4 semanas  
**Esfuerzo Estimado:** 80 horas

---

## 📊 Resumen Ejecutivo

### Alcance

```
Herramientas a Migrar: 76
├─ AZDO:     27 (Semana 1)
├─ AWS:      19 (Semana 2)
├─ GCP:      22 (Semana 3)
└─ Terminal:  6 (Semana 4)

Cambios por Herramienta:
├─ Actualizar imports
├─ Reemplazar función export_results
├─ Actualizar argumentos
├─ Actualizar llamadas
└─ Agregar tests
```

### Recursos Disponibles

```
Módulo Centralizado: scm/export_manager.py
Guía de Implementación: GUIA_ESTANDARIZACION_JSON.md
Validadores: Incluidos en guía
```

---

## 🗓️ Cronograma Detallado

### Semana 1: AZDO (27 herramientas)

#### Día 1-2: Herramientas Críticas (5)

```
1. pr_master_checker (Tool 1)
   - Archivo: azdo_pr_master_checker.py
   - Líneas a cambiar: ~50
   - Tiempo: 1 hora
   - Prioridad: CRÍTICA

2. branch_policy_checker (Tool 2)
   - Archivo: azdo_branch_policy_checker.py
   - Líneas a cambiar: ~50
   - Tiempo: 1 hora
   - Prioridad: CRÍTICA

3. release_cd_health (Tool 3)
   - Archivo: azdo_release_cd_health.py
   - Líneas a cambiar: ~60
   - Tiempo: 1.5 horas
   - Prioridad: CRÍTICA

4. pipeline_drift (Tool 4)
   - Archivo: azdo_pipeline_drift.py
   - Líneas a cambiar: ~60
   - Tiempo: 1.5 horas
   - Prioridad: CRÍTICA

5. release_deep_dive (Tool 5)
   - Archivo: azdo_release_deep_dive.py
   - Líneas a cambiar: ~40
   - Tiempo: 1 hora
   - Prioridad: CRÍTICA

Subtotal Día 1-2: 6 horas
```

#### Día 3-4: Herramientas Secundarias (10)

```
6. task_validator (Tool 6)
   - Tiempo: 1 hora

7. pipeline_logs_scanner (Tool 7)
   - Tiempo: 1 hora

8. repo_vulnerabilities_scanner (Tool 8)
   - Tiempo: 1 hora

9. cicd_inventory (Tool 9)
   - Tiempo: 1.5 horas

10. gke_pipelines_inventory (Tool 10)
    - Tiempo: 1.5 horas

11. pending_approvals (Tool 11)
    - Tiempo: 1 hora

12. branches_created (Tool 12)
    - Tiempo: 1 hora

13. hotfix_branches_inventory (Tool 13)
    - Tiempo: 1 hora

14. ci_pipeline_inventory (Tool 14)
    - Tiempo: 1.5 horas

15. cd_pipeline_inventory (Tool 15)
    - Tiempo: 1.5 horas

Subtotal Día 3-4: 12 horas
```

#### Día 5: Herramientas Restantes (12)

```
16. pipeline_health_score (Tool 16)
    - Tiempo: 1.5 horas

17. prod_deploy_inventory (Tool 17)
    - Tiempo: 1 hora

18. pipeline_status (Tool 18)
    - Tiempo: 1.5 horas

19. release_explorer (Tool 19)
    - Tiempo: 1 hora

20. properties_branch_diff (Tool 20)
    - Tiempo: 1 hora

21. repo_branch_diff (Tool 21)
    - Tiempo: 1 hora

22. release_rollback (Tool 22)
    - Tiempo: 1 hora

23. release_restore (Tool 23)
    - Tiempo: 1 hora

24. release_cd_rollback (Tool 24)
    - Tiempo: 1 hora

25. release_cd_update (Tool 25)
    - Tiempo: 1 hora

26. (Ejecutar Todos) (Tool A)
    - Tiempo: 0.5 horas

27. (Ejecutar Todo + JSON) (Tool B)
    - Tiempo: 0.5 horas

Subtotal Día 5: 12.5 horas

Total Semana 1: 30.5 horas
```

---

### Semana 2: AWS (19 herramientas)

#### Día 1-2: Herramientas Críticas (5)

```
1. aws_iam_users_policies_checker (Tool 1)
   - Tiempo: 1 hora

2. aws_iam_roles_checker (Tool 2)
   - Tiempo: 1 hora

3. aws_rds_instance_checker (Tool 4)
   - Tiempo: 1 hora

4. aws_vpc_networks_checker (Tool 6)
   - Tiempo: 1 hora

5. aws_eks_cluster_checker (Tool 9)
   - Tiempo: 1 hora

Subtotal Día 1-2: 5 horas
```

#### Día 3-5: Herramientas Restantes (14)

```
6. aws_acm_certificate_checker (Tool 3)
   - Tiempo: 1 hora

7. aws_rds_storage_monitor (Tool 5)
   - Tiempo: 1 hora

8. aws_security_groups_checker (Tool 7)
   - Tiempo: 1 hora

9. aws_load_balancer_checker (Tool 8)
   - Tiempo: 1 hora

10. aws_ecr_repository_checker (Tool 10)
    - Tiempo: 1 hora

11. aws_ec2_instances_checker (Tool 11)
    - Tiempo: 1 hora

12. aws_lambda_functions_checker (Tool 12)
    - Tiempo: 1 hora

13. aws_cloudwatch_alarms_checker (Tool 13)
    - Tiempo: 1 hora

14. aws_ebs_volume_checker (Tool 14)
    - Tiempo: 1 hora

15. aws_eks_pod_monitor (Tool 15)
    - Tiempo: 1 hora

16. aws_eks_node_monitor (Tool 16)
    - Tiempo: 1 hora

17. aws_secrets_manager_checker (Tool 17)
    - Tiempo: 1 hora

18. aws_waf_web_acl_checker (Tool 18)
    - Tiempo: 1 hora

19. aws_inventory_generator (Tool 19)
    - Tiempo: 1.5 horas

Subtotal Día 3-5: 16.5 horas

Total Semana 2: 21.5 horas
```

---

### Semana 3: GCP (22 herramientas)

#### Día 1-2: Herramientas con Exportación (10)

```
Herramientas que ya tienen JSON/CSV:
- gcp_service_account_checker (Tool 4)
- gcp_certificate_manager_checker (Tool 5)
- gcp_cloud_armor_checker (Tool 6)
- gcp_cloud_sql_disk_monitor (Tool 7)
- gcp_cloud_sql_database_checker (Tool 8)
- gcp_cloud_sql_comparator (Tool 9)
- gcp_vpc_networks_checker (Tool 10)
- gcp_gateway_services_checker (Tool 11)
- gcp_load_balancer_checker (Tool 12)
- gcp_ip_addresses_checker (Tool 13)

Tiempo por herramienta: 1 hora
Subtotal: 10 horas
```

#### Día 3-4: Herramientas sin Exportación (10)

```
Herramientas que solo tienen tabla:
- gcp_monitor_resources (Tool 1)
- gcp_gke_deployments_report (Tool 2)
- gcp_iam_roles_report (Tool 3)
- gcp_gke_cluster_checker (Tool 14)
- gcp_secrets_configmaps_checker (Tool 15)
- gcp_pod_connectivity_checker (Tool 16)
- gcp_gke_workload_analyzer (Tool 17)
- gcp_gke_pod_disruption_budgets (Tool 18)
- gcp_gke_network_policies (Tool 19)
- gcp_gke_rbac_analyzer (Tool 20)

Tiempo por herramienta: 1.5 horas (incluye agregar exportación)
Subtotal: 15 horas
```

#### Día 5: Herramientas con HTML (2)

```
- gcp_gke_node_resources_monitor (Tool 24)
  - Tiempo: 1 hora

- gcp_gke_pod_resources_monitor (Tool 25)
  - Tiempo: 1 hora

Subtotal: 2 horas

Total Semana 3: 27 horas
```

---

### Semana 4: Terminal (6 herramientas)

#### Día 1-5: Agregar Exportación (6)

```
Todas las herramientas Terminal necesitan exportación:

1. terminal_tls_certificate_validator
   - Agregar export_json_simple
   - Agregar export_csv_simple
   - Tiempo: 1.5 horas

2. terminal_database_connection_tester
   - Tiempo: 1.5 horas

3. terminal_kubernetes_manifest_diff
   - Tiempo: 1.5 horas

4. terminal_kubernetes_deployment_validator
   - Tiempo: 1.5 horas

5. terminal_docker_image_validator
   - Tiempo: 1.5 horas

6. terminal_git_repository_validator
   - Tiempo: 1.5 horas

Total Semana 4: 9 horas
```

---

## 📋 Checklist de Implementación por Herramienta

### Plantilla de Checklist

```markdown
## [ ] {tool_name}

**Archivo:** {path_to_file}
**Tiempo Estimado:** {hours} horas
**Prioridad:** {HIGH|MEDIUM|LOW}

### Cambios Requeridos

- [ ] Agregar import de export_manager
- [ ] Actualizar función export_results
- [ ] Actualizar argumentos (--org, --project)
- [ ] Actualizar llamadas a export_results
- [ ] Actualizar tests (si existen)
- [ ] Validar estructura JSON
- [ ] Validar nombres de archivos
- [ ] Crear commit

### Validación

- [ ] JSON válido
- [ ] CSV válido
- [ ] Excel válido (si aplica)
- [ ] Nombres de archivos correctos
- [ ] Ubicación correcta (scm/outcome/)
- [ ] Tests pasan

### Notas

{additional_notes}
```

---

## 🔄 Proceso de Migración Estándar

### Paso 1: Preparación (5 minutos)

```bash
# 1. Crear rama de feature
git checkout -b feat/estandarizar-{tool_name}

# 2. Abrir archivo
# scm/{platform}/{tool_file}.py
```

### Paso 2: Actualizar Imports (2 minutos)

```python
# Agregar al inicio del archivo
from export_manager import ExportManager
```

### Paso 3: Reemplazar export_results (15 minutos)

```python
# Reemplazar función completa con:
def export_results(rows, output_format, organization, project, timezone):
    manager = ExportManager("{tool_name}", __version__)
    
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
        return manager.export_excel(rows, sheet_name="Data")
```

### Paso 4: Actualizar Argumentos (5 minutos)

```python
# Asegurar que existan estos argumentos
parser.add_argument("--org", "-g", default=DEFAULT_ORG_URL, help="...")
parser.add_argument("--project", "-p", default=DEFAULT_PROJECT, help="...")
parser.add_argument("--output", "-o", choices=["json", "csv", "excel"], default=None, help="...")
parser.add_argument("--timezone", "-tz", default=DEFAULT_TIMEZONE, help="...")
```

### Paso 5: Actualizar Llamadas (10 minutos)

```python
# Buscar y reemplazar llamadas a export_results
# ANTES:
if args.output:
    filepath = export_results(rows, args.output, script_dir, ...)

# DESPUÉS:
if args.output:
    filepath = export_results(rows, args.output, args.org, args.project, tz_name)
```

### Paso 6: Validación (10 minutos)

```bash
# 1. Ejecutar herramienta
python {tool_file}.py --pat <PAT> --org <ORG> --project <PROJECT> --output json

# 2. Validar JSON
python -c "
import json
with open('outcome/{tool_name}_*.json') as f:
    data = json.load(f)
    assert 'metadata' in data
    assert 'summary' in data
    assert 'data' in data
    print('✅ JSON válido')
"

# 3. Validar nombre de archivo
# Debe ser: {tool_name}_YYYYMMDD_HHMMSS.json
```

### Paso 7: Commit (5 minutos)

```bash
git add scm/{platform}/{tool_file}.py
git commit -m "feat: Estandarizar exportación de {tool_name}

- Usar export_manager para JSON/CSV/Excel
- Estructura JSON estandarizada
- Nombres de archivos estandarizados
- Metadata consistente (tool, version, generated_at, org, project)
- Summary consistente (total, filtered, status)"
```

---

## 📊 Métricas de Progreso

### Semana 1: AZDO

```
Día 1: 5 herramientas (18%)
Día 2: 10 herramientas (37%)
Día 3: 15 herramientas (56%)
Día 4: 20 herramientas (74%)
Día 5: 27 herramientas (100%)

Commits esperados: 5-7
```

### Semana 2: AWS

```
Día 1: 5 herramientas (26%)
Día 2: 10 herramientas (53%)
Día 3: 15 herramientas (79%)
Día 4: 19 herramientas (100%)

Commits esperados: 4-5
```

### Semana 3: GCP

```
Día 1: 5 herramientas (23%)
Día 2: 10 herramientas (45%)
Día 3: 15 herramientas (68%)
Día 4: 20 herramientas (91%)
Día 5: 22 herramientas (100%)

Commits esperados: 5-6
```

### Semana 4: Terminal

```
Día 1: 2 herramientas (33%)
Día 2: 4 herramientas (67%)
Día 3: 6 herramientas (100%)

Commits esperados: 2-3
```

---

## ✅ Validación Final

### Checklist de Completitud

```
[ ] Todas las 76 herramientas migradas
[ ] Todos los JSON tienen estructura estándar
[ ] Todos los nombres de archivos siguen patrón
[ ] Todos los archivos en scm/outcome/
[ ] Tests pasan (si existen)
[ ] Documentación actualizada
[ ] README actualizado con cambios
[ ] Versión bumped a patch (ej: 1.6.13)
```

### Validación de Estructura

```bash
# Script para validar todas las herramientas
for json_file in outcome/*.json; do
    python -c "
    import json
    with open('$json_file') as f:
        data = json.load(f)
        assert 'metadata' in data, 'Falta metadata'
        assert 'summary' in data, 'Falta summary'
        assert 'data' in data, 'Falta data'
        print('✅ $json_file')
    "
done
```

---

## 📝 Documentación a Actualizar

### README.md

```markdown
## Exportación de Datos

Todas las herramientas soportan exportación a JSON, CSV y Excel con estructura estandarizada.

### Estructura JSON

```json
{
  "metadata": {
    "tool": "nombre_herramienta",
    "version": "1.0.0",
    "generated_at": "ISO timestamp",
    "organization": "org_name",
    "project": "project_name"
  },
  "summary": {
    "total": N,
    "filtered": N,
    "status": "success"
  },
  "data": [...]
}
```

### Nombres de Archivos

Patrón: `{tool_name}_{timestamp}.{format}`

Ejemplo: `pr_master_checker_20260625_180200.json`

### Ubicación

Todos los archivos se guardan en: `scm/outcome/`

### Uso de export_manager

```python
from export_manager import ExportManager

manager = ExportManager("tool_name", "1.0.0")
json_file = manager.export_json(data, organization="org", project="project")
csv_file = manager.export_csv(data)
excel_file = manager.export_excel(data)
```
```

---

## 🎯 Objetivos Finales

```
Después de la Implementación:

✅ 76 herramientas con JSON estandarizado
✅ 76 herramientas con nombres de archivos consistentes
✅ 76 herramientas con ubicación centralizada
✅ Procesamiento automatizado posible
✅ Análisis cruzado facilitado
✅ Mantenimiento simplificado
✅ Documentación completa
```

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
