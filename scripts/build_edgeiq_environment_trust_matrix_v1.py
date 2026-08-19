import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT = DATA / "edgeiq_environment_trust_matrix_v1.csv"
SUMMARY = DATA / "edgeiq_environment_trust_matrix_v1_summary.csv"
VERDICT = DATA / "edgeiq_environment_trust_matrix_v1_verdict.csv"

ENV_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]

def clean(x):
    if pd.isna(x):
        return "UNKNOWN"
    return str(x).strip().upper().replace(" ", "_") or "UNKNOWN"

def main():
    if not SRC.exists():
        raise SystemExit("Run environment replay first.")

    df = pd.read_csv(SRC, low_memory=False)

    required = ["environment_band_v1", "environment_win_v1", "trust_profile_v1"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit("Missing required columns: " + ", ".join(missing))

    df["trust_clean_v1"] = df["trust_profile_v1"].map(clean)

    rows = []
    summary_rows = []

    for trust in sorted(df["trust_clean_v1"].unique()):
        tdf = df[df["trust_clean_v1"] == trust]

        for env in ENV_ORDER:
            x = tdf[tdf["environment_band_v1"] == env]
            runners = len(x)
            wins = int(x["environment_win_v1"].sum()) if runners else 0
            rows.append({
                "trust_profile_v1": trust,
                "environment_band_v1": env,
                "runners": int(runners),
                "wins": wins,
                "win_pct": round(wins / runners * 100, 2) if runners else 0,
            })

        weak = tdf[tdf["environment_band_v1"].isin(["POOR", "NEGATIVE"])]
        strong = tdf[tdf["environment_band_v1"].isin(["POSITIVE", "ELITE"])]
        weak_win = weak["environment_win_v1"].mean() * 100 if len(weak) else 0
        strong_win = strong["environment_win_v1"].mean() * 100 if len(strong) else 0

        summary_rows.append({
            "trust_profile_v1": trust,
            "runners": int(len(tdf)),
            "weak_runners": int(len(weak)),
            "weak_win_pct": round(weak_win, 2),
            "neutral_runners": int((tdf["environment_band_v1"] == "NEUTRAL").sum()),
            "strong_runners": int(len(strong)),
            "strong_win_pct": round(strong_win, 2),
            "lift_pts": round(strong_win - weak_win, 2) if len(weak) and len(strong) else 0,
            "passes": bool(len(weak) and len(strong) and strong_win > weak_win),
        })

    out = pd.DataFrame(rows)
    summary = pd.DataFrame(summary_rows).sort_values("runners", ascending=False)

    out.to_csv(OUT, index=False)
    summary.to_csv(SUMMARY, index=False)

    meaningful = summary[(summary["weak_runners"] >= 30) & (summary["strong_runners"] >= 30)]
    pass_count = int(meaningful["passes"].sum())
    total = int(len(meaningful))
    verdict = "ENVIRONMENT_ADDS_BEYOND_TRUST" if total and pass_count == total else "ENVIRONMENT_TRUST_INDEPENDENCE_MIXED"

    pd.DataFrame([{
        "verdict": verdict,
        "trust_groups_tested": total,
        "trust_groups_passed": pass_count,
        "avg_lift_pts": round(meaningful["lift_pts"].mean(), 2) if total else "",
        "meaning": "Pass means POSITIVE+ beats POOR/NEGATIVE inside each meaningful Trust bucket.",
    }]).to_csv(VERDICT, index=False)

    print("[ENVIRONMENT_TRUST_MATRIX_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={VERDICT}")
    print(summary.to_string(index=False))
    print(f"VERDICT={verdict}")

if __name__ == "__main__":
    main()
