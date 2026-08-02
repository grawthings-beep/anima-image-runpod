import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock


SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "download_models.py"
SPEC = importlib.util.spec_from_file_location("download_models", SCRIPT)
download_models = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(download_models)


class DownloadModelsTests(unittest.TestCase):
    def test_legacy_curl_entry_prefers_aria2(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            output = root / "models" / "model.safetensors"
            entry = {
                "name": "test model",
                "url": "https://example.test/model",
                "path": "models/model.safetensors",
                "method": "curl",
                "min_bytes": 1,
            }

            def finish_download(_url, target, _connections, _splits):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"complete")

            with mock.patch.object(download_models.shutil, "which", return_value="aria2c"), mock.patch.object(
                download_models, "resolve_download_url", return_value=entry["url"]
            ), mock.patch.object(download_models, "run_aria2", side_effect=finish_download) as aria2, mock.patch.object(
                download_models, "run_curl"
            ) as curl:
                download_models.download(entry, root, True, 16, 16)

            aria2.assert_called_once()
            curl.assert_not_called()
            self.assertEqual(output.read_bytes(), b"complete")

    def test_aria2_command_uses_parallel_connections(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "model.safetensors"
            with mock.patch.object(download_models.subprocess, "run") as run:
                download_models.run_aria2("https://example.test/model", output, 16, 16)

            command = run.call_args.args[0]
        self.assertEqual(command[command.index("-x") + 1], "16")
        self.assertEqual(command[command.index("-s") + 1], "16")
        self.assertIn("--file-allocation=none", command)


if __name__ == "__main__":
    unittest.main()
