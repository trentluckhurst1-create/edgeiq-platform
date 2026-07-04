from __future__ import annotations

import csv
import hashlib
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from edgeiq_memory_safe_io import write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TELEMETRY_HEALTH = DATA / "edgeiq_telemetry_health_monitor_v1.csv"
TIMING_LINEAGE = DATA / "edgeiq_timing_lineage_validation_v1.csv"
SECTIONAL_SOURCE_INGESTION = DATA / "edgeiq_sectional_source_ingestion_v1.csv"

OUT = DATA / "edgeiq_qld_telemetry_schema_forensics_v1.csv"
SUMMARY = DATA / "edgeiq_qld_telemetry_schema_summary_v1.csv"
FIELD_DICTIONARY = DATA / "edgeiq_qld_telemetry_field_dictionary_v1.csv"
QUALITY = DATA / "edgeiq_qld_telemetry_quality_assessment_v1.csv"

FORENSICS_FIELDS = [
    "source_file",
    "source_path",
    "source_kind",
    "rows",
    "delimiter",
    "schema_signature",
    "column_count",
    "detected_columns",
    "race_date_min",
    "race_date_max",
    "tracks_detected",
    "race_count",
    "horse_rows",
    "gps_derived_fields",
    "positional_fields",
    "timing_fields",
    "split_fields",
    "split_ladder_depth",
    "timestamp_fields",
    "timestamp_precision",
    "race_identifier_fields",
    "horse_identifier_fields",
    "sectional_interval_consistency",
    "longitudinal_schema_stability",
    "hidden_telemetry_richness",
    "source_classification",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

FIELD_DICTIONARY_FIELDS = [
    "field_name",
    "field_type",
    "nullable_rate",
    "uniqueness_rate",
    "observed_examples",
    "suspected_meaning",
    "telemetry_importance",
    "schema_confidence",
    "notes",
]

QUALITY_FIELDS = [
    "track",
    "race_date",
    "race_no",
    "schema_version",
    "split_depth_score",
    "gps_richness_score",
    "timing_integrity_score",
    "position_integrity_score",
    "lineage_viability_score",
    "telemetry_density_score",
    "payload_quality_grade",
    "research_viability",
    "recommended_usage",
    "notes",
]


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> float | None:
    text = clean(value).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalise_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10] if fmt != "%Y%m%d" else text[:8], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(20\d{6})", text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return text[:10]


def normalise_track(value: object) -> str:
    text = upper(value).replace("&", " AND ")
    text = re.sub(r"\b(RACECOURSE|RACING|CLUB|TRACK)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    aliases = {
        "SUNSHINE COAST POLY": "SUNSHINE COAST POLY",
        "SUNSHINE COAST POLY T": "SUNSHINE COAST POLY",
        "SUNSHINE COAST": "SUNSHINE COAST",
        "GOLD COAST POLY": "GOLD COAST POLY",
        "GOLD COAST": "GOLD COAST",
        "IPSWICH": "IPSWICH",
        "DOOMBEN": "DOOMBEN",
        "EAGLE FARM": "EAGLE FARM",
        "MACKAY": "MACKAY",
        "ROCKHAMPTON": "ROCKHAMPTON",
        "TOWNSVILLE": "TOWNSVILLE",
        "CAIRNS": "CAIRNS",
    }
    return aliases.get(text, text)


def normalise_race_no(value: object) -> str:
    text = upper(value)
    match = re.search(r"(\d+)", text)
    return match.group(1) if match else text


def detect_delimiter(path: Path) -> str:
    try:
        sample = path.read_text(encoding="utf-8-sig", errors="ignore")[:8192]
    except Exception:
        return ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        if sample.count(";") > sample.count(","):
            return ";"
        if sample.count("\t") > sample.count(","):
            return "\t"
        return ","


def read_csv(path: Path, delimiter: str | None = None, max_rows: int | None = None) -> list[dict[str, str]]:
    if not path.exists():
        return []
    delim = delimiter or detect_delimiter(path)
    try:
        with path.open("r", newline="", encoding="utf-8-sig", errors="ignore") as handle:
            reader = csv.DictReader(handle, delimiter=delim)
            rows = []
            for idx, row in enumerate(reader):
                if max_rows is not None and idx >= max_rows:
                    break
                rows.append({clean(k): clean(v) for k, v in row.items() if k is not None})
            return rows
    except Exception:
        return []


