from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
LABEL = "FINAL_PIXEL_SPEC_LINE_ENDING_NORMALISE"

FILES = [
    ROOT / "src" / "edgeiq-os" / "home" / "EdgeiqOsHome.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx",
]


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = CHECKPOINT_ROOT / f"{LABEL}_{stamp}"
    for source in FILES:
        destination = target / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return target


def main() -> None:
    checkpoint_path = checkpoint()
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        normalised = "\n".join(text.splitlines())
        if text.endswith(("\n", "\r\n")):
            normalised += "\n"
        path.write_text(normalised, encoding="utf-8", newline="\r\n")
    print(f"CHECKPOINT={checkpoint_path}")
    print("UPDATED=src/edgeiq-os/home/EdgeiqOsHome.tsx")
    print("UPDATED=src/edgeiq-os/race/RaceFileV3.tsx")


if __name__ == "__main__":
    main()
