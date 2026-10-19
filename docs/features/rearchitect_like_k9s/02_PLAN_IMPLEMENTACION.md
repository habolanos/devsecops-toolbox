# 02 — Plan de implementación

## Fases ejecutadas

### F0 — Spike ✅
- `textual 8.2.8` (jun-2026, >7 días) instalado en el python host.
- Verificado: `App.suspend()`, `run_test()` headless, `DataTable`.
- Pin: `textual>=8.2.0,<9.0` en `scm/requirements.txt`.

### F1 — Núcleo TUI ✅
- `scm/tui/` creado (7 archivos).
- `--run <key>` en los 6 `tools.py` con normalización por plataforma.
- `main.py`: TUI por defecto, `--classic` para menú, fallback si no
  hay TTY/textual.
- Navegación end-to-end: plataformas → tools → suspend → subprocess →
  toast resultado.

### F2 — Pulido ✅ (incluido en la implementación inicial)
- Toast post-run con exit code + duración.
- `:outcome` — navegador de archivos generados (Enter abre en el
  explorador de archivos del SO).
- Historial de comandos `:` con tecla ↑.
- `r` recarga registry + `config.json` sin reiniciar.
- `?` / `:help` — modal con keymap.

### F3 — Documentación ✅
- Esta carpeta de docs + entradas en `README.version.md` y
  `scm/azdo/README.md`.

### F4 — Skin "stock" de k9s ✅ (fidelidad visual)

La primera versión usaba `Header`/`Footer` genéricos de Textual y
colores de tema — no se parecía a k9s. F4 reimplementa el chrome con
la **skin stock oficial** (`skins/stock.yaml` de
https://github.com/derailed/k9s):

- **`scm/tui/skin.py`** — paleta stock mapeada a hex + `APP_CSS`:
  | k9s skin | Widget |
  |---|---|
  | `body` fg `#1E90FF` bg `#000` logo `#FFA500` | Screen, logo ASCII |
  | `info` fg `#FFA500` section `#FFF` | líneas del header |
  | `frame.crumbs` negro/`#4682B4` activo `#FFA500` | `CrumbBar` |
  | `frame.title` aqua + fuchsia + papayawhip + steelblue | `TableTitle` `<vista(ctx)[count]>` |
  | `frame.menu` dim white, keys `#1E90FF`, nums `#FF00FF` | `HintsBar` |
  | `frame.status` greenyellow/orangered/darkorange | dots `●` de estado |
  | `prompt` `#5F9EA0` | `toolbox>` idle en `CommandBar` |
  | `views.table` cursor **negro-sobre-aqua**, header blanco | `DataTable` |

- **Chrome nuevo**: `LogoHeader` (logo ASCII naranja + info
  Toolbox Rev/Python/Config/Outcome/Context), `CrumbBar` steelblue,
  `TableTitle` `<tools(azdo)[38]>`, `HintsBar` `<enter>Run`, prompt
  `toolbox>` siempre visible. Sin `Header`/`Footer` de Textual ni
  zebra stripes (k9s no usa filas alternadas).
- Columnas de tabla en mayúsculas (`# ST GROUP NAME DESC`) y columna
  `ST` con dot `●` de estado por fila.

## Tests (29 nuevos, `scm/tests/unit/test_tui_k9s.py`)

- `TestResolvePlatform` — aliases (`:azdo`, `:ado`, `:4`...).
- `TestPlatformTools` — carga real de `TOOLS`/`SCRIPTS`, orden por
  grupo, outcome_dir.
- `TestParseCommand` — todas las acciones del parser.
- `TestRunFlag` — `--run` invoca `run_tool`/`run_script` sin menú,
  normalización de claves, exit 2 en clave inválida.
- `TestScreens` — `run_test()` headless: arranque en PlatformsScreen,
  carga de tools AZDO (38), filtro en vivo, Enter lanza tool (mock),
  Esc vuelve, `:aws` dispatch.

## Pendiente / fase futura

- Vistas nativas de recursos vivos (`:pipelines`, `:releases`,
  `:pods` con auto-refresh) — la arquitectura screens+registry ya lo
  permite; requiere refactorizar tools a providers de datos.
- Build PyInstaller: resuelto — `toolbox_build_executables.py` ya
  incluye `--collect-all textual` (Textual carga CSS/widgets desde
  package data, `--collect-all` empaqueta los assets junto a los módulos).
