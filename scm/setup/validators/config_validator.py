"""
DevSecOps Toolbox - Config Validator

Valida la configuracion final antes de guardar config.json.
Verifica que no queden placeholders sin hidratar y que las
secciones requeridas tengan los campos minimos.
"""

import re
from typing import Dict, Any, List


class ConfigValidator:
    """Valida la estructura y contenido de config.json antes de guardar."""

    PLACEHOLDER_PATTERN = re.compile(r"<TU_[^>]*>")

    REQUIRED_SECTIONS = ["azdo", "gcp", "global"]

    SECTION_REQUIRED_FIELDS = {
        "azdo": ["organization_url", "project", "pat"],
        "gcp": ["project_id"],
        "global": ["output_dir"],
    }

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> List[str]:
        """Valida el config completo.

        Args:
            config: Diccionario con la configuracion completa.

        Returns:
            List[str]: Lista de errores (vacia = config valido).
        """
        errors: List[str] = []

        errors.extend(cls._check_placeholders(config))
        errors.extend(cls._check_required_sections(config))
        errors.extend(cls._check_required_fields(config))

        return errors

    @classmethod
    def _check_placeholders(cls, config: Dict[str, Any]) -> List[str]:
        """Busca placeholders <TU_*> sin hidratar en todo el config."""
        errors: List[str] = []
        text = str(config)
        matches = cls.PLACEHOLDER_PATTERN.findall(text)
        if matches:
            unique = list(set(matches))
            errors.append(f"Placeholders sin hidratar: {', '.join(unique)}")
        return errors

    @classmethod
    def _check_required_sections(cls, config: Dict[str, Any]) -> List[str]:
        """Verifica que las secciones requeridas existan."""
        errors: List[str] = []
        for section in cls.REQUIRED_SECTIONS:
            if section not in config:
                errors.append(f"Seccion requerida '{section}' no encontrada")
        return errors

    @classmethod
    def _check_required_fields(cls, config: Dict[str, Any]) -> List[str]:
        """Verifica campos minimos por seccion."""
        errors: List[str] = []
        for section, fields in cls.SECTION_REQUIRED_FIELDS.items():
            section_data = config.get(section, {})
            if not isinstance(section_data, dict):
                continue
            for field in fields:
                value = section_data.get(field, "")
                if not value or cls.PLACEHOLDER_PATTERN.search(str(value)):
                    errors.append(f"{section}.{field} esta vacio o tiene placeholder")
        return errors

    @classmethod
    def has_placeholders(cls, config: Dict[str, Any]) -> bool:
        """True si el config contiene placeholders sin hidratar."""
        text = str(config)
        return bool(cls.PLACEHOLDER_PATTERN.search(text))
