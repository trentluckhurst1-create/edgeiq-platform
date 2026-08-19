from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PACE_REPLAY = DATA / "edgeiq_historical_pace_advantage_replay_v1.csv"
CALENDAR = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"
MARKET_WAREHOUSE = DATA / "edgeiq_pre_result_market_history_warehouse_v1.csv"

OUT_ENGINE = DATA / "edgeiq_race_shape_engine_v1_research.csv"
OUT_REPLAY = DATA / "edgeiq_race_shape_replay_results_v1.csv"
OUT_REPORT = DATA / "edgeiq_race_shape_engine_v1_report.md"

ROLE_ORDER = ["LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER"]
TEMPO_ORDER = ["CRAWL", "MODERATE", "EVEN", "FAST", "EXTREME"]
SCENARIO_MULTIPLIERS = {
    "NO_SHAPE": 0.0,
    "LIGHT_SHAPE": 0.5,
    "MODERATE_SHAPE": 1.0,
    "STRONG_SHAPE": 1.5,
}

SAFE_ROI_UNAVAILABLE = "NO_CLEAN_HISTORICAL_MARKET_MATCH"
SAFE_ROI_LOW_COVERAGE = "LOW_SAFE_MARKET_COVERAGE"
SAFE_ROI_READY = "SAFE_PRE_RESULT_MARKET_MATCHED"


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
        text = clean(value)
        if text == "":
            return None
        parsed = float(text)
        if not math.isfinite(parsed):
            return None
        return parsed
    except Exception:
        return None


def parse_sp(value: object) -> float | None:
    text = clean(value).replace("$", "").replace(",", "")
    if text == "":
        return None
    return to_float(text)


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def round_or_blank(value: float | None, places: int = 2) -> str:
    if value is None:
        return ""
    return str(round(value, places))


def safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator) * 100.0


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def map_tempo_bucket(value: object) -> str:
    text = upper(value)
    mapping = {
        "VERY_SLOW": "CRAWL",
        "SLOW": "MODERATE",
        "NEUTRAL": "EVEN",
        "FAST": "FAST",
        "VERY_FAST": "EXTREME",
        "UNKNOWN": "UNKNOWN",
    }
    return mapping.get(text, "UNKNOWN")


def build_vic_race_keys(calendar: pd.DataFrame) -> set[tuple[str, str, str]]:
    work = calendar.copy()
    work["meeting_date_key"] = work["meeting_date"].map(clean).str[:10]
    work["track_key"] = work["track"].map(norm_track)
    work["race_no_key"] = work["race_no"].map(race_no_key)
    vic = work[work["state"].map(upper).eq("VIC")].copy()
    return {
        (row.meeting_date_key, row.track_key, row.race_no_key)
        for row in vic.itertuples(index=False)
        if row.meeting_date_key and row.track_key and row.race_no_key
    }


def build_market_lookup() -> pd.DataFrame:
    empty = pd.DataFrame(
        columns=[
            "meeting_date_key",
            "track_key",
            "race_no_key",
            "horse_key_join",
            "safe_market_price_v1",
        ]
    )
    if not MARKET_WAREHOUSE.exists():
        return empty

    market = load_required_csv(MARKET_WAREHOUSE)
    if market.empty:
        return empty

    market["meeting_date_key"] = market["meeting_date"].map(clean).str[:10]
    market["track_key"] = market["track"].map(norm_track)
    market["race_no_key"] = market["race_no"].map(race_no_key)
    market["horse_key_join"] = market["horse_key"].map(canon_horse)
    market["safe_market_price_v1"] = pd.to_numeric(market["fixed_win_price_v1"], errors="coerce")

    market_time_source = market["market_captured_at"].replace("", pd.NA).fillna(market["capture_timestamp_v1"])
    market["market_time_sort"] = pd.to_datetime(market_time_source, errors="coerce", utc=True)

    market = market[
        market["meeting_date_key"].ne("")
        & market["track_key"].ne("")
        & market["race_no_key"].ne("")
        & market["horse_key_join"].ne("")
        & market["safe_market_price_v1"].notna()
        & market["safe_market_price_v1"].gt(1.0)
    ].copy()
    if market.empty:
        return empty

    market = market.sort_values(
        ["meeting_date_key", "track_key", "race_no_key", "horse_key_join", "market_time_sort"],
        ascending=[True, True, True, True, True],
    )
    latest = market.groupby(
        ["meeting_date_key", "track_key", "race_no_key", "horse_key_join"],
        as_index=False,
    ).tail(1)
    return latest[
        ["meeting_date_key", "track_key", "race_no_key", "horse_key_join", "safe_market_price_v1"]
    ].copy()


