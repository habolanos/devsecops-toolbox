# Análisis: Manejo de Errores de Variable Groups

**Fecha:** 2026-07-25  
**Problema:** Errores HTTP 400 al actualizar pipelines con referencias a variable groups inexistentes

---

## 🔴 Problema Identificado

### Error
```
Variable groups with ID(s) 186 linked to the release pipeline or to one of the stages within it do not exist.
```

### Causa
Los pipelines tienen referencias a variable groups (IDs 186, 196) que fueron:
- Eliminados de Azure DevOps
- Movidos a otro proyecto
- Renombrados o recreados con diferente ID

### Impacto
- 52 de 53 pipelines fallaron con este error
- Los pipelines no pueden actualizarse
- El cambio de nombre de stages no se aplica

---

## 📊 Análisis Técnico

### Estructura de Variable Groups en Azure DevOps

Los variable groups se referencian en dos niveles:

1. **Nivel Pipeline** (global):
```json
{
  "variables": {
    "MyVar": {
      "value": "$(my-var-group.my-var)",
      "isSecret": false
    }
  }
}
```

2. **Nivel Stage** (por environment):
```json
{
  "environments": [
    {
      "name": "Production",
      "variableGroups": [186, 196]  // ← Referencia directa
    }
  ]
}
```

### API para Validar Variable Groups

```python
# Endpoint para obtener un variable group
GET https://dev.azure.com/{org}/{project}/_apis/distributedtask/variablegroups/{groupId}?api-version=7.0

# Endpoint para listar variable groups del proyecto
GET https://dev.azure.com/{org}/{project}/_apis/distributedtask/variablegroups?api-version=7.0
```

---

## 💡 Opciones de Solución

### Opción 1: Validación y Skip (RECOMENDADA - Segura)

**Descripción:**
- Validar existencia de variable groups antes de actualizar
- Omitir pipelines con grupos faltantes
- Reportar claramente cuáles pipelines fueron omitidos y por qué

**Implementación:**
```python
def validate_variable_groups(definition: Dict, azdo_client) -> List[str]:
    """
    Valida que todos los variable groups referenciados existan.
    
    Returns:
        Lista de IDs de variable groups faltantes
    """
    missing_groups = []
    
    # Validar grupos a nivel de stages
    for env in definition.get('environments', []):
        for group_id in env.get('variableGroups', []):
            if not azdo_client.variable_group_exists(group_id):
                missing_groups.append(group_id)
    
    return missing_groups
```

**Template Option:**
```yaml
options:
  skip_on_missing_variable_groups: true  # Default: true
  fail_on_missing_variable_groups: false  # Default: false
```

**Pros:**
- ✅ Seguro: No rompe pipelines
- ✅ Transparente: Usuario sabe qué se omitió
- ✅ Reversible: No modifica datos

**Contras:**
- ❌ No actualiza pipelines con problemas
- ❌ Requiere corrección manual en Azure DevOps

---

### Opción 2: Remover Referencias Automáticamente (AGRESIVA)

**Descripción:**
- Remover referencias a variable groups inexistentes
- Actualizar el pipeline sin esos grupos
- Registrar qué se removió

**Implementación:**
```python
def remove_missing_variable_groups(definition: Dict, azdo_client) -> List[int]:
    """
    Remueve referencias a variable groups inexistentes.
    
    Returns:
        Lista de IDs removidos
    """
    removed_ids = []
    
    for env in definition.get('environments', []):
        valid_groups = []
        for group_id in env.get('variableGroups', []):
            if azdo_client.variable_group_exists(group_id):
                valid_groups.append(group_id)
            else:
                removed_ids.append(group_id)
        
        env['variableGroups'] = valid_groups
    
    return removed_ids
```

**Template Option:**
```yaml
options:
  remove_missing_variable_groups: false  # Default: false (requiere opt-in explícito)
```

**Pros:**
- ✅ Permite actualizar pipelines
- ✅ Automático
- ✅ Auditoría de cambios

**Contras:**
- ❌ Puede romper funcionalidad del pipeline
- ❌ Variables referenciadas pueden fallar en runtime
- ❌ Requiere conocimiento profundo del pipeline

---

### Opción 3: Lista de Excepciones (CONTROLADA)

**Descripción:**
- Usuario especifica qué variable groups ignorar
- Solo remueve referencias a grupos explícitamente listados

**Template Option:**
```yaml
options:
  ignore_variable_groups: [186, 196]  # IDs a ignorar
```

**Implementación:**
```python
def remove_ignored_variable_groups(definition: Dict, ignore_list: List[int]) -> List[int]:
    """
    Remueve referencias a variable groups en la lista de ignorados.
    """
    removed_ids = []
    
    for env in definition.get('environments', []):
        valid_groups = []
        for group_id in env.get('variableGroups', []):
            if group_id not in ignore_list:
                valid_groups.append(group_id)
            else:
                removed_ids.append(group_id)
        
        env['variableGroups'] = valid_groups
    
    return removed_ids
```

