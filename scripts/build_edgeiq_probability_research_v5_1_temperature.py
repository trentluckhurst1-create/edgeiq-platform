import math
from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, format_float, production_fair_price, production_probability, rating, read_csv, write_csv

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
FEATURES = DATA / "edgeiq_probability_temperature_features_v1.csv"
V5 = DATA / "edgeiq_probability_research_v5_compression_fix.csv"
OUT = DATA / "edgeiq_probability_research_v5_1_temperature.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_1_temperature_summary.csv"
OUT_AUDIT = DATA / "edgeiq_probability_research_v5_1_temperature_audit.csv"


def key(row):
    return (row.get("track", ""), row.get("race_no", ""))


def num(value, fallback=0.0):
    try:
        raw = str(value or "").replace("$", "").replace("%", "").replace(",", "").strip()
        return float(raw) if raw else fallback
    except ValueError:
        return fallback


def temp_value(band):
    return {
        "AGGRESSIVE_CONCENTRATION": 0.84,
        "BALANCED": 0.98,
        "CONSERVATIVE_FLATTER": 1.08,
        "NO_RECOMMENDATION": 1.00,
    }.get(band, 1.0)


def reason(band):
    return {
        "AGGRESSIVE_CONCENTRATION": "rating gap, evidence and chaos profile support concentration",
        "BALANCED": "mild sharpening with normal guardrails",
        "CONSERVATIVE_FLATTER": "chaos or thin evidence keeps distribution near production",
        "NO_RECOMMENDATION": "insufficient evidence for temperature adjustment",
    }.get(band, "neutral temperature")


def main():
    live = read_csv(RUNNER_BOARD)
    features = {key(row): row for row in read_csv(FEATURES)}
    v5 = {(row.get("track", ""), row.get("race_no", ""), row.get("horse", "")): row for row in read_csv(V5)}
    grouped = defaultdict(list)
    for row in live:
        if "SCRATCH" not in " ".join(str(row.get(k, "")).upper() for k in ["display_decision", "runner_status", "scratch_status", "is_scratched"]):
            grouped[key(row)].append(row)
    out, audit = [], []
    counts = Counter()
    for rkey, field in sorted(grouped.items()):
        feat = features.get(rkey, {})
        band = feat.get("recommended_temperature_band", "NO_RECOMMENDATION")
        t = temp_value(band)
        counts[band] += 1
        base_probs = [max(0.0001, production_probability(row) or 0.0001) for row in field]
        ratings = [rating(row) or 0 for row in field]
        max_rating = max(ratings) if ratings else 0
        scores = []
        for row, prob, rat in zip(field, base_probs, ratings):
            score = prob ** (1 / t)
            if band == "AGGRESSIVE_CONCENTRATION":
                score *= math.exp((rat - max_rating) / 8.0)
            elif band == "BALANCED":
                score *= math.exp((rat - max_rating) / 14.0)
            scores.append(score)
        total = sum(scores) or 1
        probs = [score / total for score in scores]
        cap = 0.38 if band == "AGGRESSIVE_CONCENTRATION" else 0.32 if band == "BALANCED" else 0.29
        if probs and max(probs) > cap:
            top = probs.index(max(probs))
            excess = probs[top] - cap
            probs[top] = cap
            others = [i for i in range(len(probs)) if i != top]
            other_total = sum(probs[i] for i in others) or 1
            for i in others:
                probs[i] += excess * probs[i] / other_total
        renorm = sum(probs) or 1
        probs = [p / renorm for p in probs]
        for row, p in zip(field, probs):
            v5row = v5.get((row.get("track", ""), row.get("race_no", ""), row.get("horse", "")), {})
            prod_prob = production_probability(row) or 0
            prod_price = production_fair_price(row) or 0
            out.append({
                "track": row.get("track", ""),
                "race_no": row.get("race_no", ""),
                "horse": row.get("horse", ""),
                "production_probability": format_float(prod_prob, 4),
                "production_fair_price": format_float(prod_price, 2),
                "v5_candidate_probability": v5row.get("candidate_probability_v5", ""),
                "v5_candidate_fair_price": v5row.get("candidate_fair_price_v5", ""),
                "v5_1_probability": format_float(p, 4),
                "v5_1_fair_price": format_float(1 / p if p else 0, 2),
                "temperature_band": band,
                "temperature_value": format_float(t, 2),
                "adjustment_reason": reason(band),
                "research_status": "RESEARCH_ONLY",
            })
        audit.append({"track": rkey[0], "race_no": rkey[1], "field_size": len(field), "temperature_band": band, "temperature_value": format_float(t, 2), "v5_1_probability_sum": format_float(sum(probs), 6), "top_probability": format_float(max(probs) if probs else 0, 4)})
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, [{"metric": "runner_rows", "value": len(out)}, {"metric": "race_rows", "value": len(audit)}, {"metric": "production_pricing_changed", "value": "NO"}] + [{"metric": f"band::{k}", "value": v} for k, v in counts.most_common()], ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
