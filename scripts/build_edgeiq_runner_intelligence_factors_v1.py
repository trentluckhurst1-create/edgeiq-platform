import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_factor_selection_engine_v2.csv"

OUT = DATA / "edgeiq_runner_intelligence_factors_v1.csv"
SUMMARY = DATA / "edgeiq_runner_intelligence_factors_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def simplify_factor(raw):
    s = clean(raw)

    if not s:
        return ("", "")

    left, sep, right = s.partition(" — ")

    title = left.strip()
    reason = right.strip() if sep else s

    replacements = {
        "Horse Track Context": "Horse Track Profile",
        "Horse Distance Context": "Horse Distance Profile",
        "Horse Condition Context": "Horse Condition Profile",
        "Horse Class Context": "Horse Class Profile",
        "Horse Barrier Context": "Horse Barrier Profile",
        "Horse Sp Context": "Horse Market Profile",

        "Trainer Track Context": "Trainer Track Context",
        "Trainer Track_Family Context": "Trainer Track Profile",
        "Trainer Distance Context": "Trainer Distance Context",
        "Trainer Condition Context": "Trainer Condition Context",
        "Trainer Class Context": "Trainer Class Context",
        "Trainer Barrier Context": "Trainer Barrier Context",
        "Trainer Sp Context": "Trainer Market Context",

        "Jockey Track Context": "Jockey Track Context",
        "Jockey Distance Context": "Jockey Distance Context",
        "Jockey Condition Context": "Jockey Condition Context",
        "Jockey Class Context": "Jockey Class Context",
        "Jockey Barrier Context": "Jockey Barrier Context",
        "Jockey Sp Context": "Jockey Market Context",

        "Connection Context": "Trainer/Jockey Connection",
    }

    title = replacements.get(title, title)

    reason = reason.replace("CONTEXT_EDGE", "positive context")
    reason = reason.replace("MILD_CONTEXT_EDGE", "mild positive context")
    reason = reason.replace("CONNECTION_EDGE", "positive connection")
    reason = reason.replace("MILD_CONNECTION_EDGE", "mild positive connection")
    reason = reason.replace("CONTEXT_RISK", "caution context")
    reason = reason.replace("CONNECTION_RISK", "caution connection")

    reason = reason.replace("track_family", "track profile")
    reason = reason.replace("track context", "track context")
    reason = reason.replace("distance context", "distance context")
    reason = reason.replace("condition context", "track condition context")
    reason = reason.replace("barrier context", "barrier context")
    reason = reason.replace("class context", "race class context")
    reason = reason.replace("sp context", "market context")

    return (title, reason)

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []

