import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT = DATA / "edgeiq_environment_exclusion_audit_v1.csv"
SUMMARY = DATA / "edgeiq_environment_exclusion_audit_v1_summary.csv"

def summarise(name, df):
    runners = len(df)
    wins = int(df["environment_win_v1"].sum()) if runners else 0
    win_pct = wins / runners * 100 if runners else 0

    px = pd.to_numeric(df.get("environment_replay_price_v1"), errors="coerce")
    expected = (1 / px).replace([float("inf")], pd.NA).sum(skipna=True)
    ae = wins / expected if expected and expected > 0 else pd.NA

    profit = pd.to_numeric(df.get("environment_replay_profit_v1"), errors="coerce").sum(skipna=True)
    staked = pd.to_numeric(df.get("environment_replay_profit_v1"), errors="coerce").notna().sum()
    roi = profit / staked * 100 if staked else pd.NA

    return {
        "scenario": name,
        "runners": int(runners),
        "wins": wins,
        "win_pct": round(win_pct, 2),
        "expected_wins": round(expected, 3) if expected else "",
        "ae": round(ae, 3) if pd.notna(ae) else "",
        "profit": round(profit, 3) if staked else "",
        "roi_pct": round(roi, 2) if pd.notna(roi) else "",
    }

def main():
    if not SRC.exists():
        raise SystemExit("Run build_edgeiq_environment_score_replay_v1.py first.")

    df = pd.read_csv(SRC, low_memory=False)
    if "environment_band_v1" not in df.columns:
        raise SystemExit("environment_band_v1 missing.")

    scenarios = [
        ("ALL", df),
        ("REMOVE_POOR", df[df["environment_band_v1"] != "POOR"]),
        ("REMOVE_POOR_NEGATIVE", df[~df["environment_band_v1"].isin(["POOR", "NEGATIVE"])]),
        ("POSITIVE_PLUS", df[df["environment_band_v1"].isin(["POSITIVE", "ELITE"])]),
        ("ELITE_ONLY", df[df["environment_band_v1"] == "ELITE"]),
    ]

    out = pd.DataFrame([summarise(name, x) for name, x in scenarios])
    out.to_csv(OUT, index=False)

    base = out[out["scenario"] == "ALL"].iloc[0]
    best = out.sort_values(["ae", "win_pct"], ascending=False).head(1).iloc[0]

    pd.DataFrame([{
        "base_win_pct": base["win_pct"],
        "best_scenario": best["scenario"],
        "best_win_pct": best["win_pct"],
        "best_ae": best["ae"],
        "verdict": "EXCLUSION_HAS_VALUE" if best["scenario"] != "ALL" and best["win_pct"] > base["win_pct"] else "EXCLUSION_NOT_PROVEN",
    }]).to_csv(SUMMARY, index=False)

    print("[ENVIRONMENT_EXCLUSION_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(out.to_string(index=False))

if __name__ == "__main__":
    main()
