from collections import Counter, defaultdict

from edgeiq_pricing_research_common import (
    DATA,
    bucket_distance,
    bucket_field_size,
    bucket_price,
    entropy_ratio,
    hhi,
    market_price,
    mean,
    median_value,
    race_key,
    read_csv,
    text,
    write_csv,
)


SOURCES = [
    DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv",
    DATA / "model_result_review.csv",
    DATA / "race_results.csv",
]
OUT = DATA / "edgeiq_market_price_shape_baseline_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_market_price_shape_baseline_summary_v1.csv"


def row_price(row: dict[str, str]) -> float | None:
    return market_price(row)


def row_class(row: dict[str, str]) -> str:
    return text(row.get("race_class") or row.get("race_conditions") or "UNKNOWN").upper() or "UNKNOWN"


def main() -> None:
    source_used = ""
    rows = []
    for source in SOURCES:
        raw = [row for row in read_csv(source) if row_price(row) and race_key(row)[0] and race_key(row)[2]]
        if raw:
            rows = raw
            source_used = source.name
            break

    grouped_races: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped_races[race_key(row)].append(row)

    buckets: defaultdict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    fav_bucket_counts: Counter[str] = Counter()
    race_records = []
    for _, field in grouped_races.items():
        prices = sorted([row_price(row) or 0 for row in field if row_price(row)])
        if len(prices) < 3:
            continue
        fav = prices[0]
        implied = [1 / price for price in prices if price > 0]
        fav_bucket = bucket_price(fav)
        fav_bucket_counts[fav_bucket] += 1
        record = {
            "field_size": len(prices),
            "favourite_price": fav,
            "favourite_probability": 1 / fav,
            "top3_sum": sum(implied[:3]),
            "top5_sum": sum(implied[:5]),
            "concentration": hhi(implied),
            "entropy": entropy_ratio(implied),
        }
        key = (
            bucket_field_size(len(prices)),
            row_class(field[0]),
            bucket_distance(field[0].get("distance")),
            fav_bucket,
        )
        buckets[key].append(record)
        race_records.append(record)

    out = []
    for key, records in sorted(buckets.items()):
        favs = [float(row["favourite_price"]) for row in records]
        out.append(
            {
                "field_size_bucket": key[0],
                "race_class": key[1],
                "distance_bucket": key[2],
                "favourite_price_bucket": key[3],
                "race_count": len(records),
                "average_favourite_price": f"{mean(favs):.2f}",
                "median_favourite_price": f"{median_value(favs):.2f}",
                "favourite_probability": f"{mean([float(row['favourite_probability']) for row in records]):.4f}",
                "market_top3_implied_probability_sum": f"{mean([float(row['top3_sum']) for row in records]):.4f}",
                "market_top5_implied_probability_sum": f"{mean([float(row['top5_sum']) for row in records]):.4f}",
                "typical_concentration": f"{mean([float(row['concentration']) for row in records]):.4f}",
                "typical_entropy": f"{mean([float(row['entropy']) for row in records]):.4f}",
            }
        )

    summary = [
        {"metric": "source_file", "value": source_used},
        {"metric": "historical_race_rows_used", "value": len(race_records)},
        {"metric": "baseline_bucket_rows", "value": len(out)},
        {"metric": "average_favourite_price", "value": f"{mean([float(row['favourite_price']) for row in race_records]):.2f}"},
        {"metric": "median_favourite_price", "value": f"{median_value([float(row['favourite_price']) for row in race_records]):.2f}"},
        {"metric": "average_market_top3_implied_probability_sum", "value": f"{mean([float(row['top3_sum']) for row in race_records]):.4f}"},
        {"metric": "favourite_price_distribution::<2", "value": fav_bucket_counts["LT_2"]},
        {"metric": "favourite_price_distribution::2-3", "value": fav_bucket_counts["2_TO_3"]},
        {"metric": "favourite_price_distribution::3-4", "value": fav_bucket_counts["3_TO_4"]},
        {"metric": "favourite_price_distribution::4-5", "value": fav_bucket_counts["4_TO_5"]},
        {"metric": "favourite_price_distribution::5-6", "value": fav_bucket_counts["5_TO_6"]},
        {"metric": "favourite_price_distribution::6+", "value": fav_bucket_counts["6_PLUS"]},
    ]
    fields = list(out[0].keys()) if out else []
    write_csv(OUT, out, fields)
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
