from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_VALIDATION = DATA / "edgeiq_regime_validation_lab_v1.csv"
IN_REGIME_MEMORY = DATA / "edgeiq_temporal_regime_memory_ontology_v1.csv"
IN_TRANSITIONS = DATA / "edgeiq_regime_transition_memory_v1.csv"
IN_MATRIX = DATA / "edgeiq_regime_transition_matrix_v1.csv"
IN_COMPACT = DATA / "edgeiq_telemetry_ontology_compact_v1.csv"

OUT_EVIDENCE = DATA / "edgeiq_longitudinal_evidence_accumulation_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_longitudinal_evidence_summary_v1.csv"
OUT_SURVIVAL = DATA / "edgeiq_longitudinal_regime_survival_v1.csv"
OUT_RECURRENCE = DATA / "edgeiq_longitudinal_transition_recurrence_v1.csv"
OUT_DECAY = DATA / "edgeiq_longitudinal_confidence_decay_v1.csv"

EVIDENCE_FIELDS = [
    "jurisdiction",
    "track",
    "regime_archetype",
    "transition_pair",
    "observation_window",
    "evidence_rows",
    "repeat_count",
    "cross_jurisdiction_support",
    "shadow_safe_rows",
    "avg_confidence",
    "confidence_delta",
    "confidence_trend",
    "repeatability_trend",
    "persistence_trend",
    "survival_score",
    "decay_risk",
    "reinforcement_score",
    "longitudinal_grade",
    "longitudinal_status",
    "recommended_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

SURVIVAL_FIELDS = [
    "regime_archetype",
    "jurisdictions_present",
    "tracks_present",
    "survival_score",
    "survival_grade",
    "confidence_persistence",
    "cross_jurisdiction_durability",
    "research_status",
    "notes",
]

RECURRENCE_FIELDS = [
    "transition_pair",
    "recurrence_count",
    "jurisdictions_present",
    "avg_transition_confidence",
    "avg_repeatability",
    "recurrence_grade",
    "research_status",
    "notes",
]

DECAY_FIELDS = [
    "regime_archetype",
    "transition_pair",
    "avg_confidence",
    "confidence_delta",
    "decay_risk",
    "drift_signal",
    "confidence_health",
    "recommended_repair",
    "notes",
]

OFFLINE_NOTES = "Longitudinal evidence accumulation baseline only. No predictions, overlays, ratings, live modelling, execution, or raw jurisdiction merge."


def clean(value: object) -> str:
    return str(value or "").strip()


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", "") or 0))
    except ValueError:
        return 0


def parse_float(value: object) -> float:
    try:
        return float(clean(value).replace(",", "") or 0)
    except ValueError:
        return 0.0


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def compact_confidence_index(compact_rows: list[dict[str, str]]) -> dict[tuple[str, str], list[float]]:
    index: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in compact_rows:
        index[(clean(row.get("jurisdiction")), clean(row.get("track")))].append(parse_float(row.get("avg_ontology_confidence")))
    return index


def transition_matrix_index(matrix_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {f"{clean(row.get('source_regime'))}->{clean(row.get('target_regime'))}": row for row in matrix_rows}


def trend_from_delta(delta: float, tolerance: float = 2.0) -> str:
    if delta >= tolerance:
        return "STRENGTHENING"
    if delta <= -tolerance:
        return "WEAKENING"
    return "STABLE"


def repeatability_trend(repeatability: float, status: str) -> str:
    if status in {"VALIDATED_REPEATING_BEHAVIOUR", "PROMISING_REPEATING_BEHAVIOUR"} and repeatability >= 70:
        return "STRENGTHENING"
    if status in {"REJECTED_NOISY_STRUCTURE", "UNSTABLE_OR_UNPROVEN"}:
        return "WEAKENING"
    return "STABLE"


def persistence_trend(validation_status: str, drift_risk: float, false_risk: float) -> str:
    if validation_status in {"VALIDATED_REPEATING_BEHAVIOUR", "PROMISING_REPEATING_BEHAVIOUR"} and drift_risk <= 35 and false_risk <= 35:
        return "STRENGTHENING"
    if validation_status == "REJECTED_NOISY_STRUCTURE" or drift_risk >= 70 or false_risk >= 70:
        return "DECAYING"
    if validation_status == "UNSTABLE_OR_UNPROVEN":
        return "WEAKENING"
    return "STABLE"


def survival_score(row: dict[str, str], confidence_delta: float) -> float:
    repeat = parse_float(row.get("repeatability_score"))
    confidence = parse_float(row.get("confidence_stability"))
    drift = parse_float(row.get("drift_risk_score"))
    false_risk = parse_float(row.get("false_persistence_risk"))
    cross = parse_int(row.get("cross_jurisdiction_support"))
    shadow = parse_int(row.get("shadow_safe_rows"))
    score = repeat * 0.38 + confidence * 0.32 + min(15.0, cross * 5.0) + min(10.0, shadow / 50.0) - drift * 0.18 - false_risk * 0.20 + max(0.0, confidence_delta) * 0.25
    return round(clamp(score), 2)


def decay_risk(row: dict[str, str], confidence_delta: float) -> float:
    drift = parse_float(row.get("drift_risk_score"))
    false_risk = parse_float(row.get("false_persistence_risk"))
    repeat = parse_float(row.get("repeatability_score"))
    penalty = abs(min(0.0, confidence_delta)) * 1.5
    score = drift * 0.45 + false_risk * 0.35 + max(0.0, 60.0 - repeat) * 0.20 + penalty
    return round(clamp(score), 2)


def reinforcement_score(row: dict[str, str], survival: float, decay: float) -> float:
    cross = parse_int(row.get("cross_jurisdiction_support"))
    shadow = parse_int(row.get("shadow_safe_rows"))
    repeat = parse_float(row.get("repeatability_score"))
    score = survival * 0.45 + repeat * 0.35 + min(12.0, cross * 4.0) + min(8.0, shadow / 100.0) - decay * 0.18
    return round(clamp(score), 2)


def grade_and_status(survival: float, decay: float, reinforcement: float, validation_status: str) -> tuple[str, str]:
    if validation_status == "REJECTED_NOISY_STRUCTURE" or decay >= 75:
        return "F", "NOISY"
    if survival >= 82 and reinforcement >= 75 and decay <= 25:
        return "A", "SURVIVING"
    if survival >= 68 and reinforcement >= 60 and decay <= 40:
        return "B", "STRENGTHENING"
    if survival >= 48 and decay <= 58:
        return "C", "SURVIVING"
    if decay >= 60:
        return "D", "DECAYING"
    return "D", "UNSTABLE"


def build_evidence_rows(validation_rows: list[dict[str, str]], compact_rows: list[dict[str, str]], matrix_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    compact_index = compact_confidence_index(compact_rows)
    matrix_index = transition_matrix_index(matrix_rows)
    evidence: list[dict[str, object]] = []
    for row in validation_rows:
        jurisdiction = clean(row.get("jurisdiction"))
        track = clean(row.get("track"))
        regime = clean(row.get("regime_archetype"))
        pair = clean(row.get("transition_pair"))
        status = clean(row.get("validation_status"))
        avg_confidence = parse_float(row.get("avg_confidence"))
        baseline_conf = avg(compact_index.get((jurisdiction, track), []))
        if pair and pair in matrix_index:
            matrix_conf = parse_float(matrix_index[pair].get("avg_transition_confidence"))
            baseline_conf = avg([value for value in [baseline_conf, matrix_conf] if value > 0])
        confidence_delta = round(avg_confidence - baseline_conf, 2) if baseline_conf else 0.0
        survival = survival_score(row, confidence_delta)
        decay = decay_risk(row, confidence_delta)
        reinforcement = reinforcement_score(row, survival, decay)
        grade, longitudinal_status = grade_and_status(survival, decay, reinforcement, status)
        evidence.append(
            {
                "jurisdiction": jurisdiction,
                "track": track,
                "regime_archetype": regime,
                "transition_pair": pair,
                "observation_window": "CURRENT_SNAPSHOT",
                "evidence_rows": row.get("rows_tested", "0"),
                "repeat_count": row.get("repeat_count", "0"),
                "cross_jurisdiction_support": row.get("cross_jurisdiction_support", "0"),
                "shadow_safe_rows": row.get("shadow_safe_rows", "0"),
                "avg_confidence": f"{avg_confidence:.2f}",
                "confidence_delta": f"{confidence_delta:.2f}",
                "confidence_trend": trend_from_delta(confidence_delta),
                "repeatability_trend": repeatability_trend(parse_float(row.get("repeatability_score")), status),
                "persistence_trend": persistence_trend(status, parse_float(row.get("drift_risk_score")), parse_float(row.get("false_persistence_risk"))),
                "survival_score": f"{survival:.2f}",
                "decay_risk": f"{decay:.2f}",
                "reinforcement_score": f"{reinforcement:.2f}",
                "longitudinal_grade": grade,
                "longitudinal_status": longitudinal_status,
                "recommended_action": recommended_action(grade, longitudinal_status, pair),
                "notes": OFFLINE_NOTES,
            }
        )
    evidence.sort(key=lambda item: (clean(item.get("longitudinal_grade")), -parse_float(item.get("survival_score")), clean(item.get("jurisdiction")), clean(item.get("track"))))
    return evidence


def recommended_action(grade: str, status: str, transition_pair: str) -> str:
    target = "transition" if transition_pair else "regime"
    if grade == "A":
        return f"Continue offline longitudinal accumulation for this {target}; do not promote to modelling."
    if grade == "B":
        return f"Prioritise future evidence collection for this {target}; require repeated snapshots."
    if grade == "C":
        return f"Keep as observational {target} structure and monitor persistence."
    if status == "DECAYING":
        return f"Watch for confidence decay and source drift before further research use."
    if status == "NOISY":
        return f"Repair ontology/source quality before using this {target} as behavioural evidence."
    return f"Accumulate more evidence before interpreting this {target}."


def build_survival(evidence_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[str, dict[str, object]] = defaultdict(lambda: {"jurisdictions": set(), "tracks": set(), "survival": [], "confidence": [], "cross": 0, "grades": Counter()})
    for row in evidence_rows:
        regime = clean(row.get("regime_archetype"))
        if not regime:
            continue
        bucket = buckets[regime]
        bucket["jurisdictions"].add(clean(row.get("jurisdiction")))  # type: ignore[union-attr]
        bucket["tracks"].add(clean(row.get("track")))  # type: ignore[union-attr]
        bucket["survival"].append(parse_float(row.get("survival_score")))  # type: ignore[union-attr]
        bucket["confidence"].append(parse_float(row.get("avg_confidence")))  # type: ignore[union-attr]
        bucket["cross"] = int(bucket["cross"]) + parse_int(row.get("cross_jurisdiction_support"))
        bucket["grades"][clean(row.get("longitudinal_grade"))] += 1  # type: ignore[index]
    output: list[dict[str, object]] = []
    for regime, bucket in buckets.items():
        survival = avg(bucket["survival"])  # type: ignore[arg-type]
        confidence = avg(bucket["confidence"])  # type: ignore[arg-type]
        jurisdictions = len(bucket["jurisdictions"])  # type: ignore[arg-type]
        tracks = len(bucket["tracks"])  # type: ignore[arg-type]
        durability = round(clamp((jurisdictions * 12) + (tracks * 1.8) + survival * 0.45), 2)
        if survival >= 80 and durability >= 70:
            grade = "A"
            status = "DURABLE_BEHAVIOURAL_STRUCTURE"
        elif survival >= 65:
            grade = "B"
            status = "STABLE_EMERGING_STRUCTURE"
        elif survival >= 45:
            grade = "C"
            status = "OBSERVATIONAL_STRUCTURE"
        elif survival >= 25:
            grade = "D"
            status = "WEAK_OR_DECAYING_STRUCTURE"
        else:
            grade = "F"
            status = "FAILED_OR_NOISY_STRUCTURE"
        output.append(
            {
                "regime_archetype": regime,
                "jurisdictions_present": str(jurisdictions),
                "tracks_present": str(tracks),
                "survival_score": f"{survival:.2f}",
                "survival_grade": grade,
                "confidence_persistence": f"{confidence:.2f}",
                "cross_jurisdiction_durability": f"{durability:.2f}",
                "research_status": status,
                "notes": OFFLINE_NOTES,
            }
        )
    output.sort(key=lambda row: (clean(row.get("survival_grade")), -parse_float(row.get("survival_score"))))
    return output


def build_recurrence(evidence_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[str, dict[str, object]] = defaultdict(lambda: {"count": 0, "jurisdictions": set(), "confidence": [], "repeatability": [], "grades": Counter()})
    for row in evidence_rows:
        pair = clean(row.get("transition_pair"))
        if not pair:
            continue
        bucket = buckets[pair]
        bucket["count"] = int(bucket["count"]) + 1
        bucket["jurisdictions"].add(clean(row.get("jurisdiction")))  # type: ignore[union-attr]
        bucket["confidence"].append(parse_float(row.get("avg_confidence")))  # type: ignore[union-attr]
        bucket["repeatability"].append(parse_float(row.get("reinforcement_score")))  # type: ignore[union-attr]
        bucket["grades"][clean(row.get("longitudinal_grade"))] += 1  # type: ignore[index]
    output: list[dict[str, object]] = []
    for pair, bucket in buckets.items():
        recurrence = int(bucket["count"])
        confidence = avg(bucket["confidence"])  # type: ignore[arg-type]
        repeatability = avg(bucket["repeatability"])  # type: ignore[arg-type]
        jurisdictions = len(bucket["jurisdictions"])  # type: ignore[arg-type]
        if recurrence >= 10 and confidence >= 65 and repeatability >= 60:
            grade = "B"
            status = "STABLE_EMERGING_STRUCTURE"
        elif recurrence >= 5 and confidence >= 45:
            grade = "C"
            status = "OBSERVATIONAL_STRUCTURE"
        elif confidence < 35:
            grade = "F"
            status = "FAILED_OR_NOISY_STRUCTURE"
        else:
            grade = "D"
            status = "WEAK_OR_DECAYING_STRUCTURE"
        output.append(
            {
                "transition_pair": pair,
                "recurrence_count": str(recurrence),
                "jurisdictions_present": str(jurisdictions),
                "avg_transition_confidence": f"{confidence:.2f}",
                "avg_repeatability": f"{repeatability:.2f}",
                "recurrence_grade": grade,
                "research_status": status,
                "notes": OFFLINE_NOTES,
            }
        )
    output.sort(key=lambda row: (clean(row.get("recurrence_grade")), -parse_int(row.get("recurrence_count"))))
    return output


def build_decay(evidence_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in evidence_rows:
        regime = clean(row.get("regime_archetype"))
        pair = clean(row.get("transition_pair"))
        confidence = parse_float(row.get("avg_confidence"))
        delta = parse_float(row.get("confidence_delta"))
        decay = parse_float(row.get("decay_risk"))
        if decay >= 70:
            drift = "HIGH_DECAY_SIGNAL"
            health = "UNHEALTHY"
            repair = "Repair ontology/source lineage or reject noisy structure."
        elif delta <= -5:
            drift = "NEGATIVE_CONFIDENCE_DRIFT"
            health = "WATCH"
            repair = "Monitor confidence decay on future snapshots."
        elif delta >= 5:
            drift = "POSITIVE_CONFIDENCE_DRIFT"
            health = "HEALTHY"
            repair = "Continue offline accumulation only."
        else:
            drift = "STABLE_CONFIDENCE"
            health = "STABLE"
            repair = "Retain as baseline evidence."
        output.append(
            {
                "regime_archetype": regime,
                "transition_pair": pair,
                "avg_confidence": f"{confidence:.2f}",
                "confidence_delta": f"{delta:.2f}",
                "decay_risk": f"{decay:.2f}",
                "drift_signal": drift,
                "confidence_health": health,
                "recommended_repair": repair,
                "notes": OFFLINE_NOTES,
            }
        )
    output.sort(key=lambda row: (-parse_float(row.get("decay_risk")), clean(row.get("regime_archetype")), clean(row.get("transition_pair"))))
    return output


def status_count(rows: list[dict[str, object]], status: str) -> int:
    return sum(1 for row in rows if clean(row.get("longitudinal_status")) == status)


def grade_count(rows: list[dict[str, object]], grade: str) -> int:
    return sum(1 for row in rows if clean(row.get("longitudinal_grade")) == grade)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    validation_rows = safe_read_csv(IN_VALIDATION)
    regime_rows = safe_read_csv(IN_REGIME_MEMORY)
    transition_rows = safe_read_csv(IN_TRANSITIONS)
    matrix_rows = safe_read_csv(IN_MATRIX)
    compact_rows = safe_read_csv(IN_COMPACT)

    evidence_rows = build_evidence_rows(validation_rows, compact_rows, matrix_rows)
    survival_rows = build_survival(evidence_rows)
    recurrence_rows = build_recurrence(evidence_rows)
    decay_rows = build_decay(evidence_rows)

    write_csv_atomic(OUT_EVIDENCE, evidence_rows, EVIDENCE_FIELDS)
    write_csv_atomic(OUT_SURVIVAL, survival_rows, SURVIVAL_FIELDS)
    write_csv_atomic(OUT_RECURRENCE, recurrence_rows, RECURRENCE_FIELDS)
    write_csv_atomic(OUT_DECAY, decay_rows, DECAY_FIELDS)

    jurisdictions = {clean(row.get("jurisdiction")) for row in evidence_rows if clean(row.get("jurisdiction"))}
    tracks = {clean(row.get("track")) for row in evidence_rows if clean(row.get("track"))}
    summary = [
        {"metric": "longitudinal_rows", "value": str(len(evidence_rows))},
        {"metric": "durable_behavioural_structures", "value": str(grade_count(evidence_rows, "A"))},
        {"metric": "stable_emerging_structures", "value": str(grade_count(evidence_rows, "B"))},
        {"metric": "observational_structures", "value": str(grade_count(evidence_rows, "C"))},
        {"metric": "weak_or_decaying_structures", "value": str(grade_count(evidence_rows, "D"))},
        {"metric": "failed_or_noisy_structures", "value": str(grade_count(evidence_rows, "F"))},
        {"metric": "surviving_structures", "value": str(status_count(evidence_rows, "SURVIVING"))},
        {"metric": "strengthening_structures", "value": str(status_count(evidence_rows, "STRENGTHENING"))},
        {"metric": "decaying_structures", "value": str(status_count(evidence_rows, "DECAYING"))},
        {"metric": "unstable_structures", "value": str(status_count(evidence_rows, "UNSTABLE"))},
        {"metric": "noisy_structures", "value": str(status_count(evidence_rows, "NOISY"))},
        {"metric": "regime_survival_rows", "value": str(len(survival_rows))},
        {"metric": "transition_recurrence_rows", "value": str(len(recurrence_rows))},
        {"metric": "confidence_decay_rows", "value": str(len(decay_rows))},
        {"metric": "source_regime_memory_rows", "value": str(len(regime_rows))},
        {"metric": "source_transition_rows", "value": str(len(transition_rows))},
        {"metric": "jurisdictions_covered", "value": str(len(jurisdictions))},
        {"metric": "tracks_covered", "value": str(len(tracks))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Longitudinal evidence rows: {len(evidence_rows)}")
    print(f"Regime survival rows: {len(survival_rows)}")
    print(f"Transition recurrence rows: {len(recurrence_rows)}")
    print(f"Confidence decay rows: {len(decay_rows)}")


if __name__ == "__main__":
    main()
