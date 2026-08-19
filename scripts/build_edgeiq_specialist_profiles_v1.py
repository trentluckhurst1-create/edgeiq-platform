from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_dna_registry_v2.csv"
OUT = DATA / "edgeiq_specialist_profiles_v1.csv"
SUMMARY = DATA / "edgeiq_specialist_profiles_v1_summary.csv"

df = pd.read_csv(SRC, low_memory=False)

df["dna_score"] = pd.to_numeric(df["dna_score"], errors="coerce")
df["starts"] = pd.to_numeric(df["starts"], errors="coerce").fillna(0)
df["wins"] = pd.to_numeric(df["wins"], errors="coerce").fillna(0)
df["places"] = pd.to_numeric(df["places"], errors="coerce").fillna(0)

df["dna_band_clean"] = df["dna_band"].astype(str).str.upper().str.strip()

supported = df[
    df["dna_score"].notna() &
    (df["dna_band_clean"] != "LOW_SAMPLE")
].copy()

def readable_specialist(row):
    dna_type = str(row.get("dna_type", "")).strip()
    key = str(row.get("profile_key", "")).strip()

    if dna_type == "TRACK_DNA":
        return f"{key} SPECIALIST"

    if dna_type == "RAIL_DNA":
        return f"{key} SPECIALIST"

    if dna_type == "PREP_DNA":
        return f"{key} SPECIALIST"

    if dna_type == "MARKET_DNA":
        return f"MARKET {key} SPECIALIST"

    if dna_type == "TDC_DNA":
        return f"{key} SPECIALIST"

    return f"{dna_type} {key} SPECIALIST"

def specialist_type(row):
    dna_type = str(row.get("dna_type", "")).strip()
    key = str(row.get("profile_key", "")).upper().strip()

    if dna_type == "TRACK_DNA":
        return "TRACK_SPECIALIST"

    if dna_type == "RAIL_DNA":
        return "RAIL_SPECIALIST"

    if dna_type == "PREP_DNA":
        if "FIRST_UP" in key:
            return "FIRST_UP_SPECIALIST"
        if "SECOND_UP" in key:
            return "SECOND_UP_SPECIALIST"
        if "THIRD_UP" in key:
            return "THIRD_UP_SPECIALIST"
        return "PREP_SPECIALIST"

    if dna_type == "MARKET_DNA":
        if "FAV" in key:
            return "FAVOURITE_SPECIALIST"
        if "15" in key or "VALUE" in key:
            return "VALUE_SPECIALIST"
        return "MARKET_SPECIALIST"

    if dna_type == "TDC_DNA":
        if "SOFT" in key:
            return "SOFT_TRACK_SPECIALIST"
        if "HEAVY" in key:
            return "HEAVY_TRACK_SPECIALIST"
        if "STAYING" in key:
            return "STAYING_SPECIALIST"
        if "SPRINT" in key:
            return "SPRINT_SPECIALIST"
        if "MILE" in key:
            return "MILE_SPECIALIST"
        return "TRACK_DISTANCE_CONDITION_SPECIALIST"

    return "SPECIALIST"

def band(score):
    if score >= 100:
        return "ELITE_SPECIALIST"
    if score >= 60:
        return "STRONG_SPECIALIST"
    if score >= 30:
        return "POSITIVE_SPECIALIST"
    return "GENERALIST"

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for (entity_type, entity_name), g in supported.groupby(["entity_type", "entity_name"], dropna=False):
    g = g.sort_values(["dna_score", "starts"], ascending=[False, False])

    elite_count = int((g["dna_band_clean"] == "ELITE").sum())
    strong_count = int((g["dna_band_clean"] == "STRONG").sum())
    positive_count = int((g["dna_band_clean"] == "POSITIVE").sum())

    specialist_rating = elite_count * 5 + strong_count * 3 + positive_count

    top = g.head(5).copy()
    spec_names = [readable_specialist(r) for _, r in top.iterrows()]
    spec_types = [specialist_type(r) for _, r in top.iterrows()]
    scores = [round(float(r["dna_score"]), 1) for _, r in top.iterrows()]
    starts = [int(float(r["starts"])) for _, r in top.iterrows()]

    while len(spec_names) < 5:
        spec_names.append("")
        spec_types.append("")
        scores.append("")
        starts.append("")

    best = top.iloc[0] if len(top) else None

    rows.append({
        "built_at": built_at,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "specialist_rating": specialist_rating,
        "specialist_band": band(specialist_rating),
        "elite_profile_count": elite_count,
        "strong_profile_count": strong_count,
        "positive_profile_count": positive_count,
        "supported_profile_count": len(g),
        "best_dna_type": best["dna_type"] if best is not None else "",
        "best_profile_key": best["profile_key"] if best is not None else "",
        "best_score": round(float(best["dna_score"]), 2) if best is not None else "",
        "specialist_1": spec_names[0],
        "specialist_1_type": spec_types[0],
        "specialist_1_score": scores[0],
        "specialist_1_starts": starts[0],
        "specialist_2": spec_names[1],
        "specialist_2_type": spec_types[1],
        "specialist_2_score": scores[1],
        "specialist_2_starts": starts[1],
        "specialist_3": spec_names[2],
        "specialist_3_type": spec_types[2],
        "specialist_3_score": scores[2],
        "specialist_3_starts": starts[2],
        "specialist_4": spec_names[3],
        "specialist_4_type": spec_types[3],
        "specialist_4_score": scores[3],
        "specialist_4_starts": starts[3],
        "specialist_5": spec_names[4],
        "specialist_5_type": spec_types[4],
        "specialist_5_score": scores[4],
        "specialist_5_starts": starts[4],
    })

out = pd.DataFrame(rows)

out = out.sort_values(["specialist_rating", "best_score", "supported_profile_count"], ascending=[False, False, False])

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "EDGEIQ_SPECIALIST_PROFILES_V1_BUILT"],
    ["source", str(SRC)],
    ["rows", len(out)],
    ["elite_specialists", int((out["specialist_band"] == "ELITE_SPECIALIST").sum())],
    ["strong_specialists", int((out["specialist_band"] == "STRONG_SPECIALIST").sum())],
    ["positive_specialists", int((out["specialist_band"] == "POSITIVE_SPECIALIST").sum())],
    ["output", str(OUT)],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[SPECIALIST_PROFILES_V1] COMPLETE")
print(f"rows={len(out)}")
print(f"output={OUT}")
