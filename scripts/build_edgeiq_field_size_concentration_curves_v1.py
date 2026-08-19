from collections import Counter, defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, bucket_field_size, bucket_price, mean, median_value

SPINE = DATA / "edgeiq_pricing_replay_spine_v1.csv"
OUT = DATA / "edgeiq_field_size_concentration_curves_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_field_size_concentration_curves_v1_summary.csv"


def num(v):
    try:
        return float(str(v or "").replace("$", "").replace(",", ""))
    except ValueError:
        return 0.0


def pct(values, q):
    if not values:
        return 0.0
    vals = sorted(values)
    idx = min(len(vals) - 1, max(0, round((len(vals) - 1) * q)))
    return vals[idx]


def main():
    races = defaultdict(list)
    for row in read_csv(SPINE):
        races[(row["race_date"], row["track"], row["race_no"])].append(row)
    buckets = defaultdict(list)
    fav_dist = Counter()
    for _, rows in races.items():
        prices = sorted([num(r.get("sp_price") or r.get("market_price")) for r in rows if num(r.get("sp_price") or r.get("market_price")) > 0])
        if len(prices) < 3:
            continue
        fav = prices[0]
        implied = [1 / p for p in prices if p > 0]
        bucket = bucket_field_size(len(prices))
        buckets[bucket].append({"fav": fav, "top": implied[0], "top3": sum(implied[:3])})
        fav_dist[bucket_price(fav)] += 1
    out = []
    for bucket, records in sorted(buckets.items()):
        favs = [r["fav"] for r in records]
        tops = [r["top"] for r in records]
        top3 = [r["top3"] for r in records]
        confidence = "HIGH" if len(records) >= 100 else "MEDIUM" if len(records) >= 30 else "LOW"
        out.append({
            "field_size_bucket": bucket,
            "race_count": len(records),
            "median_market_fav_price": f"{median_value(favs):.2f}",
            "avg_market_fav_price": f"{mean(favs):.2f}",
            "median_top3_implied_prob": f"{median_value(top3):.4f}",
            "avg_top3_implied_prob": f"{mean(top3):.4f}",
            "fav_price_p25": f"{pct(favs, .25):.2f}",
            "fav_price_p75": f"{pct(favs, .75):.2f}",
            "healthy_min_top_prob": f"{max(0.12, pct(tops, .25) * 0.72):.4f}",
            "healthy_max_top_prob": f"{min(0.42, pct(tops, .75) * 0.82):.4f}",
            "healthy_top3_range": f"{pct(top3, .25) * 0.72:.4f}-{min(.72, pct(top3, .75) * .82):.4f}",
            "confidence_band": confidence,
        })
    summary = [{"metric": "field_size_bucket_rows", "value": len(out)}, {"metric": "source_races", "value": sum(len(v) for v in buckets.values())}]
    summary += [{"metric": f"fav_price_distribution::{k}", "value": v} for k, v in sorted(fav_dist.items())]
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
