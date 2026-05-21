# RunPod Anima ComfyUI

RunPod ComfyUI template for Anima / WAI-ANIMA image generation with the trained Siren Anima LoRAs.

This image bakes only ComfyUI startup glue and downloader scripts. Large model files are downloaded into `/workspace/comfyui/models` at Pod startup so a persistent RunPod volume can reuse them.

## Container Image

After pushing this repo to GitHub, GitHub Actions builds:

```text
ghcr.io/YOUR_GITHUB_USER/YOUR_REPO:cuda12.8
```

For your account, if the repo is named `anima-image-runpod`:

```text
ghcr.io/grawthings-beep/anima-image-runpod:cuda12.8
```

## RunPod Template

Use:

```text
Type: Pod
Compute type: Nvidia GPU
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

Keep tokens in RunPod Secrets. Do not paste raw tokens into a public template.

## Model Layout

Startup downloads:

```text
/workspace/comfyui/models/diffusion_models/wai_anima_2859702.safetensors
/workspace/comfyui/models/text_encoders/qwen_3_06b_base.safetensors
/workspace/comfyui/models/vae/qwen_image_vae.safetensors
/workspace/comfyui/models/loras/anima/siren_anima_step-3500.safetensors
/workspace/comfyui/models/loras/anima/siren_anima_step-4000.safetensors
```

## ComfyUI

Open RunPod Connect for port `8188`.

Use the official Anima ComfyUI workflow or any native Anima/Qwen Image workflow, then select:

```text
Diffusion model: wai_anima_2859702.safetensors
Text encoder: qwen_3_06b_base.safetensors
VAE: qwen_image_vae.safetensors
LoRA: anima/siren_anima_step-4000.safetensors
```

Suggested settings from the Anima model card:

```text
Resolution: about 1MP, e.g. 1024x1024, 896x1152, 1152x896
Steps: 30-50
CFG: 4-5
```

## Sources

- Anima official model card: https://huggingface.co/circlestone-labs/Anima
- WAI-ANIMA model page: https://civitai.red/models/2544636/wai-anima?modelVersionId=2859702
- ComfyUI Anima workflow: https://www.comfy.org/ja/workflows/image_anima_preview/
