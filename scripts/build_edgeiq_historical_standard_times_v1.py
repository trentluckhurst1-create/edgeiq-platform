from __future__ import annotations

import csv
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PRIORITY = [
    DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv",
    DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv",
]

OUTPUT_MAIN = DATA / "edgeiq_historical_standard_times_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_historical_standard_times_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_historical_standard_times_v1_audit.csv"

MIN_EXACT_SAMPLE = 5
MIN_FALLBACK_SAMPLE = 8


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def find_column(headers: Sequence[str], aliases: Sequence[str]) -> str:
    lowered = {header.lower(): header for header in headers}
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    return ""


def parse_date(value: object) -> Optional[datetime]:
    txt = clean(value)
    if txt == "":
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def parse_float(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("$", "").replace("kg", "").replace("L", "").replace("l", "").replace(",", "")
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


def choose_source() -> Path:
    for path in SOURCE_PRIORITY:
        if path.exists():
            return path
    raise FileNotFoundError("No historical source found for standard times")


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


def percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * pct
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    fraction = index - lo
    return ordered[lo] + ((ordered[hi] - ordered[lo]) * fraction)


def build_record(
    track: str,
    distance_m: int,
    condition_group: str,
    profile_scope: str,
    values: List[float],
    date_min: Optional[datetime],
    date_max: Optional[datetime],
    source_file: str,
) -> Dict[str, object]:
    standard_time_sec = round(statistics.median(values), 3)
    p25 = percentile(values, 0.25)
    p75 = percentile(values, 0.75)
    sample_races = len(values)

    if profile_scope == "TRACK_DISTANCE_CONDITION":
        evidence_status = "READY" if sample_races >= MIN_EXACT_SAMPLE else "LIMITED"
    else:
        evidence_status = "READY" if sample_races >= MIN_FALLBACK_SAMPLE else "LIMITED"

    return {
        "track": track,
        "distance_m": distance_m,
        "condition_group": condition_group,
        "profile_scope": profile_scope,
        "sample_races": sample_races,
        "date_min": date_min.strftime("%Y-%m-%d") if date_min else "",
        "date_max": date_max.strftime("%Y-%m-%d") if date_max else "",
        "standard_time_sec": f"{standard_time_sec:.3f}",
        "p25_time_sec": f"{p25:.3f}" if p25 is not None else "",
        "p75_time_sec": f"{p75:.3f}" if p75 is not None else "",
        "evidence_status": evidence_status,
        "source_file": source_file,
    }


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    source_path = choose_source()

    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
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
        race_class_col = find_column(headers, ["race_class", "raceClass", "class_name"])
        race_name_col = find_column(headers, ["race_name", "raceName"])

        if not all([date_col, track_col, race_no_col, distance_col, time_col]):
            raise RuntimeError(
                f"Source {source_path.name} missing required columns: "
                f"date={date_col}, track={track_col}, race_no={race_no_col}, distance={distance_col}, time={time_col}"
            )

        exact_times: DefaultDict[Tuple[str, int, str], List[float]] = defaultdict(list)
        exact_dates: Dict[Tuple[str, int, str], Tuple[Optional[datetime], Optional[datetime]]] = {}
        fallback_times: DefaultDict[Tuple[str, int], List[float]] = defaultdict(list)
        fallback_dates: Dict[Tuple[str, int], Tuple[Optional[datetime], Optional[datetime]]] = {}
        winner_race_keys: set[Tuple[str, str, str]] = set()

        winner_rows = 0
        skipped_no_time = 0
        skipped_no_distance = 0

        for row in reader:
            if not is_winner(row, finish_col, won_col):
                continue
            if not is_flat_race(row, race_class_col, race_name_col):
                continue

            race_date = clean(row.get(date_col))
            track = upper(row.get(track_col))
            race_no = parse_race_no(row.get(race_no_col))
            race_key = (race_date, track, race_no)

            if race_key in winner_race_keys:
                continue

            winning_time_sec = parse_time_to_seconds(row.get(time_col))
            if winning_time_sec is None:
                skipped_no_time += 1
                continue

            distance_m = parse_distance_m(row.get(distance_col))
            if distance_m is None:
                skipped_no_distance += 1
                continue

            condition_group = normalize_condition(row.get(condition_col))
            parsed_date = parse_date(race_date)

            exact_key = (track, distance_m, condition_group)
            fallback_key = (track, distance_m)

            exact_times[exact_key].append(winning_time_sec)
            fallback_times[fallback_key].append(winning_time_sec)
            winner_race_keys.add(race_key)
            winner_rows += 1

            prev_min, prev_max = exact_dates.get(exact_key, (None, None))
            if parsed_date is not None:
                prev_min = parsed_date if prev_min is None or parsed_date < prev_min else prev_min
                prev_max = parsed_date if prev_max is None or parsed_date > prev_max else prev_max
            exact_dates[exact_key] = (prev_min, prev_max)

            fb_min, fb_max = fallback_dates.get(fallback_key, (None, None))
            if parsed_date is not None:
                fb_min = parsed_date if fb_min is None or parsed_date < fb_min else fb_min
                fb_max = parsed_date if fb_max is None or parsed_date > fb_max else fb_max
            fallback_dates[fallback_key] = (fb_min, fb_max)

    output_rows: List[Dict[str, object]] = []
    for key, values in sorted(exact_times.items()):
        track, distance_m, condition_group = key
        date_min, date_max = exact_dates.get(key, (None, None))
        row = build_record(
            track=track,
            distance_m=distance_m,
            condition_group=condition_group,
            profile_scope="TRACK_DISTANCE_CONDITION",
            values=values,
            date_min=date_min,
            date_max=date_max,
            source_file=source_path.name,
        )
        row["built_at"] = built_at
        output_rows.append(row)

    for key, values in sorted(fallback_times.items()):
        track, distance_m = key
        date_min, date_max = fallback_dates.get(key, (None, None))
        row = build_record(
            track=track,
            distance_m=distance_m,
            condition_group="ALL",
            profile_scope="TRACK_DISTANCE_ALL",
            values=values,
            date_min=date_min,
            date_max=date_max,
            source_file=source_path.name,
        )
        row["built_at"] = built_at
        output_rows.append(row)

    status_counts = Counter(clean(row.get("evidence_status")) for row in output_rows)
    scope_counts = Counter(clean(row.get("profile_scope")) for row in output_rows)

    summary_row = {
        "status": "EDGEIQ_HISTORICAL_STANDARD_TIMES_V1_BUILT",
        "source_file": source_path.name,
        "winner_rows_used": winner_rows,
        "unique_tracks": len({clean(row.get("track")) for row in output_rows if clean(row.get("track"))}),
        "unique_distances": len({clean(row.get("distance_m")) for row in output_rows if clean(row.get("distance_m"))}),
        "standard_rows": len(output_rows),
        "exact_condition_rows": scope_counts.get("TRACK_DISTANCE_CONDITION", 0),
        "fallback_track_distance_rows": scope_counts.get("TRACK_DISTANCE_ALL", 0),
        "ready_rows": status_counts.get("READY", 0),
        "limited_rows": status_counts.get("LIMITED", 0),
        "skipped_no_time": skipped_no_time,
        "skipped_no_distance": skipped_no_distance,
        "ready_for_variant_engine": "YES" if winner_rows > 0 and status_counts.get("READY", 0) > 0 else "NO",
        "built_at": built_at,
    }

    audit_rows = [
        {
            "track": row["track"],
            "distance_m": row["distance_m"],
            "condition_group": row["condition_group"],
            "profile_scope": row["profile_scope"],
            "sample_races": row["sample_races"],
            "standard_time_sec": row["standard_time_sec"],
            "evidence_status": row["evidence_status"],
            "source_file": row["source_file"],
            "built_at": built_at,
        }
        for row in output_rows
    ]

    fieldnames = [
        "track",
        "distance_m",
        "condition_group",
        "profile_scope",
        "sample_races",
        "date_min",
        "date_max",
        "standard_time_sec",
        "p25_time_sec",
        "p75_time_sec",
        "evidence_status",
        "source_file",
        "built_at",
    ]
    summary_fields = list(summary_row.keys())
    audit_fields = list(audit_rows[0].keys()) if audit_rows else [
        "track",
        "distance_m",
        "condition_group",
        "profile_scope",
        "sample_races",
        "standard_time_sec",
        "evidence_status",
        "source_file",
        "built_at",
    ]

    write_csv(OUTPUT_MAIN, output_rows, fieldnames)
    write_csv(OUTPUT_SUMMARY, [summary_row], summary_fields)
    write_csv(OUTPUT_AUDIT, audit_rows, audit_fields)

    print("EDGEiQ historical standard times built")
    print(f"Source file: {source_path.name}")
    print(f"Winner rows used: {winner_rows}")
    print(f"Standard rows: {len(output_rows)}")
    print(f"Ready for variant engine: {summary_row['ready_for_variant_engine']}")


if __name__ == "__main__":
    main()
