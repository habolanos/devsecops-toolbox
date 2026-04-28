# Azure DevOps Tools — SCM Toolbox

Colección de herramientas Python para auditoría y análisis de pipelines, políticas de ramas y pull requests en **Azure DevOps**. Todas las herramientas usan la API REST de AzDO v7.2 con autenticación por PAT y ofrecen salida enriquecida en consola (Rich) y exportación a JSON / CSV / Excel.

---

## Contenido del directorio

```
devsecops-toolbox/scm/azdo/
├── tools.py                       # Launcher interactivo unificado (punto de entrada)
├── azdo_pr_master_checker.py      # Herramienta 1 — PRs hacia master + validación CD
├── azdo_pr_pipeline_analyzer.py   # Herramienta 1b — Análisis PRs multi-rama + CD + releases
├── azdo_branch_policy_checker.py  # Herramienta 2 — Auditoría de políticas de ramas
├── azdo_release_cd_health.py      # Herramienta 3 — Score de salud de Release Pipelines
├── azdo_pipeline_drift.py         # Herramienta 4 — Detección de drift en pipelines CD
├── azdo_release_deep_dive.py      # Herramienta 5 — Deep-dive por Release Definition ID
├── azdo_task_validator.py         # Herramienta 6 — Validación DevSecOps de releases
├── azdo_scan_pipeline_logs.py     # Herramienta 7 — Scanner de logs de pipelines CI
├── azdo_scan_repos_vulnerabilities.py # Herramienta 8 — Scanner de dependencias vulnerables
├── config.json.template           # Plantilla de configuración (copiala como config.json)
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

### 1. Crear `config.json`

```bash
cp config.json.template config.json
```

Edita `config.json` con tus valores reales. **Este archivo está en `.gitignore` y nunca se sube al repositorio.**

### 2. Estructura de `config.json`

```json
{
  "organization": {
    "url":     "https://dev.azure.com/<TU_ORGANIZACION>",
    "project": "<TU_PROYECTO>",
    "pat":     "<TU_PAT_TOKEN>"
  },
  "defaults": {
    "timezone":      "America/Mazatlan",
    "threads":       8,
    "output_format": null,
    "debug":         false
  },
  "tools": {
    "pr_master_checker":   { "target_branch": "master", "pr_status": "all", "stage_name": "validador" },
    "branch_policy_checker": { ... },
    "release_cd_health":   { "top_releases": 15, "sort": "score", "diagram": false },
    "pipeline_drift":      { "min_severity": null, "sort": "severity" }
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

## Exportación de resultados

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
| 2026-04-27 | 1.6.5 | Pestaña Charts en Excel de Health Score: 13 gráficos nativos Excel + 1 tabla heatmap. P1 Stacked Bar, P2 Pie ratings, P3 Grouped Bar DORA, P5 Scatter score vs uso, P6 Treemap tecnologías, P7 Pareto críticos, P8 Tendencia histórica, P9 Riesgo Tecnológico por Área (combo bar+line con colores por salud), P10 Sankey Tecnología→Recomendación (stacked bar), P11 Radar DORA por Área (5 dimensiones top 5 áreas), P12 Bubble Esfuerzo vs Impacto (antigüedad×uso, tamaño=fallos), P13 Histograma MTTR (bins con gradiente), P14 Run Chart Fallos con UCL/LCL (desde cache histórico), Heatmap Technology Status vs Rating. Fix normalize_org. Flag --run-inventory con spinner. make_dist.ps1 incluye .cache/ en ZIP | `azdo_pipeline_health_score.py`, `cicd_inventory_ci_detailed.py`, `cicd_inventory_cd_detailed.py`, `tools.py`, `README.md`, `make_dist.ps1` |
| 2026-04-26 | 1.6.4 | Implementación completa de 3 herramientas: `cicd_inventory_ci_detailed.py` (14), `cicd_inventory_cd_detailed.py` (15), `azdo_pipeline_health_score.py` (16). Cache-first, multihilo, Rich spinners/progress, Excel 3 pestañas, scoring DORA/SRE 5 dimensiones, resumen final | `cicd_inventory_ci_detailed.py`, `cicd_inventory_cd_detailed.py`, `azdo_pipeline_health_score.py`, `tools.py`, `README.md` |
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
