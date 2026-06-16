# Release v1.9.4 - GCP Secret Manager Integration 🔐

**Fecha:** 16 de Junio, 2026  
**Autor:** Harold Adrian

---

## 🎯 Resumen

Esta versión introduce **soporte completo para GCP Secret Manager** en las herramientas de conectividad de Kubernetes, permitiendo validar conexiones a bases de datos cuyos credenciales están almacenados de forma segura en Secret Manager. Además, se mejora significativamente la experiencia visual con Rich en todas las ejecuciones.

---

## ✨ Nuevas Funcionalidades

### 🔐 Integración con GCP Secret Manager

**Herramientas actualizadas:**
- **Deploy Dependency Checker (Opción 17)** - v1.0.5
- **Deployment Validator (Opción 19)** - v1.0.4

#### Características principales:

1. **Detección automática de referencias a Secret Manager**
   - Parsea ConfigMaps con referencias YAML a Secret Manager
   - Formato soportado: `secretManager.projectId`, `secrets.*.name`, `secrets.*.version`
   - Soporte PyYAML con fallback regex para máxima compatibilidad

2. **Obtención segura de secretos**
   - Función `fetch_gcp_secret()` usando `gcloud secrets versions access`
   - Extrae conexiones DB desde JSON: `host`, `port`, `type`
   - Validación de conectividad TCP y DB Probe para secretos

3. **Columna "Source" en resultados**
   - 🔐 **SM** (Secret Manager) - Credenciales desde GCP Secret Manager
   - 🔑 **K8s** (Kubernetes Secret) - Secretos nativos de Kubernetes
   - 📋 **CM** (ConfigMap) - Configuración directa en ConfigMap

4. **Exportación mejorada**
   - CSV y JSON incluyen campos de Secret Manager:
     - `secret_project`: Proyecto GCP del secreto
     - `secret_name`: Nombre del secreto
     - `secret_version`: Versión del secreto
     - `sm_key`: Clave de conexión dentro del secreto

---

## 🎨 Mejoras de Interfaz

### Rich Console en Subprocesos

**Problema resuelto:** Las herramientas ejecutadas desde el menú mostraban salida en texto plano sin formato.

**Solución implementada:**
- `force_terminal=True` en Console para forzar modo terminal en subprocesos
- Configuración automática de requirements.txt para herramientas 17 y 19
- Detección y debug mejorado de disponibilidad de Rich

**Resultado:**
- ✅ Tablas formateadas con bordes
- ✅ Colores en toda la salida
- ✅ Iconos y emojis (🔐, 📋, 🔑, ✅, ❌)
- ✅ Progress spinners animados

---

## 🔧 Correcciones y Mejoras Técnicas

### Type Hints y Compatibilidad

- **`from __future__ import annotations`**: Evaluación postponed de type hints
- Soluciona `NameError` con importaciones opcionales de Rich
- Compatible con Python 3.9+

### Directorio de Salida Centralizado

- Uso de `get_output_dir()` para exportaciones
- Respeta variable de entorno `DEVSECOPS_OUTPUT_DIR`
- Archivos exportados van a `scm/outcome/` (centralizado)

### Debug y Diagnóstico

- Mensajes stderr para verificar importación de Rich
- Debug flags para troubleshooting de Console
- Logging mejorado de estado de terminal y color system

---

## 📋 Cambios por Herramienta

### Deploy Dependency Checker v1.0.5

**Archivo:** `scm/gcp/connectivity/deploy_dependency_checker.py`

**Commits principales:**
- `7f6ea91` - feat: Add GCP Secret Manager support
- `2ca01e3` - fix: Add Console type hint fallback
- `cd7aa72` - fix: Use __future__ annotations
- `f9179e1` - fix: Force Rich terminal mode for subprocess
- `2d31ecd` - fix: Use centralized output directory

**Funcionalidades:**
- ✅ Parse Secret Manager references en ConfigMaps
- ✅ Fetch secrets vía gcloud CLI
- ✅ Extract DB connections desde JSON
- ✅ TCP + DB Probe para conexiones de Secret Manager
- ✅ Columna Source en tabla de resultados
- ✅ Export CSV/JSON con metadata de Secret Manager

### Deployment Validator v1.0.4

**Archivo:** `scm/gcp/connectivity/deployment_validator.py`

**Commits principales:**
- `6de7618` - feat: Add GCP Secret Manager support
- Mismas mejoras de type hints y Rich que deploy_dependency_checker

**Funcionalidades:**
- ✅ Todas las funcionalidades de Secret Manager
- ✅ Dataclass `ConnectionEndpoint` extendido con campos SM
- ✅ Función `validate_configmaps` procesa referencias SM
- ✅ Tabla de conectividad con columna Source

### GCP Tools Launcher v1.9.4

