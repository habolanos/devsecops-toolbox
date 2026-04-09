# ═══════════════════════════════════════════════════════════════════════════════
# DevSecOps Toolbox - Multi-Cloud CLI Container
# ═══════════════════════════════════════════════════════════════════════════════
# Incluye: Azure CLI, AWS CLI, Google Cloud SDK, kubectl, y herramientas netshoot
# ═══════════════════════════════════════════════════════════════════════════════

FROM ubuntu:22.04

# Evitar prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ═══════════════════════════════════════════════════════════════════════════════
# LABELS
# ═══════════════════════════════════════════════════════════════════════════════
LABEL maintainer="Harold Adrian" \
      version="1.0.0" \
      description="Multi-cloud DevSecOps toolbox with Azure, AWS, GCP CLIs and netshoot tools"

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE DEPENDENCIAS BASE
# ═══════════════════════════════════════════════════════════════════════════════
RUN apt-get update && apt-get install -y \
    # Herramientas básicas
    curl \
    wget \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    # Herramientas de red (netshoot)
    iputils-ping \
    dnsutils \
    net-tools \
    tcpdump \
    traceroute \
    mtr \
    iperf3 \
    nmap \
    socat \
    netcat-openbsd \
    iproute2 \
    bridge-utils \
    ethtool \
    conntrack \
    ngrep \
    # Herramientas de análisis
    jq \
    yq \
    git \
    vim \
    nano \
    unzip \
    zip \
    tar \
    gzip \
    bzip2 \
    # Python y pip
    python3 \
    python3-pip \
    python3-venv \
    # Otras utilidades
    sudo \
    openssh-client \
    sshpass \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE AZURE CLI
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE AWS CLI (v2)
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws/

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE GOOGLE CLOUD SDK
# ═══════════════════════════════════════════════════════════════════════════════
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
    tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update \
    && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE KUBECTL
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl -LO "https://dl.k8s/release/$(curl -L -s https://dl.k8s/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE HELM
# ═══════════════════════════════════════════════════════════════════════════════
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE TERRAFORM
# ═══════════════════════════════════════════════════════════════════════════════
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y terraform \
    && rm -rf /var/lib/apt/lists/*

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALACIÓN DE HERRAMIENTAS ADICIONALES DE NETSHOOT
# ═══════════════════════════════════════════════════════════════════════════════
RUN apt-get update && apt-get install -y \
    # Análisis de red adicional
    tshark \
    termshark \
    arping \
    fping \
    hping3 \
    masscan \
    # Inspección de tráfico
    iftop \
    nethogs \
    bmon \
    slurm \
    tcptrack \
    # DNS tools
    ldnsutils \
    # HTTP tools
    httpie \
    siege \
    # SSL/TLS
    openssl \
    sslscan \
    # Utilidades de sistema
    htop \
    atop \
    glances \
    lsof \
    strace \
    ltrace \
    && rm -rf /var/lib/apt/lists/*

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL PROYECTO SCM
# ═══════════════════════════════════════════════════════════════════════════════
WORKDIR /app

# Copiar el código fuente
COPY scm/ /app/scm/
COPY VERSION /app/VERSION
COPY README.md /app/README.md

# Instalar dependencias Python del proyecto
RUN pip3 install --no-cache-dir -r /app/scm/requirements.txt || echo "No requirements.txt found"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE USUARIO Y PERMISOS
# ═══════════════════════════════════════════════════════════════════════════════
RUN groupadd -r devsecops && useradd -r -g devsecops -m -s /bin/bash devsecops \
    && echo "devsecops ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLES DE ENTORNO
# ═══════════════════════════════════════════════════════════════════════════════
ENV PATH="/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/gcloud/google-cloud-sdk/bin" \
    PYTHONPATH="/app" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTHCHECK
# ═══════════════════════════════════════════════════════════════════════════════
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD az version && aws --version && gcloud version && kubectl version --client || exit 1

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════
USER devsecops
WORKDIR /home/devsecops

# Script de inicio
COPY --chown=devsecops:devsecops docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/bin/bash"]
