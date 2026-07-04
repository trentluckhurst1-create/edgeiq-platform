from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_REGIME_MEMORY = DATA / "edgeiq_temporal_regime_memory_ontology_v1.csv"
IN_TRANSITIONS = DATA / "edgeiq_regime_transition_memory_v1.csv"
IN_MATRIX = DATA / "edgeiq_regime_transition_matrix_v1.csv"
IN_TRANSITION_WATCHLIST = DATA / "edgeiq_regime_transition_instability_watchlist_v1.csv"
IN_ENVIRONMENT = DATA / "edgeiq_telemetry_ontology_environment_summary_v1.csv"
IN_SIGNAL = DATA / "edgeiq_telemetry_ontology_signal_summary_v1.csv"

OUT_LAB = DATA / "edgeiq_regime_validation_lab_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_regime_validation_summary_v1.csv"
OUT_FAILURES = DATA / "edgeiq_regime_validation_failures_v1.csv"
OUT_BACKLOG = DATA / "edgeiq_regime_validation_promotion_backlog_v1.csv"

VALIDATION_FIELDS = [
    "validation_scope",
    "jurisdiction",
    "track",
    "regime_archetype",
    "transition_pair",
    "rows_tested",
    "repeat_count",
    "cross_jurisdiction_support",
    "shadow_safe_rows",
    "avg_confidence",
    "confidence_stability",
    "repeatability_score",
    "drift_risk_score",
    "false_persistence_risk",
    "validation_grade",
    "validation_status",
    "recommended_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

FAILURE_FIELDS = [
    "validation_scope",
    "jurisdiction",
    "track",
    "regime_archetype",
    "transition_pair",
    "failure_type",
    "failure_reason",
    "severity",
    "affected_rows",
    "recommended_repair",
    "notes",
]

BACKLOG_FIELDS = [
    "priority",
    "validation_scope",
    "jurisdiction",
    "track",
    "regime_archetype",
    "transition_pair",
    "validation_grade",
    "validation_status",
    "evidence_summary",
    "recommended_next_step",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

OFFLINE_NOTES = "Regime validation lab only. More research attention does not mean live modelling. No predictions, overlays, ratings, execution, or raw jurisdiction merge."


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


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


def cross_support_by_regime(rows: list[dict[str, str]]) -> Counter[str]:
    jurisdictions: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        regime = clean(row.get("regime_archetype"))
        jurisdiction = clean(row.get("jurisdiction"))
        if regime and jurisdiction:
            jurisdictions[regime].add(jurisdiction)
    return Counter({regime: len(items) for regime, items in jurisdictions.items()})


def cross_support_by_transition(rows: list[dict[str, str]]) -> Counter[str]:
    jurisdictions: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        source = clean(row.get("source_regime"))
        target = clean(row.get("target_regime"))
        jurisdiction = clean(row.get("jurisdiction"))
        if source and target and jurisdiction:
            jurisdictions[f"{source}->{target}"].add(jurisdiction)
    return Counter({pair: len(items) for pair, items in jurisdictions.items()})


def watchlist_penalties(rows: list[dict[str, str]]) -> Counter[tuple[str, str, str, str]]:
    penalties: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        severity = upper(row.get("severity"))
        value = {"HIGH": 20, "MEDIUM": 10, "LOW": 5}.get(severity, 5)
        penalties[
            (
                clean(row.get("jurisdiction")),
                clean(row.get("track")),
                clean(row.get("source_regime")),
                clean(row.get("target_regime")),
            )
        ] += value
    return penalties


def environment_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(clean(row.get("jurisdiction")), clean(row.get("track"))): row for row in rows}


def matrix_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {f"{clean(row.get('source_regime'))}->{clean(row.get('target_regime'))}": row for row in rows}


def grade_validation(repeatability: float, confidence_stability: float, drift_risk: float, false_risk: float, shadow_rows: int, cross_support: int) -> tuple[str, str]:
    if false_risk >= 75 or drift_risk >= 85:
        return "F", "REJECTED_NOISY_STRUCTURE"
    if repeatability >= 82 and confidence_stability >= 80 and drift_risk <= 25 and shadow_rows > 0 and cross_support >= 2:
        return "A", "VALIDATED_REPEATING_BEHAVIOUR"
    if repeatability >= 65 and confidence_stability >= 62 and drift_risk <= 45 and cross_support >= 1:
        return "B", "PROMISING_REPEATING_BEHAVIOUR"
    if repeatability >= 42 and confidence_stability >= 45:
        return "C", "DESCRIPTIVE_ONLY"
    if repeatability >= 20:
        return "D", "UNSTABLE_OR_UNPROVEN"
    return "F", "REJECTED_NOISY_STRUCTURE"


def regime_validation_rows(
    memory_rows: list[dict[str, str]],
    environment_rows: list[dict[str, str]],
    signal_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    support = cross_support_by_regime(memory_rows)
    env = environment_index(environment_rows)
    signal_conf_by_family: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in signal_rows:
        signal_conf_by_family[(clean(row.get("jurisdiction")), clean(row.get("universal_signal_family")))].append(parse_float(row.get("avg_ontology_confidence")))

    output: list[dict[str, object]] = []
    for row in memory_rows:
        jurisdiction = clean(row.get("jurisdiction"))
        track = clean(row.get("track"))
        regime = clean(row.get("regime_archetype"))
        rows_tested = parse_int(row.get("ontology_rows"))
        repeat_count = parse_int(row.get("unique_races"))
        shadow_rows = parse_int(row.get("safe_shadow_research_rows"))
        avg_conf = parse_float(row.get("avg_ontology_confidence"))
        persistence = parse_float(row.get("regime_persistence_score"))
        cross = support.get(regime, 0)

        env_row = env.get((jurisdiction, track), {})
        env_conf = parse_float(env_row.get("avg_ontology_confidence"))
        family_conf = avg(signal_conf_by_family.get((jurisdiction, clean(row.get("signal_family"))), []))
        confidence_stability = clamp(avg([value for value in [avg_conf, env_conf, family_conf] if value > 0]))
        repeatability = clamp((persistence * 0.55) + min(25.0, repeat_count / 50 * 25.0) + min(20.0, rows_tested / 2500 * 20.0))
        drift_risk = clamp(abs(avg_conf - confidence_stability) * 2.0 + (20 if clean(row.get("regime_stability_grade")) in {"D", "F"} else 0) + (15 if shadow_rows == 0 else 0))
        false_risk = clamp((35 if regime == "LOW_CONFIDENCE_NOISE_REGIME" else 0) + (25 if rows_tested < 50 else 0) + (20 if cross <= 1 else 0) + max(0.0, 65 - confidence_stability) * 0.7)
        grade, status = grade_validation(repeatability, confidence_stability, drift_risk, false_risk, shadow_rows, cross)
        if status == "VALIDATED_REPEATING_BEHAVIOUR":
            action = "Prioritise for offline longitudinal stress tests across more settled observations."
        elif status == "PROMISING_REPEATING_BEHAVIOUR":
            action = "Add to research-attention backlog; require more cross-track and shadow-safe support."
        elif status == "DESCRIPTIVE_ONLY":
            action = "Keep as descriptive regime memory; do not promote beyond research diagnostics."
        elif status == "UNSTABLE_OR_UNPROVEN":
            action = "Retain for monitoring only and improve sample/confidence stability."
        else:
            action = "Reject as noisy or blocked until ontology/source quality is repaired."
        output.append(
            {
                "validation_scope": "REGIME_MEMORY",
                "jurisdiction": jurisdiction,
                "track": track,
                "regime_archetype": regime,
                "transition_pair": "",
                "rows_tested": str(rows_tested),
                "repeat_count": str(repeat_count),
                "cross_jurisdiction_support": str(cross),
                "shadow_safe_rows": str(shadow_rows),
                "avg_confidence": f"{avg_conf:.2f}",
                "confidence_stability": f"{confidence_stability:.2f}",
                "repeatability_score": f"{repeatability:.2f}",
                "drift_risk_score": f"{drift_risk:.2f}",
                "false_persistence_risk": f"{false_risk:.2f}",
                "validation_grade": grade,
                "validation_status": status,
                "recommended_action": action,
                "notes": OFFLINE_NOTES,
            }
        )
    return output


def transition_validation_rows(
    transition_rows: list[dict[str, str]],
    matrix_rows: list[dict[str, str]],
    instability_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    support = cross_support_by_transition(transition_rows)
    matrix = matrix_index(matrix_rows)
    penalties = watchlist_penalties(instability_rows)
    output: list[dict[str, object]] = []
    for row in transition_rows:
        jurisdiction = clean(row.get("jurisdiction"))
        track = clean(row.get("track"))
        source = clean(row.get("source_regime"))
        target = clean(row.get("target_regime"))
        pair = f"{source}->{target}"
        rows_tested = parse_int(row.get("transition_repeat_count"))
        matrix_row = matrix.get(pair, {})
        matrix_count = parse_int(matrix_row.get("transition_count"))
        repeat_count = max(rows_tested, matrix_count)
        cross = support.get(pair, 0)
        shadow_rows = 1 if clean(row.get("safe_for_shadow_research")) == "YES" else 0
        avg_conf = parse_float(row.get("transition_confidence"))
        matrix_conf = parse_float(matrix_row.get("avg_transition_confidence"))
        confidence_stability = clamp(avg([value for value in [avg_conf, matrix_conf] if value > 0]))
        strength = parse_float(row.get("transition_strength"))
        repeatability = clamp((strength * 0.45) + min(30.0, repeat_count * 2.0) + min(25.0, cross * 8.0))
        penalty = penalties.get((jurisdiction, track, source, target), 0)
        drift_risk = clamp(abs(parse_float(row.get("regime_confidence_delta"))) * 2.0 + penalty + (20 if clean(row.get("transition_risk_grade")) in {"D", "F"} else 0))
        false_risk = clamp((30 if clean(row.get("transition_risk_grade")) == "F" else 0) + (20 if repeat_count < 3 else 0) + (20 if cross <= 1 else 0) + max(0.0, 60 - confidence_stability) * 0.8)
        grade, status = grade_validation(repeatability, confidence_stability, drift_risk, false_risk, shadow_rows, cross)
        if status == "VALIDATED_REPEATING_BEHAVIOUR":
            action = "Prioritise for offline holdout-style transition stability review."
        elif status == "PROMISING_REPEATING_BEHAVIOUR":
            action = "Add to research-attention backlog; require more cross-jurisdiction transition recurrence."
        elif status == "DESCRIPTIVE_ONLY":
            action = "Keep as descriptive transition topology only."
        elif status == "UNSTABLE_OR_UNPROVEN":
            action = "Monitor only; transition instability or weak repeatability remains."
        else:
            action = "Reject transition as noisy/blocked until source regime quality improves."
        output.append(
            {
                "validation_scope": "TRANSITION_MEMORY",
                "jurisdiction": jurisdiction,
                "track": track,
                "regime_archetype": "",
                "transition_pair": pair,
                "rows_tested": str(rows_tested),
                "repeat_count": str(repeat_count),
                "cross_jurisdiction_support": str(cross),
                "shadow_safe_rows": str(shadow_rows),
                "avg_confidence": f"{avg_conf:.2f}",
                "confidence_stability": f"{confidence_stability:.2f}",
                "repeatability_score": f"{repeatability:.2f}",
                "drift_risk_score": f"{drift_risk:.2f}",
                "false_persistence_risk": f"{false_risk:.2f}",
                "validation_grade": grade,
                "validation_status": status,
                "recommended_action": action,
                "notes": OFFLINE_NOTES,
            }
        )
    return output


def build_failures(validation_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for row in validation_rows:
        status = clean(row.get("validation_status"))
        if status not in {"UNSTABLE_OR_UNPROVEN", "REJECTED_NOISY_STRUCTURE"}:
            continue
        false_risk = parse_float(row.get("false_persistence_risk"))
        drift = parse_float(row.get("drift_risk_score"))
        if status == "REJECTED_NOISY_STRUCTURE":
            failure_type = "NOISY_ABSTRACTION"
            reason = "False persistence risk or drift risk blocks the structure."
            severity = "HIGH"
        elif drift >= 55:
            failure_type = "ONTOLOGY_DRIFT_RISK"
            reason = "Drift risk exceeds validation tolerance."
            severity = "MEDIUM"
        elif false_risk >= 50:
            failure_type = "FALSE_PERSISTENCE_RISK"
            reason = "Persistence appears weak or unsupported by cross-jurisdiction evidence."
            severity = "MEDIUM"
        else:
            failure_type = "INSUFFICIENT_REPEATABILITY"
            reason = "Repeatability and confidence stability are below validation threshold."
            severity = "LOW"
        failures.append(
            {
                "validation_scope": row.get("validation_scope", ""),
                "jurisdiction": row.get("jurisdiction", ""),
                "track": row.get("track", ""),
                "regime_archetype": row.get("regime_archetype", ""),
                "transition_pair": row.get("transition_pair", ""),
                "failure_type": failure_type,
                "failure_reason": reason,
                "severity": severity,
                "affected_rows": row.get("rows_tested", "0"),
                "recommended_repair": row.get("recommended_action", ""),
                "notes": OFFLINE_NOTES,
            }
        )
    failures.sort(key=lambda item: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(clean(item.get("severity")), 3), -parse_int(item.get("affected_rows"))))
    return failures


def build_backlog(validation_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    backlog: list[dict[str, object]] = []
    for row in validation_rows:
        grade = clean(row.get("validation_grade"))
        if grade not in {"A", "B"}:
            continue
        priority = "HIGH" if grade == "A" else "MEDIUM"
        evidence = (
            f"repeat={row.get('repeat_count')}; cross_jurisdiction={row.get('cross_jurisdiction_support')}; "
            f"shadow={row.get('shadow_safe_rows')}; confidence_stability={row.get('confidence_stability')}; "
            f"repeatability={row.get('repeatability_score')}"
        )
        backlog.append(
            {
                "priority": priority,
                "validation_scope": row.get("validation_scope", ""),
                "jurisdiction": row.get("jurisdiction", ""),
                "track": row.get("track", ""),
                "regime_archetype": row.get("regime_archetype", ""),
                "transition_pair": row.get("transition_pair", ""),
                "validation_grade": grade,
                "validation_status": row.get("validation_status", ""),
                "evidence_summary": evidence,
                "recommended_next_step": row.get("recommended_action", ""),
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": OFFLINE_NOTES,
            }
        )
    backlog.sort(key=lambda item: ({"HIGH": 0, "MEDIUM": 1}.get(clean(item.get("priority")), 2), -parse_float(str(item.get("evidence_summary", "")).split("repeatability=")[-1] if "repeatability=" in str(item.get("evidence_summary", "")) else 0)))
    return backlog


def count_status(rows: list[dict[str, object]], status: str) -> int:
    return sum(1 for row in rows if clean(row.get("validation_status")) == status)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    regime_rows = safe_read_csv(IN_REGIME_MEMORY)
    transition_rows = safe_read_csv(IN_TRANSITIONS)
    matrix_rows = safe_read_csv(IN_MATRIX)
    instability_rows = safe_read_csv(IN_TRANSITION_WATCHLIST)
    environment_rows = safe_read_csv(IN_ENVIRONMENT)
    signal_rows = safe_read_csv(IN_SIGNAL)

    validation_rows = regime_validation_rows(regime_rows, environment_rows, signal_rows)
    validation_rows.extend(transition_validation_rows(transition_rows, matrix_rows, instability_rows))
    validation_rows.sort(key=lambda row: (clean(row.get("validation_scope")), clean(row.get("validation_grade")), -parse_float(row.get("repeatability_score"))))

    failures = build_failures(validation_rows)
    backlog = build_backlog(validation_rows)

    write_csv_atomic(OUT_LAB, validation_rows, VALIDATION_FIELDS)
    write_csv_atomic(OUT_FAILURES, failures, FAILURE_FIELDS)
    write_csv_atomic(OUT_BACKLOG, backlog, BACKLOG_FIELDS)

    summary = [
        {"metric": "validation_rows", "value": str(len(validation_rows))},
        {"metric": "validated_repeating_behaviours", "value": str(count_status(validation_rows, "VALIDATED_REPEATING_BEHAVIOUR"))},
        {"metric": "promising_repeating_behaviours", "value": str(count_status(validation_rows, "PROMISING_REPEATING_BEHAVIOUR"))},
        {"metric": "descriptive_only", "value": str(count_status(validation_rows, "DESCRIPTIVE_ONLY"))},
        {"metric": "unstable_or_unproven", "value": str(count_status(validation_rows, "UNSTABLE_OR_UNPROVEN"))},
        {"metric": "rejected_noisy_structures", "value": str(count_status(validation_rows, "REJECTED_NOISY_STRUCTURE"))},
        {"metric": "promotion_backlog_rows", "value": str(len(backlog))},
        {"metric": "failure_rows", "value": str(len(failures))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Regime validation rows: {len(validation_rows)}")
    print(f"Promotion backlog rows: {len(backlog)}")
    print(f"Failure rows: {len(failures)}")


if __name__ == "__main__":
    main()
