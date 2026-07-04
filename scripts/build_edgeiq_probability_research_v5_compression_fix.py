import math
from collections import Counter

from edgeiq_pricing_research_common import (
    DATA,
    by_race,
    clean,
    confidence_score,
    format_float,
    horse_key,
    production_fair_price,
    production_probability,
    race_key,
    rating,
    read_csv,
    is_scratched,
    text,
    write_csv,
)


RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
DNA = DATA / "edgeiq_runner_dna_v6_2.csv"
FORM = DATA / "edgeiq_form_intelligence_v2.csv"
CAMPAIGN = DATA / "edgeiq_campaign_intelligence_engine_v1_1.csv"
CONNECTION = DATA / "edgeiq_connection_intelligence_v2_1.csv"
CHAOS = DATA / "edgeiq_chaos_index_v1.csv"
OPPORTUNITY = DATA / "edgeiq_opportunity_score_v1.csv"
OUT = DATA / "edgeiq_probability_research_v5_compression_fix.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_compression_fix_summary.csv"
OUT_AUDIT = DATA / "edgeiq_probability_research_v5_compression_fix_audit.csv"


def sidecar_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (text(row.get("current_race_date") or row.get("race_date")), clean(row.get("track")), text(row.get("race_no")), horse_key(row))


def row_map(path) -> dict[tuple[str, str, str, str], dict[str, str]]:
    return {sidecar_key(row): row for row in read_csv(path)}


def race_map(path) -> dict[tuple[str, str, str], dict[str, str]]:
    return {race_key(row): row for row in read_csv(path)}


def num_or(value: object, fallback: float) -> float:
    try:
        raw = str(value or "").replace("%", "").replace("$", "").replace(",", "").strip()
        return float(raw) if raw else fallback
    except ValueError:
        return fallback


def band_score(value: str) -> float:
    upper = value.upper()
    if any(token in upper for token in ["ELITE", "STRONG CASE", "STRONG", "HIGH", "VERY_HIGH"]):
        return 1.0
    if any(token in upper for token in ["POSITIVE", "IMPROVING", "GOOD"]):
        return 0.7
    if any(token in upper for token in ["NEUTRAL", "MEDIUM", "MODERATE"]):
        return 0.45
    if any(token in upper for token in ["LOW", "LIMITED", "BELOW", "POOR", "WEAK"]):
        return 0.15
    return 0.3


def evidence_strength(row, dna, form, campaign, connection) -> float:
    scores = [
        band_score(text(dna.get("dna_v6_2_band"))),
        band_score(text(form.get("performance_intelligence_label"))),
        band_score(text(form.get("evidence_quality"))),
        band_score(text(campaign.get("campaign_profile_band"))),
        band_score(text(connection.get("connection_band"))),
        min(1.0, num_or(connection.get("connection_score"), 0) / 100),
        confidence_score(row) / 100,
    ]
    return max(0.05, min(1.0, sum(scores) / len(scores)))


def temperature_for_race(rating_gap: float, top_evidence: float, chaos: float, first_starters: float) -> tuple[float, str]:
    temp = 1.0
    reasons = []
    if rating_gap >= 8 and top_evidence >= 0.55:
        temp -= 0.22
        reasons.append("meaningful rating gap with support")
    elif rating_gap >= 5 and top_evidence >= 0.5:
        temp -= 0.14
        reasons.append("moderate rating gap with support")
    if top_evidence >= 0.7:
        temp -= 0.08
        reasons.append("strong evidence stack")
    if chaos >= 7:
        temp += 0.18
        reasons.append("high chaos keeps distribution flatter")
    elif chaos <= 4:
        temp -= 0.05
        reasons.append("low/moderate chaos allows separation")
    if first_starters >= 4:
        temp += 0.12
        reasons.append("first-starter load limits certainty")
    return max(0.68, min(1.22, temp)), "; ".join(reasons) or "neutral research temperature"


