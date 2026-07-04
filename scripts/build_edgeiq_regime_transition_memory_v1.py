from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_MEMORY = DATA / "edgeiq_temporal_regime_memory_ontology_v1.csv"
IN_DICTIONARY = DATA / "edgeiq_regime_archetype_dictionary_v1.csv"
IN_WATCHLIST = DATA / "edgeiq_regime_memory_watchlist_v1.csv"

OUT_TRANSITIONS = DATA / "edgeiq_regime_transition_memory_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_regime_transition_summary_v1.csv"
OUT_MATRIX = DATA / "edgeiq_regime_transition_matrix_v1.csv"
OUT_WATCHLIST = DATA / "edgeiq_regime_transition_instability_watchlist_v1.csv"

TRANSITION_FIELDS = [
    "jurisdiction",
    "track",
    "source_regime",
    "target_regime",
    "transition_type",
    "transition_strength",
    "transition_confidence",
    "transition_repeat_count",
    "transition_stability",
    "regime_persistence_before",
    "regime_persistence_after",
    "regime_confidence_delta",
    "transition_risk_grade",
    "safe_for_cross_jurisdiction_research",
    "safe_for_shadow_research",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

MATRIX_FIELDS = [
    "source_regime",
    "target_regime",
    "transition_count",
    "avg_transition_strength",
    "avg_transition_confidence",
    "dominant_transition_type",
    "research_status",
    "notes",
]

WATCHLIST_FIELDS = [
    "watch_type",
    "jurisdiction",
    "track",
    "source_regime",
    "target_regime",
    "issue",
    "severity",
    "affected_rows",
    "recommended_repair",
    "notes",
]

OFFLINE_NOTES = "Regime transition memory only. No predictions, overlays, ratings, live modelling, execution, or raw jurisdiction merge."

ARCHETYPE_ORDER = {
    "HIGH_TRUST_TELEMETRY_REGIME": 0,
    "LEADER_DOMINANCE_REGIME": 1,
    "FRONT_PRESSURE_REGIME": 2,
    "PACK_COMPRESSION_REGIME": 3,
    "MIDFIELD_STABILITY_REGIME": 4,
    "LATE_ACCELERATION_REGIME": 5,
    "FADING_PRESSURE_REGIME": 6,
    "DECAYING_TELEMETRY_REGIME": 7,
    "GENERAL_UNCLASSIFIED_REGIME": 8,
    "LOW_CONFIDENCE_NOISE_REGIME": 9,
}

PHASE_ORDER = {
    "EARLY_PHASE": 0,
    "MID_PHASE": 1,
    "LATE_PHASE": 2,
    "UNKNOWN_PHASE": 3,
}

GRADE_SCORE = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 0}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> float:
    try:
        return float(clean(value).replace(",", "") or 0)
    except ValueError:
        return 0.0


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", "") or 0))
    except ValueError:
        return 0


def safe_yes(value: object) -> bool:
    return upper(value) in {"YES", "Y", "TRUE", "1"}


def behavioural_sort_key(row: dict[str, str]) -> tuple[int, int, float, float, str]:
    archetype = upper(row.get("regime_archetype"))
    phase = upper(row.get("dominant_phase"))
    return (
        ARCHETYPE_ORDER.get(archetype, 99),
        PHASE_ORDER.get(phase, 9),
        -parse_float(row.get("regime_persistence_score")),
        -parse_float(row.get("avg_ontology_confidence")),
        upper(row.get("signal_family")),
    )


