# 02 — Diseño

## Archivo

`scm/azdo/azdo_release_diagnostic.py` — opción **50**, grupo `release`,
`__version__ = "1.0.0"`. Solo lectura.

## Flujo

```
--release-id
   │
   ├─ FASE 1  release detail + artifacts  →  build{id,num,branch}  git{repo,commit,branch}
   │
   ├─ FASE 2  build↔PR                     →  refs/pull/N → PR.lastMergeCommit == commit git ?
   │
   ├─ FASE 3  log stage Validator          →  imágenes (install/prod), excepto-a, kubectl apply,
   │                                          commitPropsRollback impreso en log
   │
   ├─ FASE 4  variables                    →  commitPropertiesRollback, RELEASE_ID
   │
   ├─ FASE 5  repo properties              →  último commit folder /<componente>
   │                                          (↔ commitPropertiesRollback)
   │
   ├─ FASE 6  RELEASE_ID → release rollback → repetir FASE 1-5
   │
   ├─ FASE 7  comparativo lado a lado      →  checks + veredicto
   │
   └─ FASE 8  folio (bloque copiable + outcome/ .txt/.json/.html/.xlsx)
```

## Nuevos parsers sobre el texto del log del Validator

```python
extract_images_from_log(text)   → {install_image, prod_image}
extract_excepto(text)           → str | "N/A"
detect_kubectl_apply(text)      → bool → instrucción apply→delete
extract_props_commit_from_log   → sha | ""
```

Patrones de imagen (case-insensitive):
`image actual|image nueva|image_actual|image_nueva|newImage|imagen`,
líneas `kubectl apply`/`set image`, y hosts `gcr.io`, `*.pkg.dev`,
`harbor`, `artifact.coppel.io` — formato `repo/name:tag`.

`detect_kubectl_apply`: `kubectl\s+apply` o task `kubectl-apply`/manifest
deploy → instrucción fija:
`Actualizar kubectl apply se cambia el comando apply por delete y hacer el deploy`.

## Formato del folio (literal)

```
Componente: <git source repo>
* Release: <name>
* URL Release: https://{org}/{project}/_releaseProgress?_a=release-pipeline-progress&releaseId={id}
* Commit: <git commit>
* Version Build: <build_number>
* Commit properties deploy: <props commit>
* Folio PR master : N/A
Excepto a: <log | N/A>
Rollback:
Componente: <rollback component> (<nota release 0 si aplica>)
• Release Rollback <name>
• URL Release Rollback: <url>
• Commit Rollback Release: <git commit>
• Version Build: <build_number>
• Commit properties Rollback : <props commit>
Actualizar kubectl apply se cambia el comando apply por delete y hacer el deploy
```

## Checks del comparativo

| Check | Regla |
|---|---|
| build↔PR | lastMergeCommit del PR == commit del git source |
| props↔folder | `commitPropertiesRollback` == último commit folder componente |
| RELASE_ID | apunta al id/nombre del release de rollback |
| imagen | install_image ≠ prod_image (hay cambio real) — informativo |

Veredicto `TODO EN ORDEN` solo si todos los checks obligatorios ✔.
