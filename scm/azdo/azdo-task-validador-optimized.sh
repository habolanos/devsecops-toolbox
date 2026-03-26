#!/usr/bin/env bash
# =============================================================================
# azdo-task-validador-optimized.sh
# Script optimizado (DevSecOps) para Azure DevOps Release: variables, validación
# de imágenes, búsqueda de release rollback, validación de credenciales y
# comparación de ConfigMap vs Repo.
#
# NOTAS IMPORTANTES:
# - Este script está diseñado para ejecutarse en Bash dentro de Azure DevOps.
# - Depende de: curl, jq, (gcloud y crane para validación de imágenes), kubectl,
#   sha256sum, date.
# - Para yq: descarga un binario local y lo verifica por SHA256 (DEBES poner el
#   SHA256 real oficial en YQ_SHA256).
# - PAT debe venir como variable secreta del pipeline (recomendado).
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# -----------------------------
# Logging
# -----------------------------
ts() { date '+%Y-%m-%dT%H:%M:%S'; }
log_info()  { echo "[INFO]  $(ts) $*"; }
log_warn()  { echo "##vso[task.logissue type=warning;]$(ts) $*"; }
log_error() { echo "##vso[task.logissue type=error;]$(ts) $*"; }
section()   { echo; echo "════════════════════════════════════════"; echo "  $*"; echo "════════════════════════════════════════"; }

# -----------------------------
# Cleanup tmp files
# -----------------------------
TMPFILES=()
cleanup() {
  local ec=$?
  for f in "${TMPFILES[@]:-}"; do
    [[ -f "$f" ]] && rm -f "$f" || true
  done
  exit $ec
}
trap cleanup EXIT INT TERM

# -----------------------------
# Helpers
# -----------------------------
require_cmds() {
  local missing=0
  for c in "$@"; do
    if ! command -v "$c" >/dev/null 2>&1; then
      log_error "Falta comando requerido: $c"
      missing=1
    fi
  done
  [[ $missing -eq 1 ]] && exit 1
}

require_vars() {
  local missing=0
  for v in "$@"; do
    if [[ -z "${!v:-}" || "${!v:-}" == "null" ]]; then
      log_error "Variable requerida vacía o nula: $v"
      missing=1
    fi
  done
  [[ $missing -eq 1 ]] && exit 1
}

# curl wrapper
az_curl() {
  local method="$1"; local url="$2"; shift 2
  curl -s -f \
    --max-time 30 \
    --retry 3 \
    --retry-delay 5 \
    --retry-connrefused \
    -u ":${PAT}" \
    -X "$method" \
    "$@" \
    "$url"
}

update_release_variable() {
  local org="$1" project="$2" release_id="$3" var_name="$4" var_value="$5"
  require_vars API_VERSION

  local url="https://vsrm.dev.azure.com/${org}/${project}/_apis/release/releases/${release_id}?api-version=${API_VERSION}"

  local release_json
  release_json=$(az_curl GET "$url" -H "Accept: application/json")

  local jf rf
  jf=$(mktemp); TMPFILES+=("$jf")
  rf=$(mktemp); TMPFILES+=("$rf")

  echo "$release_json" | jq --arg k "$var_name" --arg v "$var_value" '.variables[$k].value = $v' > "$jf"

  local http
  http=$(curl -s -o "$rf" -w "%{http_code}" \
    --max-time 30 --retry 3 --retry-delay 3 --retry-connrefused \
    -u ":${PAT}" -X PUT "$url" \
    -H "Content-Type: application/json" \
    --data @"$jf")

  if [[ "$http" -lt 200 || "$http" -ge 300 ]]; then
    log_error "Error al actualizar variable '$var_name' en release $release_id (HTTP $http)"
    cat "$rf"
    exit 1
  fi
  log_info "Variable '$var_name' actualizada (HTTP $http)"
}

