#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# GKE multi-project capacity, utilization and health status report
#
# Uso:
#   ./gke_report.sh
#   ./gke_report.sh "proyecto1,proyecto2,proyecto3"
# ============================================================================

if [[ $# -ge 1 && -n "$1" ]]; then
  PROJECTS_RAW="$1"
else
  PROJECTS_RAW="cpl-cmanager-dev-13072023,cpl-cmanager-qa-13072023,cpl-cmanager-stag-01052025,cpl-cs-csc-dev-16112023,cpl-cs-csc-qa-16112023,cpl-cs-csc-stag-11042025,cpl-cs-wms-dev-30112023,cpl-cs-wms-qa-30112023,cpl-cs-wms-stag-09042025,cpl-oms-dev-08082024,cpl-oms-qa-08062023,cpl-oms-stag-09042025"
fi

WINDOW="24h"
MONITORING_API="https://monitoring.googleapis.com/v3"
WARNING_THRESHOLD=75
CRITICAL_THRESHOLD=90

# Colores ANSI.
COLOR_RESET="\033[0m"
COLOR_GREEN="\033[0;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[0;31m"
COLOR_GRAY="\033[0;37m"
COLOR_CYAN="\033[0;36m"
COLOR_BOLD="\033[1m"

# Validar herramientas requeridas.
for command in gcloud curl jq awk; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "Error: el comando '${command}' no está instalado." >&2
    exit 1
  fi
done

IFS=',' read -ra PROJECTS <<< "${PROJECTS_RAW}"
for i in "${!PROJECTS[@]}"; do
  PROJECTS[$i]="$(echo "${PROJECTS[$i]}" | tr -d '[:space:]')"
done

TOTAL_PROJECTS="${#PROJECTS[@]}"

# ============================================================================
# Spinner y barra de progreso
# ============================================================================

# PID del spinner (se guarda para poder detenerlo).
SPINNER_PID=""

# Archivo temporal para comunicar el mensaje de estado al spinner.
STATUS_FILE="$(mktemp)"
PROGRESS_FILE="$(mktemp)"

# Limpieza al salir (Ctrl+C o error).
cleanup() {
  [[ -n "${SPINNER_PID}" ]] && kill "${SPINNER_PID}" 2>/dev/null || true
  rm -f "${STATUS_FILE}" "${PROGRESS_FILE}"
  # Restaurar cursor y limpiar línea.
  tput cnorm 2>/dev/null || true
  printf "\r\033[K" >&2
}
trap cleanup EXIT

# Dibuja la barra de progreso y el spinner en una sola línea.
# Lee el mensaje actual desde STATUS_FILE y el progreso desde PROGRESS_FILE.
run_spinner() {
  local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  local frame_index=0

  # Ocultar cursor durante la animación.
  tput civis 2>/dev/null || true

  while true; do
    local current_status current_progress
    current_status="$(cat "${STATUS_FILE}" 2>/dev/null || echo "Iniciando...")"
    current_progress="$(cat "${PROGRESS_FILE}" 2>/dev/null || echo "0/${TOTAL_PROJECTS}")"

    local done_count total_count
    done_count="$(echo "${current_progress}" | cut -d'/' -f1)"
    total_count="$(echo "${current_progress}" | cut -d'/' -f2)"

    # Calcular barra de progreso (ancho fijo de 30 caracteres).
    local bar_width=30
    local filled=0
    if [[ "${total_count}" -gt 0 ]]; then
      filled=$(( done_count * bar_width / total_count ))
    fi
    local empty=$(( bar_width - filled ))

    local bar=""
    bar+="${COLOR_GREEN}"
    for (( i=0; i<filled; i++ )); do bar+="█"; done
    bar+="${COLOR_GRAY}"
    for (( i=0; i<empty; i++ )); do bar+="░"; done
    bar+="${COLOR_RESET}"

    local frame="${frames[$frame_index]}"
    frame_index=$(( (frame_index + 1) % ${#frames[@]} ))

    # Imprimir en una sola línea sobreescribible.
    printf "\r\033[K ${COLOR_CYAN}%s${COLOR_RESET} [%b] %s/%s  %s" \
      "${frame}" \
      "${bar}" \
      "${done_count}" \
      "${total_count}" \
      "${current_status}" >&2

    sleep 0.1
  done
}

update_status() {
  printf '%s' "$1" > "${STATUS_FILE}"
}

update_progress() {
  printf '%s' "$1" > "${PROGRESS_FILE}"
}

# ============================================================================
# Funciones de consulta y formato
# ============================================================================

TOKEN=""

refresh_token() {
  TOKEN="$(gcloud auth print-access-token)"
  if [[ -z "${TOKEN}" ]]; then
    echo "Error: no fue posible obtener un token." >&2
    exit 1
  fi
}

query_monitoring() {
  local project_id="$1"
  local mql_query="$2"

  curl -sS -X POST \
    "${MONITORING_API}/projects/${project_id}/timeSeries:query" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg query "${mql_query}" '{query: $query}')"
}

get_latest_value() {
  jq -r '
    [
      .timeSeriesData[]?
      | .pointData[]?
      | .values[]?
      | (.doubleValue? // .int64Value? // empty)
    ]
    | first // empty
  '
}

get_api_error() {
  jq -r '.error.message? // empty'
}

format_cores() {
  local value="$1"
  if [[ -n "${value}" ]]; then
    awk -v v="${value}" 'BEGIN { printf "%.2f cores", v }'
  else
    printf "N/A"
  fi
}

format_gib() {
  local value_bytes="$1"
  if [[ -n "${value_bytes}" ]]; then
    awk -v v="${value_bytes}" 'BEGIN { printf "%.2f GiB", v / (1024*1024*1024) }'
  else
    printf "N/A"
  fi
}

format_percent() {
  local value="$1"
  if [[ -n "${value}" ]]; then
    awk -v v="${value}" 'BEGIN { printf "%.2f%%", v * 100 }'
  else
    printf "N/A"
  fi
}

get_status() {
  local cpu_util="$1"
  local memory_util="$2"

  if [[ -z "${cpu_util}" || -z "${memory_util}" ]]; then
    printf "${COLOR_GRAY}⚪ SIN DATOS${COLOR_RESET}"
    return
  fi

  awk \
    -v cpu="${cpu_util}" \
    -v memory="${memory_util}" \
    -v warning="${WARNING_THRESHOLD}" \
    -v critical="${CRITICAL_THRESHOLD}" \
    -v green="${COLOR_GREEN}" \
    -v yellow="${COLOR_YELLOW}" \
    -v red="${COLOR_RED}" \
    -v reset="${COLOR_RESET}" \
    'BEGIN {
      max_util = cpu > memory ? cpu : memory
      max_percent = max_util * 100
      if (max_percent >= critical)      printf "%s🔴 CRITICO%s",     red,    reset
      else if (max_percent >= warning)  printf "%s🟡 ADVERTENCIA%s", yellow, reset
      else                              printf "%s🟢 OK%s",          green,  reset
    }'
}

# ============================================================================
# Recolección de datos (acumula filas en el array TABLE_ROWS)
# ============================================================================

declare -a TABLE_ROWS=()

process_project() {
  local project="$1"
  local project_index="$2"

  refresh_token

  update_status "Listando clústeres de ${project}..."
  update_progress "${project_index}/${TOTAL_PROJECTS}"

  local clusters
  clusters="$(
    gcloud container clusters list \
      --project="${project}" \
      --format="value(name,location)" \
      --quiet 2>/dev/null || true
  )"

  if [[ -z "${clusters}" ]]; then
    update_status "Sin clústeres en ${project}, omitiendo..."
    return
  fi

  local cluster_count
  cluster_count="$(echo "${clusters}" | wc -l | tr -d ' ')"
  local cluster_index=0

  while IFS=$'\t' read -r CLUSTER_NAME LOCATION; do
    [[ -z "${CLUSTER_NAME}" ]] && continue

    cluster_index=$(( cluster_index + 1 ))
    update_status "$(printf "[%d/%d clústeres] %s → %s" \
      "${cluster_index}" "${cluster_count}" "${project}" "${CLUSTER_NAME}")"

    local CPU_TOTAL_RESPONSE MEMORY_TOTAL_RESPONSE CPU_UTIL_RESPONSE MEMORY_UTIL_RESPONSE

    CPU_TOTAL_RESPONSE="$(
      query_monitoring "${project}" \
        "fetch k8s_node | metric 'kubernetes.io/node/cpu/allocatable_cores' | filter resource.cluster_name == '${CLUSTER_NAME}' && resource.location == '${LOCATION}' | within ${WINDOW} | group_by [], sum(val())"
    )"

    MEMORY_TOTAL_RESPONSE="$(
      query_monitoring "${project}" \
        "fetch k8s_node | metric 'kubernetes.io/node/memory/allocatable_bytes' | filter resource.cluster_name == '${CLUSTER_NAME}' && resource.location == '${LOCATION}' | within ${WINDOW} | group_by [], sum(val())"
    )"

    CPU_UTIL_RESPONSE="$(
      query_monitoring "${project}" \
        "fetch k8s_node | metric 'kubernetes.io/node/cpu/allocatable_utilization' | filter resource.cluster_name == '${CLUSTER_NAME}' && resource.location == '${LOCATION}' | within ${WINDOW} | group_by [], mean(val())"
    )"

    MEMORY_UTIL_RESPONSE="$(
      query_monitoring "${project}" \
        "fetch k8s_node | metric 'kubernetes.io/node/memory/allocatable_utilization' | filter resource.cluster_name == '${CLUSTER_NAME}' && resource.location == '${LOCATION}' | within ${WINDOW} | group_by [], mean(val())"
    )"

    local CPU_TOTAL MEMORY_TOTAL_BYTES CPU_UTIL MEMORY_UTIL

    CPU_TOTAL="$(printf '%s' "${CPU_TOTAL_RESPONSE}" | get_latest_value)"
    MEMORY_TOTAL_BYTES="$(printf '%s' "${MEMORY_TOTAL_RESPONSE}" | get_latest_value)"
    CPU_UTIL="$(printf '%s' "${CPU_UTIL_RESPONSE}" | get_latest_value)"
    MEMORY_UTIL="$(printf '%s' "${MEMORY_UTIL_RESPONSE}" | get_latest_value)"

    local CPU_TOTAL_F MEMORY_TOTAL_F CPU_UTIL_F MEMORY_UTIL_F STATUS

    CPU_TOTAL_F="$(format_cores "${CPU_TOTAL}")"
    MEMORY_TOTAL_F="$(format_gib "${MEMORY_TOTAL_BYTES}")"
    CPU_UTIL_F="$(format_percent "${CPU_UTIL}")"
    MEMORY_UTIL_F="$(format_percent "${MEMORY_UTIL}")"
    STATUS="$(get_status "${CPU_UTIL}" "${MEMORY_UTIL}")"

    # Acumular fila como cadena delimitada por §  (carácter poco común).
    TABLE_ROWS+=("${project}§${CLUSTER_NAME}§${LOCATION}§${CPU_TOTAL_F}§${MEMORY_TOTAL_F}§${CPU_UTIL_F}§${MEMORY_UTIL_F}§${STATUS}")

  done <<< "${clusters}"

  update_progress "$(( project_index ))/${TOTAL_PROJECTS}"
}

