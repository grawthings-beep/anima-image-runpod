import json
import pathlib
import unittest


MANIFEST = pathlib.Path(__file__).parents[1] / "config" / "anima-image-models.json"
ON_DEMAND = pathlib.Path(__file__).parents[1] / "config" / "anima-image-on-demand-loras.json"


class ManifestTests(unittest.TestCase):
    def test_expected_diffusion_checkpoints_are_downloaded(self):
        models = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        diffusion_models = [
            model for model in models if model["path"].startswith("models/diffusion_models/")
        ]

        self.assertEqual(
            {model["path"] for model in diffusion_models},
            {
                "models/diffusion_models/waiANIMA_v10Base10.safetensors",
                "models/diffusion_models/nova3DCGAM_v10.safetensors",
            },
        )

    def test_only_selected_loras_download_automatically(self):
        models = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        auto_loras = {model["name"] for model in models if model["path"].startswith("models/loras/")}

        self.assertEqual(
            auto_loras,
            {
                "Qwen Image Union Control LoRA (Canny / depth / pose)",
                "Anima Turbo LoRA v0.2 (speed / step-reduction)",
                "Skin Texture Detail LoRA",
                "Old Maxwell Anima LoRA (trigger: oldmaxwell)",
                "Marciana Anima LoRA (3) (trigger: m4rciana)",
                "Rapunzel Anima LoRA (trigger: r4punz3l)",
                "Flora Anima LoRA",
                "Red Hood Anima LoRA (trigger: r3dh00d)",
                "Face Fucking Anima action LoRA (trigger: f4c3fk)",
                "Pixel Art Anima LoRA v2.1 (triggers: pixel art, pix_merge)",
            },
        )

    def test_other_loras_are_kept_in_the_on_demand_catalog(self):
        base = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        on_demand = json.loads(ON_DEMAND.read_text(encoding="utf-8"))["models"]
        base_paths = {model["path"] for model in base}
        on_demand_paths = {model["path"] for model in on_demand}

        self.assertEqual(len(on_demand), 40)
        self.assertTrue(all(path.startswith("models/loras/") for path in on_demand_paths))
        self.assertTrue(base_paths.isdisjoint(on_demand_paths))
        self.assertIn(
            "models/loras/anima/Tsurumaki Mizuka and Kawasumi Ouka - Anima v1.safetensors",
            on_demand_paths,
        )
        self.assertIn(
            "models/loras/anima/Phantom - Anima.safetensors",
            on_demand_paths,
        )

    def test_retired_checkpoints_are_cleaned_from_existing_storage(self):
        models = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        wai = next(model for model in models if model["name"] == "WAI-ANIMA checkpoint v1.0")

        self.assertIn(
            "models/diffusion_models/BASBetterAnimeStyleAnimaBase_baseV10.safetensors",
            wai["legacy_paths"],
        )
        self.assertIn(
            "models/diffusion_models/Miaomiao 3D Harem - Anima LH 3D 1.0.safetensors",
            wai["legacy_paths"],
        )
        self.assertIn(
            "models/diffusion_models/Miaomiao Harem Ani 2.5D - v1.0.safetensors",
            wai["legacy_paths"],
        )
        self.assertNotIn(
            "models/diffusion_models/nova3DCGAM_v10.safetensors",
            wai["legacy_paths"],
        )
        self.assertIn(
            "models/diffusion_models/Diving - Anima v40.safetensors",
            wai["legacy_paths"],
        )


if __name__ == "__main__":
    unittest.main()
