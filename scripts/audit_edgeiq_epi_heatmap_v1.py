from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "public" / "data" / "edgeiq_epi_workspace_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_epi_heatmap_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_epi_heatmap_v1_audit.txt"

rows = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))

allowed = {"positive", "neutral", "negative", "missing"}
class_counts = {key: 0 for key in allowed}
invalid = []
for row in rows:
    for index in range(10, 0, -1):
        field = f"start_{index}_class"
        value = row.get(field, "")
        if value not in allowed:
            invalid.append(value)
        else:
            class_counts[value] += 1

checks = {
    "feed_exists": FEED.exists(),
    "only_allowed_tile_classes": not invalid,
    "positive_class_present": class_counts["positive"] > 0,
    "neutral_class_present": class_counts["neutral"] > 0,
    "negative_class_present": class_counts["negative"] > 0,
    "missing_class_present": class_counts["missing"] > 0,
}

payload = {
    "status": "EDGEIQ_EPI_HEATMAP_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_EPI_HEATMAP_V1_AUDIT_FAIL",
    "checks": checks,
    "class_counts": class_counts,
    "invalid_classes": invalid[:20],
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()], "", *[f"{key}: {value}" for key, value in sorted(class_counts.items())]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
