from __future__ import annotations

import csv
import hashlib
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from edgeiq_memory_safe_io import stream_csv_rows, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FORENSICS = DATA / "edgeiq_qld_telemetry_schema_forensics_v1.csv"
FIELD_DICTIONARY = DATA / "edgeiq_qld_telemetry_field_dictionary_v1.csv"
QUALITY_ASSESSMENT = DATA / "edgeiq_qld_telemetry_quality_assessment_v1.csv"
SECTIONAL_SOURCE_INGESTION = DATA / "edgeiq_sectional_source_ingestion_v1.csv"

OUT = DATA / "edgeiq_qld_telemetry_ingestion_v1.csv"
SUMMARY = DATA / "edgeiq_qld_telemetry_ingestion_summary_v1.csv"
LINEAGE = DATA / "edgeiq_qld_telemetry_lineage_v1.csv"
FAILURES = DATA / "edgeiq_qld_telemetry_ingestion_failures_v1.csv"

INGESTION_FIELDS = [
    "jurisdiction",
    "source_file",
    "source_kind",
    "schema_signature",
    "race_date",
    "track",
    "race_no",
    "horse",
    "runner_number",
    "barrier",
    "distance",
    "race_class",
    "track_condition",
    "split_marker",
    "split_distance",
    "split_time",
    "sectional_time",
    "cumulative_time",
    "position_at_split",
    "rank_at_split",
    "gps_speed",
    "gps_position",
    "early_phase_value",
    "mid_phase_value",
    "late_phase_value",
    "source_url",
    "raw_lineage_reference",
    "ingestion_confidence",
    "schema_confidence",
    "safe_for_qld_temporal_research",
    "safe_for_qld_shadow_research",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

LINEAGE_FIELDS = [
    "jurisdiction",
    "source_file",
    "schema_signature",
    "source_kind",
    "rows_ingested",
    "races_ingested",
    "horses_ingested",
    "split_rows_ingested",
    "gps_rows_ingested",
    "position_rows_ingested",
    "lineage_status",
    "schema_stability_status",
    "ingestion_quality_grade",
    "recommended_next_step",
    "notes",
]

FAILURE_FIELDS = [
    "source_file",
    "failure_type",
    "failure_reason",
    "affected_rows",
    "recommended_repair",
    "notes",
]

GRADE_LABEL = {
    "A": "ELITE_QLD_TELEMETRY_LINEAGE",
    "B": "STRONG_QLD_TELEMETRY_LINEAGE",
    "C": "USABLE_QLD_TELEMETRY_LINEAGE",
    "D": "LIMITED_QLD_TELEMETRY_LINEAGE",
    "F": "FAILED_QLD_TELEMETRY_LINEAGE",
}


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
            source = text[:8] if fmt == "%Y%m%d" else text[:10]
            return datetime.strptime(source, fmt).strftime("%Y-%m-%d")
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
        "AQUIS PARK GOLD COAST": "GOLD COAST",
        "AQUIS PARK GOLD COAST POLY": "GOLD COAST POLY",
        "LADBROKES CANNON PARK": "CAIRNS",
        "PICKLEBET PARK WARWICK": "WARWICK",
        "SUNSHINE COAST POLY T": "SUNSHINE COAST POLY",
    }
    return aliases.get(text, text)


def normalise_race_no(value: object) -> str:
    text = upper(value)
    match = re.search(r"(\d+)", text)
    return match.group(1) if match else text


def normalise_horse(value: object) -> str:
    text = upper(value)
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get(row: dict[str, str], *fields: str) -> str:
    lower = {key.lower(): key for key in row}
    for field in fields:
        key = lower.get(field.lower())
        if key:
            return clean(row.get(key))
    return ""


def schema_signature(fields: list[str]) -> str:
    joined = "|".join(sorted(field.lower() for field in fields))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        return list(stream_csv_rows(path))
    except Exception:
        return []


def detect_delimiter(path: Path) -> str:
    try:
        sample = path.read_text(encoding="utf-8-sig", errors="ignore")[:8192]
    except Exception:
        return ","
    if sample.count(";") > sample.count(","):
        return ";"
    if sample.count("\t") > sample.count(","):
        return "\t"
    return ","


