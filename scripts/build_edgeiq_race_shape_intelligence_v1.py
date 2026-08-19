from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SPEED_SOURCES = [
    DATA / "edgeiq_real_speed_map_positions.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
]

SECTIONAL_SRC = DATA / "edgeiq_live_sectional_intelligence_v1.csv"

OUT = DATA / "edgeiq_race_shape_intelligence_v1.csv"
AUDIT = DATA / "edgeiq_race_shape_intelligence_v1_audit.csv"

OUT_COLS = [
    "meeting_date",
    "track",
    "race_no",
    "horse_name",
    "horse_key",
    "runner_number",
    "sectional_archetype",
    "profile_depth_status",
    "sectional_evidence_type",
    "runs_with_sectionals",
    "run_style",
    "settling_band",
    "speed_map_bucket",
    "map_x_pct",
    "race_shape",
    "pressure_rating",
    "collapse_risk",
    "tactical_advantage",
    "tactical_reason",
    "race_shape_score",
]

AUDIT_COLS = [
    "speed_rows_loaded",
    "sectional_rows_loaded",
    "output_rows",
    "races_loaded",
    "horses_loaded",
    "positive_advantages",
    "neutral_advantages",
    "negative_advantages",
    "fast_races",
    "neutral_races",
    "slow_races",
    "high_pressure_races",
    "final_status",
]


def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    if s.upper() in {"NAN", "NONE", "NULL", "NA", "N/A", "-"}:
        return ""
    return re.sub(r"\s+", " ", s)


def key_text(v):
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())


def horse_key(row):
    for c in ["horse_key", "runner_key", "horse", "horse_name", "runner_name", "runner"]:
        v = clean(row.get(c))
        if v:
            if c == "runner_key" and "_" in v:
                return key_text(v.split("_")[-1])
            return key_text(re.sub(r"\s*\((NZ|IRE|GB|FR|USA|JPN|GER|SAF)\)\s*$", "", v, flags=re.I))
    return ""


def pick(row, cols, default=""):
    for c in cols:
        v = clean(row.get(c))
        if v:
            return v
    return default


def num(v, default=0.0):
    m = re.search(r"-?\d+(?:\.\d+)?", clean(v))
    return float(m.group(0)) if m else default


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def race_key(row):
    date = pick(row, ["meeting_date", "race_date", "date"])
    track = key_text(pick(row, ["track", "track_name", "venue"]))
    race_no = re.sub(r"[^0-9]", "", pick(row, ["race_no", "race_number", "race"]))
    return f"{date}|{track}|{race_no}"


def runner_no(row):
    return re.sub(r"[^0-9]", "", pick(row, ["runner_number", "horse_no", "saddlecloth", "number", "runner_no", "no"]))


def band(row):
    raw = " ".join([
        pick(row, ["settling_band"]),
        pick(row, ["speed_map_bucket"]),
        pick(row, ["run_style"]),
        pick(row, ["pace_profile"]),
        pick(row, ["map_position"]),
    ]).upper()

    if "LEADER" in raw:
        return "LEADER"
    if "ON" in raw and "PACE" in raw:
        return "ON_PACE"
    if "PACE" in raw and "OFF" not in raw:
        return "ON_PACE"
    if "MID" in raw:
        return "MIDFIELD"
    if "OFF" in raw:
        return "OFF_PACE"
    if "BACK" in raw or "CLOS" in raw:
        return "BACKMARKER"

    x = num(row.get("map_x_pct"), -1)
    if x >= 0:
        if x <= 28:
            return "LEADER"
        if x <= 45:
            return "ON_PACE"
        if x <= 68:
            return "MIDFIELD"
        if x <= 82:
            return "OFF_PACE"
        return "BACKMARKER"

    return "UNKNOWN"


def classify_race(rows):
    counts = Counter(band(r) for r in rows)
    pressure_units = counts["LEADER"] * 2 + counts["ON_PACE"] * 1.25 + counts["OFF_PACE"] * 0.25
    field_size = max(1, len(rows))
    pressure_index = pressure_units / field_size

    if counts["LEADER"] >= 3 or pressure_index >= 0.75:
        shape = "FAST"
        pressure = "HIGH"
        collapse = "HIGH"
    elif counts["LEADER"] <= 1 and counts["ON_PACE"] <= 2 and pressure_index <= 0.42:
        shape = "SLOW"
        pressure = "LOW"
        collapse = "LOW"
    else:
        shape = "NEUTRAL"
        pressure = "MODERATE"
        collapse = "MEDIUM"

    return shape, pressure, collapse, counts


