"""
DevSecOps Toolbox - GCP Step

Hidrata la seccion 'gcp' de config.json: project_id, region, credentials.
Detecta sesion de gcloud y sugiere project_id actual.
"""

import subprocess
from typing import Dict, Any, List

from setup.steps.base_step import WizardStep


class GcpStep(WizardStep):
    name = "GCP"
    title = "Google Cloud Platform"
    icon = "☁️"
    section = "gcp"
    optional = False

    def run(self) -> Dict[str, Any]:
        self.show_header()
        template = dict(self.template_config.get(self.section, {}))
        precheck = self.template_config.get("_precheck", {})
        gcloud_info = precheck.get("gcloud", {})

        suggested_project = ""
        if gcloud_info.get("session"):
            suggested_project = self._get_gcloud_project()
            if self.console:
                self.console.print(f"[green]Sesion gcloud activa: {gcloud_info.get('detail', '')}[/green]")
        else:
            if self.console:
                self.console.print("[yellow]GCP no autenticado. Ejecuta 'gcloud auth login' despues del wizard.[/yellow]")

        project_id = self.ask(
            "Project ID",
            default=suggested_project or template.get("project_id", "")
        )
        region = self.ask(
            "Region",
            default=template.get("region", "us-central1")
        )

        result = dict(template)
        result["project_id"] = project_id
        result["region"] = region
        result["enabled"] = True

        return result

    def validate(self, values: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        project_id = values.get("project_id", "")

        if not project_id or "<TU_" in project_id:
            errors.append("Project ID es requerido")

        return errors

    @staticmethod
    def _get_gcloud_project() -> str:
        try:
            r = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
        return ""
