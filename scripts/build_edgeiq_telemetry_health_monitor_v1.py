from __future__ import annotations

import csv
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LINEAGE = DATA / "edgeiq_timing_lineage_validation_v1.csv"
LADDERS = DATA / "edgeiq_raw_sectional_extracted_split_ladders_v1.csv"
ENHANCED = DATA / "edgeiq_enhanced_temporal_phase_confidence_v2.csv"
QUALITY = DATA / "edgeiq_sectional_payload_quality_v1.csv"
SHADOW_LOOP = DATA / "edgeiq_shadow_research_loop_v1.csv"

OUT = DATA / "edgeiq_telemetry_health_monitor_v1.csv"
SUMMARY = DATA / "edgeiq_telemetry_health_summary_v1.csv"
WATCHLIST = DATA / "edgeiq_telemetry_drift_watchlist_v1.csv"

OUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "payload_source",
    "telemetry_health_score",
    "lineage_integrity_score",
    "schema_stability_score",
    "split_completeness_score",
    "phase_confidence_score",
    "telemetry_consistency_score",
    "payload_drift_detected",
    "schema_drift_detected",
    "degradation_warning",
    "telemetry_grade",
    "telemetry_status",
    "safe_for_temporal_research",
    "safe_for_shadow_research",
    "recommended_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

WATCHLIST_FIELDS = [
    "drift_type",
    "affected_track",
    "affected_source",
    "affected_rows",
    "severity",
    "detected_issue",
    "recommended_repair",
    "priority",
    "notes",
]

GRADE_LABEL = {
    "A": "ELITE_TELEMETRY_HEALTH",
    "B": "STABLE_TELEMETRY_HEALTH",
    "C": "USABLE_TELEMETRY_HEALTH",
    "D": "DEGRADED_TELEMETRY_HEALTH",
    "F": "UNSTABLE_TELEMETRY_HEALTH",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def normalise_track(value: object) -> str:
    text = upper(value)
    text = text.replace("&", " AND ")
    text = re.sub(r"\b(RACECOURSE|RACING|CLUB|TRACK|PARK)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    aliases = {
        "CAULFIELD HEATH": "CAULFIELD",
        "LADBROKES PARK": "SANDOWN",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
        "THE VALLEY": "MOONEE VALLEY",
        "M V": "MOONEE VALLEY",
    }
    return aliases.get(text, text)


def normalise_horse(value: object) -> str:
    text = upper(value)
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10]


def normalise_race_no(value: object) -> str:
    text = upper(value)
    match = re.search(r"(\d+)", text)
    return match.group(1) if match else text


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        normalise_date(row.get("race_date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        normalise_horse(row.get("horse")),
    )


def source_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return runner_key(row) + (clean(row.get("payload_source") or row.get("source_file")),)


def parse_float(value: object, default: float = 0.0) -> float:
    text = clean(value).replace("%", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def yes(value: object) -> bool:
    return upper(value) == "YES"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".tmp.{int(time.time() * 1000)}")
    with temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    temp.replace(path)


def score_from_grade(grade: str) -> float:
    return {"A": 94.0, "B": 84.0, "C": 72.0, "D": 52.0, "F": 22.0}.get(upper(grade), 50.0)


def build_ladder_index(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str, str, str, str], dict[str, object]], dict[tuple[str, str, str, str], list[dict[str, object]]]]:
    by_source: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    by_runner: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[source_key(row)].append(row)

    for key, group in grouped.items():
        split_markers = {upper(row.get("split_marker")) for row in group if clean(row.get("split_marker"))}
        schemas = {clean(row.get("schema_type")) for row in group if clean(row.get("schema_type"))}
        statuses = {upper(row.get("extraction_status")) for row in group if clean(row.get("extraction_status"))}
        numeric_count = 0
        phase_fields_present = 0
        confidences: list[float] = []
        for row in group:
            for field in ("split_time", "sectional_time", "cumulative_time"):
                if parse_float(row.get(field)) > 0:
                    numeric_count += 1
            phase_fields_present += sum(1 for field in ("early_phase_value", "mid_phase_value", "late_phase_value") if parse_float(row.get(field)) > 0)
            if clean(row.get("schema_confidence")):
                confidences.append(parse_float(row.get("schema_confidence")))
        schema_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        record = {
            "split_count": len(split_markers),
            "usable_numeric_count": numeric_count,
            "schema_count": len(schemas),
            "schema_types": "|".join(sorted(schemas)),
            "status_count": len(statuses),
            "statuses": "|".join(sorted(statuses)),
            "phase_fields_present": phase_fields_present,
            "schema_confidence": schema_confidence,
        }
        by_source[key] = record
        by_runner[key[:4]].append(record)
    return by_source, by_runner


