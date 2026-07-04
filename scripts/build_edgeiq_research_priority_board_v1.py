from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_EVIDENCE = DATA / "edgeiq_longitudinal_evidence_accumulation_v1.csv"
IN_SURVIVAL = DATA / "edgeiq_longitudinal_regime_survival_v1.csv"
IN_RECURRENCE = DATA / "edgeiq_longitudinal_transition_recurrence_v1.csv"
IN_DECAY = DATA / "edgeiq_longitudinal_confidence_decay_v1.csv"
IN_VALIDATION = DATA / "edgeiq_regime_validation_lab_v1.csv"
IN_TRANSITIONS = DATA / "edgeiq_regime_transition_memory_v1.csv"

OUT_BOARD = DATA / "edgeiq_research_priority_board_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_research_priority_summary_v1.csv"
OUT_WATCHLIST = DATA / "edgeiq_research_priority_watchlist_v1.csv"
OUT_PROMOTIONS = DATA / "edgeiq_research_priority_promotions_v1.csv"

BOARD_FIELDS = [
    "priority_rank",
    "jurisdiction",
    "track",
    "regime_archetype",
    "transition_pair",
    "research_category",
    "evidence_rows",
    "repeat_count",
    "survival_score",
    "reinforcement_score",
    "recurrence_score",
    "cross_jurisdiction_support",
    "avg_confidence",
    "confidence_health",
    "confidence_decay_risk",
    "repeatability_score",
    "transition_stability",
    "research_priority_score",
    "priority_grade",
    "priority_status",
    "recommended_next_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

WATCHLIST_FIELDS = [
    "watch_type",
    "jurisdiction",
    "track",
    "regime_archetype",
    "issue",
    "severity",
    "affected_rows",
    "recommended_repair",
    "notes",
]

PROMOTION_FIELDS = BOARD_FIELDS

OFFLINE_NOTES = "Research priority board only. Promotion means research attention and evidence accumulation, not live modelling, ratings, overlays, betting, or execution."


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


def survival_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {clean(row.get("regime_archetype")): row for row in rows if clean(row.get("regime_archetype"))}


def recurrence_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {clean(row.get("transition_pair")): row for row in rows if clean(row.get("transition_pair"))}


def decay_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, float | str]]:
    buckets: dict[tuple[str, str], dict[str, object]] = defaultdict(lambda: {"decays": [], "deltas": [], "health": Counter()})
    for row in rows:
        regime = clean(row.get("regime_archetype"))
        pair = clean(row.get("transition_pair"))
        key = (regime, pair)
        buckets[key]["decays"].append(parse_float(row.get("decay_risk")))  # type: ignore[index,union-attr]
        buckets[key]["deltas"].append(parse_float(row.get("confidence_delta")))  # type: ignore[index,union-attr]
        buckets[key]["health"][clean(row.get("confidence_health")) or "UNKNOWN"] += 1  # type: ignore[index]
    output: dict[tuple[str, str], dict[str, float | str]] = {}
    for key, bucket in buckets.items():
        health_counter: Counter[str] = bucket["health"]  # type: ignore[assignment]
        output[key] = {
            "decay_risk": avg(bucket["decays"]),  # type: ignore[arg-type]
            "confidence_delta": avg(bucket["deltas"]),  # type: ignore[arg-type]
            "confidence_health": health_counter.most_common(1)[0][0] if health_counter else "UNKNOWN",
        }
    return output


def validation_repeatability(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], float]:
    output: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        key = (
            clean(row.get("jurisdiction")),
            clean(row.get("track")),
            clean(row.get("regime_archetype")),
            clean(row.get("transition_pair")),
        )
        output[key].append(parse_float(row.get("repeatability_score")))
    return {key: avg(values) for key, values in output.items()}


