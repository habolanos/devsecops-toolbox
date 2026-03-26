#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Task Validator

Herramienta DevSecOps para validación de releases en Azure DevOps:
- Validación de imágenes Docker (Harbor/Artifact Registry)
- Búsqueda de Release Rollback por TAG
- Validación de vigencia de credenciales GIT
- Comparación de ConfigMap vs Repositorio

Autor: Harold Adrian
Basado en: azdo-task-validador-optimized.sh
"""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.0.0"
__author__ = "Harold Adrian"
__description__ = "Azure DevOps Task Validator - DevSecOps Release Validation"

# Consola Rich
console = Console() if RICH_AVAILABLE else None

# Rutas
BASE_DIR = Path(__file__).parent.absolute()
OUTCOME_DIR = BASE_DIR / "outcome"

# ═══════════════════════════════════════════════════════════════════════════════
# COLORES FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING (Compatible con Azure DevOps)
# ═══════════════════════════════════════════════════════════════════════════════
def ts() -> str:
    """Retorna timestamp actual."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def log_info(msg: str) -> None:
    """Log informativo."""
    if RICH_AVAILABLE and console:
        console.print(f"[green]✓[/green] [{ts()}] {msg}")
    else:
        print(f"[INFO]  {ts()} {msg}")


def log_warn(msg: str) -> None:
    """Log de advertencia (compatible con Azure DevOps)."""
    if RICH_AVAILABLE and console:
        console.print(f"[yellow]⚠[/yellow] [{ts()}] {msg}")
    else:
        print(f"##vso[task.logissue type=warning;]{ts()} {msg}")


def log_error(msg: str) -> None:
    """Log de error (compatible con Azure DevOps)."""
    if RICH_AVAILABLE and console:
        console.print(f"[red]✗[/red] [{ts()}] {msg}")
    else:
        print(f"##vso[task.logissue type=error;]{ts()} {msg}")


def section(title: str) -> None:
    """Imprime sección."""
    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel(title, border_style="cyan", box=box.DOUBLE_EDGE))
    else:
        print()
        print("═" * 50)
        print(f"  {title}")
        print("═" * 50)


def set_azdo_variable(name: str, value: str) -> None:
    """Establece variable de Azure DevOps."""
    print(f"##vso[task.setvariable variable={name}]{value}")
    log_info(f"Variable '{name}' establecida: {value}")


