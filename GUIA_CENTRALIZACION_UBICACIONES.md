# 📁 Guía: Centralización de Ubicaciones de Archivos

**Fecha:** 25 de Junio de 2026  
**Objetivo:** Centralizar todas las salidas en `scm/outcome/` con estructura consistente

---

## 📋 Resumen Ejecutivo

### Problema Actual

```
4 Ubicaciones Diferentes:

Ubicación A: outcome/
  Herramientas: AZDO (mayoría)
  Ruta: {script_dir}/outcome/

Ubicación B: scm/outcome/
  Herramientas: Dashboard
  Ruta: scm/outcome/

Ubicación C: ./outcome/
  Herramientas: Algunos scripts
  Ruta: ./outcome/

Ubicación D: {script_dir}/outcome/
  Herramientas: Algunos scripts
  Ruta: {script_dir}/outcome/
```

### Solución

```
Ubicación Única: scm/outcome/

Estructura:
scm/outcome/
├─ azdo/
│  ├─ pr_master_20260625_180200.json
│  ├─ branch_policy_20260625_180200.json
│  └─ ...
├─ gcp/
│  ├─ gcp_service_account_20260625_180200.json
│  ├─ gcp_vpc_networks_20260625_180200.json
│  └─ ...
├─ aws/
│  ├─ aws_iam_users_20260625_180200.json
│  ├─ aws_eks_cluster_20260625_180200.json
│  └─ ...
├─ terminal/
│  ├─ terminal_tls_validator_20260625_180200.json
│  └─ ...
└─ dashboard/
   ├─ dashboard_data.json
   ├─ dashboard.html
   └─ history/
      ├─ 2026-06-25/
      │  ├─ dashboard_data_180200.json
      │  └─ dashboard.html
      └─ 2026-06-26/
         └─ ...
```

---

## 🔧 Módulo: output_manager.py

### Ubicación

```
scm/output_manager.py
```

### Características

```python
class OutputManager:
    """Gestor centralizado de ubicaciones"""
    
    def __init__(base_dir):
        """Inicializa con directorio base"""
    
    def get_output_dir(subdir):
        """Obtiene directorio de salida"""
    
    def get_platform_dir(platform):
        """Obtiene directorio de plataforma"""
    
    def get_dashboard_dir():
        """Obtiene directorio del dashboard"""
    
    def get_dashboard_history_dir():
        """Obtiene directorio de histórico"""
    
    def get_dashboard_history_date_dir(date):
        """Obtiene directorio de histórico por fecha"""
```

### Funciones Simplificadas

```python
# Obtener directorio de salida
get_output_dir(subdir="")

# Obtener directorio de plataforma
get_platform_dir(platform="azdo")

# Obtener directorio del dashboard
get_dashboard_dir()

# Obtener directorio de histórico
get_dashboard_history_dir()

# Obtener directorio de histórico por fecha
get_dashboard_history_date_dir(date_str="2026-06-25")
```

---

## 🚀 Cómo Usar output_manager.py

### Opción 1: Usar la Clase OutputManager

```python
from output_manager import OutputManager

# Crear instancia
manager = OutputManager()

# Obtener directorio de salida
output_dir = manager.get_output_dir()
# Resultado: Path('outcome')

# Obtener directorio de plataforma
azdo_dir = manager.get_platform_dir('azdo')
# Resultado: Path('outcome/azdo')

gcp_dir = manager.get_platform_dir('gcp')
# Resultado: Path('outcome/gcp')

aws_dir = manager.get_platform_dir('aws')
# Resultado: Path('outcome/aws')

# Obtener directorio del dashboard
dashboard_dir = manager.get_dashboard_dir()
# Resultado: Path('outcome/dashboard')

# Obtener directorio de histórico
history_dir = manager.get_dashboard_history_dir()
# Resultado: Path('outcome/dashboard/history')

# Obtener directorio de histórico por fecha
history_date_dir = manager.get_dashboard_history_date_dir('2026-06-25')
# Resultado: Path('outcome/dashboard/history/2026-06-25')
```

### Opción 2: Usar Funciones Simplificadas

```python
from output_manager import (
    get_output_dir,
    get_platform_dir,
    get_dashboard_dir,
    get_dashboard_history_dir,
    get_dashboard_history_date_dir
)

# Obtener directorio de salida
output_dir = get_output_dir()

# Obtener directorio de plataforma
azdo_dir = get_platform_dir('azdo')

# Obtener directorio del dashboard
dashboard_dir = get_dashboard_dir()

# Obtener directorio de histórico
history_dir = get_dashboard_history_dir()

# Obtener directorio de histórico por fecha
history_date_dir = get_dashboard_history_date_dir()  # Hoy
```

