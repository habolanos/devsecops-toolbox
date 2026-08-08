"""
DevSecOps Toolbox - Dashboard Step

Hidrata la seccion 'dashboard' de config.json: webhook_url, schedule.
"""

from typing import Dict, Any, List

from setup.steps.base_step import WizardStep


class DashboardStep(WizardStep):
    name = "DASHBOARD"
    title = "Dashboard Matutino"
    icon = "📈"
    section = "dashboard"
    optional = True

    def run(self) -> Dict[str, Any]:
        self.show_header()
        template = dict(self.template_config.get(self.section, {}))

        webhook = self.ask(
            "Teams Webhook URL (opcional, Enter para skip)",
            default=template.get("webhook_url", "")
        )

        result = dict(template)
        if webhook and "<TU_" not in webhook:
            result["webhook_url"] = webhook
        else:
            result["webhook_url"] = ""
        result["enabled"] = True

        return result

    def validate(self, values: Dict[str, Any]) -> List[str]:
        return []
