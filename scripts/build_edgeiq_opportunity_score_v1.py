import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_fallback_engine_v1.csv"
HIDDEN_PERFORMANCE = DATA / "edgeiq_current_hidden_gem_feed_v1_1.csv"
CHAOS = DATA / "edgeiq_chaos_index_v1.csv"

OUT = DATA / "edgeiq_opportunity_score_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_opportunity_score_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_opportunity_score_v1_audit.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def horse_clean(value: object) -> str:
    raw = text(value).upper()
    while "(" in raw and ")" in raw:
        start = raw.find("(")
        end = raw.find(")", start)
        if end < 0:
            break
        raw = raw[:start] + raw[end + 1 :]
    return clean(raw)


def num(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def race_date(row: dict[str, str]) -> str:
    return text(row.get("current_race_date") or row.get("race_date") or row.get("meeting_date") or row.get("date"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("race_number") or row.get("race"))


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (race_date(row), clean(row.get("track")), race_no(row))


def runner_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (clean(row.get("track")), race_no(row), horse_clean(row.get("horse_key") or row.get("horse")))


def is_scratched(row: dict[str, str]) -> bool:
    blob = " ".join(text(row.get(key)).upper() for key in ["display_decision", "runner_status", "scratch_status", "is_scratched"])
    return "SCRATCH" in blob or text(row.get("is_scratched")).upper() in {"YES", "TRUE", "1", "Y"}


def clamp(value: float, low = 0.0, high = 10.0) -> float:
    return max(low, min(high, value))


def band(score: float) -> str:
    if score >= 7.5:
        return "HIGH OPPORTUNITY"
    if score >= 5:
        return "LIVE OPPORTUNITY"
    if score >= 2.5:
        return "TACTICAL INTEREST"
    return "LOW OPPORTUNITY"


def percentile(value: float, values: list[float]) -> float:
    if not values:
        return 0.0
    below = sum(1 for item in values if item < value)
    equal = sum(1 for item in values if item == value)
    return ((below + (equal * 0.5)) / len(values)) * 100


def main() -> None:
    runners = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    shapes = {race_key(row): row for row in read_csv(RACE_SHAPE)}
    hidden = {runner_key(row): row for row in read_csv(HIDDEN_PERFORMANCE)}
    chaos = {race_key(row): row for row in read_csv(CHAOS)}

    by_race: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in runners:
        by_race[race_key(row)].append(row)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    raw_rows: list[dict[str, object]] = []
    audit: list[dict[str, object]] = []
    for key, field in sorted(by_race.items()):
        field_size = len(field)
        edges = [abs(num(row.get("edge_pct") or row.get("ui_edge_pct") or row.get("display_edge_pct")) or 0) for row in field]
        market_disagreement = clamp((sum(edges) / max(len(edges), 1)) / 12)

        chaos_score = num((chaos.get(key) or {}).get("chaos_index")) or 0
        shape = shapes.get(key, {})
        pressure = num(shape.get("early_pressure_score")) or 0
        pace_uncertainty = clamp(abs(pressure - 50) / 5) if pressure > 15 else clamp((15 - pressure) / 2)

        hidden_count = sum(
            1
            for row in field
            if text((hidden.get(runner_key(row)) or {}).get("actionable_watch_flag")).upper() == "YES"
            or text((hidden.get(runner_key(row)) or {}).get("historical_watch_flag")).upper() == "YES"
        )
        hidden_score = clamp((hidden_count / max(field_size, 1)) * 10)

        confidences = [num(row.get("confidence_score") or row.get("total_rating_points")) for row in field]
        confidences = [value for value in confidences if value is not None]
        if len(confidences) >= 2:
            mean = sum(confidences) / len(confidences)
            dispersion = (sum((value - mean) ** 2 for value in confidences) / len(confidences)) ** 0.5
            confidence_dispersion = clamp(dispersion / 5)
        else:
            confidence_dispersion = 5

        field_size_score = clamp((field_size - 6) / 1.4)
        raw_score = clamp(
            market_disagreement * 0.24
            + chaos_score * 0.22
            + hidden_score * 0.16
            + confidence_dispersion * 0.16
            + pace_uncertainty * 0.12
            + field_size_score * 0.1
        )
        raw_rows.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "field_size": field_size,
                "raw_opportunity_score": raw_score,
                "market_disagreement_score": f"{market_disagreement:.2f}",
                "chaos_score": f"{chaos_score:.2f}",
                "hidden_performance_score": f"{hidden_score:.2f}",
                "confidence_dispersion_score": f"{confidence_dispersion:.2f}",
                "pace_uncertainty_score": f"{pace_uncertainty:.2f}",
                "field_size_score": f"{field_size_score:.2f}",
                "built_at": built_at,
            }
        )
        audit.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "hidden_performance_runners": hidden_count,
                "field_size": field_size,
                "chaos_row_found": "YES" if key in chaos else "NO",
                "race_shape_found": "YES" if key in shapes else "NO",
            }
        )

    raw_scores = [float(row["raw_opportunity_score"]) for row in raw_rows]
    low = min(raw_scores, default=0.0)
    high = max(raw_scores, default=0.0)
    rows: list[dict[str, object]] = []
    for row in raw_rows:
        raw_score = float(row["raw_opportunity_score"])
        if high > low:
            calibrated_score = clamp(((raw_score - low) / (high - low)) * 10)
        else:
            calibrated_score = raw_score
        rank = percentile(raw_score, raw_scores)
        score = calibrated_score
        row["raw_opportunity_score"] = f"{raw_score:.2f}"
        row["opportunity_score"] = f"{score:.2f}"
        row["opportunity_percentile"] = f"{rank:.1f}"
        row["opportunity_band"] = band(score)
        rows.append(row)

    write_csv(OUT, rows, ["race_date", "track", "race_no", "field_size", "opportunity_score", "opportunity_band", "opportunity_percentile", "raw_opportunity_score", "market_disagreement_score", "chaos_score", "hidden_performance_score", "confidence_dispersion_score", "pace_uncertainty_score", "field_size_score", "built_at"])
    write_csv(OUT_AUDIT, audit, ["race_date", "track", "race_no", "hidden_performance_runners", "field_size", "chaos_row_found", "race_shape_found"])
    summary = [
        {"metric": "race_rows", "value": len(rows)},
        {"metric": "avg_opportunity_score", "value": f"{sum(float(row['opportunity_score']) for row in rows) / max(len(rows), 1):.2f}"},
        {"metric": "high_opportunity_races", "value": sum(1 for row in rows if str(row["opportunity_band"]) == "HIGH OPPORTUNITY")},
        {"metric": "score_calibration", "value": "MIN_MAX_BY_ACTIVE_RACE_SET"},
        {"metric": "raw_score_min", "value": f"{low:.2f}"},
        {"metric": "raw_score_max", "value": f"{high:.2f}"},
    ]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
