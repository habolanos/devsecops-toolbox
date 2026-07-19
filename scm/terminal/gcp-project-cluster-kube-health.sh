#!/usr/bin/env bash
set +m
set -euo pipefail

# ============================================================================
# Reporte multi-proyecto de recursos Kubernetes GKE
#
# Columnas:
#   PROYECTO | CLUSTER | UBICACION | SERVICIOS | DEPLOYMENTS | PODS | STATUS
#
# Formato:
#   DEPLOYMENTS: ready|total
#   PODS:        running|activos
#
# Estado combinado:
#   ✅ OK       Deployments >= 90% Y Pods >= 90%
#   🟡 WARNING  Deployments/PODS entre los umbrales
#   🔴 CRITICAL Deployments < 50% O Pods < 50%
#   ⚠️ TIMEOUT  Falló alguna consulta kubectl
#   ❌ NO ACCESS Falló autenticación o get-credentials
#
# Ejemplos:
#   ./gke_k8s_report.sh
#   ./gke_k8s_report.sh "proyecto1,proyecto2"
#   ./gke_k8s_report.sh "proyecto1,proyecto2" 6
# ============================================================================

DEFAULT_PROJECTS="cpl-cmanager-dev-13072023,cpl-cmanager-qa-13072023,cpl-cmanager-stag-01052025,cpl-cs-csc-dev-16112023,cpl-cs-csc-qa-16112023,cpl-cs-csc-stag-11042025,cpl-cs-wms-dev-30112023,cpl-cs-wms-qa-30112023,cpl-cs-wms-stag-09042025,cpl-oms-dev-08082024,cpl-oms-qa-08062023,cpl-oms-stag-09042025"

PROJECTS_RAW="${1:-${DEFAULT_PROJECTS}}"
MAX_PARALLEL="${2:-4}"

GCLOUD_TIMEOUT_SECONDS=90
KUBECTL_TIMEOUT_SECONDS=60
KUBECTL_REQUEST_TIMEOUT="45s"

# Umbrales de salud.
DEPLOY_OK_PCT=90
DEPLOY_WARNING_PCT=50

POD_OK_PCT=90
POD_WARNING_PCT=50

# Colores ANSI.
COLOR_RESET="\033[0m"
COLOR_GREEN="\033[0;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[0;31m"
COLOR_CYAN="\033[0;36m"
COLOR_GRAY="\033[0;37m"
COLOR_BOLD="\033[1m"

# ============================================================================
# Validaciones
# ============================================================================
for command in gcloud jq kubectl timeout; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "Error: '${command}' no está instalado o no está disponible en PATH." >&2
    exit 1
  fi
done