date_is_newer() {
  local a="$1" b="$2"
  local ea eb
  ea=$(date -d "$a" +%s 2>/dev/null) || { log_error "Fecha inválida: $a"; exit 1; }
  eb=$(date -d "$b" +%s 2>/dev/null) || { log_error "Fecha inválida: $b"; exit 1; }
  (( ea > eb ))
}

# -----------------------------
# Tooling requirements
# -----------------------------
require_cmds curl jq

# =============================================================================
# 0) Variables (tomadas de AzDO)
# =============================================================================
section "0) Inicializando variables"

# Variables esperadas (exportadas previamente o definidas en pipeline)
# - PAT (secreto)
# - API_VERSION
# - ORG_NAME, PROJECT_NAME, ACTUAL_RELEASE_ID
# - TAG_ACTUAL se setea después de validar imagen

# Derivar ORG/PROJECT/RELEASE si vienen por variables del sistema (opcional)
ORG_NAME="${ORG_NAME:-}"
PROJECT_NAME="${PROJECT_NAME:-}"
ACTUAL_RELEASE_ID="${ACTUAL_RELEASE_ID:-}"
BRANCH="${BRANCH:-master}"

# Si no vienen, intentar derivarlas usando variables runtime de AzDO
if [[ -z "$ORG_NAME" ]]; then
  ORG_NAME=$(echo "${SYSTEM_TEAMFOUNDATIONCOLLECTIONURI:-${System_TeamFoundationCollectionUri:-}}" | awk -F'/' '{print $4}' 2>/dev/null || true)
fi
if [[ -z "$PROJECT_NAME" ]]; then
  PROJECT_NAME="${SYSTEM_TEAMPROJECT:-${System_TeamProject:-}}"
fi
if [[ -z "$ACTUAL_RELEASE_ID" ]]; then
  ACTUAL_RELEASE_ID="${RELEASE_RELEASEID:-${Release_ReleaseId:-}}"
fi

require_vars PAT API_VERSION ORG_NAME PROJECT_NAME ACTUAL_RELEASE_ID

log_info "ORG_NAME=$ORG_NAME"
log_info "PROJECT_NAME=$PROJECT_NAME"
log_info "ACTUAL_RELEASE_ID=$ACTUAL_RELEASE_ID"

# =============================================================================
# 1) Validar imágenes
# =============================================================================
section "1) Validar imágenes"

# Requiere: gcloud, crane
require_cmds gcloud

IMAGE_ACTUAL="${IMAGE_ACTUAL:-$(imageP.KubectlOutput)}"
IMAGE_NUEVA="${IMAGE_NUEVA:-$(artifact.containerRegistry)/$(artifact.harborProject)/$(artifact.baseImage):$(artifact.tag)}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"

require_vars IMAGE_ACTUAL IMAGE_NUEVA GCP_PROJECT_ID

TAG_ACTUAL="${IMAGE_ACTUAL##*:}"
require_vars TAG_ACTUAL

echo "##vso[task.setvariable variable=TAG_ACTUAL]${TAG_ACTUAL}"
log_info "Imagen actual: $IMAGE_ACTUAL"
log_info "Imagen nueva : $IMAGE_NUEVA"
log_info "TAG_ACTUAL   : $TAG_ACTUAL"

revoke_gcloud() {
  log_info "Revocando credenciales gcloud..."
  gcloud auth revoke --all --quiet >/dev/null 2>&1 || true
  if gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
    log_error "Aún existen cuentas autenticadas después del revoke (FALLO DE SEGURIDAD)."
    exit 1
  fi
  log_info "OK: sin cuentas activas"
}
trap revoke_gcloud EXIT

log_info "Autenticando Service Account..."
gcloud auth activate-service-account --key-file="$(sa.secureFilePath)" >/dev/null
gcloud config set project "$GCP_PROJECT_ID" >/dev/null

