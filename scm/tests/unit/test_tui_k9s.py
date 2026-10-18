"""Tests de la TUI estilo k9s (scm/tui/).

Cubre: registry (aliases/flatten), parser de comandos `:`, `--run` en
tools.py, y navegación headless con run_test().
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCM_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCM_DIR))

from scm.tui import commands, registry           # noqa: E402
from scm.tui.commands import parse_command       # noqa: E402


# ─────────────────────────────── registry ─────────────────────────────

class TestResolvePlatform:
    def test_alias_corto(self):
        assert registry.resolve_platform("azdo") == "azdo"
        assert registry.resolve_platform("ado") == "azdo"
        assert registry.resolve_platform("gcp") == "gcp"
        assert registry.resolve_platform("term") == "terminal"
        assert registry.resolve_platform("kpi") == "kpi"

    def test_con_dos_puntos(self):
        assert registry.resolve_platform(":aws") == "aws"

    def test_main_key_numerica(self):
        assert registry.resolve_platform("4") == "azdo"
        assert registry.resolve_platform("1") == "gcp"

    def test_desconocido(self):
        assert registry.resolve_platform("nope") is None


class TestPlatformTools:
    def test_azdo_carga_herramientas(self):
        rows = registry.platform_tools("azdo")
        assert len(rows) > 30
        keys = {r["key"] for r in rows}
        assert "15" in keys and "44" in keys

    def test_terminal_usa_scripts(self):
        rows = registry.platform_tools("terminal")
        assert len(rows) >= 6

    def test_orden_numerico_por_grupo(self):
        rows = registry.platform_tools("azdo")
        # el orden es por grupo y dentro del grupo numérico
        por_grupo = {}
        for r in rows:
            if r["key"].isdigit():
                por_grupo.setdefault(r["group"], []).append(int(r["key"]))
        for g, keys in por_grupo.items():
            assert keys == sorted(keys), f"grupo {g} desordenado"

    def test_outcome_dir_default(self):
        out = registry.outcome_dir()
        assert out.name == "outcome" or "outcome" in str(out)


# ─────────────────────────────── commands ─────────────────────────────

class TestParseCommand:
    def test_plataforma(self):
        assert parse_command("azdo").action == "platform"
        assert parse_command(":gcp").arg == "gcp"

    def test_tool_en_contexto(self):
        c = parse_command("15", context_platform="azdo")
        assert c.action == "tool" and c.arg == "15"

    def test_numero_sin_contexto_es_unknown(self):
        assert parse_command("15").action == "unknown"

    def test_sistema(self):
        assert parse_command("q").action == "quit"
        assert parse_command("outcome").action == "outcome"
        assert parse_command("back").action == "back"
        assert parse_command("reload").action == "reload"
        assert parse_command("help").action == "help"

    def test_all(self):
        c = parse_command("all", context_platform="azdo")
        assert c.action == "all" and c.arg == "azdo"

    def test_vacio_y_desconocido(self):
        assert parse_command("").action == "unknown"
        assert parse_command("zzz nope").action == "unknown"


# ──────────────────────── tools.py --run flag ─────────────────────────

class TestRunFlag:
    """Cada launcher debe invocar su runner sin entrar al menú."""

    def _call_main(self, module, argv_key, runner_name="run_tool",
                   tools_attr="TOOLS"):
        mod = __import__(module, fromlist=["x"])
        fake = MagicMock()
        with patch.object(mod, runner_name, fake), \
             patch.object(sys, "argv", ["tools.py", "--run", argv_key]), \
             patch.object(mod, "print_header", lambda *a, **k: None,
                          create=True):
            mod.main()
        return fake

    def test_azdo_run_normaliza_clave(self):
        fake = self._call_main("scm.azdo.tools", "15")
        fake.assert_called_once_with("15")

    def test_azdo_run_clave_alfa_lower(self):
        """'a' minúscula se normaliza a 'A' (isalpha → upper)."""
        fake = self._call_main("scm.azdo.tools", "q")
        fake.assert_called_once_with("Q")

    def test_gcp_run(self):
        fake = self._call_main("scm.gcp.tools", "1")
        fake.assert_called_once_with("1")

    def test_terminal_run_script(self):
        fake = self._call_main("scm.terminal.tools", "1",
                               runner_name="run_script")
        fake.assert_called_once_with("1")

    def test_clave_invalida_sale_2(self):
        mod = __import__("scm.terminal.tools", fromlist=["x"])
        with patch.object(sys, "argv", ["tools.py", "--run", "99"]), \
             pytest.raises(SystemExit) as e:
            mod.main()
        assert e.value.code == 2


# ─────────────────────────── screens (headless) ───────────────────────

textual = pytest.importorskip("textual")


class TestScreens:
    def test_arranque_en_plataformas(self):
        asyncio.run(self._t_arranque())

    async def _t_arranque(self):
        from scm.tui.app import ToolboxApp
        from scm.tui.screens import PlatformsScreen
        app = ToolboxApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, PlatformsScreen)

    def test_entrar_a_azdo_carga_tools(self):
        asyncio.run(self._t_entrar())

    async def _t_entrar(self):
        from scm.tui.app import ToolboxApp
        from scm.tui.screens import ToolsScreen
        app = ToolboxApp()
        async with app.run_test() as pilot:
            app.push_tools_screen("azdo")
            await pilot.pause()
            assert isinstance(app.screen, ToolsScreen)
            assert app.screen.query_one(
                "ToolsTable").row_count > 30

    def test_filtro_en_vivo(self):
        asyncio.run(self._t_filtro())

    async def _t_filtro(self):
        from scm.tui.app import ToolboxApp
        app = ToolboxApp()
        async with app.run_test() as pilot:
            app.push_tools_screen("azdo")
            await pilot.pause()
            table = app.screen.query_one("ToolsTable")
            total = table.row_count
            table.set_filter("health")
            assert 0 < table.row_count < total

    def test_enter_lanza_tool(self):
        asyncio.run(self._t_enter())

    async def _t_enter(self):
        from scm.tui.app import ToolboxApp
        app = ToolboxApp()
        launched = []
        app.launch_tool = lambda p, k: launched.append((p, k))
        async with app.run_test() as pilot:
            app.push_tools_screen("azdo")
            await pilot.pause()
            table = app.screen.query_one("ToolsTable")
            table.move_cursor(row=0)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert launched and launched[0][0] == "azdo"

    def test_esc_vuelve_a_plataformas(self):
        asyncio.run(self._t_esc())

    async def _t_esc(self):
        from scm.tui.app import ToolboxApp
        from scm.tui.screens import PlatformsScreen, ToolsScreen
        app = ToolboxApp()
        async with app.run_test() as pilot:
            app.push_tools_screen("azdo")
            await pilot.pause()
            assert isinstance(app.screen, ToolsScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, PlatformsScreen)

    def test_dispatch_comando_plataforma(self):
        asyncio.run(self._t_dispatch())

    async def _t_dispatch(self):
        from scm.tui.app import ToolboxApp
        from scm.tui.screens import ToolsScreen
        app = ToolboxApp()
        async with app.run_test() as pilot:
            app.dispatch_command(parse_command(":aws"))
            await pilot.pause()
            assert isinstance(app.screen, ToolsScreen)
            assert app.screen.platform_key == "aws"
