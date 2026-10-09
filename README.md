# RunPod Anima ComfyUI

RunPod ComfyUI template for Anima / WAI-ANIMA image generation with reusable LoRA downloads.

**App Mode for PC / iPhone:** six ready-to-run apps expose prompts, installed
LoRAs, aspect ratios and sampler/scheduler controls. See [APP_MODE.md](APP_MODE.md)
for the workflow inventory, iPhone operation and rollout steps.

This image includes startup/downloader scripts, six native App Mode workflows,
and small controls for aspect ratios, optional LoRAs, and region layouts. Large
model files are downloaded into `/workspace/comfyui/models` at Pod startup so a
persistent RunPod volume can reuse them.

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
CUDA_NORMALIZE_VISIBLE_DEVICES=1
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

The default manifest downloads WAI-ANIMA, Nova 3D CGAM, and MeMAX 6 Noob v-pred,
every bundled NIKKE character LoRA, Kotegawa Yui, Orihime Inoue v2, Riruka,
Kaguya 2D, Yukino S3, Yui Yuigahama S3, Rangiku TYBW, Kaoruko Waguri,
Kotobuki Hisako v2, Subaru Hoshina, Yoruichi TYBW, Qwen Image Union Control,
Anima Turbo, Skin Texture Detail, 3DCGstyle DAAAA, and Flat Color v3.
The remaining non-NIKKE character, style, and pose LoRAs stay in the bundled
on-demand catalog.
Civitai-hosted files, including 3D Animated Realistic Style and Pixel Art,
are downloaded only on request so a slow transfer cannot delay startup.
Downloads run in parallel. aria2 is preferred when available, using
`ARIA2_CONNECTIONS` and `ARIA2_SPLITS` per file, while
`MODEL_DOWNLOAD_JOBS` controls how many files download at once. Existing
manifest entries use aria2 even when their fallback method is `curl`; set
`use_aria2` to `false` only when a source does not support ranged downloads.

`CUDA_PREFLIGHT=1` verifies that PyTorch can read GPU memory before any model
downloads or optional node setup. It retries for about one minute by default,
which covers normal GPU initialization delays without repeating the expensive
startup work. If every attempt fails, fully stop and restart the Pod or choose
another GPU host.

