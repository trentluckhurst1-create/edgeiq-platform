import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT = DATA / "edgeiq_environment_score_share_matrix_v1.csv"
SUMMARY = DATA / "edgeiq_environment_score_share_matrix_v1_summary.csv"
VERDICT = DATA / "edgeiq_environment_score_share_matrix_v1_verdict.csv"

ENV_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]

def clean(x):
    if pd.isna(x):
        return "UNKNOWN"
    return str(x).strip().upper().replace(" ", "_") or "UNKNOWN"

def main():
    if not SRC.exists():
        raise SystemExit("Run environment replay first.")

    df = pd.read_csv(SRC, low_memory=False)

    band_col = "score_share_band"
    if band_col not in df.columns:
        if "score_share_band_v1" in df.columns:
            band_col = "score_share_band_v1"
        else:
            raise SystemExit("Missing score share band column.")

    required = ["environment_band_v1", "environment_win_v1", band_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit("Missing required columns: " + ", ".join(missing))

    df["score_share_clean_v1"] = df[band_col].map(clean)

    rows = []
    summary_rows = []

    for ss in sorted(df["score_share_clean_v1"].unique()):
        sdf = df[df["score_share_clean_v1"] == ss]

        for env in ENV_ORDER:
            x = sdf[sdf["environment_band_v1"] == env]
            runners = len(x)
            wins = int(x["environment_win_v1"].sum()) if runners else 0

            rows.append({
                "score_share_band": ss,
                "environment_band_v1": env,
                "runners": int(runners),
                "wins": wins,
                "win_pct": round(wins / runners * 100, 2) if runners else 0,
            })

        weak = sdf[sdf["environment_band_v1"].isin(["POOR", "NEGATIVE"])]
        strong = sdf[sdf["environment_band_v1"].isin(["POSITIVE", "ELITE"])]

        weak_win = weak["environment_win_v1"].mean() * 100 if len(weak) else 0
        strong_win = strong["environment_win_v1"].mean() * 100 if len(strong) else 0

        summary_rows.append({
            "score_share_band": ss,
            "runners": int(len(sdf)),
            "weak_runners": int(len(weak)),
            "weak_win_pct": round(weak_win, 2),
            "neutral_runners": int((sdf["environment_band_v1"] == "NEUTRAL").sum()),
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

    verdict = "ENVIRONMENT_ADDS_BEYOND_SCORE_SHARE" if total and pass_count == total else "ENVIRONMENT_SCORE_SHARE_INDEPENDENCE_MIXED"

    pd.DataFrame([{
        "verdict": verdict,
        "score_share_groups_tested": total,
        "score_share_groups_passed": pass_count,
        "avg_lift_pts": round(meaningful["lift_pts"].mean(), 2) if total else "",
        "meaning": "Pass means POSITIVE+ beats POOR/NEGATIVE inside each meaningful score-share bucket.",
    }]).to_csv(VERDICT, index=False)

    print("[ENVIRONMENT_SCORE_SHARE_MATRIX_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={VERDICT}")
    print(summary.to_string(index=False))
    print(f"VERDICT={verdict}")

if __name__ == "__main__":
    main()
