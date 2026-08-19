from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import csv
import json
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROBE_CSV = DATA / "edgeiq_racingcom_speed_network_probe_v1.csv"

RUNNER_OUT = DATA / "edgeiq_racingcom_runner_speed_fact_v1.csv"
SECTIONAL_OUT = DATA / "edgeiq_racingcom_runner_sectional_fact_v1.csv"
SPLIT_OUT = DATA / "edgeiq_racingcom_runner_split_fact_v1.csv"
RACE_OUT = DATA / "edgeiq_racingcom_race_speed_summary_v1.csv"
AUDIT_OUT = DATA / "edgeiq_racingcom_runner_speed_warehouse_v1_audit.json"


RUNNER_COLUMNS = [
    "race_key",
    "race_date",
    "track",
    "race_number",
    "source_page_url",
    "source_payload_file",
    "source_provider",
    "timing_source",
    "is_timing_complete",
    "is_complete_data",
    "race_time_raw",
    "race_time_seconds",
    "runner_id",
    "saddle_number",
    "horse_name",
    "horse_url",
    "silk_url",
    "trainer_name",
    "trainer_url",
    "jockey_name",
    "jockey_url",
    "finish_position",
    "finish_position_abbreviation",
    "start_position",
    "barrier_number",
    "runner_race_time_raw",
    "runner_race_time_seconds",
    "time_variation_to_winner_source",
    "beaten_margin_source",
    "distance_run_source",
    "distance_variation_to_winner_source",
    "six_hundred_metres_time_raw",
    "six_hundred_metres_time_seconds",
    "two_hundred_metres_time_raw",
    "two_hundred_metres_time_seconds",
    "early_speed_source",
    "mid_speed_source",
    "late_speed_source",
    "overall_peak_speed_source",
    "peak_speed_location",
    "overall_average_speed_source",
    "distance_from_rail_source",
    "sectional_count",
    "split_count",
    "comment",
]

SECTIONAL_COLUMNS = [
    "race_key",
    "race_date",
    "track",
    "race_number",
    "source_page_url",
    "source_payload_file",
    "runner_id",
    "saddle_number",
    "horse_name",
    "sectional_sequence",
    "distance_marker",
    "position",
    "cumulative_time_raw",
    "cumulative_time_seconds",
    "average_speed_source",
]

SPLIT_COLUMNS = [
    "race_key",
    "race_date",
    "track",
    "race_number",
    "source_page_url",
    "source_payload_file",
    "runner_id",
    "saddle_number",
    "horse_name",
    "split_sequence",
    "split_distance",
    "position",
    "split_time_raw",
    "split_time_seconds",
    "average_speed_source",
]

RACE_COLUMNS = [
    "race_key",
    "race_date",
    "track",
    "race_number",
    "source_page_url",
    "source_payload_file",
    "source_provider",
    "timing_source",
    "is_timing_complete",
    "is_complete_data",
    "race_time_raw",
    "race_time_seconds",
    "runner_count",
    "sectional_distances_json",
    "split_distances_json",
    "field_sectional_times_json",
    "fastest_early_source",
    "fastest_mid_source",
    "fastest_late_source",
    "fastest_peak_speed_source",
    "fastest_average_speed_source",
    "fastest_early_info_json",
    "fastest_mid_info_json",
    "fastest_late_info_json",
    "fastest_peak_speed_info_json",
    "fastest_average_speed_info_json",
    "fastest_sectional_times_json",
    "fastest_split_times_json",
]


def log(message: str) -> None:
    print(f"[runner_speed_warehouse_v1] {message}", flush=True)


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def source_value(value: Any) -> str:
    """
    Preserve source semantics without asserting an undocumented unit.
    """
    return clean(value)


def time_to_seconds(value: Any) -> str:
    """
    Convert source time strings only when their format is unambiguous.

    Supported:
      12.64
      1:12.34
      01:12.34

    Empty, null or malformed values remain blank.
    """
    text = clean(value)
    if not text:
        return ""

    try:
        if ":" in text:
            parts = text.split(":")
            if len(parts) != 2:
                return ""

            minutes = float(parts[0])
            seconds = float(parts[1])
            total = minutes * 60.0 + seconds
        else:
            total = float(text)

        return f"{total:.3f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return ""


