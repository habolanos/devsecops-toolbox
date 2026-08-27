#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Release Pipeline - Update Release

Actualiza un Release existente por releaseId mediante PATCH API.
Permite modificar variables globales, variables por environment, status y descripcion.
Incluye backup automatico antes de modificar, dry-run y trazabilidad completa.

Uso:
    python pipeline_cd_update_release.py --release-id 987 --pat TOKEN \\
        --set-var GIT_USER=deploy --set-var GIT_PASS=secret \\
        --set-env-var QA,NODE_VERSION=18 --abandon --dry-run
"""

import argparse
import base64
import copy
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.error

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


console = Console()

__version__ = "1.0.0"
__author__ = "Harold Adrian"

API_VERSION = "7.0"


class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    MAGENTA = '\033[95m'


def load_config() -> Dict:
    """Carga configuracion desde scm/config.json si existe."""
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
                pipeline_config = azdo_config.get('pipeline_update_release', {})
                base_config.update(pipeline_config)
                return base_config
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ No se pudo cargar config.json: {e}{Colors.ENDC}")
    return {}


def load_template(template_path: str) -> Dict:
    """
    Carga un template YAML para actualizacion de releases.

    Estructura nueva (con search):
        metadata:
          name: "..."
          version: "1.0"
          description: "..."
        search:
          stages:
            - name: "*"          # o "QA", "PROD", etc.
          variables:             # search_value: solo actualizar si coincide
            - name: "branchConfig"
              value: "config-cadenaSuministro"
          release_ids: []        # alternativa a release.ids
        release:
          ids: []
        update:
          global_vars:
            - name: "VAR_NAME"
              value: "new_value"
          env_vars:
            - name: "NODE_VERSION"   # sin stage (viene de search.stages)
              value: "18"
          tasks:
            - name: "get file k8-manifest"
              fields:
                - path: "inputs.script"
                  old_value: "old"
                  new_value: "new"
          abandon: false
          description: "..."
        options:
          dry_run: false
          backup_path: "./outcome/backups"

    Estructura antigua (sin search, backward compatible):
        update:
          env_vars:
            - stage: "QA"
              name: "NODE_VERSION"
              value: "18"
              search_value: "old_value"   # opcional

    Returns:
        Dict con keys: release_ids, global_vars, env_vars, env_var_search_values,
                       task_updates, search_stages, abandon, description, dry_run, backup_path
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML no esta instalado. Instala con: pip install pyyaml")

    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template no encontrado: {template_path}")

    content = path.read_text(encoding='utf-8')
    template = yaml.safe_load(content)

    if not isinstance(template, dict):
        raise ValueError("Template invalido: debe ser un diccionario YAML")

    metadata = template.get('metadata', {})
    release_section = template.get('release', {})
    update_section = template.get('update', {})
    options_section = template.get('options', {})
    search_section = template.get('search', {})

    release_ids_raw = release_section.get('ids', [])
    if not release_ids_raw and search_section.get('release_ids'):
        release_ids_raw = search_section.get('release_ids', [])
    if isinstance(release_ids_raw, list):
        release_ids = [str(rid) for rid in release_ids_raw]
    elif isinstance(release_ids_raw, str):
        release_ids = [rid.strip() for rid in release_ids_raw.split(',') if rid.strip()]
    else:
        release_ids = []

    global_var_list = update_section.get('global_vars', [])
    global_vars = []
    global_var_search_values = []
    for var in global_var_list:
        name = var.get('name', '')
        value = var.get('value', '')
        global_vars.append(f"{name}={value}")
        global_var_search_values.append(None)

    env_var_list = update_section.get('env_vars', [])
    env_vars = []
    env_var_search_values = []
    search_stages = ['*']

    if search_section:
        search_stages = [s.get('name', '*') for s in search_section.get('stages', [{'name': '*'}])]
        search_vars = {}
        search_scopes = {}
        for v in search_section.get('variables', []):
            search_vars[v.get('name', '')] = v.get('value')
            search_scopes[v.get('name', '')] = v.get('scope', 'env')  # default: env
        for var in env_var_list:
            name = var.get('name', '')
            value = var.get('value', '')
            sv = search_vars.get(name)
            scope = search_scopes.get(name, 'env')
            if scope == 'global':
                # Variable global con search_value
                global_vars.append(f"{name}={value}")
                global_var_search_values.append(sv)
            else:
                for stage in search_stages:
                    env_vars.append(f"{stage},{name}={value}")
                    env_var_search_values.append(sv)
    else:
        for var in env_var_list:
            stage = var.get('stage', '')
            name = var.get('name', '')
            value = var.get('value', '')
            search_value = var.get('search_value', None)
            env_vars.append(f"{stage},{name}={value}")
            env_var_search_values.append(search_value)

    task_updates = update_section.get('tasks', [])

    abandon = update_section.get('abandon', False)
    description = update_section.get('description', '')
    if not description and metadata.get('comment'):
        description = metadata['comment'].strip()
    dry_run = options_section.get('dry_run', False)
    backup_path = options_section.get('backup_path', './outcome/backups')

    print(f"{Colors.GREEN}✓ Template cargado: {metadata.get('name', 'Unknown')} v{metadata.get('version', '1.0')}{Colors.ENDC}")
    if metadata.get('description'):
        print(f"{Colors.DIM}  {metadata['description']}{Colors.ENDC}")
    print(f"{Colors.CYAN}  Release IDs: {', '.join(release_ids) if release_ids else '(via CLI)'}{Colors.ENDC}")
    print(f"{Colors.CYAN}  Variables globales: {len(global_vars)}{Colors.ENDC}")
    print(f"{Colors.CYAN}  Variables por env: {len(env_vars)}{Colors.ENDC}")
    print(f"{Colors.CYAN}  Search stages: {', '.join(search_stages)}{Colors.ENDC}")
    print(f"{Colors.CYAN}  Task updates: {len(task_updates)}{Colors.ENDC}")
    print(f"{Colors.CYAN}  Abandonar: {abandon}{Colors.ENDC}")
    print(f"{Colors.CYAN}  Dry-run: {dry_run}{Colors.ENDC}")

    return {
        'release_ids': release_ids,
        'global_vars': global_vars,
        'global_var_search_values': global_var_search_values,
        'env_vars': env_vars,
        'env_var_search_values': env_var_search_values,
        'task_updates': task_updates,
        'search_stages': search_stages,
        'abandon': abandon,
        'description': description,
        'dry_run': dry_run,
        'backup_path': backup_path,
    }


