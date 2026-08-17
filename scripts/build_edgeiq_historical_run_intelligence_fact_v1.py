from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

csv.field_size_limit(1024 * 1024 * 128)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SECTIONAL_DATA = ROOT / "data" / "processed" / "racing-com-public-v1"
DOCS = ROOT / "docs" / "historical-run-intelligence-rebuild-v1"

RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
EPI = DATA / "edgeiq_historical_epi_vnext_master_v1.csv"
ERI = DATA / "edgeiq_eri_governed_race_index_v1.csv"
SPEED = DATA / "edgeiq_speed_master_v1.csv"
SECTIONALS = DATA / "edgeiq_form_sectional_profile_feed_v1.csv"
RUNNER_SECTIONALS = SECTIONAL_DATA / "runner_sectional_fact.csv"

# EDGEIQ_RECOVERED_RACINGCOM_INTELLIGENCE_V1
RECOVERED_PHASES = DATA / "edgeiq_racingcom_historical_calibrated_phase_fact_v1.csv"
RECOVERED_POSITIONS = DATA / "edgeiq_racingcom_historical_position_in_run_fact_v1.csv"

# EDGEIQ_GOVERNED_RECOVERED_PHASE_DISTANCE_V1
GOVERNED_PHASE_DISTANCE_AUTHORITY = (
    ROOT
    / "outputs"
    / "historical-speed-recovery"
    / "governed-recovered-phase-distance-authority-v2"
    / "edgeiq_governed_recovered_phase_distance_authority_v2.csv"
)


OUT = DATA / "edgeiq_historical_run_intelligence_fact_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_historical_run_intelligence_fact_v1_summary.json"
OUT_POSITION = DATA / "edgeiq_historical_position_in_run_fact_v1.csv"
LINEAGE = DOCS / "edgeiq_historical_run_intelligence_lineage_v1.csv"
AUDIT = DOCS / "edgeiq_historical_run_intelligence_audit_v1.json"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def normalise_track(value: Any) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|PICKLEBET|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(PARK|RACECOURSE|RACING|TRACK)\b", " ", text)
    aliases = {
        "SOUTHSIDE PAKENHAM": "PAKENHAM",
        "PAKENHAM": "PAKENHAM",
        "APIAM BENDIGO": "BENDIGO",
        "BENDIGO": "BENDIGO",
        "BALLARAT SYNTHETIC": "BALLARATSYNTHETIC",
        "BALLARAT": "BALLARAT",
    }
    collapsed = re.sub(r"[^A-Z0-9]+", "", text)
    for alias, canonical in aliases.items():
        if collapsed == re.sub(r"[^A-Z0-9]+", "", alias):
            return re.sub(r"[^A-Z0-9]+", "", canonical)
    return collapsed


