#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Docker Entrypoint Script - DevSecOps Toolbox
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        🚀 DevSecOps Toolbox - Multi-Cloud CLI Container             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que las herramientas principales estén disponibles
echo "📦 Verificando herramientas instaladas..."
echo ""

echo -n "  • Azure CLI: "
az version --query '"azure-cli"' -o tsv 2>/dev/null || echo "❌ No disponible"

echo -n "  • AWS CLI: "
aws --version 2>/dev/null | head -1 || echo "❌ No disponible"

echo -n "  • Google Cloud SDK: "
gcloud version 2>/dev/null | head -1 || echo "❌ No disponible"

echo -n "  • kubectl: "
kubectl version --client 2>/dev/null | head -1 || echo "❌ No disponible"

echo -n "  • helm: "
helm version --short 2>/dev/null || echo "❌ No disponible"

echo -n "  • terraform: "
terraform version 2>/dev/null | head -1 || echo "❌ No disponible"

echo ""
echo "🔧 Herramientas de red (netshoot) disponibles:"
echo "   ping, dig, nslookup, traceroute, mtr, iperf3, nmap, tcpdump, socat, netcat"
echo ""

# Configuración opcional de credenciales si se pasan como variables de entorno
if [ -n "$AZURE_SERVICE_PRINCIPAL" ]; then
    echo "🔐 Configurando Azure Service Principal..."
    az login --service-principal \
        --username "$AZURE_CLIENT_ID" \
        --password "$AZURE_CLIENT_SECRET" \
        --tenant "$AZURE_TENANT_ID" 2>/dev/null || echo "   ⚠️ No se pudo autenticar con Azure"
fi

if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "🔐 Configurando AWS credentials..."
    aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" 2>/dev/null
    aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" 2>/dev/null
    aws configure set region "${AWS_DEFAULT_REGION:-us-east-1}" 2>/dev/null
fi

if [ -n "$GCP_SERVICE_ACCOUNT_KEY" ]; then
    echo "🔐 Configurando Google Cloud credentials..."
    echo "$GCP_SERVICE_ACCOUNT_KEY" | base64 -d > /tmp/gcp-key.json 2>/dev/null
    gcloud auth activate-service-account --key-file=/tmp/gcp-key.json 2>/dev/null || echo "   ⚠️ No se pudo autenticar con GCP"
fi

# Configurar kubectl si se proporciona KUBECONFIG
if [ -n "$KUBECONFIG_CONTENT" ]; then
    echo "☸️  Configurando kubectl..."
    mkdir -p ~/.kube
    echo "$KUBECONFIG_CONTENT" | base64 -d > ~/.kube/config 2>/dev/null
    chmod 600 ~/.kube/config
fi

echo ""
echo "✅ Container listo para usar!"
echo ""

# Ejecutar el comando proporcionado
exec "$@"
