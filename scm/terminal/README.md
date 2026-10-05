# Terminal Tools — Scripts Universales para Kubernetes

Scripts shell agnósticos de cloud para inspección y análisis de infraestructura Kubernetes.
Compatibles con cualquier clúster K8s: **GKE, EKS, AKS, OpenShift, Minikube**.

---

## Contenido del directorio

```
devsecops-toolbox/scm/terminal/
├── tools.py                          # Launcher interactivo (punto de entrada)
├── check-certificate-report.sh       # Script 1 — Validación TLS/SSL de certificados
├── db-connections-checker.sh         # Script 2 — Verificación de conectividad a PostgreSQL
├── deployments-last-news.sh          # Script 3 — Deployments más recientes por creación
├── deployments-last-update.sh        # Script 4 — Deployments por último rollout (ReplicaSet)
├── deployments-recent-events.sh      # Script 5 — Eventos K8s recientes por Deployment
├── k8s-deploy-manifest-diff.sh       # Script 6 — Diff de manifiestos deploy actual vs anterior
├── check_cluster_memory_cpu_limits/  # Script 7 — Analizador de límites CPU/Mem GKE (90 días)
├── operation_setup_initial/          # Script 8 — Setup de entorno DevOps en Linux/WSL
│   └── install-devops-tools.sh
├── operation_update_certs_on_gke_gcp/  # Script 9 — Cert Manager Tools (submenú Python)
│   ├── tools.py                      #   Launcher interactivo Rich
│   ├── cert_backup_and_renew_tls_certs.sh
│   ├── cert_check-certificate-report.sh
│   └── cert_report_ssl_certs_gcp_components.sh
├── azdo_check_scm_inspection/        # Script 10 — Violaciones del stage SCM Inspection (AzDO)
│   └── inspection_errors.sh
├── config.json.template              # Plantilla de configuración
└── outcome/                          # Carpeta de reportes exportados (.txt)
```

---

## Requisitos

| Requisito | Versión mínima | Notas |
|-----------|---------------|-------|
| `kubectl` | 1.24+ | Configurado y autenticado al clúster |
| `jq`      | 1.6+  | Solo para `k8s-deploy-manifest-diff.sh` |
| `bash`    | 4.0+  | Todos los scripts usan `#!/usr/bin/env bash` |

### Instalar jq
```bash
# Debian/Ubuntu
apt-get install -y jq

# macOS
brew install jq

# Alpine (pods)
apk add jq
```

---

## Scripts

### Script 6 — `k8s-deploy-manifest-diff.sh` ⭐ Nuevo

Compara el manifiesto aplicado en el **Deployment actual** vs la **revisión anterior**,
analizando todos los artefactos del ciclo de vida del pod. Genera un informe ejecutivo
de riesgos con clasificación automática de severidad.

#### Artefactos analizados

| Sección | Qué compara |
|---------|-------------|
| **Rollout Status** | Réplicas deseadas vs listas, unavailable, estrategia |
| **Imagen** | Tag anterior vs actual por contenedor (detecta `:latest`) |
| **Recursos** | CPU/Memory requests y limits (detecta eliminación de límites) |
| **Env Vars** | Variables directas agregadas/eliminadas; referencias a ConfigMap/Secret |
| **ConfigMaps** | Referencias agregadas/eliminadas + keys del ConfigMap actual |
| **Secrets** | Referencias agregadas/eliminadas + keys (valores enmascarados) |
| **Probes** | Liveness/Readiness/Startup: tipo, path, puerto, timings |
| **HPA / Volumes / SA** | Auto-scaler, volume mounts, ServiceAccount, privileged mode |
| **Eventos** | Últimos Warning/Normal asociados al Deployment y sus pods |

#### Clasificación de riesgo

| Nivel | Ejemplo de hallazgo |
|-------|-------------------|
| 🚨 **CRITICAL** | Deployment degradado, tag `:latest`, resource limits eliminados, liveness probe eliminada, Secret/ConfigMap no encontrado, `privileged=true` |
| 🔴 **HIGH** | Imagen cambiada, env var eliminada, readiness probe eliminada, Secret nuevo referenciado, ServiceAccount cambiado, > 3 Warning events |
| 🟡 **MEDIUM** | Env var agregada, ConfigMap nuevo, volume mount agregado, recursos ajustados, 1-3 Warning events |
| 🔵 **LOW** | Cambios menores de configuración |

#### Opciones disponibles