check_image_exists() {
  local img="$1"
  log_info "Validando existencia: $img"
  case "$img" in
    *artifact.coppel.io*)
      require_cmds crane
      if ! crane digest "$img" >/dev/null 2>&1; then
        log_error "Imagen NO existe en Harbor: $img"
        exit 1
      fi
      ;;
    *docker.pkg.dev*)
      if ! gcloud artifacts docker images describe "$img" --format="value(image_summary.digest)" >/dev/null 2>&1; then
        log_error "Imagen NO existe en Artifact Registry: $img"
        exit 1
      fi
      ;;
    *)
      log_error "Dominio no soportado: $img"
      exit 1
      ;;
  esac
  log_info "OK: existe"
}

check_image_exists "$IMAGE_ACTUAL"
check_image_exists "$IMAGE_NUEVA"

if [[ "$IMAGE_ACTUAL" == "$IMAGE_NUEVA" ]]; then
  log_warn "La imagen actual y la nueva son la misma."
else
  log_info "Nueva versión detectada."
fi

# =============================================================================
# 2) Obtener Release de Rollback por TAG_ACTUAL
# =============================================================================
section "2) Obtener Release de Rollback"

API_BASE="https://vsrm.dev.azure.com/${ORG_NAME}/${PROJECT_NAME}"

# Definition ID desde release actual
release_detail=$(az_curl GET "${API_BASE}/_apis/release/releases/${ACTUAL_RELEASE_ID}?api-version=${API_VERSION}" -H "Accept: application/json")
DEFINITION_ID=$(echo "$release_detail" | jq -r '.releaseDefinition.id // empty')
require_vars DEFINITION_ID

LIST_URL="${API_BASE}/_apis/release/releases?definitionId=${DEFINITION_ID}&\$top=50&api-version=${API_VERSION}"
releases_json=$(az_curl GET "$LIST_URL")

FOUND=false
RELEASE_ID_RB=""

while read -r r; do
  rid=$(echo "$r" | jq -r '.id')
  [[ "$rid" == "$ACTUAL_RELEASE_ID" ]] && continue

  rurl=$(echo "$r" | jq -r '.url')
  rdetail=$(az_curl GET "$rurl" 2>/dev/null || true)
  [[ -z "$rdetail" ]] && continue

  build_url=$(echo "$rdetail" | jq -r '.artifacts[] | select(.type=="Build") | .definitionReference.artifactSourceVersionUrl.id // empty' | head -n1)
  [[ -z "$build_url" ]] && continue

  if [[ "$build_url" == *"_permalink"* ]]; then
    bid=$(echo "$build_url" | grep -oP 'buildId=\K[0-9]+' | head -n1)
    bproj=$(echo "$build_url" | grep -oP 'projectId=\K[^&]+' | head -n1)
    build_api="https://dev.azure.com/${ORG_NAME}/${bproj}/_apis/build/builds/${bid}?api-version=${API_VERSION}"
  else
    build_api="$build_url"
  fi

  bjson=$(az_curl GET "$build_api" 2>/dev/null || true)
  [[ -z "$bjson" ]] && continue

  timeline=$(echo "$bjson" | jq -r '._links.timeline.href // empty' | head -n1)
  [[ -z "$timeline" ]] && continue

  tjson=$(az_curl GET "$timeline" 2>/dev/null || true)
  [[ -z "$tjson" ]] && continue

  log_url=$(echo "$tjson" | jq -r '.records[] | select(.type=="Task" and (.name|startswith("Push Image"))) | .log.url // empty' | head -n1)
  [[ -z "$log_url" ]] && continue

  logc=$(az_curl GET "$log_url" 2>/dev/null || true)
  [[ -z "$logc" ]] && continue

  if echo "$logc" | tac | grep -m1 -E ":${TAG_ACTUAL}(\"|\s|$|[^a-zA-Z0-9.-])" >/dev/null 2>&1; then
    FOUND=true
    RELEASE_ID_RB="$rid"
    log_info "Rollback Release encontrada: $RELEASE_ID_RB"
    break
  fi

