# 📊 Guía: Agregar Excel a GCP/AWS

**Fecha:** 25 de Junio de 2026  
**Objetivo:** Agregar soporte Excel a todas las herramientas GCP/AWS que no lo tienen

---

## 📋 Resumen Ejecutivo

### Alcance

```
Herramientas sin Excel:
├─ GCP: 20 herramientas (Tools 4-23)
└─ AWS: 16 herramientas (Tools 1-14, 17-18)

Total: 36 herramientas
Tiempo estimado: 36 horas (1 hora por herramienta)
```

### Cambios Requeridos

```
1. Agregar pandas y openpyxl como dependencias
2. Actualizar argumentos (--output con "excel")
3. Agregar lógica de exportación a Excel
4. Actualizar función export_results
5. Agregar validación
```

---

## 🔧 Dependencias Requeridas

### Instalación

```bash
pip install pandas openpyxl
```

### Versiones Recomendadas

```
pandas>=1.3.0
openpyxl>=3.6.0
```

### Verificación

```bash
python -c "import pandas; import openpyxl; print('✅ Dependencias instaladas')"
```

---

## 📝 Patrón de Implementación

### Paso 1: Actualizar Argumentos

```python
# ANTES
parser.add_argument("--output", "-o", choices=["json", "csv"], default=None,
                    help="Exportar resultados")

# DESPUÉS
parser.add_argument("--output", "-o", choices=["json", "csv", "excel"], default=None,
                    help="Exportar resultados (json / csv / excel)")
```

### Paso 2: Actualizar Función export_results

```python
# ANTES
def export_results(rows, output_format):
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        # ... lógica JSON
    elif output_format == "csv":
        # ... lógica CSV

# DESPUÉS
def export_results(rows, output_format):
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        # ... lógica JSON
    elif output_format == "csv":
        # ... lógica CSV
    elif output_format == "excel":
        try:
            import pandas as pd
            filepath = os.path.join(outcome_dir, f"tool_name_{ts}.xlsx")
            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False, engine="openpyxl", sheet_name="Data")
            return filepath
        except ImportError:
            print("ERROR: Instala pandas y openpyxl para exportar a Excel.")
            return None
```

### Paso 3: Agregar Validación

```python
# En la función main()
if args.output:
    filepath = export_results(rows, args.output)
    if filepath:
        msg = f"📁 Exportado: {filepath}"
        print(msg)
    else:
        print("⚠️  Error al exportar")
```

---

## 🎨 Mejoras Opcionales: Formato Excel Avanzado

### Opción 1: Formato Básico (Recomendado)

```python
import pandas as pd

filepath = os.path.join(outcome_dir, f"tool_name_{ts}.xlsx")
df = pd.DataFrame(rows)
df.to_excel(filepath, index=False, engine="openpyxl", sheet_name="Data")
```

### Opción 2: Con Múltiples Hojas

```python
import pandas as pd

filepath = os.path.join(outcome_dir, f"tool_name_{ts}.xlsx")

with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
    # Hoja principal
    df_main = pd.DataFrame(rows)
    df_main.to_excel(writer, sheet_name="Data", index=False)
    
    # Hoja de resumen
    summary_data = {
        "Metric": ["Total", "Filtered", "Status"],
        "Value": [len(rows), len(rows), "success"]
    }
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
```

### Opción 3: Con Formato y Estilos

```python
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill

filepath = os.path.join(outcome_dir, f"tool_name_{ts}.xlsx")

# Crear Excel
df = pd.DataFrame(rows)
df.to_excel(filepath, index=False, engine="openpyxl", sheet_name="Data")

# Aplicar formato
wb = load_workbook(filepath)
ws = wb["Data"]

# Encabezados
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF")

for cell in ws[1]:
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center")

# Ancho de columnas
for column in ws.columns:
    max_length = 0
    column_letter = column[0].column_letter
    for cell in column:
        try:
            if len(str(cell.value)) > max_length:
                max_length = len(str(cell.value))
        except:
            pass
    adjusted_width = min(max_length + 2, 50)
    ws.column_dimensions[column_letter].width = adjusted_width

wb.save(filepath)
```

