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
python scm/main.py                # TUI full-screen estilo k9s (default)
python scm/main.py --classic      # menú numerado clásico
```

## Historial

| Fecha | Versión | Cambio |
|---|---|---|
| 2026-10-18 | 1.8.103 | TUI vuelve a ser el default: `python scm/main.py` = TUI, `--classic` = menú numerado (opt-out). `--k9s-style` se acepta por compatibilidad |
| 2026-10-18 | 1.8.94 | TUI pasa a ser opt-in: `python scm/main.py` = menú clásico (default), `--k9s-style` = TUI |
| 2026-10-18 | 1.8.93 | Skin "stock" de k9s: paleta oficial de `skins/stock.yaml` — cursor negro-aqua, crumbs steelblue, logo/info naranja, `<vista(ctx)[count]>`, hints, prompt `toolbox>`, columna `ST` con `●` |
| 2026-10-18 | 1.8.89 | Implementación inicial: `scm/tui/` (app, screens, widgets, registry, commands, runner), `--run <key>` en los 6 tools.py, TUI por defecto con fallback `--classic` |
