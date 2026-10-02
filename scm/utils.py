#!/usr/bin/env python3
"""
Utilidades compartidas para todo el DevSecOps Toolbox.

Este módulo debe ser importable desde cualquier script bajo scm/.
main.py y los tools.py agregan scm/ a PYTHONPATH antes de lanzar scripts.
"""

import os
import atexit
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime


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


def gke_kube_env(cluster_name: str) -> dict:
    """Entorno con KUBECONFIG aislado por cluster para gcloud/kubectl."""
    env = os.environ.copy()
    env["KUBECONFIG"] = str(_GKE_KUBECONFIG_DIR / f"{cluster_name}.yaml")
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
                                timeout=timeout, env=gke_kube_env(cluster_name))
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