---

## 📋 Checklist por Herramienta

### GCP (20 herramientas)

```
[ ] gcp_service_account_checker (Tool 4)
[ ] gcp_certificate_manager_checker (Tool 5)
[ ] gcp_cloud_armor_checker (Tool 6)
[ ] gcp_cloud_sql_disk_monitor (Tool 7)
[ ] gcp_cloud_sql_database_checker (Tool 8)
[ ] gcp_cloud_sql_comparator (Tool 9)
[ ] gcp_vpc_networks_checker (Tool 10)
[ ] gcp_gateway_services_checker (Tool 11)
[ ] gcp_load_balancer_checker (Tool 12)
[ ] gcp_ip_addresses_checker (Tool 13)
[ ] gcp_gke_cluster_checker (Tool 14)
[ ] gcp_secrets_configmaps_checker (Tool 15)
[ ] gcp_pod_connectivity_checker (Tool 16)
[ ] gcp_gke_workload_analyzer (Tool 17)
[ ] gcp_gke_pod_disruption_budgets (Tool 18)
[ ] gcp_gke_network_policies (Tool 19)
[ ] gcp_gke_rbac_analyzer (Tool 20)
[ ] gcp_gke_node_resources_monitor (Tool 24)
[ ] gcp_gke_pod_resources_monitor (Tool 25)
[ ] gcp_monitor_resources (Tool 1) - Agregar exportación completa
```

### AWS (16 herramientas)

```
[ ] aws_iam_users_policies_checker (Tool 1)
[ ] aws_iam_roles_checker (Tool 2)
[ ] aws_acm_certificate_checker (Tool 3)
[ ] aws_rds_instance_checker (Tool 4)
[ ] aws_rds_storage_monitor (Tool 5)
[ ] aws_vpc_networks_checker (Tool 6)
[ ] aws_security_groups_checker (Tool 7)
[ ] aws_load_balancer_checker (Tool 8)
[ ] aws_eks_cluster_checker (Tool 9)
[ ] aws_ecr_repository_checker (Tool 10)
[ ] aws_ec2_instances_checker (Tool 11)
[ ] aws_lambda_functions_checker (Tool 12)
[ ] aws_cloudwatch_alarms_checker (Tool 13)
[ ] aws_ebs_volume_checker (Tool 14)
[ ] aws_secrets_manager_checker (Tool 17)
[ ] aws_waf_web_acl_checker (Tool 18)
```

---

## 🔄 Proceso de Implementación

### Tiempo por Herramienta: 1 hora

```
1. Actualizar argumentos (5 min)
2. Agregar lógica Excel (15 min)
3. Validación (10 min)
4. Testing (20 min)
5. Commit (10 min)
```

### Orden Recomendado

#### Fase 1: GCP (Semana 1)

```
Día 1: Tools 4-8 (5 herramientas)
Día 2: Tools 9-13 (5 herramientas)
Día 3: Tools 14-20 (7 herramientas)
Día 4: Tools 24-25 + Tool 1 (3 herramientas)

Total: 20 herramientas, 20 horas
```

#### Fase 2: AWS (Semana 2)

```
Día 1: Tools 1-5 (5 herramientas)
Día 2: Tools 6-10 (5 herramientas)
Día 3: Tools 11-14 (4 herramientas)
Día 4: Tools 17-18 (2 herramientas)

Total: 16 herramientas, 16 horas
```

---

## 📝 Plantilla de Cambios

### Archivo: gcp_service_account_checker.py

