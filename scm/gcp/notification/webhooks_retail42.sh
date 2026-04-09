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
  "RETAIL::NPV|gke_cpl-rt-npv-prod-14052024_us-central1_gke-rt-npv-prod-02|pos"
  ###########################################################################################################
  "POSTVENTA::Postventa|gke_cpl-rt-postvta-prod-11052024_us-central1_gke-rt-postvta-prod-01|postventa"
  "POSTVENTA::Etiquetas|gke_cpl-rt-postvta-prod-11052024_us-central1_gke-rt-postvta-prod-01|etiquetas"
  "POSTVENTA::Services|gke_cpl-rt-postvta-prod-11052024_us-central1_gke-rt-postvta-prod-01|services"
  ###########################################################################################################
  "PVM::pvm|gke_cpl-rt-npvm-prod-04062024_us-central1_gke-rt-npvm-prod-01|pvm"
  ###########################################################################################################
  "INVENTARIOS::bo-prod-gke|gke_cpl-tda-bo-prod-06052025_us-central1_gke-tda-bo-prod-01|bo-prod-gke"
  "INVENTARIOS::inventory-movements|gke_cpl-tda-bo-prod-06052025_us-central1_gke-tda-bo-prod-01|inventory-movements"
  "INVENTARIOS::backoffice|gke_cpl-tda-bo-prod-06052025_us-central1_gke-tda-bo-prod-01|backoffice"
  ###########################################################################################################
  "TIENDA::opadmin|gke_cpl-tda-dir-prod-21042025_us-central1_gke-tda-dir-prod-01|opadmin"
  ###########################################################################################################
  "CDS::WMS|gke_cpl-cs-wms-prod-30112023_us-central1_gke-cs-wms-prod-01|wms"
  "CDS::TMS|gke_cpl-cmanager-prod-13072023_us-central1_gke-cmanager-prod-01|tms"
  "CDS::OMS|gke_cpl-oms-prod-08062023_us-central1_gke-oms-producto-prod|oms"
  "CDS::CSC|gke_cpl-cs-csc-prod-16112023_us-central1_gke-cs-csc-prod-01|csc"
  ###########################################################################################################
  "COMERCIAL::ComprasMuebles|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|comprasmuebles"
  "COMERCIAL::Comprasropa|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|comprasropa"
  "COMERCIAL::Consolidadora|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|consolidadora"
  "COMERCIAL::Hardline|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|hardline"
  "COMERCIAL::Importacion|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|importacion"
  "COMERCIAL::Promotions|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|promotions"
  "COMERCIAL::Rmi|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|rmi"
  "COMERCIAL::Siscomprasropa|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|siscomprasropa"
  "COMERCIAL::Sistimp|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|sistimp"
  "COMERCIAL::Softline|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|softline"
  "COMERCIAL::Items|gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01|items"
  ###########################################################################################################
  "Juridico::Juridicolegal1|gke_cpl-corp-jursaj-prod-26042024_us-central1_gke-corp-jursaj-prod-01|juridicolegal1"
  "Juridico::Juridicolegal2|gke_cpl-corp-jursaj-prod-26042024_us-central1_gke-corp-jursaj-prod-01|juridicolegal2"
  "Juridico::Juridicolegal3|gke_cpl-corp-jursaj-prod-26042024_us-central1_gke-corp-jursaj-prod-01|juridicolegal3"
  ###########################################################################################################
  "Coupa::Coupa|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|coupa"
  "Coupa::Coupa-general|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|coupa-general"
  "Coupa::Coupa-integration-platform|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|coupa-integration-platform"
  "Coupa::Coupa-items|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|coupa-items"
  "Coupa::Coupa-purchase-orders|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|coupa-purchase-orders"
  "Coupa::Obras|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|obras"
  "Coupa::Portal-unico-coupa-obras|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|portal-unico-coupa-obras"
  "Coupa::Portal-unico-coupa-portalsim|gke_cpl-corp-coupa-prod-09052024_us-central1_gke-corp-cupa-prod-01|portal-unico-coupa-portalsim"
  ###########################################################################################################
  "Colaborapp::Colaborapp|gke_cpl-corp-colaborapp-prd-220524_us-central1_gke-corp-colaborapp-prod-01|colaborapp"
  ###########################################################################################################
  "Biometricos::Biometric-web-finger|gke_cpl-rt-biomtrcs-prod-170402024_us-central1_gke-rt-biomtrics-prod-01|biometric-web-finger"
  "Biometricos::Finger-engine-10|gke_cpl-rt-biomtrcs-prod-170402024_us-central1_gke-rt-biomtrics-prod-01|finger-engine-10"
  "Biometricos::Fingerprint-validate|gke_cpl-rt-biomtrcs-prod-170402024_us-central1_gke-rt-biomtrics-prod-01|fingerprint-validate"
  "Biometricos::Huellasenlinea|gke_cpl-rt-biomtrcs-prod-170402024_us-central1_gke-rt-biomtrics-prod-01|huellasenlinea"
  "Biometricos::Huellasprimavera|gke_cpl-rt-biomtrcs-prod-170402024_us-central1_gke-rt-biomtrics-prod-01|huellasprimavera"
  "Biometricos::Remesas|gke_cpl-rt-biomtrcs-prod-170402024_us-central1_gke-rt-biomtrics-prod-01|remesas"
  "Biometricos::Replicas|gke_cpl-rt-biomtrcs-prod-170402024_us-central1_gke-rt-biomtrics-prod-01|replicas"
)

