# Re-arquitectura estilo k9s — TUI Textual

Transformación del launcher de menús numerados a una TUI full-screen
estilo k9s: las herramientas se navegan como "recursos" con tabla
viviente, `:` comandos, `/` filtro, Enter ejecuta y Esc retrocede.

## Documentos

| Archivo | Contenido |
|---|---|
| `00_INICIO_AQUI.md` | Resumen ejecutivo y decisiones |
| `01_ANALISIS_ARQUITECTURA.md` | Estado actual vs objetivo |
| `02_PLAN_IMPLEMENTACION.md` | Fases y diseño técnico |
| `03_GUIA_USO.md` | Keymap completo y comandos `:` |

## Uso rápido

```bash
python scm/main.py            # TUI por defecto
python scm/main.py --classic  # menú numerado clásico
```

## Historial

| Fecha | Versión | Cambio |
|---|---|---|
| 2026-10-18 | 1.8.89 | Implementación inicial: `scm/tui/` (app, screens, widgets, registry, commands, runner), `--run <key>` en los 6 tools.py, TUI por defecto con fallback `--classic` |
