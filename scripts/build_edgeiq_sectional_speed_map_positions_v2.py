from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
ABILITY = DATA / "edgeiq_sectional_ability_engine_v3.csv"
OLD_SPEED = DATA / "edgeiq_real_speed_map_positions.csv"

OUT = DATA / "edgeiq_sectional_speed_map_positions_v2.csv"
AUDIT = DATA / "edgeiq_sectional_speed_map_positions_v2_audit.csv"

OUT_COLS = [
    "built_at",
    "race_date",
    "track",
    "race_no",
    "race_key",
    "horse",
    "horse_key",
    "barrier",
    "runner_no",
    "sectional_source",
    "runs_with_sectionals",
    "sectional_archetype",
    "sectional_ability_score",
    "sectional_confidence_score",
    "sectional_reliability_rank",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "sectional_speed_bucket",
    "projected_settling_band",
    "run_style",
    "pace_profile",
    "map_x_pct",
    "map_y_px",
    "race_pace_pressure",
    "projected_tempo_shape",
    "sectional_map_confidence",
    "sectional_map_reason",
]

AUDIT_COLS = [
    "built_at",
    "live_rows_loaded",
    "ability_rows_loaded",
    "output_rows",
    "matched_sectional_profiles",
    "fallback_old_speed_rows",
    "no_sectional_no_fallback_rows",
    "leader_rows",
    "on_pace_rows",
    "midfield_rows",
    "backmarker_rows",
    "unknown_rows",
    "races_output",
    "final_status",
]


def clean(v):
    return "" if v is None else str(v).strip()


