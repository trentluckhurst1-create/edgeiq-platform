from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
LABEL = "FINAL_PIXEL_SPEC_HOME_ACCEPTANCE_FIX"

FILES = [
    ROOT / "src" / "edgeiq-os" / "home" / "EdgeiqOsHome.tsx",
]


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = CHECKPOINT_ROOT / f"{LABEL}_{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    for source in FILES:
        rel = source.relative_to(ROOT)
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return target


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected token not found in {path}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    checkpoint_path = checkpoint()
    home = FILES[0]
    replace_once(home, "<header><div><span>Core Workspaces</span><strong>Race analysis flow</strong></div></header>", "<header><div><span>Core Workspaces</span><strong>Race intelligence workspace</strong></div></header>")
    print(f"CHECKPOINT={checkpoint_path}")
    print("UPDATED=src/edgeiq-os/home/EdgeiqOsHome.tsx")


if __name__ == "__main__":
    main()