def prompt_with_default(prompt_text: str, default_value: any, required: bool = False) -> str:
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
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Update Release - Modo Interactivo{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    config = load_config()
    if config:
        print(f"{Colors.GREEN}✓ Configuracion cargada desde config.json{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}⚠ No se encontro config.json, usando valores por defecto{Colors.ENDC}")
    print(f"{Colors.DIM}Presione Enter para aceptar el valor por defecto{Colors.ENDC}\n")
    params = {}
    params['org'] = prompt_with_default("Organizacion de Azure DevOps", config.get('organization', 'Coppel-Retail'))
    params['project'] = prompt_with_default("Proyecto", config.get('project', 'Cadena_de_Suministros'))
    params['release_id'] = prompt_with_default("ID del Release a actualizar (separados por coma si multiples)", config.get('release_id', ''), required=True)
    print(f"\n{Colors.CYAN}--- Variables Globales ---{Colors.ENDC}")
    print(f"{Colors.DIM}Formato: NOMBRE=VALOR (vacio para terminar){Colors.ENDC}")
    global_vars = []
    while True:
        var_input = input(f"{Colors.BOLD}  Variable (o Enter para saltar): {Colors.ENDC}").strip()
        if not var_input:
            break
        if '=' in var_input:
            global_vars.append(var_input)
        else:
            print(f"{Colors.RED}  ✗ Formato invalido. Use NOMBRE=VALOR{Colors.ENDC}")
    params['set_var'] = global_vars
    print(f"\n{Colors.CYAN}--- Variables por Environment ---{Colors.ENDC}")
    print(f"{Colors.DIM}Formato: STAGE,NOMBRE=VALOR (vacio para terminar){Colors.ENDC}")
    env_vars = []
    while True:
        var_input = input(f"{Colors.BOLD}  Variable (o Enter para saltar): {Colors.ENDC}").strip()
        if not var_input:
            break
        if ',' in var_input and '=' in var_input:
            env_vars.append(var_input)
        else:
            print(f"{Colors.RED}  ✗ Formato invalido. Use STAGE,NOMBRE=VALOR{Colors.ENDC}")
    params['set_env_var'] = env_vars
    abandon_input = input(f"{Colors.BOLD}  Abandonar release? (S/N) [N]: {Colors.ENDC}").strip().lower()
    params['abandon'] = abandon_input in ('s', 'si', 'yes', 'y')
    params['description'] = prompt_with_default("Nueva descripcion (vacio para mantener)", "")
    params['pat'] = prompt_with_default("Personal Access Token (PAT)", config.get('pat', ''), required=True)
    params['backup_path'] = prompt_with_default("Carpeta de backups", config.get('backup_path', './outcome/backups'))
    dry_input = input(f"{Colors.BOLD}  Modo dry-run (solo simular)? (S/N) [N]: {Colors.ENDC}").strip().lower()
    params['dry_run'] = dry_input in ('s', 'si', 'yes', 'y')
    return params


def normalize_org(org: str) -> str:
    if org.startswith("https://"):
        return org.rstrip('/').split('/')[-1]
    return org


def create_auth_header(pat: str) -> str:
    credentials = f":{pat}"
    encoded = base64.b64encode(credentials.encode('ascii')).decode('ascii')
    return f"Basic {encoded}"


def get_release(org: str, project: str, release_id: int, pat: str) -> Dict:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases/{release_id}?api-version={API_VERSION}"
    headers = {'Authorization': create_auth_header(pat), 'Content-Type': 'application/json'}
    print(f"{Colors.CYAN}>>> Obteniendo Release #{release_id}...{Colors.ENDC}")
    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}✓ Release obtenido: {data.get('name', 'N/A')} (status: {data.get('status', 'N/A')}){Colors.ENDC}")
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def update_release(org: str, project: str, release_id: int, payload: Dict, pat: str) -> Dict:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases/{release_id}?api-version={API_VERSION}"
    headers = {'Authorization': create_auth_header(pat), 'Content-Type': 'application/json'}
    print(f"{Colors.CYAN}>>> Aplicando PUT al Release #{release_id}...{Colors.ENDC}")
    try:
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method='PUT')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"{Colors.GREEN}✓ Release actualizado exitosamente{Colors.ENDC}")
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"{Colors.RED}✗ Error HTTP {e.code}: {e.reason}{Colors.ENDC}")
        print(f"{Colors.RED}  {error_body}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.ENDC}")
        sys.exit(1)


