from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE = DATA / "racingcom_sectional_warehouse_v2.csv"
PROFILES = DATA / "edgeiq_sectional_profiles_v2.csv"
ABILITY = DATA / "edgeiq_sectional_ability_engine_v3.csv"

OUT = DATA / "edgeiq_tactical_dna_v1.csv"
AUDIT = DATA / "edgeiq_tactical_dna_v1_audit.csv"

OUT_COLS = [
    "built_at",
    "horse_key",
    "horse_name",
    "runs_used",
    "races_used",
    "leader_runs",
    "on_pace_runs",
    "midfield_runs",
    "backmarker_runs",
    "unknown_runs",
    "leader_pct",
    "on_pace_pct",
    "midfield_pct",
    "backmarker_pct",
    "unknown_pct",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "early_speed_rank_avg",
    "early_speed_percentile_avg",
    "tactical_speed_bucket",
    "tactical_position_group",
    "tempo_pressure_role",
    "sectional_archetype",
    "sectional_ability_score",
    "sectional_confidence_score",
    "sectional_reliability_rank",
    "dna_confidence",
    "bucket_confidence",
    "tactical_reason",
]

AUDIT_COLS = [
    "built_at",
    "warehouse_rows_loaded",
    "profiles_loaded",
    "ability_rows_loaded",
    "output_horses",
    "leader_horses",
    "on_pace_horses",
    "midfield_horses",
    "backmarker_horses",
    "unknown_horses",
    "high_confidence",
    "medium_confidence",
    "low_confidence",
    "insufficient_confidence",
    "final_status",
]


def clean(v):
    return "" if v is None else str(v).strip()


def n(v, default=0.0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def pct(part, whole):
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 2)


def avg(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 2)


def horse_key_text(v):
    return re.sub(r"[^A-Z0-9]+", "", re.sub(r"\([^)]*\)", "", clean(v).upper()))


def horse_key(row):
    return horse_key_text(
        row.get("horse_key")
        or row.get("horse")
        or row.get("horse_name")
        or row.get("runner_name")
    )


def horse_name(row):
    return clean(row.get("horse_name") or row.get("horse") or row.get("runner_name"))


def race_key(row):
    date = clean(row.get("meeting_date") or row.get("race_date") or row.get("date"))
    track = clean(row.get("track") or row.get("meeting_name") or row.get("location")).upper()
    race_no = clean(row.get("race_no") or row.get("race_number"))
    return f"{date}|{track}|{race_no}"


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    tmp.replace(path)


def first_num(row, names):
    for name in names:
        val = n(row.get(name), None)
        if val is not None and val != 0:
            return val
    return None


def get_early(row):
    return first_num(row, [
        "early_speed",
        "avg_early_speed",
        "early_speed_score",
        "early_sectional_speed",
        "early",
        "first_600_speed",
        "first600_speed",
    ])


def get_mid(row):
    return first_num(row, [
        "mid_speed",
        "avg_mid_speed",
        "mid_speed_score",
        "middle_speed",
        "mid",
    ])


def get_late(row):
    return first_num(row, [
        "late_speed",
        "avg_late_speed",
        "late_speed_score",
        "closing_speed",
        "closing_speed_score",
        "late",
    ])


def get_peak(row):
    return first_num(row, [
        "peak_speed",
        "avg_peak_speed",
        "peak_speed_score",
        "top_speed",
        "max_speed",
    ])


def get_avg(row):
    return first_num(row, [
        "avg_speed",
        "speed",
        "average_speed",
        "sustained_speed_score",
        "sectional_ability_score",
        "sectional_ability_score_v3",
    ])


def profile_bucket_from_pct(early_pct, field_size):
    if field_size <= 4:
        if early_pct >= 75:
            return "LEADER"
        if early_pct >= 50:
            return "ON_PACE"
        if early_pct >= 25:
            return "MIDFIELD"
        return "BACKMARKER"

    if early_pct >= 85:
        return "LEADER"
    if early_pct >= 65:
        return "ON_PACE"
    if early_pct >= 35:
        return "MIDFIELD"
    return "BACKMARKER"


def final_bucket(counts, runs, avg_early, avg_late):
    if runs <= 0:
        return "UNKNOWN"

    leader_pct = counts["LEADER"] / runs
    on_pct = counts["ON_PACE"] / runs
    mid_pct = counts["MIDFIELD"] / runs
    back_pct = counts["BACKMARKER"] / runs

    front_pct = leader_pct + on_pct

    if leader_pct >= 0.30 or (front_pct >= 0.55 and avg_early >= 58):
        return "LEADER"

    if front_pct >= 0.42 or avg_early >= 57:
        return "ON_PACE"

    if back_pct >= 0.42 or (avg_late >= 60 and avg_early < 54):
        return "BACKMARKER"

    if mid_pct >= 0.30:
        return "MIDFIELD"

    if avg_early >= 56:
        return "ON_PACE"

    if avg_late >= 59:
        return "BACKMARKER"

    return "MIDFIELD"


