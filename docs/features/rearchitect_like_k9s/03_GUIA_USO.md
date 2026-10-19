# 03 — Guía de uso: keymap estilo k9s

## Layout (skin "stock" de k9s + banner cyberpunk)

```
═══════════════                    ██████╗  ███████╗  ██████╗   ← logo
[ DSO-TOOLBOX ] v1.8.x             ██╔══██╗ ██╔════╝ ██╔═══██╗    degradado
DevSecOps Tactical Suite           ██║  ██║ ███████╗ ██║   ██║    cyan→azul→
Scope: GKE │ Cloud Run │ AzDO      ██║  ██║ ╚════██║ ██║   ██║    púrpura
Profile: DevSecOps / SRE Platform  ██████╔╝ ███████║ ╚██████╔╝  (derecha)
────────────────────────────────────────────────────────────────
 CONTEXT: azdo   AUTH: ● Azure DevOps   TOOLS: 38    ← ContextBar
toolbox ▸ contexts ▸ Azure DevOps                  ← crumbs (steelblue)
<tools(azdo)[38]>                                  ← título aqua + count
#   ST  GROUP      NAME                  DESC
15  ●   Inventario CD Detailed Inventory  ...      ← filas dodgerblue
44  ●   UpdatePipe SCM Inspection Remed.  ...      ← cursor negro/aqua
<enter>Run  <0-9>Quick  </>Filtro  <:>Cmd  <?>Ayuda  ← hints (abajo)
toolbox>                                           ← prompt (abajo)
```

Tabla y comandos usan la paleta "stock" de `skins/stock.yaml` del repo
de k9s; el banner usa la paleta Cyberpunk del toolbox (ANSI 51/39/141/
82/220/242/255). Ver `scm/tui/skin.py` para el mapeo completo. La
columna `ST` muestra el dot `●` de estado (verde = ready, naranja =
pendiente, rojo = error). Los comandos `:`, `/` y el prompt `toolbox>`
viven en la línea inferior, igual que la cmdline de k9s.

## Arranque

```bash
python scm/main.py                # menú numerado clásico (default)
python scm/main.py                # TUI full-screen estilo k9s (default)
python scm/main.py --classic      # menú numerado clásico
```

## Navegación

| Tecla | Acción |
|---|---|
| `↑` `↓` / `j` `k` | Mover cursor en la tabla |
| `Enter` | Entrar a plataforma / ejecutar tool |
| `Esc` | Volver (cierra la barra `:`/`/` primero) |
| `q` | Volver; en raíz = salir |
| `Ctrl+C` | Salir |

## Filtro en vivo

| Tecla | Acción |
|---|---|
| `/` | Abre la barra de filtro; cada tecla filtra nombre/grupo/descripción |
| `Esc` | Cierra la barra (el filtro queda aplicado; `/` + `Esc`+borrar limpia) |

## Comandos `:`

| Comando | Acción |
|---|---|
| `:azdo` `:gcp` `:aws` `:azure` `:terminal` `:kpi` | Saltar a la plataforma (aliases: `:ado`, `:sh`, `:4`...) |
| `:<N>` / `:<key>` | Ejecutar tool por clave en el contexto actual (`:15`, `:44`, `:1b`) |
| `:all` | Ejecutar "Ejecutar Todos" de la plataforma actual |
| `:allj` | Ejecutar "Ejecutar Todo + JSON" |
| `:outcome` / `:o` | Navegador de reportes de `outcome/` (Enter abre el archivo en el explorador) |
| `:reload` / `:r` | Recargar config.json + registry de tools |
| `:back` | Volver a la pantalla anterior |
| `:help` | Esta ayuda |
| `:q` | Salir |

En la barra `:` la tecla `↑` recorre el historial de comandos.

## Otros

| Tecla | Acción |
|---|---|
| `r` | Recarga directa (sin `:`) |
| `o` | Abre `:outcome` directo |
| `?` | Modal de ayuda |

## Ejecución de una tool

`Enter` suspende la TUI y lanza `python <plat>/tools.py --run <key>`
con el env preparado por `main.py` (credenciales, proxies,
`DEVSECOPS_OUTPUT_DIR`, PYTHONPATH=scm/). Todos los prompts,
confirmaciones y submenús de la tool funcionan igual que en el menú
clásico. Al terminar, la TUI vuelve a la tabla y muestra un toast con
el exit code y la duración.

## Fallback

Si no hay TTY (pipes/CI) o `textual` no está
instalado, `main.py` cae automáticamente al menú clásico e imprime
la causa. Sin el flag siempre arranca el clásico.
