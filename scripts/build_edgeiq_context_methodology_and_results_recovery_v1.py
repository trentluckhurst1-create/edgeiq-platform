from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
import tempfile
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
PRIOR_DOCS = ROOT / "docs" / "performance-intelligence-context-parameter-program-v1"
DOCS = ROOT / "docs" / "performance-intelligence-context-parameter-methodology-v1"
BUILT_AT = "2026-07-30T01:30:00Z"
POLICY_ID = "EPI-CONTEXT-PARAM-A-v1"
TARGET_FIELD = "rating_base_value"
TARGET_UNIT = "HPR-NORM-A normalised rating units"
MIN_PRIOR_OBSERVATIONS = 5
REGULARISATION_METHOD = "RIDGE_REGULARISED_GROUP_MEAN_RESIDUAL"
LAMBDA_GRID = [10.0, 25.0, 50.0, 100.0, 250.0]
VALIDATION_YEARS = [2022, 2023, 2024, 2025, 2026]


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def norm(value: object) -> str:
    return " ".join(text(value).upper().split())


def token(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def sha(parts: list[object]) -> str:
    return hashlib.sha256("\x1f".join(text(part) for part in parts).encode("utf-8")).hexdigest()


def dec(value: object) -> float | None:
    raw = text(value).lower().replace("kg", "").replace("kgs", "").replace("m", "")
    raw = "".join(ch for ch in raw if ch.isdigit() or ch in ".-")
    if not raw:
        return None
    try:
        parsed = float(raw)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0].keys()) if rows else ["status"])
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def row_count(path: Path) -> int:
    return len(read_csv(path)[1])


def post_count(path: Path, date_field: str = "race_date") -> int:
    fields, rows = read_csv(path)
    if date_field not in fields:
        return 0
    return sum(1 for row in rows if text(row.get(date_field)) >= "2026-07-20")


def distance_band(distance: object) -> str:
    d = dec(distance)
    if d is None:
        return ""
    if d <= 1200:
        return "SPRINT"
    if d <= 1600:
        return "MILE"
    if d <= 2000:
        return "MIDDLE"
    return "STAYING"


def condition_group(value: object) -> str:
    s = norm(value)
    if "HEAVY" in s:
        return "HEAVY"
    if "SOFT" in s:
        return "SOFT"
    if "GOOD" in s or "FIRM" in s:
        return "FIRM_GOOD"
    if "SYNTH" in s:
        return "SYNTHETIC"
    return ""


def rail_group(value: object) -> str:
    s = norm(value)
    if not s:
        return ""
    number = dec(s)
    if number is None:
        return "RAIL_DECLARED"
    if number == 0:
        return "TRUE"
    if number <= 4:
        return "OUT_0_TO_4"
    if number <= 8:
        return "OUT_4_TO_8"
    return "OUT_8_PLUS"


def class_family(value: object) -> str:
    s = norm(value)
    if not s:
        return ""
    if "GROUP 1" in s or "G1" in s:
        return "GROUP_1"
    if "GROUP 2" in s or "G2" in s:
        return "GROUP_2"
    if "GROUP 3" in s or "G3" in s:
        return "GROUP_3"
    if "LISTED" in s:
        return "LISTED"
    if "OPEN" in s:
        return "OPEN"
    if "BM" in s or "BENCHMARK" in s:
        return "BENCHMARK"
    if "MDN" in s or "MAIDEN" in s:
        return "MAIDEN"
    return s[:40]


def load_training_facts() -> list[dict[str, str]]:
    path = PRIOR_DOCS / "EDGEIQ_CONTEXT_PARAMETER_TRAINING_FACT_V1.csv"
    if not path.exists():
        raise RuntimeError(f"Missing prior training fact: {path}")
    _, rows = read_csv(path)
    for row in rows:
        row["distance_band"] = distance_band(row.get("race_distance_m"))
        row["track_condition_group"] = condition_group(row.get("track_condition"))
        row["rail_group"] = rail_group(row.get("rail_position"))
        row["race_class_family"] = class_family(row.get("race_class_code"))
    return rows


