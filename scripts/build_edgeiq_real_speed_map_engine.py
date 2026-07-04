from __future__ import annotations

import csv
import math
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
LIVE_SOURCE_CANDIDATES = [
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
]
OUT = DATA / "edgeiq_real_speed_map_positions.csv"
DIAG = DATA / "edgeiq_real_speed_map_positions_diagnostics.csv"

PACE = DATA / "pace_pressure.csv"
PROJECTED = DATA / "edgeiq_projected_settling_engine_v4.csv"
DNA = DATA / "edgeiq_master_positional_dna_v1.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_engine_v2.csv"

ZONES = ["LEADER", "PACE", "OFF PACE", "MIDFIELD", "BACKMARKER"]
ZONE_X = {
    "LEADER": (6.0, 18.0),
    "PACE": (20.0, 37.0),
    "OFF PACE": (39.0, 57.0),
    "MIDFIELD": (59.0, 77.0),
    "BACKMARKER": (79.0, 94.0),
}
ZONE_BASE_Y = {
    "LEADER": 218.0,
    "PACE": 194.0,
    "OFF PACE": 158.0,
    "MIDFIELD": 116.0,
    "BACKMARKER": 74.0,
}

OUT_FIELDS = [
    "built_at",
    "meeting_key",
    "race_key",
    "runner_key",
    "race_date",
    "track",
    "race_no",
    "race_time",
    "horse_no",
    "saddlecloth",
    "horse",
    "horse_key",
    "barrier",
    "live_price",
    "silkUrl",
    "silk_url",
    "local_silk_path",
    "settling_band",
    "settling_rank",
    "map_x_pct",
    "map_y_px",
    "rail_gravity",
    "settling_score",
    "settling_reason",
    "source",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def canon(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def num(value: object, default: float = math.nan) -> float:
    try:
        text = clean(value).replace("$", "").replace(",", "")
        if text == "-":
            return default
        return float(text) if text else default
    except ValueError:
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def pick(row: dict[str, str] | None, names: list[str], default: str = "") -> str:
    if row is None:
        return default
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return default


def boolish(value: object) -> bool:
    return clean(value).upper() in {"1", "Y", "YES", "TRUE", "SCR", "SCRATCHED", "LATE SCR", "WITHDRAWN", "LATESCRATCHED"}


def zone_from_text(value: object) -> str:
    text = clean(value).upper()
    if any(token in text for token in ["LEADER", " LEAD", "FRONT", "ROLL FORWARD", "SPEED"]):
        return "LEADER"
    if any(token in text for token in ["ON PACE", "ON SPEED", "PROMINENT", "STALK", "HANDY", "PACE"]):
        return "PACE"
    if any(token in text for token in ["OFF PACE", "TRACK", "SIT", "BEHIND", "COVER"]):
        return "OFF PACE"
    if "MID" in text:
        return "MIDFIELD"
    if any(token in text for token in ["BACK", "CLOS", "REAR", "LATE", "DEEP"]):
        return "BACKMARKER"
    return ""


def lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        key = canon(pick(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"]))
        if key and key not in out:
            out[key] = row
    return out


def race_group_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        pick(row, ["race_date", "date", "meeting_date"]),
        pick(row, ["track", "meeting", "meeting_name"]),
        pick(row, ["race_no", "race_number", "race"]),
    )


def clean_track_key(value: object) -> str:
    return " ".join(pick({"value": str(value or "")}, ["value"]).upper().replace("|", " ").replace("_", " ").split())


def meeting_key_value(race_date: object, track: object) -> str:
    return f"{str(race_date or '').strip()}_{clean_track_key(track)}"


def canonical_race_key(race_date: object, track: object, race_no_value: object) -> str:
    digits = "".join(ch for ch in str(race_no_value or "") if ch.isdigit()) or "0"
    return f"{meeting_key_value(race_date, track)}_R{int(digits)}"


def canonical_runner_key(race_date: object, track: object, race_no_value: object, horse_key_value: object, horse: object) -> str:
    return f"{canonical_race_key(race_date, track, race_no_value)}_{canon(str(horse_key_value or horse or ''))}"


def field_quotas(count: int) -> dict[str, int]:
    return {
        "LEADER": max(1, min(2, round(count * 0.12))),
        "PACE": max(2, min(4, round(count * 0.22))),
        "OFF PACE": max(2, min(5, round(count * 0.23))),
        "MIDFIELD": max(2, min(5, round(count * 0.24))),
        "BACKMARKER": 999,
    }


def score_runner(
    row: dict[str, str],
    projected: dict[str, str] | None,
    dna: dict[str, str] | None,
    shape: dict[str, str] | None,
    index: int,
) -> tuple[float, str, str]:
    barrier = num(pick(row, ["barrier", "gate", "bar"]), 8)
    price = num(pick(row, ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win", "tab_fixed_win"]))
    early = num(pick(projected, ["early_speed_rating", "early_speed", "projected_spd", "speed_rank"]))
    avg_pos = num(pick(dna, ["avg_800m_position", "avg_first_call_position", "projected_spd"]))
    leader_pct = num(pick(dna, ["leader_pct"]), 0)
    onpace_pct = num(pick(dna, ["onpace_pct", "on_pace_pct"]), 0)
    back_pct = num(pick(dna, ["backmarker_pct", "backmarker_rate"]), 0)
    explicit = zone_from_text(
        " ".join(
            [
                pick(row, ["settling_position", "settling_band", "map_position", "run_style", "pace_profile", "speed_map_bucket", "proxy_energy_archetype"]),
                pick(projected, ["settling_band", "archetype", "settling_note"]),
                pick(dna, ["run_style_archetype", "positional_movement_profile"]),
            ]
        )
    )

    score = 50.0
    reason: list[str] = []
    if explicit:
        score += (2 - ZONES.index(explicit)) * 13
        reason.append(f"explicit={explicit}")
    if not math.isnan(avg_pos):
        score += max(-18, min(18, (8 - avg_pos) * 2.2))
        reason.append(f"avg_pos={avg_pos:.1f}")
    if not math.isnan(early):
        score += max(-14, min(18, (early - 50) / 2.6 if early > 24 else 26 - early))
        reason.append(f"early={early:.1f}")
    score += max(-7, min(7, (7 - barrier) * 0.85))
    if not math.isnan(price):
        score += max(-5, min(8, 12 - price))
        reason.append(f"price={price:.2f}")
    score += leader_pct * 16 + onpace_pct * 8 - back_pct * 11
    pressure = num(pick(shape, ["pace_pressure_score", "pressure_index"]))
    if not math.isnan(pressure) and pressure >= 70 and explicit in {"LEADER", "PACE"}:
        score -= 3
        reason.append("high_pressure")
    score -= index * 0.16
    return score, explicit, " | ".join(reason)


def assign_zones(scored: list[dict[str, object]]) -> None:
    limits = field_quotas(len(scored))
    counts = {zone: 0 for zone in ZONES}
    for rank, item in enumerate(sorted(scored, key=lambda row: float(row["score"]), reverse=True)):
        explicit = str(item.get("explicit") or "")
        if explicit and counts[explicit] < limits[explicit] + (99 if explicit == "BACKMARKER" else 1):
            zone = explicit
        elif rank < limits["LEADER"] and counts["LEADER"] < limits["LEADER"]:
            zone = "LEADER"
        elif rank < limits["LEADER"] + limits["PACE"] and counts["PACE"] < limits["PACE"]:
            zone = "PACE"
        elif rank < limits["LEADER"] + limits["PACE"] + limits["OFF PACE"] and counts["OFF PACE"] < limits["OFF PACE"]:
            zone = "OFF PACE"
        elif rank < limits["LEADER"] + limits["PACE"] + limits["OFF PACE"] + limits["MIDFIELD"] and counts["MIDFIELD"] < limits["MIDFIELD"]:
            zone = "MIDFIELD"
        else:
            zone = "BACKMARKER"
        counts[zone] += 1
        item["settling_band"] = zone


def geometry(zone: str, slot: int, total: int, barrier: float, score: float) -> tuple[float, float]:
    start, end = ZONE_X[zone]
    cluster_position = 0.5 if total <= 1 else slot / max(1, total - 1)
    x = start + (end - start) * (0.30 + cluster_position * 0.42)
    x += (((slot * 7) % 13) - 6) * 0.22
    x += max(-1.0, min(1.8, (barrier - 7) * 0.14))
    x += max(-1.1, min(1.1, (55 - score) * 0.035))
    x = max(start + 0.7, min(end - 0.7, x))

    centre = 0 if total <= 1 else slot - ((total - 1) / 2)
    wide_lift = max(-10, min(42, (barrier - 5) * 3.6))
    rail_gravity = 18 if barrier <= 2 else 10 if barrier <= 5 else 2 if barrier <= 8 else -4
    organic = ((slot * 11) % 23) - 11
    y = ZONE_BASE_Y[zone] + centre * 8 - wide_lift + rail_gravity + organic
    if zone == "LEADER":
        y += 8
    if zone == "BACKMARKER":
        y -= 8
    y = max(30, min(236, y))
    return round(x, 2), round(y, 1)


def read_first_populated_source() -> tuple[list[dict[str, str]], str]:
    for path in LIVE_SOURCE_CANDIDATES:
        rows = read_csv(path)
        if rows:
            return rows, path.name
    return [], ""


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    base, base_source = read_first_populated_source()
    if not base:
        raise SystemExit("NO_LIVE_BASE_SOURCE")

    projected = lookup(read_csv(PROJECTED) + read_csv(PACE))
    dna = lookup(read_csv(DNA))
    shape = lookup(read_csv(RACE_SHAPE))

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in base:
        if boolish(pick(row, ["is_scratched", "scratch_status", "runner_status", "status", "tab_scratched", "scratched"])):
            continue
        if not pick(row, ["horse", "runner", "horse_name", "runner_name"]):
            continue
        grouped.setdefault(race_group_key(row), []).append(row)

    rows: list[dict[str, object]] = []
    for _, runners in grouped.items():
        scored: list[dict[str, object]] = []
        for index, row in enumerate(sorted(runners, key=lambda r: num(pick(r, ["horse_no", "saddlecloth", "runner_no"]), 999))):
            hk = canon(pick(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"]))
            score, explicit, reason = score_runner(row, projected.get(hk), dna.get(hk), shape.get(hk), index)
            scored.append({"row": row, "score": score, "explicit": explicit, "reason": reason})
        assign_zones(scored)
        totals: dict[str, int] = {}
        slots: dict[str, int] = {}
        for item in scored:
            zone_name = str(item["settling_band"])
            totals[zone_name] = totals.get(zone_name, 0) + 1
        for item in scored:
            row = item["row"]
            zone = str(item["settling_band"])
            slot = slots.get(zone, 0)
            slots[zone] = slot + 1
            barrier = num(pick(row, ["barrier", "gate", "bar"]), 8)
            x, y = geometry(zone, slot, totals[zone], barrier, float(item["score"]))
            horse_value = pick(row, ["horse", "runner", "horse_name", "runner_name"])
            horse_key_value = canon(pick(row, ["horse_key"], horse_value))
            race_date = pick(row, ["race_date", "date", "meeting_date"])
            track = pick(row, ["track", "meeting", "meeting_name"])
            race_no_value = pick(row, ["race_no", "race_number", "race"])
            out_row = {
                "built_at": datetime.now().isoformat(timespec="seconds"),
                "race_date": race_date,
                "track": track,
                "race_no": race_no_value,
                "race_time": pick(row, ["race_time", "time"]),
                "horse_no": pick(row, ["horse_no", "saddlecloth", "number", "tab_no", "runner_no"]),
                "saddlecloth": pick(row, ["saddlecloth", "horse_no", "number", "tab_no", "runner_no"]),
                "horse": horse_value,
                "horse_key": horse_key_value,
                "barrier": "" if math.isnan(barrier) else int(barrier),
                "live_price": pick(row, ["live_price", "display_live_price", "ui_price", "sportsbet_price", "market_price", "fixed_win", "tab_fixed_win"], "-") or "-",
                "silkUrl": pick(row, ["silkUrl", "silk_url", "local_silk_path"]),
                "silk_url": pick(row, ["silk_url", "silkUrl", "local_silk_path"]),
                "local_silk_path": pick(row, ["local_silk_path", "silk_url", "silkUrl"]),
                "settling_band": zone,
                "settling_rank": slot + 1,
                "map_x_pct": x,
                "map_y_px": y,
                "rail_gravity": "RAIL" if barrier <= 5 else "OUTSIDE",
                "settling_score": round(float(item["score"]), 3),
                "settling_reason": item["reason"] or "field_fallback_barrier_market",
                "source": "EDGEIQ_REAL_SETTLING_MAP",
            }
            out_row["meeting_key"] = meeting_key_value(race_date, track)
            out_row["race_key"] = canonical_race_key(race_date, track, race_no_value)
            out_row["runner_key"] = canonical_runner_key(race_date, track, race_no_value, horse_key_value, horse_value)
            rows.append(out_row)

    diag = [
        {
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "base_source": base_source,
            "rows": len(rows),
            "races": len(grouped),
            "leaders": sum(1 for row in rows if row["settling_band"] == "LEADER"),
            "pace": sum(1 for row in rows if row["settling_band"] == "PACE"),
            "off_pace": sum(1 for row in rows if row["settling_band"] == "OFF PACE"),
            "midfield": sum(1 for row in rows if row["settling_band"] == "MIDFIELD"),
            "backmarkers": sum(1 for row in rows if row["settling_band"] == "BACKMARKER"),
        }
    ]
    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(DIAG, diag, list(diag[0].keys()))
    print("=" * 90)
    print("EDGEIQ REAL SPEED MAP ENGINE")
    print("=" * 90)
    print(diag[0])
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
