"""
DevSecOps Toolbox - Global Step

Hidrata la seccion 'global' de config.json: output_dir, proxy, debug.
"""

from typing import Dict, Any, List

from setup.steps.base_step import WizardStep


class GlobalStep(WizardStep):
    name = "GLOBAL"
    title = "Configuracion Global"
    icon = "⚙️"
    section = "global"
    optional = False

    def run(self) -> Dict[str, Any]:
        self.show_header()
        template = dict(self.template_config.get(self.section, {}))

        output_dir = self.ask(
            "Directorio de salida",
            default=template.get("output_dir", "outcome")
        )
        debug = self.confirm("Habilitar debug?", default=False)
        verbose = self.confirm("Habilitar verbose?", default=False)

        result = dict(template)
        result["output_dir"] = output_dir
        result["debug"] = debug
        result["verbose"] = verbose
        result["log_level"] = "DEBUG" if debug else "INFO"

        return result

    def validate(self, values: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        if not values.get("output_dir"):
            errors.append("Directorio de salida es requerido")
        return errors
