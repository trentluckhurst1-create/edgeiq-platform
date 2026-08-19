from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, classify_shape, entropy_ratio, format_float, mean, median_value, read_csv, write_csv

SRC = DATA / "edgeiq_probability_research_v5_1_temperature.csv"
OUT = DATA / "edgeiq_probability_research_v5_1_shape_audit.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_1_shape_summary.csv"


def num(v):
    try:
        return float(str(v or "").replace("$", "").replace(",", ""))
    except ValueError:
        return 0.0


def stats(rows, prefix):
    prices = sorted([num(r[f"{prefix}_fair_price"]) for r in rows if num(r[f"{prefix}_fair_price"]) > 0])
    probs = sorted([num(r[f"{prefix}_probability"]) for r in rows], reverse=True)
    fav = prices[0] if prices else 0
    top3 = sum(probs[:3])
    ent = entropy_ratio(probs)
    return fav, top3, ent, classify_shape(fav, probs[0] if probs else 0, top3, ent)


def main():
    rows = read_csv(SRC)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["track"], row["race_no"])].append(row)
    audit = []
    favs = defaultdict(list)
    top3s = defaultdict(list)
    ents = defaultdict(list)
    counts = Counter()
    for key, race_rows in sorted(grouped.items()):
        prod_fav, prod_top3, prod_ent, prod_class = stats(race_rows, "production")
        v5_fav, v5_top3, v5_ent, v5_class = stats([dict(r, v5_candidate_probability=r.get("v5_candidate_probability", "0"), v5_candidate_fair_price=r.get("v5_candidate_fair_price", "0")) for r in race_rows], "v5_candidate")
        v51_fav, v51_top3, v51_ent, v51_class = stats(race_rows, "v5_1")
        for name, fav, top3, ent, cls in [("production", prod_fav, prod_top3, prod_ent, prod_class), ("v5", v5_fav, v5_top3, v5_ent, v5_class), ("v5_1", v51_fav, v51_top3, v51_ent, v51_class)]:
            favs[name].append(fav); top3s[name].append(top3); ents[name].append(ent); counts[f"{name}::{cls}"] += 1
        audit.append({"track": key[0], "race_no": key[1], "production_fav_price": format_float(prod_fav, 2), "v5_fav_price": format_float(v5_fav, 2), "v5_1_fav_price": format_float(v51_fav, 2), "production_top3_prob": format_float(prod_top3, 4), "v5_top3_prob": format_float(v5_top3, 4), "v5_1_top3_prob": format_float(v51_top3, 4), "production_entropy": format_float(prod_ent, 4), "v5_entropy": format_float(v5_ent, 4), "v5_1_entropy": format_float(v51_ent, 4), "production_classification": prod_class, "v5_classification": v5_class, "v5_1_classification": v51_class})
    over = counts["v5_1::OVER_CONCENTRATED"] > counts["v5::OVER_CONCENTRATED"] + 2
    if not audit:
        verdict = "NOT_READY"
    elif over:
        verdict = "OVER_CORRECTED"
    elif counts["v5_1::HEALTHY"] > counts["v5::HEALTHY"] and counts["v5_1::COMPRESSED"] <= counts["v5::COMPRESSED"]:
        verdict = "IMPROVED_OVER_V5"
    elif counts["v5_1::HEALTHY"] > counts["production::HEALTHY"]:
        verdict = "IMPROVED_OVER_PRODUCTION_ONLY"
    else:
        verdict = "NO_IMPROVEMENT"
    summary = [{"metric": "race_rows", "value": len(audit)}]
    for name in ["production", "v5", "v5_1"]:
        summary += [
            {"metric": f"{name}_compressed", "value": counts[f"{name}::COMPRESSED"]},
            {"metric": f"{name}_healthy", "value": counts[f"{name}::HEALTHY"]},
            {"metric": f"{name}_overconcentrated", "value": counts[f"{name}::OVER_CONCENTRATED"]},
            {"metric": f"{name}_avg_favourite_price", "value": f"{mean(favs[name]):.2f}"},
            {"metric": f"{name}_median_favourite_price", "value": f"{median_value(favs[name]):.2f}"},
            {"metric": f"{name}_no_horse_under_3", "value": sum(1 for v in favs[name] if v >= 3)},
            {"metric": f"{name}_no_horse_under_4", "value": sum(1 for v in favs[name] if v >= 4)},
            {"metric": f"{name}_no_horse_under_5", "value": sum(1 for v in favs[name] if v >= 5)},
            {"metric": f"{name}_no_horse_under_6", "value": sum(1 for v in favs[name] if v >= 6)},
            {"metric": f"{name}_top3_probability_avg", "value": f"{mean(top3s[name]):.4f}"},
            {"metric": f"{name}_entropy_avg", "value": f"{mean(ents[name]):.4f}"},
        ]
    summary.append({"metric": "verdict", "value": verdict})
    write_csv(OUT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(audit)} rows)")


if __name__ == "__main__":
    main()