def discover_candidate_files() -> list[Path]:
    candidates: list[Path] = []
    search_roots = [
        ROOT,
        ROOT / "outputs" / "sectionals" / "raw" / "QLD",
        DATA,
        ROOT / "dist" / "data",
    ]
    seen: set[Path] = set()
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in search_root.rglob("*.csv"):
            text = str(path).lower()
            if "\\node_modules\\" in text or "\\.git\\" in text:
                continue
            name = path.name.lower()
            is_qld_named = any(token in name for token in ("qld", "queensland", "sunshine", "gold_coast", "mackay", "doomben", "eagle_farm", "townsville", "rockhampton", "track_t"))
            is_sectional_named = "sectional" in name or "racing_queensland" in name
            if path == SECTIONAL_SOURCE_INGESTION or (is_sectional_named and is_qld_named):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    candidates.append(path)
    if SECTIONAL_SOURCE_INGESTION.exists() and SECTIONAL_SOURCE_INGESTION.resolve() not in seen:
        candidates.append(SECTIONAL_SOURCE_INGESTION)
    return sorted(candidates, key=lambda item: str(item).lower())


def source_kind(path: Path) -> str:
    if path == SECTIONAL_SOURCE_INGESTION:
        return "PARSED_Qld_SOURCE_INGESTION"
    if "outputs" in [part.lower() for part in path.parts] or "raw" in [part.lower() for part in path.parts]:
        return "RAW_Qld_SECTIONAL_CSV"
    if "dist" in [part.lower() for part in path.parts]:
        return "BUILT_ARTIFACT_Qld_SECTIONAL_CSV"
    return "DISCOVERED_Qld_SECTIONAL_CSV"


def qld_rows_for_file(path: Path) -> tuple[list[dict[str, str]], str]:
    delimiter = detect_delimiter(path)
    rows = read_csv(path, delimiter=delimiter)
    if path.name == SECTIONAL_SOURCE_INGESTION.name:
        rows = [
            row
            for row in rows
            if upper(row.get("state")) == "QLD"
            or "RACING QUEENSLAND" in upper(row.get("source_name"))
            or "RACINGQUEENSLAND" in upper(row.get("source_url"))
        ]
    return rows, delimiter


def field_groups(fields: list[str]) -> dict[str, list[str]]:
    lowered = {field: field.lower() for field in fields}
    groups = {
        "gps": [],
        "position": [],
        "timing": [],
        "split": [],
        "timestamp": [],
        "race_id": [],
        "horse_id": [],
    }
    for field, low in lowered.items():
        if any(token in low for token in ("gps", "lat", "lon", "latitude", "longitude", "coordinate", "metre", "meter", "distance_travelled", "speed", "velocity", "stride")):
            groups["gps"].append(field)
        if any(token in low for token in ("position", "rank", "place", "pos", "settling", "turn")):
            groups["position"].append(field)
        if any(token in low for token in ("time", "split", "sectional", "last_", "600", "400", "200", "early", "mid", "late", "peak")):
            groups["timing"].append(field)
        if re.search(r"(last_?\d+|\d{3,4}|split|sectional)", low):
            groups["split"].append(field)
        if any(token in low for token in ("timestamp", "fetched_at", "created_at", "updated_at", "time_utc", "datetime")):
            groups["timestamp"].append(field)
        if any(token in low for token in ("race_date", "race_no", "race_number", "race_id", "track", "meeting", "distance")):
            groups["race_id"].append(field)
        if any(token in low for token in ("horse", "runner", "horse_key", "saddlecloth", "tab_no")):
            groups["horse_id"].append(field)
    return groups


def schema_signature(fields: list[str]) -> str:
    joined = "|".join(sorted(field.lower() for field in fields))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]


