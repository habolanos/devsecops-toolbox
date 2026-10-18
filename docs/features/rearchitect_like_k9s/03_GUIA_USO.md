# 03 — Guía de uso: keymap estilo k9s

## Arranque

```bash
python scm/main.py            # TUI (default si hay terminal interactiva)
python scm/main.py --classic  # menú numerado clásico
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

Sin TTY (pipes/CI) o sin `textual` instalado, `main.py` cae
automáticamente al menú clásico. `--classic` lo fuerza siempre.
