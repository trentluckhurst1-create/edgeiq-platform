from collections import Counter

from edgeiq_pricing_research_common import (
    DATA,
    by_race,
    clean,
    confidence_score,
    entropy_ratio,
    format_float,
    horse_key,
    production_fair_price,
    production_probability,
    rating,
    read_csv,
    is_scratched,
    text,
    write_csv,
)

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
FORM = DATA / "edgeiq_form_intelligence_v2.csv"
CAMPAIGN = DATA / "edgeiq_campaign_intelligence_engine_v1_1.csv"
DNA = DATA / "edgeiq_runner_dna_v6_2.csv"
CONNECTION = DATA / "edgeiq_connection_intelligence_v2_1.csv"
CHAOS = DATA / "edgeiq_chaos_index_v1.csv"
OPPORTUNITY = DATA / "edgeiq_opportunity_score_v1.csv"
OUT = DATA / "edgeiq_probability_temperature_features_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_temperature_features_summary_v1.csv"


def sidecar_key(row):
    return (text(row.get("current_race_date") or row.get("race_date")), clean(row.get("track")), text(row.get("race_no")), horse_key(row))


def map_rows(path):
    return {sidecar_key(row): row for row in read_csv(path)}


def race_map(path):
    return {(text(row.get("race_date") or row.get("current_race_date")), clean(row.get("track")), text(row.get("race_no"))): row for row in read_csv(path)}


def score_band(value):
    upper = text(value).upper()
    if any(token in upper for token in ["ELITE", "STRONG", "STRONG CASE", "HIGH", "GOOD"]):
        return 1.0
    if any(token in upper for token in ["POSITIVE", "IMPROVING", "MEDIUM", "NEUTRAL"]):
        return 0.6
    if any(token in upper for token in ["LOW", "LIMITED", "BELOW", "POOR", "WEAK"]):
        return 0.2
    return 0.35


def num_or(value, fallback=0.0):
    try:
        raw = str(value or "").replace("%", "").replace("$", "").replace(",", "").strip()
        return float(raw) if raw else fallback
    except ValueError:
        return fallback


def recommend(rating_gap_top2, evidence_strength, chaos_index, form_depth, coverage_score):
    if rating_gap_top2 >= 6 and evidence_strength >= 0.58 and chaos_index <= 6.8 and coverage_score >= 0.55:
        return "AGGRESSIVE_CONCENTRATION"
    if chaos_index >= 7.2 and (form_depth < 2 or evidence_strength < 0.42 or coverage_score < 0.45):
        return "CONSERVATIVE_FLATTER"
    if evidence_strength <= 0.25 and form_depth == 0:
        return "NO_RECOMMENDATION"
    return "BALANCED"


def main():
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    form = map_rows(FORM)
    campaign = map_rows(CAMPAIGN)
    dna = map_rows(DNA)
    connection = map_rows(CONNECTION)
    chaos = race_map(CHAOS)
    opportunity = race_map(OPPORTUNITY)
    out = []
    counts = Counter()
    for key, field in sorted(by_race(active).items()):
        ranked = sorted(field, key=lambda row: rating(row) or 0, reverse=True)
        ratings = [rating(row) or 0 for row in ranked]
        probs = sorted([production_probability(row) or 0 for row in field], reverse=True)
        prices = sorted([production_fair_price(row) or 0 for row in field if production_fair_price(row)])
        top = ranked[0] if ranked else field[0]
        skey = (*key, horse_key(top))
        frow = form.get(skey, {})
        crow = campaign.get(skey, {})
        drow = dna.get(skey, {})
        conrow = connection.get(skey, {})
        chaos_row = chaos.get(key, {})
        opp_row = opportunity.get(key, {})
        form_depth = int(num_or(frow.get("recent_runs_found"), 0))
        coverage_items = [
            1 if form_depth > 0 else 0,
            1 if drow else 0,
            1 if crow and text(crow.get("evidence_status")).upper() not in {"", "NO_EVIDENCE"} else 0,
            1 if conrow and text(conrow.get("connection_band")).upper() not in {"", "NO_EVIDENCE"} else 0,
        ]
        coverage_score = sum(coverage_items) / len(coverage_items)
        evidence_strength = (
            score_band(frow.get("performance_intelligence_label"))
            + score_band(frow.get("evidence_quality"))
            + score_band(crow.get("campaign_profile_band"))
            + score_band(drow.get("dna_v6_2_band"))
            + score_band(conrow.get("connection_band"))
            + confidence_score(top) / 100
        ) / 6
        rating_gap_top2 = (ratings[0] - ratings[1]) if len(ratings) > 1 else 0
        rating_gap_top3 = (ratings[0] - ratings[2]) if len(ratings) > 2 else 0
        chaos_index = num_or(chaos_row.get("chaos_index"), 5)
        band = recommend(rating_gap_top2, evidence_strength, chaos_index, form_depth, coverage_score)
        counts[band] += 1
        out.append({
            "race_date": key[0],
            "track": text(field[0].get("track")),
            "race_no": key[2],
            "field_size": len(field),
            "rating_gap_top2": format_float(rating_gap_top2, 2),
            "rating_gap_top3": format_float(rating_gap_top3, 2),
            "confidence_top": format_float(confidence_score(top), 1),
            "evidence_strength": format_float(evidence_strength, 4),
            "chaos_index": format_float(chaos_index, 2),
            "opportunity_score": format_float(num_or(opp_row.get("opportunity_score"), 0), 2),
            "form_depth": form_depth,
            "first_starter_count": format_float(num_or(chaos_row.get("first_starters"), 0), 0),
            "campaign_coverage": "YES" if coverage_items[2] else "NO",
            "dna_coverage": "YES" if coverage_items[1] else "NO",
            "connection_coverage": "YES" if coverage_items[3] else "NO",
            "coverage_score": format_float(coverage_score, 4),
            "performance_intelligence_count": sum(1 for row in field if score_band((form.get((*key, horse_key(row)), {}) or {}).get("performance_intelligence_label")) >= 0.6),
            "market_shape": "FLAT" if entropy_ratio(probs) > 0.88 else "CONCENTRATED",
            "production_fav_price": format_float(prices[0] if prices else 0, 2),
            "production_top3_prob": format_float(sum(probs[:3]), 4),
            "recommended_temperature_band": band,
        })
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY, [{"metric": "race_rows", "value": len(out)}] + [{"metric": f"band::{k}", "value": v} for k, v in counts.most_common()], ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
