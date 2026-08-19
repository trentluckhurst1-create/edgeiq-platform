from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RESTART = ROOT / "docs" / "performance-intelligence" / "restart-v1"

DELTA_PATH = DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
PARAMETER_PATH = DATA / "edgeiq_length_conversion_parameter_fact_v1.csv"
SOURCE_PATH = ROOT / "config" / "performance-intelligence" / "edgeiq_length_conversion_parameter_source_v1.csv"

AUDIT_JSON = RESTART / "edgeiq_lengths_conversion_blocker_v1.json"
AUDIT_CSV = RESTART / "edgeiq_lengths_conversion_blocker_v1.csv"
AUDIT_MD = RESTART / "EDGEIQ_LENGTHS_CONVERSION_BLOCKER_V1.md"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_fields(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def main() -> None:
    RESTART.mkdir(parents=True, exist_ok=True)
    delta_rows = read_csv(DELTA_PATH)
    parameter_rows = read_csv(PARAMETER_PATH)
    source_fields = read_fields(SOURCE_PATH)
    expected_source_fields = [
        "conversion_scope",
        "official_distance_metres",
        "seconds_per_length",
        "conversion_model_version",
        "parameter_status",
        "effective_from_date",
        "effective_to_date",
        "evidence_reference",
        "evidence_sha256",
    ]
    distance_counts = Counter(text(row.get("official_distance_metres")) for row in delta_rows)
    parameter_distances = {text(row.get("official_distance_metres")) for row in parameter_rows}
    missing_distances = sorted(distance for distance in distance_counts if distance and distance not in parameter_distances)

    checks = [
        {
            "check": "race_time_delta_rows_exist",
            "status": "PASS" if delta_rows else "FAIL",
            "detail": len(delta_rows),
        },
        {
            "check": "length_conversion_parameter_fact_populated",
            "status": "PASS" if parameter_rows else "FAIL",
            "detail": len(parameter_rows),
        },
        {
            "check": "exact_distance_parameter_source_schema_available",
            "status": "PASS" if source_fields == expected_source_fields else "FAIL",
            "detail": {
                "path": str(SOURCE_PATH.relative_to(ROOT)),
                "actual_fields": source_fields,
                "expected_fields": expected_source_fields,
            },
        },
        {
            "check": "all_delta_distances_have_parameters",
            "status": "PASS" if not missing_distances else "FAIL",
            "detail": missing_distances,
        },
    ]
    status = "BLOCKED" if any(row["status"] == "FAIL" for row in checks) else "PASS"
    payload = {
        "audit": "EDGEIQ_LENGTHS_CONVERSION_BLOCKER_V1",
        "audited_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "counts": {
            "race_time_delta_rows": len(delta_rows),
            "length_conversion_parameter_rows": len(parameter_rows),
            "delta_distance_count": len(distance_counts),
        },
        "delta_distances": dict(sorted(distance_counts.items())),
        "missing_parameter_distances": missing_distances,
        "blocker": "MISSING_GOVERNED_EXACT_DISTANCE_SECONDS_PER_LENGTH_PARAMETER_ROWS_OR_SOURCE_SCHEMA" if status == "BLOCKED" else "",
        "governance": {
            "length_conversion_parameter_source_exists": SOURCE_PATH.exists(),
            "length_conversion_parameter_source_schema_exact": source_fields == expected_source_fields,
            "coefficient_fabricated": False,
            "lengths_output_rebuilt": False,
        },
        "checks": checks,
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
                "# EDGEiQ Lengths Conversion Blocker V1",
                "",
                f"Status: `{status}`",
                "",
                "## Finding",
                "",
                "Race-time delta versus Standard Time is now populated, but canonical lengths-versus-standard cannot be rebuilt because the exact-distance parameter fact is empty and the available config source uses a different surface/condition schema.",
                "",
                "## Counts",
                "",
                f"- Race-time delta rows: {len(delta_rows)}",
                f"- Length conversion parameter rows: {len(parameter_rows)}",
                f"- Missing parameter distances: {', '.join(missing_distances) if missing_distances else 'none'}",
                "",
                "## Governance",
                "",
                "- Coefficient fabricated: NO",
                "- Lengths output rebuilt: NO",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "missing_parameter_distances": missing_distances}, indent=2))


if __name__ == "__main__":
    main()
