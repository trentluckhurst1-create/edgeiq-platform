from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from edgeiq_stage011_live_scorer import FEATURES, FEATURE_SHA256, score_stage011
except ModuleNotFoundError:  # pragma: no cover - direct test import fallback
    from scripts.research.edgeiq_stage011_live_scorer import (  # type: ignore
        FEATURES,
        FEATURE_SHA256,
        score_stage011,
    )


RESEARCH_ROOT = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
PLATFORM_ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
LIVE_DIR = PLATFORM_ROOT / "outputs/research/live_acquisition_v1"
LAB245B_DIR = RESEARCH_ROOT / "outputs/research/profitability_program/lab245b"
MODEL_DIR = RESEARCH_ROOT / "outputs/research/model_v2/stage011_research_2024_fit"
DEFAULT_OUT = Path("outputs/research/issue21_caulfield_stage011_pipeline")

EXPECTED_MODEL_SHA256 = (
    "f06c050e9febcd5b2588d29f90065b0a482872ab4be8c2cdb87ac22803ab9b91"
)
EXPECTED_FEATURE_SHA256 = (
    "f35dd342d570b35831043c75cf756f7cac4e28ebdd564988393db3383c82454f"
)
TARGET_DATE = pd.Timestamp("2026-10-14")
TARGET_VENUE = "CAULFIELD"
WAREHOUSE_CUTOFF = pd.Timestamp("2026-06-21")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_distance(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return np.nan
    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else np.nan


def parse_margin(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return np.nan
    text = str(value).strip()
    if not text or text in {"-", "–"}:
        return np.nan
    if re.fullmatch(r"\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)?", text):
        return 0.0
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else np.nan


def parse_elapsed_seconds(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return np.nan
    text = str(value).strip()
    if not text or text in {"-", "–"}:
        return np.nan
    if ":" in text:
        parts = text.split(":")
        if len(parts) != 2:
            return np.nan
        return float(parts[0]) * 60.0 + float(parts[1])
    return float(text)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def condition_group(value: Any) -> str:
    text = str(value or "").upper().strip()
    if "FIRM" in text or text == "FAST":
        return "FIRM"
    if "GOOD" in text:
        return "GOOD"
    if any(token in text for token in ["SOFT", "DEAD", "SLOW"]):
        return "SOFT"
    if "HEAVY" in text or "HVY" in text:
        return "HEAVY"
    if any(token in text for token in ["SYNTH", "POLY", "TAPETA"]):
        return "STANDARD_SYNTHETIC"
    return text


def race_id(value: Any) -> str:
    return f"RCOM_RACE_{str(value).strip()}"


def load_json_payloads(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, list) else [obj]


def extract_race_records(payloads: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for payload in payloads:
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            continue
        for key in ("getNoCacheRacesForMeet", "getRacesForMeet"):
            races = data.get(key)
            if not isinstance(races, list):
                continue
            for r in races:
                if not isinstance(r, dict):
                    continue
                if parse_bool(r.get("isTrial")) or parse_bool(r.get("isJumpOut")):
                    continue
                rid = str(r.get("id") or "").strip()
                if not rid:
                    continue
                rows.append(
                    {
                        "source_operation": key,
                        "source_request_url": payload.get("request_url"),
                        "race_code": rid,
                        "race_id": race_id(rid),
                        "race_number": pd.to_numeric(r.get("raceNumber"), errors="coerce"),
                        "distance_metres": parse_distance(r.get("distance")),
                        "scheduled_time_utc": r.get("time"),
                        "race_time_seconds": parse_elapsed_seconds(r.get("raceTime")),
                        "track_condition": r.get("trackCondition") or (r.get("meet") or {}).get("trackCondition"),
                        "track_code": r.get("trackCode"),
                        "status": r.get("raceStatus"),
                        "venue": (r.get("meet") or {}).get("venue"),
                    }
                )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    valid_elapsed = frame["race_time_seconds"].notna() & frame["race_time_seconds"].gt(0)
    frame = frame[valid_elapsed | frame["distance_metres"].notna()].copy()
    return frame.drop_duplicates(["race_code", "source_operation"], keep="first")


def parse_snapshot_target_metadata(snapshot_path: Path) -> pd.DataFrame:
    if not snapshot_path.exists():
        return pd.DataFrame()
    obj = json.loads(snapshot_path.read_text(encoding="utf-8"))
    rows = []
    for r in obj.get("races", []):
        if str(r.get("venue", "")).upper() != TARGET_VENUE:
            continue
        text = str(r.get("raw_text") or "")
        distance = np.nan
        for match in re.finditer(r"(?m)^(\d{3,4})m$", text):
            distance = float(match.group(1))
            break
        rows.append(
            {
                "race_date": r.get("race_date"),
                "venue": r.get("venue"),
                "meet_code": r.get("meet_code"),
                "race_no": pd.to_numeric(r.get("race_no"), errors="coerce"),
                "distance_metres": distance,
                "snapshot_url": r.get("url"),
                "snapshot_http_status": r.get("http_status"),
                "snapshot_captured_at_utc": r.get("captured_at_utc"),
                "target_metadata_source": "public_race_snapshot_raw_text",
            }
        )
    return pd.DataFrame(rows)


def read_current_field(path: Path) -> pd.DataFrame:
    field = pd.read_csv(path)
    field = field[
        field["race_date"].astype(str).eq(str(TARGET_DATE.date()))
        & field["venue"].astype(str).str.upper().eq(TARGET_VENUE)
    ].copy()
    if field.empty:
        raise RuntimeError("No target Caulfield field rows found")
    field["scratched_bool"] = field["scratched"].map(parse_bool)
    field["scratch_status"] = np.where(field["scratched_bool"], "SCRATCHED", "ACTIVE")
    field["race_id"] = field["race_id"].map(race_id)
    field["runner_id"] = field["eiq_horse_id"].astype(str)
    field["horse_code"] = field["horse_code"].astype(str)
    field["barrier"] = pd.to_numeric(field["barrier"], errors="coerce")
    field["jockey_code"] = pd.to_numeric(field["jockey_code"], errors="coerce")
    field["trainer_code"] = pd.to_numeric(field["trainer_code"], errors="coerce")
    return field


def load_lvs(path: Path, target_ids: set[str]) -> pd.DataFrame:
    use = [
        "canonical_race_id",
        "canonical_horse_id",
        "race_date",
        "distance_metres",
        "field_size",
        "finish_position",
        "finish_margin",
        "runner_lvs",
        "benchmark_n",
    ]
    parts = []
    for chunk in pd.read_csv(path, usecols=use, chunksize=200_000):
        chunk = chunk[chunk["canonical_horse_id"].astype(str).isin(target_ids)]
        if not chunk.empty:
            parts.append(chunk)
    if not parts:
        return pd.DataFrame(columns=use)
    frame = pd.concat(parts, ignore_index=True)
    frame["race_date"] = pd.to_datetime(frame["race_date"], errors="coerce")
    for col in ["distance_metres", "field_size", "finish_position", "finish_margin", "runner_lvs"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame[frame["race_date"] < TARGET_DATE].copy()
    frame["source_family"] = "LAB245B_STRICT_PIT_LVS"
    return frame


def load_browser_form(path: Path, field: pd.DataFrame) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    form = pd.read_csv(path)
    form["horse_code"] = form["horse_code"].astype(str)
    code_to_id = dict(zip(field["horse_code"], field["runner_id"]))
    form = form[form["horse_code"].isin(code_to_id)].copy()
    form["canonical_horse_id"] = form["horse_code"].map(code_to_id)
    form["race_date"] = pd.to_datetime(form["race_date"], errors="coerce")
    form = form[form["race_date"] < TARGET_DATE].copy()
    form["distance_metres"] = form["distance"].map(parse_distance)
    form["field_size"] = pd.to_numeric(form["field_size"], errors="coerce")
    form["finish_position"] = pd.to_numeric(form["finish"], errors="coerce")
    form["finish_margin"] = form["margin"].map(parse_margin)
    form["barrier"] = pd.to_numeric(form["barrier"], errors="coerce")
    form["jockey_id"] = pd.to_numeric(form["jockey_id"], errors="coerce")
    form["trainer_id"] = pd.to_numeric(form["trainer_id"], errors="coerce")
    form["source_family"] = "RACING_COM_BROWSER_FORM_PARTIAL"
    return form


def make_recent_lvs(form: pd.DataFrame, race_records: pd.DataFrame, checkpoint: pd.DataFrame) -> pd.DataFrame:
    if form.empty or race_records.empty or checkpoint.empty:
        return pd.DataFrame()
    recent = form[form["race_date"] > WAREHOUSE_CUTOFF].copy()
    if recent.empty:
        return pd.DataFrame()
    timing = race_records[race_records["race_time_seconds"].notna()].copy()
    if timing.empty:
        return pd.DataFrame()
    timing["race_code"] = timing["race_code"].astype(str)
    recent["race_code"] = recent["race_code"].astype(str)
    recent = recent.merge(
        timing[["race_code", "race_time_seconds", "distance_metres", "track_condition"]],
        on="race_code",
        how="inner",
        suffixes=("", "_timing"),
    )
    if recent.empty:
        return pd.DataFrame()
    checkpoint = checkpoint.copy()
    checkpoint["race_date"] = pd.to_datetime(checkpoint["race_date"], errors="coerce")
    checkpoint["distance_metres"] = pd.to_numeric(checkpoint["distance_metres"], errors="coerce")
    # The checkpoint has no public track-code crosswalk for current Racing.com trackCode.
    # Use date-prior all-track exact-distance median only as a guarded fallback audit input,
    # and mark it provisional so it cannot be confused with certified LAB245B.
    std_rows = []
    for race_code, group in recent.groupby("race_code"):
        rd = group["race_date"].iloc[0]
        dist = group["distance_metres_timing"].iloc[0]
        prior = checkpoint[(checkpoint["race_date"] < rd) & (checkpoint["distance_metres"].eq(dist))]
        if len(prior) < 20:
            continue
        std = float(prior["standard_time_seconds"].median())
        n = int(len(prior))
        for _, row in group.iterrows():
            race_lvs = -((float(row["race_time_seconds"]) - std) / 0.17)
            std_rows.append(
                {
                    "canonical_race_id": race_id(row["race_code"]),
                    "canonical_horse_id": row["canonical_horse_id"],
                    "race_date": row["race_date"],
                    "distance_metres": row["distance_metres_timing"],
                    "field_size": row["field_size"],
                    "finish_position": row["finish_position"],
                    "finish_margin": row["finish_margin"],
                    "runner_lvs": race_lvs - row["finish_margin"]
                    if pd.notna(row["finish_margin"])
                    else np.nan,
                    "benchmark_n": n,
                    "source_family": "PROVISIONAL_RECENT_LVS_DISTANCE_ONLY_NOT_CERTIFIED",
                }
            )
    return pd.DataFrame(std_rows)


def build_features(
    field: pd.DataFrame,
    lvs: pd.DataFrame,
    browser_form: pd.DataFrame,
    target_meta: pd.DataFrame,
    scoring_timestamp: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    target = field[field["scratch_status"].eq("ACTIVE")].copy()
    target = target.merge(
        target_meta[["race_no", "distance_metres", "target_metadata_source"]].drop_duplicates("race_no"),
        on="race_no",
        how="left",
    )
    race_field_size = target.groupby("race_id")["runner_id"].transform("count")
    target["represented_field_size"] = race_field_size
    target["barrier_position_pct"] = (target["barrier"] - 1) / (race_field_size - 1)

    history = lvs.copy()
    if not history.empty:
        history = history.sort_values(["canonical_horse_id", "race_date", "canonical_race_id"])

    clean = browser_form.sort_values(["canonical_horse_id", "race_date", "race_code"]).copy()
    features = []
    coverage = []
    for _, runner in target.iterrows():
        hid = runner["runner_id"]
        hist = history[history["canonical_horse_id"].eq(hid)].copy()
        hist = hist[hist["race_date"] < TARGET_DATE].sort_values("race_date")
        form_hist = clean[clean["canonical_horse_id"].eq(hid)].copy()
        form_hist = form_hist[form_hist["race_date"] < TARGET_DATE].sort_values("race_date")

        margin_hist = form_hist if not form_hist.empty else hist
        last5 = hist.tail(5)
        margin_last5 = margin_hist.tail(5)
        lvs_values = last5["runner_lvs"].dropna().to_numpy(float)
        margin_values = margin_last5["finish_margin"].dropna().to_numpy(float)
        all_lvs = hist["runner_lvs"].dropna().to_numpy(float)
        current_distance = runner["distance_metres"]
        dist_hist = hist[
            hist["distance_metres"].between(current_distance - 200, current_distance + 200, inclusive="both")
        ] if pd.notna(current_distance) else hist.iloc[0:0]

        if len(margin_hist):
            last_margin = margin_hist.iloc[-1]
            days_since_last = (TARGET_DATE - last_margin["race_date"]).days
            last_distance = last_margin["distance_metres"]
            margin_last1 = last_margin["finish_margin"]
            margin_last2 = margin_hist.iloc[-2]["finish_margin"] if len(margin_hist) >= 2 else np.nan
            last_field_size = last_margin["field_size"]
            last2_field_size = margin_hist.iloc[-2]["field_size"] if len(margin_hist) >= 2 else np.nan
        elif len(hist):
            last = hist.iloc[-1]
            days_since_last = (TARGET_DATE - last["race_date"]).days
            last_distance = last["distance_metres"]
            margin_last1 = last["finish_margin"]
            margin_last2 = hist.iloc[-2]["finish_margin"] if len(hist) >= 2 else np.nan
            last_field_size = last["field_size"]
            last2_field_size = hist.iloc[-2]["field_size"] if len(hist) >= 2 else np.nan
        else:
            days_since_last = np.nan
            last_distance = np.nan
            margin_last1 = np.nan
            margin_last2 = np.nan
            last_field_size = np.nan
            last2_field_size = np.nan

        clean_tail = form_hist.tail(5)
        clean_finish = clean_tail["finish_position"].dropna().to_numpy(float)
        trainer_hist = clean[clean["trainer_id"].eq(runner["trainer_code"])]
        jockey_hist = clean[clean["jockey_id"].eq(runner["jockey_code"])]

        row = {
            "race_id": runner["race_id"],
            "runner_id": hid,
            "scoring_timestamp": scoring_timestamp,
            "scratch_status": "ACTIVE",
            "current_distance": current_distance,
            "hist_runs": float(len(hist)),
            "lvs_last1": all_lvs[-1] if len(all_lvs) else np.nan,
            "lvs_mean3": float(np.mean(all_lvs[-3:])) if len(all_lvs) else np.nan,
            "lvs_mean5": float(np.mean(all_lvs[-5:])) if len(all_lvs) else np.nan,
            "lvs_median5": float(np.median(all_lvs[-5:])) if len(all_lvs) else np.nan,
            "lvs_std5": float(np.std(all_lvs[-5:], ddof=1)) if len(all_lvs[-5:]) >= 2 else np.nan,
            "lvs_peak": float(np.max(all_lvs)) if len(all_lvs) else np.nan,
            "lvs_worst5": float(np.min(all_lvs[-5:])) if len(all_lvs) else np.nan,
            "margin_mean5": float(np.mean(margin_values)) if len(margin_values) else np.nan,
            "margin_std5": float(np.std(margin_values, ddof=1)) if len(margin_values) >= 2 else np.nan,
            "margin_worst5": float(np.max(margin_values)) if len(margin_values) else np.nan,
            "margin_last1": margin_last1,
            "margin_last2": margin_last2,
            "last_distance": last_distance,
            "margin_change_l1_l2": margin_last1 - margin_last2
            if pd.notna(margin_last1) and pd.notna(margin_last2)
            else np.nan,
            "margin_per_runner_last1": margin_last1 / last_field_size
            if pd.notna(margin_last1) and pd.notna(last_field_size) and last_field_size
            else np.nan,
            "margin_per_runner_last2": margin_last2 / last2_field_size
            if pd.notna(margin_last2) and pd.notna(last2_field_size) and last2_field_size
            else np.nan,
            "days_since_last": days_since_last,
            "dist200_runs": float(len(dist_hist)),
            "dist200_lvs_mean": float(dist_hist["runner_lvs"].mean()) if len(dist_hist) else np.nan,
            "dist200_lvs_best": float(dist_hist["runner_lvs"].max()) if len(dist_hist) else np.nan,
            "represented_field_size": runner["represented_field_size"],
            "barrier_position_pct": runner["barrier_position_pct"],
            "jockey_prior_starts": float(len(jockey_hist)),
            "jockey_prior_win_rate": float((jockey_hist["finish_position"].eq(1)).mean()) if len(jockey_hist) else np.nan,
            "jockey_prior_top3_rate": float((jockey_hist["finish_position"].le(3)).mean()) if len(jockey_hist) else np.nan,
            "trainer_prior_starts": float(len(trainer_hist)),
            "trainer_prior_win_rate": float((trainer_hist["finish_position"].eq(1)).mean()) if len(trainer_hist) else np.nan,
            "trainer_prior_top3_rate": float((trainer_hist["finish_position"].le(3)).mean()) if len(trainer_hist) else np.nan,
            "clean_finish_mean5": float(np.mean(clean_finish)) if len(clean_finish) else np.nan,
            "clean_last_finish": clean_finish[-1] if len(clean_finish) else np.nan,
            "clean_last_won": float(clean_finish[-1] == 1) if len(clean_finish) else np.nan,
            "clean_last_top3": float(clean_finish[-1] <= 3) if len(clean_finish) else np.nan,
            "clean_finish_hist_n": float(len(clean_finish)),
        }
        features.append(row)
        coverage.append(
            {
                "race_id": runner["race_id"],
                "runner_id": hid,
                "horse_name": runner["horse_name"],
                "hist_lvs_runs": int(len(hist)),
                "browser_form_runs": int(len(form_hist)),
                "target_distance_available": bool(pd.notna(current_distance)),
                "margin_source_family": "RACING_COM_BROWSER_FORM_PARTIAL"
                if not form_hist.empty
                else ("LAB245B_STRICT_PIT_LVS" if not hist.empty else ""),
                "lvs_source_families": "|".join(sorted(hist["source_family"].dropna().unique()))
                if "source_family" in hist
                else "",
            }
        )
    feature_frame = pd.DataFrame(features)
    return feature_frame[["race_id", "runner_id", "scoring_timestamp", "scratch_status"] + FEATURES], pd.DataFrame(coverage)


def validate_feature_matrix(frame: pd.DataFrame) -> dict:
    feature_missing = frame[FEATURES].isna().sum().sort_values(ascending=False)
    mass_input = frame.groupby("race_id")["runner_id"].count()
    return {
        "rows": int(len(frame)),
        "races": int(frame["race_id"].nunique()),
        "feature_count": len(FEATURES),
        "feature_manifest_sha256": FEATURE_SHA256,
        "features_with_any_missing": int((feature_missing > 0).sum()),
        "features_all_missing": feature_missing[feature_missing.eq(len(frame))].index.tolist(),
        "min_active_runners_per_race": int(mass_input.min()),
        "max_active_runners_per_race": int(mass_input.max()),
    }


def maybe_capture_with_playwright(urls: list[str], output: Path) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"status": "SKIPPED", "reason": f"playwright unavailable: {exc}"}

    captures: list[dict[str, Any]] = []
    with sync_playwright() as p:  # pragma: no cover - integration path
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response: Any) -> None:
            url = response.url
            if "graphql" not in url.lower():
                return
            try:
                payload = response.json()
            except Exception:
                return
            captures.append(
                {
                    "url": url,
                    "status": response.status,
                    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                    "data": payload.get("data") if isinstance(payload, dict) else None,
                    "errors": payload.get("errors") if isinstance(payload, dict) else None,
                }
            )

        page.on("response", handle_response)
        for url in urls:
            page.goto(url, wait_until="networkidle", timeout=45_000)
        browser.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(captures, indent=2), encoding="utf-8")
    return {"status": "PASS", "captured_payloads": len(captures), "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-dir", type=Path, default=LIVE_DIR)
    parser.add_argument("--lab245b-dir", type=Path, default=LAB245B_DIR)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--capture-browser", action="store_true")
    parser.add_argument("--skip-scoring", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scoring_timestamp = datetime.now(timezone.utc).isoformat()

    field_path = args.live_dir / "october_graphql_field_identities.csv"
    form_path = args.live_dir / "caulfield_browser_form.csv"
    payload_path = args.live_dir / "race_timing_payload_discovery.json"
    snapshot_path = args.live_dir / "public_race_snapshot_20261012T051330Z.json"
    timing_manifest_path = args.live_dir / "caulfield_recent_timing_manifest.csv"
    lvs_path = args.lab245b_dir / "LAB245B_WAREHOUSE_RUNNER_LVS.csv"
    checkpoint_path = args.lab245b_dir / "LAB245B_STRICT_PIT_RACE_BENCHMARK_CHECKPOINT.csv"
    checkpoint_meta_path = args.lab245b_dir / "LAB245B_STRICT_PIT_RACE_BENCHMARK_CHECKPOINT.json"
    model_path = args.model_dir / "STAGE011_RESEARCH_FIT_2024.joblib"
    manifest_path = args.model_dir / "STAGE011_RESEARCH_FIT_2024_MANIFEST.json"

    required = [field_path, form_path, lvs_path, checkpoint_path, checkpoint_meta_path, model_path, manifest_path]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Required local artifacts missing: {missing}")

    browser_capture = {"status": "NOT_REQUESTED"}
    if args.capture_browser:
        field_for_urls = pd.read_csv(field_path)
        urls = sorted(
            set(
                field_for_urls[
                    field_for_urls["venue"].astype(str).str.upper().eq(TARGET_VENUE)
                ]["source_url"].dropna().astype(str)
            )
        )
        if timing_manifest_path.exists():
            tm = pd.read_csv(timing_manifest_path)
            urls.extend(sorted(set(tm["meet_url"].dropna().astype(str))))
        browser_capture = maybe_capture_with_playwright(
            sorted(set(urls)),
            args.output_dir / "LAB21_BROWSER_GRAPHQL_CAPTURE.json",
        )

    field = read_current_field(field_path)
    target_meta = parse_snapshot_target_metadata(snapshot_path)
    if target_meta.empty:
        raise RuntimeError("Target race metadata unavailable")

    payloads = load_json_payloads(payload_path)
    if (args.output_dir / "LAB21_BROWSER_GRAPHQL_CAPTURE.json").exists():
        payloads.extend(load_json_payloads(args.output_dir / "LAB21_BROWSER_GRAPHQL_CAPTURE.json"))
    race_records = extract_race_records(payloads)
    race_records.to_csv(args.output_dir / "LAB21_TIMING_RACE_RECORDS.csv", index=False)

    checkpoint_meta = json.loads(checkpoint_meta_path.read_text(encoding="utf-8"))
    if checkpoint_meta.get("pit_policy") != "STRICT_DATE_LT_TARGET_DATE":
        raise RuntimeError("LAB245B checkpoint does not certify STRICT_DATE_LT_TARGET_DATE")
    checkpoint = pd.read_csv(
        checkpoint_path,
        usecols=["canonical_race_id", "race_date", "official_race_time_seconds", "standard_time_seconds", "benchmark_n"],
    )
    checkpoint["race_date"] = pd.to_datetime(checkpoint["race_date"], errors="coerce")
    # Older checkpoint files may omit distance; recover it from the certified LVS rows by race.
    lvs_distance = pd.read_csv(lvs_path, usecols=["canonical_race_id", "distance_metres"]).drop_duplicates("canonical_race_id")
    checkpoint = checkpoint.merge(lvs_distance, on="canonical_race_id", how="left")

    lvs = load_lvs(lvs_path, set(field["runner_id"]))
    browser_form = load_browser_form(form_path, field)
    recent_lvs = make_recent_lvs(browser_form, race_records, checkpoint)
    if not recent_lvs.empty:
        lvs = pd.concat([lvs, recent_lvs], ignore_index=True)
        lvs = lvs.sort_values(["canonical_horse_id", "race_date", "canonical_race_id"]).drop_duplicates(
            ["canonical_horse_id", "canonical_race_id"], keep="last"
        )

    features, row_coverage = build_features(field, lvs, browser_form, target_meta, scoring_timestamp)
    feature_path = args.output_dir / "LAB21_CAULFIELD_STAGE011_FEATURE_MATRIX.csv"
    features.to_csv(feature_path, index=False)
    row_coverage.to_csv(args.output_dir / "LAB21_CAULFIELD_FEATURE_COVERAGE_BY_RUNNER.csv", index=False)

    audit = {
        "status": "FEATURE_MATRIX_BUILT",
        "target": {"date": str(TARGET_DATE.date()), "venue": TARGET_VENUE},
        "scoring_timestamp": scoring_timestamp,
        "current_field": {
            "declared_rows": int(len(field)),
            "active_rows": int(field["scratch_status"].eq("ACTIVE").sum()),
            "scratched_rows": int(field["scratch_status"].eq("SCRATCHED").sum()),
            "races": int(field["race_id"].nunique()),
        },
        "source_artifacts": {
            "field_identities": str(field_path),
            "browser_form": str(form_path),
            "lvs_warehouse": str(lvs_path),
            "lvs_warehouse_sha256": sha256_file(lvs_path),
            "benchmark_checkpoint": str(checkpoint_path),
            "benchmark_checkpoint_sha256": sha256_file(checkpoint_path),
            "model": str(model_path),
            "model_sha256": sha256_file(model_path),
            "manifest": str(manifest_path),
        },
        "browser_capture": browser_capture,
        "target_metadata_rows": int(len(target_meta)),
        "timing_payload_races": int(len(race_records)),
        "certified_lvs_history_rows_for_target_horses": int((lvs["source_family"].eq("LAB245B_STRICT_PIT_LVS")).sum()) if not lvs.empty else 0,
        "provisional_recent_lvs_rows": int((lvs["source_family"].eq("PROVISIONAL_RECENT_LVS_DISTANCE_ONLY_NOT_CERTIFIED")).sum()) if not lvs.empty else 0,
        "browser_form_rows": int(len(browser_form)),
        "feature_matrix": validate_feature_matrix(features),
        "market_data_used": False,
        "production_modified": False,
        "frozen_artifacts_modified": False,
        "provisional_notes": [
            "Jockey/trainer priors are reconstructed from the available Caulfield browser-form slice, not a full certified all-runner prior warehouse.",
            "Recent post-2026-06-21 LVS is included only when elapsed raceTime is captured; distance-only benchmark fallback is marked provisional and not certified LAB245B.",
        ],
    }

    if not args.skip_scoring:
        output_path = args.output_dir / "LAB21_CAULFIELD_STAGE011_PROBABILITIES.csv"
        scoring = score_stage011(
            model_path,
            feature_path,
            output_path,
            EXPECTED_MODEL_SHA256,
            EXPECTED_FEATURE_SHA256,
        )
        audit["scoring"] = scoring
        audit["status"] = "SCORED_RESEARCH_ONLY"
    else:
        audit["scoring"] = {"status": "SKIPPED"}

    audit_path = args.output_dir / "LAB21_CAULFIELD_STAGE011_PIPELINE_AUDIT.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    report = args.output_dir / "LAB21_CAULFIELD_STAGE011_PIPELINE_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# Issue 21 Caulfield Stage011 Pipeline",
                "",
                f"Status: `{audit['status']}`",
                f"Active runners: {audit['current_field']['active_rows']}",
                f"Races: {audit['current_field']['races']}",
                f"Features: {audit['feature_matrix']['feature_count']}",
                f"Features with any missing values: {audit['feature_matrix']['features_with_any_missing']}",
                f"All-missing features: {audit['feature_matrix']['features_all_missing']}",
                f"Market data used: {audit['market_data_used']}",
                f"Production modified: {audit['production_modified']}",
                f"Frozen artifacts modified: {audit['frozen_artifacts_modified']}",
                "",
                "Research-only caveat: current jockey/trainer priors and post-cutoff LVS recovery remain provisional unless a full certified current all-runner prior warehouse is supplied.",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps({"status": audit["status"], "audit": str(audit_path), "features": str(feature_path)}, indent=2))


if __name__ == "__main__":
    main()
