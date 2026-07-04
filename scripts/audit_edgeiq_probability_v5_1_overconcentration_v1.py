from collections import Counter

from edgeiq_pricing_research_common import DATA, read_csv, write_csv

SHAPE = DATA / "edgeiq_probability_research_v5_1_shape_audit.csv"
FEATURES = DATA / "edgeiq_probability_temperature_features_v1.csv"
AUDIT = DATA / "edgeiq_probability_research_v5_1_temperature_audit.csv"
OUT = DATA / "edgeiq_probability_v5_1_overconcentration_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_v5_1_overconcentration_summary_v1.csv"


def key(row):
    return (row.get("track", ""), row.get("race_no", ""))


def num(value, fallback=0.0):
    try:
        return float(str(value or "").replace("$", "").replace(",", ""))
    except ValueError:
        return fallback


def root_cause(feature, audit):
    chaos = num(feature.get("chaos_index"))
    gap = num(feature.get("rating_gap_top2"))
    evidence = num(feature.get("evidence_strength"))
    form_depth = num(feature.get("form_depth"))
    band = audit.get("temperature_band", "")
    if band == "AGGRESSIVE_CONCENTRATION" and evidence < 0.7:
        return "TOO_AGGRESSIVE_TEMPERATURE"
    if chaos >= 6.8:
        return "CHAOS_UNDERWEIGHTED"
    if gap >= 8 and evidence < 0.6:
        return "RATING_GAP_OVERWEIGHTED"
    if evidence >= 0.6 and form_depth < 2:
        return "EVIDENCE_OVERSTATED"
    return "MARKET_SHAPE_MISMATCH"


def guardrail(cause):
    return {
        "TOO_AGGRESSIVE_TEMPERATURE": "raise temperature and lower top-runner cap unless evidence is exceptional",
        "CHAOS_UNDERWEIGHTED": "apply stricter top3 cap when chaos is moderate/high",
        "RATING_GAP_OVERWEIGHTED": "require evidence support before rating-gap sharpening",
        "EVIDENCE_OVERSTATED": "discount evidence when form depth is thin",
        "FIELD_SIZE_ERROR": "apply field-size bucket top-runner caps",
        "MARKET_SHAPE_MISMATCH": "cap top3 concentration and classify as guarded healthy only",
        "UNKNOWN": "manual review",
    }.get(cause, "manual review")


def main():
    features = {key(row): row for row in read_csv(FEATURES)}
    audits = {key(row): row for row in read_csv(AUDIT)}
    rows = []
    counts = Counter()
    for row in read_csv(SHAPE):
        if row.get("v5_1_classification") != "OVER_CONCENTRATED":
            continue
        f = features.get(key(row), {})
        a = audits.get(key(row), {})
        cause = root_cause(f, a)
        counts[cause] += 1
        top3 = num(row.get("v5_1_top3_prob"))
        fav = num(row.get("v5_1_fav_price"))
        why = "top3 probability too concentrated" if top3 > 0.72 else "favourite price/top probability too short for race shape"
        rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "field_size": a.get("field_size", ""),
            "temperature_band": a.get("temperature_band", ""),
            "temperature_value": a.get("temperature_value", ""),
            "favourite_candidate_price": f"{fav:.2f}",
            "top3_probability_sum": f"{top3:.4f}",
            "chaos_index": f.get("chaos_index", ""),
            "opportunity_score": f.get("opportunity_score", ""),
            "rating_gap_top2": f.get("rating_gap_top2", ""),
            "rating_gap_top3": f.get("rating_gap_top3", ""),
            "evidence_strength": f.get("evidence_strength", ""),
            "form_depth": f.get("form_depth", ""),
            "first_starter_count": f.get("first_starter_count", ""),
            "adjustment_reason": a.get("temperature_band", ""),
            "why_overconcentrated": why,
            "recommended_guardrail": guardrail(cause),
            "root_cause": cause,
        })
    write_csv(OUT, rows, list(rows[0].keys()) if rows else [])
    summary = [{"metric": "overconcentrated_races", "value": len(rows)}] + [{"metric": f"root_cause::{k}", "value": v} for k, v in counts.items()]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
