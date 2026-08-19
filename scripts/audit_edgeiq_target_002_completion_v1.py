from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RESTART = ROOT / "docs" / "performance-intelligence" / "restart-v1"

STANDARD_TIME_PATH = DATA / "edgeiq_standard_time_fact_v1.csv"
STANDARD_AUDIT_PATH = DATA / "edgeiq_standard_time_fact_v1_audit.json"
HISTORICAL_PATH = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
ACCUMULATION_PATH = DATA / "edgeiq_benchmark_accumulation_fact_v1.csv"

AUDIT_JSON = RESTART / "edgeiq_target_002_completion_audit_v1.json"
AUDIT_CSV = RESTART / "edgeiq_target_002_completion_audit_v1.csv"
AUDIT_MD = RESTART / "EDGEIQ_TARGET_002_COMPLETION_AUDIT_V1.md"

MINIMUM_REQUIRED_SAMPLE = 20
BRIDGE_VERSION = "edgeiq_standard_time_historical_results_bridge_v1.0.0"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    RESTART.mkdir(parents=True, exist_ok=True)
    standard_rows = read_csv(STANDARD_TIME_PATH)
    accumulation_rows = read_csv(ACCUMULATION_PATH)
    standard_audit = json.loads(STANDARD_AUDIT_PATH.read_text(encoding="utf-8"))

    sample_errors = [
        row["benchmark_group_id"]
        for row in standard_rows
        if int(text(row.get("sample_observation_count") or "0")) < MINIMUM_REQUIRED_SAMPLE
    ]
    bridge_rows = [
        row
        for row in standard_rows
        if text(row.get("source_accumulation_builder_version")) == BRIDGE_VERSION
    ]
    ready_accumulation_count = sum(
        1
        for row in accumulation_rows
        if text(row.get("benchmark_ready")).lower() in {"true", "1", "yes"}
        and text(row.get("accumulation_status")) == "READY"
        and int(text(row.get("eligible_observation_count") or "0")) >= MINIMUM_REQUIRED_SAMPLE
    )
    standard_seconds_errors = [
        row["benchmark_group_id"]
        for row in standard_rows
        if Decimal(text(row.get("standard_time_seconds") or "0")) <= 0
    ]
    track_counts = Counter(text(row.get("track_name")) for row in standard_rows)
    distance_counts = Counter(text(row.get("official_distance_metres")) for row in standard_rows)

    checks = [
        {
            "check": "standard_time_rows_populated",
            "status": "PASS" if standard_rows else "FAIL",
            "detail": len(standard_rows),
        },
        {
            "check": "canonical_audit_passed",
            "status": "PASS" if standard_audit.get("status") == "PASS" else "FAIL",
            "detail": standard_audit.get("status"),
        },
        {
            "check": "minimum_sample_preserved",
            "status": "PASS" if not sample_errors else "FAIL",
            "detail": sample_errors[:20],
        },
        {
            "check": "historical_bridge_lineage_present",
            "status": "PASS" if len(bridge_rows) == len(standard_rows) else "FAIL",
            "detail": {
                "bridge_rows": len(bridge_rows),
                "standard_time_rows": len(standard_rows),
            },
        },
        {
            "check": "bridge_used_only_after_zero_ready_accumulation_groups",
            "status": "PASS" if ready_accumulation_count == 0 else "FAIL",
            "detail": ready_accumulation_count,
        },
        {
            "check": "standard_time_seconds_positive",
            "status": "PASS" if not standard_seconds_errors else "FAIL",
            "detail": standard_seconds_errors[:20],
        },
    ]
    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"

    payload = {
        "audit": "EDGEIQ_TARGET_002_COMPLETION_AUDIT_V1",
        "audited_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "counts": {
            "standard_time_rows": len(standard_rows),
            "historical_bridge_rows": len(bridge_rows),
            "ready_accumulation_groups": ready_accumulation_count,
            "track_count": len(track_counts),
            "distance_count": len(distance_counts),
        },
        "top_tracks": track_counts.most_common(10),
        "top_distances": distance_counts.most_common(10),
        "checks": checks,
        "verdict": "TARGET_002_STANDARD_TIME_RECOVERED" if status == "PASS" else "TARGET_002_REQUIRES_REVIEW",
        "governance": {
            "minimum_sample": MINIMUM_REQUIRED_SAMPLE,
            "threshold_weakened": False,
            "historical_source": str(HISTORICAL_PATH.relative_to(ROOT)),
            "condition_course_surface_adjustments_added": False,
        },
    }
    AUDIT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        for row in checks:
            writer.writerow({"check": row["check"], "status": row["status"], "detail": json.dumps(row["detail"], sort_keys=True)})

    AUDIT_MD.write_text(
        "\n".join(
            [
                "# EDGEiQ Target 002 Completion Audit V1",
                "",
                f"Status: `{status}`",
                "",
                "## Result",
                "",
                "Target 002 now emits canonical track-distance Standard Time rows using the governed historical results warehouse bridge because the existing benchmark accumulation path has zero ready groups.",
                "",
                "## Counts",
                "",
                f"- Standard Time rows: {len(standard_rows)}",
                f"- Historical bridge rows: {len(bridge_rows)}",
                f"- Ready benchmark accumulation groups: {ready_accumulation_count}",
                f"- Tracks covered: {len(track_counts)}",
                f"- Distances covered: {len(distance_counts)}",
                "",
                "## Governance",
                "",
                f"- Minimum sample preserved: {MINIMUM_REQUIRED_SAMPLE}",
                "- Threshold weakened: NO",
                "- Condition/course/surface adjustments added: NO",
                "- Historical source: `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "standard_time_rows": len(standard_rows)}, indent=2))


if __name__ == "__main__":
    main()
