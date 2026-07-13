# 📐 Plan de Implementación

## 1. RESUMEN EJECUTIVO

**Objetivo**: Implementar herramienta de actualización masiva de pipelines CD  
**Duración estimada**: 40 horas (1 semana tiempo completo)  
**Complejidad**: Media-Alta  
**Riesgo**: Bajo (con validaciones y rollback)  

---

## 2. ESTRUCTURA DE MÓDULOS

```
scm/azdo/pipeline-updater/
├── __init__.py
├── config.py                    # Configuración
├── models.py                    # Dataclasses
├── template_parser.py           # Parser de templates
├── azdo_client.py              # Cliente AZDO
├── search_engine.py            # Motor de búsqueda
├── update_engine.py            # Motor de actualización
├── parallel_executor.py        # Ejecución paralela
├── reporter.py                 # Reportería
├── validator.py                # Validación
├── pipeline_updater.py         # Orquestador principal
├── test_pipeline_updater.py    # Tests unitarios
└── requirements.txt            # Dependencias
```

---

## 3. FASES DE IMPLEMENTACIÓN

### Fase 1: Setup y Modelos (8 horas)

#### 1.1 Crear estructura base
```bash
mkdir -p scm/azdo/pipeline-updater
touch scm/azdo/pipeline-updater/__init__.py
touch scm/azdo/pipeline-updater/config.py
touch scm/azdo/pipeline-updater/models.py
```

#### 1.2 Implementar config.py
```python
# Configuración de la herramienta
AZDO_API_VERSION = "7.1"
DEFAULT_WORKERS = 5
DEFAULT_TIMEOUT = 30
SNAPSHOT_DIR = "outcome/snapshots"
REPORT_DIR = "outcome/pipeline_updates"
```

**Duración**: 1 hora

#### 1.3 Implementar models.py
```python
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class SearchRule:
    stages: List[str]
    tasks: List[Dict]
    variables: List[str]
    artifacts: List[Dict]

@dataclass
class UpdateRule:
    tasks: List[Dict]
    variables: List[Dict]
    stages: List[Dict]

@dataclass
class TemplateMetadata:
    name: str
    version: str
    description: Optional[str]
    author: Optional[str]

@dataclass
class UpdateResult:
    definition_id: int
    success: bool
    snapshot_id: str
    matches_found: int
    changes_applied: int
    changes: List[Dict]
    error: Optional[str]
```

**Duración**: 2 horas

#### 1.4 Tests para modelos
```python
# test_models.py
def test_search_rule_creation():
    rule = SearchRule(stages=["Prod"], tasks=[], variables=[], artifacts=[])
    assert rule.stages == ["Prod"]

def test_update_result_success():
    result = UpdateResult(
        definition_id=3388,
        success=True,
        snapshot_id="snap_123",
        matches_found=2,
        changes_applied=2,
        changes=[],
        error=None
    )
    assert result.success is True
```

**Duración**: 2 horas

**Total Fase 1**: 8 horas

---

### Fase 2: Template Parser y Validación (6 horas)

#### 2.1 Implementar template_parser.py
```python
import yaml
from typing import Dict, Optional

class TemplateParser:
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.template = self._load_yaml()
        self.metadata = self.template.get('metadata', {})
        self.search_rules = self.template.get('search', {})
        self.update_rules = self.template.get('update', {})
        self.options = self.template.get('options', {})
    
    def _load_yaml(self) -> Dict:
        """Cargar YAML"""
        with open(self.template_path, 'r') as f:
            return yaml.safe_load(f)
    
    def validate(self) -> bool:
        """Validar estructura"""
        required = ['metadata', 'search', 'update']
        return all(k in self.template for k in required)
    
    def get_search_rules(self) -> Dict:
        """Obtener reglas de búsqueda"""
        return self.search_rules
    
    def get_update_rules(self) -> Dict:
        """Obtener reglas de actualización"""
        return self.update_rules
    
    def get_options(self) -> Dict:
        """Obtener opciones"""
        return self.options
```

