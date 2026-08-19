import re
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ENV_SRC = DATA / "edgeiq_environment_score_replay_v1.csv"
SP_SRC = DATA / "edgeiq_lone_leader_interaction_audit_v1.csv"

OUT = DATA / "edgeiq_environment_market_audit_v1.csv"
SUMMARY = DATA / "edgeiq_environment_market_audit_v1_summary.csv"
VERDICT = DATA / "edgeiq_environment_market_audit_v1_verdict.csv"

ENV_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]

def clean_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).strip().upper())

def clean_key(x):
    return re.sub(r"[^A-Z0-9]+", "", clean_text(x))

def make_join(df, horse_col):
    return (
        df["meeting_date"].astype(str).str.strip()
        + "|" + df["track"].map(clean_key)
        + "|" + df["race_no"].astype(str).str.extract(r"(\d+)", expand=False).fillna(df["race_no"].astype(str))
        + "|" + df[horse_col].map(clean_key)
    )

def summarise(label, df):
    runners = len(df)
    wins = int(df["environment_win_v1"].sum()) if runners else 0
    win_pct = wins / runners * 100 if runners else 0

    px = pd.to_numeric(df["sp_num_v1"], errors="coerce")
    valid = df[px.notna() & (px > 1)].copy()
    valid_px = pd.to_numeric(valid["sp_num_v1"], errors="coerce")

    valid_runners = len(valid)
    valid_wins = int(valid["environment_win_v1"].sum()) if valid_runners else 0
    valid_win_pct = valid_wins / valid_runners * 100 if valid_runners else 0

    expected = (1 / valid_px).sum() if valid_runners else 0
    ae = valid_wins / expected if expected > 0 else 0

    profit = 0.0
    for _, r in valid.iterrows():
        sp = float(r["sp_num_v1"])
        profit += (sp - 1.0) if int(r["environment_win_v1"]) == 1 else -1.0

    roi = profit / valid_runners * 100 if valid_runners else 0

    return {
        "segment": label,
        "runners": int(runners),
        "wins": wins,
        "win_pct": round(win_pct, 2),
        "valid_sp_runners": int(valid_runners),
        "valid_sp_wins": valid_wins,
        "valid_sp_win_pct": round(valid_win_pct, 2),
        "avg_sp": round(valid_px.mean(), 3) if valid_runners else "",
        "expected_wins": round(expected, 3) if valid_runners else "",
        "ae": round(ae, 3) if valid_runners else "",
        "profit_1u": round(profit, 3) if valid_runners else "",
        "roi_pct": round(roi, 2) if valid_runners else "",
    }

def main():
    if not ENV_SRC.exists():
        raise SystemExit("Missing edgeiq_environment_score_replay_v1.csv. Run environment replay first.")
    if not SP_SRC.exists():
        raise SystemExit("Missing edgeiq_lone_leader_interaction_audit_v1.csv. Need SP source.")

    env = pd.read_csv(ENV_SRC, low_memory=False)
    sp = pd.read_csv(SP_SRC, low_memory=False)

    env_required = ["meeting_date", "track", "race_no", "rank1_horse", "environment_band_v1", "environment_win_v1"]
    sp_required = ["meeting_date", "track", "race_no", "horse", "sp_num_v1"]

    missing_env = [c for c in env_required if c not in env.columns]
    missing_sp = [c for c in sp_required if c not in sp.columns]

    if missing_env:
        raise SystemExit("Environment file missing: " + ", ".join(missing_env))
    if missing_sp:
        raise SystemExit("SP file missing: " + ", ".join(missing_sp))

    env = env.copy()
    sp = sp.copy()

    env["market_join_key_v1"] = make_join(env, "rank1_horse")
    sp["market_join_key_v1"] = make_join(sp, "horse")

    sp_keep = sp[["market_join_key_v1", "sp_num_v1", "expected_win_prob_sp", "profit_1u"]].copy()
    sp_keep = sp_keep.drop_duplicates("market_join_key_v1")

    df = env.merge(sp_keep, on="market_join_key_v1", how="left")

    rows = []

    rows.append(summarise("ALL", df))

    for band in ENV_ORDER:
        rows.append(summarise(f"BAND_{band}", df[df["environment_band_v1"] == band]))

    weak = df[df["environment_band_v1"].isin(["POOR", "NEGATIVE"])]
    neutral = df[df["environment_band_v1"] == "NEUTRAL"]
    strong = df[df["environment_band_v1"].isin(["POSITIVE", "ELITE"])]

    rows.append(summarise("WEAK_POOR_NEGATIVE", weak))
    rows.append(summarise("NEUTRAL_ONLY", neutral))
    rows.append(summarise("STRONG_POSITIVE_ELITE", strong))

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    all_row = out[out["segment"] == "ALL"].iloc[0]
    weak_row = out[out["segment"] == "WEAK_POOR_NEGATIVE"].iloc[0]
    strong_row = out[out["segment"] == "STRONG_POSITIVE_ELITE"].iloc[0]

    valid_sp_total = int(all_row["valid_sp_runners"])
    coverage = valid_sp_total / len(df) * 100 if len(df) else 0

    strong_ae = float(strong_row["ae"]) if strong_row["ae"] != "" else 0
    weak_ae = float(weak_row["ae"]) if weak_row["ae"] != "" else 0

    verdict = "ENVIRONMENT_MARKET_EDGE_NOT_PROVEN"
    if valid_sp_total >= 1000 and strong_ae > weak_ae and strong_ae >= 1.0:
        verdict = "ENVIRONMENT_MARKET_EDGE_INDICATED"
    elif valid_sp_total >= 1000 and strong_ae > weak_ae:
        verdict = "ENVIRONMENT_MARKET_EFFICIENCY_IMPROVES_BUT_UNDER_1_AE"

    summary = pd.DataFrame([{
        "rows": int(len(df)),
        "valid_sp_rows": valid_sp_total,
        "sp_coverage_pct": round(coverage, 2),
        "weak_ae": weak_row["ae"],
        "weak_roi_pct": weak_row["roi_pct"],
        "strong_ae": strong_row["ae"],
        "strong_roi_pct": strong_row["roi_pct"],
        "strong_minus_weak_ae": round(strong_ae - weak_ae, 3),
        "verdict": verdict,
    }])
    summary.to_csv(SUMMARY, index=False)

    pd.DataFrame([{
        "verdict": verdict,
        "important_note": "This uses SP only where available from edgeiq_lone_leader_interaction_audit_v1.csv.",
        "next_step": "If SP coverage is limited, build a wider Rank1 SP join from the full historical results warehouse.",
    }]).to_csv(VERDICT, index=False)

    print("[ENVIRONMENT_MARKET_AUDIT_V1] COMPLETE")
    print(f"joined_rows={len(df)}")
    print(f"valid_sp_rows={valid_sp_total}")
    print(f"sp_coverage_pct={round(coverage, 2)}")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={VERDICT}")
    print("")
    print(summary.to_string(index=False))
    print("")
    print(out.to_string(index=False))

if __name__ == "__main__":
    main()
