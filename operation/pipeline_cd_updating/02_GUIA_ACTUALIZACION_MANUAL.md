# 🔧 Guía de Actualización Manual de Pipelines CD

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Objetivo:** Actualizar pipelines CD manualmente de forma segura

---

## 📋 Resumen Ejecutivo

Guía paso a paso para actualizar un pipeline CD manualmente en Azure DevOps con validaciones en cada etapa.

**Tiempo estimado:** 45 minutos por pipeline  
**Riesgo:** Bajo  
**Complejidad:** Baja

---

## 🎯 Cuándo Usar Esta Guía

- ✅ Actualización de 1-5 pipelines
- ✅ Cambios complejos o personalizados
- ✅ Requiere control total del proceso
- ✅ Pipelines críticos
- ✅ Cambios que afectan múltiples stages

---

## 📊 Fases de Actualización

### Fase 1: Preparación (10 minutos)
### Fase 2: Análisis (10 minutos)
### Fase 3: Cambios (15 minutos)
### Fase 4: Validación (10 minutos)

---

## 🔴 FASE 1: PREPARACIÓN

### Paso 1.1: Crear Snapshot Previo
```
1. Ir a Azure DevOps → Pipelines
2. Seleccionar pipeline a actualizar
3. Hacer clic en "Edit"
4. Copiar YAML completo
5. Guardar en archivo: pipeline_backup_YYYYMMDD.yml
6. Documentar versión actual
```

**Validación:**
- [ ] Archivo backup creado
- [ ] Contenido completo copiado
- [ ] Fecha documentada

### Paso 1.2: Documentar Configuración Actual
```
Crear documento con:
- Nombre del pipeline
- Versión actual
- Stages actuales
- Variables definidas
- Triggers configurados
- Aprobaciones requeridas
```

**Validación:**
- [ ] Documento creado
- [ ] Información completa
- [ ] Guardado en repositorio

### Paso 1.3: Notificar a Stakeholders
```
Enviar notificación:
- Equipo de desarrollo
- Equipo de operaciones
- Propietarios del pipeline
- Usuarios finales (si aplica)

Incluir:
- Pipeline a actualizar
- Cambios propuestos
- Ventana de actualización
- Plan de rollback
```

**Validación:**
- [ ] Notificación enviada
- [ ] Confirmación recibida
- [ ] Aprobaciones obtenidas

### Paso 1.4: Preparar Rollback Plan
```
Documentar:
1. Cómo revertir cambios
2. Tiempo estimado de rollback
3. Validaciones post-rollback
4. Contactos de escalación
```

**Validación:**
- [ ] Plan documentado
- [ ] Equipo informado
- [ ] Contactos confirmados

---

## 🔵 FASE 2: ANÁLISIS

### Paso 2.1: Revisar Cambios Propuestos
```
Documentar:
- Qué cambia
- Por qué cambia
- Impacto esperado
- Riesgos identificados
- Validaciones necesarias
```

**Validación:**
- [ ] Cambios documentados
- [ ] Impacto evaluado
- [ ] Riesgos identificados

### Paso 2.2: Identificar Dependencias
```
Revisar:
- Otros pipelines que dependen de este
- Variables compartidas
- Artefactos generados
- Integraciones externas
```

**Validación:**
- [ ] Dependencias mapeadas
- [ ] Impacto evaluado
- [ ] Comunicación realizada

### Paso 2.3: Validar Precondiciones
```
Verificar:
- [ ] Acceso de edición disponible
- [ ] Permisos suficientes
- [ ] Repositorio accesible
- [ ] Recursos disponibles
- [ ] No hay cambios en progreso
```

**Validación:**
- [ ] Todas las precondiciones met
- [ ] Sistema listo para cambios

---

## 🟢 FASE 3: CAMBIOS

### Paso 3.1: Acceder al Pipeline
```
1. Ir a Azure DevOps
2. Seleccionar proyecto
3. Ir a Pipelines
4. Seleccionar pipeline
5. Hacer clic en "Edit"
```

**Validación:**
- [ ] Pipeline abierto en editor
- [ ] YAML visible
- [ ] Cambios no guardados

### Paso 3.2: Realizar Cambios
```
Según el tipo de cambio:

CAMBIO DE VARIABLE:
1. Localizar sección "variables"
2. Actualizar valor
3. Guardar cambio

CAMBIO DE STAGE:
1. Localizar sección "stages"
2. Modificar stage
3. Validar sintaxis

CAMBIO DE TRIGGER:
1. Localizar sección "trigger"
2. Actualizar condiciones
3. Validar sintaxis

CAMBIO DE APROBACIÓN:
1. Localizar sección "approvals"
2. Actualizar aprobadores
3. Validar permisos
```

**Validación:**
- [ ] Cambios realizados
- [ ] Sintaxis correcta
- [ ] Indentación válida

### Paso 3.3: Guardar Cambios
```
1. Revisar cambios en editor
2. Hacer clic en "Save"
3. Agregar comentario descriptivo
4. Confirmar guardado
```

**Validación:**
- [ ] Cambios guardados
- [ ] Comentario agregado
- [ ] Versión actualizada

---

## 🟡 FASE 4: VALIDACIÓN