def transition_type(source: str, target: str, source_row: dict[str, str], target_row: dict[str, str]) -> str:
    if source == target:
        return "STABLE_PERSISTENCE"
    if target == "DECAYING_TELEMETRY_REGIME" or "DECAY" in target:
        return "TELEMETRY_DECAY"
    if target == "LOW_CONFIDENCE_NOISE_REGIME":
        return "NOISE_TRANSITION"
    if source in {"FRONT_PRESSURE_REGIME", "PACK_COMPRESSION_REGIME", "LEADER_DOMINANCE_REGIME"} and target == "FADING_PRESSURE_REGIME":
        return "PRESSURE_COLLAPSE"
    if source in {"MIDFIELD_STABILITY_REGIME", "PACK_COMPRESSION_REGIME"} and target == "LATE_ACCELERATION_REGIME":
        return "ACCELERATION_SHIFT"
    if GRADE_SCORE.get(clean(target_row.get("regime_stability_grade")), 0) > GRADE_SCORE.get(clean(source_row.get("regime_stability_grade")), 0):
        return "REGIME_STABILISATION"
    if GRADE_SCORE.get(clean(target_row.get("regime_stability_grade")), 0) < GRADE_SCORE.get(clean(source_row.get("regime_stability_grade")), 0):
        return "REGIME_ESCALATION"
    return "GRADUAL_DRIFT"


def transition_strength(source_row: dict[str, str], target_row: dict[str, str], transition: str) -> float:
    source_persistence = parse_float(source_row.get("regime_persistence_score"))
    target_persistence = parse_float(target_row.get("regime_persistence_score"))
    source_conf = parse_float(source_row.get("avg_ontology_confidence"))
    target_conf = parse_float(target_row.get("avg_ontology_confidence"))
    source_rows = parse_int(source_row.get("ontology_rows"))
    target_rows = parse_int(target_row.get("ontology_rows"))
    volume_component = min(25.0, (min(source_rows, target_rows) / 1000) * 25.0)
    persistence_component = min(35.0, ((source_persistence + target_persistence) / 200) * 35.0)
    confidence_component = min(25.0, ((source_conf + target_conf) / 200) * 25.0)
    transition_component = {
        "STABLE_PERSISTENCE": 15.0,
        "REGIME_STABILISATION": 12.0,
        "ACCELERATION_SHIFT": 10.0,
        "GRADUAL_DRIFT": 8.0,
        "PRESSURE_COLLAPSE": 6.0,
        "TELEMETRY_DECAY": 5.0,
        "REGIME_ESCALATION": 5.0,
        "NOISE_TRANSITION": 0.0,
    }.get(transition, 5.0)
    return round(min(100.0, volume_component + persistence_component + confidence_component + transition_component), 2)


def confidence_for_transition(source_row: dict[str, str], target_row: dict[str, str], repeat_count: int, watch_penalty: float) -> float:
    source_conf = parse_float(source_row.get("avg_ontology_confidence"))
    target_conf = parse_float(target_row.get("avg_ontology_confidence"))
    source_races = parse_int(source_row.get("unique_races"))
    target_races = parse_int(target_row.get("unique_races"))
    repeat_component = min(15.0, repeat_count * 3.0)
    race_component = min(15.0, (min(source_races, target_races) / 50) * 15.0)
    base = ((source_conf + target_conf) / 2) * 0.70 + repeat_component + race_component - watch_penalty
    return round(max(0.0, min(100.0, base)), 2)


def stability_label(strength: float, confidence: float, source_row: dict[str, str], target_row: dict[str, str]) -> str:
    source_grade = clean(source_row.get("regime_stability_grade"))
    target_grade = clean(target_row.get("regime_stability_grade"))
    if source_grade == "F" or target_grade == "F":
        return "BLOCKED_STABILITY"
    if strength >= 80 and confidence >= 80:
        return "HIGH_STABILITY"
    if strength >= 65 and confidence >= 65:
        return "USABLE_STABILITY"
    if strength >= 45 and confidence >= 50:
        return "DESCRIPTIVE_STABILITY"
    return "UNSTABLE_STABILITY"


def risk_grade(strength: float, confidence: float, transition: str, source_row: dict[str, str], target_row: dict[str, str]) -> tuple[str, str]:
    source_grade = clean(source_row.get("regime_stability_grade"))
    target_grade = clean(target_row.get("regime_stability_grade"))
    if transition == "NOISE_TRANSITION" or source_grade == "F" or target_grade == "F":
        return "F", "BLOCKED_TRANSITION"
    if strength >= 82 and confidence >= 82 and transition == "STABLE_PERSISTENCE":
        return "A", "STABLE_REPEATABLE_TRANSITION"
    if strength >= 68 and confidence >= 65:
        return "B", "USABLE_BEHAVIOURAL_TRANSITION"
    if strength >= 45 and confidence >= 45:
        return "C", "DESCRIPTIVE_TRANSITION"
    return "D", "UNSTABLE_TRANSITION"


