from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"

OUT = DATA / "edgeiq_race_shape_story_v1.csv"
SUMMARY = DATA / "edgeiq_race_shape_story_v1_summary.csv"


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def upper(value):
    return clean(value).upper()


def to_float(value, default=None):
    try:
        txt = clean(value)
        if txt == "":
            return default
        return float(txt)
    except Exception:
        return default


def to_int(value, default=None):
    try:
        txt = clean(value)
        if txt == "":
            return default
        return int(float(txt))
    except Exception:
        return default


def horse_name(row):
    return clean(row.get("horse")) or clean(row.get("_horse"))


def norm_track(row):
    return upper(row.get("track")) or upper(row.get("_track"))


def norm_race_no(row):
    return clean(row.get("race_no")) or clean(row.get("_race"))


def norm_race_date(row):
    return clean(row.get("race_date")) or clean(row.get("_date"))


def is_scratched(row):
    vals = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(v in {"TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for v in vals)


def speed_value(row):
    for col in ["projected_spd", "early_speed_rating", "map_x_pct"]:
        val = to_float(row.get(col), None)
        if val is not None:
            return val
    return None


def late_value(row):
    for col in ["late_power_index", "sectional_weapon_score", "sectional_score_component_v1_1"]:
        val = to_float(row.get(col), None)
        if val is not None:
            return val
    return None


def edge_value(row):
    for col in ["edge_pct", "display_edge_pct", "ui_edge_pct"]:
        val = to_float(row.get(col), None)
        if val is not None:
            return val
    return None


def fair_price(row):
    for col in ["fair_price", "display_fair_price", "ui_fair_price", "V6_1_RESEARCH_fair_price"]:
        val = to_float(row.get(col), None)
        if val is not None:
            return val
    return None


def model_rank(row):
    for col in ["V6_1_RESEARCH_price_rank", "fair_rank", "edge_rank", "live_rank"]:
        val = to_int(row.get(col), None)
        if val is not None:
            return val
    return None


def style_bucket(row):
    raw = " ".join([
        upper(row.get("settling_band")),
        upper(row.get("run_style")),
        upper(row.get("early_speed_band")),
        upper(row.get("speed_map_bucket")),
    ])

    if any(x in raw for x in ["LEADER", "FRONT", "LEAD"]):
        return "LEADER"
    if any(x in raw for x in ["ON PACE", "ON-PACE", "PACE", "PROMINENT"]):
        return "ON_PACE"
    if any(x in raw for x in ["MID", "MIDFIELD"]):
        return "MIDFIELD"
    if any(x in raw for x in ["BACK", "CLOSER", "SETTLED BACK"]):
        return "BACKMARKER"

    spd = speed_value(row)
    if spd is None:
        return "UNKNOWN"
    if spd >= 70:
        return "LEADER"
    if spd >= 58:
        return "ON_PACE"
    if spd >= 42:
        return "MIDFIELD"
    return "BACKMARKER"


def csv_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def race_key(row):
    return (norm_race_date(row), norm_track(row), norm_race_no(row))


def merge_bet_quality(board_rows, bet_rows):
    bet_index = {}
    for r in bet_rows:
        key = (
            clean(r.get("race_date")),
            upper(r.get("track")),
            clean(r.get("race_no")),
            upper(r.get("horse_key")) or upper(r.get("horse_canon")) or upper(r.get("horse")),
        )
        bet_index[key] = r

    merged = []
    for r in board_rows:
        hr_key = upper(r.get("horse_key")) or upper(horse_name(r))
        key = (norm_race_date(r), norm_track(r), norm_race_no(r), hr_key)
        b = bet_index.get(key, {})
        nr = dict(r)
        for k, v in b.items():
            if k not in nr or clean(nr.get(k)) == "":
                nr[k] = v
        merged.append(nr)
    return merged


def top_names(rows, n=4):
    return "; ".join(horse_name(r) for r in rows[:n] if horse_name(r))


def choose_pace_advantage(rows):
    candidates = []
    for r in rows:
        if style_bucket(r) not in {"LEADER", "ON_PACE"}:
            continue
        spd = speed_value(r) or 0
        edge = edge_value(r) or 0
        rank = model_rank(r)
        fair = fair_price(r)

        score = spd
        score += max(edge, 0) * 1.5
        if rank is not None:
            score += max(0, 10 - rank) * 2
        if fair is not None and fair <= 6:
            score += 4

        candidates.append((score, r))

    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    return horse_name(candidates[0][1])


def choose_late_beneficiary(rows):
    candidates = []
    for r in rows:
        if style_bucket(r) not in {"MIDFIELD", "BACKMARKER"}:
            continue
        late = late_value(r)
        if late is None:
            continue
        edge = edge_value(r) or 0
        rank = model_rank(r)
        score = late + max(edge, 0)
        if rank is not None:
            score += max(0, 10 - rank) * 1.5
        candidates.append((score, r))

    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    return horse_name(candidates[0][1])


def choose_pressure_risk(rows, leader_count):
    candidates = []
    for r in rows:
        if style_bucket(r) not in {"LEADER", "ON_PACE"}:
            continue
        late = late_value(r)
        spd = speed_value(r) or 0
        edge = edge_value(r) or 0

        risk = 0
        if leader_count >= 3:
            risk += 20
        if late is not None:
            risk += max(0, 55 - late)
        risk += max(0, spd - 70) * 0.25
        if edge < 0:
            risk += abs(edge)

        candidates.append((risk, r))

    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    if candidates[0][0] <= 0:
        return ""
    return horse_name(candidates[0][1])


def tempo_label(leader_count, on_pace_count):
    pressure = leader_count + max(0, on_pace_count - 1) * 0.5
    if leader_count >= 4:
        return "FAST / HIGH PRESSURE"
    if leader_count >= 3:
        return "FAST / PRESSURE"
    if leader_count == 2:
        return "MODERATE"
    if leader_count <= 1 and on_pace_count <= 2:
        return "SLOW / TACTICAL"
    return "EVEN"


def shape_label(tempo, late_beneficiary, pace_advantage, leader_count):
    if "HIGH PRESSURE" in tempo and late_beneficiary:
        return "PRESSURE SETUP FOR LATE POWER"
    if "FAST" in tempo:
        return "PRESSURE RACE"
    if "SLOW" in tempo and pace_advantage:
        return "TACTICAL FRONT-HALF ADVANTAGE"
    if leader_count <= 1 and pace_advantage:
        return "CONTROLLED SPEED MAP"
    return "EVEN RACE SHAPE"


def story_text(tempo, leader_count, on_pace_count, pace_adv, late_benefit, risk_runner):
    bits = []

    if "HIGH PRESSURE" in tempo or "FAST" in tempo:
        bits.append(f"{leader_count} likely leaders create early pressure.")
    elif "SLOW" in tempo:
        bits.append("Limited natural speed points to a tactical race shape.")
    else:
        bits.append(f"Tempo profiles as {tempo.lower()} with {leader_count} leader(s) and {on_pace_count} on-pace runner(s).")

    if pace_adv:
        bits.append(f"Map advantage: {pace_adv}.")
    if late_benefit:
        bits.append(f"Late-power beneficiary: {late_benefit}.")
    if risk_runner:
        bits.append(f"Pressure risk: {risk_runner}.")

    return " ".join(bits)


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    board_rows = csv_rows(INPUT_BOARD)
    bet_rows = csv_rows(INPUT_BET_QUALITY)

    if bet_rows:
        rows = merge_bet_quality(board_rows, bet_rows)
    else:
        rows = board_rows

    active_rows = [r for r in rows if not is_scratched(r)]

    grouped = defaultdict(list)
    for r in active_rows:
        key = race_key(r)
        if not all(key):
            continue
        grouped[key].append(r)

    out_rows = []

    for (race_date, track, race_no), runners in sorted(grouped.items()):
        for r in runners:
            r["_shape_bucket"] = style_bucket(r)

        leaders = sorted(
            [r for r in runners if r["_shape_bucket"] == "LEADER"],
            key=lambda r: speed_value(r) if speed_value(r) is not None else -999,
            reverse=True,
        )
        onpace = sorted(
            [r for r in runners if r["_shape_bucket"] == "ON_PACE"],
            key=lambda r: speed_value(r) if speed_value(r) is not None else -999,
            reverse=True,
        )
        midfield = sorted(
            [r for r in runners if r["_shape_bucket"] == "MIDFIELD"],
            key=lambda r: late_value(r) if late_value(r) is not None else -999,
            reverse=True,
        )
        backmarkers = sorted(
            [r for r in runners if r["_shape_bucket"] == "BACKMARKER"],
            key=lambda r: late_value(r) if late_value(r) is not None else -999,
            reverse=True,
        )

        leader_count = len(leaders)
        on_pace_count = len(onpace)
        midfield_count = len(midfield)
        backmarker_count = len(backmarkers)

        tempo = tempo_label(leader_count, on_pace_count)
        pace_adv = choose_pace_advantage(runners)
        late_benefit = choose_late_beneficiary(runners)
        risk_runner = choose_pressure_risk(runners, leader_count)
        label = shape_label(tempo, late_benefit, pace_adv, leader_count)

        out_rows.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "runner_count": len(runners),
            "tempo": tempo,
            "leader_count": leader_count,
            "on_pace_count": on_pace_count,
            "midfield_count": midfield_count,
            "backmarker_count": backmarker_count,
            "likely_leaders": top_names(leaders),
            "likely_on_pace": top_names(onpace),
            "likely_midfield": top_names(midfield),
            "likely_backmarkers": top_names(backmarkers),
            "pace_advantage_runner": pace_adv,
            "late_power_beneficiary": late_benefit,
            "pressure_risk_runner": risk_runner,
            "race_shape_label": label,
            "race_shape_story": story_text(tempo, leader_count, on_pace_count, pace_adv, late_benefit, risk_runner),
            "built_at": built_at,
        })

    fields = [
        "race_date", "track", "race_no", "runner_count", "tempo",
        "leader_count", "on_pace_count", "midfield_count", "backmarker_count",
        "likely_leaders", "likely_on_pace", "likely_midfield", "likely_backmarkers",
        "pace_advantage_runner", "late_power_beneficiary", "pressure_risk_runner",
        "race_shape_label", "race_shape_story", "built_at",
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    tempos = defaultdict(int)
    labels = defaultdict(int)
    for r in out_rows:
        tempos[r["tempo"]] += 1
        labels[r["race_shape_label"]] += 1

    summary_rows = [
        {"metric": "status", "value": "RACE_SHAPE_STORY_V1_BUILT"},
        {"metric": "input_board_rows", "value": len(board_rows)},
        {"metric": "input_bet_quality_rows", "value": len(bet_rows)},
        {"metric": "active_runner_rows", "value": len(active_rows)},
        {"metric": "race_rows", "value": len(out_rows)},
        {"metric": "built_at", "value": built_at},
    ]

    for k, v in sorted(tempos.items()):
        summary_rows.append({"metric": f"tempo_{k}", "value": v})
    for k, v in sorted(labels.items()):
        summary_rows.append({"metric": f"label_{k}", "value": v})

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary_rows)

    print("[RACE_SHAPE_STORY_V1] COMPLETE")
    print(f"races={len(out_rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
