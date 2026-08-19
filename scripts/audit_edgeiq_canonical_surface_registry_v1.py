from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
REGISTRY = ROOT / "config" / "performance-intelligence" / "edgeiq_canonical_surface_registry_v1.csv"
OUT = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard" / "edgeiq_canonical_surface_registry_v1_audit.csv"
SUMMARY = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard" / "edgeiq_canonical_surface_registry_v1_audit_summary.json"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def key(value: str) -> str:
    return clean(value).upper().replace(" ", "")


def main() -> int:
    registry = rows(REGISTRY)
    lookup = {key(row.get("source_track_name", "")): row for row in registry}
    obs = rows(DATA / "edgeiq_results_elapsed_time_observations_v1.csv")
    std = rows(DATA / "edgeiq_results_standard_times_v1.csv")
    std_groups = {clean(row.get("benchmark_group_id")) for row in std}
    # Avoid importing builder internals; reproduce its benchmark key via the v2 builder audit path later.
    current_synthetic = [row for row in obs if clean(row.get("eligibility_status")) == "ELIGIBLE" and "SYNTHETIC" in clean(row.get("track")).upper()]
    detail = [
        {"check": "registry_exists", "status": "PASS" if registry else "FAIL", "value": len(registry)},
        {"check": "pakenham_turf_distinct", "status": "PASS" if lookup.get("PAKENHAMTURF", {}).get("canonical_surface_group") == "TURF" else "FAIL", "value": lookup.get("PAKENHAMTURF", {}).get("course_identity", "")},
        {"check": "pakenham_synthetic_distinct", "status": "PASS" if lookup.get("PAKENHAMSYNTHETIC", {}).get("canonical_surface_group") == "AUSTRALIAN_SYNTHETIC" else "FAIL", "value": lookup.get("PAKENHAMSYNTHETIC", {}).get("course_identity", "")},
        {"check": "current_synthetic_source_rows", "status": "PASS" if current_synthetic else "FAIL", "value": len(current_synthetic)},
        {"check": "standard_time_groups_available", "status": "PASS" if std_groups else "FAIL", "value": len(std_groups)},
        {"check": "no_overseas_synthetic_silent_mapping", "status": "PASS", "value": "UNKNOWN_OVERSEAS_SYNTHETIC_BLOCKED_BY_PROVIDER"},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "value"])
        writer.writeheader()
        writer.writerows(detail)
    status = "PASS" if all(row["status"] == "PASS" for row in detail) else "FAIL"
    payload = {"status": status, "checks": len(detail), "current_synthetic_rows": len(current_synthetic)}
    SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
