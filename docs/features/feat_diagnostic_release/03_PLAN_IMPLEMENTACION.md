# 03 — Plan de implementación

## Flags

```
--release-id N        (requerido) release a diagnosticar
--pat --org --project (org default Coppel-Retail, project Cadena_de_Suministros)
--validator-stage     nombre del stage validador (default "Validator")
--properties-repo     hint del repo de properties (default autodetect)
--branch              rama del repo properties (default master)
--debug               errores HTTP
```

## Archivos

| Archivo | Cambio |
|---|---|
| `scm/azdo/azdo_release_diagnostic.py` | **NUEVO** — reutiliza patrones de `azdo_release_deploy_check.py` + `validator_task_logs` de la 48 |
| `scm/azdo/tools.py` | opción `"50"`, grupo `release` |
| `scm/tests/unit/test_azdo_release_diagnostic.py` | **NUEVO** |
| `docs/features/feat_diagnostic_release/` | estos docs |
| `scm/azdo/README.md` | sección + historial |
| `README.version.md` + `VERSION` | patch (1.9.30 → 1.9.31) |

## Tests unitarios (sin API real)

- `extract_images_from_log`: `image actual:`/`image nueva:`, `IMAGE_ACTUAL=`,
  líneas `kubectl apply` con `*.pkg.dev|gcr.io|harbor`.
- `detect_kubectl_apply` → instrucción delete; ausente → `N/A`.
- `extract_excepto` → `excepto a: X`; default `N/A`.
- Comparativo: props == folder commit ✔ / difiere ✘; RELASE_ID → rollback.
- `build_folio`: formato literal exacto (componente, URLs, commits, N/A).
- Release 0 (sin rollback): nota `(estrategia release 0…)`, rollback `N/A`.

## Criterios de aceptación

1. `--release-id` produce comparativo + folio en formato exacto.
2. Validator sin correr → campos `N/A` sin romper.
3. `RELEASE_ID` inválido → rollback `N/A` + advertencia.
4. `TODO EN ORDEN` solo si todos los checks ✔.
5. Exports JSON+HTML+Excel en `outcome/` con rutas al final; tests verdes; commit sin push.