**Pros:**
- ✅ Control explícito del usuario
- ✅ Solo remueve lo especificado
- ✅ Auditoría clara

**Contras:**
- ❌ Requiere conocimiento previo de los IDs
- ❌ No detecta nuevos grupos faltantes automáticamente

---

### Opción 4: Modo Repair (HÍBRIDA)

**Descripción:**
- Combinar validación + reparación opcional
- Reportar grupos faltantes
- Permitir reparación manual o automática

**Template Option:**
```yaml
options:
  repair_variable_groups: "validate"  # Options: "validate", "auto", "skip"
```

**Comportamiento:**
- `validate`: Solo reporta, no modifica (default)
- `auto`: Remueve grupos faltantes automáticamente
- `skip`: No valida, intenta actualizar igual

**Pros:**
- ✅ Flexible: 3 modos
- ✅ Default seguro (validate)
- ✅ Permite reparación cuando se desea

**Contras:**
- ❌ Más complejidad
- ❌ Requiere decisión del usuario

---

## 🎯 Recomendación

### Implementación en Fases

#### Fase 1: Validación y Reporte (Inmediato - 2 horas)
1. Agregar método `variable_group_exists()` a `AzureDevOpsClient`
2. Agregar validación en `parallel_executor._process_pipeline()`
3. Si hay grupos faltantes:
   - No intentar actualizar
   - Marcar como fallido con mensaje claro
   - Agregar a reporte con categoría "missing_variable_groups"

#### Fase 2: Opción de Ignorar (Siguiente - 1 hora)
1. Agregar opción `ignore_variable_groups` al template
2. Implementar remoción de grupos en lista
3. Registrar cambios en `UpdateResult.changes`

#### Fase 3: Modo Repair (Futuro - 2 horas)
1. Agregar opción `repair_variable_groups` con 3 modos
2. Implementar lógica condicional
3. Actualizar documentación

---

## 📋 Ejemplo de Implementación Fase 1

### azdo_client.py
```python
def variable_group_exists(self, group_id: int) -> bool:
    """
    Verifica si un variable group existe.
    
    Args:
        group_id: ID del variable group
        
    Returns:
        True si existe, False si no
    """
    url = f"{self.base_url.replace('vsrm.dev.azure.com', 'dev.azure.com')}/_apis/distributedtask/variablegroups/{group_id}"
    params = {'api-version': self.api_version}
    
    try:
        response = requests.get(url, params=params, headers=self.headers, timeout=10)
        return response.status_code == 200
    except:
        return False
```

### parallel_executor.py
```python
def _process_pipeline(self, definition_id: int, template_parser, azdo_client) -> UpdateResult:
    try:
        # ... código existente ...
        
        # VALIDACIÓN: Variable Groups
        missing_groups = self._validate_variable_groups(definition, azdo_client)
        if missing_groups:
            raise ValueError(
                f"Variable groups faltantes: {missing_groups}. "
                f"Use 'ignore_variable_groups' en el template para omitir estos grupos."
            )
        
        # ... resto del procesamiento ...
```

---

## 🔍 Análisis de Caso Actual

### Pipelines Afectados
- 52 pipelines con variable groups 186 y/o 196 faltantes
- 1 pipeline exitoso (159) - probablemente no usa esos grupos

### Solución Inmediata para Usuario
1. **Identificar variable groups faltantes:**
   ```bash
   # Listar variable groups del proyecto
   GET https://dev.azure.com/Coppel-Retail/Cadena_de_Suministros/_apis/distributedtask/variablegroups
   ```

2. **Opción A: Recrear grupos faltantes**
   - Crear variable groups 186 y 196 en Azure DevOps
   - Restaurar variables desde backup si existe

3. **Opción B: Usar ignore_variable_groups**
   - Agregar al template:
     ```yaml
     options:
       ignore_variable_groups: [186, 196]
     ```
   - Re-ejecutar actualización

4. **Opción C: Corregir manualmente pipelines**
   - Ir a cada pipeline en Azure DevOps
   - Remover referencias a grupos 186 y 196
   - Re-ejecutar actualización

---

## 📊 Métricas de Impacto

| Métrica | Valor |
|---------|-------|
| Pipelines totales | 53 |
| Pipelines con error VG | 52 (98.1%) |
| Pipelines exitosos | 1 (1.9%) |
| Variable groups faltantes | 186, 196 |
| Tiempo estimado corrección manual | 4-6 horas |
| Tiempo estimado solución código | 3-5 horas |

---

## ✅ Próximos Pasos

1. **Implementar Fase 1** (Validación y Reporte)
   - Agregar `variable_group_exists()` a `azdo_client.py`
   - Agregar validación en `parallel_executor.py`
   - Commit: `feat: Validar variable groups antes de actualizar pipelines`

2. **Documentar solución**
   - Agregar sección a README.md
   - Crear ejemplo de template con `ignore_variable_groups`

3. **Probar con pipelines afectados**
   - Ejecutar con validación
   - Verificar reporte de grupos faltantes
   - Probar con `ignore_variable_groups`

---

**Estado:** Análisis completado, listo para implementación Fase 1
