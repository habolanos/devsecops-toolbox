#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Pipeline Rollback Tool

Revierte cambios aplicados por update-pipeline-cd-branchconfig.py
usando backups locales o revisiones de Azure DevOps.

Uso:
    # Rollback desde backup local
    python rollback-pipeline.py --backup-file outcome/backups/pipeline_2758_backup_20260618_153645.json --pat YOUR_PAT
    
    # Rollback a revisión específica
    python rollback-pipeline.py --pipeline-id 2758 --to-revision 42 --org Coppel-Retail --project Cadena_de_Suministros --pat YOUR_PAT
    
    # Listar backups disponibles
    python rollback-pipeline.py --list-backups
    
    # Modo interactivo
    python rollback-pipeline.py --interactive
"""

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Dict, Optional
import urllib.request
import urllib.error
import os

__version__ = "1.2.0"
__author__ = "Harold Adrian"

# ═══════════════════════════════════════════════════════════════════════════════
# COLORES PARA TERMINAL
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    
    # Aliases para compatibilidad
    CYAN = OKCYAN
    GREEN = OKGREEN
    YELLOW = WARNING
    RED = FAIL

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def create_auth_header(pat: str) -> str:
    """Crea el header de autenticación para Azure DevOps API."""
    token = base64.b64encode(f":{pat}".encode('utf-8')).decode('utf-8')
    return f"Basic {token}"


def load_backup_file(backup_file: str) -> Dict:
    """
    Carga un archivo de backup y valida su estructura.
    
    Args:
        backup_file: Ruta al archivo de backup
        
    Returns:
        Dict con los datos del backup
    """
    if not os.path.exists(backup_file):
        print(f"{Colors.RED}✗ Error: Archivo de backup no encontrado: {backup_file}{Colors.ENDC}")
        sys.exit(1)
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Validar estructura
        if 'backup_metadata' not in backup_data or 'pipeline_definition' not in backup_data:
            print(f"{Colors.RED}✗ Error: Estructura de backup inválida{Colors.ENDC}")
            sys.exit(1)
        
        return backup_data
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}✗ Error al parsear JSON: {e}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error al cargar backup: {e}{Colors.ENDC}")
        sys.exit(1)


def get_release_definition(org: str, project: str, definition_id: int, pat: str) -> Dict:
    """Obtiene la definición actual de un Release Pipeline."""
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{definition_id}?api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def get_pipeline_revision(org: str, project: str, definition_id: int, revision: int, pat: str) -> Dict:
    """
    Obtiene una revisión específica de un Release Pipeline.
    
    Args:
        org: Nombre de la organización
        project: Nombre del proyecto
        definition_id: ID del Release Pipeline
        revision: Número de revisión a obtener
        pat: Personal Access Token
        
    Returns:
        Dict con la definición de la revisión especificada
    """
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{definition_id}?revision={revision}&api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def list_pipeline_revisions(org: str, project: str, definition_id: int, pat: str, max_revisions: int = 10):
    """
    Lista las últimas revisiones de un pipeline.
    
    Args:
        org: Nombre de la organización
        project: Nombre del proyecto
        definition_id: ID del Release Pipeline
        pat: Personal Access Token
        max_revisions: Número máximo de revisiones a mostrar
    """
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Últimas Revisiones del Pipeline {definition_id}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    # Obtener definición actual para saber cuántas revisiones hay
    current_def = get_release_definition(org, project, definition_id, pat)
    current_revision = current_def.get('revision', 1)
    
    print(f"{Colors.CYAN}Revisión actual: {current_revision}{Colors.ENDC}\n")
    
    # Listar últimas N revisiones
    start_revision = max(1, current_revision - max_revisions + 1)
    
    for rev in range(current_revision, start_revision - 1, -1):
        try:
            rev_def = get_pipeline_revision(org, project, definition_id, rev, pat)
            modified_by = rev_def.get('modifiedBy', {}).get('displayName', 'Unknown')
            modified_on = rev_def.get('modifiedOn', 'Unknown')
            comment = rev_def.get('comment', 'No comment')
            
            marker = " ← ACTUAL" if rev == current_revision else ""
            print(f"{Colors.GREEN if rev == current_revision else Colors.CYAN}Revisión {rev}{marker}{Colors.ENDC}")
            print(f"  Modificado por: {modified_by}")
            print(f"  Fecha: {modified_on}")
            print(f"  Comentario: {comment}")
            print()
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ No se pudo obtener revisión {rev}: {e}{Colors.ENDC}\n")


def restore_pipeline_definition(org: str, project: str, definition_id: int, pat: str, definition: Dict) -> Dict:
    """
    Restaura la definición de un Release Pipeline.
    
    Args:
        org: Nombre de la organización
        project: Nombre del proyecto
        definition_id: ID del Release Pipeline
        pat: Personal Access Token
        definition: Definición a restaurar
        
    Returns:
        Dict con la respuesta del servidor
    """
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{definition_id}?api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    # Agregar comentario de rollback
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    definition['comment'] = f"[Rollback - {timestamp}] Restored from backup"
    
    print(f"{Colors.CYAN}>>> Restaurando definición del pipeline...{Colors.ENDC}")
    
    try:
        body = json.dumps(definition).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method='PUT')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}>>> Pipeline restaurado exitosamente.{Colors.ENDC}")
            print(f"{Colors.GREEN}  Revision: {data.get('revision', 'N/A')}{Colors.ENDC}")
            
            if '_links' in data and 'self' in data['_links']:
                print(f"{Colors.CYAN}  URL: {data['_links']['self'].get('href', 'N/A')}{Colors.ENDC}")
            
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def list_available_backups(directory: str = "outcome/backups"):
    """Lista todos los backups disponibles."""
    if not os.path.exists(directory):
        print(f"{Colors.YELLOW}⚠ No se encontró el directorio de backups: {directory}{Colors.ENDC}")
        return
    
    backup_files = sorted([f for f in os.listdir(directory) if f.endswith('.json')], reverse=True)
    
    if not backup_files:
        print(f"{Colors.YELLOW}⚠ No se encontraron backups en {directory}{Colors.ENDC}")
        return
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Backups Disponibles{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    for backup_file in backup_files:
        filepath = os.path.join(directory, backup_file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
                metadata = backup_data.get('backup_metadata', {})
                
                print(f"{Colors.CYAN}📄 {backup_file}{Colors.ENDC}")
                print(f"   Pipeline ID: {metadata.get('pipeline_id', 'N/A')}")
                print(f"   Pipeline Name: {metadata.get('pipeline_name', 'N/A')}")
                print(f"   Backup Date: {metadata.get('backup_timestamp', 'N/A')}")
                print(f"   Original Revision: {metadata.get('original_revision', 'N/A')}")
                print(f"   Tool Version: {metadata.get('tool_version', 'N/A')}")
                print()
        except Exception as e:
            print(f"{Colors.RED}✗ Error al leer {backup_file}: {e}{Colors.ENDC}\n")


def rollback_from_backup(backup_file: str, pat: str, dry_run: bool = False):
    """
    Realiza rollback desde un archivo de backup.
    
    Args:
        backup_file: Ruta al archivo de backup
        pat: Personal Access Token
        dry_run: Si es True, solo simula el rollback
    """
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Rollback v{__version__}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    # Cargar backup
    print(f"{Colors.CYAN}>>> Cargando backup: {backup_file}{Colors.ENDC}")
    backup_data = load_backup_file(backup_file)
    
    metadata = backup_data['backup_metadata']
    definition = backup_data['pipeline_definition']
    
    print(f"{Colors.GREEN}✓ Backup cargado exitosamente{Colors.ENDC}")
    print(f"\n{Colors.CYAN}Información del backup:{Colors.ENDC}")
    print(f"  Pipeline ID: {metadata['pipeline_id']}")
    print(f"  Pipeline Name: {metadata['pipeline_name']}")
    print(f"  Backup Date: {metadata['backup_timestamp']}")
    print(f"  Original Revision: {metadata['original_revision']}")
    
    # Extraer org y project de la definición
    org = definition.get('_links', {}).get('self', {}).get('href', '').split('/')[3] if '_links' in definition else None
    project = definition.get('projectReference', {}).get('name', None)
    
    if not org or not project:
        print(f"{Colors.RED}✗ No se pudo extraer organización o proyecto del backup{Colors.ENDC}")
        print(f"{Colors.YELLOW}  Usa --org y --project para especificarlos manualmente{Colors.ENDC}")
        sys.exit(1)
    
    print(f"  Organización: {org}")
    print(f"  Proyecto: {project}")
    
    # Obtener definición actual
    print(f"\n{Colors.CYAN}>>> Obteniendo definición actual del pipeline...{Colors.ENDC}")
    current_definition = get_release_definition(org, project, metadata['pipeline_id'], pat)
    current_revision = current_definition.get('revision', 'N/A')
    print(f"{Colors.GREEN}✓ Definición actual obtenida (Revision: {current_revision}){Colors.ENDC}")
    
    # Confirmación
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⚠  CONFIRMACIÓN DE ROLLBACK{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"Estás a punto de revertir el pipeline {Colors.BOLD}{metadata['pipeline_id']}{Colors.ENDC}")
    print(f"  Revisión actual: {current_revision}")
    print(f"  Revisión del backup: {metadata['original_revision']}")
    if not dry_run:
        print(f"{Colors.RED}Los cambios se aplicarán INMEDIATAMENTE y serán PERMANENTES{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Modo DRY-RUN: Solo se simulará el rollback{Colors.ENDC}")
    
    confirm = input(f"\n{Colors.BOLD}¿Deseas continuar? (escribe 'SI' para confirmar): {Colors.ENDC}").strip()
    
    if confirm != 'SI':
        print(f"\n{Colors.YELLOW}✗ Rollback cancelado por el usuario{Colors.ENDC}")
        return 0
    
    print(f"\n{Colors.GREEN}✓ Confirmación recibida. Iniciando rollback...{Colors.ENDC}\n")
    
    # Realizar rollback
    if dry_run:
        print(f"{Colors.YELLOW}>>> Modo DRY-RUN: Cambios NO aplicados{Colors.ENDC}")
        print(f"{Colors.CYAN}  Se restauraría la definición del backup{Colors.ENDC}")
        print(f"{Colors.CYAN}  Revisión objetivo: {metadata['original_revision']}{Colors.ENDC}")
    else:
        response = restore_pipeline_definition(org, project, metadata['pipeline_id'], pat, definition)
        print(f"\n{Colors.GREEN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.GREEN}  ✓ Rollback completado exitosamente{Colors.ENDC}")
        print(f"{Colors.GREEN}{'='*70}{Colors.ENDC}\n")
    
    return 0


def rollback_hybrid(backup_file: str, pat: str, dry_run: bool = False):
    """
    Rollback híbrido: usa la revisión guardada en el backup para revertir
    directamente a esa revisión en Azure DevOps (sin restaurar el backup completo).
    
    Args:
        backup_file: Ruta al archivo de backup
        pat: Personal Access Token
        dry_run: Si es True, solo simula el rollback
    """
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Rollback v{__version__} (MODO HÍBRIDO){Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    # Cargar backup para obtener metadata
    print(f"{Colors.CYAN}>>> Cargando metadata del backup: {backup_file}{Colors.ENDC}")
    backup_data = load_backup_file(backup_file)
    
    metadata = backup_data['backup_metadata']
    definition = backup_data['pipeline_definition']
    
    print(f"{Colors.GREEN}✓ Metadata cargada exitosamente{Colors.ENDC}")
    
    # Extraer información
    pipeline_id = metadata['pipeline_id']
    target_revision = metadata['original_revision']
    
    # Extraer org y project de la definición
    org = definition.get('_links', {}).get('self', {}).get('href', '').split('/')[3] if '_links' in definition else None
    project = definition.get('projectReference', {}).get('name', None)
    
    if not org or not project:
        print(f"{Colors.RED}✗ No se pudo extraer organización o proyecto del backup{Colors.ENDC}")
        sys.exit(1)
    
    print(f"\n{Colors.CYAN}Información del backup:{Colors.ENDC}")
    print(f"  Pipeline ID: {pipeline_id}")
    print(f"  Pipeline Name: {metadata['pipeline_name']}")
    print(f"  Backup Date: {metadata['backup_timestamp']}")
    print(f"  Revisión objetivo: {target_revision}")
    print(f"  Organización: {org}")
    print(f"  Proyecto: {project}")
    
    # Obtener definición actual
    print(f"\n{Colors.CYAN}>>> Obteniendo definición actual del pipeline...{Colors.ENDC}")
    current_definition = get_release_definition(org, project, pipeline_id, pat)
    current_revision = current_definition.get('revision', 'N/A')
    print(f"{Colors.GREEN}✓ Definición actual obtenida (Revision: {current_revision}){Colors.ENDC}")
    
    # Validar que la revisión objetivo existe y es anterior
    if target_revision >= current_revision:
        print(f"{Colors.YELLOW}⚠ La revisión del backup ({target_revision}) no es anterior a la actual ({current_revision}){Colors.ENDC}")
        print(f"{Colors.CYAN}  Usando rollback desde backup completo en su lugar...{Colors.ENDC}")
        return rollback_from_backup(backup_file, pat, dry_run)
    
    # Obtener definición de la revisión objetivo desde Azure DevOps
    print(f"\n{Colors.CYAN}>>> Obteniendo revisión {target_revision} desde Azure DevOps...{Colors.ENDC}")
    target_definition = get_pipeline_revision(org, project, pipeline_id, target_revision, pat)
    print(f"{Colors.GREEN}✓ Revisión {target_revision} obtenida desde Azure DevOps{Colors.ENDC}")
    
    # Mostrar información de la revisión
    print(f"\n{Colors.CYAN}Información de la revisión objetivo:{Colors.ENDC}")
    print(f"  Modificado por: {target_definition.get('modifiedBy', {}).get('displayName', 'Unknown')}")
    print(f"  Fecha: {target_definition.get('modifiedOn', 'Unknown')}")
    print(f"  Comentario: {target_definition.get('comment', 'No comment')}")
    
    # Confirmación
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⚠  CONFIRMACIÓN DE ROLLBACK HÍBRIDO{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"Estás a punto de revertir el pipeline {Colors.BOLD}{pipeline_id}{Colors.ENDC}")
    print(f"  Método: Rollback híbrido (revisión de Azure DevOps)")
    print(f"  Revisión actual: {current_revision}")
    print(f"  Revisión objetivo: {target_revision} (desde backup)")
    print(f"  Backup de referencia: {backup_file}")
    if not dry_run:
        print(f"{Colors.RED}Los cambios se aplicarán INMEDIATAMENTE y serán PERMANENTES{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Modo DRY-RUN: Solo se simulará el rollback{Colors.ENDC}")
    
    confirm = input(f"\n{Colors.BOLD}¿Deseas continuar? (escribe 'SI' para confirmar): {Colors.ENDC}").strip()
    
    if confirm != 'SI':
        print(f"\n{Colors.YELLOW}✗ Rollback cancelado por el usuario{Colors.ENDC}")
        return 0
    
    print(f"\n{Colors.GREEN}✓ Confirmación recibida. Iniciando rollback híbrido...{Colors.ENDC}\n")
    
    # Realizar rollback
    if dry_run:
        print(f"{Colors.YELLOW}>>> Modo DRY-RUN: Cambios NO aplicados{Colors.ENDC}")
        print(f"{Colors.CYAN}  Se restauraría la revisión {target_revision} desde Azure DevOps{Colors.ENDC}")
    else:
        # Modificar el comentario para indicar rollback híbrido
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_definition['comment'] = f"[Rollback Híbrido - {timestamp}] Reverted to revision {target_revision} (from backup {backup_file})"
        
        response = restore_pipeline_definition(org, project, pipeline_id, pat, target_definition)
        print(f"\n{Colors.GREEN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.GREEN}  ✓ Rollback híbrido completado exitosamente{Colors.ENDC}")
        print(f"{Colors.GREEN}{'='*70}{Colors.ENDC}\n")
    
    return 0


def rollback_to_revision(pipeline_id: int, to_revision: int, org: str, project: str, pat: str, dry_run: bool = False):
    """
    Realiza rollback a una revisión específica de Azure DevOps.
    
    Args:
        pipeline_id: ID del pipeline
        to_revision: Número de revisión objetivo
        org: Organización
        project: Proyecto
        pat: Personal Access Token
        dry_run: Si es True, solo simula el rollback
    """
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Rollback v{__version__}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    # Listar revisiones disponibles
    print(f"{Colors.CYAN}>>> Listando revisiones del pipeline {pipeline_id}...{Colors.ENDC}")
    list_pipeline_revisions(org, project, pipeline_id, pat)
    
    # Obtener definición actual
    print(f"{Colors.CYAN}>>> Obteniendo definición actual...{Colors.ENDC}")
    current_definition = get_release_definition(org, project, pipeline_id, pat)
    current_revision = current_definition.get('revision', 'N/A')
    print(f"{Colors.GREEN}✓ Definición actual obtenida (Revision: {current_revision}){Colors.ENDC}")
    
    # Validar que la revisión objetivo existe
    if to_revision >= current_revision:
        print(f"{Colors.RED}✗ Error: La revisión {to_revision} no es anterior a la actual ({current_revision}){Colors.ENDC}")
        sys.exit(1)
    
    # Obtener definición de la revisión objetivo
    print(f"\n{Colors.CYAN}>>> Obteniendo revisión {to_revision}...{Colors.ENDC}")
    target_definition = get_pipeline_revision(org, project, pipeline_id, to_revision, pat)
    print(f"{Colors.GREEN}✓ Revisión {to_revision} obtenida exitosamente{Colors.ENDC}")
    
    # Mostrar información de la revisión objetivo
    print(f"\n{Colors.CYAN}Información de la revisión objetivo:{Colors.ENDC}")
    print(f"  Pipeline ID: {pipeline_id}")
    print(f"  Pipeline Name: {target_definition.get('name', 'Unknown')}")
    print(f"  Revisión: {to_revision}")
    print(f"  Modificado por: {target_definition.get('modifiedBy', {}).get('displayName', 'Unknown')}")
    print(f"  Fecha: {target_definition.get('modifiedOn', 'Unknown')}")
    print(f"  Comentario: {target_definition.get('comment', 'No comment')}")
    
    # Confirmación
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⚠  CONFIRMACIÓN DE ROLLBACK{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"Estás a punto de revertir el pipeline {Colors.BOLD}{pipeline_id}{Colors.ENDC}")
    print(f"  Revisión actual: {current_revision}")
    print(f"  Revisión objetivo: {to_revision}")
    if not dry_run:
        print(f"{Colors.RED}Los cambios se aplicarán INMEDIATAMENTE y serán PERMANENTES{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Modo DRY-RUN: Solo se simulará el rollback{Colors.ENDC}")
    
    confirm = input(f"\n{Colors.BOLD}¿Deseas continuar? (escribe 'SI' para confirmar): {Colors.ENDC}").strip()
    
    if confirm != 'SI':
        print(f"\n{Colors.YELLOW}✗ Rollback cancelado por el usuario{Colors.ENDC}")
        return 0
    
    print(f"\n{Colors.GREEN}✓ Confirmación recibida. Iniciando rollback...{Colors.ENDC}\n")
    
    # Realizar rollback
    if dry_run:
        print(f"{Colors.YELLOW}>>> Modo DRY-RUN: Cambios NO aplicados{Colors.ENDC}")
        print(f"{Colors.CYAN}  Se restauraría la definición de la revisión {to_revision}{Colors.ENDC}")
    else:
        # Modificar el comentario para indicar rollback
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_definition['comment'] = f"[Rollback - {timestamp}] Reverted to revision {to_revision}"
        
        response = restore_pipeline_definition(org, project, pipeline_id, pat, target_definition)
        print(f"\n{Colors.GREEN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.GREEN}  ✓ Rollback completado exitosamente{Colors.ENDC}")
        print(f"{Colors.GREEN}{'='*70}{Colors.ENDC}\n")
    
    return 0


def get_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Rollback de cambios en Azure DevOps Release Pipelines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Listar backups disponibles
  python rollback-pipeline.py --list-backups
  
  # Rollback desde backup local (restaura backup completo)
  python rollback-pipeline.py --backup-file outcome/backups/pipeline_2758_backup_20260618_153645.json --pat YOUR_PAT
  
  # Rollback híbrido (usa revisión del backup desde Azure DevOps)
  python rollback-pipeline.py --backup-file outcome/backups/pipeline_2758_backup_20260618_153645.json --hybrid --pat YOUR_PAT
  
  # Rollback a revisión específica (manual)
  python rollback-pipeline.py --pipeline-id 2758 --to-revision 42 --org Coppel-Retail --project Cadena_de_Suministros --pat YOUR_PAT
  
  # Listar revisiones de un pipeline
  python rollback-pipeline.py --list-revisions --pipeline-id 2758 --org Coppel-Retail --project Cadena_de_Suministros --pat YOUR_PAT
  
  # Dry-run
  python rollback-pipeline.py --backup-file outcome/backups/pipeline_2758_backup_20260618_153645.json --pat YOUR_PAT --dry-run
        """
    )
    
    parser.add_argument('--backup-file', type=str,
                        help='Ruta al archivo de backup para restaurar')
    parser.add_argument('--pipeline-id', type=int,
                        help='ID del Release Pipeline (para rollback por revisión)')
    parser.add_argument('--to-revision', type=int,
                        help='Número de revisión a la que revertir')
    parser.add_argument('--org', '--organization', type=str,
                        help='Nombre de la organización de Azure DevOps')
    parser.add_argument('--project', type=str,
                        help='Nombre del proyecto')
    parser.add_argument('--pat', type=str,
                        help='Personal Access Token con permisos Release (Read & Write)')
    parser.add_argument('--list-backups', action='store_true',
                        help='Listar todos los backups disponibles')
    parser.add_argument('--list-revisions', action='store_true',
                        help='Listar revisiones de un pipeline (requiere --pipeline-id, --org, --project, --pat)')
    parser.add_argument('--hybrid', action='store_true',
                        help='Modo híbrido: usa revisión del backup para rollback desde Azure DevOps (requiere --backup-file)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simular rollback sin aplicar cambios')
    parser.add_argument('--interactive', action='store_true',
                        help='Modo interactivo')
    
    return parser.parse_args()


