import re
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FAIR_IN = DATA / "edgeiq_fair_price_v7_2.csv"
TAB_IN = DATA / "edgeiq_tab_vic_racecards_v1.csv"

OUT = DATA / "edgeiq_overlay_audit_v1.csv"
AUDIT = DATA / "edgeiq_overlay_audit_v1_summary.csv"

TARGETS = {"AFTERMATH", "REAL ALLIANCE", "CHOUXDINO"}

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    return "" if pd.isna(x) else str(x).upper().strip()

def is_nonblank(x):
    if pd.isna(x):
        return False
    s = str(x).strip()
    return s not in ["", "nan", "NaN", "None", "NONE", "<NA>"]

def band(edge):
    if pd.isna(edge):
        return "NO_MARKET"
    if edge >= 25:
        return "EXECUTE_CANDIDATE"
    if edge >= 15:
        return "STRONG_WATCH"
    if edge >= 8:
        return "WATCH"
    if edge >= 0:
        return "FAIR"
    return "UNDERLAY"

def main():
    fair = pd.read_csv(FAIR_IN)
    tab = pd.read_csv(TAB_IN)

    fair["join_track"] = fair["track"].map(norm_track)
    fair["join_race_no"] = pd.to_numeric(fair["race_no"], errors="coerce").astype("Int64")
    fair["join_horse"] = fair["horse"].map(canon)

    tab["join_track"] = tab["meeting_name"].map(norm_track)
    tab["join_race_no"] = pd.to_numeric(tab["race_no"], errors="coerce").astype("Int64")
    tab["join_horse"] = tab["horse"].map(canon)

    tab["tab_fixed_win"] = pd.to_numeric(tab["tab_fixed_win"], errors="coerce")
    tab["tab_fixed_open_win"] = pd.to_numeric(tab["tab_fixed_open_win"], errors="coerce")

    status = tab["tab_fixed_betting_status"].astype(str).str.upper().str.strip() if "tab_fixed_betting_status" in tab.columns else ""
    scratched_time = tab["scratched_time"].apply(is_nonblank) if "scratched_time" in tab.columns else False

    tab["tab_scratched_v1"] = (
        status.str.contains("SCRATCH", na=False) |
        scratched_time
    )

    tab_keep = [
        "join_track", "join_race_no", "join_horse",
        "tab_fixed_win", "tab_fixed_open_win",
        "tab_fixed_betting_status", "tab_scratched_v1",
        "tab_fixed_percentage_change",
        "tab_fixed_place", "tab_tote_win",
        "early_speed_band", "early_speed_rating",
        "dfs_form_rating", "silk_url", "runner_form_url",
    ]

    tab = tab[[c for c in tab_keep if c in tab.columns]].drop_duplicates(
        ["join_track", "join_race_no", "join_horse"],
        keep="last"
    )

    out = fair.merge(
        tab,
        on=["join_track", "join_race_no", "join_horse"],
        how="left",
        indicator=True
    )

    out["fair_price_v7_2"] = pd.to_numeric(out["fair_price_v7_2"], errors="coerce")
    out["runner_score_v3_1"] = pd.to_numeric(out["runner_score_v3_1"], errors="coerce")
    out["tab_fixed_win"] = pd.to_numeric(out["tab_fixed_win"], errors="coerce")

    out["market_match_status_v1"] = np.where(out["_merge"].eq("both"), "MATCHED", "UNMATCHED")

    out["tab_scratched_v1"] = out["tab_scratched_v1"].fillna(False).astype(bool)

    out["overlay_pct_v1"] = ((out["tab_fixed_win"] / out["fair_price_v7_2"]) - 1.0) * 100.0
    out["overlay_pct_v1"] = out["overlay_pct_v1"].round(1)
    out["overlay_band_v1"] = out["overlay_pct_v1"].apply(band)

    out.loc[out["tab_scratched_v1"], "overlay_band_v1"] = "SCRATCHED"
    out.loc[out["market_match_status_v1"].eq("UNMATCHED"), "overlay_band_v1"] = "NO_MARKET"
    out.loc[out["tab_fixed_win"].isna() & ~out["tab_scratched_v1"], "overlay_band_v1"] = "NO_MARKET"

    out["target_watch_v1"] = out["join_horse"].isin({canon(x) for x in TARGETS})

    out = out.sort_values(
        ["overlay_pct_v1", "runner_score_v3_1"],
        ascending=[False, False],
        na_position="last"
    )

    out.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "rows", "value": len(out)},
        {"metric": "races", "value": out["join_track"].astype(str).add("|").add(out["join_race_no"].astype(str)).nunique()},
        {"metric": "matched_market_rows", "value": int((out["market_match_status_v1"] == "MATCHED").sum())},
        {"metric": "unmatched_market_rows", "value": int((out["market_match_status_v1"] == "UNMATCHED").sum())},
        {"metric": "priced_rows", "value": int(out["tab_fixed_win"].notna().sum())},
        {"metric": "scratched_rows", "value": int((out["overlay_band_v1"] == "SCRATCHED").sum())},
        {"metric": "execute_candidates", "value": int((out["overlay_band_v1"] == "EXECUTE_CANDIDATE").sum())},
        {"metric": "strong_watch", "value": int((out["overlay_band_v1"] == "STRONG_WATCH").sum())},
        {"metric": "watch", "value": int((out["overlay_band_v1"] == "WATCH").sum())},
        {"metric": "fair", "value": int((out["overlay_band_v1"] == "FAIR").sum())},
        {"metric": "underlays", "value": int((out["overlay_band_v1"] == "UNDERLAY").sum())},
        {"metric": "no_market", "value": int((out["overlay_band_v1"] == "NO_MARKET").sum())},
    ])

    summary.to_csv(AUDIT, index=False)

    print("[OVERLAY_AUDIT_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"matched_market_rows={(out['market_match_status_v1'] == 'MATCHED').sum()}")
    print(f"priced_rows={out['tab_fixed_win'].notna().sum()}")
    print(f"scratched_rows={(out['overlay_band_v1'] == 'SCRATCHED').sum()}")
    print(f"execute_candidates={(out['overlay_band_v1'] == 'EXECUTE_CANDIDATE').sum()}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
