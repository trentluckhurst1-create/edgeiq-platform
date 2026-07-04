from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, classify_shape, entropy_ratio, format_float, mean, median_value, read_csv, write_csv

V52 = DATA / "edgeiq_probability_research_v5_2_guarded_temperature.csv"
V5 = DATA / "edgeiq_probability_research_v5_compression_fix.csv"
OUT = DATA / "edgeiq_probability_research_v5_2_shape_audit.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_2_shape_summary.csv"


def num(v):
    try:
        return float(str(v or "").replace("$", "").replace(",", ""))
    except ValueError:
        return 0.0


def stats(rows, pcol, pricecol):
    probs = sorted([num(r.get(pcol)) for r in rows], reverse=True)
    prices = sorted([num(r.get(pricecol)) for r in rows if num(r.get(pricecol)) > 0])
    fav = prices[0] if prices else 0
    top3 = sum(probs[:3])
    ent = entropy_ratio(probs)
    return fav, top3, ent, classify_shape(fav, probs[0] if probs else 0, top3, ent)


def main():
    v5_lookup = {(r.get("track", ""), r.get("race_no", ""), r.get("horse", "")): r for r in read_csv(V5)}
    grouped = defaultdict(list)
    for row in read_csv(V52):
        v5 = v5_lookup.get((row.get("track", ""), row.get("race_no", ""), row.get("horse", "")), {})
        row["v5_probability"] = v5.get("candidate_probability_v5", "")
        row["v5_fair_price"] = v5.get("candidate_fair_price_v5", "")
        grouped[(row.get("track", ""), row.get("race_no", ""))].append(row)
    audit, counts = [], Counter()
    favs, top3s, ents = defaultdict(list), defaultdict(list), defaultdict(list)
    cols = {
        "production": ("production_probability", "production_fair_price"),
        "v5": ("v5_probability", "v5_fair_price"),
        "v5_1": ("v5_1_probability", "v5_1_fair_price"),
        "v5_2": ("v5_2_probability", "v5_2_fair_price"),
    }
    for key, rows in sorted(grouped.items()):
        rec = {"track": key[0], "race_no": key[1]}
        for name, (pcol, pricecol) in cols.items():
            fav, top3, ent, cls = stats(rows, pcol, pricecol)
            rec[f"{name}_fav_price"] = format_float(fav, 2)
            rec[f"{name}_top3_prob"] = format_float(top3, 4)
            rec[f"{name}_entropy"] = format_float(ent, 4)
            rec[f"{name}_classification"] = cls
            counts[f"{name}::{cls}"] += 1
            favs[name].append(fav); top3s[name].append(top3); ents[name].append(ent)
        audit.append(rec)
    if not audit:
        verdict = "NOT_READY"
    elif counts["v5_2::OVER_CONCENTRATED"] < counts["v5_1::OVER_CONCENTRATED"] and counts["v5_2::HEALTHY"] >= counts["v5::HEALTHY"]:
        verdict = "BETTER_THAN_V5_1"
    elif counts["v5_2::OVER_CONCENTRATED"] < counts["v5_1::OVER_CONCENTRATED"]:
        verdict = "SAFER_BUT_WEAKER"
    elif counts["v5_2::HEALTHY"] < counts["v5::HEALTHY"]:
        verdict = "OVER_GUARDED"
    else:
        verdict = "NO_IMPROVEMENT"
    summary = [{"metric": "race_rows", "value": len(audit)}]
    for name in cols:
        summary += [
            {"metric": f"{name}_compressed", "value": counts[f"{name}::COMPRESSED"]},
            {"metric": f"{name}_healthy", "value": counts[f"{name}::HEALTHY"]},
            {"metric": f"{name}_overconcentrated", "value": counts[f"{name}::OVER_CONCENTRATED"]},
            {"metric": f"{name}_avg_favourite_price", "value": f"{mean(favs[name]):.2f}"},
            {"metric": f"{name}_median_favourite_price", "value": f"{median_value(favs[name]):.2f}"},
            {"metric": f"{name}_no_runner_under_3", "value": sum(1 for v in favs[name] if v >= 3)},
            {"metric": f"{name}_no_runner_under_4", "value": sum(1 for v in favs[name] if v >= 4)},
            {"metric": f"{name}_no_runner_under_5", "value": sum(1 for v in favs[name] if v >= 5)},
            {"metric": f"{name}_no_runner_under_6", "value": sum(1 for v in favs[name] if v >= 6)},
            {"metric": f"{name}_top3_probability_avg", "value": f"{mean(top3s[name]):.4f}"},
            {"metric": f"{name}_entropy_avg", "value": f"{mean(ents[name]):.4f}"},
        ]
    summary.append({"metric": "verdict", "value": verdict})
    write_csv(OUT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(audit)} rows)")


if __name__ == "__main__":
    main()
