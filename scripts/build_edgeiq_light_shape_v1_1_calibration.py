from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PACE_REPLAY = DATA / "edgeiq_historical_pace_advantage_replay_v1.csv"
FAIR_REPLAY = DATA / "edgeiq_fair_price_replay_v1.csv"
SHAPE_ARCHIVE = DATA / "edgeiq_historical_race_shape_archive_v1.csv"
CALENDAR = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"

OUT_CALIBRATION = DATA / "edgeiq_light_shape_v1_1_calibration.csv"
OUT_SUMMARY = DATA / "edgeiq_light_shape_v1_1_summary.csv"
OUT_REPORT = DATA / "edgeiq_light_shape_v1_1_report.md"

ROLE_ORDER = ["LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER"]
TEMPO_ORDER = ["CRAWL", "MODERATE", "EVEN", "FAST", "EXTREME"]
PROBABILITY_BUCKETS = [
    (0.0, 5.0, "LT_5"),
    (5.0, 10.0, "P5_10"),
    (10.0, 15.0, "P10_15"),
    (15.0, 20.0, "P15_20"),
    (20.0, 25.0, "P20_25"),
    (25.0, 1000.0, "P25_PLUS"),
]

COMBO_SAMPLE_FLOOR = 250
TEMPO_SAMPLE_FLOOR = 500
RUN_STYLE_SAMPLE_FLOOR = 500
MAX_ADJUSTMENT_PCT = 0.03
MIN_ADJUSTMENT_PCT = -0.03


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


def safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator) * 100.0


def round_or_blank(value: float | None, places: int = 2) -> str:
    if value is None:
        return ""
    return str(round(value, places))


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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


def map_condition_group(value: object) -> str:
    text = upper(value)
    if "SYNTH" in text:
        return "SYNTHETIC"
    if "HEAVY" in text:
        return "HEAVY"
    if "SOFT" in text:
        return "SOFT"
    if "GOOD" in text or "FIRM" in text:
        return "GOOD"
    return "UNKNOWN"


def distance_band(value: object) -> str:
    text = clean(value)
    digits = re.sub(r"[^0-9]", "", text)
    if digits == "":
        return "UNKNOWN"
    distance = int(digits)
    if distance < 1000:
        return "LT_1000"
    if distance <= 1199:
        return "1000_1199"
    if distance <= 1399:
        return "1200_1399"
    if distance <= 1599:
        return "1400_1599"
    if distance <= 1799:
        return "1600_1799"
    if distance <= 1999:
        return "1800_1999"
    return "2000_PLUS"


def field_size_band(value: object) -> str:
    field = to_float(value)
    if field is None:
        return "UNKNOWN"
    if field <= 7:
        return "FIELD_LE_7"
    if field <= 10:
        return "FIELD_8_10"
    if field <= 13:
        return "FIELD_11_13"
    return "FIELD_14_PLUS"


def tempo_certainty(scale_value: object, used_for_pace: object) -> str:
    if upper(used_for_pace) != "TRUE":
        return "NONE"
    scale = to_float(scale_value)
    if scale is None or scale <= 0:
        return "NONE"
    if scale >= 1.0:
        return "HIGH"
    if scale >= 0.75:
        return "MEDIUM"
    if scale >= 0.5:
        return "LOW"
    return "NONE"


def probability_bucket(probability_pct: float) -> str:
    for low, high, label in PROBABILITY_BUCKETS:
        if probability_pct < high and probability_pct >= low:
            return label
    return "UNKNOWN"


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def vic_race_keys(calendar: pd.DataFrame) -> set[tuple[str, str, str]]:
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


