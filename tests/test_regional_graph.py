import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_regional_graph as builder
import install_graph_workflows as installer
import install_regional_dependencies as dependencies


class RegionalGraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = json.loads((ROOT / "workflows/graphs" / builder.FILENAME).read_text())
        self.nodes = {n["id"]: n for n in self.graph["nodes"]}
        self.links = {link[0]: link for link in self.graph["links"]}

    def source(self, node, name):
        item = next(i for i in node["inputs"] if i["name"] == name)
        link = self.links[item["link"]]
        return self.nodes[link[1]], link[2]

    def one(self, kind):
        return next(n for n in self.nodes.values() if n["type"] == kind)

    def test_reproducible_ordinary_workflow_without_hooks_or_apps(self):
        self.assertEqual(self.graph, builder.build())
        self.assertFalse(self.graph["extra"]["linearMode"])
        self.assertNotIn("linearData", self.graph["extra"])
        self.assertNotIn(".app.", builder.FILENAME)
        kinds = {n["type"] for n in self.nodes.values()}
        self.assertTrue({"PreviewBridge", "ColorToMask", "AttentionCouplePPM", "AnimaLLLiteApply_sdscripts"} <= kinds)
        self.assertFalse(any("Hook" in k or k.startswith("AnimaApp") or k == "AnimaRegionalCharacter" for k in kinds))
        self.assertNotIn("AnimaLLLiteApply", kinds)

    def test_every_link_is_bidirectional_typed_and_acyclic(self):
        self.assertEqual(len(self.nodes), len(self.graph["nodes"]))
        self.assertEqual(len(self.links), len(self.graph["links"]))
        for link in self.links.values():
            key, source, output, target, input_, type_ = link
            self.assertEqual(self.nodes[target]["inputs"][input_]["link"], key)
            self.assertIn(key, self.nodes[source]["outputs"][output]["links"])
            self.assertEqual(self.nodes[source]["outputs"][output]["type"], type_)
            self.assertEqual(self.nodes[target]["inputs"][input_]["type"], type_)
        pending = set(self.nodes)
        while pending:
            ready = {node for node in pending if not any(link[3] == node and link[1] in pending for link in self.links.values())}
            self.assertTrue(ready, "Graph cycle")
            pending -= ready

    def test_same_rgb_source_feeds_control_and_all_region_masks(self):
        sampler, ppm, control = self.one("KSampler"), self.one("AttentionCouplePPM"), self.one("AnimaLLLiteApply_sdscripts")
        self.assertEqual(self.source(sampler, "model")[0], ppm)
        self.assertEqual(self.source(ppm, "model")[0], control)
        self.assertEqual(self.source(sampler, "positive"), self.source(ppm, "base_cond"))
        source = self.source(control, "image")
        for index, rgb in enumerate(((255, 0, 0), (0, 0, 255), (0, 255, 0)), 1):
            mask = self.source(ppm, f"mask_{index}")[0]
            self.assertEqual(mask["type"], "ColorToMask")
            self.assertEqual(mask["widgets_values"], [False, *rgb, 10, 16])
            self.assertEqual(self.source(mask, "images"), source)
            self.assertEqual(self.source(ppm, f"cond_{index}")[0]["type"], "CLIPTextEncode")
        self.assertTrue(control["widgets_values"][-1])
        self.assertEqual(source[0]["type"], "GetImageSizeAndCount")
        self.assertEqual(self.source(source[0], "image")[0]["type"], "PreviewBridge")
        self.assertTrue(all(not i["link"] for i in ppm["inputs"] if i["name"] in ("cond_4", "mask_4")))

    def test_resolution_is_single_source_and_base_mask_covers_background(self):
        size = self.one("GetImageSizeAndCount")
        for node in (self.one("EmptyLatentImage"), self.one("SolidMask")):
            self.assertEqual(self.source(node, "width"), (size, 1))
            self.assertEqual(self.source(node, "height"), (size, 2))
        self.assertGreater(self.one("SolidMask")["widgets_values"][0], 0)
        self.assertEqual(self.one("ImageScale")["widgets_values"], ["nearest-exact", 1152, 1536, "disabled"])
        self.assertEqual(len([n for n in self.nodes.values() if n["type"] == "KSampler"]), 1)

    def test_node_rectangles_do_not_overlap(self):
        for index, node in enumerate(self.graph["nodes"]):
            x, y = node["pos"]
            width, height = node["size"]
            for other in self.graph["nodes"][index + 1:]:
                ox, oy = other["pos"]
                ow, oh = other["size"]
                overlap = x < ox + ow and x + width > ox and y - 30 < oy + oh and y + height > oy - 30
                self.assertFalse(overlap, (node["title"], other["title"]))

    def test_rgb_asset_has_white_background_and_three_distinct_regions(self):
        with Image.open(ROOT / "workflows/assets" / builder.ASSET) as image:
            pixels = np.array(image)
        self.assertEqual(pixels.shape, (1024, 768, 3))
        palette = {tuple(row) for row in np.unique(pixels.reshape(-1, 3), axis=0)}
        self.assertEqual(palette, {(255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 255)})
        np.testing.assert_array_equal(pixels, np.array(builder.sample_map()))

    def test_installer_keeps_edits_and_does_not_create_an_app_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output, nodes, inputs = (root / p for p in ("source", "workflows", "nodes", "input"))
            shutil.copytree(ROOT / "workflows/graphs", source / "workflows/graphs")
            shutil.copytree(ROOT / "workflows/assets", source / "workflows/assets")
            for name in installer.VENDORS:
                vendor = source / "vendor" / name
                (vendor / ".git").mkdir(parents=True)
                (vendor / "__init__.py").write_text("# node")
                (vendor / "LICENSE").write_text("license")
            installer.install(source, output, nodes, inputs)
            self.assertFalse((output / "Anima Apps").exists())
            graph = output / builder.FILENAME
            self.assertEqual(graph.read_bytes(), (source / "workflows/graphs" / builder.FILENAME).read_bytes())
            for name in installer.VENDORS:
                self.assertTrue((nodes / name / "LICENSE").exists())
                self.assertFalse((nodes / name / ".git").exists())
            (source / "workflows/graphs" / builder.FILENAME).write_text('{"updated":true}')
            installer.install(source, output, nodes, inputs)
            self.assertEqual(graph.read_text(), '{"updated":true}')
            graph.write_text("user edits")
            (inputs / builder.ASSET).write_bytes(b"user map")
            installer.install(source, output, nodes, inputs)
            self.assertEqual(graph.read_text(), "user edits")
            self.assertEqual((inputs / builder.ASSET).read_bytes(), b"user map")

    def test_helpers_protect_existing_cuda_stack_and_do_not_install_annotators(self):
        with patch.object(dependencies, "version", side_effect=lambda name: "2.8.0+cu128" if name == "torch" else "1.0"):
            pins = dependencies.constraints()
        self.assertIn("torch==2.8.0+cu128", pins)
        for name in dependencies.PROTECTED:
            self.assertIn(f"{name}==", pins)
        requirements = (ROOT / "config/regional-requirements.txt").read_text()
        active = [line for line in requirements.splitlines() if line and not line.startswith("#")]
        self.assertFalse(any("sam2" in line or "onnxruntime" in line or "mediapipe" in line for line in active))
        startup = (ROOT / "scripts/start.sh").read_text()
        self.assertLess(startup.index("scripts/install_graph_workflows.py"), startup.index('if [[ "${INSTALL_ANIMA_APPS:-1}"'))
        self.assertIn('INSTALL_ANIMA_REGIONAL_GRAPH:-1', startup)


if __name__ == "__main__":
    unittest.main()
