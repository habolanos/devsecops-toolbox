"""
Configuración para Health Probe Masivo Validator
"""
import os
from typing import List

# Azure DevOps Configuration
AZDO_ORG = os.getenv("AZDO_ORG", "Coppel-Retail")
AZDO_PROJECT = os.getenv("AZDO_PROJECT", "Cadena_de_Suministros")
AZDO_PAT = os.getenv("AZDO_PAT", "")
AZDO_API_VERSION = "7.1"
AZDO_BASE_URL = "https://dev.azure.com"

# Kubernetes Configuration
K8S_NAMESPACES: List[str] = os.getenv("K8S_NAMESPACES", "default,production,staging").split(",")
K8S_KUBECONFIG = os.getenv("KUBECONFIG", None)

# Connectivity Testing
CONNECTIVITY_POD_IMAGE = "nicolaka/netshoot:latest"
CONNECTIVITY_POD_NAME = "health-probe-checker"
CONNECTIVITY_NAMESPACE = "default"

# Processing Configuration
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 24 horas

# Output Configuration
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outcome/health_probe")
EXPORT_FORMATS = ["json", "csv", "html", "excel"]

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(OUTPUT_DIR, "health_probe_validator.log")

# Retry Configuration
MAX_RETRIES = 3
BACKOFF_FACTOR = 2

# Health Check Thresholds
LATENCY_WARNING_MS = 1000
LATENCY_CRITICAL_MS = 5000
PROBE_TIMEOUT_MIN = 5  # segundos
PROBE_PERIOD_MIN = 10  # segundos
