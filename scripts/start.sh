#!/usr/bin/env bash
set -Eeuo pipefail

find_python_bin() {
  command -v python || command -v python3 || true
}

find_comfyui_dir() {
  if [[ -n "${COMFYUI_DIR:-}" && -f "${COMFYUI_DIR}/main.py" ]]; then
    printf '%s\n' "${COMFYUI_DIR}"
    return 0
  fi

  for candidate in \
    /opt/ComfyUI \
    /workspace/ComfyUI \
    /workspace/comfyui \
    /comfyui \
    /ComfyUI \
    /app/ComfyUI; do
    if [[ -f "${candidate}/main.py" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  local found_main
  found_main="$(find /opt /workspace /app /comfyui /ComfyUI -maxdepth 4 -type f -name main.py 2>/dev/null | head -n 1 || true)"
  if [[ -n "${found_main}" ]]; then
    dirname "${found_main}"
    return 0
  fi

  return 1
}

COMFYUI_DIR="$(find_comfyui_dir)" || {
  echo "ERROR: could not find ComfyUI main.py. Set COMFYUI_DIR explicitly." >&2
  exit 2
}

PYTHON_BIN="$(find_python_bin)" || {
  echo "ERROR: neither python nor python3 was found in PATH." >&2
  exit 2
}

sync_git_repo() {
  local repo="$1"
  local ref="$2"
  local dir="$3"
  local label="$4"

  mkdir -p "$(dirname "${dir}")"
  if [[ -d "${dir}/.git" ]]; then
    echo "Updating ${label}..."
    git -C "${dir}" fetch --depth 1 origin "${ref}" && \
      git -C "${dir}" reset --hard "origin/${ref}" || {
        echo "WARN: ${label} update failed; keeping existing copy."
        return 1
      }
  elif [[ -e "${dir}" ]]; then
    echo "WARN: ${label} directory exists but is not a git checkout: ${dir}"
    return 1
  else
    echo "Installing ${label}..."
    git clone --depth 1 --branch "${ref}" "${repo}" "${dir}" || {
      echo "WARN: ${label} clone failed."
      return 1
    }
  fi
}

repair_torchaudio_cuda_mismatch() {
  if [[ "${FIX_TORCHAUDIO_CUDA:-1}" != "1" ]]; then
    return 0
  fi

  local torch_cuda torch_cuda_tag
  torch_cuda="$("${PYTHON_BIN}" - <<'PY'
try:
    import torch
except Exception:
    print("")
else:
    print(torch.version.cuda or "")
PY
)"

  if [[ -z "${torch_cuda}" ]]; then
    echo "Skipping TorchAudio CUDA repair: torch CUDA version could not be detected."
    return 0
  fi

  if "${PYTHON_BIN}" - <<'PY'
try:
    import torch
    import torchaudio
except Exception as exc:
    print(f"torchaudio_check_error: {exc}")
    raise SystemExit(1)
print(f"torch={torch.__version__} cuda={torch.version.cuda} torchaudio={torchaudio.__version__}")
PY
  then
    return 0
  fi

  torch_cuda_tag="cu${torch_cuda//./}"
  echo "Repairing TorchAudio for PyTorch CUDA ${torch_cuda} using ${torch_cuda_tag} wheels..."
  "${PYTHON_BIN}" -m pip install --no-cache-dir --force-reinstall --no-deps \
    --index-url "https://download.pytorch.org/whl/${torch_cuda_tag}" \
    torchaudio || {
      echo "WARN: TorchAudio CUDA repair failed."
      return 0
    }

  "${PYTHON_BIN}" - <<'PY' || echo "WARN: TorchAudio still failed to import after repair."
import torch
import torchaudio
print(f"torch={torch.__version__} cuda={torch.version.cuda} torchaudio={torchaudio.__version__}")
PY
}

# --- Install / refresh the Anima Variation Batch custom node ---
if [[ "${INSTALL_ANIMA_NODE:-1}" == "1" ]]; then
  ANIMA_NODE_REPO="${ANIMA_NODE_REPO:-https://github.com/grawthings-beep/comfyui-anima-variation-batch.git}"
  ANIMA_NODE_DIR="${COMFYUI_DIR}/custom_nodes/ComfyUI-AnimaVariationBatch"
  if [[ -d "${ANIMA_NODE_DIR}/.git" ]]; then
    echo "Updating Anima Variation Batch node..."
    git -C "${ANIMA_NODE_DIR}" fetch --depth 1 origin main && git -C "${ANIMA_NODE_DIR}" reset --hard origin/main || echo "WARN: node update failed; keeping existing copy."
  else
    echo "Installing Anima Variation Batch node..."
    git clone --depth 1 "${ANIMA_NODE_REPO}" "${ANIMA_NODE_DIR}" || echo "WARN: node clone failed."
  fi

  COMFYUI_WORKFLOW_DIR="${COMFYUI_WORKFLOW_DIR:-${COMFYUI_DIR}/user/default/workflows}"
  ANIMA_WORKFLOW_SOURCE_DIR="${ANIMA_NODE_DIR}/example_workflows"
  if [[ -d "${ANIMA_WORKFLOW_SOURCE_DIR}" ]]; then
    mkdir -p "${COMFYUI_WORKFLOW_DIR}"
    shopt -s nullglob
    anima_workflow_sources=("${ANIMA_WORKFLOW_SOURCE_DIR}"/*.json)
    if (( ${#anima_workflow_sources[@]} > 0 )); then
      cp "${anima_workflow_sources[@]}" "${COMFYUI_WORKFLOW_DIR}/"
      echo "Installed ${#anima_workflow_sources[@]} Anima workflow(s) in ${COMFYUI_WORKFLOW_DIR}."
    else
      echo "WARN: no Anima workflow JSON files were found in ${ANIMA_WORKFLOW_SOURCE_DIR}."
    fi
    shopt -u nullglob
  else
    echo "WARN: Anima workflow directory was not found at ${ANIMA_WORKFLOW_SOURCE_DIR}."
  fi
fi

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/comfyui}"
MODEL_ROOT="${MODEL_ROOT:-${WORKSPACE_DIR}}"
CONFIG_DIR="${CONFIG_DIR:-/workspace/config}"
MODEL_MANIFEST="${MODEL_MANIFEST:-${CONFIG_DIR}/anima-image-models.json}"
EXTRA_MODEL_MANIFEST="${EXTRA_MODEL_MANIFEST:-${CONFIG_DIR}/extra-anima-image-models.json}"
PORT="${PORT:-8188}"
LISTEN="${LISTEN:-0.0.0.0}"

mkdir -p "${WORKSPACE_DIR}/input" \
         "${WORKSPACE_DIR}/output" \
         "${MODEL_ROOT}/models/checkpoints" \
         "${MODEL_ROOT}/models/clip" \
         "${MODEL_ROOT}/models/clip_vision" \
         "${MODEL_ROOT}/models/configs" \
         "${MODEL_ROOT}/models/controlnet" \
         "${MODEL_ROOT}/models/controlnet_aux" \
         "${MODEL_ROOT}/models/diffusion_models" \
         "${MODEL_ROOT}/models/embeddings" \
         "${MODEL_ROOT}/models/model_patches" \
         "${MODEL_ROOT}/models/loras/anima" \
         "${MODEL_ROOT}/models/text_encoders" \
         "${MODEL_ROOT}/models/unet" \
         "${MODEL_ROOT}/models/upscale_models" \
         "${MODEL_ROOT}/models/vae" \
         "${MODEL_ROOT}/models/vae_approx" \
         "${CONFIG_DIR}"

export AUX_ANNOTATOR_CKPTS_PATH="${AUX_ANNOTATOR_CKPTS_PATH:-${MODEL_ROOT}/models/controlnet_aux}"

# --- Optional helper custom nodes ---
# The bundled Anima workflows no longer need ControlNet Aux, OpenPose Editor,
# Easy-Use, or rgthree. Keep these opt-in so startup does not spend time
# installing large preprocessor dependencies.
if [[ "${INSTALL_CONTROLNET_AUX:-0}" == "1" ]]; then
  CONTROLNET_AUX_REPO="${CONTROLNET_AUX_REPO:-https://github.com/Fannovel16/comfyui_controlnet_aux.git}"
  CONTROLNET_AUX_REF="${CONTROLNET_AUX_REF:-main}"
  CONTROLNET_AUX_DIR="${COMFYUI_DIR}/custom_nodes/comfyui_controlnet_aux"
  if sync_git_repo "${CONTROLNET_AUX_REPO}" "${CONTROLNET_AUX_REF}" "${CONTROLNET_AUX_DIR}" "ControlNet Auxiliary Preprocessors"; then
    if [[ "${INSTALL_CONTROLNET_AUX_REQUIREMENTS:-1}" == "1" && -f "${CONTROLNET_AUX_DIR}/requirements.txt" ]]; then
      echo "Installing ControlNet Auxiliary Preprocessors requirements..."
      "${PYTHON_BIN}" -m pip install --no-cache-dir -r "${CONTROLNET_AUX_DIR}/requirements.txt" || \
        echo "WARN: ControlNet Auxiliary Preprocessors requirements install failed."
    fi
  fi
fi

if [[ "${INSTALL_OPENPOSE_EDITOR:-0}" == "1" ]]; then
  OPENPOSE_EDITOR_REPO="${OPENPOSE_EDITOR_REPO:-https://github.com/space-nuko/ComfyUI-OpenPose-Editor.git}"
  OPENPOSE_EDITOR_REF="${OPENPOSE_EDITOR_REF:-master}"
  OPENPOSE_EDITOR_DIR="${COMFYUI_DIR}/custom_nodes/ComfyUI-OpenPose-Editor"
  sync_git_repo "${OPENPOSE_EDITOR_REPO}" "${OPENPOSE_EDITOR_REF}" "${OPENPOSE_EDITOR_DIR}" "OpenPose Editor" || true
fi

if [[ "${INSTALL_EASY_USE:-0}" == "1" ]]; then
  EASY_USE_REPO="${EASY_USE_REPO:-https://github.com/yolain/ComfyUI-Easy-Use.git}"
  EASY_USE_REF="${EASY_USE_REF:-main}"
  EASY_USE_DIR="${COMFYUI_DIR}/custom_nodes/ComfyUI-Easy-Use"
  if sync_git_repo "${EASY_USE_REPO}" "${EASY_USE_REF}" "${EASY_USE_DIR}" "ComfyUI-Easy-Use"; then
    if [[ "${INSTALL_EASY_USE_REQUIREMENTS:-1}" == "1" && -f "${EASY_USE_DIR}/requirements.txt" ]]; then
      echo "Installing ComfyUI-Easy-Use requirements..."
      "${PYTHON_BIN}" -m pip install --no-cache-dir -r "${EASY_USE_DIR}/requirements.txt" || \
        echo "WARN: ComfyUI-Easy-Use requirements install failed."
    fi
  fi
fi

if [[ "${INSTALL_RGTHREE:-0}" == "1" ]]; then
  RGTHREE_REPO="${RGTHREE_REPO:-https://github.com/rgthree/rgthree-comfy.git}"
  RGTHREE_REF="${RGTHREE_REF:-main}"
  RGTHREE_DIR="${COMFYUI_DIR}/custom_nodes/rgthree-comfy"
  sync_git_repo "${RGTHREE_REPO}" "${RGTHREE_REF}" "${RGTHREE_DIR}" "rgthree-comfy" || true
fi

repair_torchaudio_cuda_mismatch

write_extra_model_paths() {
  local target="$1"
  cat > "${target}" <<YAML
workspace:
  base_path: ${MODEL_ROOT}
  checkpoints: models/checkpoints/
  clip: models/clip/
  clip_vision: models/clip_vision/
  configs: models/configs/
  controlnet: models/controlnet/
  diffusion_models: models/diffusion_models/
  embeddings: models/embeddings/
  model_patches: models/model_patches/
  loras: models/loras/
  text_encoders: models/text_encoders/
  unet: models/unet/
  upscale_models: models/upscale_models/
  vae: models/vae/
  vae_approx: models/vae_approx/
YAML
}

write_extra_model_paths "${COMFYUI_DIR}/extra_model_paths.yaml"
write_extra_model_paths "${COMFYUI_DIR}/extra_model_paths.yml"

if [[ -n "${MODEL_MANIFEST_JSON:-}" ]]; then
  printf '%s' "${MODEL_MANIFEST_JSON}" > "${MODEL_MANIFEST}"
elif [[ -n "${MODEL_MANIFEST_URL:-}" ]]; then
  "${PYTHON_BIN}" - "${MODEL_MANIFEST_URL}" "${MODEL_MANIFEST}" <<'PY'
import pathlib
import sys
import urllib.request

url, output = sys.argv[1], pathlib.Path(sys.argv[2])
output.parent.mkdir(parents=True, exist_ok=True)
request = urllib.request.Request(url, headers={"User-Agent": "runpod-anima-image-template"})
with urllib.request.urlopen(request, timeout=60) as response:
    output.write_bytes(response.read())
PY
elif [[ ! -f "${MODEL_MANIFEST}" && -f /opt/runpod-anima-image/config/anima-image-models.json ]]; then
  cp /opt/runpod-anima-image/config/anima-image-models.json "${MODEL_MANIFEST}"
fi

if [[ -n "${EXTRA_MODEL_MANIFEST_JSON:-}" ]]; then
  printf '%s' "${EXTRA_MODEL_MANIFEST_JSON}" > "${EXTRA_MODEL_MANIFEST}"
elif [[ -n "${EXTRA_MODEL_MANIFEST_URL:-}" ]]; then
  "${PYTHON_BIN}" - "${EXTRA_MODEL_MANIFEST_URL}" "${EXTRA_MODEL_MANIFEST}" <<'PY'
import pathlib
import sys
import urllib.request

url, output = sys.argv[1], pathlib.Path(sys.argv[2])
output.parent.mkdir(parents=True, exist_ok=True)
request = urllib.request.Request(url, headers={"User-Agent": "runpod-anima-image-template"})
with urllib.request.urlopen(request, timeout=60) as response:
    output.write_bytes(response.read())
PY
fi

if [[ "${DOWNLOAD_MODELS:-1}" == "1" ]]; then
  download_model_args=()
  if [[ "${DOWNLOAD_OPTIONAL_MODELS:-1}" != "1" ]]; then
    download_model_args+=(--required-only)
    echo "Skipping optional model downloads. Set DOWNLOAD_OPTIONAL_MODELS=1 to fetch optional LoRAs/checkpoints at startup."
  fi
  if [[ -f "${MODEL_MANIFEST}" ]]; then
    "${PYTHON_BIN}" /opt/runpod-anima-image/scripts/download_models.py \
      --manifest "${MODEL_MANIFEST}" \
      --root "${MODEL_ROOT}" \
      "${download_model_args[@]}"
  else
    echo "No base model manifest found at ${MODEL_MANIFEST}."
  fi
  if [[ -f "${EXTRA_MODEL_MANIFEST}" ]]; then
    "${PYTHON_BIN}" /opt/runpod-anima-image/scripts/download_models.py \
      --manifest "${EXTRA_MODEL_MANIFEST}" \
      --root "${MODEL_ROOT}" \
      "${download_model_args[@]}"
  fi
else
  echo "Skipping model downloads."
fi

if [[ "${RUN_DEP_CHECK:-0}" == "1" ]]; then
  "${PYTHON_BIN}" /opt/runpod-anima-image/scripts/check_env.py --comfyui-dir "${COMFYUI_DIR}" --model-root "${MODEL_ROOT}"
fi

cd "${COMFYUI_DIR}"
exec "${PYTHON_BIN}" main.py \
  --listen "${LISTEN}" \
  --port "${PORT}" \
  --enable-cors-header "${COMFYUI_CORS_ORIGIN:-*}" \
  --input-directory "${WORKSPACE_DIR}/input" \
  --output-directory "${WORKSPACE_DIR}/output" \
  ${COMFYUI_ARGS:-}
