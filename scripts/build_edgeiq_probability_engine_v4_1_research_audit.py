from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_REPLAY = DATA / "edgeiq_probability_engine_v4_candidate_replay.csv"
INPUT_SUMMARY = DATA / "edgeiq_probability_engine_v4_candidate_summary.csv"
INPUT_REALISM = DATA / "edgeiq_probability_engine_v4_price_realism.csv"
INPUT_BUCKETS = DATA / "edgeiq_probability_engine_v4_calibration_buckets.csv"
INPUT_REPORT = DATA / "edgeiq_probability_engine_v4_report.md"

OUT_REPLAY = DATA / "edgeiq_probability_engine_v4_1_candidate_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_engine_v4_1_candidate_summary.csv"
OUT_BUCKETS = DATA / "edgeiq_probability_engine_v4_1_calibration_buckets.csv"
OUT_REALISM = DATA / "edgeiq_probability_engine_v4_1_price_realism.csv"
OUT_MARKET = DATA / "edgeiq_probability_engine_v4_1_market_blend_audit.csv"
OUT_REPORT = DATA / "edgeiq_probability_engine_v4_1_report.md"

HYBRID_SCENARIO = "V4_HYBRID_RECOMMENDED"
CURRENT_SCENARIO = "CURRENT_V6_1_CONVERSION"

MARKET_MIN_COVERAGE_PCT = 50.0
MARKET_MIN_COVERED_RUNNERS = 3
SHORT_PRICE_ANCHOR_MODEL_PROB = 0.25
SHORT_PRICE_ANCHOR_GAP = 0.04
SHORT_PRICE_ANCHOR_BLEND = 0.35
RANK_PRESERVING_ALPHA = 0.88
FIELD_SIZE_FLOOR = 0.002

PROBABILITY_BUCKETS = [
    (0.00, 0.05, "0_5"),
    (0.05, 0.10, "5_10"),
    (0.10, 0.15, "10_15"),
    (0.15, 0.20, "15_20"),
    (0.20, 0.25, "20_25"),
    (0.25, 0.30, "25_30"),
    (0.30, 0.35, "30_35"),
    (0.35, 1.01, "35_PLUS"),
]

SHORT_PRICE_BUCKETS = [100, 250, 500, 1000]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def to_float(value: object) -> float | None:
    try:
        text = clean(value).replace(",", "").replace("$", "")
        if text == "":
            return None
        parsed = float(text)
        if not math.isfinite(parsed):
            return None
        return parsed
    except Exception:
        return None


def safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator) * 100.0


def fmt_num(value: float | None, places: int = 4) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), places)


def probability_bucket(probability: float | None) -> str:
    if probability is None or math.isnan(probability):
        return "NO_PROB"
    for low, high, label in PROBABILITY_BUCKETS:
        if low <= probability < high:
            return label
    return "35_PLUS"


def normalize(weights: np.ndarray) -> np.ndarray:
    arr = np.clip(weights.astype(float), 0.0, None)
    total = float(arr.sum())
    if total <= 0:
        return np.repeat(1.0 / len(arr), len(arr))
    return arr / total


def bounded_probs(probabilities: np.ndarray, floor: float, cap: float) -> tuple[np.ndarray, int, int]:
    q = normalize(probabilities)
    cap_hits = int((q > cap).sum())
    floor_hits = int((q < floor).sum())

    fixed_low = np.zeros(len(q), dtype=bool)
    fixed_high = np.zeros(len(q), dtype=bool)

    for _ in range(50):
        changed = False

        low_mask = (~fixed_low) & (~fixed_high) & (q < floor)
        if low_mask.any():
            q[low_mask] = floor
            fixed_low[low_mask] = True
            changed = True

        high_mask = (~fixed_low) & (~fixed_high) & (q > cap)
        if high_mask.any():
            q[high_mask] = cap
            fixed_high[high_mask] = True
            changed = True

        free_mask = ~(fixed_low | fixed_high)
        fixed_sum = float(q[fixed_low | fixed_high].sum())
        remaining = 1.0 - fixed_sum

        if free_mask.any():
            if remaining <= 0:
                q[free_mask] = 0.0
            else:
                weights = np.clip(probabilities[free_mask].astype(float), 0.0, None)
                if float(weights.sum()) <= 0:
                    weights = np.ones_like(weights)
                q[free_mask] = remaining * weights / float(weights.sum())
        else:
            total_now = float(q.sum())
            if total_now > 0:
                q = q / total_now
            break

        if not changed:
            break

    return normalize(q), cap_hits, floor_hits


def field_size_cap(field_size: int) -> float:
    if field_size <= 7:
        return 0.33
    if field_size <= 10:
        return 0.31
    if field_size <= 13:
        return 0.29
    return 0.27


def scenario_rows(source: pd.DataFrame, scenario_name: str) -> pd.DataFrame:
    return source[source["scenario_name_v1"].map(upper).eq(scenario_name.upper())].copy()


def market_price_to_weight(value: object) -> float:
    price = to_float(value)
    if price is None or price <= 1.0:
        return 0.0
    return 1.0 / price


def coverage_bucket(coverage_pct: float) -> str:
    if coverage_pct >= 80.0:
        return "GE_80"
    if coverage_pct >= 50.0:
        return "GE_50"
    if coverage_pct >= 25.0:
        return "GE_25"
    if coverage_pct > 0:
        return "LT_25"
    return "ZERO"


