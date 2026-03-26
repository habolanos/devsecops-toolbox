# Azure DevOps Tools — SCM Toolbox

Colección de herramientas Python para auditoría y análisis de pipelines, políticas de ramas y pull requests en **Azure DevOps**. Todas las herramientas usan la API REST de AzDO v7.2 con autenticación por PAT y ofrecen salida enriquecida en consola (Rich) y exportación a JSON / CSV / Excel.

---

## Contenido del directorio

```
devsecops-toolbox/scm/azdo/
├── tools.py                       # Launcher interactivo unificado (punto de entrada)
├── azdo_pr_master_checker.py      # Herramienta 1 — PRs hacia master + validación CD
├── azdo_branch_policy_checker.py  # Herramienta 2 — Auditoría de políticas de ramas
├── azdo_release_cd_health.py      # Herramienta 3 — Score de salud de Release Pipelines
├── azdo_pipeline_drift.py         # Herramienta 4 — Detección de drift en pipelines CD
├── azdo_release_deep_dive.py      # Herramienta 5 — Deep-dive por Release Definition ID
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
| `azdo_branch_policy_checker` | `Code (Read)` · `Project and Team (Read)` |
| `azdo_release_cd_health` | `Release (Read)` |
| `azdo_pipeline_drift` | `Release (Read)` |

> Un PAT con `Code (Read)` + `Release (Read)` + `Project and Team (Read)` cubre **todas** las herramientas.

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
| 2026-03-25 | 1.3.0 | Nueva herramienta 5: `azdo_release_deep_dive.py` — deep-dive por `--release-id` | `azdo_release_deep_dive.py` (nuevo), `tools.py` |
| 2026-03-25 | 1.3.0 | Columna `Def ID` añadida a tabla Rich y salida texto de CD Health | `azdo_release_cd_health.py` |
| 2026-03-25 | 1.2.0 | `--repo` / `-r` añadido como alias de `--filter` en tools 3 y 4 | `azdo_release_cd_health.py`, `azdo_pipeline_drift.py` |
| 2026-03-25 | 1.2.0 | Corrección `--filter` → `--repo` en TOOLS dict de launcher; handler `--release-id` | `tools.py` |
| 2026-03-25 | 1.1.0 | Refactor PR fetch: endpoint cross-project bulk (1 llamada vs N repos) | `azdo_pr_master_checker.py` |
| 2026-03-25 | 1.1.0 | Pre-fetch paralelo de CD details; `DEFAULT_THREADS` aumentado a 16 | `azdo_pr_master_checker.py` |
| 2026-03-25 | 1.0.1 | API version corregida a `7.1` para repos/políticas (fix HTTP 400) | `azdo_pr_master_checker.py`, `azdo_branch_policy_checker.py` |
| 2026-03-26 | 1.4.0 | `make_dist.ps1` publica releases en GitHub via API (ZIP como asset) | `make_dist.ps1` |
| 2026-03-25 | 1.3.1 | Script PowerShell `make_dist.ps1` para generar ZIP distribuible | `make_dist.ps1` (nuevo en raiz) |
| 2026-03-25 | 1.0.1 | Default PR status cambiado de `all` a `active` | `azdo_pr_master_checker.py`, `config.json.template`, `tools.py` |
