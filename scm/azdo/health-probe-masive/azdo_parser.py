"""
AZDO Parser - Extrae información de releases y stages desde Azure DevOps
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from .config import (
    AZDO_BASE_URL, AZDO_ORG, AZDO_PAT, AZDO_PROJECT,
    AZDO_API_VERSION, CACHE_TTL, MAX_RETRIES, BACKOFF_FACTOR, OUTPUT_DIR
)
from .models import DeploymentInput, StageInfo

logger = logging.getLogger(__name__)


class AzDOParser:
    """Parser para Azure DevOps REST API"""
    
    def __init__(self, org: str = AZDO_ORG, project: str = AZDO_PROJECT, pat: str = AZDO_PAT):
        self.org = org
        self.project = project
        self.pat = pat
        self.session = self._create_session()
        self.cache_dir = os.path.join(OUTPUT_DIR, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _create_session(self) -> requests.Session:
        """Crea sesión autenticada con AZDO"""
        session = requests.Session()
        auth = HTTPBasicAuth("", self.pat)
        session.auth = auth
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def _retry_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Realiza request con reintentos exponenciales"""
        for attempt in range(MAX_RETRIES):
            try:
                response = getattr(self.session, method)(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Request failed after {MAX_RETRIES} attempts: {e}")
                    raise
                wait_time = BACKOFF_FACTOR ** attempt
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    
    def _get_cache_path(self, definition_id: int) -> str:
        """Obtiene ruta de caché para una definición"""
        return os.path.join(self.cache_dir, f"azdo_release_{definition_id}.json")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """Verifica si caché es válido (< 24h)"""
        if not os.path.exists(cache_path):
            return False
        
        file_time = os.path.getmtime(cache_path)
        file_age = time.time() - file_time
        return file_age < CACHE_TTL
    
    def _load_from_cache(self, definition_id: int) -> Optional[Dict]:
        """Carga definición desde caché"""
        cache_path = self._get_cache_path(definition_id)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    logger.info(f"Loaded definition {definition_id} from cache")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        
        return None
    
    def _save_to_cache(self, definition_id: int, data: Dict):
        """Guarda definición en caché"""
        cache_path = self._get_cache_path(definition_id)
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
                logger.info(f"Cached definition {definition_id}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def get_release_definition(self, definition_id: int) -> Dict:
        """
        Obtiene definición de release desde AZDO
        
        GET /_apis/release/definitions/{definitionId}
        """
        # Intentar caché primero
        cached = self._load_from_cache(definition_id)
        if cached:
            return cached
        
        url = f"{AZDO_BASE_URL}/{self.org}/{self.project}/_apis/release/definitions/{definition_id}"
        params = {"api-version": AZDO_API_VERSION}
        
        logger.info(f"Fetching release definition {definition_id}")
        response = self._retry_request("get", url, params=params)
        data = response.json()
        
        # Guardar en caché
        self._save_to_cache(definition_id, data)
        
        return data
    
    def get_stages(self, definition_id: int) -> List[StageInfo]:
        """
        Extrae stages de una definición de release
        """
        definition = self.get_release_definition(definition_id)
        stages = []
        
        for env in definition.get("environments", []):
            stage = StageInfo(
                name=env.get("name", "Unknown"),
                definition_id=definition_id,
                target_deployment=self._extract_deployment_name(env),
                target_namespace=self._extract_namespace(env),
                endpoints=self._extract_endpoints(env),
                ports=self._extract_ports(env),
                environment=self._classify_environment(env.get("name", ""))
            )
            stages.append(stage)
            logger.debug(f"Extracted stage: {stage.name}")
        
        return stages
    
    def _extract_deployment_name(self, environment: Dict) -> str:
        """Extrae nombre de deployment del environment"""
        # Buscar en deployment input
        deploy_input = environment.get("deploymentInput", {})
        
        # Intentar obtener del nombre del environment
        env_name = environment.get("name", "").lower()
        
        # Patrones comunes
        if "web" in env_name:
            return "deployment-web"
        elif "api" in env_name:
            return "deployment-api"
        elif "db" in env_name:
            return "deployment-db"
        elif "cache" in env_name:
            return "deployment-cache"
        else:
            return f"deployment-{env_name}"
    
    def _extract_namespace(self, environment: Dict) -> str:
        """Extrae namespace K8s del environment"""
        env_name = environment.get("name", "").lower()
        
        if "prod" in env_name:
            return "production"
        elif "staging" in env_name or "stage" in env_name:
            return "staging"
        elif "qa" in env_name or "test" in env_name:
            return "qa"
        else:
            return "default"
    
    def _extract_endpoints(self, environment: Dict) -> List[str]:
        """Extrae endpoints del environment"""
        endpoints = []
        
        # Buscar en deployment input
        deploy_input = environment.get("deploymentInput", {})
        
        # Buscar URLs en variables
        for key, value in deploy_input.items():
            if isinstance(value, str) and ("http" in value or "." in value):
                endpoints.append(value)
        
        # Si no hay endpoints, generar basado en nombre
        env_name = environment.get("name", "").lower()
        if not endpoints:
            if "prod" in env_name:
                endpoints.append("api.production.internal")
            elif "staging" in env_name:
                endpoints.append("api.staging.internal")
            else:
                endpoints.append(f"api.{env_name}.internal")
        
        return endpoints
    
    def _extract_ports(self, environment: Dict) -> List[int]:
        """Extrae puertos del environment"""
        ports = [8080, 443]  # Puertos por defecto
        
        deploy_input = environment.get("deploymentInput", {})
        for key, value in deploy_input.items():
            if isinstance(value, int) and 1 <= value <= 65535:
                if value not in ports:
                    ports.append(value)
        
        return ports
    
    def _classify_environment(self, env_name: str) -> str:
        """Clasifica el tipo de environment"""
        env_lower = env_name.lower()
        
        if "prod" in env_lower:
            return "Prod"
        elif "staging" in env_lower or "stage" in env_lower:
            return "Staging"
        elif "qa" in env_lower or "test" in env_lower:
            return "QA"
        elif "dev" in env_lower:
            return "Dev"
        else:
            return env_name


def parse_input(input_str: str) -> List[DeploymentInput]:
    """
    Parsea entrada CSV de deployments o definition IDs
    
    Ejemplos:
      "deployment-web-prod,deployment-api-prod"
      "definitionId=3388,definitionId=3389"
      "3388,3389,3390"
    """
    items = input_str.split(",")
    results = []
    
    for item in items:
        item = item.strip()
        
        if item.startswith("definitionId="):
            def_id = int(item.split("=")[1])
            results.append(DeploymentInput(
                definition_id=def_id,
                name=f"release_{def_id}"
            ))
        elif item.isdigit():
            def_id = int(item)
            results.append(DeploymentInput(
                definition_id=def_id,
                name=f"release_{def_id}"
            ))
        else:
            results.append(DeploymentInput(name=item))
    
    return results
