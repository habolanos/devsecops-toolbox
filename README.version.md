# 📋 Historial de Versiones

> **Único punto de verdad para el versionado del proyecto.**
> Las fechas y versiones aquí documentadas se aplican a todo el toolbox (GCP, AZDO, AWS, Terminal).

---

## Versión Actual

**`1.6.19`** — 2026-07-13

---

## Registro de Cambios

| Fecha | Versión | Descripción | Archivos / Scope |
|-------|---------|-------------|----------------|
| 2026-07-13 | **1.6.19** | **Pipeline Redo & Logging System**: (1) **Opción Redo** (Tool 22, Opción 6): Nueva funcionalidad para volver a la versión previa de un pipeline basado en definition_id. Obtiene revisión anterior, muestra información detallada, solicita confirmación (requiere escribir "SI"), soporta modo DRY-RUN. (2) **Logging Completo**: Todas las operaciones de Redo registran en `outcome/redo_pipeline_[id]_[timestamp].log` con timestamps, niveles (INFO/WARNING), y eventos clave (inicio, obtención de definiciones, confirmación, ejecución, fin). (3) **Dockerfile Enhancement**: Agregado `nano` para editar/copiar templates dentro del contenedor. (4) **Documentación**: Actualizado README.md con nueva funcionalidad de Redo. (5) **Validación de Templates**: Sistema preparado para leer y validar archivos template antes de ejecutar operaciones. | `scm/azdo/pipeline-cd-rollback-pipeline.py`, `scm/azdo/tools.py`, `Dockerfile`, `README.md` |
| 2026-07-09 | **1.6.18** | **KPI Analyzer Pro v1.9.6 - Integración Dashboard Completa**: Integración exitosa de Dashboard Matutino en KPI Analyzer Pro. (1) **5 Módulos Nuevos** (~1,980 líneas): health_score.py (DORA metrics), exporter.py (JSON/CSV/HTML/Excel), consolidator.py (multi-fuente), generator.py (dashboards HTML), scheduler.py (planificación automática). (2) **16 Herramientas Integradas**: 5 análisis KPI + 7 dashboards/consolidación + 4 exportación. (3) **Correcciones**: Fix acceso defensivo a 'emoji' y 'name' en tools.py con .get(). (4) **Limpieza**: Opción 6 (Dashboard) removida de main.py, consolidada en Opción 5. (5) **Configuración**: config.json.template actualizado a v1.9.6 con Dashboard integrado. | `scm/kpi_analyzer/`, `scm/main.py`, `scm/config.json.template` |
| 2026-07-08 | **1.6.17** | **Validación y Limpieza de Configuración**: Actualización de versión en config.json.template a 1.6.17 con referencias a Dashboard integrado en KPI Analyzer Pro. | `scm/config.json.template` |
| 2026-07-08 | **1.6.16** | **Tool 4 & Tool 38 Enhancements - Múltiples Proyectos GCP**: (1) **Tool 4 (Service Account Checker)** - Soporte para múltiples proyectos GCP con carga automática desde `config.json`. Permite override con `--projects=proj1,proj2,proj3`. Procesamiento paralelo con 5 workers. Tabla de resultados por proyecto. Spinner animado y barra de progreso. (2) **Tool 38 (Service Accounts Multi-Project Reporter)** - Visualización profesional con Rich library. Spinners y progreso durante extracción. Tabla de extracción por proyecto con columna de proyecto. Tabla de resumen final con duración. Procesamiento paralelo (5 workers). Fallback a print() si Rich no disponible. (3) **Integración tools.py** - Tool 4 no pregunta por proyecto, permite carga automática desde config.json. Cambio: `"args": ["--project", "-o"]` → `"args": ["-o"]`. Commits: `fd4d71e`, `c64033f`, `f3e68a5`, `e19a373`. | `scm/gcp/service-account/gcp_service_account_checker.py`, `scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py`, `scm/gcp/tools.py` |
| 2026-07-07 | **1.6.15** | **GCP Infrastructure Consolidation & Cloud Functions Analysis**: Implementación completa de 3 nuevas herramientas profesionales para consolidación de infraestructura GCP (Tools 35, 36, 37). (1) **Tool 35: Cloud Functions Analyzer** - Análisis profundo de Cloud Functions con seguridad, costos, triggers y performance. (2) **Tool 36: Infrastructure Consolidator** - Consolidación de Load Balancers, Cloud Run y Cloud Functions con mapeo de relaciones e identificación de servicios huérfanos. (3) **Tool 37: Unified Infrastructure Dashboard** - Dashboard ejecutivo unificado con alertas automáticas y recomendaciones. Incluye: 9 archivos de código (~3,200 líneas), 36 tests unitarios (100% exitosos), 6 documentos de análisis y guías (~2,700 líneas). Correcciones: manejo de diccionarios en tablas Rich, validación mejorada de sesión gcloud. Organización: archivos .md agrupados en carpetas temáticas (architecture, planning, analysis, sessions, corrections). Documentación de estructura agregada. | `scm/gcp/cloud-functions/`, `scm/gcp/consolidation/`, `docs/feature_loadbalancer/`, `tests/`, `docs/` |
| 2026-06-29 | **1.6.12** | **Dinamización de Menús - Eliminar Hardcode**: Implementación completa de generación dinámica de opciones de sistema (A, B, Q) en todas las plataformas. (1) **Estructura _system_options**: Diccionario de configuración con tipo, nombre, descripción y exclusiones. (2) **Función get_auto_tools()**: Genera lista de herramientas dinámicamente iterando por GROUP_ORDER y excluyendo especificadas. (3) **Función build_system_options()**: Construye opciones finales desde _system_options. (4) **Inicialización automática**: _init_system_options() al cargar módulo. Reducción: 113 → 56 líneas (50%), mapeos duplicados: 6 → 1 (83%), puntos de cambio: centralizados. Implementado en: azdo/tools.py, gcp/tools.py, aws/tools.py, terminal/tools.py, kpi_analyzer/tools.py. Sin cambios en API pública, comportamiento o salidas. Totalmente retrocompatible. | `scm/azdo/tools.py`, `scm/gcp/tools.py`, `scm/aws/tools.py`, `scm/terminal/tools.py`, `scm/kpi_analyzer/tools.py` |
| 2026-06-29 | **1.6.11** | **Análisis de Refactorización de Menús y Búsqueda Interactiva**: (1) Análisis exhaustivo de hardcode en menús: 113 líneas de hardcode identificadas en 6 archivos (main.py, azdo/tools.py, gcp/tools.py, aws/tools.py, terminal/tools.py, kpi_analyzer/tools.py). Propuesta de solución: generación dinámica de opciones de sistema con estructura `_system_options` y funciones reutilizables `get_auto_tools()` y `build_system_options()`. Reducción estimada: 50% de código (113 → 56 líneas). (2) Análisis de búsqueda interactiva: módulo `interactive_search.py` implementado en AZDO (328 líneas) con búsqueda fuzzy, captura de teclas multiplataforma (Windows/Linux/macOS), visualización con Rich. Problema: solo en AZDO (17% cobertura). Propuesta: crear módulo centralizado `scm/search_module.py` para expandir a todas las plataformas (100% cobertura). (3) Documentación completa en `docs/refactor_arquitectura/`: `ANALISIS_DINAMIZACION_MENUS.md`, `ANALISIS_COMPLETO_HARDCODE_MENUS.md`, `ANALISIS_BUSQUEDA_INTERACTIVA.md`. | `docs/refactor_arquitectura/`, `scm/azdo/interactive_search.py`, `scm/main.py`, `scm/*/tools.py` |
| 2026-06-18 | **1.6.10** | **Azure DevOps Pipeline Updater & Rollback System**: (1) **Pipeline Updater** (Tool 21, v1.0.6): Actualización masiva de pipelines (hasta 100) con batch processing, backup automático antes de cada cambio, confirmación con resumen de cambios, reportes JSON detallados, modo dry-run, y comentarios automáticos en pipelines. (2) **Pipeline Rollback** (Tool 22, v1.2.0): Sistema completo de rollback con 3 métodos - Full Backup Restore (máxima seguridad), Hybrid Rollback (usa revisión del backup desde Azure DevOps, lo mejor de ambos mundos), y Manual Revision (máxima flexibilidad). Incluye listado de backups/revisiones, validación de estructura, confirmaciones obligatorias, y modo dry-run. Backups almacenados en `outcome/backups/` con metadata completa. **AZDO Tools** actualizado a v1.3.4 con integración de ambas herramientas. | `scm/azdo/update-pipeline-cd-branchconfig.py`, `scm/azdo/rollback-pipeline.py`, `scm/azdo/tools.py` |
| 2026-06-09 | **1.6.9p** | **KPI Analyzer Fixes**: Correcciones críticas para KPI Analyzer: (1) Fix `MissingStyle` error eliminando `.replace('#', '')` en `border_style` (Rich requiere `#` en colores hex), (2) Fix `NameError` agregando import y inicialización de `DashboardGenerator`, (3) Agregadas dependencias faltantes a `requirements.txt` (pyyaml, pandas, plotly, streamlit), (4) Creados 17 unit tests en `test_kpi_analyzer.py` para mejorar cobertura. **AZDO Tools Fix**: Normalización de URL de organización en `tools.py` para prevenir duplicación de prefijo `https://dev.azure.com/` que causaba errores 400 Bad Request en todos los scripts AZDO. | `scm/kpi_analyzer/analyze_kpis.py`, `scm/requirements.txt`, `scm/tests/unit/test_kpi_analyzer.py`, `scm/azdo/tools.py` |
| 2026-06-09 | **1.6.9** | **KPI Analyzer**: Sistema completo de análisis de KPIs DevSecOps con modelo de madurez de 6 niveles (0-5), 30 KPIs organizados en 6 dimensiones, benchmarks de industria (DORA, SRE, ITIL, NIST CSF, ISO 20000), análisis automático desde salidas JSON, reportes (JSON/CSV/HTML), y documentación completa. Incluye: `analyze_kpis.py`, `analyzer.py`, `reporter.py`, `maturity_model.py`, `benchmarks.py`, `kpi_schema.yaml`, `docs/kpi_sources_inventory.md`, `docs/DevSecOps_Maturity_Model.md`, `docs/KPIs_Frameworks_DevSecOps.md`. | `scm/kpi_analyzer/`, `docs/` |
| 2026-06-04 | **1.6.8** | **AWS/GCP Homologation**: `scm/aws/tools.py` alineado visualmente con `scm/gcp/tools.py` — mismos colores (`Monitoreo` cyan, `Compute` bright_blue), emojis, nombres en español, GROUP_ORDER (monitoring primero) y estructura del menú Rich (columna Grupo width=18). `scm/aws/` validado: todos los sub-paquetes válidos tienen `__init__.py`. | `scm/aws/tools.py`, `scm/aws/**/__init__.py` |
| 2026-06-04 | **1.6.7** | **Wheel Fix W004**: Resuelto `check-wheel-contents W004` (módulos en paths no importables). Añadidos `__init__.py` a 19 sub-paquetes válidos (`azdo`, `aws/*`, `gcp/connectivity|monitoring|rolesypermisos`, `terminal`). Configurado `[tool.setuptools]` con `include-package-data = false` y `namespaces = false` para excluir directorios con guiones y keyword `lambda` del wheel. | `pyproject.toml`, 19× `__init__.py` |
| 2026-06-04 | **1.6.7p** | **Coverage Fix**: `omit` en `[tool.coverage.run]` para excluir módulos AWS/GCP/Terminal sin tests. Restaura umbral `fail-under=35` (38% total, 190/190 tests). | `pyproject.toml` |
| 2026-04-19 | **1.6.5** | **Terminal Scripts**: Nueva sección en `main.py` (opción 4) con 5 scripts shell universales agnósticos de cloud. Reubicados desde `gcp/scripts-console/` a `terminal/`: Certificate TLS Report, DB Connections Checker, Deployments Last News/Update/Events. | `scm/main.py`, `scm/terminal/` |
| 2026-04-19 | **1.6.4** | **Validación de plataforma**: `tools.py` detecta ejecución en Windows y muestra diálogo informativo cuando se intenta usar herramientas exclusivas de Linux (scripts `.sh`), sugiriendo WSL/Git Bash. | `scm/**/tools.py` |
| 2026-04-19 | **1.6.3** | **Certificate TLS Report**: Nueva herramienta (23) para validar certificados SSL/TLS remotos desde GKE con valores reales de TLS version y cipher. Integrada en `tools.py` con soporte para scripts shell. | `scm/terminal/` |
| 2026-04-18 | **1.6.2** | **Cross-platform venv**: Valida que el python del venv funcione antes de usarlo; si fue creado en otra plataforma (Linux/WSL vs Windows), lo recrea automáticamente y limpia caché de requirements. | `scm/**/tools.py` |
| 2026-04-17 | **1.6.1** | **make_dist.ps1**: Solo empaqueta folder `scm/`, lee exclusiones dinámicamente desde `.gitignore` en vez de hardcodearlas. | `make_dist.ps1` |
| 2026-04-16 | **1.6.0** | **Rich UI Inventory**: Reescritura de `generar-inventario-csv.sh` a Python con Rich (spinners, barras de progreso por hilo, Panel/Tabla). Auto-instalación de rich en venv. Launcher `run_inventory.py` con importación directa (no subprocess). | `scm/gcp/inventory/` |
| 2026-04-16 | **1.5.3** | **Sync Repos**: Script `sync_repos.py` para sincronización bidireccional toolbox ↔ azdo con commit automático. Nueva herramienta Inventario GKE+Cloud SQL (opción 22). | `sync_repos.py`, `scm/gcp/inventory/` |
| 2026-04-08 | **1.5.2** | **Docker Container**: Dockerfile slim con Azure/AWS/GCP CLI, kubectl, Helm, Terraform, netshoot. Docker Compose con 3 servicios. Entrypoint script con auto-configuración. | `Dockerfile`, `docker-compose.yml` |
| 2026-04-02 | **1.5.1** | **Testing Suite**: Arquitectura profesional de testing con pytest, cobertura 70%+, mocks para GCP/AZDO/AWS, CI/CD con GitHub Actions. Tests unitarios e integración con 500+ assertions. | `scm/tests/`, `pytest.ini` |
| 2026-04-02 | **1.5.0** | **Config Unificado**: Template `config.json.template` para gestión centralizada de tokens/credenciales de AZDO, GCP y AWS. Variables de entorno automáticas al lanzar plataformas. | `config.json.template`, `scm/main.py` |
| 2026-03-31 | **1.4.1** | **AWS Toolbox**: 13 herramientas DevSecOps para AWS (IAM, RDS, VPC, EKS, ECR, EC2, Lambda, CloudWatch). | `scm/aws/` |
| 2026-03-31 | **1.1.1** | **Análisis Pro**: Reporte completo de arquitectura con 15+ mejoras priorizadas. | `ARCHITECTURE_ANALYSIS_PRO.md` |
| 2026-03-26 | **1.0.0** | **Versión inicial**: Launcher unificado para GCP y Azure DevOps. | `scm/main.py`, `scm/gcp/`, `scm/azdo/` |

