#!/usr/bin/env bash
# gke_diag.sh - Diagnóstico de SOLO LECTURA de GKE (descubrimiento + recursos + red)
# Uso:   ./gke_diag.sh PROJECT_ID [DIRECTORIO_SALIDA]
# Vars opcionales:
#   CMD_TIMEOUT=90        segundos máx. por comando gcloud/kubectl
#   CRED_TIMEOUT=60       segundos máx. para get-credentials
#   API_TIMEOUT=20        segundos máx. para el pre-chequeo de la API
#   SKIP_KUBECTL=1        solo gcloud, sin kubectl
#   ONLY_CLUSTER=nombre   procesa solo ese clúster
#   FORCE_INTERNAL_IP=1   fuerza --internal-ip en get-credentials
#   MAX_RESTART_PODS=10   máx. de pods con reinicios a detallar

set -uo pipefail

PROJECT_ID="${1:-}"
[[ -z "$PROJECT_ID" ]] && { echo "Uso: $0 PROJECT_ID [DIRECTORIO_SALIDA]" >&2; exit 1; }

CMD_TIMEOUT="${CMD_TIMEOUT:-90}"
CRED_TIMEOUT="${CRED_TIMEOUT:-60}"
API_TIMEOUT="${API_TIMEOUT:-20}"
SKIP_KUBECTL="${SKIP_KUBECTL:-0}"
ONLY_CLUSTER="${ONLY_CLUSTER:-}"
FORCE_INTERNAL_IP="${FORCE_INTERNAL_IP:-0}"
MAX_RESTART_PODS="${MAX_RESTART_PODS:-10}"

# --- Modo no interactivo ---
export CLOUDSDK_CORE_DISABLE_PROMPTS=1
export CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK=1
export CLOUDSDK_CORE_DISABLE_USAGE_REPORTING=true
export USE_GKE_GCLOUD_AUTH_PLUGIN=True

# --- timeout (Linux) o gtimeout (macOS: brew install coreutils) ---
if command -v timeout >/dev/null; then TMO=timeout
elif command -v gtimeout >/dev/null; then TMO=gtimeout
else echo "Falta 'timeout' (macOS: brew install coreutils)" >&2; exit 1; fi

for bin in gcloud kubectl; do
  command -v "$bin" >/dev/null || { echo "Falta $bin en el PATH" >&2; exit 1; }
done

OUT="${2:-gke-diag-${PROJECT_ID}-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT/subnets"
SUMMARY="$OUT/00_resumen.log";        : > "$SUMMARY"
CAPACITY="$OUT/99_capacidad.txt";     : > "$CAPACITY"
SEEN_SUBNETS="$OUT/.subnets_vistas";  : > "$SEEN_SUBNETS"
KCFG_DIR="$OUT/.kubeconfigs";         mkdir -p "$KCFG_DIR"

cleanup() { rm -rf "$KCFG_DIR"; }
trap cleanup EXIT
trap 'echo; echo "Interrumpido por el usuario" | tee -a "$SUMMARY"; exit 130' INT TERM

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUMMARY" >&2; }

# run_t SEGUNDOS ARCHIVO cmd...  -> stdout+stderr a ARCHIVO; sin stdin; nunca excede SEGUNDOS
# IMPORTANTE: cmd debe ser un binario (no una función de bash), porque pasa por timeout.
run_t() {
  local secs="$1" file="$2"; shift 2
  local start rc cmdline el
  start=$(date +%s)
  cmdline="$*"
  log "    -> ${cmdline:0:160}"
  "$TMO" -k 5 "$secs" "$@" > "$file" 2>&1 < /dev/null
  rc=$?
  el=$(( $(date +%s) - start ))
  if   [[ $rc -eq 0 ]];                  then log "       OK (${el}s)"
  elif [[ $rc -eq 124 || $rc -eq 137 ]]; then log "       TIMEOUT tras ${secs}s -> $file"
  else                                        log "       FALLÓ rc=$rc (${el}s) -> $file"; fi
  return $rc
}
run() { local f="$1"; shift; run_t "$CMD_TIMEOUT" "$f" "$@"; }

