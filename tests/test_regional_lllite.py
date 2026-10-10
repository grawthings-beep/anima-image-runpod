import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from test_apps import ROOT, controls, installer, module


class RegionalLLLiteTests(unittest.TestCase):
    def test_layout_colors_and_masks_match_at_different_aspect_ratios(self):
        for height, width in ((128, 96), (96, 128), (64, 64)):
            for count in (2, 3, 4):
                with self.subTest(size=(width, height), count=count):
                    masks = np.zeros((4, height, width), dtype=np.float32)
                    for i in range(count):
                        masks[i, :, i * width // count:(i + 1) * width // count] = 1
                    color, result = controls.regional_map_arrays(masks, feather_percent=0)
                    np.testing.assert_array_equal(result, masks)
                    for i in range(count):
                        x = (2 * i + 1) * width // (2 * count)
                        np.testing.assert_allclose(color[0, x], np.array(controls.REGIONAL_PALETTE[i]) / 255)
                    self.assertEqual(color.shape, (height, width, 3))
                    self.assertEqual(color.dtype, np.float32)

    def test_freeform_import_white_background_alpha_and_nearest_resize(self):
        # Disjoint shapes for A, B, C, D; transparent pixels stay background.
        pixels = np.array([
            [(255, 0, 0, 255), (0, 0, 255, 255), (255, 255, 255, 255)],
            [(0, 255, 0, 255), (255, 255, 0, 255), (255, 0, 0, 0)],
        ], dtype=np.uint8)
        color, masks = controls.regional_map_arrays(
            np.zeros((4, 8, 12)), Image.fromarray(pixels), 0)
        for index, (y, x) in enumerate(((1, 1), (1, 5), (5, 1), (5, 5))):
            self.assertEqual(masks[index, y, x], 1)
            self.assertEqual(masks[:, y, x].sum(), 1)
            np.testing.assert_allclose(color[y, x], np.array(controls.REGIONAL_PALETTE[index]) / 255)
        self.assertTrue(np.all(color[:, 8:] == 1))
        self.assertEqual(masks[:, :, 8:].sum(), 0)

    def test_feather_does_not_blur_control_colors_or_activate_unused_slots(self):
        masks = np.zeros((4, 64, 96))
        masks[0, 8:56, 8:48] = 1
        masks[1, 8:56, 40:88] = 1
        hard_color, _ = controls.regional_map_arrays(masks, feather_percent=0)
        color, soft = controls.regional_map_arrays(masks, feather_percent=4)
        np.testing.assert_array_equal(color, hard_color)
        self.assertTrue(np.any((soft > 0) & (soft < 1)))
        self.assertTrue(np.all(soft.sum(axis=0) <= 1.000001))
        self.assertEqual(soft[2:].sum(), 0)
        self.assertTrue(np.all(color[0, 0] == 1))

    def test_invalid_maps_fail_instead_of_silently_ignoring_control(self):
        with self.assertRaises(ValueError):
            controls.regional_map_arrays(np.zeros((4, 32, 32)))
        with self.assertRaises(ValueError):
            controls.regional_map_arrays(np.zeros((3, 32, 32)))
        with self.assertRaises(ValueError):
            controls.regional_map_arrays(np.ones((4, 32, 32)), feather_percent=float("nan"))
        with self.assertRaisesRegex(ValueError, "Use red"):
            controls.regional_map_arrays(np.zeros((4, 32, 32)), Image.new("RGB", (32, 32), "black"))
        with self.assertRaises(ValueError):
            controls.regional_map_arrays(np.zeros((4, 32, 32)), Image.new("RGB", (32, 32), "white"))

    def test_upload_widget_validation_and_content_change_tracking(self):
        class LoadImage:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {"image": (["map.png"], {"image_upload": True})}}

            @classmethod
            def VALIDATE_INPUTS(cls, image):
                return image == "map.png"

            @classmethod
            def IS_CHANGED(cls, image):
                return "file-content-hash"

        with patch.dict("sys.modules", {"nodes": types.SimpleNamespace(LoadImage=LoadImage)}):
            node = controls.AnimaAppRegionalMap
            self.assertEqual(node.INPUT_TYPES()["required"]["image"],
                             (["(layout)", "map.png"], {"image_upload": True}))
            self.assertTrue(node.VALIDATE_INPUTS("(layout)"))
            self.assertFalse(node.VALIDATE_INPUTS("missing.png"))
            self.assertEqual(node.IS_CHANGED("(layout)"), "layout")
            self.assertEqual(node.IS_CHANGED("map.png"), "file-content-hash")

    def test_both_passes_use_control_and_same_masks_keep_hook_conditioning(self):
        workflow = json.loads(next((ROOT / "workflows/apps").glob("07_*.app.json")).read_text(encoding="utf-8"))
        nodes = {n["id"]: n for n in workflow["nodes"]}
        links = {link[0]: link for link in workflow["links"]}

        def source(node, field):
            slot = next(item for item in node["inputs"] if item["name"] == field)
            link = links[slot["link"]]
            return nodes[link[1]], link[2]

        color = next(n for n in nodes.values() if n["type"] == "AnimaAppRegionalMap")
        for index, char in enumerate((10, 30, 40, 41)):
            origin, slot = source(nodes[char], "mask")
            self.assertEqual((origin["id"], slot), (color["id"], index + 1))
            self.assertEqual(nodes[char]["type"], "AnimaRegionalCharacter")
        for sampler in (54, 61):
            control, _ = source(nodes[sampler], "model")
            self.assertEqual(control["type"], "AnimaLLLiteApply_sdscripts")
            self.assertEqual(source(control, "image")[0]["id"], color["id"])
            self.assertEqual(source(control, "model")[0]["type"], "AnimaAppLoRA")
            self.assertTrue(control["widgets_values"][-1])
        highres_control = source(nodes[61], "model")[0]
        self.assertEqual(highres_control["widgets_values"][2:4], [0.0, 1.0])
        self.assertIn(color["id"], {int(item[0].split(":")[1]) for item in workflow["extra"]["linearData"]["inputs"]})
        self.assertNotIn("AnimaLLLiteApply", {n["type"] for n in nodes.values()})

    def test_public_controlnet_is_pinned_hashed_and_not_a_character_lora(self):
        manifest = json.loads((ROOT / "config/anima-image-models.json").read_text())
        matches = [m for m in manifest["models"] if "anima-lllite-regional-exp-v3.safetensors" in m["path"]]
        self.assertEqual(len(matches), 1)
        entry = matches[0]
        self.assertTrue(entry["enabled"])
        self.assertFalse(entry["required"])
        self.assertEqual(entry["path"], "models/controlnet/anima-lllite-regional-exp-v3.safetensors")
        self.assertIn("/resolve/f1b7beeddb4175d2d20b14e10538db62bbb441a6/", entry["url"])
        self.assertEqual(entry["sha256"], "f8cdc9897a4eaa50b0f9bc18dda098fb096eeb64df001589492b9774d0cf5cc5")
        self.assertEqual(entry["min_bytes"], 51133504)
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("b7495bd8eb876e334509976896702484ed19cdbb", dockerfile)

    def test_pinned_vendor_install_keeps_git_metadata_out_of_comfyui(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "workflows/apps").mkdir(parents=True)
            (root / "custom_nodes/ComfyUI-AnimaApp").mkdir(parents=True)
            vendor = root / "vendor/ComfyUI-Anima-LLLite"
            (vendor / ".git").mkdir(parents=True)
            (vendor / "__init__.py").write_text("# test node")
            (vendor / "LICENSE").write_text("test license")
            installer.install(root, root / "installed/workflows", root / "installed/nodes")
            dest = root / "installed/nodes/ComfyUI-Anima-LLLite"
            self.assertTrue((dest / "__init__.py").is_file())
            self.assertTrue((dest / "LICENSE").is_file())
            self.assertFalse((dest / ".git").exists())

    def test_preflight_detects_missing_lllite_weights(self):
        checker = module("regional_preflight", ROOT / "scripts/check_apps.py")
        with tempfile.TemporaryDirectory() as temp:
            data = {"nodes": [{"id": 1, "type": "AnimaLLLiteApply_sdscripts",
                               "widgets_values": ["missing.safetensors"]}],
                    "extra": {"linearData": {"inputs": []}}}
            (Path(temp) / "test.app.json").write_text(json.dumps(data))
            info = {"AnimaLLLiteApply_sdscripts": {"input": {"required": {"lllite_name": [[]]}}}}
            self.assertIn("missing.safetensors", checker.check(temp, info)[0])


if __name__ == "__main__":
    unittest.main()
