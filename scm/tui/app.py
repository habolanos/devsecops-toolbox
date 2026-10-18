"""ToolboxApp — aplicación Textual estilo k9s para devsecops-toolbox."""

import os
import platform
import subprocess
import sys

from textual.app import App
from textual.binding import Binding

from . import commands, registry, runner
from .screens import (HelpScreen, OutcomeScreen, PlatformsScreen,
                      ToolsScreen)
from .widgets import CommandBar

SCM_DIR = registry.SCM_DIR


class ToolboxApp(App):
    """TUI full-screen: contextos (plataformas) ▸ recursos (tools)."""

    TITLE = "DevSecOps Toolbox"
    SUB_TITLE = "k9s mode"

    CSS = """
    #cmdbar {
        height: 3;
        dock: bottom;
        background: $surface-darken-1;
        border-top: solid $primary;
        display: none;
    }
    #cmdbar-prompt { width: 2; content-align: center middle;
                     text-style: bold; color: $accent; }
    #cmdbar Input { border: none; }
    CrumbBar {
        height: 1;
        padding: 0 1;
        background: $surface-darken-2;
        color: $text;
    }
    ToolsTable { height: 1fr; }
    #load-error { padding: 0 2; }
    HelpScreen { align: center middle; }
    #help-panel {
        width: 62; padding: 1 2;
        background: $panel; border: round $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit_or_back", "salir/volver"),
        Binding("colon", "open_cmd", ":"),
        Binding("slash", "open_filter", "/"),
        Binding("question_mark", "help", "?"),
        Binding("r", "reload", "reload"),
        Binding("o", "outcome", "outcome"),
        Binding("escape", "back", "atrás"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._last_run = None

    def on_mount(self) -> None:
        self.push_screen(PlatformsScreen())

    # ── Navegación ──────────────────────────────────────────────
    def push_tools_screen(self, platform_key: str) -> None:
        self.push_screen(ToolsScreen(platform_key))

    @property
    def current_platform(self):
        scr = self.screen
        return scr.platform_key if isinstance(scr, ToolsScreen) else None

    # ── Acciones globales ───────────────────────────────────────
    def action_open_cmd(self) -> None:
        self.screen.query_one(CommandBar).open("cmd")

    def action_open_filter(self) -> None:
        self.screen.query_one(CommandBar).open("filter")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_outcome(self) -> None:
        self.push_screen(OutcomeScreen())

    def action_quit_or_back(self) -> None:
        if isinstance(self.screen, PlatformsScreen):
            self.exit()
        else:
            self.action_back()

    def action_back(self) -> None:
        bar = self.screen.query_one(CommandBar)
        if bar.display:
            bar.close()
            return
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_reload(self) -> None:
        scr = self.screen
        if isinstance(scr, ToolsScreen):
            try:
                registry.reload_platform(scr.platform_key)
            except Exception:
                pass
            scr.reload_tools()
        elif isinstance(scr, OutcomeScreen):
            scr.reload_files()
        # invalidar config cacheada de main.py
        try:
            import main as main_mod
            main_mod._config = None
        except Exception:
            try:
                main_mod = sys.modules.get("__main__")
                if main_mod is not None:
                    main_mod._config = None
            except Exception:
                pass
        self.notify("Recargado", timeout=2)

    # ── Comandos `:` ────────────────────────────────────────────
    def dispatch_command(self, cmd: commands.Command) -> None:
        if cmd.action == "quit":
            self.exit()
        elif cmd.action == "back":
            self.action_back()
        elif cmd.action == "help":
            self.push_screen(HelpScreen())
        elif cmd.action == "outcome":
            self.push_screen(OutcomeScreen())
        elif cmd.action == "reload":
            self.action_reload()
        elif cmd.action == "platform":
            while len(self.screen_stack) > 1:
                self.pop_screen()
            self.push_tools_screen(cmd.arg)
        elif cmd.action == "tool":
            plat = self.current_platform
            if plat:
                self.launch_tool(plat, cmd.arg)
            else:
                self.notify("Sin contexto de plataforma",
                            severity="warning")
        elif cmd.action in ("all", "allj"):
            plat = self.current_platform
            if plat:
                self.launch_tool(plat, "A" if cmd.action == "all" else "B")
        else:
            self.notify(f"Comando desconocido: {cmd.raw}",
                        severity="warning")

    # ── Ejecución (subprocess con terminal suspendida) ──────────
    def launch_tool(self, platform_key: str, tool_key: str) -> None:
        meta = registry.PLATFORMS[platform_key]
        try:
            rows = registry.platform_tools(platform_key)
            names = {r["key"]: r["name"] for r in rows}
            if tool_key not in names and tool_key not in ("A", "B"):
                # clave inválida → aviso corto, no lanzar nada
                self.notify(f"Tool '{tool_key}' no existe en "
                            f"{meta['label']}", severity="error")
                return
            name = names.get(tool_key, tool_key)
        except Exception:
            name = tool_key  # registry roto → dejar que tools.py decida

        self.notify(f"▶ {meta['label']} — {name}", timeout=2)
        self.run_worker(self._run_suspended(platform_key, tool_key, name),
                        exclusive=True)

    async def _run_suspended(self, platform_key: str, tool_key: str,
                             name: str) -> None:
        with self.suspend():
            result = runner.run_tool(platform_key, tool_key, name)
        self._last_run = result
        icon = "✅" if result.returncode == 0 else "❌"
        self.notify(
            f"{icon} {name} — exit {result.returncode} "
            f"({result.elapsed:.1f}s)",
            severity="information" if result.returncode == 0 else "error",
            timeout=6)

    # ── Utilidades ──────────────────────────────────────────────
    def open_in_file_manager(self, path) -> None:
        """Abre el archivo/carpeta con el gestor del SO."""
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", "/select,", str(path)])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(Path(path).parent)])
            self.notify(f"Abriendo {path.name}", timeout=2)
        except Exception as e:
            self.notify(f"No se pudo abrir: {e}", severity="error")


def run() -> None:
    """Entry point usado por main.py."""
    ToolboxApp().run()
