from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_model_tracking_v1.csv"
OUT = DATA / "edgeiq_model_tracking_dashboard_v1.csv"


def main() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    cols = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "model_name",
        "live_price",
        "fair_price",
        "edge_pct",
        "projection_band",
        "projection_gap",
        "action",
        "status",
        "result_finish_pos",
        "won",
        "placed",
        "roi_win",
        "tracked_at",
    ]

    for column in cols:
        if column not in df.columns:
            df[column] = ""

    df = df[cols].copy()
    df["race_date_key"] = df["race_date"].astype(str).str[:10]
    df["status_key"] = df["status"].astype(str).str.upper().str.strip()
    df = df[(df["race_date_key"] == today) & (df["status_key"] == "PENDING")].copy()
    df["sort_edge"] = pd.to_numeric(df["edge_pct"], errors="coerce").fillna(-999.0)
    df = df.sort_values(["race_date", "track", "race_no", "sort_edge"], ascending=[True, True, True, False])
    df = df.drop(columns=["race_date_key", "status_key", "sort_edge"])

    df.to_csv(OUT, index=False)

    print("[MODEL_TRACKING_DASHBOARD_V1] COMPLETE")
    print(f"today={today}")
    print(f"rows={len(df)}")
    print(f"out={OUT}")
    if df.empty:
        print("no_pending_rows_today")
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
