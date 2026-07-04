from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MODULES = [
    {
        "module_name": "canonical_results_truth",
        "source_file": "edgeiq_canonical_results_truth_summary_v1.csv",
        "path": DATA / "edgeiq_canonical_results_truth_summary_v1.csv",
        "kind": "canonical_truth",
        "utility": "truth_foundation",
    },
    {
        "module_name": "real_sectional_physics_features",
        "source_file": "edgeiq_real_sectional_physics_features_v1.csv",
        "path": DATA / "edgeiq_real_sectional_physics_features_v1.csv",
        "kind": "real_measured_physics",
        "utility": "uncertainty_reduction",
    },
    {
        "module_name": "temporal_physics_validation",
        "source_file": "edgeiq_temporal_physics_validation_v1.csv",
        "path": DATA / "edgeiq_temporal_physics_validation_v1.csv",
        "summary_path": DATA / "edgeiq_temporal_physics_validation_summary_v1.csv",
        "kind": "validated_research",
        "utility": "validation_research",
    },
    {
        "module_name": "temporal_evidence_accumulator",
        "source_file": "edgeiq_temporal_evidence_accumulator_v1.csv",
        "path": DATA / "edgeiq_temporal_evidence_accumulator_v1.csv",
        "summary_path": DATA / "edgeiq_temporal_evidence_summary_v1.csv",
        "kind": "validated_research",
        "utility": "longitudinal_research",
    },
    {
        "module_name": "temporal_research_regime",
        "source_file": "edgeiq_temporal_research_regime_engine_v1.csv",
        "path": DATA / "edgeiq_temporal_research_regime_engine_v1.csv",
        "summary_path": DATA / "edgeiq_temporal_research_regime_summary_v1.csv",
        "kind": "conditional_research",
        "utility": "conditional_research",
    },
    {
        "module_name": "temporal_identity_memory",
        "source_file": "edgeiq_temporal_identity_memory_v1.csv",
        "path": DATA / "edgeiq_temporal_identity_memory_v1.csv",
        "summary_path": DATA / "edgeiq_temporal_identity_memory_summary_v1.csv",
        "kind": "identity_research",
        "utility": "descriptive_memory",
    },
    {
        "module_name": "temporal_memory_evolution",
        "source_file": "edgeiq_temporal_memory_evolution_v1.csv",
        "path": DATA / "edgeiq_temporal_memory_evolution_v1.csv",
        "summary_path": DATA / "edgeiq_temporal_memory_evolution_summary_v1.csv",
        "kind": "identity_research",
        "utility": "descriptive_memory",
    },
    {
        "module_name": "probability_realism",
        "source_file": "edgeiq_sectional_probability_realism_summary_v1.csv",
        "path": DATA / "edgeiq_sectional_probability_realism_summary_v1.csv",
        "kind": "derived_research",
        "utility": "diagnostic",
    },
]

OUT = DATA / "edgeiq_research_governor_v1.csv"
SUMMARY = DATA / "edgeiq_research_governor_summary_v1.csv"
BACKLOG = DATA / "edgeiq_research_promotion_backlog_v1.csv"

