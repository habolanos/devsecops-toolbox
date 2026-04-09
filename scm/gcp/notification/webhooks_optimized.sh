#!/usr/bin/env bash
set -euo pipefail

# Function to display help
show_help() {
    echo "Usage: $0 [--simple] [--summary] [--simple-estable] [--simple-caidos] [--simple-fin-operacion] [--simple-weekend]"
    echo "Options:"
    echo "  --simple           Show simplified output format"
    echo "  --simple-estable   Generate simplified Soporte Temprano notification"
    echo "  --simple-caidos    Generate simplified notification with fallen services"
    echo "  --simple-fin-operacion Generate operation end notification"
    echo "  --simple-weekend   Generate weekend support notification"
    echo "  --summary          Generate TIENDAS summary report notification"
    echo "  --help             Display this help message"
    exit 0
}

# Check for help flag
if [[ "${1:-}" == "--help" ]]; then
    show_help
fi

##TEST##
#WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/AAQAOnJzpCw/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jYbhXk_XMLcRCfPZyFoYOJvcZ6gmR1cBOWUh4cMI7a8"
##GUARDIA## a - INTERNO - Alertas SRE / Producción
WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/AAQAAwrKz7U/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Jg86Nq9MLD-P_h7Yus0tB_G4pqWT1s10wIFo8BT06zk"

PROJECTS=(
  "COMERCIAL::ComprasMuebles|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|comprasmuebles"
  "COMERCIAL::Comprasropa|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|comprasropa"
  "COMERCIAL::Consolidadora|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|consolidadora"
  "COMERCIAL::Hardline|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|hardline"
  #"COMERCIAL::Importacion|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|importacion"
  "COMERCIAL::Promotions|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|promotions"
  "COMERCIAL::Rmi|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|rmi"
  #"COMERCIAL::Siscomprasropa|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|siscomprasropa"
  "COMERCIAL::Sistimp|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|sistimp"
  "COMERCIAL::Softline|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|softline"
  "COMERCIAL::Items|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|items"
)

# Global variables
TOTAL_PROJECTS=${#PROJECTS[@]}
CURRENT_INDEX=0
TOTAL_GLOBAL=0
OK_GLOBAL=0
CAIDOS_GLOBAL=0
DETALLE_CAIDOS=""
SUMMARY_PROJECT_KEY=""
PROJECT_DETAILS=()

# Function to calculate all metrics in one pass
calculate_metrics() {
    local show_progress=${1:-true}
    
    for ITEM in "${PROJECTS[@]}"; do
        [[ "$show_progress" == "true" ]] && {
            CURRENT_INDEX=$((CURRENT_INDEX + 1))
            echo -ne "\r⏳ Procesando [$CURRENT_INDEX/$TOTAL_PROJECTS]: $(echo "$ITEM" | cut -d'|' -f2)...                    "
        }
        
        IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
        IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"
        
        # Store first project key for summary reports
        [[ -z "$SUMMARY_PROJECT_KEY" ]] && SUMMARY_PROJECT_KEY="$PROJECT_KEY"
        
        # Store project details for detailed report
        PROJECT_DETAILS+=("$PROJECT_KEY|$PROYECTO|$CONTEXT|$NAMESPACE")
        
        if kubectl --context "$CONTEXT" get ns "$NAMESPACE" &>/dev/null; then
            DEPLOYMENTS=$(kubectl --context "$CONTEXT" -n "$NAMESPACE" get deploy \
                -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.readyReplicas}{"|"}{.status.replicas}{"\n"}{end}' 2>/dev/null)
            
            while IFS="|" read -r NAME READY TOTAL; do
                READY=${READY:-0}
                TOTAL=${TOTAL:-0}
                [[ "$TOTAL" -eq 0 ]] && continue
                
                TOTAL_GLOBAL=$((TOTAL_GLOBAL + 1))
                
                if [[ "$READY" -eq 0 ]]; then
                    CAIDOS_GLOBAL=$((CAIDOS_GLOBAL + 1))
                    DETALLE_CAIDOS+="• $NAME ($PROJECT_KEY / $NAMESPACE)\n"
                    DETALLE_CAIDOS+="  Estado: Servicio no disponible (0/$TOTAL)\n"
                    DETALLE_CAIDOS+="  Acción: Equipo SRE en recuperación 🛠️\n\n"
                else
                    OK_GLOBAL=$((OK_GLOBAL + 1))
                fi
            done <<< "$DEPLOYMENTS"
        fi
    done
    
    [[ "$show_progress" == "true" ]] && echo -e "\r✅ Procesamiento completado ($TOTAL_PROJECTS proyectos)                    \n"
}

# Function to send notification
send_notification() {
    local message="$1"
    
    echo -e "+---------------------------------------------------+"
    echo -e "$message"
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
      -d "$(jq -n --arg text "$message" '{text: $text}')"
}

# Function to generate simple messages
generate_simple_message() {
    local type="$1"
    local title=""
    
    case "$type" in
        --simple-estable)
            title="📣 Reporte Monitoreo Soporte Temprano $SUMMARY_PROJECT_KEY"
            ;;
        --simple-caidos)
            title="📣 Reporte Monitoreo Soporte Temprano $SUMMARY_PROJECT_KEY"
            ;;
        --simple-fin-operacion)
            title="📣 Reporte Monitoreo finalización de Operación $SUMMARY_PROJECT_KEY"
            ;;
        --simple-weekend)
            title="📣 Reporte Monitoreo Soporte fin de semana $SUMMARY_PROJECT_KEY"
            ;;
    esac
    
    MESSAGE="$title\n"
    MESSAGE+="Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
    MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
    
    # Add fallen services only for specific types
    if [[ "$type" == "--simple-caidos" || "$type" == "--simple-fin-operacion" || "$type" == "--simple-weekend" ]]; then
        MESSAGE+="• Servicios caídos: $CAIDOS_GLOBAL\n"
        MESSAGE+="🛠️ Acciones requeridas por SRE:\n\n"
    fi
    
    MESSAGE+="🥷 SRE Equipo Softtek\n"
    
    MESSAGE=$(printf "%b" "$MESSAGE")
    send_notification "$MESSAGE"
}

