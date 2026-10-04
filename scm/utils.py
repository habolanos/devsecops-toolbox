#!/usr/bin/env python3
"""
Utilidades compartidas para todo el DevSecOps Toolbox.

Este módulo debe ser importable desde cualquier script bajo scm/.
main.py y los tools.py agregan scm/ a PYTHONPATH antes de lanzar scripts.
"""

import os
import sys
import json
import atexit
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime


SCM_ROOT = Path(__file__).resolve().parent
SCM_CONFIG_FILE = SCM_ROOT / "config.json"


def load_global_config() -> dict:
    """Lee la sección `global` de scm/config.json. Retorna {} si no existe o falla."""
    try:
        if SCM_CONFIG_FILE.exists():
            cfg = json.loads(SCM_CONFIG_FILE.read_text(encoding="utf-8"))
            section = cfg.get("global")
            return section if isinstance(section, dict) else {}
    except Exception:
        pass
    return {}


def resolve_outcome_dir(default: str = "outcome") -> Path:
    """
    Resuelve el directorio de salida global del toolbox.

    Orden de resolución:
      1. Variable de entorno DEVSECOPS_OUTPUT_DIR (inyectada por main.py)
      2. scm/config.json → global.output_dir (relativa se resuelve bajo scm/)
      3. scm/<default>

    El directorio se crea automáticamente si no existe.
    """
    env = os.getenv("DEVSECOPS_OUTPUT_DIR")
    if env:
        p = Path(env)
    else:
        p = Path(load_global_config().get("output_dir") or default)
        if not p.is_absolute():
            p = SCM_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def global_flag(name: str) -> bool:
    """
    Flag booleano de la configuración global.

    Orden: variable DEVSECOPS_<NAME> (inyectada por main.py) >
    config.json → global.<name>.
    """
    env_val = os.getenv(f"DEVSECOPS_{name.upper()}")
    if env_val is not None:
        return env_val.strip().lower() in {"1", "true", "yes", "on"}
    return bool(load_global_config().get(name))


def is_live_terminal() -> bool:
    """
    True si stdout puede renderizar animaciones de Rich (spinners/Progress).

    sys.stdout.isatty() cubre la ejecución directa en terminal. Además, el
    launcher (tools.py) inyecta TTY_COMPATIBLE=1 cuando él sí corre en un TTY
    pero reenvía la salida del proceso hijo por un pipe — las secuencias ANSI
    del hijo llegan intactas al terminal real, por lo que el hijo puede (y
    debe) animar. Rich honra TTY_COMPATIBLE en Console.is_terminal.
    """
    if sys.stdout.isatty():
        return True
    return os.environ.get("TTY_COMPATIBLE", "").strip().lower() in {
        "1", "true", "yes", "on"}


def log_command(cmd, status: str = "EXEC", platform_name: str = "GCP") -> None:
    """Registra un comando en <outcome>/commands_YYYYMMDD.log si log_commands está activo."""
    if not global_flag("log_commands"):
        return
    log_dir = resolve_outcome_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y%m%d")
    cmd_str = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    try:
        with open(log_dir / f"commands_{today}.log", "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{platform_name}] [{status}] {cmd_str}\n")
    except OSError:
        pass


def get_output_dir(default: str = ".") -> Path:
    """
    Retorna el directorio de salida para reportes.

    Orden de resolución:
      1. Variable de entorno DEVSECOPS_OUTPUT_DIR (inyectada por main.py)
      2. Parámetro `default` (usualmente "outcome" o ".")

    El directorio se crea automáticamente si no existe.
    """
    env = os.getenv("DEVSECOPS_OUTPUT_DIR")
    if env:
        p = Path(env)
    else:
        p = Path(default)
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


# Extensiones por formato de salida
FORMAT_EXTENSIONS = {
    "excel": ".xlsx",
    "csv":   ".csv",
    "json":  ".json",
}


