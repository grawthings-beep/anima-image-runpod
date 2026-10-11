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

# Article-style graph: real Attention Couple, KJ color masks and PreviewBridge.
ARG PPM_REV=6c6c360155cace9d7091306c1b8e26d9c7438620
ARG KJNODES_REV=d7641533d6634eb05f8570c980fce8fc8528dc7b
ARG IMPACT_REV=429d0159ad429e64d2b3916e6e7be9c22d025c3c
RUN git init /opt/runpod-anima-image/vendor/ComfyUI-ppm \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-ppm remote add origin https://github.com/pamparamm/ComfyUI-ppm.git \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-ppm fetch --depth 1 origin "${PPM_REV}" \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-ppm checkout --detach FETCH_HEAD \
    && git init /opt/runpod-anima-image/vendor/ComfyUI-KJNodes \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-KJNodes remote add origin https://github.com/kijai/ComfyUI-KJNodes.git \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-KJNodes fetch --depth 1 origin "${KJNODES_REV}" \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-KJNodes checkout --detach FETCH_HEAD \
    && git init /opt/runpod-anima-image/vendor/ComfyUI-Impact-Pack \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-Impact-Pack remote add origin https://github.com/ltdrdata/ComfyUI-Impact-Pack.git \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-Impact-Pack fetch --depth 1 origin "${IMPACT_REV}" \
    && git -C /opt/runpod-anima-image/vendor/ComfyUI-Impact-Pack checkout --detach FETCH_HEAD
RUN python3 /opt/runpod-anima-image/scripts/install_regional_dependencies.py

# App Builder and its mobile/mask editor interface use this tested stable UI.
ARG COMFYUI_FRONTEND_VERSION=1.54.8
RUN python3 -m pip install --no-cache-dir "comfyui-frontend-package==${COMFYUI_FRONTEND_VERSION}"
RUN python3 /opt/runpod-anima-image/scripts/check_regional_runtime.py
RUN chmod +x /opt/runpod-anima-image/scripts/*.sh

EXPOSE 8188

ENTRYPOINT []
CMD ["/opt/runpod-anima-image/scripts/start.sh"]
