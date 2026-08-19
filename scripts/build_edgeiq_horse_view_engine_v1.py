import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_horse_context_research_v1.csv"
OUT = DATA / "edgeiq_horse_view_engine_v1.csv"
SUMMARY = DATA / "edgeiq_horse_view_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def phrase_context(context_type, context_value):
    ctype = clean(context_type).upper()
    cval = clean(context_value)

    if ctype == "TRACK":
        return f"at {cval}"
    if ctype == "DISTANCE":
        mapping = {
            "SPRINT_SHORT": "short sprint races",
            "SPRINT": "sprint races",
            "SPRINT_MILE": "sprint-to-mile races",
            "MILE_MIDDLE": "mile-to-middle-distance races",
            "STAYING": "staying races",
            "LONG_STAYING": "long staying races",
        }
        return mapping.get(cval, cval.lower())
    if ctype == "CONDITION":
        return f"on {cval.lower()} tracks"
    if ctype == "CLASS":
        return f"in {cval.lower()} grade"
    if ctype == "SP":
        mapping = {
            "FAVOURITE": "when strongly fancied in the market",
            "WELL_FOUND": "when well found in betting",
            "MID_MARKET": "when in the middle of the market",
            "OUTSIDER": "when starting at longer odds",
        }
        return mapping.get(cval, cval.lower())

    return f"{ctype.lower()} {cval}"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []

for r in rows:
    signal = clean(r.get("signal"))
    if signal == "NEUTRAL":
        continue

    horse = clean(r.get("horse_key"))
    ctype = clean(r.get("context_type"))
    cvalue = clean(r.get("context_value"))
    starts = clean(r.get("starts"))
    win_pct = clean(r.get("win_pct"))
    base_win = clean(r.get("horse_base_win_pct"))
    place_pct = clean(r.get("place_pct"))
    base_place = clean(r.get("horse_base_place_pct"))

    context_phrase = phrase_context(ctype, cvalue)

    if signal == "POSITIVE_PROFILE":
        factor_label = f"Positive {ctype.title()} Profile"
        view_headline = f"Historically performs above baseline {context_phrase}."
        view_detail = f"Across {starts} relevant starts, the horse has produced a {win_pct}% win rate versus its overall {base_win}% baseline."
        customer_tone = "POSITIVE"
    elif signal == "CAUTION_PROFILE":
        factor_label = f"Caution {ctype.title()} Profile"
        view_headline = f"Historically performs below baseline {context_phrase}."
        view_detail = f"Across {starts} relevant starts, the horse has produced a {win_pct}% win rate versus its overall {base_win}% baseline."
        customer_tone = "CAUTION"
    else:
        continue

    out_rows.append({
        "entity_type": "HORSE",
        "entity_name": horse,
        "factor_label": factor_label,
        "context_type": ctype,
        "context_value": cvalue,
        "signal": signal,
        "customer_tone": customer_tone,
        "starts": starts,
        "win_pct": win_pct,
        "base_win_pct": base_win,
        "place_pct": place_pct,
        "base_place_pct": base_place,
        "view_headline": view_headline,
        "view_detail": view_detail,
        "edgeiq_factor": factor_label,
        "key_insight": view_headline,
        "built_at": datetime.now().isoformat(),
    })

tone_order = {"POSITIVE": 0, "CAUTION": 1}
out_rows.sort(key=lambda r: (tone_order.get(r["customer_tone"], 9), r["entity_name"], r["context_type"], r["context_value"]))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric": "status", "value": "COMPLETE"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "source_rows", "value": len(rows)},
    {"metric": "view_rows", "value": len(out_rows)},
    {"metric": "positive_rows", "value": sum(1 for r in out_rows if r["customer_tone"] == "POSITIVE")},
    {"metric": "caution_rows", "value": sum(1 for r in out_rows if r["customer_tone"] == "CAUTION")},
    {"metric": "built_at", "value": datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_HORSE_VIEW_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
