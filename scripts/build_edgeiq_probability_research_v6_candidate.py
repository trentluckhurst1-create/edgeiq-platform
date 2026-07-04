import math
from collections import defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, rating, production_probability, production_fair_price, bucket_field_size, clean, horse_key, race_key, runner_key, format_float, text

RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
V5 = DATA / "edgeiq_probability_research_v5_compression_fix.csv"
V51 = DATA / "edgeiq_probability_research_v5_1_temperature.csv"
V52 = DATA / "edgeiq_probability_research_v5_2_guarded_temperature.csv"
CHAOS = DATA / "edgeiq_chaos_index_v1.csv"
OPP = DATA / "edgeiq_opportunity_score_v1.csv"
SYN = DATA / "edgeiq_intelligence_synthesis_engine_v1.csv"
EVID = DATA / "edgeiq_evidence_strength_model_v2.csv"
CURVES = DATA / "edgeiq_field_size_concentration_curves_v1.csv"
OUT = DATA / "edgeiq_probability_research_v6_candidate.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v6_candidate_summary.csv"
OUT_AUDIT = DATA / "edgeiq_probability_research_v6_candidate_audit.csv"


def num(v, d=0.0):
    try:
        return float(str(v or "").replace("$", "").replace("%", "").replace(",", ""))
    except ValueError:
        return d


def is_scratched(row):
    return "SCRATCH" in " ".join(text(row.get(k)).upper() for k in ["display_decision", "runner_status", "scratch_status", "is_scratched"])


def simple_runner_map(path, pcol, pricecol):
    return {(clean(r.get("track")), text(r.get("race_no")), clean(r.get("horse"))): (r.get(pcol, ""), r.get(pricecol, "")) for r in read_csv(path)}


def temp_factor(evidence, synth, chaos, gap):
    factor = 1.0
    if evidence >= 70 and synth in {"EXCEPTIONAL_ALIGNMENT", "STRONG_ALIGNMENT"} and gap >= 5 and chaos < 7:
        factor += .32
    elif evidence >= 55 and gap >= 3 and chaos < 7:
        factor += .18
    if "CONFLICTING" in synth or chaos >= 7:
        factor -= .18
    return max(.85, min(1.38, factor))