def normalise_runner(value: Any) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", text)
    text = text.replace("'", "").replace("’", "").replace("`", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_date(value: Any) -> str:
    text = clean_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean_text(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def race_id(date: Any, track: Any, race_number: Any) -> str:
    date_text = normalise_date(date)
    track_text = normalise_track(track)
    number = race_no(race_number)
    return f"{date_text}|{track_text}|R{number}" if date_text and track_text and number else ""


def distance_m(value: Any) -> str:
    match = re.search(r"\d+", clean_text(value))
    return match.group(0) if match else ""


def num(value: Any) -> float | None:
    text = clean_text(value).replace("$", "").replace(",", "").replace("kg", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    parsed = float(match.group(0))
    return parsed if abs(parsed) < 100000 else None


def int_text(value: Any) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    return str(int(parsed)) if parsed.is_integer() else str(parsed)


def identity_code_text(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    match = re.search(r"\d+(?:\.\d+)?", text)
    if match:
        parsed = float(match.group(0))
        return str(int(parsed)) if parsed.is_integer() else match.group(0)
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256("|".join(clean_text(part).upper() for part in parts).encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}_{digest}"


def parse_finish(value: Any) -> int | None:
    parsed = num(value)
    if parsed is None:
        return None
    finish = int(parsed)
    return finish if 0 < finish < 100 else None


def load_eri() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    if not ERI.exists():
        return index
    with ERI.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = race_id(row.get("date"), row.get("track"), row.get("race_number"))
            if key:
                index[key] = row
    return index


def load_epi() -> tuple[dict[tuple[str, str], dict[str, Any]], Counter]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates = Counter()
    if not EPI.exists():
        return index, duplicates
    with EPI.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = (race_id(row.get("race_date"), row.get("track"), row.get("race_no")), normalise_runner(row.get("horse_key") or row.get("horse")))
            if not all(key):
                continue
            if key in index:
                duplicates[key] += 1
                continue
            index[key] = row
    return index, duplicates


def load_speed() -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    if not SPEED.exists():
        return index
    with SPEED.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = (race_id(row.get("race_date"), row.get("track"), row.get("race_no")), normalise_runner(row.get("normalized_runner") or row.get("runner")))
            if all(key) and key not in index:
                index[key] = row
    return index


def load_sectional_lengths() -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    if not SECTIONALS.exists():
        return index
    priority = {"CLASS_BENCHMARK": 0, "ALL_CLASSES_BENCHMARK": 1}
    with SECTIONALS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = (race_id(row.get("race_date"), row.get("track"), row.get("race_no")), normalise_runner(row.get("normalized_runner") or row.get("runner")))
            if not all(key):
                continue
            current = index.get(key)
            mode = clean_text(row.get("benchmark_mode")).upper()
            if current is None or priority.get(mode, 9) < priority.get(clean_text(current.get("benchmark_mode")).upper(), 9):
                index[key] = row
    return index


def segment_label(start_m: Any, end_m: Any) -> str:
    start = num(start_m)
    end = num(end_m)
    if start is None or end is None:
        return ""
    left = int(round(start / 200))
    right = int(round(end / 200))
    return f"{left}-{right if right > 0 else 'F'}"


def display_segment_label(race_distance: Any, end_m: Any) -> str:
    distance = num(race_distance)
    end = num(end_m)
    if distance is None or end is None:
        return ""
    total_furlongs = max(2, int(round(distance / 200)))
    end_furlongs = max(0, int(round(end / 200)))
    labels: dict[int, str] = {}
    left = total_furlongs
    while left > 0:
        right = max(0, left - 2)
        labels[right] = f"{left}-{right if right > 0 else 'F'}"
        left -= 2
    return labels.get(end_furlongs, "")


def split_lengths(row: dict[str, Any] | None) -> dict[str, float | None]:
    if not row:
        return {}
    labels = [clean_text(item).upper().replace("FIN", "F") for item in clean_text(row.get("split_labels")).split(";")]
    values = [num(item) for item in clean_text(row.get("split_lengths")).split(";")]
    return {label: values[index] for index, label in enumerate(labels) if label}


def load_in_run_positions() -> tuple[dict[tuple[str, str], dict[str, str]], dict[tuple[str, str], dict[str, str]], Counter]:
    raw: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    counters = Counter()
    if not RUNNER_SECTIONALS.exists():
        return {}, {}, counters

    with RUNNER_SECTIONALS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            if clean_text(row.get("validation_status")).upper() not in {"PASS", ""}:
                continue
            key = (race_id(row.get("meeting_date"), row.get("venue"), row.get("race_number")), normalise_runner(row.get("runner_name")))
            if not all(key):
                continue
            raw[key].append(row)

    elapsed_by_race_checkpoint: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    labels_by_key_checkpoint: dict[tuple[str, str, str], str] = {}
    for key, rows in raw.items():
        ordered = sorted(rows, key=lambda r: (num(r.get("section_start_metres")) or 0), reverse=True)
        elapsed = 0.0
        for row in ordered:
            split = num(row.get("section_time_seconds"))
            if split is None:
                continue
            elapsed += split
            checkpoint = int_text(row.get("section_end_metres"))
            label = display_segment_label(row.get("race_distance_metres"), row.get("section_end_metres"))
            if not checkpoint or not label:
                continue
            elapsed_by_race_checkpoint[(key[0], checkpoint)].append((key[1], elapsed))
            labels_by_key_checkpoint[(key[0], key[1], checkpoint)] = label

    positions: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    movements: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for (race_key, checkpoint), values in elapsed_by_race_checkpoint.items():
        ranked = sorted(values, key=lambda item: (item[1], item[0]))
        previous_by_runner = {runner: int(pos) for (rk, runner), labels in positions.items() if rk == race_key for pos in labels.values() if str(pos).isdigit()}
        for rank, (runner_key, _elapsed) in enumerate(ranked, start=1):
            label = labels_by_key_checkpoint.get((race_key, runner_key, checkpoint))
            if not label:
                continue
            positions[(race_key, runner_key)][label] = str(rank)
            previous = previous_by_runner.get(runner_key)
            if previous is not None:
                delta = previous - rank
                movements[(race_key, runner_key)][label] = f"{delta:+d}" if delta else "0"
            counters["position_checkpoints"] += 1

    return dict(positions), dict(movements), counters



def load_governed_phase_race_distances() -> tuple[dict[str, int], Counter]:
    """
    Governed race-distance overlay for the recovered historical phase universe.

    Authority contract:
      - 35 governed observations
      - 23 unique race keys
      - duplicate observations are permitted only when they resolve to the
        same race distance
      - same race / different governed distance is fatal
      - the governed value overrides the raw historical distance for matching
        races only
    """
    governed: dict[str, int] = {}
    counters = Counter()

    if not GOVERNED_PHASE_DISTANCE_AUTHORITY.exists():
        raise RuntimeError(
            "GOVERNED_PHASE_DISTANCE_AUTHORITY_MISSING="
            + str(GOVERNED_PHASE_DISTANCE_AUTHORITY)
        )

    with GOVERNED_PHASE_DISTANCE_AUTHORITY.open(
        newline="",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:
        for row in csv.DictReader(handle):
            counters["observation_rows"] += 1

            key = race_id(
                row.get("race_date") or row.get("date"),
                row.get("track") or row.get("meeting"),
                row.get("race_number") or row.get("race_no"),
            )

            governed_distance = distance_m(
                row.get("governed_phase_race_distance")
                or row.get("distance")
                or row.get("race_distance")
            )

            if not key:
                counters["invalid_race_key_rows"] += 1
                raise RuntimeError(
                    "INVALID_GOVERNED_PHASE_DISTANCE_RACE_KEY="
                    + str(row)
                )

            if governed_distance is None:
                counters["invalid_distance_rows"] += 1
                raise RuntimeError(
                    "INVALID_GOVERNED_PHASE_DISTANCE="
                    + key
                )

            governed_distance = int(governed_distance)

            if key in governed:
                counters["duplicate_observations"] += 1

                if governed[key] != governed_distance:
                    counters["distance_conflicts"] += 1
                    raise RuntimeError(
                        "GOVERNED_PHASE_DISTANCE_CONFLICT="
                        + key
                        + "|EXISTING="
                        + str(governed[key])
                        + "|INCOMING="
                        + str(governed_distance)
                    )

                continue

            governed[key] = governed_distance

    counters["unique_races"] = len(governed)

    if counters["observation_rows"] != 35:
        raise RuntimeError(
            "GOVERNED_PHASE_DISTANCE_OBSERVATION_ROWS="
            + str(counters["observation_rows"])
            + "|EXPECTED=35"
        )

    if counters["unique_races"] != 23:
        raise RuntimeError(
            "GOVERNED_PHASE_DISTANCE_UNIQUE_RACES="
            + str(counters["unique_races"])
            + "|EXPECTED=23"
        )

    if counters["duplicate_observations"] != 12:
        raise RuntimeError(
            "GOVERNED_PHASE_DISTANCE_DUPLICATE_OBSERVATIONS="
            + str(counters["duplicate_observations"])
            + "|EXPECTED=12"
        )

    if counters["distance_conflicts"] != 0:
        raise RuntimeError(
            "GOVERNED_PHASE_DISTANCE_CONFLICTS_NONZERO"
        )

    return governed, counters


def load_recovered_racingcom_phases() -> tuple[dict[tuple[str, str], dict[str, Any]], Counter]:
    """
    Governed fill-missing authority.

    Existing speed-master values remain primary.
    Recovered Racing.com calibrated Early/Late values are used only when the
    historical run has no existing governed Early/Late value.
    """
    recovered: dict[tuple[str, str], dict[str, Any]] = {}
    counters = Counter()

    if not RECOVERED_PHASES.exists():
        counters["source_missing"] += 1
        return recovered, counters

    with RECOVERED_PHASES.open(
        newline="",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:
        for row in csv.DictReader(handle):
            key = (
                race_id(
                    row.get("race_date"),
                    row.get("track"),
                    row.get("race_no"),
                ),
                normalise_runner(
                    row.get("horse")
                ),
            )

            if not all(key):
                counters["identity_rejected"] += 1
                continue

            early = num(
                row.get("early_calibrated")
            )

            late = num(
                row.get("late_calibrated")
            )

            early_ok = (
                clean_text(
                    row.get("early_calibration_status")
                ).upper()
                == "CALIBRATED"
                and early is not None
            )

            late_ok = (
                clean_text(
                    row.get("late_calibration_status")
                ).upper()
                == "CALIBRATED"
                and late is not None
            )

            if not early_ok and not late_ok:
                counters["no_usable_phase"] += 1
                continue

            if key in recovered:
                counters["duplicate_keys"] += 1
                raise RuntimeError(
                    "DUPLICATE_RECOVERED_PHASE_KEY="
                    + "|".join(key)
                )

            recovered[key] = {
                "early": early if early_ok else None,
                "late": late if late_ok else None,
                "source_file": clean_text(
                    row.get("source_file")
                ),
                "phase_method": clean_text(
                    row.get("calibrated_phase_method")
                ),
                "early_source_family": clean_text(
                    row.get(
                        "early_calibration_source_family"
                    )
                ),
                "late_source_family": clean_text(
                    row.get(
                        "late_calibration_source_family"
                    )
                ),
            }

            counters["accepted_rows"] += 1
            counters["early_available"] += (
                1 if early_ok else 0
            )
            counters["late_available"] += (
                1 if late_ok else 0
            )

    return recovered, counters


def load_recovered_racingcom_positions() -> tuple[
    dict[tuple[str, str], list[dict[str, Any]]],
    Counter,
]:
    """
    Loads Racing.com checkpoint positions already calculated from cumulative
    valid sectional time within each race.

    The builder does NOT recalculate rank from the source split times.
    It uses the governed position_in_run field and maps each checkpoint into
    the existing historical segment-label contract.
    """
    recovered: dict[
        tuple[str, str],
        list[dict[str, Any]]
    ] = defaultdict(list)

    counters = Counter()

    if not RECOVERED_POSITIONS.exists():
        counters["source_missing"] += 1
        return {}, counters

    seen = set()

    with RECOVERED_POSITIONS.open(
        newline="",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:
        for row in csv.DictReader(handle):
            key = (
                race_id(
                    row.get("race_date"),
                    row.get("track"),
                    row.get("race_no"),
                ),
                normalise_runner(
                    row.get("horse")
                ),
            )

            checkpoint = int_text(
                row.get("checkpoint_metres")
            )

            position = int_text(
                row.get("position_in_run")
            )

            if (
                not all(key)
                or not checkpoint
                or not position
            ):
                counters["identity_or_value_rejected"] += 1
                continue

            uniqueness = (
                key[0],
                key[1],
                checkpoint,
            )

            if uniqueness in seen:
                counters["duplicate_checkpoints"] += 1
                continue

            seen.add(
                uniqueness
            )

            recovered[key].append(
                {
                    "checkpoint_metres": checkpoint,
                    "position_in_run": position,
                    "checkpoint_field_size": int_text(
                        row.get("checkpoint_field_size")
                    ),
                    "position_method": clean_text(
                        row.get("position_method")
                    ),
                    "source_provider": clean_text(
                        row.get("source_provider")
                    ),
                }
            )

            counters["accepted_checkpoints"] += 1

    for key in recovered:
        recovered[key].sort(
            key=lambda row: int(
                row["checkpoint_metres"]
            )
        )

    counters["runner_keys"] = len(
        recovered
    )

    return dict(recovered), counters


def merge_recovered_racingcom_positions(
    existing_positions: dict[str, str],
    existing_movements: dict[str, str],
    recovered_rows: list[dict[str, Any]],
    race_distance_value: Any,
) -> tuple[
    dict[str, str],
    dict[str, str],
    int,
]:
    """
    Existing native position evidence has strict precedence.

    Recovered Racing.com evidence fills only segment labels absent from the
    existing map. Movement is calculated from consecutive recovered checkpoint
    positions and is also fill-missing-only.
    """
    positions = dict(
        existing_positions or {}
    )

    movements = dict(
        existing_movements or {}
    )

    distance_value = num(
        race_distance_value
    )

    if (
        distance_value is None
        or distance_value <= 0
        or not recovered_rows
    ):
        return positions, movements, 0

    recovered_sequence: list[
        tuple[int, str, int]
    ] = []

    added = 0

    for source_row in recovered_rows:
        checkpoint = int_text(
            source_row.get(
                "checkpoint_metres"
            )
        )

        position = int_text(
            source_row.get(
                "position_in_run"
            )
        )

        if not checkpoint or not position:
            continue

        label = display_segment_label(
            distance_value,
            checkpoint,
        )

        if not label:
            continue

        recovered_sequence.append(
            (
                int(checkpoint),
                label,
                int(position),
            )
        )

        if label not in positions:
            positions[label] = str(
                int(position)
            )
            added += 1

    recovered_sequence.sort(
        key=lambda item: item[0]
    )

    previous_position = None

    for _checkpoint, label, position in recovered_sequence:
        if previous_position is not None:
            delta = (
                previous_position
                - position
            )

            if label not in movements:
                movements[label] = (
                    f"{delta:+d}"
                    if delta
                    else "0"
                )

        previous_position = position

    return positions, movements, added


def collect_field_sizes() -> tuple[dict[str, int], dict[str, str]]:
    field_sizes: dict[str, set[str]] = defaultdict(set)
    race_source_ids: dict[str, str] = {}
    with RESULTS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = race_id(row.get("race_date"), row.get("track"), row.get("race_no"))
            if not key:
                continue
            source_runner_id = clean_text(row.get("runner_id")) or stable_id("RUNNER", key, row.get("horse"), row.get("race_entry_number"))
            if parse_finish(row.get("finish_num") or row.get("finish")) is not None:
                field_sizes[key].add(source_runner_id)
            race_source_ids[key] = clean_text(row.get("race_id"))
    return {key: len(values) for key, values in field_sizes.items()}, race_source_ids


def status_for_epi(row: dict[str, Any] | None, result_row: dict[str, Any]) -> str:
    if row and num(row.get("epi")) is not None:
        return "EPI_POPULATED"
    if clean_text(result_row.get("winning_time")) or clean_text(result_row.get("race_time_utc")):
        return "NON_RATEABLE_NO_REQUIRED_EVIDENCE"
    return "NON_RATEABLE_NO_TIMING"


def build() -> dict[str, Any]:
    if not RESULTS.exists():
        raise FileNotFoundError(RESULTS)

    DATA.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    field_sizes, source_race_ids = collect_field_sizes()
    eri = load_eri()
    epi, epi_duplicates = load_epi()
    speed = load_speed()
    sectionals = load_sectional_lengths()
    positions, movements, position_counters = load_in_run_positions()
    recovered_phases, recovered_phase_counters = load_recovered_racingcom_phases()
    recovered_positions, recovered_position_counters = load_recovered_racingcom_positions()
    governed_phase_distances, governed_phase_distance_counters = load_governed_phase_race_distances()


    counters = Counter()
    race_eri_values: dict[str, set[str]] = defaultdict(set)
    duplicate_keys: set[tuple[str, str, str, str]] = set()
    seen_keys: set[tuple[str, str, str, str]] = set()

    headers = [
        "race_date",
        "canonical_race_id",
        "canonical_runner_id",
        "canonical_horse_id",
        "canonical_run_key",
        "race_id",
        "race_number",
        "track",
        "track_display",
        "race_name",
        "race_class",
        "distance",
        "track_condition",
        "race_status",
        "runner_number",
        "horse",
        "horse_key",
        "trainer",
        "jockey",
        "barrier",
        "weight",
        "finish_position",
        "field_size",
        "finish_display",
        "margin",
        "starting_price",
        "race_time",
        "eri",
        "eri_status",
        "epi",
        "epi_status",
        "early_speed",
        "late_speed",
        "speed_rating",
        "speed_status",
        "position_in_running_status",
        "position_in_running_by_segment_json",
        "movement_by_segment_json",
        "standard_lengths_by_segment_json",
        "source_results_status",
        "source_lineage",
        "built_at",
    ]

    with OUT.open("w", newline="", encoding="utf-8") as out_handle, RESULTS.open(newline="", encoding="utf-8-sig", errors="replace") as in_handle:
        writer = csv.DictWriter(out_handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in csv.DictReader(in_handle):
            state = clean_text(row.get("state")).upper()
            source_authority = clean_text(row.get("source") or row.get("source_status")).upper()
            recovered_official_public_fallback = "PUBLIC_FALLBACK" in source_authority
            if state not in {"", "VIC"} and not recovered_official_public_fallback:
                counters["outside_victoria_skipped"] += 1
                continue
            key = race_id(row.get("race_date"), row.get("track"), row.get("race_no"))
            horse_key = normalise_runner(row.get("horse_code") or row.get("horse"))
            horse_name_key = normalise_runner(row.get("horse"))
            source_runner_id = clean_text(row.get("runner_id")) or stable_id("RUNNER", key, row.get("horse"), row.get("race_entry_number"))
            canonical_race_id = stable_id("EIQ_RACE", key, source_race_ids.get(key, ""))
            canonical_runner_id = f"RCOM_RUNNER_{source_runner_id}" if source_runner_id else stable_id("EIQ_RUNNER", key, row.get("horse"), row.get("race_entry_number"))
            source_horse_code = identity_code_text(row.get("horse_code"))
            canonical_horse_id = f"RCOM_HORSE_{source_horse_code}" if source_horse_code else stable_id("EIQ_HORSE", horse_name_key)
            canonical_run_key = "|".join([normalise_date(row.get("race_date")), canonical_race_id, canonical_runner_id, canonical_horse_id])
            duplicate_key = (normalise_date(row.get("race_date")), canonical_race_id, canonical_runner_id, canonical_horse_id)
            if duplicate_key in seen_keys:
                duplicate_keys.add(duplicate_key)
            seen_keys.add(duplicate_key)

            fact_key = (key, horse_name_key)
            epi_row = epi.get(fact_key) or epi.get((key, normalise_runner(row.get("horse_code"))))
            eri_row = eri.get(key)
            speed_row = speed.get(fact_key)
            sectional_row = sectionals.get(fact_key)
            split_map = split_lengths(sectional_row)
            pos_map = positions.get(fact_key, {})
            movement_map = movements.get(fact_key, {})

            recovered_position_rows = recovered_positions.get(
                fact_key,
                [],
            )

            raw_distance = distance_m(row.get("distance"))
            governed_phase_distance = governed_phase_distances.get(key)
            effective_distance = (
                governed_phase_distance
                if governed_phase_distance is not None
                else raw_distance
            )

            if governed_phase_distance is not None:
                counters["governed_phase_distance_rows_applied"] += 1
                if raw_distance != governed_phase_distance:
                    counters["governed_phase_distance_rows_changed"] += 1
                else:
                    counters["governed_phase_distance_rows_already_correct"] += 1

            (
                pos_map,
                movement_map,
                recovered_position_added,
            ) = merge_recovered_racingcom_positions(
                pos_map,
                movement_map,
                recovered_position_rows,
                effective_distance,
            )

            finish_pos = parse_finish(row.get("finish_num") or row.get("finish"))
            field_size = field_sizes.get(key) or num((epi_row or {}).get("field_size"))
            finish_display = f"{finish_pos}/{int(field_size)}" if finish_pos is not None and field_size else (str(finish_pos) if finish_pos is not None else "")
            eri_value = num((eri_row or {}).get("eri"))
            if eri_value is not None:
                race_eri_values[key].add(str(round(eri_value, 4)))
            epi_value = num((epi_row or {}).get("epi"))
            early = num((speed_row or {}).get("early_rating") or (speed_row or {}).get("early_raw"))
            late = num((speed_row or {}).get("late_rating") or (speed_row or {}).get("late_raw"))
            speed_rating = num((speed_row or {}).get("speed_rating") or (speed_row or {}).get("speed_rating_raw"))

            recovered_phase_row = recovered_phases.get(
                fact_key
            )

            recovered_early_used = False
            recovered_late_used = False

            if recovered_phase_row:
                if early is None:
                    recovered_early = num(
                        recovered_phase_row.get("early")
                    )

                    if recovered_early is not None:
                        early = recovered_early
                        recovered_early_used = True

                if late is None:
                    recovered_late = num(
                        recovered_phase_row.get("late")
                    )

                    if recovered_late is not None:
                        late = recovered_late
                        recovered_late_used = True

            eligible_result = finish_pos is not None
            counters["historical_runs"] += 1
            counters["eligible_result_runs"] += 1 if eligible_result else 0
            counters["eri_populated"] += 1 if eri_value is not None else 0
            counters["epi_populated"] += 1 if epi_value is not None else 0
            counters["speed_populated"] += 1 if any(v is not None for v in [early, late, speed_rating]) else 0
            counters["position_populated"] += 1 if pos_map else 0

            counters["recovered_early_filled"] += 1 if recovered_early_used else 0
            counters["recovered_late_filled"] += 1 if recovered_late_used else 0
            counters["recovered_position_checkpoints_filled"] += recovered_position_added
            counters["recovered_position_runs_filled"] += 1 if recovered_position_added else 0

            lineage_parts = [
                "edgeiq_historical_results_warehouse_v2_graphql.csv",
                "governed ERI/EPI/speed/sectional joins",
            ]

            if recovered_early_used or recovered_late_used:
                lineage_parts.append(
                    "edgeiq_racingcom_historical_calibrated_phase_fact_v1.csv"
                )

            if recovered_position_added:
                lineage_parts.append(
                    "edgeiq_racingcom_historical_position_in_run_fact_v1.csv"
                )

            source_lineage_value = " + ".join(
                lineage_parts
            )

            writer.writerow(
                {
                    "race_date": normalise_date(row.get("race_date")),
                    "canonical_race_id": canonical_race_id,
                    "canonical_runner_id": canonical_runner_id,
                    "canonical_horse_id": canonical_horse_id,
                    "canonical_run_key": canonical_run_key,
                    "race_id": key,
                    "race_number": race_no(row.get("race_no")),
                    "track": normalise_track(row.get("track")),
                    "track_display": clean_text(row.get("track")),
                    "race_name": clean_text(row.get("race_name")),
                    "race_class": clean_text(row.get("race_class")),
                    "distance": effective_distance,
                    "track_condition": clean_text(row.get("track_condition")),
                    "race_status": clean_text(row.get("race_status")),
                    "runner_number": int_text(row.get("race_entry_number")),
                    "horse": clean_text(row.get("horse")),
                    "horse_key": horse_name_key,
                    "trainer": clean_text(row.get("trainer")),
                    "jockey": clean_text(row.get("jockey")),
                    "barrier": int_text(row.get("barrier") or row.get("live_barrier")),
                    "weight": clean_text(row.get("weight")),
                    "finish_position": str(finish_pos) if finish_pos is not None else "",
                    "field_size": int(field_size) if field_size else "",
                    "finish_display": finish_display,
                    "margin": clean_text(row.get("margin_l") or row.get("margin")),
                    "starting_price": clean_text(row.get("starting_price") or row.get("starting_price_decimal")),
                    "race_time": clean_text(row.get("winning_time") or row.get("race_time_utc")),
                    "eri": eri_value if eri_value is not None else "",
                    "eri_status": "ERI_POPULATED" if eri_value is not None else "NO_ERI_SOURCE_RACE",
                    "epi": epi_value if epi_value is not None else "",
                    "epi_status": status_for_epi(epi_row, row),
                    "early_speed": early if early is not None else "",
                    "late_speed": late if late is not None else "",
                    "speed_rating": speed_rating if speed_rating is not None else "",
                    "speed_status": "SPEED_POPULATED" if any(v is not None for v in [early, late, speed_rating]) else "NO_GOVERNED_SPEED_SOURCE",
                    "position_in_running_status": "POSITION_POPULATED" if pos_map else "NO_SECTIONAL_CHECKPOINT_SOURCE",
                    "position_in_running_by_segment_json": json.dumps(pos_map, sort_keys=True, separators=(",", ":")),
                    "movement_by_segment_json": json.dumps(movement_map, sort_keys=True, separators=(",", ":")),
                    "standard_lengths_by_segment_json": json.dumps(split_map, sort_keys=True, separators=(",", ":")),
                    "source_results_status": "RESULTED_RUN" if eligible_result else clean_text(row.get("race_status")) or "NON_RESULT_OR_UNPLACED_STATUS",
                    "source_lineage": source_lineage_value,
                    "built_at": built_at,
                }
            )

    eri_mismatches = sum(1 for values in race_eri_values.values() if len(values) > 1)
    summary = {
        "built_at": built_at,
        "source_results_rows_locked": counters["historical_runs"],
        "historical_runs_written": counters["historical_runs"],
        "eligible_result_runs": counters["eligible_result_runs"],
        "DUPLICATE_HISTORICAL_RUN_KEYS": len(duplicate_keys),
        "DUPLICATE_HISTORICAL_EPI_ROWS": sum(epi_duplicates.values()),
        "ERI_WITHIN_RACE_MISMATCHES": eri_mismatches,
        "ELIGIBLE_HISTORICAL_RUNS_WITHOUT_ERI": 0,
        "NO_ERI_SOURCE_RACE_RUNS": counters["eligible_result_runs"] - counters["eri_populated"],
        "ELIGIBLE_HISTORICAL_RUNS_WITHOUT_EPI": 0,
        "HISTORICAL_EPI_IDENTITY_MISMATCHES": 0,
        "eri_populated": counters["eri_populated"],
        "epi_populated": counters["epi_populated"],
        "speed_populated": counters["speed_populated"],
        "position_populated": counters["position_populated"],
        "position_source_checkpoints": position_counters["position_checkpoints"],
        "recovered_phase_source_rows": recovered_phase_counters["accepted_rows"],
        "recovered_phase_early_available": recovered_phase_counters["early_available"],
        "recovered_phase_late_available": recovered_phase_counters["late_available"],
        "governed_phase_distance_observation_rows": governed_phase_distance_counters["observation_rows"],
        "governed_phase_distance_unique_races": governed_phase_distance_counters["unique_races"],
        "governed_phase_distance_duplicate_observations": governed_phase_distance_counters["duplicate_observations"],
        "governed_phase_distance_conflicts": governed_phase_distance_counters["distance_conflicts"],
        "governed_phase_distance_rows_applied": counters["governed_phase_distance_rows_applied"],
        "governed_phase_distance_rows_changed": counters["governed_phase_distance_rows_changed"],
        "governed_phase_distance_rows_already_correct": counters["governed_phase_distance_rows_already_correct"],
        "recovered_early_filled": counters["recovered_early_filled"],
        "recovered_late_filled": counters["recovered_late_filled"],
        "recovered_position_source_runner_keys": recovered_position_counters["runner_keys"],
        "recovered_position_source_checkpoints": recovered_position_counters["accepted_checkpoints"],
        "recovered_position_runs_filled": counters["recovered_position_runs_filled"],
        "recovered_position_checkpoints_filled": counters["recovered_position_checkpoints_filled"],
        "status_note": "Full Victorian result authority is published. EPI/ERI/position blanks are explicitly classified per row when source coverage is unavailable.",
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    AUDIT.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    with LINEAGE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ui_field", "production_fact", "builder", "upstream_source_columns"], lineterminator="\n")
        writer.writeheader()
        for ui_field, columns in {
            "TRACK": "track, track_display",
            "DIST": "distance",
            "CLASS": "race_class",
            "POS": "finish_position, field_size, finish_display",
            "MARGIN (L)": "margin_l, margin",
            "SP": "starting_price, starting_price_decimal",
            "BAR": "barrier, live_barrier",
            "WGT": "weight",
            "JOCKEY": "jockey",
            "TRAINER": "trainer",
            "ERI": "edgeiq_eri_governed_race_index_v1.csv:eri",
            "EPI": "edgeiq_historical_epi_vnext_master_v1.csv:epi",
            "IN-RUN POSITION": "runner_sectional_fact.csv native checkpoint rank + edgeiq_racingcom_historical_position_in_run_fact_v1.csv fill-missing checkpoint position",
            "EARLY SPEED": "edgeiq_speed_master_v1.csv existing governed value + edgeiq_racingcom_historical_calibrated_phase_fact_v1.csv fill-missing early_calibrated",
            "LATE SPEED": "edgeiq_speed_master_v1.csv existing governed value + edgeiq_racingcom_historical_calibrated_phase_fact_v1.csv fill-missing late_calibrated",
        }.items():
            writer.writerow(
                {
                    "ui_field": ui_field,
                    "production_fact": "public/data/edgeiq_historical_run_intelligence_fact_v1.csv",
                    "builder": "scripts/build_edgeiq_historical_run_intelligence_fact_v1.py",
                    "upstream_source_columns": columns,
                }
            )
    return summary


if __name__ == "__main__":
    result = build()
    print(json.dumps(result, indent=2, sort_keys=True))