def watch_penalties(watchlist_rows: list[dict[str, str]]) -> Counter[tuple[str, str, str]]:
    penalties: Counter[tuple[str, str, str]] = Counter()
    for row in watchlist_rows:
        jurisdiction = clean(row.get("jurisdiction"))
        track = clean(row.get("track"))
        regime = clean(row.get("regime_archetype"))
        severity = upper(row.get("severity"))
        if not jurisdiction or not track or not regime:
            continue
        penalties[(jurisdiction, track, regime)] += {"HIGH": 15, "MEDIUM": 8, "LOW": 3}.get(severity, 3)
    return penalties


def build_transitions(memory_rows: list[dict[str, str]], watchlist_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in memory_rows:
        grouped[(clean(row.get("jurisdiction")), clean(row.get("track")))].append(row)

    matrix_counts = Counter()
    for row in memory_rows:
        key = (clean(row.get("jurisdiction")), clean(row.get("track")), clean(row.get("regime_archetype")))
        matrix_counts[key] += 1

    penalties = watch_penalties(watchlist_rows)
    transitions: list[dict[str, object]] = []

    for (jurisdiction, track), rows in grouped.items():
        if not rows:
            continue
        rows = sorted(rows, key=behavioural_sort_key)
        seen_pairs: set[tuple[str, str, str, str]] = set()
        for index, source_row in enumerate(rows):
            source_regime = clean(source_row.get("regime_archetype"))
            if not source_regime:
                continue
            candidate_targets: list[dict[str, str]] = []
            if index + 1 < len(rows):
                candidate_targets.append(rows[index + 1])
            for target_row in rows:
                if clean(target_row.get("regime_archetype")) == source_regime and target_row is not source_row:
                    candidate_targets.append(target_row)
                    break
            for target_row in candidate_targets[:2]:
                target_regime = clean(target_row.get("regime_archetype"))
                if not target_regime:
                    continue
                pair_key = (jurisdiction, track, source_regime, target_regime)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                transition = transition_type(source_regime, target_regime, source_row, target_row)
                repeat_count = min(matrix_counts[(jurisdiction, track, source_regime)], matrix_counts[(jurisdiction, track, target_regime)])
                watch_penalty = float(penalties[(jurisdiction, track, source_regime)] + penalties[(jurisdiction, track, target_regime)])
                strength = transition_strength(source_row, target_row, transition)
                confidence = confidence_for_transition(source_row, target_row, repeat_count, watch_penalty)
                grade, grade_label = risk_grade(strength, confidence, transition, source_row, target_row)
                stability = stability_label(strength, confidence, source_row, target_row)
                source_persistence = parse_float(source_row.get("regime_persistence_score"))
                target_persistence = parse_float(target_row.get("regime_persistence_score"))
                confidence_delta = parse_float(target_row.get("avg_ontology_confidence")) - parse_float(source_row.get("avg_ontology_confidence"))
                safe_cross = "YES" if parse_int(source_row.get("safe_cross_research_rows")) > 0 and parse_int(target_row.get("safe_cross_research_rows")) > 0 and grade != "F" else "NO"
                safe_shadow = "YES" if parse_int(source_row.get("safe_shadow_research_rows")) > 0 and parse_int(target_row.get("safe_shadow_research_rows")) > 0 and grade in {"A", "B", "C"} else "NO"
                transitions.append(
                    {
                        "jurisdiction": jurisdiction,
                        "track": track,
                        "source_regime": source_regime,
                        "target_regime": target_regime,
                        "transition_type": transition,
                        "transition_strength": f"{strength:.2f}",
                        "transition_confidence": f"{confidence:.2f}",
                        "transition_repeat_count": str(repeat_count),
                        "transition_stability": stability,
                        "regime_persistence_before": f"{source_persistence:.2f}",
                        "regime_persistence_after": f"{target_persistence:.2f}",
                        "regime_confidence_delta": f"{confidence_delta:.2f}",
                        "transition_risk_grade": grade,
                        "safe_for_cross_jurisdiction_research": safe_cross,
                        "safe_for_shadow_research": safe_shadow,
                        "notes": f"{grade_label}. {OFFLINE_NOTES}",
                    }
                )

    transitions.sort(key=lambda row: (-parse_float(row.get("transition_strength")), -parse_float(row.get("transition_confidence")), clean(row.get("jurisdiction")), clean(row.get("track"))))
    return transitions


def build_matrix(transitions: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], dict[str, object]] = defaultdict(lambda: {"count": 0, "strength": 0.0, "confidence": 0.0, "types": Counter(), "grades": Counter()})
    for row in transitions:
        key = (clean(row.get("source_regime")), clean(row.get("target_regime")))
        bucket = buckets[key]
        bucket["count"] = int(bucket["count"]) + 1
        bucket["strength"] = float(bucket["strength"]) + parse_float(row.get("transition_strength"))
        bucket["confidence"] = float(bucket["confidence"]) + parse_float(row.get("transition_confidence"))
        bucket["types"][clean(row.get("transition_type"))] += 1  # type: ignore[index]
        bucket["grades"][clean(row.get("transition_risk_grade"))] += 1  # type: ignore[index]

    matrix: list[dict[str, object]] = []
    for (source, target), bucket in buckets.items():
        count = int(bucket["count"])
        grade_counts: Counter[str] = bucket["grades"]  # type: ignore[assignment]
        if grade_counts.get("A", 0):
            status = "STABLE_REPEATABLE_TRANSITION"
        elif grade_counts.get("B", 0):
            status = "USABLE_BEHAVIOURAL_TRANSITION"
        elif grade_counts.get("C", 0):
            status = "DESCRIPTIVE_TRANSITION"
        elif grade_counts.get("D", 0):
            status = "UNSTABLE_TRANSITION"
        else:
            status = "BLOCKED_TRANSITION"
        matrix.append(
            {
                "source_regime": source,
                "target_regime": target,
                "transition_count": str(count),
                "avg_transition_strength": f"{(float(bucket['strength']) / count if count else 0):.2f}",
                "avg_transition_confidence": f"{(float(bucket['confidence']) / count if count else 0):.2f}",
                "dominant_transition_type": bucket["types"].most_common(1)[0][0] if bucket["types"] else "",  # type: ignore[index,union-attr]
                "research_status": status,
                "notes": OFFLINE_NOTES,
            }
        )
    matrix.sort(key=lambda row: (-parse_int(row.get("transition_count")), -parse_float(row.get("avg_transition_strength")), clean(row.get("source_regime"))))
    return matrix


