#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Release Pipeline - Branch Config Updater

Actualiza la variable branchConfig y el script de tareas en un Release Pipeline
de Azure DevOps usando la API REST.

Uso:
    python pipeline-cd-update-branchconfig.py --org <org> --project <project> --definition-id <id> --pat <token>
"""

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import urllib.request
import urllib.error

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


console = Console()

__version__ = "1.0.6"
__author__ = "Harold Adrian"

# ═══════════════════════════════════════════════════════════════════════════════
# COLORES PARA TERMINAL
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def load_config() -> Dict:
    """Carga configuración desde scm/config.json (centralizado) si existe."""
    # Buscar config.json en la raíz de scm (un nivel arriba de azdo/)
    config_file = Path(__file__).parent.parent / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                azdo_config = config.get('azdo', {})
                
                # Extraer organization del organization_url si existe
                org_url = azdo_config.get('organization_url', '')
                organization = org_url.split('/')[-1] if org_url else ''
                
                # Configuración base desde azdo (nivel superior)
                base_config = {
                    'organization': organization,
                    'project': azdo_config.get('project', ''),
                    'pat': azdo_config.get('pat', '')
                }
                
                # Sobrescribir con valores específicos de pipeline_updater
                pipeline_config = azdo_config.get('pipeline_updater', {})
                base_config.update(pipeline_config)
                
                return base_config
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ No se pudo cargar config.json: {e}{Colors.ENDC}")
    return {}


def prompt_with_default(prompt_text: str, default_value: any, required: bool = False) -> str:
    """
    Solicita input con valor por defecto.
    
    Args:
        prompt_text: Texto del prompt
        default_value: Valor por defecto
        required: Si es True, no permite valor vacío
    
    Returns:
        Valor ingresado o default
    """
    default_str = str(default_value) if default_value is not None else ""
    
    if default_str:
        full_prompt = f"{Colors.BOLD}{prompt_text} [{Colors.CYAN}{default_str}{Colors.ENDC}{Colors.BOLD}]: {Colors.ENDC}"
    else:
        full_prompt = f"{Colors.BOLD}{prompt_text}: {Colors.ENDC}"
    
    value = input(full_prompt).strip()
    
    if not value:
        if required and not default_str:
            print(f"{Colors.RED}✗ Este campo es requerido{Colors.ENDC}")
            return prompt_with_default(prompt_text, default_value, required)
        return default_str
    
    return value


def interactive_mode() -> Dict:
    """
    Modo interactivo para solicitar parámetros.
    Carga defaults desde config.json y permite iteración.
    
    Returns:
        Dict con los parámetros configurados
    """
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Updater - Modo Interactivo{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    # Cargar configuración
    config = load_config()
    
    if config:
        print(f"{Colors.GREEN}✓ Configuración cargada desde config.json{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}⚠ No se encontró config.json, usando valores por defecto{Colors.ENDC}")
    
    print(f"{Colors.DIM}Presione Enter para aceptar el valor por defecto{Colors.ENDC}\n")
    
    # Solicitar parámetros con defaults desde config
    params = {}
    
    params['org'] = prompt_with_default(
        "Organización de Azure DevOps",
        config.get('organization', 'Coppel-Retail')
    )
    
    params['project'] = prompt_with_default(
        "Proyecto",
        config.get('project', 'Cadena_de_Suministros')
    )
    
    definition_ids_str = prompt_with_default(
        "ID(s) del Release Pipeline (separados por coma, máx 100)",
        config.get('definition_id', 123)
    )
    
    # Parsear y validar IDs
    try:
        if ',' in str(definition_ids_str):
            definition_ids = [int(id.strip()) for id in str(definition_ids_str).split(',')]
        else:
            definition_ids = [int(definition_ids_str)]
        
        if len(definition_ids) > 100:
            print(f"{Colors.RED}✗ Error: Máximo 100 pipelines permitidos. Se proporcionaron {len(definition_ids)}{Colors.ENDC}")
            sys.exit(1)
        
        params['definition_ids'] = definition_ids
        print(f"{Colors.GREEN}  ✓ {len(definition_ids)} pipeline(s) a actualizar{Colors.ENDC}")
    except ValueError as e:
        print(f"{Colors.RED}✗ Error: IDs inválidos. Deben ser números enteros separados por coma.{Colors.ENDC}")
        sys.exit(1)
    
    params['pat'] = prompt_with_default(
        "Personal Access Token (PAT)",
        config.get('pat', ''),
        required=True
    )
    
    print(f"\n{Colors.CYAN}Opciones de actualización:{Colors.ENDC}\n")
    
    params['branch_config'] = prompt_with_default(
        "Nuevo valor para branchConfig",
        config.get('branch_config', 'config-cadenaSuministro')
    )
    
    params['task_name'] = prompt_with_default(
        "Nombre de la tarea a actualizar",
        config.get('task_name', 'get file k8-manifest')
    )
    
    params['old_pattern'] = prompt_with_default(
        "Patrón a buscar en el script",
        config.get('old_pattern', '$(path_pipelineConfig)')
    )
    
    params['new_pattern'] = prompt_with_default(
        "Patrón de reemplazo",
        config.get('new_pattern', '$(path_pipelineConfigYml)')
    )
    
    dry_run = input(f"{Colors.BOLD}¿Modo DRY-RUN (simular sin guardar)? (s/n) [{Colors.CYAN}n{Colors.ENDC}{Colors.BOLD}]: {Colors.ENDC}").strip().lower()
    params['dry_run'] = dry_run == 's'
    
    return params

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

def create_auth_header(pat: str) -> str:
    """Crea el header de autenticación Basic con PAT."""
    credentials = f":{pat}"
    encoded = base64.b64encode(credentials.encode('ascii')).decode('ascii')
    return f"Basic {encoded}"


def get_release_definition(org: str, project: str, definition_id: int, pat: str) -> Dict:
    """
    Obtiene la definición del Release Pipeline desde Azure DevOps.
    
    Args:
        org: Nombre de la organización
        project: Nombre del proyecto
        definition_id: ID del Release Pipeline
        pat: Personal Access Token
        
    Returns:
        Dict con la definición completa del pipeline
    """
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{definition_id}?api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    print(f"{Colors.CYAN}>>> Obteniendo definición del release pipeline...{Colors.ENDC}")
    
    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}✓ Definición obtenida exitosamente{Colors.ENDC}")
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def update_branch_config_variable(definition: Dict, new_value: str) -> None:
    """
    Actualiza la variable branchConfig en la definición.
    
    Args:
        definition: Definición del pipeline
        new_value: Nuevo valor para branchConfig
    """
    print(f"{Colors.CYAN}>>> Actualizando variable 'branchConfig'...{Colors.ENDC}")
    
    if 'variables' not in definition:
        definition['variables'] = {}
    
    if 'branchConfig' in definition['variables']:
        old_value = definition['variables']['branchConfig'].get('value', 'N/A')
        definition['variables']['branchConfig']['value'] = new_value
        print(f"{Colors.YELLOW}  Valor anterior: {old_value}{Colors.ENDC}")
    else:
        # Crear la variable si no existe
        definition['variables']['branchConfig'] = {
            'value': new_value,
            'allowOverride': True
        }
        print(f"{Colors.YELLOW}  Variable creada (no existía){Colors.ENDC}")
    
    print(f"{Colors.GREEN}  branchConfig = {new_value}{Colors.ENDC}")


def update_task_script(definition: Dict, task_name: str, old_pattern: str, new_pattern: str) -> Tuple[bool, int]:
    """
    Busca y actualiza el script de una tarea específica en todos los environments.
    
    Args:
        definition: Definición del pipeline
        task_name: Name o displayName de la tarea a buscar
        old_pattern: Patrón a buscar en el script
        new_pattern: Patrón de reemplazo
        
    Returns:
        Tuple (found, count) - Si se encontró la tarea y cuántas veces se reemplazó
    """
    print(f"{Colors.CYAN}>>> Buscando tarea '{task_name}' en todos los environments...{Colors.ENDC}")
    
    task_found = False
    replacement_count = 0
    environments_updated = []
    
    if 'environments' not in definition:
        print(f"{Colors.RED}✗ No se encontraron environments en la definición{Colors.ENDC}")
        return False, 0
    
    # Primero, listar todas las tareas para debug
    print(f"{Colors.DIM}Tareas disponibles por environment:{Colors.ENDC}")
    for env in definition['environments']:
        env_name = env.get('name', 'Unknown')
        if 'deployPhases' in env:
            for phase in env['deployPhases']:
                if 'workflowTasks' in phase:
                    task_names = [t.get('name', t.get('displayName', 'N/A')) for t in phase['workflowTasks']]
                    print(f"{Colors.DIM}  [{env_name}]: {', '.join(task_names[:5])}{'...' if len(task_names) > 5 else ''}{Colors.ENDC}")
    
    print()
    
    # Buscar y actualizar
    for env in definition['environments']:
        env_name = env.get('name', 'Unknown')
        
        if 'deployPhases' not in env:
            continue
            
        for phase in env['deployPhases']:
            if 'workflowTasks' not in phase:
                continue
                
            for task in phase['workflowTasks']:
                # Buscar por 'name' o 'displayName'
                task_display_name = task.get('displayName', '')
                task_simple_name = task.get('name', '')
                
                if task_display_name == task_name or task_simple_name == task_name:
                    task_found = True
                    print(f"{Colors.YELLOW}  ✓ Tarea encontrada en environment: {env_name}{Colors.ENDC}")
                    
                    if 'inputs' in task and 'script' in task['inputs']:
                        old_script = task['inputs']['script']
                        new_script = old_script.replace(old_pattern, new_pattern)
                        
                        if old_script != new_script:
                            task['inputs']['script'] = new_script
                            replacement_count += 1
                            environments_updated.append(env_name)
                            
                            print(f"{Colors.GREEN}    Script actualizado:{Colors.ENDC}")
                            print(f"{Colors.YELLOW}      Patrón antiguo: {old_pattern}{Colors.ENDC}")
                            print(f"{Colors.GREEN}      Patrón nuevo:   {new_pattern}{Colors.ENDC}")
                        else:
                            print(f"{Colors.YELLOW}    ⚠ No se encontró el patrón '{old_pattern}' en el script{Colors.ENDC}")
                    else:
                        print(f"{Colors.YELLOW}    ⚠ La tarea no tiene script o inputs{Colors.ENDC}")
    
    if not task_found:
        print(f"{Colors.RED}✗ No se encontró la tarea '{task_name}'{Colors.ENDC}")
        print(f"{Colors.YELLOW}  Tip: Revisa el nombre exacto en la lista de tareas arriba{Colors.ENDC}")
    else:
        print(f"\n{Colors.GREEN}✓ Resumen: {replacement_count} script(s) actualizado(s) en {len(environments_updated)} environment(s){Colors.ENDC}")
        if environments_updated:
            print(f"{Colors.CYAN}  Environments actualizados: {', '.join(environments_updated)}{Colors.ENDC}")
    
    return task_found, replacement_count


def create_backup(definition: Dict, definition_id: int, output_dir: str = "outcome/backups") -> str:
    """
    Crea un backup completo de la definición del pipeline antes de modificarlo.
    
    Args:
        definition: Definición completa del pipeline
        definition_id: ID del pipeline
        output_dir: Directorio de backups
        
    Returns:
        Ruta del archivo de backup creado
    """
    import datetime
    import os
    
    # Crear directorio si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Timestamp para el nombre del archivo
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pipeline_{definition_id}_backup_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Agregar metadata al backup
    backup_data = {
        "backup_metadata": {
            "pipeline_id": definition_id,
            "pipeline_name": definition.get('name', 'Unknown'),
            "backup_timestamp": datetime.datetime.now().isoformat(),
            "original_revision": definition.get('revision', 'N/A'),
            "tool_version": __version__
        },
        "pipeline_definition": definition
    }
    
    # Guardar backup
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def export_execution_report(stats: Dict, args, definition_ids: list, output_dir: str = "outcome") -> str:
    """
    Exporta un reporte JSON con toda la información de la ejecución.
    
    Args:
        stats: Diccionario con estadísticas de ejecución
        args: Argumentos de la ejecución
        definition_ids: Lista de IDs procesados
        output_dir: Directorio de salida
        
    Returns:
        Ruta del archivo generado
    """
    import datetime
    import os
    
    # Crear directorio si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Timestamp para el nombre del archivo
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pipeline_updater_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Construir reporte
    report = {
        "metadata": {
            "tool": "Azure DevOps Pipeline Updater",
            "version": __version__,
            "execution_timestamp": datetime.datetime.now().isoformat(),
            "mode": "dry-run" if args.dry_run else "production"
        },
        "configuration": {
            "organization": args.org,
            "project": args.project,
            "pipeline_ids": definition_ids,
            "total_pipelines": len(definition_ids)
        },
        "changes_applied": {
            "branch_config": args.branch_config,
            "task_name": args.task_name,
            "old_pattern": args.old_pattern,
            "new_pattern": args.new_pattern
        },
        "statistics": {
            "total_processed": stats['total'],
            "successful": stats['success'],
            "skipped": stats['skipped'],
            "failed": stats['failed'],
            "success_rate": f"{(stats['success'] / stats['total'] * 100):.1f}%" if stats['total'] > 0 else "0%"
        },
        "backups_created": [
            {
                "pipeline_id": r['id'],
                "backup_file": r.get('backup_file', 'N/A'),
                "original_revision": r.get('original_revision', 'N/A'),
                "new_revision": r.get('revision', 'N/A')
            }
            for r in stats['results'] if 'backup_file' in r
        ],
        "results": {
            "successful_pipelines": [
                {
                    "pipeline_id": r['id'],
                    "status": r['status'],
                    "scripts_updated": r.get('replacements', 0),
                    "revision": r.get('revision', 'N/A')
                }
                for r in stats['results'] if r['status'] in ('success', 'dry-run')
            ],
            "skipped_pipelines": [
                {
                    "pipeline_id": r['id'],
                    "reason": r.get('reason', 'Unknown')
                }
                for r in stats['results'] if r['status'] == 'skipped'
            ],
            "failed_pipelines": [
                {
                    "pipeline_id": r['id'],
                    "error": r.get('error', 'Unknown error')
                }
                for r in stats['results'] if r['status'] == 'failed'
            ]
        }
    }
    
    # Guardar archivo
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return filepath


def save_release_definition(org: str, project: str, definition_id: int, pat: str, definition: Dict) -> Dict:
    """
    Guarda la definición actualizada del Release Pipeline.
    
    Args:
        org: Nombre de la organización
        project: Nombre del proyecto
        definition_id: ID del Release Pipeline
        pat: Personal Access Token
        definition: Definición actualizada
        
    Returns:
        Dict con la respuesta del servidor
    """
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{definition_id}?api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    print(f"{Colors.CYAN}>>> Enviando definición actualizada...{Colors.ENDC}")
    
    try:
        body = json.dumps(definition).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method='PUT')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}>>> Pipeline actualizado exitosamente.{Colors.ENDC}")
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


def get_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Actualiza branchConfig y scripts en Azure DevOps Release Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Usando valores por defecto (Coppel-Retail/Cadena_de_Suministros)
  python pipeline-cd-update-branchconfig.py --pat YOUR_PAT_HERE

  # Especificando organización y proyecto diferentes
  python pipeline-cd-update-branchconfig.py \\
    --org MyOrg --project MyProject --definition-id 456 \\
    --pat TOKEN --branch-config config-production \\
    --task-name "deploy manifest" \\
    --old-pattern "$(oldVar)" --new-pattern "$(newVar)"
  
  # Múltiples pipelines
  python pipeline-cd-update-branchconfig.py \\
    --definition-id "123,456,789" --pat TOKEN
        """
    )
    
    parser.add_argument('--org', '--organization', default='Coppel-Retail',
                        help='Nombre de la organización de Azure DevOps (default: Coppel-Retail)')
    parser.add_argument('--project', default='Cadena_de_Suministros',
                        help='Nombre del proyecto (default: Cadena_de_Suministros)')
    parser.add_argument('--definition-id', type=str, default='123',
                        help='ID(s) del Release Pipeline separados por coma (ej: "123,456,789", máx 100)')
    parser.add_argument('--pat', required=False,
                        help='Personal Access Token con permisos Release (Read & Write). Requerido si no se usa --interactive con config.json')
    
    parser.add_argument('--branch-config', default='config-cadenaSuministro',
                        help='Nuevo valor para la variable branchConfig (default: config-cadenaSuministro)')
    parser.add_argument('--task-name', default='get file k8-manifest',
                        help='Display name de la tarea a actualizar (default: get file k8-manifest)')
    parser.add_argument('--old-pattern', default='$(path_pipelineConfig)',
                        help='Patrón a buscar en el script (default: $(path_pipelineConfig))')
    parser.add_argument('--new-pattern', default='$(path_pipelineConfigYml)',
                        help='Patrón de reemplazo (default: $(path_pipelineConfigYml))')
    
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula los cambios sin guardarlos')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Modo interactivo: solicita parámetros uno por uno con defaults desde config.json')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Función principal."""
    args = get_args()
    
    # Si se especifica modo interactivo, obtener parámetros interactivamente
    if args.interactive:
        params = interactive_mode()
        # Sobrescribir args con params del modo interactivo
        args.org = params['org']
        args.project = params['project']
        definition_ids = params['definition_ids']  # Lista de IDs
        args.pat = params['pat']
        args.branch_config = params['branch_config']
        args.task_name = params['task_name']
        args.old_pattern = params['old_pattern']
        args.new_pattern = params['new_pattern']
        args.dry_run = params['dry_run']
    else:
        # En modo no-interactivo, PAT es obligatorio
        if not args.pat:
            print(f"{Colors.RED}✗ Error: --pat es requerido cuando no se usa --interactive{Colors.ENDC}")
            print(f"{Colors.YELLOW}Usa --interactive para modo interactivo con config.json{Colors.ENDC}")
            sys.exit(1)
        
        # Parsear definition_ids desde CLI
        try:
            if ',' in args.definition_id:
                definition_ids = [int(id.strip()) for id in args.definition_id.split(',')]
            else:
                definition_ids = [int(args.definition_id)]
            
            if len(definition_ids) > 100:
                print(f"{Colors.RED}✗ Error: Máximo 100 pipelines permitidos. Se proporcionaron {len(definition_ids)}{Colors.ENDC}")
                sys.exit(1)
        except ValueError:
            print(f"{Colors.RED}✗ Error: IDs inválidos. Deben ser números enteros separados por coma.{Colors.ENDC}")
            sys.exit(1)
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  Azure DevOps Release Pipeline - Branch Config Updater v{__version__}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    print(f"\n{Colors.CYAN}Configuración:{Colors.ENDC}")
    print(f"  Organización: {args.org}")
    print(f"  Proyecto: {args.project}")
    print(f"  Pipeline IDs: {', '.join(map(str, definition_ids))} ({len(definition_ids)} pipeline(s))")
    print(f"  Modo: {'DRY-RUN (sin guardar)' if args.dry_run else 'PRODUCCIÓN'}")
    
    print(f"\n{Colors.CYAN}Cambios a aplicar:{Colors.ENDC}")
    print(f"  • Variable branchConfig → {Colors.GREEN}{args.branch_config}{Colors.ENDC}")
    print(f"  • Tarea a modificar → {Colors.GREEN}{args.task_name}{Colors.ENDC}")
    print(f"  • Patrón a buscar → {Colors.YELLOW}{args.old_pattern}{Colors.ENDC}")
    print(f"  • Patrón nuevo → {Colors.GREEN}{args.new_pattern}{Colors.ENDC}")
    
    # Confirmación antes de ejecutar
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⚠  CONFIRMACIÓN REQUERIDA{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"Estás a punto de actualizar {Colors.BOLD}{len(definition_ids)} pipeline(s){Colors.ENDC}")
    if not args.dry_run:
        print(f"{Colors.RED}Los cambios se aplicarán INMEDIATAMENTE y serán PERMANENTES{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Modo DRY-RUN: Solo se simularán los cambios{Colors.ENDC}")
    
    confirm = input(f"\n{Colors.BOLD}¿Deseas continuar? (escribe 'SI' para confirmar): {Colors.ENDC}").strip()
    
    if confirm != 'SI':
        print(f"\n{Colors.YELLOW}✗ Operación cancelada por el usuario{Colors.ENDC}")
        return 0
    
    print(f"\n{Colors.GREEN}✓ Confirmación recibida. Iniciando procesamiento...{Colors.ENDC}")
    print()
    
    # Estadísticas de procesamiento
    stats = {
        'total': len(definition_ids),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'results': []
    }
    
    try:
        import datetime
        
        # Procesar cada pipeline
        for idx, definition_id in enumerate(definition_ids, 1):
            print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}Pipeline {idx}/{len(definition_ids)}: ID {definition_id}{Colors.ENDC}")
            print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            
            try:
                # 1. Obtener definición actual
                definition = get_release_definition(args.org, args.project, definition_id, args.pat)
                original_revision = definition.get('revision', 'N/A')
                
                # 2. Crear backup antes de modificar
                print(f"{Colors.CYAN}>>> Creando backup...{Colors.ENDC}")
                backup_file = create_backup(definition, definition_id)
                print(f"{Colors.GREEN}  ✓ Backup guardado: {backup_file}{Colors.ENDC}")
                
                # 3. Actualizar variable branchConfig
                update_branch_config_variable(definition, args.branch_config)
                
                # 4. Actualizar script de tarea
                task_found, replacements = update_task_script(
                    definition,
                    args.task_name,
                    args.old_pattern,
                    args.new_pattern
                )
                
                if not task_found:
                    print(f"{Colors.YELLOW}⚠ Pipeline {definition_id}: Tarea no encontrada, se omite{Colors.ENDC}")
                    stats['skipped'] += 1
                    stats['results'].append({
                        'id': definition_id, 
                        'status': 'skipped', 
                        'reason': 'Tarea no encontrada',
                        'backup_file': backup_file,
                        'original_revision': original_revision
                    })
                    continue
                
                # 5. Agregar comentario con resumen de cambios
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                comment_parts = [
                    f"[Pipeline Updater - {timestamp}]",
                    f"✓ Variable branchConfig: {args.branch_config}",
                    f"✓ Tarea '{args.task_name}': {replacements} script(s) actualizado(s)",
                    f"✓ Patrón: {args.old_pattern} → {args.new_pattern}",
                    f"✓ Backup: {backup_file}"
                ]
                definition['comment'] = " | ".join(comment_parts)
                
                print(f"{Colors.CYAN}>>> Comentario agregado:{Colors.ENDC}")
                print(f"{Colors.DIM}  {definition['comment']}{Colors.ENDC}")
                
                # 6. Guardar cambios (si no es dry-run)
                if args.dry_run:
                    print(f"{Colors.YELLOW}>>> Modo DRY-RUN: Cambios NO guardados{Colors.ENDC}")
                    stats['success'] += 1
                    stats['results'].append({
                        'id': definition_id, 
                        'status': 'dry-run', 
                        'replacements': replacements,
                        'backup_file': backup_file,
                        'original_revision': original_revision
                    })
                else:
                    response = save_release_definition(args.org, args.project, definition_id, args.pat, definition)
                    stats['success'] += 1
                    stats['results'].append({
                        'id': definition_id, 
                        'status': 'success', 
                        'replacements': replacements, 
                        'revision': response.get('revision', 'N/A'),
                        'backup_file': backup_file,
                        'original_revision': original_revision
                    })
                
                print(f"{Colors.GREEN}✓ Pipeline {definition_id} actualizado exitosamente{Colors.ENDC}")
                
            except Exception as e:
                print(f"{Colors.RED}✗ Error en pipeline {definition_id}: {e}{Colors.ENDC}")
                stats['failed'] += 1
                stats['results'].append({'id': definition_id, 'status': 'failed', 'error': str(e)})
                continue
        
        # Resumen final
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  📊 RESUMEN DE EJECUCIÓN{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.CYAN}Total procesados:    {stats['total']}{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Exitosos:          {stats['success']}{Colors.ENDC}")
        print(f"{Colors.YELLOW}⚠ Omitidos:          {stats['skipped']}{Colors.ENDC}")
        print(f"{Colors.RED}✗ Fallidos:          {stats['failed']}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        
        # Detalles de pipelines exitosos
        if stats['success'] > 0:
            print(f"{Colors.GREEN}✓ Pipelines actualizados exitosamente:{Colors.ENDC}")
            for result in stats['results']:
                if result['status'] in ('success', 'dry-run'):
                    mode = " (DRY-RUN)" if result['status'] == 'dry-run' else ""
                    revision = f" - Rev: {result.get('revision', 'N/A')}" if result['status'] == 'success' else ""
                    print(f"  • Pipeline {result['id']}: {result.get('replacements', 0)} script(s) actualizado(s){revision}{mode}")
            print()
        
        # Detalles de pipelines omitidos
        if stats['skipped'] > 0:
            print(f"{Colors.YELLOW}⚠ Pipelines omitidos:{Colors.ENDC}")
            for result in stats['results']:
                if result['status'] == 'skipped':
                    print(f"  • Pipeline {result['id']}: {result.get('reason', 'Omitido')}")
            print()
        
        # Detalles de pipelines con error
        if stats['failed'] > 0:
            print(f"{Colors.RED}✗ Pipelines con errores:{Colors.ENDC}")
            for result in stats['results']:
                if result['status'] == 'failed':
                    error_msg = result.get('error', 'Error desconocido')
                    # Truncar mensajes muy largos
                    if len(error_msg) > 100:
                        error_msg = error_msg[:97] + "..."
                    print(f"  • Pipeline {result['id']}: {error_msg}")
            print()
        
        # Mensaje final
        if stats['failed'] == 0 and stats['skipped'] == 0:
            print(f"{Colors.GREEN}🎉 ¡Todos los pipelines fueron actualizados exitosamente!{Colors.ENDC}\n")
        elif stats['failed'] == 0:
            print(f"{Colors.YELLOW}⚠ Proceso completado con algunos pipelines omitidos{Colors.ENDC}\n")
        else:
            print(f"{Colors.RED}⚠ Proceso completado con errores. Revisa los detalles arriba.{Colors.ENDC}\n")
        
        # Exportar reporte JSON
        try:
            report_path = export_execution_report(stats, args, definition_ids)
            print(f"{Colors.CYAN}📄 Reporte exportado: {report_path}{Colors.ENDC}\n")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ No se pudo exportar el reporte JSON: {e}{Colors.ENDC}\n")
        
        return 0 if stats['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}>>> Proceso interrumpido por el usuario{Colors.ENDC}")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}>>> ERROR INESPERADO: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    
    from pathlib import Path
    import json
    import csv
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = output_path / f"pipeline-cd-update-branchconfig_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"pipeline-cd-update-branchconfig_{ts}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        
        print(f"✅ Resultados exportados a: {filepath}")
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("pipeline-cd-update-branchconfig", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
