from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_RUNTIME_FEED_POPULATION_V1"

EMPTY_VALUES = {
    "",
    "null",
    "none",
    "nan",
    "n/a",
    "na",
    "undefined",
    "-",
    "--",
}

MAX_SAMPLE_ROWS = 5000


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_empty(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip().lower() in EMPTY_VALUES

    return False


def flatten_json(
    value: Any,
    prefix: str = "",
    output: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if output is None:
        output = []

    if isinstance(value, dict):
        row: dict[str, Any] = {}

        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)

            if isinstance(child, (dict, list)):
                flatten_json(child, name, output)
            else:
                row[name] = child

        if row:
            output.append(row)

    elif isinstance(value, list):
        for child in value[:MAX_SAMPLE_ROWS]:
            flatten_json(child, prefix, output)

    return output


def profile_rows(
    feed_path: str,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sampled_rows = rows[:MAX_SAMPLE_ROWS]

    fields = sorted(
        {
            str(field)
            for row in sampled_rows
            for field in row.keys()
        }
    )

    field_profiles: list[dict[str, Any]] = []

    for field in fields:
        present_count = 0
        populated_count = 0
        distinct_values: Counter[str] = Counter()

        for row in sampled_rows:
            if field not in row:
                continue

            present_count += 1
            value = row.get(field)

            if not is_empty(value):
                populated_count += 1
                distinct_values[str(value)] += 1

        sample_count = len(sampled_rows)
        population_rate = (
            populated_count / sample_count
            if sample_count
            else 0.0
        )

        field_profiles.append(
            {
                "feed_path": feed_path,
                "field_name": field,
                "sampled_rows": sample_count,
                "present_count": present_count,
                "populated_count": populated_count,
                "empty_count": sample_count - populated_count,
                "population_rate": round(population_rate, 6),
                "distinct_populated_values": len(distinct_values),
                "constant_value_suspected": (
                    populated_count > 1
                    and len(distinct_values) == 1
                ),
                "sample_values": " | ".join(
                    value
                    for value, _ in distinct_values.most_common(5)
                ),
            }
        )

    empty_fields = sum(
        1
        for profile in field_profiles
        if profile["population_rate"] == 0
    )

    low_population_fields = sum(
        1
        for profile in field_profiles
        if 0 < profile["population_rate"] < 0.8
    )

    summary = {
        "feed_path": feed_path,
        "row_count": len(rows),
        "sampled_rows": len(sampled_rows),
        "field_count": len(fields),
        "empty_field_count": empty_fields,
        "low_population_field_count": low_population_fields,
        "fully_populated_field_count": sum(
            1
            for profile in field_profiles
            if profile["population_rate"] == 1
        ),
        "status": (
            "EMPTY_FEED"
            if len(rows) == 0
            else "REVIEW_REQUIRED"
            if empty_fields or low_population_fields
            else "PASS_POPULATION"
        ),
    }

    return summary, field_profiles


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
        errors="replace",
    ) as handle:
        return list(csv.DictReader(handle))


def read_json_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            return payload

        return flatten_json(payload)

    if isinstance(payload, dict):
        candidate_keys = (
            "rows",
            "records",
            "data",
            "items",
            "meetings",
            "races",
            "runners",
            "results",
            "tracks",
            "weather",
        )

        for key in candidate_keys:
            candidate = payload.get(key)

            if isinstance(candidate, list):
                if all(isinstance(item, dict) for item in candidate):
                    return candidate

                flattened = flatten_json(candidate)

                if flattened:
                    return flattened

        return flatten_json(payload)

    return []


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    root = Path.cwd().resolve()

    phase_a_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-a-runtime-feed-discovery"
    )

    resolved_feed_csv = (
        phase_a_root
        / "EDGEIQ_RUNTIME_FEED_DISCOVERY_V1_RESOLVED_RUNTIME_FEEDS.csv"
    )

    if not resolved_feed_csv.exists():
        print(
            f"ERROR: Missing Phase A output: {resolved_feed_csv}",
            file=sys.stderr,
        )
        return 2

    output_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-b-runtime-feed-population"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    with resolved_feed_csv.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        runtime_feeds = list(csv.DictReader(handle))

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"runtime_feeds={len(runtime_feeds)}", flush=True)

    feed_summaries: list[dict[str, Any]] = []
    field_profiles: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for index, feed in enumerate(runtime_feeds, start=1):
        relative = feed["resolved_feed"]
        path = root / relative

        print(
            f"[profile] {index}/{len(runtime_feeds)} {relative}",
            flush=True,
        )

        try:
            if path.suffix.lower() == ".csv":
                rows = read_csv_rows(path)
            elif path.suffix.lower() == ".json":
                rows = read_json_rows(path)
            else:
                failures.append(
                    {
                        "feed_path": relative,
                        "reason": f"UNSUPPORTED_EXTENSION:{path.suffix}",
                    }
                )
                continue

            summary, profiles = profile_rows(relative, rows)

            summary["file_size_bytes"] = path.stat().st_size
            summary["extension"] = path.suffix.lower()

            feed_summaries.append(summary)
            field_profiles.extend(profiles)

        except Exception as exc:
            failures.append(
                {
                    "feed_path": relative,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )

    empty_fields = [
        row
        for row in field_profiles
        if float(row["population_rate"]) == 0
    ]

    low_population_fields = [
        row
        for row in field_profiles
        if 0 < float(row["population_rate"]) < 0.8
    ]

    constant_fields = [
        row
        for row in field_profiles
        if row["constant_value_suspected"]
    ]

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": now_utc(),
        "runtime_feeds_profiled": len(feed_summaries),
        "runtime_feeds_failed": len(failures),
        "total_fields_profiled": len(field_profiles),
        "empty_fields": len(empty_fields),
        "low_population_fields": len(low_population_fields),
        "constant_value_suspected_fields": len(constant_fields),
        "empty_feeds": sum(
            1
            for row in feed_summaries
            if row["status"] == "EMPTY_FEED"
        ),
        "status": (
            "FAIL"
            if failures
            else "REVIEW_REQUIRED"
            if empty_fields or low_population_fields
            else "PASS"
        ),
    }

    write_csv(
        output_root / f"{AUDIT_ID}_FEED_SUMMARY.csv",
        feed_summaries,
        [
            "feed_path",
            "extension",
            "file_size_bytes",
            "row_count",
            "sampled_rows",
            "field_count",
            "empty_field_count",
            "low_population_field_count",
            "fully_populated_field_count",
            "status",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_FIELD_POPULATION.csv",
        field_profiles,
        [
            "feed_path",
            "field_name",
            "sampled_rows",
            "present_count",
            "populated_count",
            "empty_count",
            "population_rate",
            "distinct_populated_values",
            "constant_value_suspected",
            "sample_values",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_EMPTY_FIELDS.csv",
        empty_fields,
        [
            "feed_path",
            "field_name",
            "sampled_rows",
            "present_count",
            "populated_count",
            "empty_count",
            "population_rate",
            "distinct_populated_values",
            "constant_value_suspected",
            "sample_values",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_LOW_POPULATION_FIELDS.csv",
        low_population_fields,
        [
            "feed_path",
            "field_name",
            "sampled_rows",
            "present_count",
            "populated_count",
            "empty_count",
            "population_rate",
            "distinct_populated_values",
            "constant_value_suspected",
            "sample_values",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_CONSTANT_FIELDS.csv",
        constant_fields,
        [
            "feed_path",
            "field_name",
            "sampled_rows",
            "present_count",
            "populated_count",
            "empty_count",
            "population_rate",
            "distinct_populated_values",
            "constant_value_suspected",
            "sample_values",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_FAILURES.csv",
        failures,
        [
            "feed_path",
            "reason",
        ],
    )

    (
        output_root / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== PHASE B COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())