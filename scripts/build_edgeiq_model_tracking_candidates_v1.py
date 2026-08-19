from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_v6_1_research_vs_production_comparison_v1_TAB_ONLY_TODAY.csv"
TRACKING = DATA / "edgeiq_model_tracking_v1.csv"
SUMMARY = DATA / "edgeiq_model_tracking_v1_summary.csv"

MODEL_NAME = "V6_1_RESEARCH_TAB_ONLY"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def main() -> None:
    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
    cands = df[df["v6_1_research_action"].isin(["LEAN", "WATCH"])].copy()

    rows: list[dict[str, str]] = []
    now = datetime.now().isoformat(timespec="seconds")

    for _, row in cands.iterrows():
        rows.append(
            {
                "tracking_key": f'{clean(row.get("track"))}|R{clean(row.get("race_no"))}|{clean(row.get("horse"))}|{MODEL_NAME}',
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "model_name": MODEL_NAME,
                "fair_price": clean(row.get("V6_1_RESEARCH_fair_price")),
                "live_price": clean(row.get("live_price")),
                "edge_pct": clean(row.get("v6_1_research_edge_pct")),
                "projection_band": clean(row.get("v6_1_research_band")),
                "projection_gap": clean(row.get("v6_1_research_gap")),
                "action": clean(row.get("v6_1_research_action")),
                "status": "PENDING",
                "result_finish_pos": "",
                "won": "",
                "placed": "",
                "sp": "",
                "tab_close_price": clean(row.get("live_price")),
                "roi_win": "",
                "roi_place": "",
                "tracked_at": now,
                "resolved_at": "",
            }
        )

    new = pd.DataFrame(rows)

    if TRACKING.exists():
        old = pd.read_csv(TRACKING, dtype=str, keep_default_na=False, low_memory=False)
        out = pd.concat([old, new], ignore_index=True)
        out = out.drop_duplicates(["tracking_key"], keep="last")
    else:
        out = new.copy()

    out.to_csv(TRACKING, index=False)

    summary = (
        out.groupby(["model_name", "status", "action"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["model_name", "status", "action"])
    )
    summary.to_csv(SUMMARY, index=False)

    print("[MODEL_TRACKING_CANDIDATES_V1] COMPLETE")
    print(f"new_candidates={len(new)}")
    print(f"total_tracking_rows={len(out)}")
    print(f"tracking={TRACKING}")
    print(f"summary={SUMMARY}")

    if new.empty:
        print("no_new_candidate_rows")
        return

    sample_cols = [
        "track",
        "race_no",
        "horse",
        "model_name",
        "live_price",
        "fair_price",
        "edge_pct",
        "action",
        "projection_band",
        "projection_gap",
    ]
    print(new[sample_cols].to_string(index=False))


if __name__ == "__main__":
    main()
