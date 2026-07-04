from __future__ import annotations

import re
from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

FIELDS = DATA / "race_fields.csv"
FORM = ROOT.parent.parent / "outputs" / "ra_careers" / "ra_horse_runs.csv"
OUT = DATA / "speed_map_report.csv"
AUDIT = DATA / "speed_map_coverage_audit.csv"

def clean_key(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([A-Z]{2,4}\)", "", s)
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def num(x):
    try:
        if pd.isna(x):
            return None
        s = str(x).replace(",", "").strip()
        if not s or s.lower() in {"nan", "none", "null", "-", "—"}:
            return None
        v = float(s)
        return v if pd.notna(v) else None
    except Exception:
        return None

def bucket_from_positions(avg800, avg400, runs):
    if runs <= 0:
        return None
    early = avg800 if avg800 is not None else avg400
    if early is None:
        return None
    if early <= 3.25:
        return "LEADER"
    if early <= 5.25:
        return "ON PACE"
    if early <= 8.0:
        return "MIDFIELD"
    return "BACKMARKER"

def elite_fallback_style(barrier, field_size, horse_no, official_runs_found, avg_rating):
    barrier = num(barrier)
    field_size = num(field_size)
    horse_no = num(horse_no)
    avg_rating = num(avg_rating)

    if official_runs_found <= 0:
        if barrier is not None and field_size is not None:
            if barrier <= 2 and field_size >= 10:
                return "ON PACE", "FALLBACK: inside draw/no position data"
            if barrier >= max(10, field_size - 2):
                return "BACKMARKER", "FALLBACK: wide draw/no position data"
        return "MIDFIELD", "FALLBACK: neutral/no position data"

    if barrier is not None:
        if barrier <= 3:
            return "ON PACE", "FALLBACK: inside draw with official runs"
        if field_size is not None and barrier >= max(10, field_size - 2):
            return "BACKMARKER", "FALLBACK: wide draw with official runs"

    if avg_rating is not None:
        if avg_rating >= 72:
            return "ON PACE", "FALLBACK: strong rating profile"
        if avg_rating <= 50:
            return "BACKMARKER", "FALLBACK: weak/unknown rating profile"

    return "MIDFIELD", "FALLBACK: neutral profile"

def confidence(runs, source):
    if runs >= 5:
        return "HIGH"
    if runs >= 3:
        return "MEDIUM"
    if runs >= 1:
        return "LOW"
    if source.startswith("FALLBACK"):
        return "FALLBACK"
    return "LOW"

def comment(bucket, barrier, source):
    if source.startswith("FALLBACK"):
        return source
    barrier = num(barrier)
    if bucket == "LEADER":
        if barrier is not None and barrier <= 4:
            return "Likely leader from a soft draw"
        return "Likely leader / early speed"
    if bucket == "ON PACE":
        return "Maps on pace from the draw"
    if bucket == "MIDFIELD":
        return "Likely midfield run"
    if bucket == "BACKMARKER":
        return "Likely to settle back"
    return ""

fields = pd.read_csv(FIELDS, low_memory=False)
form = pd.read_csv(FORM, low_memory=False)

fields["horse_key_norm"] = fields["horse"].apply(clean_key)
form["horse_key_norm"] = form["horse"].apply(clean_key)

form["run_date_dt"] = pd.to_datetime(form.get("run_date"), errors="coerce")

if "is_official_race" in form.columns:
    form["official_flag"] = pd.to_numeric(form["is_official_race"], errors="coerce").fillna(0).astype(int)
else:
    rt = form.get("run_type", "").astype(str).str.upper().str.strip()
    form["official_flag"] = (rt == "RACE").astype(int)

form = form[form["official_flag"] == 1].copy()

form["pos800_num"] = form.get("pos_800", "").map(num)
form["pos400_num"] = form.get("pos_400", "").map(num)

rating_col = "run_rating" if "run_rating" in form.columns else "rating" if "rating" in form.columns else None
if rating_col:
    form["rating_num"] = pd.to_numeric(form[rating_col], errors="coerce")
else:
    form["rating_num"] = None

rows = []

for _, runner in fields.iterrows():
    hk = runner["horse_key_norm"]

    horse_runs = form[form["horse_key_norm"] == hk].sort_values("run_date_dt", ascending=False).head(5)

    pos800 = [x for x in horse_runs["pos800_num"].tolist() if x is not None and x == x]
    pos400 = [x for x in horse_runs["pos400_num"].tolist() if x is not None and x == x]

    avg800 = sum(pos800) / len(pos800) if pos800 else None
    avg400 = sum(pos400) / len(pos400) if pos400 else None
    avg_rating = horse_runs["rating_num"].dropna().mean() if "rating_num" in horse_runs.columns else None

    runs_used = max(len(pos800), len(pos400))
    official_runs_found = len(horse_runs)

    bucket = bucket_from_positions(avg800, avg400, runs_used)
    source = "POSITIONAL"

    if bucket is None:
        bucket, source = elite_fallback_style(
            runner.get("barrier"),
            runner.get("field_size"),
            runner.get("horse_no"),
            official_runs_found,
            avg_rating,
        )

    rows.append({
        "race_date": runner.get("race_date"),
        "track": runner.get("track"),
        "race_no": runner.get("race_no"),
        "horse_no": runner.get("horse_no"),
        "horse": runner.get("horse"),
        "horse_key": hk,
        "barrier": runner.get("barrier"),
        "avg_800_pos": round(avg800, 2) if avg800 is not None else None,
        "avg_400_pos": round(avg400, 2) if avg400 is not None else None,
        "avg_recent_rating": round(float(avg_rating), 2) if avg_rating is not None and pd.notna(avg_rating) else None,
        "runs_used": runs_used,
        "official_runs_found": official_runs_found,
        "style_source": source,
        "last3_800_positions": ",".join(str(int(x)) for x in pos800[:3]),
        "last3_400_positions": ",".join(str(int(x)) for x in pos400[:3]),
        "speed_map_bucket": bucket,
        "confidence": confidence(runs_used, source),
        "pace_pressure": "",
        "map_style": bucket,
        "map_comment": comment(bucket, runner.get("barrier"), source),
    })

out = pd.DataFrame(rows)

audit_rows = []

for (race_date, track, race_no), g in out.groupby(["race_date", "track", "race_no"], dropna=False):
    leaders = int((g["speed_map_bucket"] == "LEADER").sum())
    onpace = int((g["speed_map_bucket"] == "ON PACE").sum())
    pressure_score = leaders * 2 + onpace

    if pressure_score <= 2:
        pressure = "LOW"
    elif pressure_score <= 5:
        pressure = "MODERATE"
    else:
        pressure = "HIGH"

    mask = (
        (out["race_date"] == race_date) &
        (out["track"] == track) &
        (out["race_no"] == race_no)
    )
    out.loc[mask, "pace_pressure"] = pressure

    audit_rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "runners": len(g),
        "leaders": leaders,
        "onpace": onpace,
        "pressure_score": pressure_score,
        "pace_pressure": pressure,
        "positional_styles": int((g["style_source"] == "POSITIONAL").sum()),
        "fallback_styles": int((g["style_source"] != "POSITIONAL").sum()),
    })

out.to_csv(OUT, index=False)
pd.DataFrame(audit_rows).to_csv(AUDIT, index=False)

print("ELITE FALLBACK SPEED MAP BUILT")
print("rows:", len(out))
print("races:", out.groupby(["race_date", "track", "race_no"]).ngroups)
print()
print("STYLE DISTRIBUTION:")
print(out["speed_map_bucket"].value_counts(dropna=False).to_string())
print()
print("STYLE SOURCE:")
print(out["style_source"].value_counts(dropna=False).to_string())
print()
print(out.head(40).to_string(index=False))
