from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_V4_REPLAY = DATA / "edgeiq_probability_engine_v4_candidate_replay.csv"
INPUT_V41_REPLAY = DATA / "edgeiq_probability_engine_v4_1_candidate_replay.csv"

OUT_REPLAY = DATA / "edgeiq_probability_engine_v4_2_candidate_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_engine_v4_2_candidate_summary.csv"
OUT_BUCKETS = DATA / "edgeiq_probability_engine_v4_2_calibration_buckets.csv"
OUT_REALISM = DATA / "edgeiq_probability_engine_v4_2_price_realism.csv"
OUT_RECOMMEND = DATA / "edgeiq_probability_engine_v4_2_recommendation.csv"
OUT_REPORT = DATA / "edgeiq_probability_engine_v4_2_report.md"

CURRENT_SCENARIO = "CURRENT_V6_1_CONVERSION"
HYBRID_SCENARIO = "V4_HYBRID_RECOMMENDED"

TEMPERATURE_ALPHAS = [0.65, 0.70, 0.75, 0.80, 0.85]
BASE_CAP = 0.33
BASE_FLOOR = 0.002

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

MATERIAL_SHORT500_IMPROVEMENT_PTS = 0.50
MAX_RANK1_DROP_PTS = 0.25
MAX_TOP3_DROP_PTS = 0.50
MAX_CALIBRATION_WORSE_PTS = 0.05
MAX_TOP_PICK_CHANGE_RACE_PCT = 1.0
MAX_RANK_CHANGED_ROW_PCT = 5.0


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


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def scenario_rows(frame: pd.DataFrame, scenario_name: str) -> pd.DataFrame:
    return frame[frame["scenario_name_v1"].map(upper).eq(scenario_name.upper())].copy()


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


def stable_rank(probabilities: np.ndarray, baseline_rank: np.ndarray) -> np.ndarray:
    order = np.lexsort((baseline_rank.astype(int), -probabilities.astype(float)))
    ranks = np.empty(len(probabilities), dtype=int)
    ranks[order] = np.arange(1, len(probabilities) + 1)
    return ranks


def field_size_cap(field_size: int) -> float:
    if field_size <= 7:
        return 0.36
    if field_size <= 10:
        return 0.33
    if field_size <= 13:
        return 0.30
    return 0.27


def uncertainty_cap(field_size: int, top_gap: float, entropy_ratio: float) -> float:
    cap = field_size_cap(field_size)
    if top_gap <= 0.04:
        cap -= 0.03
    elif top_gap <= 0.07:
        cap -= 0.02
    elif top_gap <= 0.10:
        cap -= 0.01

    if entropy_ratio >= 0.92:
        cap -= 0.02
    elif entropy_ratio >= 0.85:
        cap -= 0.01

    return max(0.24, min(cap, 0.36))


def compute_entropy_ratio(probabilities: np.ndarray) -> float:
    p = normalize(probabilities)
    if len(p) <= 1:
        return 0.0
    entropy = -float(np.sum(p * np.log(np.clip(p, 1e-12, None))))
    return entropy / math.log(len(p))


