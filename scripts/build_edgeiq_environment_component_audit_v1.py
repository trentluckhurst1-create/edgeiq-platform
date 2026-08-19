import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT = DATA / "edgeiq_environment_component_audit_v1.csv"
SUMMARY = DATA / "edgeiq_environment_component_audit_v1_summary.csv"
VERDICT = DATA / "edgeiq_environment_component_audit_v1_verdict.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "_")

def band(score):
    if score <= -10:
        return "POOR"
    if score <= 4:
        return "NEGATIVE"
    if score <= 24:
        return "NEUTRAL"
    if score <= 44:
        return "POSITIVE"
    return "ELITE"

def score_component(df, components):
    score = pd.Series(0, index=df.index, dtype="float64")

    if "TRUST" in components:
        trust = df["trust_profile_v1"].map(clean)
        score += trust.eq("ELITE") * 20
        score += trust.eq("STRONG") * 10

    if "FIELD_SIZE" in components:
        fs = pd.to_numeric(df["field_size"], errors="coerce")
        score += fs.le(7) * 15
        score += fs.between(8, 10, inclusive="both") * 5

    if "LONE_LEADER" in components and "lone_leader_bool" in df.columns:
        lone = df["lone_leader_bool"].map(clean)
        score += lone.isin(["TRUE", "1", "YES", "Y"]) * 20

    if "PACE" in components and "pace_advantage_band_v1" in df.columns:
        pace = df["pace_advantage_band_v1"].map(clean)
        score += pace.eq("ELITE") * 20
        score += pace.eq("POSITIVE") * 10
        score -= pace.eq("POOR") * 10

    if "RACE_STRENGTH" in components and "race_strength_band" in df.columns:
        rs = df["race_strength_band"].map(clean)
        score += rs.eq("ELITE") * 15
        score += rs.isin(["VERY_STRONG", "VSTRONG"]) * 15
        score += rs.eq("STRONG") * 10
        score -= rs.eq("WEAK") * 5

    return score

def summarise(name, components, df):
    score = score_component(df, components)
    temp = df.copy()
    temp["test_score"] = score
    temp["test_band"] = temp["test_score"].map(band)

    weak = temp[temp["test_band"].isin(["POOR", "NEGATIVE"])]
    strong = temp[temp["test_band"].isin(["POSITIVE", "ELITE"])]

    weak_win = weak["environment_win_v1"].mean() * 100 if len(weak) else 0
    strong_win = strong["environment_win_v1"].mean() * 100 if len(strong) else 0
    lift = strong_win - weak_win if len(weak) and len(strong) else 0

    return {
        "test": name,
        "components": "+".join(components),
        "runners": int(len(temp)),
        "weak_runners": int(len(weak)),
        "weak_win_pct": round(weak_win, 2),
        "neutral_runners": int((temp["test_band"] == "NEUTRAL").sum()),
        "strong_runners": int(len(strong)),
        "strong_win_pct": round(strong_win, 2),
        "strong_vs_weak_lift_pts": round(lift, 2),
        "poor_count": int((temp["test_band"] == "POOR").sum()),
        "negative_count": int((temp["test_band"] == "NEGATIVE").sum()),
        "neutral_count": int((temp["test_band"] == "NEUTRAL").sum()),
        "positive_count": int((temp["test_band"] == "POSITIVE").sum()),
        "elite_count": int((temp["test_band"] == "ELITE").sum()),
    }

def main():
    if not SRC.exists():
        raise SystemExit("Run environment replay first.")

    df = pd.read_csv(SRC, low_memory=False)

    required = ["environment_win_v1", "trust_profile_v1", "field_size"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit("Missing required columns: " + ", ".join(missing))

    all_components = ["TRUST", "FIELD_SIZE", "LONE_LEADER", "PACE", "RACE_STRENGTH"]

    tests = []

    tests.append(("FULL_V1", all_components))

    for c in all_components:
        tests.append((f"{c}_ONLY", [c]))

    for c in all_components:
        tests.append((f"REMOVE_{c}", [x for x in all_components if x != c]))

    tests.append(("TRUST_PLUS_PACE", ["TRUST", "PACE"]))
    tests.append(("TRUST_PLUS_FIELD", ["TRUST", "FIELD_SIZE"]))
    tests.append(("PACE_PLUS_LONE", ["PACE", "LONE_LEADER"]))
    tests.append(("ENV_NO_TRUST_NO_FIELD", ["PACE", "LONE_LEADER", "RACE_STRENGTH"]))

    rows = [summarise(name, comps, df) for name, comps in tests]
    out = pd.DataFrame(rows).sort_values("strong_vs_weak_lift_pts", ascending=False)
    out.to_csv(OUT, index=False)

    full = out[out["test"] == "FULL_V1"].iloc[0]
    remove_trust = out[out["test"] == "REMOVE_TRUST"].iloc[0]
    remove_pace = out[out["test"] == "REMOVE_PACE"].iloc[0]
    remove_strength = out[out["test"] == "REMOVE_RACE_STRENGTH"].iloc[0]

    summary = pd.DataFrame([{
        "full_lift_pts": full["strong_vs_weak_lift_pts"],
        "remove_trust_lift_pts": remove_trust["strong_vs_weak_lift_pts"],
        "trust_dependency_pts": round(full["strong_vs_weak_lift_pts"] - remove_trust["strong_vs_weak_lift_pts"], 2),
        "remove_pace_lift_pts": remove_pace["strong_vs_weak_lift_pts"],
        "pace_dependency_pts": round(full["strong_vs_weak_lift_pts"] - remove_pace["strong_vs_weak_lift_pts"], 2),
        "remove_race_strength_lift_pts": remove_strength["strong_vs_weak_lift_pts"],
        "race_strength_dependency_pts": round(full["strong_vs_weak_lift_pts"] - remove_strength["strong_vs_weak_lift_pts"], 2),
    }])
    summary.to_csv(SUMMARY, index=False)

    verdict = "MULTI_SIGNAL_ENVIRONMENT"
    if remove_trust["strong_vs_weak_lift_pts"] < 3:
        verdict = "TRUST_CARRYING_ENVIRONMENT"
    elif full["strong_vs_weak_lift_pts"] - remove_trust["strong_vs_weak_lift_pts"] > 6:
        verdict = "TRUST_DOMINANT_BUT_NOT_SOLE_SIGNAL"

    pd.DataFrame([{
        "verdict": verdict,
        "meaning": "Tests whether Environment V1 is a true multi-signal engine or mostly Trust repackaged.",
        "next_step": "Run stability audit by year and trust/environment matrix.",
    }]).to_csv(VERDICT, index=False)

    print("[ENVIRONMENT_COMPONENT_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={VERDICT}")
    print(summary.to_string(index=False))
    print("")
    print(out.to_string(index=False))

if __name__ == "__main__":
    main()
