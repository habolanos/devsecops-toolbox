#!/usr/bin/env bash

# =============================================================================
# Script: deployments_last_update_list.sh
# Descripción: Muestra deployments ordenados por la fecha de su ÚLTIMO ROLLOUT
#              (usando creationTimestamp del ReplicaSet actual)
# Zona horaria: America/Mazatlan (UTC-7)
# Uso: ./deployments_last_update_list.sh [número] [namespace opcional]
# Ejemplo: ./deployments_last_update_list.sh 15 prod
# =============================================================================

TZ_ZONE="America/Mazatlan"
NUM=${1:-10}                     # Por defecto top 10
NS_FILTER=${2:-}                 # Namespace opcional

echo "============================================================="
echo "  Deployments ordenados por ÚLTIMA ACTUALIZACIÓN (rollout más reciente)"
echo "  Zona: ${TZ_ZONE} (UTC-7)"
echo "  Mostrando: ${NUM}"
[ -n "$NS_FILTER" ] && echo "  Solo namespace: ${NS_FILTER}"
echo "============================================================="
echo ""

# Función para convertir UTC a Mazatlán
to_mazatlan() {
    TZ="$TZ_ZONE" date -d "$1" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || echo "N/A"
}

# Recolectar datos: namespace, deployment, revision actual, replicas, y timestamp del RS actual
declare -a results=()

while IFS=$'\t' read -r ns dep rev replicas; do
    # Buscar el ReplicaSet actual (mismo revision que el deployment)
    rs_info=$(kubectl get rs -n "$ns" -l "app.kubernetes.io/instance=$dep" \
        --field-selector metadata.annotations."deployment\.kubernetes\.io/revision"="$rev" \
        -o jsonpath='{.items[0].metadata.name}{"\t"}{.items[0].metadata.creationTimestamp}' 2>/dev/null)

    if [[ -n "$rs_info" ]]; then
        rs_name=$(echo "$rs_info" | cut -f1)
        rs_ts=$(echo "$rs_info" | cut -f2)
        local_ts=$(to_mazatlan "$rs_ts")
        results+=("$ns"$'\t'"$dep"$'\t'"$local_ts"$'\t'"$rev"$'\t'"$replicas"$'\t'"$rs_name")
    else
        # Fallback si no encuentra RS (deployment sin rollout o error)
        results+=("$ns"$'\t'"$dep"$'\t'"N/A"$'\t'"$rev"$'\t'"$replicas"$'\t'"N/A")
    fi
done < <(kubectl get deploy ${NS_FILTER:+-n "$NS_FILTER"} -A \
    -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,REV:.metadata.annotations.deployment\.kubernetes\.io/revision,REPLICAS:.spec.replicas" \
    --no-headers)

# Ordenar por timestamp descendente (más reciente primero)
# Convertimos a epoch para ordenar numéricamente
printf '%s\n' "${results[@]}" | while IFS=$'\t' read ns dep ts rev rep rs; do
    if [[ "$ts" != "N/A" ]]; then
        epoch=$(date -d "$ts" +%s 2>/dev/null || echo 0)
    else
        epoch=0
    fi
    echo "$epoch"$'\t'"$ns"$'\t'"$dep"$'\t'"$ts"$'\t'"gen:$rev"$'\t'"rep:$rep"$'\t'"rs:$rs"
done | sort -k1 -r -n | head -n "$NUM" | cut -d$'\t' -f2- | while IFS=$'\t' read ns dep ts gen rep rs; do
    printf "%-15s %-40s %-22s %-8s %-10s %s\n" "$ns" "$dep" "$ts" "$gen" "$rep" "$rs"
done

echo ""
echo "Nota: La fecha es la creación del ReplicaSet actual (≈ último rollout exitoso)."
echo "Si un deployment no tiene RS asociado → muestra N/A (poco común)."
echo "Para detalles de un rollout: kubectl rollout history deploy/NOMBRE -n NAMESPACE"