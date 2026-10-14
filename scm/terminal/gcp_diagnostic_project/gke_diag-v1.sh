#!/usr/bin/env bash
# gke_diag.sh - Diagnóstico de solo lectura de GKE (puntos 1 a 4)
# Uso: ./gke_diag.sh PROJECT_ID [DIRECTORIO_SALIDA]
# Requiere: gcloud, kubectl (con gke-gcloud-auth-plugin)

set -uo pipefail

PROJECT_ID="${1:-}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Uso: $0 PROJECT_ID [DIRECTORIO_SALIDA]" >&2
  exit 1
fi

OUT="${2:-gke-diag-${PROJECT_ID}-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"
SUMMARY="$OUT/00_resumen.log"
SEEN_SUBNETS="$OUT/.subnets_vistas"
: > "$SUMMARY"; : > "$SEEN_SUBNETS"

# kubeconfig temporal: NO toca tu ~/.kube/config
export KUBECONFIG="$OUT/.kubeconfig"
KUBECTL_TIMEOUT="30s"

for bin in gcloud kubectl; do
  command -v "$bin" >/dev/null || { echo "Falta $bin en el PATH" >&2; exit 1; }
done

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUMMARY"; }

# run ARCHIVO cmd args...  -> guarda stdout+stderr; registra si falla
run() {
  local file="$1"; shift
  if ! "$@" > "$file" 2>&1; then
    log "  WARN: falló (ver $file): $*"
    return 1
  fi
}

k() { kubectl --request-timeout="$KUBECTL_TIMEOUT" "$@"; }

log "Proyecto: $PROJECT_ID | Salida: $OUT"

# ---------- 1. Descubrir clústeres ----------
run "$OUT/01_clusters_list.txt" \
  gcloud container clusters list --project="$PROJECT_ID" || { log "No se pudo listar clústeres"; exit 1; }

mapfile -t CLUSTERS < <(gcloud container clusters list --project="$PROJECT_ID" \
  --format="value(name,location)" 2>/dev/null)

