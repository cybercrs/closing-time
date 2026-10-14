"""Build the final native app only under js/; no runtime dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = ("index.html", "app.js", "engine.js", "content.js", "style.css", "original.css", "shared.js")


def build(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        shutil.copyfile(HERE / name, output / name)
    manifest = {
        "app": "Closing Time",
        "description": "Student-facing native HTML/CSS/JavaScript accounting activity",
        "path": "/js/",
        "files": {name: {"bytes": (output / name).stat().st_size,
                         "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()}
                  for name in ASSETS},
    }
    manifest["asset_bytes"] = sum(item["bytes"] for item in manifest["files"].values())
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "dist")
    parser.add_argument("--site-output", type=Path)
    args = parser.parse_args()
    build(args.site_output / "js" if args.site_output else args.output)