def transition_stability_index(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], str]:
    index: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in rows:
        key = (clean(row.get("jurisdiction")), clean(row.get("track")), clean(row.get("source_regime")) + "->" + clean(row.get("target_regime")))
        index[key].append(clean(row.get("transition_stability")) or "UNKNOWN")
    result: dict[tuple[str, str, str], str] = {}
    for key, values in index.items():
        result[key] = Counter(values).most_common(1)[0][0]
    return result


def research_category(row: dict[str, str]) -> str:
    status = clean(row.get("longitudinal_status"))
    grade = clean(row.get("longitudinal_grade"))
    if grade == "A":
        return "DURABLE_STRUCTURE"
    if status == "STRENGTHENING":
        return "STRENGTHENING_STRUCTURE"
    if status == "SURVIVING":
        return "SURVIVING_STRUCTURE"
    if status == "DECAYING":
        return "DECAYING_STRUCTURE"
    if status == "NOISY" or grade == "F":
        return "NOISY_STRUCTURE"
    return "OBSERVATIONAL_STRUCTURE"


def priority_score(
    evidence_row: dict[str, str],
    survival_row: dict[str, str],
    recurrence_row: dict[str, str],
    decay_info: dict[str, float | str],
    repeatability: float,
) -> float:
    survival = parse_float(evidence_row.get("survival_score"))
    reinforcement = parse_float(evidence_row.get("reinforcement_score"))
    recurrence = parse_float(recurrence_row.get("avg_repeatability")) if recurrence_row else 0.0
    cross = min(12.0, parse_int(evidence_row.get("cross_jurisdiction_support")) * 4.0)
    confidence = parse_float(evidence_row.get("avg_confidence"))
    survival_global = parse_float(survival_row.get("survival_score")) if survival_row else 0.0
    decay = float(decay_info.get("decay_risk", 0.0))
    grade_bonus = {"A": 12.0, "B": 8.0, "C": 2.0, "D": -8.0, "F": -20.0}.get(clean(evidence_row.get("longitudinal_grade")), 0.0)
    score = (
        survival * 0.22
        + reinforcement * 0.22
        + recurrence * 0.12
        + confidence * 0.14
        + repeatability * 0.13
        + survival_global * 0.07
        + cross
        + grade_bonus
        - decay * 0.16
    )
    return round(clamp(score), 2)


def priority_grade_and_status(score: float, category: str, decay: float, health: str) -> tuple[str, str]:
    if category == "NOISY_STRUCTURE" or decay >= 85 or health == "UNHEALTHY":
        return "F", "REJECT"
    if score >= 82 and category == "DURABLE_STRUCTURE":
        return "A", "PROMOTE_RESEARCH"
    if score >= 68 and category in {"DURABLE_STRUCTURE", "STRENGTHENING_STRUCTURE", "SURVIVING_STRUCTURE"}:
        return "B", "ACCUMULATE_EVIDENCE"
    if score >= 48 and category in {"STRENGTHENING_STRUCTURE", "SURVIVING_STRUCTURE", "OBSERVATIONAL_STRUCTURE"}:
        return "C", "MONITOR"
    if category == "DECAYING_STRUCTURE" or decay >= 60:
        return "D", "WATCH_DECAY"
    if score < 28:
        return "F", "REJECT"
    return "D", "BLOCK_PROMOTION"


def next_action(grade: str, status: str, category: str, transition_pair: str) -> str:
    subject = "transition" if transition_pair else "regime"
    if grade == "A":
        return f"Core offline research priority: intensify evidence accumulation for this {subject}; no live modelling."
    if grade == "B":
        return f"High research priority: schedule repeated telemetry observation for this {subject}."
    if status == "MONITOR":
        return f"Active research monitor: keep collecting evidence and watch stability."
    if status == "WATCH_DECAY":
        return f"Decay watch: inspect confidence health and ontology drift before further attention."
    if status == "BLOCK_PROMOTION":
        return f"Block promotion until repeatability, survival, and confidence health improve."
    return f"Reject or quarantine from priority research until noise/source quality is repaired."


