from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "inspection": DATA / "edgeiq_shadow_eligibility_inspection_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "pattern_performance": DATA / "edgeiq_temporal_pattern_performance_v1.csv",
    "regime": DATA / "edgeiq_temporal_research_regime_engine_v1.csv",
    "opportunity": DATA / "edgeiq_temporal_regime_opportunity_map_v1.csv",
}

OUT = DATA / "edgeiq_shadow_stability_controls_v1.csv"
SUMMARY = DATA / "edgeiq_shadow_stability_summary_v1.csv"

OUT_FIELDS = [
    "module_name",
    "control_name",
    "sample_size",
    "matched_rows",
    "risk_score",
    "stability_status",
    "stability_classification",
    "control_result",
    "evidence_summary",
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
        return math.nan


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.2f}"


def module_name() -> str:
    rows = read_csv(INPUTS["inspection"])
    for row in rows:
        if clean(row.get("promotion_eligibility")) == "SHADOW_ELIGIBLE":
            return clean(row.get("module_name"))
    return "temporal_physics_validation"


def validation_stats() -> dict[str, object]:
    rows = read_csv(INPUTS["validation"])
    matched = [row for row in rows if clean(row.get("finish_position"))]
    track_counts = Counter(clean(row.get("track")) or "UNKNOWN" for row in matched)
    pattern_counts = Counter(clean(row.get("phase_transition_pattern")) or "UNKNOWN" for row in matched)
    grade_counts = Counter(clean(row.get("validation_grade")) or "UNKNOWN" for row in matched)
    top_track, top_track_count = track_counts.most_common(1)[0] if track_counts else ("", 0)
    top_pattern, top_pattern_count = pattern_counts.most_common(1)[0] if pattern_counts else ("", 0)
    return {
        "total_rows": len(rows),
        "matched_rows": len(matched),
        "track_counts": track_counts,
        "pattern_counts": pattern_counts,
        "grade_counts": grade_counts,
        "top_track": top_track,
        "top_track_count": top_track_count,
        "top_pattern": top_pattern,
        "top_pattern_count": top_pattern_count,
        "track_concentration_pct": 0.0 if not matched else (top_track_count / len(matched)) * 100.0,
        "pattern_concentration_pct": 0.0 if not matched else (top_pattern_count / len(matched)) * 100.0,
    }


def pattern_stats() -> dict[str, object]:
    rows = read_csv(INPUTS["pattern_performance"])
    matched_rows = sum(to_int(row.get("matched_rows")) for row in rows)
    low_sample = sum(1 for row in rows if clean(row.get("validation_grade")) == "LOW_SAMPLE_PATTERN")
    positive = sum(1 for row in rows if clean(row.get("validation_grade")) == "HISTORICALLY_POSITIVE")
    risks = Counter(clean(row.get("pattern_risk")) or "UNKNOWN" for row in rows)
    high_risk = risks.get("HIGH", 0)
    place_rates = [to_float(row.get("place_strike_rate")) for row in rows if not math.isnan(to_float(row.get("place_strike_rate")))]
    variance_proxy = 0.0
    if place_rates:
        mean = sum(place_rates) / len(place_rates)
        variance_proxy = sum((value - mean) ** 2 for value in place_rates) / len(place_rates)
    return {
        "rows": len(rows),
        "matched_rows": matched_rows,
        "low_sample": low_sample,
        "positive": positive,
        "high_risk": high_risk,
        "place_rate_variance": variance_proxy,
    }


def regime_stats() -> dict[str, object]:
    rows = read_csv(INPUTS["regime"])
    grades = Counter(clean(row.get("regime_signal_grade")) or clean(row.get("regime_signal_label")) or "UNKNOWN" for row in rows)
    sample_rows = [row for row in rows if to_int(row.get("sample_size")) >= 20]
    by_type = Counter(clean(row.get("regime_type")) or "UNKNOWN" for row in rows)
    unknown_rows = sum(1 for row in rows if clean(row.get("regime_value")) == "UNKNOWN")
    return {
        "rows": len(rows),
        "sample_ge_20": len(sample_rows),
        "positive": grades.get("REGIME_POSITIVE_EARLY", 0),
        "negative": grades.get("REGIME_NEGATIVE_EARLY", 0),
        "high_variance": grades.get("REGIME_HIGH_VARIANCE", 0),
        "insufficient": grades.get("INSUFFICIENT_SAMPLE", 0),
        "unknown_rows": unknown_rows,
        "by_type": by_type,
    }


def opportunity_stats() -> dict[str, object]:
    rows = read_csv(INPUTS["opportunity"])
    priorities = Counter(clean(row.get("priority")) or "UNKNOWN" for row in rows)
    by_regime_type = Counter(clean(row.get("regime_type")) or "UNKNOWN" for row in rows)
    by_value = Counter(clean(row.get("regime_value")) or "UNKNOWN" for row in rows)
    top_value, top_value_count = by_value.most_common(1)[0] if by_value else ("", 0)
    return {
        "rows": len(rows),
        "high": priorities.get("HIGH", 0),
        "medium": priorities.get("MEDIUM", 0),
        "low": priorities.get("LOW", 0),
        "by_regime_type": by_regime_type,
        "top_value": top_value,
        "top_value_count": top_value_count,
        "top_value_pct": 0.0 if not rows else (top_value_count / len(rows)) * 100.0,
    }