The image is based on RunPod ComfyUI's pinned CUDA 12.8 build for RTX 50-series
support. `CUDA_NORMALIZE_VISIBLE_DEVICES=1` also repairs a stale or invalid
single-GPU visibility value before PyTorch initializes CUDA. Startup logs print
the GPU driver and PyTorch CUDA build so host-side GPU failures can be
distinguished from image compatibility problems.

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
/workspace/comfyui/models/diffusion_models/nova3DCGAM_v10.safetensors
/workspace/comfyui/models/checkpoints/MeMax6-noob-vpred.safetensors
/workspace/comfyui/models/text_encoders/qwen_3_06b_base.safetensors
/workspace/comfyui/models/vae/qwen_image_vae.safetensors
/workspace/comfyui/models/upscale_models/4x-AnimeSharp.pth
/workspace/comfyui/models/loras/qwen_image_union_diffsynth_lora.safetensors
/workspace/comfyui/models/loras/anima-turbo-lora-v0.2.safetensors
/workspace/comfyui/models/loras/anima/Skin Texture Detail.safetensors
/workspace/comfyui/models/loras/style/3DCGstyle_DAAAA.safetensors
/workspace/comfyui/models/loras/style/anima-base-1-flat-color-v3.safetensors
/workspace/comfyui/models/loras/anima/Old Maxwell - Anima.safetensors
/workspace/comfyui/models/loras/anima/Marciana - Anima v3.safetensors
/workspace/comfyui/models/loras/anima/Marciana Marine Study - Anima.safetensors
/workspace/comfyui/models/loras/anima/Rapunzel - Anima.safetensors
/workspace/comfyui/models/loras/anima/Rapunzel 2 - Anima.safetensors
/workspace/comfyui/models/loras/anima/Scarlet Black Shadow - Anima.safetensors
/workspace/comfyui/models/loras/anima/Liberalio - Anima.safetensors
/workspace/comfyui/models/loras/anima/Kotegawa Yui - Anima.safetensors
/workspace/comfyui/models/loras/anima/Orihime Inoue - Anima v2.safetensors
/workspace/comfyui/models/loras/anima/Riruka - Anima.safetensors
/workspace/comfyui/models/loras/anima/Kaguya 2D - Anima.safetensors
/workspace/comfyui/models/loras/anima/Yukino S3 - Anima.safetensors
/workspace/comfyui/models/loras/anima/Yui Yuigahama S3 - Anima.safetensors
/workspace/comfyui/models/loras/anima/Rangiku TYBW - Anima.safetensors
/workspace/comfyui/models/loras/anima/Kaoruko Waguri - Anima.safetensors
/workspace/comfyui/models/loras/anima/Kotobuki Hisako - Anima v2.safetensors
/workspace/comfyui/models/loras/anima/Subaru Hoshina - Anima.safetensors
/workspace/comfyui/models/loras/anima/Yoruichi TYBW - Anima.safetensors
/workspace/comfyui/models/loras/anima/Flora - Anima.safetensors
/workspace/comfyui/models/loras/anima/Red Hood - Anima.safetensors
/workspace/comfyui/models/loras/anima/Mint - Anima.safetensors
/workspace/comfyui/models/loras/anima/Swimsuit Rapi - Anima.safetensors
/workspace/comfyui/models/loras/anima/Swimsuit Elegg - Anima.safetensors
/workspace/comfyui/models/loras/anima/Elegg - Anima.safetensors
/workspace/comfyui/models/loras/anima/Noir - Anima.safetensors
/workspace/comfyui/models/loras/anima/Anis Star - Anima v2.safetensors
/workspace/comfyui/models/loras/anima/Anis Star 3 - Anima.safetensors
/workspace/comfyui/models/loras/anima/Rapi - Anima.safetensors
/workspace/comfyui/models/loras/anima/Prika - Anima.safetensors
/workspace/comfyui/models/loras/anima/Siren - Anima.safetensors
/workspace/comfyui/models/loras/anima/Cinderella - Anima.safetensors
/workspace/comfyui/models/loras/anima/Maid Cinderella - Anima.safetensors
/workspace/comfyui/models/loras/anima/White Cinderella - Anima.safetensors
/workspace/comfyui/models/loras/anima/Mast - Anima.safetensors
/workspace/comfyui/models/loras/anima/Maxwell - Anima.safetensors
/workspace/comfyui/models/loras/anima/Moran - Anima v1.safetensors
/workspace/comfyui/models/loras/anima/Laplace - Anima.safetensors
/workspace/comfyui/models/loras/anima/Marciana - Anima.safetensors
/workspace/comfyui/models/loras/anima/Snow White - Anima v1.safetensors
/workspace/comfyui/models/loras/anima/Blanc - Anima.safetensors
/workspace/comfyui/models/loras/anima/Privaty - Anima.safetensors
/workspace/comfyui/models/loras/anima/Label - Anima.safetensors
/workspace/comfyui/models/loras/anima/Ark Ranger Black - Anima.safetensors
/workspace/comfyui/models/loras/anima/Little Mermaid - Anima.safetensors
/workspace/comfyui/models/loras/anima/Arcana Fortune Mate - Anima.safetensors
/workspace/comfyui/models/loras/anima/Dorothy - Anima.safetensors
/workspace/comfyui/models/loras/anima/Little Mermaid Shell Princess - Anima.safetensors
/workspace/comfyui/models/loras/anima/Anis - Anima.safetensors
/workspace/comfyui/models/loras/anima/Ain - Anima.safetensors
/workspace/comfyui/models/loras/anima/Bikini Cinderella - Anima.safetensors
/workspace/comfyui/models/loras/anima/Laplace 2 - Anima.safetensors
/workspace/comfyui/models/loras/anima/Phantom - Anima.safetensors
/workspace/comfyui/models/loras/anima/Guilty - Anima.safetensors
/workspace/comfyui/models/loras/anima/Sin - Anima.safetensors
```

MeMAX is stored as a checkpoint under `models/checkpoints/`, not as an Anima
diffusion-only model or LoRA. Select it with a checkpoint loader in a compatible
workflow. 3DCGstyle DAAAA is kept separately from Anima character LoRAs under
`models/loras/style/`. These downloads do not change the bundled Anima workflows;
compatibility with those workflows has not been verified.

Rapunzel 2 is an additional download; the original Rapunzel remains available.
Flat Color v3 uses the same `models/loras/style/anima-base-1-flat-color-v3.safetensors`
path as the temporary download command, so an existing valid file is reused.

Kotobuki Hisako v2 is an additional startup download. The original Kotobuki
Hisako remains in the on-demand catalog and is not removed from model storage.

List the 14 on-demand LoRAs:

```bash
python3 /opt/runpod-anima-image/scripts/download_on_demand.py --list
```

Download one by its saved filename:

```bash
python3 /opt/runpod-anima-image/scripts/download_on_demand.py "Eris - Anima.safetensors"
```

The command uses the same `HF_TOKEN` / `CIVITAI_TOKEN`, model root, and
accelerated aria2 settings as startup. Character-first filenames keep
ComfyUI's LoRA selector readable. Moving a LoRA to the on-demand catalog does
not delete an already downloaded file.

Pose/action LoRAs are stored separately in `models/loras/anima_pose/` when they
are downloaded on demand. On startup, the downloader removes retired BAS,
Miaomiao, and Diving checkpoint files from persistent model storage once
WAI-ANIMA is available.

Guilty replaces the previous Guilty Mighty Bunny LoRA. Its old readable and
original filenames are removed only after the new Guilty file is available
and passes the configured download checks.

Orihime Inoue v2 replaces the original Orihime LoRA. It has a distinct v2
filename so an existing v1 file cannot skip the new download. The old readable
and original filenames are removed only after v2 passes the configured download
checks. Saved workflows selecting the old file need to select the v2 filename.

Additional LoRAs can be added at Pod startup without rebuilding the Docker image. Put a small manifest in `EXTRA_MODEL_MANIFEST_JSON` or host it somewhere and set `EXTRA_MODEL_MANIFEST_URL`.

Example for a future Velvet LoRA:

```text
EXTRA_MODEL_MANIFEST_JSON={"models":[{"name":"Velvet Anima LoRA","enabled":true,"required":false,"method":"curl","url":"https://huggingface.co/uwgm/nikke-loras/resolve/main/YOUR_VELVET_LORA.safetensors","path":"models/loras/anima/velvet_anima.safetensors","headers":{"Authorization":"Bearer ${HF_TOKEN}"},"min_bytes":1048576}]}
```

## ComfyUI

Open RunPod Connect for port `8188`.

The container installs or refreshes the custom variation node on every startup
and installs these three original workflows in ComfyUI's normal Workflows list:

```text
anima_hiresfix_latent_2pass.json
anima_two_character_hooks_hiresfix.json
anima_two_character_inpaint_hiresfix.json
```

The normal workflows are installed from this image's bundled `workflows/source`
files. All normal and App Mode KSamplers default to `res_multistep` / `sgm_uniform`,
including both Hires-fix passes and character inpainting. App regeneration uses
the same defaults.

The dedicated ESRGAN 2-pass workflow is excluded. An existing saved copy is
archived outside the active workflow list at startup.

The inpaint workflow builds the composition, redraws Character A inside a
mask, then redraws Character B and finishes with AnimeSharp and a low-denoise
pass. Its App Mode version separates these stages into apps 04, 05 and 06.
Transfer each saved PNG to the next app and paint the next character's mask
using the image field's Mask Editor. The final app exposes the output aspect
ratio and size.

Six native `.app.json` workflows are installed under **Anima Apps** and added
to the workflow switcher on each device. Use the same HTTPS 8188 Connect URL
from PC or iPhone. Build and deploy the updated container image to receive
the frontend and app controls; starting an old Pod alone does not guarantee
an image update. See [APP_MODE.md](APP_MODE.md) for the complete inventory.

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
