FROM jenkins/inbound-agent:latest-jdk21

USER root

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    git \
    sshpass \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install Helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Ansible and required Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    ansible \
    requests \
    kubernetes

# Install Ansible collections as root, then fix permissions
RUN ansible-galaxy collection install community.general kubernetes.core \
    && chmod -R 755 /root/.ansible

# Set working directory
WORKDIR /home/jenkins

USER jenkins
