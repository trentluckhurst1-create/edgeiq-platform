from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from edgeiq_memory_safe_io import write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_ONTOLOGY = DATA / "edgeiq_telemetry_ontology_v1.csv"

OUT_COMPACT = DATA / "edgeiq_telemetry_ontology_compact_v1.csv"
OUT_ENVIRONMENT = DATA / "edgeiq_telemetry_ontology_environment_summary_v1.csv"
OUT_SIGNAL = DATA / "edgeiq_telemetry_ontology_signal_summary_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_telemetry_ontology_compression_summary_v1.csv"

COMPACT_FIELDS = [
    "jurisdiction",
    "track",
    "universal_signal_family",
    "universal_state",
    "universal_phase",
    "universal_movement",
    "universal_pressure",
    "rows",
    "unique_races",
    "unique_horses",
    "source_layers",
    "source_files",
    "safe_cross_research_yes",
    "safe_shadow_research_yes",
    "avg_telemetry_confidence",
    "avg_lineage_confidence",
    "avg_ontology_confidence",
    "dominant_raw_signal",
    "compact_research_status",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

ENVIRONMENT_FIELDS = [
    "jurisdiction",
    "track",
    "rows",
    "unique_races",
    "unique_horses",
    "signal_families",
    "universal_states",
    "safe_cross_research_yes",
    "safe_shadow_research_yes",
    "avg_ontology_confidence",
    "dominant_signal_family",
    "dominant_state",
    "environment_grade",
    "research_utility",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SIGNAL_FIELDS = [
    "jurisdiction",
    "universal_signal_family",
    "universal_state",
    "universal_phase",
    "universal_movement",
    "universal_pressure",
    "rows",
    "tracks",
    "unique_races",
    "unique_horses",
    "safe_cross_research_yes",
    "safe_shadow_research_yes",
    "avg_telemetry_confidence",
    "avg_lineage_confidence",
    "avg_ontology_confidence",
    "dominant_raw_signal",
    "signal_research_status",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

OFFLINE_NOTES = "Telemetry ontology compression only. Raw ontology preserved. No predictions, overlays, ratings, live modelling, or execution."


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> float:
    text = clean(value).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def yes(value: object) -> bool:
    return upper(value) in {"YES", "Y", "TRUE", "1"}


def race_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            clean(row.get("jurisdiction")),
            clean(row.get("race_date")),
            clean(row.get("track")).upper(),
            clean(row.get("race_no")),
        ]
    )


def horse_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            race_key(row),
            clean(row.get("horse")).upper(),
        ]
    )


def grade_from_counts(rows: int, safe_shadow: int, avg_confidence: float) -> str:
    shadow_rate = safe_shadow / rows if rows else 0.0
    if rows >= 500 and shadow_rate >= 0.25 and avg_confidence >= 85:
        return "A"
    if rows >= 100 and shadow_rate >= 0.10 and avg_confidence >= 75:
        return "B"
    if rows >= 25 and avg_confidence >= 60:
        return "C"
    if rows > 0:
        return "D"
    return "F"


def status_from_grade(grade: str) -> str:
    return {
        "A": "HIGH_VALUE_COMPACT_RESEARCH_LAYER",
        "B": "USABLE_COMPACT_RESEARCH_LAYER",
        "C": "DESCRIPTIVE_COMPACT_RESEARCH_LAYER",
        "D": "LOW_DENSITY_COMPACT_LAYER",
        "F": "EMPTY_COMPACT_LAYER",
    }.get(grade, "LOW_DENSITY_COMPACT_LAYER")


def new_bucket() -> dict[str, object]:
    return {
        "rows": 0,
        "safe_cross": 0,
        "safe_shadow": 0,
        "telemetry_sum": 0.0,
        "lineage_sum": 0.0,
        "ontology_sum": 0.0,
        "races": set(),
        "horses": set(),
        "tracks": set(),
        "source_layers": set(),
        "source_files": set(),
        "signal_families": set(),
        "states": set(),
        "raw_signals": Counter(),
    }


def add_row(bucket: dict[str, object], row: dict[str, str]) -> None:
    bucket["rows"] = int(bucket["rows"]) + 1
    if yes(row.get("safe_for_cross_jurisdiction_research")):
        bucket["safe_cross"] = int(bucket["safe_cross"]) + 1
    if yes(row.get("safe_for_shadow_research")):
        bucket["safe_shadow"] = int(bucket["safe_shadow"]) + 1
    bucket["telemetry_sum"] = float(bucket["telemetry_sum"]) + parse_float(row.get("telemetry_confidence"))
    bucket["lineage_sum"] = float(bucket["lineage_sum"]) + parse_float(row.get("lineage_confidence"))
    bucket["ontology_sum"] = float(bucket["ontology_sum"]) + parse_float(row.get("ontology_confidence"))

    bucket["races"].add(race_key(row))  # type: ignore[union-attr]
    bucket["horses"].add(horse_key(row))  # type: ignore[union-attr]
    bucket["tracks"].add(clean(row.get("track")).upper())  # type: ignore[union-attr]
    bucket["source_layers"].add(clean(row.get("source_layer")))  # type: ignore[union-attr]
    bucket["source_files"].add(clean(row.get("source_file")))  # type: ignore[union-attr]
    bucket["signal_families"].add(clean(row.get("universal_signal_family")))  # type: ignore[union-attr]
    bucket["states"].add(clean(row.get("universal_state")))  # type: ignore[union-attr]
    raw_signal = clean(row.get("raw_signal_name")) or "UNKNOWN_SIGNAL"
    bucket["raw_signals"][raw_signal] += 1  # type: ignore[index]