def load_base() -> tuple[pd.DataFrame, dict[str, int]]:
    pace = load_required_csv(PACE_REPLAY)
    fair = load_required_csv(FAIR_REPLAY)
    archive = load_required_csv(SHAPE_ARCHIVE)
    calendar = load_required_csv(CALENDAR)

    vic_keys = vic_race_keys(calendar)

    pace["meeting_date_key"] = pace["meeting_date"].map(clean).str[:10]
    if "track_norm" in pace.columns:
        pace["track_key"] = pace["track_norm"].where(pace["track_norm"].map(clean).ne(""), pace["track"].map(norm_track))
    else:
        pace["track_key"] = pace["track"].map(norm_track)
    pace["track_key"] = pace["track_key"].map(norm_track)
    pace["race_no_key"] = pace["race_no"].map(race_no_key)
    pace["horse_key_join"] = pace["horse_key"].where(pace["horse_key"].map(clean).ne(""), pace["horse"].map(canon_horse))
    pace["horse_key_join"] = pace["horse_key_join"].map(canon_horse)
    pace["vic_race_flag"] = pace.apply(
        lambda row: (row["meeting_date_key"], row["track_key"], row["race_no_key"]) in vic_keys,
        axis=1,
    )
    pace = pace[pace["vic_race_flag"]].copy()
    pace["runner_score_num"] = pd.to_numeric(pace["runner_score"], errors="coerce")
    pace["runner_rank_num"] = pd.to_numeric(pace["runner_rank"], errors="coerce")
    pace["won_num"] = pd.to_numeric(pace["won"], errors="coerce").fillna(0).astype(int)
    pace["finish_position_num"] = pd.to_numeric(pace["finish_position"], errors="coerce")
    pace["place_num"] = pace["finish_position_num"].le(3).fillna(False).astype(int)
    pace["role_bucket_v1"] = pace["tactical_style_pre_race_v1"].map(upper)
    pace["tempo_bucket_v1"] = pace["pace_pressure_band_v1"].map(map_tempo_bucket)
    pace["tempo_certainty_v1"] = [
        tempo_certainty(scale, used)
        for scale, used in zip(pace["pace_confidence_scale_v1"], pace["style_used_for_pace_v1"])
    ]
    pace["race_key_v1"] = pace["race_key"].where(
        pace["race_key"].map(clean).ne(""),
        pace["meeting_date_key"] + "|" + pace["track_key"] + "|R" + pace["race_no_key"],
    )

    fair["meeting_date_key"] = fair["meeting_date"].map(clean).str[:10]
    fair["track_key"] = fair["track"].map(norm_track)
    fair["race_no_key"] = fair["race_no"].map(race_no_key)
    fair["horse_key_join"] = fair["horse"].map(canon_horse)
    fair["fair_prob_replay_v1_num"] = pd.to_numeric(fair["fair_prob_replay_v1"], errors="coerce")
    fair["fair_price_replay_v1_num"] = pd.to_numeric(fair["fair_price_replay_v1"], errors="coerce")
    fair_keep = fair[
        [
            "meeting_date_key",
            "track_key",
            "race_no_key",
            "horse_key_join",
            "fair_prob_replay_v1_num",
            "fair_price_replay_v1_num",
        ]
    ].drop_duplicates(["meeting_date_key", "track_key", "race_no_key", "horse_key_join"], keep="first")

    archive["meeting_date_key"] = archive["meeting_date"].map(clean).str[:10]
    archive["track_key"] = archive["track"].map(norm_track)
    archive["race_no_key"] = archive["race_no"].map(race_no_key)
    archive["horse_key_join"] = archive["horse_key_join"].map(canon_horse)
    archive["distance_band_v1_1"] = archive["distance"].map(distance_band)
    archive["condition_group_v1_1"] = archive["trackCondition"].map(map_condition_group)
    archive["field_size_band_v1_1"] = archive["field_size"].map(field_size_band)
    archive_keep = archive[
        [
            "meeting_date_key",
            "track_key",
            "race_no_key",
            "horse_key_join",
            "distance_band_v1_1",
            "condition_group_v1_1",
            "field_size_band_v1_1",
            "field_size",
            "trackCondition",
            "distance",
        ]
    ].drop_duplicates(["meeting_date_key", "track_key", "race_no_key", "horse_key_join"], keep="first")

    merged = pace.merge(
        fair_keep,
        on=["meeting_date_key", "track_key", "race_no_key", "horse_key_join"],
        how="left",
    ).merge(
        archive_keep,
        on=["meeting_date_key", "track_key", "race_no_key", "horse_key_join"],
        how="left",
    )

    merged["distance_band_v1_1"] = merged["distance_band_v1_1"].where(merged["distance_band_v1_1"].map(clean).ne(""), "UNKNOWN")
    merged["condition_group_v1_1"] = merged["condition_group_v1_1"].where(merged["condition_group_v1_1"].map(clean).ne(""), "UNKNOWN")
    merged["field_size_band_v1_1"] = merged["field_size_band_v1_1"].where(merged["field_size_band_v1_1"].map(clean).ne(""), pace["field_size_v1"].map(field_size_band))
    merged["field_size_band_v1_1"] = merged["field_size_band_v1_1"].where(merged["field_size_band_v1_1"].map(clean).ne(""), "UNKNOWN")
    merged["baseline_prob_pct_v1"] = merged["fair_prob_replay_v1_num"] * 100.0
    merged["baseline_probability_bucket_v1"] = merged["baseline_prob_pct_v1"].apply(
        lambda value: probability_bucket(value) if pd.notna(value) else "UNKNOWN"
    )

    metadata = {
        "pace_rows_loaded": int(len(pace)),
        "fair_rows_loaded": int(len(fair)),
        "archive_rows_loaded": int(len(archive)),
        "merged_rows": int(len(merged)),
        "races_used": int(merged["race_key_v1"].nunique()),
        "rows_with_baseline_probability": int(merged["fair_prob_replay_v1_num"].notna().sum()),
    }
    return merged, metadata


