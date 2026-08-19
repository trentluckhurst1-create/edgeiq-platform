from __future__ import annotations

from collections import Counter
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_BOARD = DATA / "edgeiq_research_priority_board_v1.csv"
IN_PRIORITY_SUMMARY = DATA / "edgeiq_research_priority_summary_v1.csv"
IN_WATCHLIST = DATA / "edgeiq_research_priority_watchlist_v1.csv"
IN_PROMOTIONS = DATA / "edgeiq_research_priority_promotions_v1.csv"
IN_LONGITUDINAL_SUMMARY = DATA / "edgeiq_longitudinal_evidence_summary_v1.csv"
IN_VALIDATION_SUMMARY = DATA / "edgeiq_regime_validation_summary_v1.csv"

OUT_FEED = DATA / "edgeiq_research_dashboard_feed_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_research_dashboard_summary_v1.csv"
OUT_TOP_PRIORITIES = DATA / "edgeiq_research_dashboard_top_priorities_v1.csv"
OUT_WATCHLIST = DATA / "edgeiq_research_dashboard_watchlist_v1.csv"

FEED_FIELDS = [
    "panel",
    "display_rank",
    "jurisdiction",
    "track",
    "regime_archetype",
    "transition_pair",
    "research_category",
    "priority_grade",
    "priority_status",
    "research_priority_score",
    "evidence_rows",
    "survival_score",
    "reinforcement_score",
    "avg_confidence",
    "confidence_decay_risk",
    "headline",
    "detail",
    "recommended_action",
    "severity",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

OFFLINE_NOTE = (
    "Dashboard feed only. Research promotion means evidence accumulation and telemetry observation; "
    "live modelling, ratings, overlays, betting, and execution remain disabled."
)


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


def fmt_float(value: object) -> str:
    parsed = parse_float(value)
    return f"{parsed:.2f}"


def read_metric_map(path: Path) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in safe_read_csv(path) if clean(row.get("metric"))}


def source_missing_notes(paths: list[Path]) -> str:
    missing = [path.name for path in paths if not path.exists()]
    if not missing:
        return ""
    return "Missing optional inputs: " + "; ".join(missing)


def base_feed_row(panel: str, display_rank: int = 0) -> dict[str, str]:
    return {
        "panel": panel,
        "display_rank": str(display_rank),
        "jurisdiction": "",
        "track": "",
        "regime_archetype": "",
        "transition_pair": "",
        "research_category": "",
        "priority_grade": "",
        "priority_status": "",
        "research_priority_score": "",
        "evidence_rows": "",
        "survival_score": "",
        "reinforcement_score": "",
        "avg_confidence": "",
        "confidence_decay_risk": "",
        "headline": "",
        "detail": "",
        "recommended_action": "",
        "severity": "",
        "live_modelling_allowed": "NO",
        "live_execution_allowed": "NO",
        "notes": OFFLINE_NOTE,
    }


def board_feed_row(panel: str, display_rank: int, row: dict[str, str], headline: str, severity: str) -> dict[str, str]:
    feed = base_feed_row(panel, display_rank)
    feed.update(
        {
            "jurisdiction": clean(row.get("jurisdiction")),
            "track": clean(row.get("track")),
            "regime_archetype": clean(row.get("regime_archetype")),
            "transition_pair": clean(row.get("transition_pair")),
            "research_category": clean(row.get("research_category")),
            "priority_grade": clean(row.get("priority_grade")),
            "priority_status": clean(row.get("priority_status")),
            "research_priority_score": fmt_float(row.get("research_priority_score")),
            "evidence_rows": str(parse_int(row.get("evidence_rows"))),
            "survival_score": fmt_float(row.get("survival_score")),
            "reinforcement_score": fmt_float(row.get("reinforcement_score")),
            "avg_confidence": fmt_float(row.get("avg_confidence")),
            "confidence_decay_risk": fmt_float(row.get("confidence_decay_risk")),
            "headline": headline,
            "detail": make_board_detail(row),
            "recommended_action": clean(row.get("recommended_next_action")),
            "severity": severity,
        }
    )
    return feed


