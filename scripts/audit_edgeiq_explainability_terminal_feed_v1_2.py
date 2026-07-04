from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V1_1_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_1.csv"
V1_2_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_2.csv"

DETAIL_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_2_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_2_audit_summary.csv"

CORE_FIELDS = [
    "model_rank",
    "confidence_band",
    "trend_label",
    "race_shape_label",
    "why_ranked_here",
]

CONNECTION_FIELDS = [
    "connection_score",
    "connection_band",
    "connection_positive_1",
    "connection_positive_1_value",
    "connection_positive_2",
    "connection_positive_2_value",
    "connection_risk_1",
    "connection_risk_1_value",
    "connection_narrative",
    "market_expectation_label",
    "sp_expectation_delta",
    "trainer_track_sr",
    "jockey_track_sr",
    "combo_sr",
    "combo_track_sr",
    "sp_sample_starts",
    "connection_summary_for_decision_engine",
    "explainability_v1_2_status",
]

REQUIRED_CONNECTION_PAYLOAD_FIELDS = [
    "connection_score",
    "connection_band",
    "connection_narrative",
    "market_expectation_label",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def normalize_horse(value: object) -> str:
    text = upper(value)
    return "".join(ch for ch in text if ch.isalnum())


def normalize_track(value: object) -> str:
    text = upper(value)
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def runner_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            clean(row.get("race_date")),
            normalize_track(row.get("track")),
            clean(row.get("race_no")),
            upper(row.get("horse_key")) or normalize_horse(row.get("horse")),
        ]
    )


def main() -> None:
    built_at = now_iso()
    v1_1_rows = read_csv(V1_1_PATH)
    v1_2_rows = read_csv(V1_2_PATH)

    v1_2_header = list(v1_2_rows[0].keys()) if v1_2_rows else []
    schema_missing_connection_columns = [field for field in CONNECTION_FIELDS if field not in v1_2_header]

    v1_1_keys = [runner_key(row) for row in v1_1_rows]
    v1_2_keys = [runner_key(row) for row in v1_2_rows]

    v1_1_key_set = set(v1_1_keys)
    v1_2_key_set = set(v1_2_keys)

    v1_1_counts: dict[str, int] = {}
    v1_2_counts: dict[str, int] = {}
    for key in v1_1_keys:
        v1_1_counts[key] = v1_1_counts.get(key, 0) + 1
    for key in v1_2_keys:
        v1_2_counts[key] = v1_2_counts.get(key, 0) + 1

    detail_rows: list[dict[str, object]] = []
    missing_core_rows = 0
    missing_connection_payload_rows = 0
    partial_rows = 0

    for row in v1_2_rows:
        key = runner_key(row)
        missing_core = [field for field in CORE_FIELDS if clean(row.get(field)) == ""]
        missing_connection_payload = all(clean(row.get(field)) == "" for field in REQUIRED_CONNECTION_PAYLOAD_FIELDS)

        status = []
        if missing_core:
            missing_core_rows += 1
            status.append("MISSING_CORE_FIELDS")
        if missing_connection_payload:
            missing_connection_payload_rows += 1
            status.append("MISSING_CONNECTION_PAYLOAD")
        if clean(row.get("explainability_v1_2_status")) != "COMPLETE":
            partial_rows += 1
            status.append("PARTIAL_CONNECTION")
        if v1_2_counts.get(key, 0) > 1:
            status.append("DUPLICATE_V1_2_KEY")
        if key not in v1_1_key_set:
            status.append("MISSING_IN_V1_1")
        if not status:
            status = ["PASS"]

        detail_rows.append(
            {
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "horse_key": clean(row.get("horse_key")),
                "runner_key": key,
                "v1_1_key_present": "YES" if key in v1_1_key_set else "NO",
                "v1_2_key_count": v1_2_counts.get(key, 0),
                "missing_core_fields": "; ".join(missing_core),
                "missing_connection_payload": "YES" if missing_connection_payload else "NO",
                "explainability_v1_2_status": clean(row.get("explainability_v1_2_status")),
                "audit_status": "|".join(status),
                "built_at": built_at,
            }
        )

    missing_from_v1_2 = sorted(v1_1_key_set - v1_2_key_set)
    extra_in_v1_2 = sorted(v1_2_key_set - v1_1_key_set)
    duplicate_v1_1_keys = sum(1 for count in v1_1_counts.values() if count > 1)
    duplicate_v1_2_keys = sum(1 for count in v1_2_counts.values() if count > 1)
    connection_join_rate_pct = round(
        ((len(v1_2_rows) - partial_rows) / len(v1_2_rows)) * 100.0, 4
    ) if v1_2_rows else 0.0

    summary_row = {
        "status": "PASS"
        if len(v1_1_rows) == len(v1_2_rows)
        and duplicate_v1_1_keys == 0
        and duplicate_v1_2_keys == 0
        and missing_core_rows == 0
        and missing_connection_payload_rows == 0
        and len(schema_missing_connection_columns) == 0
        and partial_rows == 0
        and not missing_from_v1_2
        and not extra_in_v1_2
        else "FAIL",
        "v1_1_rows": len(v1_1_rows),
        "v1_2_rows": len(v1_2_rows),
        "row_count_match": "YES" if len(v1_1_rows) == len(v1_2_rows) else "NO",
        "distinct_v1_1_keys": len(v1_1_key_set),
        "distinct_v1_2_keys": len(v1_2_key_set),
        "duplicate_v1_1_keys": duplicate_v1_1_keys,
        "duplicate_v1_2_keys": duplicate_v1_2_keys,
        "missing_from_v1_2_rows": len(missing_from_v1_2),
        "extra_in_v1_2_rows": len(extra_in_v1_2),
        "missing_core_field_rows": missing_core_rows,
        "missing_connection_payload_rows": missing_connection_payload_rows,
        "missing_connection_columns_count": len(schema_missing_connection_columns),
        "missing_connection_columns": "; ".join(schema_missing_connection_columns),
        "partial_connection_missing_rows": partial_rows,
        "connection_join_rate_pct": connection_join_rate_pct,
        "built_at": built_at,
    }

    detail_fieldnames = list(detail_rows[0].keys()) if detail_rows else [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "runner_key",
        "v1_1_key_present",
        "v1_2_key_count",
        "missing_core_fields",
        "missing_connection_payload",
        "explainability_v1_2_status",
        "audit_status",
        "built_at",
    ]

    write_csv(DETAIL_PATH, detail_rows, detail_fieldnames)
    write_csv(SUMMARY_PATH, [summary_row], list(summary_row.keys()))

    print("[EDGEIQ_EXPLAINABILITY_TERMINAL_FEED_V1_2_AUDIT] COMPLETE")
    print(f"status={summary_row['status']}")
    print(f"v1_1_rows={summary_row['v1_1_rows']}")
    print(f"v1_2_rows={summary_row['v1_2_rows']}")
    print(f"duplicate_v1_2_keys={summary_row['duplicate_v1_2_keys']}")
    print(f"missing_core_field_rows={summary_row['missing_core_field_rows']}")
    print(f"missing_connection_payload_rows={summary_row['missing_connection_payload_rows']}")
    print(f"missing_connection_columns_count={summary_row['missing_connection_columns_count']}")
    print(f"partial_connection_missing_rows={summary_row['partial_connection_missing_rows']}")
    print(f"connection_join_rate_pct={summary_row['connection_join_rate_pct']}")
    print(f"wrote={DETAIL_PATH}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