if [[ ${#CLUSTERS[@]} -eq 0 ]]; then
  log "No se encontraron clústeres en $PROJECT_ID"; exit 0
fi
log "Clústeres encontrados: ${#CLUSTERS[@]}"

for entry in "${CLUSTERS[@]}"; do
  CLUSTER="$(awk '{print $1}' <<< "$entry")"
  LOCATION="$(awk '{print $2}' <<< "$entry")"
  CDIR="$OUT/$CLUSTER"; mkdir -p "$CDIR"
  log "=== Clúster: $CLUSTER ($LOCATION) ==="

  # ---------- 2. Clúster y nodepools ----------
  run "$CDIR/02_cluster_describe.yaml" \
    gcloud container clusters describe "$CLUSTER" --project="$PROJECT_ID" --location="$LOCATION" --format=yaml

  run "$CDIR/02_nodepools_list.txt" \
    gcloud container node-pools list --cluster="$CLUSTER" --project="$PROJECT_ID" --location="$LOCATION"

  mapfile -t POOLS < <(gcloud container node-pools list --cluster="$CLUSTER" \
    --project="$PROJECT_ID" --location="$LOCATION" --format="value(name)" 2>/dev/null)

  mkdir -p "$CDIR/nodepools"
  for POOL in "${POOLS[@]}"; do
    [[ -z "$POOL" ]] && continue
    log "  Pool: $POOL"
    run "$CDIR/nodepools/${POOL}.yaml" \
      gcloud container node-pools describe "$POOL" --cluster="$CLUSTER" \
      --project="$PROJECT_ID" --location="$LOCATION" --format=yaml
  done

  # Operaciones recientes de ESTE clúster
  run "$CDIR/02_operations.txt" \
    gcloud container operations list --project="$PROJECT_ID" --location="$LOCATION" \
    --filter="targetLink:$CLUSTER"

  # ---------- 3. Red / IP ----------
  # Formato típico: projects/NET_PROJECT/regions/REGION/subnetworks/NAME
  SUBNET_PATH="$(gcloud container clusters describe "$CLUSTER" --project="$PROJECT_ID" \
    --location="$LOCATION" --format="value(networkConfig.subnetwork)" 2>/dev/null)"
  [[ -z "$SUBNET_PATH" ]] && SUBNET_PATH="$(gcloud container clusters describe "$CLUSTER" \
    --project="$PROJECT_ID" --location="$LOCATION" --format="value(subnetwork)" 2>/dev/null)"

  if [[ "$SUBNET_PATH" == projects/*/regions/*/subnetworks/* ]]; then
    NET_PROJECT="$(cut -d/ -f2 <<< "$SUBNET_PATH")"
    SUBNET_REGION="$(cut -d/ -f4 <<< "$SUBNET_PATH")"
    SUBNET_NAME="$(cut -d/ -f6 <<< "$SUBNET_PATH")"
  else
    NET_PROJECT="$PROJECT_ID"
    SUBNET_NAME="$SUBNET_PATH"
    # Si la ubicación es zona (us-central1-a) se convierte en región
    SUBNET_REGION="$(sed -E 's/-[a-z]$//' <<< "$LOCATION")"
  fi

  KEY="$NET_PROJECT/$SUBNET_REGION/$SUBNET_NAME"
  if [[ -n "$SUBNET_NAME" ]] && ! grep -qxF "$KEY" "$SEEN_SUBNETS"; then
    echo "$KEY" >> "$SEEN_SUBNETS"
    mkdir -p "$OUT/subnets"
    log "  Subred: $KEY"
    run "$OUT/subnets/${NET_PROJECT}_${SUBNET_REGION}_${SUBNET_NAME}.yaml" \
      gcloud compute networks subnets describe "$SUBNET_NAME" \
      --project="$NET_PROJECT" --region="$SUBNET_REGION" --format=yaml
  fi

  # ---------- 4. kubectl ----------
  log "  Obteniendo credenciales (kubeconfig temporal)"
  if ! gcloud container clusters get-credentials "$CLUSTER" --project="$PROJECT_ID" \
        --location="$LOCATION" > "$CDIR/04_get_credentials.log" 2>&1; then
    log "  WARN: sin credenciales para $CLUSTER; se omiten comprobaciones kubectl"
    continue
  fi
  if ! k get --raw=/readyz > /dev/null 2>&1 && ! k get nodes > /dev/null 2>&1; then
    log "  WARN: API de $CLUSTER inaccesible (¿clúster privado / red autorizada?); se omite kubectl"
    continue
  fi

  K="$CDIR/kubectl"; mkdir -p "$K"

  run "$K/nodes_wide.txt"        k get nodes -o wide
  run "$K/top_nodes.txt"         k top nodes
  run "$K/top_pods_containers.txt" k top pods --all-namespaces --containers

  run "$K/nodes_allocatable.txt" k get nodes -o custom-columns=\
'NODE:.metadata.name,POOL:.metadata.labels.cloud\.google\.com/gke-nodepool,CPU_ALLOC:.status.allocatable.cpu,MEM_ALLOC:.status.allocatable.memory,PODS_ALLOC:.status.allocatable.pods,POD_CIDRS:.spec.podCIDRs'

  # Pods por nodo
  run "$K/pods_por_nodo.txt" bash -c \
    "kubectl --request-timeout=$KUBECTL_TIMEOUT get pods -A -o custom-columns=NODE:.spec.nodeName --no-headers | sort | uniq -c | sort -rn"

  # Describe de nodos por pool (Allocated resources, condiciones, eventos)
  mkdir -p "$K/describe_nodes_por_pool"
  mapfile -t KPOOLS < <(k get nodes -o jsonpath='{range .items[*]}{.metadata.labels.cloud\.google\.com/gke-nodepool}{"\n"}{end}' 2>/dev/null | sort -u)
  for KP in "${KPOOLS[@]}"; do
    [[ -z "$KP" ]] && continue
    run "$K/describe_nodes_por_pool/${KP}.txt" \
      k describe nodes -l "cloud.google.com/gke-nodepool=$KP"
  done
  # Resumen rápido de recursos asignados
  run "$K/allocated_resources_resumen.txt" bash -c \
    "kubectl --request-timeout=$KUBECTL_TIMEOUT describe nodes | grep -E '^Name:|Allocated resources|  cpu |  memory |MemoryPressure|DiskPressure|PIDPressure'"

  # Pods problemáticos
  run "$K/pods_pending.txt" k get pods -A --field-selector=status.phase=Pending -o wide
  run "$K/pods_failed.txt"  k get pods -A --field-selector=status.phase=Failed -o wide
  run "$K/pods_no_running.txt" bash -c \
    "kubectl --request-timeout=$KUBECTL_TIMEOUT get pods -A --no-headers | awk '\$4!=\"Running\" && \$4!=\"Completed\"'"
  run "$K/pods_ultimo_estado.txt" k get pods -A -o custom-columns=\
'NS:.metadata.namespace,POD:.metadata.name,RESTARTS:.status.containerStatuses[*].restartCount,LAST_REASON:.status.containerStatuses[*].lastState.terminated.reason,NODE:.spec.nodeName'
  run "$K/pods_oomkilled.txt" bash -c \
    "grep -E 'OOMKilled' '$K/pods_ultimo_estado.txt' || echo 'Sin OOMKilled en último estado'"

  # Eventos, PDB, HPA, DaemonSets, quotas, limitranges
  run "$K/events.txt"      k get events -A --sort-by=.metadata.creationTimestamp
  run "$K/events_warning.txt" k get events -A --field-selector=type=Warning --sort-by=.metadata.creationTimestamp
  run "$K/pdb.txt"         k get pdb -A
  run "$K/hpa.txt"         k get hpa -A
  run "$K/daemonsets.txt"  k get daemonsets -A
  run "$K/resourcequotas.txt" k get resourcequota -A
  run "$K/limitranges.txt" k get limitrange -A

  # Detalle de pods con reinicios > 0 (describe + logs previos, acotado)
  mkdir -p "$K/pods_con_reinicios"
  while read -r NS POD RESTARTS; do
    [[ -z "${POD:-}" || "$RESTARTS" == "0" || "$RESTARTS" == "<​none>" ]] && continue
    FIRST="${RESTARTS%%,*}"
    [[ "$FIRST" =~ ^[0-9]+$ && "$FIRST" -gt 0 ]] || continue
    run "$K/pods_con_reinicios/${NS}__${POD}.describe.txt" k describe pod "$POD" -n "$NS"
    k logs "$POD" -n "$NS" --all-containers --previous --tail=100 \
      > "$K/pods_con_reinicios/${NS}__${POD}.logs_previos.txt" 2>&1 || true
  done < <(k get pods -A --no-headers -o custom-columns='NS:.metadata.namespace,POD:.metadata.name,R:.status.containerStatuses[*].restartCount' 2>/dev/null)

  log "  Clúster $CLUSTER completado"
done

# Limpieza del kubeconfig temporal
rm -f "$KUBECONFIG"

log "Listo. Resultados en: $OUT"