def build_best_index(rows: list[dict[str, str]], score_fields: list[str]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    best: dict[tuple[str, str, str, str], dict[str, str]] = {}
    best_score: dict[tuple[str, str, str, str], float] = defaultdict(float)
    for row in rows:
        key = runner_key(row)
        score = max([parse_float(row.get(field)) for field in score_fields] or [0.0])
        if key not in best or score >= best_score[key]:
            best[key] = row
            best_score[key] = score
    return best


def build_quality_indexes(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str, str, str, str], dict[str, str]], dict[tuple[str, str, str, str], dict[str, str]]]:
    by_source: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    by_runner: dict[tuple[str, str, str, str], dict[str, str]] = {}
    runner_score: dict[tuple[str, str, str, str], float] = defaultdict(float)
    for row in rows:
        skey = source_key(row)
        rkey = runner_key(row)
        quality_score = score_from_grade(row.get("source_quality_grade", "")) + parse_float(row.get("phase_confidence_score")) * 0.05
        by_source[skey] = row
        if rkey not in by_runner or quality_score >= runner_score[rkey]:
            by_runner[rkey] = row
            runner_score[rkey] = quality_score
    return by_source, by_runner


def shadow_health(rows: list[dict[str, str]]) -> dict[str, float]:
    if not rows:
        return {"global": 70.0}
    scores = []
    for row in rows:
        base = parse_float(row.get("environment_health_score"), 50.0)
        classification = upper(row.get("loop_classification"))
        if classification == "ACTIVE_STABLE_RESEARCH":
            base += 8.0
        elif classification in {"DECAYING_RESEARCH", "REGIME_DRIFT_WARNING"}:
            base -= 15.0
        elif classification == "RETIRED_RESEARCH_ENVIRONMENT":
            base -= 25.0
        scores.append(max(0.0, min(100.0, base)))
    return {"global": sum(scores) / len(scores)}


def split_completeness_score(ladder: dict[str, object], quality: dict[str, str]) -> float:
    if ladder:
        split_count = int(ladder.get("split_count") or 0)
        numeric_count = int(ladder.get("usable_numeric_count") or 0)
        phase_fields = int(ladder.get("phase_fields_present") or 0)
        score = min(100.0, split_count * 24.0 + min(24.0, numeric_count * 2.0) + min(18.0, phase_fields * 2.0))
        return max(score, parse_float(quality.get("payload_completeness_score")) if quality else 0.0)
    return parse_float(quality.get("payload_completeness_score")) if quality else 0.0


def schema_stability_score(lineage: dict[str, str], ladder: dict[str, object]) -> float:
    base = parse_float(lineage.get("schema_consistency_score"))
    if ladder:
        schema_conf = float(ladder.get("schema_confidence") or 0.0)
        schema_count = int(ladder.get("schema_count") or 0)
        status_count = int(ladder.get("status_count") or 0)
        base = max(base, schema_conf)
        if schema_count > 1:
            base -= min(20.0, (schema_count - 1) * 7.5)
        if status_count > 1:
            base -= min(12.0, (status_count - 1) * 5.0)
    return max(0.0, min(100.0, base))


