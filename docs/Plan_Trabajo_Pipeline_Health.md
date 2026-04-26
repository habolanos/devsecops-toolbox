# Plan de Trabajo: Pipeline Health & Maintenance Tracking

## Fecha: 2026-04-26
## Autor: Harold Adrian Bolanos Rodriguez
## Version: 1.0.0

---

## 1. OBJETIVO

Implementar 3 nuevas herramientas para Azure DevOps que permitan:
1. **Inventario completo de Pipelines CI** con metadatos de ejecución y tecnología
2. **Inventario completo de Pipelines CD (Release Definitions)** con ambientes y salud
3. **Reporte de Salud (Health Score)** de pipelines con scoring multi-dimensional

---

## 2. ESTRUCTURAS DE DATOS REQUERIDAS

### 2.1 Pipeline CI Inventory (`cicd_inventory_ci_detailed.py`)

Basado en el análisis del archivo `Pipelines CI.csv`, las columnas requeridas son:

| Columna | Fuente Azure DevOps API | Descripción |
|---------|------------------------|-------------|
| `name` | Build Definitions API (`name`) | Nombre del pipeline CI |
| `pipelineCreationDate` | Build Definitions API (`createdDate`) | Fecha de creación del pipeline |
| `ejecuciones` | Build API (count con `definitions` filter) | Total de ejecuciones históricas |
| `modificaciones` | Build API (count de builds) o audit | Veces que ha sido modificado |
| `arqType` | Build Definition (`process.type`: yaml vs designerJson) | Tipo de arquitectura: yaml / designerJson |
| `Breakers` | YAML parsing / custom logic | Estado de breakers: Habilitados / No aplica |
| `lastYamlModifier` | Git history del archivo YAML o `authoredBy` | Último modificador del YAML |
| `lastPipelineModifier` | Build Definition (`authoredBy`) | Último modificador de la definición |
| `lastExecution` | Build API (`finishTime` del último build) | Fecha última ejecución |
| `lastExecutionState` | Build API (`status`) | Estado de la última ejecución |
| `lastExecutionResult` | Build API (`result`) | Resultado: succeeded, failed, canceled |
| `repositoryName` | Build Definition (`repository.name`) | Repositorio asociado |
| `repositoryUrl` | Build Definition (`repository.url`) | URL del repositorio |
| `defaultBranch` | Build Definition (`repository.defaultBranch`) | Rama por defecto |

**Endpoints Azure DevOps:**
- `GET https://dev.azure.com/{org}/{project}/_apis/build/definitions`
- `GET https://dev.azure.com/{org}/{project}/_apis/build/builds?definitions={id}&$top=1`
- `GET https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repoId}/items?path={yamlPath}`

### 2.2 Pipeline CD Inventory (`cicd_inventory_cd_detailed.py`)

Basado en el análisis del archivo `Pipelines CD.csv`, las columnas requeridas son:

| Columna | Fuente Azure DevOps API | Descripción |
|---------|------------------------|-------------|
| `id` | Release Definitions API (`id`) | ID del pipeline CD |
| `name` | Release Definitions API (`name`) | Nombre del release definition |
| `path` | Release Definitions API (`path`) | Ruta/carpeta en Azure DevOps |
| `url` | Release Definitions API (`url`) | URL directa del pipeline |
| `createdOn` | Release Definitions API (`createdOn`) | Fecha de creación |
| `environmentsCount` | Release Definitions API (count de `environments`) | Total de ambientes |
| `environments` | Release Definitions API (`environments[].name`) | Lista de ambientes separados por `/` |
| `lastReleaseDate` | Releases API (`createdOn` del último release) | Última ejecución |
| `lastReleaseStatus` | Releases API (`status`) | Estado del último release |
| `isObsolete` | Name analysis (contains "OBSOLETO", "obsoleto", "_old", "legacy-") | Indica si está marcado como obsoleto |

**Endpoints Azure DevOps:**
- `GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions`
- `GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases?definitionId={id}&$top=1`

### 2.3 Pipeline Health Report (`azdo_pipeline_health_score.py`)