def infer_track_date_from_filename(path: Path) -> tuple[str, str]:
    stem = path.stem
    race_date = normalise_date(stem)
    track_part = re.sub(r"20\d{6}", " ", stem)
    track_part = re.sub(r"[_\-]+", " ", track_part)
    track_part = re.sub(r"\([^)]*\)", " ", track_part)
    track_part = re.sub(r"\b(T|G|H|CSV|SECTIONAL|TRACK)\b", " ", track_part, flags=re.IGNORECASE)
    track = normalise_track(track_part)
    return race_date, track


def get_value(row: dict[str, str], candidates: list[str]) -> str:
    low_map = {field.lower(): field for field in row}
    for candidate in candidates:
        field = low_map.get(candidate.lower())
        if field:
            return clean(row.get(field))
    return ""


def race_key(row: dict[str, str], fallback_date: str, fallback_track: str) -> tuple[str, str, str]:
    race_date = normalise_date(get_value(row, ["race_date", "date", "meeting_date"])) or fallback_date
    track = normalise_track(get_value(row, ["track", "venue", "meeting", "track_name"])) or fallback_track
    race_no = normalise_race_no(get_value(row, ["race_no", "race_number", "race", "race_id"]))
    return race_date, track, race_no


def infer_field_type(values: list[str]) -> str:
    populated = [clean(value) for value in values if clean(value)]
    if not populated:
        return "empty"
    numeric = sum(1 for value in populated if parse_float(value) is not None)
    dates = sum(1 for value in populated if normalise_date(value) and re.search(r"\d", value))
    if numeric / len(populated) >= 0.9:
        return "numeric"
    if dates / len(populated) >= 0.75:
        return "date_or_timestamp"
    if numeric and numeric / len(populated) >= 0.25:
        return "mixed_numeric_text"
    return "text"


def suspected_meaning(field: str) -> tuple[str, str, float]:
    low = field.lower()
    if any(token in low for token in ("horse", "runner")):
        return "Horse or runner identity", "CRITICAL", 92.0
    if any(token in low for token in ("race_date", "race_no", "track", "meeting", "distance")):
        return "Race identity and linkage", "CRITICAL", 90.0
    if any(token in low for token in ("last_600", "last_400", "last_200", "sectional", "split")):
        return "Sectional timing ladder", "HIGH", 88.0
    if any(token in low for token in ("early", "mid", "late", "peak", "speed", "velocity")):
        return "Derived speed or temporal phase telemetry", "HIGH", 84.0
    if any(token in low for token in ("rank", "position", "place", "pos")):
        return "Positional or rank telemetry", "MEDIUM", 76.0
    if any(token in low for token in ("gps", "lat", "lon", "distance_travelled")):
        return "GPS-derived movement telemetry", "HIGH", 82.0
    if any(token in low for token in ("source", "url", "raw_file", "fetched")):
        return "Source lineage and provenance", "HIGH", 80.0
    return "General payload attribute", "LOW", 55.0


def build_field_dictionary(source_rows: list[tuple[Path, list[dict[str, str]]]]) -> list[dict[str, object]]:
    values_by_field: dict[str, list[str]] = defaultdict(list)
    for _, rows in source_rows:
        for row in rows:
            for field, value in row.items():
                values_by_field[field].append(clean(value))

    out_rows: list[dict[str, object]] = []
    for field, values in sorted(values_by_field.items(), key=lambda item: item[0].lower()):
        total = len(values)
        blanks = sum(1 for value in values if not value)
        populated = [value for value in values if value]
        unique = set(populated)
        meaning, importance, confidence = suspected_meaning(field)
        examples = " | ".join(list(dict.fromkeys(populated))[:5])
        out_rows.append(
            {
                "field_name": field,
                "field_type": infer_field_type(values),
                "nullable_rate": f"{(blanks / total * 100) if total else 100:.2f}",
                "uniqueness_rate": f"{(len(unique) / len(populated) * 100) if populated else 0:.2f}",
                "observed_examples": examples[:500],
                "suspected_meaning": meaning,
                "telemetry_importance": importance,
                "schema_confidence": f"{confidence:.2f}",
                "notes": "QLD telemetry field dictionary. Offline schema forensics only; no modelling or execution.",
            }
        )
    return out_rows