# q SEGUNDOS cmd... -> imprime stdout (sin stderr); vacío si falla/expira
q() { local secs="$1"; shift; "$TMO" -k 5 "$secs" "$@" 2>/dev/null < /dev/null; }

log "Proyecto: $PROJECT_ID | Salida: $OUT | timeout/cmd: ${CMD_TIMEOUT}s"

if ! command -v gke-gcloud-auth-plugin >/dev/null; then
  log "WARN: falta gke-gcloud-auth-plugin (gcloud components install gke-gcloud-auth-plugin). kubectl probablemente fallará."
fi

# ---------------------------------------------------------------- Descubrimiento
run "$OUT/01_clusters_list.txt" gcloud container clusters list --project="$PROJECT_ID"
CLUSTERS=$(q "$CMD_TIMEOUT" gcloud container clusters list --project="$PROJECT_ID" \
            --format="value(name,location)")
if [[ -z "$CLUSTERS" ]]; then
  log "No se encontraron clústeres (o sin permisos container.clusters.list). Fin."
  exit 0
fi
log "Clústeres encontrados: $(echo "$CLUSTERS" | wc -l | tr -d ' ')"

# Calcula capacidad del rango de pods: nodos_posibles = 2^(podIpv4CidrSize - prefijo_rango)
capacity_line() {
  local cluster="$1" pool="$2" cidr="$3" size="$4" maxpods="$5" nodes="$6"
  local prefix posibles
  if [[ -n "$cidr" && -n "$size" ]]; then
    prefix="${cidr#*/}"
    posibles=$(( 1 << (size - prefix) ))
    printf '%s | pool=%s | rango=%s | /%s por nodo | maxPods=%s | nodos_posibles=%s | nodos_actuales=%s%s\n' \
      "$cluster" "$pool" "$cidr" "$size" "$maxpods" "$posibles" "${nodes:-?}" \
      "$([[ "${nodes:-0}" =~ ^[0-9]+$ && "$nodes" -ge "$posibles" ]] && echo '  <-- RANGO AGOTADO')" >> "$CAPACITY"
  else
    printf '%s | pool=%s | rango de pods no determinado\n' "$cluster" "$pool" >> "$CAPACITY"
  fi
}