**Duración**: 2 horas

#### 2.2 Implementar validator.py
```python
class TemplateValidator:
    def __init__(self, template: Dict):
        self.template = template
        self.errors = []
    
    def validate(self) -> bool:
        """Validar template completo"""
        self._validate_metadata()
        self._validate_search()
        self._validate_update()
        return len(self.errors) == 0
    
    def _validate_metadata(self):
        """Validar metadata"""
        meta = self.template.get('metadata', {})
        if not meta.get('name'):
            self.errors.append("metadata.name es obligatorio")
        if not meta.get('version'):
            self.errors.append("metadata.version es obligatorio")
    
    def _validate_search(self):
        """Validar search"""
        search = self.template.get('search', {})
        if not search:
            self.errors.append("search no puede estar vacío")
    
    def _validate_update(self):
        """Validar update"""
        update = self.template.get('update', {})
        if not update:
            self.errors.append("update no puede estar vacío")
```

**Duración**: 2 horas

#### 2.3 Tests
```python
def test_template_parser_valid():
    parser = TemplateParser('tests/fixtures/valid_template.yaml')
    assert parser.validate() is True

def test_template_validator_invalid():
    template = {'metadata': {}}  # Falta search y update
    validator = TemplateValidator(template)
    assert validator.validate() is False
    assert len(validator.errors) > 0
```

**Duración**: 2 horas

**Total Fase 2**: 6 horas

---

### Fase 3: Azure DevOps Client (8 horas)

#### 3.1 Implementar azdo_client.py
```python
import requests
import json
from typing import Dict, Optional

class AzureDevOpsClient:
    def __init__(self, pat: str, org: str, project: str):
        self.pat = pat
        self.org = org
        self.project = project
        self.base_url = f"https://vsrm.dev.azure.com/{org}/{project}"
        self.api_version = "7.1"
    
    def get_release_definition(self, definition_id: int) -> Dict:
        """Descargar definición de release"""
        url = f"{self.base_url}/_apis/release/definitions/{definition_id}"
        params = {'api-version': self.api_version}
        response = requests.get(url, params=params, auth=(self.pat, ''))
        response.raise_for_status()
        return response.json()
    
    def update_release_definition(self, definition_id: int, definition: Dict) -> bool:
        """Guardar cambios"""
        url = f"{self.base_url}/_apis/release/definitions/{definition_id}"
        params = {'api-version': self.api_version}
        response = requests.put(url, json=definition, params=params, auth=(self.pat, ''))
        return response.status_code == 200
    
    def create_snapshot(self, definition_id: int, definition: Dict) -> str:
        """Crear snapshot para rollback"""
        import time
        snapshot_id = f"snapshot_{definition_id}_{int(time.time())}"
        snapshot_path = f"outcome/snapshots/{snapshot_id}.json"
        with open(snapshot_path, 'w') as f:
            json.dump(definition, f, indent=2)
        return snapshot_id
    
    def rollback(self, definition_id: int, snapshot_id: str) -> bool:
        """Revertir a snapshot"""
        snapshot_path = f"outcome/snapshots/{snapshot_id}.json"
        with open(snapshot_path, 'r') as f:
            definition = json.load(f)
        return self.update_release_definition(definition_id, definition)
```

**Duración**: 3 horas

#### 3.2 Implementar manejo de errores
```python
class AzureDevOpsError(Exception):
    pass

class PipelineNotFoundError(AzureDevOpsError):
    pass

class PermissionDeniedError(AzureDevOpsError):
    pass
```

**Duración**: 1 hora

#### 3.3 Tests
```python
def test_get_release_definition(mock_requests):
    client = AzureDevOpsClient("pat", "org", "project")
    mock_requests.get.return_value.json.return_value = {"id": 3388}
    result = client.get_release_definition(3388)
    assert result["id"] == 3388

def test_create_snapshot(tmp_path):
    client = AzureDevOpsClient("pat", "org", "project")
    definition = {"id": 3388, "name": "test"}
    snapshot_id = client.create_snapshot(3388, definition)
    assert snapshot_id.startswith("snapshot_")
```

