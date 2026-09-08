# Ejemplos de Templates para Repo Creator

**Documento:** Ejemplos prácticos de templates YAML  
**Versión:** 1.0  
**Fecha:** 8 de Septiembre de 2026

---

## 1. Template Estándar (repo_standard.yaml)

Para repositorios típicos con estructura master/develop/QA.

```yaml
metadata:
  name: "Repositorio estándar con ramas y políticas"
  version: "1.0"
  description: "Template para crear repos con estructura master/develop/QA"
  author: "DevOps Team"
  created_at: "2026-09-08"

repository:
  name: "mi-repo"                    # REQUERIDO: cambiar por nombre real
  description: "Descripción del repositorio"
  project: "Cadena_de_Suministros"
  visibility: "private"
  default_branch: "develop"

branches:
  initial:
    - name: "develop"
      description: "Rama de desarrollo"
      from_branch: null
      
    - name: "QA"
      description: "Rama de testing y QA"
      from_branch: "develop"
      
    - name: "main"
      description: "Rama de producción"
      from_branch: "QA"
      
    - name: "release"
      description: "Rama de releases"
      from_branch: "develop"

policies:
  - branch: "main"
    description: "Políticas estrictas para producción"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 2
        creator_can_approve: false
        reset_on_push: true
        
      - type: "required_reviewers"
        reviewers: ["devops-team"]
        
      - type: "build_validation"
        build_definition: "CI-Pipeline"
        valid_duration: 720  # 12 horas
        
      - type: "comment_requirements"
        require_linked_work_items: true
        require_comment: false
        
  - branch: "QA"
    description: "Políticas moderadas para QA"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 1
        creator_can_approve: true
        reset_on_push: false
        
      - type: "build_validation"
        build_definition: "CI-Pipeline"
        
  - branch: "develop"
    description: "Políticas básicas para desarrollo"
    rules:
      - type: "build_validation"
        build_definition: "CI-Pipeline"

permissions:
  groups:
    - name: "Developers"
      permissions:
        - "Contribute"
        - "Create Branch"
        - "Create Tag"
        
    - name: "DevOps Team"
      permissions:
        - "Administer"
        - "Force Push"
        - "Manage Permissions"
        
    - name: "QA Team"
      permissions:
        - "Contribute"
        - "Create Branch"

webhooks:
  - event: "push"
    url: "https://your-webhook-endpoint/push"
    filters:
      - branch: "main"
      - branch: "QA"

readme:
  generate: true
  template: "standard"

gitignore:
  generate: true
  template: "python"

labels:
  - name: "bug"
    color: "ff0000"
  - name: "feature"
    color: "00ff00"
  - name: "documentation"
    color: "0000ff"
  - name: "enhancement"
    color: "ffff00"

options:
  dry_run: true
  auto_initialize: true
  backup_existing: true
```

---

## 2. Template Microservicio (repo_microservice.yaml)

Para repositorios de microservicios con CI/CD integrado.

```yaml
metadata:
  name: "Microservicio con CI/CD"
  version: "1.0"
  description: "Template para crear repos de microservicios"
  author: "DevOps Team"

repository:
  name: "ms-nombre-servicio"
  description: "Microservicio: [descripción]"
  project: "Cadena_de_Suministros"
  visibility: "private"
  default_branch: "develop"

branches:
  initial:
    - name: "develop"
      description: "Rama de desarrollo"
      from_branch: null
      
    - name: "staging"
      description: "Rama de staging"
      from_branch: "develop"
      
    - name: "main"
      description: "Rama de producción"
      from_branch: "staging"
      
    - name: "hotfix"
      description: "Rama para hotfixes"
      from_branch: "main"

policies:
  - branch: "main"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 2
        creator_can_approve: false
        reset_on_push: true
        
      - type: "build_validation"
        build_definition: "MS-CI-Pipeline"
        
      - type: "comment_requirements"
        require_linked_work_items: true
        
  - branch: "staging"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 1
        
      - type: "build_validation"
        build_definition: "MS-CI-Pipeline"
        
  - branch: "develop"
    rules:
      - type: "build_validation"
        build_definition: "MS-CI-Pipeline"

permissions:
  groups:
    - name: "Backend Team"
      permissions:
        - "Contribute"
        - "Create Branch"
        
    - name: "DevOps Team"
      permissions:
        - "Administer"
        - "Force Push"

webhooks:
  - event: "push"
    url: "https://ci-server/webhook/push"
    filters:
      - branch: "main"
      - branch: "staging"
      - branch: "develop"

readme:
  generate: true
  template: "microservice"

gitignore:
  generate: true
  template: "python"

labels:
  - name: "bug"
    color: "ff0000"
  - name: "feature"
    color: "00ff00"
  - name: "performance"
    color: "ff9900"
  - name: "security"
    color: "ff00ff"

options:
  dry_run: true
  auto_initialize: true
```

