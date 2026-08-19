from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PACE_RACE_LEVEL = DATA / "edgeiq_pace_pressure_engine_v1_race_level.csv"
ENV_REPLAY = DATA / "edgeiq_environment_score_replay_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_pace_pressure_threshold_audit_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_pace_pressure_threshold_audit_v1_summary.csv"

SPONSOR_TOKENS = {"BET365", "LADBROKES", "SPORTSBET", "APIAM", "TAB", "NEDS"}
BUCKET_ORDER = ["0_10", "10_20", "20_30", "30_40", "40_50", "50_PLUS"]
BUCKET_LABELS = {
    "0_10": "0-10",
    "10_20": "10-20",
    "20_30": "20-30",
    "30_40": "30-40",
    "40_50": "40-50",
    "50_PLUS": "50+",
}
MIN_BUCKET_RACES_FOR_SIGNAL = 300


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


def pressure_bucket(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    if score < 10:
        return "0_10"
    if score < 20:
        return "10_20"
    if score < 30:
        return "20_30"
    if score < 40:
        return "30_40"
    if score < 50:
        return "40_50"
    return "50_PLUS"


def build_join_key(meeting_date: str, track_key: str, race_no: str) -> str:
    return f"{meeting_date}|{track_key}|R{race_no}"


def format_metric(value: float | None) -> object:
    if value is None or pd.isna(value):
        return "NA"
    return round(float(value), 2)


def main() -> None:
    if not PACE_RACE_LEVEL.exists():
        raise FileNotFoundError(f"Missing input file: {PACE_RACE_LEVEL}")
    if not ENV_REPLAY.exists():
        raise FileNotFoundError(f"Missing input file: {ENV_REPLAY}")

    race_df = pd.read_csv(PACE_RACE_LEVEL, dtype=str, keep_default_na=False)
    env_df = pd.read_csv(ENV_REPLAY, dtype=str, keep_default_na=False)

    race_df["meeting_date_norm_v1"] = race_df["meeting_date"].map(normalise_date)
    race_df["track_key_norm_v1"] = race_df["track"].map(normalise_track_key)
    race_df["race_no_norm_v1"] = race_df["race_no"].map(normalise_race_no)
    race_df["race_join_v1"] = [
        build_join_key(d, t, r)
        for d, t, r in zip(race_df["meeting_date_norm_v1"], race_df["track_key_norm_v1"], race_df["race_no_norm_v1"])
    ]
    race_df["pace_competition_score_num_v1"] = race_df["pace_competition_score_v1"].map(parse_float)
    race_df["field_size_num_v1"] = race_df["field_size_v1"].map(parse_float)
    race_df["leaders_count_num_v1"] = race_df["leaders_count_v1"].map(parse_float)
    race_df["front_pressure_ratio_num_v1"] = race_df["front_pressure_ratio_v1"].map(parse_float)
    race_df["unknown_pressure_risk_num_v1"] = race_df["unknown_pressure_risk_v1"].map(parse_float)
    race_df["pressure_score_bucket_v1"] = race_df["pace_competition_score_num_v1"].map(pressure_bucket)

    env_df["meeting_date_norm_v1"] = env_df["meeting_date"].map(normalise_date)
    env_df["track_key_norm_v1"] = env_df["track"].map(normalise_track_key)
    env_df["race_no_norm_v1"] = env_df["race_no"].map(normalise_race_no)
    env_df["race_join_v1"] = [
        build_join_key(d, t, r)
        for d, t, r in zip(env_df["meeting_date_norm_v1"], env_df["track_key_norm_v1"], env_df["race_no_norm_v1"])
    ]
    env_race = env_df[["race_join_v1", "rank1_won", "rank1_finish_position"]].drop_duplicates(subset=["race_join_v1"]).copy()
    env_race["rank1_won_num_v1"] = env_race["rank1_won"].map(lambda x: int(parse_float(x) or 0))

    merged = race_df.merge(env_race, on="race_join_v1", how="left")

    bucket_rows: list[dict[str, object]] = []
    for bucket in BUCKET_ORDER:
        group = merged[merged["pressure_score_bucket_v1"] == bucket].copy()
        races = int(len(group))
        rank1_rows = races
        rank1_wins = int(group["rank1_won_num_v1"].fillna(0).sum()) if races else 0
        rank1_win_pct = round((rank1_wins / rank1_rows) * 100, 2) if rank1_rows else None
        bucket_rows.append({
            "pressure_score_bucket_v1": bucket,
            "pressure_score_bucket_label_v1": BUCKET_LABELS[bucket],
            "races": races,
            "rank1_rows": rank1_rows,
            "rank1_wins": rank1_wins,
            "rank1_win_pct": format_metric(rank1_win_pct),
            "avg_pressure_score_v1": format_metric(group["pace_competition_score_num_v1"].mean() if races else None),
            "min_pressure_score_v1": format_metric(group["pace_competition_score_num_v1"].min() if races else None),
            "max_pressure_score_v1": format_metric(group["pace_competition_score_num_v1"].max() if races else None),
            "avg_field_size_v1": format_metric(group["field_size_num_v1"].mean() if races else None),
            "avg_leaders_count_v1": format_metric(group["leaders_count_num_v1"].mean() if races else None),
            "avg_front_pressure_ratio_v1": format_metric(group["front_pressure_ratio_num_v1"].mean() if races else None),
            "avg_unknown_pressure_risk_v1": format_metric(group["unknown_pressure_risk_num_v1"].mean() if races else None),
            "environment_bands_present_v1": "|".join(sorted({clean_text(v) for v in group["environment_band_v1"] if clean_text(v)})),
            "trust_profiles_present_v1": "|".join(sorted({clean_text(v) for v in group["trust_profile_v1"] if clean_text(v)})),
            "sample_ge_300_v1": "YES" if races >= 300 else "NO",
        })

    bucket_df = pd.DataFrame(bucket_rows)
    bucket_df.to_csv(OUTPUT_MAIN, index=False)

    eligible = bucket_df[bucket_df["sample_ge_300_v1"] == "YES"].copy()
    eligible["rank1_win_pct_num_v1"] = pd.to_numeric(eligible["rank1_win_pct"], errors="coerce")
    eligible = eligible.dropna(subset=["rank1_win_pct_num_v1"])

    monotonic_desc = False
    rank1_spread = None
    best_bucket = "NA"
    worst_bucket = "NA"
    if not eligible.empty:
        ordered = eligible.set_index("pressure_score_bucket_v1").loc[[b for b in BUCKET_ORDER if b in set(eligible["pressure_score_bucket_v1"])]].reset_index()
        values = ordered["rank1_win_pct_num_v1"].tolist()
        monotonic_desc = all(values[i] >= values[i + 1] for i in range(len(values) - 1)) if len(values) >= 2 else False
        rank1_spread = round(max(values) - min(values), 2) if values else None
        best_row = ordered.sort_values(["rank1_win_pct_num_v1", "races"], ascending=[False, False]).iloc[0]
        worst_row = ordered.sort_values(["rank1_win_pct_num_v1", "races"], ascending=[True, False]).iloc[0]
        best_bucket = clean_text(best_row["pressure_score_bucket_label_v1"])
        worst_bucket = clean_text(worst_row["pressure_score_bucket_label_v1"])

    natural_separation = monotonic_desc and rank1_spread is not None and rank1_spread >= 3.0 and len(eligible) >= 3
    recalibration_signal = "YES" if natural_separation else "NO"

    summary_rows = [
        {"metric": "rows", "value": int(len(merged))},
        {"metric": "races", "value": int(race_df.shape[0])},
        {"metric": "rank1_rows", "value": int(env_race.shape[0])},
        {"metric": "score_bucket_count", "value": len(BUCKET_ORDER)},
        {"metric": "eligible_buckets_ge_300", "value": int(len(eligible))},
        {"metric": "best_bucket_v1", "value": best_bucket},
        {"metric": "worst_bucket_v1", "value": worst_bucket},
        {"metric": "rank1_win_pct_spread_v1", "value": format_metric(rank1_spread)},
        {"metric": "monotonic_descending_rank1_win_pct_v1", "value": "YES" if monotonic_desc else "NO"},
        {"metric": "natural_separation_exists_v1", "value": "YES" if natural_separation else "NO"},
        {"metric": "v2_recalibration_candidate_v1", "value": recalibration_signal},
        {"metric": "min_bucket_races_for_signal_v1", "value": MIN_BUCKET_RACES_FOR_SIGNAL},
        {"metric": "output_main", "value": str(OUTPUT_MAIN)},
        {"metric": "output_summary", "value": str(OUTPUT_SUMMARY)},
    ]
    pd.DataFrame(summary_rows).to_csv(OUTPUT_SUMMARY, index=False)

    print("[PACE_PRESSURE_THRESHOLD_AUDIT_V1] COMPLETE")
    print(f"races={int(race_df.shape[0])}")
    print(f"eligible_buckets_ge_300={int(len(eligible))}")
    print(f"best_bucket={best_bucket}")
    print(f"worst_bucket={worst_bucket}")
    print(f"rank1_win_pct_spread={format_metric(rank1_spread)}")
    print(f"monotonic_descending={'YES' if monotonic_desc else 'NO'}")
    print(f"natural_separation={'YES' if natural_separation else 'NO'}")
    print(f"wrote={OUTPUT_MAIN}")
    print(f"wrote={OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