**Duración**: 2 horas

#### 3.4 Integración con config.json
```python
def load_azdo_config() -> Dict:
    """Cargar configuración de AZDO desde config.json"""
    with open('scm/config.json', 'r') as f:
        config = json.load(f)
    return config['azdo']
```

**Duración**: 2 horas

**Total Fase 3**: 8 horas

---

### Fase 4: Search Engine (6 horas)

#### 4.1 Implementar search_engine.py
```python
class SearchEngine:
    def __init__(self, definition: Dict, search_rules: Dict):
        self.definition = definition
        self.search_rules = search_rules
        self.matches = []
    
    def search_stages(self, stage_names: List[str]) -> List[Dict]:
        """Buscar stages"""
        matches = []
        for stage in self.definition.get('environments', []):
            if stage.get('name') in stage_names:
                matches.append({
                    'type': 'stage',
                    'name': stage['name'],
                    'id': stage['id'],
                    'object': stage
                })
        return matches
    
    def search_tasks(self, task_criteria: List[Dict]) -> List[Dict]:
        """Buscar tasks"""
        matches = []
        for stage in self.definition.get('environments', []):
            for phase in stage.get('deployPhases', []):
                for task in phase.get('deploymentInput', {}).get('tasks', []):
                    for criteria in task_criteria:
                        if self._task_matches(task, criteria):
                            matches.append({
                                'type': 'task',
                                'stage': stage['name'],
                                'name': task['displayName'],
                                'object': task
                            })
        return matches
    
    def search_variables(self, var_names: List[str]) -> List[Dict]:
        """Buscar variables"""
        matches = []
        for var_name, var_obj in self.definition.get('variables', {}).items():
            if var_name in var_names:
                matches.append({
                    'type': 'variable',
                    'name': var_name,
                    'value': var_obj.get('value'),
                    'object': var_obj
                })
        return matches
    
    def search_all(self) -> List[Dict]:
        """Ejecutar todas las búsquedas"""
        self.matches = []
        self.matches.extend(self.search_stages(self.search_rules.get('stages', [])))
        self.matches.extend(self.search_tasks(self.search_rules.get('tasks', [])))
        self.matches.extend(self.search_variables(self.search_rules.get('variables', [])))
        return self.matches
    
    def _task_matches(self, task: Dict, criteria: Dict) -> bool:
        """Verificar si task coincide con criterios"""
        name_match = task.get('displayName') == criteria.get('name')
        type_match = task.get('task', {}).get('definitionType') == criteria.get('type')
        return name_match and type_match
```

**Duración**: 3 horas

#### 4.2 Tests
```python
def test_search_stages():
    definition = {
        'environments': [
            {'id': 1, 'name': 'QA'},
            {'id': 2, 'name': 'Producción'}
        ]
    }
    search_rules = {'stages': ['Producción']}
    engine = SearchEngine(definition, search_rules)
    matches = engine.search_stages(['Producción'])
    assert len(matches) == 1
    assert matches[0]['name'] == 'Producción'
```

**Duración**: 3 horas

**Total Fase 4**: 6 horas

---

### Fase 5: Update Engine (6 horas)

