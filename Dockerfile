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
COPY workflows/ /opt/runpod-anima-image/workflows/
COPY custom_nodes/ /opt/runpod-anima-image/custom_nodes/

# Fixed upstream node ID/signature; no extra preprocessor packages are needed.
ARG ANIMA_LLLITE_REV=b7495bd8eb876e334509976896702484ed19cdbb
RUN git init /opt/runpod-anima-image/vendor/ComfyUI-Anima-LLLite \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-Anima-LLLite remote add origin https://github.com/kohya-ss/ComfyUI-Anima-LLLite.git \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-Anima-LLLite fetch --depth 1 origin "${ANIMA_LLLITE_REV}" \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-Anima-LLLite checkout --detach FETCH_HEAD

# App Builder and its mobile/mask editor interface use this tested stable UI.
ARG COMFYUI_FRONTEND_VERSION=1.54.8
RUN python3 -m pip install --no-cache-dir "comfyui-frontend-package==${COMFYUI_FRONTEND_VERSION}"
RUN chmod +x /opt/runpod-anima-image/scripts/*.sh

EXPOSE 8188

ENTRYPOINT []
CMD ["/opt/runpod-anima-image/scripts/start.sh"]
