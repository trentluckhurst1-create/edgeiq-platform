from __future__ import annotations

from collections import defaultdict
from statistics import mean

from edgeiq_results_common_v1 import DATA, first, has_value, now_iso, numeric_float, read_csv, write_csv


BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
BACKFILL = DATA / "edgeiq_projected_rating_backfill_v1.csv"


RATING_KEYS = ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH", "epi", "runner_rating"]


def load(path):
    return list(read_csv(path)) if path.exists() else []


def rating(row: dict[str, str]) -> float | None:
    return numeric_float(first(row, RATING_KEYS))


def price_anchor(row: dict[str, str], field_average: float) -> float | None:
    price = numeric_float(first(row, ["live_price", "market_price", "fixed_win", "ui_price", "tab_fixed_win"]))
    if price is None or price <= 0:
        return None
    # Research-only display anchor. This does not touch production pricing.
    implied = min(35.0, max(1.0, 100.0 / price))
    return max(45.0, min(95.0, field_average + ((implied - 10.0) * 0.35)))


def avg(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def main() -> None:
    rows = load(BOARD)
    by_class: dict[str, list[float]] = defaultdict(list)
    by_trainer: dict[str, list[float]] = defaultdict(list)
    by_jockey: dict[str, list[float]] = defaultdict(list)
    by_race: dict[str, list[float]] = defaultdict(list)
    all_ratings: list[float] = []

    for row in rows:
        value = rating(row)
        if value is None:
            continue
        all_ratings.append(value)
        by_class[first(row, ["race_class", "class"])].append(value)
        by_trainer[first(row, ["trainer"])].append(value)
        by_jockey[first(row, ["jockey", "rider"])].append(value)
        by_race[first(row, ["race_key"])].append(value)

    global_avg = avg(all_ratings) or 65.0
    output: list[dict[str, object]] = []
    for row in rows:
        if rating(row) is not None:
            continue
        race_avg = avg(by_race[first(row, ["race_key"])])
        class_avg = avg(by_class[first(row, ["race_class", "class"])])
        trainer_avg = avg(by_trainer[first(row, ["trainer"])])
        jockey_avg = avg(by_jockey[first(row, ["jockey", "rider"])])
        base = race_avg or class_avg or global_avg
        anchor = price_anchor(row, base)
        components = [value for value in [anchor, trainer_avg, jockey_avg, class_avg, race_avg, global_avg] if value is not None]
        backfill = round(mean(components), 2) if components else round(global_avg, 2)
        source_bits = []
        if anchor is not None:
            source_bits.append("MARKET_ANCHOR")
        if trainer_avg is not None:
            source_bits.append("TRAINER_PROFILE")
        if jockey_avg is not None:
            source_bits.append("JOCKEY_PROFILE")
        if class_avg is not None:
            source_bits.append("CLASS_AVERAGE")
        if race_avg is not None:
            source_bits.append("RACE_AVERAGE")
        if not source_bits:
            source_bits.append("GLOBAL_AVERAGE")

        output.append(
            {
                "race_date": first(row, ["race_date"]),
                "track": first(row, ["track"]),
                "race_no": first(row, ["race_no"]),
                "race_key": first(row, ["race_key"]),
                "saddlecloth": first(row, ["saddlecloth", "horse_no", "runner_no"]),
                "runner": first(row, ["horse", "runner", "runner_name"]),
                "runner_key": first(row, ["runner_key"]),
                "backfilled_projected_rating_v5_2": backfill,
                "backfill_source": "+".join(source_bits),
                "market_anchor_rating": anchor if anchor is not None else "",
                "trainer_profile_rating": trainer_avg if trainer_avg is not None else "",
                "jockey_profile_rating": jockey_avg if jockey_avg is not None else "",
                "class_average_rating": class_avg if class_avg is not None else "",
                "race_average_rating": race_avg if race_avg is not None else "",
                "production_pricing_changed": "NO",
                "v6_v6_1_rating_engine_changed": "NO",
                "built_at": now_iso(),
            }
        )

    fields = [
        "race_date",
        "track",
        "race_no",
        "race_key",
        "saddlecloth",
        "runner",
        "runner_key",
        "backfilled_projected_rating_v5_2",
        "backfill_source",
        "market_anchor_rating",
        "trainer_profile_rating",
        "jockey_profile_rating",
        "class_average_rating",
        "race_average_rating",
        "production_pricing_changed",
        "v6_v6_1_rating_engine_changed",
        "built_at",
    ]
    write_csv(BACKFILL, output, fields)

    backfill_by_key = {str(row["runner_key"]): row for row in output if row.get("runner_key")}
    changed = 0
    for row in rows:
        key = first(row, ["runner_key"])
        patch = backfill_by_key.get(key)
        if not patch or rating(row) is not None:
            continue
        row["projected_rating_v5_2"] = str(patch["backfilled_projected_rating_v5_2"])
        row["projection_band_v5_2"] = "BACKFILLED_DISPLAY"
        row["projection_confidence_v5_2"] = "LOW_BACKFILL"
        row["projected_rating_backfill_v1"] = str(patch["backfilled_projected_rating_v5_2"])
        row["projected_rating_backfill_source_v1"] = str(patch["backfill_source"])
        row["projected_rating_backfill_guardrail_v1"] = "DISPLAY_ONLY_NO_V6_OR_PRICING_CHANGE"
        changed += 1

    fieldnames = list(rows[0].keys()) if rows else []
    for extra in ["projected_rating_backfill_v1", "projected_rating_backfill_source_v1", "projected_rating_backfill_guardrail_v1"]:
        if extra not in fieldnames:
            fieldnames.append(extra)
    write_csv(BOARD, rows, fieldnames)
    print(f"Wrote {BACKFILL} ({len(output)} rows)")
    print(f"Updated {BOARD} ({changed} display backfills)")


if __name__ == "__main__":
    main()
