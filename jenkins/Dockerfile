FROM jenkins/jenkins:lts
USER root
RUN apt-get update && apt-get install -y docker.io python3 python3-venv python3-pip curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts --install-dir=/opt
ENV PATH=$PATH:/opt/google-cloud-sdk/bin
RUN npm install -g firebase-tools
