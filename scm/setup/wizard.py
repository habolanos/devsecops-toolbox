"""
DevSecOps Toolbox - Setup Wizard Orchestrator

Orquesta el wizard de configuracion inicial.
Detecta si config.json falta o esta incompleto, copia el template,
ejecuta los pasos secuencialmente y guarda el config hidratado.
"""

import json
import copy
from pathlib import Path
from typing import Dict, Any, List, Optional, Type

from setup.steps.base_step import WizardStep
from setup.steps.precheck_step import PrecheckStep
from setup.steps.azdo_step import AzdoStep
from setup.steps.gcp_step import GcpStep
from setup.steps.azure_step import AzureStep
from setup.steps.aws_step import AwsStep
from setup.steps.dashboard_step import DashboardStep
from setup.steps.global_step import GlobalStep
from setup.validators.config_validator import ConfigValidator

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich.box import DOUBLE_EDGE
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class SetupWizard:
    """Orquestador del wizard de configuracion inicial.

    Usage:
        wizard = SetupWizard(config_path, template_path)
        if wizard.should_run():
            wizard.run()
    """

    # Registry de pasos. Escalar: agregar nuevas clases aqui.
    STEP_CLASSES: List[Type[WizardStep]] = [
        PrecheckStep,
        AzdoStep,
        GcpStep,
        AzureStep,
        AwsStep,
        DashboardStep,
        GlobalStep,
    ]

    # Keys de metadata a remover del template antes de guardar
    META_KEYS_TO_REMOVE = ["_info", "_version", "_enabled_info", "_mode_info",
                           "_output_format_info", "_projects_info", "_webhook_info",
                           "_dangerous_roles_info", "_alert_on_risk_level_info",
                           "_maturity_model_info", "_cron_info", "_webhook_url_info",
                           "_output_dir_info", "_credentials_info"]

    def __init__(
        self,
        config_path: Path,
        template_path: Path,
        console: Optional[Any] = None
    ):
        self.config_path = config_path
        self.template_path = template_path
        self.console = console or (Console() if RICH_AVAILABLE else None)
        self.template = self._load_template()

    def _load_template(self) -> Dict[str, Any]:
        """Carga el template JSON. Retorna dict vacio si no existe."""
        if not self.template_path.exists():
            return {}
        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {}

    def should_run(self) -> bool:
        """True si config.json no existe o contiene placeholders sin hidratar.

        Returns:
            bool: True si el wizard debe ejecutarse.
        """
        if not self.config_path.exists():
            return True

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return ConfigValidator.has_placeholders(config)
        except (json.JSONDecodeError, Exception):
            return True

    def run(self) -> bool:
        """Ejecuta el wizard completo.

        Returns:
            bool: True si config.json fue guardado exitosamente.
        """
        self._show_welcome()

        config = copy.deepcopy(self.template)
        precheck_results: Dict[str, Any] = {}

        for step_cls in self.STEP_CLASSES:
            step = step_cls(self.console, self.template)

            if step.optional and step.ask_skip():
                if self.console and RICH_AVAILABLE:
                    self.console.print(f"[dim]Skip: {step.title}[/dim]")
                else:
                    print(f"Skip: {step.title}")
                continue

            values = step.run_with_validation()

            if step.section == "_precheck":
                precheck_results = values
                self.template["_precheck"] = values
            else:
                config[step.section] = values

        config.pop("_precheck", None)
        self._clean_metadata(config)

        errors = ConfigValidator.validate(config)
        if errors:
            self._show_errors(errors)
            if self._confirm_save_anyway():
                self._save_config(config)
                self._show_summary(config)
                return True
            return False

        self._save_config(config)
        self._show_summary(config)
        return True

    def run_section(self, section: str) -> bool:
        """Re-ejecuta solo una seccion del wizard.

        Args:
            section: Nombre de la seccion (ej: "azdo", "gcp").

        Returns:
            bool: True si la seccion fue actualizada.
        """
        config = self._load_existing_config()
        if config is None:
            config = copy.deepcopy(self.template)

        for step_cls in self.STEP_CLASSES:
            if step_cls.section == section:
                step = step_cls(self.console, self.template)
                values = step.run_with_validation()
                config[section] = values
                break

        self._save_config(config)
        return True

    def _load_existing_config(self) -> Optional[Dict[str, Any]]:
        if not self.config_path.exists():
            return None
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _clean_metadata(self, config: Dict[str, Any]) -> None:
        """Remueve keys de metadata (_info, _version, etc.) recursivamente."""
        if isinstance(config, dict):
            for key in list(config.keys()):
                if key in self.META_KEYS_TO_REMOVE or key.startswith("_"):
                    del config[key]
                else:
                    self._clean_metadata(config[key])
        elif isinstance(config, list):
            for item in config:
                self._clean_metadata(item)

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Guarda config.json con indentacion legible."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _show_welcome(self) -> None:
        if self.console and RICH_AVAILABLE:
            title = Text()
            title.append("🔧  Setup Wizard", style="bold cyan")
            title.append("  -  DevSecOps Toolbox", style="dim")

            self.console.print(Align.center(
                Panel(
                    Text.assemble(
                        title,
                        "\n",
                        Text("Configuracion inicial interactiva", style="dim white"),
                        "\n",
                        Text("Se te pediran los datos de cada plataforma.", style="dim"),
                        "\n",
                        Text("Los pasos marcados como opcionales se pueden skip.", style="dim"),
                    ),
                    box=DOUBLE_EDGE,
                    border_style="cyan",
                    padding=(1, 2),
                    expand=False,
                )
            ))
            self.console.print()
        else:
            print("\n" + "=" * 60)
            print("  Setup Wizard - DevSecOps Toolbox")
            print("=" * 60)
            print("  Configuracion inicial interactiva.\n")

    def _show_errors(self, errors: List[str]) -> None:
        if self.console and RICH_AVAILABLE:
            self.console.print(Panel(
                "\n".join(f"[red]• {e}[/red]" for e in errors),
                title="[red]Errores de validacion[/red]",
                border_style="red",
                expand=False
            ))
        else:
            print("\nERRORES DE VALIDACION:")
            for e in errors:
                print(f"  - {e}")

    def _confirm_save_anyway(self) -> bool:
        if self.console and RICH_AVAILABLE:
            from rich.prompt import Confirm
            return Confirm.ask(
                "Guardar config con errores?",
                default=False,
                console=self.console
            )
        else:
            val = input("Guardar config con errores? (y/N): ").strip().lower()
            return val in ("y", "yes", "s", "si")

    def _show_summary(self, config: Dict[str, Any]) -> None:
        if self.console and RICH_AVAILABLE:
            lines = []
            for section in ["azdo", "gcp", "azure", "aws", "dashboard", "global"]:
                data = config.get(section, {})
                if isinstance(data, dict) and data.get("enabled"):
                    lines.append(f"[green]✅ {section.upper()}[/green]")
                elif isinstance(data, dict) and not data.get("enabled", True):
                    lines.append(f"[dim]⬚ {section.upper()} (deshabilitado)[/dim]")
                else:
                    lines.append(f"[yellow]⚠️  {section.upper()} (no configurado)[/yellow]")

            self.console.print(Panel(
                "\n".join(lines),
                title="[green]Configuracion guardada[/green]",
                border_style="green",
                expand=False
            ))
            self.console.print(f"\n[green]Config guardado en: {self.config_path}[/green]")
        else:
            print(f"\nConfig guardado en: {self.config_path}")
