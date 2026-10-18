"""Parser de comandos `:` estilo k9s para la TUI.

Comandos soportados:
    :<plataforma>   → salta a ToolsScreen de la plataforma (:azdo, :gcp...)
    :<N>            → ejecuta la tool con esa clave en el contexto actual
    :all / :allj    → opciones de sistema A (ejecutar todo) / B (todo + JSON)
    :outcome        → abre el navegador de reportes en outcome/
    :back           → vuelve a la pantalla anterior
    :reload         → recarga config.json y registry
    :help           → ayuda (igual que ?)
    :q / :quit      → salir
"""

from dataclasses import dataclass
from typing import Optional

from . import registry


@dataclass
class Command:
    action: str           # platform | tool | all | allj | outcome | back |
                          # reload | help | quit | unknown
    arg: Optional[str] = None
    raw: str = ""


def parse_command(text: str, context_platform: Optional[str] = None) -> Command:
    """Interpreta el texto del command bar (sin el ':' inicial)."""
    raw = text
    text = text.strip().lower().lstrip(":")

    if not text:
        return Command("unknown", raw=raw)

    if text in ("q", "quit", "exit", "salir"):
        return Command("quit", raw=raw)
    if text in ("back", "b", ".."):
        return Command("back", raw=raw)
    if text in ("help", "h", "?", "ayuda"):
        return Command("help", raw=raw)
    if text in ("reload", "refresh", "r"):
        return Command("reload", raw=raw)
    if text in ("outcome", "out", "reports", "o"):
        return Command("outcome", raw=raw)
    if text in ("all", "a"):
        return Command("all", arg=context_platform, raw=raw)
    if text in ("allj", "alljson", "b"):
        return Command("allj", arg=context_platform, raw=raw)

    plat = registry.resolve_platform(text)
    if plat:
        return Command("platform", arg=plat, raw=raw)

    # :<key> ejecuta una tool dentro del contexto actual
    if context_platform:
        return Command("tool", arg=text, raw=raw)

    return Command("unknown", raw=raw)
