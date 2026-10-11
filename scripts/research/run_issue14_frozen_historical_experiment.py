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

REQUIRED_EXECUTION_APPROVAL_FIELDS = [
    "decision",
    "approval_date",
    "approval_reference",
    "scope",
    "constraints",
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


def validate_execution_approval(path: Path | None) -> tuple[bool, list[str], dict]:
    if path is None:
        return False, ["NO_EXECUTION_APPROVAL_PATH_SUPPLIED"], {}
    if not path.is_file():
        return False, ["EXECUTION_APPROVAL_FILE_NOT_FOUND"], {}
    data = load_json(path)
    reasons = []
    missing = [field for field in REQUIRED_EXECUTION_APPROVAL_FIELDS if not data.get(field)]
    if missing:
        reasons.append("MISSING_EXECUTION_APPROVAL_FIELDS:" + ",".join(missing))
    if str(data.get("decision", "")).strip().upper() != "APPROVED_ONE_FROZEN_EXPERIMENT":
        reasons.append("DECISION_NOT_APPROVED_ONE_FROZEN_EXPERIMENT")
    scope = str(data.get("scope", "")).lower()
    for required in ("2019", "2020", "single", "frozen"):
        if required not in scope:
            reasons.append(f"SCOPE_MISSING_{required.upper()}")
    try:
        approval_date = date.fromisoformat(str(data.get("approval_date", ""))[:10])
        if approval_date > date.today():
            reasons.append("EXECUTION_APPROVAL_DATE_IN_FUTURE")
    except ValueError:
        reasons.append("EXECUTION_APPROVAL_DATE_NOT_ISO")
    constraints = " ".join(str(x).lower() for x in data.get("constraints", []))
    for required in ("no tuning", "no market", "no 2025", "no stage011", "no production"):
        if required not in constraints:
            reasons.append("CONSTRAINTS_MISSING_" + required.upper().replace(" ", "_"))
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


def race_softmax_frame(df, logit_col: str = "logit"):
    import numpy as np

    max_by_race = df.groupby("race_key")[logit_col].transform("max")
    exp_scores = np.exp(df[logit_col] - max_by_race)
    denom = exp_scores.groupby(df["race_key"]).transform("sum")
    df["p_model"] = exp_scores / denom
    return df


def calibration_rows(df, year: int) -> list[dict]:
    import pandas as pd

    bins = [i / 10 for i in range(11)]
    tmp = df[["p_model", "y"]].copy()
    tmp["calibration_bin"] = pd.cut(tmp["p_model"], bins=bins, include_lowest=True, right=True)
    rows = []
    for label, g in tmp.groupby("calibration_bin", observed=False):
        if g.empty:
            rows.append({"year": year, "bin": str(label), "rows": 0, "mean_p": "", "win_rate": "", "brier": ""})
        else:
            rows.append(
                {
                    "year": year,
                    "bin": str(label),
                    "rows": int(len(g)),
                    "mean_p": float(g["p_model"].mean()),
                    "win_rate": float(g["y"].mean()),
                    "brier": float(((g["p_model"] - g["y"]) ** 2).mean()),
                }
            )
    return rows


def ranking_metrics(df, year: int) -> dict:
    import numpy as np

    race_ll = []
    uniform_ll = []
    ranks = []
    winner_probs = []
    uniform_brier_values = []
    for _, g in df.groupby("race_key", sort=False):
        g = g.sort_values(["p_model", "runner_key"], ascending=[False, True]).reset_index(drop=True)
        winner_idx = np.flatnonzero(g["y"].to_numpy(dtype=int) == 1)
        if len(winner_idx) != 1:
            raise RuntimeError(f"Evaluation race without exactly one winner in {year}")
        idx = int(winner_idx[0])
        rank = idx + 1
        p_win = float(g.loc[idx, "p_model"])
        race_ll.append(-math.log(max(p_win, 1e-15)))
        uniform_ll.append(math.log(len(g)))
        ranks.append(rank)
        winner_probs.append(p_win)
        uniform_p = 1.0 / len(g)
        uniform_brier_values.extend((uniform_p - g["y"].to_numpy(dtype=float)) ** 2)
    ranks_arr = np.asarray(ranks, dtype=float)
    return {
        "year": year,
        "runners": int(len(df)),
        "races": int(df["race_key"].nunique()),
        "race_log_loss": float(np.mean(race_ll)),
        "runner_brier": float(((df["p_model"] - df["y"]) ** 2).mean()),
        "top1": float(np.mean(ranks_arr <= 1)),
        "top3": float(np.mean(ranks_arr <= 3)),
        "mrr": float(np.mean(1.0 / ranks_arr)),
        "mean_winner_rank": float(np.mean(ranks_arr)),
        "mean_winner_probability": float(np.mean(winner_probs)),
        "uniform_race_log_loss": float(np.mean(uniform_ll)),
        "uniform_runner_brier": float(np.mean(uniform_brier_values)),
        "max_probability_mass_error": float((df.groupby("race_key")["p_model"].sum() - 1.0).abs().max()),
    }


def cohort_metrics(df, year: int) -> list[dict]:
    rows = []
    cohorts = {
        "all": [True] * len(df),
        "horse_no_prior_history": df["horse_no_prior_history"].fillna(0).astype(float).eq(1),
        "horse_prior_history": df["horse_no_prior_history"].fillna(0).astype(float).ne(1),
        "jockey_id_missing": df["jockey_id_missing"].fillna(0).astype(float).eq(1),
        "trainer_id_missing": df["trainer_id_missing"].fillna(0).astype(float).eq(1),
        "barrier_missing": df["barrier"].isna(),
        "weight_missing": df["weight"].isna(),
    }
    for cohort, mask in cohorts.items():
        g = df.loc[mask]
        if g.empty:
            rows.append({"year": year, "cohort": cohort, "rows": 0, "winner_rows": 0, "mean_p": "", "win_rate": "", "brier": ""})
        else:
            rows.append(
                {
                    "year": year,
                    "cohort": cohort,
                    "rows": int(len(g)),
                    "winner_rows": int(g["y"].sum()),
                    "mean_p": float(g["p_model"].mean()),
                    "win_rate": float(g["y"].mean()),
                    "brier": float(((g["p_model"] - g["y"]) ** 2).mean()),
                }
            )
    return rows


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def execute_frozen_experiment(pit_matrix: Path, out: Path) -> dict:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import HistGradientBoostingClassifier

    usecols = ["race_key", "runner_key", "year", "y"] + FEATURES
    df = pd.read_csv(pit_matrix, usecols=usecols)
    if any(is_forbidden_column(c) for c in df.columns):
        raise RuntimeError("Forbidden market-like column present in model frame")
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    df["y"] = pd.to_numeric(df["y"], errors="raise").astype(int)
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    train = df[df["year"].isin(TRAIN_YEARS)].copy()
    eval_df = df[df["year"].isin(EVAL_YEARS)].copy()
    if len(train) != 465622:
        raise RuntimeError(f"Unexpected training row count: {len(train)}")
    if len(eval_df[eval_df["year"] == 2019]) != 26652:
        raise RuntimeError("Unexpected 2019 evaluation row count")
    if len(eval_df[eval_df["year"] == 2020]) != 28548:
        raise RuntimeError("Unexpected 2020 evaluation row count")
    if train["race_key"].isin(eval_df["race_key"]).any():
        raise RuntimeError("Train/evaluation race overlap detected")
    model = HistGradientBoostingClassifier(**HGB_PARAMS)
    model.fit(train[FEATURES].replace([np.inf, -np.inf], np.nan), train["y"])
    feature_manifest_sha = hashlib.sha256(json.dumps(FEATURES, separators=(",", ":")).encode("utf-8")).hexdigest()
    predictions = []
    year_metrics = []
    calibration = []
    cohorts = []
    for year in EVAL_YEARS:
        te = eval_df[eval_df["year"] == year].copy()
        te["logit"] = model.decision_function(te[FEATURES].replace([np.inf, -np.inf], np.nan))
        te = race_softmax_frame(te, "logit")
        max_mass_error = (te.groupby("race_key")["p_model"].sum() - 1.0).abs().max()
        if max_mass_error > 1e-12:
            raise RuntimeError(f"Probability mass failed for {year}: {max_mass_error}")
        metrics = ranking_metrics(te, year)
        year_metrics.append(metrics)
        calibration.extend(calibration_rows(te, year))
        cohorts.extend(cohort_metrics(te, year))
        te["model_name"] = "ISSUE14_FROZEN_HISTORICAL_HGB"
        te["feature_manifest_sha256"] = feature_manifest_sha
        predictions.extend(
            te[
                [
                    "year",
                    "race_key",
                    "runner_key",
                    "y",
                    "logit",
                    "p_model",
                    "model_name",
                    "feature_manifest_sha256",
                ]
            ].to_dict("records")
        )
    write_rows(out / "ISSUE14_FROZEN_HGB_YEAR_METRICS.csv", year_metrics)
    write_rows(out / "ISSUE14_FROZEN_HGB_CALIBRATION.csv", calibration)
    write_rows(out / "ISSUE14_FROZEN_HGB_COHORT_METRICS.csv", cohorts)
    write_rows(out / "ISSUE14_FROZEN_HGB_OOS_PREDICTIONS.csv", predictions)
    result = {
        "status": "PASS_ONE_FROZEN_EXPERIMENT_COMPLETE",
        "model_fits": 1,
        "model_family": "HistGradientBoostingClassifier",
        "model_params": HGB_PARAMS,
        "train_rows": int(len(train)),
        "train_races": int(train["race_key"].nunique()),
        "evaluation_years": EVAL_YEARS,
        "year_metrics": year_metrics,
        "feature_manifest_sha256": feature_manifest_sha,
        "prediction_sha256": sha256_file(out / "ISSUE14_FROZEN_HGB_OOS_PREDICTIONS.csv"),
    }
    (out / "ISSUE14_FROZEN_HGB_RESULTS.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pit-matrix", default="outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv")
    parser.add_argument("--attestation", default=None, help="Research-use attestation JSON. Omit to prove fail-closed.")
    parser.add_argument("--execution-approval", default=None, help="Explicit one-run execution approval JSON.")
    parser.add_argument("--out", default="outputs/research/issue14_final_experiment_gate")
    parser.add_argument("--execute", action="store_true", help="Perform the single frozen fit/evaluation after all gates pass.")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    protocol = frozen_protocol()
    pit = inspect_pit_matrix(Path(args.pit_matrix))
    approved, attestation_reasons, attestation = validate_attestation(Path(args.attestation) if args.attestation else None)
    execution_approved, execution_reasons, execution_approval = validate_execution_approval(Path(args.execution_approval) if args.execution_approval else None)

    preflight_reasons = []
    if pit["status"] != "PASS":
        preflight_reasons.extend("PIT_" + reason for reason in pit.get("reasons", []))
    if not approved:
        preflight_reasons.extend("ATTESTATION_" + reason for reason in attestation_reasons)
    if args.execute and not execution_approved:
        preflight_reasons.extend("EXECUTION_" + reason for reason in execution_reasons)

    status = "PASS_READY_FOR_AUTHORISED_EXECUTION" if not preflight_reasons else "STOP"
    execution_result = None
    if args.execute and status == "PASS_READY_FOR_AUTHORISED_EXECUTION":
        execution_result = execute_frozen_experiment(Path(args.pit_matrix), out)
        status = "PASS_ONE_FROZEN_EXPERIMENT_COMPLETE"
    report = {
        "status": status,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_fitting": "YES" if execution_result else "NO",
        "model_scoring": "YES" if execution_result else "NO",
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
        "execution_approval": {
            "approved": execution_approved,
            "path": args.execution_approval or "",
            "reasons": execution_reasons,
            "sha256": sha256_file(Path(args.execution_approval)) if args.execution_approval and Path(args.execution_approval).is_file() else "",
            "redacted_fields_present": sorted(execution_approval.keys()) if execution_approval else [],
        },
        "protocol": protocol,
        "execution_result": execution_result,
    }
    (out / "ISSUE14_PREFLIGHT_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "ISSUE14_FROZEN_PROTOCOL.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "preflight_reasons": preflight_reasons, "out": str(out), "execution_result": execution_result}, indent=2))
    return 2 if status == "STOP" and args.execute else 0


if __name__ == "__main__":
    raise SystemExit(main())
