# RunPod Steps

## 1. Push Repo

Create a GitHub repo named:

```text
anima-image-runpod
```

Then from this folder:

```powershell
git init
git config user.name "grawthings-beep"
git config user.email "grawthings-beep@users.noreply.github.com"
git add .
git commit -m "Add Anima image RunPod template"
git branch -M main
git remote add origin https://github.com/grawthings-beep/anima-image-runpod.git
git push -u origin main
```

## 2. Wait For GHCR Build

Open GitHub Actions and wait for `Build GHCR image`.

Container image:

```text
ghcr.io/grawthings-beep/anima-image-runpod:cuda12.8
```

If RunPod cannot pull it, make the GHCR package public.

## 3. RunPod Template

```text
Container image: ghcr.io/grawthings-beep/anima-image-runpod:cuda12.8
Container disk: 40 GB
Volume disk: 100 GB+
Volume mount path: /workspace
Expose HTTP ports: 8188
```

Environment variables:

```text
PORT=8188
LISTEN=0.0.0.0
WORKSPACE_DIR=/workspace/comfyui
MODEL_ROOT=/workspace/comfyui
DOWNLOAD_MODELS=1
DOWNLOAD_OPTIONAL_MODELS=1
MODEL_DOWNLOAD_JOBS=4
CUDA_PREFLIGHT=1
CUDA_NORMALIZE_VISIBLE_DEVICES=1
CUDA_STARTUP_ATTEMPTS=12
CUDA_STARTUP_DELAY_SECONDS=5
RUN_DEP_CHECK=0
HF_TOKEN={{ RUNPOD_SECRET_HF_TOKEN }}
CIVITAI_TOKEN={{ RUNPOD_SECRET_CIVITAI_TOKEN }}
COMFYUI_ARGS=--reserve-vram 3
```

Optional extra LoRA manifest:

```text
EXTRA_MODEL_MANIFEST_JSON={"models":[{"name":"Velvet Anima LoRA","enabled":true,"required":false,"method":"curl","url":"https://huggingface.co/uwgm/nikke-loras/resolve/main/YOUR_VELVET_LORA.safetensors","path":"models/loras/anima/velvet_anima.safetensors","headers":{"Authorization":"Bearer ${HF_TOKEN}"},"min_bytes":1048576}]}
```

## 4. Open ComfyUI

Use RunPod Connect port `8188`.

The first boot downloads the model files. Later boots reuse `/workspace/comfyui/models`.
