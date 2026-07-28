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
DOWNLOAD_OPTIONAL_MODELS=1
MODEL_DOWNLOAD_JOBS=4
CUDA_PREFLIGHT=1
CUDA_STARTUP_ATTEMPTS=12
CUDA_STARTUP_DELAY_SECONDS=5
INSTALL_EASY_USE=0
INSTALL_RGTHREE=0
INSTALL_CONTROLNET_AUX=0
INSTALL_OPENPOSE_EDITOR=0
FIX_TORCHAUDIO_CUDA=1
RUN_DEP_CHECK=0
HF_TOKEN={{ RUNPOD_SECRET_HF_TOKEN }}
CIVITAI_TOKEN={{ RUNPOD_SECRET_CIVITAI_TOKEN }}
COMFYUI_ARGS=--reserve-vram 3
```

Keep tokens in RunPod Secrets. Do not paste raw tokens into a public template.

The default manifest keeps the diffusion model set focused on WAI-ANIMA, while
still downloading the bundled character LoRAs, separated pose/action LoRAs, and
the Anima Turbo LoRA.
Downloads run in parallel; increase or decrease `MODEL_DOWNLOAD_JOBS` if the
network or disk is the bottleneck.

`CUDA_PREFLIGHT=1` verifies that PyTorch can read GPU memory before any model
downloads or optional node setup. It retries for about one minute by default,
which covers normal GPU initialization delays without repeating the expensive
startup work. If every attempt fails, fully stop and restart the Pod or choose
another GPU host.

The default startup does not install ControlNet Aux, OpenPose Editor, Easy-Use,
or rgthree. The bundled Anima workflows use the Anima custom node plus ComfyUI
core nodes, so those helper nodes only add startup time for the current setup.
Set `INSTALL_CONTROLNET_AUX=1` only when you need DWPose/OpenPose/depth/canny
preprocessors, `INSTALL_OPENPOSE_EDITOR=1` only when you want the editor UI,
and `INSTALL_EASY_USE=1` or `INSTALL_RGTHREE=1` only for your own legacy
workflows that reference those nodes.

LoRA and checkpoint downloads are unaffected by those install flags.
`FIX_TORCHAUDIO_CUDA=1` repairs a TorchAudio CUDA wheel mismatch before ComfyUI
starts. Leave it enabled if logs show PyTorch and TorchAudio were compiled with
different CUDA versions.

## Model Layout

Startup downloads:

```text
/workspace/comfyui/models/diffusion_models/waiANIMA_v10Base10.safetensors
/workspace/comfyui/models/diffusion_models/Diving - Anima v40.safetensors
/workspace/comfyui/models/diffusion_models/nova3DCGAM_v10.safetensors
/workspace/comfyui/models/text_encoders/qwen_3_06b_base.safetensors
/workspace/comfyui/models/vae/qwen_image_vae.safetensors
/workspace/comfyui/models/upscale_models/4x-AnimeSharp.pth
/workspace/comfyui/models/loras/qwen_image_union_diffsynth_lora.safetensors
/workspace/comfyui/models/loras/anima-turbo-lora-v0.2.safetensors
/workspace/comfyui/models/loras/anima/*.safetensors
/workspace/comfyui/models/loras/anima_pose/*.safetensors
```

Character LoRAs in `models/loras/anima/` use character-first filenames such as
`Rapi - Anima.safetensors`, so ComfyUI's LoRA selector is easier to scan. When
a renamed LoRA is present, the startup downloader removes its older manifest
filename such as `anima_rapi.safetensors`.

Pose/action LoRAs are stored separately in `models/loras/anima_pose/` with
numbered readable names so they stay out of the character LoRA folder. `Diving -
Anima v40.safetensors` is treated as a diffusion checkpoint, not a LoRA; if an
older Pod has it under `models/loras/anima/`, the downloader removes that
legacy file after the checkpoint path exists.

Additional LoRAs can be added at Pod startup without rebuilding the Docker image. Put a small manifest in `EXTRA_MODEL_MANIFEST_JSON` or host it somewhere and set `EXTRA_MODEL_MANIFEST_URL`.

Example for a future Velvet LoRA:

```text
EXTRA_MODEL_MANIFEST_JSON={"models":[{"name":"Velvet Anima LoRA","enabled":true,"required":false,"method":"curl","url":"https://huggingface.co/uwgm/nikke-loras/resolve/main/YOUR_VELVET_LORA.safetensors","path":"models/loras/anima/velvet_anima.safetensors","headers":{"Authorization":"Bearer ${HF_TOKEN}"},"min_bytes":1048576}]}
```

## ComfyUI

Open RunPod Connect for port `8188`.

The container installs or refreshes the custom variation node on every startup
and copies every JSON file from its `example_workflows` directory into ComfyUI's
normal Workflows list, currently:

```text
anima_hiresfix_esrgan_2pass.json
anima_hiresfix_latent_2pass.json
anima_two_character_inpaint_hiresfix.json
```

Restart an existing Pod once after this image update to receive them.

`anima_two_character_inpaint_hiresfix.json` first builds the complete
interaction with Character A's LoRA and a temporary second character. Copy that
base image into the included Load Image node, paint Character B with ComfyUI's
Mask Editor, then enable the red final Save node. Character B's LoRA is applied
only to the masked inpaint sampler. The result is composited over the untouched
base pixels, upscaled with AnimeSharp, resized to an exact 1160x1536, and
finished with a low-denoise Turbo pass.

The workflow uses current ComfyUI core inpaint nodes and the bundled readable
character selector. It does not require ControlNet Aux, OpenPose, or another
inpaint node pack.

Use the official Anima ComfyUI workflow or any native Anima/Qwen Image workflow, then select:

```text
Diffusion model: waiANIMA_v10Base10.safetensors
Text encoder: qwen_3_06b_base.safetensors
VAE: qwen_image_vae.safetensors
Upscale model: 4x-AnimeSharp.pth
Control LoRA: qwen_image_union_diffsynth_lora.safetensors
Speed LoRA: anima-turbo-lora-v0.2.safetensors
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
