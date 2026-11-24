#!/usr/bin/env bash
#
# gke-failed-pods-scaler.sh
#
# Escanea clústeres GKE buscando pods con falla ACTIVA (CrashLoopBackOff,
# ImagePullBackOff, Unschedulable, contenedor terminado != 0, Failed/Unknown,
# Running+NotReady) y permite escalar el Deployment/StatefulSet dueño a
# 0 réplicas. Los restartCount históricos nunca generan candidatos.
#
# Uso:
#   bash gke-failed-pods-scaler.sh                            # interactivo
#   bash gke-failed-pods-scaler.sh --project WMS --env DEV    # sin menús
#   bash gke-failed-pods-scaler.sh --scan-only                # solo reporte
#
# Clústeres: se descubren del kubeconfig (contextos gke_* creados por
#   `gcloud container clusters get-credentials`). El proyecto corto y el
#   ambiente se derivan del project-id (cpl-<equipo>-<env>-<fecha>).
#   Si el descubrimiento no produce contextos se usa la tabla embebida.
#
# Bitácora: DEVSECOPS_OUTPUT_DIR > config.json global.output_dir > scm/outcome

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_JSON="$SCM_ROOT/config.json"

resolve_outcome_dir() {
  local out="${DEVSECOPS_OUTPUT_DIR:-}"
  if [[ -z "$out" && -f "$CONFIG_JSON" ]]; then
    out=$(jq -r '.global.output_dir // empty' "$CONFIG_JSON" 2>/dev/null || true)
    # Rutas relativas se resuelven bajo scm/ (convención utils.resolve_outcome_dir)
    if [[ -n "$out" && "$out" != /* && ! "$out" =~ ^[A-Za-z]: ]]; then
      out="$SCM_ROOT/$out"
    fi
  fi
  [[ -z "$out" ]] && out="$SCM_ROOT/outcome"
  mkdir -p "$out"
  printf '%s' "$out"
}
OUTCOME_DIR="$(resolve_outcome_dir)"
readonly ACTION_LOG="$OUTCOME_DIR/gke_failed_pods_scaler.log"

# Formato: PROYECTO|AMBIENTE|CONTEXTO
readonly DEFAULT_CLUSTERS_DATA=$(cat <<'EOF'
WMS|DEV|gke_cpl-cs-wms-dev-30112023_us-central1_gke-cs-wms-dev-01
WMS|DEV|gke_cpl-cs-wms-dev-30112023_us-central1_gke-cs-wms-dev-02
WMS|DEV|gke_cpl-cs-wms-dev-30112023_us-central1_gke-cs-wms-dev-03
WMS|QA|gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-01
WMS|QA|gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-02
WMS|QA|gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-03
WMS|STAG|gke_cpl-cs-wms-stag-09042025_us-central1_gke-cs-wms-stag-01
OMS|DEV|gke_cpl-oms-dev-08082024_us-central1_gke-oms-dev-01
OMS|QA|gke_cpl-oms-qa-08062023_us-central1_gke-oms-producto-qa
OMS|STAG|gke_cpl-oms-stag-09042025_us-central1_gke-oms-stag-01
CSC|DEV|gke_cpl-cs-csc-dev-16112023_us-central1_gke-cs-csc-dev-01
CSC|DEV|gke_cpl-cs-csc-dev-16112023_us-central1_us-central1-cpr-cs-csc-comp-f9241bb5-gke
CSC|QA|gke_cpl-cs-csc-qa-16112023_us-central1_gke-cs-csc-qa-01
CSC|QA|gke_cpl-cs-csc-qa-16112023_us-central1_us-central1-cpr-cs-csc-comp-11ca550e-gke
CSC|STAG|gke_cpl-cs-csc-stag-11042025_us-central1_gke-cs-csc-stag-01
CSC|STAG|gke_cpl-cs-csc-stag-11042025_us-central1_us-central1-cpr-cs-csc-comp-0e2a09bc-gke
TMS|DEV|gke_cpl-cmanager-dev-13072023_us-central1_gke-cmanager-dev-01
TMS|QA|gke_cpl-cmanager-qa-13072023_us-central1_gke-cmanager-qa-01
TMS|STAG|gke_cpl-cmanager-stag-01052025_us-central1_gke-cmanager-stag-01
EOF
)

# Descubrimiento: contextos gke_* del kubeconfig. De cada contexto
# gke_<project-id>_<region>_<cluster> se deriva PROYECTO|AMBIENTE|CONTEXTO:
#   env:  token -dev-/-qa-/-stag-/-stg-/-prod-/-prd- del project-id
#   team: project-id sin prefijo cpl- ni sufijo -<env>-<fecha>
discover_clusters() {
  command -v kubectl >/dev/null 2>&1 || return 0
  kubectl config get-contexts -o name 2>/dev/null | awk -F'_' '
    $1 == "gke" && NF >= 4 {
      proj = $2
      env = "UNK"
      if      (proj ~ /-dev-/)  env = "DEV"
      else if (proj ~ /-qa-/)   env = "QA"
      else if (proj ~ /-stag-|-stg-/) env = "STAG"
      else if (proj ~ /-prod-|-prd-/) env = "PROD"
      team = proj
      sub(/^cpl-/, "", team)
      sub(/-(dev|qa|stag|stg|prod|prd)-[0-9]+$/, "", team)
      t = toupper(team)
      # Alias de equipo conocidos; equipos nuevos se muestran con su clave.
      if      (t == "CS-WMS")   t = "WMS"
      else if (t == "CS-CSC")   t = "CSC"
      else if (t == "CMANAGER") t = "TMS"
      printf "%s|%s|%s\n", t, env, $0
    }'
}

load_clusters() {
  local from_ctx
  from_ctx="$(discover_clusters)"
  if [[ -n "$from_ctx" ]]; then
    printf '%s' "$from_ctx"
  else
    printf '%s' "$DEFAULT_CLUSTERS_DATA"
  fi
}
readonly CLUSTERS_DATA="$(load_clusters)"

declare -a CANDIDATE_CONTEXTS=()
declare -a CANDIDATE_NAMESPACES=()
declare -a CANDIDATE_TARGETS=()
declare -a CANDIDATE_PODS=()
declare -a CANDIDATE_REASONS=()
declare -A SEEN_CANDIDATES=()

ARG_PROJECT=""
ARG_ENV=""
SCAN_ONLY=0

usage() {
  cat <<'USAGE'
Uso: bash gke-failed-pods-scaler.sh [--project P] [--env E] [--scan-only]
  --project    Proyecto (WMS, OMS, CSC, TMS, según config)
  --env        Ambiente (DEV, QA, STAG, según config)
  --scan-only  Solo reporte; no ofrece escalado
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "No se encontró el comando requerido: $1"
}

# kubectl con timeout si está disponible (no existe en Git Bash/macOS).
kubectl_get() {
  if command -v timeout >/dev/null 2>&1; then
    timeout 30s kubectl --request-timeout=20s "$@"
  else
    kubectl --request-timeout=20s "$@"
  fi
}

unique_values() { # columna 1 (proyecto) o 2 (ambiente) de PROYECTO|ENV|CTX
  awk -F'|' -v f="$1" '$0 != "" && $f != "" && !seen[$f]++ { print $f }'
}

choose_from() { # $1=título, resto=opciones; escribe la elección en CHOICE
  local title="$1"; shift
  local -a options=("$@")
  local choice
  if ((${#options[@]} == 0)); then
    die "No hay opciones configuradas para: $title"
  fi
  if ((${#options[@]} == 1)); then
    CHOICE="${options[0]}"
    printf '\n%s: %s (único configurado)\n' "$title" "$CHOICE"
    return
  fi
  printf '\nSeleccione %s:\n' "$title"
  local i
  for i in "${!options[@]}"; do
    printf '  %d) %s\n' "$((i + 1))" "${options[$i]}"
  done
  printf '  0) Salir\n'
  if ! read -r -p 'Opción: ' choice; then
    printf '\n'
    exit 0
  fi
  [[ "$choice" =~ ^[0-9]+$ ]] || die "Selección inválida"
  ((choice == 0)) && exit 0
  ((choice >= 1 && choice <= ${#options[@]})) || die "Selección fuera de rango"
  CHOICE="${options[$((choice - 1))]}"
}

choose_project() {
  local -a projects=()
  mapfile -t projects < <(printf '%s\n' "$CLUSTERS_DATA" | unique_values 1)
  choose_from "el proyecto" "${projects[@]}"
  PROJECT="$CHOICE"
}

choose_environment() {
  local -a envs=()
  mapfile -t envs < <(
    awk -F'|' -v p="$PROJECT" '$1 == p && $2 != "" && !seen[$2]++ { print $2 }' \
      <<<"$CLUSTERS_DATA"
  )
  choose_from "el ambiente de $PROJECT" "${envs[@]}"
  ENVIRONMENT="$CHOICE"
}

resolve_deployment() {
  local replicasets_json="$1"
  local namespace="$2"
  local replicaset="$3"

  jq -r --arg ns "$namespace" --arg rs "$replicaset" '
    .items[]
    | select(.metadata.namespace == $ns and .metadata.name == $rs)
    | .metadata.ownerReferences[]?
    | select(.controller == true and .kind == "Deployment")
    | "deployment/" + .name
  ' <<<"$replicasets_json" | head -n 1
}

add_candidate() {
  local context="$1" namespace="$2" target="$3" pod="$4" reason="$5"
  local key="$context|$namespace|$target" replicas

  [[ -n "$target" ]] || return
  [[ "$namespace" != "kube-system" ]] || return
  [[ "$namespace" != "gke-managed-system" ]] || return
  [[ -z "${SEEN_CANDIDATES[$key]:-}" ]] || return

  # Un pod puede seguir visible brevemente después de apagar su controlador.
  # Solo se ofrecen recursos que todavía tengan réplicas mayores que cero.
  if ! replicas="$(kubectl --context "$context" -n "$namespace" get "$target" -o jsonpath='{.spec.replicas}' 2>/dev/null)"; then
    return
  fi
  [[ "$replicas" =~ ^[0-9]+$ ]] || return
  ((replicas > 0)) || return

  SEEN_CANDIDATES[$key]=1
  CANDIDATE_CONTEXTS+=("$context")
  CANDIDATE_NAMESPACES+=("$namespace")
  CANDIDATE_TARGETS+=("$target")
  CANDIDATE_PODS+=("$pod")
  CANDIDATE_REASONS+=("$reason")
}

remove_candidate() {
  local index="$1"

  CANDIDATE_CONTEXTS=("${CANDIDATE_CONTEXTS[@]:0:index}" "${CANDIDATE_CONTEXTS[@]:index+1}")
  CANDIDATE_NAMESPACES=("${CANDIDATE_NAMESPACES[@]:0:index}" "${CANDIDATE_NAMESPACES[@]:index+1}")
  CANDIDATE_TARGETS=("${CANDIDATE_TARGETS[@]:0:index}" "${CANDIDATE_TARGETS[@]:index+1}")
  CANDIDATE_PODS=("${CANDIDATE_PODS[@]:0:index}" "${CANDIDATE_PODS[@]:index+1}")
  CANDIDATE_REASONS=("${CANDIDATE_REASONS[@]:0:index}" "${CANDIDATE_REASONS[@]:index+1}")
}

scan_context() {
  local context="$1"
  local pods_json replicasets_json findings error_file
  local namespace pod phase reason restarts ready owner_kind owner_name target

  printf '\n------------------------------------------------------------------\n'
  printf 'Clúster: %s\n' "$context"

  if ! kubectl config get-contexts -o name 2>/dev/null | grep -Fxq "$context"; then
    printf 'ADVERTENCIA: el contexto no existe en kubeconfig. Se omite.\n' >&2
    return
  fi

  error_file="$(mktemp)"
  if ! pods_json="$(kubectl_get --context "$context" get pods -A -o json 2>"$error_file")"; then
    printf 'ADVERTENCIA: no fue posible consultar los pods. Se omite.\n' >&2
    if [[ -s "$error_file" ]]; then
      printf 'Detalle de kubectl: ' >&2
      tr '\n' ' ' <"$error_file" >&2
      printf '\n' >&2
    fi
    rm -f -- "$error_file"
    return
  fi
  rm -f -- "$error_file"

  replicasets_json="$(kubectl --context "$context" get replicasets -A -o json 2>/dev/null || printf '{"items":[]}')"

  findings="$(jq -r '
    .items[]
    | . as $pod
    | ((.status.initContainerStatuses // []) + (.status.containerStatuses // [])) as $statuses
    | ([$statuses[]? | (.restartCount // 0)] | add // 0) as $restarts
    # Solo razones de espera que representan una falla activa. Se excluyen
    # estados transitorios normales como ContainerCreating y PodInitializing.
    | ([$statuses[]?
        | select(.state.waiting.reason? as $r
          | ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull",
             "CreateContainerConfigError", "CreateContainerError",
             "RunContainerError", "InvalidImageName"] | index($r))
        | .state.waiting.reason] | unique) as $waiting
    | ([$statuses[]?
        | select(.state.terminated != null and (.state.terminated.exitCode // 0) != 0)
        | (.state.terminated.reason // ("ExitCode" + ((.state.terminated.exitCode // 0) | tostring)))]
       | unique) as $terminated
    | ([$pod.status.conditions[]?
        | select(.type == "PodScheduled" and .status == "False" and .reason == "Unschedulable")
        | .reason] | unique) as $scheduling
    | ([$pod.status.containerStatuses[]? | .ready] | if length == 0 then false else all end) as $ready
    | (
        if ($waiting | length) > 0 then ($waiting | join(","))
        elif ($terminated | length) > 0 then ($terminated | join(","))
        elif ($scheduling | length) > 0 then ($scheduling | join(","))
        elif ($pod.status.phase == "Failed" or $pod.status.phase == "Unknown") then ($pod.status.phase // "Desconocido")
        elif ($pod.status.phase == "Running" and $ready == false) then "NotReady"
        else "SinFallaActiva"
        end
      ) as $reason
    | select($pod.status.phase != "Succeeded")
    # Los restartCount históricos nunca generan candidatos de apagado.
    | select($reason != "SinFallaActiva")
    | ((.metadata.ownerReferences // []) | map(select(.controller == true)) | first // {"kind":"None","name":"-"}) as $owner
    | [
        .metadata.namespace,
        .metadata.name,
        (.status.phase // "Desconocido"),
        $reason,
        ($restarts | tostring),
        ($ready | tostring),
        $owner.kind,
        $owner.name
      ]
    | @tsv
  ' <<<"$pods_json")"

  if [[ -z "$findings" ]]; then
    printf 'Resultado: no se encontraron fallas activas.\n'
  else
    printf '\nPODS CON FALLA ACTIVA:\n'
    printf 'NAMESPACE\tPOD\tFASE\tMOTIVO\tREINICIOS\tREADY\n'
    while IFS=$'\t' read -r namespace pod phase reason restarts ready owner_kind owner_name; do
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$namespace" "$pod" "$phase" "$reason" "$restarts" "$ready"

      target=""
      case "$owner_kind" in
        StatefulSet) target="statefulset/$owner_name" ;;
        ReplicaSet) target="$(resolve_deployment "$replicasets_json" "$namespace" "$owner_name")" ;;
      esac
      add_candidate "$context" "$namespace" "$target" "$pod" "$reason (reinicios=$restarts)"
    done <<<"$findings"
  fi

}

show_candidates() {
  local index

  printf '\n========== SERVICIOS CON FALLA ACTIVA QUE PUEDEN ESCALARSE A CERO ==========\n'
  if ((${#CANDIDATE_TARGETS[@]} == 0)); then
    printf 'No hay Deployments o StatefulSets de aplicación para apagar.\n'
    return
  fi

  for index in "${!CANDIDATE_TARGETS[@]}"; do
    printf '%d) namespace=%s  recurso=%s\n' \
      "$((index + 1))" "${CANDIDATE_NAMESPACES[$index]}" "${CANDIDATE_TARGETS[$index]}"
    printf '   pod=%s  motivo=%s\n' "${CANDIDATE_PODS[$index]}" "${CANDIDATE_REASONS[$index]}"
    printf '   contexto=%s\n' "${CANDIDATE_CONTEXTS[$index]}"
  done
}

scale_candidate() {
  local index="$1"
  local context="${CANDIDATE_CONTEXTS[$index]}"
  local namespace="${CANDIDATE_NAMESPACES[$index]}"
  local target="${CANDIDATE_TARGETS[$index]}"
  local replicas timestamp result

  if ! replicas="$(kubectl --context "$context" -n "$namespace" get "$target" -o jsonpath='{.spec.replicas}' 2>/dev/null)"; then
    printf 'ERROR: no se pudo leer %s en %s.\n' "$target" "$namespace" >&2
    return 1
  fi

  if [[ "$replicas" == "0" ]]; then
    printf 'OMITIDO: %s/%s ya tiene 0 réplicas.\n' "$namespace" "$target"
    return 0
  fi

  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
  if kubectl --context "$context" -n "$namespace" scale "$target" --replicas=0; then
    result="ok"
    printf 'OK: %s/%s pasó de %s a 0 réplicas.\n' "$namespace" "$target" "$replicas"
  else
    result="error"
    printf 'ERROR: falló el escalamiento de %s/%s.\n' "$namespace" "$target" >&2
  fi
  printf '%s|project=%s|environment=%s|context=%s|namespace=%s|target=%s|previous_replicas=%s|requested_replicas=0|result=%s\n' \
    "$timestamp" "$PROJECT" "$ENVIRONMENT" "$context" "$namespace" "$target" "$replicas" "$result" >>"$ACTION_LOG"
  [[ "$result" == "ok" ]]
}

scale_one_by_one() {
  local choice answer index

  while true; do
    show_candidates
    printf '0) Volver al menú sin cambiar más servicios\n'
    if ! read -r -p 'Seleccione el número del servicio: ' choice; then
      printf '\nEntrada finalizada; se sale sin cambios.\n'
      return
    fi
    [[ "$choice" =~ ^[0-9]+$ ]] || { printf 'Selección inválida.\n'; continue; }
    ((choice == 0)) && return
    if ((choice < 1 || choice > ${#CANDIDATE_TARGETS[@]})); then
      printf 'Selección fuera de rango.\n'
      continue
    fi

    index=$((choice - 1))
    printf '\nSe escalará a cero: %s/%s\n' \
      "${CANDIDATE_NAMESPACES[$index]}" "${CANDIDATE_TARGETS[$index]}"
    read -r -p 'Escriba ESCALAR-A-CERO para confirmar: ' answer || return
    if [[ "$answer" == "ESCALAR-A-CERO" ]]; then
      if scale_candidate "$index"; then
        remove_candidate "$index"
        if ((${#CANDIDATE_TARGETS[@]} == 0)); then
          printf 'Ya no quedan servicios con fallas activas para escalar.\n'
          return
        fi
      fi
    else
      printf 'Cancelado; no se realizaron cambios para ese servicio.\n'
    fi
  done
}

scale_all() {
  local answer index failures=0

  show_candidates
  ((${#CANDIDATE_TARGETS[@]} > 0)) || return

  printf '\nADVERTENCIA: se intentarán apagar %d servicios de %s/%s.\n' \
    "${#CANDIDATE_TARGETS[@]}" "$PROJECT" "$ENVIRONMENT"
  read -r -p "Escriba APAGAR-TODOS-$PROJECT-$ENVIRONMENT para confirmar: " answer || return
  if [[ "$answer" != "APAGAR-TODOS-$PROJECT-$ENVIRONMENT" ]]; then
    printf 'Cancelado; no se realizó ningún cambio.\n'
    return
  fi

  for index in "${!CANDIDATE_TARGETS[@]}"; do
    scale_candidate "$index" || ((failures += 1))
  done
  printf '\nProceso terminado. Fallas al escalar: %d.\n' "$failures"
}

action_menu() {
  local choice

  if ((${#CANDIDATE_TARGETS[@]} == 0)); then
    return
  fi

  while true; do
    printf '\nSeleccione una acción:\n'
    printf '  1) Solo mostrar resultados y salir\n'
    printf '  2) Escalar servicios uno por uno\n'
    printf '  3) Escalar TODOS los servicios encontrados a cero\n'
    printf '  0) Salir sin cambios\n'
    if ! read -r -p 'Opción: ' choice; then
      printf '\nEntrada finalizada; se sale sin cambios.\n'
      return
    fi
    case "$choice" in
      1|0) return ;;
      2) scale_one_by_one; return ;;
      3) scale_all; return ;;
      *) printf 'Opción inválida.\n' ;;
    esac
  done
}

main() {
  local project environment context matched=0

  while (($#)); do
    case "$1" in
      --project) ARG_PROJECT="${2:-}"; shift 2 ;;
      --env|--environment) ARG_ENV="${2:-}"; shift 2 ;;
      --scan-only) SCAN_ONLY=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "Argumento desconocido: $1 (use --help)" ;;
    esac
  done

  require_command kubectl
  require_command jq

  if [[ -n "$ARG_PROJECT" ]]; then
    PROJECT="$ARG_PROJECT"
  elif [[ -t 0 ]]; then
    choose_project
  else
    die "stdin no es interactivo; use --project y --env (o --scan-only)"
  fi

  if [[ -n "$ARG_ENV" ]]; then
    ENVIRONMENT="$ARG_ENV"
  elif [[ -t 0 ]]; then
    choose_environment
  else
    die "stdin no es interactivo; use --env"
  fi

  printf '\nRevisando proyecto %s, ambiente %s...\n' "$PROJECT" "$ENVIRONMENT"
  while IFS='|' read -r project environment context; do
    if [[ "$project" == "$PROJECT" && "$environment" == "$ENVIRONMENT" ]]; then
      matched=1
      scan_context "$context"
    fi
  done <<<"$CLUSTERS_DATA"

  ((matched == 1)) || die "No hay clústeres configurados para $PROJECT/$ENVIRONMENT"
  show_candidates
  if ((SCAN_ONLY == 0)) && [[ -t 0 ]]; then
    action_menu
  fi
  printf '\nFinalizado. Bitácora de cambios: %s\n' "$ACTION_LOG"
}

# Guard: permite hacer source del script para probar sus funciones.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
