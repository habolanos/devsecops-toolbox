#!/usr/bin/env python3
"""
Script wrapper para ejecutar Pub/Sub Monitor.

Este script resuelve los problemas de imports relativos cuando se ejecuta
el módulo directamente desde la línea de comandos.

Uso:
  python scm/gcp/pubsub_monitor/run.py
  python scm/gcp/pubsub_monitor/run.py --config scm/config.json
"""

import sys
import os
from pathlib import Path

# Obtener el directorio raíz del proyecto
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

# Cambiar al directorio raíz para que los paths relativos funcionen
os.chdir(root_dir)

# Importar y ejecutar el monitor
from scm.gcp.pubsub_monitor.pubsub_monitor import main

if __name__ == "__main__":
    main()
