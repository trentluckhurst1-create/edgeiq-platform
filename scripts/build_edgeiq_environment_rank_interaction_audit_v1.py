import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT = DATA / "edgeiq_environment_rank_interaction_audit_v1.csv"
SUMMARY = DATA / "edgeiq_environment_rank_interaction_audit_v1_summary.csv"
MATRIX = DATA / "edgeiq_environment_rank_interaction_audit_v1_matrix.csv"
VERDICT = DATA / "edgeiq_environment_rank_interaction_audit_v1_verdict.csv"

ENV_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]

def pct(x):
    return round(float(x) * 100, 2)

def summarise(group_name, group_value, df):
    runners = len(df)
    wins = int(df["environment_win_v1"].sum()) if runners else 0
    return {
        "group": group_name,
        "value": group_value,
        "runners": runners,
        "wins": wins,
        "win_pct": round(wins / runners * 100, 2) if runners else 0,
        "avg_environment_score_v1": round(pd.to_numeric(df["environment_score_v1"], errors="coerce").mean(), 2) if runners else "",
    }

def main():
    if not SRC.exists():
        raise SystemExit("Run build_edgeiq_environment_score_replay_v1.py first.")

    df = pd.read_csv(SRC, low_memory=False)

    required = [
        "environment_band_v1",
        "environment_score_v1",
        "environment_win_v1",
        "trust_profile_v1",
        "field_size_bucket_v1",
        "score_share_band",
        "rank1_dominance_band_v1",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit("Missing required columns: " + ", ".join(missing))

    rows = []

    for band in ENV_ORDER:
        rows.append(summarise("ENVIRONMENT_BAND", band, df[df["environment_band_v1"] == band]))

    for col, label in [
        ("trust_profile_v1", "TRUST_PROFILE"),
        ("field_size_bucket_v1", "FIELD_SIZE_BUCKET"),
        ("score_share_band", "SCORE_SHARE_BAND"),
        ("rank1_dominance_band_v1", "DOMINANCE_BAND"),
    ]:
        for value, x in df.groupby(col, dropna=False):
            rows.append(summarise(label, str(value), x))

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    matrix_rows = []
    for trust, tdf in df.groupby("trust_profile_v1", dropna=False):
        for env in ENV_ORDER:
            x = tdf[tdf["environment_band_v1"] == env]
            matrix_rows.append(summarise("TRUST_X_ENVIRONMENT", f"{trust}__{env}", x))

    matrix = pd.DataFrame(matrix_rows)
    matrix.to_csv(MATRIX, index=False)

    env = out[out["group"] == "ENVIRONMENT_BAND"].copy()
    env = env[env["runners"] > 0]

    poorish = env[env["value"].isin(["POOR", "NEGATIVE"])]
    goodish = env[env["value"].isin(["POSITIVE", "ELITE"])]

    poor_win = poorish["wins"].sum() / poorish["runners"].sum() * 100 if poorish["runners"].sum() else 0
    good_win = goodish["wins"].sum() / goodish["runners"].sum() * 100 if goodish["runners"].sum() else 0
    lift = good_win - poor_win

    verdict = "ENVIRONMENT_EXPLAINS_RANK1_TRUST" if lift >= 7 else "ENVIRONMENT_INTERACTION_WEAK"

    summary = pd.DataFrame([{
        "rows": int(len(df)),
        "poor_negative_runners": int(poorish["runners"].sum()),
        "poor_negative_win_pct": round(poor_win, 2),
        "positive_elite_runners": int(goodish["runners"].sum()),
        "positive_elite_win_pct": round(good_win, 2),
        "positive_elite_lift_pts": round(lift, 2),
        "verdict": verdict,
    }])
    summary.to_csv(SUMMARY, index=False)

    pd.DataFrame([{
        "verdict": verdict,
        "meaning": "Environment is explaining when Rank1 should be trusted.",
        "next_step": "Build Environment V1 component attribution audit to identify which signals drive the lift.",
    }]).to_csv(VERDICT, index=False)

    print("[ENVIRONMENT_RANK_INTERACTION_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={MATRIX}")
    print(f"wrote={VERDICT}")
    print(summary.to_string(index=False))
    print("")
    print(env.to_string(index=False))

if __name__ == "__main__":
    main()
