# -*- coding: utf-8 -*-
"""Tests del bootstrap UTF-8 de stdout/stderr (fix pipe cp1252)."""
import io
import sys
import importlib


def _run_helper(module, stdout, stderr):
    """Ejecuta el helper del módulo con streams inyectados."""
    import unittest.mock as mock
    with mock.patch.object(sys, "stdout", stdout), \
         mock.patch.object(sys, "stderr", stderr):
        module._force_utf8_stdio()


def _wrapper(encoding="cp1252"):
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="strict")


def test_main_force_utf8_reconfigures_streams():
    main = importlib.import_module("main")
    out, err = _wrapper(), _wrapper()
    _run_helper(main, out, err)
    assert out.encoding == "utf-8"
    assert err.encoding == "utf-8"
    assert out.errors == "replace"


def test_force_utf8_tolerates_streams_without_reconfigure():
    main = importlib.import_module("main")
    # Objetos tipo capture de pytest: sin reconfigure() → no-op seguro
    _run_helper(main, object(), object())
    # Idempotente: segunda ejecución sobre streams ya UTF-8 no falla
    out, err = _wrapper("utf-8"), _wrapper("utf-8")
    _run_helper(main, out, err)
    assert out.encoding == "utf-8"


def test_all_launchers_expose_helper():
    """Los 6 tools.py y main.py deben tener el bootstrap UTF-8."""
    for name in ("main", "gcp.tools", "azure.tools", "aws.tools",
                 "azdo.tools", "terminal.tools", "kpi_analyzer.tools"):
        mod = importlib.import_module(name)
        assert callable(getattr(mod, "_force_utf8_stdio", None)), name


def test_wrapper_writes_emoji_after_fix():
    """Tras reconfigurar, escribir emojis en un stream cp1252→utf-8 funciona."""
    main = importlib.import_module("main")
    out = _wrapper("cp1252")
    _run_helper(main, out, out)
    out.write("🛠️ reporte listo ✓")
    out.flush()
