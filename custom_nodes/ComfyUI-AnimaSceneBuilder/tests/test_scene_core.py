import json
import tempfile
import unittest
from pathlib import Path

from scene_core import (
    append_jsonl_log,
    build_full_prompt,
    normalize_scene_tags,
    parse_scene_response,
    validate_adult_only,
)


class SceneCoreTests(unittest.TestCase):
    def test_parses_json_and_normalizes_anima_tags(self):
        scene = parse_scene_response(
            """```json
            {
              "tags": "from_below, dynamic_pose, masterpiece, score_7",
              "description": "An adult character turns toward the camera."
            }
            ```"""
        )
        self.assertEqual(scene["tags"], "from below, dynamic pose")
        self.assertIn("turns toward the camera", scene["description"])

    def test_builds_fixed_then_scene_prompt(self):
        prompt = build_full_prompt(
            "masterpiece, best quality",
            "1girl, fixed character",
            {
                "tags": "full body, low angle",
                "description": "An adult character stands near a window.",
            },
            "tags + natural language",
        )
        self.assertTrue(prompt.startswith("masterpiece, best quality, 1girl"))
        self.assertTrue(prompt.endswith("stands near a window."))

    def test_blocks_minor_terms(self):
        with self.assertRaises(ValueError):
            validate_adult_only("underage character")

    def test_log_is_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = append_jsonl_log(directory, {"seed": 123, "full_prompt": "test"})
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(payload["seed"], 123)

    def test_deduplicates_tags(self):
        self.assertEqual(
            normalize_scene_tags("low_angle, low angle, rim_lighting"),
            "low angle, rim lighting",
        )


if __name__ == "__main__":
    unittest.main()