done < <(echo "$releases_json" | jq -c '.value[]')

if [[ "$FOUND" != true || -z "$RELEASE_ID_RB" ]]; then
  log_error "No se encontró Release rollback para tag $TAG_ACTUAL en las últimas 50 releases."
  exit 1
fi

echo "##vso[task.setvariable variable=RELEASE_ID_RB]${RELEASE_ID_RB}"
update_release_variable "$ORG_NAME" "$PROJECT_NAME" "$ACTUAL_RELEASE_ID" "RELEASE_ID" "$RELEASE_ID_RB"

# =============================================================================
# 3) Validar vigencia credenciales GIT vs release rollback
# =============================================================================
section "3) Validar vigencia credenciales GIT"

GROUP_ID="${GROUP_ID:-$(GROUP_ID)}"
require_vars GROUP_ID

vg_url="https://dev.azure.com/${ORG_NAME}/${PROJECT_NAME}/_apis/distributedtask/variablegroups/${GROUP_ID}?api-version=${API_VERSION}"
vg_json=$(az_curl GET "$vg_url")

modified=$(echo "$vg_json" | jq -r '.modifiedOn // empty')
require_vars modified
clean_git="${modified%T*}"

rb_url="https://vsrm.dev.azure.com/${ORG_NAME}/${PROJECT_NAME}/_apis/release/releases/${RELEASE_ID_RB}?api-version=${API_VERSION}"
rb_json=$(az_curl GET "$rb_url")
created=$(echo "$rb_json" | jq -r '.createdOn // empty')
require_vars created
clean_rb="${created%T*}"

log_info "Fecha modificación credenciales GIT: $clean_git"
log_info "Fecha creación release rollback      : $clean_rb"

if date_is_newer "$clean_git" "$clean_rb"; then
  log_error "Credenciales GIT vencidas: fueron modificadas después del release rollback."
  exit 1
fi
log_info "Credenciales GIT vigentes."

# =============================================================================
# 4) Obtener commit properties (ConfigMap vs repo)
# =============================================================================
section "4) Obtener commit properties"

require_cmds kubectl sha256sum md5sum

# yq install (local + checksum)
YQ_VERSION="v4.40.5"
YQ_SHA256="REEMPLAZAR_POR_SHA256_OFICIAL"   # <- OBLIGATORIO
LOCAL_YQ="./yq_tool"

if ! command -v yq >/dev/null 2>&1; then
  if [[ ! -f "$LOCAL_YQ" ]]; then
    log_info "Descargando yq ${YQ_VERSION}..."
    curl -fsSL "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" -o "$LOCAL_YQ"
    echo "${YQ_SHA256}  ${LOCAL_YQ}" | sha256sum --check || {
      log_error "Checksum yq inválido. Abortando."
      rm -f "$LOCAL_YQ"
      exit 1
    }
    chmod +x "$LOCAL_YQ"
  fi
  yq() { "$LOCAL_YQ" "$@"; }
fi

normalize_yaml() {
  local in="$1"
  echo "$in" | yq e -o=json -I=0 - | jq -S -c . 2>/dev/null || echo ""
}

ARTIFACT_NAME="$(artifact.name)"
ARTIFACT_NAMESPACE="$(artifact.nameSpace)"
ARTIFACTS_DIR="$(System.ArtifactsDirectory)/$(sourcesArtifacts)"
mkdir -p "$ARTIFACTS_DIR" || true

CONFIGMAP_PATH="${ARTIFACTS_DIR}/application.yml"
kubectl get configmap "${ARTIFACT_NAME}-config" -n "$ARTIFACT_NAMESPACE" -o yaml > "$CONFIGMAP_PATH"

FILENAME=$(yq e '.data | keys | .[0]' "$CONFIGMAP_PATH")
require_vars FILENAME