def race_metrics(frame: pd.DataFrame, probability_column: str, rank_column: str, fair_column: str) -> dict[str, float]:
    race_count = int(frame["race_key"].nunique())
    runner_count = int(len(frame))

    rank1_rows = frame[frame[rank_column] == 1].copy()
    winner_rows = frame[frame["won_num"] == 1].copy()

    rank1_win_pct = safe_pct(rank1_rows["won_num"].sum(), len(rank1_rows))
    top2_capture_pct = safe_pct((winner_rows[rank_column] <= 2).sum(), race_count)
    top3_capture_pct = safe_pct((winner_rows[rank_column] <= 3).sum(), race_count)

    probs = pd.to_numeric(frame[probability_column], errors="coerce").fillna(0.0)
    won = frame["won_num"].astype(float)
    brier = float(np.mean(np.square(probs - won))) if len(frame) else 0.0

    race_sums = frame.groupby("race_key", dropna=False)[probability_column].sum(min_count=1)
    race_sums = pd.to_numeric(race_sums, errors="coerce").fillna(0.0)

    fair_rank1 = pd.to_numeric(rank1_rows[fair_column], errors="coerce").dropna()

    return {
        "races": race_count,
        "runners": runner_count,
        "rank1_win_pct": fmt_num(rank1_win_pct, 4),
        "top2_capture_pct": fmt_num(top2_capture_pct, 4),
        "top3_capture_pct": fmt_num(top3_capture_pct, 4),
        "brier_score_v1": fmt_num(brier, 6),
        "avg_probability_sum_by_race_v1": fmt_num(float(race_sums.mean()) if len(race_sums) else 0.0, 6),
        "underround_races": int((race_sums < 0.999).sum()),
        "overround_races": int((race_sums > 1.001).sum()),
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

    return rows


def scenario_description(name: str, chosen_alpha: float | None = None) -> str:
    descriptions = {
        CURRENT_SCENARIO: "Current V6.1 conversion reference with original cap and no-renormalisation behaviour.",
        HYBRID_SCENARIO: "Existing V4 hybrid baseline with cap, floor, and race-level renormalisation.",
        "GAP_COMPRESS_LOGISTIC": "Monotonic logistic compression of rating gaps, then bounded and renormalised.",
        "GAP_COMPRESS_SQRT": "Monotonic square-root compression of shifted rating gaps, then bounded and renormalised.",
        "DYNAMIC_FIELD_CAP": "V4 hybrid probabilities with field-size-dependent favourite caps and stable floor.",
        "DYNAMIC_UNCERTAINTY_CAP": "V4 hybrid probabilities with lower caps in uncertain races using top-gap and entropy guardrails.",
    }
    if name.startswith("TEMPERATURE_SOFT_"):
        return f"Rank-preserving temperature softening via probability power alpha={name.split('_')[-2]}.{name.split('_')[-1]} from the V4 hybrid baseline."
    if name == "HYBRID_BEST":
        alpha_text = f"{chosen_alpha:.2f}" if chosen_alpha is not None else "N/A"
        return f"Best combined candidate: V4 hybrid baseline with temperature alpha={alpha_text} plus dynamic uncertainty cap."
    return descriptions.get(name, name)


def build_base_frame() -> pd.DataFrame:
    replay_v41 = load_required_csv(INPUT_V41_REPLAY)
    replay_v4 = load_required_csv(INPUT_V4_REPLAY)

    hybrid = scenario_rows(replay_v41, HYBRID_SCENARIO)
    if hybrid.empty:
        hybrid = scenario_rows(replay_v4, HYBRID_SCENARIO)
    if hybrid.empty:
        raise RuntimeError("Could not locate V4_HYBRID_RECOMMENDED rows in replay inputs.")

    current = scenario_rows(replay_v41, CURRENT_SCENARIO)
    if current.empty:
        current = scenario_rows(replay_v4, CURRENT_SCENARIO)
    if current.empty:
        raise RuntimeError("Could not locate CURRENT_V6_1_CONVERSION rows in replay inputs.")

    hybrid = hybrid.copy()
    current = current.copy()

    key_cols = ["race_key", "horse_key"]
    current_lookup = current[key_cols + ["candidate_rank_v1"]].copy()
    current_lookup = current_lookup.rename(columns={"candidate_rank_v1": "current_v6_1_rank_v1"})

    keep_cols = [
        "race_key",
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "projection_band",
        "rating",
        "rating_gap",
        "won",
        "placed",
        "current_v6_1_probability_v1",
        "current_v6_1_fair_price_v1",
        "candidate_probability_v1",
        "candidate_fair_price_v1",
        "candidate_rank_v1",
        "market_price_v1",
        "sp_num",
    ]
    available_cols = [col for col in keep_cols if col in hybrid.columns]
    base = hybrid[available_cols].copy()
    base = base.rename(
        columns={
            "candidate_probability_v1": "hybrid_probability_v1",
            "candidate_fair_price_v1": "hybrid_fair_price_v1",
            "candidate_rank_v1": "hybrid_rank_v1",
        }
    )
    base = base.merge(current_lookup, on=key_cols, how="left")

    base["won_num"] = pd.to_numeric(base["won"], errors="coerce").fillna(0).astype(int)
    base["placed_num"] = pd.to_numeric(base["placed"], errors="coerce").fillna(0).astype(int)
    base["rating_num"] = pd.to_numeric(base["rating"], errors="coerce").fillna(0.0)
    base["rating_gap_num"] = pd.to_numeric(base["rating_gap"], errors="coerce").fillna(0.0)
    base["hybrid_probability_v1"] = pd.to_numeric(base["hybrid_probability_v1"], errors="coerce").fillna(0.0)
    base["hybrid_fair_price_v1"] = pd.to_numeric(base["hybrid_fair_price_v1"], errors="coerce")
    base["hybrid_rank_v1"] = pd.to_numeric(base["hybrid_rank_v1"], errors="coerce").fillna(0).astype(int)
    base["current_v6_1_probability_v1"] = pd.to_numeric(base["current_v6_1_probability_v1"], errors="coerce").fillna(0.0)
    base["current_v6_1_fair_price_v1"] = pd.to_numeric(base["current_v6_1_fair_price_v1"], errors="coerce")
    base["current_v6_1_rank_v1"] = pd.to_numeric(base["current_v6_1_rank_v1"], errors="coerce").fillna(0).astype(int)

    base["field_size_v1"] = base.groupby("race_key", dropna=False)["horse_key"].transform("count").astype(int)

    top_gaps: list[float] = []
    entropy_values: list[float] = []
    for _, race in base.groupby("race_key", dropna=False):
        probs = race["hybrid_probability_v1"].to_numpy(dtype=float)
        sorted_probs = np.sort(probs)[::-1]
        top_gap = float(sorted_probs[0] - sorted_probs[1]) if len(sorted_probs) >= 2 else float(sorted_probs[0])
        entropy = compute_entropy_ratio(probs)
        top_gaps.extend([top_gap] * len(race))
        entropy_values.extend([entropy] * len(race))

    base["hybrid_top_gap_v1"] = top_gaps
    base["hybrid_entropy_ratio_v1"] = entropy_values
    return base


def temperature_transform(probabilities: np.ndarray, alpha: float) -> np.ndarray:
    weights = np.power(np.clip(probabilities.astype(float), 1e-12, None), alpha)
    return weights


def logistic_gap_transform(rating_gaps: np.ndarray) -> np.ndarray:
    values = rating_gaps.astype(float)
    scale = max(float(np.std(values)), 1.0)
    centered = values - float(np.mean(values))
    weights = 1.0 / (1.0 + np.exp(-(centered / scale)))
    return np.clip(weights, 1e-6, None)


def sqrt_gap_transform(rating_gaps: np.ndarray) -> np.ndarray:
    values = rating_gaps.astype(float)
    shifted = values - float(values.min()) + 1.0
    return np.sqrt(np.clip(shifted, 1e-6, None))


def build_scenario_replay(
    base: pd.DataFrame,
    scenario_name: str,
    description: str,
    chosen_alpha: float | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for race_key, race in base.groupby("race_key", dropna=False):
        race = race.copy().reset_index(drop=True)
        hybrid_probs = race["hybrid_probability_v1"].to_numpy(dtype=float)
        current_probs = race["current_v6_1_probability_v1"].to_numpy(dtype=float)
        hybrid_rank = race["hybrid_rank_v1"].to_numpy(dtype=int)
        rating_gaps = race["rating_gap_num"].to_numpy(dtype=float)
        field_size = int(race["field_size_v1"].iloc[0])
        top_gap = float(race["hybrid_top_gap_v1"].iloc[0])
        entropy_ratio = float(race["hybrid_entropy_ratio_v1"].iloc[0])

        cap = BASE_CAP
        floor = BASE_FLOOR
        cap_hits = 0
        floor_hits = 0

        if scenario_name == CURRENT_SCENARIO:
            candidate_probs = current_probs.copy()
            candidate_ranks = stable_rank(candidate_probs, hybrid_rank)
            prob_sum = float(candidate_probs.sum())
            underround = prob_sum < 0.999
            overround = prob_sum > 1.001
        else:
            if scenario_name == HYBRID_SCENARIO:
                weights = hybrid_probs.copy()
            elif scenario_name.startswith("TEMPERATURE_SOFT_"):
                alpha = float(scenario_name.replace("TEMPERATURE_SOFT_", "").replace("_", "."))
                weights = temperature_transform(hybrid_probs, alpha)
            elif scenario_name == "GAP_COMPRESS_LOGISTIC":
                weights = logistic_gap_transform(rating_gaps)
            elif scenario_name == "GAP_COMPRESS_SQRT":
                weights = sqrt_gap_transform(rating_gaps)
            elif scenario_name == "DYNAMIC_FIELD_CAP":
                weights = hybrid_probs.copy()
                cap = field_size_cap(field_size)
            elif scenario_name == "DYNAMIC_UNCERTAINTY_CAP":
                weights = hybrid_probs.copy()
                cap = uncertainty_cap(field_size, top_gap, entropy_ratio)
            elif scenario_name == "HYBRID_BEST":
                alpha = chosen_alpha if chosen_alpha is not None else 0.80
                weights = temperature_transform(hybrid_probs, alpha)
                cap = uncertainty_cap(field_size, top_gap, entropy_ratio)
            else:
                raise ValueError(f"Unknown scenario: {scenario_name}")

            candidate_probs, cap_hits, floor_hits = bounded_probs(weights, floor=floor, cap=cap)
            candidate_ranks = stable_rank(candidate_probs, hybrid_rank)
            prob_sum = float(candidate_probs.sum())
            underround = prob_sum < 0.999
            overround = prob_sum > 1.001

        fair_prices = np.where(candidate_probs > 0, 1.0 / candidate_probs, np.nan)
        hybrid_top_horse = race.loc[race["hybrid_rank_v1"] == 1, "horse_key"].iloc[0] if (race["hybrid_rank_v1"] == 1).any() else ""
        candidate_top_horse = race.loc[np.argmin(candidate_ranks), "horse_key"] if len(race) else ""
        top_pick_changed = clean(candidate_top_horse) != clean(hybrid_top_horse)

        for idx, row in race.iterrows():
            candidate_prob = float(candidate_probs[idx])
            candidate_fair = float(fair_prices[idx]) if math.isfinite(float(fair_prices[idx])) else None
            hybrid_prob = float(row["hybrid_probability_v1"])
            hybrid_fair = to_float(row["hybrid_fair_price_v1"])
            fair_change_pct = None
            if hybrid_fair and hybrid_fair > 0 and candidate_fair is not None:
                fair_change_pct = ((candidate_fair - hybrid_fair) / hybrid_fair) * 100.0

            rows.append(
                {
                    "scenario_name_v1": scenario_name,
                    "scenario_description_v1": description,
                    "race_key": row["race_key"],
                    "race_date": row["race_date"],
                    "track": row["track"],
                    "race_no": row.get("race_no", ""),
                    "horse": row["horse"],
                    "horse_key": row["horse_key"],
                    "projection_band": row.get("projection_band", ""),
                    "rating": fmt_num(row["rating_num"], 4),
                    "rating_gap": fmt_num(row["rating_gap_num"], 4),
                    "won": row["won"],
                    "placed": row["placed"],
                    "won_num": int(row["won_num"]),
                    "placed_num": int(row["placed_num"]),
                    "field_size_v1": field_size,
                    "hybrid_top_gap_v1": fmt_num(top_gap, 6),
                    "hybrid_entropy_ratio_v1": fmt_num(entropy_ratio, 6),
                    "current_v6_1_probability_v1": fmt_num(row["current_v6_1_probability_v1"], 8),
                    "current_v6_1_fair_price_v1": fmt_num(to_float(row["current_v6_1_fair_price_v1"]), 8),
                    "current_v6_1_rank_v1": int(row["current_v6_1_rank_v1"]),
                    "hybrid_probability_v1": fmt_num(hybrid_prob, 8),
                    "hybrid_fair_price_v1": fmt_num(hybrid_fair, 8),
                    "hybrid_rank_v1": int(row["hybrid_rank_v1"]),
                    "candidate_probability_v1": fmt_num(candidate_prob, 8),
                    "candidate_fair_price_v1": fmt_num(candidate_fair, 8),
                    "candidate_rank_v1": int(candidate_ranks[idx]),
                    "probability_delta_pts_vs_hybrid_v1": fmt_num((candidate_prob - hybrid_prob) * 100.0, 4),
                    "fair_price_change_pct_vs_hybrid_v1": fmt_num(fair_change_pct, 4),
                    "rank_changed_vs_hybrid_v1": bool(int(candidate_ranks[idx]) != int(row["hybrid_rank_v1"])),
                    "top_pick_changed_race_vs_hybrid_v1": bool(top_pick_changed),
                    "material_prob_move_v1": abs((candidate_prob - hybrid_prob) * 100.0) >= 2.0,
                    "material_fair_price_move_v1": abs(fair_change_pct or 0.0) >= 10.0 if fair_change_pct is not None else False,
                    "probability_sum_by_race_v1": fmt_num(prob_sum, 8),
                    "underround_flag_v1": bool(underround),
                    "overround_flag_v1": bool(overround),
                    "cap_hits_race_v1": int(cap_hits),
                    "floor_hits_race_v1": int(floor_hits),
                    "applied_cap_v1": fmt_num(cap, 4),
                    "applied_floor_v1": fmt_num(floor, 4),
                    "market_price_v1": row.get("market_price_v1", ""),
                    "sp_num": row.get("sp_num", ""),
                }
            )

    return pd.DataFrame(rows)


def choose_best_temperature(summary_lookup: dict[str, dict[str, object]], baseline_short500_gap: float) -> float:
    candidate_rows: list[tuple[float, float, float, float]] = []
    for alpha in TEMPERATURE_ALPHAS:
        scenario_name = f"TEMPERATURE_SOFT_{str(alpha).replace('.', '_')}"
        summary = summary_lookup.get(scenario_name)
        if not summary:
            continue
        gap = float(summary.get("shortest_500_gap_pts_v1", 999.0))
        rank1 = float(summary.get("rank1_win_pct", 0.0))
        calibration = float(summary.get("calibration_error_pts_v1", 999.0))
        candidate_rows.append((alpha, gap, rank1, calibration))

    if not candidate_rows:
        return 0.80

    candidate_rows.sort(key=lambda item: (item[1], -item[2], item[3], abs(item[0] - 0.80)))

    viable = [row for row in candidate_rows if (baseline_short500_gap - row[1]) >= 0.25]
    return viable[0][0] if viable else candidate_rows[0][0]


def build_summary(replay: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    bucket_rows: list[dict[str, object]] = []
    realism_rows: list[dict[str, object]] = []

    for scenario_name, scenario_frame in replay.groupby("scenario_name_v1", dropna=False):
        scenario_frame = scenario_frame.copy()
        metrics = race_metrics(
            scenario_frame,
            probability_column="candidate_probability_v1",
            rank_column="candidate_rank_v1",
            fair_column="candidate_fair_price_v1",
        )
        bucket_table, calibration_error = calibration_table(
            scenario_frame,
            scenario_name=scenario_name,
            probability_column="candidate_probability_v1",
        )
        realism_table = price_realism_table(
            scenario_frame,
            scenario_name=scenario_name,
            fair_column="candidate_fair_price_v1",
            probability_column="candidate_probability_v1",
        )

        bucket_rows.extend(bucket_table)
        realism_rows.extend(realism_table)

        shortest_lookup = {
            row["tail_group_v1"]: row for row in realism_table
        }
        summary_rows.append(
            {
                "scenario_name_v1": scenario_name,
                "scenario_description_v1": clean(scenario_frame["scenario_description_v1"].iloc[0]),
                "races": metrics["races"],
                "runners": metrics["runners"],
                "rank1_win_pct": metrics["rank1_win_pct"],
                "top2_capture_pct": metrics["top2_capture_pct"],
                "top3_capture_pct": metrics["top3_capture_pct"],
                "calibration_error_pts_v1": fmt_num(calibration_error, 4),
                "brier_score_v1": metrics["brier_score_v1"],
                "avg_probability_sum_by_race_v1": metrics["avg_probability_sum_by_race_v1"],
                "underround_races": metrics["underround_races"],
                "overround_races": metrics["overround_races"],
                "avg_rank1_fair_price_v1": metrics["avg_rank1_fair_price_v1"],
                "median_rank1_fair_price_v1": metrics["median_rank1_fair_price_v1"],
                "shortest_100_gap_pts_v1": shortest_lookup.get("TOP_100_SHORTEST", {}).get("implied_minus_actual_gap_pts_v1"),
                "shortest_250_gap_pts_v1": shortest_lookup.get("TOP_250_SHORTEST", {}).get("implied_minus_actual_gap_pts_v1"),
                "shortest_500_gap_pts_v1": shortest_lookup.get("TOP_500_SHORTEST", {}).get("implied_minus_actual_gap_pts_v1"),
                "shortest_1000_gap_pts_v1": shortest_lookup.get("TOP_1000_SHORTEST", {}).get("implied_minus_actual_gap_pts_v1"),
                "rank_changed_rows_v1": int(scenario_frame["rank_changed_vs_hybrid_v1"].fillna(False).astype(bool).sum()),
                "rank_changed_rows_pct_v1": fmt_num(
                    safe_pct(
                        scenario_frame["rank_changed_vs_hybrid_v1"].fillna(False).astype(bool).sum(),
                        len(scenario_frame),
                    ),
                    4,
                ),
                "top_pick_changed_races_v1": int(
                    scenario_frame.groupby("race_key", dropna=False)["top_pick_changed_race_vs_hybrid_v1"]
                    .max()
                    .fillna(False)
                    .astype(bool)
                    .sum()
                ),
                "top_pick_changed_races_pct_v1": fmt_num(
                    safe_pct(
                        scenario_frame.groupby("race_key", dropna=False)["top_pick_changed_race_vs_hybrid_v1"]
                        .max()
                        .fillna(False)
                        .astype(bool)
                        .sum(),
                        scenario_frame["race_key"].nunique(),
                    ),
                    4,
                ),
                "material_prob_move_rows_v1": int(scenario_frame["material_prob_move_v1"].fillna(False).astype(bool).sum()),
                "material_fair_price_move_rows_v1": int(scenario_frame["material_fair_price_move_v1"].fillna(False).astype(bool).sum()),
                "avg_applied_cap_v1": fmt_num(pd.to_numeric(scenario_frame["applied_cap_v1"], errors="coerce").mean(), 4),
                "avg_applied_floor_v1": fmt_num(pd.to_numeric(scenario_frame["applied_floor_v1"], errors="coerce").mean(), 4),
            }
        )

    return (
        pd.DataFrame(summary_rows).sort_values("scenario_name_v1").reset_index(drop=True),
        pd.DataFrame(bucket_rows).sort_values(["scenario_name_v1", "probability_bucket_v1"]).reset_index(drop=True),
        pd.DataFrame(realism_rows).sort_values(["scenario_name_v1", "tail_group_v1"]).reset_index(drop=True),
    )


def choose_recommendation(summary: pd.DataFrame) -> pd.DataFrame:
    lookup = {
        clean(row["scenario_name_v1"]): row
        for row in summary.to_dict("records")
    }

    hybrid = lookup[HYBRID_SCENARIO]
    hybrid_gap = float(hybrid["shortest_500_gap_pts_v1"])
    hybrid_rank1 = float(hybrid["rank1_win_pct"])
    hybrid_top3 = float(hybrid["top3_capture_pct"])
    hybrid_calibration = float(hybrid["calibration_error_pts_v1"])

    candidate_rows: list[dict[str, object]] = []
    for row in summary.to_dict("records"):
        scenario_name = clean(row["scenario_name_v1"])
        if scenario_name in {CURRENT_SCENARIO, HYBRID_SCENARIO}:
            continue

        shortest_gap = float(row["shortest_500_gap_pts_v1"])
        calibration = float(row["calibration_error_pts_v1"])
        rank1 = float(row["rank1_win_pct"])
        top3 = float(row["top3_capture_pct"])
        underround = int(row["underround_races"])
        overround = int(row["overround_races"])
        rank_changed_pct = float(row["rank_changed_rows_pct_v1"])
        top_pick_changed_pct = float(row["top_pick_changed_races_pct_v1"])

        shortest_improvement = hybrid_gap - shortest_gap
        rank1_delta = rank1 - hybrid_rank1
        top3_delta = top3 - hybrid_top3
        calibration_delta = calibration - hybrid_calibration

        pass_guardrails = (
            shortest_improvement >= MATERIAL_SHORT500_IMPROVEMENT_PTS
            and rank1_delta >= -MAX_RANK1_DROP_PTS
            and top3_delta >= -MAX_TOP3_DROP_PTS
            and calibration_delta <= MAX_CALIBRATION_WORSE_PTS
            and underround == 0
            and overround == 0
            and rank_changed_pct <= MAX_RANK_CHANGED_ROW_PCT
            and top_pick_changed_pct <= MAX_TOP_PICK_CHANGE_RACE_PCT
        )

        candidate_rows.append(
            {
                "scenario_name_v1": scenario_name,
                "shortest_500_improvement_pts_v1": fmt_num(shortest_improvement, 4),
                "rank1_delta_pts_v1": fmt_num(rank1_delta, 4),
                "top3_delta_pts_v1": fmt_num(top3_delta, 4),
                "calibration_delta_pts_v1": fmt_num(calibration_delta, 4),
                "underround_races": underround,
                "overround_races": overround,
                "rank_changed_rows_pct_v1": fmt_num(rank_changed_pct, 4),
                "top_pick_changed_races_pct_v1": fmt_num(top_pick_changed_pct, 4),
                "passes_promotion_gate_v1": "YES" if pass_guardrails else "NO",
            }
        )

    candidate_df = pd.DataFrame(candidate_rows)
    if not candidate_df.empty:
        raw_best = candidate_df.sort_values(
            by=[
                "shortest_500_improvement_pts_v1",
                "calibration_delta_pts_v1",
                "rank1_delta_pts_v1",
                "top3_delta_pts_v1",
            ],
            ascending=[False, True, False, False],
        ).iloc[0]
    else:
        raw_best = {
            "scenario_name_v1": HYBRID_SCENARIO,
            "shortest_500_improvement_pts_v1": 0.0,
            "rank1_delta_pts_v1": 0.0,
            "top3_delta_pts_v1": 0.0,
            "calibration_delta_pts_v1": 0.0,
        }
    passed = candidate_df[candidate_df["passes_promotion_gate_v1"] == "YES"].copy()

    if not passed.empty:
        passed = passed.sort_values(
            by=[
                "shortest_500_improvement_pts_v1",
                "calibration_delta_pts_v1",
                "rank1_delta_pts_v1",
                "top3_delta_pts_v1",
            ],
            ascending=[False, True, False, False],
        ).reset_index(drop=True)
        best_name = clean(passed.iloc[0]["scenario_name_v1"])
        safe_next_step = "SIDE_BY_SIDE_ONLY"
        research_decision = "PROMOTE_TO_SIDE_BY_SIDE"
        why = "This candidate materially reduces the shortest-500 short-price gap while holding rank and capture guardrails."
    else:
        best_name = HYBRID_SCENARIO
        safe_next_step = "KEEP_CURRENT"
        research_decision = "KEEP_V4_HYBRID_RECOMMENDED"
        why = "No candidate improved short-price realism enough without giving back too much rank/capture quality or calibration safety."

    best_row = lookup[best_name]
    recommendation = pd.DataFrame(
        [
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "baseline_scenario_v1": HYBRID_SCENARIO,
                "recommended_scenario_v1": best_name,
                "research_decision_v1": research_decision,
                "safe_next_step_v1": safe_next_step,
                "baseline_shortest_500_gap_pts_v1": fmt_num(hybrid_gap, 4),
                "recommended_shortest_500_gap_pts_v1": best_row["shortest_500_gap_pts_v1"],
                "recommended_rank1_win_pct": best_row["rank1_win_pct"],
                "recommended_top3_capture_pct": best_row["top3_capture_pct"],
                "recommended_calibration_error_pts_v1": best_row["calibration_error_pts_v1"],
                "recommended_underround_races": best_row["underround_races"],
                "recommended_overround_races": best_row["overround_races"],
                "raw_best_realism_scenario_v1": raw_best["scenario_name_v1"],
                "raw_best_realism_shortest_500_improvement_pts_v1": raw_best["shortest_500_improvement_pts_v1"],
                "raw_best_realism_rank1_delta_pts_v1": raw_best["rank1_delta_pts_v1"],
                "raw_best_realism_top3_delta_pts_v1": raw_best["top3_delta_pts_v1"],
                "raw_best_realism_calibration_delta_pts_v1": raw_best["calibration_delta_pts_v1"],
                "why_v1": why,
            }
        ]
    )

    if not candidate_df.empty:
        recommendation = pd.concat([recommendation, candidate_df], ignore_index=True, sort=False)

    return recommendation


def write_report(summary: pd.DataFrame, recommendation: pd.DataFrame, chosen_alpha: float) -> None:
    lookup = {
        clean(row["scenario_name_v1"]): row
        for row in summary.to_dict("records")
    }
    current = lookup[CURRENT_SCENARIO]
    hybrid = lookup[HYBRID_SCENARIO]
    best = recommendation.iloc[0]
    best_name = clean(best["recommended_scenario_v1"])
    best_row = lookup.get(best_name, hybrid)
    raw_best_name = clean(best.get("raw_best_realism_scenario_v1", best_name))
    raw_best_row = lookup.get(raw_best_name, best_row)

    comparison_lines = []
    ordered = [
        CURRENT_SCENARIO,
        HYBRID_SCENARIO,
        *[f"TEMPERATURE_SOFT_{str(alpha).replace('.', '_')}" for alpha in TEMPERATURE_ALPHAS],
        "GAP_COMPRESS_LOGISTIC",
        "GAP_COMPRESS_SQRT",
        "DYNAMIC_FIELD_CAP",
        "DYNAMIC_UNCERTAINTY_CAP",
        "HYBRID_BEST",
    ]
    for name in ordered:
        row = lookup.get(name)
        if not row:
            continue
        comparison_lines.append(
            f"- {name} | rank1 {row['rank1_win_pct']}% | top3 {row['top3_capture_pct']}% | "
            f"calibration {row['calibration_error_pts_v1']} pts | shortest500 gap {row['shortest_500_gap_pts_v1']} pts | "
            f"underround {row['underround_races']} | overround {row['overround_races']}"
        )

    report = f"""# EDGEiQ Probability Engine V4.2 Rank-Preserving Calibration

Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}

## Executive Summary

This V4.2 research audit tested non-market, rank-preserving probability calibration candidates using only historical replay data.

Final research decision: **{best['research_decision_v1']}**

Safe next step: **{best['safe_next_step_v1']}**

Recommended scenario: **{best_name}**

## Why Short Favourites Still Look Overconfident

Short favourites remain too aggressive because the existing conversion still concentrates too much probability mass at the top of the race. That shows up clearly in the shortest-price realism test:

- current V6.1 shortest-500 implied minus actual gap: {current['shortest_500_gap_pts_v1']} pts
- V4 hybrid shortest-500 implied minus actual gap: {hybrid['shortest_500_gap_pts_v1']} pts

That means the very shortest EDGEiQ prices still imply more wins than they historically deliver, even after the V4 hybrid fixes rounding and race normalisation.

## Candidate Comparison

{chr(10).join(comparison_lines)}

## Best Raw Realism Candidate

- scenario: {raw_best_name}
- shortest-500 gap: {raw_best_row['shortest_500_gap_pts_v1']} pts
- improvement vs V4 hybrid: {best.get('raw_best_realism_shortest_500_improvement_pts_v1', 0.0)} pts
- rank1 delta vs V4 hybrid: {best.get('raw_best_realism_rank1_delta_pts_v1', 0.0)} pts
- top3 delta vs V4 hybrid: {best.get('raw_best_realism_top3_delta_pts_v1', 0.0)} pts
- calibration delta vs V4 hybrid: {best.get('raw_best_realism_calibration_delta_pts_v1', 0.0)} pts

## Recommended Scenario

- scenario: {best_name}
- shortest-500 gap: {best_row['shortest_500_gap_pts_v1']} pts
- rank1 win %: {best_row['rank1_win_pct']}
- top3 capture %: {best_row['top3_capture_pct']}
- calibration error: {best_row['calibration_error_pts_v1']} pts
- rank changed rows % vs hybrid: {best_row['rank_changed_rows_pct_v1']}
- top-pick changed races % vs hybrid: {best_row['top_pick_changed_races_pct_v1']}

Chosen temperature for the combined hybrid candidate: {chosen_alpha:.2f}

## Trade-Off

The best non-market candidate tries to soften the top end without scrambling race order. The trade-off is simple:

- if we soften too lightly, the shortest-price realism barely moves
- if we soften too hard, rank1 win % and top3 capture start giving back useful signal

This is why the recommendation stays conservative unless a candidate clears both realism and rank-preservation guardrails.

## Plain-English Recommendation

**Should EDGEiQ keep using market as a pricing anchor?** No for production. Market remains a sanity-check only, not a required input to this candidate.

**Which candidate best fixes short-price overconfidence on raw realism?** {raw_best_name}

**Why was it not promoted?** Because the improvement versus the V4 hybrid baseline was not material enough to clear the side-by-side gate once the guardrails were applied.

**What exact safe next step should happen now?** {best['safe_next_step_v1']}

## Interpretation

- **KEEP_CURRENT** means no V4.2 candidate beat the V4 hybrid baseline cleanly enough.
- **SIDE_BY_SIDE_ONLY** means the candidate is good enough to observe beside V4 hybrid, but not to replace live pricing.
- **PROMOTE_RESEARCH_TO_LIVE_CANDIDATE** would require stronger proof than this audit alone.

For this run, the safest answer is: **{best['safe_next_step_v1']}**.
"""
    OUT_REPORT.write_text(report, encoding="utf-8")


def main() -> None:
    base = build_base_frame()

    scenario_frames: list[pd.DataFrame] = []
    base_scenarios = [
        CURRENT_SCENARIO,
        HYBRID_SCENARIO,
        *[f"TEMPERATURE_SOFT_{str(alpha).replace('.', '_')}" for alpha in TEMPERATURE_ALPHAS],
        "GAP_COMPRESS_LOGISTIC",
        "GAP_COMPRESS_SQRT",
        "DYNAMIC_FIELD_CAP",
        "DYNAMIC_UNCERTAINTY_CAP",
    ]

    for scenario_name in base_scenarios:
        scenario_frames.append(
            build_scenario_replay(
                base=base,
                scenario_name=scenario_name,
                description=scenario_description(scenario_name),
            )
        )

    preliminary_replay = pd.concat(scenario_frames, ignore_index=True)
    preliminary_summary, _, _ = build_summary(preliminary_replay)
    summary_lookup = {
        clean(row["scenario_name_v1"]): row
        for row in preliminary_summary.to_dict("records")
    }

    chosen_alpha = choose_best_temperature(
        summary_lookup=summary_lookup,
        baseline_short500_gap=float(summary_lookup[HYBRID_SCENARIO]["shortest_500_gap_pts_v1"]),
    )

    hybrid_best_frame = build_scenario_replay(
        base=base,
        scenario_name="HYBRID_BEST",
        description=scenario_description("HYBRID_BEST", chosen_alpha=chosen_alpha),
        chosen_alpha=chosen_alpha,
    )
    replay = pd.concat([preliminary_replay, hybrid_best_frame], ignore_index=True)

    summary, buckets, realism = build_summary(replay)
    recommendation = choose_recommendation(summary)

    replay.to_csv(OUT_REPLAY, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    buckets.to_csv(OUT_BUCKETS, index=False)
    realism.to_csv(OUT_REALISM, index=False)
    recommendation.to_csv(OUT_RECOMMEND, index=False)
    write_report(summary, recommendation, chosen_alpha=chosen_alpha)

    final = recommendation.iloc[0]
    print("[PROBABILITY_ENGINE_V4_2_RANK_PRESERVING_CALIBRATION] COMPLETE")
    print(f"recommended_scenario={final['recommended_scenario_v1']}")
    print(f"research_decision={final['research_decision_v1']}")
    print(f"safe_next_step={final['safe_next_step_v1']}")
    print(f"baseline_shortest_500_gap_pts={final['baseline_shortest_500_gap_pts_v1']}")
    print(f"recommended_shortest_500_gap_pts={final['recommended_shortest_500_gap_pts_v1']}")
    print(f"recommended_rank1_win_pct={final['recommended_rank1_win_pct']}")
    print(f"recommended_top3_capture_pct={final['recommended_top3_capture_pct']}")
    print(f"recommended_calibration_error_pts={final['recommended_calibration_error_pts_v1']}")
    print(f"wrote={OUT_REPLAY}")


if __name__ == "__main__":
    main()
