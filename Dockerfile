# ═══════════════════════════════════════════════════════════════════════════════
# DevSecOps Toolbox - Multi-Cloud CLI Container (Slim Edition)
# ═══════════════════════════════════════════════════════════════════════════════
# Imagen base: python:3.11-slim (ligera, ~60MB vs ~80MB de ubuntu:22.04)
# Incluye: Azure CLI, AWS CLI, Google Cloud SDK, kubectl, helm, terraform
# Netshoot: ping, dig, traceroute, tcpdump, nmap, netcat, etc.
# Python: Todas las dependencias de requirements.txt de subfolders
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ═══════════════════════════════════════════════════════════════════════════════
# LABELS
# ═══════════════════════════════════════════════════════════════════════════════
LABEL maintainer="Harold Adrian" \
      version="1.5.2" \
      description="Multi-cloud DevSecOps toolbox"

# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIAS DEL SISTEMA
# ═══════════════════════════════════════════════════════════════════════════════
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Herramientas básicas
    curl \
    wget \
    ca-certificates \
    gnupg \
    lsb-release \
    # Herramientas de red (netshoot esenciales)
    iputils-ping \
    dnsutils \
    net-tools \
    tcpdump \
    traceroute \
    mtr \
    iperf3 \
    nmap \
    netcat-openbsd \
    iproute2 \
    socat \
    # Utilidades
    jq \
    git \
    unzip \
    openssh-client \
    # Limpieza
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ═══════════════════════════════════════════════════════════════════════════════
# AZURE CLI
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# ═══════════════════════════════════════════════════════════════════════════════
# AWS CLI v2
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip -q awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws/

# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE CLOUD SDK (solo componentes esenciales)
# ═══════════════════════════════════════════════════════════════════════════════
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
    tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-cloud-sdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ═══════════════════════════════════════════════════════════════════════════════
# KUBECTL
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl -fsSL "https://dl.k8s/release/$(curl -L -s https://dl.k8s/release/stable.txt)/bin/linux/amd64/kubectl" \
    -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl

# ═══════════════════════════════════════════════════════════════════════════════
# HELM
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl -fsSL https://get.helm.sh/helm-v3.13.3-linux-amd64.tar.gz | tar -xz \
    && mv linux-amd64/helm /usr/local/bin/helm \
    && rm -rf linux-amd64

# ═══════════════════════════════════════════════════════════════════════════════
# TERRAFORM
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip -o terraform.zip \
    && unzip -q terraform.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform.zip

# ═══════════════════════════════════════════════════════════════════════════════
# PYTHON DEPENDENCIES - Instalar TODOS los requirements.txt
# ═══════════════════════════════════════════════════════════════════════════════
WORKDIR /tmp/requirements

# Copiar todos los requirements.txt de subfolders
COPY scm/aws/requirements.txt ./aws.txt
COPY scm/azdo/requirements.txt ./azdo.txt
COPY scm/gcp/requirements.txt ./gcp.txt
COPY scm/gcp/artifact-registry/requirements.txt ./gcp-artifact.txt
COPY scm/gcp/certificate-manager/requirements.txt ./gcp-cert.txt
COPY scm/gcp/cloud-armor/requirements.txt ./gcp-armor.txt
COPY scm/gcp/cloud-sql/requirements.txt ./gcp-sql.txt
COPY scm/gcp/cluster-gke/requirements.txt ./gcp-gke.txt
COPY scm/gcp/gateway-services/requirements.txt ./gcp-gateway.txt
COPY scm/gcp/monitoring/requirements.txt ./gcp-monitor.txt
COPY scm/gcp/reports-viewer/requirements.txt ./gcp-reports.txt
COPY scm/gcp/rolesypermisos/requirements.txt ./gcp-roles.txt
COPY scm/gcp/secrets-configmaps/requirements.txt ./gcp-secrets.txt
COPY scm/gcp/vpc-networks/requirements.txt ./gcp-vpc.txt

# Combinar todos los requirements y eliminar duplicados
RUN cat *.txt 2>/dev/null | grep -v "^#" | grep -v "^$" | sort -u > /tmp/all-requirements.txt \
    && pip install --no-cache-dir -r /tmp/all-requirements.txt \
    && rm -rf /tmp/requirements /tmp/all-requirements.txt

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL PROYECTO
# ═══════════════════════════════════════════════════════════════════════════════
WORKDIR /app

# Copiar solo el código fuente necesario (sin tests, docs, etc.)
COPY scm/ /app/scm/
COPY VERSION /app/VERSION

# ═══════════════════════════════════════════════════════════════════════════════
# USUARIO NO-ROOT
# ═══════════════════════════════════════════════════════════════════════════════
RUN groupadd -r devsecops && useradd -r -g devsecops -m -s /bin/bash devsecops \
    && chown -R devsecops:devsecops /app

# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLES DE ENTORNO
# ═══════════════════════════════════════════════════════════════════════════════
ENV PATH="/usr/local/bin:/usr/local/sbin:/usr/local/gcloud/google-cloud-sdk/bin:${PATH}" \
    PYTHONPATH="/app" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTHCHECK
# ═══════════════════════════════════════════════════════════════════════════════
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD az version >/dev/null 2>&1 && aws --version >/dev/null 2>&1 && gcloud version >/dev/null 2>&1 || exit 1

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER devsecops
WORKDIR /home/devsecops

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/bin/bash"]
