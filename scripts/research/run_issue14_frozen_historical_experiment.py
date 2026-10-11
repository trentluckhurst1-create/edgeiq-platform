#!/usr/bin/env python3
"""Issue #14 frozen pre-2022 historical experiment gate.

This script is run-ready but fail-closed. By default it performs preflight only.
Even with --execute, it refuses to fit/score unless a valid research-use
attestation manifest is supplied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable


TRAIN_YEARS = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2012, 2013, 2014, 2015, 2018]
HISTORY_ONLY_YEARS = [2016]
EVAL_YEARS = [2019, 2020]
EXCLUDED_YEARS = [2011, 2017]
REUSED_NOT_INDEPENDENT_YEARS = [2021]

HGB_PARAMS = {
    "loss": "log_loss",
    "learning_rate": 0.05,
    "max_leaf_nodes": 5,
    "l2_regularization": 1.0,
    "max_iter": 200,
    "random_state": 42,
}

FEATURES = [
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
]

FORBIDDEN_TERMS = ("sp", "bsp", "starting_price", "odds", "price", "market", "bet", "stake", "return")
REQUIRED_ATTESTATION_FIELDS = [
    "decision",
    "authorising_rights_holder_or_owner_role",
    "basis_or_terms",
    "source_scope",
    "approval_date",
    "permitted_purpose",
    "approval_evidence_reference",
    "approval_evidence_sha256",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_logit_softmax_by_race(rows: Iterable[dict], score_col: str = "logit", race_col: str = "race_key") -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row[race_col]), []).append(dict(row))
    out = []
    for race_key, group in grouped.items():
        scores = [float(row[score_col]) for row in group]
        if not scores:
            continue
        max_score = max(scores)
        exp_scores = [math.exp(score - max_score) for score in scores]
        denom = sum(exp_scores)
        if not math.isfinite(denom) or denom <= 0:
            raise ValueError(f"Invalid softmax denominator for race {race_key}")
        for row, exp_score in zip(group, exp_scores):
            row["p_model"] = exp_score / denom
            out.append(row)
    return out


def assert_probability_mass(rows: Iterable[dict], race_col: str = "race_key", prob_col: str = "p_model", tol: float = 1e-12) -> None:
    sums: dict[str, float] = {}
    for row in rows:
        sums[str(row[race_col])] = sums.get(str(row[race_col]), 0.0) + float(row[prob_col])
    bad = {race: mass for race, mass in sums.items() if abs(mass - 1.0) > tol}
    if bad:
        first_race, first_mass = next(iter(bad.items()))
        raise ValueError(f"Race probability mass failed for {first_race}: {first_mass}")


def is_forbidden_column(column: str) -> bool:
    lower = column.lower()
    return lower in {"sp", "bsp"} or any(term in lower for term in FORBIDDEN_TERMS)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def validate_attestation(path: Path | None) -> tuple[bool, list[str], dict]:
    if path is None:
        return False, ["NO_ATTESTATION_PATH_SUPPLIED"], {}
    if not path.is_file():
        return False, ["ATTESTATION_FILE_NOT_FOUND"], {}
    data = load_json(path)
    reasons = []
    missing = [field for field in REQUIRED_ATTESTATION_FIELDS if not str(data.get(field, "")).strip()]
    if missing:
        reasons.append("MISSING_ATTESTATION_FIELDS:" + ",".join(missing))
    if str(data.get("decision", "")).strip().upper() != "APPROVED":
        reasons.append("DECISION_NOT_APPROVED")
    scope = str(data.get("source_scope", "")).lower()
    if "pre-2022" not in scope and "pre2022" not in scope:
        reasons.append("SOURCE_SCOPE_DOES_NOT_STATE_PRE2022")
    purpose = str(data.get("permitted_purpose", "")).lower()
    if "research" not in purpose:
        reasons.append("PERMITTED_PURPOSE_DOES_NOT_STATE_RESEARCH")
    try:
        approval_date = date.fromisoformat(str(data.get("approval_date", ""))[:10])
        if approval_date > date.today():
            reasons.append("APPROVAL_DATE_IN_FUTURE")
    except ValueError:
        reasons.append("APPROVAL_DATE_NOT_ISO")
    evidence_hash = str(data.get("approval_evidence_sha256", "")).strip().lower()
    if len(evidence_hash) != 64 or any(c not in "0123456789abcdef" for c in evidence_hash):
        reasons.append("APPROVAL_EVIDENCE_SHA256_INVALID")
    return not reasons, reasons, data


def inspect_pit_matrix(path: Path) -> dict:
    if not path.is_file():
        return {"status": "STOP", "reasons": ["PIT_MATRIX_NOT_FOUND"], "path": str(path)}
    rows = 0
    years = {}
    label_bad = 0
    race_winners: dict[str, int] = {}
    forbidden_columns = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing_features = [col for col in FEATURES if col not in header]
        missing_core = [col for col in ("race_key", "runner_key", "year", "y") if col not in header]
        forbidden_columns = [col for col in header if is_forbidden_column(col)]
        if missing_features or missing_core or forbidden_columns:
            return {
                "status": "STOP",
                "reasons": [
                    "MISSING_FEATURES:" + ",".join(missing_features) if missing_features else "",
                    "MISSING_CORE_COLUMNS:" + ",".join(missing_core) if missing_core else "",
                    "FORBIDDEN_COLUMNS:" + ",".join(forbidden_columns) if forbidden_columns else "",
                ],
                "path": str(path),
            }
        for row in reader:
            rows += 1
            year = int(row["year"])
            years[year] = years.get(year, 0) + 1
            if row["y"] not in {"0", "1"}:
                label_bad += 1
            race_winners[row["race_key"]] = race_winners.get(row["race_key"], 0) + int(row["y"] == "1")
    bad_races = sum(1 for count in race_winners.values() if count != 1)
    unexpected_years = sorted(set(years) - set(TRAIN_YEARS) - set(HISTORY_ONLY_YEARS) - set(EVAL_YEARS) - set(REUSED_NOT_INDEPENDENT_YEARS))
    reasons = []
    if label_bad:
        reasons.append("INVALID_LABEL_VALUES")
    if bad_races:
        reasons.append("RACES_WITH_NOT_EXACTLY_ONE_WINNER")
    if unexpected_years:
        reasons.append("UNEXPECTED_YEARS:" + ",".join(map(str, unexpected_years)))
    return {
        "status": "PASS" if not reasons else "STOP",
        "reasons": reasons,
        "path": str(path),
        "sha256": sha256_file(path),
        "rows": rows,
        "races": len(race_winners),
        "year_rows": dict(sorted(years.items())),
        "train_rows": sum(years.get(year, 0) for year in TRAIN_YEARS),
        "history_only_rows": sum(years.get(year, 0) for year in HISTORY_ONLY_YEARS),
        "eval_2019_rows": years.get(2019, 0),
        "eval_2020_rows": years.get(2020, 0),
        "reused_2021_rows": years.get(2021, 0),
    }


def frozen_protocol() -> dict:
    return {
        "status": "FROZEN_RUN_READY_FAIL_CLOSED",
        "training_years": TRAIN_YEARS,
        "history_only_years": HISTORY_ONLY_YEARS,
        "evaluation_years": EVAL_YEARS,
        "excluded_years": EXCLUDED_YEARS,
        "reused_not_independent_years": REUSED_NOT_INDEPENDENT_YEARS,
        "model": {"family": "HistGradientBoostingClassifier", "params": HGB_PARAMS},
        "features": FEATURES,
        "probability_formula": {
            "source": "HistGradientBoostingClassifier.decision_function(X_i)",
            "formula": "p_i = exp(z_i - max_r(z)) / sum_j exp(z_j - max_r(z)) within each race r",
            "mass_tolerance": 1e-12,
            "forbidden": "Never normalize predict_proba directly.",
        },
        "metrics": ["race_log_loss", "runner_brier", "top1", "top3", "MRR", "winner_rank", "calibration_10_bins", "coverage_by_identity_and_field_cohorts"],
        "baselines": ["uniform_within_race"],
        "missing_value_treatment": "Use HGB native missing handling; preserve explicit missing identity flags.",
        "stop_rules": [
            "No attestation approval: STOP before fit/score.",
            "Any market/SP/BSP/odds/price column: STOP.",
            "Any 2025-2026 source access: STOP.",
            "Any evaluation race without exactly one winner: STOP.",
            "Any race probability mass error > 1e-12: STOP.",
            "No refit after observing 2019/2020 metrics.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pit-matrix", default="outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv")
    parser.add_argument("--attestation", default=None, help="Research-use attestation JSON. Omit to prove fail-closed.")
    parser.add_argument("--out", default="outputs/research/issue14_final_experiment_gate")
    parser.add_argument("--execute", action="store_true", help="Attempt fitting/scoring only after attestation passes. Currently still gate-only until authorised.")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    protocol = frozen_protocol()
    pit = inspect_pit_matrix(Path(args.pit_matrix))
    approved, attestation_reasons, attestation = validate_attestation(Path(args.attestation) if args.attestation else None)

    preflight_reasons = []
    if pit["status"] != "PASS":
        preflight_reasons.extend("PIT_" + reason for reason in pit.get("reasons", []))
    if not approved:
        preflight_reasons.extend("ATTESTATION_" + reason for reason in attestation_reasons)
    if args.execute:
        preflight_reasons.append("EXECUTION_NOT_AUTHORISED_IN_ISSUE14_PR")

    status = "PASS_READY_FOR_AUTHORISED_EXECUTION" if not preflight_reasons else "STOP"
    report = {
        "status": status,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_fitting": "NO",
        "model_scoring": "NO",
        "execute_requested": bool(args.execute),
        "preflight_reasons": preflight_reasons,
        "pit_matrix": pit,
        "research_use_attestation": {
            "approved": approved,
            "path": args.attestation or "",
            "reasons": attestation_reasons,
            "sha256": sha256_file(Path(args.attestation)) if args.attestation and Path(args.attestation).is_file() else "",
            "redacted_fields_present": sorted(attestation.keys()) if attestation else [],
        },
        "protocol": protocol,
    }
    (out / "ISSUE14_PREFLIGHT_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "ISSUE14_FROZEN_PROTOCOL.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "preflight_reasons": preflight_reasons, "out": str(out)}, indent=2))
    return 2 if status == "STOP" and args.execute else 0


if __name__ == "__main__":
    raise SystemExit(main())
