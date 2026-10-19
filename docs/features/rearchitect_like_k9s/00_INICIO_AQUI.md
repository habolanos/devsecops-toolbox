# 00 — Inicio aquí: TUI estilo k9s

## Qué es

`devsecops-toolbox` ahora arranca en una TUI full-screen inspirada en
k9s (la UI de Kubernetes). En lugar de elegir plataforma con un número
y luego otra opción numerada, navegas una tabla de herramientas con
filtro en vivo, comandos `:` y ejecución con Enter.

## Decisiones clave

- **Alcance**: navegador k9s de *tools* — las herramientas son los
  "recursos" de la tabla. No se reescribió ninguna herramienta.
- **Framework**: Textual 8.2.x (mismo ecosistema que Rich, ya usado).
- **Ejecución**: 100% subprocess — la TUI suspende la terminal
  (`app.suspend()`) y lanza `python <plat>/tools.py --run <key>` con el
  mismo env-prep de `launch_platform`. Los prompts, spinners y
  submenús interactivos de cada tool funcionan idéntico.
- **Coexistencia**: el menú clásico es el default;
  `python scm/main.py --k9s-style` abre la TUI. Si no hay TTY o
  Textual no está instalado, cae al clásico automáticamente.
- **Multi-plataforma**: las 6 plataformas se leen por import perezoso
  de sus dicts `TOOLS`/`SCRIPTS` (los `tools.py` ya son paquetes con
  guard `__main__`).

## Flujo

```
TUI (main.py + Textual)
   Enter en "CD Detailed Inventory"
   app.suspend()  →  terminal normal
   subprocess: python scm/azdo/tools.py --run 15
     → run_tool("15") directo (sin menú) → prompts → script real
   subprocess termina → TUI resume → toast "✓ exit 0 (12.3s)"
```

## Estado

Implementado: núcleo navegable end-to-end, filtro en vivo, comandos
`:`, outcome browser (`:outcome`), historial de comandos (↑ en la
barra), `r` recarga, `?` ayuda, toast post-run. 25 tests nuevos.
