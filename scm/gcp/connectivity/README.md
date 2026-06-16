# Connectivity Tools

Herramientas para validar conectividad, configuración y dependencias de Deployments en GKE.

## 📋 Contenido

| Archivo | Descripción |
|---------|-------------|
| `pod_connectivity_checker.py` | Valida conectividad Pod → Cloud SQL |
| `deploy_dependency_checker.py` | Detecta dependencias de un Deployment (ConfigMaps) y valida conectividad DB |
| `deployment_validator.py` | Valida ConfigMaps, Secrets y conectividad de un Deployment |
| `README.md` | Documentación detallada |

---

## 🗺️ Especialidad de Cada Herramienta

Los tres scripts tienen **propósito, alcance y público objetivo diferentes**, aunque todos validan conectividad en GKE/GCP.

### `deployment_validator.py` — Validador Integral de Deployments

> **Pregunta que responde:** *¿Está mi Deployment correctamente configurado y puede alcanzar sus dependencias?*

Herramienta más completa. Valida en **4 capas** partiendo del nombre de un Deployment:

| Capa | Qué valida |
|------|-----------|
| **ConfigMaps** | Existencia, claves vacías, placeholders (`<CHANGE_ME>`, `TODO`) |
| **Secrets** | Existencia, claves sensibles vacías (base64 → `""`), datos binarios |
| **TCP Nivel 1** | Conectividad de red usando pod temporal + `nc -z` |
| **DB Probe Nivel 2** | Protocolo nativo del motor (PostgreSQL SSL-request, MySQL greeting, Redis PING) para descartar falsos positivos de LB |

**Flags únicos:** `--validate configmaps|secrets|connectivity|all`, `--db-probe`, `--severity`.

---

### `deploy_dependency_checker.py` — Checker de Dependencias por ConfigMaps

> **Pregunta que responde:** *¿A qué bases de datos apuntan los ConfigMaps de mi Deployment y puedo conectarme?*

Herramienta ligera y rápida. Foco **exclusivo en conectividad DB desde ConfigMaps**:

| Característica | Detalle |
|----------------|---------|
| **Alcance** | Solo ConfigMaps (no analiza Secrets ni severidades) |
| **Modo local** | `--probe-mode=local` prueba TCP con `socket` Python desde el host — sin necesitar crear pods |
| **Modo pod** | `--probe-mode=pod` crea pod temporal igual que `deployment_validator.py` |
| **DB Probe** | Mismo mecanismo `--db-probe` que `deployment_validator.py` |

**Diferencia clave vs `deployment_validator.py`:** más rápido porque no analiza Secrets ni severidades. `--probe-mode=local` permite usarlo sin acceso completo a kubectl.

---

### `pod_connectivity_checker.py` — Validador de Infraestructura Cloud SQL

> **Pregunta que responde:** *¿Está toda la infraestructura GCP correctamente configurada para que mis pods alcancen Cloud SQL?*

Herramienta de diagnóstico profundo. Analiza **9 capas de infraestructura GCP** usando `gcloud` y `kubectl` — **no crea pods temporales**:

| Sección | Qué valida |
|---------|-----------|
| **0. Discovery** | Proyecto, cluster, namespace, KSA, GSA desde contexto kubectl/gcloud |
| **1. Cloud SQL** | Existencia de la instancia, estado (`RUNNABLE`/`STOPPED`), IPs privada/pública |
| **2. GKE Cluster** | VPC-native (alias IP), Workload Identity habilitado |
| **3. VPC & PSC** | Red VPC, rangos IP, VPC Peering con `servicenetwork` de Google |
| **4. Firewall** | Reglas de egress al puerto SQL (5432/3306) |
| **5. IAM** | Roles `cloudsql.client`/`cloudsql.instanceUser` en el GSA |
| **6. Workload Identity** | Anotación KSA ↔ GSA, IAM binding `roles/iam.workloadIdentityUser` |
| **7. SQL Auth Proxy** | Detecta sidecar `cloud-sql-proxy` |
| **8. Load Balancers** | Servicios LB/NodePort/ClusterIP, Forwarding Rules, Backend Health |
| **9. Connectivity** | TCP directo con latencia + `gcloud network-management` test |

