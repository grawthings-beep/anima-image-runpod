#!/usr/bin/env python3
"""Install helper-node imports at build time, retaining the image's ML stack."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import subprocess
import sys
import tempfile

PROTECTED = ("torch", "torchvision", "torchaudio", "numpy", "transformers", "huggingface-hub", "tokenizers")


def constraints():
    pins = []
    for name in PROTECTED:
        try:
            pins.append(f"{name}=={version(name)}")
        except PackageNotFoundError:
            pass
    return "\n".join(pins) + "\n"


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as temp:
        pinfile = Path(temp) / "existing-ml-stack.txt"
        pinfile.write_text(constraints(), encoding="utf-8")
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir",
                        "-c", str(pinfile), "-r", str(root / "config/regional-requirements.txt")], check=True)


if __name__ == "__main__":
    main()