**Archivo:** `scm/gcp/tools.py`

**Commits principales:**
- `7e12d76` - fix: Add Rich requirements to connectivity tools
- `7bdd239` - chore: Bump version to 1.9.4

**Cambios:**
- ✅ Herramientas 17 y 19 ahora instalan `requirements.txt`
- ✅ Rich se instala automáticamente en venv al ejecutar desde menú
- ✅ Versión actualizada a 1.9.4

---

## 📊 Ejemplo de Salida

### Antes (v1.9.3)
```
ConfigMap       Key     Conexión        Tipo    Host    Port    TCP_Status
app-config      db.url  TCP     postgresql      10.1.2.3        5432    OK
```

### Ahora (v1.9.4)
```
╭─────────────────┬──────────────┬──────────┬──────────────┬────────────┬──────────┬────────╮
│ Origen          │ Recurso      │  Source  │ Conexión     │ Tipo DB    │ Host     │ Puerto │
├─────────────────┼──────────────┼──────────┼──────────────┼────────────┼──────────┼────────┤
│ ConfigMap       │ app-config   │  🔐 SM   │ TCP          │ postgresql │ 10.1.2.3 │  5432  │
│ ConfigMap       │ app-config   │  📋 CM   │ TCP          │ redis      │ 10.1.2.4 │  6379  │
│ Secret          │ db-creds     │  🔑 K8s  │ TCP          │ mysql      │ 10.1.2.5 │  3306  │
╰─────────────────┴──────────────┴──────────┴──────────────┴────────────┴──────────┴────────╯
```

---

## 🧪 Tests

**Archivo de pruebas:** `scm/gcp/connectivity/test_secret_manager.py`

**Cobertura:**
- ✅ `test_parse_secret_manager_references_yaml()` - Parsing YAML
- ✅ `test_parse_secret_manager_references_regex()` - Fallback regex
- ✅ `test_parse_secret_manager_no_references()` - Sin referencias
- ✅ `test_create_connection_dict_from_secret()` - Creación de dict de conexión

---

## 📝 Documentación Actualizada

**README.md - Historial de Cambios:**

| Versión | Descripción |
|---------|-------------|
| 1.0.4 | `deployment_validator.py`: Soporte para GCP Secret Manager |
| 1.0.5 | `deploy_dependency_checker.py`: Soporte para GCP Secret Manager |

---

## 🚀 Instalación y Uso

### Requisitos
- Python 3.9+
- `gcloud` CLI configurado
- Permisos para acceder a Secret Manager

### Instalación
```bash
# Clonar repositorio
git clone <repo-url>
cd devsecops-toolbox

# Ejecutar menú (instala dependencias automáticamente)
python scm/gcp/tools.py
```

### Uso desde Menú
1. Seleccionar opción **17** (Deploy Dependency Checker) o **19** (Deployment Validator)
2. Ingresar proyecto, cluster, deployment
3. La herramienta detectará automáticamente referencias a Secret Manager
4. Resultados mostrarán origen de cada conexión (SM/K8s/CM)

### Uso Directo
```bash
# Deploy Dependency Checker
python scm/gcp/connectivity/deploy_dependency_checker.py \
  --project cpl-oms-qa-08062023 \
  --cluster gke-oms-producto-qa \
  --deployment ps-com-itemstransition \
  --db-probe -o json

# Deployment Validator
python scm/gcp/connectivity/deployment_validator.py \
  --project cpl-oms-qa-08062023 \
  --cluster gke-oms-producto-qa \
  --deployment ps-com-itemstransition \
  --validate all --db-probe -o json
```

---

## 🔄 Migración desde v1.9.3

**Sin cambios breaking:** Esta versión es 100% compatible con v1.9.3.

**Mejoras automáticas:**
- Rich se instalará automáticamente al ejecutar opciones 17 o 19 desde el menú
- Exportaciones irán a `scm/outcome/` si `DEVSECOPS_OUTPUT_DIR` está configurado
- Secret Manager se detectará automáticamente sin configuración adicional

---

## 🐛 Issues Conocidos

Ninguno reportado en esta versión.

---

## 🙏 Agradecimientos

Gracias a todos los que probaron y reportaron feedback durante el desarrollo de esta versión.

---

## 📦 Distribución

**Archivo ZIP:** `devsecops-toolbox_dist_20260616_132218.zip`
- **Tamaño:** 1.294 MB
- **Archivos:** 201
- **Incluye:** Todas las herramientas actualizadas con dependencias

---

## 🔗 Links Útiles

- [Repositorio GitHub](https://github.com/your-org/devsecops-toolbox)
- [Documentación Completa](./scm/gcp/connectivity/README.md)
- [Issues](https://github.com/your-org/devsecops-toolbox/issues)

---

**¡Disfruta de la nueva versión!** 🎉
