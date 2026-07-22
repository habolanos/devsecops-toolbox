#!/bin/bash
set -euo pipefail

CONFIG_FILE="config.env"
source "$CONFIG_FILE"

OUTPUT_DIR="./deployments_yaml"
LOG_FILE="limits_analysis.log"

# Colores para output
COLOR_GREEN="\033[0;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[0;31m"
COLOR_RESET="\033[0m"

mkdir -p "$OUTPUT_DIR"
: > "$LOG_FILE"

log_info() {
  echo -e "${COLOR_GREEN}[INFO]${COLOR_RESET} $1" | tee -a "$LOG_FILE"
}

log_warn() {
  echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1" | tee -a "$LOG_FILE"
}

log_error() {
  echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" | tee -a "$LOG_FILE"
}

TOTAL_CLUSTERS="${#CLUSTERS[@]}"
CURRENT=0

for CLUSTER in "${CLUSTERS[@]}"; do
  CURRENT=$((CURRENT + 1))
  
  log_info "[$CURRENT/$TOTAL_CLUSTERS] Procesando: $CLUSTER"

  # Extraer componentes del nombre
  PROJECT_ID=$(echo "$CLUSTER" | cut -d'_' -f2)
  REGION=$(echo "$CLUSTER" | cut -d'_' -f3)
  CLUSTER_NAME=$(echo "$CLUSTER" | cut -d'_' -f4-)

  log_info "  Proyecto: $PROJECT_ID"
  log_info "  Región: $REGION"
  log_info "  Clúster: $CLUSTER_NAME"

  # Obtener credenciales
  log_info "  Obteniendo credenciales..."
  if ! gcloud container clusters get-credentials "$CLUSTER_NAME" \
    --zone "$REGION" \
    --project "$PROJECT_ID" 2>&1 | tee -a "$LOG_FILE"; then
    log_error "  Falló al obtener credenciales para $CLUSTER_NAME"
    continue
  fi

  # Cambiar contexto
  log_info "  Cambiando contexto kubectl..."
  if ! kubectx "$CLUSTER" 2>&1 | tee -a "$LOG_FILE"; then
    log_error "  Falló al cambiar contexto a $CLUSTER"
    continue
  fi

  # Ejecutar análisis con timeout de 10 minutos
  log_info "  Iniciando análisis de límites (esto puede tomar 3-5 minutos)..."
  if timeout 600 python3 history_limits_v3.py "$PROJECT_ID" "$CLUSTER_NAME" 2>&1 | tee -a "$LOG_FILE"; then
    log_info "  ✅ Análisis completado para $CLUSTER_NAME"
  else
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 124 ]]; then
      log_error "  ⏱️ Timeout: análisis excedió 10 minutos para $CLUSTER_NAME"
    else
      log_error "  ❌ Análisis falló con código $EXIT_CODE para $CLUSTER_NAME"
    fi
    continue
  fi

  # Limpiar directorio temporal
  rm -rf "$OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
done

# Limpiar
rm -rf "$OUTPUT_DIR"

log_info "✅ Procesamiento completado. Ver $LOG_FILE para detalles."