**Diferencia clave:** es el único que diagnostica la **capa de infraestructura GCP** (IAM, VPC, Firewall, Workload Identity). Los otros dos asumen que la infraestructura existe y solo verifican si la conexión funciona.

---

### Cuadro Comparativo

| Característica | `deployment_validator` | `deploy_dependency_checker` | `pod_connectivity_checker` |
|---|:---:|:---:|:---:|
| Valida ConfigMaps | ✅ | ✅ | ❌ |
| Valida Secrets | ✅ | ❌ | ❌ |
| JDBC URL sin puerto (default port) | ✅ | ✅ | ❌ N/A |
| TCP via pod temporal | ✅ | ✅ | ❌ |
| TCP local (socket Python) | ❌ | ✅ `--probe-mode=local` | ✅ directo |
| DB Probe nivel 2 (`--db-probe`) | ✅ | ✅ | ❌ |
| Diagnóstico IAM GCP | ❌ | ❌ | ✅ |
| Diagnóstico VPC / Firewall | ❌ | ❌ | ✅ |
| Workload Identity check | ❌ | ❌ | ✅ |
| Cloud SQL instance check | ❌ | ❌ | ✅ |
| Export JSON / CSV | ✅ | ✅ | ✅ |
| Requiere `--sql-instance` | ❌ | ❌ | ✅ requerido |
| Severidades (CRITICAL/WARNING/INFO) | ✅ | ❌ | ❌ |

### ¿Cuándo usar cada uno?

| Situación | Herramienta recomendada |
|-----------|------------------------|
| Revisión completa pre-release de un Deployment | `deployment_validator.py` |
| Verificar rápido si las BDs en ConfigMaps son alcanzables | `deploy_dependency_checker.py` |
| Diagnosticar por qué los pods no se conectan a Cloud SQL | `pod_connectivity_checker.py` |
| Detectar falsos positivos de load balancers (BD apagada) | Cualquiera con `--db-probe` |
| Sin acceso completo a kubectl (solo red local) | `deploy_dependency_checker.py --probe-mode=local` |

---

## 🛡️ Deployment Validator

Herramienta completa para validar deployments de Kubernetes:
- ✅ Valida existencia y contenido de **ConfigMaps** y **Secrets** referenciados
- ✅ Detecta valores vacíos, placeholders o mal configurados
- ✅ Extrae cadenas de conexión a bases de datos (**incluye JDBC URLs sin puerto explícito**)
- ✅ Valida conectividad **Nivel 1 TCP** usando pod temporal con `nettools`
- ✅ Valida conectividad **Nivel 2 DB Probe** (`--db-probe`): protocolo nativo del motor para evitar falsos positivos de load balancers
- ✅ Genera reportes detallados con recomendaciones

### Uso Básico

```bash
# Validar todo (ConfigMaps, Secrets, Conectividad TCP)
python deployment_validator.py --deployment my-app --namespace production

# Validar + DB Probe nivel 2 (descarta falsos positivos de load balancers)
python deployment_validator.py -d my-app -n production --db-probe

# Solo validar Secrets
python deployment_validator.py -d my-app -n prod --validate secrets

# Solo validar conectividad con DB probe
python deployment_validator.py -d my-app --validate connectivity --db-probe

# Exportar reporte a JSON (incluye tcp_status, db_probe_status, db_probe_message)
python deployment_validator.py -d my-app -o json --db-probe
```

### Argumentos

| Argumento | Descripción | Default |
|-----------|-------------|---------|
| `--project, -p` | ID del proyecto GCP | `cpl-corp-cial-prod-17042024` |
| `--cluster, -c` | Nombre del cluster GKE | `gke-corp-cial-prod-01` |
| `--region, -r` | Región del cluster GKE | `us-central1` |
| `--deployment, -d` | Nombre del deployment a validar | `ds-ppm-pricing-discount` |
| `--namespace, -n` | Namespace (auto-detecta si se omite) | Auto |
| `--validate` | Tipo: `all`, `secrets`, `configmaps`, `connectivity` | `all` |
| `--probe-image` | Imagen para pod temporal | `jrecord/nettools:latest` |
| `--timeout` | Timeout para pruebas TCP (segundos) | `5` |
| `--db-probe` | Nivel 2: envía protocolo nativo del motor DB para confirmar que la BD responde (evita falsos positivos de LB) | `false` |
| `--output, -o` | Exportar a `json` o `csv` | - |
| `--severity` | Filtrar: `critical`, `warning`, `info`, `all` | `all` |
| `--debug` | Modo debug | `false` |

