"""
Configuración para Pipeline Updater
"""

import json
from pathlib import Path
from typing import Dict

# API Configuration
AZDO_API_VERSION = "7.1"
AZDO_BASE_URL = "https://vsrm.dev.azure.com"

# Execution Configuration
DEFAULT_WORKERS = 5
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3

# Template Configuration
TEMPLATE_REQUIRED_FIELDS = ['metadata', 'search', 'update']
METADATA_REQUIRED_FIELDS = ['name', 'version']

# Validation Configuration
MAX_DEFINITION_IDS = 100
MIN_DEFINITION_ID = 1

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"

# Report Configuration
REPORT_FORMATS = ['json', 'csv', 'html']


def load_config() -> Dict:
    """Carga configuración desde scm/config.json si existe."""
    config_file = Path(__file__).parent.parent.parent / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                global_cfg = config.get('global', {})
                output_dir = global_cfg.get('output_dir', 'outcome')
                if not Path(output_dir).is_absolute():
                    output_dir = str(config_file.parent / output_dir)
                azdo_cfg = config.get('azdo', {})
                org_url = azdo_cfg.get('organization_url', '')
                organization = org_url.split('/')[-1] if org_url else ''
                return {
                    'organization': organization,
                    'project': azdo_cfg.get('project', ''),
                    'pat': azdo_cfg.get('pat', ''),
                    'output_dir': output_dir,
                }
        except Exception:
            pass
    return {}


_global_config = load_config()
_OUTPUT_DIR = _global_config.get('output_dir', str(Path(__file__).parent.parent.parent / 'outcome'))

# Output Configuration (resolved from global.output_dir)
SNAPSHOT_DIR = str(Path(_OUTPUT_DIR) / "snapshots")
REPORT_DIR = str(Path(_OUTPUT_DIR) / "pipeline_updates")
LOG_DIR = str(Path(_OUTPUT_DIR) / "logs")
