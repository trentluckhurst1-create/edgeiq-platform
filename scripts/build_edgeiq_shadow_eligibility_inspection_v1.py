from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "governor": DATA / "edgeiq_research_governor_v1.csv",
    "backlog": DATA / "edgeiq_research_promotion_backlog_v1.csv",
    "evidence": DATA / "edgeiq_temporal_evidence_accumulator_v1.csv",
    "regime": DATA / "edgeiq_temporal_research_regime_engine_v1.csv",
    "opportunity": DATA / "edgeiq_temporal_regime_opportunity_map_v1.csv",
    "pattern_performance": DATA / "edgeiq_temporal_pattern_performance_v1.csv",
}

OUT = DATA / "edgeiq_shadow_eligibility_inspection_v1.csv"
SUMMARY = DATA / "edgeiq_shadow_eligibility_summary_v1.csv"

OUT_FIELDS = [
    "module_name",
    "source_file",
    "rows",
    "truth_source_grade",
    "sample_size_grade",
    "confidence_grade",
    "decision_utility_grade",
    "promotion_eligibility",
    "shadow_reason",
    "supporting_evidence",
    "remaining_blocker",
    "recommended_next_step",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


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
        return 0.0


def backlog_by_module() -> dict[str, dict[str, str]]:
    return {clean(row.get("module_name")): row for row in read_csv(INPUTS["backlog"])}


def evidence_summary() -> dict[str, object]:
    rows = read_csv(INPUTS["evidence"])
    statuses = Counter(clean(row.get("evidence_status")) for row in rows)
    total_sample = sum(to_int(row.get("sample_size")) for row in rows)
    matched = sum(to_int(row.get("matched_result_rows")) for row in rows)
    wins = sum(to_int(row.get("wins")) for row in rows)
    places = sum(to_int(row.get("places")) for row in rows)
    top4 = sum(to_int(row.get("top4")) for row in rows)
    max_sample = max([to_int(row.get("sample_size")) for row in rows] or [0])
    return {
        "rows": len(rows),
        "early_positive": statuses.get("EARLY_POSITIVE_SIGNAL", 0),
        "insufficient": statuses.get("INSUFFICIENT_EVIDENCE", 0),
        "total_sample": total_sample,
        "matched": matched,
        "wins": wins,
        "places": places,
        "top4": top4,
        "max_sample": max_sample,
    }


def regime_summary() -> dict[str, object]:
    rows = read_csv(INPUTS["regime"])
    labels = Counter(clean(row.get("regime_signal_grade")) or clean(row.get("regime_signal_label")) for row in rows)
    sample_ge_20 = sum(1 for row in rows if to_int(row.get("sample_size")) >= 20)
    return {
        "rows": len(rows),
        "positive": labels.get("REGIME_POSITIVE_EARLY", 0),
        "negative": labels.get("REGIME_NEGATIVE_EARLY", 0),
        "high_variance": labels.get("REGIME_HIGH_VARIANCE", 0),
        "insufficient": labels.get("INSUFFICIENT_SAMPLE", 0),
        "sample_ge_20": sample_ge_20,
    }


def opportunity_summary() -> dict[str, object]:
    rows = read_csv(INPUTS["opportunity"])
    priorities = Counter(clean(row.get("priority")) for row in rows)
    return {
        "rows": len(rows),
        "high": priorities.get("HIGH", 0),
        "medium": priorities.get("MEDIUM", 0),
        "low": priorities.get("LOW", 0),
    }


def pattern_summary() -> dict[str, object]:
    rows = read_csv(INPUTS["pattern_performance"])
    grades = Counter(clean(row.get("validation_grade")) for row in rows)
    matched = sum(to_int(row.get("matched_rows")) for row in rows)
    pending = sum(to_int(row.get("pending_or_missing_results")) for row in rows)
    top_pattern = ""
    top_place = -1.0
    for row in rows:
        place_rate = to_float(row.get("place_strike_rate"))
        if place_rate > top_place and to_int(row.get("matched_rows")) >= 50:
            top_place = place_rate
            top_pattern = f"{clean(row.get('phase_transition_pattern'))}/{clean(row.get('energy_curve_type'))}"
    return {
        "rows": len(rows),
        "historically_positive": grades.get("HISTORICALLY_POSITIVE", 0),
        "low_sample": grades.get("LOW_SAMPLE_PATTERN", 0),
        "matched": matched,
        "pending": pending,
        "top_pattern": top_pattern,
        "top_place": top_place,
    }


def shadow_reason(row: dict[str, str]) -> str:
    return (
        f"Governor marked {clean(row.get('module_name'))} as SHADOW_ELIGIBLE because truth={clean(row.get('truth_source_grade'))}, "
        f"sample={clean(row.get('sample_size_grade'))}, confidence={clean(row.get('confidence_grade'))}, "
        f"utility={clean(row.get('decision_utility_grade'))}; eligible for offline shadow review only."
    )


def supporting_evidence() -> str:
    ev = evidence_summary()
    rg = regime_summary()
    op = opportunity_summary()
    pp = pattern_summary()
    parts = [
        f"temporal evidence rows={ev['rows']}, matched rows={ev['matched']}, early positive signals={ev['early_positive']}, insufficient evidence rows={ev['insufficient']}",
        f"pattern performance rows={pp['rows']}, historically positive patterns={pp['historically_positive']}, low sample patterns={pp['low_sample']}, matched={pp['matched']}",
        f"regime rows={rg['rows']}, positive early regimes={rg['positive']}, negative early regimes={rg['negative']}, high variance regimes={rg['high_variance']}",
        f"opportunity rows={op['rows']}, high priority={op['high']}, medium priority={op['medium']}",
    ]
    if pp["top_pattern"]:
        parts.append(f"strongest observed place-rate pattern={pp['top_pattern']} at {pp['top_place']:.2f}% place rate")
    return " | ".join(parts)


def remaining_blocker(module: str, backlog: dict[str, dict[str, str]]) -> str:
    item = backlog.get(module, {})
    blocker = clean(item.get("promotion_blocker"))
    if blocker:
        return f"{blocker}; separate shadow validation and stability controls still required before any future live-modelling review."
    return "No backlog row found; live modelling remains blocked by governance default."


def recommended_next_step(module: str, backlog: dict[str, dict[str, str]]) -> str:
    item = backlog.get(module, {})
    step = clean(item.get("recommended_next_step"))
    if step:
        return step
    return "Run offline shadow-only evaluation with strict no-execution guardrails."


def build_rows() -> list[dict[str, object]]:
    governor_rows = read_csv(INPUTS["governor"])
    backlog = backlog_by_module()
    evidence = supporting_evidence()
    rows: list[dict[str, object]] = []
    for row in governor_rows:
        if clean(row.get("promotion_eligibility")) != "SHADOW_ELIGIBLE":
            continue
        module = clean(row.get("module_name"))
        rows.append(
            {
                "module_name": module,
                "source_file": clean(row.get("source_file")),
                "rows": clean(row.get("rows")),
                "truth_source_grade": clean(row.get("truth_source_grade")),
                "sample_size_grade": clean(row.get("sample_size_grade")),
                "confidence_grade": clean(row.get("confidence_grade")),
                "decision_utility_grade": clean(row.get("decision_utility_grade")),
                "promotion_eligibility": clean(row.get("promotion_eligibility")),
                "shadow_reason": shadow_reason(row),
                "supporting_evidence": evidence,
                "remaining_blocker": remaining_blocker(module, backlog),
                "recommended_next_step": recommended_next_step(module, backlog),
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Inspection only. No promotion, predictions, overlays, rated prices, live modelling, or execution changes.",
            }
        )
    return rows


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ev = evidence_summary()
    rg = regime_summary()
    op = opportunity_summary()
    pp = pattern_summary()
    missing = [path.name for path in INPUTS.values() if not path.exists()]
    summary: list[dict[str, object]] = [
        {"metric": "shadow_eligible_rows", "value": len(rows)},
        {"metric": "shadow_eligible_modules", "value": ";".join(clean(row.get("module_name")) for row in rows)},
        {"metric": "evidence_rows", "value": ev["rows"]},
        {"metric": "evidence_matched_rows", "value": ev["matched"]},
        {"metric": "evidence_early_positive_signals", "value": ev["early_positive"]},
        {"metric": "evidence_insufficient_rows", "value": ev["insufficient"]},
        {"metric": "pattern_performance_rows", "value": pp["rows"]},
        {"metric": "historically_positive_patterns", "value": pp["historically_positive"]},
        {"metric": "low_sample_patterns", "value": pp["low_sample"]},
        {"metric": "regime_positive_early", "value": rg["positive"]},
        {"metric": "regime_negative_early", "value": rg["negative"]},
        {"metric": "regime_high_variance", "value": rg["high_variance"]},
        {"metric": "opportunity_high_priority", "value": op["high"]},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "inspection_only", "value": "YES"},
    ]
    for filename in missing:
        summary.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return summary


def main() -> None:
    rows = build_rows()
    summary = build_summary(rows)
    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ SHADOW ELIGIBILITY INSPECTION V1")
    print("=" * 88)
    print(f"shadow eligible rows: {len(rows)}")
    for row in rows:
        print(f"shadow eligible module: {row['module_name']}")
        print(f"remaining blocker: {row['remaining_blocker']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")


if __name__ == "__main__":
    main()