# ============================================================================
# Ejecución principal
# ============================================================================

# Inicializar archivos de estado.
update_status "Iniciando..."
update_progress "0/${TOTAL_PROJECTS}"

# Lanzar spinner en background.
run_spinner &
SPINNER_PID=$!

# Procesar todos los proyectos.
project_index=0
for PROJECT_ID in "${PROJECTS[@]}"; do
  project_index=$(( project_index + 1 ))
  process_project "${PROJECT_ID}" "${project_index}"
done

# Marcar como completado antes de detener el spinner.
update_status "✓ Recopilación completada."
update_progress "${TOTAL_PROJECTS}/${TOTAL_PROJECTS}"
sleep 0.5

# Detener spinner y limpiar línea.
kill "${SPINNER_PID}" 2>/dev/null || true
SPINNER_PID=""
tput cnorm 2>/dev/null || true
printf "\r\033[K" >&2

# ============================================================================
# Imprimir tabla final limpia
# ============================================================================

printf "\n"
printf "${COLOR_BOLD}GKE Multi-Project Report${COLOR_RESET} | Ventana: %s | " "${WINDOW}"
printf "🟡 Advertencia: >= %s%% | 🔴 Crítico: >= %s%%\n\n" \
  "${WARNING_THRESHOLD}" "${CRITICAL_THRESHOLD}"