Nuevo reporte con scoring multi-dimensional basado en estándares de la industria:

| Columna | Fuente / Cálculo | Descripción |
|---------|-----------------|-------------|
| `pipeline_name` | Build/Release Definition | Nombre del pipeline |
| `pipeline_type` | Static (CI/CD) | Tipo: CI o CD |
| `pipeline_path` | Definition (`path`) | Ruta/carpeta |
| `technology` | Name analysis / YAML parsing | Tecnología detectada: Spring Boot, Angular, .NET, PHP, Kotlin, etc. |
| `technology_status` | Heuristics + CVE/EOL databases | Moderna / Mantenimiento / EOL / Obsoleta |
| `health_score` | Calculated (0-100) | Score compuesto de salud |
| `recency_score` | Calculated (0-35) | Días desde última ejecución (35 pts = <7 días) |
| `stability_score` | Calculated (0-25) | Tasa de éxito de últimas 10 ejecuciones |
| `usage_score` | Calculated (0-20) | Frecuencia de ejecución mensual |
| `freshness_score` | Calculated (0-20) | Días desde última modificación (20 pts = <30 días) |
| `reliability_score` | Calculated (0-25) | Tasa de éxito + MTTR (DORA Change Failure Rate) |
| `usage_score` | Calculated (0-20) | Frecuencia de ejecución (DORA Deployment Frequency) |
| `freshness_score` | Calculated (0-15) | Días desde última modificación |
| `tech_debt_score` | Calculated (0-20) | Penalización por tecnología EOL, arquitectura designerJson, falta de YAML |
| `last_execution` | Build/Release API | Fecha última ejecución |
| `last_execution_status` | Build/Release API | Estado última ejecución |
| `last_execution_result` | Build/Release API | Resultado última ejecución |
| `total_executions_30d` | Build/Release API (count) | Ejecuciones últimos 30 días |
| `total_executions_90d` | Build/Release API (count) | Ejecuciones últimos 90 días |
| `total_failures_30d` | Build/Release API (count failed) | Fallas últimos 30 días |
| `mttr_minutes` | Build/Release API (calculated) | Mean Time To Recovery: tiempo promedio entre falla y siguiente éxito |
| `last_modified` | Definition (`modifiedDate`) | Fecha última modificación |
| `created_date` | Definition (`createdDate`) | Fecha de creación |
| `days_since_creation` | Calculated | Días desde creación |
| `demand_level` | Calculated | Elite (>200/mes) / Alto (50-200) / Medio (10-50) / Bajo (1-10) / Nulo (0) |
| `dora_profile` | Calculated | Elite / High / Medium / Low (basado en DORA 2023) |
| `recommendation` | Calculated | Mantener / Evolucionar / Consolidar / Deprecar / Eliminar |

---

## 3. REUTILIZACIÓN DE CÓDIGO EXISTENTE

### 3.1 Componentes Comunes (ya existen)

| Componente | Ubicación | Uso |
|------------|-----------|-----|
| `TeeWriter` + Logging | `cicd_inventory.py:123-170` | Redirección stdout a consola + archivo |
| `setup_logging()` / `teardown_logging()` | `cicd_inventory.py:153-170` | Logging en directorio `outcome/` |
| `_progress_context()` + Rich Progress | `cicd_inventory.py:88-121` | Barra de progreso con spinner |
| `_SimpleProgress` | `cicd_inventory.py:104-120` | Fallback si no hay Rich |
| `get_headers()` | `cicd_inventory.py:173-179` | Autenticación Basic con PAT |
| `az_get()` con retry | `cicd_inventory.py:182-206` | GET con retry exponencial (5xx, red) |
| `safe_az_get()` | `cicd_inventory.py:209-214` | Wrapper que nunca falla |
| `normalize_org()` | `cicd_inventory.py:216-220` | Normaliza nombre de org |
| `get_output_dir()` | `utils.py` | Directorio de salida centralizado |
| `resolve_output_path()` | `utils.py` | Resuelve paths de salida |
| `clone_pipelines_projects()` | `cicd_inventory.py:260-336` | Git clone shallow de pipelines-projects |
| `read_yaml_local()` | `cicd_inventory.py:339-347` | Lee YAML desde clone local |
| `parse_app_repo_from_yaml_text()` | `cicd_inventory.py:230-257` | Parsea repo desde YAML |
| `ThreadPoolExecutor` pattern | Varios scripts | Patrón de paralelización |

