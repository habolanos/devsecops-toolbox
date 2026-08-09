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
            org: Organización (URL completa o nombre)
            project: Proyecto
            api_version: Versión de API
        """
        self.pat = pat
        self.org = org
        self.project = project
        self.api_version = api_version

        # Extraer nombre de org si es URL completa
        if org.startswith("https://"):
            org_name = org.split('/')[-1]
            # Transformar dev.azure.com → vsrm.dev.azure.com
            org_base = org.replace("dev.azure.com", "vsrm.dev.azure.com")
            self.base_url = f"{org_base}/{project}"
        else:
            # Si es solo nombre, usar AZDO_BASE_URL
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
    
    def update_release_definition(self, definition_id: int, definition: Dict, comment: Optional[str] = None, disable: bool = False) -> bool:
        """
        Guardar cambios en definición de release
        
        Args:
            definition_id: ID de la definición
            definition: Diccionario con la definición actualizada
            comment: Comentario de la revisión (aparece en el historial de Azure DevOps)
            disable: Si True, setea isDisabled=true en la definicion (disable, no delete)
            
        Returns:
            True si la actualización fue exitosa
        """
        url = f"{self.base_url}/_apis/release/definitions/{definition_id}"
        params = {'api-version': self.api_version}
        
        try:
            # Hacer copia profunda para no modificar el original
            definition_copy = copy.deepcopy(definition)
            
            # NO incrementar la revisión: Azure DevOps usa 'revision' para control
            # de concurrencia optimista. Debe enviarse la MISMA revisión descargada;
            # el servidor la incrementa internamente. Enviar una revisión distinta
            # produce el error "You are using an old copy of the release pipeline".
            
            # Asignar el comentario de la revisión (visible en el historial de AzDO)
            if comment is not None:
                definition_copy['comment'] = comment
            
            # Si se va a deshabilitar, setear isDisabled=true
            if disable:
                definition_copy['isDisabled'] = True
            
            # Remover campos que no deben enviarse en PUT
            # Azure DevOps es estricto con los campos que acepta
            # Nota: isDisabled NO se remueve nunca — debe preservarse
            # para no re-activar pipelines que estaban disabled
            fields_to_remove = [
                '_links', 'url', 'projectReference', 'createdBy', 'createdOn',
                'modifiedBy', 'modifiedOn', 'isDeleted',
                'currentRelease', 'badgeUrl', 'lastRelease'
            ]
            
            for field in fields_to_remove:
                definition_copy.pop(field, None)
            
            response = requests.put(
                url,
                json=definition_copy,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 403:
                raise PermissionDeniedError(f"Permiso denegado para actualizar pipeline {definition_id}")
            
            if response.status_code >= 400:
                error_body = response.text[:2000]
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
    
    def delete_release_definition(self, definition_id: int) -> bool:
        """
        Eliminar (soft-delete) una definición de release.

        Azure DevOps marca la definición como eliminada. No aparece en la UI
        pero puede ser restaurada si es necesario.

        Args:
            definition_id: ID de la definición a eliminar

        Returns:
            True si la eliminación fue exitosa
        """
        url = f"{self.base_url}/_apis/release/definitions/{definition_id}"
        params = {'api-version': self.api_version}

        try:
            response = requests.delete(
                url,
                params=params,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 404:
                raise PipelineNotFoundError(f"Pipeline {definition_id} no encontrado")
            elif response.status_code == 403:
                raise PermissionDeniedError(f"Permiso denegado para eliminar pipeline {definition_id}")

            if response.status_code >= 400:
                error_body = response.text[:2000]
                raise AzureDevOpsError(
                    f"Error al eliminar definición {definition_id} "
                    f"(HTTP {response.status_code}): {error_body}"
                )

            response.raise_for_status()
            return True
        except requests.RequestException as e:
            raise AzureDevOpsError(f"Error al eliminar definición: {str(e)}")

    def variable_group_exists(self, group_id: int) -> bool:
        """
        Verifica si un variable group existe en el proyecto.
        
        Args:
            group_id: ID del variable group
            
        Returns:
            True si existe, False si no
        """
        # Variable groups usan la API regular (no vsrm)
        base_url = self.base_url.replace("vsrm.dev.azure.com", "dev.azure.com")
        url = f"{base_url}/_apis/distributedtask/variablegroups/{group_id}"
        params = {'api-version': self.api_version}
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False

    def agent_pool_exists(self, pool_id: int) -> bool:
        """
        Verifica si un agent pool (queue) existe en el proyecto.

        Args:
            pool_id: ID del agent pool (queueId en la definicion)

        Returns:
            True si existe, False si no
        """
        base_url = self.base_url.replace("vsrm.dev.azure.com", "dev.azure.com")
        url = f"{base_url}/_apis/distributedtask/queues/{pool_id}"
        params = {'api-version': self.api_version}

        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False