printf "${COLOR_BOLD}%-35s %-35s %-18s %14s %17s %15s %17s %-18s${COLOR_RESET}\n" \
  "PROYECTO" "CLUSTER" "UBICACION" "CPU TOTAL" "MEMORIA TOTAL" "CPU PROM." "MEMORIA PROM." "ESTADO"

printf "%-35s %-35s %-18s %14s %17s %15s %17s %-18s\n" \
  "-----------------------------------" \
  "-----------------------------------" \
  "------------------" \
  "--------------" \
  "-----------------" \
  "---------------" \
  "-----------------" \
  "------------------"

for row in "${TABLE_ROWS[@]}"; do
  IFS='§' read -r \
    R_PROJECT R_CLUSTER R_LOCATION \
    R_CPU_TOTAL R_MEM_TOTAL \
    R_CPU_UTIL R_MEM_UTIL \
    R_STATUS <<< "${row}"

  printf "%-35s %-35s %-18s %14s %17s %15s %17s %-18b\n" \
    "${R_PROJECT}" \
    "${R_CLUSTER}" \
    "${R_LOCATION}" \
    "${R_CPU_TOTAL}" \
    "${R_MEM_TOTAL}" \
    "${R_CPU_UTIL}" \
    "${R_MEM_UTIL}" \
    "${R_STATUS}"
done

printf "\n"
printf "Total clústeres reportados: %d en %d proyectos.\n\n" \
  "${#TABLE_ROWS[@]}" "${TOTAL_PROJECTS}"