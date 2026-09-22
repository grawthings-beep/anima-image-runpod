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
                "Marciana Marine Study Anima LoRA",
                "Rapunzel Anima LoRA (trigger: r4punz3l)",
                "Flora Anima LoRA",
                "Red Hood Anima LoRA (trigger: r3dh00d)",
                "Mint Anima LoRA (trigger: m1nt)",
                "Swimsuit Rapi Anima LoRA (trigger: swimsuitrapi)",
                "Swimsuit Elegg Anima LoRA (trigger: swimsuitelegg)",
                "Elegg Anima LoRA (trigger: elegg)",
                "Noir Anima LoRA (trigger: n0ir)",
                "Anis Star Anima LoRA v2 pruned (trigger: an1sstar)",
                "Anis Star 3 Anima LoRA (trigger: an1sstar3)",
                "Rapi Anima LoRA (trigger: r4pi)",
                "Prika Anima LoRA (trigger: pr1ka)",
                "Siren Anima LoRA (trigger: s1ren)",
                "Cinderella Anima LoRA (trigger: c1nde)",
                "White Cinderella Anima LoRA (trigger: whitecinderella)",
                "Mast Anima LoRA (trigger: m4st)",
                "Maxwell Anima LoRA (trigger: m4xwell)",
                "Moran Anima LoRA (trigger: m0ran)",
                "Laplace Anima LoRA (trigger: l4place)",
                "Marciana Anima LoRA (trigger: m4rciana)",
                "Snow White Anima LoRA (trigger: sn0white)",
                "Blanc Anima LoRA (trigger: bl4nc)",
                "Privaty Anima LoRA (trigger: pr1vaty)",
                "Label Anima LoRA (trigger: l4bel)",
                "Ark Ranger Black Anima LoRA (trigger: 4rkblack)",
                "Little Mermaid Anima LoRA (trigger: l1m3rma1d)",
                "Face Fucking Anima action LoRA (trigger: f4c3fk)",
                "3D Animated Realistic Style Anima LoRA (trigger: @3DYLFGxg)",
                "Pixel Art Anima LoRA v2.1 (triggers: pixel art, pix_merge)",
                "Anis Anima LoRA (trigger: 4n1s)",
                "Ain Anima LoRA (trigger: 41n)",
                "Bikini Cinderella Anima LoRA (trigger: b1k1c1nde)",
                "Laplace 2 Anima LoRA (trigger: l4pl4ce2)",
                "Phantom Anima LoRA (trigger: ph4nt0m)",
                "Guilty Anima LoRA",
                "Sin Anima LoRA",
            },
        )

    def test_other_loras_are_kept_in_the_on_demand_catalog(self):
        base = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        on_demand = json.loads(ON_DEMAND.read_text(encoding="utf-8"))["models"]
        base_paths = {model["path"] for model in base}
        on_demand_paths = {model["path"] for model in on_demand}

        self.assertEqual(len(on_demand), 12)
        self.assertTrue(all(path.startswith("models/loras/") for path in on_demand_paths))
        self.assertTrue(base_paths.isdisjoint(on_demand_paths))
        for moved_path in (
            "models/loras/anima/Mint - Anima.safetensors",
            "models/loras/anima/Swimsuit Rapi - Anima.safetensors",
            "models/loras/anima/Swimsuit Elegg - Anima.safetensors",
        ):
            self.assertIn(moved_path, base_paths)
            self.assertNotIn(moved_path, on_demand_paths)
        self.assertEqual(
            on_demand_paths,
            {
                "models/loras/anima/Eris - Anima.safetensors",
                "models/loras/anima/Kotobuki Hisako - Anima.safetensors",
                "models/loras/anima/Michinoku Komaro - Anima.safetensors",
                "models/loras/anima/There's No Way I Can Have a Lover - Anima.safetensors",
                "models/loras/anima/Watajisai - Anima v1.safetensors",
                "models/loras/anima/T-Rex Studio Style - Anima v1.safetensors",
                "models/loras/anima/Togawagatame - Anima v1.safetensors",
                "models/loras/anima_pose/01 BallsDeep - Anima v1.safetensors",
                "models/loras/anima_pose/02 SuperPosition SexPose - Anima.safetensors",
                "models/loras/anima_pose/03 Female POV - Anima.safetensors",
                "models/loras/anima/LilliePokemon_AnimaBaseV10_byKonan.safetensors",
                "models/loras/anima/Tsurumaki Mizuka and Kawasumi Ouka - Anima v1.safetensors",
            },
        )

    def test_civitai_style_loras_use_authenticated_signed_url_resolution(self):
        models = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
        by_path = {model["path"]: model for model in models}

        for path in (
            "models/loras/anima_style/3D Animated Realistic Style - Anima.safetensors",
            "models/loras/anima_style/Pixel Art - Anima v2.1.safetensors",
        ):
            model = by_path[path]
            self.assertEqual(
                model["headers"]["Authorization"],
                "Bearer ${CIVITAI_TOKEN}",
            )
            self.assertEqual(model["requires_env"], ["CIVITAI_TOKEN"])
            self.assertEqual(len(model["sha256"]), 64)

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
