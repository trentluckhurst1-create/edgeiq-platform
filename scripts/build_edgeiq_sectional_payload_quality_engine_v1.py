from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "features": DATA / "edgeiq_real_sectional_physics_features_v1.csv",
    "temporal": DATA / "edgeiq_temporal_physics_engine_v1.csv",
    "reconstruction": DATA / "edgeiq_sectional_payload_reconstruction_v1.csv",
    "physics_validation": DATA / "edgeiq_sectional_physics_validation_v1.csv",
    "shadow_state": DATA / "edgeiq_shadow_environment_state_v1.csv",
}

OUT = DATA / "edgeiq_sectional_payload_quality_v1.csv"
SUMMARY = DATA / "edgeiq_sectional_payload_quality_summary_v1.csv"
BACKLOG = DATA / "edgeiq_sectional_payload_quality_backlog_v1.csv"

OUT_FIELDS = [
    "source_file",
    "race_date",
    "track",
    "race_no",
    "horse",
    "split_count",
    "usable_numeric_count",
    "payload_completeness_score",
    "physics_consistency_score",
    "phase_confidence_score",
    "reconstruction_risk_score",
    "source_quality_grade",
    "source_quality_label",
    "safe_for_temporal_research",
    "safe_for_shadow_research",
    "quality_blocker",
    "recommended_repair",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

BACKLOG_FIELDS = [
    "priority",
    "quality_blocker",
    "affected_rows",
    "recommended_repair",
    "target_source",
    "notes",
]

TRACK_ALIASES = {
    "THE VALLEY": "MOONEE VALLEY",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
}

GRADE_LABELS = {
    "A": "HIGH_TRUST_REAL_SECTIONAL_PAYLOAD",
    "B": "USABLE_SECTIONAL_PAYLOAD",
    "C": "PARTIAL_SECTIONAL_PAYLOAD",
    "D": "DEGRADED_SECTIONAL_PAYLOAD",
    "F": "UNSAFE_SECTIONAL_PAYLOAD",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("&", " AND ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"['`’‘]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bRACING\b|\bCLUB\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return TRACK_ALIASES.get(track, track)


def normalise_date(value: object) -> str:
    text = clean(value).replace("/", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    return text[:10]


def normalise_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def runner_key(row: dict[str, object]) -> str:
    race_date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = normalise_text(row.get("horse"))
    return f"{race_date}|{track}|{race_no}|{horse}" if race_date and track and race_no and horse else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def to_int(value: object) -> int:
    try:
        return int(float(clean(value)))
    except ValueError:
        return 0


def to_float(value: object) -> float:
    try:
        return float(clean(value))
    except ValueError:
        return math.nan


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1"}


def score_grade(value: str) -> float:
    return {"A": 100.0, "B": 82.0, "C": 62.0, "D": 38.0, "F": 12.0}.get(clean(value).upper(), 35.0)


def fmt(value: float) -> str:
    if math.isnan(value):
        return "0.00"
    return f"{max(0.0, min(100.0, value)):.2f}"


def first_by_key(path_name: str) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in read_csv(INPUTS[path_name]):
        key = runner_key(row)
        if key and key not in index:
            index[key] = row
    return index


def shadow_active_phases() -> set[str]:
    phases: set[str] = set()
    for row in read_csv(INPUTS["shadow_state"]):
        if clean(row.get("current_status")) == "ACTIVE_STABLE_RESEARCH":
            phase = clean(row.get("phase_transition_pattern"))
            if phase:
                phases.add(phase)
    return phases


def payload_completeness(split_count: int, usable_count: int, feature_row: dict[str, str]) -> float:
    split_component = min(45.0, (split_count / 16.0) * 45.0)
    usable_component = min(35.0, (usable_count / 16.0) * 35.0)
    phase_fields = ["early_phase_value", "mid_phase_value", "late_phase_value"]
    phase_present = sum(1 for field in phase_fields if clean(feature_row.get(field)))
    phase_component = (phase_present / 3.0) * 20.0
    return split_component + usable_component + phase_component


def physics_consistency(feature_row: dict[str, str], physics_row: dict[str, str]) -> float:
    measured = score_grade(clean(feature_row.get("measured_physics_grade")))
    validation_grade = score_grade(clean(physics_row.get("physics_grade")))
    confidence = to_float(physics_row.get("physics_confidence"))
    if math.isnan(confidence):
        confidence = 35.0
    valid_bonus = 10.0 if yes(physics_row.get("physics_valid")) else -18.0
    velocity = to_float(physics_row.get("velocity_integrity"))
    fatigue = to_float(physics_row.get("fatigue_integrity"))
    split = to_float(physics_row.get("split_integrity"))
    integrity_values = [value for value in [velocity, fatigue, split] if not math.isnan(value)]
    integrity = sum(integrity_values) / len(integrity_values) if integrity_values else 35.0
    return max(0.0, min(100.0, (measured * 0.28) + (validation_grade * 0.24) + (confidence * 0.22) + (integrity * 0.18) + valid_bonus))


def phase_confidence(feature_row: dict[str, str], temporal_row: dict[str, str]) -> float:
    temporal_grade = score_grade(clean(temporal_row.get("temporal_stability_grade")))
    temporal_score = to_float(temporal_row.get("temporal_physics_score"))
    if math.isnan(temporal_score):
        temporal_score = score_grade(clean(feature_row.get("measured_physics_grade")))
    volatility = to_float(feature_row.get("sectional_volatility"))
    volatility_penalty = 0.0 if math.isnan(volatility) else min(35.0, max(0.0, volatility - 20.0))
    missing_phase_penalty = 12.0 * sum(1 for field in ["early_phase_value", "mid_phase_value", "late_phase_value"] if not clean(feature_row.get(field)))
    return max(0.0, min(100.0, (temporal_grade * 0.55) + (temporal_score * 0.45) - volatility_penalty - missing_phase_penalty))


def reconstruction_risk(feature_row: dict[str, str], recon_row: dict[str, str], physics_row: dict[str, str]) -> float:
    risk = 0.0
    source = clean(feature_row.get("source_file")).lower()
    if "reconstruction" in source:
        risk += 22.0
    if yes(recon_row.get("payload_repaired")):
        risk += 18.0
    if yes(recon_row.get("unsafe_reconstruction")):
        risk += 45.0
    method = clean(recon_row.get("reconstruction_method"))
    if method in {"UNSAFE", "NONE"}:
        risk += 35.0
    elif method in {"PARTIAL_RECOVERY", "DERIVED_CUMULATIVE", "DERIVED_INCREMENTAL"}:
        risk += 12.0
    confidence = to_float(recon_row.get("reconstruction_confidence"))
    if not math.isnan(confidence):
        risk += max(0.0, 60.0 - confidence) * 0.45
    if clean(physics_row.get("physics_grade")) == "BROKEN":
        risk += 30.0
    return max(0.0, min(100.0, risk))


def blocker_and_repair(completeness: float, consistency: float, phase: float, risk: float, feature_row: dict[str, str], recon_row: dict[str, str]) -> tuple[str, str]:
    missing_phases = [field for field in ["early_phase_value", "mid_phase_value", "late_phase_value"] if not clean(feature_row.get(field))]
    if missing_phases:
        return "MISSING_PHASE_VALUES", "Backfill source splits needed for early/mid/late temporal phases."
    if completeness < 45:
        return "LOW_SPLIT_COMPLETENESS", "Recover fuller split ladders or exclude from temporal research."
    if risk >= 75:
        return "UNSAFE_RECONSTRUCTION_RISK", "Review reconstruction lineage and suppress unsafe reconstructed payloads."
    if consistency < 45:
        return "WEAK_PHYSICS_CONSISTENCY", "Repair impossible physics, split ladders, or validation confidence before research use."
    if phase < 45:
        return "WEAK_PHASE_CONFIDENCE", "Keep payload in raw evidence only until temporal phase confidence improves."
    if yes(recon_row.get("payload_repaired")):
        return "REPAIRED_PAYLOAD_REVIEW", "Keep repaired payload under shadow-only review until source lineage strengthens."
    return "OK_NO_BLOCKER", "No immediate payload quality repair required."


def classify_grade(completeness: float, consistency: float, phase: float, risk: float) -> str:
    score = (completeness * 0.32) + (consistency * 0.30) + (phase * 0.23) + ((100.0 - risk) * 0.15)
    if risk >= 85 or completeness < 25 or consistency < 25:
        return "F"
    if score >= 82 and risk < 35:
        return "A"
    if score >= 68 and risk < 55:
        return "B"
    if score >= 52 and risk < 75:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def build_rows() -> list[dict[str, object]]:
    temporal = first_by_key("temporal")
    reconstruction = first_by_key("reconstruction")
    physics = first_by_key("physics_validation")
    active_phases = shadow_active_phases()
    rows: list[dict[str, object]] = []
    for feature in read_csv(INPUTS["features"]):
        key = runner_key(feature)
        temporal_row = temporal.get(key, {})
        recon_row = reconstruction.get(key, {})
        physics_row = physics.get(key, {})
        split_count = to_int(feature.get("split_count"))
        usable_count = to_int(feature.get("usable_numeric_count"))
        completeness = payload_completeness(split_count, usable_count, feature)
        consistency = physics_consistency(feature, physics_row)
        phase_score = phase_confidence(feature, temporal_row)
        risk = reconstruction_risk(feature, recon_row, physics_row)
        grade = classify_grade(completeness, consistency, phase_score, risk)
        blocker, repair = blocker_and_repair(completeness, consistency, phase_score, risk, feature, recon_row)
        temporal_safe = "YES" if grade in {"A", "B", "C"} and blocker not in {"MISSING_PHASE_VALUES", "UNSAFE_RECONSTRUCTION_RISK"} else "NO"
        phase = clean(temporal_row.get("phase_transition_pattern"))
        shadow_safe = "YES" if temporal_safe == "YES" and grade in {"A", "B"} and phase in active_phases and risk < 50 else "NO"
        rows.append(
            {
                "source_file": clean(feature.get("source_file")),
                "race_date": normalise_date(feature.get("race_date")),
                "track": normalise_track(feature.get("track")),
                "race_no": normalise_race_no(feature.get("race_no")),
                "horse": clean(feature.get("horse")),
                "split_count": split_count,
                "usable_numeric_count": usable_count,
                "payload_completeness_score": fmt(completeness),
                "physics_consistency_score": fmt(consistency),
                "phase_confidence_score": fmt(phase_score),
                "reconstruction_risk_score": fmt(risk),
                "source_quality_grade": grade,
                "source_quality_label": GRADE_LABELS[grade],
                "safe_for_temporal_research": temporal_safe,
                "safe_for_shadow_research": shadow_safe,
                "quality_blocker": blocker,
                "recommended_repair": repair,
                "notes": "Sectional payload quality research only. No live modelling, ratings, overlays, prices, or execution.",
            }
        )
    return rows


def build_backlog(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        blocker = clean(row.get("quality_blocker"))
        if blocker and blocker != "OK_NO_BLOCKER":
            grouped[blocker].append(row)
    out: list[dict[str, object]] = []
    for blocker, items in grouped.items():
        repairs = Counter(clean(row.get("recommended_repair")) for row in items)
        sources = Counter(clean(row.get("source_file")) for row in items)
        if blocker in {"UNSAFE_RECONSTRUCTION_RISK", "MISSING_PHASE_VALUES", "WEAK_PHYSICS_CONSISTENCY"}:
            priority = "HIGH"
        elif blocker in {"LOW_SPLIT_COMPLETENESS", "WEAK_PHASE_CONFIDENCE"}:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        out.append(
            {
                "priority": priority,
                "quality_blocker": blocker,
                "affected_rows": len(items),
                "recommended_repair": repairs.most_common(1)[0][0] if repairs else "Inspect payload quality source.",
                "target_source": sources.most_common(1)[0][0] if sources else "UNKNOWN",
                "notes": "Payload quality backlog is offline research only and cannot authorise live modelling.",
            }
        )
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    out.sort(key=lambda row: (priority_order.get(str(row["priority"]), 9), -int(row["affected_rows"])))
    return out


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grades = Counter(clean(row.get("source_quality_grade")) for row in rows)
    temporal_yes = sum(1 for row in rows if clean(row.get("safe_for_temporal_research")) == "YES")
    shadow_yes = sum(1 for row in rows if clean(row.get("safe_for_shadow_research")) == "YES")
    blockers = Counter(clean(row.get("quality_blocker")) for row in rows)
    values: list[dict[str, object]] = [
        {"metric": "quality_rows", "value": len(rows)},
        {"metric": "high_trust_rows", "value": grades.get("A", 0)},
        {"metric": "usable_rows", "value": grades.get("B", 0)},
        {"metric": "partial_rows", "value": grades.get("C", 0)},
        {"metric": "degraded_rows", "value": grades.get("D", 0)},
        {"metric": "unsafe_rows", "value": grades.get("F", 0)},
        {"metric": "safe_for_temporal_research_yes", "value": temporal_yes},
        {"metric": "safe_for_shadow_research_yes", "value": shadow_yes},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for blocker, count in sorted(blockers.items()):
        values.append({"metric": f"quality_blocker::{blocker}", "value": count})
    for path in INPUTS.values():
        if not path.exists():
            values.append({"metric": f"missing_input::{path.name}", "value": "YES"})
    return values


def main() -> None:
    rows = build_rows()
    backlog = build_backlog(rows)
    summary = build_summary(rows)
    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(BACKLOG, backlog, BACKLOG_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ SECTIONAL PAYLOAD QUALITY ENGINE V1")
    print("=" * 88)
    print(f"quality rows: {len(rows)}")
    print(f"backlog rows: {len(backlog)}")
    for row in summary:
        if row["metric"] in {"high_trust_rows", "usable_rows", "partial_rows", "degraded_rows", "unsafe_rows", "safe_for_temporal_research_yes", "safe_for_shadow_research_yes", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {BACKLOG}")


if __name__ == "__main__":
    main()
