"""Registry perezoso de plataformas y herramientas para la TUI.

Lee los dicts TOOLS/SCRIPTS y TOOL_GROUPS/GROUP_ORDER de cada
``<plat>/tools.py`` sin ejecutarlos (los módulos son importables gracias
a su guard ``if __name__ == "__main__"``).
"""

import importlib
import sys
from pathlib import Path
from typing import Dict, List, Optional

SCM_DIR = Path(__file__).resolve().parent.parent  # scm/

# Clave de plataforma → metadata. ``main_key`` es la clave numérica que
# usa scm/main.py (PLATFORMS / prepare_env_for_platform).
PLATFORMS: Dict[str, dict] = {
    "gcp": {
        "main_key": "1", "module": "gcp.tools", "tools_attr": "TOOLS",
        "runner": "run_tool", "label": "Google Cloud Platform",
        "emoji": "☁️", "path": "gcp/tools.py",
        "aliases": ("gcp", "google"),
    },
    "azure": {
        "main_key": "2", "module": "azure.tools", "tools_attr": "TOOLS",
        "runner": "run_tool", "label": "Azure Cloud Platform",
        "emoji": "☁️", "path": "azure/tools.py",
        "aliases": ("azure", "az"),
    },
    "aws": {
        "main_key": "3", "module": "aws.tools", "tools_attr": "TOOLS",
        "runner": "run_tool", "label": "Amazon Web Services",
        "emoji": "🟨", "path": "aws/tools.py",
        "aliases": ("aws", "amazon"),
    },
    "azdo": {
        "main_key": "4", "module": "azdo.tools", "tools_attr": "TOOLS",
        "runner": "run_tool", "label": "Azure DevOps",
        "emoji": "🔷", "path": "azdo/tools.py",
        "aliases": ("azdo", "azuredevops", "ado"),
    },
    "terminal": {
        "main_key": "5", "module": "terminal.tools",
        "tools_attr": "SCRIPTS", "runner": "run_script",
        "label": "Terminal Scripts", "emoji": "🐧", "path": "terminal/tools.py",
        "aliases": ("terminal", "term", "sh", "shell"),
    },
    "kpi": {
        "main_key": "6", "module": "kpi_analyzer.tools",
        "tools_attr": "TOOLS", "runner": "run_tool",
        "label": "KPI Analyzer", "emoji": "📊", "path": "kpi_analyzer/tools.py",
        "aliases": ("kpi", "kpis", "analyzer"),
    },
}

_MODULES: Dict[str, object] = {}


def _ensure_scm_on_path() -> None:
    """Garantiza que scm/ está en sys.path para imports bare
    (``from search_module import ...`` dentro de los tools.py)."""
    s = str(SCM_DIR)
    if s not in sys.path:
        sys.path.insert(0, s)


def resolve_platform(alias: str) -> Optional[str]:
    """Resuelve un alias (`:azdo`, `:google`...) a la clave de plataforma."""
    a = alias.strip().lower().lstrip(":")
    for key, meta in PLATFORMS.items():
        if a == key or a in meta["aliases"]:
            return key
    # También permite la clave numérica del menú clásico (:4 → azdo)
    for key, meta in PLATFORMS.items():
        if a == meta["main_key"]:
            return key
    return None


def platform_module(platform_key: str):
    """Importa perezosamente el tools.py de la plataforma."""
    meta = PLATFORMS[platform_key]
    if platform_key in _MODULES:
        return _MODULES[platform_key]
    _ensure_scm_on_path()
    mod = importlib.import_module(meta["module"])
    _MODULES[platform_key] = mod
    return mod


def reload_platform(platform_key: str) -> None:
    """Reimporta el módulo de la plataforma (tras `r` reload)."""
    meta = PLATFORMS[platform_key]
    _ensure_scm_on_path()
    mod = importlib.import_module(meta["module"])
    _MODULES[platform_key] = importlib.reload(mod)


def _menu_sort_key(key: str):
    """Orden numérico para claves '1','1b','15','A'..."""
    head = key.rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    tail = key[len(head):]
    if head.isdigit():
        return (0, int(head), tail)
    return (1, key, "")


def platform_tools(platform_key: str) -> List[dict]:
    """Filas normalizadas de la tabla de herramientas.

    Returns:
        Lista de dicts: key, name, description, group, group_label, status.
    """
    meta = PLATFORMS[platform_key]
    mod = platform_module(platform_key)
    tools: Dict = getattr(mod, meta["tools_attr"], {}) or {}
    groups: Dict = getattr(mod, "TOOL_GROUPS", {}) or {}
    group_order: List = getattr(mod, "GROUP_ORDER", list(groups) or ["system"])

    rows: List[dict] = []
    for g in group_order:
        keys = [k for k, t in tools.items()
                if t.get("group", "system") == g and not k.startswith("_")]
        keys.sort(key=_menu_sort_key)
        for k in keys:
            t = tools[k]
            ginfo = groups.get(g, {})
            rows.append({
                "key": k,
                "name": t.get("name", k),
                "description": t.get("description", ""),
                "group": g,
                "group_label": f"{ginfo.get('emoji', '')} {ginfo.get('name', g)}".strip(),
                "status": t.get("status", "ready"),
            })
    # Herramientas sin grupo o grupos no listados en GROUP_ORDER
    listed = {r["key"] for r in rows}
    rest = [k for k in tools if k not in listed and not k.startswith("_")]
    rest.sort(key=_menu_sort_key)
    for k in rest:
        t = tools[k]
        g = t.get("group", "system")
        ginfo = groups.get(g, {})
        rows.append({
            "key": k,
            "name": t.get("name", k),
            "description": t.get("description", ""),
            "group": g,
            "group_label": f"{ginfo.get('emoji', '')} {ginfo.get('name', g)}".strip(),
            "status": t.get("status", "ready"),
        })
    return rows


def outcome_dir() -> Path:
    """Resuelve el outcome dir (config.json global.output_dir → scm/outcome)."""
    import json
    cfg_file = SCM_DIR / "config.json"
    try:
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        out = cfg.get("global", {}).get("output_dir", "outcome")
    except Exception:
        out = "outcome"
    p = Path(out)
    return p if p.is_absolute() else SCM_DIR / p
