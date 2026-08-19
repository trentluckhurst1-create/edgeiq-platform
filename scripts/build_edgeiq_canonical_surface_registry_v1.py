from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "config" / "performance-intelligence" / "edgeiq_canonical_surface_registry_v1.csv"
SUMMARY = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard" / "edgeiq_canonical_surface_registry_v1_summary.json"

FIELDS = ["source_track_name", "canonical_track", "course_identity", "source_surface", "canonical_surface_group", "country", "status", "effective_from", "effective_to", "registry_version"]


ROWS = [
    ["Southside Pakenham Synthetic", "Pakenham", "PAKENHAM_SYNTHETIC", "Synthetic", "AUSTRALIAN_SYNTHETIC", "AU", "RESOLVED_AUSTRALIAN_SYNTHETIC", "", "", "EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1"],
    ["Pakenham Synthetic", "Pakenham", "PAKENHAM_SYNTHETIC", "Synthetic", "AUSTRALIAN_SYNTHETIC", "AU", "RESOLVED_AUSTRALIAN_SYNTHETIC", "", "", "EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1"],
    ["Sportsbet Pakenham Synthetic", "Pakenham", "PAKENHAM_SYNTHETIC", "Synthetic", "AUSTRALIAN_SYNTHETIC", "AU", "RESOLVED_AUSTRALIAN_SYNTHETIC", "", "", "EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1"],
    ["Ballarat Synthetic", "Ballarat", "BALLARAT_SYNTHETIC", "Synthetic", "AUSTRALIAN_SYNTHETIC", "AU", "RESOLVED_AUSTRALIAN_SYNTHETIC", "", "", "EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1"],
    ["Geelong Synthetic", "Geelong", "GEELONG_SYNTHETIC", "Synthetic", "AUSTRALIAN_SYNTHETIC", "AU", "RESOLVED_AUSTRALIAN_SYNTHETIC", "", "", "EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1"],
    ["Pakenham Turf", "Pakenham", "PAKENHAM_TURF", "Turf", "TURF", "AU", "RESOLVED_TURF", "", "", "EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1"],
    ["Pakenham", "Pakenham", "", "", "", "AU", "BLOCKED_AMBIGUOUS_COURSE", "", "", "EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1"],
]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerows(ROWS)
    payload = {"registry_rows": len(ROWS), "australian_synthetic_aliases": sum(1 for row in ROWS if row[4] == "AUSTRALIAN_SYNTHETIC"), "status": "CANONICAL_SURFACE_REGISTRY_BUILT"}
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