def tactical(row, shape, pressure, collapse):
    archetype = pick(row, ["sectional_archetype"]).upper()
    b = band(row)

    if not archetype or archetype in {"INSUFFICIENT_SAMPLE", "NO_PROFILE"}:
        return "NEUTRAL", "No reliable sectional profile yet.", 50

    positive = False
    negative = False
    reason = []

    if archetype in {"STRONG_CLOSER", "SPLIT_TIMING_CLOSER"}:
        if shape == "FAST" or collapse == "HIGH":
            positive = True
            reason.append("Closer profile suits pressure/collapse scenario.")
        elif shape == "SLOW":
            negative = True
            reason.append("Slow tempo may blunt closing profile.")

    if archetype in {"FAST_STARTER", "SPLIT_TIMING_SPEED"}:
        if pressure == "LOW" and b in {"LEADER", "ON_PACE"}:
            positive = True
            reason.append("Early speed profile can control a low-pressure race.")
        elif pressure == "HIGH":
            negative = True
            reason.append("Early speed profile may face pressure.")

    if archetype in {"PEAK_SPEED_HORSE"}:
        if shape in {"SLOW", "NEUTRAL"}:
            positive = True
            reason.append("Peak-speed profile suits sprint/turn-of-foot race shape.")
        elif collapse == "HIGH":
            negative = True
            reason.append("High-pressure race may test sustained speed.")

    if archetype in {"CONSISTENT_SECTIONALIST", "SUSTAINED_CRUISER"}:
        if shape in {"NEUTRAL", "FAST"}:
            positive = True
            reason.append("Consistent sectional profile suits honest tempo.")

    if archetype == "ONE_PACE_GRINDER":
        if shape == "FAST":
            negative = True
            reason.append("Fast pressure may expose one-pace profile.")
        else:
            reason.append("One-pace profile needs favourable tempo.")

    if positive and not negative:
        return "POSITIVE", " ".join(reason), 72
    if negative and not positive:
        return "NEGATIVE", " ".join(reason), 32
    if positive and negative:
        return "NEUTRAL", "Mixed sectional/tactical signals. " + " ".join(reason), 52
    return "NEUTRAL", "No clear sectional race-shape edge.", 50


def main():
    speed_rows = []
    speed_source_used = ""
    for src in SPEED_SOURCES:
        rows = read_csv(src)
        if rows:
            speed_rows = rows
            speed_source_used = src.name
            break

    sectional_rows = read_csv(SECTIONAL_SRC)

    sectional_by_race_horse = {}
    sectional_by_horse = {}

    for r in sectional_rows:
        hk = horse_key(r)
        if not hk:
            continue
        sectional_by_horse[hk] = r
        rk = race_key(r)
        sectional_by_race_horse[(rk, hk)] = r

    race_groups = defaultdict(list)
    for r in speed_rows:
        rk = race_key(r)
        hk = horse_key(r)
        if not rk or not hk:
            continue
        rr = dict(r)
        sec = sectional_by_race_horse.get((rk, hk)) or sectional_by_horse.get(hk) or {}
        for k, v in sec.items():
            if k not in rr or clean(rr.get(k)) == "":
                rr[k] = v
        race_groups[rk].append(rr)

    out = []

    for rk, rows in race_groups.items():
        shape, pressure, collapse, counts = classify_race(rows)
        for r in rows:
            adv, reason, score = tactical(r, shape, pressure, collapse)
            out.append({
                "meeting_date": pick(r, ["meeting_date", "race_date", "date"]),
                "track": pick(r, ["track", "track_name", "venue"]),
                "race_no": pick(r, ["race_no", "race_number", "race"]),
                "horse_name": pick(r, ["horse_name", "horse", "runner_name", "runner"]),
                "horse_key": horse_key(r),
                "runner_number": runner_no(r),
                "sectional_archetype": pick(r, ["sectional_archetype"], "NO_PROFILE"),
                "profile_depth_status": pick(r, ["profile_depth_status", "sectional_display_status"], "NO_PROFILE"),
                "sectional_evidence_type": pick(r, ["sectional_evidence_type"], "NO_PROFILE"),
                "runs_with_sectionals": pick(r, ["runs_with_sectionals"], "0"),
                "run_style": pick(r, ["run_style"]),
                "settling_band": pick(r, ["settling_band"]),
                "speed_map_bucket": pick(r, ["speed_map_bucket"]),
                "map_x_pct": pick(r, ["map_x_pct"]),
                "race_shape": shape,
                "pressure_rating": pressure,
                "collapse_risk": collapse,
                "tactical_advantage": adv,
                "tactical_reason": reason,
                "race_shape_score": score,
            })

    audit = [{
        "speed_rows_loaded": len(speed_rows),
        "sectional_rows_loaded": len(sectional_rows),
        "output_rows": len(out),
        "races_loaded": len(race_groups),
        "horses_loaded": len({r["horse_key"] for r in out if r.get("horse_key")}),
        "positive_advantages": sum(1 for r in out if r.get("tactical_advantage") == "POSITIVE"),
        "neutral_advantages": sum(1 for r in out if r.get("tactical_advantage") == "NEUTRAL"),
        "negative_advantages": sum(1 for r in out if r.get("tactical_advantage") == "NEGATIVE"),
        "fast_races": len({race_key(r) for r in out if r.get("race_shape") == "FAST"}),
        "neutral_races": len({race_key(r) for r in out if r.get("race_shape") == "NEUTRAL"}),
        "slow_races": len({race_key(r) for r in out if r.get("race_shape") == "SLOW"}),
        "high_pressure_races": len({race_key(r) for r in out if r.get("pressure_rating") == "HIGH"}),
        "final_status": "RACE_SHAPE_INTELLIGENCE_BUILT" if out else "NO_OUTPUT_ROWS",
    }]

    write_csv(OUT, out, OUT_COLS)
    write_csv(AUDIT, audit, AUDIT_COLS)

    print("EDGEiQ Race Shape Intelligence V1 built")
    print(f"speed_source_used={speed_source_used}")
    print(f"output_rows={len(out)}")
    print(f"races_loaded={len(race_groups)}")
    print(f"final_status={audit[0]['final_status']}")


if __name__ == "__main__":
    main()
