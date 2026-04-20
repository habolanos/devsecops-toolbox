#!/usr/bin/env bash

# =============================================================================
# Script: deployments-recent-events.sh
# Descripción: Muestra los eventos más recientes relacionados con Deployments
#              en el clúster Kubernetes, con fechas convertidas a zona local
# Uso: ./deployments-recent-events.sh [número de eventos] [namespace opcional]
# Ejemplo: ./deployments-recent-events.sh 20 prod
# =============================================================================
# Agnostic: Kubernetes (kubectl) - Works with any K8s cluster

# Colores para la salida
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parámetros opcionales
NUM_EVENTS=${1:-20}               # Por defecto muestra los últimos 20
NAMESPACE_FILTER=${2:-}             # Si pasas un namespace, filtra solo ese

# Zona horaria deseada
TZ_ZONE="America/Mazatlan"

# Función para convertir timestamp Kubernetes a hora local
convert_to_local() {
    local utc_time="$1"
    # date -d espera formato ISO, Kubernetes usa Z (UTC)
    TZ="$TZ_ZONE" date -d "$utc_time" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || echo "Invalid time"
}

echo "============================================================="
echo "  Últimos eventos relacionados con Deployments"
echo "  Zona horaria: ${TZ_ZONE} (UTC-7)"
echo "  Mostrando: $NUM_EVENTS eventos"
if [ -n "$NAMESPACE_FILTER" ]; then
    echo "  Filtrando namespace: $NAMESPACE_FILTER"
fi
echo "  Fecha actual: $(TZ="$TZ_ZONE" date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================="
echo ""

# Construir el comando kubectl
CMD="kubectl get events --all-namespaces --field-selector involvedObject.kind=Deployment --sort-by=.metadata.creationTimestamp"

if [ -n "$NAMESPACE_FILTER" ]; then
    CMD="kubectl get events -n $NAMESPACE_FILTER --field-selector involvedObject.kind=Deployment --sort-by=.metadata.creationTimestamp"
fi

# Ejecutar y procesar salida
$CMD -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.involvedObject.name}{"\t"}{.metadata.creationTimestamp}{"\t"}{.type}{"\t"}{.reason}{"\t"}{.message}{"\n"}{end}' \
    | sort -k3 -r \
    | head -n "$NUM_EVENTS" \
    | while read -r ns deploy ts type reason msg; do
        local_time=$(convert_to_local "$ts")
        color="$NC"
        case "$type" in
            "Normal")   color="$GREEN" ;;
            "Warning")  color="$YELLOW" ;;
            *)          color="$RED" ;;
        esac
        printf "%-15s %-40s %-25s %-10s %-20s %s\n" \
            "$ns" \
            "$deploy" \
            "$local_time" \
            "${color}$type${NC}" \
            "$reason" \
            "$msg"
      done

echo ""
echo "============================================================="
echo "Nota: Eventos ordenados del más reciente al más antiguo."
echo "Tipos comunes: Normal (éxito), Warning (problema)."
echo "Para más detalles de un deployment: kubectl describe deployment NOMBRE -n NAMESPACE"