| Flag | Default | Descripción |
|------|---------|-------------|
| `--export` | off | Exporta el informe de análisis a `outcome/k8s_diff_*.txt` |
| `--full-env` | off | Muestra valores literales de env vars directas |
| `--no-events` | off | Omite la sección de eventos (más rápido) |
| `--no-commands` | **on** | Desactiva la exportación de comandos de inspección PRD |

> `--no-commands` es el único flag activo por defecto. Los comandos se generan y exportan siempre a menos que se indique este flag.

#### Uso

```bash
# Análisis básico (incluye sección de comandos PRD por defecto)
./k8s-deploy-manifest-diff.sh orders-service prod

# Con exportación completa (informe .txt + comandos .json)
./k8s-deploy-manifest-diff.sh orders-service prod --export

# Solo informe de riesgos, sin comandos
./k8s-deploy-manifest-diff.sh orders-service prod --no-commands

# Mostrando valores de env vars directas
./k8s-deploy-manifest-diff.sh payments-api staging --full-env

# Máxima velocidad (sin eventos, sin comandos)
./k8s-deploy-manifest-diff.sh gateway default --no-events --no-commands

# Combinación completa
./k8s-deploy-manifest-diff.sh my-svc prod --export --full-env
```

#### Exit codes (útiles como quality gate en CI/CD)

```
0 → Sin riesgo o riesgo LOW
1 → Riesgo MEDIUM o HIGH detectado
2 → Riesgo CRITICAL detectado
```

#### Salida de comandos de inspección (activo por defecto)

Al final del informe se muestra un bloque agrupado por sección con comandos
listos para copiar y ejecutar en PRD:

```
╔═════════════════════════════════════════════════════════════════╗
║   📋 COMANDOS DE INSPECCIÓN PARA PRD                          ║
╚═════════════════════════════════════════════════════════════════╝
  Deployment: orders-service | Namespace: prod | Rev: #8

  ── Rollout ──
    Estado del rollout
  $ kubectl rollout status deployment/orders-service -n prod
    Historial de revisiones
  $ kubectl rollout history deployment/orders-service -n prod
  ...
  ── Rollback ──
    Revertir a revision anterior
  $ kubectl rollout undo deployment/orders-service -n prod
  ...

  📄 Comandos exportados: outcome/k8s_commands_orders-service_prod_20260603_160000.json
```

El JSON exportado a `outcome/` incluye metadatos (deployment, namespace, revisiones,
timestamp) y el array `commands[]` con `section`, `description` y `command` por entrada.

#### Cómo obtiene la versión anterior

El script usa los **ReplicaSets** del Deployment ordenados por la anotación
`deployment.kubernetes.io/revision`. El más reciente es la versión actual y el
anterior es la versión previa. Los ReplicaSets preservan el pod template de cada
revisión histórica mientras estén en el clúster.

> **Nota:** Para diff de valores históricos de ConfigMaps, se requiere un
> sistema GitOps (Flux, ArgoCD) ya que el clúster solo almacena el estado actual.

---

### Script 1 — `check-certificate-report.sh`

Valida certificados TLS/SSL remotos desde el clúster K8s.

```bash
./check-certificate-report.sh api.ejemplo.com
./check-certificate-report.sh api.ejemplo.com 8443
```

### Script 2 — `db-connections-checker.sh`

Verifica conectividad a instancias PostgreSQL.

```bash
./db-connections-checker.sh prod-db "jdbc:postgresql://host:5432/mydb"
```

### Scripts 3-5 — Deployments

```bash
./deployments-last-news.sh 20
./deployments-last-update.sh 15 prod
./deployments-recent-events.sh 20 prod
```

### Script 8 — `operation_setup_initial/install-devops-tools.sh` ⭐ Nuevo

Configura un entorno **Ubuntu / WSL** con el toolchain completo requerido para el
rol **SCM DevOps Engineer**. Instala y valida automáticamente cada herramienta.

#### Herramientas instaladas

| Paso | Herramientas |
|------|--------------|
| 1 | Paquetes base: `git`, `curl`, `wget`, `jq`, `unzip`, `python3`, `pip`, `pipx`, `nodejs`, `kubectx` |
| 2 | `pipx ensurepath` + `~/.local/bin` en `PATH` (persistente en `.bashrc`) |
| 3 | Repositorio APT de Google Cloud (keyring + source list) |
| 4 | `google-cloud-cli`, `kubectl`, `gke-gcloud-auth-plugin` |
| 5 | `k9s` (.deb para amd64/arm64 desde GitHub releases) |
| 6 | Validación: tabla de versiones de cada herramienta |

#### Uso

