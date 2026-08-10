# 🔐 DevSecOps Toolbox

[![Version](https://img.shields.io/badge/version-1.7.31-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GNUv3-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)

> **Caja de herramientas DevSecOps unificada para operaciones multi-cloud.**
> 
> Soporta **Google Cloud Platform (GCP)**, **Azure Cloud Platform (AZURE)**, **Azure DevOps (AZDO)** y **Amazon Web Services (AWS)** con un launcher centralizado, testing profesional y distribución Docker.

---

##  Tabla de Contenidos

- [🚀 Características Principales](#-características-principales)
- [📦 Instalación](#-instalación)
- [🎯 Uso Rápido](#-uso-rápido)
- [📋 Templates para Pipeline Updater](#-templates-para-pipeline-updater)
- [🐳 Docker](#-docker)
- [☁️ Plataformas Soportadas](#️-plataformas-soportadas)
- [⚙️ Configuración](#️-configuración)
- [🧪 Testing](#-testing)
- [📁 Estructura del Proyecto](#-estructura-del-proyecto)
- [🏷️ Versionado Semántico](#️-versionado-semántico)
- [📝 Contribuir](#-contribuir)
- [📜 Licencia](#-licencia)
- [📚 Historial de Cambios](README.version.md)

---

## 🚀 Características Principales

| Característica | Descripción |
|---------------|-------------|
| 🎯 **Launcher Unificado** | Punto de entrada único para todas las plataformas cloud |
| 📊 **KPI Analyzer** | Análisis de métricas DevSecOps con modelo de madurez de 6 niveles y dashboards interactivos |
| 🐳 **Docker Ready** | Contenedor optimizado con todas las herramientas CLI (Azure, AWS, GCP, Kubernetes, Terraform) |
| 🧪 **Testing Profesional** | Suite completa de tests unitarios e integración con pytest (70%+ cobertura) |
| 🔐 **Configuración Segura** | Gestión centralizada de credenciales vía `config.json` (excluido de git) |
| 📊 **Reportes** | Generación de reportes y análisis de arquitectura |
| 🌐 **Multi-Cloud** | Soporte nativo para GCP, Azure Cloud, Azure DevOps y AWS |
| 🔑 **Autenticación Automática** | Validación automática de credenciales (gcloud, az, aws) |
| 🏷️ **SemVer** | Versionado semántico automatizado |

---

## 📦 Instalación

### Opción 1: Winget (Windows Package Manager) — Recomendado para Windows

```powershell
# Instalar
winget install habolanos.devsecops-toolbox

# Ejecutar desde cualquier terminal
devsecops-toolbox
```

**Detalles:**
- **Requisitos**: Windows 10 1709+ (build 16299) o Windows 11 con App Installer instalado
- **Tamaño**: ~420 MB (ejecutable standalone con Python y todas las dependencias incluidas)
- **Sin dependencias externas**: No requiere instalar Python, pip ni ningún otro prerequisito
- **Actualización**: `winget upgrade habolanos.devsecops-toolbox`
- **Desinstalación**: `winget uninstall habolanos.devsecops-toolbox`

> **Nota**: Si `winget` no está disponible, descarga App Installer desde Microsoft Store o usa la Opción 2.

### Opción 2: Ejecutable Compilado (Sin instalar nada)

Descarga el ejecutable directamente desde [GitHub Releases](https://github.com/habolanos/devsecops-toolbox/releases):

**Windows** 🪟
```powershell
# Descargar devsecops-toolbox.exe desde la página de releases
# Ejecutar directamente
.\devsecops-toolbox.exe
```

**Linux** 🐧
```bash
# Descargar devsecops-toolbox desde la página de releases
chmod +x devsecops-toolbox
./devsecops-toolbox
```

**Requisitos**: Ninguno (todo incluido en el ejecutable)

### Opción 3: Clonar Repositorio (Para desarrollo)

```bash
git clone https://github.com/habolanos/devsecops-toolbox.git
cd devsecops-toolbox
pip install -e ".[test]"
```

**Requisitos**: Python 3.11+

### Opción 4: Docker

```bash
# Descargar imagen
docker pull devsecops-toolbox:latest

# O construir localmente
docker build -t devsecops-toolbox:latest .
```

**Requisitos**: Docker 20.10+ y Docker Compose 2.0+

---

### � Compilar Ejecutables desde el Código Fuente

Si necesitas generar los ejecutables localmente:

```bash
# Instalar PyInstaller
pip install pyinstaller

# Compilar (Windows y Linux)
python build_executables.py
```

El ejecutable se genera en `dist/devsecops-toolbox.exe` (Windows) o `dist/devsecops-toolbox` (Linux).

> **Nota**: Los binarios compilados y archivos `.spec` están excluidos del repositorio via `.gitignore`. No se deben commitear.

---

### �📊 Comparativa de Instalación

| Método | Requisitos | Complejidad | Velocidad |
|--------|-----------|-----------|----------|
| **Winget** (Opción 1) | Windows 10+ | ⭐ Muy Simple | ⚡ Inmediato |
| **Ejecutable** (Opción 2) | Ninguno | ⭐ Muy Simple | ⚡ Inmediato |
| **Clonar repo** (Opción 3) | Python 3.11+ | ⭐⭐ Simple | ⚡⚡ Rápido |
| **Docker** (Opción 4) | Docker 20.10+ | ⭐⭐⭐ Moderado | ⚡⚡⚡ Más lento |

---

## 🎯 Uso Rápido

### ⭐ Opción Recomendada: Launcher Principal

```bash
# Desde la raíz del proyecto
python scm/main.py
```

**Esto te abrirá un menú interactivo con todas las opciones:**

```
╔═══════════════════════════════════════════════════════════════╗
║          🔐 DevSecOps Toolbox - Launcher Principal           ║
╚═══════════════════════════════════════════════════════════════╝

[1] ☁️  GCP (Google Cloud Platform)
[2] ☁️  AZURE (Azure Cloud Platform)
[3] 🔷 AZDO (Azure DevOps)
[4] 🟠 AWS (Amazon Web Services)
[5] 🐧 Terminal (Scripts Universales)
[6] 📊 KPI Analyzer Pro

[A] 🚀 Ejecutar Todas las Herramientas
[Q] 🚪 Salir

Selecciona una opción [1-6, A, Q]:
```

---

### 📋 Opciones Disponibles

#### **Opción 1: GCP (Google Cloud Platform)** ☁️

Herramientas para Google Cloud Platform con 22 utilidades SRE:
- Monitoreo de Recursos GCP
- Reporte de Despliegues GKE
- Auditoría de Roles y Permisos
- Service Accounts Reporter
- Event Tracker (Rastreo de eventos)
- Y más...

#### **Opción 2: AZURE (Azure Cloud Platform)** ☁️

**[NUEVO]** Herramientas para Azure Cloud con 25 utilidades SRE:
- Monitoreo de Recursos Azure
- Reporte de Despliegues AKS
- Auditoría de Roles y Permisos (RBAC)
- AKS Cluster Monitor
- App Service Monitor
- Azure SQL Database Monitor
- Cosmos DB Analyzer
- Event Tracker (Rastreo de eventos en Azure)
- Azure Unified Infrastructure Dashboard
- Y más...

#### **Opción 3: AZDO (Azure DevOps)** 🔷
Herramientas para gestión de repositorios, pipelines y releases en Azure DevOps:
- PR Master Checker
- Branch Policy Checker
- Release CD Health
- Pipeline Drift Analyzer
- Task Validator
- **[21] Pipeline Updater** - Actualización masiva de pipelines con templates YAML
- **[22] Pipeline Rollback** - Rollback con 3 métodos (Full Backup, Hybrid, Manual Revision)
  - **Opción 6: Redo** ⭐ NUEVO - Volver a versión previa del pipeline basado en definition_id
- **[27] Pipeline CD Backup & Restore** ⭐ NUEVO - Backup/restore completo de definiciones CD (individual máx 500, masivo, restore, crear desde backup, diff, conversión JSON→YAML)
- **[40] Health Probe Masivo Validator** ⭐ NUEVO

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 1 (AZDO)
# Luego seleccionar herramienta específica (1-40)
```

#### **Opción 2: GCP (Google Cloud Platform)** ☁️
Herramientas especializadas para operaciones SRE en GCP:
- Service Account Checker
- Cloud SQL Manager
- GKE Cluster Manager
- Cloud Run Tools Suite
- Connectivity Checkers

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 2 (GCP)
```

#### **Opción 3: AWS (Amazon Web Services)** 🟠
Herramientas DevSecOps para AWS:
- IAM Analyzer
- RDS Manager
- VPC Manager
- EKS Manager
- ECR Scanner
- Lambda Manager

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 3 (AWS)
```

#### **Opción 4: Terminal (Scripts Universales)** 🐧
Scripts agnósticos de cloud provider para cualquier cluster Kubernetes:
- Certificate TLS Report
- Database Connections Checker
- Deployments Last News
- Deployments Last Update

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 4 (Terminal)
```

#### **Opción 5: KPI Analyzer Pro** 📊
Análisis de métricas DevSecOps con modelo de madurez y dashboards:
- Health Score DORA
- Exporter (JSON, CSV, HTML, Excel)
- Consolidator (multi-fuente)
- Generator (dashboards HTML)
- Scheduler (planificación automática)

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 5 (KPI Analyzer Pro)
```

#### **Opción 6: Dashboard Matutino** 📈
Dashboard automatizado que consolida el estado de repositorios, pipelines y servicios:
- Ejecución automática diaria
- Consolidación multi-cloud
- Visualización web interactiva
- Notificaciones inteligentes

```bash
# Acceso directo
python scm/main.py
# Seleccionar: 6 (Dashboard Matutino)
```

#### **Opción A: Ejecutar Todas las Herramientas** 🚀
Ejecuta todas las herramientas con la misma configuración (sin Deep Dive):

```bash
python scm/main.py
# Seleccionar: A
```

#### **Opción B: Ejecutar Todo + JSON** ⚡
Ejecuta TODAS las herramientas forzando salida JSON en `outcome/` (ideal para Dashboard):

```bash
python scm/main.py
# Seleccionar: B
```

---

### 🚀 Acceso Directo a Plataformas (Avanzado)

Si prefieres acceder directamente a una plataforma sin pasar por el menú principal:

```bash
# Herramientas GCP
python scm/gcp/tools.py

# Herramientas Azure DevOps
python scm/azdo/tools.py

# Herramientas AWS
python scm/aws/tools.py

# Herramientas KPI Analyzer
python scm/kpi_analyzer/tools.py
```

---

## 📋 Templates para Pipeline Updater

La carpeta `scm/templates/` contiene templates YAML predefinidos para actualizar masivamente pipelines CD en Azure DevOps usando la herramienta **Pipeline Updater (Tool 21)**.

### 🎯 ¿Qué son los Templates?

Los templates son archivos YAML que definen:
- **Qué buscar**: Stages, tasks, variables específicas
- **Qué cambiar**: Valores antiguos y nuevos
- **Metadatos**: Nombre, versión, comentarios de auditoría

### 📁 Templates Disponibles

#### **1. pipe_cd_update_docker.yaml** 🐳
Actualizar imagen Docker en pipelines de producción.

**Caso de uso**: Promocionar nueva versión de aplicación
```yaml
metadata:
  name: "Cambiar imagen Docker"
  comment: "Cambios: myapp:v1.0 → myapp:v2.0"

search:
  stages: ["Producción"]
  tasks:
    - name: "Push Docker"

update:
  tasks:
    - name: "Push Docker"
      fields:
        - path: "inputs.repository"
          old_value: "myapp:v1.0"
          new_value: "myapp:v2.0"
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_update_docker.yaml
```

---

#### **2. pipe_cd_update_kubernetes.yaml** ☸️
Cambiar cluster Kubernetes y namespace.

**Caso de uso**: Migración a nuevo cluster o cambio de región
```yaml
metadata:
  name: "Cambiar cluster Kubernetes"
  comment: "Cambios: old-gke-cluster → new-gke-cluster"

search:
  stages: ["Producción", "Staging"]
  tasks:
    - name: "Deploy"

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-gke-cluster"
          new_value: "new-gke-cluster"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_update_kubernetes.yaml
```

---

#### **3. pipe_cd_update_variables.yaml** 🔧
Cambiar variables de entorno en pipelines.

**Caso de uso**: Promoción de ambiente (staging → production)
```yaml
metadata:
  name: "Cambiar variables de entorno"
  comment: "Cambios: ENVIRONMENT staging → production"

search:
  variables:
    - name: "ENVIRONMENT"

update:
  variables:
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_update_variables.yaml
```

---

#### **4. pipe_cd_update_azure.yaml** ☁️
Cambiar suscripción Azure en tasks.

**Caso de uso**: Consolidación de suscripciones o cambio de tenant
```yaml
metadata:
  name: "Cambiar suscripción Azure"
  comment: "Cambios: old-subscription → new-subscription"

search:
  stages: ["Deploy"]
  tasks:
    - name: "Deploy"

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.azureSubscription"
          old_value: "old-subscription"
          new_value: "new-subscription"
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_update_azure.yaml
```

---

#### **5. pipe_cd_update_script.yaml** 📝
Cambiar contenido de scripts PowerShell en tasks.

**Caso de uso**: Actualizar scripts de deployment o validación
```yaml
metadata:
  name: "Cambiar script PowerShell"
  comment: "Actualizar script de validación"

search:
  stages: ["Deploy"]
  tasks:
    - name: "PowerShell Script"

update:
  tasks:
    - name: "PowerShell Script"
      fields:
        - path: "inputs.script"
          old_value: "old-script-content"
          new_value: "new-script-content"
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_update_script.yaml
```

---

#### **6. pipe_cd_update_migracion.yaml** 🚀
Realizar múltiples cambios simultáneamente.

**Caso de uso**: Migración completa (imagen Docker + cluster K8s + variables)
```yaml
metadata:
  name: "Migración completa"
  comment: "Cambios: Docker + Kubernetes + Variables"

search:
  stages: ["Producción"]
  tasks:
    - name: "Deploy"

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.repository"
          old_value: "myapp:v1.0"
          new_value: "myapp:v2.0"
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-cluster"
          new_value: "new-cluster"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_update_migracion.yaml
```

---

#### **7. pipe_cd_move_to_folder.yaml** 📁
Mover pipelines CD a otra carpeta en Azure DevOps.

**Caso de uso**: Reorganizar pipelines moviéndolos a una carpeta de decomiso o nueva estructura

Soporta el placeholder `{current}` que se reemplaza por el path actual del pipeline, permitiendo mover sin conocer el path previo:

```yaml
metadata:
  name: "Mover Pipeline CD a otra carpeta"
  comment: "Pipeline movido a nueva carpeta via pipeline_updater"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "move"
    path: '\Decomiso{current}'
```

**Cómo funciona `{current}`**:
- Si el pipeline está en `\GCP\Proyecto WMS\Equipo WMS` → resultado: `\Decomiso\GCP\Proyecto WMS\Equipo WMS`
- Si el pipeline está en `\Other\Folder` → resultado: `\Decomiso\Other\Folder`
- Si el pipeline no tiene path (vacío) → resultado: `\Decomiso`

**También soporta path absoluto** (sin `{current}`):
```yaml
    path: '\Decomiso\GCP\Proyecto WMS\Equipo WMS'
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_move_to_folder.yaml
```

---

#### **8. pipe_cd_copy_stage_from_pipeline.yaml** 📋
Copiar un stage desde otro pipeline (cross-pipeline) e insertarlo con un nuevo nombre.

**Caso de uso**: Copiar un stage "QA" desde un pipeline origen e insertarlo en otro pipeline como "QA-Copia"

```yaml
metadata:
  name: "Copiar stage desde otro pipeline"
  comment: "Copia cross-pipeline de stage"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758    # Pipeline origen
      source_stage: "QA"            # Stage a copiar
      new_name: "QA-Copia"          # Nombre en el destino
      position: "after"             # after | before | start | end
      reference_stage: "Develop"    # Ancla en el destino
      task_updates:                 # Modificar tasks del stage copiado
        - task_name: "Deploy to QA"
          fields:
            - path: "inputs.namespace"
              new_value: "qa-copia"
```

**Cómo funciona**:
1. Descarga el pipeline origen (`source_definition_id`)
2. Extrae el stage (`source_stage`)
3. Lo inserta en el pipeline destino con `new_name`
4. Aplica `task_updates` al stage copiado (opcional)
5. Reasigna ranks consecutivamente

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_copy_stage_from_pipeline.yaml
```

---

#### **9. pipe_cd_autosort_stages.yaml** 🔢
Auto-ordenar stages alfanuméricamente con stages fijos.

**Caso de uso**: Reordenar stages numerados (01-cedis, 02-cedis, ...) manteniendo fijos los stages no numerados (Develop, QA, Production)

```yaml
metadata:
  name: "Auto-ordenar stages numericos alfanumerico"
  comment: "Ordena stages numericos asc, fijos por rank declarado"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "autosort_stages"
    fixed_stages:
      - name: "Develop"
        rank: 1
      - name: "QA"
        rank: 2
      - name: "Production"
        rank: 3
    sort_pattern: "^\\d{2}-.*"
    sort_order: "asc"
```

**Uso**:
```bash
python scm/main.py
# Seleccionar: 3 (AZDO) → 21 (Pipeline Updater)
# Ingresar: scm/templates/pipe_cd_autosort_stages.yaml
```

---

### 🚀 Cómo Usar Templates

#### **Paso 1: Personalizar Template**

Copia uno de los templates y personaliza los valores según tu necesidad:

```bash
# Copiar template base
cp scm/templates/pipe_cd_update_docker.yaml scm/templates/mi-cambio.yaml

# Editar con tu editor favorito
nano scm/templates/mi-cambio.yaml
```

Personaliza:
- `metadata.name`: Nombre descriptivo
- `metadata.comment`: Descripción del cambio
- `search`: Qué buscar (stages, tasks, variables)
- `update`: Qué cambiar (old_value → new_value)

#### **Paso 2: Ejecutar Pipeline Updater**

```bash
python scm/main.py
```

Luego sigue estos pasos:
1. Selecciona: **3 (AZDO)**
2. Selecciona: **21 (Pipeline Updater)**
3. Ingresa: **definition-ids** (ej: 3388,3389,3390)
4. Ingresa: **ruta del template** (ej: scm/templates/mi-cambio.yaml)
5. Confirma: **Y** para ejecutar

#### **Paso 3: Revisar Resultados**

El programa generará un reporte con:
- Pipelines procesados
- Cambios aplicados
- Errores (si los hay)
- Auditoría completa

```
✅ Pipeline 3388: 2 cambios aplicados
✅ Pipeline 3389: 1 cambio aplicado
❌ Pipeline 3390: Error - Task no encontrada
```

---

### 📊 Estructura de Template YAML

```yaml
metadata:
  name: "Nombre descriptivo"
  version: "1.0"
  comment: |
    Descripción detallada del cambio
    Razón del cambio
    Aprobado por: [Persona]
    Fecha: [YYYY-MM-DD]

search:
  # Buscar en stages específicos (opcional)
  stages: ["Producción", "Staging"]
  
  # Buscar tasks específicas (opcional)
  tasks:
    - name: "Nombre exacto de la task"
  
  # Buscar variables específicas (opcional)
  variables:
    - name: "NOMBRE_VARIABLE"

update:
  # Actualizar tasks
  tasks:
    - name: "Nombre de la task"
      fields:
        - path: "inputs.nombrePropiedad"
          old_value: "valor_actual"
          new_value: "valor_nuevo"
  
  # Actualizar variables
  variables:
    - name: "NOMBRE_VARIABLE"
      old_value: "valor_actual"
      new_value: "valor_nuevo"
```

---

### ✅ Checklist Antes de Ejecutar

- [ ] Personalicé el template con mis valores
- [ ] Verifiqué nombres exactos de stages/tasks
- [ ] Preparé lista de definition-ids
- [ ] Guardé el archivo en `scm/templates/`
- [ ] Leí la documentación completa
- [ ] Tengo backup de los pipelines
- [ ] Estoy listo para ejecutar

---

### 🔒 Seguridad y Auditoría

✅ **Validación automática** de estructura YAML  
✅ **Confirmación del usuario** antes de ejecutar  
✅ **Snapshots automáticos** antes de cambios  
✅ **Rollback automático** si algo falla  
✅ **Auditoría completa** en cada pipeline  
✅ **Reporte detallado** de cambios aplicados  

---

### 📚 Documentación Adicional

Para más información sobre templates y Pipeline Updater:

- `scm/templates/README.md` - Guía rápida de templates
- `docs/features/feature_actualizacion_pipeline_cd_with_template/README.md` - Documentación completa
- `docs/features/feature_actualizacion_pipeline_cd_with_template/ESPECIFICACION.md` - Especificación técnica
- `docs/features/feature_actualizacion_pipeline_cd_with_template/EJEMPLOS.md` - Ejemplos avanzados

---

### 🐳 Con Docker

```bash
# Ejecutar toolbox interactivo
docker-compose up -d toolbox
docker-compose exec toolbox bash

# Ejecutar comando específico
docker run --rm devsecops-toolbox:latest az version
docker run --rm devsecops-toolbox:latest aws --version
docker run --rm devsecops-toolbox:latest gcloud version
```

---

### 💡 Ejemplos Prácticos

#### Ejemplo 1: Validar Health Probes en Kubernetes
```bash
python scm/main.py
# Seleccionar: 1 (AZDO)
# Seleccionar: 40 (Health Probe Masivo Validator)
# Ingresar: deployment-web-prod,deployment-api-prod
```

#### Ejemplo 2: Ejecutar Análisis de KPI
```bash
python scm/main.py
# Seleccionar: 5 (KPI Analyzer Pro)
# Seleccionar herramienta específica
```

#### Ejemplo 3: Generar Dashboard Completo
```bash
python scm/main.py
# Seleccionar: B (Ejecutar Todo + JSON)
# Esperar a que se ejecuten todas las herramientas
# Los JSONs se guardarán en outcome/
```

---

## 📊 Dashboard Matutino

**⭐ NUEVO:** Dashboard automatizado que consolida el estado de repositorios, pipelines, servicios e infraestructura.

### Características

- ✅ **Ejecución Automática Diaria** - Se ejecuta cada mañana a las 7:00 AM
- ✅ **Consolidación Multi-Cloud** - Datos de AZDO, GCP y AWS en un único dashboard
- ✅ **Visualización Web Interactiva** - HTML con gráficos, tablas y alertas
- ✅ **Notificaciones Inteligentes** - Email, Slack, Teams (configurable)
- ✅ **Análisis de Tendencias** - Histórico de 90 días para análisis
- ✅ **80% Reutilización** - Aprovecha herramientas existentes

### Métricas Incluidas

| Métrica | Descripción |
|---------|-------------|
| **Repositorios** | Total, con CI/CD, sin pipeline |
| **Health Score** | Score DORA/SRE (0-100) |
| **Branch Compliance** | % de cumplimiento de políticas |
| **Pull Requests** | Tiempo promedio a merge, SLA compliance |
| **Servicios** | Estado GCP/AWS, alertas críticas |
| **Bases de Datos** | Uso de disco, instancias con alertas |

### Inicio Rápido

```bash
# 1. Leer documentación
cat DASHBOARD_README.md

# 2. Ejecutar orquestador (Tool 26)
python scm/azdo/dashboard_consolidator.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT"

# 3. Generar dashboard web (Tool 27)
python scm/dashboard/dashboard_generator.py \
  --input "outcome/dashboard/dashboard_data_*.json"

# 4. Ver resultado
open outcome/dashboard/dashboard.html
```

### Documentación Completa

- 📖 **[DASHBOARD_README.md](DASHBOARD_README.md)** - Índice de documentación
- 📋 **[DASHBOARD_EXECUTIVE_SUMMARY.md](DASHBOARD_EXECUTIVE_SUMMARY.md)** - Resumen ejecutivo
- 🏗️ **[DASHBOARD_ARCHITECTURE.md](DASHBOARD_ARCHITECTURE.md)** - Arquitectura técnica
- 📊 **[DASHBOARD_REUSABILITY_MATRIX.md](DASHBOARD_REUSABILITY_MATRIX.md)** - Matriz de reutilización
- 🎯 **[DASHBOARD_ACTION_PLAN.md](DASHBOARD_ACTION_PLAN.md)** - Plan de acción
- 💻 **[DASHBOARD_CODE_EXAMPLES.md](DASHBOARD_CODE_EXAMPLES.md)** - Ejemplos de código

---

## 🐳 Docker

El proyecto incluye una imagen Docker optimizada (~400MB) con todas las herramientas CLI necesarias.

### Herramientas Incluidas

| Herramienta | Descripción |
|-------------|-------------|
| **Azure CLI** | Gestión de Azure Portal y Azure DevOps |
| **AWS CLI v2** | Gestión de recursos AWS |
| **Google Cloud SDK** | Gestión de GCP (gcloud) |
| **kubectl** | Gestión de clusters Kubernetes |
| **Helm** | Package manager para Kubernetes |
| **Terraform** | Infraestructura como código |
| **Netshoot** | ping, dig, traceroute, tcpdump, nmap, netcat, etc. |

### Uso con Docker Compose

```bash
# 1. Configurar credenciales
cp .env.example .env
# Editar .env con tus credenciales

# 2. Iniciar servicios
docker-compose up -d toolbox

# 3. Acceder al contenedor
docker-compose exec toolbox bash
```

### Servicios Disponibles

| Servicio | Uso | Comando |
|----------|-----|---------|
| `toolbox` | Uso interactivo | `docker-compose up -d toolbox` |
| `toolbox-dev` | Desarrollo con live reload | `docker-compose --profile dev up -d toolbox-dev` |
| `toolbox-cmd` | CI/CD - ejecuta y sale | `docker-compose --profile cmd run --rm toolbox-cmd` |

**Ver documentación completa de Docker en:** [`scm/README.md`](scm/README.md#-docker-container)

---

## ☁️ Plataformas Soportadas

### Google Cloud Platform (GCP)

Herramientas especializadas para operaciones SRE en GCP:

- Artifact Registry Manager
- Certificate Manager
- Cloud Armor Configurator
- Cloud SQL Manager
- GKE Cluster Manager
- Gateway Services Manager
- Monitoring & Logging
- Reports Viewer
- Roles & Permisos
- Secrets & ConfigMaps
- VPC Networks Manager
- Connectivity Checkers (Pods, Dependencies, DNS)

### Azure DevOps (AZDO)

Herramientas para gestión de proyectos Azure DevOps:

- Project Analyzer
- Pipeline Manager
- Repository Manager
- Work Item Manager
- Build & Release Tools

### Amazon Web Services (AWS)

Herramientas DevSecOps para AWS:

- IAM Analyzer
- RDS Manager
- VPC Manager
- EKS Manager
- ECR Scanner
- EC2 Manager
- Lambda Manager
- CloudWatch Monitor
- Security Analyzer
- Cost Optimizer
- Compliance Checker
- Network Tester
- Secrets Manager

### Terminal / Scripts Universales 🔧

Scripts shell **agnósticos de cloud provider** que funcionan con cualquier cluster Kubernetes (GKE, EKS, AKS, OpenShift, on-premise):

- **Certificate TLS Report** - Valida certificados SSL/TLS remotos desde cualquier cluster K8s (CN, emisor, expiración, chain, TLS version, cipher reales)
- **Database Connections Checker** - Valida conectividad a múltiples instancias PostgreSQL usando netcat
- **Deployments Last News** - Muestra deployments más recientes ordenados por fecha de creación
- **Deployments Last Update** - Muestra deployments ordenados por último rollout (ReplicaSet)
- **Deployments Recent Events** - Muestra eventos recientes relacionados con Deployments

> **Nota:** Estos scripts requieren un entorno Linux/Unix (WSL, Git Bash, o Linux nativo).

---

## ⚙️ Configuración

### Configuración Inicial (Wizard Automático)

Desde la versión 1.7.23, **la primera ejecución del toolbox lanza un wizard interactivo** que detecta CLIs instalados (gcloud, az, aws), sesiones activas, y hidrata `config.json` automáticamente:

```bash
# Ejecutar el launcher (wizard aparece automáticamente si config.json no existe)
python scm/main.py
```

El wizard:
- **Detecta** gcloud/az/aws instalados y sesiones activas
- **Sugiere** project_id (GCP), subscription (Azure), profile (AWS) desde la sesión activa
- **Hidrata** AZDO (org, project, pat), GCP, Azure, AWS, Dashboard y Global
- **Valida** que no queden placeholders `<TU_*>` sin hidratar
- **Guarda** `config.json` limpio (sin keys de metadata `_info`)

Pasos opcionales (Azure, AWS, Dashboard) se pueden skip con Enter.

### Configuración Manual (sin wizard)

```bash
# 1. Copiar el template
cp scm/config.json.template scm/config.json

# 2. Editar con tus credenciales
nano scm/config.json
```

### Estructura del config.json

```json
{
  "azdo": {
    "enabled": true,
    "organization_url": "https://dev.azure.com/TU_ORGANIZACION",
    "project": "TU_PROYECTO",
    "pat": "TU_PAT_TOKEN"
  },
  "gcp": {
    "enabled": true,
    "project_id": "TU_PROJECT_ID",
    "region": "us-central1",
    "credentials": {
      "type": "adc",
      "service_account_key_path": ""
    }
  },
  "aws": {
    "enabled": true,
    "profile": "default",
    "region": "us-east-1",
    "credentials": {
      "type": "profile"
    }
  },
  "global": {
    "debug": false,
    "output_dir": "outcome"
  }
}
```

> ⚠️ **IMPORTANTE**: El archivo `config.json` está en `.gitignore`. Nunca lo subas al repositorio.

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Tests unitarios
pytest scm/tests/unit/ -v

# Tests de integración
pytest scm/tests/integration/ -v

# Todos los tests con cobertura
pytest scm/tests/ -v --cov=scm --cov-report=html

# Ver reporte de cobertura
open htmlcov/index.html
```

### Testing en Docker

```bash
# Ejecutar tests en contenedor
docker-compose --profile dev up -d toolbox-dev
docker-compose exec toolbox-dev pytest scm/tests/ -v
```

**Ver guía completa de testing en:** [`scm/README.md`](scm/README.md#-testing)

---

## 📁 Estructura del Proyecto

```
devsecops-toolbox/
├── scm/                          # Código fuente principal
│   ├── main.py                   # Launcher principal (ejecuta wizard en 1a ejecucion)
│   ├── setup/                    # Wizard de configuracion inicial
│   ├── gcp/                      # Herramientas GCP
│   ├── azdo/                     # Herramientas AZDO (28 herramientas)
│   │   ├── azdo_pipeline_history.py  # Tool 26: Evolución histórica de Pipeline CD (HTML interactivo)
│   │   ├── pipeline_cd_backup_restore.py  # Tool 27: Backup & Restore completo de Pipeline CD
│   │   └── ...
│   ├── aws/                      # Herramientas AWS
│   ├── terminal/                 # Scripts universales (agnostic cloud)
│   ├── tests/                    # Tests (unitarios e integración)
│   ├── config.json.template      # Template de configuración
│   └── README.md                 # Documentación detallada
├── build_executables.py          # Compilador de ejecutables (PyInstaller)
├── winget/                       # Manifests de Windows Package Manager
│   └── manifests/h/habolanos/devsecops-toolbox/
│       └── 1.7.20/               # YAML manifests por versión
├── dist/                         # Ejecutables compilados
├── Dockerfile                    # Imagen Docker
├── docker-compose.yml            # Orquestación Docker
├── docker-entrypoint.sh          # Script de inicio Docker
├── .env.example                  # Template de variables de entorno
├── .dockerignore                 # Exclusiones de Docker build
├── pytest.ini                   # Configuración de pytest
├── pyproject.toml               # Metadatos del proyecto
├── VERSION                      # Versión actual (SemVer)
├── scripts/                     # Scripts de utilidad
│   ├── bump_version.py          # Gestión de versiones SemVer
│   └── sync-gcp.ps1             # Sincronización GCP entre repos (PowerShell)
├── sync_repos.py                 # Sincronización completa toolbox ↔ azdo (Python)
└── README.md                     # Este archivo
```

---

## 🏷️ Versionado Semántico (SemVer)

El proyecto sigue [Semantic Versioning 2.0.0](https://semver.org/lang/es/):

```
VERSION = MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

MAJOR  - Cambios incompatibles
MINOR  - Nuevas funcionalidades
PATCH  - Correcciones de bugs
```

### Gestión de Versiones

```bash
# Incrementar versión patch
python scripts/bump_version.py --patch

# Incrementar versión minor
python scripts/bump_version.py --minor

# Establecer versión explícita
python scripts/bump_version.py 2.0.0

# Validar consistencia
python scripts/bump_version.py --validate
```

---

## 📝 Contribuir

1. Fork el repositorio
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'feat: agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

### Guías de Contribución

- Seguir [Conventional Commits](https://www.conventionalcommits.org/)
- Mantener cobertura de tests > 70%
- Documentar nuevas funcionalidades en README
- Actualizar versiones usando `scripts/bump_version.py`

---

## 📜 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

---

## 📚 Historial de Cambios

**Ver historial completo y detallado en:** [`README.version.md`](README.version.md)

---

## 👤 Autor

**Harold Adrian**

- GitHub: [@habolanos](https://github.com/habolanos)
- Repositorio: [devsecops-toolbox](https://github.com/habolanos/devsecops-toolbox)

---

<p align="center">
  <b>🔐 DevSecOps Toolbox - Multi-Cloud DevOps Made Simple</b>
</p>

## 📊 Estadísticas del repositorio

![GitHub stars](https://img.shields.io/github/stars/habolanos/devsecops-toolbox?style=social)
![GitHub forks](https://img.shields.io/github/forks/habolanos/devsecops-toolbox?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/habolanos/devsecops-toolbox?style=social)