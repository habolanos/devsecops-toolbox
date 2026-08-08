"""
DevSecOps Toolbox - Setup Wizard Package

Wizard de configuracion inicial para primera ejecucion.
Detecta CLIs, hidrata config.json desde template, valida credenciales.
"""

from setup.wizard import SetupWizard

__all__ = ["SetupWizard"]
__version__ = "1.0.0"
