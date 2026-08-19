from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

INPUT_PROJECTION_AUDIT = DATA / "edgeiq_projection_calibration_audit_v1.csv"
INPUT_GAP_DISTRIBUTION = DATA / "edgeiq_projection_gap_distribution_v1.csv"
INPUT_CONVERSION_AUDIT = DATA / "edgeiq_probability_conversion_audit_v1.csv"
INPUT_PRICE_REALISM = DATA / "edgeiq_price_realism_audit_v1.csv"
INPUT_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"
INPUT_ARCHIVE = DATA / "edgeiq_historical_race_shape_archive_v1.csv"
INPUT_CALENDAR = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"

BUILDER_FAIR = SCRIPTS / "build_edgeiq_current_fair_prices_v6_1_research_replay.py"
BUILDER_BACKTEST = SCRIPTS / "build_edgeiq_projection_v6_1_research_prior_rating_backtest.py"

OUT_REPLAY = DATA / "edgeiq_probability_engine_v4_candidate_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_engine_v4_candidate_summary.csv"
OUT_BUCKETS = DATA / "edgeiq_probability_engine_v4_calibration_buckets.csv"
OUT_REALISM = DATA / "edgeiq_probability_engine_v4_price_realism.csv"
OUT_RECOMMENDED = DATA / "edgeiq_probability_engine_v4_recommended_sidecar.csv"
OUT_REPORT = DATA / "edgeiq_probability_engine_v4_report.md"

SOFTMAX_TEMPERATURES = [4, 5, 6, 7, 8, 10, 12]
POWER_SHRINK_ALPHAS = [0.75, 0.80, 0.85, 0.90, 0.95]

CURRENT_POWER_STANDARD = 0.55
CURRENT_POWER_WEAK = 0.35
CURRENT_WEAK_GAP_THRESHOLD = 2.0
CURRENT_CAP = 0.35

HYBRID_CAP = 0.33
HYBRID_FLOOR = 0.002

LOGISTIC_MIN_RUNNERS_PER_BIN = 250
LOGISTIC_MIN_RACES_PER_BIN = 50

CALIBRATION_BUCKETS = [
    (0.00, 0.02, "0_2"),
    (0.02, 0.05, "2_5"),
    (0.05, 0.08, "5_8"),
    (0.08, 0.12, "8_12"),
    (0.12, 0.18, "12_18"),
    (0.18, 0.25, "18_25"),
    (0.25, 0.35, "25_35"),
    (0.35, 1.01, "35_PLUS"),
]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def norm_track(value: object) -> str:
    text = upper(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"\s+", " ", text).strip()


def canon_horse(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def race_no_key(value: object) -> str:
    return re.sub(r"[^0-9]", "", clean(value))


def to_float(value: object) -> float | None:
    try:
        text = clean(value).replace(",", "")
        if text == "":
            return None
        parsed = float(text)
        if not math.isfinite(parsed):
            return None
        return parsed
    except Exception:
        return None


def parse_sp(value: object) -> float | None:
    text = clean(value)
    if text == "" or text == "-" or upper(text) == "SP":
        return None
    text = text.replace("$", "").replace("SP", "").replace("F", "").strip()
    return to_float(text)


def safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator) * 100.0


def round_num(value: float | None, places: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), places)


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def probability_bucket(probability: float | None) -> str:
    if probability is None or math.isnan(probability):
        return "NO_PROB"
    for low, high, label in CALIBRATION_BUCKETS:
        if low <= probability < high:
            return label
    return "35_PLUS"


def project_with_bounds(
    probabilities: np.ndarray,
    floor: float,
    cap: float,
) -> tuple[np.ndarray, int, int]:
    q = np.clip(probabilities.astype(float), 0.0, None)
    total = float(q.sum())
    if total <= 0:
        q = np.repeat(1.0 / len(q), len(q))
    else:
        q = q / total

    cap_hits = int((q > cap).sum())
    floor_hits = int((q < floor).sum())

    fixed_low = np.zeros(len(q), dtype=bool)
    fixed_high = np.zeros(len(q), dtype=bool)

    for _ in range(50):
        changed = False

        low_mask = (~fixed_low) & (~fixed_high) & (q < floor)
        if low_mask.any():
            fixed_low[low_mask] = True
            q[low_mask] = floor
            changed = True

        high_mask = (~fixed_low) & (~fixed_high) & (q > cap)
        if high_mask.any():
            fixed_high[high_mask] = True
            q[high_mask] = cap
            changed = True

        free_mask = ~(fixed_low | fixed_high)
        fixed_sum = float(q[fixed_low | fixed_high].sum())
        remaining = 1.0 - fixed_sum

        if free_mask.any():
            if remaining <= 0:
                q[free_mask] = 0.0
            else:
                weights = probabilities[free_mask].astype(float)
                weights = np.clip(weights, 0.0, None)
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

    total_now = float(q.sum())
    if total_now > 0:
        q = q / total_now
    else:
        q = np.repeat(1.0 / len(q), len(q))

    return q, cap_hits, floor_hits


def load_problem_context() -> dict[str, object]:
    context: dict[str, object] = {}

    if INPUT_PROJECTION_AUDIT.exists():
        audit = load_required_csv(INPUT_PROJECTION_AUDIT)
        root_rows = audit[audit["section"].map(upper).eq("ROOT_CAUSE_RANKING")].copy()
        if not root_rows.empty:
            top = root_rows.iloc[0]
            context["top_root_cause"] = clean(top.get("candidate_v1"))
            context["top_root_cause_likelihood"] = clean(top.get("likelihood_v1"))

    if INPUT_CONVERSION_AUDIT.exists():
        conv = load_required_csv(INPUT_CONVERSION_AUDIT)
        overall = conv[conv["section"].map(upper).eq("OVERALL_SUMMARY")].copy()
        for row in overall.to_dict("records"):
            context[f"conversion_{clean(row.get('metric'))}"] = clean(row.get("value"))

    if INPUT_PRICE_REALISM.exists():
        realism = load_required_csv(INPUT_PRICE_REALISM)
        tails = realism[realism["section"].map(upper).eq("TAIL_SUMMARY")].copy()
        shortest = tails[tails["tail_group_v1"].map(upper).eq("TOP_500_SHORTEST")]
        if not shortest.empty:
            row = shortest.iloc[0]
            context["shortest500_baseline_win_pct"] = clean(row.get("win_pct"))
            context["shortest500_baseline_implied_pct"] = clean(row.get("avg_model_prob_pct_v1"))

    if INPUT_GAP_DISTRIBUTION.exists():
        gap = load_required_csv(INPUT_GAP_DISTRIBUTION)
        context["gap_distribution_rows"] = len(gap)

    return context