```python
# ANTES
def get_args():
    parser.add_argument("--output", "-o", choices=["json", "csv"], default=None,
                        help="Exportar resultados")
    return parser.parse_args()

def export_results(rows, output_format):
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"gcp_service_account_{ts}.json")
        # ... lógica JSON
        return filepath
    elif output_format == "csv":
        filepath = os.path.join(outcome_dir, f"gcp_service_account_{ts}.csv")
        # ... lógica CSV
        return filepath

# DESPUÉS
def get_args():
    parser.add_argument("--output", "-o", choices=["json", "csv", "excel"], default=None,
                        help="Exportar resultados (json / csv / excel)")
    return parser.parse_args()

def export_results(rows, output_format):
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"gcp_service_account_{ts}.json")
        # ... lógica JSON
        return filepath
    elif output_format == "csv":
        filepath = os.path.join(outcome_dir, f"gcp_service_account_{ts}.csv")
        # ... lógica CSV
        return filepath
    elif output_format == "excel":
        try:
            import pandas as pd
            filepath = os.path.join(outcome_dir, f"gcp_service_account_{ts}.xlsx")
            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False, engine="openpyxl", sheet_name="Service Accounts")
            return filepath
        except ImportError:
            print("ERROR: Instala pandas y openpyxl para exportar a Excel.")
            return None
```

---

## 🧪 Testing

### Test Manual

```bash
# 1. Ejecutar herramienta con --output excel
python gcp_service_account_checker.py \
    --pat <PAT> \
    --org <ORG> \
    --project <PROJECT> \
    --output excel

# 2. Verificar que el archivo se creó
ls -la outcome/*.xlsx

# 3. Abrir en Excel o validar con Python
python -c "
import openpyxl
wb = openpyxl.load_workbook('outcome/gcp_service_account_*.xlsx')
print(f'✅ Excel válido: {wb.sheetnames}')
"
```

### Test Automatizado

```python
import os
import openpyxl
from pathlib import Path

def test_excel_export():
    # Ejecutar herramienta
    os.system('python gcp_service_account_checker.py --pat <PAT> --output excel')
    
    # Buscar archivo
    excel_files = list(Path('outcome').glob('gcp_service_account_*.xlsx'))
    assert len(excel_files) > 0, "No se encontró archivo Excel"
    
    # Validar estructura
    wb = openpyxl.load_workbook(excel_files[0])
    assert 'Service Accounts' in wb.sheetnames, "Falta hoja de datos"
    
    # Validar datos
    ws = wb['Service Accounts']
    assert ws.max_row > 1, "No hay datos en la hoja"
    
    print("✅ Test Excel pasado")

if __name__ == "__main__":
    test_excel_export()
```

---

## 📊 Impacto

### Antes

```
GCP:
├─ JSON: 19 herramientas
├─ CSV: 19 herramientas
└─ Excel: 0 herramientas

AWS:
├─ JSON: 19 herramientas
├─ CSV: 19 herramientas
└─ Excel: 1 herramienta
```

### Después

```
GCP:
├─ JSON: 19 herramientas
├─ CSV: 19 herramientas
└─ Excel: 20 herramientas ✅

AWS:
├─ JSON: 19 herramientas
├─ CSV: 19 herramientas
└─ Excel: 19 herramientas ✅
```

### Beneficios

```
✅ Paridad con AZDO (todas tienen Excel)
✅ Mejor experiencia de usuario
✅ Análisis en Excel facilitado
✅ Compatibilidad total
✅ Consistencia en todas las plataformas
```

---

## 📋 Validación Final

### Checklist

```
[ ] Todos los argumentos actualizados
[ ] Todas las funciones export_results actualizadas
[ ] Todos los Excel se crean correctamente
[ ] Todos los nombres de archivos son consistentes
[ ] Todos los archivos en outcome/
[ ] Tests pasan
[ ] Documentación actualizada
[ ] Commits realizados
```

### Comando de Validación

```bash
# Verificar que todas las herramientas generan Excel
for tool in gcp_service_account_checker aws_iam_users_policies_checker; do
    python scm/$platform/$tool.py --pat <PAT> --output excel
    if [ -f "outcome/${tool}_*.xlsx" ]; then
        echo "✅ $tool"
    else
        echo "❌ $tool"
    fi
done
```

---

## 🔗 Referencias

- Módulo: `scm/export_manager.py`
- Módulo: `scm/output_manager.py`
- Guía: `GUIA_ESTANDARIZACION_JSON.md`

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