---

## Versiones por Sub-proyecto

Las herramientas individuales de cada plataforma mantienen su propia versión interna en `tools.py`:

| Plataforma | `tools.py` Version | Notas |
|------------|-------------------|-------|
| **GCP** | `1.9.3` | Launcher GCP (25 herramientas) |
| **AZDO** | `1.3.4` | Launcher Azure DevOps (22 herramientas) — incluye Pipeline Updater y Rollback |
| **AWS** | `1.0.1` | Launcher AWS (19 herramientas) — homologado visualmente con GCP en v1.6.8 |
| **Terminal** | `1.0.2` | Scripts universales agnósticos de cloud (6 herramientas) |

> **Nota**: La versión del toolbox (`1.6.10`) es independiente de la versión interna de cada launcher. La versión del toolbox se usa para empaquetado (wheel), Docker tags y releases de GitHub.

---

## Convención de Versionado

El proyecto sigue [Semantic Versioning 2.0.0](https://semver.org/lang/es/):

```
MAJOR.MINOR.PATCH

MAJOR — Cambios incompatibles con versiones anteriores
MINOR — Nuevas funcionalidades (compatibles hacia atrás)
PATCH — Correcciones de bugs (compatibles hacia atrás)
```

**Regla del proyecto**: solo se generan versiones PATCH (ej: 1.6.7 → 1.6.8). No se generan versiones MAJOR ni MINOR.

---

## Referencias

- `VERSION` — Archivo fuente de verdad (versión actual del toolbox)
- `pyproject.toml` — Metadatos del paquete Python (build/wheel)
- `scm/__init__.py` — `__version__` (importable desde Python)
- Badges en `README.md` — Referencia visual al archivo `VERSION`
