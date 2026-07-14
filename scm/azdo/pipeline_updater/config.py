"""
Configuración para Pipeline Updater
"""

# API Configuration
AZDO_API_VERSION = "7.1"
AZDO_BASE_URL = "https://vsrm.dev.azure.com"

# Execution Configuration
DEFAULT_WORKERS = 5
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3

# Output Configuration
SNAPSHOT_DIR = "outcome/snapshots"
REPORT_DIR = "outcome/pipeline_updates"
LOG_DIR = "outcome/logs"

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
