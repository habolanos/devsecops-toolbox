# Azure DevOps Tools — SCM Toolbox

**21 herramientas Python** para auditoría, análisis y gestión de pipelines, políticas de ramas y pull requests en **Azure DevOps**. Incluye **Pipeline Updater Template (Tool 41)** y **Pipeline Rollback** con 3 métodos de restauración. Todas las herramientas usan la API REST de AzDO v7.2 con autenticación por PAT y ofrecen salida enriquecida en consola (Rich) y exportación a JSON / CSV / Excel.

---

## Contenido del directorio

```
devsecops-toolbox/scm/azdo/
├── tools.py                       # Launcher interactivo unificado v1.3.4 (21 herramientas)
├── azdo_pr_master_checker.py      # Herramienta 1 — PRs hacia master + validación CD
├── azdo_pr_pipeline_analyzer.py   # Herramienta 1b — Análisis PRs multi-rama + CD + releases
├── azdo_branch_policy_checker.py  # Herramienta 2 — Auditoría de políticas de ramas
├── azdo_release_cd_health.py      # Herramienta 3 — Score de salud de Release Pipelines
├── azdo_pipeline_drift.py         # Herramienta 4 — Detección de drift en pipelines CD
├── azdo_release_deep_dive.py      # Herramienta 5 — Deep-dive por Release Definition ID
├── azdo_task_validator.py         # Herramienta 6 — Validación DevSecOps de releases
├── azdo_scan_pipeline_logs.py     # Herramienta 7 — Scanner de logs de pipelines CI
├── azdo_scan_repos_vulnerabilities.py # Herramienta 8 — Scanner de dependencias vulnerables
├── cicd_inventory.py              # Herramienta 9 — Inventario completo repos ↔ CI ↔ CD
├── azdo_repo_properties_branch_diff.py # Herramienta 19 — Diff de configuración entre ramas
├── azdo_repo_branch_diff.py           # Herramienta 20 — Informe ejecutivo de impacto de cambios
├── rollback-pipeline.py                # Herramienta 22 — Pipeline Rollback v1.2.0
├── requirements.txt               # Dependencias Python compartidas
└── outcome/                       # Carpeta autogenerada con los reportes exportados
```

---

## Requisitos previos

| Requisito | Versión mínima |
|---|---|
| Python | 3.11+ |
| pip | cualquiera |

> El launcher `tools.py` crea y gestiona automáticamente un **entorno virtual** `.venv` e instala las dependencias. No es necesario instalarlas manualmente si usas el launcher.

### Instalación manual (sin launcher)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Dependencias (`requirements.txt`)

| Paquete | Versión mínima | Uso |
|---|---|---|
| `requests` | 2.31.0 | Llamadas a la API REST de AzDO |
| `rich` | 13.7.0 | Tablas y salida enriquecida en consola |
| `pandas` | 2.1.0 | Exportación a CSV y Excel |
| `openpyxl` | 3.1.2 | Escritura de archivos `.xlsx` |
| `matplotlib` | 3.8.0 | Diagramas de stages en Excel |

---

## Configuración

> **✅ Configuración Consolidada (v1.6.10)**: Todos los scripts ahora usan `scm/config.json` como única fuente de configuración.

### 1. Crear `config.json` en la raíz de scm/

```bash
# Navegar a la raíz de scm/
cd ..

# Copiar template
cp config.json.template config.json
```

Edita `scm/config.json` con tus valores reales. **Este archivo está en `.gitignore` y nunca se sube al repositorio.**

### 2. Estructura de `scm/config.json`

```json
{
  "azdo": {
    "enabled": true,
    "organization_url": "https://dev.azure.com/<TU_ORGANIZACION>",
    "organization": "<TU_ORGANIZACION>",
    "project": "<TU_PROYECTO>",
    "pat": "<TU_PAT_TOKEN>",
    
    "pat_permissions": {
      "pipeline_updater": ["Release (Read & Write)"],
      "pipeline_rollback": ["Release (Read & Write)"]
    },
    
    "defaults": {
      "timezone": "America/Mazatlan",
      "threads": 8,
      "output_format": "csv",
      "debug": false
    },
    
    "tools": {
      "pr_master_checker": { "target_branch": "master", "pr_status": "all" },
      "pipeline_updater": {
        "definition_id": 9999999,
        "branch_config": "config-cadenaSuministro"
      }
    }
  }
}
```

### 3. Permisos del PAT por herramienta

| Herramienta | Permisos requeridos |
|---|---|
| `azdo_pr_master_checker` | `Code (Read)` · `Release (Read)` |
| `azdo_pr_pipeline_analyzer` | `Code (Read)` · `Release (Read)` |
| `azdo_branch_policy_checker` | `Code (Read)` · `Project and Team (Read)` |
| `azdo_release_cd_health` | `Release (Read)` |
| `azdo_pipeline_drift` | `Release (Read)` |
| `azdo_task_validator` | `Release (Read, Write)` · `Build (Read)` · `Variable Groups (Read)` · `Code (Read)` |
| `scan_pipeline_logs` | `Build (Read)` |
| `scan_repos_vulnerabilities` | `Code (Read)` |

> Un PAT con `Code (Read)` + `Release (Read, Write)` + `Build (Read)` + `Variable Groups (Read)` + `Project and Team (Read)` cubre **todas** las herramientas.

---

## Launcher interactivo — `tools.py`

Punto de entrada unificado. Gestiona el venv, instala dependencias y lanza cualquier herramienta de forma interactiva.

```bash
python tools.py
```

### Menú principal

```
╔══════════════════════════════════════════════════╗
║        🔷  Azure DevOps Tools  🔷               ║
║   v1.0.0  |  by Harold Adrian                    ║
╚══════════════════════════════════════════════════╝
  📄 config.json:  PAT: ✅ Configurado  |  Org: https://dev.azure.com/...

  #   Grupo                  Herramienta               Descripción
  1   📬 Pull Requests        PR Master Checker         Lista PRs hacia master...
  2   🔒 Políticas de Rama    Branch Policy Checker     Audita políticas de rama...
  3   🚀 Release Pipelines    Release CD Health         Score de salud de Release...
  4   🔍 Drift Analysis       Pipeline Drift Analyzer   Detecta drift en pipelines...
  5   🚀 Release Pipelines    Release Deep Dive         Análisis profundo por ID...
  6   ✅ Validación           Task Validator            Validación DevSecOps de releases
  7   🛡️ Seguridad            Pipeline Logs Scanner     Escanea logs buscando vulnerabilidades
  8   🛡️ Seguridad            Repo Vulnerabilities      Escanea package.json en repos
  A   ⚙️  Sistema              Ejecutar Todos            Ejecuta las herramientas 1-4
  Q   ⚙️  Sistema              Salir
```

**Comportamiento:**
- Si `config.json` existe, los valores de PAT / org / proyecto se usan como defaults (solo presionas Enter).
- La opción **A** ejecuta las herramientas 1-4 secuencialmente (no incluye la 5 por requerir un ID específico).
- El venv se crea en `.venv/` y las dependencias se instalan una sola vez (marcador en `.venv/.installed_requirements`).

---

## Herramientas

---

### 1 · PR Master Checker — `azdo_pr_master_checker.py`

Cruza todos los Pull Requests hacia `master` (o la rama que definas) con los Release Pipelines CD del proyecto. Identifica si el repositorio tiene un pipeline CD asociado y si ese pipeline contiene un stage específico (por defecto `validador`).

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | `-g` | — | `https://dev.azure.com/Coppel-Retail` | URL de la organización |
| `--project` | `-p` | — | `Compras.RMI` | Nombre del proyecto |
| `--branch` | `-b` | — | `master` | Rama destino de los PRs |
| `--status` | `-s` | — | `all` | Estado de PR: `all` / `active` / `completed` / `abandoned` |
| `--repo` | `-r` | — | — | Filtrar por nombre de repositorio (substring) |
| `--stage-name` | — | — | `validador` | Nombre del stage a buscar en el pipeline CD |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` / `excel` |
| `--timezone` | `-tz` | — | `America/Mazatlan` | Zona horaria para fechas |
| `--top` | — | — | `500` | Máximo de PRs por repositorio |
| `--threads` | — | — | `6` | Hilos paralelos |
| `--debug` | — | — | `false` | Mostrar errores HTTP detallados |

#### Ejemplos

```bash
# Básico
python azdo_pr_master_checker.py --pat <PAT>

# Solo PRs activos en un repo específico, exportar a Excel
python azdo_pr_master_checker.py --pat <PAT> --status active --repo ds-ppm --output excel

# Buscar stage "qa-gate" en lugar de "validador"
python azdo_pr_master_checker.py --pat <PAT> --stage-name qa-gate
```

#### Salida en consola

```
  Repositorio         PR   Autor       Rama origen       CD Pipeline          Stage validador
  ds-ppm-pricing      42   jlopez      feature/JIRA-123  ds-ppm-pricing-cd    ✅ Encontrado
  ds-sap-supplier      7   mgarcia     hotfix/fix-null   ds-sap-supplier-cd   ❌ No encontrado
```

---

### 1b · PR Pipeline Analyzer — `azdo_pr_pipeline_analyzer.py`

Analiza Pull Requests de múltiples ramas destino (`dev`, `QA`, `master`, `release*`), los organiza por fecha descendente y cruza la información con pipelines CD y últimos releases. Incluye reporte de tiempos de ejecución.

#### Flujo de trabajo

1. **Descargar PRs** de las ramas seleccionadas (único o todas)
2. **Organizar por fecha** descendente y mostrar en tabla
3. **Agrupar por repositorio** y mostrar resumen
4. **Descargar pipelines CD** para los repositorios con PRs
5. **Descargar últimos releases** por cada repositorio
6. **Reporte de tiempos** de cada paso

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | `-g` | — | `https://dev.azure.com/Coppel-Retail` | URL de la organización |
| `--project` | `-p` | — | `Cadena_de_Suministros` | Nombre del proyecto |
| `--branches` | `-b` | — | `master` | Ramas a analizar: `dev`, `QA`, `master`, `release`, o `all` |
| `--status` | `-s` | — | `active` | Estado de PRs: `active` / `completed` / `abandoned` / `all` |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` / `excel` |
| `--timezone` | `-tz` | — | `America/Mazatlan` | Zona horaria para fechas |
| `--top` | — | — | `500` | Máximo de PRs por consulta |
| `--threads` | — | — | `16` | Hilos paralelos para releases |
| `--debug` | — | — | `false` | Mostrar errores HTTP detallados |
| `--list-cds` | — | — | `false` | Listar todos los CDs disponibles y salir (diagnóstico) |

#### Ejemplos

```bash
# Analizar PRs activos hacia master (default)
python azdo_pr_pipeline_analyzer.py --pat <PAT>

