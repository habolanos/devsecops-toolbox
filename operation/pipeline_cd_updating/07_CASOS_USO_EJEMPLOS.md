# 🎓 Casos de Uso y Ejemplos

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Objetivo:** Ejemplos prácticos de actualización en diferentes escenarios

---

## 📋 Resumen Ejecutivo

Ejemplos prácticos de cómo actualizar pipelines CD en diferentes escenarios.

---

## 🎯 CASO 1: Actualizar Variable de Configuración

### Escenario
Necesitas cambiar la configuración de compilación de "Release" a "Debug" en un pipeline.

### Paso a Paso

#### Paso 1: Identificar Variable
```yaml
# ANTES
variables:
  buildConfiguration: 'Release'
  buildPlatform: 'Any CPU'
```

#### Paso 2: Actualizar Variable
```yaml
# DESPUÉS
variables:
  buildConfiguration: 'Debug'
  buildPlatform: 'Any CPU'
```

#### Paso 3: Validar Cambios
```
1. Revisar sintaxis YAML
2. Ejecutar pipeline
3. Validar artefactos
4. Revisar logs
```

#### Paso 4: Documentar
```
Cambio: Actualizar buildConfiguration
Antes: Release
Después: Debug
Razón: Debugging en ambiente de desarrollo
Validación: Pipeline ejecuta correctamente
```

---

## 🎯 CASO 2: Cambiar Imagen Docker

### Escenario
Necesitas actualizar la imagen Docker base de "ubuntu:20.04" a "ubuntu:22.04".

### Paso a Paso

#### Paso 1: Identificar Imagen
```yaml
# ANTES
container:
  image: ubuntu:20.04
```

#### Paso 2: Actualizar Imagen
```yaml
# DESPUÉS
container:
  image: ubuntu:22.04
```

#### Paso 3: Validar Cambios
```
1. Revisar compatibilidad
2. Ejecutar pipeline
3. Validar dependencias
4. Revisar logs
```

#### Paso 4: Documentar
```
Cambio: Actualizar imagen Docker
Antes: ubuntu:20.04
Después: ubuntu:22.04
Razón: Actualización de seguridad
Validación: Pipeline ejecuta correctamente
```

---

## 🎯 CASO 3: Agregar Nuevo Stage

### Escenario
Necesitas agregar un nuevo stage de "Testing" entre "Build" y "Deploy".

### Paso a Paso

#### Paso 1: Identificar Ubicación
```yaml
# ANTES
stages:
- stage: Build
  jobs:
  - job: BuildJob
    steps:
    - script: echo Building

- stage: Deploy
  dependsOn: Build
  jobs:
  - job: DeployJob
    steps:
    - script: echo Deploying
```

#### Paso 2: Agregar Stage
```yaml
# DESPUÉS
stages:
- stage: Build
  jobs:
  - job: BuildJob
    steps:
    - script: echo Building

- stage: Test
  dependsOn: Build
  jobs:
  - job: TestJob
    steps:
    - script: echo Testing

- stage: Deploy
  dependsOn: Test
  jobs:
  - job: DeployJob
    steps:
    - script: echo Deploying
```

#### Paso 3: Validar Cambios
```
1. Revisar dependencias
2. Ejecutar pipeline
3. Validar orden de stages
4. Revisar logs
```

#### Paso 4: Documentar
```
Cambio: Agregar stage de Testing
Ubicación: Entre Build y Deploy
Dependencias: Build → Test → Deploy
Validación: Pipeline ejecuta correctamente
```

---

## 🎯 CASO 4: Actualizar Aprobaciones

### Escenario
Necesitas cambiar los aprobadores del stage "Deploy" de "John" a "John, Jane, Bob".

### Paso a Paso

#### Paso 1: Identificar Aprobaciones
```yaml
# ANTES
stages:
- stage: Deploy
  jobs:
  - deployment: DeployJob
    approvals:
    - approver: john@company.com
```

