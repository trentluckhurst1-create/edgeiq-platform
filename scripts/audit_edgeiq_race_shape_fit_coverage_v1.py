from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

FIT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v1.csv"
DNA_PATH = DATA_DIR / "edgeiq_horse_dna_v1.csv"
LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
SPEED_MAP_PATH = DATA_DIR / "edgeiq_real_speed_map_positions.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_race_shape_fit_coverage_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_race_shape_fit_coverage_v1_summary.csv"

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "runners",
    "matched_dna",
    "unmatched_dna",
    "usable_fit",
    "insufficient_fit",
    "coverage_pct",
    "race_tempo",
    "pace_pressure",
    "leader_count",
    "on_pace_count",
    "midfield_count",
    "backmarker_count",
    "off_pace_count",
    "other_position_count",
    "run_style_counts",
    "pace_profile_counts",
    "settling_band_counts",
    "speed_map_bucket_counts",
    "tempo_source_fields",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalise_key(value: str | None) -> str:
    raw = (value or "").upper().strip()
    raw = re.sub(r"\([A-Z]{2,3}\)$", "", raw).strip()
    return re.sub(r"[^A-Z0-9]+", "", raw)


def normalise_track(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").upper().strip())


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        text(row.get("race_date")),
        normalise_track(row.get("track")),
        text(row.get("race_no")),
    )


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (*race_key(row), normalise_key(row.get("horse_key") or row.get("horse")))


def canonical_position(value: str | None) -> str:
    raw = re.sub(r"[_\-]+", " ", text(value).upper())
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return "BLANK"
    if "OFF PACE" in raw or "OFFPACE" in raw:
        return "OFF_PACE"
    if "BACK" in raw or "CLOSER" in raw or "REAR" in raw:
        return "BACKMARKER"
    if "LEADER" in raw or "FRONT" in raw:
        return "LEADER"
    if raw == "PACE" or "ON PACE" in raw or "ONPACE" in raw or "PRESSURE" in raw:
        return "ON_PACE"
    if "MID" in raw:
        return "MIDFIELD"
    return raw.replace(" ", "_")


def is_usable_fit(row: dict[str, str]) -> bool:
    if text(row.get("fit_confidence")).upper() == "INSUFFICIENT":
        return False
    if text(row.get("fit_grade")).upper() == "INSUFFICIENT":
        return False
    return bool(text(row.get("race_shape_fit_score")))


def count_values(rows: list[dict[str, str]], column: str, canonical: bool = False) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = canonical_position(row.get(column)) if canonical else text(row.get(column)).upper()
        counts[value or "BLANK"] += 1
    return counts


def counter_string(counter: Counter[str]) -> str:
    if not counter:
        return ""
    return "; ".join(f"{name}:{count}" for name, count in sorted(counter.items()))


def derive_position(row: dict[str, str], speed_row: dict[str, str] | None) -> str:
    for source_row, column in (
        (row, "run_style"),
        (row, "pace_profile"),
        (row, "settling_band"),
        (row, "speed_map_bucket"),
        (speed_row or {}, "settling_band"),
        (speed_row or {}, "settling_reason"),
    ):
        value = canonical_position(source_row.get(column))
        if value != "BLANK":
            return value
    return "BLANK"


def build_speed_map_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = runner_key(row)
        if key[-1]:
            lookup[key] = row
    return lookup


