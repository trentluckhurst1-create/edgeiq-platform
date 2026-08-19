from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs" / "performance-intelligence" / "prototypes" / "phase1_6" / "edgeiq_performance_fact_v0_1_20260716_100919.csv"
AUDIT_DIR = ROOT / "docs" / "performance-intelligence" / "audits" / "phase1_6_1"
PROGRESS_INTERVAL = 100_000


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_text(value: Any) -> str:
    return " ".join(clean(value).upper().split())


def normalise_integer(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    return str(int(number)) if number.is_integer() else ""


def normalise_date(value: Any) -> str:
    return clean(value)[:10] if clean(value) else ""


def race_context_key(row: dict[str, str]) -> str:
    parts = [
        normalise_date(row.get("race_date")),
        normalise_text(row.get("state")),
        normalise_text(row.get("track")),
        normalise_integer(row.get("race_number")),
        clean(row.get("race_id")),
    ]
    return "|".join(parts) if all(parts) else ""


def row_fingerprint(row: dict[str, str]) -> str:
    payload = "\x1f".join(f"{key}={clean(row.get(key))}" for key in sorted(row))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def context(row_number: int, row: dict[str, str]) -> dict[str, str]:
    return {
        "source_row_number": str(row_number),
        "legacy_performance_fact_id": clean(row.get("performance_fact_id")),
        "race_context_key": race_context_key(row),
        "race_id": clean(row.get("race_id")),
        "runner_id": clean(row.get("runner_id")),
        "horse": clean(row.get("horse")),
        "horse_code": clean(row.get("horse_code")),
        "race_date": normalise_date(row.get("race_date")),
        "state": clean(row.get("state")),
        "track": clean(row.get("track")),
        "race_number": clean(row.get("race_number")),
        "row_fingerprint": row_fingerprint(row),
    }


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = AUDIT_DIR / f"edgeiq_phase1_6_1_primary_key_diagnostic_{timestamp}.csv"
    json_path = AUDIT_DIR / f"edgeiq_phase1_6_1_primary_key_diagnostic_{timestamp}.json"
    latest_path = AUDIT_DIR / "edgeiq_phase1_6_1_primary_key_diagnostic_latest.json"

    row_count = 0
    blank_count = 0
    id_counts: dict[str, int] = defaultdict(int)
    id_examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    natural_counts: dict[str, int] = defaultdict(int)
    natural_examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    exact_fingerprints: dict[str, int] = defaultdict(int)
    runner_missing = 0
    reused_runner_contexts: dict[str, set[str]] = defaultdict(set)

    with SOURCE.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=1):
            row_count += 1
            if row_number == 1 or row_number % PROGRESS_INTERVAL == 0:
                print(f"PHASE1_6_1_PK_DIAGNOSTIC_PROGRESS={row_number}", flush=True)
            legacy_id = clean(row.get("performance_fact_id"))
            if not legacy_id:
                blank_count += 1
            id_counts[legacy_id] += 1
            if len(id_examples[legacy_id]) < 5:
                id_examples[legacy_id].append(context(row_number, row))

            key = "|".join([
                race_context_key(row),
                clean(row.get("runner_id")),
                clean(row.get("horse_code")),
            ])
            natural_counts[key] += 1
            if len(natural_examples[key]) < 5:
                natural_examples[key].append(context(row_number, row))
            exact_fingerprints[row_fingerprint(row)] += 1
            if not clean(row.get("runner_id")):
                runner_missing += 1
            if clean(row.get("runner_id")):
                reused_runner_contexts[clean(row.get("runner_id"))].add(race_context_key(row))

    duplicate_ids = {key: count for key, count in id_counts.items() if key and count > 1}
    duplicate_natural = {key: count for key, count in natural_counts.items() if key and count > 1}
    exact_duplicate_rows = sum(count - 1 for count in exact_fingerprints.values() if count > 1)
    runner_reused = {key: len(value) for key, value in reused_runner_contexts.items() if len(value) > 1}

    rows = []
    for legacy_id, count in sorted(duplicate_ids.items(), key=lambda item: item[1], reverse=True)[:1000]:
        examples = id_examples[legacy_id]
        for example in examples:
            item = dict(example)
            item["duplicate_type"] = "LEGACY_PERFORMANCE_FACT_ID"
            item["duplicate_group_key"] = legacy_id
            item["duplicate_group_count"] = str(count)
            rows.append(item)
    for natural_key, count in sorted(duplicate_natural.items(), key=lambda item: item[1], reverse=True)[:1000]:
        examples = natural_examples[natural_key]
        for example in examples:
            item = dict(example)
            item["duplicate_type"] = "NATURAL_RACE_RUNNER_HORSE"
            item["duplicate_group_key"] = natural_key
            item["duplicate_group_count"] = str(count)
            rows.append(item)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = [
            "duplicate_type",
            "duplicate_group_key",
            "duplicate_group_count",
            "source_row_number",
            "legacy_performance_fact_id",
            "race_context_key",
            "race_id",
            "runner_id",
            "horse",
            "horse_code",
            "race_date",
            "state",
            "track",
            "race_number",
            "row_fingerprint",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "marker": "EDGEIQ_PHASE1_6_1_PRIMARY_KEY_DIAGNOSTIC_PASS",
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "row_count": row_count,
        "blank_performance_fact_id_count": blank_count,
        "duplicate_performance_fact_id_groups": len(duplicate_ids),
        "duplicate_performance_fact_id_rows": sum(duplicate_ids.values()),
        "natural_duplicate_groups": len(duplicate_natural),
        "natural_duplicate_rows": sum(duplicate_natural.values()),
        "exact_duplicate_source_rows": exact_duplicate_rows,
        "runner_id_missing_rows": runner_missing,
        "runner_id_reused_across_context_count": len(runner_reused),
        "largest_duplicate_performance_fact_id_groups": [
            {"performance_fact_id": key, "count": count, "examples": id_examples[key]}
            for key, count in sorted(duplicate_ids.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "largest_natural_duplicate_groups": [
            {"natural_key": key, "count": count, "examples": natural_examples[key]}
            for key, count in sorted(duplicate_natural.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "diagnostic_csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "root_cause": (
            "Legacy Phase 1.6 performance_fact_id is not sufficient as the corrected primary key."
            if duplicate_ids
            else "No duplicate legacy performance_fact_id groups detected; investigate builder counter logic."
        ),
    }
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("EDGEIQ_PHASE1_6_1_PRIMARY_KEY_DIAGNOSTIC_PASS", flush=True)
    print(f"duplicate_performance_fact_id_groups={len(duplicate_ids)}", flush=True)
    print(f"duplicate_performance_fact_id_rows={sum(duplicate_ids.values())}", flush=True)


if __name__ == "__main__":
    main()