# ═══════════════════════════════════════════════════════════════════════════════
# AZURE DEVOPS API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════
class AzureDevOpsClient:
    """Cliente para Azure DevOps REST API."""
    
    def __init__(self, org: str, project: str, pat: str, api_version: str = "7.1"):
        self.org = org
        self.project = project
        self.pat = pat
        self.api_version = api_version
        self.session = requests.Session()
        
        # Autenticación Basic con PAT
        auth_string = f":{pat}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {auth_bytes}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # URLs base
        self.base_url = f"https://dev.azure.com/{org}/{project}"
        self.vsrm_url = f"https://vsrm.dev.azure.com/{org}/{project}"
    
    def _request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Realiza request con reintentos."""
        kwargs.setdefault("timeout", 30)
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                if response.text:
                    return response.json()
                return {}
                
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    log_error(f"Error en request después de 3 intentos: {e}")
                    return None
                log_warn(f"Reintentando request (intento {attempt + 2}/3)...")
        
        return None
    
    def get(self, url: str, **kwargs) -> Optional[Dict]:
        """GET request."""
        return self._request("GET", url, **kwargs)
    
    def put(self, url: str, data: Dict, **kwargs) -> Optional[Dict]:
        """PUT request."""
        return self._request("PUT", url, json=data, **kwargs)
    
    def get_release(self, release_id: int) -> Optional[Dict]:
        """Obtiene detalle de un release."""
        url = f"{self.vsrm_url}/_apis/release/releases/{release_id}?api-version={self.api_version}"
        return self.get(url)
    
    def list_releases(self, definition_id: int, top: int = 50) -> Optional[Dict]:
        """Lista releases de una definición."""
        url = f"{self.vsrm_url}/_apis/release/releases?definitionId={definition_id}&$top={top}&api-version={self.api_version}"
        return self.get(url)
    
    def update_release_variable(self, release_id: int, var_name: str, var_value: str) -> bool:
        """Actualiza una variable en un release."""
        url = f"{self.vsrm_url}/_apis/release/releases/{release_id}?api-version={self.api_version}"
        
        # Obtener release actual
        release = self.get_release(release_id)
        if not release:
            log_error(f"No se pudo obtener release {release_id}")
            return False
        
        # Actualizar variable
        if "variables" not in release:
            release["variables"] = {}
        
        release["variables"][var_name] = {"value": var_value}
        
        # Enviar actualización
        result = self.put(url, release)
        if result:
            log_info(f"Variable '{var_name}' actualizada en release {release_id}")
            return True
        return False
    
    def get_variable_group(self, group_id: int) -> Optional[Dict]:
        """Obtiene un variable group."""
        url = f"{self.base_url}/_apis/distributedtask/variablegroups/{group_id}?api-version={self.api_version}"
        return self.get(url)
    
    def get_build(self, build_id: int) -> Optional[Dict]:
        """Obtiene detalle de un build."""
        url = f"{self.base_url}/_apis/build/builds/{build_id}?api-version={self.api_version}"
        return self.get(url)
    
    def get_build_timeline(self, build_id: int) -> Optional[Dict]:
        """Obtiene timeline de un build."""
        url = f"{self.base_url}/_apis/build/builds/{build_id}/timeline?api-version={self.api_version}"
        return self.get(url)
    
    def get_commits(self, repo_name: str, file_path: str, branch: str, top: int = 20) -> Optional[Dict]:
        """Obtiene commits de un archivo."""
        encoded_path = quote(file_path, safe="")
        url = (f"{self.base_url}/_apis/git/repositories/{repo_name}/commits?"
               f"searchCriteria.itemPath={encoded_path}&"
               f"searchCriteria.itemVersion.version={branch}&"
               f"searchCriteria.$top={top}&api-version={self.api_version}")
        return self.get(url)
    
    def get_file_content(self, repo_name: str, file_path: str, commit_id: str) -> Optional[str]:
        """Obtiene contenido de un archivo en un commit específico."""
        encoded_path = quote(file_path, safe="")
        url = (f"{self.base_url}/_apis/git/repositories/{repo_name}/items?"
               f"path={encoded_path}&version={commit_id}&versionType=commit&"
               f"api-version={self.api_version}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDADORES
# ═══════════════════════════════════════════════════════════════════════════════
class ImageValidator:
    """Validador de imágenes Docker."""
    
    def __init__(self, gcp_project: str = None, debug: bool = False):
        self.gcp_project = gcp_project
        self.debug = debug
    
    def _run_command(self, cmd: List[str], capture: bool = True) -> Tuple[int, str, str]:
        """Ejecuta un comando y retorna (exit_code, stdout, stderr)."""
        if self.debug:
            log_info(f"DEBUG: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                timeout=60
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Timeout"
        except Exception as e:
            return 1, "", str(e)
    
    def check_gcloud_auth(self) -> bool:
        """Verifica autenticación de gcloud."""
        code, stdout, _ = self._run_command([
            "gcloud", "auth", "list",
            "--filter=status:ACTIVE",
            "--format=value(account)"
        ])
        
        if code != 0 or not stdout.strip():
            log_error("No hay sesión activa de gcloud. Ejecuta: gcloud auth login")
            return False
        
        log_info(f"Sesión gcloud activa: {stdout.strip().split()[0]}")
        return True
    
    def activate_service_account(self, key_file: str) -> bool:
        """Activa una service account."""
        if not os.path.exists(key_file):
            log_error(f"Archivo de credenciales no encontrado: {key_file}")
            return False
        
        code, _, stderr = self._run_command([
            "gcloud", "auth", "activate-service-account",
            f"--key-file={key_file}"
        ])
        
        if code != 0:
            log_error(f"Error activando service account: {stderr}")
            return False
        
        if self.gcp_project:
            self._run_command(["gcloud", "config", "set", "project", self.gcp_project])
        
        log_info("Service account activada")
        return True
    
    def revoke_credentials(self) -> None:
        """Revoca credenciales de gcloud."""
        log_info("Revocando credenciales gcloud...")
        self._run_command(["gcloud", "auth", "revoke", "--all", "--quiet"])
        
        code, stdout, _ = self._run_command([
            "gcloud", "auth", "list",
            "--filter=status:ACTIVE",
            "--format=value(account)"
        ])
        
        if stdout.strip():
            log_error("Aún existen cuentas activas después del revoke (FALLO DE SEGURIDAD)")
        else:
            log_info("OK: sin cuentas activas")
    
    def check_image_exists(self, image: str) -> bool:
        """Verifica que una imagen exista."""
        log_info(f"Validando existencia: {image}")
        
        if "artifact.coppel.io" in image or "harbor" in image.lower():
            # Harbor - usar crane
            code, _, stderr = self._run_command(["crane", "digest", image])
            if code != 0:
                log_error(f"Imagen NO existe en Harbor: {image}")
                return False
        
        elif "docker.pkg.dev" in image:
            # Artifact Registry
            code, _, stderr = self._run_command([
                "gcloud", "artifacts", "docker", "images", "describe",
                image, "--format=value(image_summary.digest)"
            ])
            if code != 0:
                log_error(f"Imagen NO existe en Artifact Registry: {image}")
                return False
        
        elif "gcr.io" in image:
            # GCR
            code, _, stderr = self._run_command([
                "gcloud", "container", "images", "describe", image
            ])
            if code != 0:
                log_error(f"Imagen NO existe en GCR: {image}")
                return False
        
        else:
            log_warn(f"Dominio no reconocido, asumiendo existencia: {image}")
            return True
        
        log_info(f"OK: imagen existe")
        return True
    
    def extract_tag(self, image: str) -> str:
        """Extrae el tag de una imagen."""
        if ":" in image:
            return image.split(":")[-1]
        return "latest"


class RollbackFinder:
    """Buscador de releases para rollback."""
    
    def __init__(self, client: AzureDevOpsClient, debug: bool = False):
        self.client = client
        self.debug = debug
    
    def find_rollback_release(self, current_release_id: int, target_tag: str) -> Optional[int]:
        """Busca release de rollback por TAG."""
        log_info(f"Buscando release con TAG: {target_tag}")
        
        # Obtener release actual para definition_id
        current_release = self.client.get_release(current_release_id)
        if not current_release:
            log_error(f"No se pudo obtener release actual: {current_release_id}")
            return None
        
        definition_id = current_release.get("releaseDefinition", {}).get("id")
        if not definition_id:
            log_error("No se pudo obtener definition_id")
            return None
        
        # Listar releases
        releases_data = self.client.list_releases(definition_id, top=50)
        if not releases_data or "value" not in releases_data:
            log_error("No se pudieron listar releases")
            return None
        
        releases = releases_data["value"]
        log_info(f"Analizando {len(releases)} releases...")
        
        for release in releases:
            rid = release.get("id")
            
            # Saltar release actual
            if rid == current_release_id:
                continue
            
            # Obtener detalle del release
            release_detail = self.client.get(release.get("url", ""))
            if not release_detail:
                continue
            
            # Buscar artifact de tipo Build
            artifacts = release_detail.get("artifacts", [])
            for artifact in artifacts:
                if artifact.get("type") != "Build":
                    continue
                
                # Obtener build URL
                build_ref = artifact.get("definitionReference", {})
                build_url = build_ref.get("artifactSourceVersionUrl", {}).get("id", "")
                
                if not build_url:
                    continue
                
                # Extraer build_id
                build_id = self._extract_build_id(build_url)
                if not build_id:
                    continue
                
                # Verificar si el build contiene el TAG
                if self._check_build_for_tag(build_id, target_tag):
                    log_info(f"✓ Rollback Release encontrada: {rid}")
                    return rid
        
        log_error(f"No se encontró Release rollback para tag {target_tag}")
        return None
    
    def _extract_build_id(self, build_url: str) -> Optional[int]:
        """Extrae build_id de una URL."""
        # URL formato: ...buildId=123...
        match = re.search(r'buildId=(\d+)', build_url)
        if match:
            return int(match.group(1))
        
        # URL formato: .../builds/123
        match = re.search(r'/builds/(\d+)', build_url)
        if match:
            return int(match.group(1))
        
        return None
    
    def _check_build_for_tag(self, build_id: int, target_tag: str) -> bool:
        """Verifica si un build contiene el TAG buscado."""
        build = self.client.get_build(build_id)
        if not build:
            return False
        
        # Obtener timeline
        timeline_url = build.get("_links", {}).get("timeline", {}).get("href", "")
        if not timeline_url:
            return False
        
        timeline = self.client.get(timeline_url)
        if not timeline:
            return False
        
        # Buscar task "Push Image" en los records
        for record in timeline.get("records", []):
            if record.get("type") != "Task":
                continue
            
            name = record.get("name", "")
            if not name.startswith("Push Image"):
                continue
            
            # Obtener log
            log_url = record.get("log", {}).get("url", "")
            if not log_url:
                continue
            
            try:
                response = self.client.session.get(log_url, timeout=30)
                if response.status_code == 200:
                    log_content = response.text
                    
                    # Buscar tag en el log
                    pattern = rf":{re.escape(target_tag)}(\"|\\s|$|[^a-zA-Z0-9.-])"
                    if re.search(pattern, log_content):
                        return True
            except Exception:
                pass
        
        return False


class CredentialValidator:
    """Validador de vigencia de credenciales."""
    
    def __init__(self, client: AzureDevOpsClient):
        self.client = client
    
    def validate_credentials(self, group_id: int, rollback_release_id: int) -> bool:
        """Valida que las credenciales GIT sean vigentes vs release rollback."""
        log_info("Validando vigencia de credenciales GIT...")
        
        # Obtener variable group
        vg = self.client.get_variable_group(group_id)
        if not vg:
            log_error(f"No se pudo obtener variable group: {group_id}")
            return False
        
        modified_on = vg.get("modifiedOn", "")
        if not modified_on:
            log_error("No se pudo obtener fecha de modificación del variable group")
            return False
        
        # Obtener release rollback
        release = self.client.get_release(rollback_release_id)
        if not release:
            log_error(f"No se pudo obtener release rollback: {rollback_release_id}")
            return False
        
        created_on = release.get("createdOn", "")
        if not created_on:
            log_error("No se pudo obtener fecha de creación del release")
            return False
        
        # Comparar fechas
        git_date = self._parse_date(modified_on)
        rb_date = self._parse_date(created_on)
        
        log_info(f"Fecha modificación credenciales GIT: {git_date.strftime('%Y-%m-%d')}")
        log_info(f"Fecha creación release rollback    : {rb_date.strftime('%Y-%m-%d')}")
        
        if git_date > rb_date:
            log_error("Credenciales GIT vencidas: fueron modificadas después del release rollback")
            return False
        
        log_info("Credenciales GIT vigentes")
        return True
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parsea fecha de Azure DevOps."""
        # Formato: 2024-01-15T10:30:00.123Z
        date_str = date_str.split("T")[0]
        return datetime.strptime(date_str, "%Y-%m-%d")