def build_board(
    evidence_rows: list[dict[str, str]],
    survival_rows: list[dict[str, str]],
    recurrence_rows: list[dict[str, str]],
    decay_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
    transition_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    survival = survival_index(survival_rows)
    recurrence = recurrence_index(recurrence_rows)
    decay = decay_index(decay_rows)
    repeatability = validation_repeatability(validation_rows)
    transition_stability = transition_stability_index(transition_rows)
    board: list[dict[str, object]] = []

    for row in evidence_rows:
        jurisdiction = clean(row.get("jurisdiction"))
        track = clean(row.get("track"))
        regime = clean(row.get("regime_archetype"))
        pair = clean(row.get("transition_pair"))
        category = research_category(row)
        decay_info = decay.get((regime, pair), {"decay_risk": parse_float(row.get("decay_risk")), "confidence_delta": parse_float(row.get("confidence_delta")), "confidence_health": "UNKNOWN"})
        repeat_score = repeatability.get((jurisdiction, track, regime, pair), parse_float(row.get("reinforcement_score")))
        recur_row = recurrence.get(pair, {})
        survival_row = survival.get(regime, {})
        score = priority_score(row, survival_row, recur_row, decay_info, repeat_score)
        decay_risk = float(decay_info.get("decay_risk", 0.0))
        health = str(decay_info.get("confidence_health", "UNKNOWN"))
        grade, status = priority_grade_and_status(score, category, decay_risk, health)
        stability = transition_stability.get((jurisdiction, track, pair), "") if pair else ""
        board.append(
            {
                "priority_rank": "0",
                "jurisdiction": jurisdiction,
                "track": track,
                "regime_archetype": regime,
                "transition_pair": pair,
                "research_category": category,
                "evidence_rows": row.get("evidence_rows", "0"),
                "repeat_count": row.get("repeat_count", "0"),
                "survival_score": row.get("survival_score", "0"),
                "reinforcement_score": row.get("reinforcement_score", "0"),
                "recurrence_score": recur_row.get("avg_repeatability", "") if recur_row else "",
                "cross_jurisdiction_support": row.get("cross_jurisdiction_support", "0"),
                "avg_confidence": row.get("avg_confidence", "0"),
                "confidence_health": health,
                "confidence_decay_risk": f"{decay_risk:.2f}",
                "repeatability_score": f"{repeat_score:.2f}",
                "transition_stability": stability,
                "research_priority_score": f"{score:.2f}",
                "priority_grade": grade,
                "priority_status": status,
                "recommended_next_action": next_action(grade, status, category, pair),
                "notes": OFFLINE_NOTES,
            }
        )

    board.sort(key=lambda item: ({"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}.get(clean(item.get("priority_grade")), 5), -parse_float(item.get("research_priority_score")), clean(item.get("jurisdiction")), clean(item.get("track"))))
    for index, row in enumerate(board, start=1):
        row["priority_rank"] = str(index)
    return board


def build_watchlist(board_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    watchlist: list[dict[str, object]] = []
    for row in board_rows:
        grade = clean(row.get("priority_grade"))
        status = clean(row.get("priority_status"))
        category = clean(row.get("research_category"))
        decay = parse_float(row.get("confidence_decay_risk"))
        affected = clean(row.get("evidence_rows"))
        if grade == "F":
            watchlist.append(
                {
                    "watch_type": "REJECTED_RESEARCH_STRUCTURE",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "regime_archetype": row.get("regime_archetype", "") or row.get("transition_pair", ""),
                    "issue": "Structure is noisy, unhealthy, or rejected from research priority.",
                    "severity": "HIGH",
                    "affected_rows": affected,
                    "recommended_repair": "Repair ontology/source confidence and rerun validation before future research attention.",
                    "notes": OFFLINE_NOTES,
                }
            )
        elif status == "WATCH_DECAY" or category == "DECAYING_STRUCTURE" or decay >= 60:
            watchlist.append(
                {
                    "watch_type": "DECAY_RISK",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "regime_archetype": row.get("regime_archetype", "") or row.get("transition_pair", ""),
                    "issue": "Priority candidate shows confidence decay or weakening evidence.",
                    "severity": "MEDIUM",
                    "affected_rows": affected,
                    "recommended_repair": "Monitor confidence health and accumulate cleaner repeated observations.",
                    "notes": OFFLINE_NOTES,
                }
            )
        elif grade == "D":
            watchlist.append(
                {
                    "watch_type": "LOW_PRIORITY_BLOCKER",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "regime_archetype": row.get("regime_archetype", "") or row.get("transition_pair", ""),
                    "issue": "Evidence not strong enough for active research priority.",
                    "severity": "LOW",
                    "affected_rows": affected,
                    "recommended_repair": "Keep in low-priority monitor until repeatability or confidence improves.",
                    "notes": OFFLINE_NOTES,
                }
            )
    watchlist.sort(key=lambda item: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(clean(item.get("severity")), 3), -parse_int(item.get("affected_rows"))))
    return watchlist


def build_promotions(board_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in board_rows if clean(row.get("priority_grade")) in {"A", "B"}]


def count_grade(rows: list[dict[str, object]], grade: str) -> int:
    return sum(1 for row in rows if clean(row.get("priority_grade")) == grade)


def count_category(rows: list[dict[str, object]], category: str) -> int:
    return sum(1 for row in rows if clean(row.get("research_category")) == category)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    evidence_rows = safe_read_csv(IN_EVIDENCE)
    survival_rows = safe_read_csv(IN_SURVIVAL)
    recurrence_rows = safe_read_csv(IN_RECURRENCE)
    decay_rows = safe_read_csv(IN_DECAY)
    validation_rows = safe_read_csv(IN_VALIDATION)
    transition_rows = safe_read_csv(IN_TRANSITIONS)

    board = build_board(evidence_rows, survival_rows, recurrence_rows, decay_rows, validation_rows, transition_rows)
    watchlist = build_watchlist(board)
    promotions = build_promotions(board)

    write_csv_atomic(OUT_BOARD, board, BOARD_FIELDS)
    write_csv_atomic(OUT_WATCHLIST, watchlist, WATCHLIST_FIELDS)
    write_csv_atomic(OUT_PROMOTIONS, promotions, PROMOTION_FIELDS)

    summary = [
        {"metric": "priority_rows", "value": str(len(board))},
        {"metric": "core_research_priorities", "value": str(count_grade(board, "A"))},
        {"metric": "high_research_priorities", "value": str(count_grade(board, "B"))},
        {"metric": "active_research_structures", "value": str(count_grade(board, "C"))},
        {"metric": "low_priority_monitor_structures", "value": str(count_grade(board, "D"))},
        {"metric": "rejected_structures", "value": str(count_grade(board, "F"))},
        {"metric": "promotion_rows", "value": str(len(promotions))},
        {"metric": "watchlist_rows", "value": str(len(watchlist))},
        {"metric": "durable_structures_detected", "value": str(count_category(board, "DURABLE_STRUCTURE"))},
        {"metric": "strengthening_structures_detected", "value": str(count_category(board, "STRENGTHENING_STRUCTURE"))},
        {"metric": "surviving_structures_detected", "value": str(count_category(board, "SURVIVING_STRUCTURE"))},
        {"metric": "decaying_structures_detected", "value": str(count_category(board, "DECAYING_STRUCTURE"))},
        {"metric": "noisy_structures_detected", "value": str(count_category(board, "NOISY_STRUCTURE"))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Research priority rows: {len(board)}")
    print(f"Promotion rows: {len(promotions)}")
    print(f"Watchlist rows: {len(watchlist)}")


if __name__ == "__main__":
    main()