def position_group(bucket):
    if bucket == "LEADER":
        return "FRONT"
    if bucket == "ON_PACE":
        return "FORWARD"
    if bucket == "MIDFIELD":
        return "MIDFIELD"
    if bucket == "BACKMARKER":
        return "REAR"
    return "UNKNOWN"


def pressure_role(bucket, leader_pct, on_pct, early):
    if bucket == "LEADER" and early >= 60:
        return "PRESSURE_LEADER"
    if bucket == "LEADER":
        return "LIKELY_LEADER"
    if bucket == "ON_PACE" and (leader_pct + on_pct) >= 50:
        return "PRESSURE_STALKER"
    if bucket == "ON_PACE":
        return "TACTICAL_ON_SPEED"
    if bucket == "MIDFIELD":
        return "BALANCED_MIDFIELD"
    if bucket == "BACKMARKER":
        return "CLOSER"
    return "UNKNOWN"


def confidence(runs, ability_conf, reliability, unknown_pct):
    rel = clean(reliability).upper()

    if runs >= 8 and ability_conf >= 70 and rel in {"A", "B", "C"} and unknown_pct <= 20:
        return "HIGH"

    if runs >= 4 and ability_conf >= 55 and unknown_pct <= 35:
        return "MEDIUM"

    if runs >= 2:
        return "LOW"

    return "INSUFFICIENT"


