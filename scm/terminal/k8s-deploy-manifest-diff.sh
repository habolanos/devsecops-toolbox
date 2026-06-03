#!/usr/bin/env bash
# =================================================================
# k8s-deploy-manifest-diff.sh
#
# Descripción : Compara manifiestos aplicados al Deployment actual
#               vs la revisión anterior en Kubernetes.
#               Analiza: Deployment, ReplicaSets, Pods, ConfigMaps,
#               Secrets, Probes, HPA, Volumes, ServiceAccount y Eventos.
#               Clasifica los cambios por nivel de riesgo y genera
#               un informe ejecutivo con recomendaciones automáticas.
#
# Uso   : ./k8s-deploy-manifest-diff.sh <deployment> <namespace> [opciones]
# Opciones:
#   --export        Exporta el informe a outcome/k8s_diff_*.txt
#   --full-env      Muestra valores de env vars directas (ocultos por default)
#   --no-events     Omite la sección de eventos
#   --no-commands   Desactiva la exportación de comandos de inspección (activo por defecto)
#
# Ejemplos:
#   ./k8s-deploy-manifest-diff.sh orders-service prod
#   ./k8s-deploy-manifest-diff.sh payments-api staging --export
#   ./k8s-deploy-manifest-diff.sh gateway default --export --no-events
#   ./k8s-deploy-manifest-diff.sh orders-service prod --no-commands
#
# Dependencias: kubectl, jq (apt-get install jq / brew install jq)
# Agnostic: GKE, EKS, AKS, OpenShift, Minikube, cualquier clúster K8s
#
# Exit codes:
#   0 → Sin riesgo o riesgo bajo (NONE / LOW)
#   1 → Riesgo MEDIUM o HIGH detectado
#   2 → Riesgo CRITICAL detectado
# =================================================================

# ─── Configuración ────────────────────────────────────────────────────────────
TZ_ZONE="${TERMINAL_TIMEZONE:-America/Mazatlan}"

# ─── Argumentos ───────────────────────────────────────────────────────────────
DEPLOY_NAME="${1:-}"
NAMESPACE="${2:-}"
EXPORT_FLAG=false
FULL_ENV=false
NO_EVENTS=false
SHOW_COMMANDS=true

for arg in "${@:3}"; do
    case "$arg" in
        --export)      EXPORT_FLAG=true ;;
        --full-env)    FULL_ENV=true ;;
        --no-events)   NO_EVENTS=true ;;
        --no-commands) SHOW_COMMANDS=false ;;
    esac
done

usage() {
    echo ""
    echo "Uso: $0 <deployment> <namespace> [--export] [--full-env] [--no-events] [--no-commands]"
    echo "Ej.: $0 orders-service prod --export"
    echo "     $0 orders-service prod --no-commands"
    echo ""
    exit 1
}

[[ -z "$DEPLOY_NAME" || -z "$NAMESPACE" ]] && usage

# ─── Colors ───────────────────────────────────────────────────────────────────
RED_BOLD='\033[1;31m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'
WHITE='\033[1;37m'; DIM='\033[2m'; NC='\033[0m'

# ─── Dependencias ─────────────────────────────────────────────────────────────
for dep in kubectl jq; do
    if ! command -v "$dep" &>/dev/null; then
        echo -e "${RED_BOLD}ERROR: '$dep' no encontrado. Instala con: apt-get install $dep${NC}"
        exit 1
    fi
done

# ─── Export setup ─────────────────────────────────────────────────────────────
EXPORT_FILE=""
if $EXPORT_FLAG; then
    mkdir -p outcome
    TS_EXPORT=$(TZ="$TZ_ZONE" date '+%Y%m%d_%H%M%S')
    EXPORT_FILE="outcome/k8s_diff_${DEPLOY_NAME}_${NAMESPACE}_${TS_EXPORT}.txt"
fi

# ─── Work dir (temp files evitan problemas de subshell con arrays) ───────────
WORK_DIR=$(mktemp -d)
RISK_FILE="$WORK_DIR/risks.txt"
CMDS_TEMP="$WORK_DIR/cmds.txt"
touch "$RISK_FILE" "$CMDS_TEMP"
trap 'rm -rf "$WORK_DIR"' EXIT
TS_RUN=$(TZ="$TZ_ZONE" date '+%Y%m%d_%H%M%S')

# ─── Output helper ────────────────────────────────────────────────────────────
out() {
    echo -e "$@"
    if [[ -n "$EXPORT_FILE" ]]; then
        echo -e "$@" | sed 's/\x1b\[[0-9;]*m//g' >> "$EXPORT_FILE"
    fi
}

# ─── Risk helpers ─────────────────────────────────────────────────────────────
add_risk() { echo "${1}|${2}" >> "$RISK_FILE"; }

count_risk() { grep -c "^${1}|" "$RISK_FILE" 2>/dev/null || true; }

# ─── Commands export helpers ──────────────────────────────────────────────────
add_cmd() {
    $SHOW_COMMANDS || return 0
    printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$CMDS_TEMP"
}

write_commands_json() {
    local json_file="$1"
    mkdir -p "$(dirname "$json_file")"
    {
        printf '{\n'
        printf '  "meta": {\n'
        printf '    "deployment": "%s",\n'       "$DEPLOY_NAME"
        printf '    "namespace": "%s",\n'        "$NAMESPACE"
        printf '    "revision_current": "%s",\n' "$CURR_REV"
        printf '    "revision_previous": "%s",\n' "$PREV_REV"
        printf '    "selector": "%s",\n'         "$DEPLOY_SELECTOR"
        printf '    "timestamp": "%s",\n'        "$TIMESTAMP"
        printf '    "generated_by": "k8s-deploy-manifest-diff.sh v1.1",\n'
        printf '    "purpose": "Comandos de inspeccion para equipo con acceso a PRD"\n'
        printf '  },\n'
        printf '  "commands": '
        jq -Rn '[inputs | split("\t") | {"section": .[0], "description": .[1], "command": .[2]}]' \
            < "$CMDS_TEMP"
        printf '\n}'
    } > "$json_file"
}

risk_badge() {
    case "$1" in
        CRITICAL) echo -e "${RED_BOLD}🚨 CRITICAL${NC}" ;;
        HIGH)     echo -e "${RED}🔴 HIGH${NC}" ;;
        MEDIUM)   echo -e "${YELLOW}🟡 MEDIUM${NC}" ;;
        LOW)      echo -e "${BLUE}🔵 LOW${NC}" ;;
        *)        echo -e "${DIM}⚪ NONE${NC}" ;;
    esac
}

