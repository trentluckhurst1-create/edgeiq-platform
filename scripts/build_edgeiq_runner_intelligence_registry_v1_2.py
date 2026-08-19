from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_intelligence_registry_v1_1.csv"
JOCKEY_XWALK = DATA / "edgeiq_jockey_crosswalk_master_v1.csv"
COMPOSITE = DATA / "edgeiq_composite_dna_v2_1.csv"
BADGES = DATA / "edgeiq_profile_badges_v1.csv"

OUT = DATA / "edgeiq_runner_intelligence_registry_v1_2.csv"
SUMMARY = DATA / "edgeiq_runner_intelligence_registry_v1_2_summary.csv"

def nkey(s):
    return s.astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True).str.strip()

df = pd.read_csv(SRC, low_memory=False)
xwalk = pd.read_csv(JOCKEY_XWALK, low_memory=False)
comp = pd.read_csv(COMPOSITE, low_memory=False)
badges = pd.read_csv(BADGES, low_memory=False)

for d in [df, xwalk, comp, badges]:
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].astype(str).str.strip()

xwalk["live_jockey_key"] = nkey(xwalk["live_jockey"])
xwalk["warehouse_jockey_key"] = nkey(xwalk["warehouse_jockey"])

df["jockey_live_key"] = nkey(df["jockey"])

df = df.merge(
    xwalk[["live_jockey_key", "warehouse_jockey", "warehouse_jockey_key", "match_status", "match_score"]],
    left_on="jockey_live_key",
    right_on="live_jockey_key",
    how="left"
)

df["jockey_profile_name"] = df["warehouse_jockey"].where(
    df["warehouse_jockey"].astype(str).str.strip() != "",
    df["jockey"]
)

df["jockey_profile_key"] = nkey(df["jockey_profile_name"])

comp["entity_key_profile"] = nkey(comp["entity_name"])
badges["entity_key_profile"] = nkey(badges["entity_name"])

j_comp = comp[comp["entity_type"].astype(str).str.upper() == "JOCKEY"].copy()
j_badges = badges[badges["entity_type"].astype(str).str.upper() == "JOCKEY"].copy()

j_comp = j_comp[[
    "entity_key_profile",
    "composite_v2_score",
    "composite_v2_1_band",
    "specialist_rating",
    "specialist_band",
    "summary_score",
    "summary_band",
]].drop_duplicates("entity_key_profile")

j_comp = j_comp.rename(columns={
    "entity_key_profile": "jockey_profile_key",
    "composite_v2_score": "jockey_composite_score_xwalk",
    "composite_v2_1_band": "jockey_composite_band_xwalk",
    "specialist_rating": "jockey_specialist_rating_xwalk",
    "specialist_band": "jockey_specialist_band_xwalk",
    "summary_score": "jockey_summary_score_xwalk",
    "summary_band": "jockey_summary_band_xwalk",
})

j_badges = j_badges[[
    "entity_key_profile",
    "badge_1",
    "badge_2",
    "badge_3",
    "badge_score",
]].drop_duplicates("entity_key_profile")

j_badges = j_badges.rename(columns={
    "entity_key_profile": "jockey_profile_key",
    "badge_1": "jockey_badge_1_xwalk",
    "badge_2": "jockey_badge_2_xwalk",
    "badge_3": "jockey_badge_3_xwalk",
    "badge_score": "jockey_badge_score_xwalk",
})

df = df.merge(j_comp, on="jockey_profile_key", how="left")
df = df.merge(j_badges, on="jockey_profile_key", how="left")

for old, new in [
    ("jockey_composite_score_xwalk", "jockey_composite_score"),
    ("jockey_composite_band_xwalk", "jockey_composite_band"),
    ("jockey_specialist_rating_xwalk", "jockey_specialist_rating"),
    ("jockey_specialist_band_xwalk", "jockey_specialist_band"),
    ("jockey_summary_score_xwalk", "jockey_summary_score"),
    ("jockey_summary_band_xwalk", "jockey_summary_band"),
    ("jockey_badge_1_xwalk", "jockey_badge_1"),
    ("jockey_badge_2_xwalk", "jockey_badge_2"),
    ("jockey_badge_3_xwalk", "jockey_badge_3"),
    ("jockey_badge_score_xwalk", "jockey_badge_score"),
]:
    if old in df.columns:
        df[new] = df[old].where(df[old].astype(str).str.strip() != "", df.get(new, ""))

