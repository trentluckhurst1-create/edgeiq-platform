from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE = DATA / "racingcom_sectional_warehouse_v2.csv"
PROFILES = DATA / "edgeiq_sectional_profiles_v2.csv"
LAYOUT_B = DATA / "racingcom_layout_b_derived_metrics_v1.csv"

OUT = DATA / "edgeiq_sectional_ability_engine_v1.csv"
AUDIT = DATA / "edgeiq_sectional_ability_engine_v1_audit.csv"

OUT_COLS = [
    "horse_key",
    "horse_name",
    "runs_with_sectionals",
    "layout_a_runs",
    "layout_b_runs",
    "peak_speed_score",
    "closing_speed_score",
    "sustained_speed_score",
    "sectional_ability_score",
    "sectional_class",
    "percentile_rank",
    "ability_status",
]

AUDIT_COLS = [
    "warehouse_rows_loaded",
    "profiles_loaded",
    "layout_b_rows_loaded",
    "ability_rows",
    "world_class",
    "elite",
    "very_strong",
    "above_average",
    "competitive",
    "average",
    "limited",
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


def num(v):
    m = re.search(r"-?\d+(?:\.\d+)?", clean(v))
    return float(m.group(0)) if m else None


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


def pick(row, keys, default=""):
    for key in keys:
        value = clean(row.get(key))
        if value:
            return value
    return default


def percentile(value, values):
    usable = sorted(v for v in values if v is not None and math.isfinite(v))
    if value is None or not usable:
        return 0.0
    below = sum(1 for v in usable if v < value)
    equal = sum(1 for v in usable if v == value)
    return round(((below + 0.5 * equal) / len(usable)) * 100, 2)


def inverse_percentile(value, values):
    if value is None:
        return 0.0
    return round(100 - percentile(value, values), 2)


def avg(values):
    usable = [v for v in values if v is not None and math.isfinite(v)]
    return mean(usable) if usable else None


def consistency_score(values):
    usable = [v for v in values if v is not None and math.isfinite(v)]
    if len(usable) < 2:
        return None
    m = mean(usable)
    if m <= 0:
        return None
    cv = pstdev(usable) / m
    return max(0.0, min(100.0, 100.0 - (cv * 450.0)))


def class_band(score):
    if score >= 95:
        return "WORLD_CLASS"
    if score >= 90:
        return "ELITE"
    if score >= 80:
        return "VERY_STRONG"
    if score >= 70:
        return "ABOVE_AVERAGE"
    if score >= 60:
        return "COMPETITIVE"
    if score >= 50:
        return "AVERAGE"
    return "LIMITED"


def fmt(v):
    if v is None:
        return ""
    return round(float(v), 2)


def main():
    warehouse = read_csv(WAREHOUSE)
    profiles = read_csv(PROFILES)
    layout_b = read_csv(LAYOUT_B)

    by_horse = defaultdict(lambda: {
        "horse_name": "",
        "peak": [],
        "late": [],
        "early": [],
        "mid": [],
        "avg": [],
        "layout_a_runs": set(),
        "layout_b_runs": set(),
        "closing_rank": [],
        "early_rank": [],
        "late_delta": [],
        "split_consistency": [],
    })

    profile_by_horse = {}

    for row in profiles:
        hk = key_text(pick(row, ["horse_key"]))
        if hk:
            profile_by_horse[hk] = row

    for row in warehouse:
        hk = key_text(pick(row, ["horse_key"]))
        if not hk:
            continue
        h = by_horse[hk]
        h["horse_name"] = h["horse_name"] or pick(row, ["horse_name"])
        run_id = "|".join([
            pick(row, ["meeting_date"]),
            key_text(pick(row, ["track"])),
            pick(row, ["race_no"]),
        ])

        peak = num(row.get("peak_speed"))
        late = num(row.get("late_speed"))
        early = num(row.get("early_speed"))
        mid = num(row.get("mid_speed"))
        average = num(row.get("avg_speed"))

        if peak is not None or late is not None or early is not None or mid is not None or average is not None:
            h["layout_a_runs"].add(run_id)

        h["peak"].append(peak)
        h["late"].append(late)
        h["early"].append(early)
        h["mid"].append(mid)
        h["avg"].append(average)

    for row in layout_b:
        hk = key_text(pick(row, ["horse_key"]))
        if not hk:
            continue
        h = by_horse[hk]
        h["horse_name"] = h["horse_name"] or pick(row, ["horse_name"])
        run_id = "|".join([
            pick(row, ["meeting_date"]),
            key_text(pick(row, ["track"])),
            pick(row, ["race_no"]),
        ])
        h["layout_b_runs"].add(run_id)

        h["closing_rank"].append(num(row.get("closing_rank_within_race")))
        h["early_rank"].append(num(row.get("early_rank_within_race")))
        h["late_delta"].append(num(row.get("late_vs_early_delta")))
        h["split_consistency"].append(num(row.get("split_consistency_score")))

    horse_metrics = {}

    for hk, h in by_horse.items():
        profile = profile_by_horse.get(hk, {})
        profile_runs = num(profile.get("runs_with_sectionals"))
        layout_a_runs = len(h["layout_a_runs"])
        layout_b_runs = len(h["layout_b_runs"])
        runs = int(profile_runs or max(layout_a_runs + layout_b_runs, len(h["layout_a_runs"] | h["layout_b_runs"])))

        avg_peak = avg(h["peak"])
        avg_late = avg(h["late"])
        avg_early = avg(h["early"])
        avg_mid = avg(h["mid"])
        avg_avg = avg(h["avg"])

        avg_closing_rank = avg(h["closing_rank"])
        avg_early_rank = avg(h["early_rank"])
        avg_late_delta = avg(h["late_delta"])
        avg_split_consistency = avg(h["split_consistency"])
        speed_consistency = consistency_score([v for v in h["avg"] if v is not None])

        horse_metrics[hk] = {
            "horse_key": hk,
            "horse_name": h["horse_name"] or pick(profile, ["horse_name"]),
            "runs": runs,
            "layout_a_runs": layout_a_runs,
            "layout_b_runs": layout_b_runs,
            "avg_peak": avg_peak,
            "avg_late": avg_late,
            "avg_early": avg_early,
            "avg_mid": avg_mid,
            "avg_avg": avg_avg,
            "avg_closing_rank": avg_closing_rank,
            "avg_early_rank": avg_early_rank,
            "avg_late_delta": avg_late_delta,
            "avg_split_consistency": avg_split_consistency,
            "speed_consistency": speed_consistency,
        }

    peak_values = [m["avg_peak"] for m in horse_metrics.values() if m["avg_peak"] is not None]
    late_values = [m["avg_late"] for m in horse_metrics.values() if m["avg_late"] is not None]
    avg_values = [m["avg_avg"] for m in horse_metrics.values() if m["avg_avg"] is not None]
    closing_rank_values = [m["avg_closing_rank"] for m in horse_metrics.values() if m["avg_closing_rank"] is not None]
    early_rank_values = [m["avg_early_rank"] for m in horse_metrics.values() if m["avg_early_rank"] is not None]
    late_delta_values = [m["avg_late_delta"] for m in horse_metrics.values() if m["avg_late_delta"] is not None]
    consistency_values = [m["avg_split_consistency"] for m in horse_metrics.values() if m["avg_split_consistency"] is not None]
    speed_consistency_values = [m["speed_consistency"] for m in horse_metrics.values() if m["speed_consistency"] is not None]

    out = []

    for hk, m in horse_metrics.items():
        peak_score_parts = []
        closing_score_parts = []
        sustained_score_parts = []

        if m["avg_peak"] is not None:
            peak_score_parts.append(percentile(m["avg_peak"], peak_values))
        if m["avg_avg"] is not None:
            peak_score_parts.append(percentile(m["avg_avg"], avg_values) * 0.55)

        if m["avg_late"] is not None:
            closing_score_parts.append(percentile(m["avg_late"], late_values))
        if m["avg_closing_rank"] is not None:
            closing_score_parts.append(inverse_percentile(m["avg_closing_rank"], closing_rank_values))
        if m["avg_late_delta"] is not None:
            closing_score_parts.append(inverse_percentile(m["avg_late_delta"], late_delta_values))

        if m["avg_avg"] is not None:
            sustained_score_parts.append(percentile(m["avg_avg"], avg_values))
        if m["speed_consistency"] is not None:
            sustained_score_parts.append(percentile(m["speed_consistency"], speed_consistency_values))
        if m["avg_split_consistency"] is not None:
            sustained_score_parts.append(percentile(m["avg_split_consistency"], consistency_values))
        if m["avg_early_rank"] is not None:
            sustained_score_parts.append(inverse_percentile(m["avg_early_rank"], early_rank_values) * 0.65)

        peak_score = avg(peak_score_parts)
        closing_score = avg(closing_score_parts)
        sustained_score = avg(sustained_score_parts)

        usable_scores = []
        if peak_score is not None:
            usable_scores.append(("peak", peak_score, 0.35))
        if closing_score is not None:
            usable_scores.append(("closing", closing_score, 0.35))
        if sustained_score is not None:
            usable_scores.append(("sustained", sustained_score, 0.30))

        if usable_scores:
            weight_total = sum(w for _, _, w in usable_scores)
            ability = sum(score * w for _, score, w in usable_scores) / weight_total
        else:
            ability = 0.0

        if m["runs"] <= 1:
            status = "LOW_SAMPLE"
            ability = min(ability, 62.0)
        elif m["runs"] < 3:
            status = "EARLY_SAMPLE"
            ability = min(ability, 74.0)
        elif m["runs"] < 5:
            status = "EARLY_PROFILE"
        else:
            status = "STRONG_PROFILE"

        out.append({
            "horse_key": hk,
            "horse_name": m["horse_name"],
            "runs_with_sectionals": m["runs"],
            "layout_a_runs": m["layout_a_runs"],
            "layout_b_runs": m["layout_b_runs"],
            "peak_speed_score": fmt(peak_score),
            "closing_speed_score": fmt(closing_score),
            "sustained_speed_score": fmt(sustained_score),
            "sectional_ability_score": fmt(ability),
            "sectional_class": class_band(ability),
            "percentile_rank": "",
            "ability_status": status,
        })

    ability_values = [num(r["sectional_ability_score"]) for r in out if num(r["sectional_ability_score"]) is not None]

    for row in out:
        row["percentile_rank"] = fmt(percentile(num(row["sectional_ability_score"]), ability_values))

    out.sort(key=lambda r: (-(num(r["sectional_ability_score"]) or 0), r["horse_name"]))

    audit = [{
        "warehouse_rows_loaded": len(warehouse),
        "profiles_loaded": len(profiles),
        "layout_b_rows_loaded": len(layout_b),
        "ability_rows": len(out),
        "world_class": sum(1 for r in out if r["sectional_class"] == "WORLD_CLASS"),
        "elite": sum(1 for r in out if r["sectional_class"] == "ELITE"),
        "very_strong": sum(1 for r in out if r["sectional_class"] == "VERY_STRONG"),
        "above_average": sum(1 for r in out if r["sectional_class"] == "ABOVE_AVERAGE"),
        "competitive": sum(1 for r in out if r["sectional_class"] == "COMPETITIVE"),
        "average": sum(1 for r in out if r["sectional_class"] == "AVERAGE"),
        "limited": sum(1 for r in out if r["sectional_class"] == "LIMITED"),
        "final_status": "SECTIONAL_ABILITY_ENGINE_BUILT" if out else "NO_ABILITY_ROWS",
    }]

    write_csv(OUT, out, OUT_COLS)
    write_csv(AUDIT, audit, AUDIT_COLS)

    print("EDGEiQ Sectional Ability Engine V1 built")
    print(f"ability_rows={len(out)}")
    print(f"world_class={audit[0]['world_class']}")
    print(f"elite={audit[0]['elite']}")
    print(f"very_strong={audit[0]['very_strong']}")
    print(f"final_status={audit[0]['final_status']}")


if __name__ == "__main__":
    main()
