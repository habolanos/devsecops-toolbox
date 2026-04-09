#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Script: webhooks.sh
# Description: Monitoreo SRE de deployments GKE con notificaciones a Google Chat
# Version: 2.3.0
# =============================================================================

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-${SCRIPT_DIR}/config/webhooks_config.json}"

WEBHOOK_URL=""
TIMEZONE=""
REPORTER=""
declare -a PROJECTS=()
declare -a EXCLUDED_PREFIXES=()

# Directorio temporal para ejecución paralela
TEMP_DIR=""
PARALLEL_ENABLED="${PARALLEL_ENABLED:-true}"

# Medición de tiempo
START_TIME=$(date +%s)
START_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Global variables
TOTAL_PROJECTS=0
CURRENT_INDEX=0
TOTAL_GLOBAL=0
OK_GLOBAL=0
CAIDOS_GLOBAL=0
DETALLE_CAIDOS=""
SUMMARY_PROJECT_KEY=""

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  --simple              Show simplified output format
  --simple-estable      Generate simplified Soporte Temprano notification
  --simple-caidos       Generate simplified notification with fallen services
  --simple-fin-operacion Generate operation end notification
  --simple-weekend      Generate weekend support notification
  --summary             Generate summary report notification
  --help                Display this help message

Environment Variables:
  CONFIG_FILE           Path to JSON config file (default: ./config/webhooks_config.json)
  WEBHOOK_URL           Override webhook URL from config
  TIMEZONE              Override timezone from config

Config File Format (JSON):
  {
    "webhook": { "url": "https://..." },
    "settings": {
      "timezone": "America/Mazatlan",
      "reporter": "...",
      "excluded_namespace_prefixes": ["gke-", "datadog", "kube-", "default"]
    },
    "contexts": [
      { "name": "GRUPO", "context": "kubectl-context", "description": "..." }
    ]
  }

Note: Namespaces are discovered dynamically per context, excluding prefixes defined in settings.
EOF
    exit 0
}

check_dependencies() {
    local missing=()
    for cmd in kubectl jq curl; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "❌ Error: Comandos requeridos no encontrados: ${missing[*]}" >&2
        exit 1
    fi
}

