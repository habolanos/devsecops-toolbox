"""
Configuración para Health Probe Masivo Validator
"""
import json
import os
from pathlib import Path
from typing import Dict, List


def _load_global_config() -> Dict:
    """Carga configuración desde scm/config.json si existe."""
    config_file = Path(__file__).parent.parent.parent / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _resolve_output_dir(config: Dict) -> str:
    """Resuelve output_dir desde global.output_dir en config.json."""
    global_cfg = config.get('global', {})
    output_dir = global_cfg.get('output_dir', 'outcome')
    if not Path(output_dir).is_absolute():
        config_file = Path(__file__).parent.parent.parent
        output_dir = str(config_file / output_dir)
    return output_dir


_global_config = _load_global_config()

# Azure DevOps Configuration
_azdo_cfg = _global_config.get('azdo', {})
_org_url = _azdo_cfg.get('organization_url', '')
_org_name = _org_url.split('/')[-1] if _org_url else ''

AZDO_ORG = os.getenv("AZDO_ORG", _org_name or "Coppel-Retail")
AZDO_PROJECT = os.getenv("AZDO_PROJECT", _azdo_cfg.get('project', 'Cadena_de_Suministros'))
AZDO_PAT = os.getenv("AZDO_PAT", _azdo_cfg.get('pat', ''))
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
_global_output_dir = _resolve_output_dir(_global_config)
OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(Path(_global_output_dir) / "health_probe"))
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