#### Paso 2: Actualizar Aprobadores
```yaml
# DESPUÉS
stages:
- stage: Deploy
  jobs:
  - deployment: DeployJob
    approvals:
    - approver: john@company.com
    - approver: jane@company.com
    - approver: bob@company.com
```

#### Paso 3: Validar Cambios
```
1. Revisar aprobadores
2. Validar permisos
3. Ejecutar pipeline
4. Probar aprobación
```

#### Paso 4: Documentar
```
Cambio: Actualizar aprobadores del Deploy
Antes: john@company.com
Después: john@company.com, jane@company.com, bob@company.com
Razón: Requerimiento de múltiples aprobaciones
Validación: Aprobación funciona correctamente
```

---

## 🎯 CASO 5: Cambiar Trigger

### Escenario
Necesitas cambiar el trigger de "solo main" a "main y develop".

### Paso a Paso

#### Paso 1: Identificar Trigger
```yaml
# ANTES
trigger:
  branches:
    include:
    - main
```

#### Paso 2: Actualizar Trigger
```yaml
# DESPUÉS
trigger:
  branches:
    include:
    - main
    - develop
```

#### Paso 3: Validar Cambios
```
1. Revisar ramas
2. Hacer cambio en develop
3. Validar que se dispara
4. Revisar logs
```

#### Paso 4: Documentar
```
Cambio: Actualizar trigger
Antes: Solo main
Después: main y develop
Razón: Incluir rama de desarrollo
Validación: Trigger funciona en ambas ramas
```

---

## 🎯 CASO 6: Actualización Masiva de Variables

### Escenario
Necesitas actualizar 5 pipelines para cambiar el servidor de "prod-1" a "prod-2".

### Paso a Paso

#### Paso 1: Preparar Script
```powershell
$pipelines = @(
    "Pipeline1",
    "Pipeline2",
    "Pipeline3",
    "Pipeline4",
    "Pipeline5"
)

foreach ($pipeline in $pipelines) {
    # Crear snapshot
    # Cambiar variable
    # Validar
}
```

#### Paso 2: Crear Snapshots
```
1. Crear carpeta: backups/20260708/
2. Guardar YAML de cada pipeline
3. Documentar lista
```

#### Paso 3: Ejecutar Cambios
```
1. Ejecutar script
2. Monitorear progreso
3. Validar cada cambio
4. Registrar resultados
```

#### Paso 4: Validar Resultados
```
1. Ejecutar cada pipeline
2. Validar que conectan a prod-2
3. Revisar logs
4. Documentar resultados
```

---

## 📊 Matriz de Complejidad

| Caso | Complejidad | Tiempo | Riesgo | Herramientas |
|------|------------|--------|--------|-------------|
| **Caso 1** | Baja | 15 min | Bajo | Manual |
| **Caso 2** | Baja | 20 min | Bajo | Manual |
| **Caso 3** | Media | 30 min | Medio | Manual |
| **Caso 4** | Media | 25 min | Medio | Manual |
| **Caso 5** | Baja | 20 min | Bajo | Manual |
| **Caso 6** | Alta | 2-3h | Medio | Script |

---

## 🆘 Troubleshooting por Caso

### Caso 1: Variable no se aplica
```
Solución:
1. Verificar nombre de variable
2. Revisar sintaxis
3. Validar scope
4. Ejecutar pipeline
```

### Caso 2: Imagen no se encuentra
```
Solución:
1. Verificar nombre de imagen
2. Revisar disponibilidad
3. Validar permisos
4. Usar imagen alternativa
```

### Caso 3: Stage no ejecuta
```
Solución:
1. Revisar dependencias
2. Validar sintaxis
3. Revisar condiciones
4. Ejecutar manualmente
```

### Caso 4: Aprobación no funciona
```
Solución:
1. Verificar aprobadores
2. Validar permisos
3. Revisar sintaxis
4. Probar aprobación
```

