"""Widgets de la TUI con el look 'stock' de k9s.

Layout k9s: logo+info (header) ▸ crumbs (steelblue) ▸ título
`<vista(ctx)[count]>` ▸ tabla ▸ hints ▸ línea de comandos `toolbox>`.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import DataTable, Input, Static

from . import skin

_LOGO = (
    f"[{skin.CYBER_CYAN}]██████╗  ███████╗  ██████╗ [/]\n"
    f"[{skin.CYBER_CYAN}]██╔══██╗ ██╔════╝ ██╔═══██╗[/]\n"
    f"[{skin.CYBER_BLUE}]██║  ██║ ███████╗ ██║   ██║[/]\n"
    f"[{skin.CYBER_BLUE}]██║  ██║ ╚════██║ ██║   ██║[/]\n"
    f"[{skin.CYBER_PURPLE}]██████╔╝ ███████║ ╚██████╔╝[/]\n"
    f"[{skin.CYBER_PURPLE}]╚═════╝  ╚══════╝  ╚═════╝ [/]"
)


class LogoHeader(Horizontal):
    """Bloque superior: info izquierda + logo DSO arriba-derecha.

    Look "Cyberpunk / DevSecOps": [ DSO-TOOLBOX ], Tactical Suite,
    Scope y Profile a la izquierda; logo ASCII degradado cyan/azul/
    púrpura alineado a la derecha.
    """

    def __init__(self) -> None:
        super().__init__(id="logo-header")
        self._info = Static("", id="k9s-info")

    def compose(self) -> ComposeResult:
        yield self._info
        yield Static(_LOGO, id="logo")

    def set_info(self, fields: dict) -> None:
        """fields: {"Etiqueta": "valor-markup"} — una línea por campo.

        Los valores ya vienen formateados (markup) por el llamador.
        """
        self._info.update("\n".join(fields.values()))


class ContextBar(Static):
    """Línea de contexto, estilo banner de k9s.

    Una sola línea separadora superior dibujada con CSS border-top
    (ocupa el 100% del ancho siempre); el contenido va en la línea
    inferior:

        ─────────────────────────────────────────────  (border)
         CONTEXT: azdo   AUTH: ● config   TOOLS: 38
    """

    def set_context(self, fields: dict) -> None:
        """fields: {"CLAVE": "valor-markup"}."""
        line = " ".join(
            f"[{skin.WHITE} bold]{k}:[/] {v}" for k, v in fields.items())
        self.update(f" {line}")


class CrumbBar(Static):
    """Breadcrumbs: negro sobre steelblue, segmento activo en naranja."""

    def set_crumbs(self, *crumbs: str, right: str = "") -> None:
        segs = []
        for i, c in enumerate(crumbs):
            if i == len(crumbs) - 1:
                segs.append(f"[{skin.ORANGE} bold]{c}[/]")
            else:
                segs.append(f"[{skin.BLACK} bold]{c}[/]")
        left = f"[{skin.BLACK}] ▸ [/]".join(segs)
        right_txt = f"[{skin.BLACK}]{right}[/]" if right else ""
        self.update(f" {left}    {right_txt}")


class TableTitle(Static):
    """Título de la vista: `<vista(ctx)[count]>` y `/filtro` (estilo k9s)."""

    def set_title(self, view: str, ctx: str = "", count=None,
                  filter_text: str = "") -> None:
        t = f"[{skin.AQUA} bold]<{view}[/]"
        if ctx:
            t += f"[{skin.FUCHSIA} bold]({ctx})[/]"
        if count is not None:
            t += f"[{skin.PAPAYAWHIP} bold]\\[{count}\\][/]"
        t += f"[{skin.AQUA} bold]>[/]"
        if filter_text:
            t += f" [{skin.STEELBLUE} bold]/{filter_text}[/]"
        self.update(t)


class HintsBar(Static):
    """Línea de atajos estilo menú k9s: `<tecla>Acción  <tecla>Acción`."""

    def set_hints(self, hints: list) -> None:
        """hints: [(tecla, acción)] — teclas numéricas en fuchsia."""
        parts = []
        for key, label in hints:
            kc = skin.FUCHSIA if key[:1].isdigit() else skin.DODGERBLUE
            parts.append(f"[{kc} bold]<{key}>[/][dim]{label}[/]")
        self.update(" " + " ".join(parts))


class CommandBar(Horizontal):
    """Línea de comandos inferior estilo k9s.

    Idle muestra el prompt `toolbox>` (cadetblue); con `:`/`/` se abre
    el input. Emite CommandBar.Submitted(texto, modo) al Enter.
    """

    PROMPT = "toolbox>"
    can_focus = True

    class Submitted(Message):
        def __init__(self, text: str, mode: str) -> None:
            self.text = text
            self.mode = mode          # "cmd" | "filter"
            super().__init__()

    class Cancelled(Message):
        pass

    def __init__(self) -> None:
        super().__init__(id="cmdbar")
        self.mode = "cmd"
        self._history: list = []
        self._hist_idx = -1

    def compose(self) -> ComposeResult:
        yield Static(self.PROMPT, id="cmdbar-prompt")
        yield Input(id="cmdbar-input")

    def on_mount(self) -> None:
        self.query_one("#cmdbar-input", Input).display = False

    def open(self, mode: str, prefix: str = "") -> None:
        """Abre el input. mode='cmd' → ':' ; mode='filter' → '/'."""
        self.mode = mode
        self.query_one("#cmdbar-prompt", Static).update(
            ":" if mode == "cmd" else "/")
        inp = self.query_one("#cmdbar-input", Input)
        inp.display = True
        inp.value = prefix
        inp.placeholder = ("comando (:azdo :15 :outcome :q...)"
                           if mode == "cmd" else "filtrar tabla...")
        inp.focus()
        inp.action_end()

    def close(self) -> None:
        self.query_one("#cmdbar-input", Input).display = False
        self.query_one("#cmdbar-prompt", Static).update(self.PROMPT)

    @property
    def is_open(self) -> bool:
        try:
            return bool(self.query_one("#cmdbar-input", Input).display)
        except Exception:
            return False

    def on_input_changed(self, event: Input.Changed) -> None:
        # El filtro es en vivo: cada tecla filtra la tabla actual
        if self.mode == "filter":
            self.post_message(self.Submitted(event.value, "filter"))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if self.mode == "cmd" and text:
            self._history.append(text)
        self._hist_idx = -1
        self.close()
        self.post_message(self.Submitted(text, self.mode))
        event.input.value = ""

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.close()
            self.post_message(self.Cancelled())
            event.stop()
        elif event.key == "up" and self.mode == "cmd" and self._history:
            inp = self.query_one("#cmdbar-input", Input)
            self._hist_idx = min(self._hist_idx + 1,
                                 len(self._history) - 1)
            inp.value = self._history[-1 - self._hist_idx]
            inp.action_end()
            event.stop()


class ToolsTable(DataTable):
    """Tabla de herramientas/recursos con filtro en vivo (cursor de k9s)."""

    def __init__(self) -> None:
        super().__init__(cursor_type="row", zebra_stripes=False)
        self._rows_all: list = []       # (key, [celdas])
        self._filter = ""

    def load(self, columns: list, rows: list) -> None:
        """columns: [str...] ; rows: [(row_key, [celdas])]."""
        self.clear(columns=True)
        self.add_columns(*columns)
        self._rows_all = rows
        self._rebuild()

    def set_filter(self, text: str) -> None:
        self._filter = text.strip().lower()
        self._rebuild()

    @property
    def filter_text(self) -> str:
        return self._filter

    @property
    def current_key(self):
        """Key de la fila bajo el cursor, o None."""
        if self.row_count == 0:
            return None
        row = self.cursor_row
        keys = list(self.rows.keys())
        if 0 <= row < len(keys):
            return keys[row].value
        return None

    def _rebuild(self) -> None:
        self.clear()
        f = self._filter
        for key, cells in self._rows_all:
            if f and not any(f in str(c).lower() for c in cells):
                continue
            self.add_row(*cells, key=str(key))
