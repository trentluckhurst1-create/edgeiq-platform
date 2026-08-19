from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

JOIN_AUDIT = DATA / "edgeiq_form_guide_v3_4_engine_join_audit.csv"
COVERAGE = DATA / "edgeiq_form_guide_v3_4_coverage.csv"

OUT_TXT = DATA / "edgeiq_form_guide_v3_4_join_diagnosis.txt"
OUT_JSON = DATA / "edgeiq_form_guide_v3_4_join_diagnosis.json"
OUT_CSV = DATA / "edgeiq_form_guide_v3_4_join_failures.csv"

JOIN_COLUMNS = {
    "EPI": "epi_match",
    "EDGEiQ Price": "price_match",
    "Early Speed": "early_speed_match",
    "Suitability": "suitability_match",
    "Race Shape": "race_shape_match",
    "Late Speed": "late_speed_match",
    "Form Momentum": "momentum_match",
    "Profile": "profile_match",
    "Preparation": "preparation_match",
    "Recent Form": "recent_form_match",
}

IDENTITY_COLUMNS = [
    "race_date",
    "meeting",
    "race_number",
    "runner_number",
    "runner_id",
    "runner_name",
]

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))

def is_match(value: Any) -> bool:
    text = str(value or "").strip().upper()
    return text in {
        "1",
        "TRUE",
        "YES",
        "Y",
        "MATCH",
        "MATCHED",
        "EXACT",
        "DIRECT",
        "OK",
        "PASS",
    }

def safe_text(value: Any) -> str:
    return str(value or "").strip()

def main() -> None:
    join_rows = read_csv(JOIN_AUDIT)
    coverage_rows = read_csv(COVERAGE)

    total_runners = len(join_rows)

    metric_summary: dict[str, dict[str, Any]] = {}
    failure_rows: list[dict[str, Any]] = []

    failures_by_reason: Counter[str] = Counter()
    failures_by_meeting: Counter[str] = Counter()
    failures_by_race: Counter[str] = Counter()
    failures_by_metric: Counter[str] = Counter()

    for label, column in JOIN_COLUMNS.items():
        matched = sum(1 for row in join_rows if is_match(row.get(column)))
        missing = total_runners - matched
        coverage_pct = round((matched / total_runners * 100), 2) if total_runners else 0.0

        metric_summary[label] = {
            "column": column,
            "matched": matched,
            "missing": missing,
            "total": total_runners,
            "coverage_pct": coverage_pct,
        }

    for row in join_rows:
        failed_metrics = [
            label
            for label, column in JOIN_COLUMNS.items()
            if not is_match(row.get(column))
        ]

        if not failed_metrics:
            continue

        reason = safe_text(row.get("ambiguity_reason")) or "NO_REASON_RECORDED"
        meeting = safe_text(row.get("meeting")) or "UNKNOWN_MEETING"
        race_number = safe_text(row.get("race_number")) or "UNKNOWN_RACE"
        race_key = f"{safe_text(row.get('race_date'))}|{meeting}|R{race_number}"

        failures_by_reason[reason] += 1
        failures_by_meeting[meeting] += 1
        failures_by_race[race_key] += 1

        for metric in failed_metrics:
            failures_by_metric[metric] += 1

        failure_row = {
            key: safe_text(row.get(key))
            for key in IDENTITY_COLUMNS
        }
        failure_row.update({
            "failed_metrics": " | ".join(failed_metrics),
            "join_method": safe_text(row.get("join_method")),
            "ambiguity_reason": reason,
        })

        for _, column in JOIN_COLUMNS.items():
            failure_row[column] = safe_text(row.get(column))

        failure_rows.append(failure_row)

    race_coverage = []

    for row in coverage_rows:
        race_coverage.append({
            "race_date": safe_text(row.get("race_date")),
            "meeting": safe_text(row.get("meeting")),
            "race_number": safe_text(row.get("race_number")),
            "runners": safe_text(row.get("runners")),
            "epi": safe_text(row.get("EPI")),
            "edgeiq_price": safe_text(row.get("EDGEiQ Price")),
            "early_speed": safe_text(row.get("Early Speed")),
            "suitability": safe_text(row.get("Suitability")),
            "race_shape": safe_text(row.get("Race Shape")),
            "preparation_profile": safe_text(row.get("Preparation Profile")),
            "career_profile": safe_text(row.get("Career Profile")),
            "recent_form": safe_text(row.get("Recent Form")),
        })

    payload = {
        "status": "PASS",
        "join_audit_source": str(JOIN_AUDIT),
        "coverage_source": str(COVERAGE),
        "total_runner_rows": total_runners,
        "metric_summary": metric_summary,
        "failures": {
            "runner_rows_with_any_failure": len(failure_rows),
            "by_metric": dict(failures_by_metric.most_common()),
            "by_reason": dict(failures_by_reason.most_common(30)),
            "by_meeting": dict(failures_by_meeting.most_common(30)),
            "by_race": dict(failures_by_race.most_common(50)),
        },
        "race_coverage": race_coverage,
        "sample_failures": failure_rows[:100],
    }

    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    failure_fieldnames = (
        IDENTITY_COLUMNS
        + ["failed_metrics", "join_method", "ambiguity_reason"]
        + list(JOIN_COLUMNS.values())
    )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=failure_fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(failure_rows)

    lines: list[str] = []
    lines.append("EDGEiQ FORM GUIDE V3.4 JOIN DIAGNOSIS")
    lines.append("=" * 72)
    lines.append(f"Runner rows audited: {total_runners}")
    lines.append(
        f"Rows with one or more failed joins: {len(failure_rows)}"
    )
    lines.append("")

    lines.append("METRIC COVERAGE")
    lines.append("-" * 72)

    for label, result in metric_summary.items():
        lines.append(
            f"{label:<22} "
            f"{result['matched']:>5}/{result['total']:<5} "
            f"{result['coverage_pct']:>7.2f}% "
            f"missing={result['missing']}"
        )

    lines.append("")
    lines.append("FAILURES BY METRIC")
    lines.append("-" * 72)

    for label, count in failures_by_metric.most_common():
        lines.append(f"{label:<22} {count}")

    lines.append("")
    lines.append("TOP FAILURE REASONS")
    lines.append("-" * 72)

    for reason, count in failures_by_reason.most_common(30):
        lines.append(f"{count:>5}  {reason}")

    lines.append("")
    lines.append("TOP RACES WITH FAILURES")
    lines.append("-" * 72)

    for race_key, count in failures_by_race.most_common(30):
        lines.append(f"{count:>5}  {race_key}")

    lines.append("")
    lines.append("OUTPUTS")
    lines.append("-" * 72)
    lines.append(str(OUT_JSON))
    lines.append(str(OUT_CSV))

    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))

if __name__ == "__main__":
    main()