class ConfigMapComparator:
    """Comparador de ConfigMap vs Repositorio."""
    
    def __init__(self, client: AzureDevOpsClient, debug: bool = False):
        self.client = client
        self.debug = debug
    
    def compare(
        self,
        artifact_name: str,
        artifact_namespace: str,
        repo_name: str,
        branch: str
    ) -> Optional[str]:
        """Compara ConfigMap de K8s con repositorio y retorna commit_id si coincide."""
        log_info(f"Comparando ConfigMap vs Repo para: {artifact_name}")
        
        # Obtener ConfigMap de K8s
        k8s_content = self._get_configmap_content(artifact_name, artifact_namespace)
        if not k8s_content:
            log_error("No se pudo obtener contenido del ConfigMap")
            return None
        
        # Normalizar contenido K8s
        k8s_norm = self._normalize_content(k8s_content)
        k8s_hash = hashlib.md5(k8s_norm.encode()).hexdigest()
        
        log_info(f"Hash ConfigMap K8s: {k8s_hash}")
        
        # Determinar path en repo
        svc_lower = artifact_name.lower()
        # Buscar archivo de configuración (puede ser .yml, .yaml, .properties)
        possible_files = [
            f"/{svc_lower}/application.yml",
            f"/{svc_lower}/application.yaml",
            f"/{svc_lower}/config.yml",
            f"/{svc_lower}/config.yaml",
        ]
        
        # Ajustar rama según reglas especiales
        if artifact_namespace == "pvm":
            branch = "pvm-prod-gke"
        
        # Obtener commits del archivo
        for file_path in possible_files:
            commits_data = self.client.get_commits(repo_name, file_path, branch, top=20)
            
            if not commits_data or "value" not in commits_data:
                continue
            
            commits = commits_data["value"]
            if not commits:
                continue
            
            log_info(f"Analizando {len(commits)} commits para {file_path}...")
            
            for commit in commits:
                commit_id = commit.get("commitId")
                if not commit_id:
                    continue
                
                # Obtener contenido del archivo en este commit
                repo_content = self.client.get_file_content(repo_name, file_path, commit_id)
                if not repo_content:
                    continue
                
                # Normalizar y comparar
                repo_norm = self._normalize_content(repo_content)
                repo_hash = hashlib.md5(repo_norm.encode()).hexdigest()
                
                if k8s_hash == repo_hash:
                    log_info(f"✓ Coincidencia exacta encontrada: {commit_id}")
                    return commit_id
                
                if self.debug:
                    log_info(f"No coincide: K8s {k8s_hash} vs Repo {repo_hash}")
        
        log_warn("No se encontró coincidencia exacta en los últimos 20 commits")
        return None
    
    def _get_configmap_content(self, name: str, namespace: str) -> Optional[str]:
        """Obtiene contenido de un ConfigMap de K8s."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "configmap", f"{name}-config",
                 "-n", namespace, "-o", "yaml"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                log_error(f"Error obteniendo ConfigMap: {result.stderr}")
                return None
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            log_error("Timeout obteniendo ConfigMap")
            return None
        except Exception as e:
            log_error(f"Error: {e}")
            return None
    
    def _normalize_content(self, content: str) -> str:
        """Normaliza contenido YAML/JSON para comparación."""
        if not content:
            return ""
        
        if YAML_AVAILABLE:
            try:
                # Parsear YAML
                data = yaml.safe_load(content)
                
                # Remover campos de metadata de K8s
                if isinstance(data, dict):
                    if "metadata" in data:
                        for key in ["resourceVersion", "uid", "creationTimestamp",
                                    "managedFields", "annotations", "namespace"]:
                            data.get("metadata", {}).pop(key, None)
                
                # Serializar de forma ordenada
                return json.dumps(data, sort_keys=True, separators=(",", ":"))
                
            except Exception:
                pass
        
        # Fallback: limpiar espacios y ordenar líneas
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        return "\n".join(sorted(lines))


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
class ValidatorConfig:
    """Configuración del validador."""
    
    def __init__(self):
        # Azure DevOps
        self.pat = os.environ.get("PAT", "")
        self.org_name = os.environ.get("ORG_NAME", "")
        self.project_name = os.environ.get("PROJECT_NAME", "")
        self.release_id = os.environ.get("ACTUAL_RELEASE_ID", "")
        self.api_version = os.environ.get("API_VERSION", "7.1")
        
        # Imágenes
        self.image_actual = os.environ.get("IMAGE_ACTUAL", "")
        self.image_nueva = os.environ.get("IMAGE_NUEVA", "")
        self.gcp_project_id = os.environ.get("GCP_PROJECT_ID", "")
        
        # Credenciales
        self.group_id = os.environ.get("GROUP_ID", "")
        self.sa_key_file = os.environ.get("SA_KEY_FILE", "")
        
        # ConfigMap
        self.artifact_name = os.environ.get("ARTIFACT_NAME", "")
        self.artifact_namespace = os.environ.get("ARTIFACT_NAMESPACE", "")
        self.repo_name = os.environ.get("REPO_NAME", "properties")
        self.branch = os.environ.get("BRANCH", "master")
        
        # Derivar de variables de sistema Azure DevOps
        self._derive_from_system_vars()
    
    def _derive_from_system_vars(self):
        """Deriva variables desde variables de sistema de Azure DevOps."""
        if not self.org_name:
            collection_uri = os.environ.get("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI", "")
            if collection_uri:
                parts = collection_uri.rstrip("/").split("/")
                if len(parts) >= 4:
                    self.org_name = parts[3]
        
        if not self.project_name:
            self.project_name = os.environ.get("SYSTEM_TEAMPROJECT", "")
        
        if not self.release_id:
            self.release_id = os.environ.get("RELEASE_RELEASEID", "")
    
    def validate_required(self, fields: List[str]) -> bool:
        """Valida que los campos requeridos estén presentes."""
        missing = []
        for field in fields:
            value = getattr(self, field, None)
            if not value or value == "null":
                missing.append(field)
        
        if missing:
            log_error(f"Variables requeridas faltantes: {', '.join(missing)}")
            return False
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════
def get_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Azure DevOps Task Validator - DevSecOps Release Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Validar imágenes
  python azdo_task_validator.py --validate-images --image-actual us-docker.pkg.dev/proj/repo/img:v1.0 --image-nueva us-docker.pkg.dev/proj/repo/img:v1.1

  # Buscar release rollback
  python azdo_task_validator.py --find-rollback --release-id 123 --tag v1.0.0

  # Validar credenciales
  python azdo_task_validator.py --validate-credentials --group-id 456 --rollback-release-id 789

  # Comparar ConfigMap
  python azdo_task_validator.py --compare-configmap --artifact-name mi-servicio --namespace prod

  # Ejecutar todas las validaciones
  python azdo_task_validator.py --all
        """
    )
    
    # Modos de operación
    parser.add_argument("--all", action="store_true",
                        help="Ejecuta todas las validaciones")
    parser.add_argument("--validate-images", action="store_true",
                        help="Valida existencia de imágenes Docker")
    parser.add_argument("--find-rollback", action="store_true",
                        help="Busca release de rollback por TAG")
    parser.add_argument("--validate-credentials", action="store_true",
                        help="Valida vigencia de credenciales GIT")
    parser.add_argument("--compare-configmap", action="store_true",
                        help="Compara ConfigMap de K8s vs repositorio")
    
    # Azure DevOps
    parser.add_argument("--pat", type=str, help="Personal Access Token")
    parser.add_argument("--org", type=str, help="Organización Azure DevOps")
    parser.add_argument("--project", type=str, help="Proyecto Azure DevOps")
    parser.add_argument("--release-id", type=int, help="ID del release actual")
    parser.add_argument("--api-version", type=str, default="7.1", help="Versión de API")
    
    # Imágenes
    parser.add_argument("--image-actual", type=str, help="Imagen actual desplegada")
    parser.add_argument("--image-nueva", type=str, help="Imagen nueva a desplegar")
    parser.add_argument("--gcp-project", type=str, help="Proyecto GCP")
    parser.add_argument("--sa-key-file", type=str, help="Archivo de credenciales Service Account")
    
    # Rollback
    parser.add_argument("--tag", type=str, help="TAG a buscar para rollback")
    parser.add_argument("--rollback-release-id", type=int, help="ID del release rollback encontrado")
    
    # Credenciales
    parser.add_argument("--group-id", type=int, help="ID del Variable Group")
    
    # ConfigMap
    parser.add_argument("--artifact-name", type=str, help="Nombre del artefacto/servicio")
    parser.add_argument("--namespace", type=str, help="Namespace de K8s")
    parser.add_argument("--repo-name", type=str, default="properties", help="Nombre del repositorio")
    parser.add_argument("--branch", type=str, default="master", help="Rama del repositorio")
    
    # Opciones generales
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv"],
                        help="Exportar resultados")
    parser.add_argument("--help-full", action="store_true",
                        help="Muestra ayuda completa")
    
    return parser.parse_args()


