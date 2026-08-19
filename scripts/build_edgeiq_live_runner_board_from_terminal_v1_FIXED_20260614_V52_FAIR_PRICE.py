import pandas as pd
from pathlib import Path
import re
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_terminal_feed_v1.csv"
PROB = DATA / "edgeiq_probability_engine_v3.csv"
FAIR = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
INTEL = DATA / "edgeiq_runner_intelligence_v1.csv"

OUT = DATA / "edgeiq_live_runner_board_v1.csv"
DIAG = DATA / "edgeiq_live_runner_board_v1_diagnostics.csv"
MISS = DATA / "edgeiq_live_runner_board_v1_unmatched.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon(x):
    return re.sub(r"[^A-Z0-9]+", "", clean(x).upper())

def num(x):
    try:
        s = clean(x).replace("$", "").replace(",", "")
        if not s:
            return math.nan
        return float(s)
    except Exception:
        return math.nan

def edge_pct(live, fair):
    l = num(live)
    f = num(fair)
    if math.isnan(l) or math.isnan(f) or f <= 0:
        return ""
    return round(((l / f) - 1) * 100, 1)

def main():
    df = pd.read_csv(SRC, dtype=str).fillna("")

    if "horse" not in df.columns:
        raise SystemExit("edgeiq_live_terminal_feed_v1.csv missing horse column")

    df["horse_canon"] = df["horse"].map(canon)
    df["track_join"] = df["track"].map(canon)
    df["race_no_join"] = df["race_no"].map(clean)

    if "live_price" not in df.columns:
        df["live_price"] = ""

    # HARD RULE:
    # Do NOT use terminal feed edgeiq_price/rated_price/price as fair price.
    # Those created fake overlays when V3 was stale/missing.
    df["fair_price"] = ""
    df["v3_probability"] = ""
    df["v3_realism_grade"] = ""
    df["v3_pricing_action"] = ""

    if FAIR.exists():
        fair = pd.read_csv(FAIR, dtype=str).fillna("")
        if {"track","race_no","horse","rated_price_v5_2_review","rated_probability_v5_2_review","rated_price_status_v5_2_review"}.issubset(fair.columns):
            fair["horse_canon"] = fair["horse"].map(canon)
            fair["track_join"] = fair["track"].map(canon)
            fair["race_no_join"] = fair["race_no"].map(clean)

            fair_small = fair[
                [
                    "track_join","race_no_join","horse_canon",
                    "rated_price_v5_2_review",
                    "rated_probability_v5_2_review",
                    "rated_price_status_v5_2_review"
                ]
            ].drop_duplicates(["track_join","race_no_join","horse_canon"], keep="first")

            df = df.merge(
                fair_small,
                on=["track_join","race_no_join","horse_canon"],
                how="left",
                suffixes=("", "_fairv52")
            )

            df["fair_price"] = df["rated_price_v5_2_review"].fillna("")
            df["v3_probability"] = df["rated_probability_v5_2_review"].fillna("")

            status_col = "rated_price_status_v5_2_review"
            if "rated_price_status_v5_2_review_fairv52" in df.columns:
                status_col = "rated_price_status_v5_2_review_fairv52"

            df["v3_realism_grade"] = df[status_col].fillna("")
            df["rated_price_status_v5_2_review"] = df[status_col].fillna("")
            df["v3_pricing_action"] = "V5_2_REVIEW_PRICE"

    df["edge_pct"] = df.apply(lambda r: edge_pct(r.get("live_price",""), r.get("fair_price","")), axis=1)

    def action(r):
        live = clean(r.get("live_price",""))
        fair = clean(r.get("fair_price",""))
        edge = num(r.get("edge_pct",""))

        if not live:
            return "NO_LIVE"
        if not fair:
            return "NO_MODEL"
        if math.isnan(edge):
            return "NO_EDGE"
        if edge >= 18:
            return "WATCH"
        if edge >= 6:
            return "LEAN"
        if edge <= -18:
            return "UNDERLAY"
        return "PASS"

    df["execution_action"] = df.apply(action, axis=1)
    df["market_state"] = df.apply(lambda r: "NO_MODEL" if clean(r.get("fair_price","")) == "" else ("NO_LIVE" if clean(r.get("live_price","")) == "" else "LIVE"), axis=1)
    df["confidence_score"] = df.apply(lambda r: "0" if clean(r.get("fair_price","")) == "" else ("50" if clean(r.get("live_price","")) else "35"), axis=1)

    defaults = {
        "bookmaker": "",
        "edge_rank": "",
        "fair_rank": "",
        "live_rank": "",
        "projected_spd": "",
        "settling_band": "",
        "run_style": "",
        "archetype": "",
        "dna_confidence": "",
        "fatigue_risk_index": "",
        "late_power_index": "",
        "movement_velocity": "",
        "sectional_weapon_score": "",
        "intelligence_note": "",
        "projected_rating_v5_2": "",
        "projection_band_v5_2": "",
        "projection_confidence_v5_2": "",
        "projection_gap_v5_2": "",
        "race_target_rating_v5_2": "",
        "rated_price_status_v5_2_review": "",
        "sportsbet_event_id": "",
        "sportsbet_market_id": "",
        "sportsbet_timestamp": "",
        "mobile_silk_image": "",
        "market_mover": "",
        "horse_no": "",
        "barrier": "",
        "jockey": "",
        "trainer": "",
        "distance": "",
        "track_condition": "",
        "rail_position": ""
    }

    if INTEL.exists():
        intel = pd.read_csv(INTEL, dtype=str).fillna("")
        if {"track","race_no","horse"}.issubset(intel.columns):
            intel["horse_canon"] = intel["horse"].map(canon)
            intel["track_join"] = intel["track"].map(canon)
            intel["race_no_join"] = intel["race_no"].map(clean)

            intel_cols = [
                "track_join","race_no_join","horse_canon",
                "projected_spd","settling_band","run_style","archetype","dna_confidence",
                "fatigue_risk_index","late_power_index","sectional_weapon_score",
                "intelligence_note","confidence_score"
            ]
            intel_cols = [c for c in intel_cols if c in intel.columns]

            intel_small = intel[intel_cols].drop_duplicates(
                ["track_join","race_no_join","horse_canon"],
                keep="first"
            )

            df = df.merge(
                intel_small,
                on=["track_join","race_no_join","horse_canon"],
                how="left",
                suffixes=("", "_intel")
            )

            for c in [
                "projected_spd","settling_band","run_style","archetype","dna_confidence",
                "fatigue_risk_index","late_power_index","sectional_weapon_score",
                "intelligence_note","confidence_score"
            ]:
                ic = c + "_intel"
                if ic in df.columns:
                    if c not in df.columns:
                        df[c] = ""
                    df[c] = df[c].where(df[c].astype(str).str.strip() != "", df[ic])
    for k, v in defaults.items():
        if k not in df.columns:
            df[k] = v

    keep = [
        "race_date","track","race_no","horse_no","horse","horse_canon",
        "barrier","jockey","trainer","distance","track_condition","rail_position",
        "live_price","fair_price","edge_pct","execution_action","market_state",
        "confidence_score","bookmaker","edge_rank","fair_rank","live_rank",
        "projected_spd","settling_band","run_style","archetype","dna_confidence",
        "fatigue_risk_index","late_power_index","movement_velocity","sectional_weapon_score",
        "intelligence_note","v3_pricing_action","v3_probability","v3_realism_grade",
        "projected_rating_v5_2","projection_band_v5_2","projection_confidence_v5_2",
        "projection_gap_v5_2","race_target_rating_v5_2","rated_price_status_v5_2_review",
        "sportsbet_event_id","sportsbet_market_id","sportsbet_timestamp",
        "mobile_silk_image","market_mover"
    ]

    keep = [c for c in keep if c in df.columns]
    out = df[keep].copy()

    out.to_csv(OUT, index=False)
    pd.DataFrame(columns=out.columns).to_csv(MISS, index=False)

    diag = pd.DataFrame([
        ["status", "COMPLETE"],
        ["source", SRC.name],
        ["rows", len(out)],
        ["date_breakdown", "; ".join([f"{k}:{v}" for k,v in out["race_date"].value_counts().to_dict().items()])],
        ["with_live_price", int((out["live_price"].astype(str).str.strip() != "").sum())],
        ["with_fair_price", int((out["fair_price"].astype(str).str.strip() != "").sum())],
        ["with_edge", int((out["edge_pct"].astype(str).str.strip() != "").sum())],
        ["no_model_rows", int((out["execution_action"] == "NO_MODEL").sum())],
        ["watch_rows", int((out["execution_action"] == "WATCH").sum())],
        ["output", OUT.name],
    ], columns=["metric","value"])

    diag.to_csv(DIAG, index=False)

    print("[LIVE_RUNNER_BOARD_FROM_TERMINAL_V1_SAFE] COMPLETE")
    print(f"rows={len(out)}")
    print("dates=" + "; ".join([f"{k}:{v}" for k,v in out["race_date"].value_counts().to_dict().items()]))
    print(f"with_fair_price={(out['fair_price'].astype(str).str.strip() != '').sum()}")
    print(f"with_edge={(out['edge_pct'].astype(str).str.strip() != '').sum()}")
    print(f"no_model={(out['execution_action'] == 'NO_MODEL').sum()}")
    print(f"wrote={OUT}")

if __name__ == "__main__":
    main()






