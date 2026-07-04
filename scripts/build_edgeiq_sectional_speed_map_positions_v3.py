from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
DNA = DATA / "edgeiq_tactical_dna_v1.csv"
OLD_SPEED = DATA / "edgeiq_real_speed_map_positions.csv"

OUT = DATA / "edgeiq_sectional_speed_map_positions_v3.csv"
AUDIT = DATA / "edgeiq_sectional_speed_map_positions_v3_audit.csv"

OUT_COLS = [
    "built_at","race_date","track","race_no","race_key",
    "horse","horse_key","barrier","runner_no",
    "speed_map_source","runs_used","dna_confidence","bucket_confidence",
    "leader_pct","on_pace_pct","midfield_pct","backmarker_pct",
    "avg_early_speed","avg_late_speed","sectional_ability_score",
    "sectional_archetype","tactical_speed_bucket","tactical_position_group",
    "tempo_pressure_role","sectional_speed_bucket","projected_settling_band",
    "run_style","pace_profile","map_x_pct","map_y_px",
    "race_pace_pressure","projected_tempo_shape","sectional_map_reason"
]

AUDIT_COLS = [
    "built_at","live_rows_loaded","dna_rows_loaded","output_rows",
    "matched_dna_rows","fallback_old_speed_rows","no_data_rows",
    "leader_rows","on_pace_rows","midfield_rows","backmarker_rows","unknown_rows",
    "fast_races","neutral_races","controlled_races","races_output",
    "final_status"
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


def i(v, default=0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(v))
    except Exception:
        return default


def key_text(v):
    return re.sub(r"[^A-Z0-9]+", "", re.sub(r"\([^)]*\)", "", clean(v).upper()))


def horse_key(row):
    return key_text(row.get("horse_key") or row.get("horse") or row.get("horse_name") or row.get("runner_name"))


def race_key(row):
    date = clean(row.get("race_date") or row.get("meeting_date") or row.get("date"))
    track = clean(row.get("track") or row.get("location") or row.get("meeting_name")).upper()
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


def normal_bucket(v):
    raw = clean(v).upper().replace(" ", "_").replace("-", "_")
    if raw in {"LEAD", "LEADER", "FRONT"}:
        return "LEADER"
    if raw in {"ONPACE", "ON_PACE", "ON_SPEED", "FORWARD"}:
        return "ON_PACE"
    if raw in {"MID", "MIDFIELD"}:
        return "MIDFIELD"
    if raw in {"BACK", "BACKMARKER", "BACK_MARKER", "REAR"}:
        return "BACKMARKER"
    return "UNKNOWN"


def run_style(bucket):
    if bucket == "LEADER":
        return "LEADER"
    if bucket == "ON_PACE":
        return "ON PACE"
    if bucket == "MIDFIELD":
        return "MIDFIELD"
    if bucket == "BACKMARKER":
        return "BACKMARKER"
    return "UNKNOWN"


def pace_profile(bucket):
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
    return {
        "LEADER": 16.0,
        "ON_PACE": 33.0,
        "MIDFIELD": 55.0,
        "BACKMARKER": 78.0,
        "UNKNOWN": 88.0,
    }.get(bucket, 88.0)


def race_tempo(rows):
    leaders = sum(1 for r in rows if r["sectional_speed_bucket"] == "LEADER")
    onpace = sum(1 for r in rows if r["sectional_speed_bucket"] == "ON_PACE")
    field = len(rows)
    pressure_units = leaders * 2 + onpace

    if field >= 10 and pressure_units >= 7:
        return "HIGH", "FAST"
    if pressure_units >= 6 or leaders >= 3:
        return "HIGH", "FAST"
    if pressure_units >= 3:
        return "MODERATE", "NEUTRAL"
    return "LOW", "CONTROLLED"


def tactical_sort_score(row):
    bucket = row["sectional_speed_bucket"]
    leader_pct = n(row.get("leader_pct"))
    on_pct = n(row.get("on_pace_pct"))
    back_pct = n(row.get("backmarker_pct"))
    early = n(row.get("avg_early_speed"))
    ability = n(row.get("sectional_ability_score"))

    if bucket == "LEADER":
        return leader_pct * 2.0 + on_pct + early + ability * 0.2
    if bucket == "ON_PACE":
        return on_pct * 2.0 + leader_pct + early + ability * 0.2
    if bucket == "MIDFIELD":
        return n(row.get("midfield_pct")) * 2.0 + ability * 0.25
    if bucket == "BACKMARKER":
        return back_pct * 2.0 + n(row.get("avg_late_speed")) + ability * 0.2
    return -999


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    live_rows = read_csv(LIVE)
    dna_rows = read_csv(DNA)
    old_rows = read_csv(OLD_SPEED)

    dna_by_horse = {horse_key(r): r for r in dna_rows if horse_key(r)}

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

    for live in live_rows:
        hk = horse_key(live)
        rk = race_key(live)
        dna = dna_by_horse.get(hk, {})
        old = old_by_race_horse.get((rk, hk)) or old_by_horse.get(hk, {})

        if dna:
            matched += 1
            bucket = normal_bucket(dna.get("tactical_speed_bucket"))
            source = "TACTICAL_DNA_V1"
        elif old:
            fallback += 1
            bucket = normal_bucket(old.get("speed_map_bucket") or old.get("settling_band") or old.get("run_style"))
            source = "FALLBACK_OLD_SPEED_MAP"
        else:
            no_data += 1
            bucket = "UNKNOWN"
            source = "NO_DNA"

        horse = clean(live.get("horse") or live.get("horse_name") or live.get("runner_name"))
        barrier = i(live.get("barrier"))
        runner_no = clean(live.get("horse_no") or live.get("runner_no") or live.get("saddlecloth"))

        row = {
            "built_at": built_at,
            "race_date": clean(live.get("race_date") or live.get("meeting_date")),
            "track": clean(live.get("track") or live.get("location")),
            "race_no": clean(live.get("race_no")),
            "race_key": rk,
            "horse": horse,
            "horse_key": hk,
            "barrier": barrier,
            "runner_no": runner_no,
            "speed_map_source": source,
            "runs_used": clean(dna.get("runs_used")),
            "dna_confidence": clean(dna.get("dna_confidence")),
            "bucket_confidence": clean(dna.get("bucket_confidence")),
            "leader_pct": clean(dna.get("leader_pct")),
            "on_pace_pct": clean(dna.get("on_pace_pct")),
            "midfield_pct": clean(dna.get("midfield_pct")),
            "backmarker_pct": clean(dna.get("backmarker_pct")),
            "avg_early_speed": clean(dna.get("avg_early_speed")),
            "avg_late_speed": clean(dna.get("avg_late_speed")),
            "sectional_ability_score": clean(dna.get("sectional_ability_score")),
            "sectional_archetype": clean(dna.get("sectional_archetype")),
            "tactical_speed_bucket": clean(dna.get("tactical_speed_bucket")),
            "tactical_position_group": clean(dna.get("tactical_position_group")),
            "tempo_pressure_role": clean(dna.get("tempo_pressure_role")),
            "sectional_speed_bucket": bucket,
            "projected_settling_band": bucket,
            "run_style": run_style(bucket),
            "pace_profile": pace_profile(bucket),
            "map_x_pct": base_x(bucket),
            "map_y_px": "",
            "race_pace_pressure": "",
            "projected_tempo_shape": "",
            "sectional_map_reason": clean(dna.get("tactical_reason")) if dna else "Fallback map used; no Tactical DNA profile.",
        }

        grouped[rk].append(row)

    output = []

    for rk, rows in grouped.items():
        pressure, tempo = race_tempo(rows)

        sorted_barriers = sorted(
            [i(r.get("barrier")) for r in rows if i(r.get("barrier")) > 0],
            reverse=True
        )
        barrier_rank = {b: idx for idx, b in enumerate(sorted_barriers)}

        for bucket in ["LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER", "UNKNOWN"]:
            group = [r for r in rows if r["sectional_speed_bucket"] == bucket]
            ordered = sorted(group, key=tactical_sort_score, reverse=True)
            for idx, r in enumerate(ordered):
                r["map_x_pct"] = round(max(7, min(93, base_x(bucket) + idx * 2.25)), 2)

        for r in rows:
            b = i(r.get("barrier"))
            lane = barrier_rank.get(b, len(sorted_barriers))
            r["map_y_px"] = 36 + lane * 34
            r["race_pace_pressure"] = pressure
            r["projected_tempo_shape"] = tempo
            output.append(r)

    write_csv(OUT, output, OUT_COLS)

    bucket_counts = defaultdict(int)
    tempo_counts = defaultdict(int)
    for r in output:
        bucket_counts[r["sectional_speed_bucket"]] += 1

    for rows in grouped.values():
        if rows:
            tempo_counts[rows[0].get("projected_tempo_shape")] += 1

    audit = [{
        "built_at": built_at,
        "live_rows_loaded": len(live_rows),
        "dna_rows_loaded": len(dna_rows),
        "output_rows": len(output),
        "matched_dna_rows": matched,
        "fallback_old_speed_rows": fallback,
        "no_data_rows": no_data,
        "leader_rows": bucket_counts["LEADER"],
        "on_pace_rows": bucket_counts["ON_PACE"],
        "midfield_rows": bucket_counts["MIDFIELD"],
        "backmarker_rows": bucket_counts["BACKMARKER"],
        "unknown_rows": bucket_counts["UNKNOWN"],
        "fast_races": tempo_counts["FAST"],
        "neutral_races": tempo_counts["NEUTRAL"],
        "controlled_races": tempo_counts["CONTROLLED"],
        "races_output": len(grouped),
        "final_status": "SECTIONAL_SPEED_MAP_V3_BUILT" if output else "NO_ROWS_BUILT",
    }]

    write_csv(AUDIT, audit, AUDIT_COLS)

    print("EDGEiQ Sectional Speed Map Positions V3 built")
    print(f"live_rows_loaded={len(live_rows)}")
    print(f"dna_rows_loaded={len(dna_rows)}")
    print(f"output_rows={len(output)}")
    print(f"matched_dna_rows={matched}")
    print(f"fallback_old_speed_rows={fallback}")
    print(f"no_data_rows={no_data}")
    print(f"leader_rows={bucket_counts['LEADER']}")
    print(f"on_pace_rows={bucket_counts['ON_PACE']}")
    print(f"midfield_rows={bucket_counts['MIDFIELD']}")
    print(f"backmarker_rows={bucket_counts['BACKMARKER']}")
    print(f"unknown_rows={bucket_counts['UNKNOWN']}")
    print(f"races_output={len(grouped)}")
    print(f"saved={OUT}")
    print("final_status=SECTIONAL_SPEED_MAP_V3_BUILT")


if __name__ == "__main__":
    main()