def main():
    """Función principal."""
    args = get_args()
    
    # Listar backups
    if args.list_backups:
        list_available_backups()
        return 0
    
    # Listar revisiones
    if args.list_revisions:
        if not args.pipeline_id or not args.org or not args.project or not args.pat:
            print(f"{Colors.RED}✗ Error: --pipeline-id, --org, --project y --pat son requeridos{Colors.ENDC}")
            sys.exit(1)
        list_pipeline_revisions(args.org, args.project, args.pipeline_id, args.pat)
        return 0
    
    # Validar argumentos
    if not args.backup_file and not (args.pipeline_id and args.to_revision):
        print(f"{Colors.RED}✗ Error: Debes especificar --backup-file o (--pipeline-id + --to-revision){Colors.ENDC}")
        print(f"{Colors.YELLOW}Usa --help para ver ejemplos de uso{Colors.ENDC}")
        sys.exit(1)
    
    if not args.pat:
        print(f"{Colors.RED}✗ Error: --pat es requerido{Colors.ENDC}")
        sys.exit(1)
    
    # Rollback desde backup
    if args.backup_file:
        # Modo híbrido: usa revisión del backup para rollback desde Azure DevOps
        if args.hybrid:
            return rollback_hybrid(args.backup_file, args.pat, args.dry_run)
        # Modo normal: restaura backup completo
        else:
            return rollback_from_backup(args.backup_file, args.pat, args.dry_run)
    
    # Rollback por revisión
    if args.pipeline_id and args.to_revision:
        if not args.org or not args.project:
            print(f"{Colors.RED}✗ Error: --org y --project son requeridos para rollback por revisión{Colors.ENDC}")
            sys.exit(1)
        
        return rollback_to_revision(
            args.pipeline_id,
            args.to_revision,
            args.org,
            args.project,
            args.pat,
            args.dry_run
        )
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}>>> Proceso interrumpido por el usuario{Colors.ENDC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}>>> ERROR INESPERADO: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