def build_adjustment_table(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[tuple[str, str], dict[str, object]]]:
    eligible = df[
        df["role_bucket_v1"].isin(ROLE_ORDER)
        & df["tempo_bucket_v1"].isin(TEMPO_ORDER)
        & df["runner_score_num"].notna()
        & df["fair_prob_replay_v1_num"].notna()
        & df["tempo_certainty_v1"].ne("NONE")
    ].copy()

    role_stats = (
        eligible.groupby("role_bucket_v1", as_index=False)
        .agg(
            run_style_sample_v1_1=("horse_key_join", "count"),
            run_style_wins_v1_1=("won_num", "sum"),
            run_style_places_v1_1=("place_num", "sum"),
        )
    )
    role_stats["run_style_win_pct_v1_1"] = role_stats.apply(
        lambda row: safe_pct(row["run_style_wins_v1_1"], row["run_style_sample_v1_1"]), axis=1
    )
    role_stats["run_style_place_pct_v1_1"] = role_stats.apply(
        lambda row: safe_pct(row["run_style_places_v1_1"], row["run_style_sample_v1_1"]), axis=1
    )

    tempo_stats = (
        eligible.groupby("tempo_bucket_v1", as_index=False)
        .agg(
            tempo_sample_v1_1=("horse_key_join", "count"),
            tempo_wins_v1_1=("won_num", "sum"),
            tempo_places_v1_1=("place_num", "sum"),
        )
    )
    tempo_stats["tempo_win_pct_v1_1"] = tempo_stats.apply(
        lambda row: safe_pct(row["tempo_wins_v1_1"], row["tempo_sample_v1_1"]), axis=1
    )
    tempo_stats["tempo_place_pct_v1_1"] = tempo_stats.apply(
        lambda row: safe_pct(row["tempo_places_v1_1"], row["tempo_sample_v1_1"]), axis=1
    )

    combo_stats = (
        eligible.groupby(["role_bucket_v1", "tempo_bucket_v1"], as_index=False)
        .agg(
            combo_sample_v1_1=("horse_key_join", "count"),
            wins=("won_num", "sum"),
            places=("place_num", "sum"),
        )
    )
    combo_stats["combo_win_pct_v1_1"] = combo_stats.apply(
        lambda row: safe_pct(row["wins"], row["combo_sample_v1_1"]), axis=1
    )
    combo_stats["combo_place_pct_v1_1"] = combo_stats.apply(
        lambda row: safe_pct(row["places"], row["combo_sample_v1_1"]), axis=1
    )

    combo_stats = combo_stats.merge(
        role_stats[
            [
                "role_bucket_v1",
                "run_style_sample_v1_1",
                "run_style_win_pct_v1_1",
                "run_style_place_pct_v1_1",
            ]
        ],
        on="role_bucket_v1",
        how="left",
    ).merge(
        tempo_stats[
            [
                "tempo_bucket_v1",
                "tempo_sample_v1_1",
                "tempo_win_pct_v1_1",
                "tempo_place_pct_v1_1",
            ]
        ],
        on="tempo_bucket_v1",
        how="left",
    )

    combo_stats["win_lift_vs_run_style_pts_v1_1"] = (
        combo_stats["combo_win_pct_v1_1"] - combo_stats["run_style_win_pct_v1_1"]
    ).round(2)
    combo_stats["place_lift_vs_run_style_pts_v1_1"] = (
        combo_stats["combo_place_pct_v1_1"] - combo_stats["run_style_place_pct_v1_1"]
    ).round(2)
    combo_stats["signal_contradicts_place_v1_1"] = (
        (combo_stats["win_lift_vs_run_style_pts_v1_1"] > 0) & (combo_stats["place_lift_vs_run_style_pts_v1_1"] < 0)
    ) | (
        (combo_stats["win_lift_vs_run_style_pts_v1_1"] < 0) & (combo_stats["place_lift_vs_run_style_pts_v1_1"] > 0)
    )
    combo_stats["sample_floor_pass_v1_1"] = (
        combo_stats["combo_sample_v1_1"].ge(COMBO_SAMPLE_FLOOR)
        & combo_stats["tempo_sample_v1_1"].ge(TEMPO_SAMPLE_FLOOR)
        & combo_stats["run_style_sample_v1_1"].ge(RUN_STYLE_SAMPLE_FLOOR)
    )
    combo_stats["raw_adjustment_pct_v1_1"] = (
        (
            (0.65 * combo_stats["win_lift_vs_run_style_pts_v1_1"])
            + (0.35 * combo_stats["place_lift_vs_run_style_pts_v1_1"])
        ) / 200.0
    )
    combo_stats["applied_adjustment_pct_v1_1"] = combo_stats.apply(
        lambda row: 0.0
        if (not bool(row["sample_floor_pass_v1_1"])) or bool(row["signal_contradicts_place_v1_1"])
        else clip(float(row["raw_adjustment_pct_v1_1"]), MIN_ADJUSTMENT_PCT, MAX_ADJUSTMENT_PCT),
        axis=1,
    )
    combo_stats["adjustment_status_v1_1"] = combo_stats.apply(
        lambda row: "NO_ADJUSTMENT_SIGNAL_CONTRADICTION"
        if bool(row["signal_contradicts_place_v1_1"])
        else "NO_ADJUSTMENT_SAMPLE_FLOOR_FAIL"
        if not bool(row["sample_floor_pass_v1_1"])
        else "LIGHT_SHAPE_V1_1_APPLIED",
        axis=1,
    )
    combo_stats["section"] = "ADJUSTMENT_COMBO"

    adjustment_map: dict[tuple[str, str], dict[str, object]] = {}
    for row in combo_stats.itertuples(index=False):
        adjustment_map[(row.role_bucket_v1, row.tempo_bucket_v1)] = {
            "applied_adjustment_pct_v1_1": float(row.applied_adjustment_pct_v1_1),
            "sample_floor_pass_v1_1": bool(row.sample_floor_pass_v1_1),
            "signal_contradicts_place_v1_1": bool(row.signal_contradicts_place_v1_1),
            "adjustment_status_v1_1": row.adjustment_status_v1_1,
        }
    return combo_stats, adjustment_map


