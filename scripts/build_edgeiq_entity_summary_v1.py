from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_dna_registry_v2.csv"
OUT = DATA / "edgeiq_entity_summary_v1.csv"
SUMMARY = DATA / "edgeiq_entity_summary_v1_summary.csv"

df = pd.read_csv(SRC, low_memory=False)

df["dna_score"] = pd.to_numeric(df["dna_score"], errors="coerce")
df["starts"] = pd.to_numeric(df["starts"], errors="coerce").fillna(0)
df["wins"] = pd.to_numeric(df["wins"], errors="coerce").fillna(0)
df["places"] = pd.to_numeric(df["places"], errors="coerce").fillna(0)

supported = df[df["dna_band"].astype(str).str.upper() != "LOW_SAMPLE"].copy()

def safe_join(values, n=5):
    vals = [str(v) for v in values if str(v).strip() and str(v).lower() != "nan"]
    return " | ".join(vals[:n])

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for (entity_type, entity_name), g in df.groupby(["entity_type", "entity_name"], dropna=False):
    gs = supported[
        (supported["entity_type"] == entity_type) &
        (supported["entity_name"] == entity_name)
    ]

    source = gs if len(gs) else g

    best = source.sort_values(["dna_score", "starts"], ascending=[False, False]).head(1)
    worst = source.sort_values(["dna_score", "starts"], ascending=[True, False]).head(1)

    rows.append({
        "built_at": built_at,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "profile_count": len(g),
        "supported_profile_count": len(gs),
        "dna_type_count": g["dna_type"].nunique(),
        "total_starts": int(g["starts"].sum()),
        "total_wins": int(g["wins"].sum()),
        "total_places": int(g["places"].sum()),
        "elite_profiles": int((gs["dna_band"].astype(str).str.upper() == "ELITE").sum()),
        "strong_profiles": int((gs["dna_band"].astype(str).str.upper() == "STRONG").sum()),
        "positive_profiles": int((gs["dna_band"].astype(str).str.upper() == "POSITIVE").sum()),
        "neutral_profiles": int((gs["dna_band"].astype(str).str.upper() == "NEUTRAL").sum()),
        "negative_profiles": int((gs["dna_band"].astype(str).str.upper() == "NEGATIVE").sum()),
        "poor_profiles": int((gs["dna_band"].astype(str).str.upper() == "POOR").sum()),
        "avg_supported_score": round(float(gs["dna_score"].mean()), 2) if len(gs) else "",
        "best_dna_type": best["dna_type"].iloc[0] if len(best) else "",
        "best_profile_key": best["profile_key"].iloc[0] if len(best) else "",
        "best_score": round(float(best["dna_score"].iloc[0]), 2) if len(best) else "",
        "best_band": best["dna_band"].iloc[0] if len(best) else "",
        "worst_dna_type": worst["dna_type"].iloc[0] if len(worst) else "",
        "worst_profile_key": worst["profile_key"].iloc[0] if len(worst) else "",
        "worst_score": round(float(worst["dna_score"].iloc[0]), 2) if len(worst) else "",
        "worst_band": worst["dna_band"].iloc[0] if len(worst) else "",
        "top_elite_profiles": safe_join(
            gs[gs["dna_band"].astype(str).str.upper() == "ELITE"]
            .sort_values(["dna_score", "starts"], ascending=[False, False])
            .apply(lambda r: f"{r['dna_type']}={r['profile_key']} ({round(float(r['dna_score']),1)})", axis=1)
            .tolist(),
            5
        ),
    })

out = pd.DataFrame(rows)

out["summary_score"] = (
    out["elite_profiles"] * 8 +
    out["strong_profiles"] * 5 +
    out["positive_profiles"] * 3 +
    out["neutral_profiles"] * 1 -
    out["negative_profiles"] * 2 -
    out["poor_profiles"] * 4
)

def summary_band(row):
    if row["supported_profile_count"] < 1:
        return "LOW_SIGNAL"
    score = row["summary_score"]
    if score >= 80:
        return "ELITE_PROFILE"
    if score >= 40:
        return "STRONG_PROFILE"
    if score >= 15:
        return "POSITIVE_PROFILE"
    if score >= 0:
        return "MIXED_PROFILE"
    return "NEGATIVE_PROFILE"

out["summary_band"] = out.apply(summary_band, axis=1)

out = out.sort_values(["summary_score", "supported_profile_count"], ascending=[False, False])

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "EDGEIQ_ENTITY_SUMMARY_V1_BUILT"],
    ["source", str(SRC)],
    ["rows", len(out)],
    ["elite_profiles", int((out["summary_band"] == "ELITE_PROFILE").sum())],
    ["strong_profiles", int((out["summary_band"] == "STRONG_PROFILE").sum())],
    ["positive_profiles", int((out["summary_band"] == "POSITIVE_PROFILE").sum())],
    ["output", str(OUT)],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[ENTITY_SUMMARY_V1] COMPLETE")
print(f"rows={len(out)}")
print(f"output={OUT}")
