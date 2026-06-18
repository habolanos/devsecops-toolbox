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
from typing import Dict, Optional, Tuple
import urllib.request
import urllib.error

__version__ = "1.0.0"
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
    Busca y actualiza el script de una tarea específica.
    
    Args:
        definition: Definición del pipeline
        task_name: Display name de la tarea a buscar
        old_pattern: Patrón a buscar en el script
        new_pattern: Patrón de reemplazo
        
    Returns:
        Tuple (found, count) - Si se encontró la tarea y cuántas veces se reemplazó
    """
    print(f"{Colors.CYAN}>>> Buscando tarea '{task_name}'...{Colors.ENDC}")
    
    task_found = False
    replacement_count = 0
    
    if 'environments' not in definition:
        print(f"{Colors.RED}✗ No se encontraron environments en la definición{Colors.ENDC}")
        return False, 0
    
    for env in definition['environments']:
        env_name = env.get('name', 'Unknown')
        
        if 'deployPhases' not in env:
            continue
            
        for phase in env['deployPhases']:
            if 'workflowTasks' not in phase:
                continue
                
            for task in phase['workflowTasks']:
                if task.get('displayName') == task_name:
                    task_found = True
                    print(f"{Colors.YELLOW}  ✓ Tarea encontrada en environment: {env_name}{Colors.ENDC}")
                    
                    if 'inputs' in task and 'script' in task['inputs']:
                        old_script = task['inputs']['script']
                        new_script = old_script.replace(old_pattern, new_pattern)
                        
                        if old_script != new_script:
                            task['inputs']['script'] = new_script
                            replacement_count += 1
                            
                            print(f"{Colors.GREEN}  Script actualizado:{Colors.ENDC}")
                            print(f"{Colors.YELLOW}    ANT: {old_pattern}{Colors.ENDC}")
                            print(f"{Colors.GREEN}    NEW: {new_pattern}{Colors.ENDC}")
                        else:
                            print(f"{Colors.YELLOW}  ⚠ No se encontró el patrón '{old_pattern}' en el script{Colors.ENDC}")
    
    if not task_found:
        print(f"{Colors.RED}✗ No se encontró la tarea con displayName '{task_name}'{Colors.ENDC}")
        print(f"{Colors.YELLOW}  Revisa el nombre exacto en la UI de Azure DevOps{Colors.ENDC}")
    
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
  python update-pipeline-cd-branchconfig.py \\
    --org Coppel-Retail \\
    --project Cadena_de_Suministros \\
    --definition-id 123 \\
    --pat YOUR_PAT_HERE

  python update-pipeline-cd-branchconfig.py \\
    --org MyOrg --project MyProject --definition-id 456 \\
    --pat TOKEN --branch-config config-production \\
    --task-name "deploy manifest" \\
    --old-pattern "$(oldVar)" --new-pattern "$(newVar)"
        """
    )
    
    parser.add_argument('--org', '--organization', required=True,
                        help='Nombre de la organización de Azure DevOps')
    parser.add_argument('--project', required=True,
                        help='Nombre del proyecto')
    parser.add_argument('--definition-id', type=int, required=True,
                        help='ID del Release Pipeline (visible en la URL)')
    parser.add_argument('--pat', required=True,
                        help='Personal Access Token con permisos Release (Read & Write)')
    
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
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Función principal."""
    args = get_args()
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Release Pipeline - Branch Config Updater v{__version__}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    print(f"{Colors.CYAN}Configuración:{Colors.ENDC}")
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
