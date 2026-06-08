# RunPod Anima ComfyUI

RunPod ComfyUI template for Anima / WAI-ANIMA image generation with:

- persistent model and LoRA downloads
- a bundled Anima workflow
- local Qwen3 scene-prompt generation
- no external prompt API or per-request API charge

Large model files are downloaded into `/workspace/comfyui/models` at Pod
startup. A persistent RunPod volume reuses them on later boots.

## What The Automatic Workflow Does

`anima_auto_scene.json` keeps quality tags, character tags, and LoRA selection
fixed. A local GGUF language model generates only:

- composition and framing
- camera angle and distance
- pose, action, and character positioning
- location and situation
- expression and lighting

The generated scene is joined to the fixed tags and encoded directly for
Anima. Queueing again with a randomized scene seed produces a new scene.

The custom node accepts fictional adult characters only and rejects common
minor-related terms.

## Container Image

GitHub Actions builds:

```text
ghcr.io/grawthings-beep/anima-image-runpod:cuda12.8
```

The image includes ComfyUI startup glue, the custom scene node, the workflow,
and CPU `llama-cpp-python`. The GGUF and image model weights stay on the
persistent volume.

## RunPod Template

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
USER_DIR=/workspace/comfyui/user
DOWNLOAD_MODELS=1
RUN_DEP_CHECK=0
ANIMA_LLM_MODEL_DIR=/workspace/comfyui/models/llm_gguf
ANIMA_SCENE_LOG_DIR=/workspace/comfyui/output/anima_auto_scene/logs
OVERWRITE_BUNDLED_WORKFLOW=0
HF_TOKEN={{ RUNPOD_SECRET_HF_TOKEN }}
CIVITAI_TOKEN={{ RUNPOD_SECRET_CIVITAI_TOKEN }}
COMFYUI_ARGS=--reserve-vram 3
```

Keep tokens in RunPod Secrets. Do not paste raw tokens into a public template.

`OVERWRITE_BUNDLED_WORKFLOW=0` preserves edits made in ComfyUI. Change it to
`1` for one boot when you intentionally want to restore the repository copy.

## Downloaded Files

The base manifest includes:

```text
/workspace/comfyui/models/diffusion_models/waiANIMA_v10Base10.safetensors
/workspace/comfyui/models/text_encoders/qwen_3_06b_base.safetensors
/workspace/comfyui/models/vae/qwen_image_vae.safetensors
/workspace/comfyui/models/llm_gguf/Qwen3-4B-Q4_K_M.gguf
/workspace/comfyui/models/loras/anima-turbo-lora-v0.2.safetensors
/workspace/comfyui/models/loras/anima/anima_rapi.safetensors
/workspace/comfyui/models/loras/anima/skintextureV1.safetensors
```

The manifest also downloads the other optional character and style LoRAs
listed in [`config/anima-image-models.json`](config/anima-image-models.json).

Additional models can be supplied through `EXTRA_MODEL_MANIFEST_JSON` or
`EXTRA_MODEL_MANIFEST_URL` without rebuilding the image.

## Using ComfyUI

1. Open RunPod Connect for port `8188`.
2. Load `anima_auto_scene.json` from the workflow menu.
3. Enter the fixed tags in `character_tags`.
4. Adjust `scene_direction` or `extra_constraints` if desired.
5. Queue one or more generations.

The bundled workflow uses the existing WAI-ANIMA model and LoRAs:

```text
Diffusion model: waiANIMA_v10Base10.safetensors
Text encoder: qwen_3_06b_base.safetensors
VAE: qwen_image_vae.safetensors
LoRAs:
  anima/anima_rapi.safetensors
  anima-turbo-lora-v0.2.safetensors
  anima/skintextureV1.safetensors
```

The scene LLM runs on CPU by default (`gpu_layers=0`) to keep GPU VRAM
available for image generation.

## Outputs And Logs

Generated images and per-generation JSONL prompt logs are grouped under:

```text
/workspace/comfyui/output/anima_auto_scene/
├── anima_00001_.png
└── logs/anima_scene_generations.jsonl
```

Each JSONL record includes the scene seed, scene instructions, raw LLM output,
parsed scene, and final positive prompt.

## Sources

- [Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [Qwen3-4B GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF)
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [ComfyUI user directory documentation](https://docs.comfy.org/interface/appearance)
