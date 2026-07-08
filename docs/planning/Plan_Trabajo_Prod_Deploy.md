# Plan de Trabajo: `cicd_inventory_prod_deploy.py`

**Fecha:** 2026-04-29  
**Autor:** Harold Adrian Bolanos Rodriguez  
**Estado:** Pendiente de validación

---

## 1. OBJETIVO

Crear un nuevo programa `cicd_inventory_prod_deploy.py` que lea el cache CD existente y consulte la API de Azure DevOps para determinar la **fecha del último despliegue exitoso a Producción** de cada pipeline CD, junto con información del artefacto (commit, build ID) y un indicador de vigencia contra un deadline.

---

## 2. COLUMNAS DE SALIDA (Excel + JSON cache)

| # | Columna | Tipo | Descripción | Fuente API |
|---|---------|------|-------------|------------|
| 1 | `cd_pipeline_id` | int | ID de la Release Definition | Cache CD |
| 2 | `cd_pipeline_name` | string | Nombre del pipeline CD | Cache CD |
| 3 | `cd_pipeline_path` | string | Ruta/carpeta del pipeline | Cache CD |
| 4 | `environments` | string | Lista de environments del pipeline | Cache CD |
| 5 | `last_release_number` | string | Número del último release (ej: "Release-123") | `releases?definitionId={id}&$top=1` → `name` |
| 6 | `last_release_id` | int | ID del último release | `releases?definitionId={id}&$top=1` → `id` |
| 7 | `last_release_date` | datetime | Fecha de creación del último release | `releases?definitionId={id}&$top=1` → `createdOn` |
| 8 | `last_release_status` | string | Estado global del último release | `releases?definitionId={id}&$top=1` → `status` |
| 9 | `prod_env_name` | string | Nombre del environment de producción detectado | Release → `environments[].name` (match por keywords) |
| 10 | `last_prod_deploy_date` | datetime | Fecha del último despliegue **exitoso** a producción | Release → `environments[].deploySteps[].finishedOn` |
| 11 | `last_prod_deploy_status` | string | Estado del último deploy a producción | `environments[].deploySteps[].deploymentStatus` |
| 12 | `last_prod_release_number` | string | Número del release del último deploy exitoso a prod | Release padre del environment prod |
| 13 | `last_prod_release_id` | int | ID del release del último deploy exitoso a prod | Release padre del environment prod |
| 14 | `commit_sha` | string | SHA del commit del artefacto Git | Release → `artifacts[].definitionReference.sourceVersion.id` |
| 15 | `build_id` | string | ID del build del artefacto | Release → `artifacts[].definitionReference.build.id` o `primaryArtifact.sourceVersion` |
| 16 | `build_number` | string | Número del build (ej: "20260427.1") | Release → `artifacts[].definitionReference.build.name` |
| 17 | `deadline` | date | Fecha deadline pasada como argumento CLI | `--deadline` |
| 18 | `deadline_status` | string | "Vigente" si `last_prod_deploy_date > deadline`, "Actualizar release" si `<= deadline` | Cálculo local |
| 19 | `days_since_prod_deploy` | int | Días transcurridos desde el último deploy a producción | Cálculo local |
| 20 | `is_obsolete` | string | "Sí"/"No" — detección de obsolescencia | Cache CD |

---

## 3. DETECCIÓN DE ENVIRONMENT DE PRODUCCIÓN

Keywords para identificar el environment de producción (case-insensitive, búsqueda parcial):

```
PROD_KEYWORDS = ["producción", "produccion", "production", "prod", "prd", "produc"]
```

**Lógica:**
1. Para cada release, iterar `environments[]`
2. Si `environment.name` contiene algún keyword → es environment de producción
3. Si hay múltiples matches (ej: "Producción Chile" + "Producción Colombia"), tomar el más reciente por `deploySteps[].finishedOn`
4. Si no hay match → columnas de prod quedan vacías (pipeline sin environment de producción detectado)

---

## 4. FLUJO DE EJECUCIÓN

```
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: Leer cache CD                                      │
│  ─────────────────────────────────                           │
│  Busca: outcome/.cache/cicd_inventory_cd_detailed_raw_*.json│
│  Si no existe → error con instrucción de ejecutar CD primero│
│  Carga: definition IDs, names, paths, environments          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: Consultar releases por definition (paralelo)       │
│  ─────────────────────────────────                           │
│  Para cada definitionId:                                     │
│    GET /releases?definitionId={id}&$expand=environments,    │
│        artifacts&$top=10&api-version=7.1                     │
│                                                              │
│  $top=10 porque:                                             │
│    - El último release puede no tener deploy a prod          │
│    - Necesitamos buscar hacia atrás hasta encontrar el       │
│      último deploy exitoso a producción                      │
│    - 10 releases cubre ~2-3 meses de actividad normal        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: Extraer datos por pipeline                          │
│  ─────────────────────────────────                           │
│  Para cada pipeline:                                         │
│    a) Último release global → last_release_*                 │
│    b) Buscar en releases (del más reciente al más viejo):    │
│       - Iterar environments de cada release                   │
│       - Filtrar por PROD_KEYWORDS                            │
│       - Buscar deployStep con status="succeeded"             │
│       - Tomar el más reciente → last_prod_deploy_*           │
│    c) Del release con deploy exitoso a prod:                 │
│       - Extraer artifacts → commit_sha, build_id             │
│    d) Calcular deadline_status y days_since_prod_deploy      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 4: Exportar resultados                                 │
│  ─────────────────────────────────                           │
│  - Excel: outcome/cicd_inventory_prod_deploy_YYYYMMDD.xlsx  │
│  - CSV:  outcome/cicd_inventory_prod_deploy_YYYYMMDD.csv    │
│  - Cache: outcome/.cache/..._raw_YYYYMMDD_HHMMSS.json       │
│  - Resumen Rich con estadísticas                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. API CALLS ESTIMADAS

| Escenario | API calls | Duración estimada (30 workers) |
|---|---|---|
| 500 pipelines CD | ~500 (1 por definition) | ~1.5 min |
| Con cache fresco (< 24h) | 0 | ~5 seg |
| Cache + `--force-refresh` | ~500 | ~1.5 min |

---

## 6. ARGUMENTOS CLI

```
python cicd_inventory_prod_deploy.py \
  --pat <TOKEN> \
  --org <ORG> \
  --project <PROJECT> \
  --deadline 2026-03-01 \       # Fecha deadline (YYYY-MM-DD)
  --workers 30 \                # Hilos paralelos
  --output excel \              # Formato salida
  --force-refresh               # Ignorar cache propio
