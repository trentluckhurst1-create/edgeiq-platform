import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_context_translation_engine_v1.csv"

OUT = DATA / "edgeiq_narrative_engine_v1.csv"
SUMMARY = DATA / "edgeiq_narrative_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def heading_from_factor(factor):

    factor = clean(factor)

    if factor.startswith("Stable"):
        return "STABLE CONTEXT"

    if factor.startswith("Rider"):
        return "RIDER CONTEXT"

    if factor.startswith("Horse"):
        return "HORSE CONTEXT"

    if factor.startswith("Stable/Rider"):
        return "PARTNERSHIP CONTEXT"

    return "CONTEXT"

rows = []

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []

for r in rows:

    factors = []

    for i in [1,2,3]:

        factor = clean(r.get(f"edgeiq_factor_{i}"))
        reason = clean(r.get(f"edgeiq_factor_{i}_explained"))

        if factor:

            factors.append({
                "heading": heading_from_factor(factor),
                "factor": factor,
                "reason": reason
            })

    caution_factor = clean(r.get("edgeiq_caution_1"))
    caution_reason = clean(r.get("edgeiq_caution_1_explained"))

    if len(factors) >= 3:

        edgeiq_view = (
            "Several historical contexts align with today's setup. "
            "The stable, rider or horse profiles have previously "
            "performed above baseline under similar circumstances."
        )

    elif len(factors) == 2:

        edgeiq_view = (
            "Multiple positive historical contexts apply today. "
            "There is evidence of suitability from more than one area."
        )

    elif len(factors) == 1:

        edgeiq_view = (
            "One positive historical context applies today."
        )

    elif caution_factor:

        edgeiq_view = (
            "A historical caution signal applies today. "
            "The current setup differs from stronger historical profiles."
        )

    else:

        edgeiq_view = (
            "No strong historical context signal was identified "
            "from the current intelligence library."
        )

    out_rows.append({

        "race_date": clean(r.get("race_date")),
        "track": clean(r.get("track")),
        "race_no": clean(r.get("race_no")),
        "horse": clean(r.get("horse")),
        "trainer": clean(r.get("trainer")),
        "jockey": clean(r.get("jockey")),

        "edgeiq_view": edgeiq_view,

        "context_1_heading": factors[0]["heading"] if len(factors) > 0 else "",
        "context_1_factor": factors[0]["factor"] if len(factors) > 0 else "",
        "context_1_text": factors[0]["reason"] if len(factors) > 0 else "",

        "context_2_heading": factors[1]["heading"] if len(factors) > 1 else "",
        "context_2_factor": factors[1]["factor"] if len(factors) > 1 else "",
        "context_2_text": factors[1]["reason"] if len(factors) > 1 else "",

        "context_3_heading": factors[2]["heading"] if len(factors) > 2 else "",
        "context_3_factor": factors[2]["factor"] if len(factors) > 2 else "",
        "context_3_text": factors[2]["reason"] if len(factors) > 2 else "",

        "caution_heading": "CAUTION CONTEXT" if caution_factor else "",
        "caution_factor": caution_factor,
        "caution_text": caution_reason,

        "built_at": datetime.now().isoformat(),
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(out_rows[0].keys())
    )

    writer.writeheader()
    writer.writerows(out_rows)

summary = [

    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"output_rows","value":len(out_rows)},

    {
        "metric":"rows_with_narratives",
        "value":sum(
            1 for r in out_rows
            if clean(r["context_1_factor"])
        )
    },

    {
        "metric":"rows_with_cautions",
        "value":sum(
            1 for r in out_rows
            if clean(r["caution_factor"])
        )
    },

    {"metric":"built_at","value":datetime.now().isoformat()}

]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=["metric","value"]
    )

    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_NARRATIVE_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
