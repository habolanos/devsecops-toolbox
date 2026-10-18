"""Screens de la TUI: plataformas, tools de una plataforma, outcome."""

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Static

from . import commands, registry
from .widgets import CommandBar, CrumbBar, ToolsTable


def _config_badge(platform_key: str) -> str:
    """Badge de configuración reutilizando is_platform_configured."""
    try:
        import sys
        main_mod = sys.modules.get("__main__")
        fn = getattr(main_mod, "is_platform_configured", None)
        if fn is None:
            import main as main_mod
            fn = main_mod.is_platform_configured
        ok = fn(registry.PLATFORMS[platform_key]["main_key"])
        return "[green]✅[/]" if ok else "[yellow]⚠️[/]"
    except Exception:
        return "[dim]—[/]"


class PlatformsScreen(Screen):
    """Contexto raíz: tabla de plataformas (equivalente a `:ctx` de k9s)."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield CrumbBar(id="crumb")
        with Vertical():
            yield ToolsTable()
        yield CommandBar()
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CrumbBar).set_crumbs(
            "toolbox", right="Enter: entrar   :cmd   /filtro   q: salir")
        table = self.query_one(ToolsTable)
        rows = []
        for key, meta in registry.PLATFORMS.items():
            badge = _config_badge(key)
            rows.append((key, [
                meta["main_key"],
                f"{meta['emoji']} {meta['label']}",
                badge,
                meta.get("desc", ""),
            ]))
        table.load(["#", "Plataforma", "Config", ""], rows)
        table.focus()

    def on_command_bar_submitted(self, event: CommandBar.Submitted) -> None:
        if event.mode == "filter":
            self.query_one(ToolsTable).set_filter(event.text)
            return
        cmd = commands.parse_command(event.text)
        self.app.dispatch_command(cmd)

    def on_command_bar_cancelled(self, event: CommandBar.Cancelled) -> None:
        self.query_one(ToolsTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value
        if key in registry.PLATFORMS:
            self.app.push_tools_screen(key)


class ToolsScreen(Screen):
    """Tabla de herramientas de una plataforma."""

    def __init__(self, platform_key: str) -> None:
        super().__init__()
        self.platform_key = platform_key
        self._load_error: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield CrumbBar(id="crumb")
        with Vertical():
            yield ToolsTable()
            yield Static("", id="load-error")
        yield CommandBar()
        yield Footer()

    def on_mount(self) -> None:
        meta = registry.PLATFORMS[self.platform_key]
        self.query_one(CrumbBar).set_crumbs(
            "toolbox", meta["label"],
            right="Enter: ejecutar   :cmd   /filtro   Esc: volver")
        self.reload_tools()

    def reload_tools(self) -> None:
        table = self.query_one(ToolsTable)
        try:
            rows = registry.platform_tools(self.platform_key)
            self._load_error = ""
        except Exception as e:
            rows = []
            self._load_error = str(e)
        table.load(["#", "Grupo", "Herramienta", "Descripción"],
                   [(r["key"], [r["key"], r["group_label"], r["name"],
                                r["description"]]) for r in rows])
        err = self.query_one("#load-error", Static)
        if self._load_error:
            err.update(
                f"[red]⚠ No se pudo cargar el registry: "
                f"{self._load_error}[/]\n"
                f"[dim]Enter abre el menú clásico de la plataforma.[/]")
        else:
            err.update("")
        table.focus()

    def on_command_bar_submitted(self, event: CommandBar.Submitted) -> None:
        if event.mode == "filter":
            self.query_one(ToolsTable).set_filter(event.text)
            return
        cmd = commands.parse_command(event.text,
                                     context_platform=self.platform_key)
        self.app.dispatch_command(cmd)

    def on_command_bar_cancelled(self, event: CommandBar.Cancelled) -> None:
        self.query_one(ToolsTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value
        self.app.launch_tool(self.platform_key, key)


class OutcomeScreen(Screen):
    """Navegador de archivos generados en outcome/ (`:outcome`)."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield CrumbBar(id="crumb")
        with Vertical():
            yield ToolsTable()
        yield CommandBar()
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CrumbBar).set_crumbs(
            "toolbox", "outcome",
            right="Enter: abrir carpeta   /filtro   Esc: volver")
        self.reload_files()

    def reload_files(self) -> None:
        out = registry.outcome_dir()
        rows = []
        if out.exists():
            files = sorted(out.rglob("*"), key=lambda p: p.stat().st_mtime,
                           reverse=True)
            for i, f in enumerate(files[:400]):
                if f.is_dir():
                    continue
                rel = f.relative_to(out)
                rows.append((str(f), [
                    str(rel),
                    f"{f.stat().st_size / 1024:,.1f} KB",
                    datetime.fromtimestamp(f.stat().st_mtime)
                            .strftime("%Y-%m-%d %H:%M"),
                ]))
        self.query_one(ToolsTable).load(["Archivo", "Tamaño", "Modificado"],
                                        rows)
        self.query_one(ToolsTable).focus()

    def on_command_bar_submitted(self, event: CommandBar.Submitted) -> None:
        if event.mode == "filter":
            self.query_one(ToolsTable).set_filter(event.text)
            return
        self.app.dispatch_command(commands.parse_command(event.text))

    def on_command_bar_cancelled(self, event: CommandBar.Cancelled) -> None:
        self.query_one(ToolsTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        path = Path(event.row_key.value)
        self.app.open_in_file_manager(path)


class HelpScreen(ModalScreen):
    """Modal con el keymap (`?` o `:help`)."""

    BINDINGS = [("escape", "dismiss", "Cerrar"), ("q", "dismiss", "Cerrar")]

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold cyan]DevSecOps Toolbox — k9s style[/]\n\n"
            "[bold]Navegación[/]\n"
            "  Enter        Ejecutar tool / entrar a plataforma\n"
            "  Esc / q      Volver / salir\n"
            "  ↑ ↓          Mover cursor\n\n"
            "[bold]Comandos[/]\n"
            "  :azdo :gcp :aws :azure :terminal :kpi   Saltar a plataforma\n"
            "  :15            Ejecutar tool por clave\n"
            "  :all / :allj   Ejecutar todo (opción A / B)\n"
            "  :outcome       Navegador de reportes\n"
            "  :reload        Recargar config y registry\n"
            "  :back          Volver\n"
            "  :q             Salir\n\n"
            "[bold]Filtro[/]\n"
            "  /texto         Filtra la tabla en vivo\n"
            "  Esc            Cierra barra / limpia\n\n"
            "[dim]El menú clásico sigue disponible con --classic[/]",
            id="help-panel")
