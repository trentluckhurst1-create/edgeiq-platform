from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_IN = DATA / "edgeiq_live_nexus_contextual_feed_v2.csv"
SCORE_IN = DATA / "edgeiq_nexus_contextual_score_v2.csv"
DIST_IN = DATA / "edgeiq_nexus_score_distribution_v1.csv"
DIST_SUMMARY_IN = DATA / "edgeiq_nexus_score_distribution_v1_summary.csv"

CALIBRATION_OUT = DATA / "edgeiq_nexus_score_calibration_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_nexus_score_calibration_summary_v1.csv"
LIVE_OUT = DATA / "edgeiq_live_nexus_contextual_feed_v2_1.csv"
SCORE_OUT = DATA / "edgeiq_nexus_contextual_score_v2_1.csv"


def text(value: Any) -> str:
    return str(value or "").strip()


def to_float(value: Any) -> float | None:
    raw = text(value)
    if not raw:
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    return val if math.isfinite(val) else None


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def row_key(row: dict[str, Any]) -> str:
    key = text(row.get("runner_key"))
    if key:
        return key
    return "|".join([text(row.get("race_date")), text(row.get("track")).upper(), text(row.get("race_no")), text(row.get("runner_name")).upper()])


def race_key(row: dict[str, Any]) -> str:
    return "|".join([text(row.get("race_date")), text(row.get("track")).upper(), text(row.get("race_no"))])


def percentile_map(rows: list[dict[str, Any]], score_field: str) -> dict[str, float]:
    scored = [(row_key(row), to_float(row.get(score_field))) for row in rows]
    scored = [(key, score) for key, score in scored if score is not None]
    if not scored:
        return {}
    ordered = sorted(scored, key=lambda item: (item[1], item[0]))
    n = len(ordered)
    if n == 1:
        return {ordered[0][0]: 100.0}
    return {key: idx / (n - 1) * 100.0 for idx, (key, _score) in enumerate(ordered)}


