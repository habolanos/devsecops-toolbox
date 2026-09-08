# Análisis: Programa Profesional de Creación de Repositorios con Templates YAML

**Fecha:** 8 de Septiembre de 2026  
**Objetivo:** Crear un programa "pro" para crear repositorios nuevos en Azure DevOps con configuración automática de ramas basada en templates YAML

---

## 1. Visión General

### Problema
Actualmente, crear repositorios nuevos en Azure DevOps requiere:
1. Crear el repo manualmente en la UI
2. Crear ramas manualmente (develop, QA, main, etc.)
3. Configurar políticas de rama manualmente
4. Configurar protecciones y permisos manualmente
5. Documentar la estructura

**Solución:** Un programa que automatice TODO esto desde un template YAML.

---

## 2. Arquitectura Propuesta

### 2.1 Estructura de Directorios

```
scm/azdo/repo_creator/
├── __init__.py
├── repo_creator.py                 # Orquestador principal
├── repo_creator_cli.py             # Interfaz CLI
├── repo_creator_engine.py          # Motor de creación
├── branch_config_engine.py         # Motor de configuración de ramas
├── policy_engine.py                # Motor de políticas
├── template_parser.py              # Parser de templates YAML
├── azdo_repo_client.py             # Cliente Azure DevOps (repos)
├── azdo_branch_client.py           # Cliente Azure DevOps (branches)
├── azdo_policy_client.py           # Cliente Azure DevOps (policies)
├── validators.py                   # Validadores de entrada
├── templates/
│   ├── repo_standard.yaml          # Template estándar
│   ├── repo_microservice.yaml      # Template microservicio
│   ├── repo_library.yaml           # Template librería
│   └── repo_custom.yaml            # Template personalizado
├── test_repo_creator.py            # Tests unitarios
└── README.md                        # Documentación
```

---

## 3. Template YAML - Estructura Propuesta

### 3.1 Ejemplo: repo_standard.yaml

```yaml
metadata:
  name: "Crear repositorio estándar con ramas y políticas"
  version: "1.0"
  description: "Template para crear repos con estructura master/develop/QA"
  author: "DevOps Team"
  created_at: "2026-09-08"

repository:
  name: ""                           # Requerido: nombre del repo
  description: ""                    # Descripción del repo
  project: "Cadena_de_Suministros"   # Proyecto destino
  visibility: "private"              # private | public
  default_branch: "develop"          # Rama por defecto
  
branches:
  initial:
    - name: "develop"
      description: "Rama de desarrollo"
      from_branch: null              # null = crear vacía
      
    - name: "QA"
      description: "Rama de testing"
      from_branch: "develop"
      
    - name: "main"
      description: "Rama de producción"
      from_branch: "QA"
      
    - name: "release"
      description: "Rama de releases"
      from_branch: "develop"

policies:
  - branch: "main"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 2
        creator_can_approve: false
        reset_on_push: true
        
      - type: "required_reviewers"
        reviewers: ["devops-team"]
        
      - type: "build_validation"
        build_definition: "CI-Pipeline"
        
      - type: "comment_requirements"
        require_linked_work_items: true
        
  - branch: "QA"
    rules:
      - type: "minimum_reviewers"
        min_reviewers: 1
        creator_can_approve: true
        
      - type: "build_validation"
        build_definition: "CI-Pipeline"
        
  - branch: "develop"
    rules:
      - type: "build_validation"
        build_definition: "CI-Pipeline"

permissions:
  groups:
    - name: "Developers"
      permissions:
        - "Contribute"
        - "Create Branch"
        
    - name: "DevOps Team"
      permissions:
        - "Administer"
        - "Force Push"
        
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
  template: "standard"              # standard | microservice | library
  
gitignore:
  generate: true
  template: "python"                # python | node | csharp | java

labels:
  - name: "bug"
    color: "ff0000"
  - name: "feature"
    color: "00ff00"
  - name: "documentation"
    color: "0000ff"

options:
  dry_run: true
  auto_initialize: true
  backup_existing: true
```

---

## 4. Características Principales

### 4.1 Creación de Repositorio
- ✅ Crear repo nuevo en Azure DevOps
- ✅ Configurar descripción y visibilidad
- ✅ Establecer rama por defecto
- ✅ Inicializar con README.md y .gitignore

### 4.2 Creación de Ramas
- ✅ Crear ramas iniciales (develop, QA, main, etc.)
- ✅ Crear ramas desde otras ramas (QA desde develop)
- ✅ Configurar rama por defecto
- ✅ Agregar descripción a cada rama

### 4.3 Políticas de Rama
- ✅ Mínimo de revisores
- ✅ Revisores requeridos
- ✅ Validación de build
- ✅ Requisitos de comentarios
- ✅ Linked work items
- ✅ Auto-complete de PRs
- ✅ Restricción de force push

### 4.4 Permisos y Grupos
- ✅ Asignar permisos a grupos
- ✅ Contribuir, crear ramas, administrar
- ✅ Configurar por rama
- ✅ Heredar de proyecto

