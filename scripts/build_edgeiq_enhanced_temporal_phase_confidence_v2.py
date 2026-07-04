from __future__ import annotations

import csv
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LADDERS = DATA / "edgeiq_raw_sectional_extracted_split_ladders_v1.csv"
PARSER = DATA / "edgeiq_raw_sectional_payload_schema_parser_v1.csv"
QUALITY = DATA / "edgeiq_sectional_payload_quality_v1.csv"
TEMPORAL = DATA / "edgeiq_temporal_physics_engine_v1.csv"
VALIDATION = DATA / "edgeiq_temporal_physics_validation_v1.csv"

OUT = DATA / "edgeiq_enhanced_temporal_phase_confidence_v2.csv"
SUMMARY = DATA / "edgeiq_enhanced_temporal_phase_summary_v2.csv"
IMPROVEMENT = DATA / "edgeiq_phase_confidence_improvement_v2.csv"

OUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "source_file",
    "old_phase_confidence",
    "new_phase_confidence",
    "split_depth_score",
    "timing_lineage_score",
    "horse_level_timing_score",
    "physics_consistency_delta",
    "reconstruction_dependency_delta",
    "phase_integrity_score",
    "temporal_research_grade",
    "temporal_research_label",
    "quality_blocker_before",
    "quality_blocker_after",
    "improvement_status",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

IMPROVEMENT_FIELDS = [
    "improvement_type",
    "before_count",
    "after_count",
    "delta",
    "improvement_rate",
    "notes",
]