# ─── Formatting ───────────────────────────────────────────────────────────────
TOTAL_SECTIONS=9

section() {
    out ""
    out "${CYAN}┌─ [${1}/${TOTAL_SECTIONS}] ${3}${NC}"
    out "${CYAN}└$(printf '─%.0s' {1..65})${NC}"
}

divider() { out "${DIM}  $(printf '─%.0s' {1..63})${NC}"; }

to_local() {
    [[ -n "$1" ]] && TZ="$TZ_ZONE" date -d "$1" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "—"
}

# ─── Validate Deployment exists ───────────────────────────────────────────────
if ! kubectl get deployment "$DEPLOY_NAME" -n "$NAMESPACE" &>/dev/null; then
    out "${RED_BOLD}❌ Deployment '${DEPLOY_NAME}' no encontrado en namespace '${NAMESPACE}'${NC}"
    exit 1
fi

# ─── Cargar datos del Deployment ──────────────────────────────────────────────
DEPLOY_JSON=$(kubectl get deployment "$DEPLOY_NAME" -n "$NAMESPACE" -o json 2>/dev/null)

# Obtener selector del Deployment para encontrar sus ReplicaSets
DEPLOY_SELECTOR=$(echo "$DEPLOY_JSON" | jq -r '
  .spec.selector.matchLabels
  | to_entries
  | map("\(.key)=\(.value)")
  | join(",")
')

# ─── Obtener todos los ReplicaSets del Deployment ordenados por revisión ──────
RS_JSON=$(kubectl get rs -n "$NAMESPACE" -l "$DEPLOY_SELECTOR" -o json 2>/dev/null)

CURRENT_RS=$(echo "$RS_JSON" | jq '
  .items
  | map(select(
      (.metadata.annotations["deployment.kubernetes.io/revision"] != null)
      and (.metadata.ownerReferences != null)
  ))
  | sort_by(.metadata.annotations["deployment.kubernetes.io/revision"] | tonumber)
  | last // empty
')

PREV_RS=$(echo "$RS_JSON" | jq '
  .items
  | map(select(
      (.metadata.annotations["deployment.kubernetes.io/revision"] != null)
      and (.metadata.ownerReferences != null)
  ))
  | sort_by(.metadata.annotations["deployment.kubernetes.io/revision"] | tonumber)
  | if length >= 2 then .[-2] else null end
')

CURR_REV=$(echo "$CURRENT_RS" | jq -r '.metadata.annotations["deployment.kubernetes.io/revision"] // "?"')
PREV_REV=$(echo "$PREV_RS"    | jq -r '.metadata.annotations["deployment.kubernetes.io/revision"] // "N/A"' 2>/dev/null || echo "N/A")
CURR_RS_NAME=$(echo "$CURRENT_RS" | jq -r '.metadata.name // "?"')
PREV_RS_NAME=$(echo "$PREV_RS"    | jq -r '.metadata.name // "N/A"' 2>/dev/null || echo "N/A")
CURR_RS_TS=$(echo "$CURRENT_RS"   | jq -r '.metadata.creationTimestamp // ""')
PREV_RS_TS=$(echo "$PREV_RS"      | jq -r '.metadata.creationTimestamp // ""' 2>/dev/null || echo "")

HAS_PREV=true
[[ "$PREV_RS" == "null" || -z "$PREV_RS" ]] && HAS_PREV=false

TIMESTAMP=$(TZ="$TZ_ZONE" date '+%Y-%m-%d %H:%M:%S %Z')

# ─── BANNER ───────────────────────────────────────────────────────────────────
out ""
out "${WHITE}╔══════════════════════════════════════════════════════════════════╗${NC}"
out "${WHITE}║   🚀 K8s Deploy Manifest Diff — Análisis de Impacto            ║${NC}"
out "${WHITE}╚══════════════════════════════════════════════════════════════════╝${NC}"
out "  ${WHITE}Deployment :${NC} ${CYAN}${DEPLOY_NAME}${NC}"
out "  ${WHITE}Namespace  :${NC} ${CYAN}${NAMESPACE}${NC}"
out "  ${WHITE}Analizado  :${NC} ${DIM}${TIMESTAMP}${NC}"
out "  ${WHITE}Rev. actual:${NC} #${CURR_REV} — ${DIM}$(to_local "$CURR_RS_TS") | ${CURR_RS_NAME}${NC}"
if $HAS_PREV; then
    out "  ${WHITE}Rev. prev. :${NC} #${PREV_REV} — ${DIM}$(to_local "$PREV_RS_TS") | ${PREV_RS_NAME}${NC}"
else
    out "  ${WHITE}Rev. prev. :${NC} ${YELLOW}N/A — Primera revisión o revisión anterior no disponible${NC}"
fi
[[ -n "$EXPORT_FILE" ]] && out "  ${WHITE}Export     :${NC} ${DIM}${EXPORT_FILE}${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# [1] ROLLOUT STATUS
# ═══════════════════════════════════════════════════════════════════════════════
section 1 $TOTAL_SECTIONS "ROLLOUT STATUS"

DESIRED=$(echo "$DEPLOY_JSON"     | jq -r '.spec.replicas // 1')
READY=$(echo "$DEPLOY_JSON"       | jq -r '.status.readyReplicas // 0')
AVAILABLE=$(echo "$DEPLOY_JSON"   | jq -r '.status.availableReplicas // 0')
UPDATED=$(echo "$DEPLOY_JSON"     | jq -r '.status.updatedReplicas // 0')
UNAVAILABLE=$(echo "$DEPLOY_JSON" | jq -r '.status.unavailableReplicas // 0')
STRATEGY=$(echo "$DEPLOY_JSON"    | jq -r '.spec.strategy.type // "RollingUpdate"')
MAX_SURGE=$(echo "$DEPLOY_JSON"   | jq -r '.spec.strategy.rollingUpdate.maxSurge // "25%"')
MAX_UNAVAIL=$(echo "$DEPLOY_JSON" | jq -r '.spec.strategy.rollingUpdate.maxUnavailable // "25%"')

if [[ "$READY" -eq "$DESIRED" && "$AVAILABLE" -eq "$DESIRED" ]]; then
    out "  ${GREEN}✅ Disponible — ${READY}/${DESIRED} réplicas listas${NC}"
else
    out "  ${RED_BOLD}❌ Degradado — listas: ${READY}/${DESIRED} | actualizadas: ${UPDATED} | no disponibles: ${UNAVAILABLE}${NC}"
    add_risk "CRITICAL" "Deployment degradado: ${READY}/${DESIRED} réplicas listas"
fi

out "  ${WHITE}Estrategia :${NC} ${STRATEGY}  (maxSurge: ${MAX_SURGE} | maxUnavailable: ${MAX_UNAVAIL})"
[[ "$UNAVAILABLE" -gt 0 ]] && { out "  ${YELLOW}⚠️  ${UNAVAILABLE} réplica(s) no disponible(s)${NC}"; add_risk "HIGH" "${UNAVAILABLE} réplica(s) no disponibles post-deploy"; }

add_cmd "Rollout" "Estado del rollout" "kubectl rollout status deployment/${DEPLOY_NAME} -n ${NAMESPACE}"
add_cmd "Rollout" "Historial de revisiones" "kubectl rollout history deployment/${DEPLOY_NAME} -n ${NAMESPACE}"
add_cmd "Rollout" "Descriptor completo" "kubectl describe deployment ${DEPLOY_NAME} -n ${NAMESPACE}"
add_cmd "Rollout" "YAML del deployment" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o yaml"

# ═══════════════════════════════════════════════════════════════════════════════
# [2] DIFF DE IMAGEN
# ═══════════════════════════════════════════════════════════════════════════════
section 2 $TOTAL_SECTIONS "DIFF DE IMAGEN DE CONTENEDORES"

echo "$CURRENT_RS" | jq -r '.spec.template.spec.containers[] | "\(.name)|\(.image)"' 2>/dev/null \
    > "$WORK_DIR/curr_images.txt" || true
echo "N/A|N/A" > "$WORK_DIR/prev_images.txt"
$HAS_PREV && echo "$PREV_RS" | jq -r '.spec.template.spec.containers[] | "\(.name)|\(.image)"' 2>/dev/null \
    > "$WORK_DIR/prev_images.txt" || true

IMAGE_CHANGED=false
while IFS='|' read -r cname cimage; do
    [[ -z "$cname" ]] && continue
    pimage=$(grep "^${cname}|" "$WORK_DIR/prev_images.txt" | cut -d'|' -f2 || echo "N/A")
    if [[ "$cimage" != "$pimage" ]]; then
        IMAGE_CHANGED=true
        CURR_TAG=$(echo "$cimage" | awk -F: '{print $NF}')
        PREV_TAG=$(echo "$pimage" | awk -F: '{print $NF}')
        out "  ${WHITE}Contenedor: ${CYAN}${cname}${NC}"
        out "    ${DIM}Anterior : ${pimage}${NC}"
        out "    ${CYAN}Actual   : ${cimage}${NC}"
        if [[ "$CURR_TAG" == "latest" ]]; then
            out "    $(risk_badge CRITICAL) Tag ':latest' — imagen no reproducible"
            add_risk "CRITICAL" "'${cname}' usa tag ':latest' — build no trazable"
        else
            out "    $(risk_badge HIGH) Cambio de imagen: ${PREV_TAG} → ${CURR_TAG}"
            add_risk "HIGH" "'${cname}' imagen cambiada: ${PREV_TAG} → ${CURR_TAG}"
        fi
        divider
    else
        out "  ${GREEN}✅ ${cname}${NC} — sin cambio${DIM} (${cimage})${NC}"
    fi
done < "$WORK_DIR/curr_images.txt"

$IMAGE_CHANGED || out "  ${GREEN}✅ Sin cambios en imágenes${NC}"

add_cmd "Imagen" "Pods activos con imagen" "kubectl get pods -n ${NAMESPACE} -l ${DEPLOY_SELECTOR} -o wide"
add_cmd "Imagen" "Imagen actual por contenedor" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[*].image}'"

# ═══════════════════════════════════════════════════════════════════════════════
# [3] DIFF DE RECURSOS (CPU / Memory)
# ═══════════════════════════════════════════════════════════════════════════════
section 3 $TOTAL_SECTIONS "DIFF DE RECURSOS (CPU / Memory limits & requests)"

extract_resources() {
    echo "$1" | jq -r '
      .spec.template.spec.containers[] |
      "\(.name)|req.cpu=\(.resources.requests.cpu // "—") req.mem=\(.resources.requests.memory // "—") lim.cpu=\(.resources.limits.cpu // "—") lim.mem=\(.resources.limits.memory // "—")"
    ' 2>/dev/null | sort || true
}

extract_resources "$CURRENT_RS" > "$WORK_DIR/curr_res.txt"
extract_resources "$PREV_RS"    > "$WORK_DIR/prev_res.txt"

if diff -q "$WORK_DIR/curr_res.txt" "$WORK_DIR/prev_res.txt" &>/dev/null; then
    out "  ${GREEN}✅ Sin cambios en recursos${NC}"
    while IFS= read -r l; do out "  ${DIM}${l}${NC}"; done < "$WORK_DIR/curr_res.txt"
else
    while IFS='|' read -r cname rinfo; do
        prev_info=$(grep "^${cname}|" "$WORK_DIR/prev_res.txt" | cut -d'|' -f2 || echo "N/A")
        if [[ "$rinfo" != "$prev_info" ]]; then
            out "  ${WHITE}Contenedor [${cname}]:${NC}"
            out "    ${RED}- ${prev_info}${NC}"
            out "    ${GREEN}+ ${rinfo}${NC}"
            # Detectar limits eliminados
            curr_lcpu=$(echo "$rinfo"     | grep -oP 'lim\.cpu=\K[^ ]+' || echo "")
            curr_lmem=$(echo "$rinfo"     | grep -oP 'lim\.mem=\K[^ ]+' || echo "")
            prev_lcpu=$(echo "$prev_info" | grep -oP 'lim\.cpu=\K[^ ]+' || echo "")
            prev_lmem=$(echo "$prev_info" | grep -oP 'lim\.mem=\K[^ ]+' || echo "")
            if ([[ "$prev_lcpu" != "—" ]] && [[ "$curr_lcpu" == "—" ]]) ||
               ([[ "$prev_lmem" != "—" ]] && [[ "$curr_lmem" == "—" ]]); then
                out "    $(risk_badge CRITICAL) Limits eliminados — riesgo de OOM / CPU starvation"
                add_risk "CRITICAL" "[${cname}] Resource limits eliminados"
            else
                out "    $(risk_badge MEDIUM) Recursos ajustados"
                add_risk "MEDIUM" "[${cname}] Recursos cambiados"
            fi
        else
            out "  ${GREEN}✅ [${cname}]${NC} — sin cambio  ${DIM}(${rinfo})${NC}"
        fi
    done < "$WORK_DIR/curr_res.txt"
fi

add_cmd "Recursos" "Uso de CPU/Memoria en tiempo real" "kubectl top pods -n ${NAMESPACE} -l ${DEPLOY_SELECTOR}"
add_cmd "Recursos" "Limits y requests configurados" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[*].resources}' | jq ."

# ═══════════════════════════════════════════════════════════════════════════════
# [4] DIFF DE ENV VARS Y REFERENCIAS (ConfigMap / Secret)
# ═══════════════════════════════════════════════════════════════════════════════
section 4 $TOTAL_SECTIONS "DIFF DE ENV VARS Y REFERENCIAS DE ENTORNO"

# Env vars directas (con valor literal)
echo "$CURRENT_RS" | jq -r '
  .spec.template.spec.containers[] |
  .name as $c |
  (.env // [])[] |
  select(.value != null) |
  "\($c)|\(.name)|\(.value)"
' 2>/dev/null | sort > "$WORK_DIR/curr_env.txt" || true

echo "$PREV_RS" | jq -r '
  .spec.template.spec.containers[] |
  .name as $c |
  (.env // [])[] |
  select(.value != null) |
  "\($c)|\(.name)|\(.value)"
' 2>/dev/null | sort > "$WORK_DIR/prev_env.txt" || true

comm -13 "$WORK_DIR/prev_env.txt" "$WORK_DIR/curr_env.txt" > "$WORK_DIR/env_added.txt"   2>/dev/null || true
comm -23 "$WORK_DIR/prev_env.txt" "$WORK_DIR/curr_env.txt" > "$WORK_DIR/env_removed.txt" 2>/dev/null || true

if [[ ! -s "$WORK_DIR/env_added.txt" && ! -s "$WORK_DIR/env_removed.txt" ]]; then
    out "  ${GREEN}✅ Sin cambios en variables de entorno directas${NC}"
else
    [[ -s "$WORK_DIR/env_added.txt" ]] && while IFS='|' read -r cname vname vval; do
        $FULL_ENV && display="${vname} = ${vval}" || display="${vname}"
        out "  ${GREEN}  + [${cname}] ${display}${NC}"
        add_risk "MEDIUM" "Env var '${vname}' agregada en '${cname}'"
    done < "$WORK_DIR/env_added.txt"
    [[ -s "$WORK_DIR/env_removed.txt" ]] && while IFS='|' read -r cname vname vval; do
        out "  ${RED}  - [${cname}] ${vname}${NC}"
        add_risk "HIGH" "Env var '${vname}' eliminada de '${cname}'"
    done < "$WORK_DIR/env_removed.txt"
fi

# Referencias de entorno (valueFrom + envFrom)
divider
out "  ${WHITE}Referencias de ConfigMap / Secret en env:${NC}"

extract_env_refs() {
    echo "$1" | jq -r '
      .spec.template.spec.containers[] |
      .name as $c |
      (
        ((.env // [])[] | select(.valueFrom != null) |
          "\($c)|\(.name)|" + (
            if .valueFrom.configMapKeyRef then "ConfigMap:\(.valueFrom.configMapKeyRef.name)/\(.valueFrom.configMapKeyRef.key)"
            elif .valueFrom.secretKeyRef then "Secret:\(.valueFrom.secretKeyRef.name)/\(.valueFrom.secretKeyRef.key)"
            elif .valueFrom.fieldRef then "FieldRef:\(.valueFrom.fieldRef.fieldPath)"
            else "resourceField" end
          )
        ),
        ((.envFrom // [])[] |
          "\($c)|envFrom|" + (
            if .configMapRef then "ConfigMap:\(.configMapRef.name)"
            elif .secretRef then "Secret:\(.secretRef.name)"
            else "unknown" end
          )
        )
      )
    ' 2>/dev/null | sort || true
}

extract_env_refs "$CURRENT_RS" > "$WORK_DIR/curr_refs.txt" || true
extract_env_refs "$PREV_RS"    > "$WORK_DIR/prev_refs.txt" || true

comm -13 "$WORK_DIR/prev_refs.txt" "$WORK_DIR/curr_refs.txt" > "$WORK_DIR/refs_added.txt"   2>/dev/null || true
comm -23 "$WORK_DIR/prev_refs.txt" "$WORK_DIR/curr_refs.txt" > "$WORK_DIR/refs_removed.txt" 2>/dev/null || true

if [[ ! -s "$WORK_DIR/refs_added.txt" && ! -s "$WORK_DIR/refs_removed.txt" ]]; then
    out "  ${GREEN}  ✅ Sin cambios en referencias de entorno${NC}"
    [[ -s "$WORK_DIR/curr_refs.txt" ]] && while IFS= read -r l; do out "  ${DIM}  ${l}${NC}"; done < "$WORK_DIR/curr_refs.txt"
else
    [[ -s "$WORK_DIR/curr_refs.txt" ]]    && while IFS= read -r l; do out "  ${DIM}  ${l}${NC}"; done < "$WORK_DIR/curr_refs.txt"
    [[ -s "$WORK_DIR/refs_added.txt" ]]   && while IFS='|' read -r c v ref; do
        out "  ${GREEN}  + [${c}] ${v} ← ${ref}${NC}"
        add_risk "MEDIUM" "Nueva referencia de entorno: ${c}/${v} ← ${ref}"
    done < "$WORK_DIR/refs_added.txt"
    [[ -s "$WORK_DIR/refs_removed.txt" ]] && while IFS='|' read -r c v ref; do
        out "  ${RED}  - [${c}] ${v} ← ${ref}${NC}"
        add_risk "HIGH" "Referencia eliminada: ${c}/${v} ← ${ref}"
    done < "$WORK_DIR/refs_removed.txt"
fi

add_cmd "EnvVars" "Variables de entorno del pod template" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[*].env}' | jq ."
add_cmd "EnvVars" "Variables desde pod en ejecucion" "kubectl exec -n ${NAMESPACE} deployment/${DEPLOY_NAME} -- env | sort"

# ═══════════════════════════════════════════════════════════════════════════════
# [5] CONFIGMAPS REFERENCIADOS
# ═══════════════════════════════════════════════════════════════════════════════
section 5 $TOTAL_SECTIONS "CONFIGMAPS REFERENCIADOS"

extract_cm_names() {
    echo "$1" | jq -r '
      (
        (.spec.template.spec.volumes // [])[]?.configMap.name // empty,
        (.spec.template.spec.containers[].envFrom // [])[]?.configMapRef.name // empty,
        (.spec.template.spec.containers[].env // [])[]?.valueFrom.configMapKeyRef.name // empty
      )
    ' 2>/dev/null | sort -u || true
}

extract_cm_names "$CURRENT_RS" > "$WORK_DIR/curr_cms.txt" || true
extract_cm_names "$PREV_RS"    > "$WORK_DIR/prev_cms.txt" || true

comm -13 "$WORK_DIR/prev_cms.txt" "$WORK_DIR/curr_cms.txt" > "$WORK_DIR/cms_added.txt"   2>/dev/null || true
comm -23 "$WORK_DIR/prev_cms.txt" "$WORK_DIR/curr_cms.txt" > "$WORK_DIR/cms_removed.txt" 2>/dev/null || true
comm -12 "$WORK_DIR/prev_cms.txt" "$WORK_DIR/curr_cms.txt" > "$WORK_DIR/cms_common.txt"  2>/dev/null || true

[[ -s "$WORK_DIR/cms_added.txt" ]]   && while IFS= read -r cm; do
    out "  ${GREEN}+ ConfigMap agregado   : ${cm}${NC}"
    add_risk "MEDIUM" "Nuevo ConfigMap referenciado: '${cm}'"
done < "$WORK_DIR/cms_added.txt"

[[ -s "$WORK_DIR/cms_removed.txt" ]] && while IFS= read -r cm; do
    out "  ${RED}- ConfigMap eliminado  : ${cm}${NC}"
    add_risk "HIGH" "ConfigMap eliminado de referencias: '${cm}'"
done < "$WORK_DIR/cms_removed.txt"

[[ -s "$WORK_DIR/cms_common.txt" ]] && while IFS= read -r cm; do
    [[ -z "$cm" ]] && continue
    out "  ${WHITE}📋 ConfigMap: ${CYAN}${cm}${NC}"
    if kubectl get configmap "$cm" -n "$NAMESPACE" &>/dev/null; then
        CM_DATA=$(kubectl get configmap "$cm" -n "$NAMESPACE" -o json 2>/dev/null)
        CM_KEYS=$(echo "$CM_DATA" | jq -r '.data | keys[]?' 2>/dev/null | sort | tr '\n' ' ')
        CM_COUNT=$(echo "$CM_DATA" | jq '.data | length // 0' 2>/dev/null || echo 0)
        out "     ${DIM}${CM_COUNT} key(s): ${CM_KEYS}${NC}"
        out "     ${DIM}⚠  Diff de valores históricos requiere GitOps/Flux — mostrando estado actual${NC}"
        add_cmd "ConfigMap" "Contenido de ConfigMap: ${cm}" "kubectl get configmap ${cm} -n ${NAMESPACE} -o yaml"
    else
        out "     ${RED_BOLD}❌ NO ENCONTRADO en el cluster${NC}"
        add_risk "CRITICAL" "ConfigMap '${cm}' referenciado no existe en cluster"
    fi
done < "$WORK_DIR/cms_common.txt"

! { [[ -s "$WORK_DIR/curr_cms.txt" ]] && grep -q . "$WORK_DIR/curr_cms.txt"; } && \
    out "  ${DIM}Sin ConfigMaps referenciados${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# [6] SECRETS REFERENCIADOS
# ═══════════════════════════════════════════════════════════════════════════════
section 6 $TOTAL_SECTIONS "SECRETS REFERENCIADOS (solo keys — valores enmascarados)"

extract_secret_names() {
    echo "$1" | jq -r '
      (
        (.spec.template.spec.volumes // [])[]?.secret.secretName // empty,
        (.spec.template.spec.containers[].envFrom // [])[]?.secretRef.name // empty,
        (.spec.template.spec.containers[].env // [])[]?.valueFrom.secretKeyRef.name // empty,
        (.spec.template.spec.imagePullSecrets // [])[]?.name // empty
      )
    ' 2>/dev/null | sort -u || true
}

extract_secret_names "$CURRENT_RS" > "$WORK_DIR/curr_secs.txt" || true
extract_secret_names "$PREV_RS"    > "$WORK_DIR/prev_secs.txt" || true

comm -13 "$WORK_DIR/prev_secs.txt" "$WORK_DIR/curr_secs.txt" > "$WORK_DIR/secs_added.txt"   2>/dev/null || true
comm -23 "$WORK_DIR/prev_secs.txt" "$WORK_DIR/curr_secs.txt" > "$WORK_DIR/secs_removed.txt" 2>/dev/null || true
comm -12 "$WORK_DIR/prev_secs.txt" "$WORK_DIR/curr_secs.txt" > "$WORK_DIR/secs_common.txt"  2>/dev/null || true

[[ -s "$WORK_DIR/secs_added.txt" ]]   && while IFS= read -r s; do
    out "  ${YELLOW}+ Secret agregado   : ${s}${NC}"
    add_risk "HIGH" "Nuevo Secret referenciado: '${s}'"
done < "$WORK_DIR/secs_added.txt"

[[ -s "$WORK_DIR/secs_removed.txt" ]] && while IFS= read -r s; do
    out "  ${RED_BOLD}- Secret eliminado  : ${s}${NC}"
    add_risk "CRITICAL" "Secret eliminado de referencias: '${s}'"
done < "$WORK_DIR/secs_removed.txt"

[[ -s "$WORK_DIR/secs_common.txt" ]] && while IFS= read -r sec; do
    [[ -z "$sec" ]] && continue
    out "  ${WHITE}🔐 Secret: ${CYAN}${sec}${NC}"
    if kubectl get secret "$sec" -n "$NAMESPACE" &>/dev/null; then
        SEC_KEYS=$(kubectl get secret "$sec" -n "$NAMESPACE" \
            -o json 2>/dev/null | jq -r '.data | keys[]?' 2>/dev/null | sort | tr '\n' ' ')
        SEC_COUNT=$(kubectl get secret "$sec" -n "$NAMESPACE" \
            -o json 2>/dev/null | jq '.data | length // 0' 2>/dev/null || echo 0)
        out "     ${DIM}${SEC_COUNT} key(s): ${SEC_KEYS}${NC}"
        out "     ${DIM}(Valores no mostrados por seguridad)${NC}"
        add_cmd "Secret" "Keys del Secret (sin valores): ${sec}" "kubectl get secret ${sec} -n ${NAMESPACE} -o json | jq '.data | keys'"
    else
        out "     ${RED_BOLD}❌ NO ENCONTRADO en el cluster${NC}"
        add_risk "CRITICAL" "Secret '${sec}' referenciado no existe en cluster"
    fi
done < "$WORK_DIR/secs_common.txt"

! { [[ -s "$WORK_DIR/curr_secs.txt" ]] && grep -q . "$WORK_DIR/curr_secs.txt"; } && \
    out "  ${DIM}Sin Secrets referenciados${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# [7] DIFF DE PROBES
# ═══════════════════════════════════════════════════════════════════════════════
section 7 $TOTAL_SECTIONS "DIFF DE PROBES (Liveness / Readiness / Startup)"

extract_probes() {
    echo "$1" | jq -r '
      .spec.template.spec.containers[] |
      .name as $c |
      "\($c)|liveness=\(
        if .livenessProbe then
          (if .livenessProbe.httpGet then "HTTP:\(.livenessProbe.httpGet.path):\(.livenessProbe.httpGet.port)"
           elif .livenessProbe.tcpSocket then "TCP:\(.livenessProbe.tcpSocket.port)"
           elif .livenessProbe.exec then "EXEC"
           else "defined" end
          ) + " init=\(.livenessProbe.initialDelaySeconds // 0)s period=\(.livenessProbe.periodSeconds // 10)s fail=\(.livenessProbe.failureThreshold // 3)"
        else "NONE" end
      ) readiness=\(
        if .readinessProbe then
          (if .readinessProbe.httpGet then "HTTP:\(.readinessProbe.httpGet.path):\(.readinessProbe.httpGet.port)"
           elif .readinessProbe.tcpSocket then "TCP:\(.readinessProbe.tcpSocket.port)"
           elif .readinessProbe.exec then "EXEC"
           else "defined" end
          ) + " init=\(.readinessProbe.initialDelaySeconds // 0)s period=\(.readinessProbe.periodSeconds // 10)s fail=\(.readinessProbe.failureThreshold // 3)"
        else "NONE" end
      ) startup=\(if .startupProbe then "defined" else "NONE" end)"
    ' 2>/dev/null | sort || true
}

extract_probes "$CURRENT_RS" > "$WORK_DIR/curr_probes.txt" || true
extract_probes "$PREV_RS"    > "$WORK_DIR/prev_probes.txt" || true

if diff -q "$WORK_DIR/curr_probes.txt" "$WORK_DIR/prev_probes.txt" &>/dev/null; then
    out "  ${GREEN}✅ Sin cambios en probes${NC}"
    while IFS= read -r l; do out "  ${DIM}${l}${NC}"; done < "$WORK_DIR/curr_probes.txt"
else
    while IFS='|' read -r cname pinfo; do
        prev_pinfo=$(grep "^${cname}|" "$WORK_DIR/prev_probes.txt" | cut -d'|' -f2 || echo "N/A")
        if [[ "${cname}|${pinfo}" != "$(grep "^${cname}|" "$WORK_DIR/prev_probes.txt" || echo "NOMATCH")" ]]; then
            out "  ${WHITE}Contenedor [${cname}]:${NC}"
            out "    ${RED}  - ${prev_pinfo}${NC}"
            out "    ${GREEN}  + ${pinfo}${NC}"
            # Detectar eliminación de liveness
            if echo "$prev_pinfo" | grep -q "liveness=HTTP\|liveness=TCP\|liveness=EXEC"; then
                if echo "$pinfo" | grep -q "liveness=NONE"; then
                    out "    $(risk_badge CRITICAL) Liveness probe eliminada — pods en fallo NO serán reiniciados"
                    add_risk "CRITICAL" "[${cname}] Liveness probe eliminada"
                fi
            fi
            # Detectar eliminación de readiness
            if echo "$prev_pinfo" | grep -q "readiness=HTTP\|readiness=TCP\|readiness=EXEC"; then
                if echo "$pinfo" | grep -q "readiness=NONE"; then
                    out "    $(risk_badge HIGH) Readiness probe eliminada — tráfico sin validación de disponibilidad"
                    add_risk "HIGH" "[${cname}] Readiness probe eliminada"
                fi
            fi
            # Cambio de parámetros sin eliminar
            if ! (echo "$pinfo" | grep -q "liveness=NONE" && echo "$pinfo" | grep -q "readiness=NONE"); then
                grep -q "CRITICAL\|HIGH" "$RISK_FILE" 2>/dev/null || add_risk "MEDIUM" "[${cname}] Parámetros de probe cambiados"
            fi
        else
            out "  ${GREEN}✅ [${cname}]${NC} — sin cambio"
        fi
    done < "$WORK_DIR/curr_probes.txt"
fi

add_cmd "Probes" "Liveness probe configurada" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[*].livenessProbe}' | jq ."
add_cmd "Probes" "Readiness probe configurada" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[*].readinessProbe}' | jq ."

# ═══════════════════════════════════════════════════════════════════════════════
# [8] HPA / VOLUMES / SERVICEACCOUNT
# ═══════════════════════════════════════════════════════════════════════════════
section 8 $TOTAL_SECTIONS "HPA / VOLUMES / SERVICEACCOUNT"

# HPA
if kubectl get hpa "$DEPLOY_NAME" -n "$NAMESPACE" &>/dev/null; then
    HPA_JSON=$(kubectl get hpa "$DEPLOY_NAME" -n "$NAMESPACE" -o json 2>/dev/null)
    HPA_MIN=$(echo "$HPA_JSON"     | jq -r '.spec.minReplicas // 1')
    HPA_MAX=$(echo "$HPA_JSON"     | jq -r '.spec.maxReplicas // "?"')
    HPA_CURR=$(echo "$HPA_JSON"    | jq -r '.status.currentReplicas // "?"')
    HPA_METRICS=$(echo "$HPA_JSON" | jq -r '
      .spec.metrics[]? |
      "\(.type):\(.resource.name // .external.metric.name // "custom")"
    ' 2>/dev/null | tr '\n' ',' | sed 's/,$//' || echo "—")
    out "  ${WHITE}📈 HPA:${NC}  min=${HPA_MIN}  max=${HPA_MAX}  actual=${HPA_CURR}  métricas: ${HPA_METRICS}"
    if [[ "$DESIRED" -gt "$HPA_MAX" ]] 2>/dev/null; then
        out "  $(risk_badge HIGH) spec.replicas (${DESIRED}) > HPA maxReplicas (${HPA_MAX})"
        add_risk "HIGH" "spec.replicas > HPA maxReplicas — HPA reescalará a la baja"
    fi
    add_cmd "HPA" "Estado y métricas del HPA" "kubectl get hpa ${DEPLOY_NAME} -n ${NAMESPACE} -o yaml"
else
    out "  ${DIM}Sin HPA configurado${NC}"
fi

add_cmd "HPA" "Volumes declarados en el deployment" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.volumes}' | jq ."
add_cmd "HPA" "ServiceAccount del deployment" "kubectl get deployment ${DEPLOY_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.serviceAccountName}'"

divider

# Volumes (diff)
echo "$CURRENT_RS" | jq -r '
  .spec.template.spec.containers[].volumeMounts[]? |
  "\(.name) → \(.mountPath)" + (if .readOnly then " [readOnly]" else "" end)
' 2>/dev/null | sort > "$WORK_DIR/curr_vols.txt" || true

echo "$PREV_RS" | jq -r '
  .spec.template.spec.containers[].volumeMounts[]? |
  "\(.name) → \(.mountPath)" + (if .readOnly then " [readOnly]" else "" end)
' 2>/dev/null | sort > "$WORK_DIR/prev_vols.txt" || true

comm -13 "$WORK_DIR/prev_vols.txt" "$WORK_DIR/curr_vols.txt" > "$WORK_DIR/vols_added.txt"   2>/dev/null || true
comm -23 "$WORK_DIR/prev_vols.txt" "$WORK_DIR/curr_vols.txt" > "$WORK_DIR/vols_removed.txt" 2>/dev/null || true

out "  ${WHITE}📦 Volumes montados:${NC}"
[[ -s "$WORK_DIR/curr_vols.txt" ]] && while IFS= read -r v; do out "  ${DIM}  ${v}${NC}"; done < "$WORK_DIR/curr_vols.txt"
[[ -s "$WORK_DIR/vols_added.txt" ]]   && while IFS= read -r v; do
    out "  ${GREEN}  + ${v}${NC}"
    add_risk "MEDIUM" "Volume mount agregado: ${v}"
done < "$WORK_DIR/vols_added.txt"
[[ -s "$WORK_DIR/vols_removed.txt" ]] && while IFS= read -r v; do
    out "  ${RED}  - ${v}${NC}"
    add_risk "HIGH" "Volume mount eliminado: ${v}"
done < "$WORK_DIR/vols_removed.txt"
! { [[ -s "$WORK_DIR/curr_vols.txt" ]] && grep -q . "$WORK_DIR/curr_vols.txt"; } && out "  ${DIM}  (ninguno)${NC}"

divider

# ServiceAccount
CURR_SA=$(echo "$CURRENT_RS" | jq -r '.spec.template.spec.serviceAccountName // "default"')
PREV_SA="default"
$HAS_PREV && PREV_SA=$(echo "$PREV_RS" | jq -r '.spec.template.spec.serviceAccountName // "default"' 2>/dev/null || echo "default")
out "  ${WHITE}🔑 ServiceAccount:${NC} ${CURR_SA}"
if [[ "$CURR_SA" != "$PREV_SA" ]]; then
    out "  $(risk_badge HIGH) ServiceAccount cambiado: '${PREV_SA}' → '${CURR_SA}'"
    add_risk "HIGH" "ServiceAccount cambiado: '${PREV_SA}' → '${CURR_SA}'"
else
    out "  ${GREEN}  ✅ ServiceAccount sin cambio${NC}"
fi

# SecurityContext
CURR_PRIV=$(echo "$CURRENT_RS" | jq -r '
  [.spec.template.spec.containers[].securityContext.privileged // false] | any
' 2>/dev/null || echo "false")
PREV_PRIV="false"
$HAS_PREV && PREV_PRIV=$(echo "$PREV_RS" | jq -r '
  [.spec.template.spec.containers[].securityContext.privileged // false] | any
' 2>/dev/null || echo "false")
if [[ "$CURR_PRIV" == "true" && "$PREV_PRIV" == "false" ]]; then
    out "  $(risk_badge CRITICAL) Contenedor privilegiado habilitado (securityContext.privileged=true)"
    add_risk "CRITICAL" "Contenedor con privileged=true — acceso root al nodo"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# [9] EVENTOS RECIENTES
# ═══════════════════════════════════════════════════════════════════════════════
add_cmd "Eventos" "Eventos recientes del deployment" "kubectl get events -n ${NAMESPACE} --field-selector involvedObject.name=${DEPLOY_NAME} --sort-by=.metadata.creationTimestamp"
add_cmd "Eventos" "Logs recientes de todos los pods" "kubectl logs -n ${NAMESPACE} -l ${DEPLOY_SELECTOR} --tail=50 --prefix=true"
add_cmd "Rollback" "Revertir a revision anterior" "kubectl rollout undo deployment/${DEPLOY_NAME} -n ${NAMESPACE}"
add_cmd "Rollback" "Revertir a revision especifica" "kubectl rollout undo deployment/${DEPLOY_NAME} -n ${NAMESPACE} --to-revision=${PREV_REV}"
add_cmd "Rollback" "Verificar estado post-rollback" "kubectl rollout status deployment/${DEPLOY_NAME} -n ${NAMESPACE} --timeout=5m"

if ! $NO_EVENTS; then
    section 9 $TOTAL_SECTIONS "EVENTOS RECIENTES DEL DEPLOYMENT Y PODS"

    ALL_EVENTS_JSON=$(kubectl get events -n "$NAMESPACE" \
        --sort-by=.metadata.creationTimestamp -o json 2>/dev/null | \
        jq --arg d "$DEPLOY_NAME" '
          .items | map(select(
            .involvedObject.name == $d or
            (.involvedObject.name | startswith($d + "-"))
          ))
          | sort_by(.metadata.creationTimestamp)
          | reverse
          | .[:30]
        ' 2>/dev/null || echo "[]")

    WARN_COUNT=$(echo "$ALL_EVENTS_JSON" | jq '[.[] | select(.type=="Warning")] | length' 2>/dev/null || echo 0)
    NORM_COUNT=$(echo "$ALL_EVENTS_JSON" | jq '[.[] | select(.type=="Normal")] | length' 2>/dev/null || echo 0)
    TOTAL_EVTS=$(echo "$ALL_EVENTS_JSON" | jq 'length' 2>/dev/null || echo 0)

    out "  ${WHITE}Eventos:${NC}  ${GREEN}Normal: ${NORM_COUNT}${NC}   ${YELLOW}Warning: ${WARN_COUNT}${NC}   (total recientes: ${TOTAL_EVTS})"
    divider

    if [[ "$TOTAL_EVTS" -gt 0 ]]; then
        printf "  ${WHITE}%-10s %-22s %-32s %s${NC}\n" "Tipo" "Razón" "Objeto" "Mensaje"
        out "  ${DIM}$(printf '─%.0s' {1..78})${NC}"
        echo "$ALL_EVENTS_JSON" | jq -r '.[] |
          "\(.type)|\(.reason)|\(.involvedObject.name)|\(.message | gsub("\n";" "))"
        ' 2>/dev/null | while IFS='|' read -r etype ereason ename emsg; do
            [[ -z "$etype" ]] && continue
            objshort="${ename:0:32}"
            msgshort="${emsg:0:55}"
            if [[ "$etype" == "Warning" ]]; then
                printf "  ${YELLOW}%-10s %-22s %-32s %s${NC}\n" "$etype" "$ereason" "$objshort" "$msgshort"
            else
                printf "  ${GREEN}%-10s %-22s %-32s %s${NC}\n" "$etype" "$ereason" "$objshort" "$msgshort"
            fi
        done
    else
        out "  ${DIM}Sin eventos recientes asociados${NC}"
    fi

    if [[ "$WARN_COUNT" -gt 3 ]]; then
        add_risk "HIGH"   "${WARN_COUNT} Warning events en el deployment — posible inestabilidad"
    elif [[ "$WARN_COUNT" -gt 0 ]]; then
        add_risk "MEDIUM" "${WARN_COUNT} Warning event(s) detectado(s)"
    fi
else
    section 9 $TOTAL_SECTIONS "EVENTOS RECIENTES (omitido con --no-events)"
    out "  ${DIM}Usar sin --no-events para ver eventos${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL DE RIESGOS
# ═══════════════════════════════════════════════════════════════════════════════
N_CRIT=$(count_risk "CRITICAL")
N_HIGH=$(count_risk "HIGH")
N_MED=$(count_risk "MEDIUM")
N_LOW=$(count_risk "LOW")

MAX_RISK="NONE"
[[ "$N_LOW"  -gt 0 ]] && MAX_RISK="LOW"
[[ "$N_MED"  -gt 0 ]] && MAX_RISK="MEDIUM"
[[ "$N_HIGH" -gt 0 ]] && MAX_RISK="HIGH"
[[ "$N_CRIT" -gt 0 ]] && MAX_RISK="CRITICAL"

out ""
out "${WHITE}╔══════════════════════════════════════════════════════════════════╗${NC}"
out "${WHITE}║                   RESUMEN DE RIESGOS                           ║${NC}"
out "${WHITE}╚══════════════════════════════════════════════════════════════════╝${NC}"
out ""
out "  🚨 CRITICAL : ${RED_BOLD}${N_CRIT}${NC}    🔴 HIGH : ${RED}${N_HIGH}${NC}    🟡 MEDIUM : ${YELLOW}${N_MED}${NC}    🔵 LOW : ${BLUE}${N_LOW}${NC}"
out "  Nivel máximo : $(risk_badge "$MAX_RISK")"
out ""

if [[ -s "$RISK_FILE" ]]; then
    out "  ${WHITE}Hallazgos:${NC}"
    while IFS='|' read -r level msg; do
        [[ -z "$level" ]] && continue
        badge=$(risk_badge "$level")
        out "    ${badge}  ${msg}"
    done < "$RISK_FILE"
else
    out "  ${GREEN}✅ Sin hallazgos de riesgo — despliegue limpio${NC}"
fi

out ""
out "  ${WHITE}Recomendaciones:${NC}"
[[ "$N_CRIT" -gt 0 ]] && out "  ${RED_BOLD}  • Escalar inmediatamente con el equipo de ingeniería. NO promover a prod.${NC}"
[[ "$N_HIGH" -gt 0 ]] && out "  ${RED}  • Revisar los cambios con el equipo técnico antes del siguiente deploy.${NC}"
[[ "$N_MED"  -gt 0 ]] && out "  ${YELLOW}  • Ejecutar smoke tests y monitorear métricas los próximos 30 minutos.${NC}"
[[ "$N_CRIT" -eq 0 && "$N_HIGH" -eq 0 && "$N_MED" -eq 0 ]] && \
    out "  ${GREEN}  • Monitorear dashboards de observabilidad (error rate, latencia, saturación).${NC}"
out "  ${DIM}  • Consultar: kubectl rollout history deploy/${DEPLOY_NAME} -n ${NAMESPACE}${NC}"
out "  ${DIM}  • Rollback:  kubectl rollout undo deploy/${DEPLOY_NAME} -n ${NAMESPACE}${NC}"

out ""
out "${DIM}  K8s Deploy Manifest Diff v1.1 | devsecops-toolbox | ${TIMESTAMP}${NC}"
[[ -n "$EXPORT_FILE" ]] && out "${GREEN}  📁 Informe exportado: ${EXPORT_FILE}${NC}"
out ""

# ═══════════════════════════════════════════════════════════════════════════════
# COMANDOS DE INSPECCIÓN PARA PRD
# ═══════════════════════════════════════════════════════════════════════════════
if $SHOW_COMMANDS && [[ -s "$CMDS_TEMP" ]]; then
    out ""
    out "${WHITE}╔═════════════════════════════════════════════════════════════════╗${NC}"
    out "${WHITE}║   📋 COMANDOS DE INSPECCIÓN PARA PRD                          ║${NC}"
    out "${WHITE}╚═════════════════════════════════════════════════════════════════╝${NC}"
    out "  ${DIM}Comparte estos comandos con el equipo que tiene acceso a PRD.${NC}"
    out "  ${DIM}Deployment: ${DEPLOY_NAME} | Namespace: ${NAMESPACE} | Rev: #${CURR_REV}${NC}"
    out ""
    PREV_SECTION=""
    while IFS=$'\t' read -r _sec _desc _cmd; do
        [[ -z "$_sec" ]] && continue
        if [[ "$_sec" != "$PREV_SECTION" ]]; then
            [[ -n "$PREV_SECTION" ]] && out ""
            out "  ${WHITE}── ${_sec} ──${NC}"
            PREV_SECTION="$_sec"
        fi
        out "  ${DIM}  ${_desc}${NC}"
        out "  ${CYAN}  \$ ${_cmd}${NC}"
    done < "$CMDS_TEMP"
    out ""
    mkdir -p outcome
    CMDS_JSON_FILE="outcome/k8s_commands_${DEPLOY_NAME}_${NAMESPACE}_${TS_RUN}.json"
    write_commands_json "$CMDS_JSON_FILE"
    out "  ${GREEN}📄 Comandos exportados: ${CMDS_JSON_FILE}${NC}"
fi

# ─── Exit code ────────────────────────────────────────────────────────────────
case "$MAX_RISK" in
    CRITICAL) exit 2 ;;
    HIGH)     exit 1 ;;
    MEDIUM)   exit 1 ;;
    *)        exit 0 ;;
esac