#### 5.1 Implementar update_engine.py
```python
class UpdateEngine:
    def __init__(self, definition: Dict, matches: List[Dict], update_rules: Dict):
        self.definition = definition
        self.matches = matches
        self.update_rules = update_rules
        self.changes = []
    
    def apply_updates(self) -> bool:
        """Aplicar actualizaciones"""
        try:
            for match in self.matches:
                if match['type'] == 'task':
                    self._update_task(match)
                elif match['type'] == 'variable':
                    self._update_variable(match)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def _update_task(self, match: Dict):
        """Actualizar task"""
        task = match['object']
        task_rules = self.update_rules.get('tasks', [])
        
        for rule in task_rules:
            if rule.get('name') == match['name']:
                for field_update in rule.get('fields', []):
                    path = field_update.get('path')
                    new_value = field_update.get('new_value')
                    self._set_nested_value(task, path, new_value)
                    self.changes.append({
                        'type': 'task_field',
                        'task': match['name'],
                        'field': path,
                        'new': new_value
                    })
    
    def _update_variable(self, match: Dict):
        """Actualizar variable"""
        var = match['object']
        var_rules = self.update_rules.get('variables', [])
        
        for rule in var_rules:
            if rule.get('name') == match['name']:
                old_value = var.get('value')
                new_value = rule.get('new_value')
                var['value'] = new_value
                self.changes.append({
                    'type': 'variable',
                    'name': match['name'],
                    'old': old_value,
                    'new': new_value
                })
    
    def _set_nested_value(self, obj: Dict, path: str, value):
        """Establecer valor en ruta anidada"""
        keys = path.split('.')
        current = obj
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def get_changes(self) -> List[Dict]:
        """Obtener cambios realizados"""
        return self.changes
```

**Duración**: 3 horas

#### 5.2 Tests
```python
def test_update_task_field():
    definition = {
        'environments': [{
            'deployPhases': [{
                'deploymentInput': {
                    'tasks': [{
                        'displayName': 'Docker Push',
                        'inputs': {'imageRepository': 'old-image'}
                    }]
                }
            }]
        }]
    }
    matches = [{'type': 'task', 'name': 'Docker Push', 'object': definition['environments'][0]['deployPhases'][0]['deploymentInput']['tasks'][0]}]
    update_rules = {
        'tasks': [{
            'name': 'Docker Push',
            'fields': [{'path': 'inputs.imageRepository', 'new_value': 'new-image'}]
        }]
    }
    engine = UpdateEngine(definition, matches, update_rules)
    engine.apply_updates()
    assert len(engine.get_changes()) == 1
```

**Duración**: 3 horas

**Total Fase 5**: 6 horas

---

### Fase 6: Parallel Executor (6 horas)

#### 6.1 Implementar parallel_executor.py
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