GOVERNOR_FIELDS = [
    "module_name",
    "source_file",
    "rows",
    "truth_source_grade",
    "sample_size_grade",
    "confidence_grade",
    "decision_utility_grade",
    "promotion_eligibility",
    "research_status",
    "live_modelling_allowed",
    "live_execution_allowed",
    "primary_blocker",
    "recommended_next_step",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

BACKLOG_FIELDS = [
    "priority",
    "module_name",
    "promotion_blocker",
    "required_evidence",
    "current_status",
    "recommended_next_step",
    "notes",
]


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


def summary_map(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    values: dict[str, str] = {}
    for row in read_csv(path):
        metric = clean(row.get("metric"))
        value = clean(row.get("value"))
        if metric:
            values[metric] = value
    return values


def int_metric(metrics: dict[str, str], key: str, default: int = 0) -> int:
    value = clean(metrics.get(key))
    if not value:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def grade_sample(rows: int) -> str:
    if rows >= 5000:
        return "A"
    if rows >= 1000:
        return "B"
    if rows >= 250:
        return "C"
    if rows >= 50:
        return "D"
    return "F"


def grade_truth(module: dict[str, object], metrics: dict[str, str], rows: int, missing: bool) -> str:
    if missing or rows <= 0:
        return "F"
    kind = str(module["kind"])
    if kind in {"canonical_truth", "real_measured_physics"}:
        return "A"
    if kind == "validated_research":
        matched = int_metric(metrics, "outcome_matched_rows") or int_metric(metrics, "validated_rows")
        return "B" if matched > 0 else "C"
    if kind in {"conditional_research", "identity_research"}:
        return "C"
    if kind == "derived_research":
        return "C"
    return "D"


def grade_confidence(module: dict[str, object], metrics: dict[str, str], rows: int, missing: bool) -> str:
    if missing or rows <= 0:
        return "F"
    name = str(module["module_name"])
    if name == "canonical_results_truth":
        trusted = int_metric(metrics, "trusted_results")
        conflicts = int_metric(metrics, "conflict_results")
        return "A" if trusted >= 1000 and conflicts == 0 else "B" if trusted > 0 else "D"
    if name == "real_sectional_physics_features":
        return "A" if rows >= 5000 else "B"
    if name == "temporal_physics_validation":
        matched = int_metric(metrics, "outcome_matched_rows")
        if matched >= 500:
            return "B"
        if matched > 0:
            return "D"
        return "F"
    if name == "temporal_evidence_accumulator":
        emerging = int_metric(metrics, "emerging_patterns")
        insufficient = int_metric(metrics, "insufficient_evidence_patterns")
        return "B" if emerging and insufficient == 0 else "D"
    if name == "temporal_research_regime":
        positive = int_metric(metrics, "positive_regimes")
        neutral = int_metric(metrics, "neutral_regimes")
        insufficient = int_metric(metrics, "insufficient_sample_regimes")
        if positive > 0 and insufficient == 0:
            return "B"
        if neutral > 0:
            return "C"
        return "D"
    if name == "temporal_identity_memory":
        persistent = int_metric(metrics, "persistent_late_accelerators") + int_metric(metrics, "persistent_sustainers")
        return "B" if persistent > 0 else "D"
    if name == "temporal_memory_evolution":
        positive = int_metric(metrics, "positive_behavioural_evolution")
        stable = int_metric(metrics, "stable_profiles")
        return "B" if positive > 0 else "C" if stable > 0 else "D"
    if name == "probability_realism":
        realistic = int_metric(metrics, "realistic_a_b_rows")
        failed = int_metric(metrics, "grade::F")
        return "B" if realistic > 0 else "F" if failed > 0 else "D"
    return "D"


def grade_utility(module: dict[str, object], confidence: str, rows: int) -> str:
    if rows <= 0:
        return "F"
    utility = str(module["utility"])
    if utility == "truth_foundation":
        return "A"
    if utility == "uncertainty_reduction":
        return "A"
    if utility in {"validation_research", "longitudinal_research"}:
        return "B" if confidence in {"A", "B", "C", "D"} else "D"
    if utility == "conditional_research":
        return "B" if confidence in {"B", "C"} else "D"
    if utility == "descriptive_memory":
        return "C" if confidence in {"B", "C", "D"} else "D"
    if utility == "diagnostic":
        return "D" if confidence in {"D", "F"} else "C"
    return "D"


def research_status(confidence: str, utility: str, promotion: str) -> str:
    if promotion == "PROMOTION_CANDIDATE":
        return "PROMOTION_REVIEW_ONLY"
    if promotion == "SHADOW_ELIGIBLE":
        return "SHADOW_RESEARCH_ONLY"
    if confidence in {"D", "F"}:
        return "RESEARCH_BLOCKED"
    if utility in {"A", "B"}:
        return "RESEARCH_FOUNDATION"
    return "RESEARCH_ONLY"


def promotion_and_blocker(truth: str, sample: str, confidence: str, utility: str, module_name: str) -> tuple[str, str]:
    if truth == "F":
        return "BLOCKED_TRUTH", "Missing or unusable source truth"
    if truth in {"D"}:
        return "BLOCKED_TRUTH", "Truth source too weak for promotion"
    if sample == "F":
        return "BLOCKED_SAMPLE", "Sample size below 50 rows"
    if confidence == "F":
        return "BLOCKED_CONFIDENCE", "Confidence failed or false signal"
    if confidence == "D":
        return "BLOCKED_CONFIDENCE", "Insufficient sample or weak confidence"
    if sample in {"D"}:
        return "BLOCKED_SAMPLE", "Sample size below shadow threshold"
    if truth in {"A", "B"} and sample in {"A", "B"} and confidence in {"A", "B"} and utility in {"A", "B"}:
        if module_name in {"canonical_results_truth", "real_sectional_physics_features"}:
            return "RESEARCH_ONLY", "Foundational layer only; not a live model"
        return "SHADOW_ELIGIBLE", "Eligible for offline shadow review only"
    if truth in {"A", "B", "C"} and sample in {"A", "B", "C"} and confidence in {"B", "C"}:
        return "RESEARCH_ONLY", "Research evidence not strong enough for shadow promotion"
    return "RESEARCH_ONLY", "Research-only output; continue evidence accumulation"


def next_step(module_name: str, promotion: str, blocker: str) -> str:
    if promotion == "BLOCKED_SAMPLE":
        return "Accumulate more canonical settled samples before any promotion review."
    if promotion == "BLOCKED_TRUTH":
        return "Repair source truth, identity linkage, or canonical validation before interpreting this module."
    if promotion == "BLOCKED_CONFIDENCE":
        if module_name == "probability_realism":
            return "Keep suppressing realism-failed rows and improve market/entity linkage evidence."
        return "Continue longitudinal validation until confidence moves beyond insufficient-sample status."
    if promotion == "SHADOW_ELIGIBLE":
        return "Run offline shadow-only evaluation with strict no-execution guardrails."
    if promotion == "PROMOTION_CANDIDATE":
        return "Require human review and separate promotion gate before live modelling."
    return "Keep as governed research-only infrastructure."


def backlog_priority(promotion: str, utility: str) -> str:
    if promotion in {"BLOCKED_SAMPLE", "BLOCKED_TRUTH"}:
        return "HIGH"
    if promotion == "BLOCKED_CONFIDENCE":
        return "MEDIUM"
    if utility in {"A", "B"}:
        return "MEDIUM"
    return "LOW"


def required_evidence(promotion: str, module_name: str) -> str:
    if promotion == "BLOCKED_SAMPLE":
        return "Larger canonical settled sample with stable pattern/regime/identity evidence."
    if promotion == "BLOCKED_TRUTH":
        return "Canonical truth source with valid identities, settled results, and no conflicts."
    if promotion == "BLOCKED_CONFIDENCE":
        return "Repeated stable evidence, improved confidence grade, and no false signal flags."
    if module_name == "canonical_results_truth":
        return "Continue expanding official settled coverage and conflict diagnostics."
    if module_name == "real_sectional_physics_features":
        return "Maintain measured physics lineage and validate against outcomes through downstream layers."
    return "Evidence must pass separate shadow validation before any future promotion review."


def module_rows(module: dict[str, object], metrics: dict[str, str]) -> int:
    name = str(module["module_name"])
    if name == "canonical_results_truth":
        return int_metric(metrics, "rows")
    if name == "probability_realism":
        return int_metric(metrics, "realism_rows")
    if name == "temporal_evidence_accumulator":
        return int_metric(metrics, "validated_rows") or len(read_csv(Path(module["path"])))
    if name == "temporal_research_regime":
        return int_metric(metrics, "regime_rows") or len(read_csv(Path(module["path"])))
    if name == "temporal_identity_memory":
        return int_metric(metrics, "identity_rows") or len(read_csv(Path(module["path"])))
    if name == "temporal_memory_evolution":
        return int_metric(metrics, "identity_evolution_rows") or len(read_csv(Path(module["path"])))
    return len(read_csv(Path(module["path"])))


def build_governor_rows() -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    missing: list[str] = []
    for module in MODULES:
        path = Path(module["path"])
        summary_path = Path(module.get("summary_path") or module["path"])
        if not path.exists():
            rows.append(
                {
                    "module_name": module["module_name"],
                    "source_file": module["source_file"],
                    "rows": 0,
                    "truth_source_grade": "F",
                    "sample_size_grade": "F",
                    "confidence_grade": "F",
                    "decision_utility_grade": "F",
                    "promotion_eligibility": "BLOCKED_TRUTH",
                    "research_status": "MISSING_INPUT",
                    "live_modelling_allowed": "NO",
                    "live_execution_allowed": "NO",
                    "primary_blocker": "Missing input file",
                    "recommended_next_step": "Create or repair the missing source file before governance review.",
                    "notes": "Governor did not infer or fabricate missing research output.",
                }
            )
            missing.append(str(module["source_file"]))
            continue
        metrics = summary_map(summary_path)
        rows_count = module_rows(module, metrics)
        truth = grade_truth(module, metrics, rows_count, False)
        sample = grade_sample(rows_count)
        confidence = grade_confidence(module, metrics, rows_count, False)
        utility = grade_utility(module, confidence, rows_count)
        promotion, blocker = promotion_and_blocker(truth, sample, confidence, utility, str(module["module_name"]))
        rows.append(
            {
                "module_name": module["module_name"],
                "source_file": module["source_file"],
                "rows": rows_count,
                "truth_source_grade": truth,
                "sample_size_grade": sample,
                "confidence_grade": confidence,
                "decision_utility_grade": utility,
                "promotion_eligibility": promotion,
                "research_status": research_status(confidence, utility, promotion),
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "primary_blocker": blocker,
                "recommended_next_step": next_step(str(module["module_name"]), promotion, blocker),
                "notes": "Research governor only. No predictions, overlays, rated prices, live modelling, or execution promotion.",
            }
        )
    return rows, missing


def build_backlog(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    backlog: list[dict[str, object]] = []
    for row in rows:
        promotion = str(row["promotion_eligibility"])
        utility = str(row["decision_utility_grade"])
        module_name = str(row["module_name"])
        backlog.append(
            {
                "priority": backlog_priority(promotion, utility),
                "module_name": module_name,
                "promotion_blocker": row["primary_blocker"],
                "required_evidence": required_evidence(promotion, module_name),
                "current_status": row["research_status"],
                "recommended_next_step": row["recommended_next_step"],
                "notes": "Backlog is governance-only and does not authorize live modelling or execution.",
            }
        )
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(backlog, key=lambda row: (order.get(str(row["priority"]), 9), str(row["module_name"])))


def build_summary(rows: list[dict[str, object]], missing: list[str]) -> list[dict[str, object]]:
    promotions = Counter(str(row["promotion_eligibility"]) for row in rows)
    summary: list[dict[str, object]] = [
        {"metric": "governor_rows", "value": len(rows)},
        {"metric": "promotion_candidates", "value": promotions.get("PROMOTION_CANDIDATE", 0)},
        {"metric": "shadow_eligible", "value": promotions.get("SHADOW_ELIGIBLE", 0)},
        {"metric": "research_only", "value": promotions.get("RESEARCH_ONLY", 0)},
        {"metric": "blocked_sample", "value": promotions.get("BLOCKED_SAMPLE", 0)},
        {"metric": "blocked_truth", "value": promotions.get("BLOCKED_TRUTH", 0)},
        {"metric": "blocked_confidence", "value": promotions.get("BLOCKED_CONFIDENCE", 0)},
        {"metric": "live_modelling_yes", "value": sum(1 for row in rows if row["live_modelling_allowed"] == "YES")},
        {"metric": "live_execution_yes", "value": sum(1 for row in rows if row["live_execution_allowed"] == "YES")},
    ]
    for name in missing:
        summary.append({"metric": f"missing_input::{name}", "value": 1})
    for promotion, count in promotions.most_common():
        summary.append({"metric": f"promotion_eligibility::{promotion}", "value": count})
    for grade, count in Counter(str(row["confidence_grade"]) for row in rows).most_common():
        summary.append({"metric": f"confidence_grade::{grade}", "value": count})
    return summary


def main() -> None:
    rows, missing = build_governor_rows()
    backlog = build_backlog(rows)
    summary = build_summary(rows, missing)

    write_csv(OUT, rows, GOVERNOR_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(BACKLOG, backlog, BACKLOG_FIELDS)

    promotions = Counter(str(row["promotion_eligibility"]) for row in rows)
    print("=" * 88)
    print("EDGEIQ RESEARCH GOVERNOR V1")
    print("=" * 88)
    print(f"governor rows: {len(rows)}")
    print(f"backlog rows: {len(backlog)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {BACKLOG}")
    for promotion, count in promotions.most_common():
        print(f"  {promotion}: {count}")
    print("live modelling/execution: 0 / 0")


if __name__ == "__main__":
    main()