def resolve_output_path(output_arg: Optional[str], base_name: str,
                        default_format: str = "excel") -> str:
    """
    Normaliza el argumento --output del menú.

    El menú pasa formatos como 'excel', 'csv', 'json' en vez de paths.
    Esta función:
      - Si output_arg es None → genera path en outcome/ con extensión default
      - Si output_arg es un formato (excel/csv/json) → genera path en outcome/ con esa extensión
      - Si output_arg es un path real → lo usa tal cual (agrega extensión si no tiene)

    Retorna string con path absoluto.
    """
    output_dir = get_output_dir("outcome")
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = FORMAT_EXTENSIONS.get(default_format, ".xlsx")

    if not output_arg:
        return str(output_dir / f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")

    # ¿Es un formato del menú?
    if output_arg.lower() in FORMAT_EXTENSIONS:
        ext = FORMAT_EXTENSIONS[output_arg.lower()]
        return str(output_dir / f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")

    # Es un path proporcionado por el usuario
    p = Path(output_arg)
    if p.suffix == "":
        p = p.with_suffix(ext)
    return str(p.resolve())


# ═══════════════════════════════════════════════════════════════════════════
# Helpers GKE / kubectl
#
# `gcloud container clusters get-credentials` hace read-modify-write NO atómico
# de ~/.kube/config: si varias llamadas corren en paralelo, las escrituras se
# pisan y algunos contextos nunca quedan guardados ("context was not found").
# Para poder paralelizar de forma segura, cada cluster trabaja con su propio
# archivo KUBECONFIG aislado en un directorio temporal que se limpia al salir.
# ═══════════════════════════════════════════════════════════════════════════

_GKE_KUBECONFIG_DIR = Path(tempfile.mkdtemp(prefix="gke-kubeconfig-"))
atexit.register(lambda: shutil.rmtree(_GKE_KUBECONFIG_DIR, ignore_errors=True))


def gke_kube_env(cluster_name: str, project_id: str = "") -> dict:
    """Entorno con KUBECONFIG aislado por (proyecto, cluster).

    La clave incluye el proyecto porque dos proyectos distintos pueden tener
    clusters homónimos: sin él compartirían el mismo archivo y los
    get-credentials en paralelo se pisarían entre sí.
    """
    env = os.environ.copy()
    key = f"{project_id}-{cluster_name}" if project_id else cluster_name
    env["KUBECONFIG"] = str(_GKE_KUBECONFIG_DIR / f"{key}.yaml")
    return env


def gke_context_name(project_id: str, location: str, cluster_name: str) -> str:
    """Nombre del contexto kubectl que genera gcloud para un cluster GKE."""
    return f"gke_{project_id}_{location}_{cluster_name}"


def gke_location_flag(location: str) -> str:
    """--zone si es zona (p.ej. us-central1-a), --region si es región."""
    return f"--zone={location}" if location.count("-") == 2 else f"--region={location}"


def ensure_gke_cluster_credentials(project_id: str, cluster_name: str,
                                   location: str, timeout: int = 60,
                                   debug: bool = False, logger=None) -> bool:
    """Ejecuta get-credentials sobre el KUBECONFIG aislado del cluster.

    Seguro en paralelo (archivos independientes por cluster) y con cache por
    proceso. Devuelve True si el contexto quedó disponible.
    """
    cache_key = f"{project_id}:{location}:{cluster_name}"
    if getattr(ensure_gke_cluster_credentials, "_cache", None) is None:
        ensure_gke_cluster_credentials._cache = {}
    cache = ensure_gke_cluster_credentials._cache
    if cache_key in cache:
        return cache[cache_key]
    cmd = (f"gcloud container clusters get-credentials {cluster_name} "
           f"--project={project_id} {gke_location_flag(location)} --quiet")
    ok = False
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                timeout=timeout, env=gke_kube_env(cluster_name, project_id))
        ok = result.returncode == 0
        if debug and logger:
            logger.info(f"get-credentials returncode: {result.returncode}")
        if not ok and logger:
            stderr_hint = (result.stderr or "").strip().splitlines()
            hint = stderr_hint[0][:200] if stderr_hint else "sin stderr"
            logger.warning(
                f"get-credentials falló para {cluster_name} "
                f"(rc={result.returncode}): {hint}"
            )
    except subprocess.TimeoutExpired:
        if logger:
            logger.warning(f"Timeout (>{timeout}s) obteniendo credenciales para {cluster_name}")
    except Exception as e:
        if logger:
            logger.warning(f"Error obteniendo credenciales para {cluster_name}: {e}")
    cache[cache_key] = ok
    return ok
