import csv
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_narrative_engine_v1.csv"

OUT = DATA / "edgeiq_race_understanding_engine_v1.csv"
SUMMARY = DATA / "edgeiq_race_understanding_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

races = defaultdict(list)

for r in rows:
    race_key = "|".join([
        clean(r.get("race_date")),
        clean(r.get("track")),
        clean(r.get("race_no")),
    ])
    races[race_key].append(r)

out_rows = []

for race_key, rr in races.items():
    race_date, track, race_no = race_key.split("|")

    factor_counter = Counter()
    caution_counter = Counter()

    runners_with_context = 0
    runners_with_caution = 0

    for r in rr:
        factors = [
            clean(r.get("context_1_factor")),
            clean(r.get("context_2_factor")),
            clean(r.get("context_3_factor")),
        ]

        cautions = [
            clean(r.get("caution_factor")),
        ]

        factors = [x for x in factors if x]
        cautions = [x for x in cautions if x]

        if factors:
            runners_with_context += 1

        if cautions:
            runners_with_caution += 1

        for f in factors:
            factor_counter[f] += 1

        for c in cautions:
            caution_counter[c] += 1

    top_factors = factor_counter.most_common(5)
    top_cautions = caution_counter.most_common(3)

    if runners_with_context >= 5:
        race_view = "This race contains multiple runners with relevant historical context signals."
    elif runners_with_context >= 2:
        race_view = "This race contains some relevant historical context signals."
    elif runners_with_context == 1:
        race_view = "This race contains limited historical context support."
    else:
        race_view = "No strong historical context pattern was identified across this race."

    if runners_with_caution >= 3:
        caution_view = "Caution signals are present across several runners."
    elif runners_with_caution >= 1:
        caution_view = "At least one caution signal is present."
    else:
        caution_view = "No major caution cluster was detected."

    if top_factors:
        factor_view = "Key recurring themes: " + ", ".join([x[0] for x in top_factors[:3]]) + "."
    else:
        factor_view = "No recurring positive context theme was detected."

    out_rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "runner_count": len(rr),
        "runners_with_context": runners_with_context,
        "runners_with_caution": runners_with_caution,
        "top_context_1": top_factors[0][0] if len(top_factors) > 0 else "",
        "top_context_1_count": top_factors[0][1] if len(top_factors) > 0 else 0,
        "top_context_2": top_factors[1][0] if len(top_factors) > 1 else "",
        "top_context_2_count": top_factors[1][1] if len(top_factors) > 1 else 0,
        "top_context_3": top_factors[2][0] if len(top_factors) > 2 else "",
        "top_context_3_count": top_factors[2][1] if len(top_factors) > 2 else 0,
        "top_caution_1": top_cautions[0][0] if len(top_cautions) > 0 else "",
        "top_caution_1_count": top_cautions[0][1] if len(top_cautions) > 0 else 0,
        "edgeiq_race_view": race_view,
        "edgeiq_factor_view": factor_view,
        "edgeiq_caution_view": caution_view,
        "built_at": datetime.now().isoformat(),
    })

out_rows.sort(
    key=lambda r: (
        r["track"],
        int(r["race_no"]) if str(r["race_no"]).isdigit() else 999,
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"race_rows","value":len(out_rows)},
    {"metric":"races_with_context","value":sum(1 for r in out_rows if int(r["runners_with_context"]) > 0)},
    {"metric":"races_with_cautions","value":sum(1 for r in out_rows if int(r["runners_with_caution"]) > 0)},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_RACE_UNDERSTANDING_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
