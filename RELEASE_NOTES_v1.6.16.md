# 🚀 Release v1.6.16 - Tool 4 & Tool 38 Enhancements

**Fecha:** 8 de Julio de 2026  
**Versión:** 1.6.16 (Patch)  
**Estado:** ✅ PUBLICADO

---

## 📋 Resumen

Mejoras significativas en **Tool 4 (Service Account Checker)** y **Tool 38 (Service Accounts Multi-Project Reporter)** para soportar múltiples proyectos GCP con visualización profesional, procesamiento paralelo y carga automática desde `config.json`.

---

## ✨ Características Nuevas

### Tool 4: Service Account Checker - Múltiples Proyectos

#### Soporte para Múltiples Proyectos
- ✅ Carga automática de proyectos desde `config.json`
- ✅ Override con `--projects=proj1,proj2,proj3`
- ✅ Procesamiento paralelo con 5 workers
- ✅ Tabla de resultados por proyecto
- ✅ Spinner animado y barra de progreso

#### Carga desde config.json
```python
# Busca en: gcp.service_accounts_reporter.projects
# Ejemplo:
{
  "gcp": {
    "service_accounts_reporter": {
      "projects": [
        "cpl-cmanager-dev-13072023",
        "cpl-cmanager-qa-13072023",
        ...
      ]
    }
  }
}
```

#### Uso
```bash
# Opción 1: Cargar todos los proyectos de config.json (DEFECTO)
python scm/gcp/tools.py
# Seleccionar [4]

# Opción 2: Especificar proyectos manualmente
python scm/gcp/tools.py
# Seleccionar [4]
# Ingresar: cpl-cmanager-dev-13072023,cpl-cmanager-qa-13072023

# Opción 3: CLI directo
python scm/gcp/service-account/gcp_service_account_checker.py

# Opción 4: CLI con override
python scm/gcp/service-account/gcp_service_account_checker.py \
  --projects=cpl-cmanager-dev-13072023,cpl-cmanager-qa-13072023
```

---

### Tool 38: Service Accounts Multi-Project Reporter - Visualización

#### Visualización Profesional con Rich
- ✅ Spinners animados durante extracción
- ✅ Barra de progreso en tiempo real
- ✅ Tabla de extracción por proyecto
- ✅ Tabla de resumen final con duración
- ✅ Procesamiento paralelo (5 workers)
- ✅ Fallback a print() si Rich no disponible

#### Tabla de Resultados por Proyecto
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📊 Resumen de Extracción por Proyecto                             ┃
├──────────────────────────────────────────┬────────┬─────────────────┤
│ Proyecto                                 │ Estado │ Service Accounts │
├──────────────────────────────────────────┼────────┼─────────────────┤
│ cpl-cmanager-dev-13072023                │ ✅     │              12 │
│ cpl-cmanager-qa-13072023                 │ ✅     │               8 │
│ cpl-cmanager-stag-01052025               │ ✅     │               5 │
└──────────────────────────────────────────┴────────┴─────────────────┘
```

#### Tabla de Resumen Final
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📈 Resumen de Ejecución                                           ┃
├─────────────────────────┬─────────────────────────────────────────┤
│ Métrica                 │ Valor                                   │
├─────────────────────────┼─────────────────────────────────────────┤
│ Proyectos               │ 12                                      │
│ Service Accounts        │ 120                                     │
│ Roles                   │ 450                                     │
│ Duración                │ 8.42s                                   │
└─────────────────────────┴─────────────────────────────────────────┘
```

---

## 🔧 Cambios Técnicos

### Tool 4: gcp_service_account_checker.py

#### Nuevo Argumento
```python
parser.add_argument(
    "--projects",
    type=str,
    default="",
    help="Múltiples proyectos GCP separados por coma (ej: proj1,proj2,proj3)"
)
```

#### Nueva Función: load_projects_from_config()
```python
def load_projects_from_config(debug: bool, console) -> List[str]:
    """Carga proyectos desde config.json."""
    # Busca en múltiples ubicaciones
    # Lee: gcp.service_accounts_reporter.projects
    # Retorna lista de proyectos o []
```

#### Nueva Función: process_project()
```python
def process_project(project_id: str, debug: bool, console) -> List[Dict]:
    """Procesa un proyecto individual."""
    # Validar conexión
    # Obtener SAs y política IAM en paralelo
    # Analizar SAs
    # Retornar resultados
```