def interval_consistency(rows: list[dict[str, str]]) -> float:
    checks = 0
    passed = 0
    for row in rows:
        last_600 = parse_float(get_value(row, ["last_600", "last600"]))
        last_400 = parse_float(get_value(row, ["last_400", "last400"]))
        last_200 = parse_float(get_value(row, ["last_200", "last200"]))
        early = parse_float(get_value(row, ["early_speed", "early_phase_value"]))
        mid = parse_float(get_value(row, ["mid_speed", "mid_phase_value"]))
        late = parse_float(get_value(row, ["late_speed", "late_phase_value"]))
        if last_600 and last_400 and last_200:
            checks += 1
            if last_600 >= last_400 >= last_200 > 0:
                passed += 1
        if early and mid and late:
            checks += 1
            if 5 <= early <= 25 and 5 <= mid <= 25 and 5 <= late <= 25:
                passed += 1
    return passed / checks * 100 if checks else 0.0


def classify_source(split_depth: int, gps_score: float, timing_score: float, position_score: float, density: float, lineage: float) -> tuple[str, str]:
    composite = split_depth * 0.22 + gps_score * 0.16 + timing_score * 0.24 + position_score * 0.12 + density * 0.14 + lineage * 0.12
    if composite >= 86:
        return "A", "ELITE_TELEMETRY_SOURCE"
    if composite >= 74:
        return "B", "HIGH_VALUE_TELEMETRY_SOURCE"
    if composite >= 58:
        return "C", "USABLE_TELEMETRY_SOURCE"
    if composite >= 38:
        return "D", "LIMITED_TELEMETRY_SOURCE"
    return "F", "UNSTABLE_TELEMETRY_SOURCE"


