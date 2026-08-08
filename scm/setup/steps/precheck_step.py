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

    # (cli_name, session_cmd, label, login_cmd)
    CHECKS = [
        ("gcloud", ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"], "GCP", ["gcloud", "auth", "login"]),
        ("az", ["az", "account", "show", "--query", "name", "-o", "tsv"], "Azure", ["az", "login"]),
        ("aws", ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"], "AWS", ["aws", "configure"]),
    ]

    def run(self) -> Dict[str, Any]:
        self.show_header()
        results: Dict[str, Any] = {}

        rows = []
        for cli, session_cmd, label, login_cmd in self.CHECKS:
            installed = self._is_installed(cli)
            session, detail = self._check_session(session_cmd) if installed else (False, "N/A")

            if installed and not session:
                session, detail = self._try_auto_login(cli, label, login_cmd, session_cmd)

            results[cli] = {"installed": installed, "session": session, "detail": detail}
            rows.append((label, installed, session, detail))

        self._print_results(rows)
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

    def _try_auto_login(self, cli: str, label: str, login_cmd: List[str], session_cmd: List[str]) -> Tuple[bool, str]:
        """Pregunta al usuario si desea iniciar sesion y ejecuta el login."""
        if not self.confirm(f"{label} no autenticado. Ejecutar '{' '.join(login_cmd)}' ahora?", default=True):
            return False, "No autenticado"

        try:
            if self.console and RICH_AVAILABLE:
                self.console.print(f"[cyan]Ejecutando {' '.join(login_cmd)}...[/cyan]")
            else:
                print(f"Ejecutando {' '.join(login_cmd)}...")

            subprocess.run(login_cmd, check=False)

            session, detail = self._check_session(session_cmd)
            if session:
                if self.console and RICH_AVAILABLE:
                    self.console.print(f"[green]Autenticacion exitosa: {detail}[/green]")
                return True, detail
            else:
                return False, "Login fallido"
        except Exception as e:
            return False, f"Error: {str(e)[:40]}"

    def _print_results(self, rows: List[Tuple[str, bool, bool, str]]) -> None:
        """Imprime la tabla de resultados con Rich o texto plano."""
        if self.console and RICH_AVAILABLE:
            table = RichTable(title="Estado de CLIs", show_header=True, header_style="bold cyan")
            table.add_column("CLI")
            table.add_column("Instalado")
            table.add_column("Sesion activa")
            table.add_column("Detalle")

            for label, installed, session, detail in rows:
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
            for label, installed, session, detail in rows:
                print(f"{label:<10} {'Si' if installed else 'No':<12} {'Si' if session else 'No':<12} {detail[:40]}")
