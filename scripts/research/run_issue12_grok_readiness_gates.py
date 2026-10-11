#!/usr/bin/env python3
"""Issue #12 Grok readiness diagnostics for the pre-2022 PIT dataset.

Reads the local Issue #10 outputs, produces compact identity/missingness
diagnostics, and freezes a design-only 2019/2020 protocol. No fitting/scoring.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


RUNNER_FILE = "ISSUE10_PRE2022_RUNNER_PARTITION.csv"
PIT_FILE = "ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv"
MANIFEST_FILE = "ISSUE10_BUILD_MANIFEST.json"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", clean(value).upper()).strip("_")


def is_missing(value: object) -> bool:
    text = clean(value)
    if not text:
        return True
    try:
        return not math.isfinite(float(text))
    except ValueError:
        return False


def add_rate(row: dict, numerator: str, denominator: str, out_col: str) -> None:
    den = int(row.get(denominator, 0) or 0)
    num = int(row.get(numerator, 0) or 0)
    row[out_col] = "" if den == 0 else num / den


def write_csv(path: Path, rows: list[dict], fieldnames: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or (rows[0].keys() if rows else []))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def cohort_for_year(year: int) -> str:
    if year <= 2018 and year not in {2011, 2016, 2017}:
        return "TRAIN_ELIGIBLE_COMPLETE_YEARS_LE_2018"
    if year == 2016:
        return "SPARSE_HISTORY_ONLY_EXCLUDED_FROM_TRAIN_EVAL"
    if year in {2011, 2017}:
        return "MISSING_YEAR_EXCLUDED"
    if year == 2019:
        return "EVAL_2019"
    if year == 2020:
        return "EVAL_2020"
    if year == 2021:
        return "REUSED_DEVELOPMENT_NOT_INDEPENDENT"
    return "OTHER"


def counter_row(scope: str, key: str, count: int, total: int) -> dict:
    return {"scope": scope, "category": key, "rows": count, "total_rows": total, "share": count / total if total else ""}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue10-dir", default="outputs/research/issue10_pre2022_partition")
    parser.add_argument("--out", default="outputs/research/issue12_grok_readiness")
    args = parser.parse_args()

    issue10 = Path(args.issue10_dir)
    out = Path(args.out)
    runner_path = issue10 / RUNNER_FILE
    pit_path = issue10 / PIT_FILE
    manifest_path = issue10 / MANIFEST_FILE
    missing_files = [str(p) for p in (runner_path, pit_path, manifest_path) if not p.is_file()]
    if missing_files:
        raise SystemExit("STOP: missing Issue #10 local outputs. Run .\\scripts\\research\\build_issue10_pre2022_pit_partition.ps1 first. Missing: " + ", ".join(missing_files))

    with manifest_path.open("r", encoding="utf-8") as f:
        issue10_manifest = json.load(f)

    identity_by_year: dict[str, Counter] = defaultdict(Counter)
    identity_overall = Counter()
    name_to_codes: dict[str, set] = defaultdict(set)
    code_to_names: dict[str, set] = defaultdict(set)
    horse_key_to_names: dict[str, set] = defaultdict(set)
    row_quarantine_count = 0
    row_quarantine_path = issue10 / "ISSUE10_ROW_QUARANTINE.csv"
    if row_quarantine_path.is_file():
        with row_quarantine_path.open("r", encoding="utf-8-sig", newline="") as f:
            row_quarantine_count = max(sum(1 for _ in f) - 1, 0)

    missing_template = {
        "rows": 0,
        "barrier_missing_or_invalid": 0,
        "weight_missing_or_invalid": 0,
        "distance_missing_or_invalid": 0,
        "jockey_code_missing_name_present": 0,
        "jockey_name_missing_code_present": 0,
        "jockey_completely_missing": 0,
        "trainer_code_missing_name_present": 0,
        "trainer_name_missing_code_present": 0,
        "trainer_completely_missing": 0,
    }
    missing_by_year: dict[int, Counter] = defaultdict(Counter)
    missing_by_cohort: dict[str, Counter] = defaultdict(Counter)
    runner_year_counts = Counter()
    eligible_starter_year_counts = Counter()

    with runner_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row["year"])
            runner_year_counts[year] += 1
            method = clean(row.get("horse_key_method")) or "UNKNOWN"
            identity_by_year[str(year)][method] += 1
            identity_overall[method] += 1
            h_code = norm(row.get("horse_code"))
            h_name = norm(row.get("horse"))
            h_key = clean(row.get("horse_key"))
            if h_name and h_code:
                name_to_codes[h_name].add(h_code)
                code_to_names[h_code].add(h_name)
            if h_key and h_name:
                horse_key_to_names[h_key].add(h_name)
            if clean(row.get("race_eligible")) != "1" or clean(row.get("scratched")) != "0":
                continue
            eligible_starter_year_counts[year] += 1
            cohort = cohort_for_year(year)
            for bucket in (missing_by_year[year], missing_by_cohort[cohort]):
                bucket["rows"] += 1
                if is_missing(row.get("barrier")):
                    bucket["barrier_missing_or_invalid"] += 1
                if is_missing(row.get("weight")):
                    bucket["weight_missing_or_invalid"] += 1
                if is_missing(row.get("distance_metres")):
                    bucket["distance_missing_or_invalid"] += 1
                jockey_code_missing = is_missing(row.get("jockey_code"))
                jockey_name_missing = is_missing(row.get("jockey"))
                trainer_code_missing = is_missing(row.get("trainer_code"))
                trainer_name_missing = is_missing(row.get("trainer"))
                if jockey_code_missing and not jockey_name_missing:
                    bucket["jockey_code_missing_name_present"] += 1
                if jockey_name_missing and not jockey_code_missing:
                    bucket["jockey_name_missing_code_present"] += 1
                if jockey_code_missing and jockey_name_missing:
                    bucket["jockey_completely_missing"] += 1
                if trainer_code_missing and not trainer_name_missing:
                    bucket["trainer_code_missing_name_present"] += 1
                if trainer_name_missing and not trainer_code_missing:
                    bucket["trainer_name_missing_code_present"] += 1
                if trainer_code_missing and trainer_name_missing:
                    bucket["trainer_completely_missing"] += 1

    total_identity_rows = sum(identity_overall.values())
    identity_rows = [counter_row("overall", k, v, total_identity_rows) for k, v in sorted(identity_overall.items())]
    for year in sorted(identity_by_year, key=int):
        total = sum(identity_by_year[year].values())
        identity_rows.extend(counter_row(year, k, v, total) for k, v in sorted(identity_by_year[year].items()))

    name_multi_code = {k: v for k, v in name_to_codes.items() if len(v) > 1}
    code_multi_name = {k: v for k, v in code_to_names.items() if len(v) > 1}
    key_multi_name = {k: v for k, v in horse_key_to_names.items() if len(v) > 1}
    collision_summary = [
        {"collision_type": "normalised_horse_name_maps_to_multiple_codes", "groups": len(name_multi_code), "max_codes_in_group": max((len(v) for v in name_multi_code.values()), default=0)},
        {"collision_type": "horse_code_maps_to_multiple_normalised_names", "groups": len(code_multi_name), "max_names_in_group": max((len(v) for v in code_multi_name.values()), default=0)},
        {"collision_type": "constructed_horse_key_maps_to_multiple_normalised_names", "groups": len(key_multi_name), "max_names_in_group": max((len(v) for v in key_multi_name.values()), default=0)},
        {"collision_type": "explicit_row_quarantine_records", "groups": row_quarantine_count, "max_names_in_group": ""},
    ]
    collision_examples = []
    for label, groups in (
        ("normalised_horse_name_maps_to_multiple_codes", name_multi_code),
        ("horse_code_maps_to_multiple_normalised_names", code_multi_name),
        ("constructed_horse_key_maps_to_multiple_normalised_names", key_multi_name),
    ):
        for key, values in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))[:50]:
            collision_examples.append({"collision_type": label, "key": key, "value_count": len(values), "values": "|".join(sorted(values)[:20])})

    missing_rows = []
    for year in sorted(missing_by_year):
        row = {"scope": "year", "cohort": str(year), **missing_template, **dict(missing_by_year[year])}
        for col in [k for k in missing_template if k != "rows"]:
            add_rate(row, col, "rows", f"{col}_rate")
        missing_rows.append(row)
    for cohort in sorted(missing_by_cohort):
        row = {"scope": "cohort", "cohort": cohort, **missing_template, **dict(missing_by_cohort[cohort])}
        for col in [k for k in missing_template if k != "rows"]:
            add_rate(row, col, "rows", f"{col}_rate")
        missing_rows.append(row)

    pit_year_counts = Counter()
    pit_field_sizes: dict[int, Counter] = defaultdict(Counter)
    pit_prior_rows = Counter()
    with pit_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row["year"])
            pit_year_counts[year] += 1
            pit_field_sizes[year][clean(row.get("field_size"))] += 1
            if clean(row.get("horse_prior_starts")) not in {"", "0"}:
                pit_prior_rows[(year, "horse_prior_available")] += 1
            if clean(row.get("trainer_prior_starts")) not in {"", "0"}:
                pit_prior_rows[(year, "trainer_prior_available")] += 1
            if clean(row.get("jockey_prior_starts")) not in {"", "0"}:
                pit_prior_rows[(year, "jockey_prior_available")] += 1

    prior_rows = []
    for year in sorted(pit_year_counts):
        total = pit_year_counts[year]
        for metric in ("horse_prior_available", "trainer_prior_available", "jockey_prior_available"):
            count = pit_prior_rows[(year, metric)]
            prior_rows.append({"year": year, "metric": metric, "rows": count, "total_pit_rows": total, "share": count / total if total else ""})

    consistency_rows = []
    year_counts_path = issue10 / "ISSUE10_YEAR_COUNTS.csv"
    if year_counts_path.is_file():
        with year_counts_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                year = int(row["year"])
                consistency_rows.append(
                    {
                        "year": year,
                        "issue10_eligible_starters": row["eligible_starters"],
                        "pit_rows": pit_year_counts.get(year, 0),
                        "runner_partition_eligible_starters": eligible_starter_year_counts.get(year, 0),
                        "consistent": int(int(row["eligible_starters"]) == pit_year_counts.get(year, 0) == eligible_starter_year_counts.get(year, 0)),
                        "cohort": cohort_for_year(year),
                    }
                )

    protocol = {
        "status": "DESIGN_ONLY_NO_FIT_NO_SCORE",
        "training_years": [y for y in sorted(pit_year_counts) if y <= 2018 and y not in {2011, 2016, 2017}],
        "history_only_sparse_years": [2016],
        "excluded_missing_years": [2011, 2017],
        "evaluation_years": [2019, 2020],
        "excluded_from_independent_evaluation": [2021],
        "learner": {
            "family": "HistGradientBoostingClassifier",
            "fixed_parameters": {
                "loss": "log_loss",
                "learning_rate": 0.05,
                "max_leaf_nodes": 5,
                "l2_regularization": 1.0,
                "max_iter": 200,
                "random_state": 42,
            },
            "reason": "Use the established Stage011-style HGB family without tuning.",
        },
        "features": [
            "field_size",
            "barrier",
            "barrier_position_pct",
            "distance_metres",
            "weight",
            "horse_prior_starts",
            "horse_prior_wins",
            "horse_prior_top3",
            "horse_prior_win_rate",
            "horse_prior_top3_rate",
            "horse_prior_finish_mean",
            "horse_days_since_last_run",
            "horse_no_prior_history",
            "trainer_id_missing",
            "trainer_prior_starts",
            "trainer_prior_wins",
            "trainer_prior_top3",
            "trainer_prior_win_rate",
            "trainer_prior_top3_rate",
            "trainer_no_prior_history",
            "jockey_id_missing",
            "jockey_prior_starts",
            "jockey_prior_wins",
            "jockey_prior_top3",
            "jockey_prior_win_rate",
            "jockey_prior_top3_rate",
            "jockey_no_prior_history",
        ],
        "missing_value_treatment": "Use HGB native missing-value handling; preserve explicit missing identity flags. Do not impute market or outcome values.",
        "probability_normalization": "Convert raw model scores to softmax probabilities within each race; every race must sum to 1 within 1e-12.",
        "metrics": ["race_log_loss", "runner_brier", "top1", "top3", "MRR", "winner_rank", "calibration_10_bins", "coverage_by_identity_and_field_cohorts"],
        "baseline": "Uniform within-race probability plus optional Stage011-era comparison only as non-independent context; no Stage011 promotion path.",
        "gates": [
            "No market/SP/BSP/odds columns.",
            "No 2025-2026 access.",
            "No refit after observing 2019 or 2020 metrics.",
            "Report 2019 and 2020 separately.",
            "Report all identity and missingness cohorts.",
            "Stop if probability mass by race fails.",
            "Stop if any evaluation race lacks exactly one winner.",
        ],
    }

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "ISSUE12_HORSE_IDENTITY_METHODS.csv", identity_rows)
    write_csv(out / "ISSUE12_HORSE_IDENTITY_COLLISION_SUMMARY.csv", collision_summary)
    write_csv(out / "ISSUE12_HORSE_IDENTITY_COLLISION_EXAMPLES.csv", collision_examples)
    write_csv(out / "ISSUE12_MISSINGNESS_BY_YEAR_AND_COHORT.csv", missing_rows)
    write_csv(out / "ISSUE12_FIELD_CONSISTENCY.csv", consistency_rows)
    write_csv(out / "ISSUE12_PRIOR_HISTORY_COVERAGE.csv", prior_rows)
    (out / "ISSUE12_FROZEN_PROTOCOL.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")

    summary = {
        "status": "PASS_CONDITIONS_MEASURED_PROTOCOL_FROZEN_REVIEW_REQUIRED",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_fitting": "NO",
        "model_scoring": "NO",
        "market_access": "NO",
        "sealed_2025_2026_access": "NO",
        "issue10_manifest_status": issue10_manifest.get("status"),
        "pit_rows": sum(pit_year_counts.values()),
        "identity_method_counts": dict(sorted(identity_overall.items())),
        "identity_method_shares": {k: v / total_identity_rows for k, v in sorted(identity_overall.items())},
        "collision_summary": collision_summary,
        "row_quarantine_count": row_quarantine_count,
        "missing_years": [2011, 2017],
        "sparse_years": [2016],
        "protocol_status": protocol["status"],
        "training_years": protocol["training_years"],
        "evaluation_years": protocol["evaluation_years"],
        "remaining_hard_blockers": [
            "Independent Grok review required before fitting/scoring.",
            "Source rights/permissible-use status still requires owner/Grok acceptance.",
            "This remains a standalone historical source-key model; joining to Stage011 remains forbidden without canonical crosswalk certification.",
        ],
    }
    (out / "ISSUE12_GROK_CONDITIONS_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "pit_rows": summary["pit_rows"],
        "identity_method_counts": summary["identity_method_counts"],
        "training_years": summary["training_years"],
        "evaluation_years": summary["evaluation_years"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
