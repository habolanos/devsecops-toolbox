#!/bin/bash
# =============================================================================
# Script: generar-inventario-csv.sh
# Versión paralela - Procesa proyectos en hilos concurrentes
# Cada hilo usa su propio KUBECONFIG para evitar conflictos
# =============================================================================

set -euo pipefail

# === COLORES ANSI ===
RST='\033[0m'       # Reset
BOLD='\033[1m'      # Bold
DIM='\033[2m'       # Dim
RED='\033[91m'      # Red bright
GRN='\033[92m'      # Green bright
YLW='\033[93m'     # Yellow bright
BLU='\033[94m'     # Blue bright
MGN='\033[95m'     # Magenta bright
CYN='\033[96m'     # Cyan bright
WHT='\033[97m'     # White bright
GRB='\033[90m'     # Gray
BG_BLU='\033[44m'  # BG Blue
BG_GRN='\033[42m'  # BG Green
BG_YLW='\033[43m'  # BG Yellow

# === RUTAS ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/generar-inventario-csv.config"
OUTCOME_DIR="${SCRIPT_DIR}/outcome"
DELIMITER=";"
MAX_PARALLEL=4
PROGRESS_DIR="/tmp/inventario-progress-$$"
TOTAL_STEPS=8

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
  echo -e "${CYN}Uso:${RST} ./generar-inventario-csv.sh [opciones] [PROYECTO1 ...]"
  echo ""
  echo -e "  ${WHT}Opciones:${RST}"
  echo -e "  ${GRB}--delimiter=CHAR${RST}   Separador CSV (default: ;)"
  echo -e "  ${GRB}--threads=N${RST}        Hilos paralelos (default: 4)"
  echo -e "  ${GRB}--sequential${RST}       Deshabilitar paralelismo"
  echo ""
  echo -e "  ${DIM}Config : ${CONFIG_FILE}${RST}"
  echo -e "  ${DIM}Output : ${OUTCOME_DIR}/${RST}"
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
    echo -e "${RED}✘ Error:${RST} No se encontró $CONFIG_FILE"
    usage
  fi
  echo -e "${CYN}▸${RST} Leyendo proyectos desde: ${DIM}${CONFIG_FILE}${RST}"
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
rm -rf "$PROGRESS_DIR" 2>/dev/null; mkdir -p "$PROGRESS_DIR"

START_TOTAL=$(date +%s)

echo -e "${CYN}╔══════════════════════════════════════════════════════════════╗${RST}"
echo -e "${CYN}║${RST}  ${BOLD}${WHT}📋 INVENTARIO GKE + CLOUD SQL${RST}                              ${CYN}║${RST}"
echo -e "${CYN}╠══════════════════════════════════════════════════════════════╣${RST}"
echo -e "${CYN}║${RST}  ${GRB}Separador${RST}    : ${YLW}'${DELIMITER}'${RST}"
echo -e "${CYN}║${RST}  ${GRB}Proyectos${RST}    : ${WHT}${#PROJECTS[@]}${RST}"
for p in "${PROJECTS[@]}"; do
  echo -e "${CYN}║${RST}    ${DIM}• ${p}${RST}"
done
echo -e "${CYN}║${RST}  ${GRB}NS excluidos${RST} : ${DIM}${EXCLUDE_NS[*]:-ninguno}${RST}"
echo -e "${CYN}║${RST}  ${GRB}Hilos${RST}        : ${BLU}${MAX_PARALLEL}${RST}"
echo -e "${CYN}║${RST}  ${GRB}Output${RST}       : ${GRN}${OUTCOME_DIR}/${RST}"
echo -e "${CYN}╚══════════════════════════════════════════════════════════════╝${RST}"

# =============================================================================
# Funciones de progreso y dashboard
# =============================================================================
filter_ns() {
  if [ -n "$EXCLUDE_PATTERN" ]; then
    grep -vE "^[[:space:]]*(${EXCLUDE_PATTERN})[[:space:]]" || true
  else
    cat
  fi
}

# Barra de progreso ASCII: progress_bar CURRENT TOTAL WIDTH
progress_bar() {
  local cur=$1 tot=$2 w=${3:-20}
  local filled=$(( cur * w / tot ))
  local empty=$(( w - filled ))
  local bar=""
  for ((i=0; i<filled; i++)); do bar+="█"; done
  for ((i=0; i<empty; i++)); do bar+="░"; done
  echo "$bar"
}

