from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

OUTPUT_PATH = DATA_DIR / "edgeiq_horse_dna_v1.csv"
AUDIT_PATH = DATA_DIR / "edgeiq_horse_dna_v1_audit.csv"

FEATURE_FILE = DATA_DIR / "edgeiq_sectional_feature_engine_v2.csv"
INTELLIGENCE_FILE = DATA_DIR / "edgeiq_sectional_intelligence_v2.csv"
MEMORY_FILE = DATA_DIR / "edgeiq_universal_sectional_memory_v1.csv"
PHYSICS_FILE = DATA_DIR / "edgeiq_real_sectional_physics_features_v1.csv"

DISCOVERY_PATTERNS = (
    "sectional",
    "sections",
    "split",
    "trusted",
    "horse_runs",
    "run_context",
    "form",
    "race_results",
)

FEATURE_REQUIRED_COLUMNS = {
    "horse_key",
    "horse",
    "runs",
    "early_mean",
    "mid_mean",
    "late_mean",
    "avg_speed_mean",
    "late_delta_mean",
    "burst_delta_mean",
    "late_power_index",
    "burst_index",
    "sustain_index",
    "fatigue_risk_index",
    "run_style_cluster",
    "sectional_weapon_score",
}

INTELLIGENCE_REQUIRED_COLUMNS = {
    "horse_key",
    "horse",
    "sectional_runs",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "fast_finisher_rate",
    "sustained_speed_rate",
    "sectional_strength_score",
    "sectional_profile",
    "tempo_suitability",
    "preferred_distance_bucket",
}

MEMORY_REQUIRED_COLUMNS = {
    "horse_key",
    "projected_map_style",
    "run_style_cluster",
    "sectional_profile",
    "best_tempo_setup",
}