def phase_confidence_score(enhanced: dict[str, str], quality: dict[str, str]) -> float:
    enhanced_score = parse_float(enhanced.get("new_phase_confidence"))
    quality_score = parse_float(quality.get("phase_confidence_score"))
    if enhanced_score and quality_score:
        return max(enhanced_score, quality_score)
    return enhanced_score or quality_score


def lineage_integrity_score(lineage: dict[str, str]) -> float:
    integrity = parse_float(lineage.get("timing_chain_integrity"))
    direct = parse_float(lineage.get("direct_source_confidence"))
    grade_score = score_from_grade(lineage.get("lineage_trust_grade"))
    score = integrity * 0.45 + direct * 0.35 + grade_score * 0.20
    dependency = upper(lineage.get("reconstruction_dependency"))
    if dependency == "HIGH":
        score -= 18.0
    elif dependency == "MEDIUM":
        score -= 6.0
    if yes(lineage.get("duplicate_lineage_detected")):
        score -= 10.0
    if yes(lineage.get("conflicting_timing_detected")):
        score -= 25.0
    return max(0.0, min(100.0, score))


def telemetry_consistency(lineage: dict[str, str], enhanced: dict[str, str], quality: dict[str, str], shadow_score: float) -> float:
    quality_grade_score = score_from_grade(quality.get("source_quality_grade", "")) if quality else 65.0
    physics = parse_float(quality.get("physics_consistency_score"), quality_grade_score) if quality else quality_grade_score
    enhanced_grade = score_from_grade(enhanced.get("temporal_research_grade", "")) if enhanced else 65.0
    score = quality_grade_score * 0.30 + physics * 0.25 + enhanced_grade * 0.20 + shadow_score * 0.10 + 15.0
    blocker = upper(quality.get("quality_blocker")) if quality else ""
    if blocker in {"UNSAFE_RECONSTRUCTION_RISK", "WEAK_PHYSICS_CONSISTENCY"}:
        score -= 15.0
    elif blocker in {"WEAK_PHASE_CONFIDENCE", "LOW_SPLIT_COMPLETENESS"}:
        score -= 8.0
    if yes(lineage.get("conflicting_timing_detected")):
        score -= 25.0
    return max(0.0, min(100.0, score))


def grade_health(score: float, payload_drift: bool, schema_drift: bool, degradation: bool) -> str:
    if score >= 90 and not payload_drift and not schema_drift and not degradation:
        return "A"
    if score >= 80 and not schema_drift and not degradation:
        return "B"
    if score >= 65 and not (payload_drift and schema_drift):
        return "C"
    if score >= 45:
        return "D"
    return "F"


def recommended_action(grade: str, payload_drift: bool, schema_drift: bool, degradation: bool, quality: dict[str, str]) -> str:
    blocker = upper(quality.get("quality_blocker")) if quality else ""
    if grade in {"A", "B"}:
        return "Continue telemetry monitoring; preserve direct lineage and schema contract."
    if schema_drift:
        return "Review extracted schema variants and lock canonical timing ladder mapping."
    if payload_drift:
        return "Backfill fuller split ladders or direct-source payloads for degraded telemetry rows."
    if blocker:
        return f"Repair payload blocker: {blocker}."
    if degradation:
        return "Quarantine degraded telemetry from shadow research until lineage and phase confidence improve."
    return "Continue offline observation; no live modelling or execution."


