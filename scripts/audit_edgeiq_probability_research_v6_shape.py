from collections import Counter, defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, classify_shape, entropy_ratio, mean, median_value, format_float

SRC = DATA / "edgeiq_probability_research_v6_candidate.csv"
OUT = DATA / "edgeiq_probability_research_v6_shape_audit.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v6_shape_summary.csv"


def num(v):
    try: return float(str(v or "").replace("$", "").replace(",", ""))
    except ValueError: return 0.0


def stats(rows, prefix):
    probs = sorted([num(r.get(f"{prefix}_probability")) for r in rows], reverse=True)
    prices = sorted([num(r.get(f"{prefix}_fair_price")) for r in rows if num(r.get(f"{prefix}_fair_price")) > 0])
    fav = prices[0] if prices else 0
    top3 = sum(probs[:3]); ent = entropy_ratio(probs)
    return fav, top3, ent, classify_shape(fav, probs[0] if probs else 0, top3, ent)


def main():
    grouped = defaultdict(list)
    for r in read_csv(SRC):
        grouped[(r["track"], r["race_no"])].append(r)
    prefixes = ["production", "v5", "v5_1", "v5_2", "v6"]
    counts, favs, top3s, ents = Counter(), defaultdict(list), defaultdict(list), defaultdict(list)
    audit = []
    for key, rows in sorted(grouped.items()):
        rec = {"track": key[0], "race_no": key[1], "field_size_bucket": rows[0].get("field_size_bucket", "")}
        for p in prefixes:
            fav, top3, ent, cls = stats(rows, p)
            rec[f"{p}_fav_price"] = format_float(fav, 2); rec[f"{p}_top3_prob"] = format_float(top3, 4); rec[f"{p}_entropy"] = format_float(ent, 4); rec[f"{p}_classification"] = cls
            counts[f"{p}::{cls}"] += 1; favs[p].append(fav); top3s[p].append(top3); ents[p].append(ent)
        audit.append(rec)
    summary = [{"metric": "race_rows", "value": len(audit)}]
    for p in prefixes:
        summary += [
            {"metric": f"{p}_compressed", "value": counts[f"{p}::COMPRESSED"]},
            {"metric": f"{p}_healthy", "value": counts[f"{p}::HEALTHY"]},
            {"metric": f"{p}_overconcentrated", "value": counts[f"{p}::OVER_CONCENTRATED"]},
            {"metric": f"{p}_avg_favourite_price", "value": f"{mean(favs[p]):.2f}"},
            {"metric": f"{p}_median_favourite_price", "value": f"{median_value(favs[p]):.2f}"},
            {"metric": f"{p}_no_horse_under_3", "value": sum(1 for v in favs[p] if v >= 3)},
            {"metric": f"{p}_no_horse_under_4", "value": sum(1 for v in favs[p] if v >= 4)},
            {"metric": f"{p}_no_horse_under_5", "value": sum(1 for v in favs[p] if v >= 5)},
            {"metric": f"{p}_no_horse_under_6", "value": sum(1 for v in favs[p] if v >= 6)},
            {"metric": f"{p}_top3_probability_avg", "value": f"{mean(top3s[p]):.4f}"},
            {"metric": f"{p}_entropy_avg", "value": f"{mean(ents[p]):.4f}"},
        ]
    if not audit:
        verdict = "NOT_READY"
    elif counts["v6::OVER_CONCENTRATED"] > 1:
        verdict = "OVER_CORRECTED"
    elif counts["v6::HEALTHY"] >= counts["v5_2::HEALTHY"] and counts["v6::COMPRESSED"] < counts["production::COMPRESSED"]:
        verdict = "PRODUCTION_CANDIDATE_SHAPE"
    elif counts["v6::COMPRESSED"] < counts["production::COMPRESSED"]:
        verdict = "RESEARCH_IMPROVEMENT"
    else:
        verdict = "NO_IMPROVEMENT"
    summary.append({"metric": "verdict", "value": verdict})
    write_csv(OUT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(audit)} rows)")


if __name__ == "__main__":
    main()
