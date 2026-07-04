from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import math

DATA = Path("public/data")
PROFILE = DATA / "edgeiq_gear_profile_engine_v1.csv"
GOV = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_gear_signal_engine_v1.csv"
SUMMARY = DATA / "edgeiq_gear_signal_engine_v1_summary.csv"
REPORT = DATA / "edgeiq_gear_signal_engine_v1_report.txt"

def clean(v): return "" if pd.isna(v) else str(v).strip()
def num(v, default=0.0):
    try:
        x = float(str(v).replace("%", "").strip())
        if math.isnan(x) or math.isinf(x): return default
        return x
    except Exception:
        return default

def has_gear(v):
    return clean(v).lower() not in ("", "nan", "none", "null", "[]")

def band(score, gear):
    if not gear: return "NO_GEAR"
    if score >= 80: return "ELITE"
    if score >= 65: return "POSITIVE"
    if score >= 45: return "NEUTRAL"
    if score >= 25: return "CAUTION"
    return "RISK"

def yes(cond): return "YES" if cond else "NO"

profile = pd.read_csv(PROFILE, dtype=str, keep_default_na=False, low_memory=False)
# Load governed only to confirm row count/order source exists.
gov = pd.read_csv(GOV, dtype=str, keep_default_na=False, low_memory=False)
out = profile.copy()

scores = []
bands = []
positive = []
negative = []
first_blink = []
trainer_pos = []
jockey_pos = []
summaries = []
for _, r in out.iterrows():
    gear = has_gear(r.get("gear_change", ""))
    base = num(r.get("gear_intelligence_score"), 0)
    trainer_starts = num(r.get("trainer_gear_starts"), 0)
    trainer_win = num(r.get("trainer_gear_win_pct"), 0)
    trainer_place = num(r.get("trainer_gear_place_pct"), 0)
    jockey_starts = num(r.get("jockey_gear_starts"), 0)
    jockey_win = num(r.get("jockey_gear_win_pct"), 0)
    overall_starts = num(r.get("overall_gear_starts"), 0)
    overall_win = num(r.get("overall_gear_win_pct"), 0)
    text = clean(r.get("gear_change", "")).upper()
    if gear:
        support_bonus = 0
        if trainer_starts >= 10 and trainer_win >= 12: support_bonus += 6
        if trainer_place >= 40: support_bonus += 4
        if jockey_starts >= 10 and jockey_win >= 12: support_bonus += 4
        if overall_starts >= 30 and overall_win >= 10: support_bonus += 3
        off_penalty = 4 if " OFF" in f" {text}" else 0
        score = max(0, min(100, base + support_bonus - off_penalty))
    else:
        score = 0
    b = band(score, gear)
    scores.append(round(score, 1))
    bands.append(b)
    positive.append(yes(gear and b in ("ELITE", "POSITIVE") and (trainer_win >= 12 or overall_win >= 10)))
    negative.append(yes(gear and b in ("RISK", "CAUTION")))
    first_blink.append(yes(gear and "BLINKER" in text and "FIRST TIME" in text))
    trainer_pos.append(yes(gear and trainer_starts >= 10 and trainer_win >= 12))
    jockey_pos.append(yes(gear and jockey_starts >= 10 and jockey_win >= 12))
    if not gear:
        summaries.append("No listed gear change for this runner.")
    elif b in ("ELITE", "POSITIVE"):
        summaries.append(f"{clean(r.get('gear_change'))}: positive historical gear pattern; trainer {int(trainer_starts)} starts at {trainer_win:.1f}% wins.")
    elif b == "NEUTRAL":
        summaries.append(f"{clean(r.get('gear_change'))}: gear profile is neutral on available history.")
    else:
        summaries.append(f"{clean(r.get('gear_change'))}: limited or cautious gear evidence on available history.")

out["gear_signal_score"] = scores
out["gear_signal_band"] = bands
out["positive_gear_signal"] = positive
out["negative_gear_signal"] = negative
out["first_time_blinkers_signal"] = first_blink
out["trainer_gear_positive"] = trainer_pos
out["jockey_gear_positive"] = jockey_pos
out["gear_summary"] = summaries
out.to_csv(OUT, index=False)

band_counts = out["gear_signal_band"].value_counts().to_dict()
summary_rows = [
    {"metric": "status", "value": "EDGEIQ_GEAR_SIGNAL_ENGINE_V1_BUILT"},
    {"metric": "input_rows", "value": len(profile)},
    {"metric": "governed_rows", "value": len(gov)},
    {"metric": "output_rows", "value": len(out)},
    {"metric": "rows_with_gear_change", "value": int(out["gear_change"].astype(str).str.strip().ne("").sum())},
]
for k, v in sorted(band_counts.items()):
    summary_rows.append({"metric": f"gear_signal_band_{k}", "value": int(v)})
summary_rows.extend([
    {"metric": "positive_gear_signal_rows", "value": int((out["positive_gear_signal"] == "YES").sum())},
    {"metric": "negative_gear_signal_rows", "value": int((out["negative_gear_signal"] == "YES").sum())},
    {"metric": "first_time_blinkers_signal_rows", "value": int((out["first_time_blinkers_signal"] == "YES").sum())},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
REPORT.write_text("\n".join([
    "EDGEIQ_GEAR_SIGNAL_ENGINE_V1",
    "==============================",
    f"Rows: {len(out)}",
    f"Rows with gear change: {int(out['gear_change'].astype(str).str.strip().ne('').sum())}",
    f"Band counts: {band_counts}",
    "Production changed: NO",
    "Pricing changed: NO",
]) + "\n", encoding="utf-8")
print("GEAR_SIGNAL_ENGINE_COMPLETE", len(out), band_counts)