OUTPUT_COLUMNS = [
    "horse",
    "horse_key",
    "runs_used",
    "sectional_rows_used",
    "early_speed_score",
    "mid_race_strength_score",
    "late_strength_score",
    "acceleration_score",
    "sustained_speed_score",
    "pressure_tolerance_score",
    "preferred_tempo",
    "preferred_position",
    "sectional_archetype",
    "dna_confidence",
    "evidence_notes",
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


def normalise_key(value: str | None) -> str:
    raw = (value or "").upper().strip()
    raw = re.sub(r"\([A-Z]{2,3}\)$", "", raw).strip()
    return re.sub(r"[^A-Z0-9]+", "", raw)


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def to_float(value: Any) -> float | None:
    raw = text(value)
    if not raw or raw.upper() in {"NA", "N/A", "NULL", "NONE", "-"}:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    numeric = to_float(value)
    if numeric is None:
        return None
    return int(numeric)


def clamp(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(100.0, value))


def round_score(value: float | None) -> str:
    bounded = clamp(value)
    if bounded is None:
        return ""
    return f"{bounded:.2f}"


def average(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return sum(usable) / len(usable)


def percentile_maps(values_by_metric: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    maps: dict[str, dict[str, float]] = {}
    for metric, values_by_key in values_by_metric.items():
        ordered = sorted((value, key) for key, value in values_by_key.items() if value is not None)
        if not ordered:
            maps[metric] = {}
            continue
        if len(ordered) == 1:
            maps[metric] = {ordered[0][1]: 50.0}
            continue

        metric_map: dict[str, float] = {}
        for index, (_, key) in enumerate(ordered):
            metric_map[key] = 100.0 * index / (len(ordered) - 1)
        maps[metric] = metric_map
    return maps


def field(row: dict[str, str] | None, column: str) -> str:
    if not row:
        return ""
    return text(row.get(column, ""))


def number_from(feature: dict[str, str] | None, intelligence: dict[str, str] | None, feature_col: str, intelligence_col: str) -> float | None:
    value = to_float(field(feature, feature_col))
    if value is not None:
        return value
    return to_float(field(intelligence, intelligence_col))


def score_index(value: Any) -> float | None:
    numeric = to_float(value)
    if numeric is None:
        return None
    return clamp(numeric)


def infer_tempo(intelligence: dict[str, str] | None, memory: dict[str, str] | None, archetype: str) -> str:
    combined = " ".join(
        [
            field(intelligence, "tempo_suitability"),
            field(memory, "best_tempo_setup"),
            field(memory, "sectional_profile"),
            archetype,
        ]
    ).upper()
    if any(token in combined for token in ("HIGH_PRESSURE", "HOT", "FAST", "PRESSURE")):
        return "FAST_TEMPO"
    if any(token in combined for token in ("CONTROL", "LOW", "SLOW")):
        return "CONTROLLED_TEMPO"
    if any(token in combined for token in ("HONEST", "MODERATE")):
        return "HONEST_TEMPO"
    if any(token in combined for token in ("CLOSER", "SUSTAINED")):
        return "FAST_TEMPO"
    return "HONEST_TEMPO"


def infer_position(memory: dict[str, str] | None, early_score: float | None, late_score: float | None) -> str:
    raw = field(memory, "projected_map_style").upper()
    if "LEADER" in raw or "FRONT" in raw:
        return "LEADER"
    if "ON_PACE" in raw or "ON PACE" in raw or "PACE" in raw:
        return "ON_PACE"
    if "BACK" in raw or "CLOSER" in raw:
        return "BACKMARKER"
    if "MID" in raw:
        return "MIDFIELD"

    early = early_score or 0.0
    late = late_score or 0.0
    if early >= 70 and late < 70:
        return "LEADER"
    if early >= 60:
        return "ON_PACE"
    if late >= 70:
        return "BACKMARKER"
    return "MIDFIELD"


def infer_archetype(
    runs_used: int,
    early_score: float | None,
    late_score: float | None,
    acceleration_score: float | None,
    sustained_score: float | None,
    pressure_score: float | None,
    preferred_position: str,
    feature: dict[str, str] | None,
    intelligence: dict[str, str] | None,
    memory: dict[str, str] | None,
) -> str:
    if runs_used < 2 or early_score is None or late_score is None:
        return "UNKNOWN_INSUFFICIENT_DATA"

    early = early_score or 0.0
    late = late_score or 0.0
    acceleration = acceleration_score or 0.0
    sustained = sustained_score or 0.0
    pressure = pressure_score or 0.0
    distance = to_float(field(intelligence, "avg_distance_m")) or 0.0
    distance_bucket = field(intelligence, "preferred_distance_bucket").upper()

    if early >= 75 and pressure >= 70:
        return "PRESSURE_LEADER"
    if early >= 70 and sustained >= 70 and late < 70:
        return "FRONT_RUNNING_CONTROLLER"
    if preferred_position in {"LEADER", "ON_PACE"} and sustained >= 65:
        return "ON_PACE_GRINDER"
    if late >= 78 and acceleration >= 78 and distance and distance < 1400:
        return "EXPLOSIVE_SPRINTER"
    if late >= 75 and preferred_position in {"BACKMARKER", "MIDFIELD"}:
        return "STRONG_CLOSER"
    if sustained >= 78 and (distance >= 1800 or "STAY" in distance_bucket):
        return "SUSTAINED_STAYER"
    if preferred_position == "MIDFIELD" and late >= 65:
        return "MIDFIELD_FINISHER"
    if sustained >= 55 and acceleration < 50:
        return "ONE_PACE_GRINDER"

    combined = " ".join(
        [
            field(feature, "run_style_cluster"),
            field(intelligence, "sectional_profile"),
            field(memory, "run_style_cluster"),
            field(memory, "sectional_profile"),
        ]
    ).upper()
    if "CLOSER" in combined or "FAST_FINISH" in combined:
        return "STRONG_CLOSER"
    if "SUSTAIN" in combined and (distance >= 1800 or "STAY" in distance_bucket):
        return "SUSTAINED_STAYER"
    if "SUSTAIN" in combined:
        return "ON_PACE_GRINDER"
    if "LOW_SAMPLE" in combined and runs_used < 3:
        return "UNKNOWN_INSUFFICIENT_DATA"
    return "ONE_PACE_GRINDER"


def infer_confidence(
    runs_used: int,
    feature: dict[str, str] | None,
    intelligence: dict[str, str] | None,
    memory: dict[str, str] | None,
    early_value: float | None,
    mid_value: float | None,
    late_value: float | None,
) -> str:
    if runs_used < 2 or early_value is None or mid_value is None or late_value is None:
        return "INSUFFICIENT"
    source_count = sum(1 for row in (feature, intelligence, memory) if row)
    if runs_used >= 5 and source_count >= 3:
        return "HIGH"
    if runs_used >= 3 and source_count >= 2:
        return "MEDIUM"
    return "LOW"


def discover_sources() -> list[dict[str, Any]]:
    discovered = []
    for path in sorted(DATA_DIR.glob("*.csv")):
        name = path.name.lower()
        if not any(pattern in name for pattern in DISCOVERY_PATTERNS):
            continue
        rows = read_csv(path)
        columns = list(rows[0].keys()) if rows else []
        discovered.append(
            {
                "path": path.name,
                "rows": len(rows),
                "columns": columns,
            }
        )
    return discovered


def build_lookup(rows: list[dict[str, str]], key_column: str = "horse_key") -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        key = normalise_key(row.get(key_column)) or normalise_key(row.get("horse"))
        if key:
            lookup[key] = row
    return lookup


def build_physics_counts(rows: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        if field(row, "trusted_for_live_modelling").upper() == "YES":
            key = normalise_key(row.get("horse"))
            if key:
                counts[key] += 1
    return counts


def missing_columns(rows: list[dict[str, str]], required: set[str], source_name: str) -> str:
    if not rows:
        return f"{source_name}:FILE_MISSING_OR_EMPTY"
    columns = set(rows[0].keys())
    missing = sorted(required - columns)
    if not missing:
        return ""
    return f"{source_name}:{'|'.join(missing)}"


def select_horse_name(feature: dict[str, str] | None, intelligence: dict[str, str] | None, memory: dict[str, str] | None, key: str) -> str:
    for row in (feature, intelligence, memory):
        name = field(row, "horse")
        if name:
            return name
    return key


def collect_metric_values(
    feature_lookup: dict[str, dict[str, str]],
    intelligence_lookup: dict[str, dict[str, str]],
    horse_keys: set[str],
) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = defaultdict(dict)
    for key in horse_keys:
        feature = feature_lookup.get(key)
        intelligence = intelligence_lookup.get(key)
        metric_values = {
            "early": number_from(feature, intelligence, "early_mean", "avg_early_speed"),
            "mid": number_from(feature, intelligence, "mid_mean", "avg_mid_speed"),
            "late": number_from(feature, intelligence, "late_mean", "avg_late_speed"),
            "avg_speed": number_from(feature, intelligence, "avg_speed_mean", "avg_speed"),
            "late_delta": number_from(feature, intelligence, "late_delta_mean", "avg_late_vs_mid_delta"),
            "burst_delta": number_from(feature, intelligence, "burst_delta_mean", "avg_peak_vs_avg_delta"),
        }
        for metric, value in metric_values.items():
            if value is not None:
                metrics[metric][key] = value
    return metrics


def build_horse_dna() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    discovered = discover_sources()
    feature_rows = read_csv(FEATURE_FILE)
    intelligence_rows = read_csv(INTELLIGENCE_FILE)
    memory_rows = read_csv(MEMORY_FILE)
    physics_rows = read_csv(PHYSICS_FILE)

    feature_lookup = build_lookup(feature_rows)
    intelligence_lookup = build_lookup(intelligence_rows)
    memory_lookup = build_lookup(memory_rows)
    physics_counts = build_physics_counts(physics_rows)

    horse_keys = set(feature_lookup) | set(intelligence_lookup) | set(memory_lookup)
    percentile_lookup = percentile_maps(collect_metric_values(feature_lookup, intelligence_lookup, horse_keys))

    output_rows: list[dict[str, Any]] = []

    for key in sorted(horse_keys, key=lambda value: select_horse_name(feature_lookup.get(value), intelligence_lookup.get(value), memory_lookup.get(value), value)):
        feature = feature_lookup.get(key)
        intelligence = intelligence_lookup.get(key)
        memory = memory_lookup.get(key)

        horse = select_horse_name(feature, intelligence, memory, key)
        runs_used = max(
            to_int(field(feature, "runs")) or 0,
            to_int(field(intelligence, "sectional_runs")) or 0,
            to_int(field(memory, "feature_rows")) or 0,
        )
        physics_rows_used = physics_counts.get(key, 0)
        sectional_rows_used = max(runs_used, physics_rows_used)

        early_value = number_from(feature, intelligence, "early_mean", "avg_early_speed")
        mid_value = number_from(feature, intelligence, "mid_mean", "avg_mid_speed")
        late_value = number_from(feature, intelligence, "late_mean", "avg_late_speed")

        if runs_used < 2 or early_value is None or mid_value is None or late_value is None:
            confidence = "INSUFFICIENT"
            archetype = "UNKNOWN_INSUFFICIENT_DATA"
            preferred_position = ""
            preferred_tempo = ""
            early_score = None
            mid_score = None
            late_score = None
            acceleration_score = None
            sustained_score = None
            pressure_score = None
        else:
            early_score = percentile_lookup.get("early", {}).get(key)
            mid_score = percentile_lookup.get("mid", {}).get(key)
            late_score = average(
                [
                    percentile_lookup.get("late", {}).get(key),
                    percentile_lookup.get("late_delta", {}).get(key),
                    score_index(field(feature, "late_power_index")),
                    score_index(field(intelligence, "sectional_strength_score")),
                ]
            )
            acceleration_score = average(
                [
                    percentile_lookup.get("burst_delta", {}).get(key),
                    score_index(field(feature, "burst_index")),
                ]
            )
            sustained_score = average(
                [
                    score_index(field(feature, "sustain_index")),
                    score_index(field(intelligence, "sustained_speed_rate")),
                    percentile_lookup.get("avg_speed", {}).get(key),
                ]
            )
            pressure_score = average(
                [
                    score_index(field(feature, "sustain_index")),
                    score_index(field(feature, "late_power_index")),
                    100.0 - score_index(field(feature, "fatigue_risk_index")) if score_index(field(feature, "fatigue_risk_index")) is not None else None,
                    score_index(field(intelligence, "sustained_speed_rate")),
                ]
            )
            preferred_position = infer_position(memory, early_score, late_score)
            archetype = infer_archetype(
                runs_used,
                early_score,
                late_score,
                acceleration_score,
                sustained_score,
                pressure_score,
                preferred_position,
                feature,
                intelligence,
                memory,
            )
            preferred_tempo = infer_tempo(intelligence, memory, archetype)
            confidence = infer_confidence(runs_used, feature, intelligence, memory, early_value, mid_value, late_value)

        evidence_parts = []
        sources = []
        if feature:
            sources.append("feature_engine_v2")
        if intelligence:
            sources.append("sectional_intelligence_v2")
        if memory:
            sources.append("universal_memory_v1")
        if physics_rows_used:
            sources.append("trusted_physics_rows")
        evidence_parts.append(f"sources={'+'.join(sources) if sources else 'NONE'}")
        evidence_parts.append(f"runs={runs_used}")
        evidence_parts.append(f"sectional_rows={sectional_rows_used}")
        if field(feature, "run_style_cluster"):
            evidence_parts.append(f"cluster={field(feature, 'run_style_cluster')}")
        if field(intelligence, "sectional_profile"):
            evidence_parts.append(f"profile={field(intelligence, 'sectional_profile')}")
        if field(intelligence, "tempo_suitability"):
            evidence_parts.append(f"tempo={field(intelligence, 'tempo_suitability')}")
        if confidence == "INSUFFICIENT":
            evidence_parts.append("INSUFFICIENT: requires at least 2 runs with early/mid/late sectional fields")

        output_rows.append(
            {
                "horse": horse,
                "horse_key": key,
                "runs_used": runs_used,
                "sectional_rows_used": sectional_rows_used,
                "early_speed_score": round_score(early_score),
                "mid_race_strength_score": round_score(mid_score),
                "late_strength_score": round_score(late_score),
                "acceleration_score": round_score(acceleration_score),
                "sustained_speed_score": round_score(sustained_score),
                "pressure_tolerance_score": round_score(pressure_score),
                "preferred_tempo": preferred_tempo,
                "preferred_position": preferred_position,
                "sectional_archetype": archetype,
                "dna_confidence": confidence,
                "evidence_notes": "; ".join(evidence_parts),
            }
        )

    source_files_inspected = [
        f"{entry['path']}({entry['rows']})"
        for entry in discovered
    ]
    missing_required_columns = [
        value
        for value in [
            missing_columns(feature_rows, FEATURE_REQUIRED_COLUMNS, FEATURE_FILE.name),
            missing_columns(intelligence_rows, INTELLIGENCE_REQUIRED_COLUMNS, INTELLIGENCE_FILE.name),
            missing_columns(memory_rows, MEMORY_REQUIRED_COLUMNS, MEMORY_FILE.name),
        ]
        if value
    ]
    confidence_counts = Counter(row["dna_confidence"] for row in output_rows)
    archetype_counts = Counter(row["sectional_archetype"] for row in output_rows)
    horses_with_insufficient_data = confidence_counts.get("INSUFFICIENT", 0)

    audit = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_files_inspected": "; ".join(source_files_inspected),
        "source_files_used": "; ".join(
            [
                FEATURE_FILE.name,
                INTELLIGENCE_FILE.name,
                MEMORY_FILE.name,
                f"{PHYSICS_FILE.name}(trusted row counts only)",
            ]
        ),
        "total_sectional_rows_loaded": len(feature_rows) + len(intelligence_rows) + len(memory_rows) + len(physics_rows),
        "horses_profiled": len(output_rows),
        "horses_with_insufficient_data": horses_with_insufficient_data,
        "archetype_counts": "; ".join(f"{name}:{count}" for name, count in sorted(archetype_counts.items())),
        "confidence_counts": "; ".join(f"{name}:{count}" for name, count in sorted(confidence_counts.items())),
        "missing_required_columns": "; ".join(missing_required_columns) if missing_required_columns else "NONE",
        "output_rows": len(output_rows),
        "status": "HORSE_DNA_BUILT" if output_rows and len(output_rows) > horses_with_insufficient_data else "HORSE_DNA_INSUFFICIENT_SOURCE_DATA",
        "excluded_sources_notes": "sectionals.csv inspected but raw last-600/400/200 scaffold fields are blank; sectional_master/trusted_universe/tempo/cluster files are not used for scoring because they are live, quarantine, sandbox, or lower-granularity research layers.",
        "scoring_method": "Percentile-normalised early/mid/late/burst speed plus existing 0-100 sectional strength indexes; no scores emitted where core sample is below two usable runs.",
    }

    return output_rows, audit


def main() -> None:
    output_rows, audit = build_horse_dna()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_PATH, [audit], list(audit.keys()))

    print(f"Horse DNA rows written: {len(output_rows)}")
    print(f"Audit written: {AUDIT_PATH}")
    print(f"Status: {audit['status']}")
    print(f"Confidence counts: {audit['confidence_counts']}")
    print(f"Archetype counts: {audit['archetype_counts']}")


if __name__ == "__main__":
    main()