def race_percentiles(rows: list[dict[str, Any]], score_field: str) -> tuple[dict[str, float], dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if to_float(row.get(score_field)) is None:
            continue
        grouped.setdefault(race_key(row), []).append(row)
    pct: dict[str, float] = {}
    ranks: dict[str, int] = {}
    for race_rows in grouped.values():
        ordered_desc = sorted(race_rows, key=lambda r: (to_float(r.get(score_field)) or -999, text(r.get("runner_name"))), reverse=True)
        for idx, row in enumerate(ordered_desc, start=1):
            ranks[row_key(row)] = idx
        local_pct = percentile_map(race_rows, score_field)
        pct.update(local_pct)
    return pct, ranks


def global_ranks(rows: list[dict[str, Any]], score_field: str) -> dict[str, int]:
    ordered = sorted(
        [row for row in rows if to_float(row.get(score_field)) is not None],
        key=lambda r: (to_float(r.get(score_field)) or -999, text(r.get("runner_name"))),
        reverse=True,
    )
    return {row_key(row): idx for idx, row in enumerate(ordered, start=1)}


def calibrated_band(score: float) -> str:
    if score >= 92:
        return "ELITE"
    if score >= 80:
        return "STRONG"
    if score >= 65:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 25:
        return "NEGATIVE"
    return "POOR"


def append_fields(rows: list[dict[str, str]], calibration: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        cal = calibration.get(row_key(row), {})
        raw_score = text(row.get("nexus_context_score"))
        raw_band = text(row.get("nexus_context_band"))
        next_row: dict[str, Any] = dict(row)
        next_row["raw_nexus_context_score"] = raw_score
        next_row["raw_nexus_context_band"] = raw_band
        next_row["nexus_context_score_calibrated"] = cal.get("nexus_context_score_calibrated", "")
        next_row["nexus_context_band_calibrated"] = cal.get("nexus_context_band_calibrated", "")
        next_row["nexus_context_percentile"] = cal.get("nexus_context_percentile", "")
        next_row["nexus_context_rank_in_race"] = cal.get("nexus_context_rank_in_race", "")
        next_row["nexus_context_field_rank"] = cal.get("nexus_context_field_rank", "")
        next_row["calibration_method"] = cal.get("calibration_method", "")
        out.append(next_row)
    return out


def fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    return fields


def main() -> None:
    live_rows = read_rows(LIVE_IN)
    score_rows = read_rows(SCORE_IN)
    base_rows = score_rows or live_rows
    global_pct = percentile_map(base_rows, "nexus_context_score")
    race_pct, race_rank = race_percentiles(base_rows, "nexus_context_score")
    field_rank = global_ranks(base_rows, "nexus_context_score")

    calibration: dict[str, dict[str, Any]] = {}
    calibration_rows: list[dict[str, Any]] = []
    for row in base_rows:
        key = row_key(row)
        raw_score = to_float(row.get("nexus_context_score"))
        if raw_score is None:
            continue
        g_pct = global_pct.get(key, 50.0)
        r_pct = race_pct.get(key, g_pct)
        calibrated = round((g_pct * 0.70) + (r_pct * 0.30), 1)
        band = calibrated_band(calibrated)
        record = {
            "runner_key": text(row.get("runner_key")),
            "runner_name": text(row.get("runner_name")),
            "race_date": text(row.get("race_date")),
            "track": text(row.get("track")),
            "race_no": text(row.get("race_no")),
            "raw_nexus_context_score": round(raw_score, 3),
            "raw_nexus_context_band": text(row.get("nexus_context_band")),
            "nexus_context_score_calibrated": calibrated,
            "nexus_context_band_calibrated": band,
            "nexus_context_percentile": round(g_pct, 1),
            "race_context_percentile": round(r_pct, 1),
            "nexus_context_rank_in_race": race_rank.get(key, ""),
            "nexus_context_field_rank": field_rank.get(key, ""),
            "calibration_method": "70_GLOBAL_PERCENTILE_30_RACE_PERCENTILE",
        }
        calibration[key] = record
        calibration_rows.append(record)

    live_out = append_fields(live_rows, calibration)
    score_out = append_fields(score_rows, calibration)
    calibration_rows.sort(key=lambda r: float(r["nexus_context_score_calibrated"]), reverse=True)

    band_counts: dict[str, int] = {}
    scores: list[float] = []
    for row in calibration_rows:
        band_counts[text(row["nexus_context_band_calibrated"])] = band_counts.get(text(row["nexus_context_band_calibrated"]), 0) + 1
        scores.append(float(row["nexus_context_score_calibrated"]))
    summary_rows: list[dict[str, Any]] = [
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "rows", "value": len(calibration_rows)},
        {"metric": "calibration_method", "value": "70_GLOBAL_PERCENTILE_30_RACE_PERCENTILE"},
        {"metric": "min_calibrated", "value": min(scores) if scores else ""},
        {"metric": "max_calibrated", "value": max(scores) if scores else ""},
        {"metric": "spread", "value": (max(scores) - min(scores)) if scores else ""},
    ]
    for band, count in sorted(band_counts.items()):
        summary_rows.append({"metric": f"band_count_{band}", "value": count})
    for idx, row in enumerate(calibration_rows[:10], start=1):
        summary_rows.append({"metric": f"top_{idx:02d}", "value": f"{row['runner_name']} | {row['track']} R{row['race_no']} | {row['nexus_context_score_calibrated']} | {row['nexus_context_band_calibrated']} | raw {row['raw_nexus_context_score']}"})
    for idx, row in enumerate(list(reversed(calibration_rows[-10:])), start=1):
        summary_rows.append({"metric": f"bottom_{idx:02d}", "value": f"{row['runner_name']} | {row['track']} R{row['race_no']} | {row['nexus_context_score_calibrated']} | {row['nexus_context_band_calibrated']} | raw {row['raw_nexus_context_score']}"})
    summary_rows.append({"metric": "distribution_source_rows", "value": len(read_rows(DIST_IN))})
    summary_rows.append({"metric": "distribution_summary_source_rows", "value": len(read_rows(DIST_SUMMARY_IN))})

    cal_fields = [
        "runner_key",
        "runner_name",
        "race_date",
        "track",
        "race_no",
        "raw_nexus_context_score",
        "raw_nexus_context_band",
        "nexus_context_score_calibrated",
        "nexus_context_band_calibrated",
        "nexus_context_percentile",
        "race_context_percentile",
        "nexus_context_rank_in_race",
        "nexus_context_field_rank",
        "calibration_method",
    ]
    write_rows(CALIBRATION_OUT, calibration_rows, cal_fields)
    write_rows(SUMMARY_OUT, summary_rows, ["metric", "value"])
    write_rows(LIVE_OUT, live_out, fieldnames(live_out))
    write_rows(SCORE_OUT, score_out, fieldnames(score_out))
    print(f"Nexus calibration built: rows={len(calibration_rows)} spread={(max(scores)-min(scores)) if scores else 0:.1f} bands={band_counts}")


if __name__ == "__main__":
    main()