### Flujo de Validación

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT VALIDATOR                              │
├─────────────────────────────────────────────────────────────────────┤
│ 1. DISCOVERY                                                         │
│    └─ Obtener manifiesto del Deployment                             │
│    └─ Extraer referencias a ConfigMaps y Secrets                    │
├─────────────────────────────────────────────────────────────────────┤
│ 2. SECRETS VALIDATION                                                │
│    └─ Verificar existencia de cada Secret                           │
│    └─ Detectar claves con valores vacíos (base64 → "")              │
│    └─ Clasificar severidad (CRITICAL para claves sensibles)         │
├─────────────────────────────────────────────────────────────────────┤
│ 3. CONFIGMAPS VALIDATION                                             │
│    └─ Verificar existencia de cada ConfigMap                        │
│    └─ Detectar claves vacías o placeholder                          │
│    └─ Parsear cadenas de conexión (JDBC, MongoDB, Redis)            │
├─────────────────────────────────────────────────────────────────────┤
│ 4. CONNECTIVITY TEST — Nivel 1: TCP                                 │
│    └─ kubectl run validator-probe-xxx --image=jrecord/nettools      │
│    └─ nc -zv <host> <port> para cada endpoint                       │
│    └─ Reportar latencia y estado (OK/TIMEOUT/UNREACHABLE)           │
├─────────────────────────────────────────────────────────────────────┤
│ 5. DB PROBE (--db-probe) — Nivel 2: protocolo nativo del motor      │
│    └─ Solo si TCP = OK (no tiene sentido si el TCP ya falla)        │
│    └─ PostgreSQL: SSL-request packet (8 bytes) → espera 'N'/'S'    │
│    └─ MySQL: espera greeting packet (≥4 bytes al conectar)          │
│    └─ Redis: envía PING RESP → espera +PONG                        │
│    └─ Si FAILED: status cambia a DB_PROBE_FAIL (falso positivo LB)  │
│    └─ Cleanup automático del pod temporal                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Severidades

| Severidad | Emoji | Descripción |
|-----------|-------|-------------|
| CRITICAL | 🔴 | Secret/ConfigMap faltante, clave sensible vacía |
| WARNING | 🟡 | Valores placeholder, timeouts de conexión |
| INFO | 🔵 | Datos binarios, información general |
| OK | 🟢 | Validación exitosa |

### Ejemplo de Salida

```
┌─────────────────────────────────────────────────────────────────────┐
│                    📋 Hallazgos de Validación                        │
├──────┬────────────┬─────────────────────────┬────────────────────────┤
│ Sev  │ Tipo       │ Recurso                 │ Mensaje                │
├──────┼────────────┼─────────────────────────┼────────────────────────┤
│ 🔴   │ Secret     │ db-credentials          │ Clave sensible vacía   │
│ 🟡   │ ConfigMap  │ app-config              │ Valor placeholder      │
│ 🔵   │ Secret     │ tls-cert                │ Datos binarios         │
└──────┴────────────┴─────────────────────────┴────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    🔌 Validación de Conectividad                     │
├──────────┬────────────────────┬────────────────────┬────────┬────────┤
│ Origen   │ Recurso            │ Host               │ Puerto │ Estado │
├──────────┼────────────────────┼────────────────────┼────────┼────────┤
│ ConfigMap│ db-config          │ 10.128.0.5         │ 5432   │ ✅ OK  │
│ ConfigMap│ redis-config       │ 10.128.0.10        │ 6379   │ ❌ FAIL│
└──────────┴────────────────────┴────────────────────┴────────┴────────┘
```

---

