"""
Punto de entrada para ejecutar el módulo como paquete.

Permite ejecutar:
  python -m scm.gcp.pubsub_monitor
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para permitir imports relativos
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from scm.gcp.pubsub_monitor.pubsub_monitor import main

if __name__ == "__main__":
    main()