if ! [[ "${MAX_PARALLEL}" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: MAX_PARALLEL debe ser un entero mayor que cero." >&2
  exit 1
fi

IFS=',' read -r -a PROJECTS <<< "${PROJECTS_RAW}"

CLEAN_PROJECTS=()
for project in "${PROJECTS[@]}"; do
  project="$(printf '%s' "${project}" | tr -d '[:space:]')"
  [[ -n "${project}" ]] && CLEAN_PROJECTS+=("${project}")
done

PROJECTS=("${CLEAN_PROJECTS[@]}")
TOTAL_PROJECTS="${#PROJECTS[@]}"

if [[ "${TOTAL_PROJECTS}" -eq 0 ]]; then
  echo "Error: no se recibieron proyectos para procesar." >&2
  exit 1
fi

# ============================================================================
# Archivos temporales
# ============================================================================
WORK_DIR="$(mktemp -d)"
KUBECONFIG_DIR="${WORK_DIR}/kubeconfigs"
DONE_DIR="${WORK_DIR}/done"
RESULTS_DIR="${WORK_DIR}/results"

STATUS_FILE="${WORK_DIR}/status.txt"
WARNINGS_FILE="${WORK_DIR}/warnings.txt"

mkdir -p "${KUBECONFIG_DIR}" "${DONE_DIR}" "${RESULTS_DIR}"
touch "${STATUS_FILE}" "${WARNINGS_FILE}"

SPINNER_PID=""
START_TIME="$(date +%s)"

cleanup() {
  if [[ -n "${SPINNER_PID}" ]]; then
    kill "${SPINNER_PID}" 2>/dev/null || true
    wait "${SPINNER_PID}" 2>/dev/null || true
    SPINNER_PID=""
  fi

  tput cnorm 2>/dev/null || true

  if [[ -d "${WORK_DIR}" ]]; then
    rm -rf "${WORK_DIR}"
  fi
}

trap cleanup EXIT INT TERM

# ============================================================================
# Utilidades
# ============================================================================
update_status() {
  printf '%s' "$1" > "${STATUS_FILE}" 2>/dev/null || true
}

count_completed_projects() {
  find "${DONE_DIR}" -maxdepth 1 -type f -name '*.done' 2>/dev/null | wc -l | tr -d ' '
}

repeat_char() {
  local char="$1"
  local count="$2"
  local output=""

  if [[ "${count}" -le 0 ]]; then
    printf ''
    return
  fi

  printf -v output '%*s' "${count}" ''
  printf '%s' "${output// /${char}}"
}

color_for_pct() {
  local pct="$1"
  local ok_threshold="$2"
  local warning_threshold="$3"

  if [[ "${pct}" -ge "${ok_threshold}" ]]; then
    printf '%s' "${COLOR_GREEN}"
  elif [[ "${pct}" -ge "${warning_threshold}" ]]; then
    printf '%s' "${COLOR_YELLOW}"
  else
    printf '%s' "${COLOR_RED}"
  fi
}

kubectl_with_timeout() {
  local kubeconfig_file="$1"
  shift

  KUBECONFIG="${kubeconfig_file}" \
    timeout --kill-after=5s "${KUBECTL_TIMEOUT_SECONDS}s" \
    kubectl \
      --request-timeout="${KUBECTL_REQUEST_TIMEOUT}" \
      "$@" 2>/dev/null
}

# ============================================================================
# Spinner de progreso
# ============================================================================
run_spinner() {
  local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  local frame_count="${#frames[@]}"
  local i=0

  # Protección adicional ante cualquier problema de expansión.
  if [[ "${frame_count}" -eq 0 ]]; then
    return 0
  fi

  tput civis 2>/dev/null || true

  while true; do
    local completed status_msg elapsed elapsed_min elapsed_sec
    local bar_width filled empty bar

    completed="$(count_completed_projects)"
    status_msg="$(cat "${STATUS_FILE}" 2>/dev/null || printf 'Iniciando...')"

    [[ "${completed}" =~ ^[0-9]+$ ]] || completed=0

    elapsed=$(( $(date +%s) - START_TIME ))
    elapsed_min=$(( elapsed / 60 ))
    elapsed_sec=$(( elapsed % 60 ))

    bar_width=30
    filled=$(( completed * bar_width / TOTAL_PROJECTS ))
    empty=$(( bar_width - filled ))

    bar="$(repeat_char '█' "${filled}")$(repeat_char '░' "${empty}")"

    printf "\r ${COLOR_YELLOW}%s${COLOR_RESET} [%s] %d/%d  Tiempo: %dm %02ds  ${COLOR_GRAY}%.65s${COLOR_RESET}\033[K" \
      "${frames[$i]}" \
      "${bar}" \
      "${completed}" \
      "${TOTAL_PROJECTS}" \
      "${elapsed_min}" \
      "${elapsed_sec}" \
      "${status_msg}" >&2

    i=$(( (i + 1) % frame_count ))
    sleep 0.15
  done
}

# ============================================================================
# Worker por proyecto
# ============================================================================
process_project_worker() {
  local project="$1"
  local result_file="${RESULTS_DIR}/${project}.result"
  local kubeconfig_file="${KUBECONFIG_DIR}/${project}.config"

  : > "${result_file}"
  : > "${kubeconfig_file}"

  update_status "${project}: validando sesión..."

  local token=""
  token="$(
    timeout "${GCLOUD_TIMEOUT_SECONDS}s" \
      gcloud auth print-access-token \
      --project="${project}" 2>/dev/null || true
  )"

  if [[ -z "${token}" ]]; then
    printf '%s|CREDENTIAL_FAIL\n' "${project}" >> "${result_file}"
    touch "${DONE_DIR}/${project}.done"
    return 0
  fi

  update_status "${project}: listando clústeres..."

  local clusters_json="[]"
  clusters_json="$(
    timeout "${GCLOUD_TIMEOUT_SECONDS}s" \
      gcloud container clusters list \
      --project="${project}" \
      --format='json(name,location)' 2>/dev/null || printf '[]'
  )"

  local cluster_count=0
  cluster_count="$(
    printf '%s' "${clusters_json}" | jq 'length' 2>/dev/null || printf '0'
  )"

  [[ "${cluster_count}" =~ ^[0-9]+$ ]] || cluster_count=0

  if [[ "${cluster_count}" -eq 0 ]]; then
    printf '%s|NO_CLUSTERS\n' "${project}" >> "${result_file}"
    touch "${DONE_DIR}/${project}.done"
    return 0
  fi

  local index=0

  while IFS= read -r cluster_line; do
    local cluster_name=""
    local cluster_location=""

    cluster_name="$(
      printf '%s' "${cluster_line}" | jq -r '.name // empty' 2>/dev/null
    )"

    cluster_location="$(
      printf '%s' "${cluster_line}" | jq -r '.location // empty' 2>/dev/null
    )"

    [[ -z "${cluster_name}" || -z "${cluster_location}" ]] && continue

    index=$(( index + 1 ))

    # Cada clúster utiliza un kubeconfig independiente.
    : > "${kubeconfig_file}"

    update_status "[${index}/${cluster_count}] ${project}: conectando a ${cluster_name}"

    if ! KUBECONFIG="${kubeconfig_file}" \
      timeout --kill-after=5s "${GCLOUD_TIMEOUT_SECONDS}s" \
      gcloud container clusters get-credentials "${cluster_name}" \
        --location="${cluster_location}" \
        --project="${project}" >/dev/null 2>&1; then

      printf '%s|%s|%s|CRED_FAIL\n' \
        "${project}" \
        "${cluster_name}" \
        "${cluster_location}" >> "${result_file}"

      continue
    fi

    # ------------------------------------------------------------------------
    # Servicios
    # ------------------------------------------------------------------------
    update_status "[${index}/${cluster_count}] ${project}: servicios en ${cluster_name}"

    local services_raw=""
    local service_count="N/A"

    if services_raw="$(
      kubectl_with_timeout "${kubeconfig_file}" \
        get services --all-namespaces -o json
    )"; then
      service_count="$(
        printf '%s' "${services_raw}" |
          jq '[.items[] | select(.spec.type != "ExternalName")] | length' 2>/dev/null ||
          printf 'N/A'
      )"
    else
      printf '%s/%s: timeout o error en kubectl get services\n' \
        "${project}" "${cluster_name}" >> "${WARNINGS_FILE}"
    fi

    # ------------------------------------------------------------------------
    # Deployments
    # ------------------------------------------------------------------------
    update_status "[${index}/${cluster_count}] ${project}: deployments en ${cluster_name}"

    local deployments_raw=""
    local deploy_ready="N/A"
    local deploy_total="N/A"

    if deployments_raw="$(
      kubectl_with_timeout "${kubeconfig_file}" \
        get deployments --all-namespaces -o json
    )"; then
      deploy_total="$(
        printf '%s' "${deployments_raw}" |
          jq '.items | length' 2>/dev/null ||
          printf 'N/A'
      )"

      deploy_ready="$(
        printf '%s' "${deployments_raw}" |
          jq '[.items[] | select((.status.readyReplicas // 0) >= 1)] | length' 2>/dev/null ||
          printf 'N/A'
      )"
    else
      printf '%s/%s: timeout o error en kubectl get deployments\n' \
        "${project}" "${cluster_name}" >> "${WARNINGS_FILE}"
    fi

    # ------------------------------------------------------------------------
    # Pods
    # Succeeded no cuenta como pod activo, por lo que se excluye del total.
    # ------------------------------------------------------------------------
    update_status "[${index}/${cluster_count}] ${project}: pods en ${cluster_name}"

    local pods_raw=""
    local pods_running="N/A"
    local pods_active="N/A"

    if pods_raw="$(
      kubectl_with_timeout "${kubeconfig_file}" \
        get pods --all-namespaces -o json
    )"; then

      read -r pods_running pods_active <<< "$(
        printf '%s' "${pods_raw}" |
          jq -r '
            (.items | map(select(.status.phase == "Running")) | length) as $running
            | (.items | map(select(.status.phase != "Succeeded")) | length) as $active
            | "\($running) \($active)"
          ' 2>/dev/null || printf 'N/A N/A'
      )"
    else
      printf '%s/%s: timeout o error en kubectl get pods\n' \
        "${project}" "${cluster_name}" >> "${WARNINGS_FILE}"
    fi

    printf '%s|%s|%s|%s|%s|%s|%s|%s\n' \
      "${project}" \
      "${cluster_name}" \
      "${cluster_location}" \
      "${service_count}" \
      "${deploy_ready}" \
      "${deploy_total}" \
      "${pods_running}" \
      "${pods_active}" >> "${result_file}"

  done < <(
    printf '%s' "${clusters_json}" |
      jq -c '.[]' 2>/dev/null || true
  )

  touch "${DONE_DIR}/${project}.done"
  return 0
}