def build_instability_watchlist(transitions: list[dict[str, object]]) -> list[dict[str, object]]:
    watchlist: list[dict[str, object]] = []
    for row in transitions:
        grade = clean(row.get("transition_risk_grade"))
        transition = clean(row.get("transition_type"))
        strength = parse_float(row.get("transition_strength"))
        confidence = parse_float(row.get("transition_confidence"))
        if grade in {"F", "D"}:
            watchlist.append(
                {
                    "watch_type": "TRANSITION_STABILITY_BLOCKER",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "source_regime": row.get("source_regime", ""),
                    "target_regime": row.get("target_regime", ""),
                    "issue": "Transition is blocked or unstable under current ontology-memory evidence.",
                    "severity": "HIGH" if grade == "F" else "MEDIUM",
                    "affected_rows": row.get("transition_repeat_count", "0"),
                    "recommended_repair": "Improve regime confidence, reduce noise states, and accumulate repeatable transition evidence.",
                    "notes": OFFLINE_NOTES,
                }
            )
        elif transition in {"TELEMETRY_DECAY", "PRESSURE_COLLAPSE", "NOISE_TRANSITION"} and confidence < 70:
            watchlist.append(
                {
                    "watch_type": "TRANSITION_DECAY_OR_COLLAPSE",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "source_regime": row.get("source_regime", ""),
                    "target_regime": row.get("target_regime", ""),
                    "issue": f"{transition} detected with limited confidence.",
                    "severity": "MEDIUM",
                    "affected_rows": row.get("transition_repeat_count", "0"),
                    "recommended_repair": "Monitor transition recurrence and verify source telemetry lineage before interpretation.",
                    "notes": OFFLINE_NOTES,
                }
            )
        elif strength < 45 or confidence < 45:
            watchlist.append(
                {
                    "watch_type": "LOW_TRANSITION_EVIDENCE",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "source_regime": row.get("source_regime", ""),
                    "target_regime": row.get("target_regime", ""),
                    "issue": "Transition evidence is low-density or low-confidence.",
                    "severity": "LOW",
                    "affected_rows": row.get("transition_repeat_count", "0"),
                    "recommended_repair": "Keep as descriptive topology only until repeated evidence improves.",
                    "notes": OFFLINE_NOTES,
                }
            )
    watchlist.sort(key=lambda row: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(clean(row.get("severity")), 3), -parse_int(row.get("affected_rows"))))
    return watchlist


