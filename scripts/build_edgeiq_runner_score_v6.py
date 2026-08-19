from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_SCORE_V5 = DATA / "edgeiq_runner_score_v5.csv"
PACE_ADVANTAGE = DATA / "edgeiq_pace_advantage_v1.csv"
PACE_TRUST = DATA / "edgeiq_pace_trust_v1.csv"

OUT = DATA / "edgeiq_runner_score_v6.csv"
AUDIT = DATA / "edgeiq_runner_score_v6_audit.csv"

TRUST_MULTIPLIER = {
    "HIGH_TRUST": 1.00,
    "MEDIUM_TRUST": 0.50,
    "LOW_TRUST": 0.25,
    "IGNORE": 0.00,
}

PACE_COLUMNS = [
    "pace_pressure_score_v1",
    "pace_pressure_band_v1",
    "tactical_style",
    "dna_run_style",
    "style_source_v1",
    "pace_advantage_score_v1",
    "pace_advantage_band_v1",
    "pace_advantage_reason_v1",
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def upper_text(value: object) -> str:
    return clean_text(value).upper()


def canon_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value: object) -> str:
    text = upper_text(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"\s+", " ", text).strip()


def score_band(score: float) -> str:
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 80:
        return "80_PLUS"
    if score >= 70:
        return "70_79"
    if score >= 60:
        return "60_69"
    if score >= 50:
        return "50_59"
    if score >= 40:
        return "40_49"
    return "LT_40"