def race_metrics(frame: pd.DataFrame, probability_column: str, rank_column: str, fair_column: str) -> dict[str, float]:
    race_count = frame["race_key"].nunique()
    runner_count = len(frame)

    rank1_rows = frame[frame[rank_column] == 1].copy()
    rank1_win_pct = safe_pct(rank1_rows["won_num"].sum(), len(rank1_rows))
    rank1_place_pct = safe_pct(rank1_rows["placed_num"].sum(), len(rank1_rows))

    winner_rows = frame[frame["won_num"] == 1].copy()
    top3_capture_pct = safe_pct((winner_rows[rank_column] <= 3).sum(), race_count)

    probs = pd.to_numeric(frame[probability_column], errors="coerce").fillna(0.0)
    brier = float(np.mean(np.square(probs - frame["won_num"].astype(float)))) if len(frame) else 0.0

    race_sums = frame.groupby("race_key", dropna=False)[probability_column].sum(min_count=1)
    race_sums = pd.to_numeric(race_sums, errors="coerce").fillna(0.0)

    fair_rank1 = pd.to_numeric(rank1_rows[fair_column], errors="coerce").dropna()

    return {
        "race_count": int(race_count),
        "runner_count": int(runner_count),
        "rank1_win_pct": fmt_num(rank1_win_pct, 4),
        "rank1_place_pct": fmt_num(rank1_place_pct, 4),
        "top3_capture_pct": fmt_num(top3_capture_pct, 4),
        "brier_score_v1": fmt_num(brier, 6),
        "avg_probability_sum_by_race_v1": fmt_num(float(race_sums.mean()) if len(race_sums) else 0.0, 6),
        "probability_sum_min_v1": fmt_num(float(race_sums.min()) if len(race_sums) else 0.0, 6),
        "probability_sum_max_v1": fmt_num(float(race_sums.max()) if len(race_sums) else 0.0, 6),
        "underround_race_count_v1": int((race_sums < 0.999).sum()),
        "overround_race_count_v1": int((race_sums > 1.001).sum()),
        "avg_rank1_fair_price_v1": fmt_num(float(fair_rank1.mean()) if len(fair_rank1) else 0.0, 4),
        "median_rank1_fair_price_v1": fmt_num(float(fair_rank1.median()) if len(fair_rank1) else 0.0, 4),
    }


def calibration_table(frame: pd.DataFrame, scenario_name: str, probability_column: str) -> tuple[list[dict[str, object]], float]:
    rows: list[dict[str, object]] = []
    total = len(frame)
    weighted_gap = 0.0

    temp = frame.copy()
    temp["probability_bucket_v1"] = temp[probability_column].map(probability_bucket)

    for bucket, group in temp.groupby("probability_bucket_v1", dropna=False):
        predicted = float(group[probability_column].mean() * 100.0) if len(group) else 0.0
        actual = safe_pct(group["won_num"].sum(), len(group))
        gap = predicted - actual
        rows.append(
            {
                "scenario_name_v1": scenario_name,
                "probability_bucket_v1": bucket,
                "runner_count": int(len(group)),
                "wins": int(group["won_num"].sum()),
                "avg_predicted_pct_v1": fmt_num(predicted, 4),
                "actual_win_pct_v1": fmt_num(actual, 4),
                "calibration_gap_pts_v1": fmt_num(gap, 4),
            }
        )
        if total > 0:
            weighted_gap += abs(gap) * (len(group) / total)

    return rows, fmt_num(weighted_gap, 4) or 0.0