```bash
# Desde el launcher: opción 8 en Terminal Tools
# O directamente:
./operation_setup_initial/install-devops-tools.sh
```

> **Requisitos**: Ubuntu/Debian (o WSL), privilegios `sudo` y conexión a Internet.
> El script usa `set -euo pipefail` y `apt`, por lo que es interactivo en los
> prompts de sudo. Al finalizar ejecuta `source ~/.bashrc`.

### Script 9 — `operation_update_certs_on_gke_gcp/tools.py` ⭐ Nuevo

Submenú interactivo (Rich) que agrupa la operación de certificados TLS descrita
en el `README.md` de esa carpeta. Cubre dos alcances: Secrets `kubernetes.io/tls`
de K8s/GKE y `ssl-certificates` de Compute Engine.

#### Opciones del submenú

| # | Alcance | Operación | Script |
|---|---------|-----------|--------|
| 1 | K8s/GKE | Backup y renovación de Secrets TLS (genera YAML + evidencia HTML, sin aplicar) | `cert_backup_and_renew_tls_certs.sh` |
| 2 | K8s/GKE | Validar certificado TLS de un endpoint (pod temporal `jrecord/nettools`) | `cert_check-certificate-report.sh` |
| 3 | GCP | Inventario de ssl-certificates del proyecto + cartas para Multicloud | `cert_report_ssl_certs_gcp_components.sh` |
| 4 | CHECK | Verificar prerrequisitos (bash, kubectl contexto/permisos, openssl, jq, gcloud) | — |
| Q | — | Volver | — |

Los prompts del submenú corresponden a los argumentos documentados: archivo base
(`--base-cert-file`, default `cer-io-2027.yml`), host/puerto, `PROJECT_ID` y
`--todos`. La opción 3 permite exportar el reporte a `outcome/`.

#### Uso

```bash
# Desde el launcher: opción 9 en Terminal Tools
# O directamente:
python operation_update_certs_on_gke_gcp/tools.py
```

> **Requisitos**: Linux/WSL/POSIX con `bash` para los scripts .sh, `kubectl`
> autenticado (alcance K8s) y `gcloud` autenticado (alcance GCP). Los artefactos
> (`tls-backups-*/`, `update-certs-*.yaml`, `evidencia-*.html`) se generan en la
> misma carpeta del módulo.

### Script 10 — `azdo_check_scm_inspection/inspection_errors.sh` ⭐ Nuevo

Extrae las violaciones que reporta el stage **"SCM Inspection"** de los release
pipelines de Azure DevOps. El stage imprime cada violación como bloques
`##[warning]`/`##[error]`; el script descarga los logs de las tareas del último
run del stage y los parsea a CSV (severidad, regla, environment, variable,
razón, detalle, task).

#### Uso

```bash
# Desde el launcher: opción 10 en Terminal Tools (prompts guiados)
# O directamente:
./azdo_check_scm_inspection/inspection_errors.sh <definitionId|nombre>
./azdo_check_scm_inspection/inspection_errors.sh --all [--severity critical,high]
./azdo_check_scm_inspection/inspection_errors.sh 787 --release 60150 --keep-logs
```

#### Autenticación y salida

- **PAT**: `AZDO_PAT` (env) → si falta, `scm/config.json` `azdo.pat`.
  `AZDO_ORG`/`AZDO_PROJECT` también caen a `azdo.organization`/`azdo.project`.
- **Salida**: `inspection_violations_*.csv`, `inspection_project_summary_*.csv`,
  `inspection_project_violations_*.csv` y `inspection_logs_<releaseId>/` se
  escriben en el **outcome resuelto**: `DEVSECOPS_OUTPUT_DIR` →
  `global.output_dir` en config.json → `scm/outcome/`.

> **Requisitos**: `bash` 4.3+, `curl`, `jq` 1.6+. El modo `--all` escanea las
> pipelines en paralelo (`AZDO_CONCURRENCY`, `AZDO_REQUEST_DELAY_MS`).

---

## Historial de cambios

