import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_connection_context_research_v2_stability.csv"

OUT = DATA / "edgeiq_connection_view_engine_v1.csv"
SUMMARY = DATA / "edgeiq_connection_view_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []

for r in rows:

    signal = clean(r.get("signal"))

    if signal == "NEUTRAL":
        continue

    trainer = clean(r.get("trainer"))
    jockey = clean(r.get("jockey"))
    connection = clean(r.get("connection"))

    starts = clean(r.get("starts"))
    unique_horses = clean(r.get("unique_horses"))
    span_days = clean(r.get("span_days"))

    combo_win = clean(r.get("combo_win_pct"))
    trainer_base_win = clean(r.get("trainer_base_win_pct"))
    combo_win_lift = clean(r.get("combo_vs_trainer_win_lift_pct"))

    combo_place = clean(r.get("combo_place_pct"))
    trainer_base_place = clean(r.get("trainer_base_place_pct"))
    combo_place_lift = clean(r.get("combo_vs_trainer_place_lift_pct"))

    stability = clean(r.get("stability"))
    evidence = clean(r.get("evidence_band"))

    if signal == "CONNECTION_EDGE":
        tone = "POSITIVE"
        factor = "Positive Connection Context"
        headline = "Trainer/Jockey combination has historically outperformed the trainer baseline."
        detail = (
            f"{trainer} and {jockey} have combined for {starts} rides across "
            f"{unique_horses} horses, producing a {combo_win}% win rate versus "
            f"the trainer baseline of {trainer_base_win}%."
        )

    elif signal == "MILD_CONNECTION_EDGE":
        tone = "POSITIVE"
        factor = "Positive Connection Context"
        headline = "Trainer/Jockey combination has shown a mild positive historical profile."
        detail = (
            f"{trainer} and {jockey} have shown a positive connection profile "
            f"over {starts} rides."
        )

    elif signal == "CONNECTION_RISK":
        tone = "CAUTION"
        factor = "Caution Connection Context"
        headline = "Trainer/Jockey combination has historically performed below the trainer baseline."
        detail = (
            f"{trainer} and {jockey} have combined for {starts} rides, with results "
            f"below the trainer's usual baseline."
        )

    else:
        continue

    if evidence == "STRONG_EVIDENCE":
        evidence_phrase = "Strong historical sample."
    elif evidence == "PROMISING_EVIDENCE":
        evidence_phrase = "Promising historical sample."
    elif evidence == "MILD_EVIDENCE":
        evidence_phrase = "Mild historical evidence."
    elif evidence == "CAUTION_EVIDENCE":
        evidence_phrase = "Caution evidence present."
    else:
        evidence_phrase = "Neutral evidence."

    out_rows.append({
        "entity_type": "CONNECTION",
        "entity_name": connection,
        "trainer": trainer,
        "jockey": jockey,
        "factor_label": factor,
        "signal": signal,
        "customer_tone": tone,
        "starts": starts,
        "unique_horses": unique_horses,
        "span_days": span_days,
        "combo_win_pct": combo_win,
        "trainer_base_win_pct": trainer_base_win,
        "combo_vs_trainer_win_lift_pct": combo_win_lift,
        "combo_place_pct": combo_place,
        "trainer_base_place_pct": trainer_base_place,
        "combo_vs_trainer_place_lift_pct": combo_place_lift,
        "stability": stability,
        "evidence_band": evidence,
        "view_headline": headline,
        "view_detail": detail,
        "evidence_phrase": evidence_phrase,
        "key_insight": f"{headline} {evidence_phrase}",
        "built_at": datetime.now().isoformat(),
    })

tone_order = {
    "POSITIVE": 0,
    "CAUTION": 1
}

evidence_order = {
    "STRONG_EVIDENCE": 0,
    "PROMISING_EVIDENCE": 1,
    "MILD_EVIDENCE": 2,
    "CAUTION_EVIDENCE": 3,
    "NEUTRAL_EVIDENCE": 4
}

out_rows.sort(
    key=lambda r: (
        tone_order.get(r["customer_tone"],9),
        evidence_order.get(r["evidence_band"],9),
        -int(r["starts"])
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
    {"metric":"strong_evidence_rows","value":sum(1 for r in out_rows if r["evidence_band"]=="STRONG_EVIDENCE")},
    {"metric":"promising_evidence_rows","value":sum(1 for r in out_rows if r["evidence_band"]=="PROMISING_EVIDENCE")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_CONNECTION_VIEW_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
