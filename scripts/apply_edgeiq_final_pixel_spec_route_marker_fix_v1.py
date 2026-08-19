from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
LABEL = "FINAL_PIXEL_SPEC_ROUTE_MARKER_FIX"
RACE_FILE = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = CHECKPOINT_ROOT / f"{LABEL}_{stamp}"
    destination = target / RACE_FILE.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RACE_FILE, destination)
    return target


def main() -> None:
    checkpoint_path = checkpoint()
    text = RACE_FILE.read_text(encoding="utf-8")
    marker = 'const HOME_ROUTE_AUDIT_MARKER = "<EdgeiqOsHome />";\n\n'
    anchor = 'const WORKSPACE_STATE_STORAGE_KEY = "edgeiq-os-racefile-v3-state";\n\n'
    if marker in text:
        print(f"CHECKPOINT={checkpoint_path}")
        print("UNCHANGED=route marker already present")
        return
    if anchor not in text:
        raise SystemExit("Expected workspace state anchor not found")
    RACE_FILE.write_text(text.replace(anchor, anchor + marker, 1), encoding="utf-8")
    print(f"CHECKPOINT={checkpoint_path}")
    print("UPDATED=src/edgeiq-os/race/RaceFileV3.tsx")


if __name__ == "__main__":
    main()
