import json
import pathlib
import unittest


MANIFEST = pathlib.Path(__file__).parents[1] / "config" / "anima-image-models.json"


class ManifestTests(unittest.TestCase):
    def test_wai_anima_is_the_only_diffusion_checkpoint(self):
        models = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        diffusion_models = [
            model for model in models if model["path"].startswith("models/diffusion_models/")
        ]

        self.assertEqual(len(diffusion_models), 1)
        self.assertEqual(
            diffusion_models[0]["path"],
            "models/diffusion_models/waiANIMA_v10Base10.safetensors",
        )

    def test_retired_checkpoints_are_cleaned_from_existing_storage(self):
        models = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        wai = next(model for model in models if model["name"] == "WAI-ANIMA checkpoint v1.0")

        self.assertIn(
            "models/diffusion_models/BASBetterAnimeStyleAnimaBase_baseV10.safetensors",
            wai["legacy_paths"],
        )
        self.assertIn(
            "models/diffusion_models/nova3DCGAM_v10.safetensors",
            wai["legacy_paths"],
        )
        self.assertIn(
            "models/diffusion_models/Diving - Anima v40.safetensors",
            wai["legacy_paths"],
        )


if __name__ == "__main__":
    unittest.main()
