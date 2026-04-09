#!/usr/bin/env bash
set -euo pipefail

##TEST##
WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/AAQAOnJzpCw/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jYbhXk_XMLcRCfPZyFoYOJvcZ6gmR1cBOWUh4cMI7a8"
##GUARDIA##
#WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/AAQA7LOFqoE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=qqkLTkdZhr6hg9pOL5bYfQBdzOOhOjc3DwSgX4xtGjk"

PROJECTS=(
  "CDS::WMS|gke_cpl-cs-wms-prod-30112023_us-central1_gke-cs-wms-prod-01|wms"
  "CDS::TMS|gke_cpl-cmanager-prod-13072023_us-central1_gke-cmanager-prod-01|tms"
  "CDS::OMS|gke_cpl-oms-prod-08062023_us-central1_gke-oms-producto-prod|oms"
  "CDS::CSC|gke_cpl-cs-csc-prod-16112023_us-central1_gke-cs-csc-prod-01|csc"
  "TIENDAS::NPV|gke_cpl-rt-npv-prod-14052024_us-central1_gke-rt-npv-prod-02|pos"
  "POSTVENTA::Postventa|gke_cpl-rt-postvta-prod-11052024_us-central1_gke-rt-postvta-prod-01|postventa"
  "POSTVENTA::Etiquetas|gke_cpl-rt-postvta-prod-11052024_us-central1_gke-rt-postvta-prod-01|etiquetas"
  "POSTVENTA::Services|gke_cpl-rt-postvta-prod-11052024_us-central1_gke-rt-postvta-prod-01|services"
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

TOTAL_GLOBAL=0
OK_GLOBAL=0
CAIDOS_GLOBAL=0
DETALLE_CAIDOS=""

MESSAGE="*📊 Reporte SRE – Monitoreo RETAIL (Tiendas, Cadena de Suministros)*\n"
MESSAGE+="🗓 Fecha y hora (Culiacán): $(TZ=America/Mazatlan date '+%d/%m/%Y %H:%M:%S')\n\n"

CURRENT_PROJECT=""

for ITEM in "${PROJECTS[@]}"; do
  IFS="::" read -r PROJECT_KEY DATA <<< "$ITEM"
  IFS="|" read -r PROYECTO CONTEXT NAMESPACE <<< "$DATA"

  if [[ "$PROJECT_KEY" != "$CURRENT_PROJECT" ]]; then
    MESSAGE+="\n *$PROJECT_KEY*\n"
    CURRENT_PROJECT="$PROJECT_KEY"
  fi

  CLEAN_PROYECTO=$(echo "$PROYECTO" | sed 's/^://')
  MESSAGE+="\n📁 *$CLEAN_PROYECTO*\n"
  MESSAGE+="• Cluster: $CONTEXT\n"
  MESSAGE+="• Namespace: $NAMESPACE\n"

  if ! kubectl --context "$CONTEXT" get ns "$NAMESPACE" &>/dev/null; then
    MESSAGE+="  ❌ Sin acceso al namespace\n"
    continue
  fi

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

  MESSAGE+="• Total servicios: $TOTAL_PROYECTO\n"
  MESSAGE+="• Servicios caídos: $CAIDOS_PROYECTO\n"
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

MESSAGE+="👤 Quién reporta: SRE Retail\n"

MESSAGE=$(printf "%b" "$MESSAGE")

curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg text "$MESSAGE" '{text: $text}')"