# Todas las ramas
python azdo_pr_pipeline_analyzer.py --pat <PAT> --branches all

# Solo ramas QA y master
python azdo_pr_pipeline_analyzer.py --pat <PAT> --branches QA master

# PRs completados (mergeados)
python azdo_pr_pipeline_analyzer.py --pat <PAT> --status completed

# Todos los PRs sin filtro de estado
python azdo_pr_pipeline_analyzer.py --pat <PAT> --status all

# Exportar a Excel
python azdo_pr_pipeline_analyzer.py --pat <PAT> --output excel

# Listar todos los CDs disponibles (diagnóstico)
python azdo_pr_pipeline_analyzer.py --pat <PAT> --list-cds
```

#### Salida en consola

```
🔧 Configuración:
   Org: https://dev.azure.com/Coppel-Retail
   Project: Cadena_de_Suministros
   Ramas: master
   Estado PRs: active

📥 Paso 1: Descargando PRs...
   ✅ 45 PRs activos encontrados

[Tabla de PRs ordenados por fecha]

📁 Paso 2: Resumen por Repositorio (23 repos)
┌───────────────────────────────────┬──────┬──────────┬──────────────┬──────────────┐
│ Repositorio                       │ Total│ 🟢 Activos│ ✅ Completados│ ❌ Abandonados│
├───────────────────────────────────┼──────┼──────────┼──────────────┼──────────────┤
│ wms-proc-shipconfirm              │    5 │        5 │           —  │           —  │
│ tms-front-transportationapp       │    4 │        4 │           —  │           —  │
│ iwms-tiendavirtual                │    3 │        3 │           —  │           —  │
│ legacy-frontend-uc-login          │    2 │        2 │           —  │           —  │
│ ...                               │  ... │      ... │          ... │          ... │
├───────────────────────────────────┼──────┼──────────┼──────────────┼──────────────┤
│ TOTAL                             │   45 │       45 │           —  │           —  │
└───────────────────────────────────┴──────┴──────────┴──────────────┴──────────────┘

🚀 Paso 3: Buscando pipelines CD...
   Candidatos encontrados: 120 CDs únicos (de 500 totales)
   Descargando detalles de 120 CDs... ✓ (118 cargados)
   ✅ CD encontrados: 38/42

📦 Paso 4: Descargando últimos releases...
   ✅ Releases encontrados: 35/38

[Tabla de CD y releases]

⏱️ Tiempos de Ejecución
┌──────────────────────────┬────────────┬──────────┐
│ Paso                     │ Tiempo (s) │ % Total  │
├──────────────────────────┼────────────┼──────────┤
│ 1. Descargar PRs         │     45.23s │    32.5% │
│ 2. Agrupar por repo      │      0.15s │     0.1% │
│ 3. Descargar CD pipelines│     78.45s │    56.3% │
│ 4. Descargar releases    │     15.42s │    11.1% │
├──────────────────────────┼────────────┼──────────┤
│ TOTAL                    │    139.25s │   100.0% │
└──────────────────────────┴────────────┴──────────┘
```

---

### 2 · Branch Policy Checker — `azdo_branch_policy_checker.py`

---

### 2b · Branch Lock Checker — `azdo_branch_lock_checker.py`

Lista todas las ramas con **lock activo** (`isLocked = true`) en todos los repositorios del proyecto. El repositorio se repite por cada rama bloqueada que contenga.

**Columnas:**

| # | Repositorio | Rama | Bloqueado por |
|---|-------------|------|----------------|
| 1 | repo-abc | master | juan.perez |
| 2 | repo-abc | develop | juan.perez |
| 3 | repo-xyz | main | maria.lopez |

**Uso:**
```bash
python azdo_branch_lock_checker.py --pat <PAT> --org https://dev.azure.com/MiOrg --project MiProyecto

# Filtrar solo un repo
python azdo_branch_lock_checker.py --pat <PAT> --repo mi-servicio

# Exportar
python azdo_branch_lock_checker.py --pat <PAT> --output json
```

**Permisos PAT:** `Code (Read)`

---

### 2 · Branch Policy Checker — `azdo_branch_policy_checker.py`

Audita las políticas de rama configuradas en **todos los repositorios** del proyecto para tres ramas críticas: `master/main`, `QA` y `develop`. Asigna un semáforo de estado por repositorio.

#### Estado por repositorio

| Estado | Condición |
|---|---|
| 🟢 `OK` | Las tres ramas tienen al menos una política activa |
| 🟡 `WARNING` | Una o dos ramas carecen de políticas |
| 🔴 `ALERT` | Ninguna rama tiene políticas configuradas |

#### Variantes de rama detectadas automáticamente

| Rama canónica | Variantes reconocidas |
|---|---|
| `master` | `master`, `main` |
| `QA` | `QA`, `qa`, `Qa`, `release`, `Release` |
| `develop` | `develop`, `development`, `dev`, `Dev` |

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | `-g` | — | `https://dev.azure.com/Coppel-Retail` | URL de la organización |
| `--project` | `-p` | — | `Compras.RMI` | Nombre del proyecto |
| `--repo` | `-r` | — | — | Filtrar por nombre de repositorio (substring) |
| `--status-filter` | — | — | `all` | Mostrar solo repos con estado: `OK` / `WARNING` / `ALERT` / `all` |
| `--detail` | — | — | `false` | Mostrar detalle de cada política por rama |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` / `excel` |
| `--timezone` | `-tz` | — | `America/Mazatlan` | Zona horaria para fechas |
| `--debug` | — | — | `false` | Mostrar errores HTTP detallados |

#### Ejemplos

```bash
# Todos los repositorios
python azdo_branch_policy_checker.py --pat <PAT>

# Solo repositorios en ALERT, con detalle de políticas
python azdo_branch_policy_checker.py --pat <PAT> --status-filter ALERT --detail

# Exportar a Excel
python azdo_branch_policy_checker.py --pat <PAT> --output excel
```

---

### 3 · Release CD Health — `azdo_release_cd_health.py`

Analiza la salud de los **Release Pipelines CD** del proyecto. Calcula un score de 0-100 por pipeline basado en la recencia y estabilidad de los despliegues en producción. Detecta automáticamente el stage de producción por palabras clave.

#### Fórmula de score

```
Score = Recencia (0-70 pts) + Estabilidad (0-30 pts)

Recencia:
  Último deploy PROD hace ≤7 días    → 70 pts
  Último deploy PROD hace ≤30 días   → 50 pts
  Último deploy PROD hace ≤90 días   → 25 pts
  Sin deploy PROD reciente           →  0 pts

Estabilidad (últimos N releases):
  Tasa de éxito ≥ 90%  → 30 pts
  Tasa de éxito ≥ 70%  → 20 pts
  Tasa de éxito ≥ 50%  → 10 pts
  Tasa de éxito < 50%  →  0 pts
```

#### Rating por score

| Score | Rating |
|---|---|
| 80 – 100 | 🟢 Excelente |
| 60 – 79 | 🟡 Bueno |
| 40 – 59 | 🟠 Regular |
| 0 – 39 | 🔴 Crítico |

#### Keywords de producción detectadas

`prod`, `prd`, `production`, `produccion`, `productivo`, `producción`, `live`, `prd01`, `prd1`

#### Consistencia de stages

Compara los stages de cada pipeline contra la mayoría: `OK` · `PARCIAL` · `DIFERENTE` · `ÚNICO`

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | `-g` | — | `https://dev.azure.com/Coppel-Retail` | URL de la organización |
| `--project` | `-p` | — | `Compras.RMI` | Nombre del proyecto |
| `--filter` / `--repo` | `-f` / `-r` | — | — | Filtrar pipelines por nombre/repo (substring) |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` / `excel` |
| `--sort` | — | — | `score` | Ordenar por: `score` / `name` / `date` |
| `--top` | — | — | `15` | Últimos N releases a analizar por pipeline |
| `--threads` | — | — | `8` | Hilos paralelos |
| `--timezone` | `-tz` | — | `America/Mazatlan` | Zona horaria para fechas |
| `--diagram` | — | — | `false` | Imprimir diagrama ASCII de stages en consola |
| `--debug` | — | — | `false` | Mostrar errores HTTP detallados |

#### Ejemplos

```bash
# Análisis completo
python azdo_release_cd_health.py --pat <PAT>

# Filtrar + diagrama en consola + exportar Excel con imágenes
python azdo_release_cd_health.py --pat <PAT> --filter ds-ppm --diagram --output excel

# Ordenar por fecha del último deploy
python azdo_release_cd_health.py --pat <PAT> --sort date --output json
```

#### Diagrama ASCII (consola, `--diagram`)

```
  ┌────────────┐         ┌────────────┐         ┌────────────┐
  │   DEV      │────▶   │   QA        │────▶   │   PROD     │
  └────────────┘         └────────────┘         └────────────┘
  ✅ Stage PROD: PROD  |  Último deploy: 2025-03-10 14:22
```

#### Hoja "Pipeline Diagrams" en Excel (`--output excel`)

Cuando `matplotlib` está instalado, el Excel incluye una hoja adicional con imágenes PNG del diagrama de stages por pipeline (verde = PROD desplegado, rojo = PROD sin deploy, azul = stage normal).

---

### 4 · Pipeline Drift Analyzer — `azdo_pipeline_drift.py`

Compara el estado **actual** de cada Release Pipeline CD contra el **snapshot almacenado en el último release ejecutado**. Detecta cambios que aún no han sido desplegados ("drift").

#### Dimensiones de análisis

| Dimensión | Qué compara | Fuente del snapshot |
|---|---|---|
| **B — Stage diff** | Stages añadidos / eliminados en la definición | `release.environments[].name` |
| **C — Variable drift** | Keys de variables añadidas / eliminadas (no valores) | `release.variables{}` + por stage |
| **D — Approval drift** | Cambios en gates de aprobación: conteo, mínimo, aprobadores | `release.environments[].preDeployApprovals` |
| **F — Task diff** | Tasks añadidas, eliminadas o con versión cambiada | `release.environments[].deployPhases[].workflowTasks[]` |

#### Niveles de severidad

| Severidad | Condición |
|---|---|
| 🚨 `CRITICAL` | Approval gates cambiaron en algún stage |
| 🔴 `HIGH` | Stages o tasks añadidas / eliminadas |
| 🟡 `MEDIUM` | Versión de alguna task actualizada |
| 🔵 `LOW` | Solo variables añadidas / eliminadas |
| ⚪ `NONE` | Sin drift detectado |

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | `-g` | — | `https://dev.azure.com/Coppel-Retail` | URL de la organización |
| `--project` | `-p` | — | `Compras.RMI` | Nombre del proyecto |
| `--filter` / `--repo` | `-f` / `-r` | — | — | Filtrar pipelines por nombre/repo (substring) |
| `--severity` | `-s` | — | — | Mostrar solo pipelines con severidad `>=`: `NONE` / `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `--sort` | — | — | `severity` | Ordenar por: `severity` / `name` / `gap` |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` / `excel` |
| `--threads` | — | — | `8` | Hilos paralelos |
| `--timezone` | `-tz` | — | `America/Mazatlan` | Zona horaria para fechas |
| `--debug` | — | — | `false` | Mostrar errores HTTP detallados |