def apply_scenarios(df: pd.DataFrame, adjustment_map: dict[tuple[str, str], dict[str, object]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = df[df["fair_prob_replay_v1_num"].notna()].copy()
    base["baseline_probability_v1"] = base["fair_prob_replay_v1_num"]
    base["baseline_fair_price_v1"] = base["fair_price_replay_v1_num"]

    applied_adjustments = []
    statuses = []
    for row in base.itertuples(index=False):
        if row.role_bucket_v1 not in ROLE_ORDER or row.tempo_bucket_v1 not in TEMPO_ORDER or row.tempo_certainty_v1 == "NONE":
            applied_adjustments.append(0.0)
            statuses.append("NO_ADJUSTMENT_INSUFFICIENT_ROW_CONTEXT")
            continue
        meta = adjustment_map.get((row.role_bucket_v1, row.tempo_bucket_v1))
        if not meta:
            applied_adjustments.append(0.0)
            statuses.append("NO_ADJUSTMENT_MISSING_COMBO")
            continue
        applied_adjustments.append(float(meta["applied_adjustment_pct_v1_1"]))
        statuses.append(str(meta["adjustment_status_v1_1"]))

    base["light_shape_adjustment_pct_v1_1"] = applied_adjustments
    base["light_shape_status_v1_1"] = statuses
    base["light_shape_raw_probability_v1_1"] = base["baseline_probability_v1"] * (1.0 + base["light_shape_adjustment_pct_v1_1"])

    scenario_rows: list[pd.DataFrame] = []
    calibration_rows: list[pd.DataFrame] = []

    for scenario_name in ["NO_SHAPE", "LIGHT_SHAPE_V1_1"]:
        scenario = base.copy()
        if scenario_name == "NO_SHAPE":
            scenario["scenario_probability_v1"] = scenario["baseline_probability_v1"]
            scenario["scenario_adjustment_pct_v1"] = 0.0
        else:
            scenario["scenario_probability_v1"] = scenario["light_shape_raw_probability_v1_1"]
            scenario["scenario_adjustment_pct_v1"] = scenario["light_shape_adjustment_pct_v1_1"]

        for race_key, race in scenario.groupby("race_key_v1", sort=False):
            prob_sum = float(race["scenario_probability_v1"].sum())
            if prob_sum > 0:
                scenario.loc[race.index, "scenario_probability_v1"] = race["scenario_probability_v1"] / prob_sum

        scenario["scenario_fair_price_v1"] = scenario["scenario_probability_v1"].apply(
            lambda value: 1.0 / value if pd.notna(value) and value > 0 else math.nan
        )
        scenario = scenario.sort_values(
            ["race_key_v1", "scenario_probability_v1", "horse_key_join"],
            ascending=[True, False, True],
        ).copy()
        scenario["scenario_rank_v1"] = scenario.groupby("race_key_v1").cumcount() + 1
        scenario["scenario_name_v1"] = scenario_name
        scenario["probability_bucket_v1"] = (scenario["scenario_probability_v1"] * 100.0).apply(probability_bucket)
        scenario["fair_price_movement_v1"] = (scenario["scenario_fair_price_v1"] - scenario["baseline_fair_price_v1"]).abs()
        scenario["rank_changed_flag_v1"] = scenario["scenario_rank_v1"].ne(scenario["runner_rank_num"]).astype(int)

        scenario_rows.append(scenario)
        calibration_rows.append(scenario)

    scenarios = pd.concat(scenario_rows, ignore_index=True)

    baseline_top = scenarios[scenarios["scenario_name_v1"].eq("NO_SHAPE") & scenarios["scenario_rank_v1"].eq(1)][
        ["race_key_v1", "horse_key_join"]
    ].rename(columns={"horse_key_join": "baseline_top_horse_key"})
    scenarios = scenarios.merge(baseline_top, on="race_key_v1", how="left")
    scenarios["top_pick_changed_flag_v1"] = (
        scenarios["scenario_name_v1"].eq("LIGHT_SHAPE_V1_1")
        & scenarios["scenario_rank_v1"].eq(1)
        & scenarios["horse_key_join"].ne(scenarios["baseline_top_horse_key"])
    ).astype(int)

    calibration = pd.concat(calibration_rows, ignore_index=True)
    return scenarios, calibration


def scenario_summary(scenarios: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scenario_name, frame in scenarios.groupby("scenario_name_v1", sort=False):
        winners = frame[frame["won_num"].eq(1)].copy()
        winner_best = winners.groupby("race_key_v1", as_index=False)["scenario_rank_v1"].min()
        top_picks = frame[frame["scenario_rank_v1"].eq(1)].copy()
        rows.append(
            {
                "section": "SCENARIO_SUMMARY",
                "scenario_name_v1": scenario_name,
                "races": int(frame["race_key_v1"].nunique()),
                "rank1_rows": int(len(top_picks)),
                "rank1_wins": int(top_picks["won_num"].sum()),
                "rank1_places": int(top_picks["place_num"].sum()),
                "rank1_win_pct": round(safe_pct(top_picks["won_num"].sum(), len(top_picks)), 2),
                "rank1_place_pct": round(safe_pct(top_picks["place_num"].sum(), len(top_picks)), 2),
                "top3_winner_capture_pct": round(safe_pct(int(winner_best["scenario_rank_v1"].le(3).sum()), len(winner_best)), 2),
                "avg_abs_fair_price_movement_v1": round(float(top_picks["fair_price_movement_v1"].mean()) if len(top_picks) else 0.0, 4),
                "rank_changed_rows_v1": int(frame["rank_changed_flag_v1"].sum()),
                "top_pick_changed_races_v1": int(top_picks["top_pick_changed_flag_v1"].sum()) if "top_pick_changed_flag_v1" in top_picks.columns else 0,
            }
        )
    return pd.DataFrame(rows)


def segment_summary(scenarios: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    top_picks_all = scenarios[scenarios["scenario_rank_v1"].eq(1)].copy()
    winner_best_all = scenarios[scenarios["won_num"].eq(1)].groupby(
        ["scenario_name_v1", "race_key_v1", "distance_band_v1_1", "field_size_band_v1_1", "condition_group_v1_1"],
        as_index=False,
    )["scenario_rank_v1"].min()

    segment_defs = [
        ("distance_band_v1_1", sorted(scenarios["distance_band_v1_1"].dropna().unique().tolist())),
        ("field_size_band_v1_1", sorted(scenarios["field_size_band_v1_1"].dropna().unique().tolist())),
        ("condition_group_v1_1", sorted(scenarios["condition_group_v1_1"].dropna().unique().tolist())),
        ("tempo_certainty_v1", sorted(scenarios["tempo_certainty_v1"].dropna().unique().tolist())),
    ]

    for segment_type, segment_values in segment_defs:
        for scenario_name in ["NO_SHAPE", "LIGHT_SHAPE_V1_1"]:
            scenario_frame = scenarios[scenarios["scenario_name_v1"].eq(scenario_name)].copy()
            top_picks = top_picks_all[top_picks_all["scenario_name_v1"].eq(scenario_name)].copy()
            winners = scenario_frame[scenario_frame["won_num"].eq(1)].copy()
            for segment_value in segment_values:
                if clean(segment_value) == "":
                    continue
                top_segment = top_picks[top_picks[segment_type].eq(segment_value)].copy()
                winner_segment = winners[winners[segment_type].eq(segment_value)].groupby("race_key_v1", as_index=False)[
                    "scenario_rank_v1"
                ].min()
                rows.append(
                    {
                        "section": "SEGMENT_REPLAY",
                        "scenario_name_v1": scenario_name,
                        "segment_type_v1": segment_type,
                        "segment_value_v1": segment_value,
                        "races": int(top_segment["race_key_v1"].nunique()),
                        "rank1_rows": int(len(top_segment)),
                        "rank1_win_pct": round(safe_pct(top_segment["won_num"].sum(), len(top_segment)), 2),
                        "rank1_place_pct": round(safe_pct(top_segment["place_num"].sum(), len(top_segment)), 2),
                        "top3_winner_capture_pct": round(
                            safe_pct(int(winner_segment["scenario_rank_v1"].le(3).sum()), len(winner_segment)), 2
                        ),
                        "avg_abs_fair_price_movement_v1": round(float(top_segment["fair_price_movement_v1"].mean()) if len(top_segment) else 0.0, 4),
                        "rank_changed_rows_v1": int(scenario_frame[scenario_frame[segment_type].eq(segment_value)]["rank_changed_flag_v1"].sum()),
                        "top_pick_changed_races_v1": int(top_segment["top_pick_changed_flag_v1"].sum()) if "top_pick_changed_flag_v1" in top_segment.columns else 0,
                    }
                )
    return pd.DataFrame(rows)


def probability_calibration(calibration: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    rows: list[dict[str, object]] = []
    weighted_abs_gap: dict[str, float] = {}
    for scenario_name, frame in calibration.groupby("scenario_name_v1", sort=False):
        bucket_rows = []
        total_runners = int(len(frame))
        weighted_gap = 0.0
        for _, _, bucket in PROBABILITY_BUCKETS:
            subset = frame[frame["probability_bucket_v1"].eq(bucket)].copy()
            runners = int(len(subset))
            wins = int(subset["won_num"].sum()) if runners else 0
            actual_win_pct = safe_pct(wins, runners)
            avg_pred_prob_pct = float(subset["scenario_probability_v1"].mean() * 100.0) if runners else 0.0
            calibration_gap = actual_win_pct - avg_pred_prob_pct
            weighted_gap += abs(calibration_gap) * runners
            bucket_rows.append(
                {
                    "section": "PROBABILITY_BUCKET_CALIBRATION",
                    "scenario_name_v1": scenario_name,
                    "probability_bucket_v1": bucket,
                    "runners": runners,
                    "wins": wins,
                    "avg_pred_prob_pct_v1": round(avg_pred_prob_pct, 2),
                    "actual_win_pct_v1": round(actual_win_pct, 2),
                    "calibration_gap_pts_v1": round(calibration_gap, 2),
                }
            )
        rows.extend(bucket_rows)
        weighted_abs_gap[scenario_name] = round(weighted_gap / total_runners, 4) if total_runners else 0.0
    return pd.DataFrame(rows), weighted_abs_gap


def choose_recommendation(summary_df: pd.DataFrame, calibration_gap: dict[str, float]) -> tuple[str, str]:
    base = summary_df[summary_df["scenario_name_v1"].eq("NO_SHAPE")].iloc[0]
    light = summary_df[summary_df["scenario_name_v1"].eq("LIGHT_SHAPE_V1_1")].iloc[0]

    win_delta = float(light["rank1_win_pct"] - base["rank1_win_pct"])
    place_delta = float(light["rank1_place_pct"] - base["rank1_place_pct"])
    top3_delta = float(light["top3_winner_capture_pct"] - base["top3_winner_capture_pct"])
    cal_delta = float(calibration_gap.get("LIGHT_SHAPE_V1_1", 0.0) - calibration_gap.get("NO_SHAPE", 0.0))

    if win_delta <= -0.1 or place_delta <= -0.1 or top3_delta <= -0.1 or cal_delta > 0.15:
        return "REJECT", "Light shape worsened key replay or calibration metrics beyond the safety tolerance."

    if win_delta >= 0 and place_delta >= 0 and top3_delta >= 0 and cal_delta <= 0.0:
        if (win_delta > 0 or place_delta > 0 or top3_delta > 0) and int(light["top_pick_changed_races_v1"]) <= max(25, int(light["races"] * 0.02)):
            return "PROMOTE_TO_LIVE_CANDIDATE", "Light shape improved rank, place, and capture without hurting calibration."
        return "PROMOTE_TO_RESEARCH_SIDECAR", "Light shape stayed calibration-safe and performance-neutral to positive."

    if (win_delta > 0 or place_delta > 0) and top3_delta >= -0.05 and cal_delta <= 0.05:
        return "PROMOTE_TO_RESEARCH_SIDECAR", "Light shape produced a small positive replay effect while staying within calibration tolerance."

    return "KEEP_AS_EXPLAINABILITY_ONLY", "Light shape remains informative, but the replay edge is too small or too mixed for stronger promotion."


def build_report(
    metadata: dict[str, int],
    combo_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    segment_df: pd.DataFrame,
    bucket_df: pd.DataFrame,
    calibration_gap: dict[str, float],
    recommendation: str,
    recommendation_reason: str,
) -> str:
    top_positive = combo_df.sort_values(["applied_adjustment_pct_v1_1", "combo_sample_v1_1"], ascending=[False, False]).head(5)
    top_negative = combo_df.sort_values(["applied_adjustment_pct_v1_1", "combo_sample_v1_1"], ascending=[True, False]).head(5)
    summary_cols = [
        "scenario_name_v1",
        "rank1_win_pct",
        "rank1_place_pct",
        "top3_winner_capture_pct",
        "avg_abs_fair_price_movement_v1",
        "rank_changed_rows_v1",
        "top_pick_changed_races_v1",
    ]
    segment_focus = segment_df[segment_df["scenario_name_v1"].eq("LIGHT_SHAPE_V1_1")].sort_values(
        ["rank1_win_pct", "races"], ascending=[False, False]
    ).head(8)

    def table_lines(frame: pd.DataFrame, cols: list[str]) -> str:
        if frame.empty:
            return "- none"
        return "\n".join("- " + " | ".join(str(value) for value in row) for row in frame[cols].itertuples(index=False))

    return f"""# EDGEiQ Light Shape V1.1 Calibration Audit

Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}

## Scope

Research sidecar only. No V6.1, fair prices, live probabilities, or UI were changed.

## Inputs

- Pace replay rows loaded: {metadata['pace_rows_loaded']}
- Fair replay rows loaded: {metadata['fair_rows_loaded']}
- Shape archive rows loaded: {metadata['archive_rows_loaded']}
- Victoria rows merged: {metadata['merged_rows']}
- Victoria races used: {metadata['races_used']}
- Rows with baseline probability: {metadata['rows_with_baseline_probability']}

## Guardrails

- combo sample floor: {COMBO_SAMPLE_FLOOR}
- tempo sample floor: {TEMPO_SAMPLE_FLOOR}
- run-style sample floor: {RUN_STYLE_SAMPLE_FLOOR}
- max uplift: +3%
- max penalty: -3%
- no adjustment when sample floor fails
- no adjustment when win and place signals contradict

## Applied Adjustment Table

Top positive allowed combos:
{table_lines(top_positive, ['role_bucket_v1', 'tempo_bucket_v1', 'combo_sample_v1_1', 'win_lift_vs_run_style_pts_v1_1', 'place_lift_vs_run_style_pts_v1_1', 'applied_adjustment_pct_v1_1'])}

Top negative allowed combos:
{table_lines(top_negative, ['role_bucket_v1', 'tempo_bucket_v1', 'combo_sample_v1_1', 'win_lift_vs_run_style_pts_v1_1', 'place_lift_vs_run_style_pts_v1_1', 'applied_adjustment_pct_v1_1'])}

## Scenario Replay

{table_lines(summary_df, summary_cols)}

Weighted absolute calibration gap:

- NO_SHAPE: {calibration_gap.get('NO_SHAPE', 0.0)}
- LIGHT_SHAPE_V1_1: {calibration_gap.get('LIGHT_SHAPE_V1_1', 0.0)}

## Segment Focus

Best light-shape segments:
{table_lines(segment_focus, ['segment_type_v1', 'segment_value_v1', 'races', 'rank1_win_pct', 'top3_winner_capture_pct'])}

## Probability Bucket Calibration

{table_lines(bucket_df[bucket_df['scenario_name_v1'].eq('LIGHT_SHAPE_V1_1')], ['probability_bucket_v1', 'runners', 'avg_pred_prob_pct_v1', 'actual_win_pct_v1', 'calibration_gap_pts_v1'])}

## Recommendation

{recommendation}

Reason:
{recommendation_reason}
"""


def main() -> None:
    base, metadata = load_base()
    combo_df, adjustment_map = build_adjustment_table(base)
    scenarios, calibration = apply_scenarios(base, adjustment_map)
    summary_df = scenario_summary(scenarios)
    segment_df = segment_summary(scenarios)
    bucket_df, calibration_gap = probability_calibration(calibration)
    recommendation, recommendation_reason = choose_recommendation(summary_df, calibration_gap)

    combo_out = combo_df.copy()
    combo_out["section"] = "ADJUSTMENT_COMBO"
    summary_out = summary_df.copy()
    segment_out = segment_df.copy()
    bucket_out = bucket_df.copy()

    calibration_out = pd.concat(
        [combo_out, summary_out, segment_out, bucket_out],
        ignore_index=True,
        sort=False,
    )
    calibration_out.to_csv(OUT_CALIBRATION, index=False)

    base_row = summary_df[summary_df["scenario_name_v1"].eq("NO_SHAPE")].iloc[0]
    light_row = summary_df[summary_df["scenario_name_v1"].eq("LIGHT_SHAPE_V1_1")].iloc[0]
    summary_row = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows_used": metadata["merged_rows"],
        "races_used": metadata["races_used"],
        "rows_with_baseline_probability": metadata["rows_with_baseline_probability"],
        "combo_rows_total": int(len(combo_df)),
        "combo_rows_with_adjustment": int(combo_df["applied_adjustment_pct_v1_1"].ne(0).sum()),
        "baseline_rank1_win_pct": float(base_row["rank1_win_pct"]),
        "light_shape_rank1_win_pct": float(light_row["rank1_win_pct"]),
        "rank1_win_pct_delta": round(float(light_row["rank1_win_pct"] - base_row["rank1_win_pct"]), 2),
        "baseline_rank1_place_pct": float(base_row["rank1_place_pct"]),
        "light_shape_rank1_place_pct": float(light_row["rank1_place_pct"]),
        "rank1_place_pct_delta": round(float(light_row["rank1_place_pct"] - base_row["rank1_place_pct"]), 2),
        "baseline_top3_winner_capture_pct": float(base_row["top3_winner_capture_pct"]),
        "light_shape_top3_winner_capture_pct": float(light_row["top3_winner_capture_pct"]),
        "top3_winner_capture_pct_delta": round(float(light_row["top3_winner_capture_pct"] - base_row["top3_winner_capture_pct"]), 2),
        "avg_abs_fair_price_movement_v1": round(float(light_row["avg_abs_fair_price_movement_v1"]), 4),
        "rank_changed_rows_v1": int(light_row["rank_changed_rows_v1"]),
        "top_pick_changed_races_v1": int(light_row["top_pick_changed_races_v1"]),
        "baseline_weighted_abs_calibration_gap_pts": calibration_gap.get("NO_SHAPE", 0.0),
        "light_shape_weighted_abs_calibration_gap_pts": calibration_gap.get("LIGHT_SHAPE_V1_1", 0.0),
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
    }
    pd.DataFrame([summary_row]).to_csv(OUT_SUMMARY, index=False)

    OUT_REPORT.write_text(
        build_report(
            metadata=metadata,
            combo_df=combo_df,
            summary_df=summary_df,
            segment_df=segment_df,
            bucket_df=bucket_df,
            calibration_gap=calibration_gap,
            recommendation=recommendation,
            recommendation_reason=recommendation_reason,
        ),
        encoding="utf-8",
    )

    print("[LIGHT_SHAPE_V1_1_CALIBRATION] COMPLETE")
    print(f"rows_used={metadata['merged_rows']}")
    print(f"races_used={metadata['races_used']}")
    print(f"combo_rows_with_adjustment={int(combo_df['applied_adjustment_pct_v1_1'].ne(0).sum())}")
    print(f"baseline_rank1_win_pct={summary_row['baseline_rank1_win_pct']}")
    print(f"light_shape_rank1_win_pct={summary_row['light_shape_rank1_win_pct']}")
    print(f"baseline_top3_winner_capture_pct={summary_row['baseline_top3_winner_capture_pct']}")
    print(f"light_shape_top3_winner_capture_pct={summary_row['light_shape_top3_winner_capture_pct']}")
    print(f"recommendation={recommendation}")
    print(f"wrote={OUT_CALIBRATION}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_REPORT}")


if __name__ == "__main__":
    main()
