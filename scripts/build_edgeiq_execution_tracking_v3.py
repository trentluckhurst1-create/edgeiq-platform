from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import unicodedata

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

LIVE_PATH = DATA_DIR / "edgeiq_execution_engine_v3_live.csv"
CANDIDATES_PATH = DATA_DIR / "edgeiq_execution_engine_v3_live_candidates.csv"
TRACKING_PATH = DATA_DIR / "edgeiq_execution_tracking_v3.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_execution_tracking_v3_summary.csv"

TRACKING_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "execution_action_v3",
    "trust_profile_v1",
    "runner_rank_v6",
    "runner_score_v6",
    "market_price_v1",
    "edge_pct_v1",
    "execution_reason_v3",
    "captured_timestamp",
    "result_status",
    "settlement_source",
    "finish_position",
    "won",
    "placed",
    "profit_1u_win",
]

ACTION_ORDER = {
    "ELITE_EXECUTE": 1,
    "EXECUTE": 2,
    "STRONG_WATCH": 3,
    "WATCH": 4,
    "NO_BET": 5,
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_text(value: object) -> str:
    text = clean_text(value)
    if text == "":
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = ""
    return df[columns].copy()


def build_runner_key(df: pd.DataFrame) -> pd.Series:
    race_no = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int).astype(str)
    return (
        df["meeting_date"].fillna("").astype(str).str[:10]
        + "|"
        + df["track"].map(normalize_text)
        + "|"
        + race_no
        + "|"
        + df["horse"].map(normalize_text)
    )


def build_unique_key(df: pd.DataFrame) -> pd.Series:
    race_no = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int).astype(str)
    return (
        df["meeting_date"].fillna("").astype(str).str[:10]
        + "|"
        + df["track"].map(normalize_text)
        + "|"
        + race_no
        + "|"
        + df["horse"].map(normalize_text)
        + "|"
        + df["execution_action_v3"].fillna("").astype(str).str.strip().str.upper()
    )


def action_priority(action: str) -> int:
    return ACTION_ORDER.get(str(action).strip().upper(), 99)


def action_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["execution_action_v3", "runners"])
    return (
        df.groupby("execution_action_v3", dropna=False)
        .size()
        .rename("runners")
        .reset_index()
        .sort_values("execution_action_v3", key=lambda series: series.map(action_priority), kind="mergesort")
        .reset_index(drop=True)
    )


def main() -> None:
    captured_timestamp = datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="seconds")

    live_df = pd.read_csv(LIVE_PATH, dtype=str, keep_default_na=False)
    candidates_df = pd.read_csv(CANDIDATES_PATH, dtype=str, keep_default_na=False)

    live_df = live_df.copy()
    candidates_df = candidates_df.copy()

    live_df["_runner_key_v3"] = build_runner_key(live_df)
    candidates_df["_runner_key_v3"] = build_runner_key(candidates_df)

    live_lookup_columns = [
        "_runner_key_v3",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "execution_action_v3",
        "trust_profile_v1",
        "runner_rank_v6",
        "runner_score_v6",
        "market_price_v1",
        "edge_pct_v1",
        "execution_reason_v3",
    ]
    live_lookup = live_df[live_lookup_columns].drop_duplicates("_runner_key_v3", keep="first")

    candidates_df = candidates_df.merge(live_lookup, on="_runner_key_v3", how="left", suffixes=("", "_live"))
    for column in [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "execution_action_v3",
        "trust_profile_v1",
        "runner_rank_v6",
        "runner_score_v6",
        "market_price_v1",
        "edge_pct_v1",
        "execution_reason_v3",
    ]:
        live_column = f"{column}_live"
        if live_column in candidates_df.columns:
            candidates_df[column] = candidates_df[column].where(candidates_df[column].astype(str).str.strip().ne(""), candidates_df[live_column])

    current_candidates = int(len(candidates_df))

    if current_candidates == 0:
        candidate_tracking_df = pd.DataFrame(columns=TRACKING_COLUMNS)
    else:
        candidate_tracking_df = candidates_df.copy()
        candidate_tracking_df["captured_timestamp"] = captured_timestamp
        candidate_tracking_df["result_status"] = "PENDING"
        candidate_tracking_df["settlement_source"] = ""
        candidate_tracking_df["finish_position"] = ""
        candidate_tracking_df["won"] = ""
        candidate_tracking_df["placed"] = ""
        candidate_tracking_df["profit_1u_win"] = ""
        candidate_tracking_df = ensure_columns(candidate_tracking_df, TRACKING_COLUMNS)
        candidate_tracking_df["_unique_key_v3"] = build_unique_key(candidate_tracking_df)
        candidate_tracking_df = candidate_tracking_df.drop_duplicates("_unique_key_v3", keep="first")

    if TRACKING_PATH.exists():
        history_df = pd.read_csv(TRACKING_PATH, dtype=str, keep_default_na=False)
        history_df = ensure_columns(history_df, TRACKING_COLUMNS)
        history_df["_unique_key_v3"] = build_unique_key(history_df)
        existing_keys = set(history_df["_unique_key_v3"].tolist())
    else:
        history_df = pd.DataFrame(columns=TRACKING_COLUMNS)
        existing_keys = set()

    new_rows_df = candidate_tracking_df[~candidate_tracking_df["_unique_key_v3"].isin(existing_keys)].copy()

    history_core_df = history_df.drop(columns=["_unique_key_v3"], errors="ignore")
    new_rows_core_df = new_rows_df.drop(columns=["_unique_key_v3"], errors="ignore")

    combined_df = pd.concat([history_core_df, new_rows_core_df], ignore_index=True)
    combined_df = ensure_columns(combined_df, TRACKING_COLUMNS)
    combined_df.to_csv(TRACKING_PATH, index=False)

    pending_rows = int((combined_df["result_status"].astype(str).str.strip().str.upper() == "PENDING").sum())
    combined_action_counts = action_counts(combined_df)

    summary_rows = [
        {"metric": "current_candidates", "value": current_candidates},
        {"metric": "new_rows_appended", "value": int(len(new_rows_core_df))},
        {"metric": "history_total_rows", "value": int(len(combined_df))},
        {"metric": "pending_rows", "value": pending_rows},
    ]
    for _, row in combined_action_counts.iterrows():
        action_name = clean_text(row["execution_action_v3"]).lower()
        summary_rows.append({"metric": f"{action_name}_count", "value": int(row["runners"])})

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    current_action_counts = action_counts(candidate_tracking_df.drop(columns=["_unique_key_v3"], errors="ignore"))

    print("[EDGEIQ_EXECUTION_TRACKING_V3] COMPLETE")
    print(f"captured_timestamp={captured_timestamp}")
    print(f"current_candidates={current_candidates}")
    print(f"new_rows_appended={len(new_rows_core_df)}")
    print(f"history_total_rows={len(combined_df)}")
    print(f"pending_rows={pending_rows}")
    print("\nCounts By execution_action_v3")
    if current_action_counts.empty:
        print("No current V3 candidates.")
    else:
        print(current_action_counts.to_string(index=False))
    print(f"\ntracking_out={TRACKING_PATH}")
    print(f"summary_out={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