def create_backup(release: Dict, backup_path: str) -> Tuple[str, str]:
    os.makedirs(backup_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    release_id = release.get('id', 'unknown')
    version_label = f"UPD_REL_{release_id}_{timestamp}"
    filename = f"release_backup_{version_label}.json"
    filepath = os.path.join(backup_path, filename)
    backup_data = {
        "metadata": {
            "versionLabel": version_label,
            "sourceReleaseId": release_id,
            "backupDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backedUpBy": "pipeline_cd_update_release.py",
            "tool_version": __version__,
            "backupType": "pre_update"
        },
        "releaseSnapshot": {
            "releaseDefinitionId": release.get('releaseDefinition', {}).get('id'),
            "releaseDefinitionName": release.get('releaseDefinition', {}).get('name'),
            "releaseName": release.get('name'),
            "originalDescription": release.get('description'),
            "originalStatus": release.get('status'),
            "createdOn": release.get('createdOn'),
            "modifiedOn": release.get('modifiedOn'),
            "createdBy": release.get('createdBy', {}).get('displayName'),
            "artifacts": release.get('artifacts', []),
            "variables": copy.deepcopy(release.get('variables', {})),
            "environments": [
                {"id": env.get('id'), "name": env.get('name'), "status": env.get('status'),
                 "variables": copy.deepcopy(env.get('variables', {}))}
                for env in release.get('environments', [])
            ]
        }
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    return filepath, version_label


def parse_var(var_str: str) -> Tuple[str, str]:
    if '=' not in var_str:
        raise ValueError(f"Formato invalido: '{var_str}'. Use NOMBRE=VALOR")
    key, value = var_str.split('=', 1)
    return key.strip(), value.strip()


def parse_env_var(env_var_str: str) -> Tuple[str, str, str]:
    if ',' not in env_var_str or '=' not in env_var_str:
        raise ValueError(f"Formato invalido: '{env_var_str}'. Use STAGE,NOMBRE=VALOR")
    parts = env_var_str.split(',', 1)
    stage = parts[0].strip()
    key, value = parse_var(parts[1])
    return stage, key, value


def build_var_entry(value: str) -> Dict:
    return {"value": value, "allowOverride": True}


def _get_nested_value(obj: Dict, path: str) -> any:
    keys = path.split('.')
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _set_nested_value(obj: Dict, path: str, value: any) -> None:
    keys = path.split('.')
    current = obj
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _clean_value(v: Optional[str]) -> Optional[str]:
    """Remove zero-width chars and strip whitespace for value comparison."""
    if v is None:
        return None
    return re.sub(r'[\u200b\u200c\u200d\ufeff\u00a0]', '', v).strip()


def build_patch_payload(
    release: Dict, global_vars: List[str], env_vars: List[str],
    abandon: bool, description: str,
    env_var_search_values: Optional[List[Optional[str]]] = None,
    task_updates: Optional[List[Dict]] = None,
    search_stages: Optional[List[str]] = None,
    global_var_search_values: Optional[List[Optional[str]]] = None,
) -> Tuple[Dict, List[Dict]]:
    payload: Dict = {}
    changes: List[Dict] = []
    if global_vars:
        current_vars = release.get('variables', {})
        new_vars = copy.deepcopy(current_vars)
        global_changed = False
        for idx, var_str in enumerate(global_vars):
            key, value = parse_var(var_str)
            old_value = current_vars.get(key, {}).get('value')
            search_value = global_var_search_values[idx] if global_var_search_values and idx < len(global_var_search_values) else None
            if search_value is not None:
                if _clean_value(old_value) != _clean_value(search_value):
                    changes.append({"type": "global_var", "key": key, "old": old_value, "new": value,
                                    "error": f"Variable global '{key}' no tiene valor '{search_value}' (actual: '{old_value}')"})
                    continue
            changes.append({"type": "global_var", "key": key, "old": old_value, "new": value})
            new_vars[key] = build_var_entry(value)
            global_changed = True
        if global_changed:
            payload['variables'] = new_vars
    if env_vars:
        environments = copy.deepcopy(release.get('environments', []))
        for idx, env_var_str in enumerate(env_vars):
            stage_name, key, value = parse_env_var(env_var_str)
            search_value = env_var_search_values[idx] if env_var_search_values and idx < len(env_var_search_values) else None
            matched_stages = []
            stage_found = False
            for env in environments:
                env_name = env.get('name', '')
                if stage_name == '*' or env_name.lower() == stage_name.lower():
                    stage_found = True
                    env_vars_dict = env.get('variables', {})
                    old_value = env_vars_dict.get(key, {}).get('value')
                    if search_value is not None:
                        if _clean_value(old_value) != _clean_value(search_value):
                            continue
                    matched_stages.append(env_name)
                    changes.append({"type": "env_var", "key": key, "old": old_value, "new": value, "stage": env_name})
                    env_vars_dict[key] = build_var_entry(value)
                    env['variables'] = env_vars_dict
                    if stage_name != '*':
                        break
            if not matched_stages:
                if stage_name == '*':
                    changes.append({"type": "env_var", "key": key, "old": None, "new": value, "stage": "*",
                                    "error": f"Variable '{key}' no encontrada en ningun stage"
                                             + (f" con valor '{search_value}'" if search_value else "")})
                elif stage_found and search_value is not None:
                    changes.append({"type": "env_var", "key": key, "old": None, "new": value, "stage": stage_name,
                                    "error": f"Variable '{key}' en stage '{stage_name}' no tiene valor '{search_value}'"})
                else:
                    changes.append({"type": "env_var", "key": key, "old": None, "new": value, "stage": stage_name,
                                    "error": f"Stage '{stage_name}' no encontrado en el release"})
        payload['environments'] = environments
    if task_updates:
        environments = copy.deepcopy(release.get('environments', []))
        stage_filter = search_stages if search_stages else ['*']
        is_wildcard = '*' in stage_filter
        for task_spec in task_updates:
            task_name = task_spec.get('name', '')
            fields = task_spec.get('fields', [])
            task_found = False
            for env in environments:
                env_name = env.get('name', '')
                if not is_wildcard and env_name.lower() not in [s.lower() for s in stage_filter]:
                    continue
                env_phases = env.get('deployPhases', [])
                if not env_phases:
                    print(f"{Colors.YELLOW}  ⚠ Environment '{env_name}' no tiene deployPhases (keys: {list(env.keys())}){Colors.ENDC}")
                for phase in env_phases:
                    phase_tasks = phase.get('workflowTasks', [])
                    if not phase_tasks:
                        print(f"{Colors.YELLOW}  ⚠ Phase '{phase.get('name', '?')}' en '{env_name}' no tiene workflowTasks{Colors.ENDC}")
                    for task in phase_tasks:
                        task_display = task.get('displayName', '') or task.get('name', '')
                        if task_display.lower() == task_name.lower():
                            task_found = True
                            for field in fields:
                                field_path = field.get('path', '')
                                old_val = field.get('old_value', '')
                                new_val = field.get('new_value', '')
                                current_val = _get_nested_value(task, field_path)
                                if current_val is None:
                                    changes.append({
                                        "type": "task_field", "task": task_name,
                                        "path": field_path, "old": None, "new": new_val, "stage": env_name,
                                        "error": f"Task '{task_name}' campo '{field_path}' no existe en stage '{env_name}'",
                                    })
                                elif old_val not in str(current_val):
                                    changes.append({
                                        "type": "task_field", "task": task_name,
                                        "path": field_path, "old": current_val, "new": new_val, "stage": env_name,
                                        "error": f"Task '{task_name}' campo '{field_path}' no contiene '{old_val}' (actual: '{current_val}')",
                                    })
                                else:
                                    new_field_val = str(current_val).replace(old_val, new_val)
                                    _set_nested_value(task, field_path, new_field_val)
                                    changes.append({
                                        "type": "task_field", "task": task_name,
                                        "path": field_path, "old": current_val,
                                        "new": new_field_val, "stage": env_name,
                                    })
            if not task_found:
                changes.append({
                    "type": "task_field", "task": task_name,
                    "path": fields[0].get('path', '') if fields else '', "old": None, "new": None, "stage": "-",
                    "error": f"Task '{task_name}' no encontrada en ningun environment",
                })
        payload['environments'] = environments
    if abandon:
        changes.append({"type": "status", "key": "status", "old": release.get('status'), "new": "abandoned"})
        payload['status'] = 'abandoned'
    if description:
        changes.append({"type": "description", "key": "description", "old": release.get('description'), "new": description})
        payload['description'] = description
    return payload, changes


def show_release_info(release: Dict) -> None:
    table = Table(title=f"Release #{release.get('id')} - {release.get('name', 'N/A')}", show_header=False)
    table.add_column("Campo", style="cyan", no_wrap=True)
    table.add_column("Valor", style="white")
    table.add_row("ID", str(release.get('id', 'N/A')))
    table.add_row("Name", str(release.get('name', 'N/A')))
    table.add_row("Status", str(release.get('status', 'N/A')))
    table.add_row("Definition", str(release.get('releaseDefinition', {}).get('name', 'N/A')))
    table.add_row("Created On", str(release.get('createdOn', 'N/A')))
    table.add_row("Created By", str(release.get('createdBy', {}).get('displayName', 'N/A')))
    table.add_row("Description", str(release.get('description', 'N/A') or '(none)'))
    envs = release.get('environments', [])
    env_summary = ", ".join([f"{e.get('name', '?')}:{e.get('status', '?')}" for e in envs])
    table.add_row("Environments", env_summary)
    vars_count = len(release.get('variables', {}))
    table.add_row("Global Variables", f"{vars_count} variables")
    console.print(table)


def show_changes(changes: List[Dict]) -> None:
    if not changes:
        console.print("[yellow]No hay cambios para aplicar.[/]")
        return
    table = Table(title="Cambios a Aplicar", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Tipo", style="cyan", width=12)
    table.add_column("Stage", style="magenta", width=12)
    table.add_column("Variable", style="yellow", width=20)
    table.add_column("Valor Anterior", style="cyan", no_wrap=False)
    table.add_column("Valor Nuevo", style="green", width=20)
    for i, change in enumerate(changes, 1):
        stage = change.get('stage', '-')
        if change['type'] == 'task_field':
            key = f"{change.get('task', '-')} [{change.get('path', '-')}]"
        else:
            key = change.get('key', '-')
        old_val = change.get('old')
        new_val = change.get('new')
        old_display = "[dim](nueva)[/]" if old_val is None else str(old_val)
        if change.get('error'):
            new_display = f"[red]ERROR: {change['error']}[/]"
        else:
            new_display = str(new_val)[:40]
        table.add_row(str(i), change['type'], stage, key, old_display, new_display)
    console.print(table)


def export_report(stats: Dict, args, backup_file: str, updated_release: Optional[Dict],
                  changes: List[Dict], output_dir: str = "outcome") -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"update_release_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    report = {
        "metadata": {"tool": "Pipeline Update Release", "version": __version__,
                      "execution_timestamp": datetime.now().isoformat()},
        "configuration": {"organization": args.org, "project": args.project,
                          "release_id": args.release_id, "dry_run": getattr(args, 'dry_run', False)},
        "execution": {
            "source_release": {"id": stats.get('source_release_id'), "name": stats.get('source_release_name'),
                               "status": stats.get('source_release_status')},
            "backup": {"file": backup_file, "version_label": stats.get('version_label')},
            "changes": changes, "changes_count": len(changes),
            "updated_release": {"id": updated_release.get('id'), "name": updated_release.get('name'),
                                "status": updated_release.get('status')} if updated_release else None,
            "comment": getattr(args, 'description', None),
        }
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return filepath


def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    from pathlib import Path as P
    import csv
    output_path = P(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not EXPORT_MANAGER_AVAILABLE:
        if output_format == "json":
            filepath = output_path / f"pipeline_cd_update_release_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"pipeline_cd_update_release_{ts}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        print(f"✅ Resultados exportados a: {filepath}")
        return str(filepath)
    manager = ExportManager("pipeline_cd_update_release", "1.0.0")
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    return None


def get_args():
    parser = argparse.ArgumentParser(
        description='Actualiza un Release existente por releaseId via PATCH API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python pipeline_cd_update_release.py --interactive
  python pipeline_cd_update_release.py --release-id 987 --pat TOKEN --set-var FOO=bar
  python pipeline_cd_update_release.py --release-id 987 --pat TOKEN --set-env-var QA,NODE_VERSION=18
  python pipeline_cd_update_release.py --release-id 987 --pat TOKEN --abandon
  python pipeline_cd_update_release.py --release-id 987,988 --pat TOKEN --set-var FOO=bar --dry-run
        """)
    parser.add_argument('--org', '--organization', default='Coppel-Retail', help='Organizacion (default: Coppel-Retail)')
    parser.add_argument('--project', default='Cadena_de_Suministros', help='Proyecto (default: Cadena_de_Suministros)')
    parser.add_argument('--release-id', type=str, required=False, help='ID(s) del Release (separados por coma)')
    parser.add_argument('--set-var', action='append', default=[], help='Variable global: NOMBRE=VALOR')
    parser.add_argument('--set-env-var', action='append', default=[], help='Variable por environment: STAGE,NOMBRE=VALOR')
    parser.add_argument('--abandon', action='store_true', help='Abandonar el release (status=abandoned)')
    parser.add_argument('--description', default='', help='Nueva descripcion del release')
    parser.add_argument('--pat', required=False, help='Personal Access Token')
    parser.add_argument('--backup-path', default='./outcome/backups', help='Carpeta de backups')
    parser.add_argument('--dry-run', action='store_true', help='Modo simulacion (sin cambios)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Modo interactivo')
    parser.add_argument('--template', type=str, default=None,
                        help='Ruta a template YAML con configuracion de actualizacion')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    return parser.parse_args()


def main():
    args = get_args()
    args.org = normalize_org(args.org)

    if args.template:
        tpl = load_template(args.template)
        if not args.release_id and tpl['release_ids']:
            args.release_id = ','.join(tpl['release_ids'])
        if not args.set_var and tpl['global_vars']:
            args.set_var = tpl['global_vars']
        if not args.set_env_var and tpl['env_vars']:
            args.set_env_var = tpl['env_vars']
        args.env_var_search_values = tpl.get('env_var_search_values', [])
        args.global_var_search_values = tpl.get('global_var_search_values', [])
        args.task_updates = tpl.get('task_updates', [])
        args.search_stages = tpl.get('search_stages', ['*'])
        if not args.abandon and tpl['abandon']:
            args.abandon = tpl['abandon']
        if not args.description and tpl['description']:
            args.description = tpl['description']
        args.tpl_dry_run = tpl.get('dry_run', False)
        if args.backup_path == './outcome/backups' and tpl['backup_path'] != './outcome/backups':
            args.backup_path = tpl['backup_path']
        if not args.pat:
            config = load_config()
            args.pat = config.get('pat', '')
        if not args.release_id:
            print(f"{Colors.RED}✗ Error: --release-id es requerido (no encontrado en template ni CLI){Colors.ENDC}")
            sys.exit(1)
        if not args.pat:
            print(f"{Colors.RED}✗ Error: --pat es requerido (no encontrado en config.json ni CLI){Colors.ENDC}")
            sys.exit(1)
    elif args.interactive:
        params = interactive_mode()
        args.org = params['org']
        args.project = params['project']
        args.release_id = params['release_id']
        args.set_var = params['set_var']
        args.set_env_var = params['set_env_var']
        args.abandon = params['abandon']
        args.description = params['description']
        args.pat = params['pat']
        args.backup_path = params['backup_path']
        args.dry_run = params['dry_run']
        args.env_var_search_values = []
        args.global_var_search_values = []
        args.task_updates = []
        args.search_stages = ['*']
    else:
        if not args.release_id or not args.pat:
            print(f"{Colors.RED}✗ Error: --release-id y --pat son requeridos cuando no se usa --interactive{Colors.ENDC}")
            sys.exit(1)
        args.env_var_search_values = []
        args.global_var_search_values = []
        args.task_updates = []
        args.search_stages = ['*']

    release_ids = [rid.strip() for rid in str(args.release_id).split(',')]

    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Azure DevOps Pipeline Update Release v{__version__}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    print(f"{Colors.CYAN}Configuracion:{Colors.ENDC}")
    print(f"  Organizacion: {args.org}")
    print(f"  Proyecto: {args.project}")
    print(f"  Release(s): {', '.join([f'#{rid}' for rid in release_ids])}")
    print(f"  Variables globales: {len(args.set_var)}")
    print(f"  Variables por env: {len(args.set_env_var)}")
    print(f"  Abandonar: {'Si' if args.abandon else 'No'}")
    dry_run_active = getattr(args, 'dry_run', False) or getattr(args, 'tpl_dry_run', False)
    print(f"  Dry-run: {'Si' if dry_run_active else 'No'}")
    print(f"  Carpeta backups: {args.backup_path}\n")

    results = []
    total = len(release_ids)

    for idx, release_id in enumerate(release_ids, 1):
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.CYAN}Procesando Release {idx}/{total}: #{release_id}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

        try:
            # FASE 1: Obtener Release
            print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}FASE 1: Obtener Release{Colors.ENDC}")
            print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            release = get_release(args.org, args.project, int(release_id), args.pat)
            show_release_info(release)

            # FASE 2: Construir payload de cambios
            print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}FASE 2: Analizar Cambios{Colors.ENDC}")
            print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            payload, changes = build_patch_payload(
                release, args.set_var, args.set_env_var, args.abandon, args.description,
                getattr(args, 'env_var_search_values', []),
                getattr(args, 'task_updates', []),
                getattr(args, 'search_stages', ['*']),
                getattr(args, 'global_var_search_values', [])
            )
            show_changes(changes)

            if not changes:
                print(f"{Colors.YELLOW}No hay cambios para aplicar. Saltando...{Colors.ENDC}")
                results.append({'status': 'skipped', 'release_id': release_id, 'changes': 0})
                continue

            error_changes = [c for c in changes if 'error' in c]
            valid_changes = [c for c in changes if 'error' not in c]
            if error_changes:
                print(f"{Colors.YELLOW}  ⚠ {len(error_changes)} cambio(s) con error (ver tabla arriba){Colors.ENDC}")
            if not valid_changes:
                print(f"{Colors.RED}✗ Todos los cambios tienen errores. No se aplica PUT.{Colors.ENDC}")
                results.append({'status': 'error', 'release_id': release_id, 'changes': 0, 'errors': len(error_changes)})
                continue

            dry_run_active = getattr(args, 'dry_run', False) or getattr(args, 'tpl_dry_run', False)
            if dry_run_active:
                print(f"\n{Colors.YELLOW}🔍 DRY-RUN: No se aplicaron cambios.{Colors.ENDC}")
                results.append({'status': 'dry_run', 'release_id': release_id, 'changes': len(changes)})
                continue

            # FASE 3: Backup
            print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}FASE 3: Crear Backup{Colors.ENDC}")
            print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            backup_file, version_label = create_backup(release, args.backup_path)
            print(f"{Colors.GREEN}✓ Backup guardado: {backup_file}{Colors.ENDC}")
            print(f"{Colors.YELLOW}  Version: {version_label}{Colors.ENDC}")

            # FASE 4: Aplicar PUT
            print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            print(f"{Colors.BOLD}FASE 4: Aplicar PUT{Colors.ENDC}")
            print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
            # Fusionar payload con el release completo para PUT
            full_payload = copy.deepcopy(release)
            full_payload.update(payload)
            updated = update_release(args.org, args.project, int(release_id), full_payload, args.pat)

            # Resumen
            print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
            print(f"{Colors.GREEN}✅ UPDATE EXITOSO (Release {idx}/{total}){Colors.ENDC}")
            print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
            print(f"{Colors.GREEN}Release ID:     #{updated.get('id')}{Colors.ENDC}")
            print(f"{Colors.GREEN}Nombre:         {updated.get('name')}{Colors.ENDC}")
            print(f"{Colors.GREEN}Status:         {updated.get('status')}{Colors.ENDC}")
            print(f"{Colors.YELLOW}Backup:         {version_label}{Colors.ENDC}")
            print(f"{Colors.CYAN}Cambios:        {len(changes)}{Colors.ENDC}")
            print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

            stats = {
                'source_release_id': release.get('id'),
                'source_release_name': release.get('name'),
                'source_release_status': release.get('status'),
                'version_label': version_label,
            }
            report_path = export_report(stats, args, backup_file, updated, changes)
            print(f"{Colors.CYAN}📄 Reporte exportado: {report_path}{Colors.ENDC}\n")

            results.append({
                'status': 'success', 'release_id': release_id,
                'updated_id': updated.get('id'), 'changes': len(changes),
                'backup': version_label
            })

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}>>> Proceso interrumpido (Release {idx}/{total}){Colors.ENDC}")
            results.append({'status': 'cancelled', 'release_id': release_id, 'error': 'Interrumpido'})
        except Exception as e:
            print(f"\n{Colors.RED}>>> ERROR en Release #{release_id}: {e}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            results.append({'status': 'error', 'release_id': release_id, 'error': str(e)})

    # Resumen final
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  RESUMEN FINAL{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'error')
    cancelled = sum(1 for r in results if r['status'] == 'cancelled')
    dry_run = sum(1 for r in results if r['status'] == 'dry_run')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    print(f"{Colors.GREEN}✅ Exitosos: {successful}/{total}{Colors.ENDC}")
    if dry_run > 0:
        print(f"{Colors.CYAN}🔍 Dry-run:  {dry_run}/{total}{Colors.ENDC}")
    if skipped > 0:
        print(f"{Colors.YELLOW}⏭  Saltados:  {skipped}/{total}{Colors.ENDC}")
    if failed > 0:
        print(f"{Colors.RED}❌ Errores:   {failed}/{total}{Colors.ENDC}")
    if cancelled > 0:
        print(f"{Colors.YELLOW}⏸  Cancelados: {cancelled}/{total}{Colors.ENDC}")
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    return 0 if failed == 0 and cancelled == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
