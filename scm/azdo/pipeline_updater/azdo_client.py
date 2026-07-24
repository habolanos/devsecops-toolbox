"""
Cliente de Azure DevOps para Pipeline Updater
"""

import requests
import json
import base64
import copy
from pathlib import Path
from typing import Dict, Optional
from .config import AZDO_API_VERSION, AZDO_BASE_URL, SNAPSHOT_DIR


class AzureDevOpsError(Exception):
    """Error general de Azure DevOps"""
    pass


class PipelineNotFoundError(AzureDevOpsError):
    """Pipeline no encontrado"""
    pass


class PermissionDeniedError(AzureDevOpsError):
    """Permiso denegado"""
    pass


class AzureDevOpsClient:
    """Cliente REST para Azure DevOps Release API"""
    
    def __init__(self, pat: str, org: str, project: str, api_version: str = AZDO_API_VERSION):
        """
        Inicializar cliente
        
        Args:
            pat: Personal Access Token
            org: Organización
            project: Proyecto
            api_version: Versión de API
        """
        self.pat = pat
        self.org = org
        self.project = project
        self.api_version = api_version
        self.base_url = f"{AZDO_BASE_URL}/{org}/{project}"
        self.headers = self._get_headers()
        
        # Crear directorio de snapshots
        Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)
    
    def _get_headers(self) -> Dict:
        """Obtener headers con autenticación"""
        auth_string = base64.b64encode(f":{self.pat}".encode()).decode()
        return {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json'
        }
    
    def get_release_definition(self, definition_id: int) -> Dict:
        """
        Descargar definición de release
        
        Args:
            definition_id: ID de la definición
            
        Returns:
            Diccionario con la definición
        """
        url = f"{self.base_url}/_apis/release/definitions/{definition_id}"
        params = {'api-version': self.api_version}
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 404:
                raise PipelineNotFoundError(f"Pipeline {definition_id} no encontrado")
            elif response.status_code == 403:
                raise PermissionDeniedError(f"Permiso denegado para pipeline {definition_id}")
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise AzureDevOpsError(f"Error al obtener definición: {str(e)}")
    
    def update_release_definition(self, definition_id: int, definition: Dict) -> bool:
        """
        Guardar cambios en definición de release
        
        Args:
            definition_id: ID de la definición
            definition: Diccionario con la definición actualizada
            
        Returns:
            True si la actualización fue exitosa
        """
        url = f"{self.base_url}/_apis/release/definitions/{definition_id}"
        params = {'api-version': self.api_version}
        
        try:
            # Hacer copia profunda para no modificar el original
            definition_copy = copy.deepcopy(definition)
            
            # Incrementar revisión para que Azure DevOps acepte el cambio
            if 'revision' in definition_copy:
                old_revision = definition_copy['revision']
                definition_copy['revision'] = definition_copy.get('revision', 0) + 1
                print(f"    [DEBUG] Revisión incrementada: {old_revision} → {definition_copy['revision']}")
            
            # Remover campos que no deben enviarse en PUT
            # Azure DevOps es estricto con los campos que acepta
            fields_to_remove = [
                '_links', 'url', 'projectReference', 'createdBy', 'createdOn',
                'modifiedBy', 'modifiedOn', 'isDeleted', 'isDisabled',
                'currentRelease', 'badgeUrl', 'lastRelease'
            ]
            
            for field in fields_to_remove:
                definition_copy.pop(field, None)
            
            print(f"    [DEBUG] Campos principales en JSON: {list(definition_copy.keys())}")
            print(f"    [DEBUG] Tamaño del JSON: {len(json.dumps(definition_copy))} bytes")
            
            response = requests.put(
                url,
                json=definition_copy,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            print(f"    [DEBUG] Response status: {response.status_code}")
            
            if response.status_code == 403:
                raise PermissionDeniedError(f"Permiso denegado para actualizar pipeline {definition_id}")
            
            if response.status_code >= 400:
                error_body = response.text[:2000]
                print(f"    [DEBUG] Response body: {error_body}")
                raise AzureDevOpsError(
                    f"Error al actualizar definición {definition_id} "
                    f"(HTTP {response.status_code}): {error_body}"
                )
            
            response.raise_for_status()
            return response.status_code == 200
        except requests.RequestException as e:
            raise AzureDevOpsError(f"Error al actualizar definición: {str(e)}")
    
    def create_snapshot(self, definition_id: int, definition: Dict) -> str:
        """
        Crear snapshot para rollback
        
        Args:
            definition_id: ID de la definición
            definition: Diccionario con la definición
            
        Returns:
            ID del snapshot
        """
        import time
        snapshot_id = f"snapshot_{definition_id}_{int(time.time())}"
        snapshot_path = Path(SNAPSHOT_DIR) / f"{snapshot_id}.json"
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(definition, f, indent=2)
        
        return snapshot_id
    
    def rollback(self, definition_id: int, snapshot_id: str) -> bool:
        """
        Revertir a snapshot
        
        Args:
            definition_id: ID de la definición
            snapshot_id: ID del snapshot
            
        Returns:
            True si el rollback fue exitoso
        """
        snapshot_path = Path(SNAPSHOT_DIR) / f"{snapshot_id}.json"
        
        if not snapshot_path.exists():
            raise AzureDevOpsError(f"Snapshot no encontrado: {snapshot_id}")
        
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            definition = json.load(f)
        
        return self.update_release_definition(definition_id, definition)
    
    def list_release_definitions(self, top: int = 50) -> Dict:
        """
        Listar definiciones de release
        
        Args:
            top: Número máximo de resultados
            
        Returns:
            Diccionario con lista de definiciones
        """
        url = f"{self.base_url}/_apis/release/definitions"
        params = {'api-version': self.api_version, '$top': top}
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise AzureDevOpsError(f"Error al listar definiciones: {str(e)}")
