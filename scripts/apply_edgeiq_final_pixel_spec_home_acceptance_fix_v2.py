from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
LABEL = "FINAL_PIXEL_SPEC_HOME_ACCEPTANCE_FIX_V2"

HOME = ROOT / "src" / "edgeiq-os" / "home" / "EdgeiqOsHome.tsx"


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = CHECKPOINT_ROOT / f"{LABEL}_{stamp}"
    destination = target / HOME.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HOME, destination)
    return target


def main() -> None:
    checkpoint_path = checkpoint()
    text = HOME.read_text(encoding="utf-8")
    old = '<header><div><span>Current Availability</span><strong>Governed feed status</strong></div></header>'
    new = '<header><div><span>Current Availability</span><strong>Data Discipline</strong><small>Browser-safe product feeds</small></div></header>'
    if old not in text:
        raise SystemExit(f"Expected token not found: {old}")
    HOME.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"CHECKPOINT={checkpoint_path}")
    print("UPDATED=src/edgeiq-os/home/EdgeiqOsHome.tsx")


if __name__ == "__main__":
    main()