# ============================================================================
# Ejecución paralela
# ============================================================================
run_spinner &
SPINNER_PID=$!

active_jobs=0

for project in "${PROJECTS[@]}"; do
  process_project_worker "${project}" &
  active_jobs=$(( active_jobs + 1 ))

  if [[ "${active_jobs}" -ge "${MAX_PARALLEL}" ]]; then
    wait -n || true
    active_jobs=$(( active_jobs - 1 ))
  fi
done

while [[ "${active_jobs}" -gt 0 ]]; do
  wait -n || true
  active_jobs=$(( active_jobs - 1 ))
done

# Detener spinner antes de imprimir la tabla.
if [[ -n "${SPINNER_PID}" ]]; then
  kill "${SPINNER_PID}" 2>/dev/null || true
  wait "${SPINNER_PID}" 2>/dev/null || true
  SPINNER_PID=""
fi

printf "\r\033[K" >&2
tput cnorm 2>/dev/null || true

# ============================================================================
# Tiempo de ejecución
# ============================================================================
END_TIME="$(date +%s)"
ELAPSED_SECONDS=$(( END_TIME - START_TIME ))
ELAPSED_MIN=$(( ELAPSED_SECONDS / 60 ))
ELAPSED_SEC=$(( ELAPSED_SECONDS % 60 ))

