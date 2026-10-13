import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from test_apps import ROOT, module

sys.path.insert(0, str(ROOT / "scripts"))
import build_app_workflows as builder

controls = module("negpip_controls", ROOT / "custom_nodes/ComfyUI-AnimaNegPip/__init__.py")


class NegPipTests(unittest.TestCase):
    def test_off_is_exact_passthrough_without_comfy_or_ppm(self):
        model, clip = object(), object()
        with patch.dict(sys.modules, {"nodes": None, "comfy": None}):
            actual = controls.AnimaNegPipToggle().apply(model, clip, False)
        self.assertIs(actual[0], model)
        self.assertIs(actual[1], clip)
        self.assertFalse(controls.AnimaNegPipToggle.INPUT_TYPES()["required"]["enabled"][1]["default"])

    def test_on_uses_both_ppm_outputs_and_checks_support(self):
        class Anima:
            pass
        model = types.SimpleNamespace(model=Anima())
        clip = object()
        patched_model = types.SimpleNamespace(model_options={"ppm_negpip": True})
        patched_clip = types.SimpleNamespace(patcher=types.SimpleNamespace(model_options={"ppm_negpip": True}))
        calls = []

        class PPM:
            @classmethod
            def execute(cls, **kwargs):
                calls.append(kwargs)
                return patched_model, patched_clip

        mappings = {"CLIPNegPip": PPM}
        modules = {"nodes": types.SimpleNamespace(NODE_CLASS_MAPPINGS=mappings),
                   "comfy.model_base": types.SimpleNamespace(Anima=Anima)}
        with patch.dict(sys.modules, modules), patch.object(controls, "patch_legacy_anima_attention") as compat:
            actual = controls.AnimaNegPipToggle().apply(model, clip, True)
            self.assertIs(actual[0], patched_model)
            self.assertIs(actual[1], patched_clip)
            self.assertEqual(calls, [{"model": model, "clip": clip}])
            compat.assert_called_once_with(patched_model)
            patched_model.model_options.clear()
            with self.assertRaisesRegex(RuntimeError, "not applied"):
                controls.AnimaNegPipToggle().apply(model, clip, True)
            mappings.clear()
            with self.assertRaisesRegex(RuntimeError, "CLIPNegPip is unavailable"):
                controls.AnimaNegPipToggle().apply(model, clip, True)
            with self.assertRaisesRegex(ValueError, "Anima/WAI-ANIMA"):
                controls.AnimaNegPipToggle().apply(types.SimpleNamespace(model=object()), clip, True)

    def test_all_model_passes_and_encoders_use_one_toggle(self):
        paths = list((ROOT / "workflows/apps").glob("*.json")) + list((ROOT / "workflows/graphs").glob("*.json"))
        self.assertEqual(len(paths), 10)
        for path in paths:
            with self.subTest(workflow=path.name):
                graph = json.loads(path.read_text(encoding="utf-8"))
                nodes = {n["id"]: n for n in graph["nodes"]}
                toggle, = [n for n in nodes.values() if n["type"] == "AnimaNegPipToggle"]
                self.assertEqual(toggle["widgets_values"], [False])
                for node in nodes.values():
                    if node["type"] in ("UNETLoader", "CLIPLoader"):
                        outgoing = [link for link in graph["links"] if link[1] == node["id"]]
                        self.assertEqual(len(outgoing), 1)
                        self.assertEqual(outgoing[0][3], toggle["id"])
                    if node["type"] in ("KSampler", "AttentionCouplePPM"):
                        current, visited = node, set()
                        while current["type"] != "UNETLoader":
                            self.assertNotIn(current["id"], visited)
                            visited.add(current["id"])
                            input_ = next(i for i in current["inputs"] if i["name"] == "model")
                            link = next(link for link in graph["links"] if link[0] == input_["link"])
                            current = nodes[link[1]]
                        self.assertIn(toggle["id"], visited)
                    for input_ in node.get("inputs", []):
                        if input_["type"] == "CLIP" and node != toggle and input_.get("link"):
                            link = next(link for link in graph["links"] if link[0] == input_["link"])
                            self.assertEqual(link[1:3], [toggle["id"], 1])
                if graph["extra"]["linearMode"]:
                    binding = f"{graph['id']}:{toggle['id']}:enabled"
                    self.assertIn(binding, [i[0] for i in graph["extra"]["linearData"]["inputs"]])

    def test_insertion_is_idempotent_and_preserves_existing_settings(self):
        graph = builder.Graph(builder.load("anima_two_character_hooks_hiresfix.json"))
        before = copy.deepcopy(graph.w["nodes"])
        toggle = builder.add_negpip(graph)
        snapshot = copy.deepcopy(graph.w)
        self.assertEqual(builder.add_negpip(graph), toggle)
        self.assertEqual(graph.w, snapshot)
        for node in before:
            self.assertEqual(graph.node(node["id"])["widgets_values"], node["widgets_values"])

    def test_generators_are_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            apps = root / "workflows/apps"
            with patch.object(builder, "DEST", apps), patch.object(builder, "ROOT", root):
                builder.build()
            for path in (root / "workflows").rglob("*.json"):
                self.assertEqual(path.read_bytes(), (ROOT / path.relative_to(root)).read_bytes(), path.name)

    def test_ordinary_variants_match_apps_without_app_mode_or_overlaps(self):
        for name, pattern in (("basic", "01_*"), ("latent_2pass", "02_*")):
            graph = json.loads((ROOT / f"workflows/graphs/anima_negpip_{name}.json").read_text(encoding="utf-8"))
            app = json.loads(next((ROOT / "workflows/apps").glob(pattern)).read_text(encoding="utf-8"))
            self.assertFalse(graph["extra"]["linearMode"])
            self.assertNotIn("linearData", graph["extra"])
            self.assertEqual(graph["links"], app["links"])
            self.assertEqual([n["widgets_values"] for n in graph["nodes"]], [n["widgets_values"] for n in app["nodes"]])
            for index, node in enumerate(graph["nodes"]):
                x, y = node["pos"]
                width, height = node["size"]
                for other in graph["nodes"][index + 1:]:
                    ox, oy = other["pos"]
                    ow, oh = other["size"]
                    self.assertFalse(x < ox + ow and x + width > ox and y - 30 < oy + oh and y + height > oy - 30)


if __name__ == "__main__":
    unittest.main()