---

## 📝 Patrones de Migración

### Patrón 1: AZDO (outcome/)

```python
# ANTES
outcome_dir = str(get_output_dir("outcome"))
os.makedirs(outcome_dir, exist_ok=True)
filepath = os.path.join(outcome_dir, f"pr_master_{ts}.json")

# DESPUÉS
from output_manager import get_platform_dir
outcome_dir = get_platform_dir('azdo')
filepath = outcome_dir / f"pr_master_{ts}.json"
```

### Patrón 2: GCP (outcome/)

```python
# ANTES
outcome_dir = str(get_output_dir("outcome"))
os.makedirs(outcome_dir, exist_ok=True)
filepath = os.path.join(outcome_dir, f"gcp_service_account_{ts}.json")

# DESPUÉS
from output_manager import get_platform_dir
outcome_dir = get_platform_dir('gcp')
filepath = outcome_dir / f"gcp_service_account_{ts}.json"
```

### Patrón 3: AWS (outcome/)

```python
# ANTES
outcome_dir = str(get_output_dir("outcome"))
os.makedirs(outcome_dir, exist_ok=True)
filepath = os.path.join(outcome_dir, f"aws_iam_users_{ts}.json")

# DESPUÉS
from output_manager import get_platform_dir
outcome_dir = get_platform_dir('aws')
filepath = outcome_dir / f"aws_iam_users_{ts}.json"
```

### Patrón 4: Terminal (outcome/)

```python
# ANTES
outcome_dir = str(get_output_dir("outcome"))
os.makedirs(outcome_dir, exist_ok=True)
filepath = os.path.join(outcome_dir, f"terminal_tls_validator_{ts}.json")

# DESPUÉS
from output_manager import get_platform_dir
outcome_dir = get_platform_dir('terminal')
filepath = outcome_dir / f"terminal_tls_validator_{ts}.json"
```

### Patrón 5: Dashboard

```python
# ANTES
output_dir = get_output_dir("outcome/dashboard")
dashboard_file = output_dir / "dashboard_data.json"
html_file = output_dir / "dashboard.html"

# DESPUÉS
from output_manager import get_dashboard_dir
output_dir = get_dashboard_dir()
dashboard_file = output_dir / "dashboard_data.json"
html_file = output_dir / "dashboard.html"
```

### Patrón 6: Dashboard History

```python
# ANTES
history_dir = get_output_dir("outcome/dashboard/history")
date_dir = history_dir / "2026-06-25"
history_file = date_dir / "dashboard_data_180200.json"

# DESPUÉS
from output_manager import get_dashboard_history_date_dir
date_dir = get_dashboard_history_date_dir("2026-06-25")
history_file = date_dir / "dashboard_data_180200.json"
```

---

## 📋 Checklist de Migración

### Paso 1: Agregar Import

```python
# Agregar al inicio del archivo
from output_manager import get_platform_dir, get_output_dir
```

### Paso 2: Actualizar export_results

```python
# ANTES
def export_results(rows, output_format):
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"tool_name_{ts}.json")

# DESPUÉS
def export_results(rows, output_format):
    outcome_dir = get_platform_dir('azdo')  # o 'gcp', 'aws', 'terminal'
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = outcome_dir / f"tool_name_{ts}.json"
```

### Paso 3: Actualizar Rutas

```python
# ANTES
filepath = os.path.join(outcome_dir, f"tool_name_{ts}.json")
with open(filepath, "w") as f:
    json.dump(data, f)

# DESPUÉS
filepath = outcome_dir / f"tool_name_{ts}.json"
with open(filepath, "w") as f:
    json.dump(data, f)
```

### Paso 4: Validación

```bash
# Verificar estructura de directorios
ls -la scm/outcome/
# Resultado:
# drwxr-xr-x  azdo/
# drwxr-xr-x  gcp/
# drwxr-xr-x  aws/
# drwxr-xr-x  terminal/
# drwxr-xr-x  dashboard/
```

---

## 🔄 Orden de Migración

### Fase 1: Dashboard (Semana 1)

```
Archivos a actualizar:
1. scm/dashboard/run_dashboard.py
2. scm/dashboard/dashboard_consolidator.py
3. scm/dashboard/dashboard_generator.py
4. scm/dashboard/dashboard_scheduler.py

Cambios:
- Usar get_dashboard_dir()
- Usar get_dashboard_history_date_dir()
- Actualizar rutas de lectura/escritura

Tiempo: 4 horas
```

