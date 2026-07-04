from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, classify_shape, entropy_ratio, format_float, hhi, mean, median_value, market_price, read_csv, write_csv


CANDIDATE = DATA / "edgeiq_probability_research_v5_compression_fix.csv"
RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
BASELINE_SUMMARY = DATA / "edgeiq_market_price_shape_baseline_summary_v1.csv"
OUT = DATA / "edgeiq_probability_research_v5_shape_audit.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_shape_summary.csv"


def num(value, fallback=0.0) -> float:
    try:
        raw = str(value or "").replace("$", "").replace("%", "").replace(",", "").strip()
        return float(raw) if raw else fallback
    except ValueError:
        return fallback


def main() -> None:
    candidate = read_csv(CANDIDATE)
    live_market = {(row.get("track", "").upper(), row.get("race_no", ""), row.get("horse", "").upper()): market_price(row) for row in read_csv(RUNNER_BOARD)}
    by_race: defaultdict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in candidate:
        by_race[(row.get("track", ""), row.get("race_no", ""))].append(row)

    audit = []
    counts = Counter()
    prod_favs = []
    cand_favs = []
    prod_top3s = []
    cand_top3s = []
    prod_entropy = []
    cand_entropy = []
    for key, field in sorted(by_race.items()):
        prod_prices = sorted([num(row.get("production_fair_price")) for row in field if num(row.get("production_fair_price")) > 0])
        cand_prices = sorted([num(row.get("candidate_fair_price_v5")) for row in field if num(row.get("candidate_fair_price_v5")) > 0])
        prod_probs = sorted([num(row.get("production_probability")) for row in field], reverse=True)
        cand_probs = sorted([num(row.get("candidate_probability_v5")) for row in field], reverse=True)
        market_prices = sorted([live_market.get((key[0].upper(), key[1], row.get("horse", "").upper())) or 0 for row in field])
        market_prices = [price for price in market_prices if price > 0]
        prod_fav = prod_prices[0] if prod_prices else 0
        cand_fav = cand_prices[0] if cand_prices else 0
        prod_top3 = sum(prod_probs[:3])
        cand_top3 = sum(cand_probs[:3])
        prod_ent = entropy_ratio(prod_probs)
        cand_ent = entropy_ratio(cand_probs)
        prod_class = classify_shape(prod_fav, prod_probs[0] if prod_probs else 0, prod_top3, prod_ent)
        cand_class = classify_shape(cand_fav, cand_probs[0] if cand_probs else 0, cand_top3, cand_ent)
        counts[f"production::{prod_class}"] += 1
        counts[f"candidate::{cand_class}"] += 1
        prod_favs.append(prod_fav)
        cand_favs.append(cand_fav)
        prod_top3s.append(prod_top3)
        cand_top3s.append(cand_top3)
        prod_entropy.append(prod_ent)
        cand_entropy.append(cand_ent)
        audit.append(
            {
                "track": key[0],
                "race_no": key[1],
                "field_size": len(field),
                "production_favourite_price": format_float(prod_fav, 2),
                "candidate_favourite_price": format_float(cand_fav, 2),
                "market_favourite_price": format_float(market_prices[0] if market_prices else 0, 2),
                "production_no_horse_under_3": "YES" if prod_fav >= 3 else "NO",
                "candidate_no_horse_under_3": "YES" if cand_fav >= 3 else "NO",
                "production_no_horse_under_4": "YES" if prod_fav >= 4 else "NO",
                "candidate_no_horse_under_4": "YES" if cand_fav >= 4 else "NO",
                "production_no_horse_under_5": "YES" if prod_fav >= 5 else "NO",
                "candidate_no_horse_under_5": "YES" if cand_fav >= 5 else "NO",
                "production_no_horse_under_6": "YES" if prod_fav >= 6 else "NO",
                "candidate_no_horse_under_6": "YES" if cand_fav >= 6 else "NO",
                "production_top3_probability": format_float(prod_top3, 4),
                "candidate_top3_probability": format_float(cand_top3, 4),
                "production_entropy": format_float(prod_ent, 4),
                "candidate_entropy": format_float(cand_ent, 4),
                "production_concentration_hhi": format_float(hhi(prod_probs), 4),
                "candidate_concentration_hhi": format_float(hhi(cand_probs), 4),
                "production_classification": prod_class,
                "candidate_classification": cand_class,
            }
        )

    baseline_summary = {row["metric"]: row["value"] for row in read_csv(BASELINE_SUMMARY)}
    improved = counts["candidate::COMPRESSED"] < counts["production::COMPRESSED"]
    overdone = counts["candidate::OVER_CONCENTRATED"] > counts["production::OVER_CONCENTRATED"] + 3
    verdict = "OVER_CORRECTED" if overdone else "IMPROVED_SHAPE" if improved else "NO_IMPROVEMENT"
    if not audit:
        verdict = "NOT_READY"
    summary = [
        {"metric": "race_rows", "value": len(audit)},
        {"metric": "production_no_horse_under_3", "value": sum(1 for row in audit if row["production_no_horse_under_3"] == "YES")},
        {"metric": "candidate_no_horse_under_3", "value": sum(1 for row in audit if row["candidate_no_horse_under_3"] == "YES")},
        {"metric": "production_no_horse_under_4", "value": sum(1 for row in audit if row["production_no_horse_under_4"] == "YES")},
        {"metric": "candidate_no_horse_under_4", "value": sum(1 for row in audit if row["candidate_no_horse_under_4"] == "YES")},
        {"metric": "production_no_horse_under_5", "value": sum(1 for row in audit if row["production_no_horse_under_5"] == "YES")},
        {"metric": "candidate_no_horse_under_5", "value": sum(1 for row in audit if row["candidate_no_horse_under_5"] == "YES")},
        {"metric": "production_no_horse_under_6", "value": sum(1 for row in audit if row["production_no_horse_under_6"] == "YES")},
        {"metric": "candidate_no_horse_under_6", "value": sum(1 for row in audit if row["candidate_no_horse_under_6"] == "YES")},
        {"metric": "production_favourite_average", "value": f"{mean(prod_favs):.2f}"},
        {"metric": "candidate_favourite_average", "value": f"{mean(cand_favs):.2f}"},
        {"metric": "production_favourite_median", "value": f"{median_value(prod_favs):.2f}"},
        {"metric": "candidate_favourite_median", "value": f"{median_value(cand_favs):.2f}"},
        {"metric": "production_top3_probability_average", "value": f"{mean(prod_top3s):.4f}"},
        {"metric": "candidate_top3_probability_average", "value": f"{mean(cand_top3s):.4f}"},
        {"metric": "production_entropy_average", "value": f"{mean(prod_entropy):.4f}"},
        {"metric": "candidate_entropy_average", "value": f"{mean(cand_entropy):.4f}"},
        {"metric": "production_classification::COMPRESSED", "value": counts["production::COMPRESSED"]},
        {"metric": "candidate_classification::COMPRESSED", "value": counts["candidate::COMPRESSED"]},
        {"metric": "production_classification::HEALTHY", "value": counts["production::HEALTHY"]},
        {"metric": "candidate_classification::HEALTHY", "value": counts["candidate::HEALTHY"]},
        {"metric": "production_classification::OVER_CONCENTRATED", "value": counts["production::OVER_CONCENTRATED"]},
        {"metric": "candidate_classification::OVER_CONCENTRATED", "value": counts["candidate::OVER_CONCENTRATED"]},
        {"metric": "historical_market_average_favourite_price", "value": baseline_summary.get("average_favourite_price", "")},
        {"metric": "historical_market_top3_probability_sum", "value": baseline_summary.get("average_market_top3_implied_probability_sum", "")},
        {"metric": "verdict", "value": verdict},
    ]
    write_csv(OUT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(audit)} rows)")


if __name__ == "__main__":
    main()