def build_forensics_and_quality(source_rows: list[tuple[Path, list[dict[str, str]]]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    schema_counts = Counter()
    per_file_base: dict[Path, dict[str, object]] = {}
    for path, rows in source_rows:
        fields = sorted({field for row in rows for field in row.keys()})
        sig = schema_signature(fields)
        schema_counts[sig] += 1
        groups = field_groups(fields)
        fallback_date, fallback_track = infer_track_date_from_filename(path)
        dates = [race_key(row, fallback_date, fallback_track)[0] for row in rows]
        tracks = [race_key(row, fallback_date, fallback_track)[1] for row in rows]
        races = {race_key(row, fallback_date, fallback_track) for row in rows}
        horse_rows = sum(1 for row in rows if get_value(row, ["horse", "runner", "runner_name", "horse_name"]))
        split_depth = min(100, len(groups["split"]) * 18)
        gps_score = min(100, len(groups["gps"]) * 18)
        timing_score = min(100, len(groups["timing"]) * 12 + interval_consistency(rows) * 0.35)
        position_score = min(100, len(groups["position"]) * 20)
        lineage = 82.0 if any(field in fields for field in ("source_url", "raw_file", "source_file", "fetched_at")) else 55.0
        populated_cells = 0
        total_cells = max(1, len(rows) * max(1, len(fields)))
        for row in rows:
            populated_cells += sum(1 for value in row.values() if clean(value))
        density = populated_cells / total_cells * 100
        grade, label = classify_source(split_depth, gps_score, timing_score, position_score, density, lineage)
        schema_stability = schema_counts[sig]
        per_file_base[path] = {
            "fields": fields,
            "sig": sig,
            "groups": groups,
            "fallback_date": fallback_date,
            "fallback_track": fallback_track,
            "dates": dates,
            "tracks": tracks,
            "races": races,
            "horse_rows": horse_rows,
            "split_depth": split_depth,
            "gps_score": gps_score,
            "timing_score": timing_score,
            "position_score": position_score,
            "lineage": lineage,
            "density": density,
            "grade": grade,
            "label": label,
            "schema_stability": schema_stability,
        }

    forensics_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []
    for path, rows in source_rows:
        base = per_file_base[path]
        fields = base["fields"]
        groups = base["groups"]
        dates = [date for date in base["dates"] if date]
        tracks = [track for track in base["tracks"] if track]
        race_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            race_groups[race_key(row, str(base["fallback_date"]), str(base["fallback_track"]))].append(row)
        forensics_rows.append(
            {
                "source_file": path.name,
                "source_path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "source_kind": source_kind(path),
                "rows": len(rows),
                "delimiter": detect_delimiter(path),
                "schema_signature": base["sig"],
                "column_count": len(fields),
                "detected_columns": "|".join(fields),
                "race_date_min": min(dates) if dates else "",
                "race_date_max": max(dates) if dates else "",
                "tracks_detected": "|".join(sorted(set(tracks)))[:500],
                "race_count": len(race_groups),
                "horse_rows": base["horse_rows"],
                "gps_derived_fields": "|".join(groups["gps"]),
                "positional_fields": "|".join(groups["position"]),
                "timing_fields": "|".join(groups["timing"]),
                "split_fields": "|".join(groups["split"]),
                "split_ladder_depth": base["split_depth"],
                "timestamp_fields": "|".join(groups["timestamp"]),
                "timestamp_precision": "ISO_OR_DATETIME" if groups["timestamp"] else "NONE_DETECTED",
                "race_identifier_fields": "|".join(groups["race_id"]),
                "horse_identifier_fields": "|".join(groups["horse_id"]),
                "sectional_interval_consistency": f"{interval_consistency(rows):.2f}",
                "longitudinal_schema_stability": base["schema_stability"],
                "hidden_telemetry_richness": "HIGH" if base["gps_score"] >= 50 or len(groups["position"]) >= 3 else "MEDIUM" if base["split_depth"] >= 50 else "LOW",
                "source_classification": base["label"],
                "notes": "QLD telemetry schema forensics only. No predictions, ratings, overlays, live modelling, or execution.",
            }
        )
        for (race_date, track, race_no), group in sorted(race_groups.items()):
            local_consistency = interval_consistency(group)
            split_depth = min(100, int(base["split_depth"]))
            gps_score = float(base["gps_score"])
            timing_score = min(100.0, float(base["timing_score"]) * 0.65 + local_consistency * 0.35)
            position_score = float(base["position_score"])
            lineage = float(base["lineage"])
            density = float(base["density"])
            grade, label = classify_source(split_depth, gps_score, timing_score, position_score, density, lineage)
            if grade in {"A", "B"}:
                usage = "High-value offline telemetry research candidate; validate identity before any cross-state integration."
            elif grade == "C":
                usage = "Usable for offline schema and timing research; improve GPS/position richness before behavioural persistence work."
            elif grade == "D":
                usage = "Limited telemetry source; use for schema diagnostics and targeted acquisition planning only."
            else:
                usage = "Unstable telemetry source; do not use beyond diagnostics until source structure is repaired."
            quality_rows.append(
                {
                    "track": track,
                    "race_date": race_date,
                    "race_no": race_no,
                    "schema_version": base["sig"],
                    "split_depth_score": f"{split_depth:.2f}",
                    "gps_richness_score": f"{gps_score:.2f}",
                    "timing_integrity_score": f"{timing_score:.2f}",
                    "position_integrity_score": f"{position_score:.2f}",
                    "lineage_viability_score": f"{lineage:.2f}",
                    "telemetry_density_score": f"{density:.2f}",
                    "payload_quality_grade": label,
                    "research_viability": "YES" if grade in {"A", "B", "C"} else "LIMITED" if grade == "D" else "NO",
                    "recommended_usage": usage,
                    "notes": f"Race-level QLD telemetry quality from {path.name}. Offline forensics only.",
                }
            )
    return forensics_rows, quality_rows


def build_summary(forensics_rows: list[dict[str, object]], field_rows: list[dict[str, object]], quality_rows: list[dict[str, object]], source_rows: list[tuple[Path, list[dict[str, str]]]]) -> list[dict[str, object]]:
    quality_counts = Counter(clean(row.get("payload_quality_grade")) for row in quality_rows)
    source_classes = Counter(clean(row.get("source_classification")) for row in forensics_rows)
    gps_candidates = sum(1 for row in forensics_rows if clean(row.get("gps_derived_fields")))
    position_candidates = sum(1 for row in forensics_rows if clean(row.get("positional_fields")))
    split_rich = sum(1 for row in forensics_rows if float(row.get("split_ladder_depth") or 0) >= 50)
    return [
        {"metric": "qld_source_files_audited", "value": len(source_rows)},
        {"metric": "qld_source_rows_audited", "value": sum(len(rows) for _, rows in source_rows)},
        {"metric": "forensic_rows", "value": len(forensics_rows)},
        {"metric": "field_dictionary_rows", "value": len(field_rows)},
        {"metric": "quality_assessment_rows", "value": len(quality_rows)},
        {"metric": "gps_structure_candidates", "value": gps_candidates},
        {"metric": "positional_structure_candidates", "value": position_candidates},
        {"metric": "full_or_deep_split_candidates", "value": split_rich},
        {"metric": "elite_telemetry_sources", "value": source_classes.get("ELITE_TELEMETRY_SOURCE", 0)},
        {"metric": "high_value_telemetry_sources", "value": source_classes.get("HIGH_VALUE_TELEMETRY_SOURCE", 0)},
        {"metric": "usable_telemetry_sources", "value": source_classes.get("USABLE_TELEMETRY_SOURCE", 0)},
        {"metric": "limited_telemetry_sources", "value": source_classes.get("LIMITED_TELEMETRY_SOURCE", 0)},
        {"metric": "unstable_telemetry_sources", "value": source_classes.get("UNSTABLE_TELEMETRY_SOURCE", 0)},
        {"metric": "quality::ELITE_TELEMETRY_SOURCE", "value": quality_counts.get("ELITE_TELEMETRY_SOURCE", 0)},
        {"metric": "quality::HIGH_VALUE_TELEMETRY_SOURCE", "value": quality_counts.get("HIGH_VALUE_TELEMETRY_SOURCE", 0)},
        {"metric": "quality::USABLE_TELEMETRY_SOURCE", "value": quality_counts.get("USABLE_TELEMETRY_SOURCE", 0)},
        {"metric": "quality::LIMITED_TELEMETRY_SOURCE", "value": quality_counts.get("LIMITED_TELEMETRY_SOURCE", 0)},
        {"metric": "quality::UNSTABLE_TELEMETRY_SOURCE", "value": quality_counts.get("UNSTABLE_TELEMETRY_SOURCE", 0)},
        {"metric": "reference_rows::edgeiq_telemetry_health_monitor_v1", "value": len(read_csv(TELEMETRY_HEALTH, max_rows=1000000)) if TELEMETRY_HEALTH.exists() else 0},
        {"metric": "reference_rows::edgeiq_timing_lineage_validation_v1", "value": len(read_csv(TIMING_LINEAGE, max_rows=1000000)) if TIMING_LINEAGE.exists() else 0},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "merged_into_vic_telemetry", "value": "NO"},
    ]


def main() -> None:
    candidates = discover_candidate_files()
    source_rows: list[tuple[Path, list[dict[str, str]]]] = []
    for path in candidates:
        rows, _ = qld_rows_for_file(path)
        if rows:
            source_rows.append((path, rows))

    field_rows = build_field_dictionary(source_rows)
    forensics_rows, quality_rows = build_forensics_and_quality(source_rows)
    summary_rows = build_summary(forensics_rows, field_rows, quality_rows, source_rows)

    write_csv_atomic(OUT, forensics_rows, FORENSICS_FIELDS)
    write_csv_atomic(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv_atomic(FIELD_DICTIONARY, field_rows, FIELD_DICTIONARY_FIELDS)
    write_csv_atomic(QUALITY, quality_rows, QUALITY_FIELDS)

    print("=" * 88)
    print("EDGEIQ QLD TELEMETRY SCHEMA FORENSICS V1")
    print("=" * 88)
    for row in summary_rows[:18]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {FIELD_DICTIONARY}")
    print(f"saved: {QUALITY}")


if __name__ == "__main__":
    main()