def classify_sample_coverage(stats: dict[str, object]) -> dict[str, object]:
    matched = int(stats["matched_rows"])
    if matched < 500:
        classification = "INSUFFICIENT_STABILITY"
        status = "FAIL"
        risk = 90
        result = "Matched sample below minimum shadow stability floor."
    elif float(stats["track_concentration_pct"]) >= 60.0:
        classification = "CONCENTRATED_SAMPLE_RISK"
        status = "WARN"
        risk = 70
        result = "Matched sample is too concentrated in one track."
    elif float(stats["pattern_concentration_pct"]) >= 55.0:
        classification = "CONCENTRATED_SAMPLE_RISK"
        status = "WARN"
        risk = 60
        result = "Matched sample is too concentrated in one temporal pattern."
    else:
        classification = "STABLE_SHADOW_RESEARCH"
        status = "PASS"
        risk = 25
        result = "Matched sample is large enough for offline shadow stability review."
    return {
        "risk_score": risk,
        "stability_status": status,
        "stability_classification": classification,
        "control_result": result,
    }


def classify_pattern_variance(stats: dict[str, object]) -> dict[str, object]:
    variance = float(stats["place_rate_variance"])
    if int(stats["low_sample"]) > 0:
        classification = "INSUFFICIENT_STABILITY"
        status = "WARN"
        risk = 65
        result = "At least one temporal pattern remains low-sample."
    elif int(stats["high_risk"]) > 0 or variance >= 160.0:
        classification = "HIGH_VARIANCE_SHADOW"
        status = "WARN"
        risk = 70
        result = "Pattern outcome rates show high variance or high-risk pattern labels."
    else:
        classification = "STABLE_SHADOW_RESEARCH"
        status = "PASS"
        risk = 30
        result = "Pattern performance is stable enough for offline shadow review."
    return {
        "risk_score": risk,
        "stability_status": status,
        "stability_classification": classification,
        "control_result": result,
    }


def classify_regime_conflicts(stats: dict[str, object]) -> dict[str, object]:
    positive = int(stats["positive"])
    negative = int(stats["negative"])
    high_variance = int(stats["high_variance"])
    insufficient = int(stats["insufficient"])
    rows = int(stats["rows"])
    if rows <= 0:
        classification = "INSUFFICIENT_STABILITY"
        status = "FAIL"
        risk = 90
        result = "No regime rows available."
    elif insufficient > positive:
        classification = "INSUFFICIENT_STABILITY"
        status = "WARN"
        risk = 60
        result = "Many regime slices remain insufficient sample."
    elif negative > 0 or high_variance > 0:
        classification = "UNSTABLE_SHADOW_RESEARCH"
        status = "WARN"
        risk = 65
        result = "Positive regimes coexist with negative or high-variance regimes."
    else:
        classification = "STABLE_SHADOW_RESEARCH"
        status = "PASS"
        risk = 35
        result = "Regime layer has no observed negative or high-variance shadow conflict."
    return {
        "risk_score": risk,
        "stability_status": status,
        "stability_classification": classification,
        "control_result": result,
    }


def classify_opportunity_concentration(stats: dict[str, object]) -> dict[str, object]:
    rows = int(stats["rows"])
    top_pct = float(stats["top_value_pct"])
    if rows <= 0:
        classification = "INSUFFICIENT_STABILITY"
        status = "FAIL"
        risk = 90
        result = "No opportunity map rows available."
    elif top_pct >= 45.0:
        classification = "CONCENTRATED_SAMPLE_RISK"
        status = "WARN"
        risk = 68
        result = "Opportunity map is concentrated in one regime value."
    elif int(stats["high"]) <= 0:
        classification = "INSUFFICIENT_STABILITY"
        status = "WARN"
        risk = 55
        result = "No high-priority opportunity rows survived."
    else:
        classification = "STABLE_SHADOW_RESEARCH"
        status = "PASS"
        risk = 35
        result = "Opportunity map is broad enough for offline shadow review."
    return {
        "risk_score": risk,
        "stability_status": status,
        "stability_classification": classification,
        "control_result": result,
    }


def make_row(module: str, control: str, sample_size: int, matched_rows: int, classification: dict[str, object], evidence: str, blocker: str, next_step: str) -> dict[str, object]:
    return {
        "module_name": module,
        "control_name": control,
        "sample_size": sample_size,
        "matched_rows": matched_rows,
        "risk_score": classification["risk_score"],
        "stability_status": classification["stability_status"],
        "stability_classification": classification["stability_classification"],
        "control_result": classification["control_result"],
        "evidence_summary": evidence,
        "remaining_blocker": blocker,
        "recommended_next_step": next_step,
        "live_modelling_allowed": "NO",
        "live_execution_allowed": "NO",
        "notes": "Shadow stability control only. No promotion, overlays, ratings, live modelling, or execution.",
    }


