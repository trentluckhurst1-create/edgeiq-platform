from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE05D_RACE_REMOVE_EXTRA_RUNNER_BOARD_{STAMP}"


START = """      <section className="eiq-approved-race__runner-board">
        <h2>RUNNER BOARD</h2>"""

END = """      <div className="eiq-approved-race__feed-state">Race intelligence feed: {loadState === "loaded" && intelligenceRace ? "Current" : loadState === "loading" ? "Loading" : "Unavailable"}</div>"""


def remove_block(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    start = text.find(START)
    end = text.find(END, start)
    if start == -1 or end == -1:
        return False
    end = text.find("\n", end)
    if end == -1:
        end = len(text)
    text = text[:start] + text[end + 1 :]
    path.write_text(text, encoding="utf-8", newline="")
    return True


def main() -> None:
    paths = [
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx",
        ROOT / "scripts" / "apply_edgeiq_approved_ui_phase05_race_overview_v1.py",
    ]
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            target = CHECKPOINT / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    changed = [str(path.relative_to(ROOT)) for path in paths if remove_block(path)]
    print(f"checkpoint={CHECKPOINT}")
    print("changed=" + ",".join(changed))
    print("EDGEIQ_APPROVED_UI_PHASE05D_RACE_REMOVE_EXTRA_RUNNER_BOARD_PASS")


if __name__ == "__main__":
    main()
