from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_specialist_profiles_v1.csv"
OUT = DATA / "edgeiq_profile_badges_v1.csv"
SUMMARY = DATA / "edgeiq_profile_badges_v1_summary.csv"

df = pd.read_csv(SRC, low_memory=False)

def clean(v):
    return "" if pd.isna(v) else str(v).strip()

def badge_from_profile(dna_type, profile_key, spec_type):
    key = clean(profile_key).upper()
    typ = clean(spec_type).upper()
    dna = clean(dna_type).upper()

    if "FIRST_UP" in key or "FIRST_UP" in typ:
        return "FIRST-UP SPECIALIST"

    if "SECOND_UP" in key or "SECOND_UP" in typ:
        return "SECOND-UP SPECIALIST"

    if "THIRD_UP" in key or "THIRD_UP" in typ:
        return "THIRD-UP SPECIALIST"

    if "FOURTH_PLUS" in key:
        return "DEEP PREP SPECIALIST"

    if "HEAVY" in key or "HEAVY" in typ:
        return "HEAVY TRACK SPECIALIST"

    if "SOFT" in key or "SOFT" in typ:
        return "SOFT TRACK SPECIALIST"

    if "GOOD" in key:
        return "GOOD TRACK SPECIALIST"

    if "FAV" in key or "FAVOURITE" in typ:
        return "FAVOURITE SPECIALIST"

    if "15+" in key or "VALUE" in typ:
        return "VALUE HUNTER"

    if "RAIL_OUT" in key or "RAIL" in typ:
        return "RAIL POSITION SPECIALIST"

    if dna == "TRACK_DNA":
        track = key.replace("-", " ").replace("_", " ").strip()
        return f"{track} SPECIALIST"

    if dna == "TDC_DNA":
        parts = [p for p in re.split(r"[|]", key) if p]
        if parts:
            return f"{parts[0]} CONTEXT SPECIALIST"
        return "TRACK-DISTANCE SPECIALIST"

    if dna == "MARKET_DNA":
        return "MARKET SPECIALIST"

    if dna == "PREP_DNA":
        return "PREPARATION SPECIALIST"

    return "SPECIALIST PROFILE"

def dedupe_keep_order(items):
    out = []
    seen = set()
    for item in items:
        item = clean(item)
        if not item:
            continue
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for _, r in df.iterrows():
    badge_candidates = []

    for i in range(1, 6):
        spec = clean(r.get(f"specialist_{i}", ""))
        spec_type = clean(r.get(f"specialist_{i}_type", ""))
        score = clean(r.get(f"specialist_{i}_score", ""))

        dna_type = clean(r.get("best_dna_type", "")) if i == 1 else ""
        profile_key = clean(r.get("best_profile_key", "")) if i == 1 else spec

        badge = badge_from_profile(dna_type, profile_key, spec_type)

        if badge:
            badge_candidates.append(badge)

    badges = dedupe_keep_order(badge_candidates)

    while len(badges) < 3:
        badges.append("")

    rows.append({
        "built_at": built_at,
        "entity_type": clean(r.get("entity_type")),
        "entity_name": clean(r.get("entity_name")),
        "specialist_rating": clean(r.get("specialist_rating")),
        "specialist_band": clean(r.get("specialist_band")),
        "badge_1": badges[0],
        "badge_2": badges[1],
        "badge_3": badges[2],
        "badge_score": clean(r.get("specialist_rating")),
        "best_dna_type": clean(r.get("best_dna_type")),
        "best_profile_key": clean(r.get("best_profile_key")),
        "best_score": clean(r.get("best_score")),
        "elite_profile_count": clean(r.get("elite_profile_count")),
        "strong_profile_count": clean(r.get("strong_profile_count")),
        "positive_profile_count": clean(r.get("positive_profile_count")),
        "supported_profile_count": clean(r.get("supported_profile_count")),
    })

out = pd.DataFrame(rows)

out = out.sort_values(
    ["specialist_rating", "best_score"],
    ascending=[False, False],
    key=lambda s: pd.to_numeric(s, errors="coerce").fillna(0)
)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "EDGEIQ_PROFILE_BADGES_V1_BUILT"],
    ["source", str(SRC)],
    ["rows", len(out)],
    ["with_badge_1", int((out["badge_1"] != "").sum())],
    ["with_badge_2", int((out["badge_2"] != "").sum())],
    ["with_badge_3", int((out["badge_3"] != "").sum())],
    ["output", str(OUT)],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[PROFILE_BADGES_V1] COMPLETE")
print(f"rows={len(out)}")
print(f"output={OUT}")
