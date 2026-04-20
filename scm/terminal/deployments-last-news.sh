#!/usr/bin/env bash

# =============================================================================
# Script: deployments-last-news.sh
# Descripción: Muestra los deployments más recientes por fecha de creación
# Uso: ./deployments-last-news.sh [numero]
# =============================================================================
# Agnostic: Kubernetes (kubectl) - Works with any K8s cluster

NUM=${1:-${TERMINAL_K8S_LIMIT:-15}}
TZ_ZONE=${TERMINAL_TIMEZONE:-"America/Mazatlan"}

echo "============================================================="
echo "  Deployments más recientes (ordenados por creación)"
echo "  Zona horaria: ${TZ_ZONE} (UTC-7)"
echo "  Mostrando: ${NUM}"
echo "============================================================="
echo ""

kubectl get deployments --all-namespaces \
  --sort-by=.metadata.creationTimestamp \
  -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\t"}{.spec.replicas}{"\n"}{end}' \
  | sort -k3 -r \
  | head -n "$NUM" | while read -r ns name ts replicas; do
    # Convierte UTC a zona horaria configurada
    local_time=$(TZ="$TZ_ZONE" date -d "$ts" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || echo "N/A")
    printf "%-15s %-35s %-25s %s\n" "$ns" "$name" "$local_time" "$replicas"
  done

echo ""
echo "Nota: Las fechas muestran la hora local configurada."
