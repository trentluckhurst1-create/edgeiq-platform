from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

DATA = Path("public/data")
LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"
GEAR = DATA / "gear_changes.csv"
OUT = DATA / "edgeiq_current_gear_live_join_v1.csv"
SUMMARY = DATA / "edgeiq_current_gear_live_join_v1_summary.csv"
UNMATCHED = DATA / "edgeiq_current_gear_live_join_v1_unmatched.csv"
REPORT = DATA / "edgeiq_current_gear_live_join_v1_report.txt"

def clean(v): return "" if pd.isna(v) else str(v).strip()
def nt(v): return re.sub(r"\s+", " ", clean(v).upper()).strip()
def nr(v):
    s = clean(v).upper().replace("R", "")
    try: return str(int(float(s)))
    except Exception: return s
def nh(v): return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())
def nonblank(v): return clean(v).lower() not in ("", "nan", "none", "null")

def clean_gear_text(v):
    s = clean(v)
    if "|" in s:
        parts = [p.strip() for p in s.split("|") if p.strip()]
        if len(parts) >= 3:
            s = " | ".join(parts[2:])
        elif parts:
            s = parts[-1]
    s = re.sub(r"\s+", " ", s).strip()
    return s

def gear_items(v):
    s = clean_gear_text(v)
    if not s:
        return []
    return [x.strip() for x in re.split(r",|;", s) if x.strip()]

def make_flags(text):
    t = clean(text).upper()
    items = gear_items(t)
    return {
        "gear_change_count": len(items),
        "first_time_gear_count": sum(1 for x in items if "FIRST TIME" in x),
        "gear_has_blinkers": "YES" if "BLINKER" in t else "NO",
        "gear_has_tongue_tie": "YES" if "TONGUE TIE" in t else "NO",
        "gear_has_winkers": "YES" if "WINKER" in t else "NO",
        "gear_has_lugging_bit": "YES" if "LUGGING BIT" in t else "NO",
        "gear_has_nose_band": "YES" if "NOSE BAND" in t or "NOSEBAND" in t else "NO",
        "gear_has_ear_muffs": "YES" if "EAR MUFF" in t else "NO",
        "gear_has_gelded": "YES" if "GELD" in t else "NO",
        "gear_has_off": "YES" if " OFF" in f" {t}" or "OFF FIRST TIME" in t else "NO",
        "gear_has_again": "YES" if "AGAIN" in t else "NO",
    }

def build_index(df, cols):
    idx = {}
    unsafe = set()
    for _, r in df.iterrows():
        key = tuple(cols[k](r) for k in cols)
        raw = clean(r.get("gear_changes", ""))
        rec = {
            "gear_changes": clean_gear_text(raw),
            "raw_gear_changes": raw,
            "gear_source": clean(r.get("gear_source", "")),
            "gear_checked_at": clean(r.get("checked_at", "")),
            "gear_source_race_date": clean(r.get("race_date", "")),
            "gear_source_track": clean(r.get("track", "")),
            "gear_source_race_no": clean(r.get("race_no", "")),
            "gear_source_horse": clean(r.get("horse", "")),
            "gear_source_horse_key": nh(r.get("horse_key", r.get("horse", ""))),
        }
        sig = (rec["gear_changes"], rec["gear_source"], rec["gear_checked_at"])
        if key not in idx:
            idx[key] = {sig: rec}
        else:
            idx[key][sig] = rec
    safe = {}
    for k, vals in idx.items():
        if len(vals) == 1:
            safe[k] = list(vals.values())[0]
        else:
            unsafe.add(k)
    return safe, unsafe

live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
gear = pd.read_csv(GEAR, dtype=str, keep_default_na=False, low_memory=False)

stage_defs = [
    ("FULL_DATE_TRACK_RACE_HORSE", {
        "date": lambda r: clean(r.get("race_date", "")),
        "track": lambda r: nt(r.get("track", "")),
        "race": lambda r: nr(r.get("race_no", "")),
        "horse": lambda r: nh(r.get("horse_key", r.get("horse", ""))),
    }),
    ("TRACK_RACE_HORSE", {
        "track": lambda r: nt(r.get("track", "")),
        "race": lambda r: nr(r.get("race_no", "")),
        "horse": lambda r: nh(r.get("horse_key", r.get("horse", ""))),
    }),
    ("DATE_HORSE", {
        "date": lambda r: clean(r.get("race_date", "")),
        "horse": lambda r: nh(r.get("horse_key", r.get("horse", ""))),
    }),
]
indexes = []
for stage, funcs in stage_defs:
    safe, unsafe = build_index(gear, funcs)
    indexes.append((stage, funcs, safe, unsafe))

