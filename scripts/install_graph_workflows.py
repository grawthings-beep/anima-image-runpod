#!/usr/bin/env python3
"""Install ordinary graphs and pinned node packs independently of App Mode."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

VENDORS = ("ComfyUI-Anima-LLLite", "ComfyUI-ppm", "ComfyUI-KJNodes", "ComfyUI-Impact-Pack")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(source, workflow_dir, custom_nodes_dir, input_dir):
    source, workflow_dir, custom_nodes_dir, input_dir = map(Path, (source, workflow_dir, custom_nodes_dir, input_dir))
    workflow_dir.mkdir(parents=True, exist_ok=True)
    state_path = workflow_dir / ".installed-anima-graphs.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    for graph in sorted((source / "workflows/graphs").glob("*.json")):
        dest = workflow_dir / graph.name
        if dest.exists() and digest(dest) not in (state.get(graph.name), digest(graph)):
            print(f"Preserving edited workflow: {dest.name}")
            continue
        shutil.copy2(graph, dest)
        state[graph.name] = digest(graph)
        print(f"Installed graph: {dest.name}")
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    for asset in sorted((source / "workflows/assets").glob("*.png")):
        dest = input_dir / asset.name
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset, dest)
    for name in VENDORS:
        vendor = source / "vendor" / name
        if not (vendor / "__init__.py").is_file():
            raise FileNotFoundError(f"Missing bundled node pack: {vendor}")
        shutil.copytree(vendor, custom_nodes_dir / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workflow-dir", type=Path, required=True)
    parser.add_argument("--custom-nodes-dir", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    args = parser.parse_args()
    install(args.source, args.workflow_dir, args.custom_nodes_dir, args.input_dir)


if __name__ == "__main__":
    main()