class ParallelExecutor:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.results = []
        self.errors = []
    
    def execute(self, definition_ids: List[int], template_parser, azdo_client) -> Dict:
        """Ejecutar en paralelo"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_pipeline, def_id, template_parser, azdo_client): def_id
                for def_id in definition_ids
            }
            
            for future in as_completed(futures):
                def_id = futures[future]
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    self.errors.append({
                        'definition_id': def_id,
                        'error': str(e)
                    })
        
        return {
            'success': len(self.results),
            'failed': len(self.errors),
            'results': self.results,
            'errors': self.errors
        }
    
    def _process_pipeline(self, definition_id: int, template_parser, azdo_client):
        """Procesar un pipeline"""
        # 1. Descargar
        definition = azdo_client.get_release_definition(definition_id)
        
        # 2. Snapshot
        snapshot_id = azdo_client.create_snapshot(definition_id, definition)
        
        # 3. Buscar
        search_engine = SearchEngine(definition, template_parser.get_search_rules())
        matches = search_engine.search_all()
        
        # 4. Actualizar
        update_engine = UpdateEngine(definition, matches, template_parser.get_update_rules())
        update_engine.apply_updates()
        
        # 5. Guardar
        success = azdo_client.update_release_definition(definition_id, definition)
        
        return {
            'definition_id': definition_id,
            'success': success,
            'snapshot_id': snapshot_id,
            'matches_found': len(matches),
            'changes_applied': len(update_engine.get_changes()),
            'changes': update_engine.get_changes()
        }
```

**Duración**: 3 horas

#### 6.2 Tests
```python
def test_parallel_executor(mock_azdo_client):
    executor = ParallelExecutor(max_workers=2)
    definition_ids = [3388, 3389]
    result = executor.execute(definition_ids, mock_template_parser, mock_azdo_client)
    assert result['success'] + result['failed'] == 2
```

**Duración**: 3 horas

**Total Fase 6**: 6 horas

---

### Fase 7: Reporter (4 horas)

#### 7.1 Implementar reporter.py
```python
import json
import csv
from datetime import datetime

class Reporter:
    def __init__(self, results: Dict):
        self.results = results
        self.output_dir = "outcome/pipeline_updates"
    
    def generate_all(self):
        """Generar todos los reportes"""
        self.generate_json()
        self.generate_csv()
        self.generate_html()
    
    def generate_json(self):
        """Generar JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': self.results['success'] + self.results['failed'],
                'success': self.results['success'],
                'failed': self.results['failed'],
            },
            'details': self.results['results'],
            'errors': self.results['errors']
        }
        with open(f"{self.output_dir}/report.json", 'w') as f:
            json.dump(report, f, indent=2)
    
    def generate_csv(self):
        """Generar CSV"""
        rows = []
        for result in self.results['results']:
            rows.append({
                'definition_id': result['definition_id'],
                'success': result['success'],
                'matches': result['matches_found'],
                'changes': result['changes_applied'],
            })
        with open(f"{self.output_dir}/report.csv", 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['definition_id', 'success', 'matches', 'changes'])
            writer.writeheader()
            writer.writerows(rows)
    
    def generate_html(self):
        """Generar HTML"""
        html = f"""<html>
        <head><title>Pipeline Updates</title></head>
        <body>
            <h1>Pipeline Updates Report</h1>
            <p>Success: {self.results['success']} | Failed: {self.results['failed']}</p>
            <table border="1">
                <tr><th>ID</th><th>Status</th><th>Changes</th></tr>
                {''.join(f"<tr><td>{r['definition_id']}</td><td>{'✓' if r['success'] else '✗'}</td><td>{r['changes_applied']}</td></tr>" for r in self.results['results'])}
            </table>
        </body>
        </html>"""
        with open(f"{self.output_dir}/report.html", 'w') as f:
            f.write(html)
```

**Duración**: 2 horas

#### 7.2 Tests
```python
def test_reporter_json(tmp_path):
    results = {'success': 1, 'failed': 0, 'results': [], 'errors': []}
    reporter = Reporter(results)
    reporter.generate_json()
    # Verificar que se creó el archivo
```

**Duración**: 2 horas

**Total Fase 7**: 4 horas

---

### Fase 8: Orquestador Principal (4 horas)

#### 8.1 Implementar pipeline_updater.py
```python
class PipelineUpdater:
    def __init__(self, pat: str, org: str, project: str):
        self.azdo_client = AzureDevOpsClient(pat, org, project)
    
    def update_pipelines(self, definition_ids: List[int], template_path: str, dry_run: bool = False) -> Dict:
        """Actualizar múltiples pipelines"""
        
        # 1. Validar
        parser = TemplateParser(template_path)
        if not parser.validate():
            return {'error': 'Template inválido'}
        
        # 2. Análisis
        print("Analizando pipelines...")
        # ... análisis ...
        
        # 3. Confirmación
        if not dry_run:
            response = input("¿Continuar? (s/n): ")
            if response.lower() != 's':
                return {'cancelled': True}
        
        # 4. Ejecutar
        executor = ParallelExecutor()
        results = executor.execute(definition_ids, parser, self.azdo_client)
        
        # 5. Reportar
        reporter = Reporter(results)
        reporter.generate_all()
        
        return results
