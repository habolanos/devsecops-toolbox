#!/bin/bash

set -euo pipefail

echo "============================================================"
echo " DevOps Toolkit Installer - Ubuntu / WSL: devsecops-toolbox"
echo "============================================================"

export DEBIAN_FRONTEND=noninteractive

echo "[1/10] Installing base packages..."

sudo apt-get update
sudo apt --fix-broken install
sudo apt-get install -y \
  ca-certificates \
  curl \
  wget \
  gnupg \
  apt-transport-https \
  software-properties-common \
  git \
  unzip \
  zip \
  jq \
  python3 \
  python3-pip \
  python3-venv \
  pipx \
  nodejs \
  kubectx \
  golang-go \
  rustc \
  cargo

echo "[2/10] Configuring pipx..."

pipx ensurepath || true
export PATH="$HOME/.local/bin:$PATH"

if ! grep -q 'HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi

echo "[3/10] Configuring Google Cloud repository..."

sudo mkdir -p /usr/share/keyrings

curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | sudo gpg --dearmor --yes \
  -o /usr/share/keyrings/cloud.google.gpg

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list >/dev/null

sudo apt-get update

echo "[4/10] Installing gcloud, kubectl and GKE auth plugin..."

sudo apt-get install -y \
  google-cloud-cli \
  google-cloud-cli-gke-gcloud-auth-plugin \
  kubectl

echo "[5/10] Installing Helm..."

curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

echo "[6/10] Installing K9s..."

ARCH=$(dpkg --print-architecture)

case "$ARCH" in
  amd64)
    K9S_PACKAGE="k9s_linux_amd64.deb"
    ;;
  arm64)
    K9S_PACKAGE="k9s_linux_arm64.deb"
    ;;
  *)
    echo "Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

curl -fsSL \
  "https://github.com/derailed/k9s/releases/latest/download/${K9S_PACKAGE}" \
  -o "/tmp/${K9S_PACKAGE}"

sudo apt-get install -y "/tmp/${K9S_PACKAGE}"

rm -f "/tmp/${K9S_PACKAGE}"

echo "[7/10] Installing PowerShell..."

source /etc/os-release

curl -fsSL \
  "https://packages.microsoft.com/config/ubuntu/${VERSION_ID}/packages-microsoft-prod.deb" \
  -o /tmp/packages-microsoft-prod.deb

sudo dpkg -i /tmp/packages-microsoft-prod.deb
rm -f /tmp/packages-microsoft-prod.deb

sudo apt-get update
sudo apt-get install -y powershell

echo "[8/10] Installing AWS CLI v2..."

case "$ARCH" in
  amd64)
    AWS_ARCH="x86_64"
    ;;
  arm64)
    AWS_ARCH="aarch64"
    ;;
esac

curl -fsSL \
  "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_ARCH}.zip" \
  -o /tmp/awscliv2.zip

unzip -q -o /tmp/awscliv2.zip -d /tmp
sudo /tmp/aws/install --update
rm -rf /tmp/awscliv2.zip /tmp/aws

echo "[9/10] Installing Azure CLI..."

curl -fsSL https://aka.ms/InstallAzureCLIDeb | sudo bash

echo "[10/10] Validating installations..."

echo
printf "%-25s %s\n" "TOOL" "VERSION"
printf "%-25s %s\n" "------------------------" "----------------------------------------"

printf "%-25s %s\n" "gcloud" "$(gcloud version 2>/dev/null | head -1 || echo FAILED)"
printf "%-25s %s\n" "kubectl" "$(kubectl version --client 2>/dev/null | head -1 || echo FAILED)"
printf "%-25s %s\n" "GKE Auth Plugin" "$(gke-gcloud-auth-plugin --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "kubectx" "$(kubectx --version 2>/dev/null || echo INSTALLED)"
printf "%-25s %s\n" "kubens" "$(command -v kubens 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "Helm" "$(helm version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "k9s" "$(k9s version --short 2>/dev/null | head -1 || echo INSTALLED)"
printf "%-25s %s\n" "jq" "$(jq --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "Python" "$(python3 --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "pip" "$(python3 -m pip --version 2>/dev/null | cut -d' ' -f1-2 || echo FAILED)"
printf "%-25s %s\n" "pipx" "$(pipx --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "Node.js" "$(node --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "npm" "$(npm --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "Go" "$(go version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "Rust" "$(rustc --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "Cargo" "$(cargo --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "Git" "$(git --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "PowerShell" "$(pwsh --version 2>/dev/null || echo FAILED)"
printf "%-25s %s\n" "AWS CLI" "$(aws --version 2>/dev/null | cut -d' ' -f1 || echo FAILED)"
printf "%-25s %s\n" "Azure CLI" "$(az --version 2>/dev/null | head -1 || echo FAILED)"

echo
echo "============================================================"
echo " 🚀 DevSecOps Toolbox"
echo "============================================================"
echo
echo "This installer is part of DevSecOps Toolbox:"
echo "A practical collection of DevOps, Cloud, Kubernetes and"
echo "DevSecOps tools, scripts and utilities for engineers."
echo
echo "⭐ If this project is useful to you, consider starring it:"
echo
echo "   https://github.com/habolanos/devsecops-toolbox"
echo
echo "Contributions, feedback and improvements are welcome."
echo
echo "============================================================"
echo " Installation completed successfully"
echo "============================================================"
echo
echo "Run:"
echo "  source ~/.bashrc"
source ~/.bashrc