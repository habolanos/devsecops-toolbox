# Arquitectura Técnica: Repo Creator Pro

**Documento:** Especificación técnica detallada  
**Versión:** 1.0  
**Fecha:** 8 de Septiembre de 2026

---

## 1. Módulos Principales

### 1.1 repo_creator.py (Orquestador)

```python
class RepoCreator:
    """Orquestador principal de creación de repositorios"""
    
    def __init__(self, org: str, project: str, pat: str):
        self.org = org
        self.project = project
        self.pat = pat
        self.repo_client = AzDORepoClient(org, project, pat)
        self.branch_client = AzDOBranchClient(org, project, pat)
        self.policy_client = AzDOPolicyClient(org, project, pat)
        self.validator = RepositoryValidator(org, project, pat)
        self.logger = Logger()
        
    def create_from_template(self, template_path: str, dry_run: bool = True) -> CreationResult:
        """Flujo principal de creación"""
        # 1. Cargar y validar template
        # 2. Validar entrada
        # 3. Modo dry-run
        # 4. Crear repositorio
        # 5. Crear ramas
        # 6. Configurar políticas
        # 7. Configurar permisos
        # 8. Configurar webhooks
        # 9. Generar documentación
        # 10. Generar reportes
        
    def rollback(self, repo_id: str):
        """Rollback automático si algo falla"""
        # Eliminar repo creado
        # Restaurar estado anterior
        # Generar reporte de error
```

### 1.2 template_parser.py (Parser YAML)

```python
class TemplateParser:
    """Parser de templates YAML con validación"""
    
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.raw_yaml = None
        self.parsed = None
        
    def load(self) -> Dict:
        """Cargar y parsear YAML"""
        # Validar sintaxis YAML
        # Validar estructura requerida
        # Expandir variables (${VAR})
        # Retornar diccionario parseado
        
    def validate(self) -> ValidationResult:
        """Validar estructura del template"""
        # Verificar secciones requeridas
        # Validar tipos de datos
        # Validar valores permitidos
        # Retornar resultado de validación
        
    def expand_variables(self, data: Dict) -> Dict:
        """Expandir variables de entorno"""
        # ${ORG} → organización
        # ${PROJECT} → proyecto
        # ${DATE} → fecha actual
        # ${USER} → usuario actual
```

### 1.3 validators.py (Validadores)

```python
class RepositoryValidator:
    """Validar entrada antes de crear"""
    
    def validate_repo_name(self, name: str) -> bool:
        """Validar nombre de repositorio"""
        # Longitud 1-255 caracteres
        # Solo alphanumeric, -, _, .
        # No duplicado en proyecto
        
    def validate_branch_names(self, branches: List[str]) -> bool:
        """Validar nombres de ramas"""
        # Nombres válidos en Git
        # No duplicados
        # Caracteres permitidos
        
    def validate_policies(self, policies: List[Dict]) -> bool:
        """Validar políticas"""
        # Tipos soportados
        # Configuración válida
        # Ramas existen
        
    def validate_permissions(self, perms: Dict) -> bool:
        """Validar permisos"""
        # Grupos existen
        # Permisos válidos
        # Configuración correcta
```

### 1.4 azdo_repo_client.py (Cliente Repos)

```python
class AzDORepoClient:
    """Cliente para operaciones de repositorios"""
    
    def create_repository(self, name: str, description: str = "") -> RepoInfo:
        """Crear nuevo repositorio"""
        # POST /_apis/git/repositories
        # Retornar repo ID y URL
        
    def get_repository(self, repo_id: str) -> RepoInfo:
        """Obtener información del repo"""
        # GET /_apis/git/repositories/{repoId}
        
    def delete_repository(self, repo_id: str) -> bool:
        """Eliminar repositorio"""
        # DELETE /_apis/git/repositories/{repoId}
        
    def set_default_branch(self, repo_id: str, branch: str) -> bool:
        """Establecer rama por defecto"""
        # PATCH /_apis/git/repositories/{repoId}
```

### 1.5 azdo_branch_client.py (Cliente Ramas)

```python
class AzDOBranchClient:
    """Cliente para operaciones de ramas"""
    
    def create_branch(self, repo_id: str, branch_name: str, from_branch: str = None) -> BranchInfo:
        """Crear nueva rama"""
        # POST /_apis/git/repositories/{repoId}/refs
        # Si from_branch: crear desde esa rama
        # Si None: crear vacía
        
    def get_branch(self, repo_id: str, branch_name: str) -> BranchInfo:
        """Obtener información de rama"""
        # GET /_apis/git/repositories/{repoId}/refs
        
    def delete_branch(self, repo_id: str, branch_name: str) -> bool:
        """Eliminar rama"""
        # DELETE /_apis/git/repositories/{repoId}/refs
        
    def list_branches(self, repo_id: str) -> List[BranchInfo]:
        """Listar todas las ramas"""
        # GET /_apis/git/repositories/{repoId}/refs
```

### 1.6 azdo_policy_client.py (Cliente Políticas)