for r in rows:

    positives = [
        clean(r.get("positive_factor_1")),
        clean(r.get("positive_factor_2")),
        clean(r.get("positive_factor_3")),
        clean(r.get("positive_factor_4")),
        clean(r.get("positive_factor_5")),
    ]

    cautions = [
        clean(r.get("caution_factor_1")),
        clean(r.get("caution_factor_2")),
        clean(r.get("caution_factor_3")),
    ]

    positives = [x for x in positives if x]
    cautions = [x for x in cautions if x]

    p1_title, p1_reason = simplify_factor(positives[0] if len(positives) > 0 else "")
    p2_title, p2_reason = simplify_factor(positives[1] if len(positives) > 1 else "")
    p3_title, p3_reason = simplify_factor(positives[2] if len(positives) > 2 else "")
    p4_title, p4_reason = simplify_factor(positives[3] if len(positives) > 3 else "")

    c1_title, c1_reason = simplify_factor(cautions[0] if len(cautions) > 0 else "")
    c2_title, c2_reason = simplify_factor(cautions[1] if len(cautions) > 1 else "")

    positive_count = int(clean(r.get("positive_factor_count")) or 0)
    caution_count = int(clean(r.get("caution_factor_count")) or 0)

    if positive_count >= 4 and caution_count == 0:
        edgeiq_view = "Multiple positive historical contexts align with today's setup."
        edgeiq_assessment = "Strong contextual support."
    elif positive_count >= 3 and caution_count <= 1:
        edgeiq_view = "Several positive contexts apply, with limited caution."
        edgeiq_assessment = "Positive contextual profile."
    elif positive_count >= 2 and caution_count >= 2:
        edgeiq_view = "Positive and caution signals are both present."
        edgeiq_assessment = "Mixed contextual profile."
    elif positive_count >= 1 and caution_count == 0:
        edgeiq_view = "At least one positive historical context applies today."
        edgeiq_assessment = "Some contextual support."
    elif caution_count >= 1 and positive_count == 0:
        edgeiq_view = "Historical caution context applies today."
        edgeiq_assessment = "Caution contextual profile."
    elif positive_count >= 1 and caution_count >= 1:
        edgeiq_view = "Positive and caution contexts both apply."
        edgeiq_assessment = "Mixed contextual profile."
    else:
        edgeiq_view = "No strong historical context signal detected."
        edgeiq_assessment = "Limited contextual evidence."

    out_rows.append({
        "source_file": clean(r.get("source_file")),
        "race_date": clean(r.get("race_date")),
        "track": clean(r.get("track")),
        "race_no": clean(r.get("race_no")),
        "horse": clean(r.get("horse")),
        "trainer": clean(r.get("trainer_display")),
        "jockey": clean(r.get("jockey_display")),
        "trainer_context_key": clean(r.get("trainer_context_key")),
        "jockey_context_key": clean(r.get("jockey_context_key")),
        "distance": clean(r.get("distance")),
        "track_condition": clean(r.get("track_condition")),
        "race_class": clean(r.get("race_class")),
        "barrier": clean(r.get("barrier")),
        "sp_or_price": clean(r.get("sp_or_price")),

        "positive_factor_count": positive_count,
        "caution_factor_count": caution_count,

        "factor_1_title": p1_title,
        "factor_1_reason": p1_reason,
        "factor_2_title": p2_title,
        "factor_2_reason": p2_reason,
        "factor_3_title": p3_title,
        "factor_3_reason": p3_reason,
        "factor_4_title": p4_title,
        "factor_4_reason": p4_reason,

        "caution_1_title": c1_title,
        "caution_1_reason": c1_reason,
        "caution_2_title": c2_title,
        "caution_2_reason": c2_reason,

        "edgeiq_view": edgeiq_view,
        "edgeiq_assessment": edgeiq_assessment,
        "built_at": datetime.now().isoformat(),
    })

out_rows.sort(
    key=lambda r: (
        r["track"],
        int(r["race_no"]) if str(r["race_no"]).isdigit() else 999,
        -int(r["positive_factor_count"]),
        int(r["caution_factor_count"]),
        r["horse"]
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric": "status", "value": "COMPLETE"},
    {"metric": "source_rows", "value": len(rows)},
    {"metric": "output_rows", "value": len(out_rows)},
    {"metric": "rows_with_positive_factors", "value": sum(1 for r in out_rows if int(r["positive_factor_count"]) > 0)},
    {"metric": "rows_with_caution_factors", "value": sum(1 for r in out_rows if int(r["caution_factor_count"]) > 0)},
    {"metric": "strong_contextual_support", "value": sum(1 for r in out_rows if r["edgeiq_assessment"] == "Strong contextual support.")},
    {"metric": "positive_contextual_profile", "value": sum(1 for r in out_rows if r["edgeiq_assessment"] == "Positive contextual profile.")},
    {"metric": "mixed_contextual_profile", "value": sum(1 for r in out_rows if r["edgeiq_assessment"] == "Mixed contextual profile.")},
    {"metric": "caution_contextual_profile", "value": sum(1 for r in out_rows if r["edgeiq_assessment"] == "Caution contextual profile.")},
    {"metric": "built_at", "value": datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_RUNNER_INTELLIGENCE_FACTORS_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
