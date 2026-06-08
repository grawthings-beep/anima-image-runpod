# syntax=docker/dockerfile:1.7

# Anima is natively supported in recent ComfyUI builds.
ARG BASE_IMAGE=runpod/comfyui:latest
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

ARG LLAMA_CPP_PYTHON_VERSION=0.3.23

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        aria2 \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        git \
        libopenblas-dev \
        ninja-build \
    && rm -rf /var/lib/apt/lists/*

COPY config/ /opt/runpod-anima-image/config/
COPY scripts/ /opt/runpod-anima-image/scripts/
COPY custom_nodes/ /opt/runpod-anima-image/custom_nodes/
COPY workflows/ /opt/runpod-anima-image/workflows/
RUN chmod +x /opt/runpod-anima-image/scripts/*.sh

# The prompt LLM runs on CPU by default so image generation keeps all GPU VRAM.
RUN CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" \
    python -m pip install \
      "llama-cpp-python==${LLAMA_CPP_PYTHON_VERSION}" \
      --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
    && python -c "from llama_cpp import Llama; print('llama-cpp-python ready')"

EXPOSE 8188

ENTRYPOINT []
CMD ["/opt/runpod-anima-image/scripts/start.sh"]
