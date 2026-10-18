"""Widgets de la TUI estilo k9s: barra de comandos, breadcrumb y tabla."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import DataTable, Input, Static


class CrumbBar(Static):
    """Barra superior: breadcrumb + contexto (estilo header de k9s)."""

    def set_crumbs(self, *crumbs: str, right: str = "") -> None:
        left = " [bold cyan]▸[/] ".join(f"[bold]{c}[/]" for c in crumbs)
        right_txt = f"[dim]{right}[/]" if right else ""
        self.update(f" {left}    {right_txt}")


class CommandBar(Horizontal):
    """Input inferior activado con `:` (comando) o `/` (filtro).

    Emite CommandBar.Submitted(texto, modo) al Enter y se oculta solo.
    """

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
        yield Static(":", id="cmdbar-prompt")
        yield Input(placeholder="comando...", id="cmdbar-input")

    def on_mount(self) -> None:
        self.display = False

    def open(self, mode: str, prefix: str = "") -> None:
        """Muestra la barra. mode='cmd' → ':' ; mode='filter' → '/'."""
        self.mode = mode
        self.query_one("#cmdbar-prompt", Static).update(
            ":" if mode == "cmd" else "/")
        inp = self.query_one("#cmdbar-input", Input)
        inp.value = prefix
        inp.placeholder = ("comando (:azdo :15 :outcome :q...)"
                           if mode == "cmd" else "filtrar tabla...")
        self.display = True
        inp.focus()
        inp.action_end()

    def close(self) -> None:
        self.display = False

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
    """Tabla de herramientas/recursos con filtro en vivo."""

    def __init__(self) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True)
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
