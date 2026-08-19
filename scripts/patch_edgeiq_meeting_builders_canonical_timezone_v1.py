from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    ROOT / "scripts" / "build_edgeiq_vic_three_day_meeting_calendar_v1.py",
    ROOT / "scripts" / "build_edgeiq_vic_three_day_meeting_universe.py",
]

CHECKPOINT_ROOT = ROOT / "checkpoints"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
checkpoint_dir = (
    CHECKPOINT_ROOT
    / f"edgeiq_rolling_three_day_universe_v1_{timestamp}"
)
checkpoint_dir.mkdir(parents=True, exist_ok=False)

manifest_files = []

for target in TARGETS:
    if not target.exists():
        raise FileNotFoundError(f"Target does not exist: {target}")

    original_bytes = target.read_bytes()
    original_sha256 = hashlib.sha256(original_bytes).hexdigest()

    checkpoint_path = checkpoint_dir / target.name
    shutil.copy2(target, checkpoint_path)

    manifest_files.append(
        {
            "original": str(target),
            "checkpoint": str(checkpoint_path),
            "sha256": original_sha256,
        }
    )

manifest = {
    "task": "EDGEIQ_ROLLING_THREE_DAY_UNIVERSE_V1",
    "timestamp": timestamp,
    "files": manifest_files,
}

manifest_path = checkpoint_dir / "manifest.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)


def patch_target(target: Path) -> None:
    text = target.read_text(encoding="utf-8-sig")

    old_import = "from zoneinfo import ZoneInfo\n"

    new_import = (
        "from zoneinfo import ZoneInfo\n"
        "\n"
        "from edgeiq_three_day_window_v1_common import (\n"
        "    TIMEZONE,\n"
        "    build_three_day_window,\n"
        ")\n"
    )

    if old_import not in text:
        raise RuntimeError(
            f"Expected ZoneInfo import not found in {target}"
        )

    text = text.replace(old_import, new_import, 1)

    old_timezone = '''try:
    LOCAL_TZ = ZoneInfo("Australia/Sydney")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")
'''

    new_timezone = '''LOCAL_TZ = TIMEZONE
'''

    if old_timezone not in text:
        raise RuntimeError(
            f"Expected Sydney timezone block not found in {target}"
        )

    text = text.replace(old_timezone, new_timezone, 1)

    old_now_local = '''def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)
'''

    new_now_local = '''def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)
'''

    if old_now_local not in text:
        raise RuntimeError(
            f"Expected now_local function not found in {target}"
        )

    # Keep the existing public helper unchanged. It now uses the
    # canonical Melbourne timezone through LOCAL_TZ.
    text = text.replace(old_now_local, new_now_local, 1)

    target.write_text(text, encoding="utf-8")

    print(f"patched={target}")


for target in TARGETS:
    patch_target(target)

print("[EDGEIQ_MEETING_BUILDERS_CANONICAL_TIMEZONE_V1] PASS")
print(f"checkpoint_dir={checkpoint_dir}")
print(f"manifest={manifest_path}")