k8s_raw=$(FILENAME="$FILENAME" yq e '.data.[env(FILENAME)] | from_yaml' "$CONFIGMAP_PATH" 2>/dev/null || echo "")
[[ -z "$k8s_raw" ]] && k8s_raw=$(FILENAME="$FILENAME" yq e '.data.[env(FILENAME)]' "$CONFIGMAP_PATH" 2>/dev/null || echo "")
require_vars k8s_raw

ext="${FILENAME##*.}"
if [[ "$ext" == "yaml" || "$ext" == "yml" ]]; then
  k8s_clean=$(echo "$k8s_raw" | yq e 'del(.metadata.resourceVersion,.metadata.uid,.metadata.creationTimestamp,.metadata.managedFields,.metadata.annotations,.metadata.namespace)' - 2>/dev/null || echo "$k8s_raw")
  k8s_norm=$(normalize_yaml "$k8s_clean")
else
  k8s_norm="$k8s_raw"
fi
require_vars k8s_norm

# Ajuste rama por reglas especiales
if [[ "$ARTIFACT_NAMESPACE" == "pvm" ]]; then
  BRANCH="pvm-prod-gke"
elif [[ "$PROJECT_NAME" == "TiendaRyM.NPV" ]]; then
  BRANCH="$ARTIFACT_NAMESPACE"
fi

svc_lower=$(echo "$ARTIFACT_NAME" | tr '[:upper:]' '[:lower:]')
file_path="/${svc_lower}/${FILENAME}"

repo_api="https://dev.azure.com/${ORG_NAME}/${PROJECT_NAME}/_apis/git/repositories/properties"
commits_url="${repo_api}/commits?searchCriteria.itemPath=${file_path}&searchCriteria.itemVersion.version=${BRANCH}&searchCriteria.\$top=20&api-version=${API_VERSION}"

commit_ids=$(az_curl GET "$commits_url" | jq -r '.value[].commitId // empty')
if [[ -z "$commit_ids" ]]; then
  log_error "No se encontraron commits para $file_path en rama $BRANCH"
  exit 1
fi

MATCHED_CID=""
for cid in $commit_ids; do
  file_url="${repo_api}/items?path=${file_path}&version=${cid}&versionType=commit&api-version=${API_VERSION}"
  repo_raw=$(az_curl GET "$file_url" 2>/dev/null || true)
  [[ -z "$repo_raw" ]] && continue

  if [[ "$ext" == "yaml" || "$ext" == "yml" ]]; then
    repo_clean=$(echo "$repo_raw" | yq e 'del(.metadata.resourceVersion,.metadata.uid,.metadata.creationTimestamp,.metadata.managedFields,.metadata.annotations,.metadata.namespace)' - 2>/dev/null || echo "$repo_raw")
    repo_norm=$(normalize_yaml "$repo_clean")
  else
    repo_norm="$repo_raw"
  fi

  if [[ "$k8s_norm" == "$repo_norm" ]]; then
    MATCHED_CID="$cid"
    log_info "Coincidencia exacta encontrada: $MATCHED_CID"
    echo "##vso[task.setvariable variable=MatchedCommitIdJob]${MATCHED_CID}"
    echo "##vso[task.setvariable variable=ShouldRollbackJob]true"
    break
  else
    log_info "No coincide: K8s $(echo "$k8s_norm" | md5sum | cut -d' ' -f1) vs Repo $(echo "$repo_norm" | md5sum | cut -d' ' -f1)"
  fi
done

if [[ -z "$MATCHED_CID" ]]; then
  log_warn "No se encontró coincidencia exacta en los últimos 20 commits."
  echo "##vso[task.setvariable variable=ShouldRollbackJob]false"
else
  update_release_variable "$ORG_NAME" "$PROJECT_NAME" "$ACTUAL_RELEASE_ID" "commitPropertiesRollback" "$MATCHED_CID"
fi

section "FINAL"
log_info "Script finalizado correctamente"
