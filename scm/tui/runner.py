"""Ejecución de herramientas como subprocess con terminal suspendida.

La TUI cede la terminal completa al proceso hijo (prompts, spinners,
submenús interactivos de los tools.py funcionan idéntico a hoy) y la
recupera al terminar — mismo patrón que k9s usa para `kubectl exec`.
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import registry

SCM_DIR = Path(__file__).resolve().parent.parent


@dataclass
class RunResult:
    platform: str
    tool_key: str
    tool_name: str
    returncode: int
    elapsed: float


def _env_for_platform(platform_key: str) -> dict:
    """Reusa prepare_env_for_platform de scm/main.py si está disponible."""
    meta = registry.PLATFORMS[platform_key]
    env = os.environ.copy()
    try:
        _main = sys.modules.get("__main__")
        prep = getattr(_main, "prepare_env_for_platform", None)
        if prep is None:
            import main  # scm/main.py (scm/ ya está en sys.path)
            prep = main.prepare_env_for_platform
        env = prep(meta["main_key"])
    except Exception:
        pass

    # PYTHONPATH=scm/ para los imports bare (utils, base_launcher,
    # search_module) dentro de los tools.py — mismo criterio que
    # launch_platform() de main.py.
    pp = env.get("PYTHONPATH", "")
    parts = [str(SCM_DIR)] + [p for p in pp.split(os.pathsep)
                              if p and p != str(SCM_DIR)]
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def run_tool(platform_key: str, tool_key: str,
             tool_name: str = "") -> RunResult:
    """Lanza ``<plat>/tools.py --run <key>`` como subprocess.

    Debe invocarse dentro de ``app.suspend()`` para que el hijo tenga
    la terminal completa.
    """
    meta = registry.PLATFORMS[platform_key]
    tools_py = SCM_DIR / meta["path"]
    env = _env_for_platform(platform_key)
    cmd = [sys.executable, str(tools_py), "--run", tool_key]

    start = time.monotonic()
    rc = subprocess.run(cmd, env=env, cwd=str(SCM_DIR)).returncode
    return RunResult(platform=platform_key, tool_key=tool_key,
                     tool_name=tool_name or tool_key,
                     returncode=rc, elapsed=time.monotonic() - start)


def run_platform_menu(platform_key: str) -> int:
    """Fallback: lanza el tools.py completo (menú clásico) si el
    registry no pudo cargar el dict de herramientas."""
    meta = registry.PLATFORMS[platform_key]
    env = _env_for_platform(platform_key)
    return subprocess.run(
        [sys.executable, str(SCM_DIR / meta["path"])],
        env=env, cwd=str(SCM_DIR)).returncode