## Arquitectura de Conectividad

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FLUJO DE CONECTIVIDAD                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │   POD       │───▶│   SERVICE   │───▶│   VPC       │───▶│   CLOUD SQL         │   │
│  │ (Deployment)│    │ (LB/ClusterIP)   │ (Network)   │    │   (Private/Public)  │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────────────┘   │
│        │                   │                  │                      │              │
│        ▼                   ▼                  ▼                      ▼              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │    KSA      │    │  Firewall   │    │    PSC      │    │    Authorized       │   │
│  │ (K8s SA)    │    │   Rules     │    │  (Peering)  │    │    Networks         │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────────────┘   │
│        │                                                             │              │
│        ▼                                                             ▼              │
│  ┌─────────────┐                                          ┌─────────────────────┐   │
│  │    GSA      │─────────────────────────────────────────▶│    IAM Roles        │   │
│  │ (Google SA) │         Workload Identity                │ (cloudsql.client)   │   │
│  └─────────────┘                                          └─────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Requisitos

- Python 3.8+
- `gcloud` CLI instalado y autenticado
- `kubectl` CLI instalado y configurado
- Permisos IAM requeridos:
  - `container.clusters.get`
  - `cloudsql.instances.get`
  - `compute.networks.get`
  - `compute.firewalls.list`
  - `iam.serviceAccounts.get`

## Instalación

No requiere dependencias adicionales, solo la librería estándar de Python.

```bash
# Clonar el repositorio
git clone <repo-url>
cd gcp/connectivity

# Verificar autenticación
gcloud auth login
kubectl config current-context
```

---

## Fases de Validación (Paso a Paso)

### Fase 0: Discovery (Descubrimiento Automático)

El script descubre automáticamente la configuración del entorno:

| Elemento | Fuente | Comando |
|----------|--------|---------|
| **Project** | gcloud config | `gcloud config get-value project` |
| **Cluster** | kubectl context | `kubectl config current-context` |
| **Location** | kubectl context | Extraído del formato `gke_PROJECT_LOCATION_CLUSTER` |
| **Namespace** | Deployment | `kubectl get deployments --all-namespaces` |
| **KSA** | Deployment spec | `spec.template.spec.serviceAccountName` |
| **GSA** | KSA annotation | `iam.gke.io/gcp-service-account` |

```python
# Ejemplo de discovery del contexto
success, context = run_kubectl(["config", "current-context"])
# Resultado: "gke_my-project_us-central1_my-cluster"
# Extrae: project=my-project, location=us-central1, cluster=my-cluster
```

---

### Fase 1: Cloud SQL Instance

Valida que la instancia de Cloud SQL existe y está operativa.

| Check | Descripción | Comando |
|-------|-------------|---------|
| **Instance Exists** | Verifica existencia y estado | `gcloud sql instances describe INSTANCE` |
| **IP Configuration** | Verifica IP privada/pública | Campo `ipAddresses` del resultado |
| **Authorized Networks** | Redes autorizadas (si IP pública) | Campo `authorizedNetworks` |

**Estados posibles de la instancia:**
- `RUNNABLE` → ✅ PASS
- `PENDING_CREATE`, `MAINTENANCE` → ⚠️ WARN
- `STOPPED`, `FAILED` → ❌ FAIL

```python
# Comando ejecutado
gcloud sql instances describe production-db --project my-project --format json

# Validación de IP
ip_addresses = data.get("ipAddresses", [])
has_private_ip = any(ip.get("type") == "PRIVATE" for ip in ip_addresses)
has_public_ip = any(ip.get("type") == "PRIMARY" for ip in ip_addresses)
```

---

### Fase 2: GKE Cluster

Valida la configuración del cluster de Kubernetes.

| Check | Descripción | Comando |
|-------|-------------|---------|
| **Cluster Exists** | Verifica existencia del cluster | `gcloud container clusters describe CLUSTER` |
| **Network Config** | Verifica VPC-native (alias IP) | Campo `ipAllocationPolicy` |
| **Workload Identity** | Verifica WI habilitado | Campo `workloadIdentityConfig` |

**Configuración de red requerida:**
```yaml
# VPC-native debe estar habilitado para IP privada de Cloud SQL
ipAllocationPolicy:
  useIpAliases: true
  clusterSecondaryRangeName: "pods"
  servicesSecondaryRangeName: "services"
```

---

### Fase 3: VPC & Private Service Connection

Valida la red VPC y la conexión de servicios privados.