def build_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fit_rows = read_csv(FIT_PATH)
    dna_rows = read_csv(DNA_PATH)
    live_rows = read_csv(LIVE_FEED_PATH)
    speed_rows = read_csv(SPEED_MAP_PATH)

    dna_keys = {normalise_key(row.get("horse_key") or row.get("horse")) for row in dna_rows}
    dna_keys.discard("")
    speed_lookup = build_speed_map_lookup(speed_rows)
    fit_lookup = {runner_key(row): row for row in fit_rows if runner_key(row)[-1]}

    live_by_race: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in live_rows:
        if text(row.get("race_date")) and text(row.get("track")) and text(row.get("race_no")) and normalise_key(row.get("horse_key") or row.get("horse")):
            live_by_race[race_key(row)].append(row)

    output_rows: list[dict[str, Any]] = []
    total_current_runners = 0
    total_matched_dna = 0
    total_usable_fit = 0
    runners_by_tempo: Counter[str] = Counter()
    races_by_tempo: Counter[str] = Counter()
    source_field_nonblank = Counter()
    source_field_pace_contributors = Counter()

    for key in sorted(live_by_race, key=lambda item: (item[0], item[1], int(item[2]) if item[2].isdigit() else item[2])):
        rows = live_by_race[key]
        total_current_runners += len(rows)

        matched_dna = 0
        usable_fit = 0
        position_counts: Counter[str] = Counter()
        run_style_counts = count_values(rows, "run_style", canonical=True)
        pace_profile_counts = count_values(rows, "pace_profile", canonical=True)
        settling_band_counts = count_values(rows, "settling_band", canonical=True)
        speed_map_bucket_counts = count_values(rows, "speed_map_bucket", canonical=True)
        race_tempo_counter: Counter[str] = Counter()
        pace_pressure_counter: Counter[str] = Counter()

        for row in rows:
            horse_key = normalise_key(row.get("horse_key") or row.get("horse"))
            speed_row = speed_lookup.get(runner_key(row))
            fit_row = fit_lookup.get(runner_key(row), {})

            if horse_key in dna_keys:
                matched_dna += 1
            if fit_row and is_usable_fit(fit_row):
                usable_fit += 1

            race_tempo = text(fit_row.get("race_tempo")).upper() or "UNKNOWN"
            pace_pressure = text(fit_row.get("pace_pressure")).upper() or "UNKNOWN"
            race_tempo_counter[race_tempo] += 1
            pace_pressure_counter[pace_pressure] += 1
            runners_by_tempo[race_tempo] += 1

            position = derive_position(row, speed_row)
            position_counts[position] += 1

            for column in ("run_style", "pace_profile", "settling_band", "speed_map_bucket"):
                value = canonical_position(row.get(column))
                if value != "BLANK":
                    source_field_nonblank[column] += 1
                if value in {"LEADER", "ON_PACE"}:
                    source_field_pace_contributors[column] += 1
            if speed_row:
                speed_value = canonical_position(speed_row.get("settling_band"))
                if speed_value != "BLANK":
                    source_field_nonblank["speed_map_settling_band"] += 1
                if speed_value in {"LEADER", "ON_PACE"}:
                    source_field_pace_contributors["speed_map_settling_band"] += 1

        race_tempo = race_tempo_counter.most_common(1)[0][0] if race_tempo_counter else "UNKNOWN"
        pace_pressure = pace_pressure_counter.most_common(1)[0][0] if pace_pressure_counter else "UNKNOWN"
        races_by_tempo[race_tempo] += 1

        runners = len(rows)
        insufficient_fit = runners - usable_fit
        coverage_pct = (usable_fit / runners * 100.0) if runners else 0.0

        output_rows.append(
            {
                "race_date": key[0],
                "track": key[1],
                "race_no": key[2],
                "runners": runners,
                "matched_dna": matched_dna,
                "unmatched_dna": runners - matched_dna,
                "usable_fit": usable_fit,
                "insufficient_fit": insufficient_fit,
                "coverage_pct": f"{coverage_pct:.2f}",
                "race_tempo": race_tempo,
                "pace_pressure": pace_pressure,
                "leader_count": position_counts.get("LEADER", 0),
                "on_pace_count": position_counts.get("ON_PACE", 0),
                "midfield_count": position_counts.get("MIDFIELD", 0),
                "backmarker_count": position_counts.get("BACKMARKER", 0),
                "off_pace_count": position_counts.get("OFF_PACE", 0),
                "other_position_count": sum(count for name, count in position_counts.items() if name not in {"LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER", "OFF_PACE"}),
                "run_style_counts": counter_string(run_style_counts),
                "pace_profile_counts": counter_string(pace_profile_counts),
                "settling_band_counts": counter_string(settling_band_counts),
                "speed_map_bucket_counts": counter_string(speed_map_bucket_counts),
                "tempo_source_fields": f"nonblank={counter_string(source_field_nonblank)} | pace_contributors={counter_string(source_field_pace_contributors)}",
            }
        )

        total_matched_dna += matched_dna
        total_usable_fit += usable_fit

    total_unmatched_dna = total_current_runners - total_matched_dna
    total_insufficient_fit = total_current_runners - total_usable_fit
    coverage_pct = (total_usable_fit / total_current_runners * 100.0) if total_current_runners else 0.0
    fast_race_pct = (races_by_tempo.get("FAST", 0) / len(live_by_race) * 100.0) if live_by_race else 0.0

    recommendations = []
    if coverage_pct >= 50.0:
        recommendations.append("READY_FOR_UI")
    else:
        recommendations.append("HOLD_UI_LOW_COVERAGE")
    if fast_race_pct > 80.0:
        recommendations.append("REVIEW_TEMPO_DERIVATION")

    summary = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "status": "RACE_SHAPE_FIT_COVERAGE_AUDITED",
        "total_current_runners": total_current_runners,
        "matched_dna_runners": total_matched_dna,
        "unmatched_dna_runners": total_unmatched_dna,
        "usable_race_shape_fit_runners": total_usable_fit,
        "insufficient_race_shape_fit_runners": total_insufficient_fit,
        "coverage_pct": f"{coverage_pct:.2f}",
        "race_contexts": len(live_by_race),
        "races_by_race_tempo": counter_string(races_by_tempo),
        "runners_by_race_tempo": counter_string(runners_by_tempo),
        "fast_race_pct": f"{fast_race_pct:.2f}",
        "run_style_distribution": counter_string(count_values(live_rows, "run_style", canonical=True)),
        "pace_profile_distribution": counter_string(count_values(live_rows, "pace_profile", canonical=True)),
        "settling_band_distribution": counter_string(count_values(live_rows, "settling_band", canonical=True)),
        "speed_map_bucket_distribution": counter_string(count_values(live_rows, "speed_map_bucket", canonical=True)),
        "tempo_source_fields_nonblank": counter_string(source_field_nonblank),
        "tempo_source_fields_pace_contributors": counter_string(source_field_pace_contributors),
        "recommendation": "; ".join(recommendations),
        "diagnostic_note": "Usable fit requires non-insufficient fit confidence, non-insufficient fit grade, and a populated race_shape_fit_score.",
    }

    return output_rows, summary


def main() -> None:
    rows, summary = build_audit()
    write_csv(OUTPUT_PATH, rows, OUTPUT_COLUMNS)
    write_csv(SUMMARY_PATH, [summary], list(summary.keys()))

    print(f"Coverage rows written: {len(rows)}")
    print(f"Summary written: {SUMMARY_PATH}")
    print(f"Status: {summary['status']}")
    print(f"Coverage pct: {summary['coverage_pct']}")
    print(f"Recommendation: {summary['recommendation']}")


if __name__ == "__main__":
    main()
