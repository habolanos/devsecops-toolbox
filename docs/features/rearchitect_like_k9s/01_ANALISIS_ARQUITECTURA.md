# 01 — Análisis de arquitectura

## Antes (menús numerados)

```
main.py  ──menú──▶  <plat>/tools.py  ──menú──▶  run_tool(key)
                     (prompts args)      ──▶  subprocess script.py
```

- `scm/main.py`: tabla Rich de 6 plataformas → `launch_platform()`
  prepara env (`prepare_env_for_platform`, PYTHONPATH=scm/) →
  `subprocess.run(tools.py)` con el menú completo.
- Cada `tools.py`: dict `TOOLS` (`terminal` usa `SCRIPTS`) +
  `TOOL_GROUPS`/`GROUP_ORDER` + `run_tool(key)` con prompts de args,
  venv y subprocess del script + loop `main()`.
- Búsqueda `/` fuzzy ya existía (`scm/search_module.py`).

## Después (k9s)

```
main.py
   └── scm/tui/ToolboxApp (Textual)
        PlatformsScreen ──Enter──▶ ToolsScreen(plataforma)
                                     │ Enter en fila
                                     ▼
                              app.suspend() → terminal normal
                              subprocess tools.py --run <key>
                              resume → toast resultado
```

## Nuevo paquete `scm/tui/`

| Archivo | Responsabilidad |
|---|---|
| `registry.py` | `PLATFORMS` (6 contextos con aliases), import lazy de `<plat>.tools` para leer `TOOLS`/`TOOL_GROUPS`, ordenamiento por grupo, `outcome_dir()` |
| `commands.py` | Parser de `:cmd` → `Command(action, arg)` |
| `runner.py` | `run_tool()` — env-prep + `subprocess.run(tools.py --run key)`; `run_platform_menu()` fallback |
| `widgets.py` | `ToolsTable` (DataTable + filtro en vivo), `CommandBar` (`:`/`/` con historial ↑), `CrumbBar` (breadcrumb) |
| `screens.py` | `PlatformsScreen`, `ToolsScreen`, `OutcomeScreen`, `HelpScreen` |
| `app.py` | `ToolboxApp` — bindings, dispatch de comandos, `launch_tool` con `suspend()` |

## Cambios en existentes

- `scm/main.py`: `_try_run_tui()` — TUI por defecto; `--classic` fuerza el menú
  y si hay TTY + textual importable; sin el flag o ante excepción →
  menú clásico.
- `scm/<plat>/tools.py` ×6: flag `--run <key>` al inicio de `main()`
  que llama `run_tool(key)`/`run_script(key)` directo con la
  normalización de clave propia de cada plataforma (azdo: `upper()`
  si alfabética, `lower()` si alfanumérica; resto: `upper()`).
- `scm/requirements.txt`: `textual>=8.2.0,<9.0`.

## Por qué subprocess y no in-process

- **Aislamiento**: un crash/hang de una tool no tumba la TUI.
- **Env idéntico**: el hijo recibe el env de `prepare_env_for_platform`
  tal como hoy (AZDO_PAT, GCP_PROJECT_ID, proxies, DEVSECOPS_*).
- **Cero refactor**: `run_tool` conserva prompts, venv y submenús
  (opción 44, 22, 25...). La TUI solo elige *qué* ejecutar.