def load_research_base() -> tuple[pd.DataFrame, dict[str, int]]:
    pace = load_required_csv(PACE_REPLAY)
    calendar = load_required_csv(CALENDAR)
    market_lookup = build_market_lookup()

    pace["meeting_date_key"] = pace["meeting_date"].map(clean).str[:10]
    if "track_norm" in pace.columns:
        pace["track_key"] = pace["track_norm"].where(
            pace["track_norm"].map(clean).ne(""),
            pace["track"].map(norm_track),
        )
    else:
        pace["track_key"] = pace["track"].map(norm_track)
    pace["track_key"] = pace["track_key"].map(norm_track)
    pace["race_no_key"] = pace["race_no"].map(race_no_key)
    pace["horse_key_join"] = pace["horse_key"].where(
        pace["horse_key"].map(clean).ne(""),
        pace["horse"].map(canon_horse),
    )
    pace["horse_key_join"] = pace["horse_key_join"].map(canon_horse)

    vic_race_keys = build_vic_race_keys(calendar)
    pace["vic_race_flag"] = pace.apply(
        lambda row: (row["meeting_date_key"], row["track_key"], row["race_no_key"]) in vic_race_keys,
        axis=1,
    )
    filtered = pace[pace["vic_race_flag"]].copy()

    filtered["runner_score_num"] = pd.to_numeric(filtered["runner_score"], errors="coerce")
    filtered["runner_rank_num"] = pd.to_numeric(filtered["runner_rank"], errors="coerce")
    filtered["won_num"] = pd.to_numeric(filtered["won"], errors="coerce").fillna(0).astype(int)
    filtered["finish_position_num"] = pd.to_numeric(filtered["finish_position"], errors="coerce")
    filtered["place_num"] = filtered["finish_position_num"].le(3).fillna(False).astype(int)
    filtered["sp_reference_only_num"] = filtered["sp"].map(parse_sp)
    filtered["tactical_style_pre_race_v1"] = filtered["tactical_style_pre_race_v1"].map(upper)
    filtered["pace_pressure_band_v1"] = filtered["pace_pressure_band_v1"].map(upper)
    filtered["tempo_bucket_v1"] = filtered["pace_pressure_band_v1"].map(map_tempo_bucket)
    filtered["leaders_count_v1_num"] = pd.to_numeric(filtered["leaders_count_v1"], errors="coerce").fillna(0).astype(int)
    filtered["lone_leader_flag_v1"] = (
        filtered["tactical_style_pre_race_v1"].eq("LEADER")
        & filtered["leaders_count_v1_num"].eq(1)
    )
    filtered["role_bucket_v1"] = filtered["tactical_style_pre_race_v1"].where(
        filtered["tactical_style_pre_race_v1"].isin(ROLE_ORDER),
        "UNKNOWN",
    )
    filtered["race_key_v1"] = filtered["race_key"].where(
        filtered["race_key"].map(clean).ne(""),
        filtered["meeting_date_key"] + "|" + filtered["track_key"] + "|R" + filtered["race_no_key"],
    )

    filtered = filtered.merge(
        market_lookup,
        on=["meeting_date_key", "track_key", "race_no_key", "horse_key_join"],
        how="left",
    )

    metadata = {
        "pace_rows_loaded": int(len(pace)),
        "vic_rows_used": int(len(filtered)),
        "vic_races_used": int(filtered["race_key_v1"].nunique()),
        "safe_market_matches": int(filtered["safe_market_price_v1"].notna().sum()),
    }
    return filtered, metadata


