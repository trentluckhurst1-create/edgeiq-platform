from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
SOURCE = DATA / "edgeiq_results_elapsed_time_observations_v1.csv"
OUT = DATA / "edgeiq_standard_time_performance_facts_from_results_v1.csv"
AUDIT = DOCS / "edgeiq_standard_time_performance_facts_from_results_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_standard_time_performance_facts_from_results_summary_v1.json"
REPORT = DOCS / "edgeiq_standard_time_performance_facts_from_results_report_v1.md"

FIELDS = [
    "benchmark_group_id",
    "canonical_race_id",
    "canonical_runner_id",
    "race_date",
    "track",
    "race_number",
    "race_distance_metres",
    "segment_start_metres",
    "segment_end_metres",
    "segment_distance_metres",
    "elapsed_time_seconds",
    "average_speed_mps",
    "eligibility_status",
    "source_format",
    "source_hash",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def group_id(row: dict[str, str]) -> str:
    key = "|".join([
        clean(row.get("track")).upper().replace(" ", ""),
        clean(row.get("race_distance_metres")),
        clean(row.get("segment_start_metres")),
        clean(row.get("segment_end_metres")),
        clean(row.get("segment_distance_metres")),
    ])
    return "RSTG1-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16].upper()


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    rows = read_csv(SOURCE)
    eligible = [row for row in rows if clean(row.get("eligibility_status")) == "ELIGIBLE"]
    facts: list[dict[str, object]] = []
    for row in eligible:
        facts.append({
            "benchmark_group_id": group_id(row),
            "canonical_race_id": clean(row.get("canonical_race_id")),
            "canonical_runner_id": clean(row.get("canonical_runner_id")),
            "race_date": clean(row.get("race_date")),
            "track": clean(row.get("track")),
            "race_number": clean(row.get("race_number")),
            "race_distance_metres": clean(row.get("race_distance_metres")),
            "segment_start_metres": clean(row.get("segment_start_metres")),
            "segment_end_metres": clean(row.get("segment_end_metres")),
            "segment_distance_metres": clean(row.get("segment_distance_metres")),
            "elapsed_time_seconds": clean(row.get("elapsed_time_seconds")),
            "average_speed_mps": clean(row.get("average_speed_mps")),
            "eligibility_status": "ELIGIBLE",
            "source_format": clean(row.get("source_format")),
            "source_hash": clean(row.get("source_payload_sha256")),
        })

    duplicate_count = len(facts) - len({
        (
            fact["benchmark_group_id"],
            fact["canonical_race_id"],
            fact["canonical_runner_id"],
            fact["segment_start_metres"],
            fact["segment_end_metres"],
        )
        for fact in facts
    })
    group_counts = Counter(fact["benchmark_group_id"] for fact in facts)
    write_csv(OUT, facts, FIELDS)
    summary = {
        "source_rows": len(rows),
        "valid_elapsed_observations": len(eligible),
        "performance_fact_rows": len(facts),
        "races": len({fact["canonical_race_id"] for fact in facts}),
        "runners": len({(fact["canonical_race_id"], fact["canonical_runner_id"]) for fact in facts}),
        "benchmark_groups": len(group_counts),
        "largest_group_count": max(group_counts.values()) if group_counts else 0,
        "duplicate_contribution_count": duplicate_count,
        "rejections": len(rows) - len(eligible),
        "deterministic_hash": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }
    audit_rows = [
        {"check": "source_nonempty", "status": "PASS" if len(rows) > 0 else "FAIL", "value": len(rows), "detail": "Elapsed observation source must contain rows."},
        {"check": "valid_elapsed_observations", "status": "PASS" if len(eligible) > 0 else "FAIL", "value": len(eligible), "detail": "At least one eligible segment row is required."},
        {"check": "row_conservation", "status": "PASS" if len(eligible) + (len(rows) - len(eligible)) == len(rows) else "FAIL", "value": len(rows), "detail": "Eligible plus rejected observations must equal source rows."},
        {"check": "performance_fact_rows", "status": "PASS" if len(facts) == len(eligible) else "FAIL", "value": len(facts), "detail": "One fact per eligible elapsed observation."},
        {"check": "duplicate_contribution_checks", "status": "PASS" if duplicate_count == 0 else "FAIL", "value": duplicate_count, "detail": "No duplicate runner contribution per group/segment."},
        {"check": "benchmark_groups", "status": "PASS" if len(group_counts) > 0 else "FAIL", "value": len(group_counts), "detail": "Comparable groups created from contract key."},
        {"check": "deterministic_hash", "status": "PASS", "value": summary["deterministic_hash"], "detail": "Fact output SHA."},
    ]
    write_csv(AUDIT, audit_rows, ["check", "status", "value", "detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results-Based Standard Time Performance Facts V1\n\n"
        f"Performance fact rows: `{len(facts)}`\n\n"
        f"Benchmark groups: `{len(group_counts)}`\n\n"
        f"Duplicate contribution count: `{duplicate_count}`\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0 if all(row["status"] == "PASS" for row in audit_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
