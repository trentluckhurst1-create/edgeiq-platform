from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DETAIL = DATA / "edgeiq_runner_dna_weight_ladder_v1_detail.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"

OUT = DATA / "edgeiq_runner_dna_v6_3_safe_improvement_breakdown_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_3_safe_improvement_breakdown_v1_summary.csv"

VERSION = "MEDIUM"

detail = pd.read_csv(DETAIL, dtype=str).fillna("")
races = pd.read_csv(BY_RACE, dtype=str).fillna("")

built_at = datetime.now(timezone.utc).isoformat()

improved = races[
    (races["version"] == VERSION) &
    (races["top_changed_vs_base"] == "True") &
    (races["base_top_won"] == "0") &
    (races["version_top_won"] == "1")
].copy()

worsened = races[
    (races["version"] == VERSION) &
    (races["top_changed_vs_base"] == "True") &
    (races["base_top_won"] == "1") &
    (races["version_top_won"] == "0")
].copy()

medium = detail[detail["version"] == VERSION].copy()
base = detail[detail["version"] == "BASE"].copy()

medium["score"] = pd.to_numeric(medium["score"], errors="coerce")
base["score"] = pd.to_numeric(base["score"], errors="coerce")

rows = []

for _, r in improved.iterrows():
    race_key = r["race_key"]
    base_top = r["base_top"]
    new_top = r["version_top"]

    b = base[(base["race_key"] == race_key) & (base["horse"] == base_top)]
    n = medium[(medium["race_key"] == race_key) & (medium["horse"] == new_top)]

    if b.empty or n.empty:
        continue

    b = b.iloc[0]
    n = n.iloc[0]

    rows.append({
        "race_key": race_key,
        "meeting_date": r.get("meeting_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "base_top": base_top,
        "new_top": new_top,
        "base_top_score": b["score"],
        "new_top_score": n["score"],
        "score_gap_new_minus_base": round(float(n["score"]) - float(b["score"]), 3),
        "base_top_band": b["band"],
        "new_top_band": n["band"],
        "improvement_type": "BASE_LOST_NEW_WON",
        "built_at": built_at,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "RUNNER_DNA_V6_3_SAFE_IMPROVEMENT_BREAKDOWN_V1_BUILT"],
    ["version", VERSION],
    ["changed_races_improved", len(improved)],
    ["changed_races_worsened", len(worsened)],
    ["net_winner_gain", len(improved) - len(worsened)],
    ["improvement_rows_written", len(out)],
    ["source_detail", DETAIL.name],
    ["source_by_race", BY_RACE.name],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V6_3_SAFE_IMPROVEMENT_BREAKDOWN_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