| Check | Descripción | Comando |
|-------|-------------|---------|
| **VPC Network** | Verifica existencia de la VPC | `gcloud compute networks describe NETWORK` |
| **IP Ranges** | Rangos para servicios privados | `gcloud compute addresses list --filter="purpose=VPC_PEERING"` |
| **VPC Peering** | Peering con servicios de Google | `gcloud services vpc-peerings list` |

**Private Service Connection (PSC):**
```
┌─────────────────┐         ┌─────────────────┐
│   Tu VPC        │◀───────▶│  Google VPC     │
│  (10.0.0.0/16)  │ Peering │ (servicenetwork)│
└─────────────────┘         └─────────────────┘
         │                           │
         ▼                           ▼
   GKE Cluster               Cloud SQL (IP Privada)
```

---

### Fase 4: Firewall Rules

Valida las reglas de firewall para permitir el tráfico.

| Check | Descripción | Comando |
|-------|-------------|---------|
| **Egress Rules** | Reglas de salida al puerto SQL | `gcloud compute firewall-rules list --filter="network~NETWORK"` |

**Puertos requeridos:**
- PostgreSQL: `5432`
- MySQL: `3306`
- SQL Server: `1433`

**Ejemplo de regla requerida:**
```bash
gcloud compute firewall-rules create allow-sql-egress \
  --network=my-vpc \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:5432 \
  --destination-ranges=10.0.0.0/8 \
  --priority=1000
```

---

### Fase 5: IAM Permissions

Valida los permisos del Google Service Account (GSA).

| Check | Descripción | Comando |
|-------|-------------|---------|
| **SA Exists** | Verifica existencia del GSA | `gcloud iam service-accounts describe GSA_EMAIL` |
| **IAM Roles** | Verifica roles de Cloud SQL | `gcloud projects get-iam-policy PROJECT` |

**Roles requeridos para Cloud SQL:**
| Rol | Descripción |
|-----|-------------|
| `roles/cloudsql.client` | Conexión a Cloud SQL |
| `roles/cloudsql.instanceUser` | Autenticación IAM (opcional) |

```bash
# Comando de remediación
gcloud projects add-iam-policy-binding PROJECT \
  --member=serviceAccount:GSA_EMAIL \
  --role=roles/cloudsql.client
```

---

### Fase 6: Workload Identity Binding

Valida el binding entre Kubernetes Service Account (KSA) y Google Service Account (GSA).

| Check | Descripción | Comando |
|-------|-------------|---------|
| **KSA Annotation** | Anotación en el KSA | `kubectl get serviceaccount KSA -n NAMESPACE` |
| **GSA Binding** | Binding IAM en el GSA | `gcloud iam service-accounts get-iam-policy GSA_EMAIL` |

**Configuración de Workload Identity:**

```yaml
# 1. KSA con anotación
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: backend
  annotations:
    iam.gke.io/gcp-service-account: app@project.iam.gserviceaccount.com
```

```bash
# 2. Binding en el GSA
gcloud iam service-accounts add-iam-policy-binding \
  app@project.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:project.svc.id.goog[backend/app-sa]"
```

---

### Fase 7: Cloud SQL Auth Proxy (Opcional)

Verifica si hay un Cloud SQL Auth Proxy desplegado.

| Check | Descripción | Comando |
|-------|-------------|---------|
| **Proxy Deployment** | Pods con label cloud-sql-proxy | `kubectl get pods -l app=cloud-sql-proxy` |
| **Proxy Sidecar** | Contenedor sidecar en pods | Inspección de containers en pods |

**Modos de conexión:**
1. **IP Privada directa** → No requiere proxy
2. **Cloud SQL Proxy** → Requerido para IP pública o autenticación IAM

---

### Fase 8: Load Balancers & Services

Valida los servicios de Kubernetes que median la conectividad.

| Check | Descripción | Comando |
|-------|-------------|---------|
| **LoadBalancer Services** | Servicios tipo LoadBalancer | `kubectl get services -n NAMESPACE` |
| **GCP Forwarding Rules** | Reglas de balanceo en GCP | `gcloud compute forwarding-rules list` |
| **Backend Health** | Salud de los backends | `gcloud compute backend-services get-health` |
| **NEGs** | Network Endpoint Groups | `gcloud compute network-endpoint-groups list` |

