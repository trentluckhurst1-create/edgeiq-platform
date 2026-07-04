from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = DATA / "edgeiq_environment_score_replay_v1.csv"
OUTPUT_MAIN = DATA / "edgeiq_trust_field_engine_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_trust_field_engine_v1_summary.csv"
OUTPUT_BY_BAND = DATA / "edgeiq_trust_field_engine_v1_by_band.csv"
OUTPUT_MATRIX = DATA / "edgeiq_trust_field_engine_v1_matrix.csv"
OUTPUT_VERDICT = DATA / "edgeiq_trust_field_engine_v1_verdict.csv"

ENVIRONMENT_FULL_V1_LIFT_REFERENCE = 10.51

TRUST_POINTS = {
    "ELITE": 30,
    "STRONG": 20,
    "STANDARD": 5,
    "CHAOTIC": -10,
    "UNKNOWN": 0,
}

FIELD_POINTS = {
    "FIELD_LE_7": 25,
    "FIELD_8_10": 10,
    "FIELD_11_13": -5,
    "FIELD_14_PLUS": -15,
    "UNKNOWN": 0,
}

BAND_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]
COMBINED_ORDER = ["WEAK_POOR_NEGATIVE", "NEUTRAL_ONLY", "STRONG_POSITIVE_ELITE"]
FIELD_BUCKET_ORDER = ["FIELD_LE_7", "FIELD_8_10", "FIELD_11_13", "FIELD_14_PLUS", "UNKNOWN"]
TRUST_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC", "UNKNOWN"]


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
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalise_race_no(value: object) -> str:
    text = clean_text(value)
    match = re.search(r"(\d+)", text)
    return str(int(match.group(1))) if match else ""


