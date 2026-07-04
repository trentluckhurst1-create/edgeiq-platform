from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SUMMARY_SRC = DATA / "edgeiq_entity_summary_v1.csv"
SPECIALIST_SRC = DATA / "edgeiq_specialist_profiles_v1.csv"
BADGES_SRC = DATA / "edgeiq_profile_badges_v1.csv"

OUT = DATA / "edgeiq_composite_dna_v2.csv"
SUMMARY = DATA / "edgeiq_composite_dna_v2_summary.csv"

entity = pd.read_csv(SUMMARY_SRC, low_memory=False)
spec = pd.read_csv(SPECIALIST_SRC, low_memory=False)
badges = pd.read_csv(BADGES_SRC, low_memory=False)

for df in [entity, spec, badges]:
    df["entity_type"] = df["entity_type"].astype(str).str.strip()
    df["entity_name"] = df["entity_name"].astype(str).str.strip()

keep_entity = [
    "entity_type","entity_name",
    "profile_count","supported_profile_count",
    "elite_profiles","strong_profiles","positive_profiles",
    "summary_score","summary_band",
    "best_dna_type","best_profile_key","best_score","best_band",
    "top_elite_profiles",
]

entity = entity[[c for c in keep_entity if c in entity.columns]]

keep_spec = [
    "entity_type","entity_name",
    "specialist_rating","specialist_band",
    "elite_profile_count","strong_profile_count","positive_profile_count",
    "best_dna_type","best_profile_key","best_score",
    "specialist_1","specialist_1_type","specialist_1_score","specialist_1_starts",
    "specialist_2","specialist_2_type","specialist_2_score","specialist_2_starts",
    "specialist_3","specialist_3_type","specialist_3_score","specialist_3_starts",
]

spec = spec[[c for c in keep_spec if c in spec.columns]]

keep_badges = [
    "entity_type","entity_name",
    "badge_1","badge_2","badge_3","badge_score",
]

badges = badges[[c for c in keep_badges if c in badges.columns]]

df = entity.merge(
    spec,
    on=["entity_type","entity_name"],
    how="left",
    suffixes=("_entity","_specialist")
)

df = df.merge(
    badges,
    on=["entity_type","entity_name"],
    how="left"
)

def num(col):
    return pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)

df["summary_score_num"] = num("summary_score")
df["specialist_rating_num"] = num("specialist_rating")
df["best_score_num"] = num("best_score_specialist") if "best_score_specialist" in df.columns else num("best_score")
df["supported_profile_count_num"] = num("supported_profile_count")
df["elite_profile_count_num"] = num("elite_profile_count")

def scale(series):
    max_v = series.max()
    if max_v <= 0:
        return series * 0
    return (series / max_v * 100).clip(0, 100)

df["summary_component"] = scale(df["summary_score_num"])
df["specialist_component"] = scale(df["specialist_rating_num"])
df["best_score_component"] = df["best_score_num"].clip(0, 100)
df["support_component"] = scale(df["supported_profile_count_num"])
df["elite_component"] = scale(df["elite_profile_count_num"])

df["composite_v2_score"] = (
    df["specialist_component"] * 0.40 +
    df["best_score_component"] * 0.30 +
    df["support_component"] * 0.20 +
    df["elite_component"] * 0.10
).round(2)

def band(x):
    if x >= 85:
        return "ELITE"
    if x >= 72:
        return "STRONG"
    if x >= 60:
        return "POSITIVE"
    if x >= 45:
        return "NEUTRAL"
    if x >= 32:
        return "NEGATIVE"
    return "POOR"

df["composite_v2_band"] = df["composite_v2_score"].apply(band)
df["built_at"] = datetime.now(timezone.utc).isoformat()

preferred = [
    "built_at",
    "entity_type","entity_name",
    "composite_v2_score","composite_v2_band",
    "specialist_rating","specialist_band",
    "summary_score","summary_band",
    "best_score_specialist","best_dna_type_specialist","best_profile_key_specialist",
    "profile_count","supported_profile_count",
    "elite_profiles","strong_profiles","positive_profiles",
    "elite_profile_count","strong_profile_count","positive_profile_count",
    "badge_1","badge_2","badge_3",
    "specialist_1","specialist_1_type","specialist_1_score","specialist_1_starts",
    "specialist_2","specialist_2_type","specialist_2_score","specialist_2_starts",
    "specialist_3","specialist_3_type","specialist_3_score","specialist_3_starts",
]

cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]

out = df[cols].sort_values(
    ["composite_v2_score","supported_profile_count_num"],
    ascending=[False, False]
)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "EDGEIQ_COMPOSITE_DNA_V2_BUILT"],
    ["rows", len(out)],
    ["elite", int((out["composite_v2_band"] == "ELITE").sum())],
    ["strong", int((out["composite_v2_band"] == "STRONG").sum())],
    ["positive", int((out["composite_v2_band"] == "POSITIVE").sum())],
    ["neutral", int((out["composite_v2_band"] == "NEUTRAL").sum())],
    ["negative", int((out["composite_v2_band"] == "NEGATIVE").sum())],
    ["poor", int((out["composite_v2_band"] == "POOR").sum())],
    ["output", str(OUT)],
    ["built_at", datetime.now(timezone.utc).isoformat()],
], columns=["metric","value"])

summary.to_csv(SUMMARY, index=False)

print("[COMPOSITE_DNA_V2] COMPLETE")
print(f"rows={len(out)}")
print(f"output={OUT}")
