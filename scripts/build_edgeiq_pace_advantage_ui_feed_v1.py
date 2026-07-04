from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pace_advantage_engine_v1.csv"
OUT = DATA / "edgeiq_pace_advantage_ui_feed_v1.csv"
AUDIT = DATA / "edgeiq_pace_advantage_ui_feed_v1_audit.csv"

OUT_COLS = [
    "meeting_date",
    "track",
    "race_no",
    "horse_name",
    "horse_key",
    "runner_number",
    "pace_badge",
    "pace_label",
    "pace_advantage_type",
    "pace_advantage_status",
    "pace_advantage_score",
    "race_shape",
    "pressure_rating",
    "collapse_risk",
    "pace_note",
    "pace_risk_note",
    "pace_display_status",
]

AUDIT_COLS = [
    "input_rows_loaded",
    "output_rows",
    "very_positive_rows",
    "positive_rows",
    "neutral_rows",
    "negative_rows",
    "pace_collapse_beneficiaries",
    "soft_lead_advantages",
    "turn_of_foot_advantages",
    "pace_vulnerable",
    "final_status",
]


def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    if s.upper() in {"NAN", "NONE", "NULL", "NA", "N/A", "-"}:
        return ""
    return re.sub(r"\s+", " ", s)


def pick(row, keys, default=""):
    for key in keys:
        value = clean(row.get(key))
        if value:
            return value
    return default


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in cols})
    tmp.replace(path)


def label_for(adv_type):
    t = clean(adv_type).upper()
    return {
        "PACE_COLLAPSE_BENEFICIARY": "Pace collapse beneficiary",
        "SOFT_LEAD_ADVANTAGE": "Soft lead advantage",
        "TURN_OF_FOOT_ADVANTAGE": "Turn of foot advantage",
        "PACE_VULNERABLE": "Pace vulnerable",
        "HONEST_TEMPO_ADVANTAGE": "Honest tempo advantage",
        "NEUTRAL": "No clear pace edge",
    }.get(t, t.replace("_", " ").title() if t else "No clear pace edge")


def badge_for(status, adv_type):
    s = clean(status).upper()
    t = clean(adv_type).upper()

    if s == "VERY_POSITIVE":
        if t == "PACE_COLLAPSE_BENEFICIARY":
            return "PACE COLLAPSE"
        if t == "SOFT_LEAD_ADVANTAGE":
            return "SOFT LEAD"
        if t == "TURN_OF_FOOT_ADVANTAGE":
            return "TURN OF FOOT"
        return "VERY POSITIVE"

    if s == "POSITIVE":
        if t == "PACE_COLLAPSE_BENEFICIARY":
            return "PACE HELP"
        if t == "SOFT_LEAD_ADVANTAGE":
            return "LEAD HELP"
        if t == "TURN_OF_FOOT_ADVANTAGE":
            return "SPEED HELP"
        if t == "HONEST_TEMPO_ADVANTAGE":
            return "TEMPO HELP"
        return "POSITIVE"

    if s == "NEGATIVE":
        return "PACE RISK"

    return "NEUTRAL"


def note_for(row):
    reason = pick(row, ["pace_advantage_reason"], "")
    if reason:
        return reason
    status = pick(row, ["pace_advantage_status"], "NEUTRAL").upper()
    if status in {"VERY_POSITIVE", "POSITIVE"}:
        return "Projected race shape may suit this runner."
    if status == "NEGATIVE":
        return "Projected race shape may work against this runner."
    return "No clear pace-shape edge detected."


def risk_for(row):
    status = pick(row, ["pace_advantage_status"], "NEUTRAL").upper()
    adv_type = pick(row, ["pace_advantage_type"], "NEUTRAL").upper()
    if status == "NEGATIVE":
        return "Treat as a tactical risk."
    if adv_type == "PACE_COLLAPSE_BENEFICIARY":
        return "Requires pressure to materialise."
    if adv_type == "SOFT_LEAD_ADVANTAGE":
        return "Risk if challenged early."
    if adv_type == "TURN_OF_FOOT_ADVANTAGE":
        return "Best if race becomes tactical."
    return ""


def main():
    rows = read_csv(SRC)
    out = []

    for row in rows:
        status = pick(row, ["pace_advantage_status"], "NEUTRAL").upper()
        adv_type = pick(row, ["pace_advantage_type"], "NEUTRAL").upper()

        out.append({
            "meeting_date": pick(row, ["meeting_date"]),
            "track": pick(row, ["track"]),
            "race_no": pick(row, ["race_no"]),
            "horse_name": pick(row, ["horse_name"]),
            "horse_key": pick(row, ["horse_key"]),
            "runner_number": pick(row, ["runner_number"]),
            "pace_badge": badge_for(status, adv_type),
            "pace_label": label_for(adv_type),
            "pace_advantage_type": adv_type,
            "pace_advantage_status": status,
            "pace_advantage_score": pick(row, ["pace_advantage_score"], "50"),
            "race_shape": pick(row, ["race_shape"], "NEUTRAL"),
            "pressure_rating": pick(row, ["pressure_rating"], "MODERATE"),
            "collapse_risk": pick(row, ["collapse_risk"], "MEDIUM"),
            "pace_note": note_for(row),
            "pace_risk_note": risk_for(row),
            "pace_display_status": status,
        })

    audit = [{
        "input_rows_loaded": len(rows),
        "output_rows": len(out),
        "very_positive_rows": sum(1 for r in out if r["pace_advantage_status"] == "VERY_POSITIVE"),
        "positive_rows": sum(1 for r in out if r["pace_advantage_status"] == "POSITIVE"),
        "neutral_rows": sum(1 for r in out if r["pace_advantage_status"] == "NEUTRAL"),
        "negative_rows": sum(1 for r in out if r["pace_advantage_status"] == "NEGATIVE"),
        "pace_collapse_beneficiaries": sum(1 for r in out if r["pace_advantage_type"] == "PACE_COLLAPSE_BENEFICIARY"),
        "soft_lead_advantages": sum(1 for r in out if r["pace_advantage_type"] == "SOFT_LEAD_ADVANTAGE"),
        "turn_of_foot_advantages": sum(1 for r in out if r["pace_advantage_type"] == "TURN_OF_FOOT_ADVANTAGE"),
        "pace_vulnerable": sum(1 for r in out if r["pace_advantage_type"] == "PACE_VULNERABLE"),
        "final_status": "PACE_ADVANTAGE_UI_FEED_BUILT" if out else "NO_OUTPUT_ROWS",
    }]

    write_csv(OUT, out, OUT_COLS)
    write_csv(AUDIT, audit, AUDIT_COLS)

    print("EDGEiQ Pace Advantage UI Feed V1 built")
    print(f"output_rows={len(out)}")
    print(f"very_positive={audit[0]['very_positive_rows']}")
    print(f"positive={audit[0]['positive_rows']}")
    print(f"negative={audit[0]['negative_rows']}")
    print(f"final_status={audit[0]['final_status']}")


if __name__ == "__main__":
    main()