def num(v, default=0.0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def integer(v, default=0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(v))
    except Exception:
        return default


def horse_key_from_text(v):
    return re.sub(r"[^A-Z0-9]+", "", re.sub(r"\([^)]*\)", "", clean(v).upper()))


def horse_key(row):
    return horse_key_from_text(
        row.get("horse_key")
        or row.get("runner_key")
        or row.get("horse")
        or row.get("horse_name")
        or row.get("runner_name")
    )


def race_key(row):
    track = clean(row.get("track") or row.get("location") or row.get("meeting_name")).upper()
    race_no = clean(row.get("race_no") or row.get("race_number"))
    date = clean(row.get("race_date") or row.get("meeting_date") or row.get("date"))
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


def speed_bucket_from_sectionals(early, mid, late, peak, avg, archetype):
    arch = clean(archetype).upper()

    if early <= 0 and peak <= 0 and avg <= 0:
        return "UNKNOWN"

    if arch in {"PRESSURE_LEADER", "FRONT_RUNNING_CONTROLLER"}:
        return "LEADER"

    if arch in {"ON_SPEED_CRUISER", "PEAK_SPEED_HORSE"} and early >= 58:
        return "ON_PACE"

    if early >= 63:
        return "LEADER"

    if early >= 58:
        return "ON_PACE"

    if early >= 53:
        return "MIDFIELD"

    if late >= 60 and early < 53:
        return "BACKMARKER"

    if avg >= 58:
        return "MIDFIELD"

    return "BACKMARKER"


def run_style_from_bucket(bucket):
    if bucket == "LEADER":
        return "LEADER"
    if bucket == "ON_PACE":
        return "ON PACE"
    if bucket == "MIDFIELD":
        return "MIDFIELD"
    if bucket == "BACKMARKER":
        return "BACKMARKER"
    return "UNKNOWN"


def pace_profile_from_bucket(bucket):
    if bucket == "LEADER":
        return "PRESSURE / LEADER"
    if bucket == "ON_PACE":
        return "TACTICAL / ON SPEED"
    if bucket == "MIDFIELD":
        return "BALANCED / MIDFIELD"
    if bucket == "BACKMARKER":
        return "CLOSER / BACKMARKER"
    return "UNKNOWN"


def base_x(bucket):
    if bucket == "LEADER":
        return 18
    if bucket == "ON_PACE":
        return 34
    if bucket == "MIDFIELD":
        return 55
    if bucket == "BACKMARKER":
        return 78
    return 88


def confidence_from_profile(runs, conf, reliability, matched):
    rel = clean(reliability).upper()

    if not matched:
        return "FALLBACK"

    if runs >= 8 and conf >= 70 and rel in {"A", "B", "C"}:
        return "HIGH"

    if runs >= 4 and conf >= 55:
        return "MEDIUM"

    if runs >= 1:
        return "LOW"

    return "INSUFFICIENT"


def reason_for(bucket, runs, early, late, ability, matched):
    if not matched:
        return "No sectional profile matched; used fallback speed-map data where available."

    if bucket == "LEADER":
        return f"Sectional DNA projects forward: early={early:.2f}, late={late:.2f}, runs={runs}."
    if bucket == "ON_PACE":
        return f"Sectional DNA projects on-pace: early={early:.2f}, ability={ability:.2f}, runs={runs}."
    if bucket == "MIDFIELD":
        return f"Sectional DNA projects midfield: early={early:.2f}, late={late:.2f}, runs={runs}."
    if bucket == "BACKMARKER":
        return f"Sectional DNA projects rearward/closing profile: early={early:.2f}, late={late:.2f}, runs={runs}."
    return "Insufficient sectional DNA to project map position."


def race_tempo(rows):
    leaders = sum(1 for r in rows if r["sectional_speed_bucket"] == "LEADER")
    onpace = sum(1 for r in rows if r["sectional_speed_bucket"] == "ON_PACE")
    pressure_units = leaders * 2 + onpace

    if pressure_units >= 6 or leaders >= 3:
        return "HIGH", "FAST"
    if pressure_units >= 3:
        return "MODERATE", "NEUTRAL"
    return "LOW", "CONTROLLED"


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    live_rows = read_csv(LIVE)
    ability_rows = read_csv(ABILITY)
    old_rows = read_csv(OLD_SPEED)

    ability_by_horse = {}
    for r in ability_rows:
        hk = horse_key(r)
        if hk:
            ability_by_horse[hk] = r

    old_by_race_horse = {}
    old_by_horse = {}
    for r in old_rows:
        hk = horse_key(r)
        rk = race_key(r)
        if hk:
            old_by_horse[hk] = r
        if hk and rk:
            old_by_race_horse[(rk, hk)] = r

    grouped = defaultdict(list)
    matched = 0
    fallback = 0
    no_data = 0

    prelim = []

    for live in live_rows:
        hk = horse_key(live)
        rk = race_key(live)

        ability = ability_by_horse.get(hk, {})
        old = old_by_race_horse.get((rk, hk)) or old_by_horse.get(hk, {})

        has_sectional = bool(ability)

        runs = integer(ability.get("runs_with_sectionals"))
        early = num(ability.get("avg_early_speed"))
        mid = num(ability.get("avg_mid_speed"))
        late = num(ability.get("avg_late_speed"))
        peak = num(ability.get("avg_peak_speed"))
        avg = num(ability.get("avg_speed"))
        ability_score = num(ability.get("sectional_ability_score_v3"))
        conf_score = num(ability.get("sectional_confidence_score_v3"))
        reliability = clean(ability.get("sectional_reliability_rank_v3"))
        archetype = clean(ability.get("sectional_archetype"))

        if has_sectional:
            matched += 1
            bucket = speed_bucket_from_sectionals(early, mid, late, peak, avg, archetype)
            source = "SECTIONAL_DNA_V2"
        elif old:
            fallback += 1
            bucket = clean(old.get("speed_map_bucket") or old.get("settling_band") or old.get("run_style")).upper().replace(" ", "_")
            if bucket in {"LEAD", "LEADER"}:
                bucket = "LEADER"
            elif bucket in {"ONPACE", "ON_PACE", "ON-SPEED", "ON_SPEED"}:
                bucket = "ON_PACE"
            elif bucket in {"MID", "MIDFIELD"}:
                bucket = "MIDFIELD"
            elif bucket in {"BACK", "BACKMARKER", "BACK_MARKER"}:
                bucket = "BACKMARKER"
            else:
                bucket = "UNKNOWN"
            source = "FALLBACK_EXISTING_SPEED_MAP"
        else:
            no_data += 1
            bucket = "UNKNOWN"
            source = "NO_SECTIONAL_PROFILE"

        barrier = integer(live.get("barrier"))
        runner_no = clean(live.get("horse_no") or live.get("runner_no") or live.get("saddlecloth"))

        row = {
            "built_at": built_at,
            "race_date": clean(live.get("race_date") or live.get("meeting_date")),
            "track": clean(live.get("track") or live.get("location")),
            "race_no": clean(live.get("race_no")),
            "race_key": rk,
            "horse": clean(live.get("horse") or live.get("horse_name") or live.get("runner_name")),
            "horse_key": hk,
            "barrier": barrier,
            "runner_no": runner_no,
            "sectional_source": source,
            "runs_with_sectionals": runs,
            "sectional_archetype": archetype if has_sectional else "",
            "sectional_ability_score": round(ability_score, 2),
            "sectional_confidence_score": round(conf_score, 2),
            "sectional_reliability_rank": reliability,
            "avg_early_speed": round(early, 2) if early else "",
            "avg_mid_speed": round(mid, 2) if mid else "",
            "avg_late_speed": round(late, 2) if late else "",
            "avg_peak_speed": round(peak, 2) if peak else "",
            "avg_speed": round(avg, 2) if avg else "",
            "sectional_speed_bucket": bucket,
            "projected_settling_band": bucket,
            "run_style": run_style_from_bucket(bucket),
            "pace_profile": pace_profile_from_bucket(bucket),
            "map_x_pct": base_x(bucket),
            "map_y_px": "",
            "race_pace_pressure": "",
            "projected_tempo_shape": "",
            "sectional_map_confidence": confidence_from_profile(runs, conf_score, reliability, has_sectional),
            "sectional_map_reason": reason_for(bucket, runs, early, late, ability_score, has_sectional),
        }

        prelim.append(row)
        grouped[rk].append(row)

    output = []

    for rk, rows in grouped.items():
        pressure, tempo = race_tempo(rows)

        sorted_barriers = sorted(
            [integer(r.get("barrier")) for r in rows if integer(r.get("barrier")) > 0],
            reverse=True
        )
        barrier_rank = {b: i for i, b in enumerate(sorted_barriers)}

        for r in rows:
            b = integer(r.get("barrier"))
            lane = barrier_rank.get(b, len(sorted_barriers))
            r["map_y_px"] = 36 + lane * 34

            bucket_group = [x for x in rows if x["sectional_speed_bucket"] == r["sectional_speed_bucket"]]
            bucket_group_sorted = sorted(
                bucket_group,
                key=lambda x: (
                    -num(x.get("avg_early_speed")),
                    -num(x.get("sectional_ability_score")),
                    integer(x.get("barrier"), 99),
                )
            )
            offset_index = next((i for i, x in enumerate(bucket_group_sorted) if x["horse_key"] == r["horse_key"]), 0)
            r["map_x_pct"] = max(8, min(92, num(r["map_x_pct"]) + offset_index * 2.2))

            r["race_pace_pressure"] = pressure
            r["projected_tempo_shape"] = tempo
            output.append(r)

    write_csv(OUT, output, OUT_COLS)

    counts = defaultdict(int)
    for r in output:
        counts[r["sectional_speed_bucket"]] += 1

    audit = [{
        "built_at": built_at,
        "live_rows_loaded": len(live_rows),
        "ability_rows_loaded": len(ability_rows),
        "output_rows": len(output),
        "matched_sectional_profiles": matched,
        "fallback_old_speed_rows": fallback,
        "no_sectional_no_fallback_rows": no_data,
        "leader_rows": counts["LEADER"],
        "on_pace_rows": counts["ON_PACE"],
        "midfield_rows": counts["MIDFIELD"],
        "backmarker_rows": counts["BACKMARKER"],
        "unknown_rows": counts["UNKNOWN"],
        "races_output": len(grouped),
        "final_status": "SECTIONAL_SPEED_MAP_V2_BUILT" if output else "NO_ROWS_BUILT",
    }]

    write_csv(AUDIT, audit, AUDIT_COLS)

    print("EDGEiQ Sectional Speed Map Positions V2 built")
    print(f"live_rows_loaded={len(live_rows)}")
    print(f"ability_rows_loaded={len(ability_rows)}")
    print(f"output_rows={len(output)}")
    print(f"matched_sectional_profiles={matched}")
    print(f"fallback_old_speed_rows={fallback}")
    print(f"no_sectional_no_fallback_rows={no_data}")
    print(f"races_output={len(grouped)}")
    print(f"saved={OUT}")
    print("final_status=SECTIONAL_SPEED_MAP_V2_BUILT")


if __name__ == "__main__":
    main()
