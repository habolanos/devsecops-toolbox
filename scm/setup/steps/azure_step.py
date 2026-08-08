"""
DevSecOps Toolbox - Azure Cloud Step

Hidrata la seccion 'azure' de config.json: subscription_id, tenant_id, region.
Detecta sesion de az cli y sugiere subscription.
"""

import subprocess
from typing import Dict, Any, List

from setup.steps.base_step import WizardStep


class AzureStep(WizardStep):
    name = "AZURE"
    title = "Azure Cloud Platform"
    icon = "☁️"
    section = "azure"
    optional = True

    def run(self) -> Dict[str, Any]:
        self.show_header()
        template = dict(self.template_config.get(self.section, {}))
        precheck = self.template_config.get("_precheck", {})
        az_info = precheck.get("az", {})

        suggested_sub = ""
        suggested_tenant = ""
        if az_info.get("session"):
            suggested_sub, suggested_tenant = self._get_az_info()
            if self.console:
                self.console.print(f"[green]Sesion az cli activa: {az_info.get('detail', '')}[/green]")
        else:
            if self.console:
                self.console.print("[yellow]Azure no autenticado. Ejecuta 'az login' despues del wizard.[/yellow]")

        subscription_id = self.ask(
            "Subscription ID",
            default=suggested_sub or template.get("subscription_id", "")
        )
        tenant_id = self.ask(
            "Tenant ID",
            default=suggested_tenant or template.get("tenant_id", "")
        )
        region = self.ask(
            "Region",
            default=template.get("region", "eastus")
        )

        result = dict(template)
        result["subscription_id"] = subscription_id
        result["tenant_id"] = tenant_id
        result["region"] = region
        result["enabled"] = True

        return result

    def validate(self, values: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        sub_id = values.get("subscription_id", "")

        if not sub_id or "<TU_" in sub_id:
            errors.append("Subscription ID es requerido")

        return errors

    @staticmethod
    def _get_az_info() -> tuple:
        sub_id = ""
        tenant_id = ""
        try:
            r = subprocess.run(
                ["az", "account", "show", "--query", "id", "-o", "tsv"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                sub_id = r.stdout.strip()
            r2 = subprocess.run(
                ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
                capture_output=True, text=True, timeout=10
            )
            if r2.returncode == 0:
                tenant_id = r2.stdout.strip()
        except Exception:
            pass
        return sub_id, tenant_id
