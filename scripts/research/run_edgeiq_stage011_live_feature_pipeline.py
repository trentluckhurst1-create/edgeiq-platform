"""Research-only Stage011 live feature pipeline for the Caulfield dry run.

This builder consolidates the live field, Racing.com-native historical form,
and existing LAB245B candidate evidence into one 35-feature Stage011 matrix.
It does not retrain, score incomplete rows, read target-race outcomes, or use
market data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


FEATURES = [
    "current_distance",
    "hist_runs",
    "lvs_last1",
    "lvs_mean3",
    "lvs_mean5",
    "lvs_median5",
    "lvs_std5",
    "lvs_peak",
    "lvs_worst5",
    "margin_mean5",
    "margin_std5",
    "margin_worst5",
    "margin_last1",
    "margin_last2",
    "last_distance",
    "margin_change_l1_l2",
    "margin_per_runner_last1",
    "margin_per_runner_last2",
    "days_since_last",
    "dist200_runs",
    "dist200_lvs_mean",
    "dist200_lvs_best",
    "represented_field_size",
    "barrier_position_pct",
    "jockey_prior_starts",
    "jockey_prior_win_rate",
    "jockey_prior_top3_rate",
    "trainer_prior_starts",
    "trainer_prior_win_rate",
    "trainer_prior_top3_rate",
    "clean_finish_mean5",
    "clean_last_finish",
    "clean_last_won",
    "clean_last_top3",
    "clean_finish_hist_n",
]

LVS_FEATURES = {
    "lvs_last1",
    "lvs_mean3",
    "lvs_mean5",
    "lvs_median5",
    "lvs_std5",
    "lvs_peak",
    "lvs_worst5",
    "dist200_lvs_mean",
    "dist200_lvs_best",
}

RCOM_NATIVE_CERTIFIED_FEATURES = {
    "current_distance",
    "hist_runs",
    "margin_mean5",
    "margin_std5",
    "margin_worst5",
    "margin_last1",
    "margin_last2",
    "last_distance",
    "margin_change_l1_l2",
    "margin_per_runner_last1",
    "margin_per_runner_last2",
    "days_since_last",
    "dist200_runs",
    "represented_field_size",
    "barrier_position_pct",
    "clean_finish_mean5",
    "clean_last_finish",
    "clean_last_won",
    "clean_last_top3",
    "clean_finish_hist_n",
}

PERSONNEL_FEATURES = {
    "jockey_prior_starts",
    "jockey_prior_win_rate",
    "jockey_prior_top3_rate",
    "trainer_prior_starts",
    "trainer_prior_win_rate",
    "trainer_prior_top3_rate",
}

FORBIDDEN_LOWER = {
    "y",
    "winner",
    "won",
    "outcome",
    "sp",
    "bsp",
    "starting_price",
    "closing_price",
    "profit",
    "return",
}


@dataclass(frozen=True)
class Paths:
    field: Path
    form: Path
    public_snapshot: Path
    lab245b_candidates: Path
    output_dir: Path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_distance(value: object) -> float:
    if pd.isna(value):
        return math.nan
    m = re.search(r"(\d+(?:\.\d+)?)\s*m", str(value), flags=re.I)
    return float(m.group(1)) if m else math.nan


def parse_margin(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>", "-"}:
        return math.nan
    m = re.search(r"(-?\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else math.nan


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y", "scratched", "scr"}


def stats_last(values: Iterable[float], n: int) -> tuple[float, float, float]:
    arr = np.asarray(list(values)[-n:], dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return math.nan, math.nan, math.nan
    return float(np.mean(arr)), float(np.median(arr)), float(np.std(arr))


def clean_columns(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.copy()
    d.columns = [str(c).strip() for c in d.columns]
    forbidden = sorted(c for c in d.columns if c.lower() in FORBIDDEN_LOWER)
    if forbidden:
        raise RuntimeError(f"Forbidden outcome/market columns present: {forbidden}")
    return d


def load_field(path: Path, target_date: str, venue: str) -> pd.DataFrame:
    d = clean_columns(pd.read_csv(path, dtype="string"))
    need = {
        "race_date",
        "venue",
        "race_no",
        "race_id",
        "horse_name",
        "horse_code",
        "race_entry_id",
        "barrier",
        "scratched",
        "trainer_code",
        "jockey_code",
    }
    missing = sorted(need - set(d.columns))
    if missing:
        raise RuntimeError(f"Field source missing columns: {missing}")
    d = d[d["race_date"].eq(target_date) & d["venue"].str.upper().eq(venue.upper())].copy()
    if d.empty:
        raise RuntimeError(f"No live field rows found for {venue} {target_date}")
    if d.duplicated(["race_id", "race_entry_id"]).any():
        dup = d[d.duplicated(["race_id", "race_entry_id"], keep=False)][["race_id", "race_entry_id"]].head(10)
        raise RuntimeError(f"Duplicate live runners: {dup.to_dict('records')}")
    d["race_no_num"] = pd.to_numeric(d["race_no"], errors="coerce")
    d["barrier_num"] = pd.to_numeric(d["barrier"], errors="coerce")
    d["is_scratched"] = d["scratched"].map(parse_bool)
    return d.sort_values(["race_no_num", "race_entry_id"], kind="stable").reset_index(drop=True)


def load_form(path: Path, target_date: str) -> pd.DataFrame:
    d = clean_columns(pd.read_csv(path, dtype="string"))
    need = {
        "horse_code",
        "horse_name",
        "race_date",
        "race_code",
        "distance",
        "field_size",
        "finish",
        "margin",
        "jockey_id",
        "trainer_id",
    }
    missing = sorted(need - set(d.columns))
    if missing:
        raise RuntimeError(f"Form source missing columns: {missing}")
    d["race_date_dt"] = pd.to_datetime(d["race_date"], errors="coerce")
    target = pd.Timestamp(target_date)
    d = d[d["race_date_dt"].notna() & d["race_date_dt"].lt(target)].copy()
    d["distance_m"] = d["distance"].map(parse_distance)
    d["field_size_num"] = pd.to_numeric(d["field_size"], errors="coerce")
    d["finish_num"] = pd.to_numeric(d["finish"], errors="coerce")
    d["margin_len"] = d["margin"].map(parse_margin)
    d.loc[d["finish_num"].eq(1), "margin_len"] = 0.0
    d["race_code_sort"] = pd.to_numeric(d["race_code"], errors="coerce")
    return d.sort_values(["horse_code", "race_date_dt", "race_code_sort"], kind="stable").reset_index(drop=True)


def scheduled_utc(target_date: str, local_time_text: str) -> str:
    text = str(local_time_text or "").strip().lower()
    if not text:
        return ""
    parsed = pd.to_datetime(f"{target_date} {text}", format="%Y-%m-%d %I:%M%p", errors="coerce")
    if pd.isna(parsed):
        return ""
    local = parsed.to_pydatetime().replace(tzinfo=ZoneInfo("Australia/Melbourne"))
    return local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_race_metadata(path: Path, target_date: str, venue: str) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=["race_date", "venue", "race_no", "current_distance"])
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = []
    seen = set()
    for race in payload.get("races", []):
        if str(race.get("race_date")) != target_date or str(race.get("venue", "")).upper() != venue.upper():
            continue
        race_no = str(race.get("race_no"))
        key = (target_date, venue.upper(), race_no)
        if key in seen:
            continue
        seen.add(key)
        raw_text = str(race.get("raw_text", ""))
        distance = math.nan
        scheduled = ""
        for line in [x.strip() for x in raw_text.splitlines() if x.strip()]:
            if math.isnan(distance) and re.fullmatch(r"\d{3,4}m", line, flags=re.I):
                distance = parse_distance(line)
            if not scheduled and re.fullmatch(r"\d{1,2}:\d{2}\s*(am|pm)", line, flags=re.I):
                scheduled = line.lower().replace(" ", "")
            if not math.isnan(distance) and scheduled:
                break
        rows.append(
            {
                "race_date": target_date,
                "venue": venue,
                "race_no": race_no,
                "current_distance": distance,
                "scheduled_local_time_text": scheduled,
                "scheduled_start_time_utc": scheduled_utc(target_date, scheduled),
            }
        )
    return pd.DataFrame(rows)


def load_lab245b_candidates(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=["race_date", "race_no", "horse_name", "canonical_horse_id"])
    d = clean_columns(pd.read_csv(path, dtype="string"))
    keep = [c for c in ["race_date", "race_no", "horse_name", "canonical_horse_id", "feature_status"] if c in d.columns]
    return d[keep].drop_duplicates(keep).copy()


def personnel_prior(form: pd.DataFrame, code: object, code_col: str, target_date: str) -> tuple[float, float, float]:
    if pd.isna(code):
        return math.nan, math.nan, math.nan
    text = str(code).strip()
    if not text or text.lower() in {"nan", "<na>", "none"}:
        return math.nan, math.nan, math.nan
    target = pd.Timestamp(target_date)
    g = form[(form[code_col].astype("string").str.strip().eq(text)) & (form["race_date_dt"].lt(target))].copy()
    g = g[g["finish_num"].notna()]
    starts = int(len(g))
    if starts == 0:
        return math.nan, math.nan, math.nan
    wins = int((g["finish_num"] == 1).sum())
    top3 = int((g["finish_num"] <= 3).sum())
    return float(starts), float((wins + 1) / (starts + 10)), float((top3 + 3) / (starts + 10))


def build_runner_features(row: pd.Series, form: pd.DataFrame, active_field_sizes: dict, target_date: str) -> dict:
    horse_code = str(row["horse_code"])
    hist = form[form["horse_code"].astype("string").eq(horse_code)].copy()
    hist = hist.sort_values(["race_date_dt", "race_code_sort"], kind="stable")
    margins = pd.to_numeric(hist["margin_len"], errors="coerce").to_numpy(float)
    finishes = pd.to_numeric(hist["finish_num"], errors="coerce").to_numpy(float)
    distances = pd.to_numeric(hist["distance_m"], errors="coerce").to_numpy(float)
    field_sizes = pd.to_numeric(hist["field_size_num"], errors="coerce").to_numpy(float)
    race_dates = pd.to_datetime(hist["race_date_dt"], errors="coerce")

    rec = {feature: math.nan for feature in FEATURES}
    race_id = str(row["race_id"])
    current_distance = float(row.get("current_distance")) if pd.notna(row.get("current_distance")) else math.nan
    active_field_size = active_field_sizes.get(race_id, math.nan)
    barrier = float(row["barrier_num"]) if pd.notna(row["barrier_num"]) else math.nan

    rec["current_distance"] = current_distance
    rec["hist_runs"] = float(len(hist))
    rec["represented_field_size"] = float(active_field_size) if pd.notna(active_field_size) else math.nan
    if pd.notna(barrier) and pd.notna(active_field_size) and active_field_size > 1:
        rec["barrier_position_pct"] = float((barrier - 1.0) / (active_field_size - 1.0))

    finite_margins = [float(x) for x in margins if np.isfinite(x)]
    finite_finishes = [float(x) for x in finishes if np.isfinite(x)]
    if finite_margins:
        m5 = np.asarray(finite_margins[-5:], dtype=float)
        rec["margin_mean5"] = float(np.mean(m5))
        rec["margin_std5"] = float(np.std(m5))
        rec["margin_worst5"] = float(np.max(m5))
        rec["margin_last1"] = float(finite_margins[-1])
        if len(finite_margins) >= 2:
            rec["margin_last2"] = float(finite_margins[-2])
            rec["margin_change_l1_l2"] = float(finite_margins[-1] - finite_margins[-2])

    if len(hist):
        rec["last_distance"] = float(distances[-1]) if np.isfinite(distances[-1]) else math.nan
        valid_dates = race_dates.dropna()
        if len(valid_dates):
            rec["days_since_last"] = float((pd.Timestamp(target_date) - valid_dates.max()).days)
    if finite_finishes:
        f5 = np.asarray(finite_finishes[-5:], dtype=float)
        rec["clean_finish_mean5"] = float(np.mean(f5))
        rec["clean_last_finish"] = float(finite_finishes[-1])
        rec["clean_last_won"] = float(finite_finishes[-1] == 1)
        rec["clean_last_top3"] = float(finite_finishes[-1] <= 3)
        rec["clean_finish_hist_n"] = float(len(f5))

    if len(hist) >= 1 and np.isfinite(margins[-1]) and np.isfinite(field_sizes[-1]):
        rec["margin_per_runner_last1"] = float(margins[-1] / max(field_sizes[-1] - 1.0, 1.0))
    if len(hist) >= 2 and np.isfinite(margins[-2]) and np.isfinite(field_sizes[-2]):
        rec["margin_per_runner_last2"] = float(margins[-2] / max(field_sizes[-2] - 1.0, 1.0))

    if np.isfinite(current_distance):
        near = hist[np.abs(pd.to_numeric(hist["distance_m"], errors="coerce") - current_distance) <= 200]
        rec["dist200_runs"] = float(len(near))

    js = personnel_prior(form, row.get("jockey_code"), "jockey_id", target_date)
    ts = personnel_prior(form, row.get("trainer_code"), "trainer_id", target_date)
    rec["jockey_prior_starts"], rec["jockey_prior_win_rate"], rec["jockey_prior_top3_rate"] = js
    rec["trainer_prior_starts"], rec["trainer_prior_win_rate"], rec["trainer_prior_top3_rate"] = ts
    return rec


def feature_reason(feature: str, value: object, has_form: bool) -> tuple[str, str]:
    if feature in LVS_FEATURES:
        return "MISSING", "NO_CERTIFIED_LIVE_LVS_TIMING_IDENTITY"
    if feature in PERSONNEL_FEATURES:
        if pd.notna(value):
            return "POPULATED_UNCERTIFIED", "RCOM_NATIVE_PARTIAL_PERSONNEL_HISTORY"
        return "MISSING", "NO_CERTIFIED_PERSONNEL_HISTORY"
    if pd.notna(value):
        return "POPULATED_CERTIFIED_RCOM_NATIVE", "RCOM_NATIVE_STRICT_PRIOR_FORM_OR_FIELD"
    if not has_form and feature not in {"current_distance", "represented_field_size", "barrier_position_pct"}:
        return "MISSING", "FIRST_STARTER_OR_NO_RCOM_HISTORY"
    return "MISSING", "SOURCE_FIELD_UNAVAILABLE"


def build_matrix(
    paths: Paths, target_date: str, venue: str, expected_rows: int | None = 104
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    field = load_field(paths.field, target_date, venue)
    if expected_rows is not None and len(field) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} declared runners, found {len(field)}")
    form = load_form(paths.form, target_date)
    metadata = load_race_metadata(paths.public_snapshot, target_date, venue)
    candidates = load_lab245b_candidates(paths.lab245b_candidates)

    field = field.merge(
        metadata[["race_no", "current_distance", "scheduled_local_time_text", "scheduled_start_time_utc"]],
        on="race_no",
        how="left",
    )
    active_field_sizes = field[~field["is_scratched"]].groupby("race_id")["race_entry_id"].nunique().to_dict()
    candidate_keys = {
        (str(r.race_date), str(r.race_no), str(r.horse_name).strip().upper())
        for r in candidates.itertuples(index=False)
        if hasattr(r, "race_date") and hasattr(r, "race_no") and hasattr(r, "horse_name")
    }

    rows = []
    feature_status_rows = []
    for src in field.itertuples(index=False):
        row = pd.Series(src._asdict())
        race_no = str(row["race_no"])
        horse_name = str(row["horse_name"])
        hist = form[form["horse_code"].astype("string").eq(str(row["horse_code"]))]
        features = build_runner_features(row, form, active_field_sizes, target_date)
        candidate_key = (target_date, race_no, horse_name.strip().upper())
        has_candidate = candidate_key in candidate_keys
        has_form = len(hist) > 0
        reason_codes = []
        populated = 0
        certified_populated = 0
        uncertified_populated = 0
        for feature in FEATURES:
            status, reason = feature_reason(feature, features[feature], has_form)
            feature_status_rows.append(
                {
                    "race_id": row["race_id"],
                    "runner_id": row["race_entry_id"],
                    "horse_code": row["horse_code"],
                    "feature": feature,
                    "value_populated": bool(pd.notna(features[feature])),
                    "feature_status": status,
                    "reason_code": reason,
                }
            )
            if pd.notna(features[feature]):
                populated += 1
                if status == "POPULATED_CERTIFIED_RCOM_NATIVE":
                    certified_populated += 1
                elif status == "POPULATED_UNCERTIFIED":
                    uncertified_populated += 1
            if status == "MISSING":
                reason_codes.append(f"{feature}:{reason}")
        if has_candidate:
            history_status = "HISTORICAL_LVS_CANDIDATE_UNCERTIFIED"
        elif has_form:
            history_status = "RACINGCOM_NATIVE_FORM_AVAILABLE"
        else:
            history_status = "FIRST_STARTER_OR_INSUFFICIENT_HISTORY"
        complete_values = populated == len(FEATURES)
        certified_complete = certified_populated == len(FEATURES)
        eligible = bool(complete_values and certified_complete and not row["is_scratched"])
        rows.append(
            {
                "race_date": target_date,
                "venue": venue,
                "race_no": race_no,
                "race_id": row["race_id"],
                "runner_id": row["race_entry_id"],
                "horse_code": row["horse_code"],
                "horse_name": horse_name,
                "barrier": row["barrier"],
                "scratched": bool(row["is_scratched"]),
                "jockey_code": row.get("jockey_code"),
                "trainer_code": row.get("trainer_code"),
                "scheduled_local_time_text": row.get("scheduled_local_time_text"),
                "scheduled_start_time_utc": row.get("scheduled_start_time_utc"),
                "rcom_form_runs": int(len(hist)),
                "historical_identity_status": history_status,
                "feature_status": "ELIGIBLE_FOR_SCORING" if eligible else "INCOMPLETE_OR_UNCERTIFIED_DO_NOT_SCORE",
                "eligible_for_stage011_scoring": eligible,
                "populated_feature_count": populated,
                "certified_populated_feature_count": certified_populated,
                "uncertified_populated_feature_count": uncertified_populated,
                "missing_feature_count": len(FEATURES) - populated,
                "missing_reason_codes": "|".join(reason_codes[:80]),
                **features,
            }
        )

    matrix = pd.DataFrame(rows)
    feature_status = pd.DataFrame(feature_status_rows)
    family_rows = []
    family_map = {
        "CURRENT_CONTEXT": ["current_distance", "represented_field_size", "barrier_position_pct"],
        "RCOM_NATIVE_HISTORY": [
            "hist_runs",
            "margin_mean5",
            "margin_std5",
            "margin_worst5",
            "margin_last1",
            "margin_last2",
            "last_distance",
            "margin_change_l1_l2",
            "margin_per_runner_last1",
            "margin_per_runner_last2",
            "days_since_last",
            "dist200_runs",
            "clean_finish_mean5",
            "clean_last_finish",
            "clean_last_won",
            "clean_last_top3",
            "clean_finish_hist_n",
        ],
        "LVS_TIMING": sorted(LVS_FEATURES),
        "PERSONNEL_PARTIAL": sorted(PERSONNEL_FEATURES),
    }
    for family, cols in family_map.items():
        vals = matrix[cols].notna()
        family_rows.append(
            {
                "family": family,
                "features": len(cols),
                "populated_cells": int(vals.sum().sum()),
                "total_cells": int(vals.size),
                "rows_all_features_populated": int(vals.all(axis=1).sum()),
                "coverage_pct": round(float(vals.sum().sum() / vals.size * 100), 2) if vals.size else 0.0,
            }
        )
    coverage = pd.DataFrame(family_rows)
    audit = {
        "status": "PASS" if len(matrix) == expected_rows else "FAIL",
        "target_date": target_date,
        "venue": venue,
        "declared_runners": int(len(matrix)),
        "races": int(matrix["race_id"].nunique()),
        "eligible_for_stage011_scoring": int(matrix["eligible_for_stage011_scoring"].sum()),
        "rcom_native_form_available": int(matrix["rcom_form_runs"].gt(0).sum()),
        "historical_identity_status_counts": matrix["historical_identity_status"].value_counts().to_dict(),
        "feature_status_counts": matrix["feature_status"].value_counts().to_dict(),
        "feature_manifest": FEATURES,
        "feature_manifest_sha256": hashlib.sha256(json.dumps(FEATURES, separators=(",", ":")).encode()).hexdigest(),
        "sources": {
            "field": str(paths.field),
            "field_sha256": file_sha256(paths.field),
            "form": str(paths.form),
            "form_sha256": file_sha256(paths.form),
            "public_snapshot": str(paths.public_snapshot),
            "public_snapshot_sha256": file_sha256(paths.public_snapshot) if paths.public_snapshot.is_file() else None,
            "lab245b_candidates": str(paths.lab245b_candidates),
            "lab245b_candidates_sha256": file_sha256(paths.lab245b_candidates) if paths.lab245b_candidates.is_file() else None,
        },
        "no_market_features": True,
        "no_current_race_outcomes": True,
        "no_stage011_retraining": True,
        "model_ready_for_prospective_scoring": bool(matrix["eligible_for_stage011_scoring"].sum() > 0),
        "primary_blockers": [
            "No certified live LVS timing identity for Racing.com numeric horses to LAB245B timing namespace.",
            "Personnel prior statistics from Caulfield browser form are partial to the 98 captured horses, not the full historical jockey/trainer universe.",
            "Historical LAB245B candidate links are preserved as candidate evidence only and are not promoted to certified identity.",
        ],
    }
    return matrix, coverage, feature_status, audit


def write_outputs(
    matrix: pd.DataFrame, coverage: pd.DataFrame, feature_status: pd.DataFrame, audit: dict, output_dir: Path
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "matrix": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_MATRIX.csv",
        "coverage": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_COVERAGE_BY_FAMILY.csv",
        "feature_status": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_STATUS_LONG.csv",
        "audit": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_AUDIT.json",
        "score_input": output_dir / "EDGEIQ_STAGE011_LIVE_SCORE_ELIGIBLE_INPUT.csv",
    }
    matrix.to_csv(paths["matrix"], index=False)
    coverage.to_csv(paths["coverage"], index=False)
    feature_status.to_csv(paths["feature_status"], index=False)
    paths["audit"].write_text(json.dumps(audit, indent=2), encoding="utf-8")
    eligible_cols = ["race_id", "runner_id", "scratch_status", "scoring_timestamp", "scheduled_start_time"] + FEATURES
    eligible = matrix[matrix["eligible_for_stage011_scoring"]].copy()
    score = pd.DataFrame(columns=eligible_cols)
    if not eligible.empty:
        score = eligible.rename(columns={"scratched": "scratch_status"})[["race_id", "runner_id"] + FEATURES].copy()
        score["scratch_status"] = "ACTIVE"
        score["scoring_timestamp"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        score["scheduled_start_time"] = eligible["scheduled_start_time_utc"].fillna("")
        score = score[eligible_cols]
    score.to_csv(paths["score_input"], index=False)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", default="2026-10-14")
    parser.add_argument("--venue", default="Caulfield")
    parser.add_argument("--expected-runners", type=int, default=104)
    parser.add_argument(
        "--field",
        type=Path,
        default=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv"),
    )
    parser.add_argument(
        "--form",
        type=Path,
        default=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv"),
    )
    parser.add_argument(
        "--public-snapshot",
        type=Path,
        default=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\public_race_snapshot_20261012T051330Z.json"),
    )
    parser.add_argument(
        "--lab245b-candidates",
        type=Path,
        default=Path(r"C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V3.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/research/stage011_live_completion"),
    )
    args = parser.parse_args()
    paths = Paths(args.field, args.form, args.public_snapshot, args.lab245b_candidates, args.output_dir)
    matrix, coverage, feature_status, audit = build_matrix(paths, args.target_date, args.venue, args.expected_runners)
    outputs = write_outputs(matrix, coverage, feature_status, audit, args.output_dir)
    print("EDGEIQ_STAGE011_LIVE_FEATURE_PIPELINE")
    print("RUNNERS", len(matrix), "RACES", matrix["race_id"].nunique())
    print("ELIGIBLE_FOR_STAGE011_SCORING", int(matrix["eligible_for_stage011_scoring"].sum()))
    print("IDENTITY_STATUS", matrix["historical_identity_status"].value_counts().to_dict())
    print("COVERAGE_BY_FAMILY", coverage.to_dict("records"))
    for key, value in outputs.items():
        print(key.upper(), value)
    print("NO_MARKET; NO_TARGET_OUTCOMES; NO_STAGE011_RETRAINING; FAIL_CLOSED_SCORING")


if __name__ == "__main__":
    main()
