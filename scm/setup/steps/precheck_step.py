"""
DevSecOps Toolbox - Precheck Step

Detecta CLIs instalados y sesiones activas antes de pedir credenciales.
No hidrata ninguna seccion de config.json; sus resultados se pasan
a los pasos siguientes via template_config["_precheck"].
"""

import subprocess
import shutil
from typing import Dict, Any, List, Tuple

from setup.steps.base_step import WizardStep

try:
    from rich.table import Table as RichTable
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class PrecheckStep(WizardStep):
    name = "PRECHECK"
    title = "Deteccion de CLIs y Sesiones"
    icon = "🔍"
    section = "_precheck"
    optional = False

    # (cli_name, version_cmd, session_cmd, label)
    CHECKS = [
        ("gcloud", ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"], "GCP"),
        ("az", ["az", "account", "show", "--query", "name", "-o", "tsv"], "Azure"),
        ("aws", ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"], "AWS"),
    ]

    def run(self) -> Dict[str, Any]:
        self.show_header()
        results: Dict[str, Any] = {}

        if self.console and RICH_AVAILABLE:
            table = RichTable(title="Estado de CLIs", show_header=True, header_style="bold cyan")
            table.add_column("CLI")
            table.add_column("Instalado")
            table.add_column("Sesion activa")
            table.add_column("Detalle")

            for cli, session_cmd, label in self.CHECKS:
                installed = self._is_installed(cli)
                session, detail = self._check_session(session_cmd) if installed else (False, "N/A")
                results[cli] = {"installed": installed, "session": session, "detail": detail}
                table.add_row(
                    label,
                    "[green]Si[/green]" if installed else "[red]No[/red]",
                    "[green]Si[/green]" if session else "[yellow]No[/yellow]",
                    detail[:60]
                )

            self.console.print(table)
        else:
            print(f"{'CLI':<10} {'Instalado':<12} {'Sesion':<12} {'Detalle'}")
            print("-" * 60)
            for cli, session_cmd, label in self.CHECKS:
                installed = self._is_installed(cli)
                session, detail = self._check_session(session_cmd) if installed else (False, "N/A")
                results[cli] = {"installed": installed, "session": session, "detail": detail}
                print(f"{label:<10} {'Si' if installed else 'No':<12} {'Si' if session else 'No':<12} {detail[:40]}")

        return results

    def validate(self, values: Dict[str, Any]) -> List[str]:
        return []

    def _is_installed(self, cli: str) -> bool:
        try:
            return shutil.which(cli) is not None
        except Exception:
            return False

    def _check_session(self, cmd: List[str]) -> Tuple[bool, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and r.stdout.strip():
                return True, r.stdout.strip()
            return False, "No autenticado"
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except FileNotFoundError:
            return False, "CLI no encontrado"
        except Exception as e:
            return False, str(e)[:50]
