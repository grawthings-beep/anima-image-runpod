#!/usr/bin/env python3
"""Build the article-style, ordinary graph (no App Mode and no LoRA hooks)."""

import json
from pathlib import Path
import uuid

from PIL import Image, ImageDraw

from build_app_workflows import Graph

ROOT = Path(__file__).resolve().parents[1]
FILENAME = "anima_lllite_regional_ppm.json"
ASSET = "anima_regional_rgb_example.png"


def build():
    g = Graph()

    def add(kind, title, values, pos, size, inputs=(), outputs=(), color=None):
        node_id = g.add(kind, title, values, inputs, outputs)
        node = g.node(node_id)
        node.update(pos=list(pos), size=list(size), order=node_id - 1)
        if color:
            node.update(color=color, bgcolor="#24282d")
        return node_id

    model = add("UNETLoader", "WAI-ANIMA", ["waiANIMA_v10Base10.safetensors", "default"],
                (40, 80), (340, 90), outputs=(("MODEL", "MODEL"),))
    clip = add("CLIPLoader", "Qwen text encoder", ["qwen_3_06b_base.safetensors", "stable_diffusion", "default"],
               (40, 225), (340, 115), outputs=(("CLIP", "CLIP"),))
    vae = add("VAELoader", "Qwen image VAE", ["qwen_image_vae.safetensors"],
              (40, 395), (340, 65), outputs=(("VAE", "VAE"),))
    turbo = add("LoraLoaderModelOnly", "Global Turbo LoRA", ["anima-turbo-lora-v0.2.safetensors", .6],
                (40, 515), (340, 90), (("model", "MODEL"),), (("MODEL", "MODEL"),))
    skin = add("LoraLoaderModelOnly", "Global Skin Texture LoRA", ["anima/Skin Texture Detail.safetensors", .45],
               (40, 660), (340, 90), (("model", "MODEL"),), (("MODEL", "MODEL"),))
    g.connect(model, 0, turbo, "model")
    g.connect(turbo, 0, skin, "model")

    load = add("LoadImage", "RGB color map / persistent input", [ASSET, "image"],
               (455, 80), (370, 395), outputs=(("IMAGE", "IMAGE"), ("MASK", "MASK")))
    scale = add("ImageScale", "Output resolution", ["nearest-exact", 1152, 1536, "disabled"],
                (455, 535), (370, 140), (("image", "IMAGE"),), (("IMAGE", "IMAGE"),))
    bridge = add("PreviewBridge", "PreviewBridge / RGB paint", ["", False, "never"],
                 (885, 80), (420, 460), (("images", "IMAGE"),), (("IMAGE", "IMAGE"), ("MASK", "MASK")))
    size = add("GetImageSizeAndCount", "Color map size", [], (885, 610), (420, 110),
               (("image", "IMAGE"),), (("image", "IMAGE"), ("width", "INT"), ("height", "INT"), ("count", "INT")))
    save_map = add("SaveImage", "Save RGB map", ["Anima/regional_maps/map"],
                   (455, 795), (370, 320), (("images", "IMAGE"),))
    g.connect(load, 0, scale, "image")
    g.connect(scale, 0, bridge, "images")
    g.connect(bridge, 0, size, "image")
    g.connect(size, 0, save_map, "images")

    global_prompt = add("CLIPTextEncode", "Global / composition, interaction, background, light", [
        "masterpiece, best quality, score_7, safe, 2girls, two adult women sitting together at a laboratory desk, "
        "upper body, both faces at the same distance from the camera, smiling at each other, "
        "one microscope on the desk, laboratory interior, soft daylight, clean anime illustration"
    ], (1800, 80), (480, 235), (("clip", "CLIP"),), (("CONDITIONING", "CONDITIONING"),))
    g.connect(clip, 0, global_prompt, "clip")
    negative = add("ConditioningZeroOut", "Zero negative (Turbo / CFG 1)", [],
                   (2345, 80), (340, 65), (("conditioning", "CONDITIONING"),), (("CONDITIONING", "CONDITIONING"),))
    g.connect(global_prompt, 0, negative, "conditioning")

    region_conds, region_masks = [], []
    regions = (
        ("A / red", (255, 0, 0), "adult woman, short black bob hair, brown eyes, white laboratory coat", "#653131"),
        ("B / blue", (0, 0, 255), "adult woman, long silver hair, blue eyes, blue jacket", "#303d62"),
        ("C / green", (0, 255, 0), "laboratory microscope, white metal body, black eyepiece", "#305b42"),
    )
    for index, (label, rgb, prompt, color) in enumerate(regions):
        y = 370 + index * 340
        mask = add("ColorToMask", f"{label} / KJ color mask", [False, *rgb, 10, 16],
                   (1370, y), (365, 215), (("images", "IMAGE"),), (("MASK", "MASK"),), color)
        cond = add("CLIPTextEncode", f"{label} / region prompt", [prompt],
                   (1800, y), (480, 220), (("clip", "CLIP"),), (("CONDITIONING", "CONDITIONING"),), color)
        preview = add("MaskToImage", f"{label} / mask image", [],
                      (1370, 1450 + index * 400), (365, 65), (("mask", "MASK"),), (("IMAGE", "IMAGE"),), color)
        output = add("PreviewImage", f"{label} / mask preview", [],
                     (1800, 1450 + index * 400), (365, 320), (("images", "IMAGE"),), color=color)
        g.connect(size, 0, mask, "images")
        g.connect(clip, 0, cond, "clip")
        g.connect(mask, 0, preview, "mask")
        g.connect(preview, 0, output, "images")
        region_masks.append(mask)
        region_conds.append(cond)

    base_mask = add("SolidMask", "Global attention mask", [1.0, 1152, 1536],
                    (1370, 80), (365, 130), outputs=(("MASK", "MASK"),))
    g.connect(size, 1, base_mask, "width", "INT", True)
    g.connect(size, 2, base_mask, "height", "INT", True)
    control = add("AnimaLLLiteApply_sdscripts", "LLLite / colored spatial guidance", [
        "anima-lllite-regional-exp-v3.safetensors", .6, 0.0, .65, True
    ], (2345, 230), (390, 235), (("model", "MODEL"), ("image", "IMAGE")), (("MODEL", "MODEL"),))
    g.connect(skin, 0, control, "model")
    g.connect(size, 0, control, "image")
    ppm_inputs = [("model", "MODEL"), ("base_cond", "CONDITIONING"), ("base_mask", "MASK")]
    for index in range(1, 5):
        ppm_inputs.extend(((f"cond_{index}", "CONDITIONING"), (f"mask_{index}", "MASK")))
    ppm = add("AttentionCouplePPM", "Attention Couple / global + RGB regions", [],
              (2345, 530), (390, 285), ppm_inputs, (("MODEL", "MODEL"),))
    g.connect(control, 0, ppm, "model")
    g.connect(global_prompt, 0, ppm, "base_cond")
    g.connect(base_mask, 0, ppm, "base_mask")
    for index, (cond, mask) in enumerate(zip(region_conds, region_masks), 1):
        g.connect(cond, 0, ppm, f"cond_{index}")
        g.connect(mask, 0, ppm, f"mask_{index}")

    latent = add("EmptyLatentImage", "Latent / matches color map", [1152, 1536, 1],
                 (2345, 900), (390, 110), outputs=(("LATENT", "LATENT"),))
    g.connect(size, 1, latent, "width", "INT", True)
    g.connect(size, 2, latent, "height", "INT", True)
    sampler = add("KSampler", "Generate / PPM + LLLite", [42, "fixed", 18, 1.0, "res_multistep", "sgm_uniform", 1.0],
                  (2810, 80), (360, 310), (("model", "MODEL"), ("positive", "CONDITIONING"),
                                        ("negative", "CONDITIONING"), ("latent_image", "LATENT")), (("LATENT", "LATENT"),))
    for source, name in ((ppm, "model"), (global_prompt, "positive"), (negative, "negative"), (latent, "latent_image")):
        g.connect(source, 0, sampler, name)
    decode = add("VAEDecode", "Decode", [], (2810, 460), (360, 85),
                 (("samples", "LATENT"), ("vae", "VAE")), (("IMAGE", "IMAGE"),))
    save = add("SaveImage", "Final image", ["Anima/LLLite_PPM"], (2810, 615), (510, 550), (("images", "IMAGE"),))
    g.connect(sampler, 0, decode, "samples")
    g.connect(vae, 0, decode, "vae")
    g.connect(decode, 0, save, "images")
    g.rebuild()
    g.w.update(id=str(uuid.uuid5(uuid.NAMESPACE_URL, FILENAME)), revision=0,
               last_node_id=max(n["id"] for n in g.w["nodes"]),
               last_link_id=max(link[0] for link in g.w["links"]))
    g.w["extra"] = {"linearMode": False, "frontendVersion": "1.54.8"}
    g.w["groups"] = [
        {"id": i, "title": title, "bounding": bounds, "color": color, "font_size": 24, "flags": {}}
        for i, (title, bounds, color) in enumerate((
            ("1. Models / global LoRAs", [10, 10, 400, 780], "#546777"),
            ("2. Color map", [430, 10, 900, 1160], "#59685c"),
            ("3. Regional masks and prompts", [1345, 10, 960, 1375], "#675e71"),
            ("4. LLLite + Attention Couple", [2320, 10, 440, 1065], "#7a6450"),
            ("5. Generation", [2785, 10, 565, 1195], "#4b7275"),
            ("RGB mask previews", [1345, 1385, 850, 1220], "#606060"),
        ), 1)
    ]
    return g.w


def sample_map():
    image = Image.new("RGB", (768, 1024), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((90, 145, 335, 395), fill=(255, 0, 0))
    draw.polygon([(140, 355), (300, 355), (375, 760), (45, 760)], fill=(255, 0, 0))
    draw.ellipse((430, 145, 675, 395), fill=(0, 0, 255))
    draw.polygon([(460, 355), (620, 355), (725, 760), (390, 760)], fill=(0, 0, 255))
    draw.rectangle((300, 710, 465, 870), fill=(0, 255, 0))
    return image


def main():
    graphs, assets = ROOT / "workflows/graphs", ROOT / "workflows/assets"
    graphs.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    (graphs / FILENAME).write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8", newline="\n")
    sample_map().save(assets / ASSET)


if __name__ == "__main__":
    main()
