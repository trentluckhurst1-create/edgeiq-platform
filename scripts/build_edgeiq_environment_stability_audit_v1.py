import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT = DATA / "edgeiq_environment_stability_audit_v1.csv"
SUMMARY = DATA / "edgeiq_environment_stability_audit_v1_summary.csv"
VERDICT = DATA / "edgeiq_environment_stability_audit_v1_verdict.csv"

ENV_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]

def get_year(df):
    if "year" in df.columns:
        return pd.to_numeric(df["year"], errors="coerce")
    if "meeting_date" in df.columns:
        return pd.to_datetime(df["meeting_date"], errors="coerce").dt.year
    raise SystemExit("No year or meeting_date column found.")

def summarise(year, band, df):
    runners = len(df)
    wins = int(df["environment_win_v1"].sum()) if runners else 0
    return {
        "year": int(year),
        "environment_band_v1": band,
        "runners": int(runners),
        "wins": wins,
        "win_pct": round(wins / runners * 100, 2) if runners else 0,
    }

def main():
    if not SRC.exists():
        raise SystemExit("Run environment replay first.")

    df = pd.read_csv(SRC, low_memory=False)
    df["audit_year_v1"] = get_year(df)
    df = df[df["audit_year_v1"].notna()].copy()
    df["audit_year_v1"] = df["audit_year_v1"].astype(int)

    rows = []
    summary_rows = []

    for year in sorted(df["audit_year_v1"].unique()):
        ydf = df[df["audit_year_v1"] == year]

        for band in ENV_ORDER:
            rows.append(summarise(year, band, ydf[ydf["environment_band_v1"] == band]))

        weak = ydf[ydf["environment_band_v1"].isin(["POOR", "NEGATIVE"])]
        strong = ydf[ydf["environment_band_v1"].isin(["POSITIVE", "ELITE"])]

        weak_win = weak["environment_win_v1"].mean() * 100 if len(weak) else 0
        strong_win = strong["environment_win_v1"].mean() * 100 if len(strong) else 0

        summary_rows.append({
            "year": int(year),
            "runners": int(len(ydf)),
            "weak_runners": int(len(weak)),
            "weak_win_pct": round(weak_win, 2),
            "neutral_runners": int((ydf["environment_band_v1"] == "NEUTRAL").sum()),
            "strong_runners": int(len(strong)),
            "strong_win_pct": round(strong_win, 2),
            "lift_pts": round(strong_win - weak_win, 2) if len(weak) and len(strong) else 0,
            "passes": bool(len(weak) and len(strong) and strong_win > weak_win),
        })

    out = pd.DataFrame(rows)
    summary = pd.DataFrame(summary_rows)

    out.to_csv(OUT, index=False)
    summary.to_csv(SUMMARY, index=False)

    pass_years = int(summary["passes"].sum())
    total_years = int(len(summary))
    verdict = "ENVIRONMENT_STABLE_BY_YEAR" if total_years and pass_years == total_years else "ENVIRONMENT_YEAR_STABILITY_MIXED"

    pd.DataFrame([{
        "verdict": verdict,
        "years_tested": total_years,
        "years_passed": pass_years,
        "min_lift_pts": round(summary["lift_pts"].min(), 2) if total_years else "",
        "avg_lift_pts": round(summary["lift_pts"].mean(), 2) if total_years else "",
        "meaning": "Pass means POSITIVE+ beats POOR/NEGATIVE in every available year.",
    }]).to_csv(VERDICT, index=False)

    print("[ENVIRONMENT_STABILITY_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={VERDICT}")
    print(summary.to_string(index=False))
    print(f"VERDICT={verdict}")

if __name__ == "__main__":
    main()
