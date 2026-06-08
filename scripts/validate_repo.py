#!/usr/bin/env python3
import json
import pathlib
import py_compile
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
NODE_ROOT = ROOT / "custom_nodes" / "ComfyUI-AnimaSceneBuilder"


def validate_manifest():
    manifest = json.loads(
        (ROOT / "config" / "anima-image-models.json").read_text(encoding="utf-8")
    )
    paths = {entry["path"] for entry in manifest["models"]}
    required = {
        "models/diffusion_models/waiANIMA_v10Base10.safetensors",
        "models/text_encoders/qwen_3_06b_base.safetensors",
        "models/vae/qwen_image_vae.safetensors",
        "models/llm_gguf/Qwen3-4B-Q4_K_M.gguf",
        "models/loras/anima-turbo-lora-v0.2.safetensors",
        "models/loras/anima/anima_rapi.safetensors",
        "models/loras/anima/skintextureV1.safetensors",
    }
    missing = required - paths
    if missing:
        raise AssertionError(f"Manifest is missing required files: {sorted(missing)}")


def validate_workflow():
    workflow = json.loads(
        (ROOT / "workflows" / "anima_auto_scene.json").read_text(encoding="utf-8")
    )
    nodes = {node["id"]: node for node in workflow["nodes"]}

    assert nodes[11]["type"] == "AnimaLocalSceneEncode"
    assert nodes[11]["widgets_values"][0] == "Qwen3-4B-Q4_K_M.gguf"
    assert nodes[44]["widgets_values"][0] == "waiANIMA_v10Base10.safetensors"
    assert nodes[46]["widgets_values"][0] == "anima/anima_rapi.safetensors"
    assert nodes[47]["widgets_values"][0] == "anima-turbo-lora-v0.2.safetensors"
    assert nodes[48]["widgets_values"][0] == "anima/skintextureV1.safetensors"
    assert nodes[49]["type"] == "SaveImage"
    assert nodes[49]["widgets_values"][0] == "anima_auto_scene/anima"


def validate_python():
    for path in (
        NODE_ROOT / "__init__.py",
        NODE_ROOT / "scene_core.py",
        NODE_ROOT / "anima_scene_nodes.py",
        ROOT / "scripts" / "download_models.py",
        ROOT / "scripts" / "check_env.py",
    ):
        py_compile.compile(str(path), doraise=True)


def run_unit_tests():
    sys.path.insert(0, str(NODE_ROOT))
    suite = unittest.defaultTestLoader.discover(str(NODE_ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError("Unit tests failed")


def main():
    validate_manifest()
    validate_workflow()
    validate_python()
    run_unit_tests()
    print("Repository validation passed.")


if __name__ == "__main__":
    main()
