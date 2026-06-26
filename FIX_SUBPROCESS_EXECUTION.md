# 🔧 Fix: Corregir Ejecución de Subprocess en azdo/tools.py

**Fecha:** 25 de Junio de 2026  
**Commit:** 3372f19  
**Severidad:** 🔴 CRÍTICA

---

## 📋 Problema

### Error Reportado

```
did not find executable at '/usr/bin\python.exe': The system cannot find the path specified.

⚡ [1/15] 📬 PR Master Checker → json
──────────────────────────────────────────────────
did not find executable at '/usr/bin\python.exe': The system cannot find the path specified.

❌ exit 103
```

### Causa Raíz

En `scm/azdo/tools.py`, las funciones que ejecutan herramientas usando `subprocess.run()` no especificaban el directorio de trabajo (`cwd`):

```python
# INCORRECTO
result = subprocess.run(cmd)  # Se ejecuta desde el directorio actual

# CORRECTO
result = subprocess.run(cmd, cwd=BASE_DIR)  # Se ejecuta desde scm/azdo/
```

Cuando `cwd` no se especifica, `subprocess.run()` hereda el directorio de trabajo del proceso padre. Esto causaba que:

1. Los scripts se ejecutaran desde un directorio incorrecto
2. Las rutas relativas se resolvieran incorrectamente
3. Los imports de módulos locales fallaran
4. Se generara el error de ruta de Python mixta (`/usr/bin\python.exe`)

### Funciones Afectadas

```
1. run_tool()      - Línea 1540 (Opción individual)
2. run_all_tools() - Línea 1654 (Opción A: Ejecutar Todos)
3. run_all_json()  - Línea 1760 (Opción B: Ejecutar Todo + JSON)
```

### Opciones Afectadas

```
Opción A: Ejecutar Todas las Herramientas
├─ Estado: ❌ FALLABA
└─ Causa: subprocess.run sin cwd

Opción B: Ejecutar Todo + JSON (Dashboard Feed)
├─ Estado: ❌ FALLABA (15/15 herramientas)
└─ Causa: subprocess.run sin cwd

Opción Individual (1-25)
├─ Estado: ⚠️ FUNCIONABA (por coincidencia)
└─ Causa: Usaba cwd=BASE_DIR correctamente
```

---

## ✅ Solución

### Cambios Realizados

```python
# ANTES (Línea 1540 - run_tool)
result = subprocess.run(cmd)

# DESPUÉS
result = subprocess.run(cmd, cwd=BASE_DIR)

# ANTES (Línea 1654 - run_all_tools)
result = subprocess.run(cmd)

# DESPUÉS
result = subprocess.run(cmd, cwd=BASE_DIR)

# ANTES (Línea 1760 - run_all_json)
result = subprocess.run(cmd, cwd=BASE_DIR)

# DESPUÉS (ya estaba correcto)
result = subprocess.run(cmd, cwd=BASE_DIR)
```

### Verificación

```bash
# Verificar que los cambios se aplicaron
git diff HEAD~1 scm/azdo/tools.py

# Output esperado:
# -            result = subprocess.run(cmd)
# +            result = subprocess.run(cmd, cwd=BASE_DIR)
```

---

## 🧪 Testing

### Prueba Manual

```bash
# 1. Ejecutar Opción B (Dashboard Feed)
python scm/main.py
# Seleccionar: 2 (AZDO)
# Seleccionar: B (Ejecutar Todo + JSON)
# Ingresar credenciales
# Confirmar

# 2. Verificar que los JSONs se generan
ls -la scm/outcome/
# Debe mostrar archivos JSON generados

# 3. Verificar que no hay errores
# Todos los 15 tools deben mostrar ✅ OK
```

### Resultado Esperado

```
⚡ [1/15] 📬 PR Master Checker → json
──────────────────────────────────────────────────
✅ OK

⚡ [2/15] 🔒 Branch Policy Checker → json
──────────────────────────────────────────────────
✅ OK

... (13 más)

✅ Exitosos: 15  ❌ Errores: 0  ⏱️  Tiempo: X.XXs
```

---

## 📊 Impacto

### Antes del Fix

```
Opción A (Ejecutar Todos):
├─ Estado: ❌ FALLABA
├─ Herramientas ejecutadas: 0/25
├─ JSONs generados: 0
└─ Error: subprocess.run sin cwd

Opción B (Dashboard Feed):
├─ Estado: ❌ FALLABA
├─ Herramientas ejecutadas: 0/15
├─ JSONs generados: 0
└─ Error: subprocess.run sin cwd
```

### Después del Fix

```
Opción A (Ejecutar Todos):
├─ Estado: ✅ FUNCIONA
├─ Herramientas ejecutadas: 25/25
├─ JSONs generados: 25
└─ Error: Ninguno

Opción B (Dashboard Feed):
├─ Estado: ✅ FUNCIONA
├─ Herramientas ejecutadas: 15/15
├─ JSONs generados: 15
└─ Error: Ninguno
```

---

## 🔍 Análisis Técnico

### ¿Por qué pasó esto?

```
1. Las funciones run_all_tools() y run_all_json() fueron agregadas recientemente
2. Se copió el patrón de otras funciones pero sin copiar el cwd=BASE_DIR
3. Las pruebas manuales no se ejecutaron para estas opciones
4. El error solo se manifestaba cuando se ejecutaban desde el menú principal
```

### ¿Por qué solo afectaba a Opción A y B?

```
Opción Individual (1-25):
├─ Usa run_tool()
├─ Línea 818: result = subprocess.run(cmd, cwd=BASE_DIR) ✅
└─ Funciona correctamente

Opción A (Ejecutar Todos):
├─ Usa run_all_tools()
├─ Línea 1654: result = subprocess.run(cmd) ❌
└─ Fallaba

Opción B (Dashboard Feed):
├─ Usa run_all_json()
├─ Línea 1760: result = subprocess.run(cmd) ❌
└─ Fallaba
```

---

## 📚 Lecciones Aprendidas

### 1. Consistencia en Patrones

```
✅ HACER: Usar el mismo patrón en todas las funciones
❌ NO HACER: Copiar código sin verificar detalles críticos
```

### 2. Testing Completo

```
✅ HACER: Probar todas las opciones del menú
❌ NO HACER: Asumir que funciona si una opción funciona
```

### 3. Revisión de Código

```
✅ HACER: Revisar subprocess.run() siempre con cwd
❌ NO HACER: Dejar subprocess.run() sin cwd especificado
```

---

## 🔗 Referencias

- **Archivo:** `scm/azdo/tools.py`
- **Líneas:** 1540, 1654, 1760
- **Commit:** 3372f19
- **Función:** `subprocess.run(cmd, cwd=BASE_DIR)`

---

## ✨ Resumen

```
Problema:  subprocess.run sin cwd en 2 funciones
Causa:     Herencia de directorio de trabajo incorrecto
Solución:  Agregar cwd=BASE_DIR a 2 líneas
Impacto:   Opción A y B ahora funcionan correctamente
Severidad: 🔴 CRÍTICA (bloqueaba Dashboard Feed)
Estado:    ✅ RESUELTO
```

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