### 3.2 Lógica Específica a Reutilizar

| Funcionalidad | Script Origen | Qué reutilizar |
|---------------|--------------|----------------|
| CI Pipelines fetch | `cicd_inventory.py:456-575` | `_fetch_ci_pipeline()`, `get_ci_pipelines()` |
| CD Pipelines fetch | `cicd_inventory.py:578-671` | `_fetch_cd_pipeline()`, `get_cd_pipelines()` |
| Health Score (recencia + estabilidad) | `azdo_release_cd_health.py` | Lógica de scoring 0-100 |
| GKE Pipeline filtering | `cicd_inventory_gke_pipelines.py` | Filtrado por nombre/stage |
| Parallel execution | `cicd_inventory_branches_created.py` | `ThreadPoolExecutor` con workers |

---

## 4. PLAN DE IMPLEMENTACIÓN

### Fase 1: Pipeline CI Detailed Inventory
**Archivo:** `scm/azdo/cicd_inventory_ci_detailed.py`

**Pasos:**
1. [ ] Crear script base con imports, TeeWriter, logging, progress
2. [ ] Implementar `get_ci_definitions()` → lista todas las build definitions
3. [ ] Implementar `get_build_history()` → cuenta ejecuciones y último build
4. [ ] Implementar `detect_breakers()` → parsea YAML buscando breakers
5. [ ] Implementar `detect_technology()` → extrae tecnología del nombre
6. [ ] Implementar `export_to_excel()` → genera archivo con todas las columnas
7. [ ] Implementar `main()` → orquesta todo con argumentos CLI
8. [ ] Agregar entrada en `tools.py` con número de herramienta
9. [ ] Actualizar `README.md` con descripción

**Columnas a generar:**
- name, pipelineCreationDate, ejecuciones, modificaciones, arqType
- Breakers, lastYamlModifier, lastPipelineModifier
- lastExecution, lastExecutionState, lastExecutionResult
- repositoryName, repositoryUrl, defaultBranch

### Fase 2: Pipeline CD Detailed Inventory
**Archivo:** `scm/azdo/cicd_inventory_cd_detailed.py`

**Pasos:**
1. [ ] Crear script base con imports, TeeWriter, logging, progress
2. [ ] Implementar `get_cd_definitions()` → lista todas las release definitions
3. [ ] Implementar `get_last_release()` → obtiene último release por definition
4. [ ] Implementar `detect_obsolete()` → detecta pipelines marcados obsoletos
5. [ ] Implementar `export_to_excel()` → genera archivo con todas las columnas
6. [ ] Implementar `main()` → orquesta todo con argumentos CLI
7. [ ] Agregar entrada en `tools.py`
8. [ ] Actualizar `README.md`

**Columnas a generar:**
- id, name, path, url, createdOn
- environmentsCount, environments (lista separada por /)
- lastReleaseDate, lastReleaseStatus, isObsolete

### Fase 3: Pipeline Health Score Report
**Archivo:** `scm/azdo/azdo_pipeline_health_score.py`