# ============================================================================
# Renderizado
# ============================================================================
COL_PROJECT=35
COL_CLUSTER=44
COL_LOCATION=18
COL_SERVICES=10
COL_DEPLOYMENTS=20
COL_PODS=20
COL_STATUS=18

TOTAL_CLUSTERS=0
for result_file in "${RESULTS_DIR}"/*.result; do
  [[ -f "${result_file}" ]] || continue

  while IFS= read -r line; do
    field_count="$(printf '%s' "${line}" | awk -F'|' '{print NF}')"
    [[ "${field_count}" -ge 7 ]] && TOTAL_CLUSTERS=$(( TOTAL_CLUSTERS + 1 ))
  done < "${result_file}"
done

printf "\n"
printf "${COLOR_BOLD}GKE Kubernetes Resources Report${COLOR_RESET}"
printf " | Proyectos: ${COLOR_CYAN}%d${COLOR_RESET}" "${TOTAL_PROJECTS}"
printf " | Clústeres: ${COLOR_CYAN}%d${COLOR_RESET}" "${TOTAL_CLUSTERS}"
printf " | Paralelos: ${COLOR_CYAN}%d${COLOR_RESET}\n" "${MAX_PARALLEL}"
printf "Generado: ${COLOR_GRAY}%s${COLOR_RESET}" "$(date '+%Y-%m-%d %H:%M:%S')"
printf " | Duración: ${COLOR_CYAN}%dm %02ds${COLOR_RESET}\n\n" \
  "${ELAPSED_MIN}" \
  "${ELAPSED_SEC}"

printf "${COLOR_BOLD}${COLOR_CYAN}"
printf "%-${COL_PROJECT}s  %-${COL_CLUSTER}s  %-${COL_LOCATION}s  %${COL_SERVICES}s  %${COL_DEPLOYMENTS}s  %${COL_PODS}s  %-${COL_STATUS}s\n" \
  "PROYECTO" \
  "CLUSTER" \
  "UBICACION" \
  "SERVICIOS" \
  "DEPLOYMENTS" \
  "PODS" \
  "STATUS"

printf "${COLOR_GRAY}"
printf "%-${COL_PROJECT}s  %-${COL_CLUSTER}s  %-${COL_LOCATION}s  %${COL_SERVICES}s  %${COL_DEPLOYMENTS}s  %${COL_PODS}s  %-${COL_STATUS}s\n" \
  "$(repeat_char '-' "${COL_PROJECT}")" \
  "$(repeat_char '-' "${COL_CLUSTER}")" \
  "$(repeat_char '-' "${COL_LOCATION}")" \
  "$(repeat_char '-' "${COL_SERVICES}")" \
  "$(repeat_char '-' "${COL_DEPLOYMENTS}")" \
  "$(repeat_char '-' "${COL_PODS}")" \
  "$(repeat_char '-' "${COL_STATUS}")"

printf "${COLOR_RESET}"

for project in "${PROJECTS[@]}"; do
  result_file="${RESULTS_DIR}/${project}.result"
  [[ -f "${result_file}" ]] || continue

  while IFS='|' read -r proj cluster location services d_ready d_total p_running p_active; do

    # Proyecto sin token.
    if [[ "${cluster}" == "CREDENTIAL_FAIL" ]]; then
      printf "%-${COL_PROJECT}s  %-${COL_CLUSTER}s  %-${COL_LOCATION}s  %${COL_SERVICES}s  %${COL_DEPLOYMENTS}s  %${COL_PODS}s  ${COLOR_RED}%-${COL_STATUS}s${COLOR_RESET}\n" \
        "${proj}" "-" "-" "-" "-" "-" "❌ NO ACCESS"
      continue
    fi

    # Proyecto sin clústeres.
    if [[ "${cluster}" == "NO_CLUSTERS" ]]; then
      printf "%-${COL_PROJECT}s  %-${COL_CLUSTER}s  %-${COL_LOCATION}s  %${COL_SERVICES}s  %${COL_DEPLOYMENTS}s  %${COL_PODS}s  ${COLOR_YELLOW}%-${COL_STATUS}s${COLOR_RESET}\n" \
        "${proj}" "-" "-" "-" "-" "-" "⚠️ NO CLUSTERS"
      continue
    fi

    # Credenciales del clúster fallaron.
    if [[ "${services}" == "CRED_FAIL" ]]; then
      printf "%-${COL_PROJECT}s  %-${COL_CLUSTER}s  %-${COL_LOCATION}s  %${COL_SERVICES}s  %${COL_DEPLOYMENTS}s  %${COL_PODS}s  ${COLOR_RED}%-${COL_STATUS}s${COLOR_RESET}\n" \
        "${proj}" "${cluster}" "${location}" "-" "-" "-" "❌ NO ACCESS"
      continue
    fi

    has_timeout=false
    deploy_pct=0
    pod_pct=0

    if [[ "${d_ready}" == "N/A" || "${d_total}" == "N/A" ||
          "${p_running}" == "N/A" || "${p_active}" == "N/A" ]]; then
      has_timeout=true
    else
      [[ "${d_total}" =~ ^[0-9]+$ ]] || d_total=0
      [[ "${d_ready}" =~ ^[0-9]+$ ]] || d_ready=0
      [[ "${p_active}" =~ ^[0-9]+$ ]] || p_active=0
      [[ "${p_running}" =~ ^[0-9]+$ ]] || p_running=0

      if [[ "${d_total}" -gt 0 ]]; then
        deploy_pct=$(( d_ready * 100 / d_total ))
      else
        deploy_pct=100
      fi

      if [[ "${p_active}" -gt 0 ]]; then
        pod_pct=$(( p_running * 100 / p_active ))
      else
        pod_pct=100
      fi
    fi

    if [[ "${has_timeout}" == true ]]; then
      deploy_value="N/A"
      pod_value="N/A"
      deploy_color="${COLOR_YELLOW}"
      pod_color="${COLOR_YELLOW}"
      status_text="⚠️ TIMEOUT"
      status_color="${COLOR_YELLOW}"
    else
      deploy_value="${d_ready}|${d_total}"
      pod_value="${p_running}|${p_active}"

      deploy_color="$(color_for_pct "${deploy_pct}" "${DEPLOY_OK_PCT}" "${DEPLOY_WARNING_PCT}")"
      pod_color="$(color_for_pct "${pod_pct}" "${POD_OK_PCT}" "${POD_WARNING_PCT}")"

      # Estado combinado:
      # 1. Critical si cualquiera de los dos está debajo de 50%.
      # 2. OK si ambos están en 90% o más.
      # 3. Warning para todos los demás casos.
      if [[ "${deploy_pct}" -lt "${DEPLOY_WARNING_PCT}" ||
            "${pod_pct}" -lt "${POD_WARNING_PCT}" ]]; then
        status_text="🔴 CRITICAL"
        status_color="${COLOR_RED}"
      elif [[ "${deploy_pct}" -ge "${DEPLOY_OK_PCT}" &&
              "${pod_pct}" -ge "${POD_OK_PCT}" ]]; then
        status_text="✅ OK"
        status_color="${COLOR_GREEN}"
      else
        status_text="🟡 WARNING"
        status_color="${COLOR_YELLOW}"
      fi
    fi

    # Los emojis solo aparecen en STATUS.
    # DEPLOYMENTS y PODS se muestran únicamente con color.
    printf "%-${COL_PROJECT}s  %-${COL_CLUSTER}s  %-${COL_LOCATION}s  %${COL_SERVICES}s  " \
      "${proj}" \
      "${cluster}" \
      "${location}" \
      "${services}"

    printf "${deploy_color}%${COL_DEPLOYMENTS}s${COLOR_RESET}  " "${deploy_value}"
    printf "${pod_color}%${COL_PODS}s${COLOR_RESET}  " "${pod_value}"
    printf "${status_color}%-${COL_STATUS}s${COLOR_RESET}\n" "${status_text}"

  done < "${result_file}"
done

# ============================================================================
# Leyenda
# ============================================================================
printf "\n${COLOR_BOLD}Leyenda${COLOR_RESET}\n"
printf "  ${COLOR_GRAY}DEPLOYMENTS: ready|total. Se considera ready si tiene al menos una réplica lista.${COLOR_RESET}\n"
printf "  ${COLOR_GRAY}PODS: Running|activos. Los pods Succeeded no se cuentan como activos.${COLOR_RESET}\n\n"

printf "  ${COLOR_GREEN}Verde${COLOR_RESET}     >= 90%%\n"
printf "  ${COLOR_YELLOW}Amarillo${COLOR_RESET}  >= 50%% y < 90%%\n"
printf "  ${COLOR_RED}Rojo${COLOR_RESET}      < 50%%\n\n"

printf "  ✅ OK        Deployments >= %d%% y Pods >= %d%%\n" \
  "${DEPLOY_OK_PCT}" \
  "${POD_OK_PCT}"

printf "  🟡 WARNING   Sin condición crítica, pero al menos una métrica está por debajo de 90%%.\n"
printf "  🔴 CRITICAL  Deployments < %d%% o Pods < %d%%\n" \
  "${DEPLOY_WARNING_PCT}" \
  "${POD_WARNING_PCT}"

printf "  ⚠️ TIMEOUT   Alguna consulta kubectl excedió %ds.\n" \
  "${KUBECTL_TIMEOUT_SECONDS}"

printf "  ❌ NO ACCESS No fue posible autenticarse u obtener credenciales del clúster.\n"

# ============================================================================
# Advertencias y resumen
# ============================================================================
WARN_TOTAL=0

if [[ -s "${WARNINGS_FILE}" ]]; then
  WARN_TOTAL="$(wc -l < "${WARNINGS_FILE}" | tr -d ' ')"

  printf "\n${COLOR_YELLOW}Advertencias (%d):${COLOR_RESET}\n" "${WARN_TOTAL}"

  while IFS= read -r warning; do
    printf "  ${COLOR_GRAY}- %s${COLOR_RESET}\n" "${warning}"
  done < "${WARNINGS_FILE}"
fi

printf "\n${COLOR_BOLD}Resumen${COLOR_RESET}\n"
printf "  Proyectos procesados : ${COLOR_CYAN}%d${COLOR_RESET}\n" "${TOTAL_PROJECTS}"
printf "  Clústeres reportados : ${COLOR_CYAN}%d${COLOR_RESET}\n" "${TOTAL_CLUSTERS}"
printf "  Ejecuciones paralelas: ${COLOR_CYAN}%d${COLOR_RESET}\n" "${MAX_PARALLEL}"
printf "  Advertencias         : ${COLOR_YELLOW}%d${COLOR_RESET}\n" "${WARN_TOTAL}"
printf "  Tiempo total         : ${COLOR_CYAN}%dm %02ds${COLOR_RESET}\n\n" \
  "${ELAPSED_MIN}" \
  "${ELAPSED_SEC}"