```

**`--deadline` es obligatorio.** Sin deadline, no se genera la columna `deadline_status`.

---

## 7. ESTRUCTURA DEL JSON CACHE

```json
{
  "metadata": {
    "script": "cicd_inventory_prod_deploy",
    "org": "Coppel-Retail",
    "project": "Cadena_de_Suministros",
    "deadline": "2026-03-01",
    "generated_at": "2026-04-29T18:00:00Z",
    "count": 500
  },
  "rows": [
    {
      "cd_pipeline_id": 123,
      "cd_pipeline_name": "Release - WMS",
      "cd_pipeline_path": "\\WMS",
      "environments": "QA / Producción",
      "last_release_number": "Release-456",
      "last_release_id": 456,
      "last_release_date": "2026-04-25T10:30:00Z",
      "last_release_status": "active",
      "prod_env_name": "Producción",
      "last_prod_deploy_date": "2026-04-20T14:00:00Z",
      "last_prod_deploy_status": "succeeded",
      "last_prod_release_number": "Release-455",
      "last_prod_release_id": 455,
      "commit_sha": "a1b2c3d4e5f6...",
      "build_id": "789",
      "build_number": "20260420.1",
      "deadline": "2026-03-01",
      "deadline_status": "Vigente",  // 2026-04-20 > 2026-03-01
      "days_since_prod_deploy": 9,
      "is_obsolete": "No"
    }
  ]
}
```

---

## 8. INTEGRACIÓN CON TOOLBOX

### tools.py — Nueva herramienta 17

```python
"17": {
    "name":        "Prod Deploy Tracker",
    "description": "[Flujo] Rastrea último despliegue exitoso a Producción por pipeline CD. Requiere cache CD previo. Genera Excel + CSV + JSON cache con deadline de vigencia.",
    "path":        "cicd_inventory_prod_deploy.py",
    "args":        ["--pat", "--org", "--project", "--deadline", "--workers", "--output", "--force-refresh"],
    "group":       "deploy",
    "status":      "ready",
},
```

### Integración con Health Score

`cicd_inventory_health_score.py` puede invocar este script con `--run-inventory` para enriquecer la hoja Health Score con las columnas de prod deploy.

---

## 9. LÓGICA DEL DEADLINE

```
last_prod_deploy_date  vs  deadline
─────────────────────     ─────────

    Si last_prod_deploy_date >   deadline  →  "Vigente" ✅
    Si last_prod_deploy_date <=  deadline  →  "Actualizar release" ⚠️
    Si last_prod_deploy_date es null       →  "Sin deploy a prod" ❌
```

---

## 10. MANEJO DE CASOS EDGE

| Caso | Comportamiento |
|---|---|
| Pipeline sin environment de producción | Columnas prod quedan vacías, `deadline_status` = "Sin env. Producción" |
| Pipeline con deploy a prod fallido | `last_prod_deploy_status` = "failed", se busca release anterior con "succeeded" |
| Pipeline sin releases | Todas las columnas de release/prod vacías, `deadline_status` = "Sin releases" |
| Múltiples environments prod (ej: Prod Chile + Prod Colombia) | Se toma el más reciente por fecha de deploy |
| Artefacto no es tipo Build (ej: Jenkins) | `build_id` y `build_number` vacíos, `commit_sha` si está disponible |
| Cache CD no existe | Error con mensaje: "Ejecutar herramienta 15 (CD Inventory) primero" |

---

## 11. DEPENDENCIAS

- Lee cache de `cicd_inventory_cd_detailed.py` (herramienta 15)
- Sin dependencia de `cicd_inventory_health_score.py` (herramienta 16)
- Puede ejecutarse de forma independiente

---

## 12. CRITERIOS DE ÉXITO

- [ ] Lee cache CD existente sin modificarlo
- [ ] Consulta API de releases con `$expand=environments,artifacts`
- [ ] Detecta correctamente environments de producción por keywords
- [ ] Extrae commit SHA y build ID del artefacto primario
- [ ] Calcula `deadline_status` correctamente contra `--deadline`
- [ ] Genera Excel + CSV + JSON cache
- [ ] Funciona en modo directo y desde launcher (tools.py)
- [ ] Maneja casos edge sin crashear
- [ ] Cache propio con TTL de 24h
