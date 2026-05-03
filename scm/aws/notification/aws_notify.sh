#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# aws_notify.sh — AWS EKS Workload Notifier via Google Chat Webhook
#
# Equivalente AWS de: webhooks.sh / webhooks_optimized.sh (GCP Notification)
#
# Monitorea deployments de Kubernetes en clusters EKS y envía notificaciones
# a Google Chat con estado de pods, réplicas y condiciones de deployments.
#
# Uso:
#   ./aws_notify.sh                        # Todos los proyectos configurados
#   ./aws_notify.sh --cluster my-cluster   # Cluster específico
#   ./aws_notify.sh --namespace kube-system
#   ./aws_notify.sh --dry-run              # Simula sin enviar webhook
#   ./aws_notify.sh --help
#
# Requisitos: aws cli, kubectl, jq
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-${SCRIPT_DIR}/config.json}"

# ─── Validación de config.json ─────────────────────────────────────────────
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Error: config.json no encontrado en $CONFIG_FILE"
    echo "   Copia config.json.template a config.json y configura las URLs de webhook."
    exit 1
fi

WEBHOOK_URL="$(jq -r '.webhook.url // empty' "$CONFIG_FILE")"
if [[ -z "$WEBHOOK_URL" ]]; then
    echo "❌ Error: webhook.url no definido en $CONFIG_FILE" >&2
    exit 1
fi

AWS_PROFILE="$(jq -r '.aws.profile // "default"' "$CONFIG_FILE")"
AWS_REGION="$(jq -r '.aws.region // "us-east-1"' "$CONFIG_FILE")"

# ─── Argumentos ────────────────────────────────────────────────────────────
CLUSTER_FILTER=""
NAMESPACE_FILTER=""
DRY_RUN=false

show_help() {
    echo "Uso: $0 [OPTIONS]"
    echo ""
    echo "Opciones:"
    echo "  --cluster   CLUSTER    Filtrar por nombre de cluster EKS"
    echo "  --namespace NS         Filtrar por namespace (default: todos)"
    echo "  --dry-run              Simula el mensaje sin enviar al webhook"
    echo "  --help                 Muestra esta ayuda"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cluster)   CLUSTER_FILTER="$2"; shift 2 ;;
        --namespace) NAMESPACE_FILTER="$2"; shift 2 ;;
        --dry-run)   DRY_RUN=true; shift ;;
        --help)      show_help ;;
        *) echo "⚠️  Argumento desconocido: $1"; shift ;;
    esac
done

# ─── Helpers ────────────────────────────────────────────────────────────────
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
NOW_EPOCH=$(date +%s)

send_webhook() {
    local payload="$1"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "──── DRY-RUN payload ────"
        echo "$payload" | jq .
        echo "─────────────────────────"
        return
    fi
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$payload" > /dev/null
}

emoji_status() {
    local available="$1" ready="$2" replicas="$3"
    if [[ "$available" -ge "$replicas" && "$ready" -ge "$replicas" ]]; then
        echo "🟢"
    elif [[ "$available" -gt 0 ]]; then
        echo "🟡"
    else
        echo "🔴"
    fi
}

update_kubeconfig() {
    local cluster="$1"
    aws eks update-kubeconfig \
        --name "$cluster" \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" \
        --quiet 2>/dev/null || true
}

# ─── Obtener clusters EKS ───────────────────────────────────────────────────
get_clusters() {
    if [[ -n "$CLUSTER_FILTER" ]]; then
        echo "$CLUSTER_FILTER"
        return
    fi
    aws eks list-clusters \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" \
        --query 'clusters[]' \
        --output text 2>/dev/null | tr '\t' '\n'
}

# ─── Procesar un cluster ─────────────────────────────────────────────────────
process_cluster() {
    local cluster="$1"
    echo "  ▶ Procesando cluster: $cluster"

    update_kubeconfig "$cluster"

    local ns_flag=""
    [[ -n "$NAMESPACE_FILTER" ]] && ns_flag="-n $NAMESPACE_FILTER" || ns_flag="--all-namespaces"

    local deployments
    deployments="$(kubectl get deployments $ns_flag -o json 2>/dev/null)" || return

    local total ready_count not_ready_count
    total="$(echo "$deployments" | jq '.items | length')"
    [[ "$total" -eq 0 ]] && return

    ready_count=0
    not_ready_count=0
    local deploy_rows=""

    while IFS= read -r deploy_json; do
        local name namespace replicas ready available
        name="$(echo "$deploy_json" | jq -r '.metadata.name')"
        namespace="$(echo "$deploy_json" | jq -r '.metadata.namespace')"
        replicas="$(echo "$deploy_json" | jq -r '.spec.replicas // 0')"
        ready="$(echo "$deploy_json" | jq -r '.status.readyReplicas // 0')"
        available="$(echo "$deploy_json" | jq -r '.status.availableReplicas // 0')"

        local icon
        icon="$(emoji_status "$available" "$ready" "$replicas")"

        if [[ "$available" -ge "$replicas" ]]; then
            ((ready_count++)) || true
        else
            ((not_ready_count++)) || true
        fi

        deploy_rows+="${icon} *${namespace}/${name}* | ${ready}/${replicas}\n"
    done < <(echo "$deployments" | jq -c '.items[]')

    # Construir mensaje para Google Chat
    local cluster_status_icon
    if [[ "$not_ready_count" -eq 0 ]]; then
        cluster_status_icon="🟢"
    elif [[ "$not_ready_count" -lt "$total" ]]; then
        cluster_status_icon="🟡"
    else
        cluster_status_icon="🔴"
    fi

    local message
    message="$(cat <<EOF
{
  "cards": [
    {
      "header": {
        "title": "${cluster_status_icon} EKS Workload Status",
        "subtitle": "Cluster: ${cluster} | ${TIMESTAMP}",
        "imageUrl": "https://a0.awsstatic.com/libra-css/images/logos/aws_logo_smile_1200x630.png"
      },
      "sections": [
        {
          "header": "📊 Resumen",
          "widgets": [
            {
              "textParagraph": {
                "text": "Cluster: <b>${cluster}</b> | Region: <b>${AWS_REGION}</b>\nTotal deployments: <b>${total}</b> | ✅ Ready: <b>${ready_count}</b> | ❌ Not Ready: <b>${not_ready_count}</b>"
              }
            }
          ]
        },
        {
          "header": "☸️  Deployments",
          "widgets": [
            {
              "textParagraph": {
                "text": "$(echo -e "$deploy_rows" | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|/\\n/g')"
              }
            }
          ]
        }
      ]
    }
  ]
}
EOF
)"
    send_webhook "$message"
    echo "    ✅ Notificación enviada ($total deployments)"
}

# ─── Main ───────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         AWS EKS Workload Notifier                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Región:  ${AWS_REGION}"
echo "  Profile: ${AWS_PROFILE}"
echo "  Webhook: $(echo "$WEBHOOK_URL" | cut -c1-60)..."
[[ "$DRY_RUN" == "true" ]] && echo "  Modo:    DRY-RUN (no se envían webhooks)"
echo ""

CLUSTERS="$(get_clusters)"
if [[ -z "$CLUSTERS" ]]; then
    echo "⚠️  No se encontraron clusters EKS en región: $AWS_REGION"
    exit 0
fi

while IFS= read -r cluster; do
    [[ -z "$cluster" ]] && continue
    process_cluster "$cluster"
done <<< "$CLUSTERS"

echo ""
echo "✅ Notificaciones completadas: $(date '+%H:%M:%S')"
