# syntax=docker/dockerfile:1.7

# Anima is natively supported in recent ComfyUI builds.
ARG BASE_IMAGE=runpod/comfyui:1.4.4-cuda12.8
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        aria2 \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY config/ /opt/runpod-anima-image/config/
COPY scripts/ /opt/runpod-anima-image/scripts/
RUN chmod +x /opt/runpod-anima-image/scripts/*.sh

EXPOSE 8188

ENTRYPOINT []
CMD ["/opt/runpod-anima-image/scripts/start.sh"]