#### Ejemplos

```bash
# Análisis completo de drift
python azdo_pipeline_drift.py --pat <PAT>

# Solo pipelines CRITICAL y HIGH
python azdo_pipeline_drift.py --pat <PAT> --severity HIGH

# Filtrar + exportar Excel con celdas de severidad coloreadas
python azdo_pipeline_drift.py --pat <PAT> --filter ds-ppm --output excel

# Ordenar por mayor revision gap
python azdo_pipeline_drift.py --pat <PAT> --sort gap
```

#### Salida de ejemplo (consola)

```
  #  Pipeline              Rev Gap  Stages Δ  Vars Δ  Approvals Δ  Tasks Δ   Último Release    Severity
  1  ds-ppm-pricing-cd         3    +1 -0     +2 -0   1 stage(s)   +0-1 ~2   2025-03-10 14:22  🚨 CRITICAL
  2  ds-sap-supplier-cd        1    +0 -0     +1 -0   —            +1-0 ~0   2025-03-18 09:01  🔴 HIGH
  3  ds-tms-import-cd          0    +0 -0     +0 -0   —            —         2025-03-19 11:30  ⚪ NONE
```

**Columnas:**
- `Rev Gap` — número de revisiones del pipeline sin desplegar (`revision_actual - revision_snapshot`)
- `Stages Δ` — stages `+añadidos` / `-eliminados` desde el último release
- `Vars Δ` — variables `+añadidas` / `-eliminadas` (acumulado pipeline + stages)
- `Approvals Δ` — cantidad de stages donde los gates de aprobación cambiaron
- `Tasks Δ` — tasks `+añadidas` / `-eliminadas` / `~versión_cambiada`

---

### 5 · Release Deep Dive — `azdo_release_deep_dive.py`

Análisis unificado para un único Release Definition identificado por ID. Extrae el repositorio Git vinculado desde los artefactos y ejecuta los cuatro análisis del toolbox sobre esa combinación pipeline + repo en una sola ejecución.

#### Secciones del reporte

| Sección | Descripción |
|---|---|
| **Release Definition** | Nombre, ID, stages, pre/post approvals por stage |
| **Pull Requests** | PRs activos hacia `--branch` del repo vinculado |
| **Branch Policies** | Políticas en master, QA y develop del repo vinculado |
| **CD Health** | Score 0-100: estabilidad, recencia y frecuencia de deploys |
| **Pipeline Drift** | Cambios de stages/variables vs snapshot del último release |

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--release-id` / `--id` | — | ✅ | — | ID de la Release Definition a analizar |
| `--org` | `-g` | — | `https://dev.azure.com/Coppel-Retail` | URL de la organización |
| `--project` | `-p` | — | `Compras.RMI` | Nombre del proyecto |
| `--branch` | `-b` | — | `master` | Branch destino para análisis de PRs |
| `--stage-name` | — | — | `validador` | Stage a verificar en el pipeline |
| `--top` | — | — | `15` | Últimos N releases para health/drift |
| `--timezone` | `-tz` | — | `America/Mazatlan` | Zona horaria para fechas |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` / `excel` |
| `--debug` | — | — | `false` | Mostrar errores HTTP detallados |

#### Ejemplos

```bash
# Deep-dive básico por ID
python azdo_release_deep_dive.py --release-id 42 --pat <PAT>

# Verificar stage 'qa-gate' y exportar a Excel
python azdo_release_deep_dive.py --release-id 42 --pat <PAT> --stage-name qa-gate --output excel
```

> **Cómo obtener el `--release-id`:** Ejecuta la herramienta 3 (`azdo_release_cd_health.py`) y consulta la columna **Def ID** en la tabla de resultados.

---

### 6 · Task Validator — `azdo_task_validator.py`

Herramienta DevSecOps para validación de releases en Azure DevOps. Implementa controles de seguridad y verificación de integridad durante el proceso de release.

#### Funciones de validación

| # | Función | Descripción |
|---|---------|-------------|
| 1 | **Validación de Imágenes** | Verifica existencia de imágenes Docker en Harbor/Artifact Registry |
| 2 | **Búsqueda de Rollback** | Encuentra releases anteriores por TAG para rollback |
| 3 | **Validación de Credenciales** | Compara fechas de vigencia de credenciales GIT |
| 4 | **Comparación ConfigMap** | Compara configuración K8s vs repositorio Git |

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | — | — | Desde env | URL de la organización |
| `--project` | — | — | Desde env | Nombre del proyecto |
| `--release-id` | — | — | Desde env | ID del release actual |
| `--image-actual` | — | — | — | Imagen actualmente desplegada |
| `--image-nueva` | — | — | — | Nueva imagen a desplegar |
| `--gcp-project` | — | — | — | Proyecto GCP para autenticación |
| `--group-id` | — | — | — | ID del Variable Group de credenciales |
| `--artifact-name` | — | — | — | Nombre del servicio/artefacto |
| `--namespace` | — | — | — | Namespace de Kubernetes |
| `--all` | — | — | — | Ejecuta todas las validaciones |
| `--validate-images` | — | — | — | Solo validación de imágenes |
| `--find-rollback` | — | — | — | Solo búsqueda de rollback |
| `--validate-credentials` | — | — | — | Solo validación de credenciales |
| `--compare-configmap` | — | — | — | Solo comparación de ConfigMap |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` |
| `--debug` | — | — | `false` | Modo debug con logs detallados |

#### Variables de Azure DevOps establecidas

| Variable | Descripción |
|----------|-------------|
| `TAG_ACTUAL` | TAG extraído de la imagen actual |
| `RELEASE_ID_RB` | ID del release de rollback encontrado |
| `MatchedCommitIdJob` | Commit ID que coincide con el ConfigMap |
| `ShouldRollbackJob` | `true` o `false` según si se encontró coincidencia |

#### Ejemplos

```bash
# Ejecutar todas las validaciones
python azdo_task_validator.py --all --pat <PAT> --org mi-org --project mi-proyecto --release-id 123

# Solo validar imágenes
python azdo_task_validator.py --validate-images --image-actual us-docker.pkg.dev/.../img:v1.0 --image-nueva us-docker.pkg.dev/.../img:v1.1

# Solo buscar release rollback
python azdo_task_validator.py --find-rollback --release-id 123 --tag v1.0.0
```

#### Requisitos adicionales

- `gcloud` CLI (para validación de imágenes en Artifact Registry)
- `crane` (para validación de imágenes en Harbor)
- `kubectl` (para obtener ConfigMaps de Kubernetes)

> **Basado en:** `azdo-task-validador-optimized.sh` — Port de bash a Python con mejoras de UI y exportación.

---

### 7 · Pipeline Logs Scanner — `azdo_scan_pipeline_logs.py`

Escanea los logs de todos los pipelines CI del proyecto buscando términos específicos relacionados con vulnerabilidades de dependencias. Útil para detectar si alguna build ha reportado paquetes vulnerables.

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | `-g` | — | desde config.json | Organización de Azure DevOps |
| `--project` | `-p` | — | desde config.json | Proyecto a escanear |
| `--search-terms` | — | — | `axios@1.14.1,axios@0.30.4,plain-crypto-js` | Términos a buscar (separados por coma) |
| `--context-terms` | — | — | `vulnerab,npm audit,critical,high` | Términos de contexto |
| `--top-runs` | — | — | `50` | Últimas N ejecuciones por pipeline |
| `--threads` | — | — | `10` | Hilos paralelos |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` |
| `--debug` | — | — | `false` | Modo debug |
| `--help-config` | — | — | — | Mostrar ejemplo de config.json |

#### Ejemplos

```bash
# Básico con PAT
python azdo_scan_pipeline_logs.py --pat <PAT> --org Coppel-Retail --project MiProyecto

# Términos personalizados + exportar CSV
python azdo_scan_pipeline_logs.py --pat <PAT> --search-terms "lodash@4.17.20,moment" --output csv

# Más ejecuciones por pipeline
python azdo_scan_pipeline_logs.py --pat <PAT> --top-runs 100 --threads 15

# Desde el launcher (opción 7)
python tools.py
```

#### Configuración en config.json

```json
"scan_pipeline_logs": {
    "top_runs": 50,
    "threads": 10,
    "search_terms": ["axios@1.14.1", "axios@0.30.4", "plain-crypto-js"],
    "context_terms": ["vulnerab", "npm audit", "critical", "high"]
}
```

#### Salida

Tabla con columnas: `organization`, `project`, `pipeline_name`, `pipeline_id`, `run_id`, `run_name`, `source_branch`, `status`, `result`, `log_id`, `line_number`, `match_term`, `context_detected`, `matched_line`, `web_url`

---

### 8 · Repo Vulnerabilities Scanner — `azdo_scan_repos_vulnerabilities.py`

Escanea todos los repositorios del proyecto buscando archivos `package.json` en las ramas críticas y detecta dependencias vulnerables específicas.

#### Argumentos CLI

| Argumento | Corto | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--pat` | — | ✅ | — | Personal Access Token |
| `--org` | `-g` | — | desde config.json | Organización de Azure DevOps |
| `--project` | `-p` | — | desde config.json | Proyecto a escanear |
| `--branches` | — | — | `develop,QA,master,main` | Ramas a revisar (separadas por coma) |
| `--targets` | — | — | `axios:1.14.1\|0.30.4,plain-crypto-js` | Dependencias a buscar |
| `--repo` | `-r` | — | — | Filtrar por nombre de repositorio |
| `--output` | `-o` | — | — | Exportar: `json` / `csv` |
| `--debug` | — | — | `false` | Modo debug |
| `--help-config` | — | — | — | Mostrar ejemplo de config.json |

