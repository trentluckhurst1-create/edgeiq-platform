from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PACE_REPLAY = DATA / "edgeiq_pace_advantage_replay_v1.csv"
ENV_REPLAY = DATA / "edgeiq_environment_score_replay_v1.csv"

OUTPUT_RUNNER = DATA / "edgeiq_pace_pressure_engine_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_pace_pressure_engine_v1_summary.csv"
OUTPUT_BY_BAND = DATA / "edgeiq_pace_pressure_engine_v1_by_band.csv"
OUTPUT_RACE = DATA / "edgeiq_pace_pressure_engine_v1_race_level.csv"
OUTPUT_VERDICT = DATA / "edgeiq_pace_pressure_engine_v1_verdict.csv"

SPONSOR_TOKENS = {"BET365", "LADBROKES", "SPORTSBET", "APIAM", "TAB", "NEDS"}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def parse_float(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "").replace("$", "")
    if text.upper() in {"NA", "N/A", "NULL", "NONE", "-", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalise_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        return pd.to_datetime(text).strftime("%Y-%m-%d")
    except Exception:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        return match.group(1) if match else text


def normalise_track(value: object) -> str:
    text = clean_text(value).upper()
    if not text:
        return ""
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    parts = [part for part in text.split() if part and part not in SPONSOR_TOKENS]
    return " ".join(parts)


def normalise_track_key(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", normalise_track(value))


def normalise_race_no(value: object) -> str:
    text = clean_text(value)
    match = re.search(r"(\d+)", text)
    return str(int(match.group(1))) if match else ""


def normalise_horse_key(value: object) -> str:
    text = clean_text(value).upper()
    if not text:
        return ""
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def normalise_role(value: object) -> str:
    text = clean_text(value).upper().replace(" ", "_")
    if text in {"LEADER", "LEAD"}:
        return "LEADER"
    if text in {"ON_PACE", "ONPACE", "ON-PACE"}:
        return "ON_PACE"
    if text in {"MIDFIELD", "MID_FIELD", "MID-FIELD"}:
        return "MIDFIELD"
    if text in {"BACKMARKER", "BACK_MARKER", "BACK-MARKER", "BACK"}:
        return "BACKMARKER"
    return "UNKNOWN"


def first_valid(series: pd.Series) -> float | None:
    for value in series:
        number = parse_float(value)
        if number is not None:
            return number
    return None


def first_text(series: pd.Series) -> str:
    for value in series:
        text = clean_text(value)
        if text:
            return text
    return ""


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def pressure_band(score: float) -> str:
    if score >= 60:
        return "EXTREME_PRESSURE"
    if score >= 40:
        return "HIGH_PRESSURE"
    if score >= 20:
        return "MODERATE_PRESSURE"
    return "LOW_PRESSURE"


def race_shape_summary(leaders_count: int, front_pressure_ratio: float, unknown_pressure_risk: float) -> str:
    if leaders_count == 1 and front_pressure_ratio <= 0.30:
        return "LONE_LEADER_LOW_PRESSURE"
    if leaders_count == 1 and front_pressure_ratio > 0.30:
        return "LEADER_WITH_PRESSURE"
    if leaders_count >= 3:
        return "MULTI_LEADER_PRESSURE"
    if front_pressure_ratio >= 0.50:
        return "FRONT_HEAVY"
    if unknown_pressure_risk >= 0.30:
        return "UNKNOWN_HEAVY"
    return "BALANCED"


def runner_fit(role: str, band: str) -> str:
    if role == "LEADER":
        return {
            "LOW_PRESSURE": "POSITIVE",
            "MODERATE_PRESSURE": "NEUTRAL",
            "HIGH_PRESSURE": "NEGATIVE",
            "EXTREME_PRESSURE": "POOR",
        }.get(band, "UNKNOWN")
    if role == "ON_PACE":
        return {
            "LOW_PRESSURE": "POSITIVE",
            "MODERATE_PRESSURE": "POSITIVE",
            "HIGH_PRESSURE": "NEUTRAL",
            "EXTREME_PRESSURE": "NEGATIVE",
        }.get(band, "UNKNOWN")
    if role == "MIDFIELD":
        return {
            "LOW_PRESSURE": "NEUTRAL",
            "MODERATE_PRESSURE": "NEUTRAL",
            "HIGH_PRESSURE": "POSITIVE",
            "EXTREME_PRESSURE": "POSITIVE",
        }.get(band, "UNKNOWN")
    if role == "BACKMARKER":
        return {
            "LOW_PRESSURE": "NEGATIVE",
            "MODERATE_PRESSURE": "NEUTRAL",
            "HIGH_PRESSURE": "POSITIVE",
            "EXTREME_PRESSURE": "POSITIVE",
        }.get(band, "UNKNOWN")
    return "UNKNOWN"


def format_metric(value: float | None) -> object:
    if value is None:
        return "NA"
    return round(float(value), 2)


def build_group_metrics(df: pd.DataFrame, analysis_scope: str, group_col: str, rank1_only: bool = False) -> pd.DataFrame:
    source = df[df["runner_rank_num_v1"] == 1].copy() if rank1_only else df.copy()
    rows: list[dict[str, object]] = []
    if source.empty:
        return pd.DataFrame(columns=[
            "analysis_scope_v1",
            "group_value_v1",
            "rank1_only_v1",
            "runners",
            "wins",
            "win_pct",
            "avg_field_size",
            "avg_leaders_count",
            "avg_front_pressure_ratio",
            "avg_unknown_pressure_risk",
        ])

    for group_value, group in source.groupby(group_col, dropna=False):
        runners = int(len(group))
        wins = int(group["won_num_v1"].sum())
        rows.append({
            "analysis_scope_v1": analysis_scope,
            "group_value_v1": clean_text(group_value) or "UNKNOWN",
            "rank1_only_v1": "YES" if rank1_only else "NO",
            "runners": runners,
            "wins": wins,
            "win_pct": round((wins / runners) * 100, 2) if runners else 0.0,
            "avg_field_size": round(group["field_size_v1"].mean(), 4) if runners else 0.0,
            "avg_leaders_count": round(group["leaders_count_v1"].mean(), 4) if runners else 0.0,
            "avg_front_pressure_ratio": round(group["front_pressure_ratio_v1"].mean(), 4) if runners else 0.0,
            "avg_unknown_pressure_risk": round(group["unknown_pressure_risk_v1"].mean(), 4) if runners else 0.0,
        })

    return pd.DataFrame(rows).sort_values(["analysis_scope_v1", "win_pct", "runners", "group_value_v1"], ascending=[True, False, False, True]).reset_index(drop=True)


def metric_lookup(df: pd.DataFrame, scope: str, group_value: str) -> float | None:
    subset = df[(df["analysis_scope_v1"] == scope) & (df["group_value_v1"] == group_value)]
    if subset.empty:
        return None
    return float(subset.iloc[0]["win_pct"])


def main() -> None:
    if not PACE_REPLAY.exists():
        raise FileNotFoundError(f"Missing input file: {PACE_REPLAY}")
    if not ENV_REPLAY.exists():
        raise FileNotFoundError(f"Missing input file: {ENV_REPLAY}")

    pace_df = pd.read_csv(PACE_REPLAY, dtype=str, keep_default_na=False)
    env_df = pd.read_csv(ENV_REPLAY, dtype=str, keep_default_na=False)

    pace_df["meeting_date_norm_v1"] = pace_df["meeting_date"].map(normalise_date)
    pace_df["track_norm_v1"] = pace_df["track"].map(normalise_track)
    pace_df["track_key_norm_v1"] = pace_df["track"].map(normalise_track_key)
    pace_df["race_no_norm_v1"] = pace_df["race_no"].map(normalise_race_no)
    pace_df["horse_key_norm_v1"] = pace_df["horse"].map(normalise_horse_key)
    pace_df["race_join_v1"] = pace_df["meeting_date_norm_v1"] + "|" + pace_df["track_key_norm_v1"] + "|R" + pace_df["race_no_norm_v1"]
    pace_df["pace_role_norm_v1"] = pace_df["pace_role_v1"].map(normalise_role)
    pace_df["won_num_v1"] = pace_df["won"].map(lambda x: int(parse_float(x) or 0))
    pace_df["placed_num_v1"] = pace_df["placed"].map(lambda x: int(parse_float(x) or 0))
    pace_df["finish_position_num_v1"] = pace_df["finish_position"].map(parse_float)
    pace_df["runner_rank_num_v1"] = pace_df["runner_rank"].map(parse_float)
    pace_df["runner_score_num_v1"] = pace_df["runner_score"].map(parse_float)
    pace_df["score_share_of_race_num_v1"] = pace_df["score_share_of_race"].map(parse_float)
    pace_df["dominance_score_num_v1"] = pace_df["dominance_score_v1"].map(parse_float)

    env_df["meeting_date_norm_v1"] = env_df["meeting_date"].map(normalise_date)
    env_df["track_norm_v1"] = env_df["track"].map(normalise_track)
    env_df["track_key_norm_v1"] = env_df["track"].map(normalise_track_key)
    env_df["race_no_norm_v1"] = env_df["race_no"].map(normalise_race_no)
    env_df["race_join_v1"] = env_df["meeting_date_norm_v1"] + "|" + env_df["track_key_norm_v1"] + "|R" + env_df["race_no_norm_v1"]

    env_race = env_df[[
        "race_join_v1",
        "environment_score_v1",
        "environment_band_v1",
        "gap_1_2",
        "gap_1_3",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_certainty_band",
        "field_size",
        "trust_profile_v1",
        "trust_band_v1",
    ]].drop_duplicates(subset=["race_join_v1"]).copy()

    race_rows: list[dict[str, object]] = []
    for race_join, group in pace_df.groupby("race_join_v1", dropna=False):
        if not clean_text(race_join):
            continue

        field_size_val = first_valid(group["field_size"])
        field_size = int(round(field_size_val)) if field_size_val is not None and field_size_val > 0 else int(len(group))

        derived_counts = group["pace_role_norm_v1"].value_counts().to_dict()
        leaders_existing = first_valid(group["leaders_v1"])
        on_pace_existing = first_valid(group["on_pace_v1"])
        midfield_existing = first_valid(group["midfield_v1"])
        backmarkers_existing = first_valid(group["backmarkers_v1"])
        unknown_existing = first_valid(group["unknown_pace_v1"])

        leaders_count = int(round(leaders_existing)) if leaders_existing is not None else int(derived_counts.get("LEADER", 0))
        on_pace_count = int(round(on_pace_existing)) if on_pace_existing is not None else int(derived_counts.get("ON_PACE", 0))
        midfield_count = int(round(midfield_existing)) if midfield_existing is not None else int(derived_counts.get("MIDFIELD", 0))
        backmarkers_count = int(round(backmarkers_existing)) if backmarkers_existing is not None else int(derived_counts.get("BACKMARKER", 0))
        unknown_count = int(round(unknown_existing)) if unknown_existing is not None else int(derived_counts.get("UNKNOWN", 0))

        known_ratio_existing = first_valid(group["known_pace_ratio_v1"])
        early_density_existing = first_valid(group["early_speed_density_v1"])
        race_density_existing = first_valid(group["race_shape_density_v1"])

        pressure_front_count = leaders_count + on_pace_count
        leader_pressure_ratio = round(leaders_count / field_size, 4) if field_size else 0.0
        front_pressure_ratio = round(pressure_front_count / field_size, 4) if field_size else 0.0
        unknown_pressure_risk = round(unknown_count / field_size, 4) if field_size else 0.0
        known_pace_ratio = round(known_ratio_existing, 4) if known_ratio_existing is not None else round(1 - unknown_pressure_risk, 4)
        early_speed_density = round(early_density_existing, 4) if early_density_existing is not None else round(leader_pressure_ratio + (on_pace_count / field_size if field_size else 0.0), 4)
        race_shape_density = clean_text(first_text(group["race_shape_density_v1"])) or (clean_text(race_density_existing) if race_density_existing is not None else "UNKNOWN")

        score = 0
        if leaders_count >= 4:
            score += 25
        elif leaders_count == 3:
            score += 18
        elif leaders_count == 2:
            score += 10
        elif leaders_count == 1:
            score -= 10

        if on_pace_count >= 4:
            score += 15
        elif on_pace_count == 3:
            score += 10
        elif on_pace_count == 2:
            score += 5

        if front_pressure_ratio >= 0.55:
            score += 15
        elif front_pressure_ratio >= 0.45:
            score += 10
        elif front_pressure_ratio >= 0.35:
            score += 5

        if unknown_pressure_risk >= 0.30:
            score += 10
        elif unknown_pressure_risk >= 0.20:
            score += 5

        if leaders_count == 1 and on_pace_count <= 2:
            score -= 10
        if leaders_count == 1 and front_pressure_ratio <= 0.30:
            score -= 15

        pace_competition_score = round(clamp(score, 0, 100), 2)
        pace_pressure_band = pressure_band(pace_competition_score)
        race_shape_summary_text = race_shape_summary(leaders_count, front_pressure_ratio, unknown_pressure_risk)

        race_rows.append({
            "race_join_v1": race_join,
            "meeting_date": first_text(group["meeting_date"]),
            "track": first_text(group["track"]),
            "race_no": first_text(group["race_no"]),
            "race_key_v1": first_text(group["race_key"]),
            "field_size_v1": field_size,
            "leaders_count_v1": leaders_count,
            "on_pace_count_v1": on_pace_count,
            "midfield_count_v1": midfield_count,
            "backmarkers_count_v1": backmarkers_count,
            "unknown_pace_count_v1": unknown_count,
            "known_pace_ratio_v1": known_pace_ratio,
            "early_speed_density_v1": early_speed_density,
            "race_shape_density_v1": race_shape_density,
            "pressure_front_count_v1": pressure_front_count,
            "leader_pressure_ratio_v1": leader_pressure_ratio,
            "front_pressure_ratio_v1": front_pressure_ratio,
            "unknown_pressure_risk_v1": unknown_pressure_risk,
            "pace_competition_score_v1": pace_competition_score,
            "pace_pressure_band_v1": pace_pressure_band,
            "race_shape_summary_v1": race_shape_summary_text,
            "rank1_wins_race_v1": int(((group["runner_rank_num_v1"] == 1) & (group["won_num_v1"] == 1)).sum()),
        })

    race_df = pd.DataFrame(race_rows)
    race_df = race_df.merge(env_race, on="race_join_v1", how="left")

    runner_df = pace_df.merge(race_df, on="race_join_v1", how="left", suffixes=("", "_race"))
    runner_df["pace_pressure_runner_fit_v1"] = runner_df.apply(
        lambda row: runner_fit(clean_text(row.get("pace_role_norm_v1")), clean_text(row.get("pace_pressure_band_v1"))),
        axis=1,
    )

    runner_output = runner_df[[
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_key",
        "join_key_v1",
        "runner_rank",
        "runner_score",
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "environment_score_v1",
        "environment_band_v1",
        "won",
        "placed",
        "finish_position",
        "pace_role_v1",
        "pace_advantage_band_v1",
        "pace_advantage_score_v1",
        "field_size_v1",
        "leaders_count_v1",
        "on_pace_count_v1",
        "midfield_count_v1",
        "backmarkers_count_v1",
        "unknown_pace_count_v1",
        "known_pace_ratio_v1",
        "early_speed_density_v1",
        "race_shape_density_v1",
        "pressure_front_count_v1",
        "leader_pressure_ratio_v1",
        "front_pressure_ratio_v1",
        "unknown_pressure_risk_v1",
        "pace_competition_score_v1",
        "pace_pressure_band_v1",
        "race_shape_summary_v1",
        "pace_pressure_runner_fit_v1",
    ]].copy()
    runner_output.to_csv(OUTPUT_RUNNER, index=False)

    race_output = race_df[[
        "meeting_date",
        "track",
        "race_no",
        "race_key_v1",
        "field_size_v1",
        "leaders_count_v1",
        "on_pace_count_v1",
        "midfield_count_v1",
        "backmarkers_count_v1",
        "unknown_pace_count_v1",
        "known_pace_ratio_v1",
        "early_speed_density_v1",
        "race_shape_density_v1",
        "pressure_front_count_v1",
        "leader_pressure_ratio_v1",
        "front_pressure_ratio_v1",
        "unknown_pressure_risk_v1",
        "pace_competition_score_v1",
        "pace_pressure_band_v1",
        "race_shape_summary_v1",
        "environment_score_v1",
        "environment_band_v1",
        "gap_1_2",
        "gap_1_3",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_certainty_band",
        "trust_profile_v1",
        "trust_band_v1",
    ]].copy()
    race_output.to_csv(OUTPUT_RACE, index=False)

    group_frames = [
        build_group_metrics(runner_df, "PACE_PRESSURE_BAND", "pace_pressure_band_v1", rank1_only=False),
        build_group_metrics(runner_df, "RACE_SHAPE_SUMMARY", "race_shape_summary_v1", rank1_only=False),
        build_group_metrics(runner_df, "RUNNER_FIT", "pace_pressure_runner_fit_v1", rank1_only=False),
        build_group_metrics(runner_df, "RANK1_PRESSURE_BAND", "pace_pressure_band_v1", rank1_only=True),
        build_group_metrics(runner_df, "RANK1_RUNNER_FIT", "pace_pressure_runner_fit_v1", rank1_only=True),
    ]
    by_band_df = pd.concat(group_frames, ignore_index=True)
    by_band_df.to_csv(OUTPUT_BY_BAND, index=False)

    rows = int(len(runner_df))
    races = int(race_df.shape[0])
    rank1_df = runner_df[runner_df["runner_rank_num_v1"] == 1].copy()
    rank1_rows = int(len(rank1_df))
    rank1_wins = int(rank1_df["won_num_v1"].sum())
    rank1_win_pct = round((rank1_wins / rank1_rows) * 100, 2) if rank1_rows else 0.0

    low_pressure_rank1_win_pct = metric_lookup(by_band_df, "RANK1_PRESSURE_BAND", "LOW_PRESSURE")
    extreme_pressure_rank1_win_pct = metric_lookup(by_band_df, "RANK1_PRESSURE_BAND", "EXTREME_PRESSURE")
    runner_fit_positive_win_pct = metric_lookup(by_band_df, "RUNNER_FIT", "POSITIVE")
    runner_fit_poor_win_pct = metric_lookup(by_band_df, "RUNNER_FIT", "POOR")

    rank1_delta = round(low_pressure_rank1_win_pct - extreme_pressure_rank1_win_pct, 2) if low_pressure_rank1_win_pct is not None and extreme_pressure_rank1_win_pct is not None else None
    runner_fit_delta = round(runner_fit_positive_win_pct - runner_fit_poor_win_pct, 2) if runner_fit_positive_win_pct is not None and runner_fit_poor_win_pct is not None else None

    rank1_flag = rank1_delta is not None and rank1_delta >= 5
    runner_fit_flag = runner_fit_delta is not None and runner_fit_delta >= 5
    if rank1_flag and runner_fit_flag:
        verdict = "PACE_PRESSURE_ENGINE_PROMISING"
    elif rank1_flag:
        verdict = "PACE_PRESSURE_SEPARATES_RANK1"
    elif runner_fit_flag:
        verdict = "PACE_PRESSURE_RUNNER_FIT_SEPARATES"
    else:
        verdict = "PACE_PRESSURE_NOT_PROVEN"

    summary_rows = [
        {"metric": "rows", "value": rows},
        {"metric": "races", "value": races},
        {"metric": "rank1_rows", "value": rank1_rows},
        {"metric": "rank1_wins", "value": rank1_wins},
        {"metric": "rank1_win_pct", "value": rank1_win_pct},
        {"metric": "low_pressure_rank1_win_pct", "value": format_metric(low_pressure_rank1_win_pct)},
        {"metric": "extreme_pressure_rank1_win_pct", "value": format_metric(extreme_pressure_rank1_win_pct)},
        {"metric": "runner_fit_positive_win_pct", "value": format_metric(runner_fit_positive_win_pct)},
        {"metric": "runner_fit_poor_win_pct", "value": format_metric(runner_fit_poor_win_pct)},
        {"metric": "verdict", "value": verdict},
        {"metric": "output_runner", "value": str(OUTPUT_RUNNER)},
        {"metric": "output_race", "value": str(OUTPUT_RACE)},
        {"metric": "output_by_band", "value": str(OUTPUT_BY_BAND)},
        {"metric": "output_verdict", "value": str(OUTPUT_VERDICT)},
    ]
    pd.DataFrame(summary_rows).to_csv(OUTPUT_SUMMARY, index=False)

    verdict_rows = [
        {"metric": "rank1_low_minus_extreme_delta_pct", "value": format_metric(rank1_delta)},
        {"metric": "runner_fit_positive_minus_poor_delta_pct", "value": format_metric(runner_fit_delta)},
        {"metric": "rank1_separation_flag", "value": "YES" if rank1_flag else "NO"},
        {"metric": "runner_fit_separation_flag", "value": "YES" if runner_fit_flag else "NO"},
        {"metric": "verdict", "value": verdict},
    ]
    pd.DataFrame(verdict_rows).to_csv(OUTPUT_VERDICT, index=False)

    print("[PACE_PRESSURE_ENGINE_V1] COMPLETE")
    print(f"rows={rows}")
    print(f"races={races}")
    print(f"rank1_rows={rank1_rows}")
    print(f"rank1_win_pct={rank1_win_pct}")
    print(f"low_pressure_rank1_win_pct={format_metric(low_pressure_rank1_win_pct)}")
    print(f"extreme_pressure_rank1_win_pct={format_metric(extreme_pressure_rank1_win_pct)}")
    print(f"runner_fit_positive_win_pct={format_metric(runner_fit_positive_win_pct)}")
    print(f"runner_fit_poor_win_pct={format_metric(runner_fit_poor_win_pct)}")
    print(f"verdict={verdict}")
    print(f"wrote={OUTPUT_RUNNER}")
    print(f"wrote={OUTPUT_SUMMARY}")
    print(f"wrote={OUTPUT_BY_BAND}")
    print(f"wrote={OUTPUT_RACE}")
    print(f"wrote={OUTPUT_VERDICT}")


if __name__ == "__main__":
    main()
