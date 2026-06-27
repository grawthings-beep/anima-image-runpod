# RunPod Anima ComfyUI

RunPod ComfyUI template for Anima / WAI-ANIMA image generation with reusable LoRA downloads.

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

Additional LoRAs can be added at Pod startup without rebuilding the Docker image. Put a small manifest in `EXTRA_MODEL_MANIFEST_JSON` or host it somewhere and set `EXTRA_MODEL_MANIFEST_URL`.

Example for a future Velvet LoRA:

```text
EXTRA_MODEL_MANIFEST_JSON={"models":[{"name":"Velvet Anima LoRA","enabled":true,"required":false,"method":"curl","url":"https://huggingface.co/uwgm/nikke-loras/resolve/main/YOUR_VELVET_LORA.safetensors","path":"models/loras/anima/velvet_anima.safetensors","headers":{"Authorization":"Bearer ${HF_TOKEN}"},"min_bytes":1048576}]}
```

## ComfyUI

Open RunPod Connect for port `8188`.

The container installs or refreshes the custom variation node on every startup
and copies every JSON file from its `example_workflows` directory into ComfyUI's
normal Workflows list, including:

```text
ANIMA_EasyMultiAngle.json
anima_easy_multiangle_batch_workflow.json
anima_variation_batch_workflow.json
```

Restart an existing Pod once after this image update to receive them.

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

## Cloudflare Manga Composer

This repository also includes a static Cloudflare Pages app for manga layout and lettering:

```text
cloudflare/manga-composer
```

It handles panel frames, speech bubbles, Japanese text, SFX text, layout JSON import/export, and PNG export in the browser. GPU image generation stays on RunPod/ComfyUI.

To deploy it through GitHub Actions, create these repository secrets:

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

Then run the `Deploy Manga Composer Pages` workflow, or push changes under `cloudflare/manga-composer` to `main`.