def load_base_replay() -> pd.DataFrame:
    calendar = load_required_csv(INPUT_CALENDAR)
    archive = load_required_csv(INPUT_ARCHIVE)
    back = load_required_csv(INPUT_BACKTEST)

    calendar["date_key"] = calendar["meeting_date"].map(clean).str[:10]
    calendar["track_key"] = calendar["track"].map(norm_track)
    calendar["race_no_key"] = calendar["race_no"].map(race_no_key)
    vic_track_dates = {
        (row.date_key, row.track_key)
        for row in calendar[calendar["state"].map(upper).eq("VIC")].itertuples(index=False)
        if row.date_key and row.track_key
    }

    archive["date_key"] = archive["meeting_date"].map(clean).str[:10]
    archive["track_key"] = archive["track"].map(norm_track)
    archive["race_no_key"] = archive["race_no"].map(race_no_key)
    archive["horse_key"] = archive["horse_key_join"].where(
        archive["horse_key_join"].map(clean).ne(""),
        archive["horseName"].map(canon_horse),
    )
    archive["horse_key"] = archive["horse_key"].map(canon_horse)
    archive["sp_num"] = archive["sp"].map(parse_sp)
    archive["is_scratched_num"] = pd.to_numeric(archive["is_scratched"], errors="coerce").fillna(0)
    archive_small = archive[
        [
            "date_key",
            "track_key",
            "horse_key",
            "race_no_key",
            "race_key_join",
            "sp_num",
            "is_scratched_num",
        ]
    ].drop_duplicates(["date_key", "track_key", "horse_key"], keep="first")

    back = back[back["model"].map(upper).eq("V6_1_RESEARCH_PRIOR")].copy()
    back["date_key"] = back["race_date"].map(clean).str[:10]
    back["track_key"] = back["track"].map(norm_track)
    back["horse_key"] = back["horse"].map(canon_horse)
    back = back[
        back.apply(lambda row: (row["date_key"], row["track_key"]) in vic_track_dates, axis=1)
    ].copy()

    numeric_cols = [
        "distance",
        "finish_position_num",
        "field_size",
        "prior_starts",
        "earned_rating",
        "prior_rating",
        "rating",
        "race_median_rating",
        "rating_gap",
        "rank",
        "model_prob",
        "fair_price",
        "won",
        "placed",
    ]
    for col in numeric_cols:
        back[col] = pd.to_numeric(back[col], errors="coerce")

    merged = back.merge(
        archive_small,
        how="left",
        on=["date_key", "track_key", "horse_key"],
    )
    merged = merged[merged["is_scratched_num"].fillna(0).le(0)].copy()
    merged["year"] = pd.to_datetime(merged["race_date"], errors="coerce").dt.year
    merged["race_no"] = pd.to_numeric(merged["race_no_key"], errors="coerce")
    merged["sp_num"] = pd.to_numeric(merged["sp_num"], errors="coerce")
    merged["baseline_data_source_v1"] = "V6_1_RESEARCH_PRIOR_BACKTEST_VIC"
    merged["actual_winner_flag_v1"] = merged["won"].astype(int)
    merged["actual_place_flag_v1"] = merged["placed"].astype(int)
    return merged