def json_compact(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def parse_page_url(page_url: str) -> tuple[str, str, str]:
    """
    Expected Racing.com shape:

    /form/YYYY-MM-DD/TRACK/race/N/speed-data
    """
    parsed = urlparse(page_url)
    path = parsed.path.strip("/")

    match = re.search(
        r"^form/"
        r"(?P<date>\d{4}-\d{2}-\d{2})/"
        r"(?P<track>[^/]+)/"
        r"race/"
        r"(?P<race>\d+)/"
        r"speed-data$",
        path,
        flags=re.IGNORECASE,
    )

    if not match:
        return "", "", ""

    race_date = match.group("date")
    track_slug = match.group("track")
    race_number = match.group("race")

    track = " ".join(
        part.capitalize()
        for part in re.split(r"[-_]+", track_slug)
        if part
    )

    return race_date, track, race_number


def resolve_payload_path(raw_sample_file: str) -> Path:
    candidate = Path(raw_sample_file)

    if candidate.is_absolute():
        return candidate

    return ROOT / candidate


def first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def write_csv(
    path: Path,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow({
                column: row.get(column, "")
                for column in columns
            })


def load_probe_rows() -> list[dict[str, str]]:
    if not PROBE_CSV.exists():
        raise FileNotFoundError(f"Missing probe CSV: {PROBE_CSV}")

    with PROBE_CSV.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    probe_rows = load_probe_rows()

    sectional_probe_rows = [
        row
        for row in probe_rows
        if "sectionaltimes_callback" in clean(
            row.get("response_url")
        ).lower()
    ]

    if not sectional_probe_rows:
        raise RuntimeError(
            "No sectionaltimes_callback rows found in probe CSV."
        )

    runner_rows: list[dict[str, Any]] = []
    sectional_rows: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    race_rows: list[dict[str, Any]] = []

    missing_payloads: list[str] = []
    unreadable_payloads: list[dict[str, str]] = []
    invalid_payloads: list[dict[str, str]] = []
    duplicate_race_keys: list[str] = []

    race_key_counts: Counter[str] = Counter()

    for probe_row in sectional_probe_rows:
        page_url = clean(probe_row.get("page_url"))
        raw_sample_file = clean(probe_row.get("raw_sample_file"))

        race_date, track, race_number = parse_page_url(page_url)

        if not race_date or not track or not race_number:
            invalid_payloads.append({
                "page_url": page_url,
                "payload": raw_sample_file,
                "reason": "PAGE_URL_PARSE_FAILED",
            })
            continue

        race_key = f"{race_date}|{track.upper()}|R{int(race_number):02d}"
        race_key_counts[race_key] += 1

        payload_path = resolve_payload_path(raw_sample_file)

        if not payload_path.exists():
            missing_payloads.append(str(payload_path))
            continue

        try:
            payload = json.loads(
                payload_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            unreadable_payloads.append({
                "payload": str(payload_path),
                "reason": str(exc),
            })
            continue

        data = payload.get("data")

        if not isinstance(data, dict):
            invalid_payloads.append({
                "page_url": page_url,
                "payload": str(payload_path),
                "reason": "DATA_OBJECT_MISSING",
            })
            continue

        race = first_present(
            data,
            "sectionaltimes_callback",
            "getRaceForm",
        )

        if not isinstance(race, dict):
            invalid_payloads.append({
                "page_url": page_url,
                "payload": str(payload_path),
                "reason": "SECTIONAL_RACE_OBJECT_MISSING",
            })
            continue

        horses = first_present(race, "Horses", "raceEntryTimes")

        if not isinstance(horses, list):
            invalid_payloads.append({
                "page_url": page_url,
                "payload": str(payload_path),
                "reason": "HORSES_ARRAY_MISSING",
            })
            continue

        timing_source = source_value(
            first_present(race, "Source", "timingSource")
        )
        is_timing_complete = source_value(
            first_present(race, "IsComplete", "isTimingComplete")
        )
        is_complete_data = source_value(
            first_present(race, "IsCompleteData", "isCompleteData")
        )

        race_time_raw = source_value(
            first_present(race, "RaceTime", "raceTime")
        )

        source_file_relative = payload_path.relative_to(ROOT).as_posix()

        race_rows.append({
            "race_key": race_key,
            "race_date": race_date,
            "track": track,
            "race_number": race_number,
            "source_page_url": page_url,
            "source_payload_file": source_file_relative,
            "source_provider": "RACING.COM",
            "timing_source": timing_source,
            "is_timing_complete": is_timing_complete,
            "is_complete_data": is_complete_data,
            "race_time_raw": race_time_raw,
            "race_time_seconds": time_to_seconds(race_time_raw),
            "runner_count": len(horses),
            "sectional_distances_json": json_compact(
                first_present(
                    race,
                    "SectionalDistances",
                    "sectionalDistances",
                )
            ),
            "split_distances_json": json_compact(
                first_present(
                    race,
                    "SplitDistances",
                    "splitDistances",
                )
            ),
            "field_sectional_times_json": json_compact(
                first_present(
                    race,
                    "FieldSectionalTimes",
                    "fieldSectionalTimes",
                )
            ),
            "fastest_early_source": source_value(
                first_present(race, "FastestEarly", "fastestEarly")
            ),
            "fastest_mid_source": source_value(
                first_present(race, "FastestMid", "fastestMid")
            ),
            "fastest_late_source": source_value(
                first_present(race, "FastestLate", "fastestLate")
            ),
            "fastest_peak_speed_source": source_value(
                first_present(
                    race,
                    "FastestPeakSpeed",
                    "fastestPeakSpeed",
                )
            ),
            "fastest_average_speed_source": source_value(
                first_present(
                    race,
                    "FastestAvgSpeed",
                    "fastestAvgSpeed",
                )
            ),
            "fastest_early_info_json": json_compact(
                first_present(
                    race,
                    "FastestEarlyInfo",
                    "fastestEarlyInfo",
                )
            ),
            "fastest_mid_info_json": json_compact(
                first_present(
                    race,
                    "FastestMidInfo",
                    "fastestMidInfo",
                )
            ),
            "fastest_late_info_json": json_compact(
                first_present(
                    race,
                    "FastestLateInfo",
                    "fastestLateInfo",
                )
            ),
            "fastest_peak_speed_info_json": json_compact(
                first_present(
                    race,
                    "FastestPeakSpeedInfo",
                    "fastestPeakSpeedInfo",
                )
            ),
            "fastest_average_speed_info_json": json_compact(
                first_present(
                    race,
                    "FastestAvgSpeedInfo",
                    "fastestAvgSpeedInfo",
                )
            ),
            "fastest_sectional_times_json": json_compact(
                first_present(
                    race,
                    "FastestSectionalTimes",
                    "fastestSectionalTimes",
                )
            ),
            "fastest_split_times_json": json_compact(
                first_present(
                    race,
                    "FastestSplitTimes",
                    "fastestSplitTimes",
                )
            ),
        })

        for horse in horses:
            if not isinstance(horse, dict):
                continue

            runner_id = source_value(first_present(horse, "id", "Id"))
            saddle_number = source_value(
                first_present(
                    horse,
                    "SaddleNumber",
                    "saddleNumber",
                )
            )
            horse_name = source_value(
                first_present(
                    horse,
                    "FullName",
                    "horseName",
                )
            )

            sectional_times = first_present(
                horse,
                "SectionalTimes",
                "times",
            )
            split_times = first_present(
                horse,
                "SplitTimes",
                "splitTimes",
            )

            if not isinstance(sectional_times, list):
                sectional_times = []

            if not isinstance(split_times, list):
                split_times = []

            runner_race_time_raw = source_value(
                first_present(
                    horse,
                    "RaceTime",
                    "finishTime",
                )
            )
            last_600_raw = source_value(
                first_present(
                    horse,
                    "SixHundredMetresTime",
                    "sixHundredMetresTime",
                )
            )
            last_200_raw = source_value(
                first_present(
                    horse,
                    "TwoHundredMetresTime",
                    "twoHundredMetresTime",
                )
            )

            runner_rows.append({
                "race_key": race_key,
                "race_date": race_date,
                "track": track,
                "race_number": race_number,
                "source_page_url": page_url,
                "source_payload_file": source_file_relative,
                "source_provider": "RACING.COM",
                "timing_source": timing_source,
                "is_timing_complete": is_timing_complete,
                "is_complete_data": is_complete_data,
                "race_time_raw": race_time_raw,
                "race_time_seconds": time_to_seconds(race_time_raw),
                "runner_id": runner_id,
                "saddle_number": saddle_number,
                "horse_name": horse_name,
                "horse_url": source_value(
                    first_present(horse, "HorseUrl", "horseUrl")
                ),
                "silk_url": source_value(
                    first_present(horse, "SilkUrl", "silkUrl")
                ),
                "trainer_name": source_value(
                    first_present(horse, "Trainer", "trainerName")
                ),
                "trainer_url": source_value(
                    first_present(horse, "TrainerUrl", "trainerUrl")
                ),
                "jockey_name": source_value(
                    first_present(horse, "Jockey", "jockeyName")
                ),
                "jockey_url": source_value(
                    first_present(horse, "JockeyUrl", "jockeyUrl")
                ),
                "finish_position": source_value(
                    first_present(
                        horse,
                        "FinalPosition",
                        "finishPosition",
                    )
                ),
                "finish_position_abbreviation": source_value(
                    first_present(
                        horse,
                        "FinalPositionAbbreviation",
                        "finishPositionAbv",
                    )
                ),
                "start_position": source_value(
                    first_present(
                        horse,
                        "StartPosition",
                        "startPosition",
                    )
                ),
                "barrier_number": source_value(
                    first_present(
                        horse,
                        "BarrierNumber",
                        "barrierNumber",
                    )
                ),
                "runner_race_time_raw": runner_race_time_raw,
                "runner_race_time_seconds": time_to_seconds(
                    runner_race_time_raw
                ),
                "time_variation_to_winner_source": source_value(
                    first_present(
                        horse,
                        "TimeVarToWinner",
                        "timeVarToWinner",
                    )
                ),
                "beaten_margin_source": source_value(
                    first_present(
                        horse,
                        "BeatenMargin",
                        "beatenMargin",
                    )
                ),
                "distance_run_source": source_value(
                    first_present(
                        horse,
                        "DistanceRun",
                        "distanceTravelled",
                    )
                ),
                "distance_variation_to_winner_source": source_value(
                    first_present(
                        horse,
                        "DistanceVarToWinner",
                        "distanceVarToWinner",
                    )
                ),
                "six_hundred_metres_time_raw": last_600_raw,
                "six_hundred_metres_time_seconds": time_to_seconds(
                    last_600_raw
                ),
                "two_hundred_metres_time_raw": last_200_raw,
                "two_hundred_metres_time_seconds": time_to_seconds(
                    last_200_raw
                ),
                "early_speed_source": source_value(
                    first_present(horse, "Early", "avgSpeedEarly")
                ),
                "mid_speed_source": source_value(
                    first_present(horse, "Mid", "avgSpeedMid")
                ),
                "late_speed_source": source_value(
                    first_present(horse, "Late", "avgSpeedLate")
                ),
                "overall_peak_speed_source": source_value(
                    first_present(
                        horse,
                        "OverallPeakSpeed",
                        "overallPeakSpeed",
                    )
                ),
                "peak_speed_location": source_value(
                    first_present(
                        horse,
                        "PeakSpeedLocation",
                        "peakSpeedLocation",
                    )
                ),
                "overall_average_speed_source": source_value(
                    first_present(
                        horse,
                        "OverallAvgSpeed",
                        "overallAvgSpeed",
                    )
                ),
                "distance_from_rail_source": source_value(
                    first_present(
                        horse,
                        "DistanceFromRail",
                        "distanceFromRail",
                    )
                ),
                "sectional_count": len(sectional_times),
                "split_count": len(split_times),
                "comment": source_value(
                    first_present(horse, "Comment", "comment")
                ),
            })

            for sequence, sectional in enumerate(
                sectional_times,
                start=1,
            ):
                if not isinstance(sectional, dict):
                    continue

                time_raw = source_value(
                    first_present(
                        sectional,
                        "Time",
                        "intermediateTime",
                    )
                )

                sectional_rows.append({
                    "race_key": race_key,
                    "race_date": race_date,
                    "track": track,
                    "race_number": race_number,
                    "source_page_url": page_url,
                    "source_payload_file": source_file_relative,
                    "runner_id": runner_id,
                    "saddle_number": saddle_number,
                    "horse_name": horse_name,
                    "sectional_sequence": sequence,
                    "distance_marker": source_value(
                        first_present(
                            sectional,
                            "Distance",
                            "distance",
                        )
                    ),
                    "position": source_value(
                        first_present(
                            sectional,
                            "Position",
                            "rank",
                        )
                    ),
                    "cumulative_time_raw": time_raw,
                    "cumulative_time_seconds": time_to_seconds(time_raw),
                    "average_speed_source": source_value(
                        first_present(
                            sectional,
                            "AvgSpeed",
                            "avgSpeed",
                        )
                    ),
                })

            for sequence, split in enumerate(
                split_times,
                start=1,
            ):
                if not isinstance(split, dict):
                    continue

                time_raw = source_value(
                    first_present(split, "Time", "time")
                )

                split_rows.append({
                    "race_key": race_key,
                    "race_date": race_date,
                    "track": track,
                    "race_number": race_number,
                    "source_page_url": page_url,
                    "source_payload_file": source_file_relative,
                    "runner_id": runner_id,
                    "saddle_number": saddle_number,
                    "horse_name": horse_name,
                    "split_sequence": sequence,
                    "split_distance": source_value(
                        first_present(
                            split,
                            "Distance",
                            "distance",
                        )
                    ),
                    "position": source_value(
                        first_present(
                            split,
                            "Position",
                            "position",
                        )
                    ),
                    "split_time_raw": time_raw,
                    "split_time_seconds": time_to_seconds(time_raw),
                    "average_speed_source": source_value(
                        first_present(
                            split,
                            "AvgSpeed",
                            "avgSpeed",
                        )
                    ),
                })

    duplicate_race_keys = sorted(
        race_key
        for race_key, count in race_key_counts.items()
        if count > 1
    )

    runner_identity_counts = Counter(
        (
            row["race_key"],
            row["runner_id"],
        )
        for row in runner_rows
    )

    duplicate_runner_keys = [
        {
            "race_key": race_key,
            "runner_id": runner_id,
            "count": count,
        }
        for (race_key, runner_id), count
        in sorted(runner_identity_counts.items())
        if count > 1
    ]

    sectionals_without_runner = sum(
        1
        for row in sectional_rows
        if not row["runner_id"] or not row["horse_name"]
    )

    splits_without_runner = sum(
        1
        for row in split_rows
        if not row["runner_id"] or not row["horse_name"]
    )

    runner_rows.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
            int(row["finish_position"] or 999),
            int(row["saddle_number"] or 999),
        )
    )

    sectional_rows.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
            int(row["saddle_number"] or 999),
            int(row["sectional_sequence"] or 0),
        )
    )

    split_rows.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
            int(row["saddle_number"] or 999),
            int(row["split_sequence"] or 0),
        )
    )

    race_rows.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
        )
    )

    write_csv(RUNNER_OUT, RUNNER_COLUMNS, runner_rows)
    write_csv(SECTIONAL_OUT, SECTIONAL_COLUMNS, sectional_rows)
    write_csv(SPLIT_OUT, SPLIT_COLUMNS, split_rows)
    write_csv(RACE_OUT, RACE_COLUMNS, race_rows)

    audit_status = "PASS"

    failures: list[str] = []

    if not race_rows:
        failures.append("NO_RACE_ROWS")
    if not runner_rows:
        failures.append("NO_RUNNER_ROWS")
    if not sectional_rows:
        failures.append("NO_SECTIONAL_ROWS")
    if not split_rows:
        failures.append("NO_SPLIT_ROWS")
    if missing_payloads:
        failures.append("MISSING_PAYLOADS")
    if unreadable_payloads:
        failures.append("UNREADABLE_PAYLOADS")
    if invalid_payloads:
        failures.append("INVALID_PAYLOADS")
    if duplicate_race_keys:
        failures.append("DUPLICATE_RACE_KEYS")
    if duplicate_runner_keys:
        failures.append("DUPLICATE_RUNNER_KEYS")
    if sectionals_without_runner:
        failures.append("SECTIONALS_WITHOUT_RUNNER_IDENTITY")
    if splits_without_runner:
        failures.append("SPLITS_WITHOUT_RUNNER_IDENTITY")

    if failures:
        audit_status = "FAIL"

    audit = {
        "audit_name": "EDGEIQ_RACINGCOM_RUNNER_SPEED_WAREHOUSE_V1",
        "generated_at_utc": generated_at,
        "status": audit_status,
        "failures": failures,
        "source_probe_csv": PROBE_CSV.relative_to(ROOT).as_posix(),
        "sectional_probe_rows": len(sectional_probe_rows),
        "race_rows": len(race_rows),
        "runner_rows": len(runner_rows),
        "runner_sectional_rows": len(sectional_rows),
        "runner_split_rows": len(split_rows),
        "unique_race_keys": len({
            row["race_key"]
            for row in race_rows
        }),
        "unique_runner_keys": len({
            (row["race_key"], row["runner_id"])
            for row in runner_rows
        }),
        "missing_payloads": missing_payloads,
        "unreadable_payloads": unreadable_payloads,
        "invalid_payloads": invalid_payloads,
        "duplicate_race_keys": duplicate_race_keys,
        "duplicate_runner_keys": duplicate_runner_keys,
        "sectionals_without_runner_identity": sectionals_without_runner,
        "splits_without_runner_identity": splits_without_runner,
        "outputs": {
            "runner_fact": RUNNER_OUT.relative_to(ROOT).as_posix(),
            "runner_sectionals": SECTIONAL_OUT.relative_to(ROOT).as_posix(),
            "runner_splits": SPLIT_OUT.relative_to(ROOT).as_posix(),
            "race_summary": RACE_OUT.relative_to(ROOT).as_posix(),
        },
        "semantic_controls": {
            "source_values_preserved": True,
            "undocumented_speed_units_asserted": False,
            "time_strings_normalised_to_seconds": True,
            "ratings_calculated": False,
            "benchmarks_calculated": False,
            "estimated_values_created": False,
        },
    }

    AUDIT_OUT.write_text(
        json.dumps(
            audit,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    log(f"races: {len(race_rows)}")
    log(f"runners: {len(runner_rows)}")
    log(f"runner sectionals: {len(sectional_rows)}")
    log(f"runner splits: {len(split_rows)}")
    log(f"audit status: {audit_status}")
    log(f"wrote {RUNNER_OUT.relative_to(ROOT)}")
    log(f"wrote {SECTIONAL_OUT.relative_to(ROOT)}")
    log(f"wrote {SPLIT_OUT.relative_to(ROOT)}")
    log(f"wrote {RACE_OUT.relative_to(ROOT)}")
    log(f"wrote {AUDIT_OUT.relative_to(ROOT)}")

    if audit_status != "PASS":
        log(f"failures: {', '.join(failures)}")
        return 1

    print("EDGEIQ_RACINGCOM_RUNNER_SPEED_WAREHOUSE_V1_AUDIT_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