### Fase 2: AZDO (Semana 1-2)

```
Archivos a actualizar: 27 herramientas

Cambios:
- Usar get_platform_dir('azdo')
- Actualizar rutas de lectura/escritura
- Actualizar export_results

Tiempo: 27 horas (1 hora por herramienta)
```

### Fase 3: GCP (Semana 2-3)

```
Archivos a actualizar: 22 herramientas

Cambios:
- Usar get_platform_dir('gcp')
- Actualizar rutas de lectura/escritura
- Actualizar export_results

Tiempo: 22 horas (1 hora por herramienta)
```

### Fase 4: AWS (Semana 3-4)

```
Archivos a actualizar: 19 herramientas

Cambios:
- Usar get_platform_dir('aws')
- Actualizar rutas de lectura/escritura
- Actualizar export_results

Tiempo: 19 horas (1 hora por herramienta)
```

### Fase 5: Terminal (Semana 4)

```
Archivos a actualizar: 6 herramientas

Cambios:
- Usar get_platform_dir('terminal')
- Actualizar rutas de lectura/escritura
- Actualizar export_results

Tiempo: 6 horas (1 hora por herramienta)
```

---

## 📊 Estructura Final

### Árbol de Directorios

```
scm/outcome/
├─ azdo/
│  ├─ pr_master_20260625_180200.json
│  ├─ pr_master_20260625_180200.csv
│  ├─ pr_master_20260625_180200.xlsx
│  ├─ branch_policy_20260625_180200.json
│  ├─ branch_policy_20260625_180200.csv
│  ├─ branch_policy_20260625_180200.xlsx
│  ├─ release_cd_health_20260625_180200.json
│  ├─ release_cd_health_20260625_180200.csv
│  ├─ release_cd_health_20260625_180200.xlsx
│  └─ ... (27 herramientas)
├─ gcp/
│  ├─ gcp_service_account_20260625_180200.json
│  ├─ gcp_service_account_20260625_180200.csv
│  ├─ gcp_service_account_20260625_180200.xlsx
│  ├─ gcp_vpc_networks_20260625_180200.json
│  ├─ gcp_vpc_networks_20260625_180200.csv
│  ├─ gcp_vpc_networks_20260625_180200.xlsx
│  └─ ... (22 herramientas)
├─ aws/
│  ├─ aws_iam_users_20260625_180200.json
│  ├─ aws_iam_users_20260625_180200.csv
│  ├─ aws_iam_users_20260625_180200.xlsx
│  ├─ aws_eks_cluster_20260625_180200.json
│  ├─ aws_eks_cluster_20260625_180200.csv
│  ├─ aws_eks_cluster_20260625_180200.xlsx
│  └─ ... (19 herramientas)
├─ terminal/
│  ├─ terminal_tls_validator_20260625_180200.json
│  ├─ terminal_tls_validator_20260625_180200.csv
│  └─ ... (6 herramientas)
└─ dashboard/
   ├─ dashboard_data.json
   ├─ dashboard.html
   └─ history/
      ├─ 2026-06-25/
      │  ├─ dashboard_data_180200.json
      │  └─ dashboard.html
      ├─ 2026-06-26/
      │  ├─ dashboard_data_180200.json
      │  └─ dashboard.html
      └─ ...
```

---

## ✅ Validación

### Checklist

```
[ ] Todos los imports actualizados
[ ] Todas las rutas actualizadas
[ ] Todos los directorios creados
[ ] Todos los archivos en ubicación correcta
[ ] Tests pasan
[ ] Documentación actualizada
[ ] .gitignore actualizado
```

### Comando de Validación

```bash
# Verificar estructura
find scm/outcome -type f | head -20

# Contar archivos por plataforma
echo "AZDO: $(find scm/outcome/azdo -type f 2>/dev/null | wc -l)"
echo "GCP: $(find scm/outcome/gcp -type f 2>/dev/null | wc -l)"
echo "AWS: $(find scm/outcome/aws -type f 2>/dev/null | wc -l)"
echo "Terminal: $(find scm/outcome/terminal -type f 2>/dev/null | wc -l)"
echo "Dashboard: $(find scm/outcome/dashboard -type f 2>/dev/null | wc -l)"
```

---

## 🔗 Referencias

- Módulo: `scm/output_manager.py`
- Módulo: `scm/export_manager.py`
- Guía: `GUIA_ESTANDARIZACION_JSON.md`

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