def main():
    active = [r for r in read_csv(RUNNER) if not is_scratched(r)]
    by_race = defaultdict(list)
    for r in active:
        by_race[race_key(r)].append(r)
    v5 = simple_runner_map(V5, "candidate_probability_v5", "candidate_fair_price_v5")
    v51 = simple_runner_map(V51, "v5_1_probability", "v5_1_fair_price")
    v52 = simple_runner_map(V52, "v5_2_probability", "v5_2_fair_price")
    chaos = {race_key(r): r for r in read_csv(CHAOS)}
    opp = {race_key(r): r for r in read_csv(OPP)}
    syn = {runner_key(r): r for r in read_csv(SYN)}
    evid = {runner_key(r): r for r in read_csv(EVID)}
    curves = {r["field_size_bucket"]: r for r in read_csv(CURVES)}
    out, audit = [], []
    for rk, field in sorted(by_race.items()):
        ranked = sorted(field, key=lambda r: rating(r) or 0, reverse=True)
        ratings = [rating(r) or 0 for r in ranked]
        top_rating = ratings[0] if ratings else 0
        min_rating = min(ratings) if ratings else 0
        gap12 = ratings[0] - ratings[1] if len(ratings) > 1 else 0
        bucket = bucket_field_size(len(field))
        curve = curves.get(bucket, {})
        top_cap = num(curve.get("healthy_max_top_prob"), .34) or .34
        top3_cap = min(.70, num(str(curve.get("healthy_top3_range", "0-0")).split("-")[-1], .64) or .64)
        cidx = num(chaos.get(rk, {}).get("chaos_index"), 5)
        if cidx >= 7:
            top_cap = min(top_cap, .30); top3_cap = min(top3_cap, .58)
        raw = []
        explanations = []
        for r in ranked:
            ev = num(evid.get(runner_key(r), {}).get("evidence_strength_score"), 40)
            sb = syn.get(runner_key(r), {}).get("confidence_band", "INSUFFICIENT_EVIDENCE")
            gap_top = top_rating - (rating(r) or 0)
            factor = temp_factor(ev, sb, cidx, gap12)
            score = math.exp(((rating(r) or min_rating) - top_rating) / max(5.5, 10.5 / factor))
            score *= .75 + ev / 100 * .5
            if "CONFLICTING" in sb:
                score *= .88
            raw.append(score)
            explanations.append((ev, sb, factor, gap_top))
        total = sum(raw) or 1
        probs = [s / total for s in raw]
        guardrails = []
        if probs and max(probs) > top_cap:
            i = probs.index(max(probs)); excess = probs[i] - top_cap; probs[i] = top_cap
            rest = [j for j in range(len(probs)) if j != i]; rt = sum(probs[j] for j in rest) or 1
            for j in rest: probs[j] += excess * probs[j] / rt
            guardrails.append("top runner cap")
        order = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
        top3 = sum(probs[i] for i in order[:3])
        if top3 > top3_cap and len(order) > 3:
            excess = top3 - top3_cap
            for i in order[:3]: probs[i] -= excess * probs[i] / top3
            rest = order[3:]; rt = sum(probs[i] for i in rest) or 1
            for i in rest: probs[i] += excess * probs[i] / rt
            guardrails.append("top3 cap")
        total = sum(probs) or 1
        probs = [p / total for p in probs]
        for idx, (r, p, ex) in enumerate(zip(ranked, probs, explanations), 1):
            k = (clean(r.get("track")), text(r.get("race_no")), clean(r.get("horse")))
            ev, sb, factor, gap_top = ex
            out.append({
                "track": text(r.get("track")), "race_no": text(r.get("race_no")), "horse": text(r.get("horse")),
                "production_probability": format_float(production_probability(r), 4), "production_fair_price": format_float(production_fair_price(r), 2),
                "v5_probability": v5.get(k, ("", ""))[0], "v5_fair_price": v5.get(k, ("", ""))[1],
                "v5_1_probability": v51.get(k, ("", ""))[0], "v5_1_fair_price": v51.get(k, ("", ""))[1],
                "v5_2_probability": v52.get(k, ("", ""))[0], "v5_2_fair_price": v52.get(k, ("", ""))[1],
                "v6_probability": format_float(p, 4), "v6_fair_price": format_float(1 / p if p else 0, 2),
                "rating": format_float(rating(r), 2), "rating_rank": idx, "rating_gap_to_top": format_float(gap_top, 2),
                "field_size_bucket": bucket, "chaos_index": format_float(cidx, 2), "opportunity_score": format_float(num(opp.get(rk, {}).get("opportunity_score")), 2),
                "evidence_strength_score": format_float(ev, 1), "synthesis_band": sb, "temperature_band": "EVIDENCE_GATED",
                "concentration_factor": format_float(factor, 3), "guardrail_applied": "YES" if guardrails else "NO",
                "pricing_explanation": f"rating/evidence concentration; synthesis={sb}; guardrails={';'.join(guardrails) or 'none'}",
                "research_status": "RESEARCH_ONLY",
            })
        audit.append({"race_date": rk[0], "track": text(field[0].get("track")), "race_no": rk[2], "field_size": len(field), "field_size_bucket": bucket, "top_probability": format_float(max(probs), 4), "top3_probability": format_float(sum(sorted(probs, reverse=True)[:3]), 4), "probability_sum": format_float(sum(probs), 6), "guardrails": ";".join(guardrails) or "none"})
    summary = [{"metric": "runner_rows", "value": len(out)}, {"metric": "race_rows", "value": len(audit)}, {"metric": "production_pricing_changed", "value": "NO"}, {"metric": "guardrailed_races", "value": sum(1 for a in audit if a["guardrails"] != "none")}]
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
