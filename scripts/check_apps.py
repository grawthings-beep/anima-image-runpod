#!/usr/bin/env python3
"""Read-only node/option preflight; never submits a prompt or starts a GPU job."""

import argparse
import json
from pathlib import Path
import sys
import urllib.request


MODEL_WIDGETS = {
    "UNETLoader": [(0, "unet_name")],
    "CLIPLoader": [(0, "clip_name")],
    "VAELoader": [(0, "vae_name")],
    "UpscaleModelLoader": [(0, "model_name")],
    "AnimaAppLoRA": [(0, "lora_name")],
    "AnimaRegionalCharacter": [(0, "lora_name")],
    "KSampler": [(4, "sampler_name"), (5, "scheduler")],
}


def check(workflow_dir, info):
    problems = []
    apps = sorted(Path(workflow_dir).glob("*.app.json"))
    if not apps:
        return [f"No apps found in {workflow_dir}"]
    for app in apps:
        data = json.loads(app.read_text(encoding="utf-8"))
        for node in data["nodes"]:
            kind = node["type"]
            if kind not in info:
                problems.append(f"{app.name}: missing node {kind}")
                continue
            fields = dict(info[kind].get("input", {}).get("required", {}))
            fields.update(info[kind].get("input", {}).get("optional", {}))
            values = node.get("widgets_values", [])
            for index, field in MODEL_WIDGETS.get(kind, []):
                if index >= len(values) or values[index] == "(none)":
                    continue
                options = fields.get(field, [None])[0]
                if isinstance(options, list) and values[index] not in options:
                    problems.append(f"{app.name}: choose an installed/supported {field}: {values[index]}")
            for widget, label, *_ in data["extra"]["linearData"]["inputs"]:
                _, node_id, name = widget.split(":")
                if int(node_id) == node["id"] and name not in fields:
                    problems.append(f"{app.name}: unavailable App input {label} ({kind}.{name})")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8188")
    parser.add_argument("--workflow-dir", type=Path, default=Path(__file__).resolve().parents[1] / "workflows/apps")
    args = parser.parse_args()
    with urllib.request.urlopen(args.url.rstrip("/") + "/object_info", timeout=30) as response:
        info = json.load(response)
    problems = check(args.workflow_dir, info)
    for problem in problems:
        print(problem)
    print(f"Checked {len(list(args.workflow_dir.glob('*.app.json')))} apps; {len(problems)} problem(s). No generation submitted.")
    return bool(problems)


if __name__ == "__main__":
    sys.exit(main())
