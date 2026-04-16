#!/bin/bash
# =============================================================================
# Script: generar-inventario-csv.sh
# Versión paralela - Procesa proyectos en hilos concurrentes
# Cada hilo usa su propio KUBECONFIG para evitar conflictos
# =============================================================================

set -euo pipefail

# === RUTAS ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/generar-inventario-csv.config"
OUTCOME_DIR="${SCRIPT_DIR}/outcome"
DELIMITER=";"
MAX_PARALLEL=4

# Función para mostrar tiempo
format_time() {
  local seconds=$1
  if [ "$seconds" -ge 60 ]; then
    printf "%dm %ds" $((seconds / 60)) $((seconds % 60))
  else
    printf "%ds" "$seconds"
  fi
}

usage() {
  echo "Uso: ./generar-inventario-csv.sh [opciones] [PROYECTO1 ...]"
  echo ""
  echo "Opciones:"
  echo "  --delimiter=CHAR   Separador CSV (default: ;)"
  echo "  --threads=N        Hilos paralelos (default: 4)"
  echo "  --sequential       Deshabilitar paralelismo"
  echo ""
  echo "Config : ${CONFIG_FILE}"
  echo "Output : ${OUTCOME_DIR}/"
  exit 1
}

# Procesar argumentos
PROJECTS=()
SEQUENTIAL=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --delimiter=*) DELIMITER="${1#*=}"; shift ;;
    --delimiter)   DELIMITER="$2"; shift 2 ;;
    --threads=*)   MAX_PARALLEL="${1#*=}"; shift ;;
    --threads)     MAX_PARALLEL="$2"; shift 2 ;;
    --sequential)  SEQUENTIAL=true; shift ;;
    -*) echo "Opción desconocida: $1"; usage ;;
    *) PROJECTS+=("$1"); shift ;;
  esac
done

