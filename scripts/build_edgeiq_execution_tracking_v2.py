from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import unicodedata

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

CANDIDATES_PATH = DATA_DIR / "edgeiq_execution_engine_v2_live_candidates.csv"
OVERLAY_TRACKING_PATH = DATA_DIR / "edgeiq_overlay_tracking_v1.csv"
TRACKING_PATH = DATA_DIR / "edgeiq_execution_tracking_v2.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_execution_tracking_v2_summary.csv"

TRACKING_COLUMNS = [
    "signal_date",
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "execution_action_v2",
    "runner_rank_v6",
    "runner_score_v6",
    "trust_profile_v1",
    "trust_band_v1",
    "trust_index_v1",
    "empirical_fair_price_v1",
    "market_price_v1",
    "edge_pct_v1",
    "edge_band_v1",
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

SETTLEMENT_FIELDS = [
    "result_status",
    "settlement_source",
    "finish_position",
    "won",
    "placed",
    "profit_1u_win",
]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    if text == "" or text == "NAN":
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalize_number_for_key(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text == "" or text.upper() == "NAN":
        return ""
    try:
        return f"{float(text):.6f}"
    except Exception:
        return text.upper()


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = ""
    return df[columns].copy()


def build_tracking_key(df: pd.DataFrame) -> pd.Series:
    return (
        df["signal_date"].fillna("").astype(str).str.strip()
        + "|"
        + df["meeting_date"].fillna("").astype(str).str.strip()
        + "|"
        + df["track"].apply(normalize_text)
        + "|"
        + df["race_no"].fillna("").astype(str).str.strip()
        + "|"
        + df["horse"].apply(normalize_text)
        + "|"
        + df["execution_action_v2"].fillna("").astype(str).str.strip().str.upper()
        + "|"
        + df["empirical_fair_price_v1"].apply(normalize_number_for_key)
        + "|"
        + df["market_price_v1"].apply(normalize_number_for_key)
    )


def build_overlay_match_key(df: pd.DataFrame) -> pd.Series:
    return (
        df["signal_date"].fillna("").astype(str).str.strip()
        + "|"
        + df["meeting_date"].fillna("").astype(str).str.strip()
        + "|"
        + df["track"].apply(normalize_text)
        + "|"
        + df["race_no"].fillna("").astype(str).str.strip()
        + "|"
        + df["horse"].apply(normalize_text)
        + "|"
        + df["empirical_fair_price_v1"].apply(normalize_number_for_key)
        + "|"
        + df["market_price_v1"].apply(normalize_number_for_key)
    )


def action_priority(action: str) -> int:
    return ACTION_ORDER.get(str(action).strip().upper(), 99)


def action_counts(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=["execution_action_v2", "runners"])
    counts = (
        df.groupby("execution_action_v2", dropna=False)
        .size()
        .rename("runners")
        .reset_index()
        .sort_values("execution_action_v2", key=lambda series: series.map(action_priority), kind="mergesort")
        .reset_index(drop=True)
    )
    return counts


def main() -> None:
    signal_date = datetime.now(ZoneInfo("Australia/Sydney")).date().isoformat()

    candidates_df = pd.read_csv(CANDIDATES_PATH, dtype=str, keep_default_na=False)
    candidates_df = candidates_df.copy()
    current_candidates = int(len(candidates_df))

    if current_candidates == 0:
        candidate_tracking_df = pd.DataFrame(columns=TRACKING_COLUMNS)
    else:
        candidate_tracking_df = candidates_df.copy()
        candidate_tracking_df["signal_date"] = signal_date
        candidate_tracking_df["result_status"] = "PENDING"
        candidate_tracking_df["settlement_source"] = ""
        candidate_tracking_df["finish_position"] = ""
        candidate_tracking_df["won"] = ""
        candidate_tracking_df["placed"] = ""
        candidate_tracking_df["profit_1u_win"] = ""
        candidate_tracking_df = ensure_columns(candidate_tracking_df, TRACKING_COLUMNS)

    if TRACKING_PATH.exists():
        history_df = pd.read_csv(TRACKING_PATH, dtype=str, keep_default_na=False)
        history_df = ensure_columns(history_df, TRACKING_COLUMNS)
    else:
        history_df = pd.DataFrame(columns=TRACKING_COLUMNS)

    overlay_df = pd.read_csv(OVERLAY_TRACKING_PATH, dtype=str, keep_default_na=False)
    overlay_columns = [
        "signal_date",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "empirical_fair_price_v1",
        "market_price_v1",
        "result_status",
        "settlement_source",
        "finish_position",
        "won",
        "placed",
        "profit_1u_win",
    ]
    overlay_df = ensure_columns(overlay_df, overlay_columns)
    overlay_df["_overlay_match_key_v2"] = build_overlay_match_key(overlay_df)
    overlay_lookup = overlay_df.drop_duplicates("_overlay_match_key_v2", keep="first").set_index("_overlay_match_key_v2")

    if len(candidate_tracking_df) > 0:
        candidate_tracking_df["_overlay_match_key_v2"] = build_overlay_match_key(candidate_tracking_df)

        def apply_overlay_settlement(row: pd.Series) -> pd.Series:
            match_key = row.get("_overlay_match_key_v2", "")
            if match_key == "" or match_key not in overlay_lookup.index:
                return row
            overlay_row = overlay_lookup.loc[match_key]
            overlay_status = str(overlay_row.get("result_status", "")).strip().upper()
            if overlay_status == "" or overlay_status == "PENDING":
                return row
            row["result_status"] = overlay_row.get("result_status", row["result_status"])
            settlement_source = str(overlay_row.get("settlement_source", "")).strip()
            row["settlement_source"] = settlement_source if settlement_source != "" else "OVERLAY_TRACKING_V1"
            row["finish_position"] = overlay_row.get("finish_position", row["finish_position"])
            row["won"] = overlay_row.get("won", row["won"])
            row["placed"] = overlay_row.get("placed", row["placed"])
            row["profit_1u_win"] = overlay_row.get("profit_1u_win", row["profit_1u_win"])
            return row

        candidate_tracking_df = candidate_tracking_df.apply(apply_overlay_settlement, axis=1)
        candidate_tracking_df["_unique_key_v2"] = build_tracking_key(candidate_tracking_df)
    else:
        candidate_tracking_df["_unique_key_v2"] = pd.Series(dtype=str)

    if len(history_df) > 0:
        history_df["_unique_key_v2"] = build_tracking_key(history_df)
        existing_keys = set(history_df["_unique_key_v2"].tolist())
    else:
        existing_keys = set()

    new_rows_df = candidate_tracking_df[~candidate_tracking_df["_unique_key_v2"].isin(existing_keys)].copy()

    history_core_df = history_df.drop(columns=["_unique_key_v2"], errors="ignore")
    new_rows_core_df = new_rows_df.drop(columns=["_unique_key_v2", "_overlay_match_key_v2"], errors="ignore")

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
    for _, count_row in combined_action_counts.iterrows():
        action_name = str(count_row["execution_action_v2"]).strip().lower()
        summary_rows.append({"metric": f"{action_name}_count", "value": int(count_row["runners"])})

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    current_action_counts = action_counts(candidate_tracking_df.drop(columns=["_unique_key_v2", "_overlay_match_key_v2"], errors="ignore"))

    print("[EDGEIQ_EXECUTION_TRACKING_V2] COMPLETE")
    print(f"signal_date={signal_date}")
    print(f"current_candidates={current_candidates}")
    print(f"new_rows_appended={len(new_rows_core_df)}")
    print(f"history_total_rows={len(combined_df)}")
    print(f"pending_rows={pending_rows}")
    print("\nCounts By execution_action_v2")
    if len(current_action_counts) == 0:
        print("No current execution candidates.")
    else:
        print(current_action_counts.to_string(index=False))
    print(f"\ntracking_out={TRACKING_PATH}")
    print(f"summary_out={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