### 4.5 Webhooks
- ✅ Configurar webhooks por evento
- ✅ Filtrar por rama
- ✅ Validar URL

### 4.6 Documentación Automática
- ✅ Generar README.md desde template
- ✅ Generar .gitignore
- ✅ Crear etiquetas (labels)
- ✅ Documentar estructura de ramas

### 4.7 Validación y Seguridad
- ✅ Validar nombre de repo (no duplicados)
- ✅ Validar nombres de ramas
- ✅ Validar políticas
- ✅ Validar permisos
- ✅ Dry-run antes de aplicar
- ✅ Rollback automático si falla

---

## 5. Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CARGAR TEMPLATE YAML                                     │
│    - Validar sintaxis YAML                                  │
│    - Validar estructura requerida                           │
│    - Expandir variables                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. VALIDAR ENTRADA                                          │
│    - Nombre de repo único                                   │
│    - Nombres de ramas válidos                               │
│    - Políticas soportadas                                   │
│    - Permisos válidos                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. MODO DRY-RUN (Simulación)                                │
│    - Mostrar qué se va a crear                              │
│    - Mostrar qué se va a configurar                         │
│    - Pedir confirmación del usuario                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. CREAR REPOSITORIO                                        │
│    - Crear repo en Azure DevOps                             │
│    - Esperar a que esté listo                               │
│    - Obtener repo ID                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. CREAR RAMAS INICIALES                                    │
│    - Crear rama develop (vacía)                             │
│    - Crear rama QA desde develop                            │
│    - Crear rama main desde QA                               │
│    - Establecer rama por defecto                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. CONFIGURAR POLÍTICAS                                     │
│    - Mínimo de revisores por rama                           │
│    - Validación de build                                    │
│    - Requisitos de comentarios                              │
│    - Linked work items                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. CONFIGURAR PERMISOS                                      │
│    - Asignar permisos a grupos                              │
│    - Configurar por rama                                    │
│    - Validar permisos                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. CONFIGURAR WEBHOOKS                                      │
│    - Crear webhooks por evento                              │
│    - Validar URL                                            │
│    - Filtrar por rama                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. GENERAR DOCUMENTACIÓN                                    │
│    - Crear README.md                                        │
│    - Crear .gitignore                                       │
│    - Crear etiquetas                                        │
│    - Documentar estructura                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 10. GENERAR REPORTES                                        │
│     - JSON con configuración aplicada                       │
│     - CSV con resumen                                       │
│     - HTML con documentación                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Interfaz CLI Propuesta

### 6.1 Modo Interactivo

```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 43 (Repo Creator)
# Seleccionar: Crear nuevo repositorio
# Ingresar: Nombre del repo
# Seleccionar: Template (standard, microservice, library, custom)
# Ingresar: Ruta del template YAML (opcional)
# Confirmar: Dry-run (s/n)
```

### 6.2 Modo CLI Directo

```bash
python scm/azdo/repo_creator/repo_creator_cli.py \
  --org https://dev.azure.com/Coppel-Retail \
  --project "Cadena_de_Suministros" \
  --template scm/azdo/repo_creator/templates/repo_standard.yaml \
  --repo-name "nuevo-repo" \
  --pat $AZURE_DEVOPS_PAT \
  --dry-run
```

### 6.3 Modo Batch (Múltiples Repos)

```bash
python scm/azdo/repo_creator/repo_creator_cli.py \
  --batch repos.csv \
  --template scm/azdo/repo_creator/templates/repo_standard.yaml \
  --parallel 3
```

---

## 7. Salida y Reportes

### 7.1 Dry-Run Output

```
╔════════════════════════════════════════════════════════════════╗
║          REPO CREATOR - DRY-RUN (Simulación)                  ║
╚════════════════════════════════════════════════════════════════╝

📦 Repositorio a Crear
  Nombre: nuevo-repo
  Descripción: Mi nuevo repositorio
  Proyecto: Cadena_de_Suministros
  Visibilidad: private
  Rama por defecto: develop

🌿 Ramas a Crear
  ✓ develop (vacía)
  ✓ QA (desde develop)
  ✓ main (desde QA)
  ✓ release (desde develop)

📋 Políticas a Configurar
  [main]
    - Mínimo 2 revisores
    - Validación de build
    - Linked work items requeridos
  [QA]
    - Mínimo 1 revisor
    - Validación de build
  [develop]
    - Validación de build

👥 Permisos a Asignar
  Developers: Contribute, Create Branch
  DevOps Team: Administer, Force Push
  QA Team: Contribute, Create Branch

🔗 Webhooks a Configurar
  - push (main, QA) → https://webhook.example.com/push

📄 Documentación a Generar
  - README.md (template: standard)
  - .gitignore (template: python)
  - Labels: bug, feature, documentation

✅ Cambios a aplicar: 45
🔍 Modo: DRY-RUN (sin cambios reales)

¿Deseas continuar? (s/n):
```

### 7.2 Reportes Finales