```python
class AzDOPolicyClient:
    """Cliente para operaciones de políticas"""
    
    def create_policy(self, repo_id: str, policy_config: Dict) -> PolicyInfo:
        """Crear política de rama"""
        # POST /_apis/policy/configurations
        # Soportar múltiples tipos
        
    def get_policies(self, repo_id: str, branch: str = None) -> List[PolicyInfo]:
        """Obtener políticas de un repo/rama"""
        # GET /_apis/policy/configurations
        
    def update_policy(self, policy_id: str, config: Dict) -> PolicyInfo:
        """Actualizar política existente"""
        # PUT /_apis/policy/configurations/{policyId}
        
    def delete_policy(self, policy_id: str) -> bool:
        """Eliminar política"""
        # DELETE /_apis/policy/configurations/{policyId}
```

### 1.7 branch_config_engine.py (Motor de Configuración)

```python
class BranchConfigEngine:
    """Motor para crear y configurar ramas"""
    
    def create_branches(self, repo_id: str, branches_config: List[Dict]) -> List[BranchInfo]:
        """Crear todas las ramas del template"""
        # Crear en orden correcto (respetando dependencias)
        # develop → QA → main
        # Retornar lista de ramas creadas
        
    def configure_policies(self, repo_id: str, policies_config: List[Dict]) -> List[PolicyInfo]:
        """Configurar políticas para cada rama"""
        # Crear políticas según configuración
        # Validar que ramas existan
        # Retornar lista de políticas creadas
        
    def configure_permissions(self, repo_id: str, perms_config: Dict) -> Dict:
        """Configurar permisos por grupo"""
        # Asignar permisos a grupos
        # Validar que grupos existan
        # Retornar resumen de permisos
```

### 1.8 policy_engine.py (Motor de Políticas)

```python
class PolicyEngine:
    """Motor para crear diferentes tipos de políticas"""
    
    def create_minimum_reviewers(self, repo_id: str, branch: str, config: Dict) -> PolicyInfo:
        """Política: Mínimo de revisores"""
        # min_reviewers: int
        # creator_can_approve: bool
        # reset_on_push: bool
        
    def create_required_reviewers(self, repo_id: str, branch: str, config: Dict) -> PolicyInfo:
        """Política: Revisores requeridos"""
        # reviewers: List[str] (grupos)
        
    def create_build_validation(self, repo_id: str, branch: str, config: Dict) -> PolicyInfo:
        """Política: Validación de build"""
        # build_definition: str
        # valid_duration: int
        
    def create_comment_requirements(self, repo_id: str, branch: str, config: Dict) -> PolicyInfo:
        """Política: Requisitos de comentarios"""
        # require_linked_work_items: bool
        # comment_required: bool
```

---

## 2. Flujo de Datos

### 2.1 Entrada: Template YAML

```yaml
repository:
  name: "nuevo-repo"
  description: "Descripción"
  
branches:
  initial:
    - name: "develop"
      from_branch: null
    - name: "QA"
      from_branch: "develop"
    - name: "main"
      from_branch: "QA"
      
policies:
  - branch: "main"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 2
```

### 2.2 Procesamiento

```
Template YAML
    ↓
TemplateParser.load()
    ↓
Diccionario parseado
    ↓
TemplateParser.validate()
    ↓
RepositoryValidator.validate_*()
    ↓
Validación exitosa
    ↓
RepoCreator.create_from_template()
    ↓
Múltiples llamadas a APIs
    ↓
CreationResult
```

### 2.3 Salida: CreationResult

```python
@dataclass
class CreationResult:
    success: bool
    repo_id: str
    repo_url: str
    branches_created: List[BranchInfo]
    policies_created: List[PolicyInfo]
    permissions_assigned: Dict
    webhooks_configured: List[WebhookInfo]
    documentation_generated: List[str]
    errors: List[str]
    warnings: List[str]
    duration: float
    timestamp: datetime
```

---

## 3. Manejo de Errores

### 3.1 Estrategia de Rollback

```python
class RollbackManager:
    """Gestionar rollback automático"""
    
    def __init__(self):
        self.operations = []  # Stack de operaciones
        
    def add_operation(self, op: Operation):
        """Agregar operación al stack"""
        self.operations.append(op)
        
    def rollback(self):
        """Ejecutar rollback en orden inverso"""
        for op in reversed(self.operations):
            op.undo()
```

### 3.2 Tipos de Errores

| Error | Acción |
|-------|--------|
| Repo duplicado | Validar antes, no crear |
| Rama no existe | Validar dependencias |
| Política inválida | Validar configuración |
| Permiso denegado | Mostrar error y parar |
| API timeout | Reintentar 3 veces |
| Fallo parcial | Rollback completo |

---

## 4. Logging y Auditoría

### 4.1 Niveles de Log

```python
logger.debug("Creando rama develop")
logger.info("Rama develop creada exitosamente")
logger.warning("Política no soportada, saltando")
logger.error("No se pudo crear repositorio")
logger.critical("Rollback iniciado")
```

### 4.2 Auditoría