def make_board_detail(row: dict[str, str]) -> str:
    parts = [
        f"Category {clean(row.get('research_category')) or '-'}",
        f"score {fmt_float(row.get('research_priority_score'))}",
        f"evidence rows {parse_int(row.get('evidence_rows'))}",
        f"survival {fmt_float(row.get('survival_score'))}",
        f"reinforcement {fmt_float(row.get('reinforcement_score'))}",
    ]
    if clean(row.get("transition_pair")):
        parts.append(f"transition {clean(row.get('transition_pair'))}")
    return "; ".join(parts)


def classify_headline(row: dict[str, str]) -> str:
    grade = clean(row.get("priority_grade"))
    category = clean(row.get("research_category"))
    regime = clean(row.get("regime_archetype")) or "Behavioural structure"
    track = clean(row.get("track"))
    jurisdiction = clean(row.get("jurisdiction"))
    location = " ".join(part for part in [jurisdiction, track] if part)
    if grade == "A":
        return f"Core research candidate: {regime} {location}".strip()
    if grade == "B":
        return f"High-priority research structure: {regime} {location}".strip()
    if category == "DURABLE_STRUCTURE":
        return f"Durable behavioural structure detected: {regime} {location}".strip()
    if category == "STRENGTHENING_STRUCTURE":
        return f"Strengthening behavioural structure: {regime} {location}".strip()
    if category == "NOISY_STRUCTURE":
        return f"Rejected noisy structure: {regime} {location}".strip()
    return f"Active research structure: {regime} {location}".strip()


def severity_for_board(row: dict[str, str]) -> str:
    grade = clean(row.get("priority_grade"))
    category = clean(row.get("research_category"))
    decay = parse_float(row.get("confidence_decay_risk"))
    if grade == "A":
        return "CRITICAL_RESEARCH"
    if grade == "B":
        return "HIGH"
    if category in {"DECAYING_STRUCTURE", "NOISY_STRUCTURE"} or decay >= 50:
        return "WATCH"
    if grade == "F":
        return "REJECTED"
    return "NORMAL"


def make_command_summary_rows(priority_summary: dict[str, str], longitudinal: dict[str, str], validation: dict[str, str]) -> list[dict[str, str]]:
    summary_items = [
        (
            "Research Priority Board",
            f"{priority_summary.get('priority_rows', '0')} ranked structures; {priority_summary.get('promotion_rows', '0')} research promotions queued.",
            "Use promotions for evidence accumulation only.",
            "NORMAL",
        ),
        (
            "Durability Status",
            f"{priority_summary.get('durable_structures_detected', '0')} durable and {priority_summary.get('strengthening_structures_detected', '0')} strengthening structures detected.",
            "Keep accumulating telemetry before any modelling review.",
            "HIGH" if parse_int(priority_summary.get("high_research_priorities")) else "NORMAL",
        ),
        (
            "Noise Rejection",
            f"{priority_summary.get('rejected_structures', '0')} rejected structures; {priority_summary.get('watchlist_rows', '0')} watchlist issues.",
            "Repair rejected/noisy telemetry before future research attention.",
            "WATCH",
        ),
        (
            "Longitudinal Evidence",
            f"{longitudinal.get('longitudinal_rows', '0')} longitudinal rows; {longitudinal.get('surviving_structures', '0')} surviving structures.",
            "Track survival, reinforcement, confidence decay, and recurrence.",
            "NORMAL",
        ),
        (
            "Validation Health",
            f"{validation.get('promising_repeating_behaviours', '0')} promising behaviours; {validation.get('rejected_noisy_structures', '0')} noisy structures rejected.",
            "Promotion remains research attention only.",
            "NORMAL",
        ),
    ]
    rows: list[dict[str, str]] = []
    for index, (headline, detail, action, severity) in enumerate(summary_items, start=1):
        row = base_feed_row("COMMAND_SUMMARY", index)
        row.update(
            {
                "headline": headline,
                "detail": detail,
                "recommended_action": action,
                "severity": severity,
                "priority_status": "RESEARCH_ONLY",
            }
        )
        rows.append(row)
    return rows