def read_raw_csv(path: Path) -> list[dict[str, str]]:
    delimiter = detect_delimiter(path)
    try:
        with path.open("r", newline="", encoding="utf-8-sig", errors="ignore") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            return [{clean(k): clean(v) for k, v in row.items() if k is not None} for row in reader]
    except Exception:
        return []


def discover_raw_qld_files() -> list[Path]:
    roots = [
        ROOT / "outputs" / "sectionals" / "raw" / "QLD",
        DATA,
        ROOT / "dashboard" / "racing-dashboard" / "public" / "data",
    ]
    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            text = str(path).lower()
            if "\\node_modules\\" in text or "\\dist\\" in text:
                continue
            name = path.name.lower()
            if path == SECTIONAL_SOURCE_INGESTION or any(token in name for token in ("qld", "queensland", "sunshine", "gold_coast", "mackay", "doomben", "eagle_farm", "townsville", "rockhampton", "track_t")):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    candidates.append(path)
    if SECTIONAL_SOURCE_INGESTION.exists() and SECTIONAL_SOURCE_INGESTION.resolve() not in seen:
        candidates.append(SECTIONAL_SOURCE_INGESTION)
    return sorted(candidates, key=lambda path: str(path).lower())


def forensics_by_source() -> dict[str, dict[str, str]]:
    rows = read_csv(FORENSICS)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        result[clean(row.get("source_file"))] = row
    return result


def quality_by_race() -> dict[tuple[str, str, str], dict[str, str]]:
    result: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in read_csv(QUALITY_ASSESSMENT):
        key = (
            normalise_date(row.get("race_date")),
            normalise_track(row.get("track")),
            normalise_race_no(row.get("race_no")),
        )
        result[key] = row
    return result


def source_kind(path: Path, forensic: dict[str, str]) -> str:
    if clean(forensic.get("source_kind")):
        return clean(forensic.get("source_kind"))
    if path.name == SECTIONAL_SOURCE_INGESTION.name:
        return "PARSED_QLD_SOURCE_INGESTION"
    if "raw" in [part.lower() for part in path.parts]:
        return "RAW_QLD_SECTIONAL_CSV"
    return "DISCOVERED_QLD_SECTIONAL_CSV"


def is_qld_row(row: dict[str, str], path: Path) -> bool:
    if upper(row.get("state")) == "QLD":
        return True
    if "RACING QUEENSLAND" in upper(row.get("source_name")):
        return True
    if "RACINGQUEENSLAND" in upper(row.get("source_url")):
        return True
    if any(token in path.name.lower() for token in ("qld", "queensland", "sunshine", "gold_coast", "mackay", "doomben", "eagle_farm", "townsville", "rockhampton", "track_t")):
        return True
    return False


def infer_source_rows(path: Path) -> list[dict[str, str]]:
    rows = read_raw_csv(path)
    if path.name == SECTIONAL_SOURCE_INGESTION.name:
        return [row for row in rows if is_qld_row(row, path)]
    return rows


def fallback_track_date(path: Path) -> tuple[str, str]:
    stem = path.stem
    race_date = normalise_date(stem)
    track_part = re.sub(r"20\d{6}", " ", stem)
    track_part = re.sub(r"[_\-]+", " ", track_part)
    track_part = re.sub(r"\([^)]*\)", " ", track_part)
    track_part = re.sub(r"\b(T|G|H|CSV|SECTIONAL|TRACK)\b", " ", track_part, flags=re.IGNORECASE)
    return race_date, normalise_track(track_part)


def split_rows_for_source_row(row: dict[str, str]) -> list[dict[str, str]]:
    split_specs = [
        ("LAST_600", "600", get(row, "last_600", "last600"), get(row, "last_600_rank", "last600_rank")),
        ("LAST_400", "400", get(row, "last_400", "last400"), get(row, "last_400_rank", "last400_rank")),
        ("LAST_200", "200", get(row, "last_200", "last200"), get(row, "last_200_rank", "last200_rank")),
    ]
    result = []
    for marker, distance, split_time, rank in split_specs:
        if split_time:
            result.append(
                {
                    "split_marker": marker,
                    "split_distance": distance,
                    "split_time": split_time,
                    "sectional_time": split_time,
                    "cumulative_time": "",
                    "rank_at_split": rank,
                }
            )
    if result:
        return result
    for field, value in row.items():
        low = field.lower()
        if not value:
            continue
        if "split" in low or "sectional" in low or re.search(r"(200|400|600|800|1000|1200)", low):
            number = re.search(r"(\d{3,4})", low)
            result.append(
                {
                    "split_marker": upper(field),
                    "split_distance": number.group(1) if number else "",
                    "split_time": value,
                    "sectional_time": value,
                    "cumulative_time": "",
                    "rank_at_split": "",
                }
            )
    return result


