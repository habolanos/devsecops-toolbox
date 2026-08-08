"""
DevSecOps Toolbox - AZDO Step

Hidrata la seccion 'azdo' de config.json: organization, project, pat.
"""

import re
from typing import Dict, Any, List

from setup.steps.base_step import WizardStep


class AzdoStep(WizardStep):
    name = "AZDO"
    title = "Azure DevOps"
    icon = "🔷"
    section = "azdo"
    optional = False

    def run(self) -> Dict[str, Any]:
        self.show_header()
        template = dict(self.template_config.get(self.section, {}))

        org_url = self.ask(
            "Organization URL (https://dev.azure.com/<org>)",
            default=template.get("organization_url", "")
        )
        project = self.ask(
            "Project name",
            default=template.get("project", "")
        )
        pat = self.ask(
            "PAT token",
            password=True
        )

        org_name = self._extract_org_name(org_url)

        result = dict(template)
        result["organization_url"] = org_url
        result["organization"] = org_name
        result["project"] = project
        result["pat"] = pat
        result["enabled"] = True

        return result

    def validate(self, values: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        pat = values.get("pat", "")
        org_url = values.get("organization_url", "")
        project = values.get("project", "")

        if not pat or "<TU_" in pat:
            errors.append("PAT token es requerido")
        if not org_url or "<TU_" in org_url:
            errors.append("Organization URL es requerida")
        if not project or "<TU_" in project:
            errors.append("Project name es requerido")
        if org_url and not org_url.startswith("https://dev.azure.com/"):
            errors.append("Organization URL debe empezar con https://dev.azure.com/")

        return errors

    @staticmethod
    def _extract_org_name(org_url: str) -> str:
        if not org_url:
            return ""
        url = org_url.rstrip("/")
        return url.split("/")[-1] if "/" in url else org_url
