import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
HISTORY_DETAIL = DATA / "edgeiq_runner_history_detail_v1.csv"
RUNNER_HISTORY = DATA / "runner_form_history.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_fallback_engine_v1.csv"

OUT = DATA / "edgeiq_chaos_index_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_chaos_index_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_chaos_index_v1_audit.csv"


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


def horse(row: dict[str, str]) -> str:
    return text(row.get("horse") or row.get("runner") or row.get("runner_name"))


def is_scratched(row: dict[str, str]) -> bool:
    blob = " ".join(text(row.get(key)).upper() for key in ["display_decision", "runner_status", "scratch_status", "is_scratched"])
    return "SCRATCH" in blob or text(row.get("is_scratched")).upper() in {"YES", "TRUE", "1", "Y"}


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (race_date(row), clean(row.get("track")), race_no(row))


def history_key(row: dict[str, str]) -> str:
    return horse_clean(row.get("horse_key") or horse(row))


def clamp(value: float, low = 0.0, high = 10.0) -> float:
    return max(low, min(high, value))


def band(score: float) -> str:
    if score >= 7.5:
        return "HIGH CHAOS"
    if score >= 5:
        return "TACTICAL CHAOS"
    if score >= 2.5:
        return "MODERATE CHAOS"
    return "LOW CHAOS"


def main() -> None:
    runners = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    race_shapes = {race_key(row): row for row in read_csv(RACE_SHAPE)}

    history_counts: defaultdict[str, int] = defaultdict(int)
    for source in [read_csv(HISTORY_DETAIL), read_csv(RUNNER_HISTORY)]:
        for row in source:
            key = history_key(row)
            if key:
                history_counts[key] += 1

    by_race: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in runners:
        by_race[race_key(row)].append(row)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, object]] = []
    audit: list[dict[str, object]] = []
    for key, field in sorted(by_race.items()):
        field_size = len(field)
        first_starters = sum(1 for row in field if history_counts[history_key(row)] == 0)
        exposed = sum(1 for row in field if history_counts[history_key(row)] >= 3)
        shape = race_shapes.get(key, {})

        pace_pressure = num(shape.get("early_pressure_score")) or 0
        pace_uncertainty = clamp(abs(pace_pressure - 50) / 5) if pace_pressure > 15 else clamp((15 - pace_pressure) / 2)

        prices = [num(row.get("live_price") or row.get("tab_fixed_win")) for row in field]
        implied = [1 / price for price in prices if price and price > 1]
        market_concentration = max(implied) / sum(implied) if implied else 0
        market_concentration_score = clamp((1 - market_concentration) * 10)

        ratings = [num(row.get("projected_rating_V6_1_RESEARCH") or row.get("projected_rating_v5_2") or row.get("total_rating_points")) for row in field]
        ratings = [value for value in ratings if value is not None and value > 0]
        if len(ratings) >= 2:
            rating_range = max(ratings) - min(ratings)
            rating_compression = clamp(10 - rating_range / 4)
        else:
            rating_compression = 5

        first_starter_score = clamp((first_starters / max(field_size, 1)) * 10)
        exposed_score = clamp(10 - (exposed / max(field_size, 1)) * 10)
        score = clamp(
            first_starter_score * 0.22
            + exposed_score * 0.18
            + pace_uncertainty * 0.2
            + market_concentration_score * 0.2
            + rating_compression * 0.2
        )

        rows.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "field_size": field_size,
                "chaos_index": f"{score:.2f}",
                "chaos_band": band(score),
                "first_starters": first_starters,
                "exposed_form_runners": exposed,
                "pace_uncertainty_score": f"{pace_uncertainty:.2f}",
                "market_concentration_score": f"{market_concentration_score:.2f}",
                "rating_compression_score": f"{rating_compression:.2f}",
                "built_at": built_at,
            }
        )
        audit.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "rating_values_used": len(ratings),
                "market_prices_used": len(implied),
                "race_shape_found": "YES" if bool(shape) else "NO",
            }
        )

    write_csv(OUT, rows, ["race_date", "track", "race_no", "field_size", "chaos_index", "chaos_band", "first_starters", "exposed_form_runners", "pace_uncertainty_score", "market_concentration_score", "rating_compression_score", "built_at"])
    write_csv(OUT_AUDIT, audit, ["race_date", "track", "race_no", "rating_values_used", "market_prices_used", "race_shape_found"])
    summary = [
        {"metric": "race_rows", "value": len(rows)},
        {"metric": "avg_chaos_index", "value": f"{sum(float(row['chaos_index']) for row in rows) / max(len(rows), 1):.2f}"},
        {"metric": "high_chaos_races", "value": sum(1 for row in rows if str(row["chaos_band"]) == "HIGH CHAOS")},
    ]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
