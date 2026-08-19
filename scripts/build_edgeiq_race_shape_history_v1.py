from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SHAPE_FIT = DATA / "edgeiq_race_shape_fit_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"
MARKET = DATA / "edgeiq_market_rank_v1.csv"

OUTPUT = DATA / "edgeiq_race_shape_history_v1.csv"
AUDIT = DATA / "edgeiq_race_shape_history_v1_audit.csv"

def clean_key(v):
    if pd.isna(v):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(v).upper().strip())

def normalise_race_key(v):
    if pd.isna(v):
        return ""
    s = str(v).upper().strip()
    parts = s.split("|")
    if len(parts) >= 3:
        last = parts[-1].strip()
        if re.fullmatch(r"\d+", last):
            parts[-1] = "R" + last
        return "|".join(parts)
    return s

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(str(v).replace("$","").replace(",","").strip())
    except:
        return np.nan

def finish_num(v):
    try:
        s = str(v).upper().strip()
        if s in ["SCR", "SCRATCHED", "", "NAN"]:
            return np.nan
        return float(re.sub(r"[^0-9.]", "", s))
    except:
        return np.nan

def main():
    for p in [SHAPE_FIT, RESULTS]:
        if not p.exists():
            raise FileNotFoundError(f"Missing input: {p}")

    sf = pd.read_csv(SHAPE_FIT)
    res = pd.read_csv(RESULTS)

    sf["race_key_join"] = sf["race_key"].apply(normalise_race_key)
    sf["horse_key_join"] = sf["horse_key"].apply(clean_key)

    res["race_key_join"] = res["race_key"].apply(normalise_race_key) if "race_key" in res.columns else (
        res["meeting_date"].astype(str).str.strip()
        + "|"
        + res["track"].astype(str).str.upper().str.strip()
        + "|R"
        + res["race_no"].astype(str).str.replace(".0","",regex=False).str.strip()
    )

    if "horseKey" in res.columns:
        res["horse_key_join"] = res["horseKey"].apply(clean_key)
    elif "horse_key" in res.columns:
        res["horse_key_join"] = res["horse_key"].apply(clean_key)
    elif "horseName" in res.columns:
        res["horse_key_join"] = res["horseName"].apply(clean_key)
    else:
        raise ValueError("Results missing horse key/name")

    finish_col = "finishPosition" if "finishPosition" in res.columns else "finish_position"
    horse_name_col = "horseName" if "horseName" in res.columns else "horse"

    res_small = res.copy()
    res_small["finish_position_num"] = res_small[finish_col].apply(finish_num) if finish_col in res_small.columns else np.nan
    res_small["won"] = np.where(res_small["finish_position_num"] == 1, 1, 0)
    res_small["placed"] = np.where(res_small["finish_position_num"].between(1,3), 1, 0)

    keep_res = [
        "race_key_join",
        "horse_key_join",
        horse_name_col,
        finish_col,
        "finish_position_num",
        "won",
        "placed",
        "sp",
        "margin",
        "raceTime",
        "raceClass",
        "trackCondition",
        "distance",
        "jockey",
        "trainer",
        "barrier",
    ]
    keep_res = [c for c in keep_res if c in res_small.columns]
    res_small = res_small[keep_res].drop_duplicates(["race_key_join","horse_key_join"], keep="first")

    out = sf.merge(
        res_small,
        on=["race_key_join","horse_key_join"],
        how="left",
        suffixes=("","_result")
    )

    if MARKET.exists():
        mk = pd.read_csv(MARKET)
        mk["race_key_join"] = mk["race_key"].apply(normalise_race_key)
        mk["horse_key_join"] = mk["horse_key"].apply(clean_key)

        keep_mk = [
            "race_key_join",
            "horse_key_join",
            "market_price_v1",
            "market_rank_v1",
            "shape_edge_v1",
            "shape_edge_band_v1",
        ]
        keep_mk = [c for c in keep_mk if c in mk.columns]
        mk = mk[keep_mk].drop_duplicates(["race_key_join","horse_key_join"], keep="first")

        out = out.merge(
            mk,
            on=["race_key_join","horse_key_join"],
            how="left",
            suffixes=("","_market")
        )

    out["race_shape_history_engine"] = "RACE_SHAPE_HISTORY_V1"
    out["race_shape_history_note"] = "CURRENT_SHAPE_ARCHIVE_WITH_RESULTS_JOIN"

    preferred = [
        "race_key",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "race_shape_v1",
        "pace_pressure_v3",
        "ability_dna_v3",
        "positional_dna_v3",
        "race_shape_fit_score_v1",
        "race_shape_fit_band_v1",
        "shape_fit_rank_in_race",
        "shape_fit_percentile_in_race",
        "market_price_v1",
        "market_rank_v1",
        "shape_edge_v1",
        "shape_edge_band_v1",
        finish_col,
        "finish_position_num",
        "won",
        "placed",
        "sp",
        "margin",
        "distance",
        "raceClass",
        "trackCondition",
        "jockey",
        "trainer",
        "barrier",
    ]
    preferred = [c for c in preferred if c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    matched_results = int(out["finish_position_num"].notna().sum()) if "finish_position_num" in out.columns else 0
    matched_market = int(out["market_rank_v1"].notna().sum()) if "market_rank_v1" in out.columns else 0

    audit = pd.DataFrame([{
        "shape_rows": len(sf),
        "result_rows": len(res),
        "output_rows": len(out),
        "unique_races": out["race_key"].nunique() if "race_key" in out.columns else "",
        "unique_horses": out["horse_key"].nunique() if "horse_key" in out.columns else "",
        "matched_results": matched_results,
        "unmatched_results": int(len(out) - matched_results),
        "matched_market": matched_market,
        "unmatched_market": int(len(out) - matched_market),
        "wins_joined": int(out["won"].sum()) if "won" in out.columns else 0,
        "places_joined": int(out["placed"].sum()) if "placed" in out.columns else 0,
        "output": str(OUTPUT),
    }])
    audit.to_csv(AUDIT, index=False)

    print("[RACE_SHAPE_HISTORY_V1] COMPLETE")
    print(f"output_rows={len(out)}")
    print(f"matched_results={matched_results}")
    print(f"matched_market={matched_market}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