GRADE_LABEL = {
    "A": "HIGH_CONFIDENCE_TEMPORAL_PAYLOAD",
    "B": "STRONG_TEMPORAL_PAYLOAD",
    "C": "USABLE_TEMPORAL_PAYLOAD",
    "D": "WEAK_TEMPORAL_PAYLOAD",
    "F": "UNSAFE_TEMPORAL_PAYLOAD",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, csv.Error):
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{time.time_ns()}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def parse_float(value: object, default: float = 0.0) -> float:
    text = clean(value).replace("%", "").replace(",", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def normal_horse(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\([A-Z]{2,3}\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def normal_track(value: object) -> str:
    text = upper(value)
    aliases = {
        "BET365 YARRA VALLEY": "YARRA VALLEY",
        "BET365 PARK KILMORE": "KILMORE",
        "BET365 KILMORE": "KILMORE",
        "LADBROKES GEELONG": "GEELONG",
        "SPORTSBET SANDOWN HILLSIDE": "SANDOWN",
        "SPORTSBET SANDOWN LAKESIDE": "SANDOWN",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
        "THE VALLEY": "MOONEE VALLEY",
    }
    return aliases.get(text, text)


def normal_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d%b%y", "%d%b%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def race_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            normal_date(row.get("race_date")),
            normal_track(row.get("track")),
            clean(row.get("race_no")),
            normal_horse(row.get("horse")),
        ]
    )


def grade_from_score(score: float, unsafe: bool = False) -> str:
    if unsafe or score < 35:
        return "F"
    if score >= 85:
        return "A"
    if score >= 72:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def build_ladder_profiles(rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = race_key(row)
        if key.strip("|"):
            grouped[key].append(row)

    profiles: dict[str, dict[str, object]] = {}
    for key, values in grouped.items():
        markers = {upper(row.get("split_marker")) for row in values if clean(row.get("split_marker"))}
        distances = {clean(row.get("split_distance")) for row in values if clean(row.get("split_distance"))}
        confidences = [parse_float(row.get("schema_confidence")) for row in values if clean(row.get("schema_confidence"))]
        early = max((parse_float(row.get("early_phase_value")) for row in values), default=0.0)
        mid = max((parse_float(row.get("mid_phase_value")) for row in values), default=0.0)
        late = max((parse_float(row.get("late_phase_value")) for row in values), default=0.0)
        split_depth = min(100.0, (len(markers) / 3.0) * 82.0 + (len(distances) / 3.0) * 18.0)
        profiles[key] = {
            "split_markers": markers,
            "split_depth_score": split_depth,
            "schema_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "early": early,
            "mid": mid,
            "late": late,
            "rows": len(values),
        }
    return profiles


def build_parser_profiles(rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    best: dict[str, dict[str, object]] = {}
    for row in rows:
        key = race_key(row)
        if not key.strip("|"):
            continue
        status = upper(row.get("extraction_status"))
        confidence = parse_float(row.get("schema_confidence"))
        schema = clean(row.get("schema_type"))
        timing_score = 0.0
        if status == "FULL_SPLIT_LADDER_EXTRACTED":
            timing_score = 100.0
        elif status == "PARTIAL_SPLIT_LADDER_EXTRACTED":
            timing_score = 72.0
        elif status == "HORSE_LEVEL_TIMING_EXTRACTED":
            timing_score = 54.0
        elif status == "SCHEMA_DETECTED_NOT_EXTRACTED":
            timing_score = 24.0
        existing = best.get(key)
        if not existing or confidence > parse_float(existing.get("schema_confidence")):
            best[key] = {
                "schema_confidence": confidence,
                "schema_type": schema,
                "extraction_status": status,
                "horse_level_timing_score": timing_score,
                "payload_source": clean(row.get("payload_source")),
            }
    return best


def build_temporal_profiles(rows: list[dict[str, str]], validation_rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[race_key(row)].append(row)
    for row in validation_rows:
        grouped[race_key(row)].append(row)

    profiles: dict[str, dict[str, object]] = {}
    for key, values in grouped.items():
        scores = [parse_float(row.get("temporal_physics_score")) for row in values if clean(row.get("temporal_physics_score"))]
        grades = Counter(upper(row.get("temporal_stability_grade")) for row in values if clean(row.get("temporal_stability_grade")))
        profiles[key] = {
            "temporal_score": sum(scores) / len(scores) if scores else 0.0,
            "temporal_grade": grades.most_common(1)[0][0] if grades else "",
        }
    return profiles


def blocker_after(old_blocker: str, new_confidence: float, split_depth: float, reconstruction_delta: float, physics_delta: float) -> str:
    old = upper(old_blocker)
    if new_confidence >= 72 and split_depth >= 80:
        return "OK_CONFIDENCE_IMPROVED"
    if old == "WEAK_PHASE_CONFIDENCE" and new_confidence >= 55:
        return "PHASE_CONFIDENCE_REPAIRED_PARTIAL"
    if old == "LOW_SPLIT_COMPLETENESS" and split_depth >= 80:
        return "SPLIT_COMPLETENESS_REPAIRED"
    if old == "UNSAFE_RECONSTRUCTION_RISK" and reconstruction_delta < -20:
        return "RECONSTRUCTION_RISK_REDUCED"
    if old == "WEAK_PHYSICS_CONSISTENCY" and physics_delta > 15:
        return "PHYSICS_CONSISTENCY_IMPROVED"
    return old or "UNKNOWN"


def calculate_row(
    quality_row: dict[str, str],
    ladder_profile: dict[str, object] | None,
    parser_profile: dict[str, object] | None,
    temporal_profile: dict[str, object] | None,
) -> dict[str, object]:
    old_confidence = parse_float(quality_row.get("phase_confidence_score"))
    old_physics = parse_float(quality_row.get("physics_consistency_score"))
    old_reconstruction = parse_float(quality_row.get("reconstruction_risk_score"))
    split_depth = parse_float(ladder_profile.get("split_depth_score") if ladder_profile else "")
    schema_confidence = parse_float(parser_profile.get("schema_confidence") if parser_profile else "")
    horse_timing = parse_float(parser_profile.get("horse_level_timing_score") if parser_profile else "")
    temporal_score = parse_float(temporal_profile.get("temporal_score") if temporal_profile else "")

    timing_lineage = 0.0
    if parser_profile:
        extraction_status = upper(parser_profile.get("extraction_status"))
        if extraction_status == "FULL_SPLIT_LADDER_EXTRACTED":
            timing_lineage = 92.0
        elif extraction_status == "PARTIAL_SPLIT_LADDER_EXTRACTED":
            timing_lineage = 70.0
        elif extraction_status == "HORSE_LEVEL_TIMING_EXTRACTED":
            timing_lineage = 52.0
        else:
            timing_lineage = 26.0
    if ladder_profile and split_depth >= 80:
        timing_lineage = max(timing_lineage, 88.0)

    phase_integrity = min(100.0, (split_depth * 0.34) + (timing_lineage * 0.26) + (horse_timing * 0.18) + (schema_confidence * 0.14) + (temporal_score * 0.08))
    new_confidence = max(old_confidence, min(100.0, old_confidence * 0.35 + phase_integrity * 0.65))
    physics_delta = max(0.0, phase_integrity - old_physics)
    reconstruction_delta = -min(old_reconstruction, (split_depth * 0.38 + timing_lineage * 0.22)) if split_depth or timing_lineage else 0.0
    unsafe = upper(quality_row.get("source_quality_grade")) == "F" and not ladder_profile and not parser_profile
    grade = grade_from_score(new_confidence, unsafe=unsafe)
    after_blocker = blocker_after(quality_row.get("quality_blocker"), new_confidence, split_depth, reconstruction_delta, physics_delta)
    improved = new_confidence - old_confidence
    if improved >= 20:
        improvement_status = "MATERIAL_CONFIDENCE_IMPROVEMENT"
    elif improved >= 7:
        improvement_status = "MODEST_CONFIDENCE_IMPROVEMENT"
    elif parser_profile or ladder_profile:
        improvement_status = "PAYLOAD_LINKED_NO_MAJOR_UPLIFT"
    else:
        improvement_status = "NO_NEW_PAYLOAD_MATCH"

    return {
        "race_date": clean(quality_row.get("race_date")),
        "track": clean(quality_row.get("track")),
        "race_no": clean(quality_row.get("race_no")),
        "horse": clean(quality_row.get("horse")),
        "source_file": clean(quality_row.get("source_file") or (parser_profile or {}).get("payload_source")),
        "old_phase_confidence": f"{old_confidence:.2f}",
        "new_phase_confidence": f"{new_confidence:.2f}",
        "split_depth_score": f"{split_depth:.2f}",
        "timing_lineage_score": f"{timing_lineage:.2f}",
        "horse_level_timing_score": f"{horse_timing:.2f}",
        "physics_consistency_delta": f"{physics_delta:.2f}",
        "reconstruction_dependency_delta": f"{reconstruction_delta:.2f}",
        "phase_integrity_score": f"{phase_integrity:.2f}",
        "temporal_research_grade": grade,
        "temporal_research_label": GRADE_LABEL[grade],
        "quality_blocker_before": upper(quality_row.get("quality_blocker")) or "UNKNOWN",
        "quality_blocker_after": after_blocker,
        "improvement_status": improvement_status,
        "trusted_for_live_modelling": "NO",
        "trusted_for_live_execution": "NO",
        "notes": "Offline enhanced phase confidence research only. No predictions, overlays, live modelling, ratings, or execution.",
    }


def synthetic_quality_from_parser(key: str, parser_profile: dict[str, object], ladder_profile: dict[str, object] | None) -> dict[str, str]:
    parts = key.split("|")
    return {
        "race_date": parts[0] if len(parts) > 0 else "",
        "track": parts[1] if len(parts) > 1 else "",
        "race_no": parts[2] if len(parts) > 2 else "",
        "horse": parts[3] if len(parts) > 3 else "",
        "source_file": clean(parser_profile.get("payload_source")),
        "phase_confidence_score": "0",
        "physics_consistency_score": "0",
        "reconstruction_risk_score": "0",
        "source_quality_grade": "",
        "quality_blocker": "NEW_RAW_PAYLOAD_SCHEMA",
    }


def build_rows() -> list[dict[str, object]]:
    ladder_profiles = build_ladder_profiles(read_csv(LADDERS))
    parser_profiles = build_parser_profiles(read_csv(PARSER))
    temporal_profiles = build_temporal_profiles(read_csv(TEMPORAL), read_csv(VALIDATION))
    quality_rows = read_csv(QUALITY)

    rows: list[dict[str, object]] = []
    seen_keys = set()
    for quality_row in quality_rows:
        key = race_key(quality_row)
        seen_keys.add(key)
        rows.append(calculate_row(quality_row, ladder_profiles.get(key), parser_profiles.get(key), temporal_profiles.get(key)))

    for key, parser_profile in parser_profiles.items():
        if key in seen_keys:
            continue
        if upper(parser_profile.get("extraction_status")) not in {"FULL_SPLIT_LADDER_EXTRACTED", "HORSE_LEVEL_TIMING_EXTRACTED", "PARTIAL_SPLIT_LADDER_EXTRACTED"}:
            continue
        rows.append(calculate_row(synthetic_quality_from_parser(key, parser_profile, ladder_profiles.get(key)), ladder_profiles.get(key), parser_profile, temporal_profiles.get(key)))

    rows.sort(key=lambda row: (-parse_float(row.get("new_phase_confidence")), clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no")), clean(row.get("horse"))))
    return rows


def build_improvement(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    before_weak = sum(1 for row in rows if parse_float(row.get("old_phase_confidence")) < 40 or upper(row.get("quality_blocker_before")) == "WEAK_PHASE_CONFIDENCE")
    after_weak = sum(1 for row in rows if parse_float(row.get("new_phase_confidence")) < 40 or upper(row.get("quality_blocker_after")) == "WEAK_PHASE_CONFIDENCE")
    before_unsafe_recon = sum(1 for row in rows if upper(row.get("quality_blocker_before")) == "UNSAFE_RECONSTRUCTION_RISK")
    after_unsafe_recon = sum(1 for row in rows if upper(row.get("quality_blocker_after")) == "UNSAFE_RECONSTRUCTION_RISK")
    before_low_split = sum(1 for row in rows if upper(row.get("quality_blocker_before")) == "LOW_SPLIT_COMPLETENESS")
    after_low_split = sum(1 for row in rows if upper(row.get("quality_blocker_after")) == "LOW_SPLIT_COMPLETENESS")
    material = sum(1 for row in rows if upper(row.get("improvement_status")) == "MATERIAL_CONFIDENCE_IMPROVEMENT")
    modest = sum(1 for row in rows if upper(row.get("improvement_status")) == "MODEST_CONFIDENCE_IMPROVEMENT")

    def row(name: str, before: int, after: int, notes: str) -> dict[str, object]:
        delta = after - before
        rate = ((before - after) / before * 100.0) if before else 0.0
        return {
            "improvement_type": name,
            "before_count": before,
            "after_count": after,
            "delta": delta,
            "improvement_rate": f"{rate:.2f}",
            "notes": notes,
        }

    return [
        row("WEAK_PHASE_CONFIDENCE_REDUCTION", before_weak, after_weak, "Counts rows below confidence threshold or still carrying WEAK_PHASE_CONFIDENCE."),
        row("UNSAFE_RECONSTRUCTION_RISK_REDUCTION", before_unsafe_recon, after_unsafe_recon, "Counts rows still blocked by unsafe reconstruction risk after direct split/timing linkage."),
        row("LOW_SPLIT_COMPLETENESS_REDUCTION", before_low_split, after_low_split, "Counts rows still blocked by low split completeness after extracted ladders."),
        {"improvement_type": "MATERIAL_CONFIDENCE_IMPROVEMENT_ROWS", "before_count": 0, "after_count": material, "delta": material, "improvement_rate": "", "notes": "Rows with new confidence at least 20 points above old confidence."},
        {"improvement_type": "MODEST_CONFIDENCE_IMPROVEMENT_ROWS", "before_count": 0, "after_count": modest, "delta": modest, "improvement_rate": "", "notes": "Rows with new confidence 7-19.99 points above old confidence."},
    ]


def build_summary(rows: list[dict[str, object]], improvement_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grades = Counter(upper(row.get("temporal_research_grade")) for row in rows)
    statuses = Counter(upper(row.get("improvement_status")) for row in rows)
    avg_old = sum(parse_float(row.get("old_phase_confidence")) for row in rows) / len(rows) if rows else 0.0
    avg_new = sum(parse_float(row.get("new_phase_confidence")) for row in rows) / len(rows) if rows else 0.0
    split_linked = sum(1 for row in rows if parse_float(row.get("split_depth_score")) > 0)
    horse_timing = sum(1 for row in rows if parse_float(row.get("horse_level_timing_score")) > 0)
    summary = [
        {"metric": "enhanced_rows", "value": len(rows)},
        {"metric": "avg_old_phase_confidence", "value": f"{avg_old:.2f}"},
        {"metric": "avg_new_phase_confidence", "value": f"{avg_new:.2f}"},
        {"metric": "avg_confidence_delta", "value": f"{avg_new - avg_old:.2f}"},
        {"metric": "split_ladder_linked_rows", "value": split_linked},
        {"metric": "horse_level_timing_linked_rows", "value": horse_timing},
        {"metric": "grade_A_high_confidence", "value": grades.get("A", 0)},
        {"metric": "grade_B_strong", "value": grades.get("B", 0)},
        {"metric": "grade_C_usable", "value": grades.get("C", 0)},
        {"metric": "grade_D_weak", "value": grades.get("D", 0)},
        {"metric": "grade_F_unsafe", "value": grades.get("F", 0)},
        {"metric": "material_confidence_improvements", "value": statuses.get("MATERIAL_CONFIDENCE_IMPROVEMENT", 0)},
        {"metric": "modest_confidence_improvements", "value": statuses.get("MODEST_CONFIDENCE_IMPROVEMENT", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for row in improvement_rows:
        summary.append({"metric": f"improvement::{row['improvement_type']}", "value": row.get("delta")})
    return summary


def main() -> None:
    rows = build_rows()
    improvement_rows = build_improvement(rows)
    summary_rows = build_summary(rows, improvement_rows)
    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv(IMPROVEMENT, improvement_rows, IMPROVEMENT_FIELDS)

    print("=" * 88)
    print("EDGEIQ ENHANCED TEMPORAL PHASE CONFIDENCE V2")
    print("=" * 88)
    for row in summary_rows[:16]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {IMPROVEMENT}")


if __name__ == "__main__":
    main()