while IFS=$'\t' read -r CLUSTER LOC; do
  [[ -z "$CLUSTER" ]] && continue
  [[ -n "$ONLY_CLUSTER" && "$CLUSTER" != "$ONLY_CLUSTER" ]] && continue

  log "=== Clúster: $CLUSTER ($LOC) ==="
  CD="$OUT/$CLUSTER"; K="$CD/kubectl"
  mkdir -p "$CD/nodepools" "$K/describe_nodes_por_pool" "$K/pods_con_reinicios"

  run "$CD/02_cluster_describe.yaml" gcloud container clusters describe "$CLUSTER" \
      --project="$PROJECT_ID" --location="$LOC" --format=yaml
  run "$CD/02_nodepools_list.txt" gcloud container node-pools list --cluster="$CLUSTER" \
      --project="$PROJECT_ID" --location="$LOC"
  run "$CD/02_operations.txt" gcloud container operations list --project="$PROJECT_ID" \
      --location="$LOC" --filter="targetLink:$CLUSTER"

  POOLS=$(q "$CMD_TIMEOUT" gcloud container node-pools list --cluster="$CLUSTER" \
          --project="$PROJECT_ID" --location="$LOC" --format="value(name)")
  PRIVATE_EP=$(q "$CMD_TIMEOUT" gcloud container clusters describe "$CLUSTER" \
          --project="$PROJECT_ID" --location="$LOC" \
          --format="value(privateClusterConfig.enablePrivateEndpoint)")

  # Nº de nodos actuales (se completa luego con kubectl si hay acceso)
  NODES_NOW=""

  # ---- Nodepools + subredes
  declare -A POOL_INFO=()
  for POOL in $POOLS; do
    log "  Pool: $POOL"
    PF="$CD/nodepools/$POOL.yaml"
    run "$PF" gcloud container node-pools describe "$POOL" --cluster="$CLUSTER" \
        --project="$PROJECT_ID" --location="$LOC" --format=yaml

    SUBNET_URL=$(grep -m1 -E '^\s*subnetwork:' "$PF" | sed -E 's/.*subnetwork:\s*//')
    POD_CIDR=$(grep -m1 -E 'podIpv4CidrBlock:' "$PF" | sed -E 's/.*:\s*//')
    POD_SIZE=$(grep -m1 -E '^podIpv4CidrSize:' "$PF" | sed -E 's/.*:\s*//')
    MAXPODS=$(grep -m1 -E 'maxPodsPerNode:' "$PF" | sed -E "s/.*:\s*'?([0-9]+)'?.*/\1/")
    POOL_INFO["$POOL"]="$POD_CIDR|$POD_SIZE|$MAXPODS"

    if [[ -n "$SUBNET_URL" ]]; then
      NET_PROJECT=$(echo "$SUBNET_URL" | sed -E 's|.*/projects/([^/]+)/.*|\1|')
      SUBNET_REGION=$(echo "$SUBNET_URL" | sed -E 's|.*/regions/([^/]+)/.*|\1|')
      SUBNET_NAME=$(echo "$SUBNET_URL" | sed -E 's|.*/subnetworks/||')
      KEY="${NET_PROJECT}_${SUBNET_REGION}_${SUBNET_NAME}"
      if ! grep -qxF "$KEY" "$SEEN_SUBNETS"; then
        echo "$KEY" >> "$SEEN_SUBNETS"
        log "  Subred: $NET_PROJECT/$SUBNET_REGION/$SUBNET_NAME"
        if ! run "$OUT/subnets/$KEY.yaml" gcloud compute networks subnets describe "$SUBNET_NAME" \
              --project="$NET_PROJECT" --region="$SUBNET_REGION" --format=yaml; then
          log "  Sin permiso directo; probando list-usable (se filtra localmente)"
          run "$OUT/subnets/$KEY.usable_all.txt" gcloud compute networks subnets list-usable \
              --project="$NET_PROJECT" --format=yaml
          grep -B3 -A12 "$SUBNET_NAME" "$OUT/subnets/$KEY.usable_all.txt" \
              > "$OUT/subnets/$KEY.usable.txt" 2>/dev/null || \
              echo "Sin datos para $SUBNET_NAME en list-usable" > "$OUT/subnets/$KEY.usable.txt"
        fi
      fi
    fi
  done

  # ---- kubectl
  if [[ "$SKIP_KUBECTL" == "1" ]]; then
    log "  SKIP_KUBECTL=1: se omite kubectl"
  else
    KCFG="$KCFG_DIR/$CLUSTER.kubeconfig"
    CRED_ARGS=(gcloud container clusters get-credentials "$CLUSTER" --project="$PROJECT_ID" --location="$LOC")
    if [[ "$PRIVATE_EP" == "True" || "$FORCE_INTERNAL_IP" == "1" ]]; then
      CRED_ARGS+=(--internal-ip)
      log "  Endpoint privado: usando --internal-ip (requiere ruta de red/VPN)"
    fi
    run_t "$CRED_TIMEOUT" "$CD/04_get_credentials.log" env KUBECONFIG="$KCFG" "${CRED_ARGS[@]}"
    KC=(kubectl --kubeconfig="$KCFG" --request-timeout=30s)

    if run_t "$API_TIMEOUT" "$CD/04_api_check.log" "${KC[@]}" get --raw=/readyz; then
      run "$K/nodes_wide.txt"  "${KC[@]}" get nodes -o wide
      run "$K/top_nodes.txt"   "${KC[@]}" top nodes
      run "$K/top_pods_containers.txt" "${KC[@]}" top pods --all-namespaces --containers
      run "$K/nodes_allocatable.txt" "${KC[@]}" get nodes -o \
          'custom-columns=NODE:.metadata.name,POOL:.metadata.labels.cloud\.google\.com/gke-nodepool,CPU_ALLOC:.status.allocatable.cpu,MEM_ALLOC:.status.allocatable.memory,PODS_ALLOC:.status.allocatable.pods,POD_CIDRS:.spec.podCIDRs'
      run "$K/describe_nodes_todos.txt" "${KC[@]}" describe nodes
      for POOL in $POOLS; do
        run "$K/describe_nodes_por_pool/$POOL.txt" "${KC[@]}" describe nodes \
            -l "cloud.google.com/gke-nodepool=$POOL"
      done
      run "$K/pods_pending.txt" "${KC[@]}" get pods -A --field-selector=status.phase=Pending -o wide
      run "$K/pods_failed.txt"  "${KC[@]}" get pods -A --field-selector=status.phase=Failed -o wide
      run "$K/.pods_all.txt"    "${KC[@]}" get pods -A --no-headers
      run "$K/pods_ultimo_estado.txt" "${KC[@]}" get pods -A -o \
          'custom-columns=NS:.metadata.namespace,POD:.metadata.name,RESTARTS:.status.containerStatuses[*].restartCount,LAST_REASON:.status.containerStatuses[*].lastState.terminated.reason,NODE:.spec.nodeName'
      run "$K/events.txt"         "${KC[@]}" get events -A --sort-by=.metadata.creationTimestamp
      run "$K/events_warning.txt" "${KC[@]}" get events -A --field-selector=type=Warning --sort-by=.metadata.creationTimestamp
      run "$K/pdb.txt"            "${KC[@]}" get pdb -A
      run "$K/hpa.txt"            "${KC[@]}" get hpa -A
      run "$K/daemonsets.txt"     "${KC[@]}" get daemonsets -A
      run "$K/resourcequotas.txt" "${KC[@]}" get resourcequota -A
      run "$K/limitranges.txt"    "${KC[@]}" get limitrange -A

      # ---- Post-procesamiento LOCAL (sin más llamadas a la API, salvo describe acotado)
      grep -E 'OOMKilled' "$K/pods_ultimo_estado.txt" > "$K/pods_oomkilled.txt" 2>/dev/null || true

      awk '/^Name:/{n=$2} /^Allocated resources:/{f=1}
           f && /^  cpu /{c=$2" "$3}
           f && /^  memory /{print n, "cpu_req="c, "mem_req="$2" "$3; f=0}' \
          "$K/describe_nodes_todos.txt" > "$K/allocated_resources_resumen.txt" 2>/dev/null || true

      NODES_NOW=$(grep -c . "$K/nodes_wide.txt" 2>/dev/null || echo 0)
      NODES_NOW=$(( NODES_NOW > 0 ? NODES_NOW - 1 : 0 ))   # quita cabecera

      # Pods con más reinicios (excluye los de DaemonSets repetidos solo por límite N)
      awk '$5+0>0 {print $5, $1, $2}' "$K/.pods_all.txt" 2>/dev/null \
        | sort -rn | head -n "$MAX_RESTART_PODS" > "$K/pods_top_reinicios.txt"
      while read -r RST NS POD; do
        [[ -z "$POD" ]] && continue
        run "$K/pods_con_reinicios/${NS}_${POD}.txt" "${KC[@]}" describe pod -n "$NS" "$POD"
      done < "$K/pods_top_reinicios.txt"
    else
      log "  WARN: API inaccesible (endpoint privado sin ruta/VPN, red autorizada, plugin o permisos)."
      log "        Ver $CD/04_api_check.log. Se omite kubectl para este clúster."
    fi
  fi

  # ---- Capacidad del rango de pods
  for POOL in "${!POOL_INFO[@]}"; do
    IFS='|' read -r PC PS PM <<< "${POOL_INFO[$POOL]}"
    capacity_line "$CLUSTER" "$POOL" "$PC" "$PS" "$PM" "$NODES_NOW"
  done
  unset POOL_INFO
  log "  Clúster $CLUSTER completado"
done <<< "$CLUSTERS"

log "=== Resumen de capacidad del rango de pods (ver $CAPACITY) ==="
cat "$CAPACITY" | tee -a "$SUMMARY" >&2
log "Diagnóstico completo. Salida en: $OUT"
log "Empaquetar: zip -r ${OUT}.zip $OUT"
