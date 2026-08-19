
from pathlib import Path
import json
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "edgeiq-os" / "race" / "services" / "threeDayCatalog.ts"
CHECKPOINT = ROOT / "src" / "edgeiq-os" / "race" / "services" / "threeDayCatalog_CHECKPOINT_PRE_OPERATIONS_CATALOG_SIZE_GUARD_20260726.ts"
REPORT = ROOT / "docs" / "operations-readiness" / "runtime-feeds" / "edgeiq_catalog_size_guard_patch_v1.json"
text = TARGET.read_text(encoding="utf-8")
CHECKPOINT.write_text(text, encoding="utf-8")
old = "const MAX_CATALOG_BYTES = 3_000_000;"
new = "const MAX_CATALOG_BYTES = 15_000_000;"
if old not in text and new not in text:
    raise SystemExit("catalog size guard constant not found")
changed = False
if old in text:
    TARGET.write_text(text.replace(old, new), encoding="utf-8")
    changed = True
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps({
    "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "target": str(TARGET),
    "checkpoint": str(CHECKPOINT),
    "old_max_bytes": 3000000,
    "new_max_bytes": 15000000,
    "changed": changed,
    "reason": "Current governed three-day product catalog is 10.3MB and was rejected by runtime feed guard. Bound raised only for this governed catalog.",
    "model_pricing_change": "NO"
}, indent=2), encoding="utf-8")
print(REPORT)
