from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
LIVE_BOARD_GOVERNED = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT_JSON = DATA / "edgeiq_epi_current_rating_v1.json"
OUT_CSV = DATA / "edgeiq_epi_current_rating_v1.csv"
DIST_CSV = DATA / "edgeiq_epi_distribution_v1.csv"
DIST_SUMMARY = DATA / "edgeiq_epi_distribution_summary_v1.csv"
VERSION = "v5_2"
SOURCE = "edgeiq_live_runner_board_governed_v1.csv:projected_rating_v5_2"


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na"} else text


def to_float(value: Any) -> float | None:
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def is_scratched(row: dict[str, Any]) -> bool:
    values = [row.get("is_scratched"), row.get("runner_status"), row.get("scratch_status"), row.get("market_source_status")]
    return any(clean(value).upper() in {"TRUE", "SCRATCHED", "SCRATCHING"} or "SCRATCH" in clean(value).upper() for value in values)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    pos = (len(ordered) - 1) * pct
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return round(ordered[int(pos)], 2)
    weight = pos - low
    return round((ordered[low] * (1 - weight)) + (ordered[high] * weight), 2)


def stats(values: list[float], missing: int) -> dict[str, Any]:
    if not values:
        return {
            "count": 0, "missing": missing, "min": "", "max": "", "mean": "", "median": "", "std": "",
            "p5": "", "p10": "", "p25": "", "p50": "", "p75": "", "p90": "", "p95": "",
        }
    return {
        "count": len(values),
        "missing": missing,
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "std": round(pstdev(values), 2) if len(values) > 1 else 0.0,
        "p5": percentile(values, 0.05),
        "p10": percentile(values, 0.10),
        "p25": percentile(values, 0.25),
        "p50": percentile(values, 0.50),
        "p75": percentile(values, 0.75),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
    }


def display(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.1f}" if value % 1 else f"{value:.0f}"


def trend_for(value: float | None) -> str:
    return "" if value is None else "CURRENT"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not LIVE_BOARD_GOVERNED.exists():
        raise FileNotFoundError(LIVE_BOARD_GOVERNED)

    rows: list[dict[str, Any]] = []
    with LIVE_BOARD_GOVERNED.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        rows = list(csv.DictReader(handle))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[clean(row.get("race_key")) or "|".join([clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no"))])].append(row)

    output_rows: list[dict[str, Any]] = []
    json_rows: list[dict[str, Any]] = []
    all_values: list[float] = []
    missing = 0
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for race_key, race_rows in grouped.items():
        active_with_epi = []
        for row in race_rows:
            value = to_float(row.get("projected_rating_v5_2"))
            if not is_scratched(row) and value is not None:
                active_with_epi.append((row, value))
        values = [value for _, value in active_with_epi]
        high = max(values) if values else None
        avg = mean(values) if values else None
        ranked = sorted(active_with_epi, key=lambda item: item[1], reverse=True)
        ranks = {id(row): index + 1 for index, (row, _) in enumerate(ranked)}

        for row in race_rows:
            value = to_float(row.get("projected_rating_v5_2"))
            scratched = is_scratched(row)
            status = "SCRATCHED" if scratched else ("CURRENT" if value is not None else "MISSING")
            if value is None and not scratched:
                missing += 1
            if value is not None and not scratched:
                all_values.append(value)
            diff = None if value is None or avg is None else round(value - avg, 2)
            payload = {
                "raceDate": clean(row.get("race_date")),
                "meeting": clean(row.get("display_track") or row.get("track")),
                "raceNumber": clean(row.get("race_no") or row.get("race_number")),
                "raceKey": race_key,
                "runnerNumber": clean(row.get("runner_number") or row.get("saddlecloth") or row.get("horse_no")),
                "runnerName": clean(row.get("runner") or row.get("horse")),
                "normalizedRunnerName": clean(row.get("horse_canon") or row.get("horse_key")),
                "runnerId": clean(row.get("runner_id")),
                "value": value,
                "display": display(value),
                "version": VERSION if value is not None else None,
                "source": SOURCE if value is not None else None,
                "status": status,
                "rankInRace": ranks.get(id(row)) if not scratched and value is not None else None,
                "activeFieldSize": len(values),
                "fieldHigh": round(high, 2) if high is not None else None,
                "fieldAverage": round(avg, 2) if avg is not None else None,
                "differenceFromFieldAverage": diff,
                "recentChange": None,
                "trend": trend_for(value),
                "asAt": clean(row.get("built_at") or row.get("timestamp")) or generated,
            }
            json_rows.append(payload)
            output_rows.append(payload)

    distribution = stats(all_values, missing)
    summary_rows = [
        {"metric": key, "value": value}
        for key, value in distribution.items()
    ]
    distribution_rows = [{"bucket": "all_current_active", **distribution}]

    payload = {
        "schemaVersion": "EDGEIQ_EPI_CURRENT_RATING_V1",
        "generatedAt": generated,
        "source": SOURCE,
        "version": VERSION,
        "rules": {
            "activeField": "Scratchings excluded from rank, high and average.",
            "missing": "No zero/default/fallback is emitted when projected_rating_v5_2 is missing.",
            "scale": "EDGEiQ performance points.",
        },
        "runners": json_rows,
        "distribution": distribution,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    fieldnames = [
        "raceDate", "meeting", "raceNumber", "raceKey", "runnerNumber", "runnerName", "normalizedRunnerName", "runnerId",
        "value", "display", "version", "source", "status", "rankInRace", "activeFieldSize", "fieldHigh", "fieldAverage",
        "differenceFromFieldAverage", "recentChange", "trend", "asAt",
    ]
    write_csv(OUT_CSV, output_rows, fieldnames)
    write_csv(DIST_CSV, distribution_rows, ["bucket", "count", "missing", "min", "max", "mean", "median", "std", "p5", "p10", "p25", "p50", "p75", "p90", "p95"])
    write_csv(DIST_SUMMARY, summary_rows, ["metric", "value"])
    print(f"EPI_CURRENT_RATING_V1 runners={len(json_rows)} active_values={len(all_values)} missing={missing}")


if __name__ == "__main__":
    main()
