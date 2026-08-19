from __future__ import annotations

import csv
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TELEMETRY = DATA / "edgeiq_telemetry_health_monitor_v1.csv"
LINEAGE = DATA / "edgeiq_timing_lineage_validation_v1.csv"
ENHANCED = DATA / "edgeiq_enhanced_temporal_phase_confidence_v2.csv"
SHADOW_LOOP = DATA / "edgeiq_shadow_research_loop_v1.csv"
SHADOW_STATE = DATA / "edgeiq_shadow_environment_state_v1.csv"

OUT = DATA / "edgeiq_longitudinal_telemetry_accumulation_v1.csv"
SUMMARY = DATA / "edgeiq_longitudinal_telemetry_summary_v1.csv"
WATCHLIST = DATA / "edgeiq_telemetry_persistence_watchlist_v1.csv"

OUT_FIELDS = [
    "observation_date",
    "track",
    "race_class",
    "distance_bucket",
    "tempo_bucket",
    "telemetry_environment",
    "telemetry_health_score",
    "lineage_integrity_score",
    "phase_confidence_score",
    "shadow_research_status",
    "telemetry_stability_state",
    "telemetry_decay_detected",
    "persistence_strength",
    "environment_consistency",
    "longitudinal_confidence",
    "telemetry_grade",
    "safe_for_temporal_research",
    "safe_for_shadow_research",
    "recommended_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

WATCHLIST_FIELDS = [
    "watch_type",
    "affected_environment",
    "persistence_issue",
    "affected_rows",
    "severity",
    "detected_pattern",
    "recommended_repair",
    "priority",
    "notes",
]

STATE_LABELS = {
    "A": "ELITE_PERSISTENT_TELEMETRY",
    "B": "STABLE_PERSISTENT_TELEMETRY",
    "C": "USABLE_EVOLVING_TELEMETRY",
    "D": "VOLATILE_TELEMETRY",
    "F": "DEGRADING_TELEMETRY",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


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
    }
    return aliases.get(text, text)


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


def avg(values: list[float], default: float = 0.0) -> float:
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else default


def grade_score(grade: str) -> float:
    return {"A": 95.0, "B": 84.0, "C": 72.0, "D": 50.0, "F": 20.0}.get(upper(grade), 60.0)


def classify_state(
    health: float,
    lineage: float,
    phase: float,
    consistency: float,
    decay: bool,
    volatile: bool,
    shadow_status: str,
) -> str:
    status = upper(shadow_status)
    if decay or status in {"DECAYING_RESEARCH", "REGIME_DRIFT_WARNING"}:
        if health < 80 or consistency < 70:
            return "F"
        return "D"
    if volatile or consistency < 60:
        return "D"
    if health >= 90 and lineage >= 90 and phase >= 75 and consistency >= 82:
        return "A"
    if health >= 80 and lineage >= 82 and phase >= 60 and consistency >= 72:
        return "B"
    if health >= 65 and lineage >= 65 and phase >= 45:
        return "C"
    if health >= 45:
        return "D"
    return "F"


def split_environment(row: dict[str, str]) -> tuple[str, str, str, str]:
    segment_type = upper(row.get("segment_type"))
    segment_value = clean(row.get("segment_value")) or "UNKNOWN"
    track = "ALL"
    race_class = "UNKNOWN"
    distance_bucket = "UNKNOWN"
    tempo_bucket = "UNKNOWN"
    if segment_type == "TRACK":
        track = segment_value
    elif segment_type == "RACE_CLASS":
        race_class = segment_value
    elif segment_type == "DISTANCE_BUCKET":
        distance_bucket = segment_value
    elif segment_type in {"TEMPO_BUCKET", "RACE_SHAPE_LABEL"}:
        tempo_bucket = segment_value
    return track, race_class, distance_bucket, tempo_bucket


def latest_shadow_state(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_key: dict[str, dict[str, str]] = {}
    for row in rows:
        key = clean(row.get("environment_key"))
        if not key:
            continue
        current = by_key.get(key)
        current_date = clean(current.get("last_observed_date") if current else "")
        next_date = clean(row.get("last_observed_date"))
        if current is None or next_date >= current_date:
            by_key[key] = row
    return by_key


def build_track_rows(telemetry_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in telemetry_rows:
        obs_date = normalise_date(row.get("race_date"))
        track = normalise_track(row.get("track")) or "UNKNOWN"
        grouped[(obs_date, track)].append(row)

    out: list[dict[str, object]] = []
    for (obs_date, track), rows in grouped.items():
        health = avg([parse_float(row.get("telemetry_health_score")) for row in rows])
        lineage = avg([parse_float(row.get("lineage_integrity_score")) for row in rows])
        phase = avg([parse_float(row.get("phase_confidence_score")) for row in rows])
        consistency = avg([parse_float(row.get("telemetry_consistency_score")) for row in rows])
        decay = any(yes(row.get("degradation_warning")) for row in rows)
        volatile = any(yes(row.get("schema_drift_detected")) or yes(row.get("payload_drift_detected")) for row in rows)
        state_grade = classify_state(health, lineage, phase, consistency, decay, volatile, "TRACK_TELEMETRY")
        persistence = min(100.0, max(0.0, (health * 0.35 + lineage * 0.25 + phase * 0.20 + consistency * 0.20)))
        temporal_safe = "YES" if state_grade in {"A", "B", "C"} and all(yes(row.get("safe_for_temporal_research")) for row in rows) else "NO"
        shadow_safe = "YES" if state_grade in {"A", "B"} and all(yes(row.get("safe_for_shadow_research")) for row in rows) else "NO"
        out.append(
            {
                "observation_date": obs_date,
                "track": track,
                "race_class": "UNKNOWN",
                "distance_bucket": "UNKNOWN",
                "tempo_bucket": "UNKNOWN",
                "telemetry_environment": f"track:{track}",
                "telemetry_health_score": f"{health:.2f}",
                "lineage_integrity_score": f"{lineage:.2f}",
                "phase_confidence_score": f"{phase:.2f}",
                "shadow_research_status": "TRACK_TELEMETRY",
                "telemetry_stability_state": STATE_LABELS[state_grade],
                "telemetry_decay_detected": "YES" if decay else "NO",
                "persistence_strength": f"{persistence:.2f}",
                "environment_consistency": f"{consistency:.2f}",
                "longitudinal_confidence": f"{min(100.0, persistence * 0.85 + min(15.0, len(rows) / 10.0)):.2f}",
                "telemetry_grade": state_grade,
                "safe_for_temporal_research": temporal_safe,
                "safe_for_shadow_research": shadow_safe,
                "recommended_action": "Continue accumulating track-level telemetry evidence; do not promote to live modelling or execution.",
                "notes": f"Aggregated from {len(rows)} telemetry rows. Offline longitudinal telemetry research only.",
            }
        )
    return out


def build_shadow_rows(loop_rows: list[dict[str, str]], state_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    state_by_key = latest_shadow_state(state_rows)
    out: list[dict[str, object]] = []
    for row in loop_rows:
        environment_key = clean(row.get("environment_key"))
        state = state_by_key.get(environment_key, {})
        track, race_class, distance_bucket, tempo_bucket = split_environment(row)
        phase_pattern = clean(row.get("phase_transition_pattern")) or "UNKNOWN_PHASE"
        status = clean(row.get("loop_classification") or state.get("current_status")) or "UNKNOWN"
        health = parse_float(row.get("environment_health_score"), parse_float(state.get("environment_health_score"), 50.0))
        stability_drift = parse_float(row.get("stability_drift"))
        variance_drift = parse_float(row.get("variance_drift"))
        resilience_change = parse_float(row.get("resilience_change"))
        consistency = parse_float(row.get("regime_consistency"), 50.0)
        sample_growth = parse_float(row.get("prospective_sample_growth"), parse_float(state.get("current_sample_count")))
        decay = upper(status) in {"DECAYING_RESEARCH", "REGIME_DRIFT_WARNING", "RETIRED_RESEARCH_ENVIRONMENT"} or stability_drift > 25
        volatile = variance_drift > 12 or consistency < 45
        lineage = max(55.0, min(96.0, health + resilience_change * 0.1))
        phase = max(45.0, min(92.0, health - variance_drift * 0.35 + sample_growth * 0.002))
        state_grade = classify_state(health, lineage, phase, consistency, decay, volatile, status)
        persistence = max(0.0, min(100.0, health * 0.45 + consistency * 0.35 + max(-20.0, resilience_change) * 0.20))
        confidence = max(0.0, min(100.0, persistence * 0.75 + min(25.0, sample_growth / 100.0)))
        out.append(
            {
                "observation_date": clean(row.get("loop_timestamp"))[:10] or clean(state.get("last_observed_date")) or "",
                "track": track,
                "race_class": race_class,
                "distance_bucket": distance_bucket,
                "tempo_bucket": tempo_bucket,
                "telemetry_environment": f"{environment_key}|{phase_pattern}",
                "telemetry_health_score": f"{health:.2f}",
                "lineage_integrity_score": f"{lineage:.2f}",
                "phase_confidence_score": f"{phase:.2f}",
                "shadow_research_status": status,
                "telemetry_stability_state": STATE_LABELS[state_grade],
                "telemetry_decay_detected": "YES" if decay else "NO",
                "persistence_strength": f"{persistence:.2f}",
                "environment_consistency": f"{consistency:.2f}",
                "longitudinal_confidence": f"{confidence:.2f}",
                "telemetry_grade": state_grade,
                "safe_for_temporal_research": "YES" if state_grade in {"A", "B", "C"} else "NO",
                "safe_for_shadow_research": "YES" if state_grade in {"A", "B"} and upper(status) not in {"DECAYING_RESEARCH", "RETIRED_RESEARCH_ENVIRONMENT"} else "NO",
                "recommended_action": "Keep environment in offline shadow telemetry accumulation; require future settled observations before any review.",
                "notes": "Shadow environment telemetry accumulation only. No predictions, overlays, live modelling, staking, or execution.",
            }
        )
    return out


def build_watchlist(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        state = clean(row.get("telemetry_stability_state"))
        if state in {"DEGRADING_TELEMETRY", "VOLATILE_TELEMETRY"} or clean(row.get("telemetry_decay_detected")) == "YES":
            grouped[(state or "DECAY_WATCH", clean(row.get("telemetry_environment")))].append(row)

    watch_rows: list[dict[str, object]] = []
    for (state, environment), members in grouped.items():
        avg_conf = avg([parse_float(row.get("longitudinal_confidence")) for row in members])
        decay_count = sum(1 for row in members if clean(row.get("telemetry_decay_detected")) == "YES")
        if state == "DEGRADING_TELEMETRY" or decay_count >= 5:
            severity = "HIGH"
            priority = "HIGH"
        elif state == "VOLATILE_TELEMETRY" or avg_conf < 55:
            severity = "MEDIUM"
            priority = "MEDIUM"
        else:
            severity = "LOW"
            priority = "LOW"
        issue = "Telemetry decay detected" if decay_count else "Volatile telemetry environment"
        repair = "Continue offline observation and repair source lineage or phase confidence before shadow use."
        watch_rows.append(
            {
                "watch_type": state,
                "affected_environment": environment,
                "persistence_issue": issue,
                "affected_rows": len(members),
                "severity": severity,
                "detected_pattern": f"{decay_count} decay rows; average longitudinal confidence {avg_conf:.2f}.",
                "recommended_repair": repair,
                "priority": priority,
                "notes": "Persistence watchlist is offline telemetry governance only; live modelling and execution remain disabled.",
            }
        )
    watch_rows.sort(key=lambda row: (clean(row.get("priority")), -int(row.get("affected_rows") or 0), clean(row.get("affected_environment"))))
    return watch_rows


def main() -> None:
    telemetry_rows = read_csv(TELEMETRY)
    lineage_rows = read_csv(LINEAGE)
    enhanced_rows = read_csv(ENHANCED)
    loop_rows = read_csv(SHADOW_LOOP)
    state_rows = read_csv(SHADOW_STATE)

    out_rows = build_track_rows(telemetry_rows)
    out_rows.extend(build_shadow_rows(loop_rows, state_rows))
    out_rows.sort(
        key=lambda row: (
            clean(row.get("observation_date")),
            clean(row.get("track")),
            clean(row.get("race_class")),
            clean(row.get("distance_bucket")),
            clean(row.get("tempo_bucket")),
            clean(row.get("telemetry_environment")),
        )
    )
    watch_rows = build_watchlist(out_rows)

    states = Counter(clean(row.get("telemetry_stability_state")) for row in out_rows)
    summary_rows: list[dict[str, object]] = [
        {"metric": "accumulation_rows", "value": len(out_rows)},
        {"metric": "elite_persistent_rows", "value": states.get("ELITE_PERSISTENT_TELEMETRY", 0)},
        {"metric": "stable_persistent_rows", "value": states.get("STABLE_PERSISTENT_TELEMETRY", 0)},
        {"metric": "usable_evolving_rows", "value": states.get("USABLE_EVOLVING_TELEMETRY", 0)},
        {"metric": "volatile_rows", "value": states.get("VOLATILE_TELEMETRY", 0)},
        {"metric": "degrading_rows", "value": states.get("DEGRADING_TELEMETRY", 0)},
        {"metric": "persistent_shadow_environments", "value": sum(1 for row in out_rows if clean(row.get("safe_for_shadow_research")) == "YES" and clean(row.get("shadow_research_status")) != "TRACK_TELEMETRY")},
        {"metric": "telemetry_decay_rows", "value": sum(1 for row in out_rows if clean(row.get("telemetry_decay_detected")) == "YES")},
        {"metric": "environment_drift_rows", "value": sum(1 for row in out_rows if upper(row.get("shadow_research_status")) in {"DECAYING_RESEARCH", "REGIME_DRIFT_WARNING"})},
        {"metric": "safe_for_temporal_research_yes", "value": sum(1 for row in out_rows if clean(row.get("safe_for_temporal_research")) == "YES")},
        {"metric": "safe_for_shadow_research_yes", "value": sum(1 for row in out_rows if clean(row.get("safe_for_shadow_research")) == "YES")},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "source_rows::edgeiq_telemetry_health_monitor_v1", "value": len(telemetry_rows)},
        {"metric": "source_rows::edgeiq_timing_lineage_validation_v1", "value": len(lineage_rows)},
        {"metric": "source_rows::edgeiq_enhanced_temporal_phase_confidence_v2", "value": len(enhanced_rows)},
        {"metric": "source_rows::edgeiq_shadow_research_loop_v1", "value": len(loop_rows)},
        {"metric": "source_rows::edgeiq_shadow_environment_state_v1", "value": len(state_rows)},
        {"metric": "watchlist_rows", "value": len(watch_rows)},
    ]
    for path in (TELEMETRY, LINEAGE, ENHANCED, SHADOW_LOOP, SHADOW_STATE):
        if not path.exists():
            summary_rows.append({"metric": f"missing_input::{path.name}", "value": "YES"})

    write_csv(OUT, out_rows, OUT_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv(WATCHLIST, watch_rows, WATCHLIST_FIELDS)

    print("=" * 88)
    print("EDGEIQ LONGITUDINAL TELEMETRY ACCUMULATION V1")
    print("=" * 88)
    for row in summary_rows[:14]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {WATCHLIST}")


if __name__ == "__main__":
    main()
