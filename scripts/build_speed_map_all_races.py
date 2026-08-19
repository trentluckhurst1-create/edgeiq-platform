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

STYLE_ORDER = ["BACKMARKER", "MIDFIELD", "ON PACE", "LEADER"]

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

def style_shift(style, steps):
    if style not in STYLE_ORDER:
        return style
    i = STYLE_ORDER.index(style)
    return STYLE_ORDER[max(0, min(len(STYLE_ORDER) - 1, i + steps))]

def positional_style(avg800, avg400, valid_runs):
    if valid_runs <= 0:
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

def fallback_style(barrier, field_size, official_runs_found, avg_rating):
    b = num(barrier)
    fs = num(field_size)
    rating = num(avg_rating)

    style = "MIDFIELD"
    source = "PRO_FALLBACK_NEUTRAL"
    confidence = "FALLBACK"

    if b is not None and fs is not None and fs > 0:
        pct = b / fs

        if pct <= 0.16:
            style = "LEADER"
            source = "PRO_FALLBACK_BARRIER_INSIDE"
            confidence = "BARRIER_STRONG"
        elif pct <= 0.34:
            style = "ON PACE"
            source = "PRO_FALLBACK_BARRIER_FORWARD"
            confidence = "BARRIER"
        elif pct >= 0.82:
            style = "BACKMARKER"
            source = "PRO_FALLBACK_BARRIER_WIDE"
            confidence = "BARRIER_STRONG"
        elif pct >= 0.68:
            style = "BACKMARKER"
            source = "PRO_FALLBACK_BARRIER_BACK"
            confidence = "BARRIER"
        else:
            style = "MIDFIELD"
            source = "PRO_FALLBACK_BARRIER_NEUTRAL"
            confidence = "FALLBACK"

        if fs >= 14 and pct >= 0.65:
            style = style_shift(style, -1)
            source = source + "_BIG_FIELD_WIDE"

        if fs <= 8 and pct <= 0.25:
            style = style_shift(style, 1)
            source = source + "_SMALL_FIELD_INSIDE"

    if rating is not None:
        if rating >= 75:
            style = style_shift(style, 1)
            source = source + "_RATING_FORWARD"
        elif rating <= 55:
            style = style_shift(style, -1)
            source = source + "_RATING_BACK"

    if official_runs_found <= 0:
        if style == "MIDFIELD" and b is not None and fs is not None and b <= max(3, fs * 0.25):
            style = "ON PACE"
            source = source + "_UNKNOWN_INSIDE_FORWARD"
        elif style == "MIDFIELD":
            source = source + "_UNKNOWN_NEUTRAL"

    return style, source, confidence

def position_confidence(valid_runs):
    if valid_runs >= 5:
        return "POSITIONAL_HIGH"
    if valid_runs >= 3:
        return "POSITIONAL_MEDIUM"
    if valid_runs >= 1:
        return "POSITIONAL_LOW"
    return "FALLBACK"

def map_comment(style, source, barrier, field_size):
    if source.startswith("POSITIONAL"):
        if style == "LEADER":
            return "Position data: likely leader"
        if style == "ON PACE":
            return "Position data: maps forward"
        if style == "MIDFIELD":
            return "Position data: midfield pattern"
        if style == "BACKMARKER":
            return "Position data: settles back"

    b = num(barrier)
    fs = num(field_size)
    draw = ""
    if b is not None and fs is not None and fs > 0:
        draw = f" barrier {int(b)}/{int(fs)}"

    return f"{source}{draw}"

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

rating_col = "run_rating" if "run_rating" in form.columns else "rating" if "rating" in form.columns else ""
if rating_col:
    form["rating_num"] = pd.to_numeric(form[rating_col], errors="coerce")
else:
    form["rating_num"] = pd.NA

rows = []

for _, runner in fields.iterrows():
    hk = runner["horse_key_norm"]

    horse_runs = form[form["horse_key_norm"] == hk].sort_values("run_date_dt", ascending=False).head(5)

    pos800 = [x for x in horse_runs["pos800_num"].tolist() if x is not None and x == x]
    pos400 = [x for x in horse_runs["pos400_num"].tolist() if x is not None and x == x]

    avg800 = sum(pos800) / len(pos800) if pos800 else None
    avg400 = sum(pos400) / len(pos400) if pos400 else None
    avg_rating = horse_runs["rating_num"].dropna().mean() if "rating_num" in horse_runs.columns else None

    valid_runs = max(len(pos800), len(pos400))
    official_runs_found = len(horse_runs)

    style = positional_style(avg800, avg400, valid_runs)

    if style:
        source = "POSITIONAL"
        conf = position_confidence(valid_runs)
    else:
        style, source, conf = fallback_style(
            runner.get("barrier"),
            runner.get("field_size"),
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
        "field_size": runner.get("field_size"),
        "avg_800_pos": round(avg800, 2) if avg800 is not None else None,
        "avg_400_pos": round(avg400, 2) if avg400 is not None else None,
        "avg_recent_rating": round(float(avg_rating), 2) if avg_rating is not None and pd.notna(avg_rating) else None,
        "runs_used": valid_runs,
        "official_runs_found": official_runs_found,
        "style_source": source,
        "last3_800_positions": ",".join(str(int(x)) for x in pos800[:3]),
        "last3_400_positions": ",".join(str(int(x)) for x in pos400[:3]),
        "speed_map_bucket": style,
        "confidence": conf,
        "pace_pressure": "",
        "map_style": style,
        "map_comment": map_comment(style, source, runner.get("barrier"), runner.get("field_size")),
    })

out = pd.DataFrame(rows)

audit_rows = []

for (race_date, track, race_no), g in out.groupby(["race_date", "track", "race_no"], dropna=False):
    leaders = int((g["speed_map_bucket"] == "LEADER").sum())
    onpace = int((g["speed_map_bucket"] == "ON PACE").sum())
    midfield = int((g["speed_map_bucket"] == "MIDFIELD").sum())
    backmarkers = int((g["speed_map_bucket"] == "BACKMARKER").sum())

    pressure_score = leaders * 2 + onpace

    if pressure_score <= 2:
        pressure = "LOW"
    elif pressure_score <= 5:
        pressure = "MODERATE"
    elif pressure_score <= 9:
        pressure = "HIGH"
    else:
        pressure = "EXTREME"

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
        "midfield": midfield,
        "backmarkers": backmarkers,
        "pressure_score": pressure_score,
        "pace_pressure": pressure,
        "positional_styles": int((g["style_source"] == "POSITIONAL").sum()),
        "fallback_styles": int((g["style_source"] != "POSITIONAL").sum()),
    })

out.to_csv(OUT, index=False)
pd.DataFrame(audit_rows).to_csv(AUDIT, index=False)

print("PRO STYLE SPEED MAP BUILT")
print("rows:", len(out))
print("races:", out.groupby(["race_date", "track", "race_no"]).ngroups)
print()
print("STYLE DISTRIBUTION:")
print(out["speed_map_bucket"].value_counts(dropna=False).to_string())
print()
print("STYLE SOURCE:")
print(out["style_source"].value_counts(dropna=False).to_string())
print()
print("CONFIDENCE:")
print(out["confidence"].value_counts(dropna=False).to_string())
print()
print(out.head(50).to_string(index=False))
