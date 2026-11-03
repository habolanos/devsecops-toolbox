# Release Diagnostic & Folio Generator — Opción 50

A partir de **un release ID** de un pipeline CD produce:

1. **Diagnóstico de coherencia install ↔ rollback** — artifacts, build↔PR,
   logs del stage Validator, variables, repo de properties.
2. **Folio** en el formato Service Desk, listo para copiar.

## Documentos

| Archivo | Contenido |
|---|---|
| [01_ANALISIS.md](01_ANALISIS.md) | Qué verifica, de dónde sale cada dato, caso de uso |
| [02_DISENO.md](02_DISENO.md) | Arquitectura, fases, parsers del log, formato del folio |
| [03_PLAN_IMPLEMENTACION.md](03_PLAN_IMPLEMENTACION.md) | Flags, archivos, tests, criterios de aceptación |

## Uso rápido

```bash
python scm/azdo/azdo_release_diagnostic.py --pat <PAT> \
    --org https://dev.azure.com/<ORG> --project <PROJECT> \
    --release-id 62650
```

Opción **50** en `python scm/azdo/tools.py` (grupo Release).

## Historial de cambios

| Fecha | Versión | Cambio |
|---|---|---|
| 2026-11-03 | 1.9.31 | Propuesta inicial: diagnóstico por release-id + folio Service Desk (reutiliza opción 47 + logs del Validator de la 48) |
