from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math
import re
import unicodedata

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

CANDIDATES_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1_candidates.csv"
TRACKING_PATH = DATA_DIR / "edgeiq_overlay_tracking_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_overlay_tracking_v1_summary.csv"

TRACKING_COLUMNS = [
    "signal_date",
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "runner_score_v6",
    "runner_rank_v6",
    "governance_band_v7_2",
    "empirical_fair_price_v1",
    "empirical_fair_prob_v1",
    "market_price_v1",
    "edge_pct_v1",
    "edge_band_v1",
    "overlay_5_v1",
    "overlay_10_v1",
    "overlay_15_v1",
    "overlay_20_v1",
    "overlay_30_v1",
    "result_status",
    "settlement_source",
    "finish_position",
    "won",
    "placed",
    "profit_1u_win",
    "clv_pct",
]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


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


def build_key(df: pd.DataFrame) -> pd.Series:
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


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in TRACKING_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    return df[TRACKING_COLUMNS].copy()


def main() -> None:
    signal_date = datetime.now().date().isoformat()

    candidates_df = pd.read_csv(CANDIDATES_PATH, dtype=str, keep_default_na=False)
    if len(candidates_df) == 0:
        candidates_tracking_df = pd.DataFrame(columns=TRACKING_COLUMNS)
    else:
        candidates_tracking_df = candidates_df.copy()
        candidates_tracking_df["signal_date"] = signal_date
        candidates_tracking_df["result_status"] = "PENDING"
        candidates_tracking_df["settlement_source"] = ""
        candidates_tracking_df["finish_position"] = ""
        candidates_tracking_df["won"] = ""
        candidates_tracking_df["placed"] = ""
        candidates_tracking_df["profit_1u_win"] = ""
        candidates_tracking_df["clv_pct"] = ""
        candidates_tracking_df = ensure_columns(candidates_tracking_df)

    if TRACKING_PATH.exists():
        history_df = pd.read_csv(TRACKING_PATH, dtype=str, keep_default_na=False)
        history_df = ensure_columns(history_df)
    else:
        history_df = pd.DataFrame(columns=TRACKING_COLUMNS)

    if len(history_df) == 0:
        existing_keys = set()
    else:
        history_df["_unique_key_v1"] = build_key(history_df)
        existing_keys = set(history_df["_unique_key_v1"].tolist())

    if len(candidates_tracking_df) == 0:
        new_rows_df = candidates_tracking_df.copy()
    else:
        candidates_tracking_df["_unique_key_v1"] = build_key(candidates_tracking_df)
        new_rows_df = candidates_tracking_df[~candidates_tracking_df["_unique_key_v1"].isin(existing_keys)].copy()

    history_core_df = history_df.drop(columns=["_unique_key_v1"], errors="ignore")
    new_rows_core_df = new_rows_df.drop(columns=["_unique_key_v1"], errors="ignore")

    combined_df = pd.concat([history_core_df, new_rows_core_df], ignore_index=True)
    combined_df = ensure_columns(combined_df)
    combined_df.to_csv(TRACKING_PATH, index=False)

    pending_rows = int((combined_df["result_status"].astype(str).str.upper() == "PENDING").sum())
    summary_df = pd.DataFrame(
        {
            "metric": [
                "current_candidates",
                "new_rows_appended",
                "history_total_rows",
                "pending_rows",
            ],
            "value": [
                int(len(candidates_tracking_df)),
                int(len(new_rows_core_df)),
                int(len(combined_df)),
                pending_rows,
            ],
        }
    )
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_OVERLAY_TRACKING_V1] COMPLETE")
    print(f"signal_date={signal_date}")
    print(f"current_candidates={len(candidates_tracking_df)}")
    print(f"new_rows_appended={len(new_rows_core_df)}")
    print(f"history_total_rows={len(combined_df)}")
    print(f"pending_rows={pending_rows}")
    print(f"tracking_out={TRACKING_PATH}")
    print(f"summary_out={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
