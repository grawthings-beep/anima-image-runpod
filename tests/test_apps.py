import importlib.util
import json
import shutil
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


controls = module("app_controls", ROOT / "custom_nodes/ComfyUI-AnimaApp/__init__.py")
installer = module("installer", ROOT / "scripts/install_apps.py")


class AppTests(unittest.TestCase):
    def test_ratios_and_resolution_limits(self):
        self.assertEqual(controls.resolution("3:4 縦", 1024), (768, 1024))
        self.assertEqual(controls.resolution("16:9 横", 1024), (1024, 576))
        for ratio in controls.RATIOS:
            for edge in (512, 1024, 1536, 2048):
                size = controls.resolution(ratio, edge)
                self.assertEqual(max(size), edge)
                self.assertTrue(all(value % 8 == 0 for value in size))
        for invalid in (True, 0, 1023, 4096):
            with self.assertRaises(ValueError):
                controls.resolution("3:4 縦", invalid)

    def test_region_presets_cover_the_whole_image_without_duplicate_owners(self):
        for preset in controls.REGION_PRESETS:
            data = json.loads(controls.AnimaAppRegionPreset().create(preset, 4, 4)[0])
            self.assertAlmostEqual(sum(r["w"] * r["h"] for r in data["regions"]), 1)
            self.assertEqual(len({r["owner"] for r in data["regions"]}), len(data["regions"]))

    def test_lora_none_does_not_import_or_load_models(self):
        model = object()
        self.assertIs(controls.AnimaAppLoRA().load(model, "(none)", .8)[0], model)
        self.assertIs(controls.AnimaAppLoRA().load(model, "unavailable", 0)[0], model)

    def test_lora_uses_installed_files_and_passes_strength(self):
        paths = types.SimpleNamespace(get_filename_list=lambda _: ["test.safetensors"], get_full_path=lambda _, name: name if name == "test.safetensors" else None)
        calls = []
        class Loader:
            def load_lora_model_only(self, model, name, strength):
                calls.append((name, strength))
                return (model,)
        old = {key: sys.modules.get(key) for key in ("folder_paths", "nodes")}
        try:
            sys.modules["folder_paths"] = paths
            sys.modules["nodes"] = types.SimpleNamespace(LoraLoaderModelOnly=Loader)
            self.assertEqual(controls.AnimaAppLoRA.INPUT_TYPES()["required"]["lora_name"][0], ["(none)", "test.safetensors"])
            controls.AnimaAppLoRA().load(object(), "test.safetensors", .65)
            self.assertEqual(calls, [("test.safetensors", .65)])
            with self.assertRaises(ValueError):
                controls.AnimaAppLoRA().load(object(), "missing", .8)
        finally:
            for key, value in old.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value

    def test_apps_have_valid_graph_links_bindings_and_active_outputs(self):
        apps = list((ROOT / "workflows/apps").glob("*.json"))
        self.assertEqual(len(apps), 6)
        for path in apps:
            with self.subTest(path=path.name):
                w = json.loads(path.read_text(encoding="utf-8"))
                nodes = {n["id"]: n for n in w["nodes"]}
                self.assertEqual(len(nodes), len(w["nodes"]))
                links = {link[0]: link for link in w["links"]}
                self.assertEqual(len(links), len(w["links"]))
                for link in links.values():
                    id_, source, output, target, input_, type_ = link
                    self.assertEqual(nodes[target]["inputs"][input_]["link"], id_)
                    self.assertIn(id_, nodes[source]["outputs"][output]["links"])
                    self.assertEqual(nodes[source]["outputs"][output]["type"], type_)
                for node in nodes.values():
                    for input_ in node.get("inputs", []):
                        if input_.get("link"):
                            self.assertIn(input_["link"], links)
                for widget, label, config in w["extra"]["linearData"]["inputs"]:
                    graph_id, node_id, field = widget.split(":")
                    self.assertEqual(graph_id, w["id"])
                    self.assertIn(int(node_id), nodes)
                    self.assertTrue(label)
                    self.assertFalse(any(i["name"] == field and i.get("link") for i in nodes[int(node_id)].get("inputs", [])))
                for output in w["extra"]["linearData"]["outputs"]:
                    self.assertEqual(nodes[int(output)]["mode"], 0)
                    self.assertIn(nodes[int(output)]["type"], ("SaveImage", "PreviewImage"))
                self.assertTrue(w["extra"]["linearMode"])
                self.assertTrue(path.name.endswith(".app.json"))

    def test_unwanted_pose_lora_and_esrgan_app_are_absent(self):
        for p in (ROOT / "workflows/apps").glob("*.json"):
            self.assertNotIn("ESRGAN", p.name)
            self.assertNotIn("anima_pose/", p.read_text(encoding="utf-8"))

    def test_inpaint_stages_are_separate_and_have_editable_image_inputs(self):
        a = json.loads((ROOT / "workflows/apps/05_2人描き直し_2人物A.app.json").read_text(encoding="utf-8"))
        b = json.loads((ROOT / "workflows/apps/06_2人描き直し_3人物Bと高解像度.app.json").read_text(encoding="utf-8"))
        self.assertNotIn(36, {n["id"] for n in a["nodes"]})
        self.assertNotIn(17, {n["id"] for n in b["nodes"]})
        for w, node in ((a, 17), (b, 36)):
            self.assertTrue(any(entry[0] == f"{w['id']}:{node}:image" for entry in w["extra"]["linearData"]["inputs"]))

    def test_installer_preserves_builder_edits_and_updates_untouched_apps(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows, nodes = root / "user/default/workflows", root / "custom_nodes"
            bundle = root / "bundle"
            shutil.copytree(ROOT / "workflows/apps", bundle / "workflows/apps")
            shutil.copytree(ROOT / "custom_nodes", bundle / "custom_nodes")
            installer.install(bundle, workflows, nodes)
            edited = workflows / "Anima Apps/01_通常生成.app.json"
            edited.write_text("user change")
            updated = "02_プロンプト一括_latent高解像度.app.json"
            (bundle / "workflows/apps" / updated).write_text("bundled update")
            installer.install(bundle, workflows, nodes)
            self.assertEqual(edited.read_text(), "user change")
            self.assertEqual((workflows / "Anima Apps" / updated).read_text(), "bundled update")
            self.assertTrue((nodes / "ComfyUI-AnimaApp/__init__.py").exists())

    def test_user_migration_copies_saved_workflows_without_overwriting_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / "old", Path(temp) / "volume"
            (old / "default/workflows").mkdir(parents=True)
            (new / "default").mkdir(parents=True)
            (old / "default/workflows/custom.json").write_text("saved workflow")
            (old / "default/comfy.settings.json").write_text("old settings")
            (new / "default/comfy.settings.json").write_text("current settings")
            installer.migrate_user_data(old, new)
            self.assertEqual((new / "default/workflows/custom.json").read_text(), "saved workflow")
            self.assertEqual((new / "default/comfy.settings.json").read_text(), "current settings")


if __name__ == "__main__":
    unittest.main()