# Leer namespaces excluidos del config
EXCLUDE_NS=()
EXCLUDE_PATTERN=""
if [ -f "$CONFIG_FILE" ]; then
  in_exclude=false
  while IFS= read -r line || [ -n "$line" ]; do
    line_clean=$(echo "$line" | sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')
    [ -z "$line_clean" ] && continue
    if [ "$line_clean" = "[exclude-namespaces]" ]; then
      in_exclude=true
      continue
    fi
    if [[ "$line_clean" == [* ]]; then
      in_exclude=false
      continue
    fi
    if $in_exclude; then
      EXCLUDE_NS+=("$line_clean")
    fi
  done < "$CONFIG_FILE"
  if [ ${#EXCLUDE_NS[@]} -gt 0 ]; then
    EXCLUDE_PATTERN=$(IFS='|'; echo "${EXCLUDE_NS[*]}")
    export EXCLUDE_PATTERN
  fi
fi

if [ ${#PROJECTS[@]} -eq 0 ]; then
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: No se encontró $CONFIG_FILE"
    usage
  fi
  echo "Leyendo proyectos desde: $CONFIG_FILE"
  in_exclude=false
  while IFS= read -r line || [ -n "$line" ]; do
    line=$(echo "$line" | sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')
    [ -z "$line" ] && continue
    # Skip [exclude-namespaces] section lines
    if [ "$line" = "[exclude-namespaces]" ]; then
      in_exclude=true
      continue
    fi
    if [[ "$line" == [* ]]; then
      in_exclude=false
      continue
    fi
    $in_exclude && continue
    PROJECTS+=("$line")
  done < "$CONFIG_FILE"
fi

mkdir -p "$OUTCOME_DIR"

START_TOTAL=$(date +%s)

echo "========================================================"
echo "INVENTARIO GKE + CLOUD SQL - CSV"
echo "Separador       : '$DELIMITER'"
echo "Proyectos       : ${PROJECTS[*]}"
echo "NS excluidos    : ${EXCLUDE_NS[*]}"
echo "Hilos           : $MAX_PARALLEL"
echo "Output          : $OUTCOME_DIR"
echo "========================================================"

# =============================================================================
# Función auxiliar: filtrar namespaces excluidos de stdin a stdout
# =============================================================================
filter_ns() {
  if [ -n "$EXCLUDE_PATTERN" ]; then
    grep -vE "^[[:space:]]*(${EXCLUDE_PATTERN})[[:space:]]" || true
  else
    cat
  fi
}

# =============================================================================
# Función: procesar un proyecto (se ejecuta en background si paralelo)
# =============================================================================
process_project() {
  local PROJECT_ID="$1"
  local DELIM="$2"

  # KUBECONFIG aislado por proyecto (evita conflictos entre hilos)
  local KUBECONFIG="/tmp/kubeconfig-inventario-${PROJECT_ID}-$$"
  export KUBECONFIG

  local PROJECT_START=$(date +%s)
  local TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
  local PROJECT_OUT_DIR="${OUTCOME_DIR}/inventario-${PROJECT_ID}-${TIMESTAMP}"
  mkdir -p "$PROJECT_OUT_DIR"

  echo ""
  echo "▶ [$PROJECT_ID] Iniciando..."
  echo "------------------------------------------------"

  # 1. Clusters GKE (JSON → Python csv.writer para CSV robusto)
  local SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] clusters.csv"
  gcloud container clusters list --project="$PROJECT_ID" --format=json --quiet 2>/dev/null | \
    DELIM="$DELIM" python3 -c "
import json,sys,csv,os
w=csv.writer(sys.stdout,delimiter=os.environ['DELIM'],quoting=csv.QUOTE_ALL)
w.writerow(['NAME','LOCATION','VERSION','CURRENT_VERSION','STATUS','MACHINE_TYPE'])
try:
 data=sys.stdin.read().strip()
 if data:
  d=json.loads(data)
  for c in d:
   ps=c.get('nodePools') or []
   mt='|'.join(p.get('config',{}).get('machineType','') for p in ps)
   w.writerow([c.get('name',''),c.get('location',''),c.get('currentMasterVersion',''),c.get('currentMasterVersion',''),c.get('status',''),mt])
except: pass
" > "$PROJECT_OUT_DIR/clusters.csv"
  echo "   └─ [$PROJECT_ID] clusters: $(format_time $(( $(date +%s) - SECTION_START )))"

  # 2. Deployments
  SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] deployments.csv"
  echo "NAMESPACE${DELIM}CLUSTER${DELIM}DEPLOYMENT${DELIM}IMAGES" > "$PROJECT_OUT_DIR/deployments.csv"

  local CLUSTERS=$(gcloud container clusters list --project="$PROJECT_ID" --format="value(name,location)" --quiet 2>/dev/null || true)

  if [ -n "$CLUSTERS" ]; then
    echo "$CLUSTERS" | while read -r CLUSTER LOCATION; do
      gcloud container clusters get-credentials "$CLUSTER" --location="$LOCATION" --project="$PROJECT_ID" --quiet >/dev/null 2>&1

      kubectl get deployments --all-namespaces \
        -o custom-columns="NAMESPACE:.metadata.namespace,DEPLOYMENT:.metadata.name,IMAGES:.spec.template.spec.containers[*].image" \
        --no-headers 2>/dev/null | filter_ns | \
        while read -r ns deploy images; do
          images_clean=$(echo "$images" | sed 's/,/;/g' | sed 's/"//g')
          printf '"%s"%s"%s"%s"%s"%s"%s"\n' "$ns" "$DELIM" "$CLUSTER" "$DELIM" "$deploy" "$DELIM" "$images_clean" \
            >> "$PROJECT_OUT_DIR/deployments.csv"
        done || true
    done
  fi
  echo "   └─ [$PROJECT_ID] deployments: $(format_time $(( $(date +%s) - SECTION_START )))"

  # 3. Services
  SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] services.csv"
  echo "NAMESPACE${DELIM}CLUSTER${DELIM}NAME${DELIM}TYPE${DELIM}CLUSTER-IP${DELIM}EXTERNAL-IP${DELIM}PORTS" > "$PROJECT_OUT_DIR/services.csv"

  if [ -n "$CLUSTERS" ]; then
    echo "$CLUSTERS" | while read -r CLUSTER LOCATION; do
      gcloud container clusters get-credentials "$CLUSTER" --location="$LOCATION" --project="$PROJECT_ID" --quiet >/dev/null 2>&1

      kubectl get services --all-namespaces \
        -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,EXTERNAL-IP:.status.loadBalancer.ingress[*].ip,PORTS:.spec.ports[*].port" \
        --no-headers 2>/dev/null | filter_ns | \
        while read -r ns name type cip eip ports; do
          eip_clean=$(echo "$eip" | sed 's/,/;/g' | sed 's/"//g')
          ports_clean=$(echo "$ports" | sed 's/,/;/g' | sed 's/"//g')
          printf '"%s"%s"%s"%s"%s"%s"%s"%s"%s"%s"%s"%s"%s"\n' \
            "$ns" "$DELIM" "$CLUSTER" "$DELIM" "$name" "$DELIM" "$type" "$DELIM" "$cip" "$DELIM" "$eip_clean" "$DELIM" "$ports_clean" \
            >> "$PROJECT_OUT_DIR/services.csv"
        done || true
    done
  fi
  echo "   └─ [$PROJECT_ID] services: $(format_time $(( $(date +%s) - SECTION_START )))"

  # 4. Cloud SQL
  SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] cloudsql.csv"
  local INSTANCE_COUNT=$(gcloud sql instances list --project="$PROJECT_ID" --quiet --format="value(name)" | wc -l)

  if [ "$INSTANCE_COUNT" -eq 0 ]; then
    echo "  (No se encontraron instancias Cloud SQL)"
    echo "NAME${DELIM}DATABASE_VERSION${DELIM}REGION${DELIM}TIER${DELIM}STATE${DELIM}PUBLIC_IP${DELIM}PRIVATE_IP${DELIM}AUTO_RESIZE${DELIM}BACKUP_ENABLED" > "$PROJECT_OUT_DIR/cloudsql.csv"
    echo "Sin instancias${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-" >> "$PROJECT_OUT_DIR/cloudsql.csv"
  else
    echo "  Encontradas $INSTANCE_COUNT instancia(s) Cloud SQL..."
    gcloud sql instances list \
      --project="$PROJECT_ID" \
      --format="csv[no-heading,separator=$DELIM](name,databaseVersion,region,settings.tier,state,settings.ipConfiguration.ipv4Enabled,ipAddresses[0].ipAddress,settings.storageAutoResize,settings.backupConfiguration.enabled)" \
      > "$PROJECT_OUT_DIR/cloudsql.csv" 2>/dev/null || true

    {
      echo "NAME${DELIM}DATABASE_VERSION${DELIM}REGION${DELIM}TIER${DELIM}STATE${DELIM}PUBLIC_IP${DELIM}PRIVATE_IP${DELIM}AUTO_RESIZE${DELIM}BACKUP_ENABLED"
      cat "$PROJECT_OUT_DIR/cloudsql.csv"
    } > "$PROJECT_OUT_DIR/cloudsql.tmp" 2>/dev/null && mv "$PROJECT_OUT_DIR/cloudsql.tmp" "$PROJECT_OUT_DIR/cloudsql.csv"

    sed -i '/^$/d' "$PROJECT_OUT_DIR/cloudsql.csv"
  fi
  echo "   └─ [$PROJECT_ID] cloudsql: $(format_time $(( $(date +%s) - SECTION_START )))"

  # 5. Cloud SQL Databases (bases de datos dentro de cada instancia)
  SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] clouddatabases.csv"
  echo "INSTANCE${DELIM}DATABASE${DELIM}CHARSET${DELIM}COLLATION" > "$PROJECT_OUT_DIR/clouddatabases.csv"

  if [ "$INSTANCE_COUNT" -gt 0 ]; then
    local INSTANCES=$(gcloud sql instances list --project="$PROJECT_ID" --quiet --format="value(name)" 2>/dev/null || true)
    if [ -n "$INSTANCES" ]; then
      echo "$INSTANCES" | while read -r INSTANCE_NAME; do
        [ -z "$INSTANCE_NAME" ] && continue
        gcloud sql databases list --instance="$INSTANCE_NAME" --project="$PROJECT_ID" \
          --format="csv[no-heading,separator=$DELIM](name,charset,collation)" \
          --quiet 2>/dev/null | while IFS= read -r line; do
          [ -z "$line" ] && continue
          printf '"%s"%s%s\n' "$INSTANCE_NAME" "$DELIM" "$line" >> "$PROJECT_OUT_DIR/clouddatabases.csv"
        done || true
      done
    fi
    # Filtrar líneas vacías
    sed -i '/^$/d' "$PROJECT_OUT_DIR/clouddatabases.csv"
  else
    echo "Sin instancias${DELIM}-${DELIM}-${DELIM}-" >> "$PROJECT_OUT_DIR/clouddatabases.csv"
  fi
  echo "   └─ [$PROJECT_ID] clouddatabases: $(format_time $(( $(date +%s) - SECTION_START )))"

  # 6. Ingress (K8s)
  SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] ingress.csv"
  echo "NAMESPACE${DELIM}CLUSTER${DELIM}NAME${DELIM}HOSTS${DELIM}ADDRESS${DELIM}PORTS" > "$PROJECT_OUT_DIR/ingress.csv"

  if [ -n "$CLUSTERS" ]; then
    echo "$CLUSTERS" | while read -r CLUSTER LOCATION; do
      gcloud container clusters get-credentials "$CLUSTER" --location="$LOCATION" --project="$PROJECT_ID" --quiet >/dev/null 2>&1

      kubectl get ingress --all-namespaces \
        -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,HOSTS:.spec.rules[*].host,ADDRESS:.status.loadBalancer.ingress[*].ip,PORTS:.spec.tls[*].secretName" \
        --no-headers 2>/dev/null | filter_ns | \
        while read -r ns name hosts addr ports; do
          hosts_clean=$(echo "$hosts" | sed 's/,/;/g' | sed 's/"//g')
          addr_clean=$(echo "$addr" | sed 's/,/;/g' | sed 's/"//g')
          ports_clean=$(echo "$ports" | sed 's/,/;/g' | sed 's/"//g')
          printf '"%s"%s"%s"%s"%s"%s"%s"%s"%s"%s"%s"\n' \
            "$ns" "$DELIM" "$CLUSTER" "$DELIM" "$name" "$DELIM" "$hosts_clean" "$DELIM" "$addr_clean" "$DELIM" "$ports_clean" \
            >> "$PROJECT_OUT_DIR/ingress.csv"
        done || true
    done
  fi
  sed -i '/^$/d' "$PROJECT_OUT_DIR/ingress.csv"
  echo "   └─ [$PROJECT_ID] ingress: $(format_time $(( $(date +%s) - SECTION_START )))"

  # 7. Cloud Run Services (JSON → Python csv.writer para CSV robusto)
  SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] cloudrun.csv"
  gcloud run services list --project="$PROJECT_ID" --platform=managed --format=json --quiet 2>/dev/null | \
    DELIM="$DELIM" python3 -c "
import json,sys,csv,os,re
w=csv.writer(sys.stdout,delimiter=os.environ['DELIM'],quoting=csv.QUOTE_ALL)
w.writerow(['NAME','REGION','URL','LAST_DEPLOYED','IMAGE'])
try:
 data=sys.stdin.read().strip()
 if data:
  d=json.loads(data)
  for s in d:
   name=s.get('metadata',{}).get('name','')
   url=s.get('status',{}).get('url','')
   region=''
   m=re.search(r'\.([a-z]+[0-9]-[a-z]+[0-9]*)\.run\.app',url)
   if m: region=m.group(1)
   ts=s.get('metadata',{}).get('creationTimestamp','')
   ctnrs=s.get('spec',{}).get('template',{}).get('spec',{}).get('containers',[])
   image=ctnrs[0].get('image','') if ctnrs else ''
   w.writerow([name,region,url,ts,image])
except: pass
" > "$PROJECT_OUT_DIR/cloudrun.csv"
  echo "   └─ [$PROJECT_ID] cloudrun: $(format_time $(( $(date +%s) - SECTION_START )))"

  # 8. Pub/Sub Topics (JSON → Python csv.writer para CSV robusto)
  SECTION_START=$(date +%s)
  echo "→ [$PROJECT_ID] pubsub.csv"
  gcloud pubsub topics list --project="$PROJECT_ID" --format=json --quiet 2>/dev/null | \
    DELIM="$DELIM" python3 -c "
import json,sys,csv,os
w=csv.writer(sys.stdout,delimiter=os.environ['DELIM'],quoting=csv.QUOTE_ALL)
w.writerow(['NAME','LABELS'])
try:
 data=sys.stdin.read().strip()
 if data:
  d=json.loads(data)
  for t in d:
   name=t.get('name','').split('/')[-1]
   if not name: continue
   if name.startswith('pubsub_'): continue
   labels=t.get('labels',{}) or {}
   lbl='|'.join(f'{k}={v}' for k,v in labels.items())
   w.writerow([name,lbl])
except: pass
" > "$PROJECT_OUT_DIR/pubsub.csv"
  echo "   └─ [$PROJECT_ID] pubsub: $(format_time $(( $(date +%s) - SECTION_START )))"

  # Cleanup kubeconfig aislado
  rm -f "$KUBECONFIG"

  local PROJECT_TIME=$(( $(date +%s) - PROJECT_START ))
  echo "✓ [$PROJECT_ID] Completado en $(format_time "$PROJECT_TIME") → $PROJECT_OUT_DIR/"
}

# =============================================================================
# Ejecución: paralela o secuencial
# =============================================================================
PIDS=()

for PROJECT_ID in "${PROJECTS[@]}"; do
  if [ "$SEQUENTIAL" = true ]; then
    process_project "$PROJECT_ID" "$DELIMITER"
  else
    # Lanzar en background
    process_project "$PROJECT_ID" "$DELIMITER" &
    PIDS+=($!)

    # Control de concurrencia: esperar si hay MAX_PARALLEL jobs corriendo
    while [ $(jobs -r | wc -l) -ge "$MAX_PARALLEL" ]; do
      sleep 1
    done
  fi
done

# Esperar a que todos los hilos terminen
if [ ${#PIDS[@]} -gt 0 ]; then
  echo ""
  echo "⏳ Esperando ${#PIDS[@]} hilo(s) en ejecución..."
  for pid in "${PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
fi

TOTAL_TIME=$(( $(date +%s) - START_TOTAL ))
echo ""
echo "========================================================"
echo "¡Proceso COMPLETO finalizado exitosamente!"
echo "Tiempo total : $(format_time "$TOTAL_TIME")"
echo "Hilos usados : $MAX_PARALLEL"
echo "Carpeta      : $OUTCOME_DIR"
echo "========================================================"