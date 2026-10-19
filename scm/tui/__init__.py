"""
DevSecOps Toolbox TUI — interfaz full-screen estilo k9s (Textual).

Navegación por contextos (plataformas) y recursos (herramientas):
- `Enter` ejecuta la herramienta vía subprocess `tools.py --run <key>`
- `/` filtra la tabla en vivo
- `:` comandos (`:azdo`, `:15`, `:outcome`, `:all`, `:q`)
- `Esc`/`q` retrocede, `?` ayuda, `r` recarga config/registry
"""

__version__ = "1.0.6"
