from collections import Counter

from edgeiq_pricing_research_common import (
    DATA,
    by_race,
    classify_shape,
    confidence_score,
    entropy_ratio,
    format_float,
    hhi,
    market_price,
    production_fair_price,
    production_probability,
    rating,
    read_csv,
    is_scratched,
    text,
    write_csv,
)


RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_current_price_shape_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_current_price_shape_summary_v1.csv"


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    rows: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    for key, field in sorted(by_race(active).items()):
        priced = sorted([(production_fair_price(row) or 0, row) for row in field if production_fair_price(row)], key=lambda item: item[0])
        probs = sorted([production_probability(row) or 0 for row in field], reverse=True)
        ratings = sorted([rating(row) or 0 for row in field], reverse=True)
        market_prices = sorted([market_price(row) or 0 for row in field if market_price(row)])
        fav = priced[0][0] if priced else 0
        second = priced[1][0] if len(priced) > 1 else 0
        third = priced[2][0] if len(priced) > 2 else 0
        top_prob = probs[0] if probs else 0
        top3 = sum(probs[:3])
        top5 = sum(probs[:5])
        ent = entropy_ratio(probs)
        conc = hhi(probs)
        market_top3_spread = (market_prices[2] - market_prices[0]) if len(market_prices) >= 3 else 0
        classification = classify_shape(fav, top_prob, top3, ent)
        counts[classification] += 1
        no_under = {level: fav >= level if fav else True for level in [3, 4, 5, 6]}
        for level, value in no_under.items():
            if value:
                flags[f"no_under_{level}"] += 1
        top_runner = priced[0][1] if priced else field[0]
        rows.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "field_size": len(field),
                "favourite_edgeiq_price": format_float(fav, 2),
                "second_favourite_edgeiq_price": format_float(second, 2),
                "third_favourite_edgeiq_price": format_float(third, 2),
                "top_probability": format_float(top_prob, 4),
                "top3_probability_sum": format_float(top3, 4),
                "top5_probability_sum": format_float(top5, 4),
                "entropy": format_float(ent, 4),
                "concentration_hhi": format_float(conc, 4),
                "rating_gap_rank1_rank2": format_float((ratings[0] - ratings[1]) if len(ratings) > 1 else 0, 2),
                "rating_gap_rank1_rank3": format_float((ratings[0] - ratings[2]) if len(ratings) > 2 else 0, 2),
                "confidence_of_top_runner": format_float(confidence_score(top_runner), 1),
                "market_favourite_price": format_float(market_prices[0] if market_prices else 0, 2),
                "market_top3_price_spread": format_float(market_top3_spread, 2),
                "classification": classification,
                "no_runner_under_3": "YES" if no_under[3] else "NO",
                "no_runner_under_4": "YES" if no_under[4] else "NO",
                "no_runner_under_5": "YES" if no_under[5] else "NO",
                "no_runner_under_6": "YES" if no_under[6] else "NO",
            }
        )

    summary = [
        {"metric": "race_rows", "value": len(rows)},
        {"metric": "active_runner_rows", "value": len(active)},
        {"metric": "no_runner_under_3", "value": flags["no_under_3"]},
        {"metric": "no_runner_under_4", "value": flags["no_under_4"]},
        {"metric": "no_runner_under_5", "value": flags["no_under_5"]},
        {"metric": "no_runner_under_6", "value": flags["no_under_6"]},
        {"metric": "classification::COMPRESSED", "value": counts["COMPRESSED"]},
        {"metric": "classification::HEALTHY", "value": counts["HEALTHY"]},
        {"metric": "classification::OVER_CONCENTRATED", "value": counts["OVER_CONCENTRATED"]},
        {"metric": "classification::UNKNOWN", "value": counts["UNKNOWN"]},
    ]
    fields = list(rows[0].keys()) if rows else []
    write_csv(OUT, rows, fields)
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
