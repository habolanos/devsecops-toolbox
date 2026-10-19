"""Screens de la TUI con el chrome estilo k9s (logo ▸ crumbs ▸ tabla ▸ hints)."""

import sys
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.css.query import NoMatches
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Static
from textual.worker import WorkerState

from . import commands, registry, skin
from .widgets import (CommandBar, ContextBar, CrumbBar, HintsBar,
                      LogoHeader, TableTitle, ToolsTable)

_VERSION = "?"


def _version() -> str:
    """Versión del toolbox desde VERSION en la raíz del repo."""
    global _VERSION
    if _VERSION == "?":
        try:
            _VERSION = (registry.SCM_DIR.parent / "VERSION")\
                .read_text(encoding="utf-8").strip()
        except Exception:
            _VERSION = "dev"
    return _VERSION


def _configured(platform_key: str) -> bool:
    """True si la plataforma tiene config (reusa is_platform_configured)."""
    try:
        main_mod = sys.modules.get("__main__")
        fn = getattr(main_mod, "is_platform_configured", None)
        if fn is None:
            import main as main_mod
            fn = main_mod.is_platform_configured
        return bool(fn(registry.PLATFORMS[platform_key]["main_key"]))
    except Exception:
        return False


def _status_dot(status: str) -> Text:
    """Dot `●` de estado (columna PF de k9s) coloreado según skin."""
    color = skin.STATUS_COLORS.get(status, skin.STATUS_COLORS["completed"])
    return Text("●", style=color)


def _outcome_count() -> int:
    try:
        out = registry.outcome_dir()
        return sum(1 for p in out.rglob("*") if p.is_file()) \
            if out.exists() else 0
    except Exception:
        return 0


def _header_info() -> dict:
    """Info del banner (mockup cyberpunk): título, suite, scope, profile."""
    return {
        "title": f"[{skin.WHITE} bold]\\[ DSO-TOOLBOX ][/]  "
                 f"[{skin.CYBER_PURPLE}]v{_version()}[/]",
        "suite": f"[{skin.CYBER_PURPLE}]DevSecOps Tactical Suite[/]",
        "scope": f"[{skin.WHITE} bold]Scope:[/] "
                 f"[{skin.CYBER_GREEN}]GKE[/] "
                 f"[{skin.CYBER_GRAY}]│[/] "
                 f"[{skin.CYBER_YELLOW}]Cloud Run[/] "
                 f"[{skin.CYBER_GRAY}]│[/] "
                 f"[{skin.CYBER_BLUE}]Azure DevOps[/]",
        "profile": f"[{skin.WHITE} bold]Profile:[/] "
                   f"[{skin.CYBER_PURPLE}]DevSecOps / SCM Engineer "
                   f"Platform[/]",
    }


def _sync_title(screen: Screen, view: str, ctx: str = "") -> None:
    """Actualiza el TableTitle `<vista(ctx)[count]>` con filtro activo."""
    table = screen.query_one(ToolsTable)
    screen.query_one(TableTitle).set_title(
        view, ctx, table.row_count, table.filter_text)


_LOADING_ROW = ("__loading__", ["", "…", "cargando…", ""])