def price_realism_table(frame: pd.DataFrame, scenario_name: str, fair_column: str, probability_column: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    valid = frame[pd.to_numeric(frame[fair_column], errors="coerce").notna()].copy()
    valid[fair_column] = pd.to_numeric(valid[fair_column], errors="coerce")

    for bucket_size in SHORT_PRICE_BUCKETS:
        sample = valid.nsmallest(bucket_size, fair_column)
        implied = float(sample[probability_column].mean() * 100.0) if len(sample) else 0.0
        actual = safe_pct(sample["won_num"].sum(), len(sample))
        avg_fair = float(sample[fair_column].mean()) if len(sample) else 0.0
        rows.append(
            {
                "scenario_name_v1": scenario_name,
                "tail_group_v1": f"TOP_{bucket_size}_SHORTEST",
                "runner_count": int(len(sample)),
                "wins": int(sample["won_num"].sum()),
                "avg_implied_prob_pct_v1": fmt_num(implied, 4),
                "actual_win_pct_v1": fmt_num(actual, 4),
                "implied_minus_actual_gap_pts_v1": fmt_num(implied - actual, 4),
                "avg_fair_price_v1": fmt_num(avg_fair, 4),
            }
        )

    for bucket_size in SHORT_PRICE_BUCKETS:
        sample = valid.nlargest(bucket_size, fair_column)
        implied = float(sample[probability_column].mean() * 100.0) if len(sample) else 0.0
        actual = safe_pct(sample["won_num"].sum(), len(sample))
        avg_fair = float(sample[fair_column].mean()) if len(sample) else 0.0
        rows.append(
            {
                "scenario_name_v1": scenario_name,
                "tail_group_v1": f"TOP_{bucket_size}_LONGEST",
                "runner_count": int(len(sample)),
                "wins": int(sample["won_num"].sum()),
                "avg_implied_prob_pct_v1": fmt_num(implied, 4),
                "actual_win_pct_v1": fmt_num(actual, 4),
                "implied_minus_actual_gap_pts_v1": fmt_num(implied - actual, 4),
                "avg_fair_price_v1": fmt_num(avg_fair, 4),
            }
        )

    return rows


def overlay_metrics(frame: pd.DataFrame, fair_column: str) -> dict[str, float]:
    valid_market = frame[frame["market_price_v1"].notna() & frame[fair_column].notna()].copy()
    if valid_market.empty:
        return {
            "market_proxy_rows_v1": 0,
            "overlay_rows_v1": 0,
            "overlay_win_pct_v1": 0.0,
            "non_overlay_rows_v1": 0,
            "non_overlay_win_pct_v1": 0.0,
            "overlay_edge_gap_pts_v1": 0.0,
        }

    overlays = valid_market[valid_market["market_price_v1"] > valid_market[fair_column]].copy()
    non_overlays = valid_market[valid_market["market_price_v1"] <= valid_market[fair_column]].copy()

    overlay_win = safe_pct(overlays["won_num"].sum(), len(overlays))
    non_overlay_win = safe_pct(non_overlays["won_num"].sum(), len(non_overlays))

    return {
        "market_proxy_rows_v1": int(len(valid_market)),
        "overlay_rows_v1": int(len(overlays)),
        "overlay_win_pct_v1": fmt_num(overlay_win, 4),
        "non_overlay_rows_v1": int(len(non_overlays)),
        "non_overlay_win_pct_v1": fmt_num(non_overlay_win, 4),
        "overlay_edge_gap_pts_v1": fmt_num(overlay_win - non_overlay_win, 4),
    }


def scenario_description(name: str) -> str:
    mapping = {
        CURRENT_SCENARIO: "Current V6.1 live builder conversion with existing cap/no-renormalisation behaviour.",
        HYBRID_SCENARIO: "Existing V4 hybrid recommended baseline.",
        "MARKET_ONLY_NORMALISED": "Market proxy where available, model fill where missing, race-normalised with coverage guardrails.",
        "BLEND_80_MODEL_20_MARKET": "80% V4 hybrid model + 20% market proxy on eligible races.",
        "BLEND_70_MODEL_30_MARKET": "70% V4 hybrid model + 30% market proxy on eligible races.",
        "BLEND_60_MODEL_40_MARKET": "60% V4 hybrid model + 40% market proxy on eligible races.",
        "SHORT_PRICE_ANCHOR_ONLY": "Only shrink extreme short-price model probabilities toward market when market is materially longer.",
        "FIELD_SIZE_DYNAMIC_CAP": "V4 hybrid with field-size-dependent favourite cap and stable floor.",
        "RANK_PRESERVING_TEMPERATURE": "V4 hybrid probabilities softened by a monotonic power transform that preserves rank order.",
    }
    return mapping.get(name, name)


def market_blend_status(covered_count: int, field_size: int) -> tuple[bool, float, str]:
    coverage_pct = safe_pct(covered_count, field_size)
    if covered_count < MARKET_MIN_COVERED_RUNNERS:
        return False, coverage_pct, "INSUFFICIENT_MARKET_RUNNERS"
    if coverage_pct < MARKET_MIN_COVERAGE_PCT:
        return False, coverage_pct, "MARKET_COVERAGE_BELOW_50_PCT"
    return True, coverage_pct, "MARKET_ELIGIBLE"


def race_market_proxy(model_probs: np.ndarray, market_prices: list[float | None]) -> tuple[np.ndarray, int]:
    market_weights = np.array([market_price_to_weight(price) for price in market_prices], dtype=float)
    covered_mask = market_weights > 0
    blended_weights = np.where(covered_mask, market_weights, model_probs.astype(float))
    return normalize(blended_weights), int(covered_mask.sum())


def build_scenarios(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    replay_rows: list[dict[str, object]] = []
    market_rows: list[dict[str, object]] = []

    for race_key, race in base.groupby("race_key", dropna=False, sort=False):
        race = race.copy().reset_index(drop=True)
        field_size = len(race)
        model_probs = race["hybrid_probability_v1"].astype(float).to_numpy()
        current_probs = race["current_probability_v1"].astype(float).to_numpy()
        market_prices = race["market_price_v1"].tolist()
        market_proxy_probs, covered_count = race_market_proxy(model_probs, market_prices)
        market_eligible, coverage_pct, coverage_reason = market_blend_status(covered_count, field_size)
        coverage_group = coverage_bucket(coverage_pct)
        full_market_coverage = covered_count == field_size

        scenario_probabilities: dict[str, np.ndarray] = {
            CURRENT_SCENARIO: current_probs.copy(),
            HYBRID_SCENARIO: model_probs.copy(),
        }
        scenario_guardrails: dict[str, str] = {
            CURRENT_SCENARIO: "CURRENT_LIVE_REFERENCE",
            HYBRID_SCENARIO: "V4_HYBRID_BASELINE",
        }
        scenario_market_applied: dict[str, bool] = {
            CURRENT_SCENARIO: False,
            HYBRID_SCENARIO: False,
        }
        scenario_caps: dict[str, int] = {
            CURRENT_SCENARIO: int(pd.to_numeric(race["cap_hits_race_v1"], errors="coerce").fillna(0).max()),
            HYBRID_SCENARIO: 0,
        }
        scenario_floors: dict[str, int] = {
            CURRENT_SCENARIO: int(pd.to_numeric(race["floor_hits_race_v1"], errors="coerce").fillna(0).max()),
            HYBRID_SCENARIO: 0,
        }

        if market_eligible:
            scenario_probabilities["MARKET_ONLY_NORMALISED"] = market_proxy_probs.copy()
            scenario_guardrails["MARKET_ONLY_NORMALISED"] = "MARKET_PROXY_WITH_MODEL_FILL"
            scenario_market_applied["MARKET_ONLY_NORMALISED"] = True
        else:
            scenario_probabilities["MARKET_ONLY_NORMALISED"] = model_probs.copy()
            scenario_guardrails["MARKET_ONLY_NORMALISED"] = f"{coverage_reason}|FALLBACK_MODEL"
            scenario_market_applied["MARKET_ONLY_NORMALISED"] = False
        scenario_caps["MARKET_ONLY_NORMALISED"] = 0
        scenario_floors["MARKET_ONLY_NORMALISED"] = 0

        for model_weight, market_weight, name in [
            (0.8, 0.2, "BLEND_80_MODEL_20_MARKET"),
            (0.7, 0.3, "BLEND_70_MODEL_30_MARKET"),
            (0.6, 0.4, "BLEND_60_MODEL_40_MARKET"),
        ]:
            if market_eligible:
                scenario_probabilities[name] = normalize((model_weight * model_probs) + (market_weight * market_proxy_probs))
                scenario_guardrails[name] = f"BLEND_APPLIED|MODEL_{model_weight:.1f}|MARKET_{market_weight:.1f}"
                scenario_market_applied[name] = True
            else:
                scenario_probabilities[name] = model_probs.copy()
                scenario_guardrails[name] = f"{coverage_reason}|FALLBACK_MODEL"
                scenario_market_applied[name] = False
            scenario_caps[name] = 0
            scenario_floors[name] = 0

        anchor_probs = model_probs.copy()
        anchor_applied = False
        anchor_reasons = []
        for idx, market_prob in enumerate(market_proxy_probs):
            if market_price_to_weight(market_prices[idx]) <= 0:
                continue
            if model_probs[idx] >= SHORT_PRICE_ANCHOR_MODEL_PROB and (model_probs[idx] - market_prob) >= SHORT_PRICE_ANCHOR_GAP:
                anchor_probs[idx] = ((1.0 - SHORT_PRICE_ANCHOR_BLEND) * model_probs[idx]) + (SHORT_PRICE_ANCHOR_BLEND * market_prob)
                anchor_applied = True
                anchor_reasons.append(race.at[idx, "horse"])
        if anchor_applied:
            anchor_probs = normalize(anchor_probs)
            scenario_guardrails["SHORT_PRICE_ANCHOR_ONLY"] = "SHORT_PRICE_ANCHOR_APPLIED"
            scenario_market_applied["SHORT_PRICE_ANCHOR_ONLY"] = True
        else:
            scenario_guardrails["SHORT_PRICE_ANCHOR_ONLY"] = f"{coverage_reason}|NO_ANCHOR_TRIGGER"
            scenario_market_applied["SHORT_PRICE_ANCHOR_ONLY"] = False
        scenario_probabilities["SHORT_PRICE_ANCHOR_ONLY"] = anchor_probs
        scenario_caps["SHORT_PRICE_ANCHOR_ONLY"] = 0
        scenario_floors["SHORT_PRICE_ANCHOR_ONLY"] = 0

        dynamic_cap = field_size_cap(field_size)
        dynamic_probs, dynamic_cap_hits, dynamic_floor_hits = bounded_probs(model_probs, FIELD_SIZE_FLOOR, dynamic_cap)
        scenario_probabilities["FIELD_SIZE_DYNAMIC_CAP"] = dynamic_probs
        scenario_guardrails["FIELD_SIZE_DYNAMIC_CAP"] = f"FIELD_SIZE_CAP={dynamic_cap:.3f}"
        scenario_market_applied["FIELD_SIZE_DYNAMIC_CAP"] = False
        scenario_caps["FIELD_SIZE_DYNAMIC_CAP"] = dynamic_cap_hits
        scenario_floors["FIELD_SIZE_DYNAMIC_CAP"] = dynamic_floor_hits

        temperature_probs = normalize(np.power(np.clip(model_probs, 1e-9, None), RANK_PRESERVING_ALPHA))
        scenario_probabilities["RANK_PRESERVING_TEMPERATURE"] = temperature_probs
        scenario_guardrails["RANK_PRESERVING_TEMPERATURE"] = f"ALPHA={RANK_PRESERVING_ALPHA:.2f}"
        scenario_market_applied["RANK_PRESERVING_TEMPERATURE"] = False
        scenario_caps["RANK_PRESERVING_TEMPERATURE"] = 0
        scenario_floors["RANK_PRESERVING_TEMPERATURE"] = 0

        hybrid_ranks = race["hybrid_rank_v1"].astype(int).to_numpy()

        race_top_pick_changes: dict[str, bool] = {}
        for scenario_name, probs in scenario_probabilities.items():
            scenario_ranks = pd.Series(-probs).rank(method="first").astype(int).to_numpy()
            top_pick_changed = bool(np.any((hybrid_ranks == 1) & (scenario_ranks != 1)) or np.any((hybrid_ranks != 1) & (scenario_ranks == 1)))
            race_top_pick_changes[scenario_name] = top_pick_changed

            scenario_sum = float(np.sum(probs))
            underround = scenario_sum < 0.999
            overround = scenario_sum > 1.001

            for idx, row in race.iterrows():
                scenario_prob = float(probs[idx])
                scenario_fair = (1.0 / scenario_prob) if scenario_prob > 0 else math.nan
                replay_rows.append(
                    {
                        "scenario_name_v1": scenario_name,
                        "candidate_family_v1": scenario_name,
                        "candidate_setting_v1": scenario_description(scenario_name),
                        "race_key": row["race_key"],
                        "race_date": row["race_date"],
                        "track": row["track"],
                        "race_no": row["race_no"],
                        "horse": row["horse"],
                        "horse_key": row["horse_key"],
                        "projection_band": row["projection_band"],
                        "rating": row["rating"],
                        "rating_gap": row["rating_gap"],
                        "won": int(row["won_num"]),
                        "placed": int(row["placed_num"]),
                        "market_price_v1": fmt_num(row["market_price_v1"], 4),
                        "sp_num": clean(row["sp_num"]),
                        "base_model_probability_v1": fmt_num(float(model_probs[idx]), 8),
                        "base_model_fair_price_v1": fmt_num((1.0 / float(model_probs[idx])) if model_probs[idx] > 0 else math.nan, 8),
                        "current_v6_1_probability_v1": fmt_num(float(current_probs[idx]), 8),
                        "current_v6_1_fair_price_v1": fmt_num((1.0 / float(current_probs[idx])) if current_probs[idx] > 0 else math.nan, 8),
                        "market_proxy_probability_v1": fmt_num(float(market_proxy_probs[idx]), 8),
                        "candidate_probability_v1": fmt_num(scenario_prob, 8),
                        "candidate_fair_price_v1": fmt_num(scenario_fair, 8),
                        "candidate_rank_v1": int(scenario_ranks[idx]),
                        "hybrid_rank_v1": int(hybrid_ranks[idx]),
                        "probability_delta_pts_vs_hybrid_v1": fmt_num((scenario_prob - float(model_probs[idx])) * 100.0, 4),
                        "fair_price_change_pct_vs_hybrid_v1": fmt_num((((scenario_fair / (1.0 / float(model_probs[idx]))) - 1.0) * 100.0) if model_probs[idx] > 0 else math.nan, 4),
                        "rank_changed_vs_hybrid_v1": bool(int(scenario_ranks[idx]) != int(hybrid_ranks[idx])),
                        "top_pick_changed_race_vs_hybrid_v1": race_top_pick_changes[scenario_name],
                        "material_prob_move_v1": bool(abs(scenario_prob - float(model_probs[idx])) >= 0.02),
                        "material_fair_price_move_v1": bool(
                            abs((((scenario_fair / (1.0 / float(model_probs[idx]))) - 1.0) * 100.0)) >= 10.0
                        ) if model_probs[idx] > 0 else False,
                        "probability_sum_by_race_v1": fmt_num(scenario_sum, 8),
                        "underround_flag_v1": underround,
                        "overround_flag_v1": overround,
                        "cap_hits_race_v1": scenario_caps[scenario_name],
                        "floor_hits_race_v1": scenario_floors[scenario_name],
                        "market_coverage_pct_race_v1": fmt_num(coverage_pct, 4),
                        "market_covered_runner_count_v1": covered_count,
                        "market_coverage_bucket_v1": coverage_group,
                        "market_eligible_race_v1": market_eligible,
                        "full_market_coverage_race_v1": full_market_coverage,
                        "market_scenario_applied_v1": scenario_market_applied[scenario_name],
                        "scenario_guardrail_v1": scenario_guardrails[scenario_name],
                    }
                )

                market_rows.append(
                    {
                        "scenario_name_v1": scenario_name,
                        "race_key": row["race_key"],
                        "race_date": row["race_date"],
                        "track": row["track"],
                        "race_no": row["race_no"],
                        "horse": row["horse"],
                        "horse_key": row["horse_key"],
                        "won": int(row["won_num"]),
                        "model_probability_v1": fmt_num(float(model_probs[idx]), 8),
                        "market_price_v1": fmt_num(row["market_price_v1"], 4),
                        "market_proxy_probability_v1": fmt_num(float(market_proxy_probs[idx]), 8),
                        "scenario_probability_v1": fmt_num(scenario_prob, 8),
                        "market_coverage_pct_race_v1": fmt_num(coverage_pct, 4),
                        "market_covered_runner_count_v1": covered_count,
                        "market_eligible_race_v1": market_eligible,
                        "full_market_coverage_race_v1": full_market_coverage,
                        "market_scenario_applied_v1": scenario_market_applied[scenario_name],
                        "scenario_guardrail_v1": scenario_guardrails[scenario_name],
                    }
                )

    return pd.DataFrame(replay_rows), pd.DataFrame(market_rows)


def load_previous_context() -> dict[str, object]:
    context: dict[str, object] = {}

    if INPUT_SUMMARY.exists():
        summary = pd.read_csv(INPUT_SUMMARY, dtype=str, keep_default_na=False, low_memory=False)
        if not summary.empty:
            recommended = summary[summary["is_recommended_candidate_v1"].map(upper).eq("TRUE")]
            if not recommended.empty:
                row = recommended.iloc[0]
                context["prior_recommendation"] = clean(row.get("final_recommendation_v1"))
                context["prior_recommended_scenario"] = clean(row.get("scenario_name_v1"))
                context["prior_short500_gap"] = clean(row.get("shortest500_implied_minus_actual_gap_pts_v1"))
                context["prior_calibration_gap"] = clean(row.get("weighted_abs_calibration_gap_pts_v1"))

    if INPUT_REPORT.exists():
        context["prior_report_excerpt"] = INPUT_REPORT.read_text(encoding="utf-8", errors="ignore")

    return context


def final_recommendation(summary: pd.DataFrame, market_audit: pd.DataFrame) -> tuple[str, str]:
    current = summary[summary["scenario_name_v1"] == CURRENT_SCENARIO].iloc[0]
    hybrid = summary[summary["scenario_name_v1"] == HYBRID_SCENARIO].iloc[0]
    market_rows_pct = float(hybrid["market_proxy_row_coverage_pct_v1"])
    full_market_races = int(hybrid["market_proxy_full_coverage_races_v1"])
    market_eligible_races = int(hybrid["market_proxy_eligible_races_v1"])

    v41_candidates = summary[
        ~summary["scenario_name_v1"].isin([CURRENT_SCENARIO, HYBRID_SCENARIO, "MARKET_ONLY_NORMALISED"])
    ].copy()

    rank1_floor = float(hybrid["rank1_win_pct"]) - 0.2
    top3_floor = float(hybrid["top3_capture_pct"]) - 0.3
    hybrid_gap = abs(float(hybrid["shortest500_gap_pts_v1"]))
    hybrid_cal = float(hybrid["calibration_error_pts_v1"])

    promotable = v41_candidates[
        (v41_candidates["rank1_win_pct"].astype(float) >= rank1_floor)
        & (v41_candidates["top3_capture_pct"].astype(float) >= top3_floor)
        & (v41_candidates["underround_race_count_v1"].astype(int) == 0)
        & (v41_candidates["overround_race_count_v1"].astype(int) == 0)
        & (v41_candidates["shortest500_gap_pts_v1"].astype(float).abs() < hybrid_gap)
        & (v41_candidates["calibration_error_pts_v1"].astype(float) <= hybrid_cal)
    ].copy()

    if not promotable.empty:
        promotable["abs_shortest500_gap_pts_v1"] = promotable["shortest500_gap_pts_v1"].astype(float).abs()
        best = promotable.sort_values(
            ["abs_shortest500_gap_pts_v1", "calibration_error_pts_v1", "rank1_win_pct"],
            ascending=[True, True, False],
        ).iloc[0]
        if market_eligible_races >= 100 and market_rows_pct >= 25.0:
            return (
                "PROMOTE_V4_1_SIDE_BY_SIDE",
                f"{best['scenario_name_v1']} improved short-price realism and calibration without breaching rank-capture guardrails.",
            )
        return (
            "MARKET_BLEND_RESEARCH_ONLY",
            f"{best['scenario_name_v1']} looked directionally promising, but market coverage in the replay proxy is too thin for a side-by-side promotion.",
        )

    if market_rows_pct < 35.0 or full_market_races == 0:
        return (
            "MARKET_BLEND_RESEARCH_ONLY",
            "Market proxy coverage is too sparse and incomplete for direct fair-price promotion. Keep market as a research pressure-test only.",
        )

    if abs(float(hybrid["shortest500_gap_pts_v1"])) < abs(float(current["shortest500_gap_pts_v1"])) or float(hybrid["calibration_error_pts_v1"]) < float(current["calibration_error_pts_v1"]):
        return (
            "PROMOTE_V4_HYBRID_SIDE_BY_SIDE",
            "The existing V4 hybrid remains the strongest safe side-by-side candidate. Market-informed variants did not beat it cleanly.",
        )

    return (
        "KEEP_CURRENT",
        "No V4.1 scenario improved realism enough without added trade-offs, so the current reference remains the safest baseline for now.",
    )


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not INPUT_REPLAY.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_REPLAY}")

    replay = pd.read_csv(INPUT_REPLAY, dtype=str, keep_default_na=False, low_memory=False)
    context = load_previous_context()

    hybrid = scenario_rows(replay, HYBRID_SCENARIO)
    if hybrid.empty:
        raise ValueError(f"Could not find {HYBRID_SCENARIO} rows in {INPUT_REPLAY}")

    base = hybrid.copy()
    base["won_num"] = pd.to_numeric(base["won"], errors="coerce").fillna(0).astype(int)
    base["placed_num"] = pd.to_numeric(base["placed"], errors="coerce").fillna(0).astype(int)
    base["market_price_v1"] = base["sp_num"].map(to_float)
    base["hybrid_probability_v1"] = pd.to_numeric(base["candidate_probability_v1"], errors="coerce").fillna(0.0)
    base["hybrid_rank_v1"] = pd.to_numeric(base["candidate_rank_v1"], errors="coerce").fillna(999).astype(int)
    base["current_probability_v1"] = pd.to_numeric(base["current_v6_1_probability_v1"], errors="coerce").fillna(0.0)
    base["projection_band"] = base["projection_band"].map(clean)
    base["rating"] = pd.to_numeric(base["rating"], errors="coerce")
    base["rating_gap"] = pd.to_numeric(base["rating_gap"], errors="coerce")

    candidate_replay, market_audit = build_scenarios(base)
    candidate_replay.to_csv(OUT_REPLAY, index=False)
    market_audit.to_csv(OUT_MARKET, index=False)

    summary_rows: list[dict[str, object]] = []
    bucket_rows: list[dict[str, object]] = []
    realism_rows: list[dict[str, object]] = []

    for scenario_name, scenario_df in candidate_replay.groupby("scenario_name_v1", dropna=False):
        scenario_df = scenario_df.copy()
        scenario_df["won_num"] = pd.to_numeric(scenario_df["won"], errors="coerce").fillna(0).astype(int)
        scenario_df["placed_num"] = pd.to_numeric(scenario_df["placed"], errors="coerce").fillna(0).astype(int)
        scenario_df["candidate_probability_v1"] = pd.to_numeric(scenario_df["candidate_probability_v1"], errors="coerce").fillna(0.0)
        scenario_df["candidate_fair_price_v1"] = pd.to_numeric(scenario_df["candidate_fair_price_v1"], errors="coerce")
        scenario_df["market_price_v1"] = pd.to_numeric(scenario_df["market_price_v1"], errors="coerce")
        scenario_df["candidate_rank_v1"] = pd.to_numeric(scenario_df["candidate_rank_v1"], errors="coerce").fillna(999).astype(int)

        metrics = race_metrics(
            frame=scenario_df,
            probability_column="candidate_probability_v1",
            rank_column="candidate_rank_v1",
            fair_column="candidate_fair_price_v1",
        )
        buckets, calibration_error = calibration_table(
            frame=scenario_df,
            scenario_name=scenario_name,
            probability_column="candidate_probability_v1",
        )
        realism = price_realism_table(
            frame=scenario_df,
            scenario_name=scenario_name,
            fair_column="candidate_fair_price_v1",
            probability_column="candidate_probability_v1",
        )
        overlay = overlay_metrics(
            frame=scenario_df,
            fair_column="candidate_fair_price_v1",
        )

        bucket_rows.extend(buckets)
        realism_rows.extend(realism)

        shortest500 = next((row for row in realism if row["tail_group_v1"] == "TOP_500_SHORTEST"), None)
        shortest100 = next((row for row in realism if row["tail_group_v1"] == "TOP_100_SHORTEST"), None)
        shortest250 = next((row for row in realism if row["tail_group_v1"] == "TOP_250_SHORTEST"), None)
        shortest1000 = next((row for row in realism if row["tail_group_v1"] == "TOP_1000_SHORTEST"), None)

        summary_rows.append(
            {
                "scenario_name_v1": scenario_name,
                "scenario_description_v1": scenario_description(scenario_name),
                "races": metrics["race_count"],
                "runners": metrics["runner_count"],
                "rank1_win_pct": metrics["rank1_win_pct"],
                "rank1_place_pct": metrics["rank1_place_pct"],
                "top3_capture_pct": metrics["top3_capture_pct"],
                "calibration_error_pts_v1": calibration_error,
                "brier_score_v1": metrics["brier_score_v1"],
                "avg_probability_sum_by_race_v1": metrics["avg_probability_sum_by_race_v1"],
                "underround_race_count_v1": metrics["underround_race_count_v1"],
                "overround_race_count_v1": metrics["overround_race_count_v1"],
                "avg_rank1_fair_price_v1": metrics["avg_rank1_fair_price_v1"],
                "median_rank1_fair_price_v1": metrics["median_rank1_fair_price_v1"],
                "shortest100_implied_prob_pct_v1": shortest100["avg_implied_prob_pct_v1"] if shortest100 else 0.0,
                "shortest100_actual_win_pct_v1": shortest100["actual_win_pct_v1"] if shortest100 else 0.0,
                "shortest100_gap_pts_v1": shortest100["implied_minus_actual_gap_pts_v1"] if shortest100 else 0.0,
                "shortest250_implied_prob_pct_v1": shortest250["avg_implied_prob_pct_v1"] if shortest250 else 0.0,
                "shortest250_actual_win_pct_v1": shortest250["actual_win_pct_v1"] if shortest250 else 0.0,
                "shortest250_gap_pts_v1": shortest250["implied_minus_actual_gap_pts_v1"] if shortest250 else 0.0,
                "shortest500_implied_prob_pct_v1": shortest500["avg_implied_prob_pct_v1"] if shortest500 else 0.0,
                "shortest500_actual_win_pct_v1": shortest500["actual_win_pct_v1"] if shortest500 else 0.0,
                "shortest500_gap_pts_v1": shortest500["implied_minus_actual_gap_pts_v1"] if shortest500 else 0.0,
                "shortest1000_implied_prob_pct_v1": shortest1000["avg_implied_prob_pct_v1"] if shortest1000 else 0.0,
                "shortest1000_actual_win_pct_v1": shortest1000["actual_win_pct_v1"] if shortest1000 else 0.0,
                "shortest1000_gap_pts_v1": shortest1000["implied_minus_actual_gap_pts_v1"] if shortest1000 else 0.0,
                "market_proxy_row_coverage_pct_v1": fmt_num(safe_pct(scenario_df["market_price_v1"].notna().sum(), len(scenario_df)), 4),
                "market_proxy_eligible_races_v1": int(scenario_df.groupby("race_key")["market_eligible_race_v1"].max().sum()),
                "market_proxy_full_coverage_races_v1": int(scenario_df.groupby("race_key")["full_market_coverage_race_v1"].max().sum()),
                "market_scenario_applied_races_v1": int(scenario_df.groupby("race_key")["market_scenario_applied_v1"].max().sum()),
                "rank_changed_runner_rows_vs_hybrid_v1": int(scenario_df["rank_changed_vs_hybrid_v1"].sum()),
                "top_pick_changed_races_vs_hybrid_v1": int(scenario_df.groupby("race_key")["top_pick_changed_race_vs_hybrid_v1"].max().sum()),
                "material_prob_move_runner_rows_v1": int(scenario_df["material_prob_move_v1"].sum()),
                "material_fair_price_move_runner_rows_v1": int(scenario_df["material_fair_price_move_v1"].sum()),
                "decision_reason_v1": scenario_description(scenario_name),
                **overlay,
                "built_at_utc_v1": built_at,
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values("scenario_name_v1")
    market_df = pd.DataFrame(market_audit)
    recommendation, recommendation_reason = final_recommendation(summary_df, market_df)
    summary_df["final_recommendation_v1"] = recommendation
    summary_df["recommendation_reason_v1"] = recommendation_reason
    summary_df.to_csv(OUT_SUMMARY, index=False)

    buckets_df = pd.DataFrame(bucket_rows).sort_values(["scenario_name_v1", "probability_bucket_v1"])
    buckets_df.to_csv(OUT_BUCKETS, index=False)

    realism_df = pd.DataFrame(realism_rows).sort_values(["scenario_name_v1", "tail_group_v1"])
    realism_df.to_csv(OUT_REALISM, index=False)

    current_row = summary_df[summary_df["scenario_name_v1"] == CURRENT_SCENARIO].iloc[0]
    hybrid_row = summary_df[summary_df["scenario_name_v1"] == HYBRID_SCENARIO].iloc[0]
    candidate_rank_df = summary_df[
        ~summary_df["scenario_name_v1"].isin([CURRENT_SCENARIO, HYBRID_SCENARIO])
    ].copy()
    candidate_rank_df["abs_shortest500_gap_pts_v1"] = candidate_rank_df["shortest500_gap_pts_v1"].astype(float).abs()
    best_marketish = candidate_rank_df.sort_values(
        ["abs_shortest500_gap_pts_v1", "calibration_error_pts_v1", "rank1_win_pct"],
        ascending=[True, True, False],
    ).iloc[0]

    report_lines = [
        "# EDGEiQ Probability Engine V4.1 Research Audit",
        "",
        f"Generated: {built_at}",
        "",
        "## Executive Summary",
        "",
        "This V4.1 sidecar audit tested whether market prices should influence EDGEiQ fair prices as a calibration prior rather than as truth.",
        "",
        f"Final recommendation: **{recommendation}**",
        "",
        f"Reason: {recommendation_reason}",
        "",
        "## Starting Point",
        "",
        f"- prior V4 recommendation: {context.get('prior_recommendation', 'UNKNOWN')}",
        f"- prior recommended scenario: {context.get('prior_recommended_scenario', HYBRID_SCENARIO)}",
        f"- current V6.1 shortest-500 gap: {current_row['shortest500_gap_pts_v1']} pts",
        f"- V4 hybrid shortest-500 gap: {hybrid_row['shortest500_gap_pts_v1']} pts",
        "",
        "## Market Coverage Constraint",
        "",
        f"- market proxy source in replay: `sp_num`",
        f"- runner-level market coverage: {hybrid_row['market_proxy_row_coverage_pct_v1']}%",
        f"- market-eligible races (>= {MARKET_MIN_COVERED_RUNNERS} runners and >= {MARKET_MIN_COVERAGE_PCT:.0f}% race coverage): {hybrid_row['market_proxy_eligible_races_v1']}",
        f"- full market coverage races: {hybrid_row['market_proxy_full_coverage_races_v1']}",
        "",
        "This means the market blend research is useful as a pressure-test, but not a clean production-grade market truth layer.",
        "",
        "## Scenario Comparison",
        "",
    ]

    for row in summary_df.itertuples(index=False):
        report_lines.append(
            f"- {row.scenario_name_v1} | rank1 {row.rank1_win_pct}% | top3 {row.top3_capture_pct}% | "
            f"calibration {row.calibration_error_pts_v1} pts | short500 gap {row.shortest500_gap_pts_v1} pts | "
            f"underround {row.underround_race_count_v1} | overround {row.overround_race_count_v1}"
        )

    report_lines.extend(
        [
            "",
            "## Best V4.1 Candidate",
            "",
            f"- scenario: {best_marketish['scenario_name_v1']}",
            f"- rank1 win %: {best_marketish['rank1_win_pct']}",
            f"- top3 capture %: {best_marketish['top3_capture_pct']}",
            f"- calibration error: {best_marketish['calibration_error_pts_v1']} pts",
            f"- shortest-500 implied minus actual gap: {best_marketish['shortest500_gap_pts_v1']} pts",
            f"- market-applied races: {best_marketish['market_scenario_applied_races_v1']}",
            "",
            "## Plain-English Answers",
            "",
            f"**Is the model overconfident at short prices?** Yes. Current V6.1 still shows a short-price gap of {current_row['shortest500_gap_pts_v1']} pts on the shortest 500 prices.",
            "",
            f"**Does market improve true calibration?** Not cleanly from this replay proxy. Market-informed scenarios can move realism a little, but the available market coverage is too sparse and incomplete to trust as a direct fair-price input.",
            "",
            "**Where should market influence EDGEiQ?** As a pressure-test on extreme short prices, and only when a race has strong, genuinely pre-result market coverage.",
            "",
            "**Where should it not?** It should not replace the rating model, it should not drive the whole race off incomplete runner coverage, and it should not be treated as truth just because a price exists.",
            "",
            f"**Exact next implementation recommendation:** {recommendation}.",
            "",
            "## Interpretation",
            "",
            "The safest current path is still to treat market as a calibration prior or guardrail, not as a ranking engine. If a future clean market warehouse delivers broad runner-level coverage, the short-price anchor idea is the right next place to test side-by-side.",
        ]
    )

    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    print("[PROBABILITY_ENGINE_V4_1_RESEARCH_AUDIT] COMPLETE")
    print(f"current_short500_gap_pts={current_row['shortest500_gap_pts_v1']}")
    print(f"hybrid_short500_gap_pts={hybrid_row['shortest500_gap_pts_v1']}")
    print(f"best_v4_1_scenario={best_marketish['scenario_name_v1']}")
    print(f"best_v4_1_short500_gap_pts={best_marketish['shortest500_gap_pts_v1']}")
    print(f"market_proxy_row_coverage_pct={hybrid_row['market_proxy_row_coverage_pct_v1']}")
    print(f"market_proxy_eligible_races={hybrid_row['market_proxy_eligible_races_v1']}")
    print(f"recommendation={recommendation}")
    print(f"wrote={OUT_REPLAY}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BUCKETS}")
    print(f"wrote={OUT_REALISM}")
    print(f"wrote={OUT_MARKET}")
    print(f"wrote={OUT_REPORT}")


if __name__ == "__main__":
    main()
