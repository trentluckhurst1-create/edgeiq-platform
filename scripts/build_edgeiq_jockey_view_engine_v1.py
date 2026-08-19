import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_jockey_context_research_v1.csv"

OUT = DATA / "edgeiq_jockey_view_engine_v1.csv"
SUMMARY = DATA / "edgeiq_jockey_view_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []

for r in rows:

    signal = clean(r.get("signal"))

    if signal not in ("STRONG_POSITIVE","POSITIVE","NEGATIVE"):
        continue

    jockey = clean(r.get("jockey"))
    context_type = clean(r.get("context_type"))
    context_value = clean(r.get("context_value"))

    starts = clean(r.get("starts"))
    win_pct = clean(r.get("win_pct"))
    place_pct = clean(r.get("place_pct"))
    win_lift = clean(r.get("win_lift_pct"))
    place_lift = clean(r.get("place_lift_pct"))

    if signal == "STRONG_POSITIVE":

        tone = "POSITIVE"

        factor = f"Positive {context_type.title()} Context"

        headline = (
            f"Historically performs well in "
            f"{context_type.lower()} context: {context_value}."
        )

        detail = (
            f"Across {starts} rides, "
            f"win performance improved by {win_lift}% "
            f"and place performance improved by {place_lift}%."
        )

    elif signal == "POSITIVE":

        tone = "POSITIVE"

        factor = f"Positive {context_type.title()} Context"

        headline = (
            f"Historically performs above baseline in "
            f"{context_type.lower()} context: {context_value}."
        )

        detail = (
            f"Across {starts} rides, "
            f"the rider has produced a positive profile."
        )

    else:

        tone = "CAUTION"

        factor = f"Caution {context_type.title()} Context"

        headline = (
            f"Historically performs below baseline in "
            f"{context_type.lower()} context: {context_value}."
        )

        detail = (
            f"Results have historically been weaker "
            f"than the rider's overall profile."
        )

    out_rows.append({
        "entity_type": "JOCKEY",
        "entity_name": jockey,
        "factor_label": factor,
        "context_type": context_type,
        "context_value": context_value,
        "signal": signal,
        "customer_tone": tone,
        "starts": starts,
        "win_pct": win_pct,
        "place_pct": place_pct,
        "win_lift_pct": win_lift,
        "place_lift_pct": place_lift,
        "view_headline": headline,
        "view_detail": detail,
        "key_insight": headline,
        "built_at": datetime.now().isoformat(),
    })

tone_order = {
    "POSITIVE": 0,
    "CAUTION": 1
}

out_rows.sort(
    key=lambda r: (
        tone_order.get(r["customer_tone"],9),
        r["entity_name"]
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"view_rows","value":len(out_rows)},
    {"metric":"positive_rows","value":sum(1 for r in out_rows if r["customer_tone"]=="POSITIVE")},
    {"metric":"caution_rows","value":sum(1 for r in out_rows if r["customer_tone"]=="CAUTION")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_JOCKEY_VIEW_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
