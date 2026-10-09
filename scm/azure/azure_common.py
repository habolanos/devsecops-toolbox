#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Common — helpers compartidos para la suite scm/azure.

Convención del proyecto: los tools usan **Azure CLI** (`az ... -o
json`) como backend — el README de scm/azure ya lo requiere y evita
depender de paquetes azure-mgmt-* no listados en requirements.txt.
AKS usa `az aks get-credentials` + `kubectl -o json` (mismo patrón
que EKS en scm/aws/eks).

- run_az / kubectl_json / az_check
- Resolución de suscripción: --subscription > config.json
  (azure.subscription_id) > `az account show`
- Directorio de salida: DEVSECOPS_OUTPUT_DIR > scm/outcome
- Consola Rich opcional + UTF-8 en Windows
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Directorio de salida centralizado ---
try:
    from utils import get_output_dir
except ImportError:
    def get_output_dir(default="."):
        env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        p = Path(env) if env else Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# ------------------------------------------

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


def az_available() -> bool:
    """True si az CLI está instalado y logueado."""
    if not shutil.which("az"):
        return False
    try:
        subprocess.run(["az", "account", "show", "-o", "none"],
                       capture_output=True, timeout=30, check=True)
        return True
    except Exception:
        return False


def run_az(args: List[str], subscription: Optional[str] = None,
           timeout: int = 180) -> Union[List, Dict, str, None]:
    """Ejecuta `az <args> -o json` y retorna el JSON parseado.

    Lanza RuntimeError con el stderr si az falla.
    """
    cmd = ["az", *args, "-o", "json"]
    if subscription:
        cmd += ["--subscription", subscription]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(
            f"az {' '.join(args)} → rc={proc.returncode}: "
            f"{(proc.stderr or proc.stdout).strip()[:300]}")
    text = (proc.stdout or "").strip()
    if not text:
        return None
    return json.loads(text)


def try_az(args: List[str], subscription: Optional[str] = None,
           timeout: int = 180, default=None):
    """run_az tolerante: retorna `default` ante cualquier error."""
    try:
        result = run_az(args, subscription, timeout)
        return default if result is None else result
    except Exception:
        return default


def run_kubectl(args: List[str], timeout: int = 60) -> str:
    """kubectl plano → stdout (lanza RuntimeError)."""
    proc = subprocess.run(["kubectl", *args], capture_output=True,
                          text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(
            f"kubectl {' '.join(args)} → rc={proc.returncode}: "
            f"{proc.stderr.strip()[:300]}")
    return proc.stdout


def kubectl_json(args: List[str], timeout: int = 60) -> Dict:
    """kubectl <args> -o json → dict."""
    return json.loads(run_kubectl([*args, "-o", "json"], timeout))


def setup_aks_kubeconfig(cluster: str, resource_group: str,
                         subscription: Optional[str] = None,
                         timeout: int = 60) -> bool:
    """Descarga credenciales del cluster AKS al kubeconfig actual."""
    cmd = ["az", "aks", "get-credentials", "--name", cluster,
           "--resource-group", resource_group, "--overwrite-existing"]
    if subscription:
        cmd += ["--subscription", subscription]
    try:
        subprocess.run(cmd, capture_output=True, timeout=timeout,
                       check=True)
        return True
    except Exception:
        return False


def load_config() -> Dict:
    """Lee la sección `azure` de scm/config.json ({} si falta)."""
    cfg_path = Path(__file__).parent.parent / "config.json"
    try:
        return json.loads(cfg_path.read_text(
            encoding="utf-8")).get("azure", {})
    except Exception:
        return {}


def resolve_subscription(cli_value: Optional[str] = None) -> str:
    """--subscription > config.json > `az account show`."""
    if cli_value and "<" not in cli_value:
        return cli_value
    cfg = load_config()
    sub = cfg.get("subscription_id", "")
    if sub and "<" not in sub:
        return sub
    try:
        return run_az(["account", "show",
                       "--query", "id"]) or ""
    except Exception:
        return ""


def az_account_name(subscription: str) -> str:
    return try_az(["account", "show", "--query", "name"],
                  subscription, default="") or ""


def rg_of(resource: Dict) -> str:
    """resourceGroup del recurso (campo o derivado del id)."""
    if resource.get("resourceGroup"):
        return resource["resourceGroup"]
    parts = (resource.get("id") or "").split("/")
    for i, p in enumerate(parts):
        if p.lower() == "resourcegroups" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def now_ts() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def export_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, default=str),
                    encoding="utf-8")


def export_csv(path: Path, fieldnames: List[str],
               rows: List[Dict]) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