# Function to generate summary message
generate_summary_message() {
    FECHA=$(TZ=America/Mazatlan date '+%d/%m/%Y')
    HORA=$(TZ=America/Mazatlan date '+%-I:%M %p')

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
    MESSAGE+="SRE Equipo Softtek - Harold Adrian\n"

    MESSAGE=$(printf "%b" "$MESSAGE")
    send_notification "$MESSAGE"
}

# Function to generate detailed message
generate_detailed_message() {
    local simple_output="$1"
    
    MESSAGE="*📊 Reporte SRE – Monitoreo RETAIL (Comercial)*\n"
    MESSAGE+="🗓 Fecha y hora (Culiacán): $(TZ=America/Mazatlan date '+%d/%m/%Y %H:%M:%S')\n\n"

    CURRENT_PROJECT=""
    
    for DETAIL in "${PROJECT_DETAILS[@]}"; do
        IFS="|" read -r PROJECT_KEY PROYECTO CONTEXT NAMESPACE <<< "$DETAIL"
        
        if [[ "$PROJECT_KEY" != "$CURRENT_PROJECT" ]]; then
            MESSAGE+="\n *$PROJECT_KEY*\n"
            CURRENT_PROJECT="$PROJECT_KEY"
        fi

        CLEAN_PROYECTO=$(echo "$PROYECTO" | sed 's/^://')
        MESSAGE+="\n📁 *$CLEAN_PROYECTO*\n"
        MESSAGE+="• Cluster: $CONTEXT\n"
        if [ "$simple_output" = false ]; then
            MESSAGE+="• Namespace: $NAMESPACE\n"
        fi

        if ! kubectl --context "$CONTEXT" get ns "$NAMESPACE" &>/dev/null; then
            MESSAGE+="  ❌ Sin acceso al namespace\n"
            continue
        fi

        if [ "$simple_output" = false ]; then
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

        # Calculate project-specific metrics
        TOTAL_PROYECTO=0
        CAIDOS_PROYECTO=0

        DEPLOYMENTS=$(kubectl --context "$CONTEXT" -n "$NAMESPACE" get deploy \
          -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.readyReplicas}{"|"}{.status.replicas}{"\n"}{end}')

        while IFS="|" read -r NAME READY TOTAL; do
            READY=${READY:-0}
            TOTAL=${TOTAL:-0}
            [[ "$TOTAL" -eq 0 ]] && continue

            TOTAL_PROYECTO=$((TOTAL_PROYECTO + 1))

            if [[ "$READY" -eq 0 ]]; then
                CAIDOS_PROYECTO=$((CAIDOS_PROYECTO + 1))
            fi
        done <<< "$DEPLOYMENTS"

        if [ "$simple_output" = true ]; then
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

    if [ "$simple_output" = true ]; then
        MESSAGE+="👤 Quién reporta: SRE Retail - Harold Adrian\n"
    else
        MESSAGE+="👤 Quién reporta: Equipo Softtek SE\n"
    fi

    MESSAGE=$(printf "%b" "$MESSAGE")
    send_notification "$MESSAGE"
}

# Main logic
SIMPLE_OUTPUT=false
case "${1:-}" in
    --simple)
        SIMPLE_OUTPUT=true
        calculate_metrics
        generate_detailed_message "true"
        ;;
    --simple-estable|--simple-caidos|--simple-fin-operacion|--simple-weekend)
        calculate_metrics "false"
        generate_simple_message "${1}"
        ;;
    --summary)
        calculate_metrics "false"
        generate_summary_message
        ;;
    *)
        calculate_metrics
        generate_detailed_message "false"
        ;;
esac