for c in ["horse_composite_score", "trainer_composite_score", "jockey_composite_score", "connection_composite_score"]:
    if c not in df.columns:
        df[c] = 0
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["profile_intelligence_score"] = (
    df["horse_composite_score"] * 0.15 +
    df["trainer_composite_score"] * 0.25 +
    df["jockey_composite_score"] * 0.25 +
    df["connection_composite_score"] * 0.35
).round(2)

def band(x):
    if x >= 60:
        return "ELITE_PROFILE_EDGE"
    if x >= 45:
        return "STRONG_PROFILE_EDGE"
    if x >= 30:
        return "POSITIVE_PROFILE_EDGE"
    if x > 0:
        return "LIGHT_PROFILE_EDGE"
    return "NO_PROFILE"

df["profile_intelligence_band"] = df["profile_intelligence_score"].apply(band)

badge_cols = [
    "horse_badge_1","horse_badge_2","horse_badge_3",
    "trainer_badge_1","trainer_badge_2","trainer_badge_3",
    "jockey_badge_1","jockey_badge_2","jockey_badge_3",
    "connection_badge_1","connection_badge_2","connection_badge_3",
]

for c in badge_cols:
    if c not in df.columns:
        df[c] = ""

def badge_summary(row):
    vals, seen = [], set()
    for c in badge_cols:
        v = str(row.get(c, "")).strip()
        if not v or v.lower() == "nan":
            continue
        if v not in seen:
            vals.append(v)
            seen.add(v)
    return " | ".join(vals[:5])

df["profile_badge_summary"] = df.apply(badge_summary, axis=1)

df["built_at_v1_2"] = datetime.now(timezone.utc).isoformat()

preferred = [
    "built_at_v1_2","race_date","track","race_no","horse","trainer","jockey",
    "jockey_profile_name","match_status","match_score","connection_name",
    "dna_v6_2_score","dna_v6_2_band",
    "profile_intelligence_score","profile_intelligence_band","profile_badge_summary",
    "horse_composite_score","horse_composite_band",
    "trainer_composite_score","trainer_composite_band",
    "jockey_composite_score","jockey_composite_band",
    "connection_composite_score","connection_composite_band",
    "jockey_badge_1","jockey_badge_2","jockey_badge_3",
]

cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
df[cols].to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status","EDGEIQ_RUNNER_INTELLIGENCE_REGISTRY_V1_2_BUILT"],
    ["rows",len(df)],
    ["with_jockey_crosswalk",int((df["warehouse_jockey"].astype(str).str.strip()!="").sum())],
    ["with_horse_profile",int((df["horse_composite_score"]>0).sum())],
    ["with_trainer_profile",int((df["trainer_composite_score"]>0).sum())],
    ["with_jockey_profile",int((df["jockey_composite_score"]>0).sum())],
    ["with_connection_profile",int((df["connection_composite_score"]>0).sum())],
    ["elite_profile_edge",int((df["profile_intelligence_band"]=="ELITE_PROFILE_EDGE").sum())],
    ["strong_profile_edge",int((df["profile_intelligence_band"]=="STRONG_PROFILE_EDGE").sum())],
    ["positive_profile_edge",int((df["profile_intelligence_band"]=="POSITIVE_PROFILE_EDGE").sum())],
    ["output",str(OUT)],
    ["built_at",datetime.now(timezone.utc).isoformat()],
], columns=["metric","value"])

summary.to_csv(SUMMARY,index=False)

print("[RUNNER_INTELLIGENCE_REGISTRY_V1_2] COMPLETE")
print(f"rows={len(df)}")
print(f"output={OUT}")
