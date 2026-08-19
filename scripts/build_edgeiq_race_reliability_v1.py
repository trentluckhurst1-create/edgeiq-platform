from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = DATA / "edgeiq_environment_v2_trust_field_core.csv"
OUTPUT_PATH = DATA / "edgeiq_race_reliability_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_race_reliability_v1_summary.csv"

DISPLAY_LABELS = {
    "POOR": "Race Reliability: Poor",
    "NEGATIVE": "Race Reliability: Negative",
    "NEUTRAL": "Race Reliability: Neutral",
    "POSITIVE": "Race Reliability: Positive",
    "ELITE": "Race Reliability: Elite",
    "UNKNOWN": "Race Reliability: Unknown",
}

DISPLAY_RANKS = {
    "POOR": 1,
    "NEGATIVE": 2,
    "NEUTRAL": 3,
    "POSITIVE": 4,
    "ELITE": 5,
    "UNKNOWN": 0,
}

PLAIN_ENGLISH = {
    "POOR": "This race is historically less reliable for the model.",
    "NEGATIVE": "This race has more risk and the model should be treated carefully.",
    "NEUTRAL": "This race is standard for model reliability.",
    "POSITIVE": "This race is a favourable setup for trusting the model.",
    "ELITE": "This race is historically one of the cleanest setups for the model.",
    "UNKNOWN": "Race reliability is unavailable.",
}

UI_HINTS = {
    "POOR": "High variance race",
    "NEGATIVE": "Caution race",
    "NEUTRAL": "Standard race",
    "POSITIVE": "Model-friendly race",
    "ELITE": "High-confidence race shape",
    "UNKNOWN": "Unknown reliability",
}

BAND_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE", "UNKNOWN"]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def derive_race_key(meeting_date: object, track: object, race_no: object) -> str:
    date_text = clean_text(meeting_date)
    track_text = clean_text(track)
    race_text = clean_text(race_no)
    if not date_text or not track_text or not race_text:
        return ""
    return f"{date_text}|{track_text}|R{race_text}"


def band_value(value: object) -> str:
    text = clean_text(value).upper()
    return text if text in DISPLAY_LABELS else "UNKNOWN"


def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Missing Environment V2 file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, low_memory=False)

    if "race_key" not in df.columns:
        df["race_key"] = [
            derive_race_key(meeting_date, track, race_no)
            for meeting_date, track, race_no in zip(df.get("meeting_date", ""), df.get("track", ""), df.get("race_no", ""))
        ]

    df["environment_band_v2"] = df.get("environment_band_v2", "UNKNOWN").map(band_value)
    df["race_reliability_score_v1"] = pd.to_numeric(df.get("environment_score_v2"), errors="coerce")
    df["race_reliability_band_v1"] = df["environment_band_v2"]
    df["race_reliability_reason_v1"] = df.get("environment_reason_v2", "")
    df["race_reliability_display_label_v1"] = df["race_reliability_band_v1"].map(DISPLAY_LABELS)
    df["race_reliability_display_rank_v1"] = df["race_reliability_band_v1"].map(DISPLAY_RANKS).fillna(0).astype(int)
    df["race_reliability_plain_english_v1"] = df["race_reliability_band_v1"].map(PLAIN_ENGLISH)
    df["race_reliability_ui_hint_v1"] = df["race_reliability_band_v1"].map(UI_HINTS)

    ordered_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "rank1_horse",
        "environment_horse_key_v2",
        "trust_profile_v1",
        "field_size",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "race_reliability_reason_v1",
        "race_reliability_display_label_v1",
        "race_reliability_display_rank_v1",
        "race_reliability_plain_english_v1",
        "race_reliability_ui_hint_v1",
        "environment_score_v2",
        "environment_band_v2",
        "environment_reason_v2",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
        "environment_band_comparison_v2_vs_v1",
        "environment_band_delta_v2_vs_v1",
    ]
    remaining_columns = [column for column in df.columns if column not in ordered_columns]
    output_df = df[ordered_columns + remaining_columns].copy()
    output_df.to_csv(OUTPUT_PATH, index=False)

    rows = int(len(output_df))
    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "source_file", "value": str(INPUT_PATH)},
        {"metric": "rows", "value": rows},
        {"metric": "output_file", "value": str(OUTPUT_PATH)},
    ]
    for band in BAND_ORDER:
        summary_rows.append(
            {
                "metric": f"race_reliability_{band.lower()}_rows",
                "value": int((output_df["race_reliability_band_v1"] == band).sum()),
            }
        )
    pd.DataFrame(summary_rows).to_csv(SUMMARY_PATH, index=False)

    print("[RACE_RELIABILITY_V1] COMPLETE")
    print(f"rows={rows}")
    print(f"wrote={OUTPUT_PATH}")
    print(f"wrote={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
