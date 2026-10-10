#!/usr/bin/env python3
"""Install bundled apps; preserve edits made with App Builder on a volume."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migrate_user_data(legacy_user_dir, user_dir):
    legacy_user_dir, user_dir = map(Path, (legacy_user_dir, user_dir))
    if legacy_user_dir.resolve() == user_dir.resolve():
        return
    for old in legacy_user_dir.rglob("*"):
        if not old.is_file():
            continue
        dest = user_dir / old.relative_to(legacy_user_dir)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, dest)


def install(source, workflow_dir, custom_nodes_dir):
    source, workflow_dir, custom_nodes_dir = map(Path, (source, workflow_dir, custom_nodes_dir))
    target = workflow_dir / "Anima Apps"
    target.mkdir(parents=True, exist_ok=True)
    state_path = target / ".installed-apps.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    for app in sorted((source / "workflows" / "apps").glob("*.json")):
        dest = target / app.name
        if dest.exists() and digest(dest) not in (state.get(app.name), digest(app)):
            print(f"Preserving App Builder edits: {dest.name}")
            continue
        shutil.copy2(app, dest)
        state[app.name] = digest(app)
        print(f"Installed app: {dest.name}")
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    shutil.copytree(source / "custom_nodes" / "ComfyUI-AnimaApp", custom_nodes_dir / "ComfyUI-AnimaApp", dirs_exist_ok=True)
    lllite = source / "vendor" / "ComfyUI-Anima-LLLite"
    if lllite.is_dir():
        shutil.copytree(lllite, custom_nodes_dir / "ComfyUI-Anima-LLLite",
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workflow-dir", type=Path, required=True)
    parser.add_argument("--custom-nodes-dir", type=Path, required=True)
    parser.add_argument("--legacy-user-dir", type=Path)
    parser.add_argument("--user-dir", type=Path)
    args = parser.parse_args()
    if args.legacy_user_dir and args.user_dir:
        migrate_user_data(args.legacy_user_dir, args.user_dir)
    install(args.source, args.workflow_dir, args.custom_nodes_dir)


if __name__ == "__main__":
    main()
