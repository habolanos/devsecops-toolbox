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

#### Uso

```bash
# Análisis básico
./k8s-deploy-manifest-diff.sh <deployment> <namespace>

# Con exportación a outcome/
./k8s-deploy-manifest-diff.sh orders-service prod --export

# Mostrando valores de env vars directas (ocultos por defecto)
./k8s-deploy-manifest-diff.sh payments-api staging --full-env

# Omitir sección de eventos (más rápido)
./k8s-deploy-manifest-diff.sh gateway default --no-events

# Combinar opciones
./k8s-deploy-manifest-diff.sh my-svc prod --export --no-events
```

#### Exit codes (útiles como quality gate en CI/CD)

```
0 → Sin riesgo o riesgo LOW
1 → Riesgo MEDIUM o HIGH detectado
2 → Riesgo CRITICAL detectado
```

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

---

## Historial de cambios

| Fecha | Versión | Cambio | Archivos |
|-------|---------|--------|---------|
| 2026-06-03 | 1.0.1 | **Script 6: `k8s-deploy-manifest-diff.sh`** — Diff ejecutivo de manifiestos K8s: imagen, recursos, env vars, ConfigMaps, Secrets, probes, HPA, volumes, ServiceAccount, eventos. Clasificación de riesgo en 4 niveles (24+ reglas). Score de impacto. Recomendaciones automáticas. Export `--export`. Flags `--full-env`, `--no-events`. Exit 0/1/2. `tools.py` v1.0.1 con handlers para deployment/namespace/flags | `k8s-deploy-manifest-diff.sh` (nuevo), `tools.py`, `README.md` |
| 2026-06-01 | 1.0.0 | Scripts iniciales: Certificate TLS, DB Checker, Deployments Last News/Update/Events | `check-certificate-report.sh`, `db-connections-checker.sh`, `deployments-*.sh`, `tools.py` |
