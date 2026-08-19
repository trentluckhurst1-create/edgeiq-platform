from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_SRC_CANDIDATES = [
    DATA / "edgeiq_runner_dna_v6_2.csv",
    DATA / "edgeiq_live_runner_dna_v6_2.csv",
]

COMPOSITE = DATA / "edgeiq_composite_dna_v2_1.csv"
BADGES = DATA / "edgeiq_profile_badges_v1.csv"

OUT = DATA / "edgeiq_runner_intelligence_registry_v1.csv"
SUMMARY = DATA / "edgeiq_runner_intelligence_registry_v1_summary.csv"

def pick_existing(paths):
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError("No runner DNA source found")

def clean_series(s):
    return s.astype(str).str.strip()

def norm_series(s):
    return clean_series(s).str.upper()

runner_src = pick_existing(RUNNER_SRC_CANDIDATES)

runners = pd.read_csv(runner_src, low_memory=False)
comp = pd.read_csv(COMPOSITE, low_memory=False)
badges = pd.read_csv(BADGES, low_memory=False)

for df in [runners, comp, badges]:
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()

def ensure_col(df, col):
    if col not in df.columns:
        df[col] = ""
    return df

for c in ["horse", "trainer", "jockey"]:
    ensure_col(runners, c)

runners["horse_key"] = norm_series(runners["horse"])
runners["trainer_key"] = norm_series(runners["trainer"])
runners["jockey_key"] = norm_series(runners["jockey"])
runners["connection_name"] = runners["trainer"].astype(str).str.strip() + " | " + runners["jockey"].astype(str).str.strip()
runners["connection_key"] = norm_series(runners["connection_name"])

comp["entity_key"] = norm_series(comp["entity_name"])
badges["entity_key"] = norm_series(badges["entity_name"])

comp_keep = [
    "entity_type",
    "entity_key",
    "composite_v2_score",
    "composite_v2_band",
    "composite_v2_1_band",
    "specialist_rating",
    "specialist_band",
    "summary_score",
    "summary_band",
]

comp = comp[[c for c in comp_keep if c in comp.columns]].drop_duplicates(["entity_type", "entity_key"])

badge_keep = [
    "entity_type",
    "entity_key",
    "badge_1",
    "badge_2",
    "badge_3",
    "badge_score",
]

badges = badges[[c for c in badge_keep if c in badges.columns]].drop_duplicates(["entity_type", "entity_key"])

def attach(base, entity_type, key_col, prefix):
    c = comp[comp["entity_type"].astype(str).str.upper() == entity_type].copy()
    b = badges[badges["entity_type"].astype(str).str.upper() == entity_type].copy()

    c = c.rename(columns={
        "entity_key": key_col,
        "composite_v2_score": f"{prefix}_composite_score",
        "composite_v2_band": f"{prefix}_composite_band",
        "composite_v2_1_band": f"{prefix}_composite_band_v2_1",
        "specialist_rating": f"{prefix}_specialist_rating",
        "specialist_band": f"{prefix}_specialist_band",
        "summary_score": f"{prefix}_summary_score",
        "summary_band": f"{prefix}_summary_band",
    })

    b = b.rename(columns={
        "entity_key": key_col,
        "badge_1": f"{prefix}_badge_1",
        "badge_2": f"{prefix}_badge_2",
        "badge_3": f"{prefix}_badge_3",
        "badge_score": f"{prefix}_badge_score",
    })

    base = base.merge(c.drop(columns=["entity_type"], errors="ignore"), on=key_col, how="left")
    base = base.merge(b.drop(columns=["entity_type"], errors="ignore"), on=key_col, how="left")
    return base

out = runners.copy()

out = attach(out, "HORSE", "horse_key", "horse")
out = attach(out, "TRAINER", "trainer_key", "trainer")
out = attach(out, "JOCKEY", "jockey_key", "jockey")
out = attach(out, "CONNECTION", "connection_key", "connection")