def load_runner_score_v5() -> pd.DataFrame:
    if not RUNNER_SCORE_V5.exists():
        raise FileNotFoundError(f"Missing runner score v5 file: {RUNNER_SCORE_V5}")

    df = pd.read_csv(RUNNER_SCORE_V5, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["join_track"] = df["track"].map(norm_track)
    df["join_race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_horse"] = df["horse"].map(canon_horse)
    df["runner_score_v4"] = pd.to_numeric(df["runner_score_v4"], errors="coerce")
    df["runner_score_v5"] = pd.to_numeric(df["runner_score_v5"], errors="coerce")
    df["runner_rank_v4"] = pd.to_numeric(df.get("runner_rank_v4"), errors="coerce")
    df["runner_rank_v5"] = pd.to_numeric(df.get("runner_rank_v5"), errors="coerce")
    df["race_key_v6"] = df["meeting_date"].astype(str) + "|" + df["track"].astype(str) + "|R" + df["race_no"].astype(str)

    drop_cols = [col for col in PACE_COLUMNS if col in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    return df


def load_pace_advantage() -> pd.DataFrame:
    if not PACE_ADVANTAGE.exists():
        raise FileNotFoundError(f"Missing pace advantage file: {PACE_ADVANTAGE}")

    df = pd.read_csv(PACE_ADVANTAGE, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["join_track"] = df["track"].map(norm_track)
    df["join_race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_horse"] = df["horse"].map(canon_horse)
    df["pace_advantage_score_v1"] = pd.to_numeric(df["pace_advantage_score_v1"], errors="coerce").fillna(0.0)
    return df


def load_pace_trust() -> pd.DataFrame:
    if not PACE_TRUST.exists():
        raise FileNotFoundError(f"Missing pace trust file: {PACE_TRUST}")

    df = pd.read_csv(PACE_TRUST, low_memory=False)
    df["race_key"] = df["race_key"].astype(str).str.strip()
    df["pace_trust_band_v1"] = df["pace_trust_band_v1"].fillna("IGNORE").astype(str).str.upper().str.strip()
    df["pace_trust_score_v1"] = pd.to_numeric(df["pace_trust_score_v1"], errors="coerce").fillna(0)
    df["trust_multiplier_v1"] = df["pace_trust_band_v1"].map(TRUST_MULTIPLIER).fillna(0.0)
    return df


def main() -> None:
    base = load_runner_score_v5()
    pace = load_pace_advantage()
    trust = load_pace_trust()

    merged = base.merge(
        pace[[
            "meeting_date",
            "join_track",
            "join_race_no",
            "join_horse",
            "pace_pressure_score_v1",
            "pace_pressure_band_v1",
            "tactical_style",
            "dna_run_style",
            "style_source_v1",
            "pace_advantage_score_v1",
            "pace_advantage_band_v1",
            "pace_advantage_reason_v1",
        ]],
        on=["meeting_date", "join_track", "join_race_no", "join_horse"],
        how="inner",
    )
    if merged.empty:
        raise RuntimeError("No current runners matched between runner_score_v5 and pace_advantage_v1.")

    merged = merged.merge(
        trust[[
            "race_key",
            "field_size",
            "leaders_count",
            "on_pace_count",
            "midfield_count",
            "backmarker_count",
            "unknown_count",
            "pace_trust_score_v1",
            "pace_trust_band_v1",
            "pace_trust_reason_v1",
            "trust_multiplier_v1",
        ]],
        left_on="race_key_v6",
        right_on="race_key",
        how="left",
    )

    merged["pace_trust_band_v1"] = merged["pace_trust_band_v1"].fillna("IGNORE")
    merged["trust_multiplier_v1"] = pd.to_numeric(merged["trust_multiplier_v1"], errors="coerce").fillna(0.0)
    merged["pace_trust_score_v1"] = pd.to_numeric(merged["pace_trust_score_v1"], errors="coerce").fillna(0.0)
    merged["pace_adjustment_trusted_v1"] = (
        merged["pace_advantage_score_v1"].fillna(0.0) * merged["trust_multiplier_v1"]
    ).round(3)

    merged["runner_score_v6"] = np.clip(
        merged["runner_score_v4"].fillna(0.0) + merged["pace_adjustment_trusted_v1"].fillna(0.0),
        0,
        100,
    ).round(3)
    merged["v6_minus_v4"] = (merged["runner_score_v6"] - merged["runner_score_v4"]).round(3)
    merged["v6_minus_v5"] = (merged["runner_score_v6"] - merged["runner_score_v5"]).round(3)

    merged = merged.sort_values(
        ["meeting_date", "track", "race_no", "runner_score_v6", "pace_adjustment_trusted_v1", "runner_score_v4", "horse"],
        ascending=[True, True, True, False, False, False, True],
    ).reset_index(drop=True)

    merged["runner_order_v6"] = merged.groupby("race_key_v6").cumcount() + 1
    merged["runner_rank_v6"] = (
        merged.groupby("race_key_v6")["runner_score_v6"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    merged["runner_score_band_v6"] = merged["runner_score_v6"].apply(score_band)
    merged["runner_score_reason_v6"] = (
        "v4=" + merged["runner_score_v4"].round(3).astype(str)
        + " | raw_pace=" + merged["pace_advantage_score_v1"].round(3).astype(str)
        + " | trust=" + merged["pace_trust_band_v1"].astype(str)
        + " | multiplier=" + merged["trust_multiplier_v1"].round(2).astype(str)
        + " | trusted_pace=" + merged["pace_adjustment_trusted_v1"].round(3).astype(str)
    )

    output_columns = list(base.columns)
    extra_columns = [
        "pace_pressure_score_v1",
        "pace_pressure_band_v1",
        "tactical_style",
        "dna_run_style",
        "style_source_v1",
        "pace_advantage_score_v1",
        "pace_advantage_band_v1",
        "pace_advantage_reason_v1",
        "field_size",
        "leaders_count",
        "on_pace_count",
        "midfield_count",
        "backmarker_count",
        "unknown_count",
        "pace_trust_score_v1",
        "pace_trust_band_v1",
        "pace_trust_reason_v1",
        "trust_multiplier_v1",
        "pace_adjustment_trusted_v1",
        "runner_score_v6",
        "v6_minus_v4",
        "v6_minus_v5",
        "runner_score_band_v6",
        "runner_order_v6",
        "runner_rank_v6",
        "runner_score_reason_v6",
    ]
    keep = [col for col in output_columns + extra_columns if col in merged.columns]
    out = merged[keep].copy()
    out.to_csv(OUT, index=False)

    top_scores = out.groupby("race_key_v6")["runner_score_v6"].max().reset_index(name="top_score")
    tied_top = out.merge(top_scores, on="race_key_v6", how="left")
    tied_top_races = tied_top[tied_top["runner_score_v6"].eq(tied_top["top_score"])].groupby("race_key_v6").size()

    audit_rows = [
        {"metric": "runner_score_v5_rows", "value": int(len(base))},
        {"metric": "pace_advantage_rows", "value": int(len(pace))},
        {"metric": "pace_trust_races", "value": int(len(trust))},
        {"metric": "runner_score_v6_rows", "value": int(len(out))},
        {"metric": "runner_score_v6_races", "value": int(out["race_key_v6"].nunique())},
        {"metric": "avg_runner_score_v4", "value": round(float(out["runner_score_v4"].mean()), 3)},
        {"metric": "avg_runner_score_v5", "value": round(float(out["runner_score_v5"].mean()), 3)},
        {"metric": "avg_runner_score_v6", "value": round(float(out["runner_score_v6"].mean()), 3)},
        {"metric": "avg_raw_pace_adjustment", "value": round(float(out["pace_advantage_score_v1"].mean()), 3)},
        {"metric": "avg_trusted_pace_adjustment", "value": round(float(out["pace_adjustment_trusted_v1"].mean()), 3)},
        {"metric": "positive_trusted_adjustment_rows", "value": int(out["pace_adjustment_trusted_v1"].gt(0).sum())},
        {"metric": "negative_trusted_adjustment_rows", "value": int(out["pace_adjustment_trusted_v1"].lt(0).sum())},
        {"metric": "neutral_trusted_adjustment_rows", "value": int(out["pace_adjustment_trusted_v1"].eq(0).sum())},
        {"metric": "clipped_zero_rows", "value": int(out["runner_score_v6"].le(0).sum())},
        {"metric": "clipped_hundred_rows", "value": int(out["runner_score_v6"].ge(100).sum())},
        {"metric": "races_with_tied_top_score_v6", "value": int((tied_top_races > 1).sum())},
    ]

    for band in ["HIGH_TRUST", "MEDIUM_TRUST", "LOW_TRUST", "IGNORE"]:
        audit_rows.append({"metric": f"trust_band::{band}", "value": int(out["pace_trust_band_v1"].eq(band).sum())})

    pd.DataFrame(audit_rows).to_csv(AUDIT, index=False)

    print("[EDGEIQ_RUNNER_SCORE_V6] COMPLETE")
    print(f"runner_score_v6_rows={len(out)}")
    print(f"runner_score_v6_races={out['race_key_v6'].nunique()}")
    print(f"avg_trusted_pace_adjustment={round(float(out['pace_adjustment_trusted_v1'].mean()), 3)}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")


if __name__ == "__main__":
    main()