```

**Duración**: 2 horas

#### 8.2 CLI
```python
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--definition-ids', required=True)
    parser.add_argument('--template', required=True)
    parser.add_argument('--pat', required=True)
    parser.add_argument('--org', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--dry-run', action='store_true')
    
    args = parser.parse_args()
    definition_ids = [int(x) for x in args.definition_ids.split(',')]
    
    updater = PipelineUpdater(args.pat, args.org, args.project)
    result = updater.update_pipelines(definition_ids, args.template, args.dry_run)
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
```

**Duración**: 2 horas

**Total Fase 8**: 4 horas

---

### Fase 9: Integración en tools.py (2 horas)

#### 9.1 Agregar herramienta en tools.py
```python
"41": {
    "name":        "Pipeline Updater Template",
    "description": "Actualización masiva de pipelines CD usando templates",
    "path":        "pipeline-updater/pipeline_updater.py",
    "args":        ["--definition-ids", "--template", "--dry-run"],
    "group":       "updatepipe",
    "status":      "ready",
}
```

**Duración**: 1 hora

#### 9.2 Crear función run_tool_41()
```python
def run_tool_41():
    """Ejecutar Pipeline Updater Template"""
    # ... implementación ...
```

**Duración**: 1 hora

**Total Fase 9**: 2 horas

---

## 4. CRONOGRAMA

| Fase | Descripción | Horas | Días |
|------|-------------|-------|------|
| 1 | Setup y Modelos | 8 | 1 |
| 2 | Template Parser | 6 | 1 |
| 3 | AZDO Client | 8 | 1 |
| 4 | Search Engine | 6 | 1 |
| 5 | Update Engine | 6 | 1 |
| 6 | Parallel Executor | 6 | 1 |
| 7 | Reporter | 4 | 0.5 |
| 8 | Orquestador | 4 | 0.5 |
| 9 | Integración | 2 | 0.5 |
| **TOTAL** | | **50 horas** | **7 días** |

---

## 5. CHECKLIST DE IMPLEMENTACIÓN

### Fase 1
- [ ] Crear estructura de directorios
- [ ] Implementar config.py
- [ ] Implementar models.py
- [ ] Tests para modelos
- [ ] Documentación

### Fase 2
- [ ] Implementar template_parser.py
- [ ] Implementar validator.py
- [ ] Tests para parser
- [ ] Tests para validator

### Fase 3
- [ ] Implementar azdo_client.py
- [ ] Manejo de errores
- [ ] Tests para cliente
- [ ] Integración con config.json

### Fase 4
- [ ] Implementar search_engine.py
- [ ] Tests para búsqueda
- [ ] Validar casos edge

### Fase 5
- [ ] Implementar update_engine.py
- [ ] Tests para actualización
- [ ] Validar integridad

### Fase 6
- [ ] Implementar parallel_executor.py
- [ ] Tests para paralelismo
- [ ] Validar rollback

### Fase 7
- [ ] Implementar reporter.py
- [ ] Generar JSON, CSV, HTML
- [ ] Tests para reportería

### Fase 8
- [ ] Implementar orquestador
- [ ] CLI
- [ ] Tests de integración

### Fase 9
- [ ] Agregar en tools.py
- [ ] Crear función run_tool_41()
- [ ] Testing final

---

## 6. CRITERIOS DE ACEPTACIÓN

✅ **Funcionalidad**:
- [ ] Actualizar 50+ pipelines en < 10 segundos
- [ ] Validar templates correctamente
- [ ] Rollback automático en caso de error
- [ ] Generar reportes en JSON, CSV, HTML

✅ **Calidad**:
- [ ] 80%+ cobertura de tests
- [ ] Sin errores críticos
- [ ] Documentación completa
- [ ] Ejemplos funcionales

✅ **Seguridad**:
- [ ] Validación de permisos
- [ ] Snapshots automáticos
- [ ] Auditoría completa
- [ ] Confirmación del usuario

---

## 7. RIESGOS Y MITIGACIÓN

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|--------|-----------|
| Error en AZDO API | Media | Alto | Validación, retry, rollback |
| Template inválido | Baja | Medio | Validación estricta |
| Parallelismo | Baja | Medio | Tests exhaustivos |
| Pérdida de datos | Muy baja | Crítico | Snapshots automáticos |

---

**Versión**: 1.0  
**Fecha**: 2026-07-13
