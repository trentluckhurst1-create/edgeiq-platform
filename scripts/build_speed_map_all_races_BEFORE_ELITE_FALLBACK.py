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


def txt(x):
    if pd.isna(x):
        return ""
    s = str(x).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


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
        return "MIDFIELD"
    early = avg800 if avg800 is not None else avg400
    if early is None:
        return "MIDFIELD"
    if early <= 3.25:
        return "LEADER"
    if early <= 5.25:
        return "ON PACE"
    if early <= 8.0:
        return "MIDFIELD"
    return "BACKMARKER"


def confidence(runs):
    if runs >= 5:
        return "HIGH"
    if runs >= 3:
        return "MEDIUM"
    if runs >= 1:
        return "LOW"
    return "LOW"


def comment(bucket, barrier):
    if bucket == "FIRST START":
        return "FIRST START / NO OFFICIAL FORM"
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




form["run_date_dt"] = pd.to_datetime(form.get("run_date"), errors="coerce")

if "is_official_race" in form.columns:
    form["official_flag"] = pd.to_numeric(form["is_official_race"], errors="coerce").fillna(0).astype(int)
else:
    rt = form.get("run_type", "").astype(str).str.upper().str.strip()
    rc = form.get("race_class", "").astype(str).str.upper()
    sp = form.get("sp_text", form.get("starting_price", "")).astype(str).str.upper()
    form["official_flag"] = ((rt == "RACE") & ~rc.str.contains("BT|TRIAL|JUMP", na=False) & ~sp.eq("$000")).astype(int)

form = form[form["official_flag"] == 1].copy()

form["pos800_num"] = form.get("pos_800", "").map(num)
form["pos400_num"] = form.get("pos_400", "").map(num)

rows = []

for _, runner in fields.iterrows():
    hk = str(runner.get("horse_key", "")).replace("’","").replace("'","").strip().upper()

    horse_runs = form[form["horse_key"].astype(str).str.upper().str.strip() == hk.strip().upper()].sort_values("run_date_dt", ascending=False).head(5)

    pos800 = [x for x in horse_runs["pos800_num"].tolist() if x is not None and x == x]
    pos400 = [x for x in horse_runs["pos400_num"].tolist() if x is not None and x == x]

    avg800 = sum(pos800) / len(pos800) if pos800 else None
    avg400 = sum(pos400) / len(pos400) if pos400 else None
    runs_used = max(len(pos800), len(pos400))
    official_runs_found = len(horse_runs)

    bucket = bucket_from_positions(avg800, avg400, runs_used)
    barrier = num(runner.get("barrier"))

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
        "runs_used": runs_used,
        "official_runs_found": official_runs_found,
        "last3_800_positions": ",".join(str(int(x)) for x in pos800[:3]),
        "last3_400_positions": ",".join(str(int(x)) for x in pos400[:3]),
        "speed_map_bucket": bucket,
        "confidence": confidence(runs_used),
        "pace_pressure": "",
        "map_style": bucket,
        "map_comment": comment(bucket, barrier),
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
        "with_style": int((g["speed_map_bucket"] != "FIRST START").sum()),
        "first_start_or_no_form": int((g["speed_map_bucket"] == "FIRST START").sum()),
    })

out.to_csv(OUT, index=False)
pd.DataFrame(audit_rows).to_csv(AUDIT, index=False)

print("AUTO SPEED MAP REPORT BUILT")
print("rows:", len(out))
print("races:", out.groupby(["race_date", "track", "race_no"]).ngroups)
print("wrote:", OUT)
print("wrote:", AUDIT)
print()
print(out["speed_map_bucket"].value_counts(dropna=False).to_string())
print()
print(out.head(30).to_string(index=False))