out_rows = []
unmatched = []
stage_counts = {stage: 0 for stage, _, _, _ in indexes}
unsafe_hits = 0
for _, r in live.iterrows():
    base = r.to_dict()
    match = None
    match_stage = "NO_MATCH"
    unsafe_stage = ""
    for stage, funcs, safe, unsafe in indexes:
        k = tuple(funcs[name](r) for name in funcs)
        if k in unsafe:
            unsafe_hits += 1
            unsafe_stage = stage
            continue
        if k in safe:
            match = safe[k]
            match_stage = stage
            stage_counts[stage] += 1
            break
    if match:
        flags = make_flags(match["gear_changes"])
        base.update(match)
        base.update(flags)
        base["join_stage"] = match_stage
        base["join_confidence"] = "HIGH" if match_stage == "FULL_DATE_TRACK_RACE_HORSE" else ("MEDIUM" if match_stage == "TRACK_RACE_HORSE" else "LOW")
    else:
        base.update({
            "gear_changes": "",
            "raw_gear_changes": "",
            "gear_source": "",
            "gear_checked_at": "",
            "gear_source_race_date": "",
            "gear_source_track": "",
            "gear_source_race_no": "",
            "gear_source_horse": "",
            "gear_source_horse_key": "",
            "gear_change_count": 0,
            "first_time_gear_count": 0,
            "gear_has_blinkers": "NO",
            "gear_has_tongue_tie": "NO",
            "gear_has_winkers": "NO",
            "gear_has_lugging_bit": "NO",
            "gear_has_nose_band": "NO",
            "gear_has_ear_muffs": "NO",
            "gear_has_gelded": "NO",
            "gear_has_off": "NO",
            "gear_has_again": "NO",
            "join_stage": "NO_MATCH" if not unsafe_stage else "UNSAFE_MANY_TO_MANY_REJECTED",
            "join_confidence": "NONE",
        })
        unmatched.append({
            "race_date": clean(r.get("race_date", "")),
            "track": clean(r.get("track", "")),
            "race_no": clean(r.get("race_no", "")),
            "horse": clean(r.get("horse", "")),
            "horse_key": clean(r.get("horse_key", "")),
            "unmatched_reason": base["join_stage"],
            "unsafe_stage": unsafe_stage,
        })
    out_rows.append(base)

out = pd.DataFrame(out_rows)
out.to_csv(OUT, index=False)
pd.DataFrame(unmatched).to_csv(UNMATCHED, index=False)
matched = int((out["join_stage"] != "NO_MATCH").sum() - (out["join_stage"] == "UNSAFE_MANY_TO_MANY_REJECTED").sum()) if "join_stage" in out.columns else 0
summary_rows = [
    {"metric": "live_rows", "value": len(live)},
    {"metric": "gear_source_rows", "value": len(gear)},
    {"metric": "matched_rows", "value": matched},
    {"metric": "unmatched_rows", "value": int((out["join_stage"] == "NO_MATCH").sum())},
    {"metric": "unsafe_many_to_many_rejected", "value": int((out["join_stage"] == "UNSAFE_MANY_TO_MANY_REJECTED").sum())},
    {"metric": "safe_to_apply", "value": "YES" if matched > 0 and len(out) == len(live) else "NO"},
]
for k, v in stage_counts.items():
    summary_rows.append({"metric": f"matched_{k}", "value": v})
summary_rows.extend([
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
REPORT.write_text("\n".join([
    "EDGEIQ_CURRENT_GEAR_LIVE_JOIN_V1",
    "=================================",
    f"Live rows: {len(live)}",
    f"Gear source rows: {len(gear)}",
    f"Matched rows: {matched}",
    f"Unmatched rows: {int((out['join_stage'] == 'NO_MATCH').sum())}",
    f"Unsafe many-to-many rejected: {int((out['join_stage'] == 'UNSAFE_MANY_TO_MANY_REJECTED').sum())}",
    f"Stage counts: {stage_counts}",
    f"Safe to apply: {'YES' if matched > 0 and len(out) == len(live) else 'NO'}",
    "Production changed: NO",
    "Pricing changed: NO",
]) + "\n", encoding="utf-8")
print("CURRENT_GEAR_LIVE_JOIN_COMPLETE", matched, len(unmatched))