#### Formato de targets

- `paquete:version1|version2` — Detecta versiones específicas
- `paquete` — Detecta cualquier versión del paquete

#### Ejemplos

```bash
# Básico con PAT
python azdo_scan_repos_vulnerabilities.py --pat <PAT> --org Coppel-Retail --project MiProyecto

# Targets personalizados
python azdo_scan_repos_vulnerabilities.py --pat <PAT> --targets "lodash:4.17.20|4.17.19,moment"

# Filtrar por repo y exportar
python azdo_scan_repos_vulnerabilities.py --pat <PAT> --repo ds-ppm --output csv

# Solo ramas específicas
python azdo_scan_repos_vulnerabilities.py --pat <PAT> --branches "master,main"

# Desde el launcher (opción 8)
python tools.py
```

#### Configuración en config.json

```json
"scan_repos_vulnerabilities": {
    "branches": ["develop", "QA", "master", "main"],
    "targets": {
        "axios": ["1.14.1", "0.30.4"],
        "plain-crypto-js": null
    }
}
```

> **Nota:** Si `targets[paquete]` es `null`, detecta cualquier versión del paquete.

#### Salida

Tabla con columnas: `organization`, `project`, `repository`, `branch`, `package_json_path`, `dependency`, `version_found`, `normalized_version`, `dependency_section`, `repository_url`

---

### 9 · SCM Inspection Remediator — opción 44

Descubre las violaciones del stage **SCM Inspection** de un pipeline CD y genera
un template `pipe_cd_inspection_fix_<definitionId>_<ts>.yaml` en `outcome/` con las
correcciones (secrets sin marcar, paridad de variables entre stages, valores vacíos,
variables a nivel pipeline). El template se aplica con el Pipeline Updater (opción 41),
en modo solo-template, dry-run o aplicación real.

Ambos templates (`pipe_cd_*` y `release_*`) llevan al inicio un **comentario `#`
simplificado** con todos los cambios, y el mismo resumen en `metadata.comment` —
campo que los engines envían en el PUT → queda en el **historial de revisiones
de Azure DevOps** (definición o release). `metadata.description` solo describe
el objetivo del template:

```yaml
# 3 cambio(s): +requests.cpu@Develop=200m, ~ksa@Production=******** 🔒, -tuSecret@release
metadata:
  description: "Corrige violaciones del stage SCM Inspection del pipeline CD: ..."
  comment: "3 cambio(s): +requests.cpu@Develop=200m, ~ksa@Production=******** 🔒, -tuSecret@release"
```

Convención: `+` add, `~` update, `-` remove; `@<stage>` scope environment o
`@release` scope release; valores sensibles enmascarados (`mask_value`).

> **`allowOverride` ("Settable at release time")**: todas las reglas
> `add`/`update` generadas llevan `allowOverride: false` — las variables del
> pipeline CD no deben quedar setteables al crear un release. Además, desde
> v1.8.29 el **default del Pipeline Updater** para variables nuevas es
> `allowOverride: false` (antes `true`); un `update` preserva el flag salvo
> que la regla lo especifique. En el release el engine (opción 42) lo aplica
> al snapshot. Reglas `remove` no lo llevan.

#### Flujo interactivo

1. Se solicita el **Definition ID del pipeline CD** (la definición de release que
   contiene el stage `SCM Inspection`) y opcionalmente un **Release ID**
   (Enter = último run del stage; un ID específico inspecciona ese release y lo
   deja como destino por defecto en las opciones `4`–`6`).
2. Se descubre el último release con ese stage, se descargan los logs de sus tareas
   y se parsean las violaciones (`##[warning]` / `##[error]`).
3. Las violaciones se convierten en **ajustes candidatos** (`add` / `update` /
   `remove` sobre variables de la definición del release). La comprobación de
   existencia de cada variable consulta **la definición y la instancia del
   release** — el inspector evalúa el snapshot del release, por lo que una
   variable puede existir solo ahí (p. ej. agregada tras crear el release o
   ya eliminada de la definición). En ese caso el ajuste se genera igual con
   la nota *"existe solo en el release — se elimina/actualiza ahí"*: el engine
   de release (opción 42) la aplica al snapshot y en la definición es no-op.
   Solo queda "manual" si la variable no existe en ninguna de las dos.
4. Las variables sin valor fuente pasan por el ciclo de valores pendientes
   (Enter = `TBD`, texto = valor, `e` = eliminar, `i` = ignorar).
5. Se muestra el **Resumen FINAL de cambios** y el menú de confirmación.

#### Menú de confirmación

```
[Enter] Generar template | [c] Corregir valores pendientes
| [e] Editar ajustes uno a uno | [v] Editar variable puntual
| [r] Recargar ajustes | [0] Salir
```

| Opción | Alcance |
|---|---|
| `Enter` | Genera el template en `outcome/` y pasa a la selección de aplicación (solo-template / dry-run / aplicar) |
| `[c]` | Recorre solo las variables **pendientes** (sin valor fuente): Enter conserva, texto reemplaza, `s` regresa a manual |
| `[e]` | Recorre **todos** los ajustes candidatos uno por uno |
| `[v]` | Edición puntual: `nombre` o `nombre@stage` (ej. `cluster_name@Production`) |
| `[r]` | **Recargar ajustes** — ver detalle abajo |
| `[0]` | Sale sin generar template |

Dentro del editor (`e`/`v`), cada ajuste acepta: `Enter` = conservar, texto =
reemplazar valor (en un `remove` revierte a `update`), `e` = eliminar la variable,
`i` = descartar el ajuste, `k` = toggle `isSecret` (marcar 🔒 / desmarcar 🔓;
no aplica a `remove`).

#### Opción `[r]` — Recargar ajustes candidatos

Reconstruye los ajustes candidatos **desde las violaciones descubiertas en el
release del Definition ID del pipeline CD** que se está remediando. Es decir,
vuelve al estado "recién generado" como si la sesión acabara de iniciar con ese
mismo Definition ID.

- **Descarta**: las ediciones manuales hechas con `[e]` o `[v]` (ajustes
  descartados, valores cambiados a mano, removes convertidos, toggles `k`).
- **Conserva**: los valores capturados en el ciclo de pendientes (`TBD` o
  valores escritos por el usuario) y las variables marcadas para eliminar — esas
  decisiones se re-aplican al reconstruir.
- Uso típico: recuperar un ajuste descartado por error o deshacer una edición
  incorrecta sin salir de la herramienta.

> **Nota**: `[r]` no vuelve a consultar Azure DevOps; reutiliza las violaciones
> ya descubiertas del release actual del pipeline CD. Para re-descubrir (otro
> release o un Definition ID distinto) se debe salir (`[0]`) y ejecutar de nuevo.

#### Destino de la aplicación

Tras generar el template se elige **dónde** aplicar los ajustes (el menú es un
bucle: tras cada ejecución vuelve a aparecer hasta salir con `0` o `1`):

```
[1] Solo template (definición — aplicar luego con opción 41)
[2] Definición: dry-run
[3] Definición: aplicar
[4] Release: dry-run (default #<último descubierto>)
[5] Release: aplicar (default #<último descubierto>)
[6] Ambos: definición + release
[0] Salir
```

- **Definición** (`1`–`3`): aplica el template `pipe_cd_*.yaml` a la release
  **definition** del pipeline CD via Pipeline Updater (opción 41), que incluye
  sus propios snapshots/rollback.
- **Release** (`4`–`6`): genera un template `release_inspection_fix_<relId>_*
  .yaml` (formato de la opción 42: `update.global_vars` + `update.env_vars`
  con `stage`) y lo aplica con el **engine existente de Update Release**
  (`pipeline_cd_update_release` — opción 42): GET → tabla de cambios →
  backup en `outcome/backups/` → PUT. Soporta `add`/`update`/`remove`/
  `isSecret` por variable (campos nuevos del engine). El default es el
  release descubierto en el análisis; también acepta escribir un **release
  ID específico**.
- Con `[6]` la definición se aplica primero; si falla, el release se omite.

> **Nota**: son dos engines con dos formatos de template distintos —
> definición → `pipe_cd_inspection_fix_*.yaml` (opción 41), release →
> `release_inspection_fix_*.yaml` (opción 42).

#### Redeploy del stage inspeccionado

Tras una aplicación **real** al release (opciones `5` o `6`), se ofrece
re-correr el deploy del stage inspeccionado (p. ej. `SCM Inspection`) en ese
release — `PATCH releases/{id}/environments/{envId}` con
`status: inProgress` — para que la inspección vuelva a correr con las
variables ya remediadas. En CLI se activa con `--redeploy`.

> **Cuándo usar cada destino**: la definición corrige futuros releases; el
> release actualiza el snapshot de variables de una instancia ya creada
> (útil para re-correr el stage SCM Inspection sobre el mismo release).

#### Modo CLI

```bash
python -m scm.azdo.scm_inspection_remediator \
  --definition-id <id> \
  [--stage "SCM Inspection"] [--release-id <id>] \
  [--set NAME=VALUE ...] [--remove NAME ...] [--tbd] \
  [--target definition|release|both] [--redeploy] \
  [--apply | --dry-run]
```

Sin `--apply` ni `--dry-run` el modo no interactivo solo genera el template.
`--target` (default `definition`) selecciona el destino de `--apply`/`--dry-run`;
con `release`/`both` el release destino es `--release-id` o, si no se indica,
el último release descubierto del stage.

---

### 10 · Release Manifest Drift — opción 45

`azdo_release_manifest_drift.py` — Auditoría de consistencia entre la
**definición** del pipeline CD, el **snapshot** del último release con deploy
efectivo en el stage (default `Production`) y los **logs** de las tasks de
manifiesto K8s. El objetivo es detectar **drift por manipulación directa del
cluster** (cambios hechos por fuera del pipeline).

#### Flujo por pipeline

1. Lista release definitions (`release/definitions`, paginado) y filtra por
   `all` | ID | lista `id1,id2` | substring de nombre (mezclables).
2. Descarga la definición (`definitions/{id}?$expand=environments`) y ubica
   el stage por nombre (`--stage-name`, default `production`; match exacto →
   sufijo `duction` — cubre `Production`/`Producción` — → token `prod` →
   substring).
3. Busca el **último deploy efectivo** del stage vía **Deployments API**
   (`release/deployments?definitionEnvironmentId=…&queryOrder=descending`,
   saltando `deploymentStatus=notDeployed`) — distinto a "último release",
   un release puede existir sin haber desplegado en prod. Las entradas se
   deduplican por `release.id` (la API devuelve una por *attempt*), así el
   "release anterior" de `--prev-release` es siempre un release distinto.