def current_v61_conversion(gaps: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    min_gap = float(np.min(gaps))
    top_gap = float(np.max(gaps))
    power_used = CURRENT_POWER_WEAK if top_gap < CURRENT_WEAK_GAP_THRESHOLD else CURRENT_POWER_STANDARD
    scores = np.power(np.clip(gaps - min_gap + 1.0, 0.000001, None), power_used)
    pre_cap = scores / float(np.sum(scores))
    post_cap = np.minimum(pre_cap, CURRENT_CAP)
    return post_cap, {
        "power_used": power_used,
        "pre_cap_sum": float(np.sum(pre_cap)),
        "post_cap_sum": float(np.sum(post_cap)),
        "cap_hits": int((pre_cap > CURRENT_CAP).sum()),
        "floor_hits": 0,
    }


def softmax_temperature(gaps: np.ndarray, temperature: float) -> tuple[np.ndarray, dict[str, float]]:
    raw = np.exp(np.clip(gaps / float(temperature), -50, 50))
    probs = raw / float(np.sum(raw))
    return probs, {
        "power_used": None,
        "pre_cap_sum": float(np.sum(probs)),
        "post_cap_sum": float(np.sum(probs)),
        "cap_hits": 0,
        "floor_hits": 0,
    }


def power_shrink(base_probs: np.ndarray, alpha: float) -> tuple[np.ndarray, dict[str, float]]:
    clipped = np.clip(base_probs, 1e-12, None)
    raw = np.power(clipped, float(alpha))
    probs = raw / float(np.sum(raw))
    return probs, {
        "power_used": alpha,
        "pre_cap_sum": float(np.sum(probs)),
        "post_cap_sum": float(np.sum(probs)),
        "cap_hits": 0,
        "floor_hits": 0,
    }


def fit_monotonic_gap_bins(train: pd.DataFrame) -> list[dict[str, float]]:
    work = train.sort_values("rating_gap").reset_index(drop=True).copy()
    blocks: list[dict[str, object]] = []

    start = 0
    unique_races: set[str] = set()
    wins = 0

    for idx, row in work.iterrows():
        unique_races.add(clean(row["race_key"]))
        wins += int(row["won"])
        runners = idx - start + 1
        if runners >= LOGISTIC_MIN_RUNNERS_PER_BIN and len(unique_races) >= LOGISTIC_MIN_RACES_PER_BIN:
            block = {
                "start": start,
                "end": idx,
                "low_gap": float(work.at[start, "rating_gap"]),
                "high_gap": float(work.at[idx, "rating_gap"]),
                "avg_gap": float(work.loc[start:idx, "rating_gap"].mean()),
                "runners": runners,
                "races": len(unique_races),
                "wins": wins,
                "win_rate": wins / runners,
            }
            blocks.append(block)
            start = idx + 1
            unique_races = set()
            wins = 0

    if start < len(work):
        if not blocks:
            idx = len(work) - 1
            blocks.append(
                {
                    "start": 0,
                    "end": idx,
                    "low_gap": float(work.at[0, "rating_gap"]),
                    "high_gap": float(work.at[idx, "rating_gap"]),
                    "avg_gap": float(work["rating_gap"].mean()),
                    "runners": len(work),
                    "races": work["race_key"].nunique(),
                    "wins": int(work["won"].sum()),
                    "win_rate": float(work["won"].mean()),
                }
            )
        else:
            prev = blocks[-1]
            idx = len(work) - 1
            new_start = int(prev["start"])
            blocks[-1] = {
                "start": new_start,
                "end": idx,
                "low_gap": float(work.at[new_start, "rating_gap"]),
                "high_gap": float(work.at[idx, "rating_gap"]),
                "avg_gap": float(work.loc[new_start:idx, "rating_gap"].mean()),
                "runners": int(idx - new_start + 1),
                "races": int(work.loc[new_start:idx, "race_key"].nunique()),
                "wins": int(work.loc[new_start:idx, "won"].sum()),
                "win_rate": float(work.loc[new_start:idx, "won"].mean()),
            }

    if not blocks:
        return []

    pav_blocks: list[dict[str, float]] = []
    for block in blocks:
        pav_blocks.append(
            {
                "start": int(block["start"]),
                "end": int(block["end"]),
                "weight": float(block["runners"]),
                "sum_y": float(block["win_rate"]) * float(block["runners"]),
            }
        )
        while len(pav_blocks) >= 2:
            left = pav_blocks[-2]
            right = pav_blocks[-1]
            left_rate = left["sum_y"] / left["weight"]
            right_rate = right["sum_y"] / right["weight"]
            if left_rate <= right_rate:
                break
            merged = {
                "start": int(left["start"]),
                "end": int(right["end"]),
                "weight": float(left["weight"] + right["weight"]),
                "sum_y": float(left["sum_y"] + right["sum_y"]),
            }
            pav_blocks = pav_blocks[:-2] + [merged]

    smoothed_rates: list[float] = [0.0] * len(blocks)
    for block in pav_blocks:
        rate = float(block["sum_y"] / block["weight"])
        for idx in range(int(block["start"]), int(block["end"]) + 1):
            pass

    # Map from row index ranges back to block ranges.
    final_bins: list[dict[str, float]] = []
    for pav in pav_blocks:
        subset = work.loc[int(pav["start"]):int(pav["end"])].copy()
        final_bins.append(
            {
                "low_gap": float(subset["rating_gap"].min()),
                "high_gap": float(subset["rating_gap"].max()),
                "avg_gap": float(subset["rating_gap"].mean()),
                "runners": int(len(subset)),
                "races": int(subset["race_key"].nunique()),
                "wins": int(subset["won"].sum()),
                "smoothed_rate": float(pav["sum_y"] / pav["weight"]),
            }
        )

    return final_bins


def apply_logistic_calibrated(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    predictions = np.zeros(len(df), dtype=float)
    years = sorted(int(year) for year in df["year"].dropna().unique().tolist())

    for year in years:
        test_mask = df["year"].eq(year)
        train = df[~test_mask].copy()
        test = df[test_mask].copy()
        if train.empty:
            train = df.copy()
        bins = fit_monotonic_gap_bins(train)
        if not bins:
            predictions[test_mask] = 1.0
            continue

        highs = np.array([row["high_gap"] for row in bins], dtype=float)
        rates = np.array([max(row["smoothed_rate"], 1e-6) for row in bins], dtype=float)
        gaps = test["rating_gap"].to_numpy(dtype=float)
        idxs = np.searchsorted(highs, gaps, side="left")
        idxs = np.clip(idxs, 0, len(rates) - 1)
        predictions[test_mask] = rates[idxs]

    return predictions, np.zeros(len(df), dtype=float)


def scenario_labels() -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = [
        {
            "scenario_name_v1": "CURRENT_V6_1_CONVERSION",
            "candidate_family_v1": "CURRENT_V6_1_CONVERSION",
            "candidate_setting_v1": "LIVE_BUILDER_BASELINE",
        }
    ]
    for temp in SOFTMAX_TEMPERATURES:
        rows.append(
            {
                "scenario_name_v1": f"V4_SOFTMAX_TEMPERATURE_T{temp}",
                "candidate_family_v1": "V4_SOFTMAX_TEMPERATURE",
                "candidate_setting_v1": f"TEMP_{temp}",
            }
        )
    for alpha in POWER_SHRINK_ALPHAS:
        alpha_text = str(alpha).replace(".", "_")
        rows.append(
            {
                "scenario_name_v1": f"V4_POWER_SHRINK_A{alpha_text}",
                "candidate_family_v1": "V4_POWER_SHRINK",
                "candidate_setting_v1": f"ALPHA_{alpha}",
            }
        )
    rows.append(
        {
            "scenario_name_v1": "V4_LOGISTIC_CALIBRATED",
            "candidate_family_v1": "V4_LOGISTIC_CALIBRATED",
            "candidate_setting_v1": "MONOTONIC_BINS_250_RUNNERS_50_RACES",
        }
    )
    return rows


def build_base_candidate_rows(df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    logistic_base, _ = apply_logistic_calibrated(df)
    logistic_lookup = pd.Series(logistic_base, index=df.index)

    for race_key, race in df.groupby("race_key", dropna=False):
        work = race.copy().reset_index(drop=False).rename(columns={"index": "base_index_v1"})
        gaps = work["rating_gap"].to_numpy(dtype=float)
        current_probs, current_meta = current_v61_conversion(gaps)
        baseline_rank = pd.Series(current_probs).rank(method="first", ascending=False).astype(int).to_numpy()

        base_payload = {
            "CURRENT_V6_1_CONVERSION": (current_probs, current_meta, current_meta["post_cap_sum"], current_meta["cap_hits"], current_meta["floor_hits"]),
        }

        for temp in SOFTMAX_TEMPERATURES:
            probs, meta = softmax_temperature(gaps, temp)
            base_payload[f"V4_SOFTMAX_TEMPERATURE_T{temp}"] = (probs, meta, float(np.sum(probs)), meta["cap_hits"], meta["floor_hits"])

        for alpha in POWER_SHRINK_ALPHAS:
            probs, meta = power_shrink(current_probs, alpha)
            base_payload[f"V4_POWER_SHRINK_A{str(alpha).replace('.', '_')}"] = (
                probs,
                meta,
                float(np.sum(probs)),
                meta["cap_hits"],
                meta["floor_hits"],
            )

        logistic_probs = work["base_index_v1"].map(logistic_lookup).to_numpy(dtype=float)
        if float(np.sum(logistic_probs)) <= 0:
            logistic_probs = np.ones_like(logistic_probs)
        logistic_probs = logistic_probs / float(np.sum(logistic_probs))
        base_payload["V4_LOGISTIC_CALIBRATED"] = (
            logistic_probs,
            {"power_used": None, "pre_cap_sum": 1.0, "post_cap_sum": 1.0, "cap_hits": 0, "floor_hits": 0},
            1.0,
            0,
            0,
        )

        for label in scenario_labels():
            scenario_name = str(label["scenario_name_v1"])
            probs, meta, prob_sum, cap_hits, floor_hits = base_payload[scenario_name]
            fair = np.where(probs > 0, 1.0 / probs, np.nan)
            rank = pd.Series(probs).rank(method="first", ascending=False).astype(int).to_numpy()
            underround = prob_sum < 0.9999
            overround = prob_sum > 1.0001

            for row_idx, (_, row) in enumerate(work.iterrows()):
                records.append(
                    {
                        "scenario_name_v1": scenario_name,
                        "candidate_family_v1": label["candidate_family_v1"],
                        "candidate_setting_v1": label["candidate_setting_v1"],
                        "race_key": row["race_key"],
                        "race_date": row["race_date"],
                        "track": row["track"],
                        "race_no": row["race_no"],
                        "horse": row["horse"],
                        "horse_key": row["horse_key"],
                        "projection_band": row["projection_band"],
                        "rating": row["rating"],
                        "rating_gap": row["rating_gap"],
                        "won": int(row["won"]),
                        "placed": int(row["placed"]),
                        "sp_num": row["sp_num"],
                        "current_v6_1_probability_v1": float(current_probs[row_idx]),
                        "current_v6_1_fair_price_v1": float(1.0 / current_probs[row_idx]) if current_probs[row_idx] > 0 else np.nan,
                        "current_v6_1_rank_v1": int(baseline_rank[row_idx]),
                        "candidate_probability_v1": float(probs[row_idx]),
                        "candidate_fair_price_v1": float(fair[row_idx]) if pd.notna(fair[row_idx]) else np.nan,
                        "candidate_rank_v1": int(rank[row_idx]),
                        "probability_delta_pts_v1": float((probs[row_idx] - current_probs[row_idx]) * 100.0),
                        "fair_price_change_pct_v1": float(((fair[row_idx] / (1.0 / current_probs[row_idx])) - 1.0) * 100.0)
                        if current_probs[row_idx] > 0 and pd.notna(fair[row_idx])
                        else np.nan,
                        "rank_changed_v1": bool(int(rank[row_idx]) != int(baseline_rank[row_idx])),
                        "top_pick_changed_race_v1": False,
                        "material_prob_move_v1": abs(float((probs[row_idx] - current_probs[row_idx]) * 100.0)) >= 2.0,
                        "material_fair_price_move_v1": abs(
                            float(((fair[row_idx] / (1.0 / current_probs[row_idx])) - 1.0) * 100.0)
                        ) >= 10.0 if current_probs[row_idx] > 0 and pd.notna(fair[row_idx]) else False,
                        "probability_sum_by_race_v1": float(prob_sum),
                        "underround_flag_v1": bool(underround),
                        "overround_flag_v1": bool(overround),
                        "cap_hits_race_v1": int(cap_hits),
                        "floor_hits_race_v1": int(floor_hits),
                        "builder_power_or_setting_v1": meta.get("power_used"),
                        "scratched_probability_mass_v1": 0.0,
                    }
                )

    replay = pd.DataFrame(records)

    for scenario_name, group in replay.groupby("scenario_name_v1", dropna=False):
        base_top = replay[
            replay["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION") & replay["candidate_rank_v1"].eq(1)
        ][["race_key", "horse"]].rename(columns={"horse": "baseline_top_horse_v1"})
        top = group[group["candidate_rank_v1"].eq(1)][["race_key", "horse"]].rename(columns={"horse": "scenario_top_horse_v1"})
        top = top.merge(base_top, how="left", on="race_key")
        changed = {
            (row["race_key"], row["scenario_top_horse_v1"] != row["baseline_top_horse_v1"])
            for row in top.to_dict("records")
        }
        changed_map = {race_key: flag for race_key, flag in changed}
        replay.loc[replay["scenario_name_v1"].eq(scenario_name), "top_pick_changed_race_v1"] = (
            replay.loc[replay["scenario_name_v1"].eq(scenario_name), "race_key"].map(lambda key: bool(changed_map.get(key, False)))
        )

    return replay


def choose_base_winner(summary_df: pd.DataFrame) -> str:
    base = summary_df[summary_df["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].iloc[0]
    candidates = summary_df[~summary_df["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].copy()
    candidates = candidates[~candidates["candidate_family_v1"].eq("V4_HYBRID_RECOMMENDED")].copy()

    def score(row: pd.Series) -> tuple:
        short_improve = abs(float(base["shortest500_implied_minus_actual_gap_pts_v1"])) - abs(float(row["shortest500_implied_minus_actual_gap_pts_v1"]))
        tail_improve = abs(float(base["tail500_implied_minus_actual_gap_pts_v1"])) - abs(float(row["tail500_implied_minus_actual_gap_pts_v1"]))
        calib_improve = float(base["weighted_abs_calibration_gap_pts_v1"]) - float(row["weighted_abs_calibration_gap_pts_v1"])
        rank1_delta = float(row["rank1_win_pct"]) - float(base["rank1_win_pct"])
        top3_delta = float(row["top3_winner_capture_pct"]) - float(base["top3_winner_capture_pct"])
        safe_round = int(float(row["underround_race_count_v1"]) == 0 and float(row["overround_race_count_v1"]) == 0)
        return (
            safe_round,
            int(rank1_delta >= -0.2),
            int(top3_delta >= -0.3),
            round(short_improve, 6),
            round(calib_improve, 6),
            round(rank1_delta, 6),
            round(top3_delta, 6),
            round(tail_improve, 6),
            round(float(base["brier_score_v1"]) - float(row["brier_score_v1"]), 6),
            round(float(base["log_loss_v1"]) - float(row["log_loss_v1"]), 6),
        )

    ranked = candidates.sort_values(
        by=["scenario_name_v1"],
        ascending=True,
    ).copy()
    ranked["selection_key_v1"] = ranked.apply(score, axis=1)
    ranked = ranked.sort_values("selection_key_v1", ascending=False)
    return str(ranked.iloc[0]["scenario_name_v1"])


def build_hybrid_replay(base_df: pd.DataFrame, base_replay: pd.DataFrame, seed_scenario_name: str) -> pd.DataFrame:
    seed = base_replay[base_replay["scenario_name_v1"].eq(seed_scenario_name)].copy()
    rows: list[dict[str, object]] = []

    for race_key, race in seed.groupby("race_key", dropna=False):
        work = race.copy().sort_values("horse").reset_index(drop=True)
        base_probs = work["candidate_probability_v1"].to_numpy(dtype=float)
        hybrid_probs, cap_hits, floor_hits = project_with_bounds(base_probs, HYBRID_FLOOR, HYBRID_CAP)
        fair = np.where(hybrid_probs > 0, 1.0 / hybrid_probs, np.nan)
        rank = pd.Series(hybrid_probs).rank(method="first", ascending=False).astype(int).to_numpy()
        prob_sum = float(np.sum(hybrid_probs))
        underround = prob_sum < 0.9999
        overround = prob_sum > 1.0001

        for row_idx, (_, row) in enumerate(work.iterrows()):
            rows.append(
                {
                    "scenario_name_v1": "V4_HYBRID_RECOMMENDED",
                    "candidate_family_v1": "V4_HYBRID_RECOMMENDED",
                    "candidate_setting_v1": f"SEED={seed_scenario_name}|CAP={HYBRID_CAP}|FLOOR={HYBRID_FLOOR}",
                    "race_key": row["race_key"],
                    "race_date": row["race_date"],
                    "track": row["track"],
                    "race_no": row["race_no"],
                    "horse": row["horse"],
                    "horse_key": row["horse_key"],
                    "projection_band": row["projection_band"],
                    "rating": row["rating"],
                    "rating_gap": row["rating_gap"],
                    "won": int(row["won"]),
                    "placed": int(row["placed"]),
                    "sp_num": row["sp_num"],
                    "current_v6_1_probability_v1": float(row["current_v6_1_probability_v1"]),
                    "current_v6_1_fair_price_v1": float(row["current_v6_1_fair_price_v1"]),
                    "current_v6_1_rank_v1": int(row["current_v6_1_rank_v1"]),
                    "candidate_probability_v1": float(hybrid_probs[row_idx]),
                    "candidate_fair_price_v1": float(fair[row_idx]) if pd.notna(fair[row_idx]) else np.nan,
                    "candidate_rank_v1": int(rank[row_idx]),
                    "probability_delta_pts_v1": float((hybrid_probs[row_idx] - row["current_v6_1_probability_v1"]) * 100.0),
                    "fair_price_change_pct_v1": float(((fair[row_idx] / row["current_v6_1_fair_price_v1"]) - 1.0) * 100.0)
                    if row["current_v6_1_fair_price_v1"] > 0 and pd.notna(fair[row_idx])
                    else np.nan,
                    "rank_changed_v1": bool(int(rank[row_idx]) != int(row["current_v6_1_rank_v1"])),
                    "top_pick_changed_race_v1": False,
                    "material_prob_move_v1": abs(float((hybrid_probs[row_idx] - row["current_v6_1_probability_v1"]) * 100.0)) >= 2.0,
                    "material_fair_price_move_v1": abs(
                        float(((fair[row_idx] / row["current_v6_1_fair_price_v1"]) - 1.0) * 100.0)
                    ) >= 10.0 if row["current_v6_1_fair_price_v1"] > 0 and pd.notna(fair[row_idx]) else False,
                    "probability_sum_by_race_v1": prob_sum,
                    "underround_flag_v1": bool(underround),
                    "overround_flag_v1": bool(overround),
                    "cap_hits_race_v1": int(cap_hits),
                    "floor_hits_race_v1": int(floor_hits),
                    "builder_power_or_setting_v1": seed_scenario_name,
                    "scratched_probability_mass_v1": 0.0,
                }
            )

    hybrid = pd.DataFrame(rows)
    base_top = base_replay[
        base_replay["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION") & base_replay["candidate_rank_v1"].eq(1)
    ][["race_key", "horse"]].rename(columns={"horse": "baseline_top_horse_v1"})
    hybrid_top = hybrid[hybrid["candidate_rank_v1"].eq(1)][["race_key", "horse"]].rename(columns={"horse": "scenario_top_horse_v1"})
    hybrid_top = hybrid_top.merge(base_top, how="left", on="race_key")
    top_changed_map = {
        row["race_key"]: bool(row["scenario_top_horse_v1"] != row["baseline_top_horse_v1"])
        for row in hybrid_top.to_dict("records")
    }
    hybrid["top_pick_changed_race_v1"] = hybrid["race_key"].map(lambda key: bool(top_changed_map.get(key, False)))
    return hybrid


def calibration_buckets(replay: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    rows: list[dict[str, object]] = []
    weighted_gaps: dict[str, float] = {}

    for scenario_name, group in replay.groupby("scenario_name_v1", dropna=False):
        total = len(group)
        weighted = 0.0
        for low, high, label in CALIBRATION_BUCKETS:
            subset = group[
                group["candidate_probability_v1"].ge(low) & group["candidate_probability_v1"].lt(high)
            ].copy()
            runners = int(len(subset))
            wins = int(subset["won"].sum()) if runners else 0
            implied_pct = float(subset["candidate_probability_v1"].mean() * 100.0) if runners else 0.0
            actual_pct = safe_pct(wins, runners)
            gap = actual_pct - implied_pct
            weighted += abs(gap) * runners
            rows.append(
                {
                    "scenario_name_v1": scenario_name,
                    "candidate_family_v1": clean(subset["candidate_family_v1"].iloc[0]) if runners else "",
                    "probability_bucket_v1": label,
                    "runner_count": runners,
                    "wins": wins,
                    "avg_implied_prob_pct_v1": round_num(implied_pct, 4),
                    "actual_win_pct_v1": round_num(actual_pct, 4),
                    "calibration_gap_pts_v1": round_num(gap, 4),
                }
            )
        weighted_gaps[scenario_name] = round_num(weighted / total if total else 0.0, 4) or 0.0

    return pd.DataFrame(rows), weighted_gaps


def price_realism(replay: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for scenario_name, group in replay.groupby("scenario_name_v1", dropna=False):
        for tail_name, subset in [
            ("TOP_500_SHORTEST", group.nsmallest(500, "candidate_fair_price_v1")),
            ("TOP_500_LONGEST", group.nlargest(500, "candidate_fair_price_v1")),
        ]:
            implied_pct = float(subset["candidate_probability_v1"].mean() * 100.0) if not subset.empty else 0.0
            actual_pct = safe_pct(subset["won"].sum(), len(subset)) if not subset.empty else 0.0
            rows.append(
                {
                    "scenario_name_v1": scenario_name,
                    "candidate_family_v1": clean(subset["candidate_family_v1"].iloc[0]) if not subset.empty else "",
                    "tail_group_v1": tail_name,
                    "runner_count": int(len(subset)),
                    "wins": int(subset["won"].sum()) if not subset.empty else 0,
                    "places": int(subset["placed"].sum()) if not subset.empty else 0,
                    "actual_win_pct_v1": round_num(actual_pct, 4),
                    "actual_place_pct_v1": round_num(safe_pct(subset["placed"].sum(), len(subset)), 4) if not subset.empty else 0.0,
                    "avg_implied_prob_pct_v1": round_num(implied_pct, 4),
                    "implied_minus_actual_gap_pts_v1": round_num(implied_pct - actual_pct, 4),
                    "avg_fair_price_v1": round_num(subset["candidate_fair_price_v1"].mean(), 4) if not subset.empty else None,
                    "median_fair_price_v1": round_num(subset["candidate_fair_price_v1"].median(), 4) if not subset.empty else None,
                    "avg_actual_sp_v1": round_num(pd.to_numeric(subset["sp_num"], errors="coerce").mean(), 4) if not subset.empty else None,
                }
            )

    return pd.DataFrame(rows)


def candidate_summary(replay: pd.DataFrame, bucket_df: pd.DataFrame, weighted_gaps: dict[str, float], realism_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    race_counts = replay["race_key"].nunique()
    baseline = replay[replay["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].copy()
    baseline_top = baseline[baseline["candidate_rank_v1"].eq(1)][["race_key", "horse"]].rename(columns={"horse": "baseline_top_horse_v1"})

    for scenario_name, group in replay.groupby("scenario_name_v1", dropna=False):
        top = group[group["candidate_rank_v1"].eq(1)].copy()
        winners = group[group["won"].eq(1)].copy()
        top3_capture = winners["candidate_rank_v1"].le(3).sum()
        race_prob_sums = group.groupby("race_key", dropna=False)["candidate_probability_v1"].sum()

        brier_race_scores = []
        log_losses = []
        winner_missing_races = 0
        for race_key, race in group.groupby("race_key", dropna=False):
            p = race["candidate_probability_v1"].to_numpy(dtype=float)
            y = race["won"].to_numpy(dtype=float)
            brier_race_scores.append(float(np.sum((p - y) ** 2)))
            winner_slice = race.loc[race["won"].eq(1), "candidate_probability_v1"]
            if winner_slice.empty:
                winner_missing_races += 1
            else:
                winner_prob = float(winner_slice.iloc[0])
                log_losses.append(float(-np.log(max(winner_prob, 1e-12))))

        shortest = realism_df[
            realism_df["scenario_name_v1"].eq(scenario_name) & realism_df["tail_group_v1"].eq("TOP_500_SHORTEST")
        ].iloc[0]
        longest = realism_df[
            realism_df["scenario_name_v1"].eq(scenario_name) & realism_df["tail_group_v1"].eq("TOP_500_LONGEST")
        ].iloc[0]

        top_merged = top[["race_key", "horse"]].merge(baseline_top, how="left", on="race_key")
        top_pick_changes = int((top_merged["horse"] != top_merged["baseline_top_horse_v1"]).sum())

        row = {
            "scenario_name_v1": scenario_name,
            "candidate_family_v1": clean(group["candidate_family_v1"].iloc[0]),
            "candidate_setting_v1": clean(group["candidate_setting_v1"].iloc[0]),
            "runner_rows": int(len(group)),
            "race_count": int(group["race_key"].nunique()),
            "rank1_win_pct": round_num(safe_pct(top["won"].sum(), len(top)), 4),
            "rank1_place_pct": round_num(safe_pct(top["placed"].sum(), len(top)), 4),
            "top3_winner_capture_pct": round_num(safe_pct(top3_capture, group["race_key"].nunique()), 4),
            "brier_score_v1": round_num(float(np.mean(brier_race_scores)), 6),
            "log_loss_v1": round_num(float(np.mean(log_losses)), 6) if log_losses else None,
            "weighted_abs_calibration_gap_pts_v1": weighted_gaps.get(scenario_name, 0.0),
            "shortest500_actual_win_pct_v1": round_num(float(shortest["actual_win_pct_v1"]), 4),
            "shortest500_implied_win_pct_v1": round_num(float(shortest["avg_implied_prob_pct_v1"]), 4),
            "shortest500_implied_minus_actual_gap_pts_v1": round_num(float(shortest["implied_minus_actual_gap_pts_v1"]), 4),
            "tail500_actual_win_pct_v1": round_num(float(longest["actual_win_pct_v1"]), 4),
            "tail500_implied_win_pct_v1": round_num(float(longest["avg_implied_prob_pct_v1"]), 4),
            "tail500_implied_minus_actual_gap_pts_v1": round_num(float(longest["implied_minus_actual_gap_pts_v1"]), 4),
            "avg_rank1_fair_price_v1": round_num(top["candidate_fair_price_v1"].mean(), 4),
            "median_rank1_fair_price_v1": round_num(top["candidate_fair_price_v1"].median(), 4),
            "races_with_favourite_le_2_v1": int(top["candidate_fair_price_v1"].le(2.0).sum()),
            "races_with_favourite_le_3_v1": int(top["candidate_fair_price_v1"].le(3.0).sum()),
            "probability_sum_min_v1": round_num(race_prob_sums.min(), 6),
            "probability_sum_max_v1": round_num(race_prob_sums.max(), 6),
            "probability_sum_avg_v1": round_num(race_prob_sums.mean(), 6),
            "cap_hit_runner_count_v1": int(pd.to_numeric(group["cap_hits_race_v1"], errors="coerce").sum()),
            "floor_hit_runner_count_v1": int(pd.to_numeric(group["floor_hits_race_v1"], errors="coerce").sum()),
            "underround_race_count_v1": int(group.groupby("race_key")["underround_flag_v1"].max().sum()),
            "overround_race_count_v1": int(group.groupby("race_key")["overround_flag_v1"].max().sum()),
            "top_pick_changed_races_v1": top_pick_changes,
            "rank_changed_runner_rows_v1": int(group["rank_changed_v1"].sum()),
            "horses_moved_ge_2pts_v1": int(group["material_prob_move_v1"].sum()),
            "horses_moved_ge_10pct_price_v1": int(group["material_fair_price_move_v1"].sum()),
            "scratched_probability_mass_rows_v1": int(pd.to_numeric(group["scratched_probability_mass_v1"], errors="coerce").gt(0).sum()),
            "winner_missing_races_v1": int(winner_missing_races),
            "baseline_race_count_v1": race_counts,
        }
        rows.append(row)

    summary = pd.DataFrame(rows)
    base = summary[summary["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].iloc[0]

    decision_reasons: list[str] = []
    selection_scores: list[tuple] = []
    for _, row in summary.iterrows():
        if row["scenario_name_v1"] == "CURRENT_V6_1_CONVERSION":
            decision_reasons.append("Baseline reference.")
            selection_scores.append(tuple())
            continue
        reasons = []
        rank1_delta = float(row["rank1_win_pct"] - base["rank1_win_pct"])
        top3_delta = float(row["top3_winner_capture_pct"] - base["top3_winner_capture_pct"])
        short_gap_improve = abs(float(base["shortest500_implied_minus_actual_gap_pts_v1"])) - abs(float(row["shortest500_implied_minus_actual_gap_pts_v1"]))
        calib_improve = float(base["weighted_abs_calibration_gap_pts_v1"]) - float(row["weighted_abs_calibration_gap_pts_v1"])
        if short_gap_improve <= 0:
            reasons.append("did not improve short-price realism")
        if rank1_delta < -0.2:
            reasons.append(f"rank1 win fell {round(rank1_delta, 2)} pts")
        if top3_delta < -0.3:
            reasons.append(f"top3 capture fell {round(top3_delta, 2)} pts")
        if calib_improve <= 0:
            reasons.append("calibration did not improve")
        if int(row["underround_race_count_v1"]) > 0 or int(row["overround_race_count_v1"]) > 0:
            reasons.append("race probability sums were not clean")
        if not reasons:
            reasons.append("passed the safety screen and remains a viable research candidate")
        decision_reasons.append("; ".join(reasons))
        selection_scores.append(tuple())

    summary["decision_reason_v1"] = decision_reasons
    return summary.sort_values(["candidate_family_v1", "candidate_setting_v1", "scenario_name_v1"]).reset_index(drop=True)


def recommend_candidate(summary: pd.DataFrame) -> tuple[str, str]:
    base = summary[summary["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].iloc[0]
    candidates = summary[~summary["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].copy()

    def score(row: pd.Series) -> tuple:
        short_improve = abs(float(base["shortest500_implied_minus_actual_gap_pts_v1"])) - abs(float(row["shortest500_implied_minus_actual_gap_pts_v1"]))
        tail_improve = abs(float(base["tail500_implied_minus_actual_gap_pts_v1"])) - abs(float(row["tail500_implied_minus_actual_gap_pts_v1"]))
        calib_improve = float(base["weighted_abs_calibration_gap_pts_v1"]) - float(row["weighted_abs_calibration_gap_pts_v1"])
        rank1_delta = float(row["rank1_win_pct"]) - float(base["rank1_win_pct"])
        top3_delta = float(row["top3_winner_capture_pct"]) - float(base["top3_winner_capture_pct"])
        safe_round = int(float(row["underround_race_count_v1"]) == 0 and float(row["overround_race_count_v1"]) == 0)
        no_scratched = int(float(row["scratched_probability_mass_rows_v1"]) == 0)
        return (
            safe_round,
            no_scratched,
            int(rank1_delta >= -0.2),
            int(top3_delta >= -0.3),
            round(short_improve, 6),
            round(calib_improve, 6),
            round(rank1_delta, 6),
            round(top3_delta, 6),
            round(tail_improve, 6),
            round(float(base["brier_score_v1"]) - float(row["brier_score_v1"]), 6),
            round(float(base["log_loss_v1"]) - float(row["log_loss_v1"]), 6),
        )

    candidates["selection_key_v1"] = candidates.apply(score, axis=1)
    candidates = candidates.sort_values("selection_key_v1", ascending=False)
    best = candidates.iloc[0]

    short_gap_improve = abs(float(base["shortest500_implied_minus_actual_gap_pts_v1"])) - abs(float(best["shortest500_implied_minus_actual_gap_pts_v1"]))
    calib_improve = float(base["weighted_abs_calibration_gap_pts_v1"]) - float(best["weighted_abs_calibration_gap_pts_v1"])
    rank1_delta = float(best["rank1_win_pct"]) - float(base["rank1_win_pct"])
    top3_delta = float(best["top3_winner_capture_pct"]) - float(base["top3_winner_capture_pct"])
    safe_round = int(float(best["underround_race_count_v1"]) == 0 and float(best["overround_race_count_v1"]) == 0)
    no_scratched = int(float(best["scratched_probability_mass_rows_v1"]) == 0)

    if short_gap_improve <= 0 and calib_improve <= 0 and rank1_delta < 0 and top3_delta < 0:
        return "REJECT_ALL", "Every tested V4 candidate failed to improve the main realism/calibration problem cleanly enough."

    live_gate = (
        short_gap_improve >= 1.0
        and rank1_delta >= -0.2
        and top3_delta >= -0.3
        and calib_improve > 0
        and safe_round == 1
        and no_scratched == 1
    )
    if live_gate:
        return "PROMOTE_TO_LIVE_CANDIDATE_LATER", "The best V4 candidate materially improved short-price realism and calibration without breaking race sums or materially hurting rank capture."

    research_gate = (
        short_gap_improve > 0
        and safe_round == 1
        and no_scratched == 1
        and rank1_delta >= -0.2
        and top3_delta >= -0.3
    )
    if research_gate:
        return "PROMOTE_TO_SIDE_BY_SIDE_RESEARCH", "The best V4 candidate improved realism safely enough for side-by-side research, but it still needs more evidence before any live promotion."

    return "KEEP_RESEARCH_ONLY", "The candidate set is informative, but the best version is still better treated as research context than as a live candidate."


def build_report(
    context: dict[str, object],
    summary: pd.DataFrame,
    buckets: pd.DataFrame,
    realism: pd.DataFrame,
    recommended_scenario: str,
    final_recommendation: str,
) -> str:
    base = summary[summary["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].iloc[0]
    best = summary[summary["scenario_name_v1"].eq(recommended_scenario)].iloc[0]

    def table(frame: pd.DataFrame, columns: list[str], limit: int = 20) -> str:
        if frame.empty:
            return "- none"
        work = frame.head(limit)
        return "\n".join("- " + " | ".join(str(row[col]) for col in columns) for _, row in work.iterrows())

    comparisons = summary[
        [
            "scenario_name_v1",
            "candidate_family_v1",
            "candidate_setting_v1",
            "rank1_win_pct",
            "rank1_place_pct",
            "top3_winner_capture_pct",
            "weighted_abs_calibration_gap_pts_v1",
            "shortest500_implied_minus_actual_gap_pts_v1",
            "underround_race_count_v1",
            "top_pick_changed_races_v1",
        ]
    ].copy().sort_values("scenario_name_v1")

    rejected = summary[
        ~summary["scenario_name_v1"].isin(["CURRENT_V6_1_CONVERSION", recommended_scenario])
    ][["scenario_name_v1", "decision_reason_v1"]].copy()

    best_bucket = buckets[buckets["scenario_name_v1"].eq(recommended_scenario)].copy()
    best_realism = realism[realism["scenario_name_v1"].eq(recommended_scenario)].copy()

    return f"""# EDGEiQ Probability Engine V4 Research Audit

Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}

## Executive Summary

The incoming projection/price deep audit identified `{context.get("top_root_cause", "Probability Conversion")}` as the leading distortion source. This V4 research audit replayed alternative probability conversion methods against the same VIC historical V6.1 rating-gap base without changing production formulas.

Final recommendation: **{final_recommendation}**

Recommended candidate: **{recommended_scenario}**

## Current V6.1 Problem Statement

- shortest-500 implied minus actual gap: {base["shortest500_implied_minus_actual_gap_pts_v1"]} pts
- rank1 win %: {base["rank1_win_pct"]}
- top3 winner capture %: {base["top3_winner_capture_pct"]}
- weighted calibration gap: {base["weighted_abs_calibration_gap_pts_v1"]}
- underround races: {base["underround_race_count_v1"]}
- overround races: {base["overround_race_count_v1"]}
- conversion audit context: races_with_cap_hits={context.get("conversion_races_with_cap_hits", "")}, races_with_underround_after_cap_no_renorm={context.get("conversion_races_with_underround_after_cap_no_renorm", "")}

## Candidate Comparison Table

{table(comparisons, ["scenario_name_v1", "rank1_win_pct", "rank1_place_pct", "top3_winner_capture_pct", "weighted_abs_calibration_gap_pts_v1", "shortest500_implied_minus_actual_gap_pts_v1", "underround_race_count_v1", "top_pick_changed_races_v1"], 30)}

## Best Candidate

- scenario: {best["scenario_name_v1"]}
- family: {best["candidate_family_v1"]}
- setting: {best["candidate_setting_v1"]}
- rank1 win %: {best["rank1_win_pct"]} vs baseline {base["rank1_win_pct"]}
- top3 capture %: {best["top3_winner_capture_pct"]} vs baseline {base["top3_winner_capture_pct"]}
- shortest-500 implied minus actual gap: {best["shortest500_implied_minus_actual_gap_pts_v1"]} vs baseline {base["shortest500_implied_minus_actual_gap_pts_v1"]}
- weighted calibration gap: {best["weighted_abs_calibration_gap_pts_v1"]} vs baseline {base["weighted_abs_calibration_gap_pts_v1"]}
- underround races: {best["underround_race_count_v1"]}
- overround races: {best["overround_race_count_v1"]}

## Does It Improve Short-Price Realism?

Baseline shortest-500:
{table(realism[(realism["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")) & (realism["tail_group_v1"].eq("TOP_500_SHORTEST"))], ["tail_group_v1", "actual_win_pct_v1", "avg_implied_prob_pct_v1", "implied_minus_actual_gap_pts_v1", "avg_fair_price_v1"], 5)}

Recommended shortest-500:
{table(best_realism[best_realism["tail_group_v1"].eq("TOP_500_SHORTEST")], ["tail_group_v1", "actual_win_pct_v1", "avg_implied_prob_pct_v1", "implied_minus_actual_gap_pts_v1", "avg_fair_price_v1"], 5)}

## Does It Hurt Rank1 / Top3?

- rank1 win delta: {round_num(float(best["rank1_win_pct"]) - float(base["rank1_win_pct"]), 4)}
- rank1 place delta: {round_num(float(best["rank1_place_pct"]) - float(base["rank1_place_pct"]), 4)}
- top3 capture delta: {round_num(float(best["top3_winner_capture_pct"]) - float(base["top3_winner_capture_pct"]), 4)}
- top-pick changed races: {best["top_pick_changed_races_v1"]}
- rank-changed runner rows: {best["rank_changed_runner_rows_v1"]}

## Calibration

Recommended candidate bucket calibration:
{table(best_bucket, ["probability_bucket_v1", "runner_count", "avg_implied_prob_pct_v1", "actual_win_pct_v1", "calibration_gap_pts_v1"], 20)}

## Exact Reasons Other Candidates Were Rejected

{table(rejected, ["scenario_name_v1", "decision_reason_v1"], 40)}

## Final Recommendation

{final_recommendation}
"""


def main() -> None:
    for path in [
        INPUT_PROJECTION_AUDIT,
        INPUT_GAP_DISTRIBUTION,
        INPUT_CONVERSION_AUDIT,
        INPUT_PRICE_REALISM,
        INPUT_BACKTEST,
        INPUT_ARCHIVE,
        INPUT_CALENDAR,
        BUILDER_FAIR,
        BUILDER_BACKTEST,
    ]:
        if not Path(path).exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    context = load_problem_context()
    base_df = load_base_replay()

    replay = build_base_candidate_rows(base_df)
    bucket_df, weighted_gaps = calibration_buckets(replay)
    realism_df = price_realism(replay)
    summary_df = candidate_summary(replay, bucket_df, weighted_gaps, realism_df)

    seed_scenario = choose_base_winner(summary_df)
    hybrid_replay = build_hybrid_replay(base_df, replay, seed_scenario)
    replay = pd.concat([replay, hybrid_replay], ignore_index=True, sort=False)
    bucket_df, weighted_gaps = calibration_buckets(replay)
    realism_df = price_realism(replay)
    summary_df = candidate_summary(replay, bucket_df, weighted_gaps, realism_df)

    recommended_scenario = choose_base_winner(summary_df)
    # Compare hybrid as well after it exists.
    recommended_final = summary_df[
        ~summary_df["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")
    ].copy()
    base = summary_df[summary_df["scenario_name_v1"].eq("CURRENT_V6_1_CONVERSION")].iloc[0]

    def final_key(row: pd.Series) -> tuple:
        short_improve = abs(float(base["shortest500_implied_minus_actual_gap_pts_v1"])) - abs(float(row["shortest500_implied_minus_actual_gap_pts_v1"]))
        calib_improve = float(base["weighted_abs_calibration_gap_pts_v1"]) - float(row["weighted_abs_calibration_gap_pts_v1"])
        rank1_delta = float(row["rank1_win_pct"]) - float(base["rank1_win_pct"])
        top3_delta = float(row["top3_winner_capture_pct"]) - float(base["top3_winner_capture_pct"])
        return (
            int(float(row["underround_race_count_v1"]) == 0 and float(row["overround_race_count_v1"]) == 0),
            int(float(row["scratched_probability_mass_rows_v1"]) == 0),
            int(rank1_delta >= -0.2),
            int(top3_delta >= -0.3),
            round(short_improve, 6),
            round(calib_improve, 6),
            round(rank1_delta, 6),
            round(top3_delta, 6),
            round(float(base["brier_score_v1"]) - float(row["brier_score_v1"]), 6),
            round(float(base["log_loss_v1"]) - float(row["log_loss_v1"]), 6),
        )

    recommended_final["selection_key_v1"] = recommended_final.apply(final_key, axis=1)
    recommended_final = recommended_final.sort_values("selection_key_v1", ascending=False)
    recommended_scenario = str(recommended_final.iloc[0]["scenario_name_v1"])
    final_recommendation, final_reason = recommend_candidate(summary_df)

    summary_df["is_recommended_candidate_v1"] = summary_df["scenario_name_v1"].eq(recommended_scenario)
    summary_df["final_recommendation_v1"] = ""
    summary_df.loc[summary_df["scenario_name_v1"].eq(recommended_scenario), "final_recommendation_v1"] = final_recommendation
    summary_df.loc[summary_df["scenario_name_v1"].eq(recommended_scenario), "decision_reason_v1"] = final_reason

    replay["is_recommended_candidate_v1"] = replay["scenario_name_v1"].eq(recommended_scenario)

    replay.to_csv(OUT_REPLAY, index=False)
    summary_df.sort_values(["scenario_name_v1"]).to_csv(OUT_SUMMARY, index=False)
    bucket_df.sort_values(["scenario_name_v1", "probability_bucket_v1"]).to_csv(OUT_BUCKETS, index=False)
    realism_df.sort_values(["scenario_name_v1", "tail_group_v1"]).to_csv(OUT_REALISM, index=False)
    replay[replay["scenario_name_v1"].eq(recommended_scenario)].to_csv(OUT_RECOMMENDED, index=False)
    OUT_REPORT.write_text(
        build_report(
            context=context,
            summary=summary_df.sort_values(["scenario_name_v1"]),
            buckets=bucket_df,
            realism=realism_df,
            recommended_scenario=recommended_scenario,
            final_recommendation=final_recommendation,
        ),
        encoding="utf-8",
    )

    best = summary_df[summary_df["scenario_name_v1"].eq(recommended_scenario)].iloc[0]
    print("[PROBABILITY_ENGINE_V4_RESEARCH_AUDIT] COMPLETE")
    print(f"historical_rows_used={len(base_df)}")
    print(f"historical_races_used={base_df['race_key'].nunique()}")
    print(f"scenarios_tested={summary_df['scenario_name_v1'].nunique()}")
    print(f"recommended_scenario={recommended_scenario}")
    print(f"rank1_win_pct={best['rank1_win_pct']}")
    print(f"top3_winner_capture_pct={best['top3_winner_capture_pct']}")
    print(f"shortest500_gap_pts={best['shortest500_implied_minus_actual_gap_pts_v1']}")
    print(f"weighted_calibration_gap_pts={best['weighted_abs_calibration_gap_pts_v1']}")
    print(f"final_recommendation={final_recommendation}")
    print(f"wrote={OUT_REPLAY}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BUCKETS}")
    print(f"wrote={OUT_REALISM}")
    print(f"wrote={OUT_RECOMMENDED}")
    print(f"wrote={OUT_REPORT}")


if __name__ == "__main__":
    main()
