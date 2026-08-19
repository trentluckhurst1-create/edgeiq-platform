import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACTORS = DATA / "edgeiq_factor_selection_engine_v2_1_separation.csv"
STABLE = DATA / "edgeiq_stable_intent_engine_v1_1_rebalance.csv"

OUT = DATA / "edgeiq_race_briefing_engine_v2.csv"
SUMMARY = DATA / "edgeiq_race_briefing_engine_v2_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

print("[RACE_BRIEFING_ENGINE_V2] loading inputs...")
factors = pd.read_csv(FACTORS, low_memory=False)
stable = pd.read_csv(STABLE, low_memory=False)

factors["race_no"] = factors["race_no"].astype(str)
stable["race_no"] = stable["race_no"].astype(str)

rows = []

for _, r in factors.iterrows():
    race_date = clean(r["race_date"])
    track = clean(r["track"])
    race_no = clean(r["race_no"])

    race_stable = stable[
        (stable["race_date"].astype(str).str[:10] == race_date) &
        (stable["track"].astype(str) == track) &
        (stable["race_no"].astype(str) == race_no)
    ].copy()

    watch = race_stable[race_stable["stable_intent_v1_1_band"] == "WATCH"]
    caution = race_stable[race_stable["stable_intent_v1_1_band"] == "CAUTION"]
    low = race_stable[race_stable["stable_intent_v1_1_band"] == "LOW_EVIDENCE"]

    watch_names = ", ".join(watch["horse"].dropna().astype(str).head(6).tolist())
    caution_names = ", ".join(caution["horse"].dropna().astype(str).head(6).tolist())

    what_matters = clean(r.get("race_factor_view"))
    what_helps = clean(r.get("what_helps"))
    what_hurts = clean(r.get("what_hurts"))

    if not what_helps:
        what_helps = "No clear positive cluster detected."
    if not what_hurts:
        what_hurts = "No clear caution cluster detected."

    what_to_watch = clean(r.get("what_to_watch"))
    if watch_names:
        watch_line = f"Stable intent watch runners: {watch_names}."
    else:
        watch_line = "No strong stable-intent watch cluster detected."

    if caution_names:
        caution_line = f"Stable intent cautions: {caution_names}."
    else:
        caution_line = "No major stable-intent caution cluster detected."

    briefing = (
        f"What matters: {what_matters} "
        f"What helps: {what_helps}. "
        f"What hurts: {what_hurts}. "
        f"What to watch: {watch_line} {caution_line}"
    )

    rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "runner_count": r.get("runner_count", ""),
        "factor_count": r.get("factor_count", ""),
        "what_matters": what_matters,
        "what_helps": what_helps,
        "what_hurts": what_hurts,
        "what_to_watch": what_to_watch,
        "watch_runners": watch_names,
        "caution_runners": caution_names,
        "low_evidence_count": len(low),
        "edgeiq_race_briefing": briefing,
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

out = pd.DataFrame(rows).sort_values(["race_date", "track", "race_no"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RACE_BRIEFING_ENGINE_V2_BUILT",
    "race_rows": len(out),
    "races_with_watch_runners": int((out["watch_runners"] != "").sum()),
    "races_with_caution_runners": int((out["caution_runners"] != "").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[RACE_BRIEFING_ENGINE_V2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
