import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_runner_intelligence_explainer_v1.csv"

OUT = DATA / "edgeiq_context_translation_engine_v1.csv"
SUMMARY = DATA / "edgeiq_context_translation_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def translate_title(title):
    t = clean(title)

    mapping = {
        "Trainer Track Context": "Stable Track Profile",
        "Trainer Track Profile": "Stable Track Profile",
        "Trainer Distance Context": "Stable Distance Profile",
        "Trainer Condition Context": "Stable Condition Profile",
        "Trainer Class Context": "Stable Class Profile",
        "Trainer Barrier Context": "Stable Draw Profile",
        "Trainer Market Context": "Stable Market Pattern",

        "Jockey Track Context": "Rider Track Profile",
        "Jockey Distance Context": "Rider Distance Profile",
        "Jockey Condition Context": "Rider Condition Profile",
        "Jockey Class Context": "Rider Race-Type Profile",
        "Jockey Barrier Context": "Rider Draw Profile",
        "Jockey Market Context": "Rider Market Pattern",

        "Horse Track Profile": "Horse Track Profile",
        "Horse Distance Profile": "Horse Distance Profile",
        "Horse Condition Profile": "Horse Condition Profile",
        "Horse Class Profile": "Horse Race-Type Profile",
        "Horse Barrier Profile": "Horse Draw Profile",
        "Horse Market Profile": "Horse Market Pattern",

        "Trainer/Jockey Connection": "Stable/Rider Partnership",
    }

    return mapping.get(t, t)

def explain_title(title):
    t = clean(title)

    if t == "Stable Track Profile":
        return "This stable has historically performed above baseline at this venue or similar track setup."
    if t == "Stable Distance Profile":
        return "This stable has historically produced stronger results in this distance range."
    if t == "Stable Condition Profile":
        return "This stable has historically performed well under similar track conditions."
    if t == "Stable Class Profile":
        return "This stable has historically performed well in this race type or grade."
    if t == "Stable Draw Profile":
        return "This stable has historically converted similar barrier setups well."
    if t == "Stable Market Pattern":
        return "This stable has historically performed well when runners started in a similar market position."

    if t == "Rider Track Profile":
        return "This rider has historically performed above baseline at this venue or similar track setup."
    if t == "Rider Distance Profile":
        return "This rider has historically performed well over this distance range."
    if t == "Rider Condition Profile":
        return "This rider has historically performed well under similar track conditions."
    if t == "Rider Race-Type Profile":
        return "This rider has historically performed well in this race type or grade."
    if t == "Rider Draw Profile":
        return "This rider has historically handled similar barrier setups well."
    if t == "Rider Market Pattern":
        return "This rider has historically performed well when runners started in a similar market position."

    if t == "Horse Track Profile":
        return "This horse has historically performed above baseline at this venue."
    if t == "Horse Distance Profile":
        return "This horse has historically performed above baseline in this distance range."
    if t == "Horse Condition Profile":
        return "This horse has historically performed above baseline under similar track conditions."
    if t == "Horse Race-Type Profile":
        return "This horse has historically performed above baseline in this race type or grade."
    if t == "Horse Draw Profile":
        return "This horse has historically performed above baseline from similar draws."
    if t == "Horse Market Pattern":
        return "This horse has historically performed well when starting in a similar market position."

    if t == "Stable/Rider Partnership":
        return "This stable and rider combination has historically performed above baseline when partnered."

    return ""

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []

for r in rows:

    factor_titles = [
        clean(r.get("factor_1_title")),
        clean(r.get("factor_2_title")),
        clean(r.get("factor_3_title")),
    ]

    caution_titles = [
        clean(r.get("caution_1_title")),
    ]

    translated = [translate_title(x) for x in factor_titles if x]
    translated_cautions = [translate_title(x) for x in caution_titles if x]

    explanations = [explain_title(x) for x in translated]
    caution_explanations = [explain_title(x) for x in translated_cautions]

    if len(translated) >= 3 and len(translated_cautions) == 0:
        edgeiq_view = (
            "Several relevant historical profiles line up with today's setup. "
            "The most notable signals relate to " +
            ", ".join(translated[:3]).lower() +
            "."
        )
    elif len(translated) >= 2 and len(translated_cautions) >= 1:
        edgeiq_view = (
            "There are useful positive signals, but at least one caution profile is also present. "
            "This creates a mixed context picture rather than a clean read."
        )
    elif len(translated) >= 2:
        edgeiq_view = (
            "Multiple positive historical profiles apply to today's setup."
        )
    elif len(translated) == 1 and len(translated_cautions) == 0:
        edgeiq_view = (
            "One positive historical profile applies to today's setup."
        )
    elif len(translated_cautions) >= 1 and len(translated) == 0:
        edgeiq_view = (
            "One or more caution profiles apply to today's setup."
        )
    elif len(translated) >= 1 and len(translated_cautions) >= 1:
        edgeiq_view = (
            "Both positive and caution profiles apply to today's setup."
        )
    else:
        edgeiq_view = (
            "No strong historical context signal was identified from the current intelligence library."
        )

    out_rows.append({
        "race_date": clean(r.get("race_date")),
        "track": clean(r.get("track")),
        "race_no": clean(r.get("race_no")),
        "horse": clean(r.get("horse")),
        "trainer": clean(r.get("trainer")),
        "jockey": clean(r.get("jockey")),

        "edgeiq_factor_1": translated[0] if len(translated) > 0 else "",
        "edgeiq_factor_1_explained": explanations[0] if len(explanations) > 0 else "",

        "edgeiq_factor_2": translated[1] if len(translated) > 1 else "",
        "edgeiq_factor_2_explained": explanations[1] if len(explanations) > 1 else "",

        "edgeiq_factor_3": translated[2] if len(translated) > 2 else "",
        "edgeiq_factor_3_explained": explanations[2] if len(explanations) > 2 else "",

        "edgeiq_caution_1": translated_cautions[0] if len(translated_cautions) > 0 else "",
        "edgeiq_caution_1_explained": caution_explanations[0] if len(caution_explanations) > 0 else "",

        "edgeiq_view": edgeiq_view,
        "built_at": datetime.now().isoformat(),
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"output_rows","value":len(out_rows)},
    {"metric":"rows_with_edgeiq_factor_1","value":sum(1 for r in out_rows if r["edgeiq_factor_1"])},
    {"metric":"rows_with_edgeiq_caution_1","value":sum(1 for r in out_rows if r["edgeiq_caution_1"])},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_CONTEXT_TRANSLATION_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
