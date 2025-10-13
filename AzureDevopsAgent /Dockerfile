FROM gcr.io/kaniko-project/executor:v1.23.2-debug AS kaniko
FROM ubuntu:22.04

ARG ANGULAR_CLI_VERSION=16.1.0
ARG CRANE_VERSION=0.20.3

ENV AGENT_DIR=/azagent \
    PATH=$PATH:/kaniko \
    SSL_CERT_DIR=/kaniko/ssl/certs \
    HOME=/root \
    AGENT_ALLOW_RUNASROOT=true

ARG AGENT_VERSION=4.258.1

ENV AGENT_VERSION=${AGENT_VERSION}
ENV HELM_VERSION="v3.14.0"
ENV DEBIAN_FRONTEND=noninteractive
#ENV AZP_AGENTPACKAGE_URL=https://download.agent.dev.azure.com/agent/${AGENT_VERSION}/vsts-agent-linux-x64-${AGENT_VERSION}.tar.gz


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl jq git unzip gnupg2 bash openjdk-21-jdk maven tar wget \
      ca-certificates software-properties-common lsb-release && \
    mkdir -p ${AGENT_DIR} /kaniko && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Copy Kaniko binaries
COPY --from=kaniko /kaniko/executor /kaniko/executor
COPY --from=kaniko /kaniko/ssl /kaniko/ssl
COPY --from=kaniko /kaniko/warmer /kaniko/warmer

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @angular/cli@${ANGULAR_CLI_VERSION}

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install kubectl (latest stable)
RUN curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# Crane
RUN curl -sSL "https://github.com/google/go-containerregistry/releases/download/v${CRANE_VERSION}/go-containerregistry_Linux_x86_64.tar.gz" | tar -xz -C /usr/local/bin crane


RUN curl -sSLo /tmp/sonar-scanner.zip \
    https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip && \
    unzip /tmp/sonar-scanner.zip -d /usr/local && \
    ln -s /usr/local/sonar-scanner-5.0.1.3006-linux/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    rm /tmp/sonar-scanner.zip

RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin v0.61.0



RUN apt-get purge -y apt apt-transport-https iputils-ping net-tools --allow-remove-essential && \
    rm -rf /var/lib/apt /etc/apt /usr/share/man/* && \
    find / -name ping -type f -delete && \
    find / -name apt -type f -delete


WORKDIR ${AGENT_DIR}

# Copy entrypoint start

COPY start.sh .

RUN chmod +x ./start.sh

CMD ["/bin/bash", "./start.sh"]