def make_health_rows(panel: str, metrics: dict[str, str], entries: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, (headline, metric_key, action) in enumerate(entries, start=1):
        row = base_feed_row(panel, index)
        row.update(
            {
                "headline": headline,
                "detail": f"{metric_key}: {metrics.get(metric_key, '0')}",
                "recommended_action": action,
                "severity": "NORMAL",
                "priority_status": "RESEARCH_ONLY",
            }
        )
        rows.append(row)
    return rows


def watchlist_feed_row(display_rank: int, row: dict[str, str]) -> dict[str, str]:
    feed = base_feed_row("WATCHLIST", display_rank)
    severity = clean(row.get("severity")) or "WATCH"
    feed.update(
        {
            "jurisdiction": clean(row.get("jurisdiction")),
            "track": clean(row.get("track")),
            "regime_archetype": clean(row.get("regime_archetype")),
            "research_category": clean(row.get("watch_type")),
            "evidence_rows": str(parse_int(row.get("affected_rows"))),
            "headline": clean(row.get("issue")) or "Research watchlist issue",
            "detail": f"{clean(row.get('watch_type'))}; affected rows {parse_int(row.get('affected_rows'))}",
            "recommended_action": clean(row.get("recommended_repair")),
            "severity": severity,
            "priority_status": "WATCH_DECAY" if severity in {"HIGH", "CRITICAL"} else "MONITOR",
        }
    )
    return feed


def sort_board_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (
            parse_int(row.get("priority_rank")) or 999999,
            -parse_float(row.get("research_priority_score")),
            clean(row.get("jurisdiction")),
            clean(row.get("track")),
            clean(row.get("regime_archetype")),
        ),
    )


def compact_board_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    compacted: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for row in sort_board_rows(rows):
        key = (
            clean(row.get("jurisdiction")).upper(),
            clean(row.get("track")).upper(),
            clean(row.get("regime_archetype")).upper(),
            clean(row.get("transition_pair")).upper(),
            clean(row.get("research_category")).upper(),
            clean(row.get("priority_grade")).upper(),
        )
        if key in seen:
            continue
        seen.add(key)
        compacted.append(row)
    return compacted