### Paso 4.1: Validar Sintaxis
```
1. Abrir pipeline en editor
2. Revisar errores mostrados
3. Corregir si es necesario
4. Validar indentación
5. Validar referencias
```

**Validación:**
- [ ] Sin errores de sintaxis
- [ ] YAML válido
- [ ] Referencias correctas

### Paso 4.2: Ejecutar Test
```
1. Hacer clic en "Run"
2. Seleccionar rama
3. Ejecutar pipeline
4. Monitorear ejecución
5. Revisar resultados
```

**Validación:**
- [ ] Pipeline ejecuta
- [ ] Stages completan
- [ ] Sin errores críticos

### Paso 4.3: Validar Resultados
```
Verificar:
- [ ] Todos los stages ejecutaron
- [ ] Artefactos generados correctamente
- [ ] Variables se aplicaron
- [ ] Aprobaciones funcionan
- [ ] Triggers se disparan
```

**Validación:**
- [ ] Resultados esperados
- [ ] Sin problemas identificados

### Paso 4.4: Documentar Cambios
```
Crear documento con:
- Cambios realizados
- Fecha y hora
- Persona que realizó cambios
- Validaciones ejecutadas
- Resultados obtenidos
- Próximos pasos
```

**Validación:**
- [ ] Documentación completa
- [ ] Guardada en repositorio

---

## 📊 Matriz de Validación

| Validación | Antes | Después | Estado |
|-----------|-------|---------|--------|
| Sintaxis YAML | ✅ | ✅ | |
| Variables | ✅ | ✅ | |
| Stages | ✅ | ✅ | |
| Triggers | ✅ | ✅ | |
| Aprobaciones | ✅ | ✅ | |
| Ejecución | ✅ | ✅ | |
| Artefactos | ✅ | ✅ | |

---

## 🔄 Rollback (si es necesario)

### Paso 1: Evaluar Severidad
```
¿Problema crítico?
├─ SÍ → Ejecutar rollback inmediato
└─ NO → Investigar y planificar fix
```

### Paso 2: Ejecutar Rollback
```
1. Abrir pipeline en editor
2. Restaurar contenido del backup
3. Guardar cambios
4. Ejecutar test
5. Validar funcionamiento
```

### Paso 3: Documentar Incidente
```
Crear documento con:
- Problema identificado
- Causa raíz
- Solución aplicada
- Lecciones aprendidas
- Prevención futura
```

---

## 📋 Checklist de Actualización

### Preparación
- [ ] Snapshot creado
- [ ] Configuración documentada
- [ ] Stakeholders notificados
- [ ] Rollback plan preparado
- [ ] Aprobaciones obtenidas

### Análisis
- [ ] Cambios documentados
- [ ] Dependencias identificadas
- [ ] Precondiciones validadas
- [ ] Riesgos evaluados

### Cambios
- [ ] Pipeline abierto en editor
- [ ] Cambios realizados
- [ ] Sintaxis validada
- [ ] Cambios guardados

### Validación
- [ ] Sintaxis correcta
- [ ] Test ejecutado
- [ ] Resultados validados
- [ ] Documentación completada

### Post-Actualización
- [ ] Monitoreo iniciado (24h)
- [ ] Equipo notificado
- [ ] Documentación actualizada
- [ ] Lecciones aprendidas registradas

---

## 🆘 Troubleshooting

### Error: "Invalid YAML"
```
Solución:
1. Revisar indentación
2. Validar comillas
3. Revisar caracteres especiales
4. Usar validador YAML online
5. Restaurar backup si es necesario
```

### Error: "Variable not found"
```
Solución:
1. Verificar nombre de variable
2. Revisar scope de variable
3. Validar sintaxis de referencia
4. Revisar variables definidas
```

### Error: "Stage failed"
```
Solución:
1. Revisar logs de ejecución
2. Validar comandos
3. Revisar permisos
4. Validar recursos disponibles
```

### Error: "Approval not working"
```
Solución:
1. Verificar aprobadores configurados
2. Validar permisos de aprobadores
3. Revisar condiciones de aprobación
4. Validar sintaxis de aprobación
```

---

## 📞 Escalación

### Problema Crítico
```
Acción:
1. Ejecutar rollback inmediato
2. Notificar a stakeholders
3. Iniciar post-mortem
4. Documentar incidente
```

### Problema Alto
```
Acción:
1. Investigar causa
2. Contactar equipo de soporte
3. Considerar rollback
4. Documentar hallazgos
```

---

## 📚 Ejemplos Prácticos

### Ejemplo 1: Cambiar Variable
```yaml
# ANTES
variables:
  buildConfiguration: 'Release'

# DESPUÉS
variables:
  buildConfiguration: 'Debug'
  enableTests: 'true'
```

### Ejemplo 2: Agregar Stage
```yaml
# AGREGAR DESPUÉS DE STAGE EXISTENTE
- stage: NewStage
  displayName: 'New Stage'
  dependsOn: PreviousStage
  jobs:
  - job: NewJob
    steps:
    - script: echo Hello
```

### Ejemplo 3: Cambiar Trigger
```yaml
# ANTES
trigger:
  branches:
    include:
    - main

# DESPUÉS
trigger:
  branches:
    include:
    - main
    - develop
  paths:
    include:
    - src/**
```

---

**Guía de Actualización Manual v1.0.0**  
**Última actualización:** 8 de Julio de 2026