def avg(bucket: dict[str, object], field: str) -> float:
    rows = int(bucket["rows"])
    return round(float(bucket[field]) / rows, 2) if rows else 0.0


def dominant(counter: Counter[str]) -> str:
    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def compact_row_from_key(key: tuple[str, ...], bucket: dict[str, object]) -> dict[str, object]:
    rows = int(bucket["rows"])
    avg_ontology = avg(bucket, "ontology_sum")
    grade = grade_from_counts(rows, int(bucket["safe_shadow"]), avg_ontology)
    return {
        "jurisdiction": key[0],
        "track": key[1],
        "universal_signal_family": key[2],
        "universal_state": key[3],
        "universal_phase": key[4],
        "universal_movement": key[5],
        "universal_pressure": key[6],
        "rows": str(rows),
        "unique_races": str(len(bucket["races"])),
        "unique_horses": str(len(bucket["horses"])),
        "source_layers": str(len({item for item in bucket["source_layers"] if item})),
        "source_files": str(len({item for item in bucket["source_files"] if item})),
        "safe_cross_research_yes": str(bucket["safe_cross"]),
        "safe_shadow_research_yes": str(bucket["safe_shadow"]),
        "avg_telemetry_confidence": f"{avg(bucket, 'telemetry_sum'):.2f}",
        "avg_lineage_confidence": f"{avg(bucket, 'lineage_sum'):.2f}",
        "avg_ontology_confidence": f"{avg_ontology:.2f}",
        "dominant_raw_signal": dominant(bucket["raw_signals"]),
        "compact_research_status": status_from_grade(grade),
        "live_modelling_allowed": "NO",
        "live_execution_allowed": "NO",
        "notes": OFFLINE_NOTES,
    }


def environment_row_from_key(key: tuple[str, ...], bucket: dict[str, object]) -> dict[str, object]:
    rows = int(bucket["rows"])
    avg_ontology = avg(bucket, "ontology_sum")
    grade = grade_from_counts(rows, int(bucket["safe_shadow"]), avg_ontology)
    family_counter = Counter()
    state_counter = Counter()
    for signal in bucket["signal_families"]:
        if signal:
            family_counter[str(signal)] += 1
    for state in bucket["states"]:
        if state:
            state_counter[str(state)] += 1
    return {
        "jurisdiction": key[0],
        "track": key[1],
        "rows": str(rows),
        "unique_races": str(len(bucket["races"])),
        "unique_horses": str(len(bucket["horses"])),
        "signal_families": str(len({item for item in bucket["signal_families"] if item})),
        "universal_states": str(len({item for item in bucket["states"] if item})),
        "safe_cross_research_yes": str(bucket["safe_cross"]),
        "safe_shadow_research_yes": str(bucket["safe_shadow"]),
        "avg_ontology_confidence": f"{avg_ontology:.2f}",
        "dominant_signal_family": dominant(family_counter),
        "dominant_state": dominant(state_counter),
        "environment_grade": grade,
        "research_utility": status_from_grade(grade),
        "live_modelling_allowed": "NO",
        "live_execution_allowed": "NO",
        "notes": OFFLINE_NOTES,
    }


def signal_row_from_key(key: tuple[str, ...], bucket: dict[str, object]) -> dict[str, object]:
    rows = int(bucket["rows"])
    avg_ontology = avg(bucket, "ontology_sum")
    grade = grade_from_counts(rows, int(bucket["safe_shadow"]), avg_ontology)
    return {
        "jurisdiction": key[0],
        "universal_signal_family": key[1],
        "universal_state": key[2],
        "universal_phase": key[3],
        "universal_movement": key[4],
        "universal_pressure": key[5],
        "rows": str(rows),
        "tracks": str(len({item for item in bucket["tracks"] if item})),
        "unique_races": str(len(bucket["races"])),
        "unique_horses": str(len(bucket["horses"])),
        "safe_cross_research_yes": str(bucket["safe_cross"]),
        "safe_shadow_research_yes": str(bucket["safe_shadow"]),
        "avg_telemetry_confidence": f"{avg(bucket, 'telemetry_sum'):.2f}",
        "avg_lineage_confidence": f"{avg(bucket, 'lineage_sum'):.2f}",
        "avg_ontology_confidence": f"{avg_ontology:.2f}",
        "dominant_raw_signal": dominant(bucket["raw_signals"]),
        "signal_research_status": status_from_grade(grade),
        "live_modelling_allowed": "NO",
        "live_execution_allowed": "NO",
        "notes": OFFLINE_NOTES,
    }