# Progress indicator
TOTAL_PROJECTS=${#PROJECTS[@]}
CURRENT_INDEX=0

TOTAL_GLOBAL=0
OK_GLOBAL=0
CAIDOS_GLOBAL=0
DETALLE_CAIDOS=""

# Check for simple flag
SIMPLE_OUTPUT=false
if [[ "${1:-}" == "--simple" ]]; then
    SIMPLE_OUTPUT=true
fi

# Check for simple-estable flag
if [[ "${1:-}" == "--simple-estable" ]]; then
    # Calcular TOTAL_GLOBAL, OK_GLOBAL contando deployments
    TOTAL_GLOBAL=0
    OK_GLOBAL=0
    SUMMARY_PROJECT_KEY=""
    for ITEM in "${PROJECTS[@]}"; do
        IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
        IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"
        [[ -z "$SUMMARY_PROJECT_KEY" ]] && SUMMARY_PROJECT_KEY="$PROJECT_KEY"
        if kubectl --context "$CONTEXT" get ns "$NAMESPACE" &>/dev/null; then
            DEPLOYMENTS=$(kubectl --context "$CONTEXT" -n "$NAMESPACE" get deploy \
                -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.readyReplicas}{"|"}{.status.replicas}{"\n"}{end}' 2>/dev/null)
            while IFS="|" read -r NAME READY TOTAL; do
                READY=${READY:-0}
                TOTAL=${TOTAL:-0}
                [[ "$TOTAL" -eq 0 ]] && continue
                TOTAL_GLOBAL=$((TOTAL_GLOBAL + 1))
                if [[ "$READY" -gt 0 ]]; then
                    OK_GLOBAL=$((OK_GLOBAL + 1))
                fi
            done <<< "$DEPLOYMENTS"
        fi
    done

    MESSAGE="📣 Reporte Monitoreo $SUMMARY_PROJECT_KEY\n\n"
    MESSAGE+="• Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
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
    # Calcular TOTAL_GLOBAL, OK_GLOBAL y CAIDOS_GLOBAL contando deployments
    TOTAL_GLOBAL=0
    OK_GLOBAL=0
    CAIDOS_GLOBAL=0
    SUMMARY_PROJECT_KEY=""
    for ITEM in "${PROJECTS[@]}"; do
        IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
        IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"
        [[ -z "$SUMMARY_PROJECT_KEY" ]] && SUMMARY_PROJECT_KEY="$PROJECT_KEY"
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
                else
                    OK_GLOBAL=$((OK_GLOBAL + 1))
                fi
            done <<< "$DEPLOYMENTS"
        fi
    done

    MESSAGE="📣 Reporte Monitoreo $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="• Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
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
    # Calcular TOTAL_GLOBAL, OK_GLOBAL y CAIDOS_GLOBAL contando deployments
    TOTAL_GLOBAL=0
    OK_GLOBAL=0
    CAIDOS_GLOBAL=0
    SUMMARY_PROJECT_KEY=""
    for ITEM in "${PROJECTS[@]}"; do
        IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
        IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"
        [[ -z "$SUMMARY_PROJECT_KEY" ]] && SUMMARY_PROJECT_KEY="$PROJECT_KEY"
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
                else
                    OK_GLOBAL=$((OK_GLOBAL + 1))
                fi
            done <<< "$DEPLOYMENTS"
        fi
    done

    MESSAGE="📣 Reporte Monitoreo finalización de Operación $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="• Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
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
    # Calcular TOTAL_GLOBAL, OK_GLOBAL y CAIDOS_GLOBAL contando deployments
    TOTAL_GLOBAL=0
    OK_GLOBAL=0
    CAIDOS_GLOBAL=0
    SUMMARY_PROJECT_KEY=""
    for ITEM in "${PROJECTS[@]}"; do
        IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
        IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"
        [[ -z "$SUMMARY_PROJECT_KEY" ]] && SUMMARY_PROJECT_KEY="$PROJECT_KEY"
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
                else
                    OK_GLOBAL=$((OK_GLOBAL + 1))
                fi
            done <<< "$DEPLOYMENTS"
        fi
    done

    MESSAGE="📣 Reporte Monitoreo $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="• Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
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
    # Calcular TOTAL_GLOBAL, OK_GLOBAL y CAIDOS_GLOBAL contando deployments
    TOTAL_GLOBAL=0
    OK_GLOBAL=0
    CAIDOS_GLOBAL=0
    SUMMARY_PROJECT_KEY=""
    for ITEM in "${PROJECTS[@]}"; do
        IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
        IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"
        [[ -z "$SUMMARY_PROJECT_KEY" ]] && SUMMARY_PROJECT_KEY="$PROJECT_KEY"
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
                else
                    OK_GLOBAL=$((OK_GLOBAL + 1))
                fi
            done <<< "$DEPLOYMENTS"
        fi
    done

    FECHA=$(TZ=America/Mazatlan date '+%d/%m/%Y')
    HORA=$(TZ=America/Mazatlan date '+%-I:%M %p')

    MESSAGE="📣 Reporte $SUMMARY_PROJECT_KEY\n"
    MESSAGE+="📅 Fecha: $FECHA\n"
    MESSAGE+="🕒 Hora: $HORA Culiacan Time\n\n"
    MESSAGE+="Incidente activo: No\n"
    MESSAGE+="📌 Estatus breve:\n"
    MESSAGE+="No se reporta ningún problemas dentro de los servicios.\n"
    MESSAGE+="• Servicios monitoreados: $TOTAL_GLOBAL de $TOTAL_PROJECTS namespaces\n"
    MESSAGE+="• Operando normalmente: $OK_GLOBAL ✅\n"
    MESSAGE+="• Servicios caídos: $CAIDOS_GLOBAL\n\n"
    MESSAGE+="🛠️ Acciones requeridas por SRE:\n"
    MESSAGE+="Monitoreo en servicios productivos.\n"
    MESSAGE+="Continuar validación de alertas.\n"
    MESSAGE+="👤 Quien reporta:\n"
    MESSAGE+="SRE Equipo Softtek - Harold Adrian\n"

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
MESSAGE+="🗓 Fecha y hora (Culiacán): $(TZ=America/Mazatlan date '+%d/%m/%Y %H:%M:%S')\n\n"

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

if [ "$SIMPLE_OUTPUT" = true ]; then
    MESSAGE+="👤 Quién reporta: SRE Retail - Harold Adrian\n"
else
    MESSAGE+="👤 Quién reporta: Equipo Softtek SE\n"
fi

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