4. Del release toma el `deployStep` de mayor `attempt` en el stage y descarga
   el log (`tasks/{id}/logs`) de las tasks que matchean `--task-patterns`
   (default `get.?file.?k8.?manifest|show.?manifest|kubectl.*apply`) **más
   las tasks apply-typed detectadas por sus inputs** — `Kubernetes@1`/
   `Kubectl@1` con `command: apply|create|replace|patch` o scripts inline
   con `kubectl apply`, aunque su displayName no lo diga (p.ej. "Deploy
   manifests").
5. **Diff definición vs snapshot**: tasks añadidas/eliminadas, versión de
   task, **inputs** de tasks y variables del environment. Inputs ausentes
   equivalen a defaults falsy (`false`, vacío, `0`) para evitar ruido de
   diffs espurios al re-guardar la definición.
6. **Análisis del manifiesto**: parsea el YAML mostrado por *show manifest*
   (`kind`/`metadata.name` por documento) y los verdicts de *kubectl apply*
   (`created`/`configured`/`unchanged`/`deleted`/`replaced` + warnings).
   Soporta el formato de kubectl < 1.18 (`kind "name" configured`) y el
   moderno (`kind/name configured`), más sufijos `(server dry run)`.

#### Señales de drift detectadas

| Severidad | Regla | Significado |
|---|---|---|
| HIGH | `NOT_MANAGED_BY_APPLY` | El recurso existe sin anotación `last-applied-configuration` → creado fuera de `kubectl apply` |
| HIGH | `EXTERNAL_MODIFICATION` | `--prev-release`: manifiesto **idéntico** al release efectivo anterior pero el apply tuvo que `configured` → el objeto vivo fue editado a mano |
| MEDIUM | `NOT_APPLIED` | Objeto del manifiesto sin línea en la salida del apply |
| MEDIUM | `DEF_RELEASE_DRIFT` | La definición difiere del snapshot (tasks/inputs/vars) |
| MEDIUM | `APPLY_ERROR` | Líneas de error del apply |
| MEDIUM | `APPLY_NO_VERDICTS` | El log de apply no produjo verdicts reconocibles (formato no soportado o salida silenciosa) |
| LOW | `APPLIED_NOT_IN_MANIFEST` | El apply procesó un recurso no visto en *show manifest* |
| LOW | `OLD_APPLY_WARNING` | kubectl antiguo emitió el warning genérico de recurso no creado con `--save-config` (no indica cuál) |
| INFO | `UNRENDERED_NAME` | Objeto del manifiesto con placeholders sin renderizar (`#{var}#`, `$(var)`, `{{var}}`) — el show manifest mostró el template pre-sustitución |
| INFO | `EMPTY_LOG` | Log de una task apply vacío o no descargable |
| INFO | `CREATED` / `CONFIGURED` / `EXPECTED_CONFIG` | Contexto (creado, reconfigurado sin previo, cambio explicado por el manifiesto) |

`--prev-release` repite el flujo sobre el **segundo** deploy efectivo y
compara manifiestos documento a documento (YAML canonical): habilita la
señal `EXTERNAL_MODIFICATION`, la más precisa para detectar manipulación.

#### Uso

```bash
# Launcher: opción 45 (grupo Drift & Cambios)
python tools.py

# CLI
python azdo_release_manifest_drift.py --definition-ids all
python azdo_release_manifest_drift.py --definition-ids 3670
python azdo_release_manifest_drift.py --definition-ids 3670,3701 --prev-release
python azdo_release_manifest_drift.py --definition-ids "wms" \
    --task-patterns "k8.?manifest|kubectl.*apply" \
    --stage-name production --output both --threads 6
```

Credenciales: `--pat/--org/--project` o `azdo.*` en `scm/config.json`
(PAT con scope **Release: Read**). Por pipeline se imprime una **tabla
objeto × verdict × severidad** (manifiesto vs apply — análisis principal)
más los findings sin objeto; los pipelines sin stage o sin deploy efectivo
se colapsan en un conteo (`--show-skipped` para verlos uno a uno).
`--output json|csv|html|both|all` exporta a `outcome/` (`all` incluye un
**reporte HTML autocontenido** con resumen, detalle por pipeline y tabla de
objetos). Exit `2` si alguna severidad ≥ HIGH.

---

Todas las herramientas soportan el flag `--output` con tres formatos:

| Formato | Descripción |
|---|---|
| `json` | Archivo JSON con metadata + array de resultados |
| `csv` | Archivo CSV plano |
| `excel` | Archivo `.xlsx` con columnas coloreadas por estado/severidad |

Los archivos se guardan en `outcome/` con timestamp en el nombre:

```
outcome/
├── pr_master_report_20250320_142233.json
├── branch_policy_report_20250320_142233.xlsx
├── release_cd_health_20250320_142233.xlsx   ← incluye hoja "Pipeline Diagrams"
└── pipeline_drift_20250320_142233.xlsx      ← celdas de severidad coloreadas
```

---

## API REST de Azure DevOps

| Recurso | Versión API |
|---|---|
| Repositorios / PRs / Políticas | `7.1` |
| Release Definitions | `7.2-preview.4` |
| Releases (instancias) | `7.2-preview.8` |

**URL base:** `https://vsrm.dev.azure.com/{org}/{project}/_apis/release/...`  
*(Las herramientas de release reemplazan `dev.azure.com` → `vsrm.dev.azure.com` automáticamente)*

---

## Resolución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `401 Unauthorized` | PAT inválido o expirado | Regenera el PAT en AzDO → User Settings → Personal Access Tokens |
| `403 Forbidden` | PAT sin permisos suficientes | Revisa la tabla de permisos por herramienta |
| `Sin release definitions` | Proyecto incorrecto | Verifica `--org` y `--project` |
| `Sin releases ejecutados` | Pipeline nuevo sin historial | Es esperado; se reporta como `"Sin releases ejecutados"` |
| `Tasks: snapshot no disponible` | Release muy antiguo sin `workflowTasks` en el snapshot | Solo aplica a la dimensión F del Drift Analyzer; las demás dimensiones funcionan normalmente |
| `pip install pandas openpyxl` en consola | Dependencias no instaladas | Ejecuta `pip install -r requirements.txt` o usa `tools.py` |

---

## Generación de distribución

El script `make_dist.ps1` (ubicado en la raíz de `devsecops-toolbox/`) empaqueta todos los archivos del proyecto en un ZIP distribuible.

```powershell
# Uso basico
.\make_dist.ps1

# Con carpeta de salida personalizada y lista de excluidos
.\make_dist.ps1 -OutputDir "C:\entregas" -ShowExcluded

# Generar ZIP y publicar release en GitHub
.\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.4.0" -GitHubToken "ghp_xxxx"

# Con titulo, notas y modo draft
.\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.4.0" -ReleaseTitle "Release 1.4.0" -ReleaseNotes "Cambios incluidos..." -Draft

# El token puede venir de una variable de entorno
$env:GITHUB_TOKEN = "ghp_xxxx"
.\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.4.0"
```

**Parametros de GitHub Release:**

| Parametro | Requerido | Descripcion |
|---|---|---|
| `-GitHubPublish` | Para publicar | Activa el flujo de publicacion en GitHub |
| `-ReleaseTag` | Si usa `-GitHubPublish` | Tag de version (ej: `v1.4.0`) |
| `-GitHubToken` | Si no hay `GITHUB_TOKEN` | PAT con scope `Contents: Read and Write` |
| `-ReleaseTitle` | No | Titulo del release (default: mismo que el tag) |
| `-ReleaseNotes` | No | Descripcion / changelog del release |
| `-Draft` | No | Crear como borrador (no visible publicamente) |
| `-Prerelease` | No | Marcar como pre-release |

> El repositorio `owner/repo` se detecta automaticamente desde `git remote get-url origin`.

**Exclusiones automáticas:**

| Categoría | Excluido |
|---|---|
| Control de versiones | `.git/`, `.github/` |
| Secretos | `config.json` (se incluye `config.json.template`) |
| Entornos Python | `.venv/`, `venv/`, `__pycache__/`, `*.pyc` |
| Resultados | `outcome/` (logs, reportes, ZIPs anteriores) |
| IDE / sistema | `.vscode/`, `.windsurf/`, `*.log` |
| Office | `*.xlsx`, `*.docx` |

El ZIP se genera en `outcome/devsecops-toolbox_dist_<YYYYMMDD_HHMMSS>.zip`.

---

## Autor

**Harold Adrian** — DevSecOps Toolbox  
API Reference: [Azure DevOps REST API v7.2](https://learn.microsoft.com/en-us/rest/api/azure/devops/?view=azure-devops-rest-7.2)

---

## Historial de cambios

| Fecha | Versión | Cambio | Archivos afectados |
|---|---|---|---|
| 2026-10-08 | 1.8.38 | **Opción 45: tabla objeto×verdict + reporte HTML** — (1) El análisis de las 3 tasks (get manifest / show manifest / kubectl apply) ahora se presenta como **tabla por pipeline**: Objeto · NS · En manifiesto · Verdict apply · Severidad · Regla (`build_object_rows` reusa `map_verdicts`); findings sin objeto (DEF_RELEASE_DRIFT, APPLY_ERROR…) debajo. (2) `--output html|all` genera `manifest_drift_*.html` autocontenido en `outcome/`: resumen con badges de severidad + detalle por pipeline (release, diff, tabla de objetos, findings) + lista de omitidos. (3) Auto-descarga de tasks con "manifest" en el nombre aunque no matcheen el regex. (4) Nueva señal `NO_MANIFEST_TASKS` (INFO) cuando ninguna task produjo log. (5) El JSON exportado omite el canonical YAML (`objects`). Tests: +6 (build_object_rows, build_html_report). | `scm/azdo/azdo_release_manifest_drift.py` (v1.0.3), `scm/azdo/tools.py`, `scm/tests/unit/test_azdo_release_manifest_drift.py`, `scm/azdo/README.md` |
| 2026-10-08 | 1.8.37 | **Fix opción 45 tras primer run real** — (1) crash `KeyError` en `print_summary` con diff vacío (`d.get`). (2) `parse_apply_log` soporta formato kubectl < 1.18 (`kind "name" configured`), verdicts `replaced`/`(dry run)` y el warning genérico antiguo → `OLD_APPLY_WARNING`. (3) Deployments API deduplicada por `release.id` — antes `--prev-release` podía devolver el mismo release por attempts. (4) Objetos con placeholders sin renderizar (`#{var}#`) → `UNRENDERED_NAME` INFO en vez de `NOT_APPLIED` MEDIUM. (5) Inputs ausentes ≡ defaults falsy → menos ruido en `task_inputs_changed`. (6) Tasks apply-typed detectadas por inputs (`command: apply` / `kubectl apply` inline) aunque el displayName no matchee. (7) Nuevas señales `APPLY_NO_VERDICTS`/`EMPTY_LOG` para diagnosticar logs sin salida. (8) `--show-skipped` — los ~120 pipelines sin stage/deploy se colapsan en conteo. Tests: +16. | `scm/azdo/azdo_release_manifest_drift.py` (v1.0.2), `scm/azdo/tools.py`, `scm/tests/unit/test_azdo_release_manifest_drift.py`, `scm/azdo/README.md` |
| 2026-10-08 | 1.8.36 | **Fix opción 45: org como URL + stage Producción** — (1) `AzdoClient`/`get_azdo_params` normalizan `--org`: el launcher pasa `azdo.organization_url` completa (`https://dev.azure.com/ORG`) y el cliente la concatenaba al host vsrm → HTTP 400. Ahora se extrae el nombre de la org en ambos puntos. (2) `find_stage_env` agrega match por sufijo `duction` → cubre stages `Production`/`Producción` sin depender del nombre exacto. Tests: +5. | `scm/azdo/scm_inspection_remediator.py`, `scm/azdo/azdo_release_manifest_drift.py`, `scm/tests/unit/test_azdo_release_manifest_drift.py`, `scm/azdo/README.md` |
| 2026-10-08 | 1.8.35 | **Nueva herramienta: Release Manifest Drift (opción 45)** — `azdo_release_manifest_drift.py` audita la consistencia del stage Production de pipelines CD: selección `all`/ID/lista/substring; último deploy efectivo vía Deployments API; logs de tasks de manifiesto (`get file k8-manifest`, `show manifest`, `kubectl apply`); diff def-vs-snapshot (tasks/versión/**inputs**/variables); detección de manipulación del cluster — `NOT_MANAGED_BY_APPLY` (sin anotación last-applied) y `EXTERNAL_MODIFICATION` (`configured` con YAML idéntico al release previo, flag `--prev-release`). Parser tolerante a ruido de log (`_YAMLISH` fallback), matching de tasks por regex configurable, paralelo por pipeline, export JSON/CSV, exit 2 si severidad ≥ HIGH. Launcher: prompts para `--definition-ids`, `--task-patterns`, `--prev-release`; defaults de stage/output específicos de la 45. Tests: +30. | `scm/azdo/azdo_release_manifest_drift.py`, `scm/azdo/tools.py`, `scm/tests/unit/test_azdo_release_manifest_drift.py`, `scm/azdo/README.md` |
| 2026-10-07 | 1.8.30 | **Pipeline Updater: default `allowOverride` → `false`** — El engine de definiciones (opción 41) creaba variables nuevas con `allowOverride: true` cuando la regla no lo especificaba ("Settable at release time" marcado). Default cambiado a `false`; `update` preserva el flag y reglas explícitas (`allowOverride: true`) siguen funcionando. Complementa v1.8.29 (que ya fijaba `false` en las reglas del remediator). Test `test_add_variable_default_allow_override` actualizado. | `scm/azdo/pipeline_updater/update_engine.py`, `scm/azdo/pipeline_updater/test_triggers.py`, `scm/azdo/README.md` |
| 2026-10-07 | 1.8.29 | **Fix `allowOverride` ("Settable at release time") en opción 44** — Las reglas `add`/`update` ahora llevan `allowOverride: false`: antes el updater de definiciones creaba variables nuevas con `allowOverride: true` por default (bug: todas quedaban setteables) y el engine de release forzaba `allowOverride: True` en `build_var_entry`. El engine ganó el campo `allowOverride` en extras de `global_vars`/`env_vars` (explícito → se aplica; ausente → preserva el flag actual; variable nueva → `true` por back-compat). El editor conserva el flag al revertir remove→update. Tests: +5 (`TestAllowOverride`). | `scm/azdo/scm_inspection_remediator.py`, `scm/azdo/pipeline_cd_update_release/pipeline_cd_update_release.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-07 | 1.8.28 | **SCM Inspection Remediator: resumen de cambios → `metadata.comment`** — El comentario simplificado (`rules_summary`) ahora viaja en `metadata.comment` en vez de `description`: ambos engines lo envían en el PUT (opción 41 → `definition.comment` = historial de revisiones de la definición; opción 42 → `release.comment`). `metadata.description` vuelve a ser solo el objetivo del template. El comentario `#` al inicio del archivo se conserva. | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-07 | 1.8.27 | **SCM Inspection Remediator: comentario simplificado en templates** — `rules_summary()` genera un resumen compacto de todos los cambios (`+var@Stage=val`, `~var@Stage`, `-var@release`, 🔒/🔓; secretos enmascarados, notas internas excluidas) que se escribe como comentario `#` en la primera línea del YAML **y** dentro de `metadata.description` — visible tanto al inspeccionar el archivo como al cargarlo con las opciones 41/42. Aplica a `pipe_cd_inspection_fix_*` (definición) y `release_inspection_fix_*` (release). Tests: +1 (`test_comentario_simplificado_en_yaml`). | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-07 | 1.8.26 | **SCM Inspection Remediator: existencia verificada contra el release** — `build_actionables` ahora acepta `release` y comprueba también las variables de la instancia inspeccionada. Fix real: una variable solo en el snapshot del release (ausente en la definición, p. ej. `tuSecret`) iba a "manual / ya ausente" y no podía eliminarse — ahora genera `remove`/`update` con nota "existe solo en el release" (el engine opción 42 la aplica; en la definición es no-op). `RULE_1_SECRET` ya no manda a manual cuando el valor no es legible: toma el valor del release si existe y aplica `isSecret: true` preservando el valor; solo queda manual si la variable no existe en definición ni en release. Tests: +6 (`TestReleaseFallback`). | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-06 | 1.8.25 | **Aplicación a release via engine existente (opción 42)** — La opción 44 ya no hace PUT directo: genera `release_inspection_fix_<relId>_<ts>.yaml` en formato `pipeline_cd_update_release` y lo aplica por subprocess (backup + tabla de cambios + PUT del engine). El engine ganó campos `isSecret`/`action: remove` por variable y preserva `isSecret` al actualizar vars secretas (bugfix). | `scm/azdo/scm_inspection_remediator.py`, `scm/azdo/pipeline_cd_update_release/pipeline_cd_update_release.py`, `scm/azdo/tools.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-06 | 1.8.24 | **SCM Inspection Remediator: menú en bucle + redeploy del stage** — El menú de aplicación reaparece tras cada acción (hasta `0`/`1`); tras aplicar al release se ofrece re-correr el deploy del stage inspeccionado (`PATCH environments/{id} status=inProgress`; `--redeploy` en CLI). Nota UX: el YAML es solo para la definición; el release usa PUT directo. `AzdoClient._send` unifica GET/PUT/PATCH. | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-06 | 1.8.23 | **SCM Inspection Remediator: prompt de Release ID interactivo** — El modo interactivo ahora pregunta el Release ID tras el Definition ID (Enter = último run del stage; un ID específico inspecciona ese release y queda como destino default de las opciones `4`–`6`). Input no numérico → fallback al último. Hint CLI del submenú con ejemplos `--release-id`/`--target`. | `scm/azdo/scm_inspection_remediator.py`, `scm/azdo/tools.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-06 | 1.8.22 | **SCM Inspection Remediator: aplicar a un Release (instancia)** — Nuevo destino de aplicación además de la definición: PUT directo sobre `release.variables`/`environments[].variables` del último release descubierto o uno específico. Soporta `add`/`update`/`remove`/`isSecret` (incl. desmarcar), backup en `outcome/backups/` y confirmación `[s/N]`. Menú con opciones `4`/`5`/`6` y flag `--target definition|release|both` en CLI. Sección 9 del README actualizada. | `scm/azdo/scm_inspection_remediator.py`, `scm/azdo/tools.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md` |
| 2026-10-06 | 1.8.21 | **Docs: sección funcional de la opción 44** — Nueva sección `9 · SCM Inspection Remediator` con flujo interactivo, menú de confirmación completo, opciones del editor y detalle de `[r]` (recarga ajustes desde las violaciones del Definition ID del pipeline CD, sin re-consultar AzDO). | `scm/azdo/README.md` |
| 2026-10-06 | 1.8.20 | **SCM Inspection Remediator: `[r]` recargar ajustes** — Nueva opción en la confirmación: reconstruye los ajustes candidatos desde las violaciones conservando los valores pendientes capturados y los removes; descarta las ediciones manuales de `e`/`v`. | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py` |
| 2026-10-06 | 1.8.19 | **SCM Inspection Remediator: toggle isSecret (`k`)** — En el editor de ajustes (`e`/`v`), `k` marca una variable como secreta (`isSecret: true`) o la desmarca explícitamente (`isSecret: false` — el updater aplica el desmarque). Indicadores 🔒/🔓 en la tabla; no aplica a `remove`. | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py` |
| 2026-10-06 | 1.8.18 | **SCM Inspection Remediator: acción real en notas + edición puntual** — (1) Las reglas reflejan lo que el updater hará: add sobre existente → update ("ya existe — se actualiza"), mismo valor → "sin cambio" (sin regla), update/remove inexistente → omitida/ya ausente, update con otro valor → "sobrescribe valor actual" vs "existía vacía — se rellena"; la fuente de paridad excluye el stage destino (adiós "copiado de Production" sobre Production). (2) `[v]` en la confirmación: edición puntual por `nombre` o `nombre@stage`. (3) Contraste: prompts del editor/captura en bold con colores (cyan Enter / green texto / red e / yellow i). | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py` |
| 2026-10-06 | 1.8.17 | **SCM Inspection Remediator: 'Ajustes candidatos' + edición uno-a-uno** — La sección de acciones se renombra a "Ajustes candidatos" con la misma tabla coloreada del resumen. Nueva opción `[e]` en la confirmación: recorre cada ajuste permitiendo conservar (Enter), cambiar valor (texto), eliminar variable (`e`) o descartar el ajuste (`i`). | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py` |
| 2026-10-06 | 1.8.16 | **SCM Inspection Remediator: UI Rich + remove/ignorar por variable** — (1) Migración completa a Rich: panel de descubrimiento, tabla de violaciones por severidad, resumen final con acciones en colores de alto contraste (add=verde, update=amarillo, remove=rojo, 🔒=isSecret, TBD=cyan); fallback ASCII en cp1252. (2) Variables pendientes ahora aceptan `e`=eliminar (regla `action: remove` donde exista) e `i`=ignorar, además de Enter=TBD y valor; `--remove NAME` para CLI. (3) El ciclo de corrección permite revertir entre valor/eliminar/manual. | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py` |
| 2026-10-06 | 1.8.15 | **SCM Inspection Remediator: isSecret en adds por paridad + warning cross-ambiente** — (1) Fix: variables marcadas por `RULE_1_SECRET` se agregan ahora con `isSecret: true` cuando llegan por paridad a otro stage (ej. `ksaSecretManager` en Production-Rollback quedaba como texto plano). (2) Warning en plan/resumen cuando el valor se copia entre stages de ambientes distintos (`⚠ origen 'Develop' es ambiente 'dev' ≠ destino 'prod'`) — evita propagar valores de dev a producción sin revisión. | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py` |
| 2026-10-05 | 1.8.13 | **SCM Inspection Remediator: resumen final + corrección antes de aplicar** — Tras el ciclo de valores pendientes se muestra el `Resumen FINAL de cambios` (regla, scope/stage y valor; secretos enmascarados, `TBD` visible). Confirmación: Enter genera el template, `[c]` permite corregir valores (Enter conserva / texto reemplaza / `s` regresa a manual) reconstruyendo las reglas, `[0]` sale. El resumen también se imprime en modo no interactivo antes de `--apply`/`--dry-run`. | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py` |
| 2026-10-05 | 1.8.12 | **SCM Inspection Remediator: ciclo de valores pendientes con default `TBD`** — Las variables sin valor fuente (paridad sin origen, contenido vacío, variables a nivel pipeline como `tuSecret`) ahora se recorren en un ciclo interactivo: Enter = `TBD`, valor escrito = se usa, `s`/`skip` = queda manual. Modo no interactivo: flag `--tbd` rellena todas las pendientes con `TBD`. `build_actionables` expone `pending` ({var: {scope, stages}}) y los helpers `collect_pending_values`/`fill_pending_default`. Tras resolver valores se reconstruyen las reglas y el template incluye los `add`/`update` resultantes. Tests: +7 en `test_scm_inspection_remediator.py` | `scm/azdo/scm_inspection_remediator.py`, `scm/tests/unit/test_scm_inspection_remediator.py`, `scm/azdo/README.md`, `VERSION`, `README.version.md` |
| 2026-10-05 | 1.8.11 | **Opción 44: SCM Inspection Remediator** — Nueva tool `scm_inspection_remediator.py` con submenú (interactivo/CLI). Descubre violaciones del stage 'SCM Inspection' de un pipeline CD (mismo descubrimiento que `inspection_errors.sh` portado a Python: definición → último deployment → release → logs de tareas → parser de bloques `##[warning]/##[error]`). Convierte violaciones en reglas `update.variables` del motor de templates: `RULE_1_SECRET` → `isSecret: true` preservando el valor actual; paridad → `add` con valor copiado del stage origen (`(de Stage)` del detalle); contenido → `update` con valor de otro stage; sin fuente → pendiente manual o `--set NAME=VALUE`. Genera `pipe_cd_inspection_fix_<id>_<ts>.yaml` en outcome resuelto y lo aplica llamando directamente a `pipeline_updater` (opción 41) con dry-run/aplicar/solo-template. Además `inspection_errors.sh` genera columna `ACTION` en sus CSVs. Tests: `test_scm_inspection_remediator.py` (14) | `scm/azdo/scm_inspection_remediator.py` (nuevo), `scm/azdo/tools.py`, `scm/terminal/azdo_check_scm_inspection/inspection_errors.sh`, `scm/tests/unit/test_scm_inspection_remediator.py` (nuevo), `scm/azdo/README.md` |
| 2026-09-10 | 1.7.73 | **Pipeline Drift Analyzer: sin límite de descarga** — `get_release_definitions` ahora implementa paginación mediante `continuationToken` de la API de Azure DevOps. Se piden páginas de 200 resultados hasta agotar todos los pipelines, eliminando el límite anterior de `$top: 500`. Permite analizar drift en proyectos con más de 500 release pipelines. | `azdo_pipeline_drift.py` |
| 2026-08-08 | 1.0.9 | **Pipeline Updater: acción `move`** — Mover pipelines CD entre carpetas de Azure DevOps via template YAML. (1) `update.pipeline` con `action: "move"` cambia el campo `path` de la definición de release. (2) Placeholder `{current}`: se reemplaza por el path actual del pipeline, permitiendo mover sin conocer el path previo (ej: `path: '\Decomiso{current}'`). (3) Path absoluto: también soporta paths fijos sin `{current}`. (4) `TemplateParser.get_pipeline_path()`: nuevo método. (5) `ParallelExecutor`: ramifica al flujo de move, resuelve `{current}`, setea `definition["path"]` y envía via PUT. (6) Snapshot automático antes de mover. (7) Template: `pipe_cd_move_to_folder.yaml`. (8) 27 tests en `test_template_move_to_folder.py` | `scm/templates/pipe_cd_move_to_folder.yaml` (nuevo), `scm/azdo/pipeline_updater/template_parser.py`, `scm/azdo/pipeline_updater/parallel_executor.py`, `scm/azdo/pipeline_updater/test_template_move_to_folder.py` (nuevo), `scm/azdo/pipeline_updater/__init__.py`, `scm/azdo/pipeline_updater/README.md`, `README.md` |
| 2026-06-03 | 1.3.7 | **Excel Diff Lado-a-Lado línea por línea** — Hoja "Diff Lado-a-Lado": una fila por línea de comparación con columnas `# Orig │ ◀ origen │ # Dest │ ▶ destino`. Colores por tipo: delete=rojo, insert=verde, replace=amarillo, equal=gris. Fila separadora por archivo con color de severidad. `freeze_panes` en fila 2 | `azdo_repo_properties_branch_diff.py` |
| 2026-06-03 | 1.3.6 | **Vista lado-a-lado sin líneas vacías entre filas** — `show_lines=False` en la tabla Rich elimina el separador horizontal entre cada fila | `azdo_repo_properties_branch_diff.py` |
| 2026-06-03 | 1.3.5 | **Fix orden columnas y números de línea en vista lado-a-lado** — Columna izquierda = source/origen, derecha = target/destino. Números de línea independientes por lado (`ln_src`/`ln_tgt`): incrementa solo en el lado donde existe la línea | `azdo_repo_properties_branch_diff.py` |
| 2026-06-03 | 1.3.4 | **Fix descarga de ambas ramas para comparativa** — `_process_changes()` ahora descarga siempre `sc` y `tc` (antes ponía `None` para ADD/DELETE). Re-evalúa `change_type` con contenido real: ambos presentes+distintos→EDIT activa vista lado-a-lado | `azdo_repo_properties_branch_diff.py` |
| 2026-06-03 | 1.3.3 | **Vista lado-a-lado en Properties Branch Diff v1.1.0** — Reemplaza unified diff por tabla Rich 4 columnas (`# │ origen │ # │ destino`). `build_side_by_side_rows()` usa `SequenceMatcher`; `_print_side_by_side()` muestra contexto configurable con separador `···`. **Fix exit codes quality gate** — `subprocess.run(check=True)` → `result.returncode`: 0=OK, 1=HIGH, 2=CRITICAL son resultados válidos; >2 es error real. Aplica en `run_tool`, `run_all`, `run_all_json` | `azdo_repo_properties_branch_diff.py`, `tools.py` |
| 2026-06-03 | 1.3.2 | **Nueva herramienta 20: `azdo_repo_branch_diff.py`** — Informe ejecutivo de impacto de cambios entre dos ramas de cualquier repositorio AzDO. Motor de clasificación de riesgo por archivo (24 reglas regex): CRITICAL (Dockerfile/Jenkinsfile/azure-pipelines/k8s/secretos), HIGH (pom.xml/package.json/migraciones SQL/application.yml), MEDIUM (código fuente .java/.py/.ts), LOW (tests/docs). Score 0-100 = suma ponderada por riesgo + bonus log(commits). Secciones del informe: Resumen Ejecutivo (score + barra visual), Distribución por categoría (barras %) , Archivos (tabla con emoji de riesgo), Commits (SHA/autor/fecha/mensaje), Estadísticas por autor, Recomendaciones automáticas. Export JSON/CSV/Excel (3 pestañas: Archivos/Commits/Resumen). Exit 0=OK/1=HIGH/2=CRITICAL. 63 pruebas unitarias. `tools.py` v1.3.2: herramienta 20 en grupo `quality` con handlers `--top-files/--top-commits/--no-commits/--no-authors` | `azdo_repo_branch_diff.py` (nuevo), `test_azdo_repo_branch_diff.py` (nuevo), `tools.py`, `config.json.template`, `README.md` |
| 2026-06-03 | 1.3.1 | **Nueva herramienta 19: `azdo_repo_properties_branch_diff.py`** — Compara la configuración de un componente (carpeta) entre dos ramas de un repositorio de propiedades en AzDO. Detecta diferencias que puedan impactar la calidad de un despliegue productivo. Severidad: CRITICAL (archivo eliminado en source), HIGH (contenido cambiado), MEDIUM (archivo nuevo), LOW (solo formato/comentarios), NONE (idéntico). Modo interactivo: selección de repo, componente y ramas con prompts Rich. Export JSON/CSV/Excel (3 pestañas). Exit code como quality gate (0=OK, 1=HIGH, 2=CRITICAL). 36 pruebas unitarias cubren diff engine, severity classifier, fallback por items API. `tools.py` v1.3.1: grupo `quality`, herramienta 19 con handlers `--source/--target/--component/--context/--severity/--only-diff/--no-content`. `config.json.template` con bloque `properties_branch_diff` | `azdo_repo_properties_branch_diff.py` (nuevo), `test_azdo_repo_properties_branch_diff.py` (nuevo), `tools.py`, `config.json.template`, `README.md` |
| 2026-05-09 | 1.7.2 | **JSON export universal + opción B (Ejecutar Todo + JSON):** (1) `cicd_inventory.py` — `--output json` exporta repos/ci/cd/relations en un único JSON con metadata; (2) `cicd_inventory_gke_pipelines.py` — ídem, exporta pipelines GKE con stages y último release; (3) `cicd_inventory_pending_approvals.py` — ídem, exporta aprobaciones pendientes; (4) `cicd_inventory_hotfix_branches.py` — ídem, exporta ramas hotfix; (5) `tools.py` — nueva opción **B** `Ejecutar Todo + JSON` que corre las 15 herramientas batcheables forzando `--output json` (tools con cache JSON se ejecutan sin `--output`); opción **A** ampliada de 4 → 15 tools; `_JSON_FORMAT_TOOLS` y `_CACHE_JSON_TOOLS` como constantes de clasificación | `cicd_inventory.py`, `cicd_inventory_gke_pipelines.py`, `cicd_inventory_pending_approvals.py`, `cicd_inventory_hotfix_branches.py`, `tools.py`, `README.md` |
| 2026-05-07 | 1.7.1 | `cicd_pipeline_status.py`: (1) Fix conteo pipelines CI/CD — paginación via `x-ms-continuationtoken`: `api_get_paginated()` acumula todas las páginas (`$top=1000` por página) en lugar de `$top=5000` en única llamada que ignoraba páginas adicionales; (2) Umbral de deprecación cambiado de 90 → **365 días** (1 año) para CI y CD | `cicd_pipeline_status.py`, `test_cicd_pipeline_status.py`, `README.md` |
| 2026-05-06 | 1.7.0 | Herramienta 18 `cicd_pipeline_status.py`: (1) Cache JSON en `outcome/.cache/` — TTL 24h, `--force-refresh`, `--use-cache-only`; (2) Excel con 3 pestañas: Datos / Resumen / Charts — 4 gráficos nativos openpyxl: Donut CI, Donut CD, Barras agrupadas CI vs CD por bucket de inactividad, Barras resumen ejecutivo | `cicd_pipeline_status.py`, `README.md` |
| 2026-05-05 | 1.6.9 | Nueva herramienta 18: `cicd_pipeline_status.py` — Reporte consolidado CI+CD: totales, deprecados, última actualización, estado. CI usa `queueStatus` (enabled/paused/disabled). CD infiere estado por días sin releases. `--inactive-days` configurable, `--type ci/cd/all`, `--only-deprecated`. Paralelo con workers para CD | `cicd_pipeline_status.py` (nuevo), `tools.py`, `README.md` |
| 2026-05-04 | 1.6.8 | Nueva herramienta 2b: `azdo_branch_lock_checker.py` — Lista ramas bloqueadas (isLocked) por repositorio. Tabla: Repo / Rama / Bloqueado por. Exporta json/csv/excel. Progress bar por repo | `azdo_branch_lock_checker.py` (nuevo), `tools.py`, `README.md` |
| 2026-04-30 | 1.6.7 | Fixes y mejoras en `cicd_inventory_prod_deploy.py`: (1) Fix crítico — Deployments API usa `completedOn` no `finishedOn`; (2) Artefactos: `build_id`/`build_number` ahora usan `version.id`/`version.name`; (3) Nueva columna `git_commit_sha` para artefactos tipo Git separados del CI Build; (4) Nuevas columnas `refresh_release_*` — detecta releases más recientes con el mismo build (config/variable refresh); (5) `deadline_status`, `days_since_prod_deploy` e `is_obsolete` recalculados con fecha efectiva del refresh release; (6) Error logging explícito por API call, fallback de environments desde deployments, fallback a releases expandidos cuando Deployments API no retorna prod | `cicd_inventory_prod_deploy.py`, `README.md` |
| 2026-04-29 | 1.6.6 | Nueva herramienta 17: `cicd_inventory_prod_deploy.py` — Rastrea último despliegue exitoso a Producción por pipeline CD. Lee cache CD previo, consulta releases con environments+artifacts. 20 columnas: pipeline, último release, deploy a prod (fecha/status/release), commit SHA, build ID/number, deadline (Vigente/Actualizar release), days_since_prod_deploy. Fix IndexError charts, PYTHONUTF8=1 en subprocess, --run-inventory con --offline | `cicd_inventory_prod_deploy.py` (nuevo), `cicd_inventory_health_score.py`, `tools.py`, `README.md`, `docs/Plan_Trabajo_Prod_Deploy.md` |
| 2026-04-27 | 1.6.5 | Pestaña Charts en Excel de Health Score: 13 gráficos nativos Excel + 1 tabla heatmap. P1 Stacked Bar, P2 Pie ratings, P3 Grouped Bar DORA, P5 Scatter score vs uso, P6 Treemap tecnologías, P7 Pareto críticos, P8 Tendencia histórica, P9 Riesgo Tecnológico por Área (combo bar+line con colores por salud), P10 Sankey Tecnología→Recomendación (stacked bar), P11 Radar DORA por Área (5 dimensiones top 5 áreas), P12 Bubble Esfuerzo vs Impacto (antigüedad×uso, tamaño=fallos), P13 Histograma MTTR (bins con gradiente), P14 Run Chart Fallos con UCL/LCL (desde cache histórico), Heatmap Technology Status vs Rating. Fix normalize_org. Flag --run-inventory con spinner. make_dist.ps1 incluye .cache/ en ZIP | `cicd_inventory_health_score.py`, `cicd_inventory_ci_detailed.py`, `cicd_inventory_cd_detailed.py`, `tools.py`, `README.md`, `make_dist.ps1` |
| 2026-04-26 | 1.6.4 | Implementación completa de 3 herramientas: `cicd_inventory_ci_detailed.py` (14), `cicd_inventory_cd_detailed.py` (15), `cicd_inventory_health_score.py` (16). Cache-first, multihilo, Rich spinners/progress, Excel 3 pestañas, scoring DORA/SRE 5 dimensiones, resumen final | `cicd_inventory_ci_detailed.py`, `cicd_inventory_cd_detailed.py`, `cicd_inventory_health_score.py`, `tools.py`, `README.md` |
| 2026-04-26 | 1.6.3 | Plan de trabajo para Pipeline Health Score replanteado con modelo basado en DORA 2023, Google SRE, Microsoft DevOps Maturity y Accelerate. 5 dimensiones: Recency(20), Reliability(25), Usage(20), Freshness(15), TechDebt(20) | `docs/Plan_Trabajo_Pipeline_Health.md`, `README.md` |
| 2026-04-10 | 1.6.2 | Paso 3 optimizado: busca candidatos por nombre primero, descarga solo detalles de candidatos (vs 500 CDs completos). Usa `vsrm.dev.azure.com` para Release APIs | `azdo_pr_pipeline_analyzer.py`, `README.md` |
| 2026-04-10 | 1.3.1 | Launcher: herramienta 1b `azdo_pr_pipeline_analyzer.py` añadida al menú con prompts interactivos | `tools.py`, `README.md` |
| 2026-04-10 | 1.6.1 | Fix Release APIs: usa `vsrm.dev.azure.com` en lugar de `dev.azure.com`. Default threads=20 | `azdo_pr_pipeline_analyzer.py` |
| 2026-04-10 | 1.6.0 | Nueva herramienta 1b: `azdo_pr_pipeline_analyzer.py` — Análisis PRs multi-rama + CD + releases con reporte de tiempos | `azdo_pr_pipeline_analyzer.py` (nuevo), `README.md` |
| 2026-03-26 | 1.4.0 | `make_dist.ps1` publica releases en GitHub via API (ZIP como asset) | `make_dist.ps1` |
| 2026-03-25 | 1.3.1 | Script PowerShell `make_dist.ps1` para generar ZIP distribuible | `make_dist.ps1` (nuevo en raiz) |
| 2026-03-31 | 1.3.0 | Scanners 7-8: Refactor con argumentos CLI y soporte config.json | `azdo_scan_pipeline_logs.py`, `azdo_scan_repos_vulnerabilities.py`, `tools.py`, `README.md` |
| 2026-03-25 | 1.3.0 | Nueva herramienta 5: `azdo_release_deep_dive.py` — deep-dive por `--release-id` | `azdo_release_deep_dive.py` (nuevo), `tools.py` |
| 2026-03-25 | 1.3.0 | Columna `Def ID` añadida a tabla Rich y salida texto de CD Health | `azdo_release_cd_health.py` |
| 2026-03-31 | 1.2.0 | Scanners 7-8: Barras de progreso con rich (spinner + progress bar) | `azdo_scan_pipeline_logs.py`, `azdo_scan_repos_vulnerabilities.py` |
| 2026-03-31 | 1.2.0 | Herramientas 7-8: Scanners de seguridad para logs y dependencias vulnerables | `azdo_scan_pipeline_logs.py`, `azdo_scan_repos_vulnerabilities.py`, `tools.py`, `README.md` |
| 2026-03-25 | 1.2.0 | `--repo` / `-r` añadido como alias de `--filter` en tools 3 y 4 | `azdo_release_cd_health.py`, `azdo_pipeline_drift.py` |
| 2026-03-25 | 1.2.0 | Corrección `--filter` → `--repo` en TOOLS dict de launcher; handler `--release-id` | `tools.py` |
| 2026-03-26 | 1.1.0 | Nueva herramienta 6: `azdo_task_validator.py` — Validación DevSecOps de releases | `azdo_task_validator.py` (nuevo), `tools.py`, `README.md` |
| 2026-04-13 | 1.2.1 | Wildcard en `--branch`: soporta `release/*`, `release/v*` etc. Descarga PRs sin filtro de branch y filtra localmente con `fnmatch` | `azdo_pr_master_checker.py`, `README.md` |
| 2026-04-13 | 1.2.0-fix | Skip None cd_detail en artifact source matching (fix AttributeError) | `azdo_pr_master_checker.py`, `azdo_pr_pipeline_analyzer.py` |
| 2026-04-10 | 1.2.0 | CD fetching optimizado: candidatos por nombre primero, descarga solo candidatos, artifact source matching, threads=20, paginación release defs | `azdo_pr_master_checker.py`, `README.md` |
| 2026-03-25 | 1.1.0 | Refactor PR fetch: endpoint cross-project bulk (1 llamada vs N repos) | `azdo_pr_master_checker.py` |
| 2026-03-25 | 1.1.0 | Pre-fetch paralelo de CD details; `DEFAULT_THREADS` aumentado a 16 | `azdo_pr_master_checker.py` |
| 2026-03-25 | 1.0.1 | Default PR status cambiado de `all` a `active` | `azdo_pr_master_checker.py`, `config.json.template`, `tools.py` |
| 2026-03-25 | 1.0.1 | API version corregida a `7.1` para repos/políticas (fix HTTP 400) | `azdo_pr_master_checker.py`, `azdo_branch_policy_checker.py` |
