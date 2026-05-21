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
RUN_DEP_CHECK=0
HF_TOKEN={{ RUNPOD_SECRET_HF_TOKEN }}
CIVITAI_TOKEN={{ RUNPOD_SECRET_CIVITAI_TOKEN }}
COMFYUI_ARGS=--reserve-vram 3
```

## 4. Open ComfyUI

Use RunPod Connect port `8188`.

The first boot downloads the model files. Later boots reuse `/workspace/comfyui/models`.
