import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_runner_intelligence_factors_v1.csv"

OUT = DATA / "edgeiq_runner_intelligence_explainer_v1.csv"
SUMMARY = DATA / "edgeiq_runner_intelligence_explainer_v1_summary.csv"

def clean(v):
    return (v or "").strip()

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []

for r in rows:

    positive_titles = [
        clean(r.get("factor_1_title")),
        clean(r.get("factor_2_title")),
        clean(r.get("factor_3_title")),
        clean(r.get("factor_4_title")),
    ]

    positive_reasons = [
        clean(r.get("factor_1_reason")),
        clean(r.get("factor_2_reason")),
        clean(r.get("factor_3_reason")),
        clean(r.get("factor_4_reason")),
    ]

    caution_titles = [
        clean(r.get("caution_1_title")),
        clean(r.get("caution_2_title")),
    ]

    caution_reasons = [
        clean(r.get("caution_1_reason")),
        clean(r.get("caution_2_reason")),
    ]

    positive_titles = [x for x in positive_titles if x]
    positive_reasons = [x for x in positive_reasons if x]

    caution_titles = [x for x in caution_titles if x]
    caution_reasons = [x for x in caution_reasons if x]

    positive_count = int(clean(r.get("positive_factor_count")) or 0)
    caution_count = int(clean(r.get("caution_factor_count")) or 0)

    if positive_count >= 4 and caution_count == 0:
        edgeiq_view = (
            "Multiple historical profiles align with today's setup. "
            "Several trainer, jockey, horse or connection contexts "
            "match conditions that have historically produced "
            "above-baseline outcomes."
        )

    elif positive_count >= 2 and caution_count <= 1:
        edgeiq_view = (
            "Several positive historical contexts apply today. "
            "The current setup shares characteristics with situations "
            "that have previously produced favourable results."
        )

    elif positive_count >= 1 and caution_count >= 1:
        edgeiq_view = (
            "Positive and caution signals are both present. "
            "Some aspects of today's setup align with historical strengths "
            "while other factors introduce uncertainty."
        )

    elif caution_count > 0:
        edgeiq_view = (
            "One or more historical caution signals are present. "
            "Today's setup differs from the strongest historical contexts "
            "associated with this runner or connections."
        )

    elif positive_count > 0:
        edgeiq_view = (
            "At least one positive historical context applies today."
        )

    else:
        edgeiq_view = (
            "No strong historical context signals were identified "
            "from the current intelligence library."
        )

    out_rows.append({
        "race_date": clean(r.get("race_date")),
        "track": clean(r.get("track")),
        "race_no": clean(r.get("race_no")),
        "horse": clean(r.get("horse")),
        "trainer": clean(r.get("trainer")),
        "jockey": clean(r.get("jockey")),

        "factor_1_title": positive_titles[0] if len(positive_titles) > 0 else "",
        "factor_1_reason": positive_reasons[0] if len(positive_reasons) > 0 else "",

        "factor_2_title": positive_titles[1] if len(positive_titles) > 1 else "",
        "factor_2_reason": positive_reasons[1] if len(positive_reasons) > 1 else "",

        "factor_3_title": positive_titles[2] if len(positive_titles) > 2 else "",
        "factor_3_reason": positive_reasons[2] if len(positive_reasons) > 2 else "",

        "caution_1_title": caution_titles[0] if len(caution_titles) > 0 else "",
        "caution_1_reason": caution_reasons[0] if len(caution_reasons) > 0 else "",

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
    {"metric":"with_explanations","value":sum(1 for r in out_rows if r["factor_1_title"])},
    {"metric":"with_cautions","value":sum(1 for r in out_rows if r["caution_1_title"])},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_RUNNER_INTELLIGENCE_EXPLAINER_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
