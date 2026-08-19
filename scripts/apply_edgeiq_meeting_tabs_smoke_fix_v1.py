from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT_ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
CHECKPOINT_ROOT = PROJECT_ROOT / "checkpoints"


def checkpoint(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = CHECKPOINT_ROOT / f"edgeiq_meeting_tabs_smoke_fix_v1_{stamp}"
    target = dest / path.relative_to(PROJECT_ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return dest


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return source.replace(old, new, 1)


def main() -> int:
    source = RESULTS.read_text(encoding="utf-8")
    original = source

    source = replace_once(source, 'return "—";', 'return "-";', "plain dash for missing table value")
    source = replace_once(source, 'aria-label="Results workspace"', 'aria-label="Results"', "user-facing results aria label")

    if 'return "—";' in source:
        raise RuntimeError("Results valueOrDash still returns em dash")
    if 'aria-label="Results workspace"' in source:
        raise RuntimeError("Results aria label still contains workspace")
    if source == original:
        raise RuntimeError("No changes applied")

    checkpoint_path = checkpoint(RESULTS)
    RESULTS.write_text(source, encoding="utf-8")

    print("EDGEIQ_MEETING_TABS_SMOKE_FIX_V1_APPLIED")
    print(f"checkpoint={checkpoint_path}")
    print(f"changed={RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