score_cols = [
    "horse_composite_score",
    "trainer_composite_score",
    "jockey_composite_score",
    "connection_composite_score",
]

for c in score_cols:
    if c not in out.columns:
        out[c] = 0
    out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

out["profile_intelligence_score"] = (
    out["horse_composite_score"] * 0.20 +
    out["trainer_composite_score"] * 0.25 +
    out["jockey_composite_score"] * 0.20 +
    out["connection_composite_score"] * 0.35
).round(2)

def band(x):
    if x >= 70:
        return "ELITE_PROFILE_EDGE"
    if x >= 55:
        return "STRONG_PROFILE_EDGE"
    if x >= 40:
        return "POSITIVE_PROFILE_EDGE"
    if x >= 25:
        return "LIGHT_PROFILE_EDGE"
    if x > 0:
        return "LOW_PROFILE_SIGNAL"
    return "NO_PROFILE"

out["profile_intelligence_band"] = out["profile_intelligence_score"].apply(band)

badge_cols = [
    "horse_badge_1", "horse_badge_2", "horse_badge_3",
    "trainer_badge_1", "trainer_badge_2", "trainer_badge_3",
    "jockey_badge_1", "jockey_badge_2", "jockey_badge_3",
    "connection_badge_1", "connection_badge_2", "connection_badge_3",
]

for c in badge_cols:
    if c not in out.columns:
        out[c] = ""

def top_badges(row):
    vals = []
    seen = set()
    for c in badge_cols:
        v = str(row.get(c, "")).strip()
        if not v or v.lower() == "nan":
            continue
        if v not in seen:
            seen.add(v)
            vals.append(v)
    return " | ".join(vals[:5])

out["profile_badge_summary"] = out.apply(top_badges, axis=1)

out["built_at"] = datetime.now(timezone.utc).isoformat()

preferred = [
    "built_at",
    "race_date","track","race_no","horse","trainer","jockey","connection_name",
    "dna_v6_2_score","dna_v6_2_band",
    "profile_intelligence_score","profile_intelligence_band","profile_badge_summary",
    "horse_composite_score","horse_composite_band_v2_1","horse_badge_1","horse_badge_2","horse_badge_3",
    "trainer_composite_score","trainer_composite_band_v2_1","trainer_badge_1","trainer_badge_2","trainer_badge_3",
    "jockey_composite_score","jockey_composite_band_v2_1","jockey_badge_1","jockey_badge_2","jockey_badge_3",
    "connection_composite_score","connection_composite_band_v2_1","connection_badge_1","connection_badge_2","connection_badge_3",
]

cols = [c for c in preferred if c in out.columns] + [c for c in out.columns if c not in preferred]

out[cols].to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "EDGEIQ_RUNNER_INTELLIGENCE_REGISTRY_V1_BUILT"],
    ["runner_source", str(runner_src)],
    ["rows", len(out)],
    ["with_horse_profile", int((out["horse_composite_score"] > 0).sum())],
    ["with_trainer_profile", int((out["trainer_composite_score"] > 0).sum())],
    ["with_jockey_profile", int((out["jockey_composite_score"] > 0).sum())],
    ["with_connection_profile", int((out["connection_composite_score"] > 0).sum())],
    ["elite_profile_edge", int((out["profile_intelligence_band"] == "ELITE_PROFILE_EDGE").sum())],
    ["strong_profile_edge", int((out["profile_intelligence_band"] == "STRONG_PROFILE_EDGE").sum())],
    ["positive_profile_edge", int((out["profile_intelligence_band"] == "POSITIVE_PROFILE_EDGE").sum())],
    ["output", str(OUT)],
    ["built_at", datetime.now(timezone.utc).isoformat()],
], columns=["metric","value"])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_INTELLIGENCE_REGISTRY_V1] COMPLETE")
print(f"rows={len(out)}")
print(f"output={OUT}")
