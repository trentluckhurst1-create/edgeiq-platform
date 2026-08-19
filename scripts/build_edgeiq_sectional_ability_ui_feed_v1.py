import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_sectional_ability_engine_v3.csv"
OUT = DATA / "edgeiq_sectional_ability_ui_feed_v1.csv"
AUDIT = DATA / "edgeiq_sectional_ability_ui_feed_v1_audit.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def to_float(v, default=0.0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default

def to_int(v, default=0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(v))
    except Exception:
        return default

def badge_for_class(cls):
    cls = clean(cls).upper()
    if cls in ("WORLD_CLASS", "ELITE"):
        return "ELITE"
    if cls == "VERY_STRONG":
        return "STRONG"
    if cls == "ABOVE_AVERAGE":
        return "ABOVE"
    if cls == "COMPETITIVE":
        return "COMP"
    if cls == "AVERAGE":
        return "AVG"
    return "LIMITED"

def tone_for_class(cls):
    cls = clean(cls).upper()
    if cls in ("WORLD_CLASS", "ELITE", "VERY_STRONG"):
        return "positive"
    if cls in ("ABOVE_AVERAGE", "COMPETITIVE"):
        return "neutral"
    if cls == "AVERAGE":
        return "watch"
    return "negative"

def short_confidence(conf_band):
    conf_band = clean(conf_band).upper()
    if conf_band == "VERY_HIGH_CONFIDENCE":
        return "VERY HIGH"
    if conf_band == "HIGH_CONFIDENCE":
        return "HIGH"
    if conf_band == "MEDIUM_CONFIDENCE":
        return "MEDIUM"
    if conf_band == "LOW_CONFIDENCE":
        return "LOW"
    return "VERY LOW"

def readable_class(cls):
    return clean(cls).replace("_", " ").title()

def readable_warning(w):
    w = clean(w).upper()
    if w == "EARLY_HIGH_UPSIDE_NEEDS_CONFIRMATION":
        return "Early upside — needs confirmation"
    if w == "SMALL_SAMPLE_HIGH_UPSIDE":
        return "Small sample high-upside profile"
    if w == "PROVEN_SECTIONAL_ABILITY":
        return "Proven sectional ability"
    if w == "PROVEN_LIMITED_SECTIONALS":
        return "Proven limited sectional profile"
    if w == "LOW_EVIDENCE":
        return "Low evidence"
    return "OK"

def note_for(row):
    ability = to_float(row.get("sectional_ability_score_v3"))
    cls = clean(row.get("sectional_ability_class_v3")).upper()
    conf = clean(row.get("sectional_confidence_band_v3")).upper()
    rank = clean(row.get("sectional_reliability_rank_v3")).upper()
    warning = clean(row.get("sectional_sample_warning_v3")).upper()
    runs = to_int(row.get("runs_with_sectionals"))

    if warning == "EARLY_HIGH_UPSIDE_NEEDS_CONFIRMATION":
        return f"Strong sectional profile from {runs} runs, but evidence is still early."
    if warning == "SMALL_SAMPLE_HIGH_UPSIDE":
        return f"High upside sectional signal from a very small sample."
    if warning == "PROVEN_SECTIONAL_ABILITY":
        return f"Strong ability with reliable sectional evidence."
    if warning == "PROVEN_LIMITED_SECTIONALS":
        return f"Reliable evidence, but sectional output is limited."
    if cls in ("WORLD_CLASS", "ELITE", "VERY_STRONG") and rank in ("A", "B"):
        return f"High-grade sectional ability with solid reliability."
    if cls in ("WORLD_CLASS", "ELITE", "VERY_STRONG"):
        return f"High ability signal, but confidence needs more evidence."
    if ability >= 68:
        return f"Above-average sectional profile."
    if conf in ("HIGH_CONFIDENCE", "VERY_HIGH_CONFIDENCE"):
        return f"Reliable profile; ability level is well exposed."
    return f"Sectional profile still developing."

rows = []

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for r in reader:
        horse_name = clean(r.get("horse_name"))
        ability_score = round(to_float(r.get("sectional_ability_score_v3")), 2)
        ability_class = clean(r.get("sectional_ability_class_v3"))
        conf_score = round(to_float(r.get("sectional_confidence_score_v3")), 2)
        conf_band = clean(r.get("sectional_confidence_band_v3"))
        reliability = clean(r.get("sectional_reliability_rank_v3"))
        warning = clean(r.get("sectional_sample_warning_v3"))
        runs = to_int(r.get("runs_with_sectionals"))

        out = {
            "horse_name": horse_name,
            "runs_with_sectionals": runs,
            "sectional_ability_badge": badge_for_class(ability_class),
            "sectional_ability_tone": tone_for_class(ability_class),
            "sectional_ability_score": ability_score,
            "sectional_ability_class": ability_class,
            "sectional_ability_label": readable_class(ability_class),
            "sectional_confidence_score": conf_score,
            "sectional_confidence_band": conf_band,
            "sectional_confidence_label": short_confidence(conf_band),
            "sectional_reliability_rank": reliability,
            "sectional_sample_warning": warning,
            "sectional_warning_label": readable_warning(warning),
            "sectional_ability_note": note_for(r),
            "sectional_display_status": "READY" if horse_name else "NO_NAME",
        }

        rows.append(out)

fields = [
    "horse_name",
    "runs_with_sectionals",
    "sectional_ability_badge",
    "sectional_ability_tone",
    "sectional_ability_score",
    "sectional_ability_class",
    "sectional_ability_label",
    "sectional_confidence_score",
    "sectional_confidence_band",
    "sectional_confidence_label",
    "sectional_reliability_rank",
    "sectional_sample_warning",
    "sectional_warning_label",
    "sectional_ability_note",
    "sectional_display_status",
]

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

badge_counts = {}
tone_counts = {}
status_counts = {}

for r in rows:
    badge_counts[r["sectional_ability_badge"]] = badge_counts.get(r["sectional_ability_badge"], 0) + 1
    tone_counts[r["sectional_ability_tone"]] = tone_counts.get(r["sectional_ability_tone"], 0) + 1
    status_counts[r["sectional_display_status"]] = status_counts.get(r["sectional_display_status"], 0) + 1

audit_row = {
    "source_rows": len(rows),
    "ready_rows": status_counts.get("READY", 0),
    "elite_badge": badge_counts.get("ELITE", 0),
    "strong_badge": badge_counts.get("STRONG", 0),
    "above_badge": badge_counts.get("ABOVE", 0),
    "comp_badge": badge_counts.get("COMP", 0),
    "avg_badge": badge_counts.get("AVG", 0),
    "limited_badge": badge_counts.get("LIMITED", 0),
    "positive_tone": tone_counts.get("positive", 0),
    "neutral_tone": tone_counts.get("neutral", 0),
    "watch_tone": tone_counts.get("watch", 0),
    "negative_tone": tone_counts.get("negative", 0),
    "final_status": "SECTIONAL_ABILITY_UI_FEED_BUILT",
}

with AUDIT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(audit_row.keys()))
    writer.writeheader()
    writer.writerow(audit_row)

print("EDGEiQ Sectional Ability UI Feed V1 built")
print(f"rows={len(rows)}")
print(f"saved={OUT}")
print(f"audit={AUDIT}")
print("final_status=SECTIONAL_ABILITY_UI_FEED_BUILT")