def build_rows() -> list[dict[str, object]]:
    module = module_name()
    validation = validation_stats()
    patterns = pattern_stats()
    regimes = regime_stats()
    opportunities = opportunity_stats()
    blocker = "Offline shadow stability review only; live modelling remains blocked until separate holdout, stability, and governance reviews pass."
    next_step = "Run deeper offline holdout testing and concentration repair before any future live-modelling review."
    rows = [
        make_row(
            module,
            "MATCHED_SAMPLE_COVERAGE",
            int(validation["total_rows"]),
            int(validation["matched_rows"]),
            classify_sample_coverage(validation),
            f"matched_rows={validation['matched_rows']}; top_track={validation['top_track']} ({fmt(float(validation['track_concentration_pct']))}%); top_pattern={validation['top_pattern']} ({fmt(float(validation['pattern_concentration_pct']))}%)",
            blocker,
            next_step,
        ),
        make_row(
            module,
            "PATTERN_VARIANCE_CONTROL",
            int(patterns["rows"]),
            int(patterns["matched_rows"]),
            classify_pattern_variance(patterns),
            f"positive_patterns={patterns['positive']}; low_sample_patterns={patterns['low_sample']}; high_risk_patterns={patterns['high_risk']}; place_rate_variance={fmt(float(patterns['place_rate_variance']))}",
            blocker,
            next_step,
        ),
        make_row(
            module,
            "REGIME_CONFLICT_CONTROL",
            int(regimes["rows"]),
            int(regimes["sample_ge_20"]),
            classify_regime_conflicts(regimes),
            f"positive_regimes={regimes['positive']}; negative_regimes={regimes['negative']}; high_variance_regimes={regimes['high_variance']}; insufficient_regimes={regimes['insufficient']}; unknown_rows={regimes['unknown_rows']}",
            blocker,
            next_step,
        ),
        make_row(
            module,
            "OPPORTUNITY_CONCENTRATION_CONTROL",
            int(opportunities["rows"]),
            int(opportunities["high"]),
            classify_opportunity_concentration(opportunities),
            f"high_priority={opportunities['high']}; medium_priority={opportunities['medium']}; top_value={opportunities['top_value']} ({fmt(float(opportunities['top_value_pct']))}%)",
            blocker,
            next_step,
        ),
    ]
    return rows


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    classifications = Counter(clean(row.get("stability_classification")) for row in rows)
    statuses = Counter(clean(row.get("stability_status")) for row in rows)
    max_risk = max([to_int(row.get("risk_score")) for row in rows] or [0])
    if statuses.get("FAIL", 0) > 0:
        overall = "INSUFFICIENT_STABILITY"
    elif classifications.get("UNSTABLE_SHADOW_RESEARCH", 0) > 0:
        overall = "UNSTABLE_SHADOW_RESEARCH"
    elif classifications.get("CONCENTRATED_SAMPLE_RISK", 0) > 0:
        overall = "CONCENTRATED_SAMPLE_RISK"
    elif classifications.get("HIGH_VARIANCE_SHADOW", 0) > 0:
        overall = "HIGH_VARIANCE_SHADOW"
    elif classifications.get("INSUFFICIENT_STABILITY", 0) > 0:
        overall = "INSUFFICIENT_STABILITY"
    else:
        overall = "STABLE_SHADOW_RESEARCH"
    missing = [path.name for path in INPUTS.values() if not path.exists()]
    summary: list[dict[str, object]] = [
        {"metric": "control_rows", "value": len(rows)},
        {"metric": "overall_shadow_stability_classification", "value": overall},
        {"metric": "max_risk_score", "value": max_risk},
        {"metric": "stable_shadow_research", "value": classifications.get("STABLE_SHADOW_RESEARCH", 0)},
        {"metric": "unstable_shadow_research", "value": classifications.get("UNSTABLE_SHADOW_RESEARCH", 0)},
        {"metric": "concentrated_sample_risk", "value": classifications.get("CONCENTRATED_SAMPLE_RISK", 0)},
        {"metric": "high_variance_shadow", "value": classifications.get("HIGH_VARIANCE_SHADOW", 0)},
        {"metric": "insufficient_stability", "value": classifications.get("INSUFFICIENT_STABILITY", 0)},
        {"metric": "pass_controls", "value": statuses.get("PASS", 0)},
        {"metric": "warn_controls", "value": statuses.get("WARN", 0)},
        {"metric": "fail_controls", "value": statuses.get("FAIL", 0)},
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
    print("EDGEIQ SHADOW STABILITY CONTROLS V1")
    print("=" * 88)
    print(f"control rows: {len(rows)}")
    for row in summary:
        if row["metric"] in {"overall_shadow_stability_classification", "max_risk_score", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")


if __name__ == "__main__":
    main()