**Pasos:**
1. [ ] Crear script base con imports, TeeWriter, logging, progress
2. [ ] Implementar `calculate_recency_score()` → 20 pts, basado en DORA deployment frequency thresholds
3. [ ] Implementar `calculate_reliability_score()` → 25 pts, DORA Change Failure Rate + Google SRE MTTR
4. [ ] Implementar `calculate_usage_score()` → 20 pts, DORA Deployment Frequency profile
5. [ ] Implementar `calculate_freshness_score()` → 15 pts, CI/CD maturity maintenance windows
6. [ ] Implementar `calculate_tech_debt_score()` → 20 pts, penalizaciones SRE toil + Microsoft DevOps maturity
7. [ ] Implementar `calculate_mttr()` → Mean Time To Recovery entre falla y siguiente éxito
8. [ ] Implementar `detect_technology()` → extrae tecnología y versión del nombre del pipeline
9. [ ] Implementar `classify_technology_status()` → Moderna / Mantenimiento / EOL / Obsoleta
10. [ ] Implementar `calculate_dora_profile()` → Elite / High / Medium / Low basado en 4 métricas DORA
11. [ ] Implementar `calculate_demand_level()` → Elite/Alto/Medio/Bajo/Nulo basado en DORA frequency
12. [ ] Implementar `generate_recommendation()` → Mantener/Evolucionar/Consolidar/Deprecar/Eliminar
13. [ ] Implementar `export_to_excel()` → genera reporte con scoring + gráfico de distribución
14. [ ] Implementar `main()` → orquesta CI + CD scoring en paralelo
15. [ ] Agregar entrada en `tools.py`
16. [ ] Actualizar `README.md`

## 4. MODELO DE SCORING FUNDAMENTADO EN ESTÁNDARES

### 4.1 Fuentes y Estándares de Referencia

| Estándar / Referencia | Métricas Relevantes | Aplicación en este modelo |
|---|---|---|
| **DORA (DevOps Research and Assessment)** | Deployment Frequency, Lead Time for Changes, Change Failure Rate, Time to Recovery (MTTR) | `usage_score` (frecuencia), `reliability_score` (tasa de fallo + MTTR) |
| **Accelerate (Forsgren, Humble, Kim)** | Throughput + Stability como indicadores de rendimiento de elite | Balance 50/50 entre throughput (uso + frescura) y estabilidad (confiabilidad) |
| **Google SRE Book** | Error budgets, SLIs/SLOs, toil reduction | `tech_debt_score` penaliza toil (pipelines designerJson, tecnologías EOL) |
| **Microsoft DevOps Maturity Model** | CI/CD maturity levels: Basic → Standard → High → Elite | `dora_profile` clasifica pipelines en niveles de madurez |
| **Azure DevOps Best Practices** | YAML > Classic, infra-as-code, parallel jobs, caching | `tech_debt_score` penaliza designerJson, ausencia de YAML |
| **NIST / OWASP** | Seguridad en el pipeline, dependency scanning | Detección de tecnologías con CVEs conocidos |

### 4.2 Fórmula Compuesta (0-100)

```
health_score = recency_score(0-20) + reliability_score(0-25) + usage_score(0-20) + freshness_score(0-15) + tech_debt_score(0-20)

Peso por dimensión:
┌─────────────────────┬───────┬────────────────────────────────────────────┐
│ Dimensión           │ Peso  │ Fundamento                                 │
├─────────────────────┼───────┼────────────────────────────────────────────┤
│ Recency             │ 20%   │ DORA: pipeline inactivo = sin valor entregado│
│ Reliability         │ 25%   │ DORA Change Failure Rate + MTTR (elite <5%) │
│ Usage               │ 20%   │ DORA Deployment Frequency (elite: on-demand)│
│ Freshness           │ 15%   │ Madurez: pipeline mantenido evita drift    │
│ Tech Debt           │ 20%   │ SRE: toil técnico consume capacidad del equipo│
└─────────────────────┴───────┴────────────────────────────────────────────┘
```

### 4.3 Cálculo por Dimensión

#### A. Recency Score (0-20) — Última Utilización
*Basado en DORA: un pipeline que no se ejecuta no entrega valor. Benchmark de madurez: elite ejecuta on-demand.*

| Días sin ejecución | Score | Benchmark |
|---|---|---|
| 0-1 (hoy/ayer) | 20 | Elite — Continuous Deployment |
| 2-7 | 17 | High — Daily/Weekly deployments |
| 8-14 | 13 | Medium — Bi-weekly sprints |
| 15-30 | 9 | Low — Monthly releases |
| 31-60 | 5 | Atrophying — Quarterly or less |
| 61-90 | 2 | Stale — Risk of bit-rot |
| > 90 | 0 | Zombie — Candidate for deletion |