---

## 3. Template Librería (repo_library.yaml)

Para repositorios de librerías compartidas.

```yaml
metadata:
  name: "Librería compartida"
  version: "1.0"
  description: "Template para crear repos de librerías"
  author: "DevOps Team"

repository:
  name: "lib-nombre-libreria"
  description: "Librería: [descripción]"
  project: "Cadena_de_Suministros"
  visibility: "private"
  default_branch: "main"

branches:
  initial:
    - name: "develop"
      description: "Rama de desarrollo"
      from_branch: null
      
    - name: "main"
      description: "Rama de releases"
      from_branch: "develop"

policies:
  - branch: "main"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 2
        creator_can_approve: false
        
      - type: "build_validation"
        build_definition: "Lib-CI-Pipeline"
        
      - type: "comment_requirements"
        require_linked_work_items: true
        
  - branch: "develop"
    rules:
      - type: "build_validation"
        build_definition: "Lib-CI-Pipeline"

permissions:
  groups:
    - name: "Library Maintainers"
      permissions:
        - "Administer"
        - "Force Push"
        
    - name: "Developers"
      permissions:
        - "Contribute"
        - "Create Branch"

readme:
  generate: true
  template: "library"

gitignore:
  generate: true
  template: "python"

labels:
  - name: "breaking-change"
    color: "ff0000"
  - name: "feature"
    color: "00ff00"
  - name: "bugfix"
    color: "ffff00"

options:
  dry_run: true
  auto_initialize: true
```

---

## 4. Template Monorepo (repo_monorepo.yaml)

Para repositorios monorepo con múltiples proyectos.

```yaml
metadata:
  name: "Monorepo con múltiples proyectos"
  version: "1.0"
  description: "Template para crear monorepos"
  author: "DevOps Team"

repository:
  name: "mono-nombre-proyecto"
  description: "Monorepo: [descripción]"
  project: "Cadena_de_Suministros"
  visibility: "private"
  default_branch: "develop"

branches:
  initial:
    - name: "develop"
      description: "Rama de desarrollo"
      from_branch: null
      
    - name: "QA"
      description: "Rama de QA"
      from_branch: "develop"
      
    - name: "staging"
      description: "Rama de staging"
      from_branch: "QA"
      
    - name: "main"
      description: "Rama de producción"
      from_branch: "staging"

policies:
  - branch: "main"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 3
        creator_can_approve: false
        reset_on_push: true
        
      - type: "build_validation"
        build_definition: "Mono-CI-Pipeline"
        
      - type: "comment_requirements"
        require_linked_work_items: true
        
  - branch: "staging"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 2
        
      - type: "build_validation"
        build_definition: "Mono-CI-Pipeline"
        
  - branch: "QA"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 1
        
      - type: "build_validation"
        build_definition: "Mono-CI-Pipeline"
        
  - branch: "develop"
    rules:
      - type: "build_validation"
        build_definition: "Mono-CI-Pipeline"

permissions:
  groups:
    - name: "Core Team"
      permissions:
        - "Administer"
        - "Force Push"
        - "Manage Permissions"
        
    - name: "Developers"
      permissions:
        - "Contribute"
        - "Create Branch"
        
    - name: "QA Team"
      permissions:
        - "Contribute"
        - "Create Branch"

webhooks:
  - event: "push"
    url: "https://ci-server/webhook/push"
    filters:
      - branch: "main"
      - branch: "staging"
      - branch: "QA"
      - branch: "develop"

readme:
  generate: true
  template: "monorepo"

gitignore:
  generate: true
  template: "python"

labels:
  - name: "critical"
    color: "ff0000"
  - name: "feature"
    color: "00ff00"
  - name: "module-api"
    color: "0000ff"
  - name: "module-web"
    color: "00ffff"
  - name: "module-mobile"
    color: "ff00ff"

options:
  dry_run: true
  auto_initialize: true
```

---

## 5. Template Personalizado (repo_custom.yaml)

Para casos especiales con configuración personalizada.