def show_help():
    """Muestra ayuda completa."""
    script_dir = Path(__file__).parent
    readme_path = script_dir / "README_task_validator.md"
    
    if readme_path.exists():
        if RICH_AVAILABLE and console:
            from rich.markdown import Markdown
            with open(readme_path, "r", encoding="utf-8") as f:
                console.print(Markdown(f.read()))
        else:
            with open(readme_path, "r", encoding="utf-8") as f:
                print(f.read())
    else:
        print("README no encontrado. Use --help para ver opciones disponibles.")


def export_results(results: Dict, output_format: str, filename: str = "validation_results"):
    """Exporta resultados a archivo."""
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        output_path = OUTCOME_DIR / f"{filename}_{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        output_path = OUTCOME_DIR / f"{filename}_{timestamp}.csv"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("step,status,message\n")
            for step, data in results.get("steps", {}).items():
                f.write(f"{step},{data.get('status', 'unknown')},{data.get('message', '')}\n")
    
    log_info(f"Resultados exportados a: {output_path}")


def main():
    """Función principal."""
    args = get_args()
    
    if args.help_full:
        show_help()
        return 0
    
    # Verificar dependencias
    if not REQUESTS_AVAILABLE:
        log_error("Módulo 'requests' no disponible. Instalar con: pip install requests")
        return 1
    
    # Cargar configuración desde env + args
    config = ValidatorConfig()
    
    # Sobreescribir con argumentos CLI si se proporcionan
    if args.pat:
        config.pat = args.pat
    if args.org:
        config.org_name = args.org
    if args.project:
        config.project_name = args.project
    if args.release_id:
        config.release_id = str(args.release_id)
    if args.api_version:
        config.api_version = args.api_version
    if args.image_actual:
        config.image_actual = args.image_actual
    if args.image_nueva:
        config.image_nueva = args.image_nueva
    if args.gcp_project:
        config.gcp_project_id = args.gcp_project
    if args.sa_key_file:
        config.sa_key_file = args.sa_key_file
    if args.group_id:
        config.group_id = str(args.group_id)
    if args.artifact_name:
        config.artifact_name = args.artifact_name
    if args.namespace:
        config.artifact_namespace = args.namespace
    if args.repo_name:
        config.repo_name = args.repo_name
    if args.branch:
        config.branch = args.branch
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "steps": {},
        "overall_status": "success"
    }
    
    # Si no se especifica ningún modo, mostrar ayuda
    if not any([args.all, args.validate_images, args.find_rollback,
                args.validate_credentials, args.compare_configmap]):
        print("Uso: python azdo_task_validator.py [--all | --validate-images | --find-rollback | ...]")
        print("Use --help para ver todas las opciones.")
        return 0
    
    # Validar configuración básica de Azure DevOps
    if not config.validate_required(["pat", "org_name", "project_name"]):
        return 1
    
    # Crear cliente
    client = AzureDevOpsClient(
        config.org_name,
        config.project_name,
        config.pat,
        config.api_version
    )
    
    section("Azure DevOps Task Validator")
    log_info(f"Organización: {config.org_name}")
    log_info(f"Proyecto: {config.project_name}")
    
    rollback_release_id = args.rollback_release_id
    tag_actual = args.tag
    
    # ─────────────────────────────────────────────────────────────────────────
    # 1) Validar imágenes
    # ─────────────────────────────────────────────────────────────────────────
    if args.all or args.validate_images:
        section("1) Validar imágenes")
        
        if not config.validate_required(["image_actual", "image_nueva"]):
            results["steps"]["validate_images"] = {"status": "error", "message": "Imágenes no configuradas"}
            results["overall_status"] = "error"
        else:
            validator = ImageValidator(config.gcp_project_id, args.debug)
            
            # Autenticar si hay SA key
            if config.sa_key_file:
                if not validator.activate_service_account(config.sa_key_file):
                    results["steps"]["validate_images"] = {"status": "error", "message": "Error autenticando"}
                    results["overall_status"] = "error"
            
            # Validar ambas imágenes
            img_actual_ok = validator.check_image_exists(config.image_actual)
            img_nueva_ok = validator.check_image_exists(config.image_nueva)
            
            if img_actual_ok and img_nueva_ok:
                tag_actual = validator.extract_tag(config.image_actual)
                set_azdo_variable("TAG_ACTUAL", tag_actual)
                
                if config.image_actual == config.image_nueva:
                    log_warn("La imagen actual y la nueva son la misma")
                else:
                    log_info("Nueva versión detectada")
                
                results["steps"]["validate_images"] = {
                    "status": "success",
                    "message": "Imágenes validadas",
                    "tag_actual": tag_actual
                }
            else:
                results["steps"]["validate_images"] = {"status": "error", "message": "Imagen(es) no encontrada(s)"}
                results["overall_status"] = "error"
    
    # ─────────────────────────────────────────────────────────────────────────
    # 2) Buscar release rollback
    # ─────────────────────────────────────────────────────────────────────────
    if args.all or args.find_rollback:
        section("2) Buscar Release de Rollback")
        
        if not config.release_id:
            results["steps"]["find_rollback"] = {"status": "error", "message": "release_id no configurado"}
            results["overall_status"] = "error"
        elif not tag_actual:
            results["steps"]["find_rollback"] = {"status": "error", "message": "TAG no disponible"}
            results["overall_status"] = "error"
        else:
            finder = RollbackFinder(client, args.debug)
            rollback_release_id = finder.find_rollback_release(int(config.release_id), tag_actual)
            
            if rollback_release_id:
                set_azdo_variable("RELEASE_ID_RB", str(rollback_release_id))
                client.update_release_variable(int(config.release_id), "RELEASE_ID", str(rollback_release_id))
                
                results["steps"]["find_rollback"] = {
                    "status": "success",
                    "message": f"Release rollback encontrado: {rollback_release_id}",
                    "rollback_release_id": rollback_release_id
                }
            else:
                results["steps"]["find_rollback"] = {"status": "error", "message": "No se encontró release rollback"}
                results["overall_status"] = "error"
    
    # ─────────────────────────────────────────────────────────────────────────
    # 3) Validar credenciales
    # ─────────────────────────────────────────────────────────────────────────
    if args.all or args.validate_credentials:
        section("3) Validar vigencia credenciales GIT")
        
        if not config.group_id:
            results["steps"]["validate_credentials"] = {"status": "error", "message": "group_id no configurado"}
            results["overall_status"] = "error"
        elif not rollback_release_id:
            results["steps"]["validate_credentials"] = {"status": "error", "message": "rollback_release_id no disponible"}
            results["overall_status"] = "error"
        else:
            cred_validator = CredentialValidator(client)
            if cred_validator.validate_credentials(int(config.group_id), rollback_release_id):
                results["steps"]["validate_credentials"] = {"status": "success", "message": "Credenciales vigentes"}
            else:
                results["steps"]["validate_credentials"] = {"status": "error", "message": "Credenciales vencidas"}
                results["overall_status"] = "error"
    
    # ─────────────────────────────────────────────────────────────────────────
    # 4) Comparar ConfigMap
    # ─────────────────────────────────────────────────────────────────────────
    if args.all or args.compare_configmap:
        section("4) Comparar ConfigMap vs Repositorio")
        
        if not config.artifact_name or not config.artifact_namespace:
            results["steps"]["compare_configmap"] = {"status": "error", "message": "artifact no configurado"}
            results["overall_status"] = "error"
        else:
            comparator = ConfigMapComparator(client, args.debug)
            matched_commit = comparator.compare(
                config.artifact_name,
                config.artifact_namespace,
                config.repo_name,
                config.branch
            )
            
            if matched_commit:
                set_azdo_variable("MatchedCommitIdJob", matched_commit)
                set_azdo_variable("ShouldRollbackJob", "true")
                client.update_release_variable(
                    int(config.release_id),
                    "commitPropertiesRollback",
                    matched_commit
                )
                
                results["steps"]["compare_configmap"] = {
                    "status": "success",
                    "message": f"Coincidencia encontrada: {matched_commit}",
                    "matched_commit": matched_commit
                }
            else:
                set_azdo_variable("ShouldRollbackJob", "false")
                results["steps"]["compare_configmap"] = {
                    "status": "warning",
                    "message": "No se encontró coincidencia exacta"
                }
    
    # ─────────────────────────────────────────────────────────────────────────
    # Resultado final
    # ─────────────────────────────────────────────────────────────────────────
    section("RESULTADO FINAL")
    
    if results["overall_status"] == "success":
        log_info("✓ Todas las validaciones completadas exitosamente")
    else:
        log_error("✗ Algunas validaciones fallaron")
    
    # Mostrar resumen
    if RICH_AVAILABLE and console:
        table = Table(title="Resumen de Validaciones", box=box.ROUNDED)
        table.add_column("Paso", style="cyan")
        table.add_column("Estado", justify="center")
        table.add_column("Mensaje", style="dim")
        
        for step, data in results["steps"].items():
            status = data.get("status", "unknown")
            if status == "success":
                status_icon = "[green]✓[/green]"
            elif status == "warning":
                status_icon = "[yellow]⚠[/yellow]"
            else:
                status_icon = "[red]✗[/red]"
            
            table.add_row(step, status_icon, data.get("message", ""))
        
        console.print(table)
    
    # Exportar si se solicita
    if args.output:
        export_results(results, args.output)
    
    return 0 if results["overall_status"] == "success" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        log_error(f"Error inesperado: {e}")
        sys.exit(1)