def confidence_from_quality(quality: dict[str, str], forensic: dict[str, str], split_count: int, gps_present: bool, position_present: bool) -> tuple[float, float]:
    split_score = parse_float(quality.get("split_depth_score")) or parse_float(forensic.get("split_ladder_depth")) or 0.0
    timing_score = parse_float(quality.get("timing_integrity_score")) or parse_float(forensic.get("sectional_interval_consistency")) or 0.0
    lineage_score = parse_float(quality.get("lineage_viability_score")) or 65.0
    density_score = parse_float(quality.get("telemetry_density_score")) or 50.0
    schema_conf = min(100.0, split_score * 0.35 + timing_score * 0.30 + lineage_score * 0.20 + density_score * 0.15)
    ingestion = schema_conf
    ingestion += 4.0 if gps_present else 0.0
    ingestion += 4.0 if position_present else 0.0
    ingestion += min(6.0, split_count * 1.5)
    return min(100.0, ingestion), schema_conf


def grade_lineage(rows: int, races: int, horses: int, split_rows: int, gps_rows: int, position_rows: int, avg_conf: float) -> str:
    if rows <= 0 or races <= 0 or horses <= 0:
        return "F"
    gps_rate = gps_rows / rows if rows else 0
    position_rate = position_rows / rows if rows else 0
    split_rate = split_rows / rows if rows else 0
    score = avg_conf * 0.45 + min(100.0, split_rate * 100) * 0.25 + min(100.0, gps_rate * 100) * 0.15 + min(100.0, position_rate * 100) * 0.15
    if score >= 86:
        return "A"
    if score >= 74:
        return "B"
    if score >= 58:
        return "C"
    if score >= 38:
        return "D"
    return "F"


