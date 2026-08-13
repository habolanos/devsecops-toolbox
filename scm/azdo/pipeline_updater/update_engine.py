"""
Motor de actualización para Pipeline Updater
"""

import copy
import fnmatch
import json
import re
from typing import Dict, List, Any
from .models import Match, TemplateOptions


class UpdateEngine:
    """Motor de actualización de definiciones de release"""
    
    def __init__(self, definition: Dict, matches: List[Match], update_rules: Dict, template_options: TemplateOptions = None):
        """
        Inicializar motor de actualización
        
        Args:
            definition: Definición de release
            matches: Coincidencias encontradas
            update_rules: Reglas de actualización
            template_options: Opciones del template
        """
        self.definition = definition
        self.matches = matches
        self.update_rules = update_rules
        self.template_options = template_options or TemplateOptions()
        self.changes: List[Dict] = []
    
    def apply_updates(self) -> bool:
        """
        Aplicar todas las actualizaciones
        
        Returns:
            True si todas las actualizaciones fueron exitosas
        """
        try:
            # Primero remover variable groups ignorados si están configurados
            if self.template_options.ignore_variable_groups:
                self._remove_ignored_variable_groups()
            
            # Reemplazar agent pools si están configurados
            if self.template_options.replace_agent_pools:
                self._replace_agent_pools()
            
            stage_rules = self.update_rules.get('stages', [])
            
            # Primero procesar acciones de stage (copy/add/rename) que modifican stages
            if stage_rules and any(rule.get('action') in ('copy', 'add', 'rename') for rule in stage_rules):
                self._process_stage_actions(stage_rules)
            
            # Luego aplicar reordenamiento de stages si existe
            if stage_rules and any(rule.get('rank') for rule in stage_rules):
                self._reorder_stages(stage_rules)
            
            # Procesar inserción de tasks nuevas en stages existentes
            task_rules = self.update_rules.get('tasks', [])
            if task_rules and any(rule.get('action') == 'add' for rule in task_rules):
                self._process_add_task_actions(task_rules)
            
            # Procesar acciones de triggers (add/update/remove)
            trigger_rules = self.update_rules.get('triggers', [])
            if trigger_rules and any(rule.get('action') for rule in trigger_rules):
                self._process_trigger_actions(trigger_rules)
            
            # Luego aplicar otras actualizaciones
            for match in self.matches:
                if match.type == 'task':
                    self._update_task(match)
                elif match.type == 'variable':
                    self._update_variable(match)
                elif match.type == 'stage':
                    self._update_stage(match)
                elif match.type == 'artifact':
                    self._update_artifact(match)
                elif match.type == 'trigger':
                    self._update_trigger(match)
            
            return True
        except Exception as e:
            print(f"Error al aplicar actualizaciones: {e}")
            return False
    
    def _reorder_stages(self, stage_rules: List[Dict]):
        """
        Reordenar stages según las reglas
        
        Args:
            stage_rules: Reglas de actualización de stages con rank
        """
        environments = self.definition.get('environments', [])
        
        # Crear mapeo de nombre -> stage y rank
        stage_map = {}
        for rule in stage_rules:
            stage_name = rule.get('name', '')
            rank = rule.get('rank')
            if rank is None and rule.get('definition'):
                rank = rule['definition'].get('rank')
            if stage_name and rank is not None:
                stage_map[stage_name] = rank
        
        # Encontrar stages que necesitan reordenamiento
        stages_to_reorder = []
        for stage in environments:
            stage_name = stage.get('name', '')
            if stage_name in stage_map:
                stages_to_reorder.append((stage, stage_map[stage_name], stage_name))
        
        # Ordenar por rank
        stages_to_reorder.sort(key=lambda x: x[1])
        
        # Reordenar en la definición
        if stages_to_reorder:
            # IMPORTANTE: En Azure DevOps el orden de los stages lo determina el
            # campo 'rank' de cada environment, NO la posición en el array. Por eso
            # se DEBE asignar el nuevo rank a cada stage; reordenar solo el array no
            # tiene efecto porque el servidor reordena por 'rank'.
            for stage, rank, name in stages_to_reorder:
                old_rank = stage.get('rank')
                stage['rank'] = rank
                
                self.changes.append({
                    'type': 'stage_reorder',
                    'stage': name,
                    'old_rank': old_rank,
                    'new_rank': rank
                })
            
            # Reordenar también el array por rank (por consistencia/legibilidad)
            reorder_names = {name for _, _, name in stages_to_reorder}
            other_stages = [s for s in environments if s.get('name', '') not in reorder_names]
            
            new_environments = [stage for stage, _, _ in stages_to_reorder]
            new_environments.extend(other_stages)
            
            # Azure DevOps requiere que los ranks sean números consecutivos
            # empezando desde 1 para TODOS los stages. Si el template solo
            # especifica ranks para algunos stages, los demás conservan su
            # rank original, lo que puede crear ranks duplicados o no
            # consecutivos. Renumerar todos los stages consecutivamente.
            for i, stage in enumerate(new_environments):
                old_rank = stage.get('rank')
                new_rank = i + 1
                if old_rank != new_rank:
                    stage['rank'] = new_rank
                    self.changes.append({
                        'type': 'stage_reorder',
                        'stage': stage.get('name', ''),
                        'old_rank': old_rank,
                        'new_rank': new_rank
                    })
            
            self.definition['environments'] = new_environments
    
    def _process_stage_actions(self, stage_rules: List[Dict]):
        """
        Procesar acciones de stage que modifican o insertan environments.
        
        Soporta:
          - action: "copy"  -> Copia un stage existente (source_stage) y lo inserta
                               con un nuevo nombre (new_name).
          - action: "add"   -> Inserta un stage nuevo desde una definición embebida.
          - action: "rename" -> Renombra un stage existente (source_stage) a new_name.
        
        Parámetros de la regla:
          - action: "copy"
          - source_stage: nombre del stage a copiar (obligatorio)
          - new_name: nombre del nuevo stage insertado (obligatorio)
          - position: "after" | "before" | "start" | "end" (default: "after")
          - reference_stage: stage ancla para after/before (default: source_stage)
          - task_updates: lista opcional de modificaciones a tasks del stage copiado:
                - task_name: displayName de la task (soporta comodines)
                  fields:
                    - path: "inputs.namespace"
                      new_value: "..."
        
          - action: "add"
          - name: nombre del nuevo stage (obligatorio)
          - definition: definición completa del stage (obligatorio)
          - position: "after" | "before" | "between" | "start" | "end"
          - after_stage / before_stage: para position "between"
        
          - action: "rename"
          - source_stage: nombre del stage a renombrar (obligatorio)
          - new_name: nuevo nombre del stage (obligatorio)
        
        Args:
            stage_rules: Reglas de actualización de stages
        """
        for rule in stage_rules:
            action = rule.get('action')
            if action == 'copy':
                self._copy_stage(rule)
            elif action == 'add':
                self._add_stage(rule)
            elif action == 'rename':
                self._rename_stage(rule)
    
    def _copy_stage(self, rule: Dict):
        """Copiar un stage existente e insertarlo con un nuevo nombre."""
        environments = self.definition.get('environments', [])
        
        source_name = rule.get('source_stage')
        new_name = rule.get('new_name') or rule.get('name')
        
        if not source_name or not new_name:
            raise ValueError("action 'copy' requiere 'source_stage' y 'new_name'")
        
        # Localizar el stage origen
        source_stage = None
        for stage in environments:
            if stage.get('name', '') == source_name:
                source_stage = stage
                break
        
        if source_stage is None:
            raise ValueError(f"source_stage '{source_name}' no encontrado en el pipeline")
        
        # Clonar y renombrar
        new_stage = copy.deepcopy(source_stage)
        new_stage['name'] = new_name
        new_stage['id'] = self._next_environment_id(environments)
        
        # Aplicar modificaciones de tasks al stage copiado
        task_updates = rule.get('task_updates', [])
        if task_updates:
            self._apply_task_updates_to_stage(new_stage, task_updates, new_name)
        
        # Determinar posición de inserción
        insert_index = self._resolve_insert_index(environments, rule, source_name)
        environments.insert(insert_index, new_stage)
        
        # Reasignar ranks según el orden del array (rank gobierna el orden en AzDO)
        self._resequence_ranks(environments)
        
        self.definition['environments'] = environments
        
        self.changes.append({
            'type': 'stage_copy',
            'source_stage': source_name,
            'new_stage': new_name,
            'position_index': insert_index,
            'new_rank': new_stage.get('rank')
        })
    
    def _add_stage(self, rule: Dict):
        """Insertar un stage nuevo a partir de una definicion embebida."""
        environments = self.definition.get('environments', [])
        
        definition = rule.get('definition')
        new_name = rule.get('name') or (definition.get('name') if definition else None)
        
        if not definition or not new_name:
            raise ValueError("action 'add' requiere 'definition' y 'name'")
        
        new_stage = copy.deepcopy(definition)
        new_stage['name'] = new_name
        new_stage['id'] = self._next_environment_id(environments)
        
        # Aplicar modificaciones de tasks al stage insertado (opcional)
        task_updates = rule.get('task_updates', [])
        if task_updates:
            self._apply_task_updates_to_stage(new_stage, task_updates, new_name)
        
        # Sobrescribir el trigger del stage copiado (opcional)
        trigger = rule.get('trigger')
        if trigger is not None:
            self._apply_trigger_override(new_stage, trigger, rule, new_name)
        
        # Agregar artifact filters al stage copiado (opcional)
        artifact_filters = rule.get('artifact_filters', [])
        if artifact_filters:
            self._apply_artifact_filters(new_stage, artifact_filters, new_name)
        
        insert_index = self._resolve_insert_index(
            environments, rule, rule.get('after_stage')
        )
        environments.insert(insert_index, new_stage)
        
        self._resequence_ranks(environments)
        self.definition['environments'] = environments
        
        # Hacer que otros stages dependan del nuevo stage (opcional)
        make_dependents = rule.get('make_dependents', [])
        if make_dependents:
            self._apply_make_dependents(environments, make_dependents, new_name)
        
        self.changes.append({
            'type': 'stage_add',
            'new_stage': new_name,
            'position_index': insert_index,
            'new_rank': new_stage.get('rank')
        })
    
    def _rename_stage(self, rule: Dict):
        """Renombrar un stage existente y actualizar referencias de dependencia."""
        environments = self.definition.get('environments', [])

        source_name = rule.get('source_stage')
        new_name = rule.get('new_name')

        if not source_name or not new_name:
            raise ValueError("action 'rename' requiere 'source_stage' y 'new_name'")

        # Si el source_stage no existe, skip silencioso (no-op).
        # Permite que un template cubra multiples variantes de pipelines
        # donde algunos tienen "Texcoco" y otros "Cedis Texcoco".
        existing_names = [stage.get('name', '') for stage in environments]
        if source_name not in existing_names:
            return

        # Si el new_name ya existe como un stage distinto, skip silencioso.
        # El pipeline puede ya tener el stage con el nombre destino (ej:
        # ya tiene "Production" y no necesita renombrar "Texcoco").
        if new_name in existing_names and new_name != source_name:
            return

        # Localizar el stage a renombrar
        for stage in environments:
            if stage.get('name', '') == source_name:
                old_name = stage['name']
                stage['name'] = new_name

                self.changes.append({
                    'type': 'stage_rename',
                    'old_name': old_name,
                    'new_name': new_name
                })
                break

        # Actualizar referencias al nombre viejo en las dependencias de otros stages
        # Las dependencias entre stages en Azure DevOps se almacenan en:
        # 1. environment.conditions[] (conditionType=environmentState, name=stage_referenciado)
        # 2. deployPhases[].deploymentInput.condition (string con succeeded('StageName'))
        for stage in environments:
            # 1. Actualizar environment.conditions[]
            conditions = stage.get('conditions', [])
            for condition in conditions:
                if condition.get('name') == source_name:
                    condition['name'] = new_name
                    self.changes.append({
                        'type': 'stage_dependency_update',
                        'stage': stage.get('name', ''),
                        'field': 'conditions',
                        'old_ref': source_name,
                        'new_ref': new_name
                    })

            # 2. Actualizar deployPhases[].deploymentInput.condition (string)
            deploy_phases = stage.get('deployPhases', [])
            for phase in deploy_phases:
                deployment_input = phase.get('deploymentInput', {})
                cond_str = deployment_input.get('condition', '')
                if source_name in cond_str:
                    new_cond = cond_str.replace(f"'{source_name}'", f"'{new_name}'")
                    deployment_input['condition'] = new_cond
                    self.changes.append({
                        'type': 'stage_dependency_update',
                        'stage': stage.get('name', ''),
                        'field': 'deploymentInput.condition',
                        'old_ref': source_name,
                        'new_ref': new_name
                    })

        self.definition['environments'] = environments
    
    def _process_add_task_actions(self, task_rules: List[Dict]):
        """
        Procesar acciones de inserción de tasks nuevas dentro de stages existentes.
        
        Soporta reglas con action='add' que insertan una task nueva:
          - before_task: displayName de la task existente antes de la cual insertar
          - after_task: displayName de la task existente después de la cual insertar
          - stage: nombre del stage donde insertar (opcional, default: todos los stages)
          - task: definición completa de la task a insertar
        
        Args:
            task_rules: Reglas de actualización de tasks
        """
        environments = self.definition.get('environments', [])
        
        for rule in task_rules:
            if rule.get('action') != 'add':
                continue
            
            task_def = rule.get('task')
            if not task_def:
                raise ValueError("action 'add' en tasks requiere 'task' con la definición")
            
            before_task_name = rule.get('before_task')
            after_task_name = rule.get('after_task')
            target_stage_name = rule.get('stage')
            
            if not before_task_name and not after_task_name:
                raise ValueError("action 'add' en tasks requiere 'before_task' o 'after_task'")
            
            for stage in environments:
                stage_name = stage.get('name', '')
                
                # Filtrar por stage si se especifica
                if target_stage_name and stage_name != target_stage_name:
                    continue
                
                for phase in stage.get('deployPhases', []):
                    deployment_input = phase.get('deploymentInput', {})
                    tasks = deployment_input.get('tasks', [])
                    
                    insert_index = None
                    if before_task_name:
                        for idx, t in enumerate(tasks):
                            if fnmatch.fnmatch(t.get('displayName', ''), before_task_name):
                                insert_index = idx
                                break
                    elif after_task_name:
                        for idx, t in enumerate(tasks):
                            if fnmatch.fnmatch(t.get('displayName', ''), after_task_name):
                                insert_index = idx + 1
                                break
                    
                    if insert_index is not None:
                        new_task = copy.deepcopy(task_def)
                        tasks.insert(insert_index, new_task)
                        
                        self.changes.append({
                            'type': 'task_add',
                            'stage': stage_name,
                            'task': new_task.get('displayName', ''),
                            'before_task': before_task_name or '',
                            'after_task': after_task_name or '',
                            'position': insert_index
                        })
    
    def _process_trigger_actions(self, trigger_rules: List[Dict]):
        """
        Procesar acciones de triggers (add/update/remove) en la definicion de release.
        
        Azure DevOps almacena triggers en definition.triggers[] con:
          - triggerType: "artifactSource" | "schedule" | "sourcePullRequest"
          - triggerConfiguration: {
              triggerType, artifactName, branchFilters: ["+refs/heads/main"],
              useDefaultBranch, scheduleDays, scheduleTime, ...
            }
        
        Soporta:
          - action: "add"    -> Agrega un nuevo trigger
          - action: "update" -> Actualiza branchFilters u otros campos de un trigger existente
          - action: "remove" -> Elimina un trigger existente
        
        Soporta artifactName: "$auto" que se resuelve dinamicamente al primer
        Build artifact del pipeline. "$auto:Git" resuelve al primer Git artifact.
        
        Args:
            trigger_rules: Reglas de actualizacion de triggers
        """
        triggers = self.definition.get('triggers', [])
        
        for rule in trigger_rules:
            action = rule.get('action')
            
            if action == 'add':
                trigger_type = rule.get('triggerType', 'artifactSource')
                trigger_config = rule.get('triggerConfiguration', {})
                
                # Resolver $auto en artifactName
                if trigger_config.get('artifactName', '').startswith('$auto'):
                    trigger_config = copy.deepcopy(trigger_config)
                    trigger_config['artifactName'] = self._resolve_artifact_name(
                        trigger_config['artifactName']
                    )
                
                new_trigger = {
                    'triggerType': trigger_type,
                    'triggerConfiguration': trigger_config
                }
                
                triggers.append(new_trigger)
                
                self.changes.append({
                    'type': 'trigger_add',
                    'triggerType': trigger_type,
                    'artifactName': trigger_config.get('artifactName', '')
                })
            
            elif action == 'update':
                target_type = rule.get('triggerType')
                target_artifact = rule.get('artifactName', '')
                
                # Resolver $auto en artifactName para matching
                if target_artifact.startswith('$auto'):
                    target_artifact = self._resolve_artifact_name(target_artifact)
                
                fields = rule.get('fields', [])
                
                for trigger in triggers:
                    trig_type = trigger.get('triggerType', '')
                    trig_config = trigger.get('triggerConfiguration', {})
                    trig_artifact = trig_config.get('artifactName', '')
                    
                    if target_type and trig_type != target_type:
                        continue
                    if target_artifact and trig_artifact != target_artifact:
                        continue
                    
                    for field_update in fields:
                        path = field_update.get('path')
                        new_value = field_update.get('new_value')
                        old_value = self._get_nested_value(trig_config, path)
                        self._set_nested_value(trig_config, path, new_value)
                        
                        self.changes.append({
                            'type': 'trigger_update',
                            'triggerType': trig_type,
                            'artifactName': trig_artifact,
                            'field': path,
                            'old': old_value,
                            'new': new_value
                        })
            
            elif action == 'remove':
                target_type = rule.get('triggerType')
                target_artifact = rule.get('artifactName', '')
                
                # Resolver $auto en artifactName para matching
                if target_artifact.startswith('$auto'):
                    target_artifact = self._resolve_artifact_name(target_artifact)
                
                original_len = len(triggers)
                triggers = [
                    t for t in triggers
                    if not (
                        (not target_type or t.get('triggerType', '') == target_type) and
                        (not target_artifact or
                         t.get('triggerConfiguration', {}).get('artifactName', '') == target_artifact)
                    )
                ]
                
                if len(triggers) < original_len:
                    self.changes.append({
                        'type': 'trigger_remove',
                        'triggerType': target_type or '',
                        'artifactName': target_artifact or '',
                        'removed_count': original_len - len(triggers)
                    })
        
        self.definition['triggers'] = triggers
    
    def _resolve_artifact_name(self, token: str) -> str:
        """
        Resolver un token $auto al alias real del artifact del pipeline.
        
        Tokens soportados:
          - "$auto"     -> primer Build artifact
          - "$auto:Git" -> primer Git artifact
          - "$auto:Build" -> primer Build artifact (explicito)
        
        Si el token no empieza con $auto, se retorna tal cual.
        Si no se encuentra ningun artifact del tipo solicitado, se retorna "".
        
        Args:
            token: Token a resolver (ej: "$auto", "$auto:Git", "_myartifact")
        
        Returns:
            Alias del artifact resuelto, o string vacio si no se encuentra
        """
        if not token or not token.startswith('$auto'):
            return token
        
        # Determinar tipo de artifact solicitado
        artifact_type = 'Build'
        if ':' in token:
            artifact_type = token.split(':', 1)[1]
        
        # Buscar en los artifacts de la definicion
        for artifact in self.definition.get('artifacts', []):
            if artifact.get('type', '') == artifact_type:
                return artifact.get('alias', '')
        
        return ''
    
    def _update_trigger(self, match: Match):
        """
        Actualizar un trigger encontrado por search.
        
        Aplica reglas de update.triggers que no tienen 'action' (updates via fields).
        
        Args:
            match: Coincidencia de trigger
        """
        trigger = match.object
        trigger_rules = self.update_rules.get('triggers', [])
        
        for rule in trigger_rules:
            if rule.get('action'):
                continue
            
            rule_type = rule.get('triggerType', '')
            if rule_type and rule_type != match.name:
                continue
            
            trig_config = trigger.get('triggerConfiguration', {})
            for field_update in rule.get('fields', []):
                path = field_update.get('path')
                new_value = field_update.get('new_value')
                old_value = self._get_nested_value(trig_config, path)
                self._set_nested_value(trig_config, path, new_value)
                
                self.changes.append({
                    'type': 'trigger_update',
                    'triggerType': match.name,
                    'field': path,
                    'old': old_value,
                    'new': new_value
                })
    
    def _remove_ignored_variable_groups(self):
        """
        Remover referencias a variable groups segun el scope configurado.
        
        Scope 'global' o 'all': remueve de definition.variableGroups
        Scope 'environments' o 'all': remueve de environments[].variableGroups
        """
        ignore_vg = self.template_options.ignore_variable_groups
        if not ignore_vg.has_any():
            return
        
        global_ignore = ignore_vg.ids_for_global()
        env_ignore = ignore_vg.ids_for_environments()
        
        # 1. Remover grupos a nivel global del pipeline
        if global_ignore:
            global_groups = self.definition.get('variableGroups', [])
            if global_groups:
                valid_global = [g for g in global_groups if g not in global_ignore]
                removed_global = [g for g in global_groups if g in global_ignore]
                if removed_global:
                    self.definition['variableGroups'] = valid_global
                    self.changes.append({
                        'type': 'variable_groups_removed',
                        'scope': 'global',
                        'removed_ids': removed_global
                    })
        
        # 2. Remover grupos a nivel de environments
        if env_ignore:
            for env in self.definition.get('environments', []):
                current_groups = env.get('variableGroups', [])
                if not current_groups:
                    continue
                
                valid_groups = [g for g in current_groups if g not in env_ignore]
                removed = [g for g in current_groups if g in env_ignore]
                if removed:
                    env['variableGroups'] = valid_groups
                    self.changes.append({
                        'type': 'variable_groups_removed',
                        'scope': 'environment',
                        'environment': env.get('name', 'Unknown'),
                        'removed_ids': removed
                    })
    
    def _replace_agent_pools(self):
        """
        Reemplazar agent pool IDs (queueId) segun el mapeo configurado.

        Busca queueId en deployPhases[].deploymentInput de cada environment
        y reemplaza los IDs viejos por los nuevos especificados.
        """
        replace_pools = self.template_options.replace_agent_pools
        if not replace_pools.has_any():
            return

        mappings = replace_pools.mappings

        for env in self.definition.get('environments', []):
            env_name = env.get('name', 'Unknown')

            for phase in env.get('deployPhases', []):
                deployment_input = phase.get('deploymentInput', {})
                current_queue_id = deployment_input.get('queueId')

                if current_queue_id is not None and current_queue_id in mappings:
                    new_queue_id = mappings[current_queue_id]
                    deployment_input['queueId'] = new_queue_id

                    # Actualizar tambien el objeto queue si existe
                    queue_obj = deployment_input.get('queue', {})
                    if queue_obj:
                        queue_obj['id'] = new_queue_id

                    self.changes.append({
                        'type': 'agent_pool_replaced',
                        'environment': env_name,
                        'old_queue_id': current_queue_id,
                        'new_queue_id': new_queue_id
                    })

    def _resolve_insert_index(self, environments: List[Dict], rule: Dict, default_ref: str) -> int:
        """
        Resolver el índice de inserción en el array de environments.
        
        position: "after" (default) | "before" | "between" | "start" | "end"
        reference_stage / after_stage / before_stage: stage ancla.
        
        Para "between": requiere after_stage y before_stage.
        """
        position = (rule.get('position') or 'after').lower()
        
        if position == 'start':
            return 0
        if position == 'end':
            return len(environments)
        
        if position == 'between':
            after_stage = rule.get('after_stage')
            before_stage = rule.get('before_stage')
            if not after_stage or not before_stage:
                raise ValueError("position 'between' requiere 'after_stage' y 'before_stage'")
            
            after_index = None
            before_index = None
            for idx, stage in enumerate(environments):
                name = stage.get('name', '')
                if name == after_stage:
                    after_index = idx
                if name == before_stage:
                    before_index = idx
            
            # Si no se encuentran ambos, insertar al final
            if after_index is None or before_index is None:
                return len(environments)
            
            # Insertar justo después de after_stage (antes de before_stage)
            return after_index + 1
        
        reference = (
            rule.get('reference_stage')
            or rule.get('after_stage')
            or rule.get('before_stage')
            or default_ref
        )
        
        ref_index = None
        for idx, stage in enumerate(environments):
            if stage.get('name', '') == reference:
                ref_index = idx
                break
        
        # Si no se encuentra la referencia, insertar al final
        if ref_index is None:
            return len(environments)
        
        if position == 'before':
            return ref_index
        # default: after
        return ref_index + 1
    
    def _next_environment_id(self, environments: List[Dict]) -> int:
        """Obtener un id para un nuevo environment.
        
        Azure DevOps requiere que los stages nuevos tengan id < 1.
        El servidor asigna el id real al guardar la definicion.
        """
        return 0
    
    def _resequence_ranks(self, environments: List[Dict]):
        """Reasignar ranks secuenciales (1..N) según el orden actual del array."""
        for idx, stage in enumerate(environments):
            stage['rank'] = idx + 1
    
    def _apply_trigger_override(self, stage: Dict, trigger: str, rule: Dict, stage_name: str):
        """
        Sobrescribir las conditions[] (trigger) del stage copiado.
        
        Opciones:
          - "after_release": trigger automático al iniciar el release.
          - "after_stage":   depende de reference_stage (o after_stage).
          - "none":          sin conditions (ejecución manual).
        
        Preserva artifact filters (conditionType: "artifact").
        """
        artifact_conditions = [
            c for c in stage.get('conditions', [])
            if c.get('conditionType') == 'artifact'
        ]
        
        if trigger == 'after_release':
            new_conditions = [{
                'name': 'ReleaseStarted',
                'conditionType': 'event',
                'value': '',
                'result': None
            }]
        elif trigger == 'after_stage':
            ref = rule.get('reference_stage') or rule.get('after_stage', '')
            if not ref:
                raise ValueError(
                    "trigger 'after_stage' requiere 'reference_stage' "
                    "o 'after_stage' en la regla"
                )
            new_conditions = [{
                'name': ref,
                'conditionType': 'environmentState',
                'value': '4',
                'result': None
            }]
        elif trigger == 'none':
            new_conditions = []
        else:
            raise ValueError(
                f"trigger '{trigger}' no válido. "
                "Usar: after_release | after_stage | none"
            )
        
        new_conditions.extend(artifact_conditions)
        stage['conditions'] = new_conditions
        
        self.changes.append({
            'type': 'stage_trigger_override',
            'stage': stage_name,
            'trigger': trigger,
            'reference': rule.get('reference_stage') or rule.get('after_stage', '')
        })
    
    def _apply_make_dependents(self, environments: List[Dict], make_dependents: List[Dict], new_stage_name: str):
        """
        Hacer que stages existentes dependan del stage recién insertado.
        
        Reemplaza las conditions de tipo 'environmentState' y 'event' por una
        dependencia al nuevo stage. Preserva artifact filters.
        """
        for dep in make_dependents:
            target_stage_name = dep.get('stage')
            if not target_stage_name:
                continue
            
            for stage in environments:
                if stage.get('name', '') != target_stage_name:
                    continue
                
                artifact_conditions = [
                    c for c in stage.get('conditions', [])
                    if c.get('conditionType') == 'artifact'
                ]
                
                stage['conditions'] = [{
                    'name': new_stage_name,
                    'conditionType': 'environmentState',
                    'value': '4',
                    'result': None
                }] + artifact_conditions
                
                self.changes.append({
                    'type': 'stage_dependency_update',
                    'stage': target_stage_name,
                    'field': 'conditions',
                    'old_ref': '(replaced)',
                    'new_ref': new_stage_name
                })
                break
    
    def _apply_artifact_filters(self, stage: Dict, artifact_filters: List[Dict], stage_name: str):
        """
        Agregar artifact filters (conditions de tipo artifact) al stage copiado.
        
        Cada filtro especifica:
          - artifact: alias del artifact o token $auto / $auto:Git
          - type: "include" | "exclude" (default: "include")
          - branches: lista de nombres de branch (ej: ["develop", "QA", "release/*"])
        
        Las branches con wildcards (ej: release/*) se expanden a formato
        Azure DevOps: +refs/heads/release/*
        
        Si el stage ya tiene artifact conditions, se reemplazan por las nuevas.
        Las conditions de tipo event/environmentState se preservan.
        """
        non_artifact_conditions = [
            c for c in stage.get('conditions', [])
            if c.get('conditionType') != 'artifact'
        ]
        
        new_artifact_conditions = []
        
        for filt in artifact_filters:
            artifact_token = filt.get('artifact', '$auto:Git')
            filter_type = filt.get('type', 'include')
            branches = filt.get('branches', [])
            
            alias = self._resolve_artifact_name(artifact_token)
            if not alias:
                print(f"  ⚠ artifact_filters: no se encontro artifact para "
                      f"token '{artifact_token}' en el pipeline, se omite el filtro")
                continue
            
            for branch in branches:
                condition_value = json.dumps({
                    'sourceBranch': branch,
                    'alias': alias
                })
                new_artifact_conditions.append({
                    'name': alias,
                    'conditionType': 'artifact',
                    'value': condition_value,
                    'result': None
                })
            
            self.changes.append({
                'type': 'stage_artifact_filter',
                'stage': stage_name,
                'artifact': alias,
                'filter_type': filter_type,
                'branches': branches
            })
        
        stage['conditions'] = non_artifact_conditions + new_artifact_conditions
    
    def _apply_task_updates_to_stage(self, stage: Dict, task_updates: List[Dict], stage_name: str):
        """
        Aplicar modificaciones de atributos a tasks dentro de un stage.
        
        Args:
            stage: Stage (environment) sobre el que aplicar cambios
            task_updates: Lista de reglas {task_name, fields:[{path, new_value}]}
            stage_name: Nombre del stage (para el registro de cambios)
        """
        for phase in stage.get('deployPhases', []):
            tasks = phase.get('deploymentInput', {}).get('tasks', [])
            for task in tasks:
                display_name = task.get('displayName', '')
                for tu in task_updates:
                    task_name = tu.get('task_name', tu.get('name', ''))
                    if task_name and not fnmatch.fnmatch(display_name, task_name):
                        continue
                    for field_update in tu.get('fields', []):
                        path = field_update.get('path')
                        new_value = field_update.get('new_value')
                        old_value = self._get_nested_value(task, path)
                        self._set_nested_value(task, path, new_value)
                        
                        self.changes.append({
                            'type': 'copied_task_field',
                            'stage': stage_name,
                            'task': display_name,
                            'field': path,
                            'old': old_value,
                            'new': new_value
                        })
    
    def _update_task(self, match: Match):
        """
        Actualizar una task
        
        Args:
            match: Coincidencia de task
        """
        task = match.object
        task_rules = self.update_rules.get('tasks', [])
        
        for rule in task_rules:
            if self._rule_matches_match(rule, match):
                # Actualizar campos
                for field_update in rule.get('fields', []):
                    path = field_update.get('path')
                    new_value = field_update.get('new_value')
                    old_value = self._get_nested_value(task, path)
                    
                    self._set_nested_value(task, path, new_value)
                    
                    self.changes.append({
                        'type': 'task_field',
                        'stage': match.stage_name,
                        'task': match.name,
                        'field': path,
                        'old': old_value,
                        'new': new_value
                    })
    
    def _update_variable(self, match: Match):
        """
        Actualizar una variable
        
        Args:
            match: Coincidencia de variable
        """
        var = match.object
        var_rules = self.update_rules.get('variables', [])
        
        for rule in var_rules:
            if self._rule_matches_match(rule, match):
                old_value = var.get('value')
                new_value = rule.get('new_value')
                
                var['value'] = new_value
                
                self.changes.append({
                    'type': 'variable',
                    'name': match.name,
                    'old': old_value,
                    'new': new_value
                })
    
    def _update_stage(self, match: Match):
        """
        Actualizar un stage
        
        Args:
            match: Coincidencia de stage
        """
        stage = match.object
        stage_rules = self.update_rules.get('stages', [])
        
        for rule in stage_rules:
            if self._rule_matches_match(rule, match):
                # Actualizar propiedades del stage (formato 'properties')
                for prop_update in rule.get('properties', []):
                    path = prop_update.get('path')
                    new_value = prop_update.get('new_value')
                    old_value = self._get_nested_value(stage, path)
                    
                    self._set_nested_value(stage, path, new_value)
                    
                    self.changes.append({
                        'type': 'stage_property',
                        'stage': match.name,
                        'property': path,
                        'old': old_value,
                        'new': new_value
                    })
                
                # Actualizar campos del stage (formato 'fields')
                for field_update in rule.get('fields', []):
                    path = field_update.get('path')
                    new_value = field_update.get('new_value')
                    old_value = self._get_nested_value(stage, path)
                    
                    self._set_nested_value(stage, path, new_value)
                    
                    self.changes.append({
                        'type': 'stage_field',
                        'stage': match.name,
                        'field': path,
                        'old': old_value,
                        'new': new_value
                    })
    
    def _update_artifact(self, match: Match):
        """
        Actualizar un artifact
        
        Soporta actualizacion de propiedades via 'fields' y 'properties'.
        Tambien soporta actualizacion de branch filters via:
          - path: "definitionReference.branch.id" -> cambiar branch del artifact
          - path: "definitionReference.branch.name" -> cambiar nombre de branch
        
        Args:
            match: Coincidencia de artifact
        """
        artifact = match.object
        artifact_rules = self.update_rules.get('artifacts', [])
        
        for rule in artifact_rules:
            if rule.get('action'):
                continue
                
            if self._rule_matches_match(rule, match):
                # Actualizar propiedades del artifact (formato 'properties')
                for prop_update in rule.get('properties', []):
                    path = prop_update.get('path')
                    new_value = prop_update.get('new_value')
                    old_value = self._get_nested_value(artifact, path)
                    
                    self._set_nested_value(artifact, path, new_value)
                    
                    self.changes.append({
                        'type': 'artifact_property',
                        'artifact': match.name,
                        'property': path,
                        'old': old_value,
                        'new': new_value
                    })
                
                # Actualizar campos del artifact (formato 'fields')
                for field_update in rule.get('fields', []):
                    path = field_update.get('path')
                    new_value = field_update.get('new_value')
                    old_value = self._get_nested_value(artifact, path)
                    
                    self._set_nested_value(artifact, path, new_value)
                    
                    self.changes.append({
                        'type': 'artifact_field',
                        'artifact': match.name,
                        'field': path,
                        'old': old_value,
                        'new': new_value
                    })
    
    def _rule_matches_match(self, rule: Dict, match: Match) -> bool:
        """
        Verificar si una regla coincide con un match
        
        Args:
            rule: Regla de actualización
            match: Coincidencia
            
        Returns:
            True si la regla aplica al match
        """
        rule_name = rule.get('name', '')
        
        if rule_name and rule_name != match.name:
            return False
        
        return True
    
    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """
        Obtener valor en ruta anidada
        
        Soporta indices de array con notacion key[index]:
          ej: "preDeployApprovals.approvals[0].approver.displayName"
        
        Args:
            obj: Diccionario
            path: Ruta (ej: "inputs.imageRepository")
            
        Returns:
            Valor en la ruta
        """
        keys = path.split('.')
        current = obj
        
        for key in keys:
            current = self._navigate_key(current, key)
            if current is None:
                return None
        
        return current
    
    @staticmethod
    def _navigate_key(current: Any, key: str) -> Any:
        """
        Navegar una clave que puede contener un indice de array.
        
        Formatos soportados:
          - "key" -> dict[key]
          - "key[0]" -> dict[key][0]
          - "key[0][1]" -> dict[key][0][1]
        
        Args:
            current: Objeto actual (dict o list)
            key: Clave a navegar
        
        Returns:
            Valor en la ruta, o None si no existe
        """
        match = re.match(r'^(\w+)((?:\[\d+\])*)$', key)
        if not match:
            if isinstance(current, dict):
                return current.get(key)
            return None
        
        base_key = match.group(1)
        indices = match.group(2)
        
        if isinstance(current, dict):
            current = current.get(base_key)
        else:
            return None
        
        if current is None:
            return None
        
        for idx_match in re.finditer(r'\[(\d+)\]', indices):
            idx = int(idx_match.group(1))
            if isinstance(current, list) and 0 <= idx < len(current):
                current = current[idx]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, obj: Dict, path: str, value: Any):
        """
        Establecer valor en ruta anidada
        
        Soporta indices de array con notacion key[index]:
          ej: "preDeployApprovals.approvals[0].approver.displayName"
        
        Args:
            obj: Diccionario
            path: Ruta (ej: "inputs.imageRepository")
            value: Nuevo valor
        """
        keys = path.split('.')
        current = obj
        
        for key in keys[:-1]:
            current = self._navigate_and_create(current, key)
        
        self._navigate_and_set(current, keys[-1], value)
    
    @staticmethod
    def _navigate_and_create(current: Any, key: str) -> Any:
        """
        Navegar una clave que puede contener indices de array,
        creando estructuras intermedias si no existen.
        """
        match = re.match(r'^(\w+)((?:\[\d+\])*)$', key)
        if not match:
            if not isinstance(current, dict):
                return current
            if key not in current:
                current[key] = {}
            return current[key]
        
        base_key = match.group(1)
        indices = match.group(2)
        
        if not isinstance(current, dict):
            return current
        if base_key not in current:
            current[base_key] = [] if indices else {}
        
        current = current[base_key]
        
        for idx_match in re.finditer(r'\[(\d+)\]', indices):
            idx = int(idx_match.group(1))
            if not isinstance(current, list):
                return current
            while len(current) <= idx:
                current.append({})
            if not isinstance(current[idx], (dict, list)):
                current[idx] = {}
            current = current[idx]
        
        return current
    
    @staticmethod
    def _navigate_and_set(current: Any, key: str, value: Any):
        """
        Navegar una clave final que puede contener indices de array
        y establecer el valor.
        """
        match = re.match(r'^(\w+)((?:\[\d+\])*)$', key)
        if not match:
            if isinstance(current, dict):
                current[key] = value
            return
        
        base_key = match.group(1)
        indices = match.group(2)
        
        if not indices:
            if isinstance(current, dict):
                current[base_key] = value
            return
        
        if not isinstance(current, dict):
            return
        if base_key not in current:
            current[base_key] = []
        
        current = current[base_key]
        
        idx_matches = list(re.finditer(r'\[(\d+)\]', indices))
        for i, idx_match in enumerate(idx_matches):
            idx = int(idx_match.group(1))
            if not isinstance(current, list):
                return
            if i == len(idx_matches) - 1:
                while len(current) <= idx:
                    current.append(None)
                current[idx] = value
            else:
                while len(current) <= idx:
                    current.append({})
                if not isinstance(current[idx], (dict, list)):
                    current[idx] = {}
                current = current[idx]
    
    def get_changes(self) -> List[Dict]:
        """Obtener lista de cambios realizados"""
        return self.changes
    
    def get_changes_count(self) -> int:
        """Obtener cantidad de cambios realizados"""
        return len(self.changes)