#### Lógica de Carga de Proyectos
```python
if args.projects:
    # Si se especifica --projects, usar solo esos
    projects = [p.strip() for p in args.projects.split(',') if p.strip()]
else:
    # Intentar cargar desde config.json
    projects = load_projects_from_config(debug, console)
    if not projects:
        # Fallback al proyecto por defecto
        projects = [args.project]
```

### Tool 38: gcp_sa_multi_project_reporter.py

#### Imports Rich Mejorados
```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.box import ROUNDED, HEAVY
```

#### Método: print_results_table()
```python
def print_results_table(self):
    """Imprime tabla de resultados con Rich."""
    # Crea tabla con columnas: Proyecto, Estado, Service Accounts
    # Muestra resultados de extracción
```

#### Procesamiento Paralelo Mejorado
```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console
) as progress:
    # Procesa múltiples proyectos en paralelo
    # Actualiza progreso en tiempo real
```

### tools.py: Integración

#### Cambio en Tool 4
```python
# Antes:
"args": ["--project", "-o"]

# Después:
"args": ["-o"]
```

**Razón:** Tool 4 ahora carga proyectos desde config.json automáticamente, no necesita preguntar por `--project`.

---

## 📊 Comparativa: Antes vs Después

| Característica | Antes | Después |
|---|---|---|
| **Tool 4: Un proyecto** | ✅ Sí | ✅ Sí |
| **Tool 4: Múltiples proyectos** | ❌ No | ✅ Sí (NUEVO) |
| **Tool 4: Carga desde config.json** | ❌ No | ✅ Sí (NUEVO) |
| **Tool 4: Spinners** | ✅ Sí | ✅ Sí |
| **Tool 4: Tabla de resultados** | ❌ No | ✅ Sí (NUEVO) |
| **Tool 38: Visualización Rich** | ❌ No | ✅ Sí (NUEVO) |
| **Tool 38: Tabla por proyecto** | ❌ No | ✅ Sí (NUEVO) |
| **Tool 38: Procesamiento paralelo** | ✅ Sí | ✅ Sí (MEJORADO) |

---

## 🎯 Casos de Uso

### Caso 1: Análisis de 12 Proyectos en Paralelo
```bash
python scm/gcp/tools.py
# Seleccionar [4]
# Resultado: Carga 12 proyectos desde config.json, procesa en paralelo
```

### Caso 2: Análisis de Proyectos Específicos
```bash
python scm/gcp/tools.py
# Seleccionar [4]
# Ingresar: cpl-cmanager-dev-13072023,cpl-cmanager-qa-13072023
# Resultado: Procesa solo esos 2 proyectos
```

### Caso 3: Reporte Multi-Proyecto con Tool 38
```bash
python scm/gcp/tools.py
# Seleccionar [38]
# Resultado: Carga 12 proyectos, genera reportes con visualización Rich
```

---

## 📝 Commits Incluidos

| Commit | Mensaje |
|--------|---------|
| `fd4d71e` | feat: Agregar visualización profesional con Rich a Tool 38 |
| `c64033f` | feat: Agregar soporte para múltiples proyectos a Tool 4 |
| `f3e68a5` | feat: Tool 4 carga proyectos desde config.json por defecto |
| `e19a373` | fix: Tool 4 no pregunta por proyecto, carga desde config.json |
| `cb56e33` | docs: Actualizar documentación para v1.6.16 |

---

## 🔄 Sincronización

✅ Sincronización exitosa con Azure DevOps:
- 7 archivos nuevos
- 4 archivos actualizados
- 208 archivos sin cambios
- Commit + push exitoso

---

## 📦 Instalación / Actualización

```bash
# Clonar o actualizar
git clone https://github.com/habolanos/devsecops-toolbox.git
cd devsecops-toolbox

# Checkout a v1.6.16
git checkout 1.6.16

# Instalar dependencias
pip install -r scm/requirements.txt
```

---

## ✅ Validación

- ✅ Tool 4 carga proyectos desde config.json
- ✅ Tool 4 permite override con --projects
- ✅ Tool 38 muestra visualización Rich
- ✅ Procesamiento paralelo funciona
- ✅ Tablas de resultados se muestran correctamente
- ✅ Fallback a print() sin Rich
- ✅ Sincronización con AzDO completada

---

## 📚 Documentación

- ✅ README.md actualizado
- ✅ README.version.md actualizado
- ✅ VERSION actualizado a 1.6.16
- ✅ RELEASE_NOTES_v1.6.16.md creado

---

## 🙏 Agradecimientos

Gracias por usar DevSecOps Toolbox. Para reportar problemas o sugerencias, por favor abre un issue en GitHub.

---

**Release v1.6.16 - Publicado el 8 de Julio de 2026**
