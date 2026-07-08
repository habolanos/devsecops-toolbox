# 🚀 Opciones de Ejecución - Service Accounts Reporter

**Fecha:** 8 de Julio de 2026  
**Versión:** 1.0.0  
**Estado:** ✅ LISTO PARA USAR

---

## 📋 Tabla de Contenidos

1. [Opción 1: Ejecución Directa (Recomendada)](#opción-1-ejecución-directa-recomendada)
2. [Opción 2: Con Argumentos CLI](#opción-2-con-argumentos-cli)
3. [Opción 3: Desde Python](#opción-3-desde-python)
4. [Opción 4: Integración en Menú (Próxima)](#opción-4-integración-en-menú-próxima)
5. [Comparativa de Opciones](#comparativa-de-opciones)

---

## ✅ Opción 1: Ejecución Directa (Recomendada)

### Comando

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py
```

### Requisitos Previos

1. **Copiar template de configuración:**
   ```bash
   cp scm/config.json.template scm/config.json
   ```

2. **Editar `scm/config.json`:**
   ```json
   {
     "gcp": {
       "service_accounts_reporter": {
         "enabled": true,
         "projects": [
           "proyecto-prod",
           "proyecto-staging"
         ]
       }
     }
   }
   ```

3. **Autenticarse en GCP:**
   ```bash
   gcloud auth application-default login
   ```

### Ejecución

```bash
cd devsecops-toolbox
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py
```

### Salida

```
🚀 Iniciando análisis de 2 proyecto(s)...
   Proyectos: proyecto-prod, proyecto-staging
   Modo: all
   Salida: json

📊 Generando reporte json...
✅ Reporte generado: outcome/sa_report_20260708_114900.json

📈 Resumen:
   - Proyectos: 2
   - Service Accounts: 45
   - Roles: 120
```

---

## 🎯 Opción 2: Con Argumentos CLI

### Comando Base

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py [opciones]
```

### Opciones Disponibles

```
--projects PROYECTOS      Proyectos a analizar (separados por coma)
--mode MODO              Modo: all, security, compliance, usage
--output FORMATO         Formato: json, csv, excel, html
--config RUTA            Ruta a config.json
--output-dir DIRECTORIO  Directorio de salida
--debug                  Modo debug
--help                   Mostrar ayuda
```

### Ejemplos

#### A. Proyectos Específicos

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --projects=proyecto-prod,proyecto-staging
```

#### B. Modo Seguridad

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=security
```

#### C. Salida Excel

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --output=excel
```

#### D. Modo Cumplimiento + CSV

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=compliance \
  --output=csv
```

#### E. Debug Mode

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --debug
```

#### F. Combinado (Recomendado)

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --projects=proyecto-prod,proyecto-staging,proyecto-dev \
  --mode=all \
  --output=excel \
  --output-dir=outcome/reports
```

---

## 🐍 Opción 3: Desde Python

### Importar Módulos

```python
from scm.gcp.service_accounts import (
    ConfigLoader,
    ServiceAccountExtractor,
    RolesAndPermissionsAnalyzer,
    SecurityAnalyzer,
    JSONReportGenerator,
    ExcelReportGenerator
)
```

### Ejemplo 1: Uso Básico

```python
from scm.gcp.service_accounts import ConfigLoader, ServiceAccountExtractor

# Cargar configuración
config_loader = ConfigLoader('scm/config.json')
projects = config_loader.get_projects()

# Extraer datos del primer proyecto
extractor = ServiceAccountExtractor(projects[0])
data = extractor.extract_all()

print(f"Service Accounts: {len(data['service_accounts'])}")
```

### Ejemplo 2: Análisis Completo

```python
from scm.gcp.service_accounts import (
    ConfigLoader,
    ServiceAccountExtractor,
    RolesAndPermissionsAnalyzer,
    SecurityAnalyzer,
    JSONReportGenerator
)

# Configuración
config_loader = ConfigLoader('scm/config.json')
projects = config_loader.get_projects()

# Procesar cada proyecto
all_data = {}
for project in projects:
    extractor = ServiceAccountExtractor(project)
    data = extractor.extract_all()
    
    # Analizar roles
    roles_analyzer = RolesAndPermissionsAnalyzer()
    for sa in data['service_accounts']:
        sa['roles_analysis'] = roles_analyzer.analyze_roles(
            sa['email'],
            data['iam_bindings']
        )
    
    # Analizar seguridad
    security_analyzer = SecurityAnalyzer()
    for sa in data['service_accounts']:
        sa['security'] = security_analyzer.analyze(sa)
    
    all_data[project] = data

# Generar reporte
generator = JSONReportGenerator()
report_path = generator.generate({'by_project': all_data})
print(f"Reporte: {report_path}")
```

### Ejemplo 3: Análisis Específico

```python
from scm.gcp.service_accounts import ServiceAccountExtractor

# Extraer datos
extractor = ServiceAccountExtractor('proyecto-prod')
data = extractor.extract_all()

# Acceder a service accounts
for sa in data['service_accounts']:
    print(f"Email: {sa['email']}")
    print(f"Claves: {len(sa['keys'])}")
    for key in sa['keys']:
        print(f"  - Edad: {key['age_days']} días")
        print(f"  - Tipo: {key['key_type']}")
```

---

## 📌 Opción 4: Integración en Menú (Próxima)

### Próximamente

La herramienta será integrada como **Tool 38** en el menú principal:

```bash
python scm/gcp/tools.py
```

**Seleccionar:** `[38] Service Accounts Reporter`

### Estado

- ✅ Código implementado
- ✅ Documentación completa
- ⏳ Integración en `tools.py` (próxima versión)
- ⏳ Tests unitarios (próxima versión)

---

## 📊 Comparativa de Opciones

| Opción | Comando | Requisitos | Ventajas | Desventajas |
|--------|---------|-----------|----------|------------|
| **1. Directa** | `python gcp_sa_multi_project_reporter.py` | config.json | Simple, usa defaults | Menos flexible |
| **2. CLI** | `python ... --projects=p1,p2` | Ninguno | Flexible, rápido | Más parámetros |
| **3. Python** | `from scm.gcp.service_accounts import ...` | Código | Máximo control | Más complejo |
| **4. Menú** | `python tools.py` → `[38]` | Integración | Interfaz unificada | No disponible aún |

---

## 🎯 Recomendaciones por Caso de Uso

### Caso 1: Auditoría Rápida

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=security \
  --output=excel
```

**Ventaja:** Rápido, reporte ejecutivo en Excel

---

### Caso 2: Análisis Detallado

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=all \
  --output=json \
  --debug
```

**Ventaja:** Información completa, logs detallados

---

### Caso 3: Cumplimiento Normativo

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=compliance \
  --output=csv
```

**Ventaja:** Formato para análisis, validación de políticas

---

### Caso 4: Automatización

```python
from scm.gcp.service_accounts import ConfigLoader, MultiProjectOrchestrator

config_loader = ConfigLoader('config.json')
projects = config_loader.get_projects()
defaults = config_loader.get_defaults()

orchestrator = MultiProjectOrchestrator(projects, defaults)
data = orchestrator.extract_all()
consolidated = orchestrator.consolidate(data)
```

**Ventaja:** Integración en pipelines, máximo control

---

## ✅ Checklist de Configuración

- [ ] Copiar `config.json.template` a `config.json`
- [ ] Editar `config.json` con proyectos reales
- [ ] Ejecutar `gcloud auth application-default login`
- [ ] Verificar permisos IAM
- [ ] Ejecutar comando de prueba
- [ ] Revisar reporte generado
- [ ] Configurar notificaciones (opcional)

---

## 🔍 Verificación Rápida

### 1. Verificar Instalación

```bash
python -c "from scm.gcp.service_accounts import ConfigLoader; print('✅ Instalación OK')"
```

### 2. Verificar Configuración

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py --help
```

### 3. Verificar Autenticación

```bash
gcloud auth list
gcloud projects list
```

### 4. Ejecutar Prueba

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --projects=<TU_PROYECTO> \
  --debug
```

---

## 📁 Archivos Generados

### Ubicación

```
outcome/
├── sa_report_20260708_114900.json
├── sa_report_20260708_114900.csv
├── sa_report_20260708_114900.xlsx
└── sa_report_20260708_114900.html
```

### Nombres

```
sa_report_YYYYMMDD_HHMMSS.<extension>
```

---

## 🆘 Troubleshooting Rápido

### Error: "config.json no encontrado"

```bash
cp scm/config.json.template scm/config.json
```

### Error: "No hay proyectos para analizar"

```bash
python ... --projects=proyecto1,proyecto2
```

### Error: "Permiso denegado"

```bash
gcloud auth application-default login
gcloud projects get-iam-policy <PROYECTO>
```

### Error: "Timeout"

```bash
python ... --debug  # Ver logs detallados
```

---

## 📞 Soporte

**Documentación:**
- Guía de acceso: `docs/feature_loadbalancer/GUIA_ACCESO_SA_REPORTER.md`
- Análisis técnico: `docs/analysis/ANALISIS_REPORTE_SERVICE_ACCOUNTS_MULTI_PROYECTO.md`

**Código:**
- Módulos: `scm/gcp/service-accounts/`
- Script principal: `scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py`

---

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Estado:** ✅ LISTO PARA USAR