def softmax_rating_probabilities(sidecars: list[tuple[dict[str, str], float]], chaos_index: float, rating_gap_12: float) -> list[float]:
    ratings = [rating(row) or 0 for row, _ in sidecars]
    if not ratings:
        return []
    max_rating = max(ratings)
    scale = 9.0
    if rating_gap_12 >= 10:
        scale = 5.8
    elif rating_gap_12 >= 6:
        scale = 7.0
    elif rating_gap_12 < 2:
        scale = 13.0
    if chaos_index >= 7:
        scale += 3.0
    elif chaos_index <= 4:
        scale -= 1.0
    scores = []
    for row, evidence in sidecars:
        value = math.exp(((rating(row) or max_rating) - max_rating) / max(scale, 2.5))
        value *= 0.75 + (evidence * 0.55)
        scores.append(value)
    total = sum(scores) or 1
    return [score / total for score in scores]


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    dna_map = row_map(DNA)
    form_map = row_map(FORM)
    campaign_map = row_map(CAMPAIGN)
    connection_map = row_map(CONNECTION)
    chaos_map = race_map(CHAOS)
    opportunity_map = race_map(OPPORTUNITY)

    out = []
    audit = []
    statuses: Counter[str] = Counter()
    for key, field in sorted(by_race(active).items()):
        ranked = sorted(field, key=lambda row: rating(row) or 0, reverse=True)
        ratings = [rating(row) or 0 for row in ranked]
        min_rating = min(ratings) if ratings else 0
        top_rating = ratings[0] if ratings else 0
        rating_gap_12 = (ratings[0] - ratings[1]) if len(ratings) > 1 else 0
        sidecars = []
        for row in ranked:
            skey = (*key, horse_key(row))
            sidecars.append(
                (
                    row,
                    evidence_strength(row, dna_map.get(skey, {}), form_map.get(skey, {}), campaign_map.get(skey, {}), connection_map.get(skey, {})),
                )
            )
        top_evidence = sidecars[0][1] if sidecars else 0.3
        chaos_row = chaos_map.get(key, {})
        chaos_index = num_or(chaos_row.get("chaos_index"), 5)
        first_starters = num_or(chaos_row.get("first_starters"), 0)
        opportunity = num_or((opportunity_map.get(key, {}) or {}).get("opportunity_score"), 0)
        temp, race_reason = temperature_for_race(rating_gap_12, top_evidence, chaos_index, first_starters)

        softmax_probs = softmax_rating_probabilities(sidecars, chaos_index, rating_gap_12)
        prod_probs = [production_probability(row) or 0 for row, _ in sidecars]
        prod_total = sum(prod_probs) or 1
        prod_probs = [value / prod_total for value in prod_probs]
        softmax_weight = 0.62
        if chaos_index >= 7:
            softmax_weight = 0.48
        elif rating_gap_12 >= 8 and top_evidence >= 0.45:
            softmax_weight = 0.72
        candidate_probs = [
            (prod * (1 - softmax_weight)) + (soft * softmax_weight)
            for prod, soft in zip(prod_probs, softmax_probs)
        ]
        total = sum(candidate_probs) or 1
        candidate_probs = [value / total for value in candidate_probs]
        top_cap = 0.43 if chaos_index < 7 else 0.36
        if candidate_probs and max(candidate_probs) > top_cap:
            top_idx = candidate_probs.index(max(candidate_probs))
            excess = candidate_probs[top_idx] - top_cap
            candidate_probs[top_idx] = top_cap
            others = [i for i in range(len(candidate_probs)) if i != top_idx]
            other_total = sum(candidate_probs[i] for i in others) or 1
            for i in others:
                candidate_probs[i] += excess * (candidate_probs[i] / other_total)

        for idx, ((row, evidence), cand_prob) in enumerate(zip(sidecars, candidate_probs), start=1):
            prod_prob = production_probability(row) or 0
            prod_price = production_fair_price(row) or 0
            cand_price = 1 / cand_prob if cand_prob > 0 else 0
            statuses["RESEARCH_ONLY"] += 1
            out.append(
                {
                    "track": text(row.get("track")),
                    "race_no": key[2],
                    "horse": text(row.get("horse")),
                    "production_probability": format_float(prod_prob, 4),
                    "production_fair_price": format_float(prod_price, 2),
                    "candidate_probability_v5": format_float(cand_prob, 4),
                    "candidate_fair_price_v5": format_float(cand_price, 2),
                    "probability_delta": format_float(cand_prob - prod_prob, 4),
                    "price_delta": format_float(cand_price - prod_price, 2),
                    "rank": idx,
                    "rating": format_float(rating(row), 2),
                    "rating_gap_to_top": format_float(top_rating - (rating(row) or 0), 2),
                    "evidence_strength": format_float(evidence, 4),
                    "chaos_index": format_float(chaos_index, 2),
                    "opportunity_score": format_float(opportunity, 2),
                    "adjustment_reason": race_reason,
                    "research_status": "RESEARCH_ONLY",
                }
            )
        audit.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "field_size": len(field),
                "temperature": format_float(temp, 3),
                "rating_gap_rank1_rank2": format_float(rating_gap_12, 2),
                "top_evidence_strength": format_float(top_evidence, 4),
                "chaos_index": format_float(chaos_index, 2),
                "candidate_probability_sum": format_float(sum(candidate_probs), 6),
                "candidate_top_probability": format_float(max(candidate_probs) if candidate_probs else 0, 4),
                "adjustment_reason": race_reason,
            }
        )

    fields = list(out[0].keys()) if out else []
    write_csv(OUT, out, fields)
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    summary = [
        {"metric": "runner_rows", "value": len(out)},
        {"metric": "race_rows", "value": len(audit)},
        {"metric": "research_status::RESEARCH_ONLY", "value": statuses["RESEARCH_ONLY"]},
        {"metric": "production_pricing_changed", "value": "NO"},
        {"metric": "candidate_probability_sum_rule", "value": "NORMALISED_TO_100_PERCENT_BY_RACE"},
    ]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