def stream_ontology(path: Path) -> Iterable[dict[str, str]]:
    if not path.exists():
        return
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def file_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    return round(path.stat().st_size / (1024 * 1024), 2)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    compact: dict[tuple[str, ...], dict[str, object]] = defaultdict(new_bucket)
    environment: dict[tuple[str, ...], dict[str, object]] = defaultdict(new_bucket)
    signal: dict[tuple[str, ...], dict[str, object]] = defaultdict(new_bucket)

    rows = 0
    safe_cross = 0
    safe_shadow = 0
    jurisdictions: set[str] = set()
    missing_input = "NO"

    if not IN_ONTOLOGY.exists():
        missing_input = "YES"
    else:
        for row in stream_ontology(IN_ONTOLOGY):
            rows += 1
            jurisdiction = clean(row.get("jurisdiction")) or "UNKNOWN"
            track = clean(row.get("track")).upper() or "UNKNOWN"
            family = clean(row.get("universal_signal_family")) or "UNKNOWN_SIGNAL_FAMILY"
            state = clean(row.get("universal_state")) or "UNKNOWN_STATE"
            phase = clean(row.get("universal_phase")) or "UNKNOWN_PHASE"
            movement = clean(row.get("universal_movement")) or "UNKNOWN_MOVEMENT"
            pressure = clean(row.get("universal_pressure")) or "UNKNOWN_PRESSURE"

            jurisdictions.add(jurisdiction)
            if yes(row.get("safe_for_cross_jurisdiction_research")):
                safe_cross += 1
            if yes(row.get("safe_for_shadow_research")):
                safe_shadow += 1

            add_row(compact[(jurisdiction, track, family, state, phase, movement, pressure)], row)
            add_row(environment[(jurisdiction, track)], row)
            add_row(signal[(jurisdiction, family, state, phase, movement, pressure)], row)

    compact_rows = [compact_row_from_key(key, bucket) for key, bucket in compact.items()]
    environment_rows = [environment_row_from_key(key, bucket) for key, bucket in environment.items()]
    signal_rows = [signal_row_from_key(key, bucket) for key, bucket in signal.items()]

    compact_rows.sort(key=lambda row: (-int(row["rows"]), row["jurisdiction"], row["track"], row["universal_signal_family"]))
    environment_rows.sort(key=lambda row: (-int(row["rows"]), row["jurisdiction"], row["track"]))
    signal_rows.sort(key=lambda row: (-int(row["rows"]), row["jurisdiction"], row["universal_signal_family"]))

    write_csv_atomic(OUT_COMPACT, compact_rows, COMPACT_FIELDS)
    write_csv_atomic(OUT_ENVIRONMENT, environment_rows, ENVIRONMENT_FIELDS)
    write_csv_atomic(OUT_SIGNAL, signal_rows, SIGNAL_FIELDS)

    raw_mb = file_mb(IN_ONTOLOGY)
    compact_total_mb = file_mb(OUT_COMPACT) + file_mb(OUT_ENVIRONMENT) + file_mb(OUT_SIGNAL)
    reduction_pct = round((1 - (compact_total_mb / raw_mb)) * 100, 2) if raw_mb else 0.0
    recommendation = (
        "YES - raw ontology exceeds GitHub recommended 50 MB file size; keep generated locally or under release/artifact storage after reproducible rebuild is proven."
        if raw_mb > 50
        else "NO - raw ontology is below the current GitHub warning threshold."
    )

    summary = [
        {"metric": "compression_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        {"metric": "missing_input::edgeiq_telemetry_ontology_v1.csv", "value": missing_input},
        {"metric": "raw_ontology_rows", "value": str(rows)},
        {"metric": "raw_ontology_size_mb", "value": f"{raw_mb:.2f}"},
        {"metric": "compact_rows", "value": str(len(compact_rows))},
        {"metric": "environment_summary_rows", "value": str(len(environment_rows))},
        {"metric": "signal_summary_rows", "value": str(len(signal_rows))},
        {"metric": "compact_outputs_total_mb", "value": f"{compact_total_mb:.2f}"},
        {"metric": "compression_reduction_pct", "value": f"{reduction_pct:.2f}"},
        {"metric": "jurisdictions", "value": str(len(jurisdictions))},
        {"metric": "safe_for_cross_jurisdiction_research_yes", "value": str(safe_cross)},
        {"metric": "safe_for_shadow_research_yes", "value": str(safe_shadow)},
        {"metric": "merged_raw_jurisdictions", "value": "NO"},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "exclude_raw_ontology_from_git_recommendation", "value": recommendation},
        {"metric": "notes", "value": OFFLINE_NOTES},
    ]
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Ontology raw rows: {rows}")
    print(f"Compact rows: {len(compact_rows)}")
    print(f"Environment rows: {len(environment_rows)}")
    print(f"Signal rows: {len(signal_rows)}")
    print(f"Raw MB: {raw_mb:.2f}")
    print(f"Compact MB: {compact_total_mb:.2f}")


if __name__ == "__main__":
    main()
