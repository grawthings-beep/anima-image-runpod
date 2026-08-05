#!/usr/bin/env python3
import argparse
import json
import os
import pathlib

import download_models


DEFAULT_CATALOG = (
    pathlib.Path(__file__).parents[1] / "config" / "anima-image-on-demand-loras.json"
)


def aliases(model):
    path = pathlib.Path(model["path"])
    return {
        model["name"].casefold(),
        model["path"].casefold(),
        path.name.casefold(),
        path.stem.casefold(),
    }


def find_model(models, query):
    needle = query.strip().casefold()
    exact = [model for model in models if needle in aliases(model)]
    if len(exact) == 1:
        return exact[0]

    partial = [model for model in models if any(needle in value for value in aliases(model))]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise ValueError(f"No on-demand LoRA matched: {query}")

    choices = "\n".join(f"  - {model['name']}" for model in partial)
    raise ValueError(f"Multiple on-demand LoRAs matched {query!r}:\n{choices}")


def main():
    parser = argparse.ArgumentParser(description="Download selected Anima LoRAs")
    parser.add_argument("models", nargs="*", help="LoRA name or saved filename")
    parser.add_argument("--list", action="store_true", help="list available LoRAs")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--root", default=os.environ.get("MODEL_ROOT", "/workspace/comfyui"))
    parser.add_argument("--connections", type=int, default=int(os.environ.get("ARIA2_CONNECTIONS", "16")))
    parser.add_argument("--splits", type=int, default=int(os.environ.get("ARIA2_SPLITS", "16")))
    args = parser.parse_args()

    catalog = json.loads(pathlib.Path(args.catalog).read_text(encoding="utf-8"))["models"]
    if args.list:
        for model in catalog:
            print(f"{pathlib.Path(model['path']).name}\t{model['name']}")
        if not args.models:
            return
    if not args.models:
        parser.error("provide a LoRA name or use --list")

    selected = []
    seen_paths = set()
    for query in args.models:
        model = find_model(catalog, query)
        if model["path"] not in seen_paths:
            selected.append(model)
            seen_paths.add(model["path"])

    root = pathlib.Path(args.root)
    for model in selected:
        requested = dict(model)
        requested["required"] = True
        download_models.download(requested, root, True, args.connections, args.splits)
        print(f"READY: {root / requested['path']}")


if __name__ == "__main__":
    main()