| Fecha | Versión | Cambio | Archivos |
|-------|---------|--------|---------|
| 2026-10-04 | 1.0.7 | **Script 10: AzDO SCM Inspection Violations** — `inspection_errors.sh` registrado en el launcher (prompts: pipeline/`--all`, severidad, stage, `--release`, `--keep-logs`). El script ahora resuelve salida al outcome global (`DEVSECOPS_OUTPUT_DIR` → `global.output_dir` → `scm/outcome`) y lee credenciales de `config.json` (`azdo.pat`/`organization`/`project`) como fallback de las env vars. `prepare_env_from_config` también inyecta `AZDO_*` al hijo. Tests en `test_terminal_tools.py`. | `azdo_check_scm_inspection/inspection_errors.sh`, `tools.py`, `README.md` |
| 2026-09-29 | 1.0.6 | **Cert backup/renew: salida única en outcome global** — `cert_backup_and_renew_tls_certs.sh` ahora agrupa `tls-backups/`, `update-certs-*.yaml` y `evidencia-*.html` en `<OUTCOME>/certs-<cluster>-<ts>/`. Resolución de `<OUTCOME>`: `DEVSECOPS_OUTPUT_DIR` → `scm/config.json` (`global.output_dir`) → `scm/outcome`. El submenú (v1.0.1) inyecta `DEVSECOPS_OUTPUT_DIR` resuelto al ejecutar standalone. | `operation_update_certs_on_gke_gcp/cert_backup_and_renew_tls_certs.sh`, `operation_update_certs_on_gke_gcp/tools.py`, `operation_update_certs_on_gke_gcp/README.md`, `tools.py` |
| 2026-09-29 | 1.0.5 | **Script 9: Cert Manager Tools (submenú Python)** — Nuevo launcher `operation_update_certs_on_gke_gcp/tools.py` con interfaz Rich: agrupa los 3 scripts de certificados (backup/renovación Secrets TLS, validación TLS de endpoint, inventario ssl-certificates GCP) más una opción de verificación de prerrequisitos (kubectl/gcloud/bash/openssl/jq). Prompts guiados para `--base-cert-file`, host/puerto, PROJECT_ID y `--todos`; exportación del inventario a `outcome/`. `tools.py` (terminal) v1.0.5. | `operation_update_certs_on_gke_gcp/tools.py` (nuevo), `tools.py`, `README.md` |
| 2026-09-29 | 1.0.4 | **Script 8: Setup Entorno DevOps (Linux/WSL)** — Nueva opción en el menú que ejecuta `operation_setup_initial/install-devops-tools.sh`: instala el toolchain SCM DevOps en Ubuntu/WSL (gcloud, kubectl, gke-gcloud-auth-plugin, kubectx/kubens, k9s, jq, python3, pipx, nodejs, git) vía apt con validación final de versiones. `tools.py` v1.0.4. | `operation_setup_initial/install-devops-tools.sh`, `tools.py`, `README.md` |
| 2026-06-18 | 1.0.3 | **Script 7: Azure DevOps Pipeline Updater** — Herramienta Python para actualizar Release Pipelines de Azure DevOps vía API REST. Actualiza variable `branchConfig` y scripts de tareas en todos los environments. Modo interactivo con config.json (hereda org/project/pat de `azdo` parent). Búsqueda dual por `name` y `displayName`. Dry-run mode. `tools.py` v1.0.3 con soporte Python scripts. | `update-pipeline-cd-branchconfig.py` (nuevo), `tools.py`, `config.json.template`, `AZURE_DEVOPS_PIPELINE_UPDATER.md`, `IMPLEMENTATION_SUMMARY.md` |
| 2026-06-03 | 1.0.2 | **Script 6 v1.1: `--no-commands` desactivable** — Flag `--no-commands` añadido (activo por defecto). Exporta comandos de inspección para equipo PRD al final de cada ejecución: bloque por sección (Rollout/Imagen/Recursos/EnvVars/ConfigMap/Secret/Probes/HPA/Eventos/Rollback) + JSON `outcome/k8s_commands_*.json` con metadatos. `tools.py` v1.0.2 incluye prompt `--no-commands`. | `k8s-deploy-manifest-diff.sh` v1.1, `tools.py`, `README.md` |
| 2026-06-03 | 1.0.1 | **Script 6: `k8s-deploy-manifest-diff.sh`** — Diff ejecutivo de manifiestos K8s: imagen, recursos, env vars, ConfigMaps, Secrets, probes, HPA, volumes, ServiceAccount, eventos. Clasificación de riesgo en 4 niveles (24+ reglas). Score de impacto. Recomendaciones automáticas. Export `--export`. Flags `--full-env`, `--no-events`. Exit 0/1/2. `tools.py` v1.0.1 con handlers para deployment/namespace/flags | `k8s-deploy-manifest-diff.sh` (nuevo), `tools.py`, `README.md` |
| 2026-06-01 | 1.0.0 | Scripts iniciales: Certificate TLS, DB Checker, Deployments Last News/Update/Events | `check-certificate-report.sh`, `db-connections-checker.sh`, `deployments-*.sh`, `tools.py` |
