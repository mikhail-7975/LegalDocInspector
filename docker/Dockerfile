FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    ca-certificates \
    iputils-ping \
    wget \
    curl \
    net-tools \
    iproute2 \
    dnsutils \
    procps \
    less \
    nano \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    vim-tiny && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN python3.12 -m pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
CMD ["/bin/bash"]
