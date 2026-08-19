from collections import Counter

from edgeiq_pricing_research_common import (
    DATA,
    by_race,
    confidence_score,
    format_float,
    production_fair_price,
    production_probability,
    rating,
    read_csv,
    is_scratched,
    text,
    write_csv,
)


RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_probability_decomposition_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_decomposition_summary_v1.csv"


def root_cause(top_prob: float, prob_gap: float, rating_gap: float, confidence: float, field_size: int, evidence: str) -> str:
    if evidence in {"NO_PROJECTION", "NO_HISTORY", "LOW"}:
        return "MISSING_EVIDENCE_FLATTENING"
    if top_prob < 0.22 and field_size >= 10:
        return "FIELD_SIZE_NORMALISATION"
    if top_prob < 0.24 and prob_gap < 0.035:
        return "PROBABILITY_FLATTENING"
    if rating_gap >= 6 and prob_gap < 0.05:
        return "RANK_GAP_UNDER_TRANSLATED"
    if confidence < 50:
        return "CONFIDENCE_SUPPRESSION"
    if top_prob < 0.08 or top_prob > 0.45:
        return "CAP_FLOOR_CONSTRAINT"
    return "SOURCE_UNKNOWN"


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    out = []
    counts: Counter[str] = Counter()
    for key, field in sorted(by_race(active).items()):
        ranked = sorted(field, key=lambda row: rating(row) or 0, reverse=True)
        probs = sorted([(production_probability(row) or 0, row) for row in field], key=lambda item: item[0], reverse=True)
        ratings = [rating(row) or 0 for row in ranked]
        top_rating = ratings[0] if ratings else 0
        top_prob = probs[0][0] if probs else 0
        second_prob = probs[1][0] if len(probs) > 1 else 0
        for idx, row in enumerate(ranked, start=1):
            raw_rating = rating(row) or 0
            final_prob = production_probability(row) or 0
            gap = top_rating - raw_rating
            rating_gap_12 = (ratings[0] - ratings[1]) if len(ratings) > 1 else 0
            conf = confidence_score(row)
            evidence = text(row.get("projection_band_V6_1_RESEARCH") or row.get("projection_confidence_v5_2") or row.get("projection_band_v5_2")).upper()
            cause = root_cause(top_prob, top_prob - second_prob, rating_gap_12, conf, len(field), evidence)
            counts[cause] += 1
            raw_score = max(0.1, raw_rating - min(ratings) + 1) if ratings else 1
            out.append(
                {
                    "race_date": key[0],
                    "track": text(row.get("track")),
                    "race_no": key[2],
                    "horse": text(row.get("horse")),
                    "raw_rating": format_float(raw_rating, 2),
                    "rating_rank": idx,
                    "rating_gap_to_top": format_float(gap, 2),
                    "raw_score_approx": format_float(raw_score, 4),
                    "raw_probability_if_available": format_float(production_probability(row), 4),
                    "confidence_multiplier_approx": format_float(conf / 100, 4),
                    "environment_multiplier_approx": "",
                    "risk_multiplier_approx": "",
                    "first_starter_adjustment_approx": "YES" if evidence in {"NO_PROJECTION", "NO_HISTORY"} else "NO",
                    "field_size_adjustment_approx": format_float(1 / max(len(field), 1), 4),
                    "final_probability": format_float(final_prob, 4),
                    "final_fair_price": format_float(production_fair_price(row), 2),
                    "top_probability": format_float(top_prob, 4),
                    "top_probability_gap_to_second": format_float(top_prob - second_prob, 4),
                    "rank1_probability_flattened_flag": "YES" if top_prob < 0.24 else "NO",
                    "rank_gap_under_translated_flag": "YES" if rating_gap_12 >= 6 and (top_prob - second_prob) < 0.05 else "NO",
                    "confidence_suppression_flag": "YES" if conf < 50 else "NO",
                    "field_size_spread_flag": "YES" if len(field) >= 10 and top_prob < 0.24 else "NO",
                    "cap_floor_constraint_flag": "YES" if final_prob < 0.08 or final_prob > 0.45 else "NO",
                    "missing_evidence_flattening_flag": "YES" if evidence in {"NO_PROJECTION", "NO_HISTORY", "LOW"} else "NO",
                    "root_cause": cause,
                }
            )

    summary = [{"metric": "runner_rows", "value": len(out)}]
    summary += [{"metric": f"root_cause::{key}", "value": value} for key, value in counts.most_common()]
    fields = list(out[0].keys()) if out else []
    write_csv(OUT, out, fields)
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
