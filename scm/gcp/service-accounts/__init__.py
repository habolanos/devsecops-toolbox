"""
GCP Service Accounts Multi-Project Reporter
Herramienta para extraer, analizar y reportar service accounts de múltiples proyectos GCP
"""

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

from .sa_config_loader import ConfigLoader
from .sa_extractors import ServiceAccountExtractor
from .sa_analyzers import RolesAndPermissionsAnalyzer, SecurityAnalyzer
from .sa_report_generators import JSONReportGenerator, CSVReportGenerator, ExcelReportGenerator

__all__ = [
    'ConfigLoader',
    'ServiceAccountExtractor',
    'RolesAndPermissionsAnalyzer',
    'SecurityAnalyzer',
    'JSONReportGenerator',
    'CSVReportGenerator',
    'ExcelReportGenerator'
]
