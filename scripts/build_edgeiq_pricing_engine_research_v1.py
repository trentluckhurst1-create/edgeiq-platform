from __future__ import annotations

import math
from collections import defaultdict

from edgeiq_results_common_v1 import DATA, has_value, normalize_race_no, normalized_track, numeric_float, read_csv, write_csv
from build_edgeiq_lengths_per_point_engine_v1 import distance_band
from build_edgeiq_standard_times_v1 import class_band, condition_band


RUNNERS = DATA / "edgeiq_live_runner_board_v1.csv"
LPP = DATA / "edgeiq_lengths_per_point_engine_v1.csv"
OUT = DATA / "edgeiq_pricing_engine_research_v1.csv"
SUMMARY = DATA / "edgeiq_pricing_engine_research_summary_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "runner",
    "projected_rating",
    "user_adjusted_rating",
    "rating_delta",
    "rating_delta_lengths",
    "data_confidence",
    "market_confidence_weight",
    "model_probability",
    "market_probability",
    "blended_probability",
    "research_price",
    "production_price",
    "price_delta",
    "pricing_mode",
    "pricing_status",
]


def lpp_lookup() -> dict[tuple[str, str, str], dict[str, str]]:
    lookup = {}
    for row in read_csv(LPP):
        key = (row["distance_band"], row["class_band"], row["condition_band"])
        existing = lookup.get(key)
        if existing is None or int(row.get("sample_size", "0") or 0) > int(existing.get("sample_size", "0") or 0):
            lookup[key] = row
    return lookup


def find_lpp(row: dict[str, str], lookup: dict[tuple[str, str, str], dict[str, str]]) -> tuple[float, str]:
    d_band = distance_band(row.get("distance", ""))
    c_band = class_band(row.get("race_class", ""))
    cond = condition_band(row.get("track_condition", ""))
    for key in [(d_band, c_band, cond), (d_band, c_band, "ALL_CONDITIONS"), (d_band, "ALL_CLASSES", cond), (d_band, "ALL_CLASSES", "ALL_CONDITIONS")]:
        found = lookup.get(key)
        if found:
            return float(found["rating_point_to_lengths"]), found["fallback_level"]
    return 0.75, "GLOBAL_DEFAULT_RESEARCH"


def confidence_weight(row: dict[str, str]) -> float:
    starts = numeric_float(row.get("starts_found_v5_2", "")) or numeric_float(row.get("starts_found_research", ""))
    conf = (row.get("projection_confidence_v5_2", "") or "").upper()
    if starts is not None and starts <= 1:
        return 0.35
    if starts is not None and starts <= 3:
        return 0.55
    if conf == "HIGH":
        return 0.85
    if conf == "MEDIUM":
        return 0.7
    if conf == "LOW":
        return 0.45
    return 0.6


def market_probability(price: float | None) -> float:
    if price is None or price <= 1.0:
        return 0.0
    return 1.0 / price


def active_rows() -> list[dict[str, str]]:
    rows = []
    for row in read_csv(RUNNERS):
        if row.get("runner_status", "").upper() == "SCRATCHED" or row.get("is_scratched", "").upper() == "TRUE":
            continue
        if not has_value(row.get("horse", "")):
            continue
        rows.append(row)
    return rows


def main() -> None:
    lookup = lpp_lookup()
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in active_rows():
        race_key = f"{row.get('race_date','')}_{normalized_track(row.get('track',''))}_R{normalize_race_no(row.get('race_no',''))}"
        groups[race_key].append(row)

    out = []
    for race_key, race_rows in groups.items():
        prepared = []
        for row in race_rows:
            rating = numeric_float(row.get("projected_rating_V6_1_RESEARCH", "")) or numeric_float(row.get("projected_rating_v5_2", ""))
            if rating is None:
                continue
            lpp, fallback = find_lpp(row, lookup)
            live_price = numeric_float(row.get("live_price", "")) or numeric_float(row.get("tab_fixed_win", ""))
            market_prob = market_probability(live_price)
            data_conf = confidence_weight(row)
            prepared.append((row, rating, lpp, fallback, live_price, market_prob, data_conf))
        if not prepared:
            continue
        max_rating = max(item[1] for item in prepared)
        raw_scores = []
        for row, rating, lpp, fallback, live_price, market_prob, data_conf in prepared:
            delta_lengths = (rating - max_rating) * lpp
            raw_scores.append(math.exp(delta_lengths / 2.5))
        score_sum = sum(raw_scores) or 1.0
        market_sum = sum(item[5] for item in prepared) or 1.0
        blended = []
        for idx, item in enumerate(prepared):
            row, rating, lpp, fallback, live_price, market_prob, data_conf = item
            model_prob = raw_scores[idx] / score_sum
            m_prob = market_prob / market_sum if market_prob else 0.0
            market_weight = 1.0 - data_conf
            final_prob = model_prob * data_conf + m_prob * market_weight
            mode = "EDGEIQ_BASE"
            if data_conf <= 0.4:
                mode = "LOW_DATA_MARKET_ANCHOR"
            elif market_weight >= 0.3:
                mode = "MARKET_BLEND"
            blended.append((item, model_prob, m_prob, final_prob, mode))
        final_sum = sum(item[3] for item in blended) or 1.0
        for item, model_prob, m_prob, final_prob, mode in blended:
            row, rating, lpp, fallback, live_price, market_prob, data_conf = item
            final_prob = final_prob / final_sum
            production_price = numeric_float(row.get("fair_price", "")) or numeric_float(row.get("ui_fair_price", ""))
            research_price = round(1.0 / final_prob, 2) if final_prob > 0 else ""
            out.append(
                {
                    "race_date": row.get("race_date", ""),
                    "track": row.get("track", ""),
                    "race_no": row.get("race_no", ""),
                    "runner": row.get("horse", ""),
                    "projected_rating": round(rating, 4),
                    "user_adjusted_rating": round(rating, 4),
                    "rating_delta": 0,
                    "rating_delta_lengths": 0,
                    "data_confidence": round(data_conf, 4),
                    "market_confidence_weight": round(1.0 - data_conf, 4),
                    "model_probability": round(model_prob, 8),
                    "market_probability": round(m_prob, 8),
                    "blended_probability": round(final_prob, 8),
                    "research_price": research_price,
                    "production_price": production_price or "",
                    "price_delta": round(float(research_price) - production_price, 2) if research_price and production_price else "",
                    "pricing_mode": mode,
                    "pricing_status": f"RESEARCH_ONLY_{fallback}",
                }
            )
    write_csv(OUT, out, FIELDS)
    summary = {
        "races_priced": len({(r["race_date"], r["track"], r["race_no"]) for r in out}),
        "runners_priced": len(out),
        "low_data_market_anchor_rows": sum(1 for r in out if r["pricing_mode"] == "LOW_DATA_MARKET_ANCHOR"),
        "market_blend_rows": sum(1 for r in out if r["pricing_mode"] == "MARKET_BLEND"),
        "edgeiq_base_rows": sum(1 for r in out if r["pricing_mode"] == "EDGEIQ_BASE"),
        "research_only": "YES",
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
