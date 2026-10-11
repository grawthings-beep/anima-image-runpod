#!/usr/bin/env python3
"""Build-time CPU smoke test of real ComfyUI/node imports. No model downloads."""

import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

from install_graph_workflows import VENDORS


def check_anima_attention(nodes):
    import torch
    from comfy.model_base import Anima
    from comfy.model_patcher import ModelPatcher
    from comfy.ldm.cosmos.predict2 import Attention

    # Real Anima type and cross-attention, but tiny random weights, not a checkpoint.
    model = Anima.__new__(Anima)
    torch.nn.Module.__init__(model)
    model.diffusion_model = torch.nn.Module()
    model.diffusion_model.dtype = torch.float32
    model.diffusion_model.cross_attn = Attention(32, 32, n_heads=2, head_dim=16, operations=torch.nn)
    patcher = ModelPatcher(model, torch.device("cpu"), torch.device("cpu"))
    existing_wrapper = lambda apply_model, args: apply_model(args["input"], args["timestep"], **args["c"])
    patcher.set_model_unet_function_wrapper(existing_wrapper)
    base, region, query = torch.randn(1, 3, 32), torch.randn(1, 3, 32), torch.randn(1, 4, 32)
    base_mask = torch.ones(1, 2, 2)
    region_mask = torch.tensor([[[1., 0.], [1., 0.]]])
    patched = nodes.NODE_CLASS_MAPPINGS["AttentionCouplePPM"].execute(
        model=patcher, base_cond=[[base, {}]], base_mask=base_mask,
        cond_1=[[region, {}]], mask_1=region_mask)[0]
    assert patched.model_options["model_function_wrapper"] is existing_wrapper
    forward = patched.object_patches["diffusion_model.cross_attn.forward"]
    weights = torch.stack((base_mask, region_mask))
    weights = weights / weights.sum(dim=0, keepdim=True)
    options = {"cond_or_uncond": [0], "ppm_couple_conds": [region], "ppm_couple_num_tokens": [3],
               "ppm_couple_num_conds": 2, "ppm_couple_mask": weights, "activations_shape": (1, 32, 2, 2)}
    with torch.inference_mode():
        actual = forward(query, base, transformer_options=options)
        attention = model.diffusion_model.cross_attn
        expected = (attention(query, base) * weights[0].reshape(1, 4, 1)
                    + attention(query, region) * weights[1].reshape(1, 4, 1))
    torch.testing.assert_close(actual, expected, rtol=1e-4, atol=1e-5)
    print("Anima PPM CPU attention test passed: regional weighting and existing model wrapper retained.")


def find_comfy():
    candidates = [os.environ.get("COMFYUI_DIR", ""), "/opt/ComfyUI", "/workspace/ComfyUI",
                  "/workspace/comfyui", "/comfyui", "/ComfyUI", "/app/ComfyUI"]
    for candidate in candidates:
        if candidate and (Path(candidate) / "main.py").is_file():
            return Path(candidate)
    for root in (Path("/opt"), Path("/workspace"), Path("/app")):
        for depth in range(1, 4):
            for entry in root.glob("*/" * depth + "main.py"):
                if (entry.parent / "comfy/model_management.py").is_file():
                    return entry.parent
    raise FileNotFoundError("Set COMFYUI_DIR for the regional node smoke test")


def main():
    logging.basicConfig(level=logging.INFO)
    root = Path(__file__).resolve().parents[1]
    comfy_path = find_comfy()
    sys.path.insert(0, str(comfy_path))
    sys.argv = [sys.argv[0], "--cpu"]
    import comfy.options
    comfy.options.enable_args_parsing()
    import torch
    import folder_paths
    import nodes
    from server import PromptServer

    async def check():
        PromptServer(asyncio.get_running_loop())
        await nodes.load_custom_node(str(comfy_path / "comfy_extras/nodes_mask.py"), module_parent="comfy_extras")
        vendor_root = Path(os.environ.get("REGIONAL_VENDOR_ROOT", root / "vendor"))
        for name in VENDORS:
            if not await nodes.load_custom_node(str(vendor_root / name)):
                raise RuntimeError(f"Cannot import regional node pack: {name}")
        graph = json.loads((root / "workflows/graphs/anima_lllite_regional_ppm.json").read_text())
        for node in graph["nodes"]:
            cls = nodes.NODE_CLASS_MAPPINGS[node["type"]]
            fields = cls.INPUT_TYPES()
            known = dict(fields.get("required", {})) | dict(fields.get("optional", {}))
            connected = {i["name"] for i in node["inputs"] if i.get("link") is not None}
            for name in connected:
                if node["type"] == "AttentionCouplePPM" and name.startswith(("cond_", "mask_")):
                    continue
                if name not in known:
                    raise AssertionError(f"Unknown input {node['type']}.{name}")
            for index, output in enumerate(node["outputs"]):
                if output.get("links"):
                    assert index < len(cls.RETURN_TYPES), node["type"]
                    assert output["type"] == cls.RETURN_TYPES[index], node["type"]

        image = torch.tensor([[[[1., 0., 0.], [0., 0., 1.], [0., 1., 0.], [1., 1., 1.]]]])
        color = nodes.NODE_CLASS_MAPPINGS["ColorToMask"]()
        for index, rgb in enumerate(((255, 0, 0), (0, 0, 255), (0, 255, 0))):
            mask = color.clip(image, *rgb, threshold=10, invert=False, per_batch=1)[0]
            assert mask.shape == (1, 1, 4)
            assert mask.sum().item() == 1 and mask[0, 0, index].item() == 1
        size = nodes.NODE_CLASS_MAPPINGS["GetImageSizeAndCount"]().getsize(image)["result"]
        assert size[1:] == (4, 1, 1)
        bridge = nodes.NODE_CLASS_MAPPINGS["PreviewBridge"]()
        first = bridge.doit(image, "", "anima-regional-smoke")
        assert torch.equal(first["result"][0], image)
        # Real PreviewBridge path: an RGB edit must be returned, not just alpha.
        from impact import core
        from PIL import Image
        paint = Path(folder_paths.get_input_directory()) / "clipspace" / "regional-smoke.png"
        paint.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 1), (0, 0, 255)).save(paint)
        edited = bridge.doit(image, "clipspace/regional-smoke.png [input]", "anima-regional-smoke")
        assert torch.all(edited["result"][0][..., 2] == 1)
        assert torch.all(edited["result"][0][..., :2] == 0)
        core.preview_bridge_cache.pop("anima-regional-smoke", None)
        check_anima_attention(nodes)
        print("Regional CPU smoke test passed: real node imports, graph sockets, RGB masks and PreviewBridge RGB roundtrip. GPU generation not tested.")

    with tempfile.TemporaryDirectory(prefix="anima-regional-check-") as temp:
        for name in ("temp", "input", "output"):
            (Path(temp) / name).mkdir()
        folder_paths.set_temp_directory(str(Path(temp) / "temp"))
        folder_paths.set_input_directory(str(Path(temp) / "input"))
        folder_paths.set_output_directory(str(Path(temp) / "output"))
        asyncio.run(check())


if __name__ == "__main__":
    main()
