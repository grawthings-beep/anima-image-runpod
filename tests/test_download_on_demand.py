import importlib.util
import pathlib
import sys
import unittest


SCRIPTS = pathlib.Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "download_on_demand.py"
SPEC = importlib.util.spec_from_file_location("download_on_demand", SCRIPT)
download_on_demand = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(download_on_demand)


class DownloadOnDemandTests(unittest.TestCase):
    def setUp(self):
        self.models = [
            {
                "name": "Rapi Anima LoRA (trigger: r4pi)",
                "path": "models/loras/anima/Rapi - Anima.safetensors",
            },
            {
                "name": "Swimsuit Rapi Anima LoRA (trigger: swimsuitrapi)",
                "path": "models/loras/anima/Swimsuit Rapi - Anima.safetensors",
            },
        ]

    def test_exact_saved_filename_selects_one_model(self):
        model = download_on_demand.find_model(self.models, "Rapi - Anima.safetensors")
        self.assertEqual(model["name"], "Rapi Anima LoRA (trigger: r4pi)")

    def test_ambiguous_partial_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Multiple on-demand LoRAs"):
            download_on_demand.find_model(self.models, "Rapi")


if __name__ == "__main__":
    unittest.main()