**Tipos de servicios:**
- **LoadBalancer** → Crea Load Balancer externo en GCP
- **NodePort** → Expone puerto en cada nodo
- **ClusterIP** → Solo acceso interno

---

### Fase 9: Connectivity Test

Realiza una prueba de conectividad de red.

| Check | Descripción | Comando |
|-------|-------------|---------|
| **Network Test** | Test de conectividad GCP | `gcloud network-management connectivity-tests create` |

**Prueba manual desde un Pod:**
```bash
# Conectar a un pod
kubectl exec -it POD_NAME -n NAMESPACE -- /bin/sh

# Probar conectividad
nc -zv CLOUD_SQL_IP 5432
```

---

## Uso del Script

### Modo Simplificado (Recomendado)

Solo requiere el nombre del deployment y la instancia de Cloud SQL:

```bash
python connectivity-checker.py \
  --deployment my-app \
  --sql-instance my-database
```

El script descubre automáticamente:
- ✅ Project (de gcloud config)
- ✅ Cluster y Location (del contexto kubectl)
- ✅ Namespace (buscando el deployment)
- ✅ KSA (del spec del deployment)
- ✅ GSA (de la anotación del KSA)

### Modo Completo

Especifica todos los parámetros manualmente:

```bash
python connectivity-checker.py \
  --sql-instance my-database \
  --project my-project \
  --region us-central1 \
  --gke-cluster my-cluster \
  --gke-location us-central1 \
  --namespace backend \
  --ksa-name app-sa \
  --gsa-email app@my-project.iam.gserviceaccount.com \
  --verbose
```

### Parámetros

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--sql-instance, -s` | ✅ | Nombre de la instancia Cloud SQL |
| `--deployment, -d` | ❌ | Nombre del deployment (habilita discovery) |
| `--project, -p` | ❌ | ID del proyecto GCP |
| `--region, -r` | ❌ | Región de Cloud SQL |
| `--gke-cluster, -c` | ❌ | Nombre del cluster GKE |
| `--gke-location, -l` | ❌ | Ubicación del cluster |
| `--namespace, -n` | ❌ | Namespace de Kubernetes (default: "default") |
| `--ksa-name` | ❌ | Kubernetes Service Account |
| `--gsa-email` | ❌ | Google Service Account email |
| `--verbose, -v` | ❌ | Mostrar comandos ejecutados |

---

## Deploy Dependency Checker (ConfigMaps → Connections)

Nueva herramienta que inspecciona los ConfigMaps referenciados por un Deployment y valida las cadenas de conexión detectadas (JDBC / host:puerto) ejecutando pruebas TCP.

### Flujo
1. Obtiene el Deployment (`kubectl get deployment`) y detecta namespace + ServiceAccount.
2. Resuelve todos los ConfigMaps referenciados en `envFrom`, `env.valueFrom` y `volumes`.
3. Extrae posibles conexiones a BD e intenta conectarse a cada host:puerto.
4. Muestra una tabla Rich y puede exportar los resultados (`-o csv|json`) a `connectivity/outcome/`.

### Opciones Clave
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--project, -p` | `cpl-corp-cial-prod-17042024` | Proyecto donde reside el cluster |
| `--cluster, -c` | `gke-corp-cial-prod-01` | Nombre del cluster GKE |
| `--region, -r` | `us-central1` | Región del cluster GKE |
| `--deployment, -d` | `ds-ppm-pricing-discount` | Deployment objetivo |
| `--probe-mode` | `pod` | `pod`: crea un pod temporal dentro del namespace del deployment para emular la subnet de pods. `local`: usa sockets del host |
| `--probe-image` | `jrecord/nettools:latest` | Imagen utilizada para el pod temporal (incluye `nc`) |
| `--timeout` | `5` | Timeout en segundos para cada intento |

> Cuando `--probe-mode=pod`, el script crea `nettools-sre-<timestamp>` usando el mismo `serviceAccountName` del deployment para respetar NetworkPolicies/Workload Identity. Si falla la creación, cambia automáticamente a modo `local` y notifica un warning.

### Ejemplo (modo pod por defecto)