```
[2026-09-08 09:12:34] INFO: Iniciando creación de repo "nuevo-repo"
[2026-09-08 09:12:35] DEBUG: Validando template
[2026-09-08 09:12:35] INFO: Template válido
[2026-09-08 09:12:36] INFO: Creando repositorio
[2026-09-08 09:12:37] INFO: Repositorio creado: ID=12345
[2026-09-08 09:12:38] INFO: Creando rama develop
[2026-09-08 09:12:39] INFO: Rama develop creada
...
[2026-09-08 09:12:45] INFO: Creación completada en 11 segundos
```

---

## 5. Testing

### 5.1 Tests Unitarios

```python
def test_template_parser_valid():
    """Test parser con template válido"""
    
def test_template_parser_invalid():
    """Test parser con template inválido"""
    
def test_repo_validator_duplicate():
    """Test validador detecta duplicados"""
    
def test_branch_creation_order():
    """Test crear ramas en orden correcto"""
    
def test_policy_creation():
    """Test crear políticas"""
    
def test_rollback():
    """Test rollback automático"""
```

### 5.2 Tests de Integración

```python
def test_create_repo_full_flow():
    """Test flujo completo de creación"""
    # Crear repo
    # Crear ramas
    # Configurar políticas
    # Verificar resultado
    # Limpiar (eliminar repo)
```

---

## 6. Performance

### 6.1 Optimizaciones

- **Parallelización:** Crear ramas en paralelo
- **Caching:** Cachear lista de repos/grupos
- **Batch:** Múltiples repos en una ejecución
- **Async:** Llamadas HTTP asincrónicas

### 6.2 Benchmarks

| Operación | Tiempo |
|-----------|--------|
| Crear repo | 2-3 seg |
| Crear rama | 1-2 seg |
| Crear política | 1-2 seg |
| Crear 4 ramas | 4-8 seg |
| Crear 7 políticas | 7-14 seg |
| **Total** | **~20 seg** |

---

## 7. Seguridad

### 7.1 Validación de Entrada

- Sanitizar nombres (no inyección)
- Validar URLs (webhooks)
- Validar tokens (PAT)
- Validar permisos (usuario)

### 7.2 Credenciales

```python
# NO hardcodear PAT
pat = os.getenv("AZURE_DEVOPS_PAT")

# Validar PAT antes de usar
if not pat or len(pat) < 20:
    raise ValueError("PAT inválido")
```

### 7.3 Auditoría

- Registrar todas las operaciones
- Registrar usuario y timestamp
- Registrar cambios realizados
- Permitir rollback

---

## 8. Configuración

### 8.1 Variables de Entorno

```bash
AZURE_DEVOPS_ORG=https://dev.azure.com/Coppel-Retail
AZURE_DEVOPS_PROJECT=Cadena_de_Suministros
AZURE_DEVOPS_PAT=xxxxx
DEVSECOPS_OUTPUT_DIR=./outcome
```

### 8.2 Archivo de Configuración

```json
{
  "org": "https://dev.azure.com/Coppel-Retail",
  "project": "Cadena_de_Suministros",
  "api_version": "7.1",
  "timeout": 30,
  "retries": 3,
  "parallel_workers": 5
}
```

---

## 9. Extensibilidad

### 9.1 Agregar Nuevo Tipo de Política

```python
class CustomPolicyEngine(PolicyEngine):
    def create_custom_policy(self, repo_id: str, branch: str, config: Dict):
        """Implementar nueva política"""
        pass
```

### 9.2 Agregar Nuevo Template

```yaml
# scm/azdo/repo_creator/templates/repo_custom.yaml
metadata:
  name: "Mi template personalizado"
  
repository:
  # ...
```

### 9.3 Agregar Nuevo Generador de Documentación

```python
class CustomDocGenerator:
    def generate(self, repo_info: RepoInfo) -> str:
        """Generar documentación personalizada"""
        pass
```

---

## 10. Integración con Toolbox

### 10.1 Agregar a tools.py

```python
TOOL_GROUPS["repo_creator"] = {
    "name": "Creador de Repositorios",
    "emoji": "📦",
    "color": "cyan"
}

TOOLS = {
    43: {
        "id": 43,
        "name": "Repo Creator Pro",
        "group": "repo_creator",
        "status": "ready",
        "description": "Crear repositorios con templates YAML",
        "module": "azdo.repo_creator.repo_creator_cli",
        "function": "main"
    }
}
```

### 10.2 Integración en main.py

```python
# En scm/main.py
from scm.azdo.repo_creator.repo_creator_cli import main as repo_creator_main

# En menú de Azure DevOps
if tool_id == 43:
    repo_creator_main()
```

---

## 11. Conclusión

Esta arquitectura proporciona:

✅ **Modularidad** - Componentes independientes  
✅ **Escalabilidad** - Fácil agregar nuevas características  
✅ **Robustez** - Manejo de errores y rollback  
✅ **Testabilidad** - Tests unitarios e integración  
✅ **Mantenibilidad** - Código limpio y documentado  
✅ **Performance** - Optimizaciones implementadas  
✅ **Seguridad** - Validación y auditoría  