def reason(bucket, runs, leader_pct, on_pct, mid_pct, back_pct, early, late):
    return (
        f"Projected {bucket} from Tactical DNA: "
        f"runs={runs}, leader={leader_pct:.1f}%, on_pace={on_pct:.1f}%, "
        f"midfield={mid_pct:.1f}%, backmarker={back_pct:.1f}%, "
        f"early={early:.2f}, late={late:.2f}."
    )


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    warehouse = read_csv(WAREHOUSE)
    profiles = read_csv(PROFILES)
    ability = read_csv(ABILITY)

    profile_by_horse = {horse_key(r): r for r in profiles if horse_key(r)}
    ability_by_horse = {horse_key(r): r for r in ability if horse_key(r)}

    race_groups = defaultdict(list)
    for r in warehouse:
        hk = horse_key(r)
        rk = race_key(r)
        early = get_early(r)
        if not hk or not rk or early is None:
            continue

        rr = dict(r)
        rr["_horse_key"] = hk
        rr["_race_key"] = rk
        rr["_early"] = early
        rr["_mid"] = get_mid(r)
        rr["_late"] = get_late(r)
        rr["_peak"] = get_peak(r)
        rr["_avg"] = get_avg(r)
        race_groups[rk].append(rr)

    horse_runs = defaultdict(list)

    for rk, rows in race_groups.items():
        usable = [r for r in rows if r.get("_early") is not None]
        if not usable:
            continue

        ordered = sorted(usable, key=lambda r: r["_early"], reverse=True)
        field_size = len(ordered)

        for idx, r in enumerate(ordered, start=1):
            if field_size <= 1:
                early_pct = 100.0
            else:
                early_pct = round(((field_size - idx) / (field_size - 1)) * 100.0, 2)

            bucket = profile_bucket_from_pct(early_pct, field_size)

            horse_runs[r["_horse_key"]].append({
                "horse_name": horse_name(r),
                "race_key": rk,
                "early": r.get("_early"),
                "mid": r.get("_mid"),
                "late": r.get("_late"),
                "peak": r.get("_peak"),
                "avg": r.get("_avg"),
                "rank": idx,
                "field_size": field_size,
                "early_pct": early_pct,
                "bucket": bucket,
            })

    out = []

    all_keys = set(horse_runs.keys()) | set(profile_by_horse.keys()) | set(ability_by_horse.keys())

    for hk in sorted(all_keys):
        runs = horse_runs.get(hk, [])
        profile = profile_by_horse.get(hk, {})
        ab = ability_by_horse.get(hk, {})

        counts = defaultdict(int)
        for r in runs:
            counts[r["bucket"]] += 1

        run_count = len(runs)

        early_vals = [r["early"] for r in runs if r.get("early") is not None]
        mid_vals = [r["mid"] for r in runs if r.get("mid") is not None]
        late_vals = [r["late"] for r in runs if r.get("late") is not None]
        peak_vals = [r["peak"] for r in runs if r.get("peak") is not None]
        avg_vals = [r["avg"] for r in runs if r.get("avg") is not None]
        rank_vals = [r["rank"] for r in runs if r.get("rank") is not None]
        pct_vals = [r["early_pct"] for r in runs if r.get("early_pct") is not None]

        avg_early = avg(early_vals) or n(profile.get("avg_early_speed"))
        avg_mid = avg(mid_vals) or n(profile.get("avg_mid_speed"))
        avg_late = avg(late_vals) or n(profile.get("avg_late_speed"))
        avg_peak = avg(peak_vals) or n(profile.get("avg_peak_speed"))
        avg_speed = avg(avg_vals) or n(profile.get("avg_speed"))

        runs_for_bucket = run_count
        if runs_for_bucket <= 0 and n(profile.get("runs_with_sectionals")) > 0:
            runs_for_bucket = int(n(profile.get("runs_with_sectionals")))

        bucket = final_bucket(counts, runs_for_bucket, avg_early, avg_late)

        ability_score = n(ab.get("sectional_ability_score_v3"))
        ability_conf = n(ab.get("sectional_confidence_score_v3"))
        reliability = clean(ab.get("sectional_reliability_rank_v3"))
        archetype = clean(ab.get("sectional_archetype") or profile.get("sectional_archetype"))

        leader_pct = pct(counts["LEADER"], run_count)
        on_pct = pct(counts["ON_PACE"], run_count)
        mid_pct = pct(counts["MIDFIELD"], run_count)
        back_pct = pct(counts["BACKMARKER"], run_count)
        unknown_pct = pct(counts["UNKNOWN"], run_count)

        conf = confidence(runs_for_bucket, ability_conf, reliability, unknown_pct)

        name = (
            clean((runs[0] or {}).get("horse_name")) if runs else ""
        ) or clean(profile.get("horse_name") or ab.get("horse_name"))

        out.append({
            "built_at": built_at,
            "horse_key": hk,
            "horse_name": name,
            "runs_used": runs_for_bucket,
            "races_used": run_count,
            "leader_runs": counts["LEADER"],
            "on_pace_runs": counts["ON_PACE"],
            "midfield_runs": counts["MIDFIELD"],
            "backmarker_runs": counts["BACKMARKER"],
            "unknown_runs": counts["UNKNOWN"],
            "leader_pct": leader_pct,
            "on_pace_pct": on_pct,
            "midfield_pct": mid_pct,
            "backmarker_pct": back_pct,
            "unknown_pct": unknown_pct,
            "avg_early_speed": round(avg_early, 2),
            "avg_mid_speed": round(avg_mid, 2),
            "avg_late_speed": round(avg_late, 2),
            "avg_peak_speed": round(avg_peak, 2),
            "avg_speed": round(avg_speed, 2),
            "early_speed_rank_avg": avg(rank_vals),
            "early_speed_percentile_avg": avg(pct_vals),
            "tactical_speed_bucket": bucket,
            "tactical_position_group": position_group(bucket),
            "tempo_pressure_role": pressure_role(bucket, leader_pct, on_pct, avg_early),
            "sectional_archetype": archetype,
            "sectional_ability_score": round(ability_score, 2),
            "sectional_confidence_score": round(ability_conf, 2),
            "sectional_reliability_rank": reliability,
            "dna_confidence": conf,
            "bucket_confidence": conf,
            "tactical_reason": reason(bucket, runs_for_bucket, leader_pct, on_pct, mid_pct, back_pct, avg_early, avg_late),
        })

    out.sort(key=lambda r: (
        {"LEADER": 0, "ON_PACE": 1, "MIDFIELD": 2, "BACKMARKER": 3, "UNKNOWN": 4}.get(r["tactical_speed_bucket"], 9),
        -n(r.get("runs_used")),
        r.get("horse_name", ""),
    ))

    write_csv(OUT, out, OUT_COLS)

    bucket_counts = defaultdict(int)
    conf_counts = defaultdict(int)
    for r in out:
        bucket_counts[r["tactical_speed_bucket"]] += 1
        conf_counts[r["dna_confidence"]] += 1

    audit = [{
        "built_at": built_at,
        "warehouse_rows_loaded": len(warehouse),
        "profiles_loaded": len(profiles),
        "ability_rows_loaded": len(ability),
        "output_horses": len(out),
        "leader_horses": bucket_counts["LEADER"],
        "on_pace_horses": bucket_counts["ON_PACE"],
        "midfield_horses": bucket_counts["MIDFIELD"],
        "backmarker_horses": bucket_counts["BACKMARKER"],
        "unknown_horses": bucket_counts["UNKNOWN"],
        "high_confidence": conf_counts["HIGH"],
        "medium_confidence": conf_counts["MEDIUM"],
        "low_confidence": conf_counts["LOW"],
        "insufficient_confidence": conf_counts["INSUFFICIENT"],
        "final_status": "TACTICAL_DNA_V1_BUILT" if out else "NO_DNA_ROWS",
    }]

    write_csv(AUDIT, audit, AUDIT_COLS)

    print("EDGEiQ Tactical DNA V1 built")
    print(f"warehouse_rows_loaded={len(warehouse)}")
    print(f"output_horses={len(out)}")
    print(f"leader_horses={bucket_counts['LEADER']}")
    print(f"on_pace_horses={bucket_counts['ON_PACE']}")
    print(f"midfield_horses={bucket_counts['MIDFIELD']}")
    print(f"backmarker_horses={bucket_counts['BACKMARKER']}")
    print(f"unknown_horses={bucket_counts['UNKNOWN']}")
    print(f"saved={OUT}")
    print("final_status=TACTICAL_DNA_V1_BUILT")


if __name__ == "__main__":
    main()