class PlatformsScreen(Screen):
    """Contexto raíz: tabla de plataformas (equivalente a `:ctx` de k9s)."""

    def compose(self) -> ComposeResult:
        yield LogoHeader()
        yield ContextBar()
        yield CrumbBar(id="crumb")
        yield TableTitle()
        yield ToolsTable()
        yield HintsBar()
        yield CommandBar()

    def on_mount(self) -> None:
        # Shell visible al instante; los datos pesados (config ×6 +
        # scan de outcome/) se hidratan en un worker.
        self.query_one(LogoHeader).set_info(_header_info())
        self.query_one(ContextBar).set_context({
            "CONTEXT": f"[{skin.CYBER_GREEN}]toolbox[/]",
            "AUTH": f"[{skin.CYBER_GRAY}]…[/]",
            "OUTCOME": f"[{skin.CYBER_GRAY}]…[/]",
        })
        self.query_one(CrumbBar).set_crumbs("toolbox", "contexts")
        self.query_one(HintsBar).set_hints([
            ("enter", "Entrar"), ("0-9", "Quick"), ("/", "Filtro"),
            (":", "Cmd"), ("r", "Reload"), ("?", "Ayuda"), ("q", "Salir"),
        ])
        table = self.query_one(ToolsTable)
        table.load(["#", "CONTEXT", "ST", "DESC"], [_LOADING_ROW])
        _sync_title(self, "contexts")
        table.focus()
        self.run_worker(self._hydrate, name="hydrate-contexts",
                        thread=True)

    def _hydrate(self) -> dict:
        """Datos pesados en hilo: config por plataforma, descripción
        (de main.PLATFORMS) y conteo de archivos en outcome/."""
        configured = {}
        descs = {}
        main_mod = sys.modules.get("__main__")
        if main_mod is None or not hasattr(main_mod, "PLATFORMS"):
            try:
                import main as main_mod
            except Exception:
                main_mod = None
        main_plats = getattr(main_mod, "PLATFORMS", {}) or {}
        for k, meta in registry.PLATFORMS.items():
            configured[k] = _configured(k)
            descs[k] = main_plats.get(meta["main_key"], {})\
                .get("description", "")
        return {"configured": configured, "desc": descs,
                "outcome": _outcome_count()}

    def on_worker_state_changed(self, event) -> None:
        if getattr(event.worker, "name", "") != "hydrate-contexts" \
                or event.state != WorkerState.SUCCESS:
            return
        data = event.worker.result
        try:
            table = self.query_one(ToolsTable)
            rows = []
            for key, meta in registry.PLATFORMS.items():
                ok = data["configured"].get(key, False)
                rows.append((key, [
                    meta["main_key"],
                    f"{meta['emoji']} {meta['label']}",
                    _status_dot("ready" if ok else "error"),
                    data["desc"].get(key, ""),
                ]))
            table.load(["#", "CONTEXT", "ST", "DESC"], rows)
            n_ok = sum(1 for v in data["configured"].values() if v)
            self.query_one(ContextBar).set_context({
                "CONTEXT": f"[{skin.CYBER_GREEN}]toolbox[/]",
                "AUTH": f"[{skin.CYBER_GREEN}]●[/] "
                        f"[{skin.CYBER_WHITE}]{n_ok}/"
                        f"{len(registry.PLATFORMS)} platforms[/]",
                "OUTCOME": f"[{skin.CYBER_PURPLE}]"
                           f"{data['outcome']} archivos[/]",
            })
            _sync_title(self, "contexts")
            table.focus()
        except NoMatches:
            pass  # la screen ya no existe (pop rápido)

    def on_command_bar_submitted(self, event: CommandBar.Submitted) -> None:
        if event.mode == "filter":
            self.query_one(ToolsTable).set_filter(event.text)
            _sync_title(self, "contexts")
            return
        cmd = commands.parse_command(event.text)
        self.app.dispatch_command(cmd)

    def on_command_bar_cancelled(self, event: CommandBar.Cancelled) -> None:
        self.query_one(ToolsTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value
        if key in registry.PLATFORMS:
            self.app.push_tools_screen(key)
        # "__loading__" (hidratación en curso) se ignora


class ToolsScreen(Screen):
    """Tabla de herramientas de una plataforma."""

    def __init__(self, platform_key: str) -> None:
        super().__init__()
        self.platform_key = platform_key
        self._load_error: str = ""

    def compose(self) -> ComposeResult:
        yield LogoHeader()
        yield ContextBar()
        yield CrumbBar(id="crumb")
        yield TableTitle()
        yield ToolsTable()
        yield Static("", id="load-error")
        yield HintsBar()
        yield CommandBar()

    def on_mount(self) -> None:
        meta = registry.PLATFORMS[self.platform_key]
        self.query_one(LogoHeader).set_info(_header_info())
        self.query_one(CrumbBar).set_crumbs(
            "toolbox", "contexts", meta["label"])
        self.query_one(HintsBar).set_hints([
            ("enter", "Run"), ("0-9", "Quick"), ("/", "Filtro"),
            (":", "Cmd"), ("o", "Outcome"), ("r", "Reload"),
            ("?", "Ayuda"), ("esc", "Atrás"), ("q", "Volver"),
        ])
        table = self.query_one(ToolsTable)
        table.load(["#", "ST", "GROUP", "NAME", "DESC"], [_LOADING_ROW])
        self.query_one(ContextBar).set_context({
            "CONTEXT": f"[{skin.CYBER_GREEN}]{self.platform_key}[/]",
            "AUTH": f"[{skin.CYBER_GRAY}]…[/]",
            "TOOLS": f"[{skin.CYBER_GRAY}]…[/]",
        })
        _sync_title(self, "tools", self._title_ctx())
        table.focus()
        self.reload_tools()

    def _title_ctx(self) -> str:
        return registry.PLATFORMS[self.platform_key]["label"].split()[0]\
            .lower()

    def reload_tools(self) -> None:
        """Hidrata las tools en un worker (el import del tools.py de
        la plataforma es lo pesado; la UI queda libre al instante)."""
        self.run_worker(self._hydrate_tools, name="hydrate-tools",
                        thread=True)

    def _hydrate_tools(self) -> dict:
        try:
            rows = registry.platform_tools(self.platform_key)
            return {"rows": rows, "error": "", "ok": _configured(
                self.platform_key)}
        except Exception as e:
            return {"rows": [], "error": str(e), "ok": False}

    def on_worker_state_changed(self, event) -> None:
        if getattr(event.worker, "name", "") != "hydrate-tools" \
                or event.state != WorkerState.SUCCESS:
            return
        data = event.worker.result
        self._load_error = data["error"]
        rows = data["rows"]
        try:
            table = self.query_one(ToolsTable)
            table.load(
                ["#", "ST", "GROUP", "NAME", "DESC"],
                [(r["key"], [r["key"], _status_dot(r["status"]),
                             r["group_label"], r["name"],
                             r["description"]])
                 for r in rows])
            label = registry.PLATFORMS[self.platform_key]["label"]
            auth = (
                f"[{skin.CYBER_GREEN}]●[/] "
                f"[{skin.CYBER_WHITE}]{label}[/]" if data["ok"] else
                f"[{skin.ORANGERED}]●[/] "
                f"[{skin.CYBER_WHITE}]sin config[/]")
            self.query_one(ContextBar).set_context({
                "CONTEXT": f"[{skin.CYBER_GREEN}]{self.platform_key}[/]",
                "AUTH": auth,
                "TOOLS": f"[{skin.CYBER_PURPLE}]{table.row_count}[/]",
            })
            _sync_title(self, "tools", self._title_ctx())
            err = self.query_one("#load-error", Static)
            if self._load_error:
                err.update(
                    f"⚠ No se pudo cargar el registry: "
                    f"{self._load_error}\n"
                    f"[dim]Enter abre el menú clásico de la "
                    f"plataforma.[/]")
            else:
                err.update("")
            table.focus()
        except NoMatches:
            pass  # screen popeada antes de terminar el worker

    def on_command_bar_submitted(self, event: CommandBar.Submitted) -> None:
        if event.mode == "filter":
            self.query_one(ToolsTable).set_filter(event.text)
            _sync_title(self, "tools", self._title_ctx())
            return
        cmd = commands.parse_command(event.text,
                                     context_platform=self.platform_key)
        self.app.dispatch_command(cmd)

    def on_command_bar_cancelled(self, event: CommandBar.Cancelled) -> None:
        self.query_one(ToolsTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value
        if key.startswith("__"):
            return  # fila "cargando…" — hidratación aún en curso
        self.app.launch_tool(self.platform_key, key)


class OutcomeScreen(Screen):
    """Navegador de archivos generados en outcome/ (`:outcome`)."""

    def compose(self) -> ComposeResult:
        yield LogoHeader()
        yield ContextBar()
        yield CrumbBar(id="crumb")
        yield TableTitle()
        yield ToolsTable()
        yield HintsBar()
        yield CommandBar()

    def on_mount(self) -> None:
        self.query_one(LogoHeader).set_info(_header_info())
        self.query_one(ContextBar).set_context({
            "CONTEXT": f"[{skin.CYBER_GREEN}]outcome[/]",
            "DIR": f"[{skin.CYBER_WHITE}]"
                   f"{registry.outcome_dir()}[/]",
        })
        self.query_one(CrumbBar).set_crumbs("toolbox", "outcome")
        self.query_one(HintsBar).set_hints([
            ("enter", "Abrir"), ("/", "Filtro"), (":", "Cmd"),
            ("r", "Reload"), ("esc", "Atrás"),
        ])
        self.reload_files()

    def reload_files(self) -> None:
        """Scan de outcome/ en worker (rglob puede ser pesado)."""
        self.query_one(ToolsTable).load(
            ["FILE", "SIZE", "MODIFIED"], [_LOADING_ROW])
        _sync_title(self, "outcome", "files")
        self.query_one(ToolsTable).focus()
        self.run_worker(self._hydrate_files, name="hydrate-outcome",
                        thread=True)

    def _hydrate_files(self) -> list:
        out = registry.outcome_dir()
        rows = []
        if out.exists():
            files = sorted((f for f in out.rglob("*") if f.is_file()),
                           key=lambda p: p.stat().st_mtime, reverse=True)
            for f in files[:400]:
                rel = f.relative_to(out)
                rows.append((str(f), [
                    str(rel),
                    f"{f.stat().st_size / 1024:,.1f} KB",
                    datetime.fromtimestamp(f.stat().st_mtime)
                            .strftime("%Y-%m-%d %H:%M"),
                ]))
        return rows

    def on_worker_state_changed(self, event) -> None:
        if getattr(event.worker, "name", "") != "hydrate-outcome" \
                or event.state != WorkerState.SUCCESS:
            return
        try:
            self.query_one(ToolsTable).load(
                ["FILE", "SIZE", "MODIFIED"], event.worker.result)
            _sync_title(self, "outcome", "files")
            self.query_one(ToolsTable).focus()
        except NoMatches:
            pass

    def on_command_bar_submitted(self, event: CommandBar.Submitted) -> None:
        if event.mode == "filter":
            self.query_one(ToolsTable).set_filter(event.text)
            _sync_title(self, "outcome", "files")
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
            "[bold #00ffff]<toolbox>[/] [dim]k9s stock skin[/]\n\n"
            "[bold #ffffff]Navegación[/]\n"
            "  [#1e90ff]<enter>[/]     Ejecutar tool / entrar a plataforma\n"
            "  [#1e90ff]<esc>/<q>[/]   Volver / salir\n"
            "  [#1e90ff]<↑>/<↓>[/]     Mover cursor\n\n"
            "[bold #ffffff]Comandos[/]\n"
            "  [#1e90ff]:azdo :gcp :aws :azure :terminal :kpi[/]  Plataforma\n"
            "  [#1e90ff]:15[/]           Ejecutar tool por clave\n"
            "  [#1e90ff]:all/:allj[/]    Ejecutar todo (opción A / B)\n"
            "  [#1e90ff]:outcome[/]      Navegador de reportes\n"
            "  [#1e90ff]:reload[/]       Recargar config y registry\n"
            "  [#1e90ff]:back[/]         Volver\n"
            "  [#1e90ff]:q[/]            Salir\n\n"
            "[bold #ffffff]Filtro[/]\n"
            "  [#1e90ff]/texto[/]        Filtra la tabla en vivo\n"
            "  [#1e90ff]<esc>[/]         Cierra barra / limpia\n\n"
            "[dim]El menú clásico sigue disponible con --classic[/]",
            id="help-panel")