def main() -> None:
    lineage_rows = read_csv(LINEAGE)
    ladder_rows = read_csv(LADDERS)
    enhanced_rows = read_csv(ENHANCED)
    quality_rows = read_csv(QUALITY)
    shadow_rows = read_csv(SHADOW_LOOP)

    ladder_by_source, ladder_by_runner = build_ladder_index(ladder_rows)
    enhanced_by_runner = build_best_index(enhanced_rows, ["new_phase_confidence", "phase_integrity_score", "timing_lineage_score"])
    quality_by_source, quality_by_runner = build_quality_indexes(quality_rows)
    shadow = shadow_health(shadow_rows)

    out_rows: list[dict[str, object]] = []
    drift_counter: Counter[tuple[str, str, str]] = Counter()
    issue_notes: dict[tuple[str, str, str], str] = {}

    for lineage in lineage_rows:
        rkey = runner_key(lineage)
        skey = source_key(lineage)
        ladder = ladder_by_source.get(skey) or (ladder_by_runner.get(rkey, [{}])[0] if ladder_by_runner.get(rkey) else {})
        enhanced = enhanced_by_runner.get(rkey, {})
        quality = quality_by_source.get(skey) or quality_by_runner.get(rkey, {})

        lineage_score = lineage_integrity_score(lineage)
        schema_score = schema_stability_score(lineage, ladder)
        split_score = split_completeness_score(ladder, quality)
        phase_score = phase_confidence_score(enhanced, quality)
        consistency_score = telemetry_consistency(lineage, enhanced, quality, shadow["global"])
        health = (
            lineage_score * 0.28
            + schema_score * 0.20
            + split_score * 0.18
            + phase_score * 0.20
            + consistency_score * 0.14
        )

        blocker = upper(quality.get("quality_blocker")) if quality else ""
        quality_grade = upper(quality.get("source_quality_grade")) if quality else ""
        payload_drift = blocker in {"UNSAFE_RECONSTRUCTION_RISK", "WEAK_PHASE_CONFIDENCE", "LOW_SPLIT_COMPLETENESS", "WEAK_PHYSICS_CONSISTENCY"} or quality_grade in {"D", "F"}
        schema_count = int(ladder.get("schema_count") or 0) if ladder else 0
        schema_drift = schema_score < 70 or schema_count > 1 or yes(lineage.get("conflicting_timing_detected"))
        degradation = health < 65 or phase_score < 45 or consistency_score < 55 or split_score < 45
        grade = grade_health(health, payload_drift, schema_drift, degradation)
        temporal_safe = "YES" if grade in {"A", "B", "C"} and not schema_drift and yes(lineage.get("safe_for_temporal_research")) else "NO"
        shadow_safe = "YES" if grade in {"A", "B"} and not payload_drift and not schema_drift and yes(lineage.get("safe_for_shadow_research")) else "NO"

        source = clean(lineage.get("payload_source"))
        track = clean(lineage.get("track"))
        if payload_drift:
            key = ("PAYLOAD_DRIFT", track, source)
            drift_counter[key] += 1
            issue_notes[key] = blocker or "Payload quality degraded versus lineage trust."
        if schema_drift:
            key = ("SCHEMA_DRIFT", track, source)
            drift_counter[key] += 1
            issue_notes[key] = "Schema consistency below threshold or multiple schema variants detected."
        if degradation:
            key = ("TELEMETRY_DEGRADATION", track, source)
            drift_counter[key] += 1
            issue_notes[key] = "Composite telemetry health degraded."

        out_rows.append(
            {
                "race_date": clean(lineage.get("race_date")),
                "track": track,
                "race_no": clean(lineage.get("race_no")),
                "horse": clean(lineage.get("horse")),
                "payload_source": source,
                "telemetry_health_score": f"{max(0.0, min(100.0, health)):.2f}",
                "lineage_integrity_score": f"{lineage_score:.2f}",
                "schema_stability_score": f"{schema_score:.2f}",
                "split_completeness_score": f"{split_score:.2f}",
                "phase_confidence_score": f"{phase_score:.2f}",
                "telemetry_consistency_score": f"{consistency_score:.2f}",
                "payload_drift_detected": "YES" if payload_drift else "NO",
                "schema_drift_detected": "YES" if schema_drift else "NO",
                "degradation_warning": "YES" if degradation else "NO",
                "telemetry_grade": grade,
                "telemetry_status": GRADE_LABEL[grade],
                "safe_for_temporal_research": temporal_safe,
                "safe_for_shadow_research": shadow_safe,
                "recommended_action": recommended_action(grade, payload_drift, schema_drift, degradation, quality),
                "notes": "Offline telemetry health governance only. No predictions, overlays, live modelling, ratings, or execution.",
            }
        )

    out_rows.sort(key=lambda row: (clean(row.get("telemetry_grade")), clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no")), clean(row.get("horse"))))

    watch_rows: list[dict[str, object]] = []
    for (drift_type, track, source), count in drift_counter.most_common():
        severity = "HIGH" if count >= 250 else "MEDIUM" if count >= 50 else "LOW"
        priority = "HIGH" if drift_type in {"SCHEMA_DRIFT", "TELEMETRY_DEGRADATION"} and severity != "LOW" else "MEDIUM" if severity != "LOW" else "LOW"
        repair = {
            "PAYLOAD_DRIFT": "Acquire fuller direct split ladders and repair weak phase extraction before shadow use.",
            "SCHEMA_DRIFT": "Audit schema parser mapping and lock canonical split-ladder contract for this source.",
            "TELEMETRY_DEGRADATION": "Quarantine affected telemetry rows from shadow research until health score recovers.",
        }.get(drift_type, "Review telemetry lineage.")
        watch_rows.append(
            {
                "drift_type": drift_type,
                "affected_track": track,
                "affected_source": source,
                "affected_rows": count,
                "severity": severity,
                "detected_issue": issue_notes.get((drift_type, track, source), drift_type),
                "recommended_repair": repair,
                "priority": priority,
                "notes": "Telemetry drift watchlist is offline research governance only; no live modelling or execution.",
            }
        )

    grades = Counter(clean(row.get("telemetry_grade")) for row in out_rows)
    statuses = Counter(clean(row.get("telemetry_status")) for row in out_rows)
    summary_rows: list[dict[str, object]] = [
        {"metric": "telemetry_rows", "value": len(out_rows)},
        {"metric": "elite_health_rows", "value": grades.get("A", 0)},
        {"metric": "stable_health_rows", "value": grades.get("B", 0)},
        {"metric": "usable_health_rows", "value": grades.get("C", 0)},
        {"metric": "degraded_health_rows", "value": grades.get("D", 0)},
        {"metric": "unstable_health_rows", "value": grades.get("F", 0)},
        {"metric": "payload_drift_rows", "value": sum(1 for row in out_rows if row.get("payload_drift_detected") == "YES")},
        {"metric": "schema_drift_rows", "value": sum(1 for row in out_rows if row.get("schema_drift_detected") == "YES")},
        {"metric": "degradation_warning_rows", "value": sum(1 for row in out_rows if row.get("degradation_warning") == "YES")},
        {"metric": "safe_for_temporal_research_yes", "value": sum(1 for row in out_rows if row.get("safe_for_temporal_research") == "YES")},
        {"metric": "safe_for_shadow_research_yes", "value": sum(1 for row in out_rows if row.get("safe_for_shadow_research") == "YES")},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "drift_watchlist_rows", "value": len(watch_rows)},
    ]
    for status, count in statuses.most_common():
        summary_rows.append({"metric": f"telemetry_status::{status}", "value": count})
    for path in (LINEAGE, LADDERS, ENHANCED, QUALITY, SHADOW_LOOP):
        if not path.exists():
            summary_rows.append({"metric": f"missing_input::{path.name}", "value": "YES"})

    write_csv(OUT, out_rows, OUT_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv(WATCHLIST, watch_rows, WATCHLIST_FIELDS)

    print("=" * 88)
    print("EDGEIQ TELEMETRY HEALTH MONITOR V1")
    print("=" * 88)
    for row in summary_rows[:15]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {WATCHLIST}")


if __name__ == "__main__":
    main()