```bash
python deploy_dependency_checker.py \
  --project cpl-cs-wms-qa-30112023 \
  --cluster gke-cs-wms-qa-01 \
  --region us-central1 \
  --deployment bs-wms-preship-store \
  --namespace wms \
  --probe-mode pod \
  --output json
```

### Ejemplo (modo local manual)

```bash
python deploy_dependency_checker.py --deployment my-app --probe-mode local
```

### Requisitos
- `kubectl` con acceso al cluster/namespace.
- Imagen con utilidades de red (por defecto `jrecord/nettools`).
- Permisos para crear pods temporales en el namespace objetivo.

---

## Interpretación de Resultados

### Estados de Validación

| Estado | Símbolo | Significado |
|--------|---------|-------------|
| **PASS** | ✅ | Validación exitosa |
| **FAIL** | ❌ | Error crítico - requiere acción |
| **WARN** | ⚠️ | Advertencia - revisar |
| **INFO** | ℹ️ | Información - no requiere acción |
| **SKIP** | ⏭️ | Omitido - no aplica |

### Ejemplo de Salida

```
=======================================================================================================================================
                                               🔍 CLOUD SQL CONNECTIVITY CHECKER                                                       
=======================================================================================================================================

=======================================================================================================================================
#    SECCIÓN                   VALIDACIÓN                               ESTADO     MENSAJE                                           
=======================================================================================================================================
---------------------------------------------------------------------------------------------------------------------------------------
1    0. Discovery              Project Discovery                        ℹ️  INFO    Proyecto detectado: my-project                    
2    0. Discovery              Kubectl Context                          ℹ️  INFO    Contexto actual: gke_my-project_us-central1_cl... 
3    0. Discovery              GKE Context Parsed                       ✅ PASS    Cluster: my-cluster, Location: us-central1         
---------------------------------------------------------------------------------------------------------------------------------------
4    1. Cloud SQL              Cloud SQL Instance Exists                ✅ PASS    Instancia 'my-db' está activa (RUNNABLE)           
5    1. Cloud SQL              Cloud SQL IP Configuration               ✅ PASS    IP Privada está habilitada                         
---------------------------------------------------------------------------------------------------------------------------------------
...
=======================================================================================================================================
                    TOTAL: 25 | ✅ 20 | ❌ 0 | ⚠️  2 | ℹ️  3 | ⏭️  0                                                                     
=======================================================================================================================================
                                        ✅ TODAS LAS VALIDACIONES CRÍTICAS PASARON                                                      
=======================================================================================================================================
```

---

## Troubleshooting

### Errores Comunes

#### 1. "No se encontró el deployment"
```bash
# Verificar que el deployment existe
kubectl get deployments -A | grep DEPLOYMENT_NAME
```

#### 2. "Workload Identity no está habilitado"
```bash
# Habilitar Workload Identity en el cluster
gcloud container clusters update CLUSTER \
  --workload-pool=PROJECT.svc.id.goog \
  --location=LOCATION
```

#### 3. "Faltan roles IAM"
```bash
# Asignar rol de Cloud SQL client
gcloud projects add-iam-policy-binding PROJECT \
  --member=serviceAccount:GSA_EMAIL \
  --role=roles/cloudsql.client
```