```
✅ Repositorio creado exitosamente

📊 Resumen
  Repositorio: nuevo-repo
  Ramas creadas: 4
  Políticas configuradas: 7
  Permisos asignados: 3 grupos
  Webhooks configurados: 1
  Documentación generada: 3 archivos

📁 Archivos Generados
  - outcome/repo_creation/report_20260908_091252.json
  - outcome/repo_creation/report_20260908_091252.csv
  - outcome/repo_creation/report_20260908_091252.html

🔗 URL del Repositorio
  https://dev.azure.com/Coppel-Retail/Cadena_de_Suministros/_git/nuevo-repo
```

---

## 8. Características Avanzadas

### 8.1 Templates Predefinidos
- **repo_standard.yaml** - Estructura master/develop/QA
- **repo_microservice.yaml** - Para microservicios
- **repo_library.yaml** - Para librerías compartidas
- **repo_monorepo.yaml** - Para monorepos

### 8.2 Validación Inteligente
- Detectar repos duplicados
- Validar nombres según convenciones
- Verificar permisos del usuario
- Validar políticas soportadas

### 8.3 Rollback Automático
- Si algo falla, eliminar lo creado
- Restaurar estado anterior
- Generar reporte de error

### 8.4 Integración con Otros Tools
- Crear automáticamente pipelines CI/CD
- Crear automáticamente work items
- Crear automáticamente documentación
- Notificar al equipo

---

## 9. Tecnologías y Dependencias

### 9.1 Librerías Principales
```
requests>=2.28.0          # HTTP calls
pyyaml>=6.0               # YAML parsing
rich>=13.0                # CLI UI
jinja2>=3.1               # Template rendering
pandas>=1.5               # Data processing
openpyxl>=3.9             # Excel export
```

### 9.2 APIs de Azure DevOps
```
GET    /_apis/git/repositories
POST   /_apis/git/repositories
GET    /_apis/git/repositories/{repoId}/refs
POST   /_apis/git/repositories/{repoId}/refs
GET    /_apis/policy/configurations
POST   /_apis/policy/configurations
GET    /_apis/git/repositories/{repoId}/permissions
PATCH  /_apis/git/repositories/{repoId}/permissions
```

---

## 10. Plan de Implementación

### Fase 1: Core (Semana 1)
- [ ] Estructura de directorios
- [ ] Template parser
- [ ] Validadores
- [ ] Clientes Azure DevOps (repos, branches)
- [ ] Motor de creación básico
- [ ] Tests unitarios

### Fase 2: Políticas y Permisos (Semana 2)
- [ ] Motor de políticas
- [ ] Motor de permisos
- [ ] Validación de políticas
- [ ] Tests de integración

### Fase 3: Documentación y Webhooks (Semana 3)
- [ ] Generador de README
- [ ] Generador de .gitignore
- [ ] Motor de webhooks
- [ ] Generador de etiquetas

### Fase 4: CLI y Reportes (Semana 4)
- [ ] Interfaz CLI
- [ ] Modo batch
- [ ] Generador de reportes
- [ ] Integración con main.py

### Fase 5: Testing y Documentación (Semana 5)
- [ ] Tests exhaustivos
- [ ] Documentación completa
- [ ] Ejemplos de uso
- [ ] Troubleshooting guide

---

## 11. Estimación de Esfuerzo

| Componente | Horas | Complejidad |
|-----------|-------|------------|
| Template Parser | 4 | Baja |
| Validadores | 6 | Media |
| Repo Client | 8 | Media |
| Branch Client | 6 | Media |
| Policy Engine | 12 | Alta |
| Permission Engine | 8 | Media |
| Webhook Engine | 6 | Media |
| Doc Generator | 8 | Media |
| CLI Interface | 10 | Media |
| Reportes | 8 | Media |
| Tests | 20 | Alta |
| Documentación | 12 | Baja |
| **TOTAL** | **108 horas** | **~3 semanas** |

---

## 12. Ventajas vs Alternativas

### vs. Crear Manualmente
- ⏱️ **Tiempo:** 30 min → 2 min
- 🎯 **Consistencia:** 100% (sin errores humanos)
- 📚 **Documentación:** Automática
- 🔄 **Repetibilidad:** Infinita

### vs. Scripts Bash
- 🐍 **Lenguaje:** Python (más mantenible)
- 🎨 **UI:** Rich (profesional)
- 📦 **Distribución:** Integrado en toolbox
- 🧪 **Testing:** Unitarios y de integración

### vs. Terraform/IaC
- ⚡ **Velocidad:** Más rápido de implementar
- 🎯 **Enfoque:** Específico para Azure DevOps
- 📝 **YAML:** Más legible que HCL
- 🔗 **Integración:** Directa con toolbox

---

## 13. Conclusión

Un programa profesional de creación de repositorios con templates YAML sería:

✅ **Altamente productivo** - Crear repos en minutos  
✅ **Consistente** - Misma estructura siempre  
✅ **Documentado** - README y .gitignore automáticos  
✅ **Seguro** - Políticas y permisos configurados  
✅ **Escalable** - Batch processing para múltiples repos  
✅ **Mantenible** - Código limpio y testeable  
✅ **Profesional** - UI moderna con Rich  

**Recomendación:** Implementar en 3-4 semanas con máxima prioridad.