def summarize_roi(selection_df: pd.DataFrame) -> tuple[str, str, int, float | None, float | None]:
    matched = selection_df[selection_df["safe_market_price_v1"].notna()].copy()
    matched_count = int(len(matched))
    avg_safe_price = round(float(matched["safe_market_price_v1"].mean()), 2) if matched_count else None

    if matched_count == 0:
        return SAFE_ROI_UNAVAILABLE, "", 0, avg_safe_price, None

    returns = matched.apply(
        lambda row: float(row["safe_market_price_v1"]) if int(row["won_num"]) == 1 else 0.0,
        axis=1,
    ).sum()
    stakes = float(matched_count)
    roi_pct = ((returns - stakes) / stakes) * 100.0 if stakes > 0 else None

    if matched_count < 20:
        return SAFE_ROI_LOW_COVERAGE, round_or_blank(roi_pct), matched_count, avg_safe_price, roi_pct
    return SAFE_ROI_READY, round_or_blank(roi_pct), matched_count, avg_safe_price, roi_pct


def compute_role_baselines(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    baselines: dict[str, dict[str, float]] = {}
    for role in ROLE_ORDER:
        subset = df[df["role_bucket_v1"].eq(role)].copy()
        baselines[role] = {
            "runners": float(len(subset)),
            "win_pct": safe_pct(subset["won_num"].sum(), len(subset)),
            "place_pct": safe_pct(subset["place_num"].sum(), len(subset)),
        }
    return baselines


def compute_shape_factor(
    runners: int,
    win_pct: float,
    place_pct: float,
    role_base_win_pct: float,
    role_base_place_pct: float,
) -> tuple[float, float, float]:
    sample_shrink = min(1.0, math.sqrt(runners / 300.0)) if runners > 0 else 0.0
    win_lift = win_pct - role_base_win_pct
    place_lift = place_pct - role_base_place_pct
    raw = ((0.80 * win_lift) + (0.20 * place_lift)) * sample_shrink / 2.5
    factor = clip(raw, -4.0, 4.0)
    return round(factor, 3), round(win_lift, 2), round(place_lift, 2)


def build_engine_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    overall_win_pct = safe_pct(df["won_num"].sum(), len(df))
    overall_place_pct = safe_pct(df["place_num"].sum(), len(df))
    baselines = compute_role_baselines(df)
    rows: list[dict[str, object]] = []
    factor_map: dict[str, float] = {}

    for role in ROLE_ORDER:
        role_subset = df[df["role_bucket_v1"].eq(role)].copy()
        role_base = baselines[role]
        for tempo in TEMPO_ORDER:
            subset = role_subset[role_subset["tempo_bucket_v1"].eq(tempo)].copy()
            runners = int(len(subset))
            wins = int(subset["won_num"].sum()) if runners else 0
            places = int(subset["place_num"].sum()) if runners else 0
            win_pct = safe_pct(wins, runners)
            place_pct = safe_pct(places, runners)
            shape_factor, win_lift_role, place_lift_role = compute_shape_factor(
                runners=runners,
                win_pct=win_pct,
                place_pct=place_pct,
                role_base_win_pct=role_base["win_pct"],
                role_base_place_pct=role_base["place_pct"],
            )
            factor_key = f"{role}|{tempo}"
            factor_map[factor_key] = shape_factor
            roi_status, roi_pct, safe_market_matched, avg_safe_price, _ = summarize_roi(subset)

            rows.append(
                {
                    "section": "ROLE_TEMPO_REPLAY",
                    "role_bucket_v1": role,
                    "tempo_bucket_v1": tempo,
                    "lone_leader_flag_v1": "NO",
                    "runners": runners,
                    "wins": wins,
                    "places": places,
                    "win_pct": round(win_pct, 2),
                    "place_pct": round(place_pct, 2),
                    "win_lift_vs_role_pts": win_lift_role,
                    "place_lift_vs_role_pts": place_lift_role,
                    "win_lift_vs_overall_pts": round(win_pct - overall_win_pct, 2),
                    "place_lift_vs_overall_pts": round(place_pct - overall_place_pct, 2),
                    "avg_sp_reference_only": round_or_blank(subset["sp_reference_only_num"].mean() if runners else None),
                    "safe_market_avg_price_v1": round_or_blank(avg_safe_price),
                    "safe_market_roi_pct_v1": roi_pct,
                    "safe_market_matched_rows_v1": safe_market_matched,
                    "roi_status_v1": roi_status,
                    "shape_adjustment_factor_v1": shape_factor,
                    "shape_adjustment_confidence_v1": "HIGH" if runners >= 500 else "MEDIUM" if runners >= 200 else "LOW",
                    "notes_v1": "Empirical role x tempo replay. ROI uses clean pre-result market only when matched.",
                }
            )

    leader_subset = df[df["role_bucket_v1"].eq("LEADER")].copy()
    for lone_flag, label in [(True, "LONE_LEADER"), (False, "NON_LONE_LEADER")]:
        subset = leader_subset[leader_subset["lone_leader_flag_v1"].eq(lone_flag)].copy()
        runners = int(len(subset))
        wins = int(subset["won_num"].sum()) if runners else 0
        places = int(subset["place_num"].sum()) if runners else 0
        win_pct = safe_pct(wins, runners)
        place_pct = safe_pct(places, runners)
        roi_status, roi_pct, safe_market_matched, avg_safe_price, _ = summarize_roi(subset)
        rows.append(
            {
                "section": "LONE_LEADER_REPLAY",
                "role_bucket_v1": label,
                "tempo_bucket_v1": "ALL",
                "lone_leader_flag_v1": "YES" if lone_flag else "NO",
                "runners": runners,
                "wins": wins,
                "places": places,
                "win_pct": round(win_pct, 2),
                "place_pct": round(place_pct, 2),
                "win_lift_vs_role_pts": round(win_pct - baselines["LEADER"]["win_pct"], 2),
                "place_lift_vs_role_pts": round(place_pct - baselines["LEADER"]["place_pct"], 2),
                "win_lift_vs_overall_pts": round(win_pct - overall_win_pct, 2),
                "place_lift_vs_overall_pts": round(place_pct - overall_place_pct, 2),
                "avg_sp_reference_only": round_or_blank(subset["sp_reference_only_num"].mean() if runners else None),
                "safe_market_avg_price_v1": round_or_blank(avg_safe_price),
                "safe_market_roi_pct_v1": roi_pct,
                "safe_market_matched_rows_v1": safe_market_matched,
                "roi_status_v1": roi_status,
                "shape_adjustment_factor_v1": "",
                "shape_adjustment_confidence_v1": "",
                "notes_v1": "Leader-only split to quantify lone leader edge separately from general leader behaviour.",
            }
        )

    collapse_subset = df[df["tempo_bucket_v1"].isin(["FAST", "EXTREME"])].copy()
    for role in ROLE_ORDER:
        subset = collapse_subset[collapse_subset["role_bucket_v1"].eq(role)].copy()
        runners = int(len(subset))
        wins = int(subset["won_num"].sum()) if runners else 0
        places = int(subset["place_num"].sum()) if runners else 0
        win_pct = safe_pct(wins, runners)
        place_pct = safe_pct(places, runners)
        roi_status, roi_pct, safe_market_matched, avg_safe_price, _ = summarize_roi(subset)
        rows.append(
            {
                "section": "PRESSURE_COLLAPSE_REPLAY",
                "role_bucket_v1": role,
                "tempo_bucket_v1": "FAST_OR_EXTREME",
                "lone_leader_flag_v1": "NO",
                "runners": runners,
                "wins": wins,
                "places": places,
                "win_pct": round(win_pct, 2),
                "place_pct": round(place_pct, 2),
                "win_lift_vs_role_pts": round(win_pct - baselines[role]["win_pct"], 2),
                "place_lift_vs_role_pts": round(place_pct - baselines[role]["place_pct"], 2),
                "win_lift_vs_overall_pts": round(win_pct - overall_win_pct, 2),
                "place_lift_vs_overall_pts": round(place_pct - overall_place_pct, 2),
                "avg_sp_reference_only": round_or_blank(subset["sp_reference_only_num"].mean() if runners else None),
                "safe_market_avg_price_v1": round_or_blank(avg_safe_price),
                "safe_market_roi_pct_v1": roi_pct,
                "safe_market_matched_rows_v1": safe_market_matched,
                "roi_status_v1": roi_status,
                "shape_adjustment_factor_v1": "",
                "shape_adjustment_confidence_v1": "",
                "notes_v1": "Pressure-collapse audit for FAST and EXTREME tempo states.",
            }
        )

    return pd.DataFrame(rows), factor_map


def build_lone_leader_factor_map(engine_df: pd.DataFrame, factor_map: dict[str, float]) -> dict[str, float]:
    lone_rows = engine_df[engine_df["section"].eq("LONE_LEADER_REPLAY")].copy()
    lone_leader = lone_rows[lone_rows["role_bucket_v1"].eq("LONE_LEADER")]
    non_lone = lone_rows[lone_rows["role_bucket_v1"].eq("NON_LONE_LEADER")]
    if lone_leader.empty or non_lone.empty:
        return factor_map

    lone_win = to_float(lone_leader.iloc[0]["win_pct"]) or 0.0
    non_lone_win = to_float(non_lone.iloc[0]["win_pct"]) or 0.0
    lone_factor = clip((lone_win - non_lone_win) / 2.5, -4.0, 4.0)
    for tempo in TEMPO_ORDER:
        factor_map[f"LONE_LEADER|{tempo}"] = round(lone_factor, 3)
    return factor_map


def role_tempo_factor(row: pd.Series, factor_map: dict[str, float]) -> float:
    role = clean(row.get("role_bucket_v1"))
    tempo = clean(row.get("tempo_bucket_v1"))
    if role == "LEADER" and bool(row.get("lone_leader_flag_v1")):
        lone_key = f"LONE_LEADER|{tempo}"
        if lone_key in factor_map:
            return float(factor_map[lone_key])
    return float(factor_map.get(f"{role}|{tempo}", 0.0))


def scenario_metrics(scenario_df: pd.DataFrame, scenario_name: str, baseline_tops: pd.DataFrame) -> dict[str, object]:
    ranked = scenario_df.sort_values(
        ["race_key_v1", "adjusted_score_v1", "horse_key_join"],
        ascending=[True, False, True],
    ).copy()
    ranked["scenario_rank_v1"] = ranked.groupby("race_key_v1").cumcount() + 1

    rank1 = ranked[ranked["scenario_rank_v1"].eq(1)].copy()
    winner_rows = ranked[ranked["won_num"].eq(1)].copy()
    winner_best_rank = winner_rows.groupby("race_key_v1", as_index=False)["scenario_rank_v1"].min()
    top3_accuracy = safe_pct(int(winner_best_rank["scenario_rank_v1"].le(3).sum()), len(winner_best_rank))

    roi_status, roi_pct, safe_market_matched, avg_safe_price, roi_numeric = summarize_roi(rank1)
    rank1_changed = 0
    if not baseline_tops.empty:
        compare = rank1[["race_key_v1", "horse_key_join"]].merge(
            baseline_tops.rename(columns={"horse_key_join": "baseline_horse_key_join"}),
            on="race_key_v1",
            how="left",
        )
        rank1_changed = int(compare["horse_key_join"].ne(compare["baseline_horse_key_join"]).sum())

    return {
        "section": "COUNTERFACTUAL_REPLAY",
        "scenario_v1": scenario_name,
        "scenario_multiplier_v1": SCENARIO_MULTIPLIERS[scenario_name],
        "races": int(ranked["race_key_v1"].nunique()),
        "rank1_rows": int(len(rank1)),
        "rank1_wins": int(rank1["won_num"].sum()),
        "rank1_places": int(rank1["place_num"].sum()),
        "rank1_win_pct": round(safe_pct(rank1["won_num"].sum(), len(rank1)), 2),
        "rank1_place_pct": round(safe_pct(rank1["place_num"].sum(), len(rank1)), 2),
        "top3_accuracy_pct": round(top3_accuracy, 2),
        "avg_rank1_sp_reference_only": round_or_blank(rank1["sp_reference_only_num"].mean() if len(rank1) else None),
        "safe_market_avg_price_v1": round_or_blank(avg_safe_price),
        "safe_market_roi_pct_v1": roi_pct,
        "safe_market_matched_rows_v1": safe_market_matched,
        "roi_status_v1": roi_status,
        "rank1_changed_races_v1": rank1_changed,
        "avg_abs_shape_adjustment_v1": round(float(ranked["applied_shape_adjustment_v1"].abs().mean()), 3),
        "notes_v1": "Counterfactual replay applies empirical shape adjustment factor to historical runner_score without changing live models.",
        "_roi_numeric": roi_numeric,
    }


def build_replay_rows(df: pd.DataFrame, factor_map: dict[str, float]) -> pd.DataFrame:
    work = df[
        df["runner_score_num"].notna()
        & df["runner_rank_num"].notna()
        & df["role_bucket_v1"].isin(ROLE_ORDER)
        & df["tempo_bucket_v1"].isin(TEMPO_ORDER)
    ].copy()
    work["shape_adjustment_factor_v1"] = work.apply(lambda row: role_tempo_factor(row, factor_map), axis=1)

    baseline_ranked = work.sort_values(
        ["race_key_v1", "runner_score_num", "horse_key_join"],
        ascending=[True, False, True],
    ).copy()
    baseline_ranked["baseline_rank_v1"] = baseline_ranked.groupby("race_key_v1").cumcount() + 1
    baseline_tops = baseline_ranked[baseline_ranked["baseline_rank_v1"].eq(1)][["race_key_v1", "horse_key_join"]].copy()

    rows: list[dict[str, object]] = []
    for scenario_name, multiplier in SCENARIO_MULTIPLIERS.items():
        scenario_df = work.copy()
        scenario_df["applied_shape_adjustment_v1"] = scenario_df["shape_adjustment_factor_v1"] * multiplier
        scenario_df["adjusted_score_v1"] = scenario_df["runner_score_num"] + scenario_df["applied_shape_adjustment_v1"]
        rows.append(scenario_metrics(scenario_df, scenario_name, baseline_tops))

    replay_df = pd.DataFrame(rows)
    baseline = replay_df[replay_df["scenario_v1"].eq("NO_SHAPE")].iloc[0]
    for column in ["rank1_win_pct", "rank1_place_pct", "top3_accuracy_pct"]:
        replay_df[f"{column}_delta_vs_no_shape"] = (replay_df[column] - float(baseline[column])).round(2)
    return replay_df


def choose_recommendation(replay_df: pd.DataFrame) -> tuple[str, str]:
    candidates = replay_df[replay_df["scenario_v1"].isin(["LIGHT_SHAPE", "MODERATE_SHAPE", "STRONG_SHAPE"])].copy()
    if candidates.empty:
        return "NO_IMPLEMENTATION", "No counterfactual scenarios were available."

    candidates["composite_gain_v1"] = (
        candidates["rank1_win_pct_delta_vs_no_shape"]
        + candidates["top3_accuracy_pct_delta_vs_no_shape"]
        + (0.25 * candidates["rank1_place_pct_delta_vs_no_shape"])
    )
    best = candidates.sort_values(
        ["composite_gain_v1", "rank1_win_pct_delta_vs_no_shape", "top3_accuracy_pct_delta_vs_no_shape"],
        ascending=[False, False, False],
    ).iloc[0]

    best_gain = float(best["composite_gain_v1"])
    win_gain = float(best["rank1_win_pct_delta_vs_no_shape"])
    top3_gain = float(best["top3_accuracy_pct_delta_vs_no_shape"])

    if best_gain <= 0 or (win_gain <= 0 and top3_gain <= 0):
        return "NO_IMPLEMENTATION", "No shape tier improved the historical replay enough to justify promotion."

    scenario = clean(best["scenario_v1"])
    if scenario == "LIGHT_SHAPE":
        return "LIGHT_IMPLEMENTATION", "Light shape weighting gave the best positive replay without needing aggressive adjustment."
    if scenario == "MODERATE_SHAPE":
        return "MODERATE_IMPLEMENTATION", "Moderate shape weighting produced the strongest historical replay improvement."
    return "STRONG_IMPLEMENTATION", "Strong shape weighting produced the strongest historical replay improvement."


def build_report(
    metadata: dict[str, int],
    engine_df: pd.DataFrame,
    replay_df: pd.DataFrame,
    recommendation: str,
    recommendation_reason: str,
) -> str:
    role_tempo = engine_df[engine_df["section"].eq("ROLE_TEMPO_REPLAY")].copy()
    lone = engine_df[engine_df["section"].eq("LONE_LEADER_REPLAY")].copy()
    collapse = engine_df[engine_df["section"].eq("PRESSURE_COLLAPSE_REPLAY")].copy()

    top_positive = role_tempo.sort_values(["shape_adjustment_factor_v1", "runners"], ascending=[False, False]).head(5)
    top_negative = role_tempo.sort_values(["shape_adjustment_factor_v1", "runners"], ascending=[True, False]).head(5)
    best_counterfactual = replay_df.sort_values(
        ["rank1_win_pct_delta_vs_no_shape", "top3_accuracy_pct_delta_vs_no_shape"],
        ascending=[False, False],
    ).head(1)

    def format_rows(frame: pd.DataFrame, cols: list[str]) -> str:
        if frame.empty:
            return "- none"
        lines = []
        for row in frame[cols].itertuples(index=False):
            lines.append("- " + " | ".join(str(value) for value in row))
        return "\n".join(lines)

    return f"""# EDGEiQ Race Shape Engine V1 Research

Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}

## Scope

Research sidecar only. No live probabilities, fair prices, V6.1 logic, or UI were changed.

## Inputs

- Historical pace replay rows loaded: {metadata['pace_rows_loaded']}
- Victoria replay rows used: {metadata['vic_rows_used']}
- Victoria races used: {metadata['vic_races_used']}
- Safe pre-result market matches: {metadata['safe_market_matches']}

## Historical Role x Tempo Replay

Top positive shape combinations:
{format_rows(top_positive, ['role_bucket_v1', 'tempo_bucket_v1', 'runners', 'win_pct', 'shape_adjustment_factor_v1'])}

Top negative shape combinations:
{format_rows(top_negative, ['role_bucket_v1', 'tempo_bucket_v1', 'runners', 'win_pct', 'shape_adjustment_factor_v1'])}

## Lone Leader Replay

{format_rows(lone, ['role_bucket_v1', 'runners', 'win_pct', 'place_pct', 'avg_sp_reference_only', 'safe_market_roi_pct_v1'])}

## Pressure Collapse Replay

{format_rows(collapse, ['role_bucket_v1', 'runners', 'win_pct', 'place_pct', 'win_lift_vs_role_pts'])}

## Counterfactual Replay

{format_rows(replay_df, ['scenario_v1', 'rank1_win_pct', 'rank1_place_pct', 'top3_accuracy_pct', 'safe_market_roi_pct_v1'])}

Best counterfactual:
{format_rows(best_counterfactual, ['scenario_v1', 'rank1_win_pct_delta_vs_no_shape', 'top3_accuracy_pct_delta_vs_no_shape', 'rank1_changed_races_v1'])}

## ROI Note

ROI was calculated only where the clean pre-result market warehouse matched a runner historically.
Racing.com SP was not used for profitability inference.

## Recommendation

{recommendation}

Reason:
{recommendation_reason}
"""


def main() -> None:
    research_df, metadata = load_research_base()
    if research_df.empty:
        raise SystemExit("No Victoria historical race-shape replay rows available after filtering.")

    engine_df, factor_map = build_engine_rows(research_df)
    factor_map = build_lone_leader_factor_map(engine_df, factor_map)

    replay_df = build_replay_rows(research_df, factor_map)
    recommendation, recommendation_reason = choose_recommendation(replay_df)

    engine_df.to_csv(OUT_ENGINE, index=False)

    replay_out = replay_df.drop(columns=[column for column in replay_df.columns if column.startswith("_")], errors="ignore").copy()
    replay_out["recommendation_v1"] = recommendation
    replay_out.to_csv(OUT_REPLAY, index=False)

    OUT_REPORT.write_text(
        build_report(
            metadata=metadata,
            engine_df=engine_df,
            replay_df=replay_out,
            recommendation=recommendation,
            recommendation_reason=recommendation_reason,
        ),
        encoding="utf-8",
    )

    print("[RACE_SHAPE_ENGINE_V1_RESEARCH] COMPLETE")
    print(f"vic_rows_used={metadata['vic_rows_used']}")
    print(f"vic_races_used={metadata['vic_races_used']}")
    print(f"safe_market_matches={metadata['safe_market_matches']}")
    print(f"recommendation={recommendation}")
    print(f"wrote={OUT_ENGINE}")
    print(f"wrote={OUT_REPLAY}")
    print(f"wrote={OUT_REPORT}")


if __name__ == "__main__":
    main()