def build_dashboard() -> None:
    inputs = [
        IN_BOARD,
        IN_PRIORITY_SUMMARY,
        IN_WATCHLIST,
        IN_PROMOTIONS,
        IN_LONGITUDINAL_SUMMARY,
        IN_VALIDATION_SUMMARY,
    ]
    source_board_rows = sort_board_rows(safe_read_csv(IN_BOARD))
    board_rows = compact_board_rows(source_board_rows)
    watchlist_rows_raw = safe_read_csv(IN_WATCHLIST)
    priority_summary = read_metric_map(IN_PRIORITY_SUMMARY)
    longitudinal_summary = read_metric_map(IN_LONGITUDINAL_SUMMARY)
    validation_summary = read_metric_map(IN_VALIDATION_SUMMARY)

    feed_rows: list[dict[str, str]] = []
    feed_rows.extend(make_command_summary_rows(priority_summary, longitudinal_summary, validation_summary))

    top_priority_rows = [
        board_feed_row(
            "TOP_RESEARCH_PRIORITIES",
            index,
            row,
            classify_headline(row),
            severity_for_board(row),
        )
        for index, row in enumerate(board_rows[:25], start=1)
    ]
    feed_rows.extend(top_priority_rows)

    durable_rows = [row for row in board_rows if clean(row.get("research_category")) == "DURABLE_STRUCTURE"]
    strengthening_rows = [row for row in board_rows if clean(row.get("research_category")) == "STRENGTHENING_STRUCTURE"]
    active_rows = [row for row in board_rows if clean(row.get("priority_grade")) == "C"]
    rejected_rows = [row for row in board_rows if clean(row.get("priority_grade")) == "F" or clean(row.get("research_category")) == "NOISY_STRUCTURE"]

    for index, row in enumerate(durable_rows[:10], start=1):
        feed_rows.append(board_feed_row("DURABLE_STRUCTURE", index, row, classify_headline(row), "HIGH"))

    for index, row in enumerate(strengthening_rows[:20], start=1):
        feed_rows.append(board_feed_row("STRENGTHENING_STRUCTURES", index, row, classify_headline(row), "HIGH"))

    for index, row in enumerate(active_rows[:30], start=1):
        feed_rows.append(board_feed_row("ACTIVE_RESEARCH", index, row, classify_headline(row), "NORMAL"))

    for index, row in enumerate(rejected_rows[:20], start=1):
        feed_rows.append(board_feed_row("REJECTED_NOISE", index, row, classify_headline(row), "REJECTED"))

    watchlist_rows = [
        watchlist_feed_row(index, row)
        for index, row in enumerate(
            sorted(watchlist_rows_raw, key=lambda item: (-parse_int(item.get("affected_rows")), clean(item.get("track"))))[:50],
            start=1,
        )
    ]
    feed_rows.extend(watchlist_rows)

    feed_rows.extend(
        make_health_rows(
            "VALIDATION_HEALTH",
            validation_summary,
            [
                ("Promising repeating behaviours", "promising_repeating_behaviours", "Keep in research backlog until persistence improves."),
                ("Rejected noisy structures", "rejected_noisy_structures", "Keep rejected structures out of modelling review."),
                ("Failure rows", "failure_rows", "Prioritise source and ontology repairs."),
            ],
        )
    )
    feed_rows.extend(
        make_health_rows(
            "LONGITUDINAL_HEALTH",
            longitudinal_summary,
            [
                ("Durable behavioural structures", "durable_behavioural_structures", "Continue longitudinal observation."),
                ("Stable emerging structures", "stable_emerging_structures", "Accumulate repeated evidence."),
                ("Weak or decaying structures", "weak_or_decaying_structures", "Watch confidence decay and survival drift."),
            ],
        )
    )

    missing_note = source_missing_notes(inputs)
    if missing_note:
        row = base_feed_row("COMMAND_SUMMARY", len(feed_rows) + 1)
        row.update(
            {
                "headline": "Missing dashboard input",
                "detail": missing_note,
                "recommended_action": "Regenerate the missing research inputs before dashboard review.",
                "severity": "WATCH",
                "priority_status": "MONITOR",
            }
        )
        feed_rows.append(row)

    panel_counts = Counter(row["panel"] for row in feed_rows)
    grade_counts = Counter(clean(row.get("priority_grade")) for row in board_rows)
    category_counts = Counter(clean(row.get("research_category")) for row in board_rows)

    summary_rows = [
        {"metric": "dashboard_rows", "value": str(len(feed_rows))},
        {"metric": "top_priority_rows", "value": str(len(top_priority_rows))},
        {"metric": "watchlist_rows", "value": str(len(watchlist_rows))},
        {"metric": "durable_structure_rows", "value": str(panel_counts.get("DURABLE_STRUCTURE", 0))},
        {"metric": "strengthening_structure_rows", "value": str(panel_counts.get("STRENGTHENING_STRUCTURES", 0))},
        {"metric": "active_research_rows", "value": str(panel_counts.get("ACTIVE_RESEARCH", 0))},
        {"metric": "rejected_noise_rows", "value": str(panel_counts.get("REJECTED_NOISE", 0))},
        {"metric": "source_priority_rows", "value": str(len(source_board_rows))},
        {"metric": "compact_priority_rows", "value": str(len(board_rows))},
        {"metric": "source_watchlist_rows", "value": str(len(watchlist_rows_raw))},
        {"metric": "source_a_grade_rows", "value": str(grade_counts.get("A", 0))},
        {"metric": "source_b_grade_rows", "value": str(grade_counts.get("B", 0))},
        {"metric": "source_c_grade_rows", "value": str(grade_counts.get("C", 0))},
        {"metric": "source_d_grade_rows", "value": str(grade_counts.get("D", 0))},
        {"metric": "source_f_grade_rows", "value": str(grade_counts.get("F", 0))},
        {"metric": "source_durable_structures", "value": str(category_counts.get("DURABLE_STRUCTURE", 0))},
        {"metric": "source_strengthening_structures", "value": str(category_counts.get("STRENGTHENING_STRUCTURE", 0))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv_atomic(OUT_FEED, feed_rows, FEED_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv_atomic(OUT_TOP_PRIORITIES, top_priority_rows, FEED_FIELDS)
    write_csv_atomic(OUT_WATCHLIST, watchlist_rows, FEED_FIELDS)

    print(f"Research dashboard rows: {len(feed_rows)}")
    print(f"Top priority rows: {len(top_priority_rows)}")
    print(f"Watchlist rows: {len(watchlist_rows)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_dashboard()
