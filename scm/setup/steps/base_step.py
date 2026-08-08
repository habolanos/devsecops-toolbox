"""
DevSecOps Toolbox - WizardStep base class

Clase abstracta para pasos del wizard de configuracion.
Cada plataforma implementa su propio paso heredando de WizardStep.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class WizardStep(ABC):
    """Clase base para un paso del wizard de configuracion.

    Atributos de clase (override en subclases):
        name: Nombre corto (ej: "AZDO")
        title: Titulo display (ej: "Azure DevOps")
        icon: Emoji representativo
        section: Key en config.json (ej: "azdo")
        optional: Si es True, se puede skip con confirmacion
    """

    name: str = ""
    title: str = ""
    icon: str = ""
    section: str = ""
    optional: bool = False

    def __init__(self, console: Optional[Any], template_config: Dict[str, Any]):
        self.console = console
        self.template_config = template_config
        self.values: Dict[str, Any] = {}

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """Ejecuta el paso y retorna los valores hidratados para su seccion.

        Returns:
            Dict[str, Any]: Valores para la seccion de config.json.
        """
        pass

    @abstractmethod
    def validate(self, values: Dict[str, Any]) -> List[str]:
        """Valida los valores ingresados.

        Args:
            values: Diccionario con los valores a validar.

        Returns:
            List[str]: Lista de errores (vacia = validacion OK).
        """
        pass

    def show_header(self):
        """Muestra el encabezado del paso."""
        if self.console and RICH_AVAILABLE:
            self.console.print(Panel(
                f"{self.icon}  {self.title}",
                border_style="cyan",
                expand=False
            ))
        else:
            print(f"\n{'='*50}")
            print(f"  {self.icon}  {self.title}")
            print(f"{'='*50}")

    def ask(self, prompt: str, default: str = "", password: bool = False) -> str:
        """Wrapper de Prompt.ask con default y validacion basica."""
        if self.console and RICH_AVAILABLE:
            return Prompt.ask(
                prompt,
                default=default if default else None,
                password=password,
                console=self.console
            )
        else:
            label = f"{prompt}"
            if default:
                label += f" [{default}]"
            label += ": "
            val = input(label)
            return val if val else default

    def confirm(self, prompt: str, default: bool = True) -> bool:
        """Wrapper de Confirm.ask."""
        if self.console and RICH_AVAILABLE:
            return Confirm.ask(prompt, default=default, console=self.console)
        else:
            hint = "Y/n" if default else "y/N"
            val = input(f"{prompt} ({hint}): ").strip().lower()
            if not val:
                return default
            return val in ("y", "yes", "s", "si")

    def ask_skip(self) -> bool:
        """Si el paso es opcional, pregunta si se desea skip.

        Returns:
            bool: True si el usuario quiere skip este paso.
        """
        if not self.optional:
            return False
        return not self.confirm(f"Configurar {self.title}?", default=False)

    def run_with_validation(self) -> Dict[str, Any]:
        """Ejecuta el paso con validacion y re-intento automatico.

        Returns:
            Dict[str, Any]: Valores validados.
        """
        while True:
            values = self.run()
            errors = self.validate(values)
            if not errors:
                return values
            for err in errors:
                if self.console and RICH_AVAILABLE:
                    self.console.print(f"[red]Error: {err}[/red]")
                else:
                    print(f"ERROR: {err}")
            if not self.confirm("Reintentar?", default=True):
                return values