# Actualizar archivo de progreso de un proyecto
update_progress() {
  local PROJECT_ID="$1"
  local STEP="$2"
  local STEP_NAME="$3"
  local STATUS="$4"  # running|done|error
  echo "${STEP}|${STEP_NAME}|${STATUS}|$(date +%s)" > "${PROGRESS_DIR}/${PROJECT_ID}.progress"
}

# Dashboard en vivo: muestra progreso de todos los hilos
show_dashboard() {
  local completed=0
  local running=0
  for pf in "${PROGRESS_DIR}"/*.progress; do
    [ -f "$pf" ] || continue
    local proj=$(basename "$pf" .progress)
    local info=$(cat "$pf")
    local step=$(echo "$info" | cut -d'|' -f1)
    local sname=$(echo "$info" | cut -d'|' -f2)
    local status=$(echo "$info" | cut -d'|' -f3)
    if [ "$status" = "done" ]; then
      completed=$((completed + 1))
    else
      running=$((running + 1))
    fi
  done
  local total=${#PROJECTS[@]}
  local bar=$(progress_bar $completed $total 25)
  echo -e "${DIM}  ┌─────────────────────────────────────────────────┐${RST}"
  echo -e "${DIM}  │${RST} ${BOLD}Progreso${RST} ${GRN}${bar}${RST} ${WHT}${completed}/${total}${RST} proyectos  ${DIM}│${RST}"
  echo -e "${DIM}  └─────────────────────────────────────────────────┘${RST}"
}

# Contador de proyectos completados (archivo compartido)
COMPLETED_FILE="${PROGRESS_DIR}/completed.count"
PREV_COMPLETED=0

# Mostrar resumen compacto de progreso (una sola línea por proyecto activo)
show_progress_line() {
  local completed=$(cat "$COMPLETED_FILE" 2>/dev/null || echo 0)
  local total=${#PROJECTS[@]}
  local bar=$(progress_bar $completed $total 20)

  # Solo mostrar cuando cambia el estado
  if [ "$completed" -ne "$PREV_COMPLETED" ]; then
    echo -e "  ${DIM}│${RST} ${GRN}${bar}${RST} ${WHT}${completed}/${total}${RST} completados"
    PREV_COMPLETED=$completed
  fi

  # Línea por cada proyecto en ejecución
  for pf in "${PROGRESS_DIR}"/*.progress; do
    [ -f "$pf" ] || continue
    local proj=$(basename "$pf" .progress)
    local info=$(cat "$pf")
    local step=$(echo "$info" | cut -d'|' -f1)
    local sname=$(echo "$info" | cut -d'|' -f2)
    local status=$(echo "$info" | cut -d'|' -f3)
    if [ "$status" = "done" ]; then
      echo -e "  ${GRN}✅${RST} ${DIM}${proj}${RST} ${GRN}completado${RST}"
    else
      local bar=$(progress_bar $step $TOTAL_STEPS 10)
      echo -e "  ${BLU}🔄${RST} ${WHT}${proj}${RST} ${CYN}${bar}${RST} ${YLW}${step}/${TOTAL_STEPS}${RST} ${DIM}${sname}${RST}"
    fi
  done
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

  update_progress "$PROJECT_ID" 0 "iniciando" "running"
  echo -e ""
  echo -e "${BOLD}${BLU}▶${RST} ${BOLD}${WHT}[${PROJECT_ID}]${RST} Iniciando inventario..."
  echo -e "${DIM}─────────────────────────────────────────────────────────${RST}"

  # 1. Clusters GKE (JSON → Python csv.writer para CSV robusto)
  local SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 1 "clusters" "running"
  echo -e "  ${CYN}❶${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}clusters.csv${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] clusters: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # 2. Deployments
  SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 2 "deployments" "running"
  echo -e "  ${CYN}❷${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}deployments.csv${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] deployments: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # 3. Services
  SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 3 "services" "running"
  echo -e "  ${CYN}❸${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}services.csv${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] services: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # 4. Cloud SQL
  SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 4 "cloudsql" "running"
  echo -e "  ${MGN}❹${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}cloudsql.csv${RST}"
  local INSTANCE_COUNT=$(gcloud sql instances list --project="$PROJECT_ID" --quiet --format="value(name)" | wc -l)

  if [ "$INSTANCE_COUNT" -eq 0 ]; then
    echo -e "  ${DIM}  (Sin instancias Cloud SQL)${RST}"
    echo "NAME${DELIM}DATABASE_VERSION${DELIM}REGION${DELIM}TIER${DELIM}STATE${DELIM}PUBLIC_IP${DELIM}PRIVATE_IP${DELIM}AUTO_RESIZE${DELIM}BACKUP_ENABLED" > "$PROJECT_OUT_DIR/cloudsql.csv"
    echo "Sin instancias${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-${DELIM}-" >> "$PROJECT_OUT_DIR/cloudsql.csv"
  else
    echo -e "  ${GRN}  ✓${RST} ${INSTANCE_COUNT} instancia(s) Cloud SQL encontradas${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] cloudsql: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # 5. Cloud SQL Databases (bases de datos dentro de cada instancia)
  SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 5 "clouddatabases" "running"
  echo -e "  ${MGN}❺${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}clouddatabases.csv${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] clouddatabases: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # 6. Ingress (K8s)
  SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 6 "ingress" "running"
  echo -e "  ${BLU}❻${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}ingress.csv${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] ingress: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # 7. Cloud Run Services (JSON → Python csv.writer para CSV robusto)
  SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 7 "cloudrun" "running"
  echo -e "  ${YLW}❼${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}cloudrun.csv${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] cloudrun: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # 8. Pub/Sub Topics (JSON → Python csv.writer para CSV robusto)
  SECTION_START=$(date +%s)
  update_progress "$PROJECT_ID" 8 "pubsub" "running"
  echo -e "  ${YLW}❽${RST} ${WHT}[${PROJECT_ID}]${RST} ${DIM}pubsub.csv${RST}"
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
  echo -e "   ${GRN}└─${RST} [${PROJECT_ID}] pubsub: ${YLW}$(format_time $(( $(date +%s) - SECTION_START )))${RST}"

  # Cleanup kubeconfig aislado
  rm -f "$KUBECONFIG"

  update_progress "$PROJECT_ID" 8 "completado" "done"
  # Incrementar contador compartido
  local count=$(cat "$COMPLETED_FILE" 2>/dev/null || echo 0)
  echo $((count + 1)) > "$COMPLETED_FILE"
  local PROJECT_TIME=$(( $(date +%s) - PROJECT_START ))
  echo -e "${BOLD}${GRN}✅${RST} ${BOLD}[${PROJECT_ID}]${RST} Completado en ${YLW}$(format_time "$PROJECT_TIME")${RST} → ${DIM}${PROJECT_OUT_DIR}/${RST}"
  # Mostrar resumen compacto de progreso
  show_progress_line
}

# =============================================================================
# Ejecución: paralela o secuencial
# =============================================================================
PIDS=()

# Inicializar contador de completados
echo 0 > "$COMPLETED_FILE"

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
  echo -e "${BLU}⏳${RST} Esperando ${BOLD}${#PIDS[@]}${RST} hilo(s) restantes..."
  for pid in "${PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
fi

# Resumen final de progreso
show_progress_line
rm -rf "$PROGRESS_DIR" 2>/dev/null

TOTAL_TIME=$(( $(date +%s) - START_TOTAL ))
echo ""
echo -e "${GRN}╔══════════════════════════════════════════════════════════════╗${RST}"
echo -e "${GRN}║${RST}  ${BOLD}${WHT}🎉 ¡Proceso COMPLETO finalizado exitosamente!${RST}              ${GRN}║${RST}"
echo -e "${GRN}╠══════════════════════════════════════════════════════════════╣${RST}"
echo -e "${GRN}║${RST}  ${GRB}Tiempo total${RST} : ${YLW}$(format_time "$TOTAL_TIME")${RST}"
echo -e "${GRN}║${RST}  ${GRB}Hilos usados${RST} : ${BLU}${MAX_PARALLEL}${RST}"
echo -e "${GRN}║${RST}  ${GRB}Proyectos${RST}    : ${WHT}${#PROJECTS[@]}${RST}"
echo -e "${GRN}║${RST}  ${GRB}Carpeta${RST}      : ${CYN}${OUTCOME_DIR}/${RST}"
echo -e "${GRN}╚══════════════════════════════════════════════════════════════╝${RST}"