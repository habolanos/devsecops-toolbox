# 01 — Análisis: Release Diagnostic & Folio

## Necesidad

Antes de una instalación a Production (o durante su folio en Service Desk) hay
que responder con datos: **¿el release que se va a instalar es coherente con su
build, su PR a master, su properties y su release de rollback?**

Hoy esa información se recolecta a mano. La opción 47 ya resuelve el comparativo
install↔rollback; esta herramienta lo empaqueta **a partir de un release-id** y
agrega la evidencia del **log del Validator** (imágenes, instrucción kubectl)
más un **folio** copiable.

## Qué verifica (input: `--release-id`)

| # | Verificación | Fuente |
|---|---|---|
| 1 | Artifacts del release: **build id/number** y **git source** (repo componente + commit) | release detail (`$expand=artifacts`) |
| 2 | El build corresponde al **commit del PR** del git source | `refs/pull/N/merge` → PR `lastMergeCommit` == commit del git source |
| 3 | **Log del stage Validator** (si existe/corrió) → **imagen a instalar**, **imagen en producción**, commit de rollback impreso, `excepto a`, detección de `kubectl apply` | `releaseDeployPhases → tasks → logUrl` |
| 4 | Variables **`commitPropertiesRollback`** y **`RELEASE_ID`/`RELASE_ID`** | `release.variables` |
| 5 | `commitPropertiesRollback` vs **repo properties** — folder con el **nombre del git artifact source** | `git/repositories/{propsRepo}/commits?itemPath=<componente>` |
| 6 | Todo lo anterior para el **release de rollback** (`RELEASE_ID`) | mismo pipeline, otro release |
| 7 | **Comparativo lado a lado** → veredicto `TODO EN ORDEN` / `REVISAR` | checks por fila |

## De dónde sale cada campo del folio

| Campo folio | Origen |
|---|---|
| Componente | nombre del repo del **git source artifact** |
| Release / URL Release | `release.name` + URL `_releaseProgress?releaseId=` |
| Commit | `git_artifact_info(commit)` del source |
| Version Build | `definitionReference.version.name` del Build artifact |
| Commit properties deploy | último commit del folder `/<componente>` en repo properties |
| Folio PR master | **N/A** (no derivable de AzDO) |
| Excepto a | del log del Validator (`excepto a:`) o `N/A` |
| Rollback (componente/release/url/commit/build/properties) | release apuntado por `RELEASE_ID`, mismas reglas |
| Instrucción kubectl | si el log del Validator muestra `kubectl apply`/task manifest → `Actualizar kubectl apply se cambia el comando apply por delete y hacer el deploy` |

## Reutilización (opción 47 / 48)

- `extract_artifacts`, `artifact_info`, `git_artifact_info`,
  `classify_git_artifacts`, `find_pr_for_commit`, `folder_commits`,
  `commit_matching_date`, `find_properties_repo`, `release_variables`,
  `relase_id_matches_rollback` — de `azdo_release_deploy_check.py`.
- `validator_task_logs` (todos los tasks del último intento del stage
  Validator) — de `azdo_prod_preinstall_validator.py`.
- Nuevos parsers sobre el **texto** del log: `extract_images_from_log`,
  `extract_excepto`, `detect_kubectl_apply`, `extract_props_commit_from_log`.