def main() -> None:
    forensic_index = forensics_by_source()
    quality_index = quality_by_race()
    candidates = discover_raw_qld_files()
    ingestion_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    source_stats: dict[str, dict[str, object]] = defaultdict(lambda: {
        "source_kind": "",
        "schema_signature": "",
        "rows": 0,
        "races": set(),
        "horses": set(),
        "split_rows": 0,
        "gps_rows": 0,
        "position_rows": 0,
        "confidences": [],
    })

    for path in candidates:
        source_rows = infer_source_rows(path)
        if not source_rows:
            failures.append(
                {
                    "source_file": path.name,
                    "failure_type": "NO_Qld_ROWS",
                    "failure_reason": "No QLD sectional rows were detected in this source.",
                    "affected_rows": 0,
                    "recommended_repair": "Confirm source jurisdiction, file delimiter, and raw Racing Queensland CSV availability.",
                    "notes": "QLD ingestion is isolated and did not ingest non-QLD rows.",
                }
            )
            continue
        fields = sorted({field for row in source_rows for field in row.keys()})
        forensic = forensic_index.get(path.name, {})
        signature = clean(forensic.get("schema_signature")) or schema_signature(fields)
        kind = source_kind(path, forensic)
        fallback_date, fallback_track = fallback_track_date(path)
        for raw in source_rows:
            race_date = normalise_date(get(raw, "race_date", "date", "meeting_date")) or fallback_date
            track = normalise_track(get(raw, "track", "venue", "meeting", "track_name")) or fallback_track
            race_no = normalise_race_no(get(raw, "race_no", "race_number", "race", "race_id"))
            horse = clean(get(raw, "horse", "runner", "horse_name", "runner_name"))
            if not race_date or not track or not race_no or not horse:
                failures.append(
                    {
                        "source_file": path.name,
                        "failure_type": "MISSING_IDENTITY_FIELDS",
                        "failure_reason": "Race date, track, race number, or horse identity was missing.",
                        "affected_rows": 1,
                        "recommended_repair": "Repair source identity columns before attempting QLD telemetry research.",
                        "notes": f"race_date={race_date}; track={track}; race_no={race_no}; horse={horse}",
                    }
                )
                continue
            race_key = (race_date, track, race_no)
            quality = quality_index.get(race_key, {})
            split_rows = split_rows_for_source_row(raw)
            if not split_rows:
                failures.append(
                    {
                        "source_file": path.name,
                        "failure_type": "NO_SPLIT_LADDER",
                        "failure_reason": "No split ladder fields were available for this runner row.",
                        "affected_rows": 1,
                        "recommended_repair": "Acquire fuller Racing Queensland CSV payload or repair split field extraction.",
                        "notes": f"{race_date}|{track}|R{race_no}|{horse}",
                    }
                )
            gps_speed = get(raw, "top_speed", "peak_speed", "gps_speed", "speed")
            gps_position = get(raw, "distance_travelled", "gps_position", "position")
            position_available = any(get(raw, field) for field in ("sectional_rank", "last_600_rank", "last_400_rank", "last_200_rank", "position_at_split", "rank_at_split"))
            ingestion_conf, schema_conf = confidence_from_quality(quality, forensic, len(split_rows), bool(gps_speed), position_available)
            horse_key = normalise_horse(horse)
            qld_runner_key = f"QLD|{race_date}|{track}|R{race_no}|{horse_key}"
            stats = source_stats[path.name]
            stats["source_kind"] = kind
            stats["schema_signature"] = signature
            stats["rows"] = int(stats["rows"]) + 1
            stats["races"].add(race_key)
            stats["horses"].add(qld_runner_key)
            stats["gps_rows"] = int(stats["gps_rows"]) + (1 if gps_speed or gps_position else 0)
            stats["position_rows"] = int(stats["position_rows"]) + (1 if position_available else 0)
            stats["split_rows"] = int(stats["split_rows"]) + len(split_rows)
            stats["confidences"].append(ingestion_conf)
            for split in split_rows:
                rank_at_split = clean(split.get("rank_at_split"))
                ingestion_rows.append(
                    {
                        "jurisdiction": "QLD",
                        "source_file": path.name,
                        "source_kind": kind,
                        "schema_signature": signature,
                        "race_date": race_date,
                        "track": track,
                        "race_no": race_no,
                        "horse": horse,
                        "runner_number": get(raw, "runner_number", "runner_no", "saddlecloth", "tab_no"),
                        "barrier": get(raw, "barrier", "barrier_no", "gate"),
                        "distance": get(raw, "distance"),
                        "race_class": get(raw, "race_class", "class"),
                        "track_condition": get(raw, "track_condition", "condition", "going"),
                        "split_marker": split["split_marker"],
                        "split_distance": split["split_distance"],
                        "split_time": split["split_time"],
                        "sectional_time": split["sectional_time"],
                        "cumulative_time": split["cumulative_time"],
                        "position_at_split": rank_at_split,
                        "rank_at_split": rank_at_split,
                        "gps_speed": gps_speed,
                        "gps_position": gps_position,
                        "early_phase_value": get(raw, "early_speed", "early_phase_value"),
                        "mid_phase_value": get(raw, "mid_speed", "mid_phase_value"),
                        "late_phase_value": get(raw, "late_speed", "late_phase_value"),
                        "source_url": get(raw, "source_url"),
                        "raw_lineage_reference": get(raw, "raw_file", "source_file") or qld_runner_key,
                        "ingestion_confidence": f"{ingestion_conf:.2f}",
                        "schema_confidence": f"{schema_conf:.2f}",
                        "safe_for_qld_temporal_research": "YES" if ingestion_conf >= 58 and split_rows else "NO",
                        "safe_for_qld_shadow_research": "YES" if ingestion_conf >= 74 and split_rows and position_available else "NO",
                        "notes": f"Isolated QLD telemetry ingestion only. qld_runner_key={qld_runner_key}. No VIC merge, modelling, ratings, overlays, or execution.",
                    }
                )

    lineage_rows: list[dict[str, object]] = []
    for source_file, stats in sorted(source_stats.items()):
        rows_ingested = int(stats["rows"])
        races = stats["races"]
        horses = stats["horses"]
        split_count = int(stats["split_rows"])
        gps_count = int(stats["gps_rows"])
        position_count = int(stats["position_rows"])
        confidences = stats["confidences"]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        grade = grade_lineage(rows_ingested, len(races), len(horses), split_count, gps_count, position_count, avg_conf)
        schema_status = "STABLE_SCHEMA" if grade in {"A", "B"} else "REVIEW_SCHEMA" if grade in {"C", "D"} else "FAILED_SCHEMA"
        if grade in {"A", "B"}:
            next_step = "Keep QLD isolated; begin longitudinal QLD-only lineage monitoring before any cross-jurisdiction review."
        elif grade == "C":
            next_step = "Use QLD source for offline diagnostics; improve identity and position extraction before shadow research."
        elif grade == "D":
            next_step = "Repair split ladder completeness and source lineage before temporal research."
        else:
            next_step = "Do not use source beyond failure diagnostics."
        lineage_rows.append(
            {
                "jurisdiction": "QLD",
                "source_file": source_file,
                "schema_signature": stats["schema_signature"],
                "source_kind": stats["source_kind"],
                "rows_ingested": rows_ingested,
                "races_ingested": len(races),
                "horses_ingested": len(horses),
                "split_rows_ingested": split_count,
                "gps_rows_ingested": gps_count,
                "position_rows_ingested": position_count,
                "lineage_status": GRADE_LABEL[grade],
                "schema_stability_status": schema_status,
                "ingestion_quality_grade": grade,
                "recommended_next_step": next_step,
                "notes": "QLD lineage remains isolated from VIC telemetry and execution.",
            }
        )

    grades = Counter(clean(row.get("ingestion_quality_grade")) for row in lineage_rows)
    summary_rows = [
        {"metric": "qld_rows_ingested", "value": sum(int(row.get("rows_ingested") or 0) for row in lineage_rows)},
        {"metric": "qld_races_ingested", "value": len({(row["race_date"], row["track"], row["race_no"]) for row in ingestion_rows})},
        {"metric": "qld_horses_ingested", "value": len({(row["race_date"], row["track"], row["race_no"], normalise_horse(row["horse"])) for row in ingestion_rows})},
        {"metric": "qld_split_rows_ingested", "value": len(ingestion_rows)},
        {"metric": "qld_gps_rows_ingested", "value": sum(1 for row in ingestion_rows if clean(row.get("gps_speed")) or clean(row.get("gps_position")))},
        {"metric": "qld_position_rows_ingested", "value": sum(1 for row in ingestion_rows if clean(row.get("position_at_split")) or clean(row.get("rank_at_split")))},
        {"metric": "elite_lineage_sources", "value": grades.get("A", 0)},
        {"metric": "strong_lineage_sources", "value": grades.get("B", 0)},
        {"metric": "usable_lineage_sources", "value": grades.get("C", 0)},
        {"metric": "limited_lineage_sources", "value": grades.get("D", 0)},
        {"metric": "failed_lineage_sources", "value": grades.get("F", 0)},
        {"metric": "safe_for_qld_temporal_research_yes", "value": sum(1 for row in ingestion_rows if row.get("safe_for_qld_temporal_research") == "YES")},
        {"metric": "safe_for_qld_shadow_research_yes", "value": sum(1 for row in ingestion_rows if row.get("safe_for_qld_shadow_research") == "YES")},
        {"metric": "ingestion_failures", "value": len(failures)},
        {"metric": "merged_into_vic_telemetry", "value": "NO"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv_atomic(OUT, ingestion_rows, INGESTION_FIELDS)
    write_csv_atomic(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv_atomic(LINEAGE, lineage_rows, LINEAGE_FIELDS)
    write_csv_atomic(FAILURES, failures, FAILURE_FIELDS)

    print("=" * 88)
    print("EDGEIQ QLD TELEMETRY INGESTION PIPELINE V1")
    print("=" * 88)
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {LINEAGE}")
    print(f"saved: {FAILURES}")


if __name__ == "__main__":
    main()