def status_count(transitions: list[dict[str, object]], grade: str) -> int:
    return sum(1 for row in transitions if clean(row.get("transition_risk_grade")) == grade)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    memory_rows = safe_read_csv(IN_MEMORY)
    dictionary_rows = safe_read_csv(IN_DICTIONARY)
    watchlist_rows = safe_read_csv(IN_WATCHLIST)

    transitions = build_transitions(memory_rows, watchlist_rows)
    matrix = build_matrix(transitions)
    instability = build_instability_watchlist(transitions)

    write_csv_atomic(OUT_TRANSITIONS, transitions, TRANSITION_FIELDS)
    write_csv_atomic(OUT_MATRIX, matrix, MATRIX_FIELDS)
    write_csv_atomic(OUT_WATCHLIST, instability, WATCHLIST_FIELDS)

    jurisdictions = {clean(row.get("jurisdiction")) for row in transitions if clean(row.get("jurisdiction"))}
    tracks = {clean(row.get("track")) for row in transitions if clean(row.get("track"))}
    safe_cross = sum(1 for row in transitions if clean(row.get("safe_for_cross_jurisdiction_research")) == "YES")
    safe_shadow = sum(1 for row in transitions if clean(row.get("safe_for_shadow_research")) == "YES")
    missing_inputs = [path.name for path in (IN_MEMORY, IN_DICTIONARY, IN_WATCHLIST) if not path.exists()]

    summary = [
        {"metric": "transition_rows", "value": str(len(transitions))},
        {"metric": "matrix_rows", "value": str(len(matrix))},
        {"metric": "instability_watchlist_rows", "value": str(len(instability))},
        {"metric": "stable_repeatable_transitions", "value": str(status_count(transitions, "A"))},
        {"metric": "usable_behavioural_transitions", "value": str(status_count(transitions, "B"))},
        {"metric": "descriptive_transitions", "value": str(status_count(transitions, "C"))},
        {"metric": "unstable_transitions", "value": str(status_count(transitions, "D"))},
        {"metric": "blocked_transitions", "value": str(status_count(transitions, "F"))},
        {"metric": "jurisdictions_covered", "value": str(len(jurisdictions))},
        {"metric": "tracks_covered", "value": str(len(tracks))},
        {"metric": "safe_cross_research_rows", "value": str(safe_cross)},
        {"metric": "safe_shadow_research_rows", "value": str(safe_shadow)},
        {"metric": "dictionary_rows_used", "value": str(len(dictionary_rows))},
        {"metric": "source_watchlist_rows_used", "value": str(len(watchlist_rows))},
        {"metric": "missing_inputs", "value": ";".join(missing_inputs)},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Regime transition rows: {len(transitions)}")
    print(f"Transition matrix rows: {len(matrix)}")
    print(f"Instability watchlist rows: {len(instability)}")
    print(f"Jurisdictions: {len(jurisdictions)}")
    print(f"Tracks: {len(tracks)}")


if __name__ == "__main__":
    main()