### Caso 5: Trigger no se dispara
```
Solución:
1. Verificar ramas
2. Revisar configuración
3. Validar paths
4. Probar manualmente
```

### Caso 6: Actualización masiva falla
```
Solución:
1. Identificar pipeline fallido
2. Revisar logs
3. Ejecutar rollback
4. Actualizar manualmente
```

---

## 📋 Checklist por Caso

### Caso 1: Variable
- [ ] Variable identificada
- [ ] Valor actualizado
- [ ] Sintaxis validada
- [ ] Pipeline ejecutado
- [ ] Cambio documentado

### Caso 2: Imagen Docker
- [ ] Imagen identificada
- [ ] Imagen actualizada
- [ ] Compatibilidad validada
- [ ] Pipeline ejecutado
- [ ] Cambio documentado

### Caso 3: Nuevo Stage
- [ ] Ubicación identificada
- [ ] Stage agregado
- [ ] Dependencias configuradas
- [ ] Pipeline ejecutado
- [ ] Cambio documentado

### Caso 4: Aprobaciones
- [ ] Aprobadores identificados
- [ ] Aprobadores actualizados
- [ ] Permisos validados
- [ ] Aprobación probada
- [ ] Cambio documentado

### Caso 5: Trigger
- [ ] Trigger identificado
- [ ] Ramas actualizadas
- [ ] Trigger probado
- [ ] Pipeline ejecutado
- [ ] Cambio documentado

### Caso 6: Actualización Masiva
- [ ] Script preparado
- [ ] Snapshots creados
- [ ] Cambios ejecutados
- [ ] Validación completada
- [ ] Cambios documentados

---

## 🆕 CASO 6: Reordenar Stages con Validación Exacta

### Escenario
Necesitas reordenar stages en pipelines que tengan EXACTAMENTE 4 stages (Build, Test, Deploy, Validate), sin tocar pipelines que tengan stages adicionales.

### Paso a Paso

#### Paso 1: Crear Template con `exact_match: true`

```yaml
metadata:
  name: "Reordenar stages - Validación exacta"
  version: "1.0"
  comment: |
    Reordena stages en pipelines con EXACTAMENTE 4 stages
    Ignora pipelines con stages adicionales

search:
  exact_match: true  # ← Validación exacta
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"

update:
  stages:
    - name: "Build"
      rank: 1
    - name: "Deploy"
      rank: 2
    - name: "Test"
      rank: 3
    - name: "Validate"
      rank: 4
```

#### Paso 2: Ejecutar Template

```bash
python scm/main.py
# → Seleccionar 3 (Azure DevOps)
# → Seleccionar 21 (Pipeline Updater)
# → Ingresar definition-ids
# → Ingresar: scm/templates/pipe_cd_reorder_stages_exact_match.yaml
# → Confirmar
```

#### Paso 3: Validar Resultados

```
Pipeline A: Build, Test, Deploy, Validate
            ✅ ACTUALIZADO (4 stages exactos)

Pipeline B: Build, Test, Deploy, Validate, Security
            ❌ IGNORADO (5 stages, no exacto)

Pipeline C: Build, Test, Deploy
            ❌ IGNORADO (3 stages, no exacto)
```

#### Paso 4: Revisar Reporte

```json
{
  "summary": {
    "total_pipelines": 3,
    "matched": 1,
    "ignored_exact_mismatch": 2,
    "success": 1
  }
}
```

### Ventajas

✅ **Garantiza integridad:** Solo toca pipelines con estructura exacta  
✅ **Previene errores:** No actualiza pipelines con variantes  
✅ **Auditable:** Fácil de rastrear qué se actualizó  
✅ **Seguro:** Parámetro opcional (default=false)  

### Cuándo Usar

- ✅ Migración crítica de infraestructura
- ✅ Cambios en estructura de stages
- ✅ Reordenamiento de stages
- ✅ Necesitas garantizar integridad

---

**Casos de Uso y Ejemplos v1.1.0**  
**Última actualización:** 24 de Julio de 2026