#### B. Reliability Score (0-25) — Ejecución de Errores
*Basado en DORA Change Failure Rate + Google SRE MTTR. Elite: <5% fallo, MTTR < 1 hora.*

```
reliability_score = min(success_rate_pts + mttr_pts, 25)

success_rate_pts (últimas 20 ejecuciones):
  100% éxito  → 15 pts
  95-99%      → 12 pts  (DORA "High" threshold)
  90-94%      → 9 pts
  80-89%      → 6 pts
  60-79%      → 3 pts
  < 60%       → 0 pts

mttr_pts (Mean Time To Recovery en minutos):
  < 15 min    → 10 pts  (SRE "rapid recovery")
  15-60 min   → 8 pts
  1-4 horas   → 6 pts   (DORA elite: < 1 hora típico)
  4-24 horas  → 3 pts
  > 24 horas  → 0 pts
  Sin datos   → 5 pts (neutral)
```

#### C. Usage Score (0-20) — Qué Tan Usado Es
*Basado en DORA Deployment Frequency. Elite: múltiples deploys diarios. Low: < 1 por mes.*

| Ejecuciones / 30 días | Score | DORA Profile |
|---|---|---|
| > 200 | 20 | Elite — On-demand / multiple per day |
| 50-200 | 17 | High — Daily to weekly |
| 20-49 | 13 | Medium — Weekly to bi-weekly |
| 5-19 | 8 | Low — Monthly |
| 1-4 | 3 | Atrophying — Rarely used |
| 0 | 0 | Zombie — No executions |

#### D. Freshness Score (0-15) — Fecha de Modificaciones
*Basado en madurez CI/CD: pipeline actualizado = pipeline relevante. Pipeline sin cambios = drift acumulado.*

| Días desde última modificación | Score | Interpretación |
|---|---|---|
| < 7 días | 15 | Active development / hotfixing |
| 7-30 días | 12 | Regular maintenance |
| 31-90 días | 9 | Stable but monitored |
| 91-180 días | 5 | Seasonal / low-touch |
| 181-365 días | 2 | At risk of drift |
| > 365 días | 0 | Abandoned — needs audit |

#### E. Tech Debt Score (0-20) — Tecnología + Arquitectura
*Basado en SRE toil + Microsoft DevOps maturity. Penaliza arquitecturas legacy, tecnologías EOL, falta de infra-as-code.*

```
tech_debt_score = max(0, 20 - penalties)

Penalties (acumulativas):
  Arquitectura designerJson (Classic UI)     → -8 pts
    Fundamento: Microsoft recomienda YAML para CI (2023+). Classic = tech debt.

  Tecnología EOL (End of Life)               → -7 pts
    Fundamento: EOL = sin parches de seguridad. Riesgo CVE no resoluble.
    Ejemplos: Java 8 (Oracle EOL 2030, pero OpenJDK 8 ya legacy), .NET Framework 4.x,
              Angular < 14 (EOL por Google), PHP 5.x, Python 2.x

  Tecnología en Mantenimiento (no latest)      → -4 pts
    Fundamento: No recibe features nuevos, solo parches críticos.
    Ejemplos: Java 11, Angular 14-16, Spring Boot 2.x

  Pipeline sin YAML (no infra-as-code)         → -5 pts
    Fundamento: No versionable, no auditable, no reproducible.

  Sin repositorio asociado / repo_orphan       → -3 pts
    Fundamento: Pipeline huérfano = maintenance nightmare.

  Nombre contiene "obsoleto", "legacy", "_old"  → -2 pts
    Fundamento: Etiqueta explícita de abandono.
```

### 4.4 Clasificación DORA Profile

*Basado en DORA 2023 State of DevOps Report. Se evalúan las 4 métricas DORA para cada pipeline.*

| Perfil | Deployment Frequency | Change Failure Rate | MTTR | Lead Time |
|---|---|---|---|---|
| **Elite** | On-demand (> 200/mes) | < 5% | < 1 hora | < 1 día |
| **High** | Daily-Weekly (50-200/mes) | 5-15% | < 1 día | 1-7 días |
| **Medium** | Weekly-Biweekly (10-50/mes) | 15-30% | < 1 semana | 1-4 semanas |
| **Low** | Monthly o menos (< 10/mes) | > 30% | > 1 semana | > 1 mes |