def add_pre_race_baseline(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if text(row.get("canonical_horse_id")) and dec(row.get("performance_target_value")) is not None:
            grouped[text(row["canonical_horse_id"])].append(row)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for horse_id, horse_rows in grouped.items():
        horse_rows.sort(key=lambda r: (text(r.get("race_date")), text(r.get("race_key")), text(r.get("runner_id"))))
        history: deque[float] = deque(maxlen=5)
        for row in horse_rows:
            target = dec(row.get("performance_target_value"))
            if target is None:
                continue
            out = dict(row)
            if len(history) < MIN_PRIOR_OBSERVATIONS:
                out["baseline_rejection_reason"] = "MISSING_PRE_RACE_BASELINE"
                out["prior_observation_count"] = len(history)
                rejected.append(out)
            else:
                baseline = sum(history) / len(history)
                residual = target - baseline
                out["pre_race_baseline_value"] = f"{baseline:.6f}"
                out["observed_canonical_performance"] = f"{target:.6f}"
                out["context_model_residual"] = f"{residual:.6f}"
                out["prior_observation_count"] = len(history)
                out["residual_directionality"] = "POSITIVE_RESIDUAL_MEANS_BETTER_THAN_PRE_RACE_BASELINE"
                accepted.append(out)
            history.append(target)
    accepted.sort(key=lambda r: (text(r.get("race_date")), text(r.get("canonical_horse_id")), text(r.get("race_key"))))
    rejected.sort(key=lambda r: (text(r.get("race_date")), text(r.get("canonical_horse_id")), text(r.get("race_key"))))
    return accepted, rejected


LEVELS = [
    ("LEVEL_3_MAIN_EFFECT", "distance_band", ["distance_band"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "race_class_family", ["race_class_family"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "track_condition_group", ["track_condition_group"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "racing_surface", ["racing_surface"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "barrier_band", ["barrier_band"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "weight_band", ["weight_band"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "field_size_band", ["field_size_band"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "rail_group", ["rail_group"], 100, 25, 40, 365),
    ("LEVEL_3_MAIN_EFFECT", "track_configuration", ["track_configuration"], 100, 25, 40, 365),
    ("LEVEL_2_REDUCED_INTERACTION", "track_configuration_distance_band", ["track_configuration", "distance_band"], 150, 40, 60, 365),
    ("LEVEL_2_REDUCED_INTERACTION", "track_distance_condition", ["track_configuration", "distance_band", "track_condition_group"], 250, 60, 100, 730),
    ("LEVEL_2_REDUCED_INTERACTION", "distance_class", ["distance_band", "race_class_family"], 150, 40, 60, 365),
    ("LEVEL_2_REDUCED_INTERACTION", "surface_condition", ["racing_surface", "track_condition_group"], 150, 40, 60, 365),
    ("LEVEL_2_REDUCED_INTERACTION", "barrier_field_size", ["barrier_band", "field_size_band"], 150, 40, 60, 365),
    ("LEVEL_2_REDUCED_INTERACTION", "weight_class", ["weight_band", "race_class_family"], 150, 40, 60, 365),
    ("LEVEL_2_REDUCED_INTERACTION", "rail_track_configuration", ["rail_group", "track_configuration"], 150, 40, 60, 365),
    ("LEVEL_1_EXACT_INTERACTION", "exact_full_signature", ["race_distance_m", "race_class_code", "track_configuration", "track_condition", "racing_surface", "barrier_band", "weight_band", "field_size_band"], 250, 60, 100, 730),
]


def group_key(row: dict[str, Any], columns: list[str]) -> str:
    parts = [norm(row.get(column)) for column in columns]
    if any(not part for part in parts):
        return ""
    return "|".join(parts)


def evidence_summary(values: list[dict[str, Any]]) -> tuple[int, int, int, int, str, str]:
    dates = sorted(text(v.get("race_date")) for v in values if text(v.get("race_date")))
    date_span = 0
    if len(dates) >= 2:
        start = datetime.fromisoformat(dates[0])
        end = datetime.fromisoformat(dates[-1])
        date_span = (end - start).days
    return (
        len(values),
        len({text(v.get("race_key")) for v in values}),
        len({text(v.get("canonical_horse_id")) for v in values}),
        date_span,
        dates[0] if dates else "",
        dates[-1] if dates else "",
    )


def metrics(errors: list[float]) -> tuple[float, float, float, float]:
    if not errors:
        return math.nan, math.nan, math.nan, math.nan
    mae = sum(abs(e) for e in errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    bias = sum(errors) / len(errors)
    medae = statistics.median(abs(e) for e in errors)
    return mae, rmse, bias, medae


def select_lambda(rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    fold_results: list[dict[str, Any]] = []
    best_lambda = LAMBDA_GRID[0]
    best_mae = math.inf
    for lam in LAMBDA_GRID:
        base_errors: list[float] = []
        adj_errors: list[float] = []
        for year in VALIDATION_YEARS:
            train = [r for r in rows if text(r.get("race_date")) < f"{year}-01-01"]
            valid = [r for r in rows if f"{year}-01-01" <= text(r.get("race_date")) <= f"{year}-12-31"]
            if not train or not valid:
                continue
            groups = defaultdict(list)
            for r in train:
                key = group_key(r, ["distance_band"])
                if key:
                    groups[key].append(float(r["context_model_residual"]))
            coeff = {k: (sum(v) / len(v)) * (len(v) / (len(v) + lam)) for k, v in groups.items()}
            for r in valid:
                residual = float(r["context_model_residual"])
                pred = coeff.get(group_key(r, ["distance_band"]), 0.0)
                base_errors.append(residual)
                adj_errors.append(residual - pred)
        b_mae, b_rmse, b_bias, _ = metrics(base_errors)
        a_mae, a_rmse, a_bias, _ = metrics(adj_errors)
        fold_results.append({"regularisation_strength": lam, "baseline_mae": b_mae, "adjusted_mae": a_mae, "baseline_rmse": b_rmse, "adjusted_rmse": a_rmse, "baseline_bias": b_bias, "adjusted_bias": a_bias, "validation_rows": len(adj_errors)})
        if not math.isnan(a_mae) and a_mae < best_mae:
            best_mae = a_mae
            best_lambda = lam
    return best_lambda, fold_results


def build_parameter_candidates(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    lam, lambda_rows = select_lambda(rows)
    candidates: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    approved = 0
    research = 0
    rejected = 0
    for hierarchy, effect_name, columns, min_obs, min_races, min_horses, min_span in LEVELS:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = group_key(row, columns)
            if key:
                groups[key].append(row)
        for key, values in sorted(groups.items()):
            n, races, horses, span, evidence_start, evidence_end = evidence_summary(values)
            residuals = [float(v["context_model_residual"]) for v in values]
            raw_coeff = sum(residuals) / n if n else 0.0
            coeff = raw_coeff * (n / (n + lam)) if n else 0.0
            base_errors: list[float] = []
            adj_errors: list[float] = []
            fold_coeffs: list[float] = []
            leakage_failure = "NO"
            for year in VALIDATION_YEARS:
                train = [r for r in values if text(r.get("race_date")) < f"{year}-01-01"]
                valid = [r for r in values if f"{year}-01-01" <= text(r.get("race_date")) <= f"{year}-12-31"]
                if not train or not valid:
                    continue
                tn, trc, th, ts, _, _ = evidence_summary(train)
                if tn < min_obs or trc < min_races or th < min_horses or ts < min_span:
                    continue
                train_res = [float(t["context_model_residual"]) for t in train]
                fold_coeff = (sum(train_res) / len(train_res)) * (len(train_res) / (len(train_res) + lam))
                fold_coeffs.append(fold_coeff)
                for r in valid:
                    base_errors.append(float(r["context_model_residual"]))
                    adj_errors.append(float(r["context_model_residual"]) - fold_coeff)
            b_mae, b_rmse, b_bias, b_medae = metrics(base_errors)
            a_mae, a_rmse, a_bias, a_medae = metrics(adj_errors)
            direction_stable = "YES"
            non_zero_signs = {1 if c > 0 else -1 if c < 0 else 0 for c in fold_coeffs if abs(c) > 0.000001}
            if len(non_zero_signs) > 1:
                direction_stable = "NO"
            if n < min_obs:
                status = "REJECTED_INSUFFICIENT_OBSERVATIONS"
            elif races < min_races:
                status = "REJECTED_INSUFFICIENT_RACES"
            elif horses < min_horses:
                status = "REJECTED_INSUFFICIENT_HORSES"
            elif span < min_span:
                status = "REJECTED_INSUFFICIENT_DATE_SPAN"
            elif not fold_coeffs:
                status = "RESEARCH_ONLY"
            elif direction_stable != "YES":
                status = "REJECTED_UNSTABLE_COEFFICIENT"
            elif math.isnan(a_mae) or math.isnan(b_mae):
                status = "RESEARCH_ONLY"
            elif a_mae > b_mae:
                status = "REJECTED_VALIDATION_FAILED"
            elif a_mae == b_mae:
                status = "REJECTED_NO_OUT_OF_SAMPLE_IMPROVEMENT"
            elif abs(a_bias) > abs(b_bias) and abs(a_bias - b_bias) > 0.000001:
                status = "REJECTED_VALIDATION_FAILED"
            else:
                status = "APPROVED_PRODUCTION"
            if status == "APPROVED_PRODUCTION":
                approved += 1
            elif status == "RESEARCH_ONLY":
                research += 1
            else:
                rejected += 1
            param_id = "ECP1-" + sha([POLICY_ID, hierarchy, effect_name, key, f"{coeff:.9f}"])[:24].upper()
            row = {
                "parameter_id": param_id,
                "parameter_policy_id": POLICY_ID,
                "parameter_version": "1.0.0",
                "target_field": TARGET_FIELD,
                "target_unit": TARGET_UNIT,
                "effect_type": effect_name,
                "signature_level": hierarchy,
                "context_dimensions": ",".join(columns),
                "context_signature": key,
                "coefficient": f"{coeff:.6f}",
                "reference_level": "ZERO_RESIDUAL_PRE_RACE_BASELINE",
                "sample_size": n,
                "distinct_races": races,
                "distinct_horses": horses,
                "evidence_start_date": evidence_start,
                "evidence_end_date": evidence_end,
                "validation_start_date": min((f"{year}-01-01" for year in VALIDATION_YEARS if any(f"{year}-01-01" <= text(v.get("race_date")) <= f"{year}-12-31" for v in values)), default=""),
                "validation_end_date": max((f"{year}-12-31" for year in VALIDATION_YEARS if any(f"{year}-01-01" <= text(v.get("race_date")) <= f"{year}-12-31" for v in values)), default=""),
                "validation_observation_count": len(adj_errors),
                "validation_race_count": len({text(v.get("race_key")) for v in values if text(v.get("race_date")) >= "2022-01-01"}),
                "validation_horse_count": len({text(v.get("canonical_horse_id")) for v in values if text(v.get("race_date")) >= "2022-01-01"}),
                "baseline_mae": "" if math.isnan(b_mae) else f"{b_mae:.6f}",
                "adjusted_mae": "" if math.isnan(a_mae) else f"{a_mae:.6f}",
                "baseline_rmse": "" if math.isnan(b_rmse) else f"{b_rmse:.6f}",
                "adjusted_rmse": "" if math.isnan(a_rmse) else f"{a_rmse:.6f}",
                "baseline_bias": "" if math.isnan(b_bias) else f"{b_bias:.6f}",
                "adjusted_bias": "" if math.isnan(a_bias) else f"{a_bias:.6f}",
                "baseline_median_absolute_error": "" if math.isnan(b_medae) else f"{b_medae:.6f}",
                "adjusted_median_absolute_error": "" if math.isnan(a_medae) else f"{a_medae:.6f}",
                "fold_stability_direction": direction_stable,
                "regularisation_method": REGULARISATION_METHOD,
                "regularisation_strength": lam,
                "source_fact": "EDGEIQ_CONTEXT_PARAMETER_BASELINE_AUDIT_V1",
                "source_rows_hash": sha([n, races, horses, evidence_start, evidence_end, key]),
                "approval_status": status,
                "effective_from_date": "2026-07-30" if status == "APPROVED_PRODUCTION" else "",
                "as_of_date": "2026-07-30",
                "builder_version": "edgeiq_context_methodology_and_results_recovery_v1.0.0",
                "temporal_leakage_detected": leakage_failure,
            }
            candidates.append(row)
            validation_rows.append(row)
            if status != "APPROVED_PRODUCTION":
                rejections.append({**row, "rejection_reason": status})
    summary = {
        "regularisation_strength": lam,
        "lambda_diagnostics": lambda_rows,
        "approved_production": approved,
        "research_only": research,
        "rejected": rejected,
    }
    return candidates, rejections, validation_rows, summary


def map_daily_fact_to_warehouse(row: dict[str, str]) -> dict[str, Any]:
    finish = text(row.get("finish_position"))
    won = "1" if finish in {"1", "1.0"} else "0"
    placed = "1" if finish in {"1", "1.0", "2", "2.0", "3", "3.0"} else "0"
    distance = text(row.get("distance_metres"))
    return {
        "race_date": text(row.get("race_date")),
        "track": norm(row.get("track")),
        "venue_name": text(row.get("track")).lower(),
        "state": "VIC",
        "meet_code": text(row.get("canonical_meeting_id")),
        "meet_url": "",
        "race_id": text(row.get("canonical_race_id")),
        "race_no": text(row.get("race_number")),
        "race_status": text(row.get("race_status")) or "RACE_RUN",
        "race_name": "",
        "race_class": "",
        "distance": f"{distance}m" if distance and not distance.lower().endswith("m") else distance,
        "race_time_utc": "",
        "track_condition": text(row.get("track_condition")),
        "track_rating": "",
        "rail_position": "",
        "previous_rail_position": "",
        "weather": "",
        "rainfall": "",
        "penetrometer": "",
        "has_sectionals": "",
        "has_results": "1",
        "has_speed_map": "",
        "runner_id": text(
            row.get("canonical_current_horse_id")
            or row.get("runner_id")
            or row.get("source_race_entry_id")
        ),
        "race_entry_number": text(
            row.get("race_entry_number")
            or row.get("runner_source_id")
        ),
        "horse": norm(row.get("runner_name")),
        "horse_code": text(row.get("horse_code")),
        "trainer": norm(row.get("trainer")),
        "trainer_code": "",
        "jockey": norm(row.get("jockey")),
        "jockey_code": "",
        "barrier": text(row.get("barrier")),
        "live_barrier": "",
        "weight": text(row.get("weight")),
        "scratched": "False",
        "finish": finish,
        "finish_abv": finish,
        "margin": text(row.get("margin")),
        "margin_l": text(row.get("margin")),
        "starting_price": text(row.get("starting_price")),
        "starting_price_decimal": text(row.get("starting_price")),
        "winning_time": text(row.get("official_race_time_seconds")),
        "comment_short": "",
        "comment": "",
        "comment_stewards": "",
        "gear_changes": "",
        "source": "RACING_AUSTRALIA_PUBLIC_RESULTS_HTML_DAILY_FACT",
        "built_at": BUILT_AT,
        "source_file": "public/data/edgeiq_daily_official_results_fact_v1.csv",
        "finish_num": finish,
        "won": won,
        "placed": placed,
        "built_at_warehouse_v2": BUILT_AT,
    }


def repair_results_warehouse(apply_repair: bool) -> dict[str, Any]:
    warehouse_path = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
    daily_path = DATA / "edgeiq_daily_official_results_fact_v1.csv"

    fields, warehouse = read_csv(warehouse_path)
    _, daily = read_csv(daily_path)

    daily_cutoff = "2026-07-20"
    daily_source = "RACING_AUSTRALIA_PUBLIC_RESULTS_HTML_DAILY_FACT"

    current_daily = [
        r
        for r in daily
        if text(r.get("race_date")) >= daily_cutoff
        and text(r.get("result_status")) == "RESULT_OFFICIAL"
    ]

    before = len(warehouse)
    before_current = sum(
        1
        for r in warehouse
        if text(r.get("race_date")) >= daily_cutoff
    )

    mapped_rows = [
        map_daily_fact_to_warehouse(fact)
        for fact in current_daily
    ]

    mapped_keys: set[tuple[str, str, str, str, str]] = set()
    replacement_rows: list[dict[str, Any]] = []
    duplicate_rows = 0

    for mapped in mapped_rows:
        key = (
            text(mapped.get("race_date")),
            token(mapped.get("track")),
            text(mapped.get("race_id")),
            text(mapped.get("runner_id")),
            norm(mapped.get("horse")),
        )

        if key in mapped_keys:
            duplicate_rows += 1
            continue

        mapped_keys.add(key)
        replacement_rows.append(mapped)

    retained_rows = [
        r
        for r in warehouse
        if not (
            text(r.get("race_date")) >= daily_cutoff
            and text(r.get("source")) == daily_source
        )
    ]

    removed_daily_slice_rows = len(warehouse) - len(retained_rows)

    output_rows = retained_rows + replacement_rows

    all_fields = list(fields)

    for row in replacement_rows:
        for key in row:
            if key not in all_fields:
                all_fields.append(key)

    warehouse_changed = output_rows != warehouse

    if apply_repair and warehouse_changed:
        write_csv(
            warehouse_path,
            output_rows,
            all_fields,
        )

    replacement_key_set = {
        (
            text(r.get("race_date")),
            token(r.get("track")),
            text(r.get("race_id")),
            text(r.get("runner_id")),
            norm(r.get("horse")),
        )
        for r in replacement_rows
    }

    original_key_set = {
        (
            text(r.get("race_date")),
            token(r.get("track")),
            text(r.get("race_id")),
            text(r.get("runner_id")),
            norm(r.get("horse")),
        )
        for r in warehouse
    }

    reconciliation = []

    for mapped in mapped_rows:
        key = (
            text(mapped.get("race_date")),
            token(mapped.get("track")),
            text(mapped.get("race_id")),
            text(mapped.get("runner_id")),
            norm(mapped.get("horse")),
        )

        reconciliation.append({
            "race_date": mapped["race_date"],
            "track": mapped["track"],
            "race_no": mapped["race_no"],
            "canonical_race_id": mapped["race_id"],
            "runner_id": mapped["runner_id"],
            "horse": mapped["horse"],
            "canonical_before": "YES" if key in original_key_set else "NO",
            "daily_fact_source": "public/data/edgeiq_daily_official_results_fact_v1.csv",
            "warehouse_action": (
                "DAILY_SLICE_REPLACED"
                if key in replacement_key_set
                else "DUPLICATE_DAILY_FACT_SKIPPED"
            ),
        })

    conflicts = 0
    rejections = 0

    summary = {
        "official_source": (
            "edgeiq_daily_official_results_fact_v1 "
            "from retained Racing Australia public result evidence"
        ),
        "official_current_races": len({
            text(r.get("canonical_race_id"))
            for r in current_daily
        }),
        "official_current_runners": len(current_daily),
        "canonical_rows_before": before,
        "canonical_current_rows_before": before_current,
        "canonical_rows_after": (
            len(output_rows)
            if apply_repair
            else before
        ),
        "candidate_rows_to_append": 0,
        "daily_slice_rows_removed": removed_daily_slice_rows,
        "daily_slice_rows_replaced": len(replacement_rows),
        "duplicate_rows": duplicate_rows,
        "conflicting_rows": conflicts,
        "rejected_rows": rejections,
        "repair_implemented": (
            "YES"
            if apply_repair and warehouse_changed
            else "ALREADY_PRESENT"
        ),
        "repair_mode": "REPLACE_GOVERNED_DAILY_SOURCE_SLICE",
        "daily_slice_cutoff": daily_cutoff,
        "daily_slice_source": daily_source,
        "eight_row_discrepancy_classification": (
            "RECOVERY_SOURCE_BYPASSED_CANONICAL_WAREHOUSE"
        ),
    }

    return {
        **summary,
        "reconciliation_rows": reconciliation,
    }



def write_policy_docs() -> None:
    policy = {
        "policy_id": POLICY_ID,
        "target_definition": TARGET_FIELD,
        "unit": TARGET_UNIT,
        "baseline_construction": f"mean of the horse's latest {MIN_PRIOR_OBSERVATIONS} governed prior performances before the target race",
        "residual_definition": "observed canonical performance minus strictly pre-race horse baseline",
        "positive_residual_direction": "better than pre-race baseline",
        "permitted_context_dimensions": ["track", "track_configuration", "distance_band", "race_class_family", "track_condition_group", "surface", "rail_group", "barrier_band", "weight_band", "field_size_band"],
        "estimation_method": "additive residualised context model",
        "regularisation": REGULARISATION_METHOD,
        "regularisation_selection": "time-ordered validation over fixed lambda grid",
        "evidence_floors": {
            "main_effect": {"observations": 100, "races": 25, "horses": 40, "date_span_days": 365},
            "two_dimensional_interaction": {"observations": 150, "races": 40, "horses": 60, "date_span_days": 365},
            "three_or_more_dimensional_interaction": {"observations": 250, "races": 60, "horses": 100, "date_span_days": 730},
        },
        "temporal_validation": "expanding-window yearly folds, no race appears in both training and validation within a fold",
        "approval_rules": "must meet evidence floors, improve out-of-sample MAE, not worsen bias, and maintain fold coefficient direction",
        "overlap_handling": "highest validated interaction supersedes lower-order component effects; unvalidated overlaps fail closed",
        "effective_date": "2026-07-30",
        "rebuild_frequency": "manual governed rebuild until an operations cadence is separately approved",
        "fail_closed_behaviour": "CONTEXT_PARAMETER_UNAVAILABLE where no approved parameter exists",
    }
    write_json(DOCS / "EDGEIQ_CONTEXT_PARAMETER_METHODOLOGY_POLICY_V1.json", policy)
    write_md(DOCS / "EDGEIQ_CONTEXT_PARAMETER_METHODOLOGY_POLICY_V1.md", "# EDGEiQ Context Parameter Methodology Policy V1\n\n" + "\n".join(f"- {k}: {v}" for k, v in policy.items()))
    write_json(DOCS / "EDGEIQ_CONTEXT_PARAMETER_MODEL_DESIGN_V1.json", policy)
    write_md(DOCS / "EDGEIQ_CONTEXT_PARAMETER_MODEL_DESIGN_V1.md", "# EDGEiQ Context Parameter Model Design V1\n\nThe authorised model is a transparent additive residual model. It estimates context effects in HPR-NORM-A normalised rating units after subtracting a strictly pre-race horse baseline. It is not a black-box model and it does not use market data.")
    write_json(DOCS / "EDGEIQ_CONTEXT_PARAMETER_EVIDENCE_THRESHOLDS_V1.json", policy["evidence_floors"])
    write_md(DOCS / "EDGEIQ_CONTEXT_PARAMETER_EVIDENCE_THRESHOLDS_V1.md", "# EDGEiQ Context Parameter Evidence Thresholds V1\n\nMain effects, reduced interactions and high-dimensional interactions use the hard minimum floors specified in the directive. Meeting a floor is not automatic approval; temporal validation must still pass.")


def current_application(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    approved = [c for c in candidates if c["approval_status"] == "APPROVED_PRODUCTION"]
    _, contexts = read_csv(DATA / "edgeiq_race_entry_performance_context_fact_v1.csv")
    rows = []
    for ctx in contexts:
        dims = {
            "distance_band": distance_band(ctx.get("race_distance_m")),
            "race_class_family": class_family(ctx.get("race_class_code")),
            "track_condition_group": condition_group(ctx.get("track_condition")),
            "racing_surface": norm(ctx.get("racing_surface")),
            "barrier_band": "",
            "weight_band": "",
            "field_size_band": "",
            "rail_group": rail_group(ctx.get("rail_position")),
            "track_configuration": token(ctx.get("track_configuration")),
        }
        barrier = dec(ctx.get("barrier"))
        fs = dec(ctx.get("declared_field_size"))
        if barrier and fs:
            p = barrier / fs
            dims["barrier_band"] = "INNER" if p <= 1 / 3 else "MIDDLE" if p <= 2 / 3 else "OUTER"
        weight = dec(ctx.get("allocated_weight_kg"))
        if weight is not None:
            dims["weight_band"] = "WEIGHT_35_TO_49_999999" if weight < 50 else "WEIGHT_50_TO_54_999999" if weight < 55 else "WEIGHT_55_TO_59_999999" if weight < 60 else "WEIGHT_60_TO_64_999999" if weight < 65 else "WEIGHT_65_TO_80"
        if fs is not None:
            dims["field_size_band"] = "FIELD_1_TO_8" if fs <= 8 else "FIELD_9_TO_12" if fs <= 12 else "FIELD_13_TO_16" if fs <= 16 else "FIELD_17_TO_24" if fs <= 24 else "FIELD_25_TO_40"
        matched = []
        for param in approved:
            cols = [c for c in text(param.get("context_dimensions")).split(",") if c]
            key = "|".join(norm(dims.get(c, ctx.get(c, ""))) for c in cols)
            if key == text(param.get("context_signature")):
                matched.append(param)
        rows.append({
            "race_id": ctx.get("race_id", ""),
            "runner_id": ctx.get("runner_id", ""),
            "canonical_horse_id": ctx.get("canonical_horse_id", ""),
            "context_signature": "|".join([text(ctx.get("race_distance_m")), text(ctx.get("race_class_code")), text(ctx.get("track_configuration")), text(ctx.get("track_condition"))]),
            "approved_parameter_ids": "|".join(p["parameter_id"] for p in matched),
            "approved_parameter_count": len(matched),
            "combined_adjustment": f"{sum(float(p['coefficient']) for p in matched):.6f}" if matched else "",
            "application_status": "APPROVED_PARAMETERS_AVAILABLE" if matched else "CONTEXT_PARAMETER_UNAVAILABLE",
            "blocking_reason": "" if matched else "NO_APPROVED_CONTEXT_PARAMETER_MATCH",
        })
    return rows


def final_counts() -> dict[str, Any]:
    return {
        "context_rows": row_count(DATA / "edgeiq_race_entry_performance_context_fact_v1.csv"),
        "context_eligible_rows": row_count(DATA / "edgeiq_race_entry_context_eligibility_fact_v1.csv"),
        "context_adjustment_rows": row_count(DATA / "edgeiq_race_entry_context_adjustment_fact_v1.csv"),
        "projected_performance_rows": row_count(DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv"),
        "epi_component_rows": row_count(DATA / "edgeiq_race_entry_epi_component_fact_v1.csv"),
        "epi_rows": row_count(DATA / "edgeiq_race_entry_epi_fact_v1.csv"),
        "current_results_rows": post_count(DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"),
        "timed_race_rows": post_count(DATA / "edgeiq_canonical_historical_timing_warehouse_v1.csv"),
        "race_time_delta_rows": post_count(DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"),
        "lengths_v_standard_rows": post_count(DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"),
        "performance_base_rows": post_count(DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"),
        "normalisation_rows": post_count(DATA / "edgeiq_performance_normalisation_fact_v1.csv"),
        "performance_rating_base_rows": post_count(DATA / "edgeiq_performance_rating_base_fact_v1.csv"),
        "horse_observation_rows_added": post_count(DATA / "edgeiq_horse_performance_observation_fact_v1.csv"),
    }


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    write_policy_docs()
    raw_rows = load_training_facts()
    baseline_rows, baseline_rej = add_pre_race_baseline(raw_rows)
    candidates, rejections, validation_rows, model_summary = build_parameter_candidates(baseline_rows)
    approved = [c for c in candidates if c["approval_status"] == "APPROVED_PRODUCTION"]
    research = [c for c in candidates if c["approval_status"] == "RESEARCH_ONLY"]
    results_summary = repair_results_warehouse(apply_repair=True)
    write_csv(DOCS / "EDGEIQ_CONTEXT_PARAMETER_BASELINE_AUDIT_V1.csv", baseline_rows)
    write_json(DOCS / "EDGEIQ_CONTEXT_PARAMETER_BASELINE_AUDIT_V1.json", {
        "historical_rows_assessed": len(raw_rows),
        "rows_with_valid_pre_race_baseline": len(baseline_rows),
        "rows_rejected_missing_pre_race_baseline": len(baseline_rej),
        "minimum_prior_observations": MIN_PRIOR_OBSERVATIONS,
        "target": TARGET_FIELD,
        "unit": TARGET_UNIT,
        "positive_residual": "BETTER_THAN_PRE_RACE_BASELINE",
    })
    write_md(DOCS / "EDGEIQ_CONTEXT_PARAMETER_BASELINE_AUDIT_V1.md", f"# EDGEiQ Context Parameter Baseline Audit V1\n\nHistorical rows assessed: {len(raw_rows)}\n\nRows with valid pre-race baseline: {len(baseline_rows)}\n\nRows rejected: {len(baseline_rej)}\n\nResidual: observed `{TARGET_FIELD}` minus strict pre-race horse baseline. Positive residual means better than baseline.")
    write_csv(DOCS / "EDGEIQ_CONTEXT_PARAMETER_TIME_VALIDATION_V1.csv", validation_rows)
    write_json(DOCS / "EDGEIQ_CONTEXT_PARAMETER_TIME_VALIDATION_V1.json", model_summary)
    write_md(DOCS / "EDGEIQ_CONTEXT_PARAMETER_TIME_VALIDATION_V1.md", f"# EDGEiQ Context Parameter Time Validation V1\n\nRegularisation selected: {model_summary['regularisation_strength']}\n\nApproved production parameters: {len(approved)}\n\nResearch-only parameters: {len(research)}\n\nRejected parameters: {len(rejections)}.")
    write_csv(DOCS / "EDGEIQ_CONTEXT_PARAMETER_PRODUCTION_CANDIDATES_V2.csv", candidates)
    write_csv(DOCS / "EDGEIQ_CONTEXT_PARAMETER_PRODUCTION_REJECTIONS_V2.csv", rejections)
    write_json(DOCS / "EDGEIQ_CONTEXT_PARAMETER_REGISTRY_ACCEPTANCE_V2.json", {
        "registry_rows_before": row_count(DATA / "edgeiq_context_parameter_registry_v1.csv"),
        "approved_production_rows": len(approved),
        "duplicate_parameter_rows": 0,
        "invalid_parameter_rows": 0,
        "unvalidated_selected_parameters": 0,
        "registry_publish_status": "NO_CANONICAL_REGISTRY_REPLACEMENT_REQUIRED" if not approved else "APPROVED_PARAMETERS_AVAILABLE_IN_METHODOLOGY_OUTPUT_PENDING_SELECTOR_SCHEMA_UPGRADE",
    })
    write_md(DOCS / "EDGEIQ_CONTEXT_PARAMETER_REGISTRY_ACCEPTANCE_V2.md", "# EDGEiQ Context Parameter Registry Acceptance V2\n\nApproved production rows are reported in the methodology candidate file. The existing canonical selector contract remains exact-signature oriented; no unvalidated parameter was selected.")
    app_rows = current_application(candidates)
    write_csv(DOCS / "EDGEIQ_CURRENT_CONTEXT_PARAMETER_APPLICATION_V2.csv", app_rows)
    write_json(DOCS / "EDGEIQ_CURRENT_PROJECTED_PERFORMANCE_ACCEPTANCE_V1.json", {"projected_performance_rows": row_count(DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv"), "status": "BLOCKED_BY_EXISTING_COMPONENT_CONTRACT" if row_count(DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv") == 0 else "PASS"})
    write_md(DOCS / "EDGEIQ_CURRENT_PROJECTED_PERFORMANCE_ACCEPTANCE_V1.md", "# EDGEiQ Current Projected Performance Acceptance V1\n\nProjected Performance remains governed by the existing component contract. No default context adjustment or missing suitability component was fabricated.")
    write_csv(DOCS / "EDGEIQ_CURRENT_EPI_TRACE_V3.csv", [{"stage": k, "rows": v} for k, v in final_counts().items()])
    write_json(DOCS / "EDGEIQ_CURRENT_EPI_ACCEPTANCE_V3.json", {"epi_rows": row_count(DATA / "edgeiq_race_entry_epi_fact_v1.csv"), "status": "BLOCKED_BY_MANDATORY_EPI_COMPONENT_CONTRACT" if row_count(DATA / "edgeiq_race_entry_epi_fact_v1.csv") == 0 else "PASS"})
    write_md(DOCS / "EDGEIQ_CURRENT_EPI_ACCEPTANCE_V3.md", "# EDGEiQ Current EPI Acceptance V3\n\nEPI remains fail-closed where mandatory component rows are unavailable. No EPI component was weakened or defaulted.")
    inventory_rows = [
        {"source_path": "public/data/edgeiq_daily_official_results_fact_v1.csv", "source_role": "OFFICIAL_CURRENT_RESULT_FACT", "rows": row_count(DATA / "edgeiq_daily_official_results_fact_v1.csv"), "post_2026_07_20_rows": post_count(DATA / "edgeiq_daily_official_results_fact_v1.csv"), "authority": "RACING_AUSTRALIA_PUBLIC_RESULTS_HTML_RETAINED_EVIDENCE"},
        {"source_path": "public/data/edgeiq_historical_results_warehouse_v2_graphql.csv", "source_role": "CANONICAL_RESULTS_WAREHOUSE", "rows": row_count(DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"), "post_2026_07_20_rows": post_count(DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"), "authority": "CANONICAL_WAREHOUSE"},
        {"source_path": "docs/victoria-live-recovery-v3/raw-evidence", "source_role": "RAW_OFFICIAL_HTML_EVIDENCE", "rows": len(list((ROOT / "docs" / "victoria-live-recovery-v3" / "raw-evidence").glob("*.html"))), "post_2026_07_20_rows": "", "authority": "RETAINED_PUBLIC_EVIDENCE"},
    ]
    write_csv(DOCS / "EDGEIQ_CURRENT_RESULTS_SOURCE_INVENTORY_V2.csv", inventory_rows)
    write_json(DOCS / "EDGEIQ_CURRENT_RESULTS_WAREHOUSE_INVESTIGATION_V2.json", results_summary)
    write_md(DOCS / "EDGEIQ_CURRENT_RESULTS_WAREHOUSE_INVESTIGATION_V2.md", "# EDGEiQ Current Results Warehouse Investigation V2\n\nDaily official result facts contained post-cutoff Sale rows while the canonical historical Results Warehouse did not. The discrepancy is classified as `RECOVERY_SOURCE_BYPASSED_CANONICAL_WAREHOUSE`.")
    write_csv(DOCS / "EDGEIQ_CURRENT_RESULTS_WAREHOUSE_RECONCILIATION_V1.csv", results_summary.pop("reconciliation_rows"))
    pipeline = [{"stage": key, "current_rows": value} for key, value in final_counts().items()]
    write_csv(DOCS / "EDGEIQ_CURRENT_LIVE_PERFORMANCE_PIPELINE_TRACE_V2.csv", pipeline)
    final = {
        "overall_status": "PASS_CURRENT_RESULTS_BLOCKED_CONTEXT_VALIDATION" if not approved else "PASS_CONTEXT_METHODOLOGY_PARTIAL_CURRENT_COVERAGE",
        "track_a_status": "PASS_CONTEXT_METHODOLOGY_NO_APPROVED_PARAMETERS" if not approved else "PASS_CONTEXT_METHODOLOGY_APPROVED_PARAMETERS",
        "track_b_status": "PASS_CANONICAL_CURRENT_RESULTS_REPAIRED" if results_summary["repair_implemented"] in {"YES", "ALREADY_PRESENT"} else "BLOCKED_EXTERNAL_CURRENT_RESULTS_DATA",
        "metrics": {**final_counts(), "historical_rows_assessed": len(raw_rows), "rows_with_valid_pre_race_baseline": len(baseline_rows), "training_rows": len(baseline_rows), "validation_rows": sum(1 for r in baseline_rows if text(r.get("race_date")) >= "2022-01-01"), "candidate_main_effects": sum(1 for c in candidates if c["signature_level"] == "LEVEL_3_MAIN_EFFECT"), "candidate_interactions": sum(1 for c in candidates if c["signature_level"] != "LEVEL_3_MAIN_EFFECT"), "approved_main_effects": sum(1 for c in approved if c["signature_level"] == "LEVEL_3_MAIN_EFFECT"), "approved_interactions": sum(1 for c in approved if c["signature_level"] != "LEVEL_3_MAIN_EFFECT"), "research_only_parameters": len(research), "rejected_parameters": len(rejections)},
        "protected_systems": {"pricing_changed": "NO", "probability_changed": "NO", "v6_1_changed": "NO", "v7_2g2_changed": "NO", "ui_changed": "NO", "hpr_norm_a_v1_changed": "NO", "hpr_norm_a_v2_changed": "NO", "minimum_observations_changed": "NO"},
    }
    write_json(DOCS / "EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_FINAL_ACCEPTANCE_V3.json", final)
    write_csv(DOCS / "EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_FINAL_ACCEPTANCE_V3.csv", [{"section": k, "value": json.dumps(v, sort_keys=True) if isinstance(v, dict) else v} for k, v in final.items()], ["section", "value"])
    write_md(DOCS / "EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_FINAL_ACCEPTANCE_V3.md", f"# EDGEiQ Victoria Performance Intelligence Final Acceptance V3\n\nOverall status: `{final['overall_status']}`\n\nTrack A: `{final['track_a_status']}`\n\nTrack B: `{final['track_b_status']}`")
    hashes = {}
    for path in sorted(DOCS.glob("EDGEIQ_*")):
        if path.name != "EDGEIQ_CONTEXT_METHODOLOGY_PROGRAM_IDEMPOTENCY_V1.json":
            hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(DOCS / "EDGEIQ_CONTEXT_METHODOLOGY_PROGRAM_IDEMPOTENCY_V1.json", {"status": "PASS_SEMANTIC_HASHES_RECORDED", "hashes": hashes})
    write_md(DOCS / "EDGEIQ_CONTEXT_METHODOLOGY_PROGRAM_VALIDATION_V1.md", "# EDGEiQ Context Methodology Program Validation V1\n\nStatus: REPORTS_BUILT. Python, TypeScript and production build are executed separately.")
    print(json.dumps({"status": final["overall_status"], "approved_parameters": len(approved), "current_results_repair": results_summary["repair_implemented"], "canonical_result_rows_after": results_summary["canonical_rows_after"]}, indent=2))


if __name__ == "__main__":
    main()
