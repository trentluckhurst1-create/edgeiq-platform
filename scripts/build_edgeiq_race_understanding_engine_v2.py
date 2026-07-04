import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BRIEF = DATA / "edgeiq_race_briefing_engine_v2.csv"
FACTORS = DATA / "edgeiq_factor_selection_engine_v2_1_separation.csv"
STABLE = DATA / "edgeiq_stable_intent_engine_v1_1_rebalance.csv"

OUT = DATA / "edgeiq_race_understanding_engine_v2.csv"
SUMMARY = DATA / "edgeiq_race_understanding_engine_v2_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

print("[RACE_UNDERSTANDING_ENGINE_V2] loading inputs...")
brief = pd.read_csv(BRIEF, low_memory=False)
factors = pd.read_csv(FACTORS, low_memory=False)
stable = pd.read_csv(STABLE, low_memory=False)

brief["race_no"] = brief["race_no"].astype(str)
factors["race_no"] = factors["race_no"].astype(str)
stable["race_no"] = stable["race_no"].astype(str)
stable["race_date"] = stable["race_date"].astype(str).str[:10]

rows = []

for _, r in brief.iterrows():
    race_date = clean(r["race_date"])
    track = clean(r["track"])
    race_no = clean(r["race_no"])

    rs = stable[
        (stable["race_date"] == race_date) &
        (stable["track"].astype(str) == track) &
        (stable["race_no"].astype(str) == race_no)
    ].copy()

    watch = rs[rs["stable_intent_v1_1_band"] == "WATCH"].copy()
    caution = rs[rs["stable_intent_v1_1_band"] == "CAUTION"].copy()

    watch_top = ", ".join(watch.sort_values("stable_intent_v1_1_score", ascending=False)["horse"].astype(str).head(5).tolist())
    caution_top = ", ".join(caution["horse"].astype(str).head(5).tolist())

    separators = []
    for n in [1, 2, 3]:
        val = clean(r.get(f"what_matters_{n}", ""))
        direction = clean(r.get(f"what_matters_{n}_direction", ""))
        if val:
            separators.append(f"{val} ({direction})")

    if not separators:
        separators_text = "No dominant separator has emerged."
    else:
        separators_text = "; ".join(separators)

    race_setup = clean(r.get("what_matters"))
    if not race_setup:
        race_setup = "This race has no clear dominant setup from the current context library."

    helped = clean(r.get("what_helps"))
    hurt = clean(r.get("what_hurts"))

    if not helped:
        helped = "No clear helped group identified."
    if not hurt:
        hurt = "No clear hurt group identified."

    if watch_top and caution_top:
        summary = f"This race has both intent watch runners ({watch_top}) and caution runners ({caution_top}). The main separators are {separators_text}."
    elif watch_top:
        summary = f"This race is mainly an intent-watch race. Key runners to inspect: {watch_top}. Main separators: {separators_text}."
    elif caution_top:
        summary = f"This race is mainly a caution-profile race. Main caution runners: {caution_top}. Main separators: {separators_text}."
    else:
        summary = f"This race has limited intent separation. Main separators: {separators_text}."

    rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "runner_count": r.get("runner_count", ""),
        "race_setup": race_setup,
        "key_separators": separators_text,
        "runners_helped": helped,
        "runners_hurt": hurt,
        "intent_watch_runners": watch_top,
        "intent_caution_runners": caution_top,
        "customer_summary": summary,
        "source_briefing": clean(r.get("edgeiq_race_briefing")),
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

out = pd.DataFrame(rows).sort_values(["race_date", "track", "race_no"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RACE_UNDERSTANDING_ENGINE_V2_BUILT",
    "race_rows": len(out),
    "races_with_watch": int((out["intent_watch_runners"] != "").sum()),
    "races_with_caution": int((out["intent_caution_runners"] != "").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[RACE_UNDERSTANDING_ENGINE_V2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
