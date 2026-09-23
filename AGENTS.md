# DevSecOps Toolbox — Convenciones del proyecto

## Convención prioritaria: listas de proyectos GCP desde config.json

Al implementar o modificar programas que necesiten listas de proyectos GCP
(launchers, checkers, reporters), **cargar los proyectos desde `scm/config.json`
en lugar de hardcodearlos**:

- **Fuente**: `gcp.service_accounts_reporter.projects` (lista plana de IDs).
- **Helpers existentes** en `scm/gcp/tools.py` — reusar, no duplicar:
  - `load_projects_from_config(path=None)` → lista plana desde config; `[]` si falta.
  - `team_key_for_project(project)` → deriva equipo del ID (`cpl-<equipo>-<env>-<fecha>` → `cs-csc`, `oms`); sin token de env → `otros`.
  - `group_projects_by_team(projects)` → `Dict[equipo, List[proyecto]]`.
  - `get_cloud_run_projects_by_team()` → config primero, fallback a `CLOUD_RUN_PROJECTS_BY_TEAM` (hardcoded).
  - `_match_team_key(name, groups)` → aliases por coincidencia exacta o sufijo (`CSC`→`cs-csc`, `WMS`→`cs-wms`).
  - `resolve_cloud_run_projects(input)` → expande `ALL`, alias de equipo, o lista manual.
  - `cloud_run_env_names(projects)` → `dev/qa/stg/prod` posicional (≤4) o `<equipo>-<env>` derivado (>4).
- **Reglas**:
  - `ALL` (case-insensitive) siempre debe expandir todos los proyectos configurados.
  - Tokens de ambiente reconocidos: `dev`, `qa`, `stg`, `stag`, `prod`, `prd` (normalizar `stag`→`stg`, `prd`→`prod`).
  - Si `config.json` no existe o la lista está vacía → fallback al dict hardcoded.
  - En el script diagnóstico Cloud Run (`gcp_cloudrun_vpc_ip_diagnostic.py`) existen equivalentes: `env_key_from_text()` y `env_label_for_project()`; `MAX_PROJECTS = 20`.

## Otras convenciones

- Reportes/archivos de salida → carpeta `outcome` (config `global.output_dir`; variable `DEVSECOPS_OUTPUT_DIR` tiene prioridad). Resolución: `scm/outcome/` por defecto.
- Pruebas unitarias obligatorias en `scm/tests/unit/` (pytest).
- Solo versiones **patch** en `VERSION`; documentar cada cambio en la tabla de historial de `README.md` y en `README.version.md`.
- Nunca hacer `git push`.
