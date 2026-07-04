from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRIMARY = DATA / "edgeiq_live_runner_dna_v6_2.csv"
FALLBACK = DATA / "edgeiq_runner_dna_ui_feed_v1.csv"

OUT = DATA / "edgeiq_runner_dna_drawer_feed_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_drawer_feed_v1_summary.csv"
JSON_OUT = DATA / "edgeiq_runner_dna_drawer_feed_v1_summary.json"

KEEP = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "runner_key",
    "runner_dna_v6_1_score",
    "runner_dna_v6_1_band",
    "runner_dna_v6_1_rank_in_race",
    "strongest_factor_v6_1",
    "strongest_factor_score_v6_1",
    "weakest_factor_v6_1",
    "weakest_factor_score_v6_1",
    "form_score",
    "rating_score",
    "sectional_score",
    "profile_score",
    "distance_fit_score",
    "distance_fit_band",
    "condition_fit_score",
    "condition_fit_band",
    "class_fit_score",
    "class_fit_band",
    "class_movement",
    "runner_dna_v6_1_narrative",
    "runner_dna_v6_1_customer_summary",
]


def read_source() -> tuple[pd.DataFrame, Path]:
    if PRIMARY.exists():
        return pd.read_csv(PRIMARY, low_memory=False), PRIMARY
    if FALLBACK.exists():
        return pd.read_csv(FALLBACK, low_memory=False), FALLBACK
    raise SystemExit(f"Missing DNA drawer source. Checked: {PRIMARY.name}, {FALLBACK.name}")


def normalize_key(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().upper()
    return "".join(char for char in text if char.isalnum())


def build_runner_key(frame: pd.DataFrame) -> pd.Series:
    race_date = frame.get("race_date", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    track = frame.get("track", pd.Series("", index=frame.index)).map(normalize_key)
    race_no = frame.get("race_no", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    horse_key = frame.get("horse_key", pd.Series("", index=frame.index)).map(normalize_key)
    return race_date + "|" + track + "|" + race_no + "|" + horse_key


def ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    missing = [column for column in columns if column not in frame.columns]
    if not missing:
        return frame
    return frame.assign(**{column: "" for column in missing})


def main() -> None:
    df, source_path = read_source()
    df = df.copy()

    if "runner_key" not in df.columns:
        df = df.assign(runner_key=build_runner_key(df))
    else:
        runner_key = df["runner_key"].fillna("").astype(str).str.strip()
        rebuilt_runner_key = build_runner_key(df)
        df["runner_key"] = runner_key.where(runner_key != "", rebuilt_runner_key)

    df = ensure_columns(df, KEEP)
    out = df.loc[:, KEEP].copy()
    out.to_csv(OUT, index=False)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_DNA_DRAWER_FEED_V1_BUILT"},
        {"metric": "rows", "value": len(out)},
        {"metric": "columns", "value": len(out.columns)},
        {"metric": "source", "value": source_path.name},
        {"metric": "output", "value": str(OUT)},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY, index=False)

    JSON_OUT.write_text(
        json.dumps({row["metric"]: row["value"] for row in summary_rows}, indent=2),
        encoding="utf-8",
    )

    print("[RUNNER_DNA_DRAWER_FEED_V1] COMPLETE")
    print(summary.to_string(index=False))
    print()
    print(out.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
