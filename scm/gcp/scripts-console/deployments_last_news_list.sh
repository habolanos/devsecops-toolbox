#!/usr/bin/env bash

# Script: list-recent-deployments-mazatlan.sh
# Muestra los deployments más recientes con fecha en America/Mazatlan

echo "============================================================="
echo "  Deployments más recientes (ordenados por creación)"
echo "  Zona horaria: America/Mazatlan (UTC-7)"
echo "============================================================="
echo ""

kubectl get deployments --all-namespaces \
  --sort-by=.metadata.creationTimestamp \
  -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\t"}{.spec.replicas}{"\n"}{end}' \
  | sort -k3 -r \
  | head -n 15 | while read -r ns name ts replicas; do
    # Convierte UTC a America/Mazatlan
    local_time=$(TZ='America/Mazatlan' date -d "$ts" '+%Y-%m-%d %H:%M:%S %Z')
    printf "%-15s %-35s %-25s %s\n" "$ns" "$name" "$local_time" "$replicas"
  done

echo ""
echo "Nota: Las fechas muestran la hora local en Mazatlán (sin horario de verano)."