cleanup() {
    [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"
}

print_execution_time() {
    local end_time end_timestamp duration_seconds duration_formatted
    end_time=$(date +%s)
    end_timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    duration_seconds=$((end_time - START_TIME))
    
    # Formatear duración
    local hours=$((duration_seconds / 3600))
    local minutes=$(( (duration_seconds % 3600) / 60 ))
    local seconds=$((duration_seconds % 60))
    
    if [[ $hours -gt 0 ]]; then
        duration_formatted="${hours}h ${minutes}m ${seconds}s"
    elif [[ $minutes -gt 0 ]]; then
        duration_formatted="${minutes}m ${seconds}s"
    else
        duration_formatted="${seconds}s"
    fi
    
    echo ""
    echo "┌─────────────────────────────────────────────────────┐"
    echo "│ ⏱️  TIEMPO DE EJECUCIÓN                              │"
    echo "├─────────────────────────────────────────────────────┤"
    printf "│ 🚀 Inicio:   %-38s │\n" "$START_TIMESTAMP"
    printf "│ 🏁 Fin:      %-38s │\n" "$end_timestamp"
    printf "│ ⏳ Duración: %-38s │\n" "$duration_formatted"
    echo "└─────────────────────────────────────────────────────┘"
}

trap 'cleanup; print_execution_time' EXIT

init_temp_dir() {
    TEMP_DIR=$(mktemp -d)
    mkdir -p "$TEMP_DIR/namespaces" "$TEMP_DIR/results"
}

discover_context_namespaces() {
    local ctx_name="$1"
    local ctx_context="$2"
    local output_file="$TEMP_DIR/namespaces/${ctx_name}.txt"
    
    local namespaces
    if ! namespaces=$(kubectl --context "$ctx_context" get ns -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); then
        echo "FAILED" > "$output_file"
        return
    fi
    
    for ns in $namespaces; do
        local excluded=false
        for prefix in "${EXCLUDED_PREFIXES[@]}"; do
            if [[ "$ns" == "$prefix"* || "$ns" == "$prefix" ]]; then
                excluded=true
                break
            fi
        done
        [[ "$excluded" == "false" ]] && echo "${ctx_name}::${ns}|${ctx_context}|${ns}" >> "$output_file"
    done
}

process_namespace_stats() {
    local item="$1"
    local output_file="$2"
    
    IFS="::" read -r PROJECT_KEY DATA <<< "$item"
    IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"
    
    local total=0 ok=0 caidos=0 detalle=""
    
    if kubectl --context "$CONTEXT" get ns "$NAMESPACE" &>/dev/null; then
        local deployments
        deployments=$(kubectl --context "$CONTEXT" -n "$NAMESPACE" get deploy \
            -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.readyReplicas}{"|"}{.status.replicas}{"\n"}{end}' 2>/dev/null)
        
        while IFS="|" read -r NAME READY TOTAL_REPLICAS; do
            READY=${READY:-0}
            TOTAL_REPLICAS=${TOTAL_REPLICAS:-0}
            [[ "$TOTAL_REPLICAS" -eq 0 ]] && continue
            total=$((total + 1))
            if [[ "$READY" -eq 0 ]]; then
                caidos=$((caidos + 1))
                detalle+="• $NAME ($PROJECT_KEY / $NAMESPACE)|Estado: Servicio no disponible (0/$TOTAL_REPLICAS)|Acción: Equipo SRE en recuperación 🛠️\n"
            else
                ok=$((ok + 1))
            fi
        done <<< "$deployments"
    fi
    
    echo "$PROJECT_KEY|$total|$ok|$caidos|$detalle" >> "$output_file"
}

load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "❌ Error: Archivo de configuración no encontrado: $CONFIG_FILE" >&2
        echo "   Crear archivo de configuración o especificar ruta con CONFIG_FILE=<path>" >&2
        exit 1
    fi
    
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        echo "❌ Error: Archivo JSON inválido: $CONFIG_FILE" >&2
        exit 1
    fi
    
    # Cargar webhook URL (prioridad: env var > json)
    local json_webhook
    json_webhook=$(jq -r '.webhook.url // empty' "$CONFIG_FILE")
    WEBHOOK_URL="${WEBHOOK_URL:-$json_webhook}"
    
    if [[ -z "$WEBHOOK_URL" ]]; then
        echo "❌ Error: webhook.url no definido en configuración" >&2
        exit 1
    fi
    
    # Cargar timezone (prioridad: env var > json > default)
    local json_timezone
    json_timezone=$(jq -r '.settings.timezone // "America/Mazatlan"' "$CONFIG_FILE")
    TIMEZONE="${TIMEZONE:-$json_timezone}"
    
    # Cargar reporter
    REPORTER=$(jq -r '.settings.reporter // "SRE Equipo Softtek"' "$CONFIG_FILE")
    
    # Cargar prefijos de namespaces excluidos
    EXCLUDED_PREFIXES=()
    while IFS= read -r prefix; do
        [[ -n "$prefix" ]] && EXCLUDED_PREFIXES+=("$prefix")
    done < <(jq -r '.settings.excluded_namespace_prefixes[]? // empty' "$CONFIG_FILE")
    
    if [[ ${#EXCLUDED_PREFIXES[@]} -eq 0 ]]; then
        EXCLUDED_PREFIXES=("gke-" "datadog" "kube-" "default")
    fi
    
    echo "📋 Prefijos de namespaces excluidos: ${EXCLUDED_PREFIXES[*]}"
    
    # Cargar contextos
    local context_count
    context_count=$(jq '.contexts | length' "$CONFIG_FILE")
    
    if [[ "$context_count" -eq 0 ]]; then
        echo "❌ Error: No hay contextos definidos en configuración" >&2
        exit 1
    fi
    
    # Inicializar directorio temporal
    init_temp_dir
    
    # Descubrir namespaces en paralelo
    local pids=()
    local i ctx_name ctx_context
    
    if [[ "$PARALLEL_ENABLED" == "true" ]]; then
        echo "⚡ Descubriendo namespaces en paralelo ($context_count contextos)..."
        for ((i=0; i<context_count; i++)); do
            ctx_name=$(jq -r ".contexts[$i].name" "$CONFIG_FILE")
            ctx_context=$(jq -r ".contexts[$i].context" "$CONFIG_FILE")
            echo "  🔍 Iniciando: $ctx_name"
            discover_context_namespaces "$ctx_name" "$ctx_context" &
            pids+=($!)
        done
        
        # Esperar a que todos terminen
        for pid in "${pids[@]}"; do
            wait "$pid" 2>/dev/null || true
        done
        echo "  ✅ Descubrimiento paralelo completado"
    else
        echo "🔍 Descubriendo namespaces secuencialmente..."
        for ((i=0; i<context_count; i++)); do
            ctx_name=$(jq -r ".contexts[$i].name" "$CONFIG_FILE")
            ctx_context=$(jq -r ".contexts[$i].context" "$CONFIG_FILE")
            echo "  🔍 $ctx_name ($ctx_context)..."
            discover_context_namespaces "$ctx_name" "$ctx_context"
        done
    fi
    
    # Consolidar resultados
    PROJECTS=()
    for file in "$TEMP_DIR/namespaces"/*.txt; do
        [[ -f "$file" ]] || continue
        local ctx_name_file
        ctx_name_file=$(basename "$file" .txt)
        if [[ $(head -1 "$file" 2>/dev/null) == "FAILED" ]]; then
            echo "  ⚠️ No se pudo conectar al contexto $ctx_name_file"
        else
            while IFS= read -r line; do
                [[ -n "$line" ]] && PROJECTS+=("$line")
            done < "$file"
        fi
    done
    
    TOTAL_PROJECTS=${#PROJECTS[@]}
    
    if [[ "$TOTAL_PROJECTS" -eq 0 ]]; then
        echo "❌ Error: No se encontraron namespaces válidos en ningún contexto" >&2
        exit 1
    fi
    
    echo "✅ Configuración cargada: $TOTAL_PROJECTS namespaces desde $context_count contextos"
}

calculate_stats_parallel() {
    local results_file="$TEMP_DIR/results/stats.txt"
    > "$results_file"
    
    local pids=()
    local total_items=${#PROJECTS[@]}
    
    if [[ "$PARALLEL_ENABLED" == "true" && "$total_items" -gt 1 ]]; then
        echo "⚡ Procesando $total_items namespaces en paralelo..."
        for item in "${PROJECTS[@]}"; do
            process_namespace_stats "$item" "$results_file" &
            pids+=($!)
        done
        
        # Esperar a que todos terminen
        for pid in "${pids[@]}"; do
            wait "$pid" 2>/dev/null || true
        done
    else
        echo "🔄 Procesando $total_items namespaces..."
        for item in "${PROJECTS[@]}"; do
            process_namespace_stats "$item" "$results_file"
        done
    fi
    
    # Consolidar resultados
    TOTAL_GLOBAL=0
    OK_GLOBAL=0
    CAIDOS_GLOBAL=0
    DETALLE_CAIDOS=""
    SUMMARY_PROJECT_KEY=""
    
    while IFS="|" read -r proj_key total ok caidos detalle; do
        [[ -z "$SUMMARY_PROJECT_KEY" ]] && SUMMARY_PROJECT_KEY="$proj_key"
        TOTAL_GLOBAL=$((TOTAL_GLOBAL + total))
        OK_GLOBAL=$((OK_GLOBAL + ok))
        CAIDOS_GLOBAL=$((CAIDOS_GLOBAL + caidos))
        [[ -n "$detalle" ]] && DETALLE_CAIDOS+="$detalle"
    done < "$results_file"
    
    echo "✅ Estadísticas calculadas: $TOTAL_GLOBAL servicios, $OK_GLOBAL OK, $CAIDOS_GLOBAL caídos"
}

# -----------------------------------------------------------------------------
# MAIN SCRIPT
# -----------------------------------------------------------------------------

# Check for help flag
if [[ "${1:-}" == "--help" ]]; then
    show_help
fi

# Initialize
check_dependencies
load_config

# Check for simple flag
SIMPLE_OUTPUT=false
if [[ "${1:-}" == "--simple" ]]; then
    SIMPLE_OUTPUT=true
fi

# Check for simple-estable flag
if [[ "${1:-}" == "--simple-estable" ]]; then
    calculate_stats_parallel

    MESSAGE="📣 Reporte Monitoreo Soporte Temprano $SUMMARY_PROJECT_KEY\n\n"
    MESSAGE+="Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
    MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
    MESSAGE+="🥷 SRE Equipo Softtek\n"

    MESSAGE=$(printf "%b" "$MESSAGE")

    echo -e "+---------------------------------------------------+"
    echo -e "$MESSAGE"
    echo -e "+---------------------------------------------------+"
    echo

    read -p "¿Deseas continuar con el envío del mensaje? (Y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operación cancelada."
        exit 0
    fi

    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg text "$MESSAGE" '{text: $text}')"

    exit 0
fi

# Check for simple-caidos flag
if [[ "${1:-}" == "--simple-caidos" ]]; then
    calculate_stats_parallel

    MESSAGE="📣 Reporte Monitoreo Soporte Temprano $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
    MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
    MESSAGE+="• Servicios caídos: $CAIDOS_GLOBAL\n"
    MESSAGE+="🛠️ Acciones requeridas por SRE:\n\n"
    MESSAGE+="🥷 SRE Equipo Softtek\n"

    MESSAGE=$(printf "%b" "$MESSAGE")

    echo -e "+---------------------------------------------------+"
    echo -e "$MESSAGE"
    echo -e "+---------------------------------------------------+"
    echo

    read -p "¿Deseas continuar con el envío del mensaje? (Y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operación cancelada."
        exit 0
    fi

    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg text "$MESSAGE" '{text: $text}')"

    exit 0
fi

# Check for simple-fin-operacion flag
if [[ "${1:-}" == "--simple-fin-operacion" ]]; then
    calculate_stats_parallel

    MESSAGE="📣 Reporte Monitoreo finalización de Operación $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
    MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
    MESSAGE+="• Servicios caídos: $CAIDOS_GLOBAL\n"
    MESSAGE+="🛠️ Acciones requeridas por SRE:\n\n"
    MESSAGE+="🥷 SRE Equipo Softtek\n"

    MESSAGE=$(printf "%b" "$MESSAGE")

    echo -e "+---------------------------------------------------+"
    echo -e "$MESSAGE"
    echo -e "+---------------------------------------------------+"
    echo

    read -p "¿Deseas continuar con el envío del mensaje? (Y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operación cancelada."
        exit 0
    fi

    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg text "$MESSAGE" '{text: $text}')"

    exit 0
fi

# Check for simple-weekend flag
if [[ "${1:-}" == "--simple-weekend" ]]; then
    calculate_stats_parallel

    MESSAGE="📣 Reporte Monitoreo Soporte fin de semana $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
    MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
    MESSAGE+="• Servicios caídos: $CAIDOS_GLOBAL\n"
    MESSAGE+="🛠️ Acciones requeridas por SRE:\n\n"
    MESSAGE+="🥷 SRE Equipo Softtek\n"

    MESSAGE=$(printf "%b" "$MESSAGE")

    echo -e "+---------------------------------------------------+"
    echo -e "$MESSAGE"
    echo -e "+---------------------------------------------------+"
    echo

    read -p "¿Deseas continuar con el envío del mensaje? (Y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operación cancelada."
        exit 0
    fi

    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg text "$MESSAGE" '{text: $text}')"

    exit 0
fi


# Check for summary flag
if [[ "${1:-}" == "--summary" ]]; then
    calculate_stats_parallel

    FECHA=$(TZ="$TIMEZONE" date '+%d/%m/%Y')
    HORA=$(TZ="$TIMEZONE" date '+%-I:%M %p')

    MESSAGE="📣 Reporte $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="📅 Fecha: $FECHA\n"
    MESSAGE+="🕒 Hora: $HORA Culiacan Time\n\n"
    MESSAGE+="Incidente activo: No\n"
    MESSAGE+="📌 Estatus breve:\n"
    MESSAGE+="No se reporta ningún problemas dentro de los servicios.\n"
    MESSAGE+="Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
    MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
    MESSAGE+="• Servicios caídos: $CAIDOS_GLOBAL\n\n"
    MESSAGE+="🛠️ Acciones requeridas por SRE:\n"
    MESSAGE+="Monitoreo en servicios productivos.\n"
    MESSAGE+="Continuar validación de alertas.\n"
    MESSAGE+="👤 Quien reporta:\n"
    MESSAGE+="$REPORTER\n"

    MESSAGE=$(printf "%b" "$MESSAGE")

    echo -e "+---------------------------------------------------+"
    echo -e "$MESSAGE"
    echo -e "+---------------------------------------------------+"
    echo

    read -p "¿Deseas continuar con el envío del mensaje? (Y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operación cancelada."
        exit 0
    fi

    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg text "$MESSAGE" '{text: $text}')"

    exit 0
fi

MESSAGE="*📊 Reporte SRE - Monitoreo RETAIL (Comercial)*\n"
MESSAGE+="🗓 Fecha y hora: $(TZ="$TIMEZONE" date '+%d/%m/%Y %H:%M:%S')\n\n"

CURRENT_PROJECT=""

for ITEM in "${PROJECTS[@]}"; do
  CURRENT_INDEX=$((CURRENT_INDEX + 1))
  IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
  IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"

  # Show progress
  echo -ne "\r⏳ Procesando [$CURRENT_INDEX/$TOTAL_PROJECTS]: $PROYECTO...                    "

  if [[ "$PROJECT_KEY" != "$CURRENT_PROJECT" ]]; then
    MESSAGE+="\n *$PROJECT_KEY*\n"
    CURRENT_PROJECT="$PROJECT_KEY"
  fi

  CLEAN_PROYECTO=$(echo "$PROYECTO" | sed 's/^://')
  MESSAGE+="\n📁 *$CLEAN_PROYECTO*\n"
  MESSAGE+="• Cluster: $CONTEXT\n"
  if [ "$SIMPLE_OUTPUT" = false ]; then
      MESSAGE+="• Namespace: $NAMESPACE\n"
  fi

  if ! kubectl --context "$CONTEXT" get ns "$NAMESPACE" &>/dev/null; then
    MESSAGE+="  ❌ Sin acceso al namespace\n"
    continue
  fi

  if [ "$SIMPLE_OUTPUT" = false ]; then
      MESSAGE+="  ✅ Acceso OK\n"

      if kubectl --context "$CONTEXT" top pod -n "$NAMESPACE" &>/dev/null; then
        CPU_TOTAL=$(kubectl --context "$CONTEXT" top pod -n "$NAMESPACE" \
          --no-headers | awk '{sum+=$2} END {print (sum ? sum "m" : "N/A")}')

        MEM_TOTAL=$(kubectl --context "$CONTEXT" top pod -n "$NAMESPACE" \
          --no-headers | awk '{sum+=$3} END {print (sum ? sum "Mi" : "N/A")}')

        POD_COUNT=$(kubectl --context "$CONTEXT" get pod -n "$NAMESPACE" --no-headers | wc -l)

        MESSAGE+="  📈 *Consumo recursos:*\n"
        MESSAGE+="   • CPU total: $CPU_TOTAL\n"
        MESSAGE+="   • Memoria total: $MEM_TOTAL\n"
        MESSAGE+="   • Pods activos (Considerando escalamiento en HPA): $POD_COUNT\n"
      else
        MESSAGE+="  ⚠️ Metrics-server no disponible\n"
      fi
  fi

  TOTAL_PROYECTO=0
  CAIDOS_PROYECTO=0

  DEPLOYMENTS=$(kubectl --context "$CONTEXT" -n "$NAMESPACE" get deploy \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.readyReplicas}{"|"}{.status.replicas}{"\n"}{end}')

  while IFS="|" read -r NAME READY TOTAL; do
    READY=${READY:-0}
    TOTAL=${TOTAL:-0}
    [[ "$TOTAL" -eq 0 ]] && continue

    TOTAL_PROYECTO=$((TOTAL_PROYECTO + 1))
    TOTAL_GLOBAL=$((TOTAL_GLOBAL + 1))

    if [[ "$READY" -eq 0 ]]; then
      CAIDOS_PROYECTO=$((CAIDOS_PROYECTO + 1))
      CAIDOS_GLOBAL=$((CAIDOS_GLOBAL + 1))

      DETALLE_CAIDOS+="• $NAME ($PROJECT_KEY / $NAMESPACE)\n"
      DETALLE_CAIDOS+="  Estado: Servicio no disponible (0/$TOTAL)\n"
      DETALLE_CAIDOS+="  Acción: Equipo SRE en recuperación 🛠️\n\n"
    else
      OK_GLOBAL=$((OK_GLOBAL + 1))
    fi
  done <<< "$DEPLOYMENTS"

  if [ "$SIMPLE_OUTPUT" = true ]; then
      if [ "$CAIDOS_PROYECTO" -eq 0 ]; then
          MESSAGE+="✅ No Alertados\n"
          MESSAGE+="✅ No Errores\n"
          MESSAGE+="🟢 Estado general: OPERACIÓN NORMAL\n"
      else
          MESSAGE+="❌ Servicios con problemas: $CAIDOS_PROYECTO\n"
      fi
  else
      MESSAGE+="• Total servicios: $TOTAL_PROYECTO\n"
      MESSAGE+="• Servicios caídos: $CAIDOS_PROYECTO\n"
  fi
done

# Clear progress indicator
echo -e "\r✅ Procesamiento completado ($TOTAL_PROJECTS proyectos)                    \n"

MESSAGE+="\n🔢 *Totales generales*\n"
MESSAGE+="• Servicios monitoreados: $TOTAL_GLOBAL\n"
MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
MESSAGE+="• Servicios caídos: $CAIDOS_GLOBAL\n\n"

if [[ "$CAIDOS_GLOBAL" -gt 0 ]]; then
  MESSAGE+="🚨 *Estado general: Servicios no disponibles*\n\n"
else
  MESSAGE+="🟢 *Estado general: OPERACIÓN NORMAL*\n\n"
fi


[[ -n "$DETALLE_CAIDOS" ]] && MESSAGE+="\n$DETALLE_CAIDOS"

MESSAGE+="👤 Quién reporta: $REPORTER\n"

MESSAGE=$(printf "%b" "$MESSAGE")

echo -e "+---------------------------------------------------+"
echo -e "$MESSAGE"
echo -e "+---------------------------------------------------+"
echo

read -p "¿Deseas continuar con el envío del mensaje? (Y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Operación cancelada."
    exit 0
fi

curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg text "$MESSAGE" '{text: $text}')"