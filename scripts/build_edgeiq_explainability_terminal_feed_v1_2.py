from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V1_1_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_1.csv"
CONNECTION_PATH = DATA / "edgeiq_connection_intelligence_v1.csv"

OUT_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_2.csv"
SUMMARY_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_2_summary.csv"

CONNECTION_COLUMNS = [
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
]

DERIVED_COLUMNS = [
    "connection_summary_for_decision_engine",
    "explainability_v1_2_status",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def normalize_track(value: object) -> str:
    text = upper(value)
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_horse(value: object) -> str:
    text = upper(value)
    return "".join(ch for ch in text if ch.isalnum())


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


def primary_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("race_date")),
        upper(row.get("track")),
        clean(row.get("race_no")),
        upper(row.get("horse_key")),
    )


def fallback_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("race_date")),
        normalize_track(row.get("track")),
        clean(row.get("race_no")),
        normalize_horse(row.get("horse") or row.get("horse_key")),
    )


def build_connection_summary(merged_row: dict[str, str]) -> str:
    narrative = clean(merged_row.get("connection_narrative"))
    if narrative:
        return narrative

    band = upper(merged_row.get("connection_band"))
    positive_label = clean(merged_row.get("connection_positive_1"))
    positive_value = clean(merged_row.get("connection_positive_1_value"))
    risk_label = clean(merged_row.get("connection_risk_1"))
    risk_value = clean(merged_row.get("connection_risk_1_value"))

    if band in {"ELITE", "STRONG", "POSITIVE"} and positive_label:
        suffix = f" {positive_value}".strip()
        return f"Connection profile adds support: {positive_label}{suffix}."
    if band in {"NEGATIVE", "POOR"} and risk_label:
        suffix = f" {risk_value}".strip()
        return f"Connection profile is a risk: {risk_label}{suffix}."
    return "Connection profile is neutral or limited from available history."


def numeric_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def main() -> None:
    built_at = now_iso()

    v1_1_rows = read_csv(V1_1_PATH)
    connection_rows = read_csv(CONNECTION_PATH)

    connection_by_primary: dict[tuple[str, str, str, str], dict[str, str]] = {}
    connection_by_fallback: dict[tuple[str, str, str, str], dict[str, str]] = {}

    for row in connection_rows:
        p_key = primary_key(row)
        if all(p_key):
            connection_by_primary[p_key] = row
        f_key = fallback_key(row)
        if all(f_key):
            connection_by_fallback[f_key] = row

    out_rows: list[dict[str, str]] = []
    complete_rows = 0
    partial_rows = 0
    joined_scores: list[float] = []
    band_counts: dict[str, int] = {}
    market_counts: dict[str, int] = {}

    original_fields = list(v1_1_rows[0].keys()) if v1_1_rows else []
    fieldnames = original_fields + [col for col in CONNECTION_COLUMNS + DERIVED_COLUMNS if col not in original_fields]

    for source_row in v1_1_rows:
        merged_row = dict(source_row)

        conn_row = connection_by_primary.get(primary_key(source_row))
        if conn_row is None:
            conn_row = connection_by_fallback.get(fallback_key(source_row))

        if conn_row is not None:
            complete_rows += 1
            merged_row["explainability_v1_2_status"] = "COMPLETE"
            for col in CONNECTION_COLUMNS:
                merged_row[col] = clean(conn_row.get(col))
            score_text = clean(conn_row.get("connection_score"))
            try:
                if score_text != "":
                    joined_scores.append(float(score_text))
            except ValueError:
                pass
            band = upper(conn_row.get("connection_band")) or "MISSING"
            band_counts[band] = band_counts.get(band, 0) + 1
            market_label = upper(conn_row.get("market_expectation_label")) or "MISSING"
            market_counts[market_label] = market_counts.get(market_label, 0) + 1
        else:
            partial_rows += 1
            merged_row["explainability_v1_2_status"] = "PARTIAL_CONNECTION_MISSING"
            for col in CONNECTION_COLUMNS:
                merged_row[col] = ""

        merged_row["connection_summary_for_decision_engine"] = build_connection_summary(merged_row)
        out_rows.append(merged_row)

    output_rows = len(out_rows)
    join_rate_pct = round((complete_rows / output_rows) * 100.0, 4) if output_rows else 0.0

    summary_row: dict[str, object] = {
        "status": "EDGEIQ_EXPLAINABILITY_TERMINAL_FEED_V1_2_BUILT",
        "input_v1_1_rows": len(v1_1_rows),
        "input_connection_rows": len(connection_rows),
        "output_rows": output_rows,
        "complete_rows": complete_rows,
        "partial_connection_missing_rows": partial_rows,
        "join_rate_pct": join_rate_pct,
        "avg_connection_score": round(numeric_mean(joined_scores), 4) if joined_scores else "",
        "built_at": built_at,
    }

    for band in ["ELITE", "STRONG", "POSITIVE", "NEUTRAL", "NEGATIVE", "POOR", "MISSING"]:
        summary_row[f"band_{band.lower()}_rows"] = band_counts.get(band, 0)

    for label in ["OUTPERFORMS_MARKET", "UNDERPERFORMS_MARKET", "MARKET_NEUTRAL", "INSUFFICIENT_SP_SAMPLE", "MISSING"]:
        summary_row[f"market_{label.lower()}_rows"] = market_counts.get(label, 0)

    write_csv(OUT_PATH, out_rows, fieldnames)
    write_csv(SUMMARY_PATH, [summary_row], list(summary_row.keys()))

    print("[EDGEIQ_EXPLAINABILITY_TERMINAL_FEED_V1_2] COMPLETE")
    print(f"status={summary_row['status']}")
    print(f"input_v1_1_rows={summary_row['input_v1_1_rows']}")
    print(f"input_connection_rows={summary_row['input_connection_rows']}")
    print(f"output_rows={summary_row['output_rows']}")
    print(f"complete_rows={summary_row['complete_rows']}")
    print(f"partial_connection_missing_rows={summary_row['partial_connection_missing_rows']}")
    print(f"join_rate_pct={summary_row['join_rate_pct']}")
    print(f"wrote={OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
