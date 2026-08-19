from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGET = ROOT / "scripts" / "build_edgeiq_three_day_product_catalog_v1.py"
CHECKPOINT_ROOT = ROOT / "checkpoints"

if not TARGET.exists():
    raise FileNotFoundError(f"Target does not exist: {TARGET}")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
checkpoint_dir = (
    CHECKPOINT_ROOT
    / f"edgeiq_rolling_three_day_universe_v1_{timestamp}"
)
checkpoint_dir.mkdir(parents=True, exist_ok=False)

checkpoint_path = checkpoint_dir / TARGET.name
shutil.copy2(TARGET, checkpoint_path)

original_bytes = TARGET.read_bytes()
original_sha256 = hashlib.sha256(original_bytes).hexdigest()

manifest = {
    "task": "EDGEIQ_ROLLING_THREE_DAY_UNIVERSE_V1",
    "timestamp": timestamp,
    "files": [
        {
            "original": str(TARGET),
            "checkpoint": str(checkpoint_path),
            "sha256": original_sha256,
        }
    ],
}

(checkpoint_dir / "manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)

text = original_bytes.decode("utf-8-sig")

old_import = "from datetime import date, datetime, timedelta\n"

new_import = (
    "from datetime import date, datetime, timedelta\n"
    "\n"
    "from edgeiq_three_day_window_v1_common import "
    "build_three_day_window\n"
)

if old_import not in text:
    raise RuntimeError(
        "Expected datetime import was not found. No patch applied."
    )

text = text.replace(old_import, new_import, 1)

old_dates = '''TODAY = date.today()
TARGET_DATES = [
    TODAY,
    TODAY + timedelta(days=1),
    TODAY + timedelta(days=2),
]
TARGET_DATE_SET = {item.isoformat() for item in TARGET_DATES}
'''

new_dates = '''THREE_DAY_WINDOW = build_three_day_window()
TODAY = date.fromisoformat(THREE_DAY_WINDOW.today)
TARGET_DATES = [
    date.fromisoformat(THREE_DAY_WINDOW.today),
    date.fromisoformat(THREE_DAY_WINDOW.tomorrow),
    date.fromisoformat(THREE_DAY_WINDOW.dayPlus2),
]
TARGET_DATE_SET = {item.isoformat() for item in TARGET_DATES}
'''

if old_dates not in text:
    raise RuntimeError(
        "Expected product-catalog date block was not found. "
        "No patch applied."
    )

text = text.replace(old_dates, new_dates, 1)

TARGET.write_text(text, encoding="utf-8")

print("[EDGEIQ_PRODUCT_CATALOG_WINDOW_MIGRATION_V1] PASS")
print(f"target={TARGET}")
print(f"checkpoint={checkpoint_path}")
print(f"manifest={checkpoint_dir / 'manifest.json'}")
print(f"original_sha256={original_sha256}")
