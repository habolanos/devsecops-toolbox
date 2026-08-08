"""
DevSecOps Toolbox - AWS Step

Hidrata la seccion 'aws' de config.json: profile, region, credentials.
Detecta sesion de aws cli y sugiere account/region.
"""

import subprocess
from typing import Dict, Any, List

from setup.steps.base_step import WizardStep


class AwsStep(WizardStep):
    name = "AWS"
    title = "Amazon Web Services"
    icon = "🟠"
    section = "aws"
    optional = True

    def run(self) -> Dict[str, Any]:
        self.show_header()
        template = dict(self.template_config.get(self.section, {}))
        precheck = self.template_config.get("_precheck", {})
        aws_info = precheck.get("aws", {})

        if aws_info.get("session"):
            if self.console:
                self.console.print(f"[green]Sesion aws cli activa: {aws_info.get('detail', '')}[/green]")
        else:
            if self.console:
                self.console.print("[yellow]AWS no autenticado. Ejecuta 'aws configure' despues del wizard.[/yellow]")

        profile = self.ask(
            "Profile name",
            default=template.get("profile", "default")
        )
        region = self.ask(
            "Region",
            default=template.get("region", "us-east-1")
        )

        result = dict(template)
        result["profile"] = profile
        result["region"] = region
        result["enabled"] = True

        return result

    def validate(self, values: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        profile = values.get("profile", "")

        if not profile:
            errors.append("Profile name es requerido")

        return errors
