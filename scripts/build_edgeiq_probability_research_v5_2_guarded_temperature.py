from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, format_float, read_csv, write_csv

V51 = DATA / "edgeiq_probability_research_v5_1_temperature.csv"
FEATURES = DATA / "edgeiq_probability_temperature_features_v1.csv"
OUT = DATA / "edgeiq_probability_research_v5_2_guarded_temperature.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_2_guarded_temperature_summary.csv"
OUT_AUDIT = DATA / "edgeiq_probability_research_v5_2_guarded_temperature_audit.csv"


def key(row):
    return (row.get("track", ""), row.get("race_no", ""))


def num(value, fallback=0.0):
    try:
        return float(str(value or "").replace("$", "").replace(",", ""))
    except ValueError:
        return fallback


def top_cap(field_size, evidence, chaos):
    if evidence >= 0.75 and chaos <= 5.8:
        return 0.40
    if field_size >= 16:
        return 0.28
    if field_size >= 12:
        return 0.32
    return 0.36


def top3_cap(chaos):
    if chaos >= 7:
        return 0.58
    if chaos >= 6:
        return 0.64
    return 0.70


def main():
    features = {key(row): row for row in read_csv(FEATURES)}
    grouped = defaultdict(list)
    for row in read_csv(V51):
        grouped[key(row)].append(row)
    out, audit = [], []
    counts = Counter()
    for rkey, rows in sorted(grouped.items()):
        feat = features.get(rkey, {})
        field_size = len(rows)
        chaos = num(feat.get("chaos_index"), 5)
        evidence = num(feat.get("evidence_strength"), 0.4)
        gap = num(feat.get("rating_gap_top2"), 0)
        form_depth = num(feat.get("form_depth"), 0)
        probs = [num(r.get("v5_1_probability")) for r in rows]
        reasons = []
        cap1 = top_cap(field_size, evidence, chaos)
        cap3 = top3_cap(chaos)
        if form_depth < 2 or evidence < 0.55 or gap < 4 or chaos >= 6.8:
            blend = 0.35
            reasons.append("blended toward production due to guardrail triggers")
        else:
            blend = 0.15
        prod = [num(r.get("production_probability")) for r in rows]
        total_prod = sum(prod) or 1
        prod = [p / total_prod for p in prod]
        guarded = [(p * (1 - blend)) + (pp * blend) for p, pp in zip(probs, prod)]
        applied = False
        if guarded and max(guarded) > cap1:
            i = guarded.index(max(guarded))
            excess = guarded[i] - cap1
            guarded[i] = cap1
            others = [j for j in range(len(guarded)) if j != i]
            ot = sum(guarded[j] for j in others) or 1
            for j in others:
                guarded[j] += excess * guarded[j] / ot
            applied = True
            reasons.append(f"top runner cap {cap1:.2f}")
        order = sorted(range(len(guarded)), key=lambda i: guarded[i], reverse=True)
        top3 = sum(guarded[i] for i in order[:3])
        if top3 > cap3 and len(order) > 3:
            excess = top3 - cap3
            for i in order[:3]:
                guarded[i] -= excess * guarded[i] / top3
            rest_total = sum(guarded[i] for i in order[3:]) or 1
            for i in order[3:]:
                guarded[i] += excess * guarded[i] / rest_total
            applied = True
            reasons.append(f"top3 cap {cap3:.2f}")
        total = sum(guarded) or 1
        guarded = [p / total for p in guarded]
        for row, p in zip(rows, guarded):
            counts["YES" if applied else "NO"] += 1
            out.append({
                "track": row.get("track", ""),
                "race_no": row.get("race_no", ""),
                "horse": row.get("horse", ""),
                "production_probability": row.get("production_probability", ""),
                "v5_1_probability": row.get("v5_1_probability", ""),
                "v5_2_probability": format_float(p, 4),
                "production_fair_price": row.get("production_fair_price", ""),
                "v5_1_fair_price": row.get("v5_1_fair_price", ""),
                "v5_2_fair_price": format_float(1 / p if p else 0, 2),
                "temperature_band": row.get("temperature_band", ""),
                "guardrail_applied": "YES" if applied else "NO",
                "guardrail_reason": "; ".join(reasons) if reasons else "no guardrail required",
                "research_status": "RESEARCH_ONLY",
            })
        audit.append({"track": rkey[0], "race_no": rkey[1], "field_size": field_size, "chaos_index": format_float(chaos, 2), "evidence_strength": format_float(evidence, 4), "rating_gap_top2": format_float(gap, 2), "top_probability": format_float(max(guarded), 4), "top3_probability": format_float(sum(sorted(guarded, reverse=True)[:3]), 4), "guardrail_applied": "YES" if applied else "NO", "guardrail_reason": "; ".join(reasons) if reasons else "no guardrail required", "probability_sum": format_float(sum(guarded), 6)})
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, [{"metric": "runner_rows", "value": len(out)}, {"metric": "race_rows", "value": len(audit)}, {"metric": "production_pricing_changed", "value": "NO"}, {"metric": "guardrail_applied_runner_rows", "value": counts["YES"]}], ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
