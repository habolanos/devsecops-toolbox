#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Release Pipeline - Branch Config Updater

Actualiza la variable branchConfig y el script de tareas en un Release Pipeline
de Azure DevOps usando la API REST.

Uso:
    python update-pipeline-cd-branchconfig.py --org <org> --project <project> --definition-id <id> --pat <token>
"""

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import urllib.request
import urllib.error

__version__ = "1.0.1"
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
    """Carga configuración desde scm/azdo/config.json si existe."""
    # Buscar config.json en el mismo directorio que el script
    config_file = Path(__file__).parent / "config.json"
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
    
    params['definition_id'] = int(prompt_with_default(
        "ID del Release Pipeline",
        config.get('definition_id', 123)
    ))
    
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
  python update-pipeline-cd-branchconfig.py --pat YOUR_PAT_HERE

  # Especificando organización y proyecto diferentes
  python update-pipeline-cd-branchconfig.py \\
    --org MyOrg --project MyProject --definition-id 456 \\
    --pat TOKEN --branch-config config-production \\
    --task-name "deploy manifest" \\
    --old-pattern "$(oldVar)" --new-pattern "$(newVar)"
        """
    )
    
    parser.add_argument('--org', '--organization', default='Coppel-Retail',
                        help='Nombre de la organización de Azure DevOps (default: Coppel-Retail)')
    parser.add_argument('--project', default='Cadena_de_Suministros',
                        help='Nombre del proyecto (default: Cadena_de_Suministros)')
    parser.add_argument('--definition-id', type=int, default=123,
                        help='ID del Release Pipeline (default: 123)')
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
        args.definition_id = params['definition_id']
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
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  Azure DevOps Release Pipeline - Branch Config Updater v{__version__}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    print(f"\n{Colors.CYAN}Configuración:{Colors.ENDC}")
    print(f"  Organización: {args.org}")
    print(f"  Proyecto: {args.project}")
    print(f"  Pipeline ID: {args.definition_id}")
    print(f"  Modo: {'DRY-RUN (sin guardar)' if args.dry_run else 'PRODUCCIÓN'}")
    print()
    
    try:
        # 1. Obtener definición actual
        definition = get_release_definition(args.org, args.project, args.definition_id, args.pat)
        
        # 2. Actualizar variable branchConfig
        update_branch_config_variable(definition, args.branch_config)
        
        # 3. Actualizar script de tarea
        task_found, replacements = update_task_script(
            definition,
            args.task_name,
            args.old_pattern,
            args.new_pattern
        )
        
        if not task_found:
            print(f"\n{Colors.RED}✗ No se pudo completar la actualización{Colors.ENDC}")
            sys.exit(1)
        
        # 4. Guardar cambios (si no es dry-run)
        if args.dry_run:
            print(f"\n{Colors.YELLOW}>>> Modo DRY-RUN: Cambios NO guardados{Colors.ENDC}")
            print(f"{Colors.CYAN}  Variable branchConfig actualizada: {args.branch_config}{Colors.ENDC}")
            print(f"{Colors.CYAN}  Reemplazos en scripts: {replacements}{Colors.ENDC}")
        else:
            response = save_release_definition(args.org, args.project, args.definition_id, args.pat, definition)
        
        print(f"\n{Colors.GREEN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.GREEN}  ✓ Proceso completado exitosamente{Colors.ENDC}")
        print(f"{Colors.GREEN}{'='*70}{Colors.ENDC}\n")
        
        return 0
        
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
