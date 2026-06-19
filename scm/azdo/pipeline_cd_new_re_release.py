#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Release Pipeline - Re-Release Creator

Crea un nuevo Release desde un Release existente con backup automático versionado.
Permite re-ejecutar un release anterior con artefactos frescos.

Uso:
    python pipeline_cd_new_re_release.py --source-release-id 987 --release-comment "Motivo" --pat TOKEN
"""

import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
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
    DIM = '\033[2m'
    MAGENTA = '\033[95m'

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def load_config() -> Dict:
    """Carga configuración desde scm/config.json (centralizado) si existe."""
    config_file = Path(__file__).parent.parent / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                azdo_config = config.get('azdo', {})
                
                org_url = azdo_config.get('organization_url', '')
                organization = org_url.split('/')[-1] if org_url else ''
                
                base_config = {
                    'organization': organization,
                    'project': azdo_config.get('project', ''),
                    'pat': azdo_config.get('pat', '')
                }
                
                pipeline_config = azdo_config.get('pipeline_re_release', {})
                base_config.update(pipeline_config)
                
                return base_config
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ No se pudo cargar config.json: {e}{Colors.ENDC}")
    return {}


def prompt_with_default(prompt_text: str, default_value: any, required: bool = False) -> str:
    """Solicita input con valor por defecto."""
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
    """Modo interactivo para solicitar parámetros."""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Re-Release - Modo Interactivo{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    config = load_config()
    
    if config:
        print(f"{Colors.GREEN}✓ Configuración cargada desde config.json{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}⚠ No se encontró config.json, usando valores por defecto{Colors.ENDC}")
    
    print(f"{Colors.DIM}Presione Enter para aceptar el valor por defecto{Colors.ENDC}\n")
    
    params = {}
    
    params['org'] = prompt_with_default(
        "Organización de Azure DevOps",
        config.get('organization', 'Coppel-Retail')
    )
    
    params['project'] = prompt_with_default(
        "Proyecto",
        config.get('project', 'Cadena_de_Suministros')
    )
    
    params['source_release_id'] = int(prompt_with_default(
        "ID del Release origen a re-ejecutar",
        config.get('source_release_id', 999999)
    ))
    
    params['release_comment'] = prompt_with_default(
        "Comentario para el nuevo release",
        config.get('release_comment', 'Renovacion de Credenciales Git'),
        required=True
    )
    
    params['pat'] = prompt_with_default(
        "Personal Access Token (PAT)",
        config.get('pat', ''),
        required=True
    )
    
    params['backup_path'] = prompt_with_default(
        "Carpeta de backups",
        config.get('backup_path', './outcome/backups')
    )
    
    return params


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_org(org: str) -> str:
    """Normaliza la organización: extrae el nombre si es una URL completa."""
    if org.startswith("https://"):
        return org.split('/')[-1]
    return org


def create_auth_header(pat: str) -> str:
    """Crea el header de autenticación Basic con PAT."""
    credentials = f":{pat}"
    encoded = base64.b64encode(credentials.encode('ascii')).decode('ascii')
    return f"Basic {encoded}"


def get_release(org: str, project: str, release_id: int, pat: str) -> Dict:
    """Obtiene un Release desde Azure DevOps."""
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases/{release_id}?api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    print(f"{Colors.CYAN}>>> Obteniendo Release #{release_id}...{Colors.ENDC}")
    
    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}✓ Release obtenido: {data.get('name', 'N/A')}{Colors.ENDC}")
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def create_backup(release: Dict, backup_path: str) -> str:
    """Crea un backup versionado del release."""
    import os
    
    os.makedirs(backup_path, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    release_id = release.get('id', 'unknown')
    version_label = f"REL_{release_id}_{timestamp}"
    filename = f"release_backup_{version_label}.json"
    filepath = os.path.join(backup_path, filename)
    
    backup_data = {
        "metadata": {
            "versionLabel": version_label,
            "sourceReleaseId": release_id,
            "backupDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backedUpBy": "pipeline_cd_new_re_release.py",
            "tool_version": __version__
        },
        "releaseSnapshot": {
            "releaseDefinitionId": release.get('releaseDefinition', {}).get('id'),
            "releaseDefinitionName": release.get('releaseDefinition', {}).get('name'),
            "originalDescription": release.get('description'),
            "originalStatus": release.get('status'),
            "createdOn": release.get('createdOn'),
            "modifiedOn": release.get('modifiedOn'),
            "createdBy": release.get('createdBy', {}).get('displayName'),
            "artifacts": release.get('artifacts', []),
            "variables": release.get('variables', {}),
            "environments": [
                {
                    "id": env.get('id'),
                    "name": env.get('name'),
                    "status": env.get('status'),
                    "variables": env.get('variables', {})
                }
                for env in release.get('environments', [])
            ]
        }
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    return filepath, version_label


def create_new_release(org: str, project: str, release: Dict, release_comment: str, pat: str, version_label: str) -> Dict:
    """Crea un nuevo Release con los artefactos del release origen."""
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases?api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    # Mapear artefactos
    artifacts_payload = []
    for artifact in release.get('artifacts', []):
        artifacts_payload.append({
            'alias': artifact.get('alias'),
            'instanceReference': {
                'id': artifact.get('definitionReference', {}).get('version', {}).get('id'),
                'name': artifact.get('definitionReference', {}).get('version', {}).get('name')
            }
        })
    
    # Descripción con trazabilidad
    full_description = f"Re-release desde #{release.get('id')} [Backup: {version_label}]. Motivo: {release_comment}"
    
    payload = {
        'definitionId': release.get('releaseDefinition', {}).get('id'),
        'description': full_description,
        'artifacts': artifacts_payload,
        'isDraft': False,
        'reason': 'manual',
        'manualEnvironments': []
    }
    
    print(f"{Colors.CYAN}>>> Creando nuevo Release...{Colors.ENDC}")
    print(f"{Colors.YELLOW}  Descripción: {full_description}{Colors.ENDC}")
    
    try:
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}✓ Release creado exitosamente{Colors.ENDC}")
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def export_report(stats: Dict, args, backup_file: str, new_release: Dict, output_dir: str = "outcome") -> str:
    """Exporta un reporte JSON con la ejecución."""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"re_release_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    report = {
        "metadata": {
            "tool": "Pipeline Re-Release",
            "version": __version__,
            "execution_timestamp": datetime.now().isoformat(),
        },
        "configuration": {
            "organization": args.org,
            "project": args.project,
            "source_release_id": args.source_release_id,
        },
        "execution": {
            "source_release": {
                "id": stats.get('source_release_id'),
                "name": stats.get('source_release_name'),
            },
            "backup": {
                "file": backup_file,
                "version_label": stats.get('version_label'),
            },
            "new_release": {
                "id": new_release.get('id'),
                "name": new_release.get('name'),
                "url": new_release.get('_links', {}).get('self', {}).get('href', 'N/A'),
            },
            "comment": args.release_comment,
        }
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return filepath


def get_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Crea un nuevo Release desde uno existente con backup automático',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Modo interactivo
  python pipeline_cd_new_re_release.py --interactive
  
  # Especificando parámetros
  python pipeline_cd_new_re_release.py \\
    --org Coppel-Retail --project Cadena_de_Suministros \\
    --source-release-id 987 --release-comment "Motivo" --pat TOKEN
        """
    )
    
    parser.add_argument('--org', '--organization', default='Coppel-Retail',
                        help='Organización de Azure DevOps (default: Coppel-Retail)')
    parser.add_argument('--project', default='Cadena_de_Suministros',
                        help='Proyecto (default: Cadena_de_Suministros)')
    parser.add_argument('--source-release-id', type=int, default=999999,
                        help='ID del Release origen (default: 999999)')
    parser.add_argument('--release-comment', default='Renovacion de Credenciales Git',
                        help='Comentario para el nuevo release')
    parser.add_argument('--pat', required=False,
                        help='Personal Access Token (requerido si no se usa --interactive)')
    parser.add_argument('--backup-path', default='./outcome/backups',
                        help='Carpeta de backups (default: ./outcome/backups)')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Modo interactivo')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Función principal."""
    args = get_args()
    
    # Normalizar organización (extraer nombre si es URL)
    args.org = normalize_org(args.org)
    
    if args.interactive:
        params = interactive_mode()
        args.org = params['org']
        args.project = params['project']
        args.source_release_id = params['source_release_id']
        args.release_comment = params['release_comment']
        args.pat = params['pat']
        args.backup_path = params['backup_path']
    else:
        if not args.pat:
            print(f"{Colors.RED}✗ Error: --pat es requerido cuando no se usa --interactive{Colors.ENDC}")
            sys.exit(1)
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Re-Release v{__version__}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    print(f"{Colors.CYAN}Configuración:{Colors.ENDC}")
    print(f"  Organización: {args.org}")
    print(f"  Proyecto: {args.project}")
    print(f"  Release origen: #{args.source_release_id}")
    print(f"  Comentario: {args.release_comment}")
    print(f"  Carpeta backups: {args.backup_path}\n")
    
    # Confirmación
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⚠  CONFIRMACIÓN REQUERIDA{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"Se creará un nuevo Release desde Release #{args.source_release_id}")
    print(f"Se generará un backup automático versionado\n")
    
    confirm = input(f"{Colors.BOLD}¿Deseas continuar? (escribe 'SI' para confirmar): {Colors.ENDC}").strip()
    
    if confirm != 'SI':
        print(f"\n{Colors.YELLOW}✗ Operación cancelada por el usuario{Colors.ENDC}")
        return 0
    
    print(f"\n{Colors.GREEN}✓ Confirmación recibida. Iniciando...{Colors.ENDC}\n")
    
    try:
        # FASE 1: Obtener Release origen
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}FASE 1: Obtener Release Origen{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        
        source_release = get_release(args.org, args.project, args.source_release_id, args.pat)
        
        # FASE 2: Crear backup
        print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}FASE 2: Crear Backup Versionado{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        
        backup_file, version_label = create_backup(source_release, args.backup_path)
        print(f"{Colors.GREEN}✓ Backup guardado: {backup_file}{Colors.ENDC}")
        print(f"{Colors.YELLOW}  Versión: {version_label}{Colors.ENDC}")
        
        # FASE 3: Crear nuevo Release
        print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}FASE 3: Crear Nuevo Release{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        
        new_release = create_new_release(
            args.org, args.project, source_release, 
            args.release_comment, args.pat, version_label
        )
        
        # Resumen final
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  ✅ RE-RELEASE EXITOSO{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.GREEN}Release origen:     #{source_release.get('id')}{Colors.ENDC}")
        print(f"{Colors.GREEN}Nuevo Release:      #{new_release.get('id')}{Colors.ENDC}")
        print(f"{Colors.GREEN}Nombre:             {new_release.get('name')}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Backup:             {version_label}{Colors.ENDC}")
        print(f"{Colors.CYAN}Comentario:         {args.release_comment}{Colors.ENDC}")
        
        if '_links' in new_release and 'self' in new_release['_links']:
            url = new_release['_links']['self'].get('href', '')
            print(f"{Colors.CYAN}URL:                {url}{Colors.ENDC}")
        
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        
        # Exportar reporte
        stats = {
            'source_release_id': source_release.get('id'),
            'source_release_name': source_release.get('name'),
            'version_label': version_label,
        }
        
        report_path = export_report(stats, args, backup_file, new_release)
        print(f"{Colors.CYAN}📄 Reporte exportado: {report_path}{Colors.ENDC}\n")
        
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
