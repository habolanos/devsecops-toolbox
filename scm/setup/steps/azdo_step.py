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

        existing_org = template.get("organization", "")
        if existing_org and "<TU_" not in existing_org:
            default_org = existing_org
        else:
            default_org = ""

        org_input = self.ask(
            "Organization name (ej: Coppel-Retail)",
            default=default_org
        )
        project = self.ask(
            "Project name",
            default=template.get("project", "")
        )
        pat = self.ask(
            "PAT token",
            password=True
        )

        org_name = self._normalize_org_name(org_input)
        org_url = f"https://dev.azure.com/{org_name}"

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
            errors.append("Organization es requerida")
        if not project or "<TU_" in project:
            errors.append("Project name es requerido")

        return errors

    @staticmethod
    def _normalize_org_name(org_input: str) -> str:
        """Normaliza el input del usuario a un organization name.

        Acepta:
        - 'Coppel-Retail' -> 'Coppel-Retail'
        - 'https://dev.azure.com/Coppel-Retail' -> 'Coppel-Retail'
        - 'https://dev.azure.com/Coppel-Retail/' -> 'Coppel-Retail'
        """
        if not org_input:
            return ""
        val = org_input.strip().rstrip("/")
        if val.startswith("https://dev.azure.com/"):
            val = val[len("https://dev.azure.com/"):]
        elif val.startswith("https://"):
            val = val.split("/")[-1]
        return val.strip()