*Asignación: se evalúa cada pipeline contra los thresholds. El perfil es el peor caso (más conservador) de las métricas disponibles.*

### 4.5 Rating de Health Score

| Score | Rating | Color | Acción Recomendada |
|---|---|---|---|
| 90-100 | 🟢 Excelente | Saludable | Mantener. Pipeline óptimo, cumple estándares DORA elite/high |
| 75-89 | 🔵 Bueno | Saludable | Evolucionar. Buen rendimiento, pequeñas mejoras posibles |
| 50-74 | 🟡 Regular | Atención | Consolidar. Requiere atención en 1-2 dimensiones. Plan de mejora |
| 25-49 | 🟠 Bajo | Riesgo | Deprecar. Múltiples problemas. Evaluar reemplazo o refactor |
| 0-24 | 🔴 Crítico | Crítico | Eliminar. Pipeline abandonado, EOL, o sin valor. Candidato a decomisión |

### 4.6 Recomendaciones Automáticas

| Condiciones | Recomendación | Justificación |
|---|---|---|
| Score ≥ 75, DORA ≥ High | **Mantener** | Pipeline saludable. Invertir en observabilidad |
| Score 50-74, Tech Debt > 10 | **Evolucionar** | Funcional pero con deuda técnica. Migrar YAML, actualizar tech stack |
| Score 25-49, Usage < 5/mes | **Consolidar** | Pipeline poco usado. Evaluar si es necesario o puede fusionarse |
| Score < 25, Recency = 0 | **Deprecar** | Pipeline abandonado. Marcar obsoleto, crear plan de transición |
| Score < 10, sin ejecuciones 90d | **Eliminar** | Zombie pipeline. Sin valor, solo genera costo/confusión |

### 4.7 Tecnologías y Ciclo de Vida

| Tecnología | Moderna (0 pts) | Mantenimiento (-4 pts) | EOL (-7 pts) | Fuente |
|---|---|---|---|---|
| **Java** | 17, 21 (LTS) | 11 (LTS hasta 2026/2032) | 8 (EOL 2030 Oracle, legacy) | Oracle/Java SE Support Roadmap |
| **Angular** | 18, 19+ | 14-17 (LTS 18 meses) | < 14 (EOL por Google) | Angular Support Policy |
| **Spring Boot** | 3.x (Java 17+) | 2.7.x (EOL Nov 2023+) | 2.6 o menor | Spring Boot Support |
| **.NET** | .NET 8, 9 (LTS) | .NET 6 (LTS hasta Nov 2024) | .NET Framework 4.x | Microsoft .NET Support Policy |
| **Node.js** | 20, 22 (LTS) | 18 (LTS hasta Abr 2025) | 16 o menor | Node.js Releases |
| **PHP** | 8.2, 8.3 | 8.1 | 7.4 o menor, 5.x | PHP Supported Versions |
| **Python** | 3.11, 3.12 | 3.9, 3.10 | 3.8 o menor, 2.x | Python Dev Guide |
| **Kubernetes** | 1.29+ | 1.27-1.28 | < 1.26 | Kubernetes Support |

*Nota: Las fechas EOL se actualizan automáticamente desde fuentes oficiales cuando sea posible, o mediante tabla de referencia en config.json.*

---

## 5. ESTRATEGIA DE EJECUCIÓN Y DATA SHARING

### 5.1 Problema: Consultas Duplicadas

Si los 3 programas se ejecutan de forma independiente, se repiten las mismas consultas API:
- **CI Inventory** consulta: build definitions + último build por definition
- **CD Inventory** consulta: release definitions + último release por definition
- **Health Score** necesita: definitions + últimas 20 ejecuciones + MTTR + fechas de modificación