```yaml
metadata:
  name: "Repositorio personalizado"
  version: "1.0"
  description: "Template personalizado para caso especial"
  author: "Tu Nombre"

repository:
  name: "custom-repo"
  description: "Repositorio personalizado"
  project: "Cadena_de_Suministros"
  visibility: "private"
  default_branch: "main"

branches:
  initial:
    - name: "main"
      description: "Rama principal"
      from_branch: null
      
    - name: "develop"
      description: "Rama de desarrollo"
      from_branch: "main"
      
    - name: "feature/base"
      description: "Base para features"
      from_branch: "develop"

policies:
  - branch: "main"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 1
        
      - type: "build_validation"
        build_definition: "Custom-CI"

permissions:
  groups:
    - name: "Team"
      permissions:
        - "Contribute"
        - "Create Branch"

readme:
  generate: true
  template: "custom"

gitignore:
  generate: true
  template: "python"

options:
  dry_run: true
  auto_initialize: true
```

---

## 6. Cómo Usar los Templates

### 6.1 Opción 1: Template Predefinido

```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 43 (Repo Creator)
# Seleccionar: Template predefinido
# Seleccionar: repo_standard.yaml
# Ingresar: Nombre del repo
# Confirmar: Dry-run
```

### 6.2 Opción 2: Template Personalizado

```bash
python scm/azdo/repo_creator/repo_creator_cli.py \
  --template mi-template.yaml \
  --org https://dev.azure.com/Coppel-Retail \
  --project "Cadena_de_Suministros" \
  --pat $AZURE_DEVOPS_PAT \
  --dry-run
```

### 6.3 Opción 3: Batch (Múltiples Repos)

```bash
# Crear archivo repos.csv
# repo_name,template,description
# repo1,standard,"Descripción 1"
# repo2,microservice,"Descripción 2"
# repo3,library,"Descripción 3"

python scm/azdo/repo_creator/repo_creator_cli.py \
  --batch repos.csv \
  --org https://dev.azure.com/Coppel-Retail \
  --project "Cadena_de_Suministros" \
  --pat $AZURE_DEVOPS_PAT \
  --parallel 3
```

---

## 7. Personalización de Templates

### 7.1 Cambiar Nombre del Repo

```yaml
repository:
  name: "mi-nuevo-repo"  # ← Cambiar aquí
```

### 7.2 Agregar Rama Personalizada

```yaml
branches:
  initial:
    - name: "develop"
      from_branch: null
    - name: "mi-rama"      # ← Nueva rama
      from_branch: "develop"
```

### 7.3 Cambiar Política de Revisores

```yaml
policies:
  - branch: "main"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 3  # ← Cambiar aquí
```

### 7.4 Agregar Grupo de Permisos

```yaml
permissions:
  groups:
    - name: "Mi Team"      # ← Nuevo grupo
      permissions:
        - "Contribute"
        - "Create Branch"
```

---

## 8. Variables de Entorno en Templates

Puedes usar variables en templates:

```yaml
repository:
  name: "repo-${DATE}"           # repo-2026-09-08
  description: "Creado por ${USER}"  # Creado por harold.bolanos
  project: "${PROJECT}"          # Cadena_de_Suministros
```

Variables disponibles:
- `${DATE}` - Fecha actual (YYYY-MM-DD)
- `${TIME}` - Hora actual (HH:MM:SS)
- `${USER}` - Usuario actual
- `${ORG}` - Organización
- `${PROJECT}` - Proyecto
- `${TIMESTAMP}` - Timestamp Unix

---

## 9. Validación de Templates

Antes de usar un template, validarlo:

```bash
python scm/azdo/repo_creator/repo_creator_cli.py \
  --validate mi-template.yaml
```

Esto verificará:
- ✅ Sintaxis YAML válida
- ✅ Estructura requerida
- ✅ Valores permitidos
- ✅ Nombres válidos
- ✅ Políticas soportadas

---

## 10. Troubleshooting

### Problema: "Repositorio ya existe"
**Solución:** Cambiar nombre en template o eliminar repo existente

### Problema: "Rama no encontrada"
**Solución:** Verificar que rama origen existe antes de crear dependiente

### Problema: "Política no soportada"
**Solución:** Usar solo tipos de política soportados (ver documentación)

### Problema: "Permiso denegado"
**Solución:** Verificar que PAT tiene permisos suficientes

---

## 11. Conclusión

Los templates YAML proporcionan:

✅ **Reutilización** - Usar mismo template para múltiples repos  
✅ **Consistencia** - Misma estructura siempre  
✅ **Flexibilidad** - Personalizar según necesidad  
✅ **Documentación** - Template es la documentación  
✅ **Versionamiento** - Guardar templates en Git  