def normalise_horse_key(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def normalise_trust_profile(value: object) -> str:
    text = clean_text(value).upper()
    if text in TRUST_POINTS:
        return text
    return "UNKNOWN"


def derive_field_bucket(field_size_value: object, existing_bucket: object) -> str:
    existing = clean_text(existing_bucket).upper()
    if existing in FIELD_BUCKET_ORDER:
        return existing
    number = parse_float(field_size_value)
    if number is None:
        return "UNKNOWN"
    if number <= 7:
        return "FIELD_LE_7"
    if number <= 10:
        return "FIELD_8_10"
    if number <= 13:
        return "FIELD_11_13"
    return "FIELD_14_PLUS"


def derive_band(score: float) -> str:
    if score <= -15:
        return "POOR"
    if score <= 4:
        return "NEGATIVE"
    if score <= 24:
        return "NEUTRAL"
    if score <= 44:
        return "POSITIVE"
    return "ELITE"


def derive_reason(trust_profile: str, field_bucket: str) -> str:
    trust_points = TRUST_POINTS.get(trust_profile, 0)
    field_points = FIELD_POINTS.get(field_bucket, 0)
    trust_reason = f"TRUST_{trust_profile}:{trust_points:+d}"
    field_reason = f"{field_bucket}:{field_points:+d}"
    return f"{trust_reason}; {field_reason}"


def derive_win(row: pd.Series) -> int:
    rank1_won = parse_float(row.get("rank1_won"))
    if rank1_won is not None:
        return int(rank1_won > 0)
    env_win = parse_float(row.get("environment_win_v1"))
    if env_win is not None:
        return int(env_win > 0)
    return 0


def summarize_group(df: pd.DataFrame, group_name: str, mask: pd.Series) -> dict[str, object]:
    group = df[mask].copy()
    runners = int(len(group))
    wins = int(group["trust_field_win_v1"].sum()) if runners else 0
    win_pct = round((wins / runners) * 100, 2) if runners else None
    avg_score = round(group["trust_field_score_v1"].mean(), 4) if runners else None
    avg_field_size = round(group["field_size_num_v1"].mean(), 4) if runners else None
    return {
        "group_type_v1": "COMBINED" if group_name in COMBINED_ORDER else "BAND",
        "trust_field_band_v1": group_name,
        "runners": runners,
        "wins": wins,
        "win_pct": "NA" if win_pct is None else win_pct,
        "avg_trust_field_score_v1": "NA" if avg_score is None else avg_score,
        "avg_field_size": "NA" if avg_field_size is None else avg_field_size,
    }


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False)

    df["meeting_date"] = df["meeting_date"].map(normalise_date)
    df["track"] = df["track"].map(normalise_track)
    df["race_no"] = df["race_no"].map(normalise_race_no)
    df["rank1_horse_key"] = [
        normalise_horse_key(key if clean_text(key) else horse)
        for key, horse in zip(df.get("rank1_horse_key", ""), df.get("rank1_horse", ""))
    ]
    df["trust_profile_tf_v1"] = df["trust_profile_v1"].map(normalise_trust_profile)
    df["field_size_num_v1"] = df["field_size"].map(parse_float)
    df["field_size_bucket_tf_v1"] = [
        derive_field_bucket(field_size, existing)
        for field_size, existing in zip(df.get("field_size", ""), df.get("field_size_bucket_v1", ""))
    ]
    df["trust_points_v1"] = df["trust_profile_tf_v1"].map(lambda x: TRUST_POINTS.get(x, 0))
    df["field_points_v1"] = df["field_size_bucket_tf_v1"].map(lambda x: FIELD_POINTS.get(x, 0))
    df["trust_field_score_v1"] = df["trust_points_v1"] + df["field_points_v1"]
    df["trust_field_band_v1"] = df["trust_field_score_v1"].map(derive_band)
    df["trust_field_reason_v1"] = [
        derive_reason(trust_profile, field_bucket)
        for trust_profile, field_bucket in zip(df["trust_profile_tf_v1"], df["field_size_bucket_tf_v1"])
    ]
    df["trust_field_win_v1"] = df.apply(derive_win, axis=1)

    output_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "rank1_horse",
        "rank1_horse_key",
        "rank1_won",
        "environment_win_v1",
        "trust_profile_v1",
        "trust_profile_tf_v1",
        "field_size",
        "field_size_bucket_v1",
        "field_size_bucket_tf_v1",
        "score_share_band",
        "rank1_score_share_of_race",
        "rank1_dominance_band_v1",
        "rank1_dominance_score_v1",
        "environment_score_v1",
        "environment_band_v1",
        "trust_points_v1",
        "field_points_v1",
        "trust_field_score_v1",
        "trust_field_band_v1",
        "trust_field_reason_v1",
        "trust_field_win_v1",
    ]
    df[output_columns].to_csv(OUTPUT_MAIN, index=False)

    band_rows = []
    for band in BAND_ORDER:
        band_rows.append(summarize_group(df, band, df["trust_field_band_v1"] == band))

    band_rows.append(summarize_group(df, "WEAK_POOR_NEGATIVE", df["trust_field_band_v1"].isin(["POOR", "NEGATIVE"])))
    band_rows.append(summarize_group(df, "NEUTRAL_ONLY", df["trust_field_band_v1"] == "NEUTRAL"))
    band_rows.append(summarize_group(df, "STRONG_POSITIVE_ELITE", df["trust_field_band_v1"].isin(["POSITIVE", "ELITE"])))

    by_band_df = pd.DataFrame(band_rows)
    by_band_df["sort_order_v1"] = by_band_df["trust_field_band_v1"].map({name: idx for idx, name in enumerate(BAND_ORDER + COMBINED_ORDER)})
    by_band_df = by_band_df.sort_values(["sort_order_v1", "group_type_v1"]).drop(columns=["sort_order_v1"])
    by_band_df.to_csv(OUTPUT_BY_BAND, index=False)

    matrix_rows: list[dict[str, object]] = []
    for trust_profile in TRUST_ORDER:
        trust_group = df[df["trust_profile_tf_v1"] == trust_profile]
        for field_bucket in FIELD_BUCKET_ORDER:
            group = trust_group[trust_group["field_size_bucket_tf_v1"] == field_bucket]
            runners = int(len(group))
            wins = int(group["trust_field_win_v1"].sum()) if runners else 0
            win_pct = round((wins / runners) * 100, 2) if runners else None
            avg_score = round(group["trust_field_score_v1"].mean(), 4) if runners else None
            matrix_rows.append({
                "trust_profile_v1": trust_profile,
                "field_size_bucket_tf_v1": field_bucket,
                "runners": runners,
                "wins": wins,
                "win_pct": "NA" if win_pct is None else win_pct,
                "avg_trust_field_score_v1": "NA" if avg_score is None else avg_score,
            })

    matrix_df = pd.DataFrame(matrix_rows)
    matrix_df.to_csv(OUTPUT_MATRIX, index=False)

    rows = int(len(df))
    wins = int(df["trust_field_win_v1"].sum())
    overall_win_pct = round((wins / rows) * 100, 2) if rows else 0.0

    weak_group = by_band_df[by_band_df["trust_field_band_v1"] == "WEAK_POOR_NEGATIVE"].iloc[0]
    neutral_group = by_band_df[by_band_df["trust_field_band_v1"] == "NEUTRAL_ONLY"].iloc[0]
    strong_group = by_band_df[by_band_df["trust_field_band_v1"] == "STRONG_POSITIVE_ELITE"].iloc[0]

    weak_runners = int(weak_group["runners"])
    weak_win_pct = float(weak_group["win_pct"]) if clean_text(weak_group["win_pct"]) != "NA" else 0.0
    neutral_runners = int(neutral_group["runners"])
    neutral_win_pct = float(neutral_group["win_pct"]) if clean_text(neutral_group["win_pct"]) != "NA" else 0.0
    strong_runners = int(strong_group["runners"])
    strong_win_pct = float(strong_group["win_pct"]) if clean_text(strong_group["win_pct"]) != "NA" else 0.0

    strong_vs_weak_lift = round(strong_win_pct - weak_win_pct, 2)
    beats_environment = strong_vs_weak_lift >= ENVIRONMENT_FULL_V1_LIFT_REFERENCE

    if strong_vs_weak_lift >= ENVIRONMENT_FULL_V1_LIFT_REFERENCE:
        verdict = "TRUST_FIELD_BEATS_ENVIRONMENT_V1"
    elif strong_vs_weak_lift >= 8:
        verdict = "TRUST_FIELD_APPROX_ENVIRONMENT_V1"
    elif strong_vs_weak_lift >= 5:
        verdict = "TRUST_FIELD_USEFUL_BUT_WEAKER"
    else:
        verdict = "TRUST_FIELD_NOT_PROVEN"

    summary_rows = [
        {"metric": "rows", "value": rows},
        {"metric": "wins", "value": wins},
        {"metric": "overall_win_pct", "value": overall_win_pct},
        {"metric": "weak_runners", "value": weak_runners},
        {"metric": "weak_win_pct", "value": weak_win_pct},
        {"metric": "neutral_runners", "value": neutral_runners},
        {"metric": "neutral_win_pct", "value": neutral_win_pct},
        {"metric": "strong_runners", "value": strong_runners},
        {"metric": "strong_win_pct", "value": strong_win_pct},
        {"metric": "strong_vs_weak_lift_pts", "value": strong_vs_weak_lift},
        {"metric": "environment_full_v1_lift_reference", "value": ENVIRONMENT_FULL_V1_LIFT_REFERENCE},
        {"metric": "beats_environment_full_v1", "value": "YES" if beats_environment else "NO"},
        {"metric": "verdict", "value": verdict},
        {"metric": "output_main", "value": str(OUTPUT_MAIN)},
        {"metric": "output_by_band", "value": str(OUTPUT_BY_BAND)},
        {"metric": "output_matrix", "value": str(OUTPUT_MATRIX)},
        {"metric": "output_verdict", "value": str(OUTPUT_VERDICT)},
    ]
    pd.DataFrame(summary_rows).to_csv(OUTPUT_SUMMARY, index=False)

    verdict_rows = [
        {"metric": "strong_vs_weak_lift_pts", "value": strong_vs_weak_lift},
        {"metric": "environment_full_v1_lift_reference", "value": ENVIRONMENT_FULL_V1_LIFT_REFERENCE},
        {"metric": "beats_environment_full_v1", "value": "YES" if beats_environment else "NO"},
        {"metric": "verdict", "value": verdict},
    ]
    pd.DataFrame(verdict_rows).to_csv(OUTPUT_VERDICT, index=False)

    print("[TRUST_FIELD_ENGINE_V1] COMPLETE")
    print(f"rows={rows}")
    print(f"overall_win_pct={overall_win_pct}")
    print(f"weak_win_pct={weak_win_pct}")
    print(f"neutral_win_pct={neutral_win_pct}")
    print(f"strong_win_pct={strong_win_pct}")
    print(f"strong_vs_weak_lift_pts={strong_vs_weak_lift}")
    print(f"beats_environment_full_v1={'YES' if beats_environment else 'NO'}")
    print(f"verdict={verdict}")
    print(f"wrote={OUTPUT_MAIN}")
    print(f"wrote={OUTPUT_SUMMARY}")
    print(f"wrote={OUTPUT_BY_BAND}")
    print(f"wrote={OUTPUT_MATRIX}")
    print(f"wrote={OUTPUT_VERDICT}")


if __name__ == "__main__":
    main()
