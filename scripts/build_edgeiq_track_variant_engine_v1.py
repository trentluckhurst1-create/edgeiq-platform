from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
INPUT_STANDARDS = DATA / "edgeiq_historical_standard_times_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_track_variant_engine_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_track_variant_engine_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_track_variant_engine_v1_audit.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("$", "").replace("kg", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return None


def parse_race_no(value: object) -> str:
    number = parse_float(value)
    if number is None:
        return clean(value)
    return str(int(round(number)))


def parse_distance_m(value: object) -> Optional[int]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("m", "").replace("M", "").replace(",", "")
    try:
        return int(round(float(txt)))
    except Exception:
        return None


def parse_time_to_seconds(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("s", "").replace("S", "")
    if ":" in txt:
        parts = txt.split(":")
        try:
            if len(parts) == 2:
                return (float(parts[0]) * 60.0) + float(parts[1])
            if len(parts) == 3:
                return (float(parts[0]) * 3600.0) + (float(parts[1]) * 60.0) + float(parts[2])
        except Exception:
            return None
    numeric = parse_float(txt)
    if numeric is None:
        return None
    if numeric > 1000:
        return numeric / 100.0
    return numeric


def normalize_condition(value: object) -> str:
    txt = upper(value)
    if txt == "":
        return "UNKNOWN"
    if "HEAVY" in txt:
        return "HEAVY"
    if "SOFT" in txt:
        return "SOFT"
    if "GOOD" in txt:
        return "GOOD"
    if "FIRM" in txt:
        return "FIRM"
    if "SYNTH" in txt or "POLY" in txt or "TAPETA" in txt or "ALL WEATHER" in txt:
        return "SYNTH"
    return "UNKNOWN"


def is_flat_race(row: Dict[str, str], race_class_col: str, race_name_col: str) -> bool:
    raw = " ".join([upper(row.get(race_class_col)), upper(row.get(race_name_col))]).strip()
    if raw == "":
        return True
    blocked_tokens = ["TRIAL", "HURDLE", "STEEPLE", "JUMP", "CHASE", "H'CAP HURDLE", "H'CAP STEEPLE"]
    return not any(token in raw for token in blocked_tokens)


def find_column(headers: Sequence[str], aliases: Sequence[str]) -> str:
    lowered = {header.lower(): header for header in headers}
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    return ""


def is_winner(row: Dict[str, str], finish_col: str, won_col: str) -> bool:
    if won_col:
        won_txt = upper(row.get(won_col))
        if won_txt in {"1", "TRUE", "YES", "Y"}:
            return True
    if finish_col:
        finish_val = parse_float(row.get(finish_col))
        if finish_val is not None and int(round(finish_val)) == 1:
            return True
        finish_txt = upper(row.get(finish_col))
        if finish_txt in {"1", "1ST", "FIRST"}:
            return True
    return False


def variant_band(value: Optional[float]) -> str:
    if value is None:
        return "UNKNOWN"
    if value <= -1.0:
        return "VERY_FAST"
    if value <= -0.35:
        return "FAST"
    if value < 0.35:
        return "NEUTRAL"
    if value < 1.0:
        return "SLOW"
    return "VERY_SLOW"


def variant_narrative(meeting_variant: Optional[float], timed_races: int) -> str:
    if meeting_variant is None:
        return "Variant unavailable because timed race coverage or standards were missing."
    direction = "faster" if meeting_variant < 0 else "slower" if meeting_variant > 0 else "neutral"
    return (
        f"Meeting played {abs(meeting_variant):.2f}s {direction} than the historical standard "
        f"across {timed_races} timed races."
    )


def evidence_status(meeting_variant: Optional[float], timed_races: int) -> str:
    if meeting_variant is None or timed_races <= 0:
        return "NO_STANDARD"
    if timed_races >= 5:
        return "STRONG_MEETING"
    if timed_races >= 3:
        return "USABLE_MEETING"
    return "LIMITED_MEETING"


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    if not INPUT_RESULTS.exists():
        raise FileNotFoundError(INPUT_RESULTS)
    if not INPUT_STANDARDS.exists():
        raise FileNotFoundError(INPUT_STANDARDS)

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    exact_standard: Dict[Tuple[str, int, str], Dict[str, str]] = {}
    fallback_standard: Dict[Tuple[str, int], Dict[str, str]] = {}

    with INPUT_STANDARDS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            track = upper(row.get("track"))
            distance_m = parse_distance_m(row.get("distance_m"))
            if distance_m is None:
                continue
            scope = clean(row.get("profile_scope"))
            if scope == "TRACK_DISTANCE_CONDITION":
                exact_standard[(track, distance_m, upper(row.get("condition_group")))] = row
            elif scope == "TRACK_DISTANCE_ALL":
                fallback_standard[(track, distance_m)] = row

    with INPUT_RESULTS.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []

        date_col = find_column(headers, ["race_date", "meeting_date", "date"])
        track_col = find_column(headers, ["track"])
        race_no_col = find_column(headers, ["race_no"])
        distance_col = find_column(headers, ["distance"])
        time_col = find_column(headers, ["winning_time", "raceTime", "race_time"])
        finish_col = find_column(headers, ["finish_num", "finish_position", "finishPosition", "finish_pos", "finish"])
        won_col = find_column(headers, ["won"])
        condition_col = find_column(headers, ["track_condition", "trackCondition", "condition"])
        rail_col = find_column(headers, ["rail_position"])
        race_class_col = find_column(headers, ["race_class", "raceClass", "class_name"])
        race_name_col = find_column(headers, ["race_name", "raceName"])

        race_rows: List[Dict[str, object]] = []
        meeting_variants: DefaultDict[Tuple[str, str], List[float]] = defaultdict(list)
        seen_races: set[Tuple[str, str, str]] = set()

        for row in reader:
            if not is_winner(row, finish_col, won_col):
                continue
            if not is_flat_race(row, race_class_col, race_name_col):
                continue

            race_date = clean(row.get(date_col))
            track = upper(row.get(track_col))
            race_no = parse_race_no(row.get(race_no_col))
            race_key = (race_date, track, race_no)
            if race_key in seen_races:
                continue
            seen_races.add(race_key)

            distance_m = parse_distance_m(row.get(distance_col))
            actual_time_sec = parse_time_to_seconds(row.get(time_col))
            condition_group = normalize_condition(row.get(condition_col))
            rail_position = clean(row.get(rail_col))

            standard_row = None
            standard_scope = ""
            if distance_m is not None:
                standard_row = exact_standard.get((track, distance_m, condition_group))
                if standard_row is not None:
                    standard_scope = "TRACK_DISTANCE_CONDITION"
                else:
                    standard_row = fallback_standard.get((track, distance_m))
                    if standard_row is not None:
                        standard_scope = "TRACK_DISTANCE_ALL"

            standard_time_sec = parse_float(standard_row.get("standard_time_sec")) if standard_row else None
            raw_variant_sec = None
            if actual_time_sec is not None and standard_time_sec is not None:
                raw_variant_sec = round(actual_time_sec - standard_time_sec, 3)
                meeting_variants[(race_date, track)].append(raw_variant_sec)

            race_rows.append(
                {
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "distance": distance_m if distance_m is not None else clean(row.get(distance_col)),
                    "condition_official": clean(row.get(condition_col)),
                    "condition_group": condition_group,
                    "rail_position": rail_position,
                    "standard_time_sec": f"{standard_time_sec:.3f}" if standard_time_sec is not None else "",
                    "actual_winner_time_sec": f"{actual_time_sec:.3f}" if actual_time_sec is not None else "",
                    "raw_variant_sec": f"{raw_variant_sec:.3f}" if raw_variant_sec is not None else "",
                    "standard_scope": standard_scope,
                }
            )

    meeting_summary: Dict[Tuple[str, str], Tuple[Optional[float], int]] = {}
    for key, values in meeting_variants.items():
        meeting_summary[key] = (round(statistics.median(values), 3), len(values))

    output_rows: List[Dict[str, object]] = []
    for row in race_rows:
        meeting_key = (clean(row.get("race_date")), clean(row.get("track")))
        meeting_variant, timed_races = meeting_summary.get(meeting_key, (None, 0))
        band = variant_band(meeting_variant)
        output_rows.append(
            {
                **row,
                "meeting_variant_sec": f"{meeting_variant:.3f}" if meeting_variant is not None else "",
                "variant_band": band,
                "variant_narrative": variant_narrative(meeting_variant, timed_races),
                "evidence_status": evidence_status(meeting_variant, timed_races),
                "timed_races_in_meeting": timed_races,
                "built_at": built_at,
            }
        )

    band_counts = Counter(clean(row.get("variant_band")) for row in output_rows)
    status_counts = Counter(clean(row.get("evidence_status")) for row in output_rows)

    summary_row = {
        "status": "EDGEIQ_TRACK_VARIANT_ENGINE_V1_BUILT",
        "input_results_file": INPUT_RESULTS.name,
        "input_standard_times_file": INPUT_STANDARDS.name,
        "race_rows": len(race_rows),
        "meeting_count": len(meeting_summary),
        "timed_meetings": sum(1 for _, count in meeting_summary.values() if count > 0),
        "missing_standard_races": sum(1 for row in output_rows if clean(row.get("standard_time_sec")) == ""),
        "very_fast_races": band_counts.get("VERY_FAST", 0),
        "fast_races": band_counts.get("FAST", 0),
        "neutral_races": band_counts.get("NEUTRAL", 0),
        "slow_races": band_counts.get("SLOW", 0),
        "very_slow_races": band_counts.get("VERY_SLOW", 0),
        "strong_meeting_rows": status_counts.get("STRONG_MEETING", 0),
        "usable_meeting_rows": status_counts.get("USABLE_MEETING", 0),
        "limited_meeting_rows": status_counts.get("LIMITED_MEETING", 0),
        "no_standard_rows": status_counts.get("NO_STANDARD", 0),
        "built_at": built_at,
    }

    audit_rows = [
        {
            "race_date": row["race_date"],
            "track": row["track"],
            "race_no": row["race_no"],
            "standard_scope": row["standard_scope"],
            "variant_band": row["variant_band"],
            "evidence_status": row["evidence_status"],
            "timed_races_in_meeting": row["timed_races_in_meeting"],
            "built_at": built_at,
        }
        for row in output_rows
    ]

    fieldnames = [
        "race_date",
        "track",
        "race_no",
        "distance",
        "condition_official",
        "condition_group",
        "rail_position",
        "standard_time_sec",
        "actual_winner_time_sec",
        "raw_variant_sec",
        "meeting_variant_sec",
        "standard_scope",
        "variant_band",
        "variant_narrative",
        "evidence_status",
        "timed_races_in_meeting",
        "built_at",
    ]
    summary_fields = list(summary_row.keys())
    audit_fields = list(audit_rows[0].keys()) if audit_rows else [
        "race_date",
        "track",
        "race_no",
        "standard_scope",
        "variant_band",
        "evidence_status",
        "timed_races_in_meeting",
        "built_at",
    ]

    write_csv(OUTPUT_MAIN, output_rows, fieldnames)
    write_csv(OUTPUT_SUMMARY, [summary_row], summary_fields)
    write_csv(OUTPUT_AUDIT, audit_rows, audit_fields)

    print("EDGEiQ track variant engine built")
    print(f"Race rows: {len(race_rows)}")
    print(f"Meetings with timed variants: {len(meeting_summary)}")
    print(f"Missing-standard races: {summary_row['missing_standard_races']}")


if __name__ == "__main__":
    main()
