"""Paleta y CSS de la skin "stock" de k9s para la TUI.

Referencia: https://github.com/derailed/k9s/blob/master/skins/stock.yaml

Mapeo k9s → widget:
  body.fgColor/bgColor      → Screen background/texto base
  body.logoColor            → bloque del logo ASCII
  info.fgColor/sectionColor → valores/etiquetas del bloque superior
  frame.border.fgColor      → bordes, teclas de hints
  frame.crumbs              → CrumbBar (negro sobre steelblue, activo naranja)
  frame.title               → TableTitle `<vista(ctx)[count]>`
  frame.menu                → HintsBar (texto dim, teclas dodgerblue/fuchsia)
  frame.status              → dots de estado de la tabla
  prompt                    → CommandBar (`toolbox>` idle, `:`/`/` abierto)
  views.table               → DataTable (texto dodgerblue, cursor negro/aqua)
"""

BLACK = "#000000"
DODGERBLUE = "#1E90FF"
ORANGE = "#FFA500"
AQUA = "#00FFFF"
WHITE = "#FFFFFF"
STEELBLUE = "#4682B4"
PAPAYAWHIP = "#FFEFD5"
FUCHSIA = "#FF00FF"
CADETBLUE = "#5F9EA0"
GRAY = "#808080"
GREENYELLOW = "#ADFF2F"
LIGHTSKYBLUE = "#87CEFA"
DARKORANGE = "#FF8C00"
ORANGERED = "#FF4500"
MEDIUMPURPLE = "#9370DB"

# ── Paleta Cyberpunk / DevSecOps del header (ANSI 256) ─────
# 51=#00ffff  39=#00afff  141=#af87ff  82=#5fff00
# 220=#ffd700 242=#6c6c6c 255=#eeeeee
CYBER_CYAN = "#00ffff"
CYBER_BLUE = "#00afff"
CYBER_PURPLE = "#af87ff"
CYBER_GREEN = "#5fff00"
CYBER_YELLOW = "#ffd700"
CYBER_GRAY = "#6c6c6c"
CYBER_WHITE = "#eeeeee"

# frame.status
STATUS_COLORS = {
    "ready": GREENYELLOW,
    "ok": GREENYELLOW,
    "running": GREENYELLOW,
    "new": LIGHTSKYBLUE,
    "modify": GREENYELLOW,
    "pending": DARKORANGE,
    "coming_soon": DARKORANGE,
    "warning": DARKORANGE,
    "error": ORANGERED,
    "kill": MEDIUMPURPLE,
    "completed": GRAY,
}

APP_CSS = f"""
Screen {{ background: {BLACK}; }}

/* ── Bloque superior: info izquierda + logo derecha ───────── */
LogoHeader {{ height: 6; background: {BLACK}; }}
#k9s-info {{ color: {CYBER_WHITE}; padding: 0 1; width: 1fr; }}
#logo {{ width: 33; padding: 0 1; content-align: right top; }}
ContextBar {{
    height: 2; background: {BLACK};
    border-bottom: solid {CYBER_GRAY};
}}

/* ── Breadcrumbs: negro sobre steelblue, activo naranja ───── */
CrumbBar {{ height: 1; background: {STEELBLUE}; color: {BLACK}; }}

/* ── Título de la vista: <vista(ctx)[count]> ──────────────── */
TableTitle {{ height: 1; background: {BLACK}; }}

/* ── Tabla (views.table) ──────────────────────────────────── */
ToolsTable {{ height: 1fr; background: {BLACK}; color: {DODGERBLUE}; }}
ToolsTable > .datatable--header {{
    background: {BLACK}; color: {WHITE}; text-style: bold;
}}
ToolsTable > .datatable--cursor {{
    background: {AQUA}; color: {BLACK}; text-style: bold;
}}
ToolsTable > .datatable--hover {{
    background: {BLACK}; color: {AQUA};
}}
ToolsTable .datatable--odd-row {{ background: {BLACK}; }}
ToolsTable .datatable--even-row {{ background: {BLACK}; }}

/* ── Menú de hints (frame.menu) ───────────────────────────── */
HintsBar {{ height: 1; background: {BLACK}; }}

/* ── Línea de comandos / prompt ───────────────────────────── */
#cmdbar {{ height: 1; dock: bottom; background: {BLACK}; padding: 0 1; }}
#cmdbar-prompt {{ width: 9; color: {CADETBLUE}; text-style: bold; }}
#cmdbar Input {{
    border: none; background: {BLACK}; color: {DODGERBLUE};
    height: 1; padding: 0;
}}
#cmdbar Input:focus {{ border: none; }}

#load-error {{ padding: 0 2; color: {ORANGERED}; }}

/* ── Modal de ayuda (dialog) ──────────────────────────────── */
HelpScreen {{ align: center middle; }}
#help-panel {{
    width: 64; padding: 1 2;
    background: {BLACK}; color: {DODGERBLUE};
    border: solid {DODGERBLUE};
}}
"""