#### 4. "Private Service Connection no establecida"
```bash
# Crear rangos de IP para servicios
gcloud compute addresses create google-managed-services-VPC \
  --global --purpose=VPC_PEERING \
  --prefix-length=16 --network=VPC_NAME

# Crear la conexión de servicios privados
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-VPC \
  --network=VPC_NAME
```

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-06-16 | 1.0.4 | `deployment_validator.py`: **Soporte para GCP Secret Manager** — (1) Nuevas funciones `parse_secret_manager_references` y `fetch_gcp_secret` para detectar y obtener secretos de GCP; (2) `ConnectionEndpoint` dataclass actualizado con campos `secret_project`, `secret_name`, `secret_version`, `sm_key`; (3) `validate_configmaps` procesa referencias a Secret Manager y extrae conexiones DB; (4) Tabla de conectividad con columna **Source** (🔐 SM / 🔑 K8s / 📋 CM); (5) CSV/JSON export incluyen campos de Secret Manager; (6) Soporte PyYAML opcional con fallback regex |
| 2026-06-16 | 1.0.5 | `deploy_dependency_checker.py`: **Soporte para GCP Secret Manager** — (1) Nueva función `parse_secret_manager_references` detecta referencias YAML a Secret Manager en ConfigMaps (formato: `secretManager.projectId`, `secrets.*.name`, `secrets.*.version`); (2) Nueva función `fetch_gcp_secret` obtiene valores de secretos vía `gcloud secrets versions access`; (3) `collect_connections` ahora procesa secretos referenciados y extrae conexiones DB del contenido JSON (`host`, `port`, `type`); (4) Nuevos campos en conexiones: `source_type` (configmap/secretmanager), `secret_project`, `secret_name`, `secret_version`, `sm_key`; (5) Tabla Rich con columna **Source** (🔐 SM / 📋 CM) cuando hay secretos; (6) CSV/JSON export incluyen campos de Secret Manager; (7) Soporte PyYAML opcional con fallback regex |
| 2026-05-18 | 1.2.1 | `README.md`: nueva sección **🗺️ Especialidad de Cada Herramienta** con descripción individual, cuadro comparativo de 13 características y tabla de decisión *¿Cuándo usar cada uno?* |
| 2026-05-18 | 1.2.1 | `pod_connectivity_checker.py`: (1) Nuevos imports `os`, `socket`, `timezone`; (2) `check_connectivity_test` ahora ejecuta primero un **TCP socket directo** (`socket.create_connection`) con latencia medida, reportado como `TCP Direct Connectivity` (PASS/FAIL real); el test de `gcloud network-management` pasa a secundario/INFO ya que requiere permisos adicionales; (3) nueva función `export_results` exporta metadata, summary (total/pass/fail/warn/info/skip/critical_ok) y lista de resultados; (4) nuevo flag `--output json|csv` para exportar a `outcome/pod_connectivity_<instance>_<ts>.<ext>`; versión `1.2.0 → 1.2.1` |
| 2026-05-18 | 1.0.1 | `deploy_dependency_checker.py`: (1) mismo **JDBC port bug fix** que `deployment_validator.py` — `DB_DEFAULT_PORTS` por engine en `parse_connection_values`; (2) nuevo flag `--db-probe` igual que `deployment_validator.py` — protocolo nativo PostgreSQL/MySQL/Redis vía `kubectl exec python3 -c`; (3) `export_results` JSON reestructurado con `metadata`, `summary` (tcp_ok/db_probe_alive/etc.) y `connections` con campos separados `tcp_status`/`db_probe_status`/`db_probe_message`; (4) CSV actualizado con nuevas columnas `tcp_status`, `db_probe_status`, `db_probe_message`; (5) tabla Rich condicional con columna **DB Probe**; (6) `print_summary_counts` muestra `DB ALIVE` / `DB FAIL` |
| 2026-05-18 | 1.0.1 | `deployment_validator.py`: (1) **Bug fix** — JDBC URLs sin puerto explícito (`jdbc:postgresql://host/db`) eran silenciosamente ignoradas por `parse_connection_string`; corregido usando `DB_DEFAULT_PORTS` por engine (PG=5432, MySQL=3306, etc.); (2) **Nueva feature** `--db-probe` — verificación nivel 2 con protocolo nativo del motor (PostgreSQL SSL-request, MySQL greeting, Redis PING) para detectar falsos positivos de load balancers; nuevos estados `DB_PROBE_FAIL` / `ALIVE` / `UNEXPECTED`; columna extra en tabla de conectividad y en JSON/CSV exportado |
| 2026-03-26 | 1.4.0 | Agregar `--cluster` y `--region` a deployment_validator.py y deploy_dependency_checker.py para configurar contexto kubectl automáticamente |
| 2026-03-09 | 1.3.0 | Nuevo deploy_dependency_checker.py con `--probe-mode` (default pod) para validar dependencias de ConfigMaps y conexiones DB |
| 2026-02-19 | 1.2.0 | Validación de conexión GCP al inicio, renombrado a pod_connectivity_checker.py |
| 2026-02-16 | 1.1.0 | Timezone configurable con America/Mazatlan como default |
| 2025-12-01 | 1.0.0 | Versión inicial |

---

## Autor

**Harold Adrian**

---

## Licencia

Internal SRE Tool - Softtek