**Costo estimado** para 1500 pipelines:
- Sin data sharing: ~4500-6000 llamadas API (CI×2 + CD×2 + Health×3-4)
- Con data sharing: ~3000 llamadas API (CI×2 + CD×2 + Health solo incremental)

### 5.2 Arquitectura Recomendada: 2-Pass con Raw Cache

```
┌─────────────────────────────────────────────────────────────────────┐
│  PASO 1: Inventarios (semanal/mensual)                              │
│  ─────────────────────────────────────                              │
│  $ python cicd_inventory_ci_detailed.py  → outcome/ci_inventory.xlsx│
│                                          → outcome/.cache/ci_raw.json│
│  $ python cicd_inventory_cd_detailed.py  → outcome/cd_inventory.xlsx│
│                                          → outcome/.cache/cd_raw.json│
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PASO 2: Health Score (diario/semanal)                              │
│  ─────────────────────────────────────                              │
│  Opción A: Con inputs (rápido, ~30% menos llamadas)                   │
│  $ python azdo_pipeline_health_score.py                             │
│      --ci-input outcome/ci_inventory_20260426_103000.xlsx             │
│      --cd-input outcome/cd_inventory_20260426_103500.xlsx            │
│                                                                      │
│  Opción B: Standalone (sin inputs, consulta todo)                     │
│  $ python azdo_pipeline_health_score.py                               │
│      --org Coppel-Retail --project "Compras.RMI"                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Raw Cache: Estructura

Cada inventario guarda un `.cache/{tipo}_raw.json` con datos crudos API:

```json
{
  "metadata": {
    "org": "Coppel-Retail",
    "project": "Compras.RMI",
    "generated_at": "2026-04-26T10:30:00Z",
    "api_version": "7.1"
  },
  "definitions": [
    {
      "id": 123,
      "name": "api-gateway-CI",
      "createdDate": "2024-03-20T14:11:00Z",
      "modifiedDate": "2025-03-03T12:43:00Z",
      "process": {"type": "yaml", "yamlFilename": "azure-pipelines.yml"},
      "repository": {"id": "repo-uuid", "name": "api-gateway", "url": "..."},
      "authoredBy": {"displayName": "..."},
      "_last_build": {"id": 456, "status": "completed", "result": "succeeded", "finishTime": "2025-03-03T12:43:00Z"},
      "_build_count_30d": 6,
      "_build_count_90d": 18
    }
  ]
}
```

**Ventajas del cache:**
- Health Score lee `ci_raw.json` + `cd_raw.json` → evita re-consultar definitions básicos
- Solo consulta incremental: últimas 20 ejecuciones por pipeline (para reliability + MTTR)
- Si `--use-cache` y el cache tiene < 24h, Health Score puede ejecutarse sin ninguna llamada API (modo offline)

### 5.4 Flujos de Ejecución Soportados

| Flujo | Comando | Cuándo usar | Llamadas API |
|---|---|---|---|
| **Full** (sin cache) | Ejecutar los 3 scripts standalone | Primera vez, o después de limpiar cache | ~5000 |
| **Inventory + Health** | Inventarios → Health con `--ci-input`/`--cd-input` | Uso normal semanal | ~3500 |
| **Health rápido** | Health con `--use-cache` | Diario, monitoreo continuo | ~1500 (solo builds/releases recientes) |
| **Health offline** | Health con `--offline` + cache < 24h | Sin conectividad, reportes locales | 0 |

### 5.5 Implementación en Cada Script

**Inventarios CI/CD:**
- Siempre guardan `.cache/{ci|cd}_raw.json` después de terminar
- Incluyen todos los campos crudos de la API + metadatos enriquecidos (`_build_count_*`, `_last_build`)

**Health Score:**
- `--ci-input PATH` / `--cd-input PATH`: lee Excel generado por inventarios
- `--use-cache`: intenta leer `.cache/ci_raw.json` y `.cache/cd_raw.json` primero; falta datos → consulta API
- `--offline`: solo usa cache, error si cache no existe o > 24h
- Sin flags: consulta todo directamente (standalone)

---

## 6. ENDPOINTS AZURE DEVOPS REQUERIDOS

### CI Pipelines
```
GET https://dev.azure.com/{org}/{project}/_apis/build/definitions?api-version=7.1
GET https://dev.azure.com/{org}/{project}/_apis/build/definitions/{definitionId}?api-version=7.1
GET https://dev.azure.com/{org}/{project}/_apis/build/builds?definitions={definitionId}&$top=100&api-version=7.1
GET https://dev.azure.com/{org}/{project}/_apis/build/builds/{buildId}?api-version=7.1
```

### CD Pipelines
```
GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions?api-version=7.1
GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{definitionId}?api-version=7.1
GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases?definitionId={definitionId}&$top=100&api-version=7.1
```

### Git Repositories (para YAML history)
```
GET https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repositoryId}/commits?path={yamlPath}&$top=1&api-version=7.1
GET https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repositoryId}/items?path={yamlPath}&includeContent=true&api-version=7.1
```

---

## 6. ESTRUCTURA DE ARCHIVOS

```
devsecops-toolbox/
├── scm/
│   └── azdo/
│       ├── cicd_inventory_ci_detailed.py      # NUEVO: Inventario CI detallado
│       ├── cicd_inventory_cd_detailed.py      # NUEVO: Inventario CD detallado
│       ├── azdo_pipeline_health_score.py      # NUEVO: Reporte de salud
│       ├── tools.py                           # MODIFICAR: Agregar entradas
│       └── ...
├── docs/
│   ├── Plan_Trabajo_Pipeline_Health.md        # ESTE DOCUMENTO
│   ├── Pipelines CI.csv                       # Datos de referencia
│   └── Pipelines CD.csv                       # Datos de referencia
└── README.md                                  # MODIFICAR: Agregar herramientas
```

---

## 7. CONFIGURACIÓN EN tools.py

Agregar entradas al diccionario `TOOLS`:

```python
"14": {
    "name":        "CI Detailed Inventory",
    "description": "Inventario detallado de pipelines CI con ejecuciones, tecnología y metadatos",
    "path":        "cicd_inventory_ci_detailed.py",
    "args":        ["--pat", "--org", "--project", "--workers", "--output"],
    "group":       "inventory",
    "status":      "ready",
},
"15": {
    "name":        "CD Detailed Inventory",
    "description": "Inventario detallado de pipelines CD (Release Definitions) con ambientes y estados",
    "path":        "cicd_inventory_cd_detailed.py",
    "args":        ["--pat", "--org", "--project", "--workers", "--output"],
    "group":       "inventory",
    "status":      "ready",
},
"16": {
    "name":        "Pipeline Health Score",
    "description": "Reporte de salud de pipelines con scoring: recencia, estabilidad, uso, frescura",
    "path":        "azdo_pipeline_health_score.py",
    "args":        ["--pat", "--org", "--project", "--workers", "--output"],
    "group":       "health",
    "status":      "ready",
},
```

---

## 8. CRITERIOS DE ÉXITO

- [ ] Los 3 scripts ejecutan sin errores en modo directo y desde launcher
- [ ] Los archivos Excel se generan en `outcome/` con nombres timestamp
- [ ] El scoring es consistente y reproduce los valores esperados
- [ ] La detección de tecnología es precisa (>90% accuracy)
- [ ] Las recomendaciones son útiles para toma de decisiones
- [ ] El rendimiento es aceptable: < 5 min para 1500 pipelines con 30 workers

---

## 9. NOTAS

- Las fechas del CSV están en formato `DD/MM/YYYY HH:MM` (local) mientras que Azure DevOps API retorna ISO 8601 UTC. Se debe normalizar.
- Algunos pipelines tienen nombres duplicados (mismo nombre, diferentes fechas de creación) - esto representa pipelines recreados.
- La detección de "Breakers" requiere parsear el YAML buscando keywords como `condition`, `break`, `fail` o stage names.
- La detección de tecnología es heurística basada en el nombre - puede refinarse leyendo el contenido del YAML.
- Los pipelines "obsoletos" se detectan por keywords en el nombre: OBSOLETO, obsoleto, _old, legacy-, deprecated.
