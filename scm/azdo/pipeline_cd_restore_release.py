#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Release Pipeline - Restore Release

Restaura un Release desde un backup versionado con trazabilidad completa.
Permite rollback seguro con confirmación interactiva.

Uso:
    python pipeline_cd_restore_release.py --backup-file backup.json --restore-comment "Motivo" --pat TOKEN
"""

import argparse
import base64
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
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
                
                pipeline_config = azdo_config.get('pipeline_restore_release', {})
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
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Restore - Modo Interactivo{Colors.ENDC}")
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
    
    params['backup_file'] = prompt_with_default(
        "Archivo de backup (ruta o nombre)",
        config.get('backup_file', ''),
        required=True
    )
    
    params['restore_comment'] = prompt_with_default(
        "Comentario para el restore",
        config.get('restore_comment', 'Restore automático desde tools.py'),
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

def create_auth_header(pat: str) -> str:
    """Crea el header de autenticación Basic con PAT."""
    credentials = f":{pat}"
    encoded = base64.b64encode(credentials.encode('ascii')).decode('ascii')
    return f"Basic {encoded}"


def load_backup(backup_file: str, backup_path: str) -> Dict:
    """Carga un archivo de backup."""
    print(f"{Colors.CYAN}>>> Cargando backup desde: {backup_file}{Colors.ENDC}")
    
    # Si no existe la ruta completa, buscar en backup_path
    if not os.path.exists(backup_file):
        print(f"{Colors.YELLOW}  ⚠️  Archivo no encontrado en ruta directa. Buscando en {backup_path}...{Colors.ENDC}")
        
        matching_files = []
        if os.path.exists(backup_path):
            for file in os.listdir(backup_path):
                if backup_file in file or file.endswith(backup_file):
                    matching_files.append(os.path.join(backup_path, file))
        
        if matching_files:
            # Seleccionar el más reciente
            backup_file = max(matching_files, key=os.path.getmtime)
            print(f"{Colors.GREEN}  ✓ Backup encontrado: {backup_file}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}✗ No se encontró ningún backup con ese nombre{Colors.ENDC}")
            sys.exit(1)
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup = json.load(f)
            print(f"{Colors.GREEN}✓ Backup cargado correctamente{Colors.ENDC}")
            return backup
    except Exception as e:
        print(f"{Colors.RED}✗ Error al leer el archivo: {e}{Colors.ENDC}")
        sys.exit(1)


def show_backup_info(backup: Dict) -> None:
    """Muestra información del backup."""
    meta = backup.get('metadata', {})
    snapshot = backup.get('releaseSnapshot', {})
    
    print(f"\n{Colors.MAGENTA}╔══════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.MAGENTA}║           INFORMACIÓN DEL BACKUP                ║{Colors.ENDC}")
    print(f"{Colors.MAGENTA}╠══════════════════════════════════════════════════╣{Colors.ENDC}")
    print(f"{Colors.MAGENTA}║{Colors.ENDC}  Versión Label  : {meta.get('versionLabel', 'N/A')}")
    print(f"{Colors.MAGENTA}║{Colors.ENDC}  Release Origen : #{meta.get('sourceReleaseId', 'N/A')}")
    print(f"{Colors.MAGENTA}║{Colors.ENDC}  Fecha Backup   : {meta.get('backupDate', 'N/A')}")
    print(f"{Colors.MAGENTA}║{Colors.ENDC}  Generado por   : {meta.get('backedUpBy', 'N/A')}")
    print(f"{Colors.MAGENTA}║{Colors.ENDC}  Pipeline       : {snapshot.get('releaseDefinitionName', 'N/A')}")
    print(f"{Colors.MAGENTA}║{Colors.ENDC}  Artefactos     : {len(snapshot.get('artifacts', []))}")
    print(f"{Colors.MAGENTA}╚══════════════════════════════════════════════════╝{Colors.ENDC}\n")


def confirm_restore() -> bool:
    """Solicita confirmación interactiva para el restore."""
    confirm = input(f"{Colors.BOLD}¿Confirmas el RESTORE desde este backup? (S/N): {Colors.ENDC}").strip().lower()
    return confirm in ('s', 'si', 'yes', 'y')


def create_restore_release(org: str, project: str, backup: Dict, restore_comment: str, pat: str) -> Dict:
    """Crea un nuevo Release desde el backup."""
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases?api-version=7.0"
    
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json'
    }
    
    meta = backup.get('metadata', {})
    snapshot = backup.get('releaseSnapshot', {})
    
    # Mapear artefactos
    artifacts_payload = []
    for artifact in snapshot.get('artifacts', []):
        artifacts_payload.append({
            'alias': artifact.get('alias'),
            'instanceReference': {
                'id': artifact.get('definitionReference', {}).get('version', {}).get('id'),
                'name': artifact.get('definitionReference', {}).get('version', {}).get('name')
            }
        })
    
    # Descripción con trazabilidad
    full_description = f"🔄 RESTORE desde backup [{meta.get('versionLabel')}] - Release #{meta.get('sourceReleaseId')}. Motivo: {restore_comment}"
    
    payload = {
        'definitionId': snapshot.get('releaseDefinitionId'),
        'description': full_description,
        'artifacts': artifacts_payload,
        'isDraft': False,
        'reason': 'manual',
        'manualEnvironments': []
    }
    
    print(f"{Colors.CYAN}>>> Creando Release de Restore...{Colors.ENDC}")
    print(f"{Colors.YELLOW}  Descripción: {full_description}{Colors.ENDC}")
    
    try:
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}✓ Release de Restore creado exitosamente{Colors.ENDC}")
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def export_report(stats: Dict, args, backup: Dict, restore_release: Dict, output_dir: str = "outcome") -> str:
    """Exporta un reporte JSON con la ejecución."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"restore_release_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    meta = backup.get('metadata', {})
    
    report = {
        "metadata": {
            "tool": "Pipeline Restore Release",
            "version": __version__,
            "execution_timestamp": datetime.now().isoformat(),
        },
        "configuration": {
            "organization": args.org,
            "project": args.project,
        },
        "execution": {
            "backup": {
                "version_label": meta.get('versionLabel'),
                "source_release_id": meta.get('sourceReleaseId'),
                "backup_date": meta.get('backupDate'),
            },
            "restore_release": {
                "id": restore_release.get('id'),
                "name": restore_release.get('name'),
                "url": restore_release.get('_links', {}).get('self', {}).get('href', 'N/A'),
            },
            "comment": args.restore_comment,
        }
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return filepath


def get_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Restaura un Release desde un backup versionado',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Modo interactivo
  python pipeline_cd_restore_release.py --interactive
  
  # Especificando parámetros
  python pipeline_cd_restore_release.py \\
    --org Coppel-Retail --project Cadena_de_Suministros \\
    --backup-file release_backup_REL_987_20260619_123045.json \\
    --restore-comment "Motivo del restore" --pat TOKEN
        """
    )
    
    parser.add_argument('--org', '--organization', default='Coppel-Retail',
                        help='Organización de Azure DevOps (default: Coppel-Retail)')
    parser.add_argument('--project', default='Cadena_de_Suministros',
                        help='Proyecto (default: Cadena_de_Suministros)')
    parser.add_argument('--backup-file', required=False,
                        help='Archivo de backup (ruta o nombre)')
    parser.add_argument('--restore-comment', default='Restore automático desde tools.py',
                        help='Comentario para el restore')
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
    
    if args.interactive:
        params = interactive_mode()
        args.org = params['org']
        args.project = params['project']
        args.backup_file = params['backup_file']
        args.restore_comment = params['restore_comment']
        args.pat = params['pat']
        args.backup_path = params['backup_path']
    else:
        if not args.backup_file or not args.pat:
            print(f"{Colors.RED}✗ Error: --backup-file y --pat son requeridos cuando no se usa --interactive{Colors.ENDC}")
            sys.exit(1)
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Restore v{__version__}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    try:
        # FASE 1: Cargar backup
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}FASE 1: Cargar Backup{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        
        backup = load_backup(args.backup_file, args.backup_path)
        
        # FASE 2: Mostrar información y confirmar
        print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}FASE 2: Validación del Backup{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        
        show_backup_info(backup)
        
        if not confirm_restore():
            print(f"\n{Colors.YELLOW}✗ Restore cancelado por el usuario{Colors.ENDC}")
            return 0
        
        # FASE 3: Crear Release de Restore
        print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}FASE 3: Crear Release de Restore{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}\n")
        
        restore_release = create_restore_release(
            args.org, args.project, backup, args.restore_comment, args.pat
        )
        
        # Resumen final
        meta = backup.get('metadata', {})
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}  ✅ RESTORE EXITOSO{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Backup Origen:      {meta.get('versionLabel')}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Release Origen:     #{meta.get('sourceReleaseId')}{Colors.ENDC}")
        print(f"{Colors.GREEN}Nuevo Release:      #{restore_release.get('id')}{Colors.ENDC}")
        print(f"{Colors.GREEN}Nombre:             {restore_release.get('name')}{Colors.ENDC}")
        print(f"{Colors.CYAN}Comentario:         {args.restore_comment}{Colors.ENDC}")
        
        if '_links' in restore_release and 'self' in restore_release['_links']:
            url = restore_release['_links']['self'].get('href', '')
            print(f"{Colors.CYAN}URL:                {url}{Colors.ENDC}")
        
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        
        # Exportar reporte
        stats = {}
        report_path = export_report(stats, args, backup, restore_release)
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
