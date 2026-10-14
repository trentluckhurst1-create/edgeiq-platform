"""Build certified research-only V2 selection-gate inputs from real snapshots.

This is an adapter and readiness checker, not a betting engine. It joins a
frozen Stage011-style scorer output to timestamped market quote observations,
then writes V2 contract rows only when source fields can be certified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from run_edgeiq_selection_gate_v2 import CONTRACT_VERSION


MODEL_ID = "STAGE011"
FORBIDDEN_LOWER = {
    "outcome",
    "won",
    "winner",
    "sp",
    "bsp",
    "result",
    "finish_position",
    "starting_price",
    "closing_price",
    "profit",
    "return",
}
MODEL_REQUIRED = {
    "race_id",
    "runner_id",
    "scoring_timestamp",
    "scheduled_start_time",
    "stage011_probability",
    "champion_model_sha256",
}
QUOTE_REQUIRED = {
    "race_id",
    "runner_id",
    "quote_snapshot_id",
    "quote_timestamp",
    "scheduled_start_time",
    "market_source",
    "provider",
    "quote_side",
    "quote_type",
    "odds",
    "available_amount",
    "commission_rate",
    "market_status",
    "in_play",
    "suspended",
}
SUPPORTED_BACK_TYPES = {"BETFAIR_BACK", "BOOKMAKER_FIXED_WIN"}
SUPPORTED_LAY_TYPES = {"BETFAIR_LAY"}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_hash(values: Iterable[object]) -> str:
    payload = json.dumps([str(v) for v in values], separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def read_csv(path: Path, required: set[str], label: str) -> tuple[pd.DataFrame, list[dict], str | None]:
    if not path:
        return pd.DataFrame(), [{"stage": label, "reason": "NO_PATH_SUPPLIED", "detail": ""}], None
    if not path.is_file():
        return pd.DataFrame(), [{"stage": label, "reason": "FILE_MISSING", "detail": str(path)}], None
    header = pd.read_csv(path, nrows=0).columns.tolist()
    forbidden = sorted(c for c in header if c.lower() in FORBIDDEN_LOWER)
    if forbidden:
        return pd.DataFrame(), [{"stage": label, "reason": "FORBIDDEN_OUTCOME_OR_MARKET_FIELD", "detail": "|".join(forbidden)}], file_sha256(path)
    missing = sorted(required - set(header))
    if missing:
        return pd.DataFrame(), [{"stage": label, "reason": "MISSING_REQUIRED_FIELDS", "detail": "|".join(missing)}], file_sha256(path)
    frame = pd.read_csv(path, dtype="string")
    if frame.empty:
        return pd.DataFrame(), [{"stage": label, "reason": "NO_ROWS", "detail": str(path)}], file_sha256(path)
    return frame, [], file_sha256(path)


def load_manifest(path: Path) -> tuple[dict | None, list[dict], str | None]:
    if not path.is_file():
        return None, [{"stage": "model_manifest", "reason": "FILE_MISSING", "detail": str(path)}], None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [{"stage": "model_manifest", "reason": "INVALID_JSON", "detail": str(exc)}], file_sha256(path)
    blockers: list[dict] = []
    for key in ["stage011_sha256", "features", "training_year_max", "status", "no_market"]:
        if key not in manifest:
            blockers.append({"stage": "model_manifest", "reason": "MISSING_MANIFEST_FIELD", "detail": key})
    if manifest.get("no_market") is not True:
        blockers.append({"stage": "model_manifest", "reason": "NO_MARKET_FLAG_NOT_TRUE", "detail": ""})
    return manifest, blockers, file_sha256(path)


def adapt_model(model_path: Path, manifest_path: Path) -> tuple[pd.DataFrame, list[dict], dict]:
    manifest, manifest_blockers, manifest_sha = load_manifest(manifest_path)
    model, model_blockers, model_sha = read_csv(model_path, MODEL_REQUIRED, "model_output")
    blockers = manifest_blockers + model_blockers
    evidence = {
        "model_output": str(model_path),
        "model_output_sha256": model_sha,
        "artifact_manifest": str(manifest_path),
        "artifact_manifest_sha256": manifest_sha,
    }
    if manifest is None or manifest_blockers or model_blockers or model.empty:
        return pd.DataFrame(), blockers, evidence

    row_blockers: list[dict] = []
    d = model.copy()
    d["model_probability"] = pd.to_numeric(d["stage011_probability"], errors="coerce")
    score_ts = pd.to_datetime(d["scoring_timestamp"], utc=True, errors="coerce")
    scheduled = pd.to_datetime(d["scheduled_start_time"], utc=True, errors="coerce")
    expected_sha = str(manifest.get("stage011_sha256", ""))
    feature_digest = canonical_json_sha256({"features": manifest.get("features", [])})
    model_snapshot_id = f"{MODEL_ID}_TRAIN_THROUGH_{manifest.get('training_year_max', 'UNKNOWN')}_{expected_sha[:12]}"

    duplicate_keys = d.duplicated(["race_id", "runner_id"])
    for idx in d.index[duplicate_keys]:
        row_blockers.append({"stage": "model_output", "reason": "DUPLICATE_MODEL_RUNNER", "detail": f"{d.at[idx, 'race_id']}|{d.at[idx, 'runner_id']}"})

    probability_sum = d.groupby("race_id")["model_probability"].sum(min_count=1)
    bad_probability_races = set(probability_sum.index[(probability_sum - 1).abs() > 1e-8])

    valid = pd.Series(True, index=d.index)
    checks = {
        "MODEL_IDENTITY_MISSING": d[["race_id", "runner_id"]].isna().any(axis=1),
        "MODEL_PROBABILITY_INVALID": d["model_probability"].isna() | d["model_probability"].le(0) | d["model_probability"].ge(1),
        "MODEL_TIMESTAMP_INVALID": score_ts.isna() | scheduled.isna() | score_ts.ge(scheduled),
        "MODEL_HASH_MISMATCH": d["champion_model_sha256"].fillna("").ne(expected_sha),
        "MODEL_RACE_PROBABILITY_SUM_FAIL": d["race_id"].isin(bad_probability_races),
        "DUPLICATE_MODEL_RUNNER": duplicate_keys,
    }
    for reason, mask in checks.items():
        valid &= ~mask.fillna(True)
        for idx in d.index[mask.fillna(True)]:
            row_blockers.append({"stage": "model_output", "reason": reason, "detail": f"{d.at[idx, 'race_id']}|{d.at[idx, 'runner_id']}"})

    out = pd.DataFrame(
        {
            "race_id": d["race_id"],
            "runner_id": d["runner_id"],
            "model_probability": d["model_probability"],
            "model_snapshot_time": d["scoring_timestamp"],
            "scheduled_start_time": d["scheduled_start_time"],
            "model_id": MODEL_ID,
            "model_version": f"train_through_{manifest.get('training_year_max', 'UNKNOWN')}",
            "model_snapshot_id": model_snapshot_id,
            "model_snapshot_sha256": expected_sha,
            "feature_manifest_sha256": feature_digest,
            "probability_certified": True,
            "data_certified": True,
            "model_source_sha256": model_sha,
            "artifact_manifest_sha256": manifest_sha,
        }
    )
    return out[valid].reset_index(drop=True), blockers + row_blockers, evidence


def adapt_quotes(quote_path: Path) -> tuple[pd.DataFrame, list[dict], dict]:
    quotes, blockers, quote_sha = read_csv(quote_path, QUOTE_REQUIRED, "quote_snapshot")
    evidence = {"quote_snapshot": str(quote_path), "quote_snapshot_sha256": quote_sha}
    if quotes.empty:
        return pd.DataFrame(), blockers, evidence

    d = quotes.copy()
    d["quote_side_norm"] = d["quote_side"].fillna("").str.upper().str.strip()
    d["quote_type_norm"] = d["quote_type"].fillna("").str.upper().str.strip()
    d["market_source_norm"] = d["market_source"].fillna("").str.upper().str.strip()
    d["market_status_norm"] = d["market_status"].fillna("").str.upper().str.strip()
    d["odds_num"] = pd.to_numeric(d["odds"], errors="coerce")
    d["available_num"] = pd.to_numeric(d["available_amount"], errors="coerce")
    d["commission_num"] = pd.to_numeric(d["commission_rate"], errors="coerce")
    quote_ts = pd.to_datetime(d["quote_timestamp"], utc=True, errors="coerce")
    scheduled = pd.to_datetime(d["scheduled_start_time"], utc=True, errors="coerce")

    duplicate_side = d.duplicated(
        ["race_id", "runner_id", "quote_snapshot_id", "market_source", "provider", "quote_side_norm"],
        keep=False,
    )
    row_blockers: list[dict] = []
    valid = pd.Series(True, index=d.index)
    back_type_ok = d["quote_side_norm"].eq("BACK") & d["quote_type_norm"].isin(SUPPORTED_BACK_TYPES)
    lay_type_ok = d["quote_side_norm"].eq("LAY") & d["quote_type_norm"].isin(SUPPORTED_LAY_TYPES)
    checks = {
        "QUOTE_IDENTITY_MISSING": d[["race_id", "runner_id", "quote_snapshot_id"]].isna().any(axis=1),
        "QUOTE_SOURCE_PROVIDER_MISSING": d["market_source"].isna() | d["provider"].isna() | d["market_source"].str.strip().eq("") | d["provider"].str.strip().eq(""),
        "QUOTE_TIMESTAMP_INVALID": quote_ts.isna() | scheduled.isna() | quote_ts.ge(scheduled),
        "QUOTE_SIDE_UNSUPPORTED": ~d["quote_side_norm"].isin({"BACK", "LAY"}),
        "QUOTE_TYPE_UNSUPPORTED_FOR_SIDE": ~(back_type_ok | lay_type_ok),
        "QUOTE_ODDS_OR_DEPTH_INVALID": d["odds_num"].isna() | d["odds_num"].le(1) | d["available_num"].isna() | d["available_num"].lt(0),
        "QUOTE_COMMISSION_INVALID": d["commission_num"].isna() | d["commission_num"].lt(0) | d["commission_num"].ge(1),
        "QUOTE_MARKET_NOT_OPEN": ~d["market_status_norm"].isin({"OPEN", "ACTIVE"}),
        "QUOTE_IN_PLAY": d["in_play"].map(truth),
        "QUOTE_SUSPENDED": d["suspended"].map(truth),
        "DUPLICATE_QUOTE_SIDE": duplicate_side,
        "LAY_NOT_BETFAIR_EXCHANGE": d["quote_side_norm"].eq("LAY") & ~d["market_source_norm"].eq("BETFAIR_EXCHANGE"),
    }
    for reason, mask in checks.items():
        mask = mask.fillna(True)
        valid &= ~mask
        for idx in d.index[mask]:
            row_blockers.append({"stage": "quote_snapshot", "reason": reason, "detail": f"{d.at[idx, 'race_id']}|{d.at[idx, 'runner_id']}|{d.at[idx, 'quote_snapshot_id']}"})

    d = d[valid].copy()
    if d.empty:
        return pd.DataFrame(), blockers + row_blockers, evidence

    group_cols = ["race_id", "runner_id", "quote_snapshot_id", "quote_timestamp", "scheduled_start_time", "market_source", "provider"]
    rows: list[dict] = []
    for key, g in d.groupby(group_cols, sort=False, dropna=False):
        row = dict(zip(group_cols, key))
        row["quote_certified"] = True
        row["commission_rate"] = float(g["commission_num"].max())
        row["quote_source_sha256"] = quote_sha
        back = g[g["quote_side_norm"].eq("BACK")]
        lay = g[g["quote_side_norm"].eq("LAY")]
        if not back.empty:
            row["back_quote_type"] = back.iloc[0]["quote_type_norm"]
            row["back_odds"] = float(back.iloc[0]["odds_num"])
            row["back_available"] = float(back.iloc[0]["available_num"])
        else:
            row["back_quote_type"] = ""
            row["back_odds"] = np.nan
            row["back_available"] = np.nan
        if not lay.empty:
            row["lay_quote_type"] = lay.iloc[0]["quote_type_norm"]
            row["lay_odds"] = float(lay.iloc[0]["odds_num"])
            row["lay_available"] = float(lay.iloc[0]["available_num"])
        else:
            row["lay_quote_type"] = ""
            row["lay_odds"] = np.nan
            row["lay_available"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows), blockers + row_blockers, evidence


def build_v2_input(model: pd.DataFrame, quotes: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    blockers: list[dict] = []
    if model.empty or quotes.empty:
        if model.empty:
            blockers.append({"stage": "join", "reason": "NO_CERTIFIED_MODEL_ROWS", "detail": ""})
        if quotes.empty:
            blockers.append({"stage": "join", "reason": "NO_CERTIFIED_QUOTE_ROWS", "detail": ""})
        return pd.DataFrame(), blockers

    joined = model.merge(
        quotes,
        on=["race_id", "runner_id", "scheduled_start_time"],
        how="outer",
        indicator=True,
        suffixes=("_model", "_quote"),
    )
    for _, row in joined[joined["_merge"].eq("left_only")].iterrows():
        blockers.append({"stage": "join", "reason": "MISSING_QUOTE_FOR_MODEL_RUNNER", "detail": f"{row['race_id']}|{row['runner_id']}"})
    for _, row in joined[joined["_merge"].eq("right_only")].iterrows():
        blockers.append({"stage": "join", "reason": "QUOTE_WITHOUT_MODEL_RUNNER", "detail": f"{row['race_id']}|{row['runner_id']}"})
    joined = joined[joined["_merge"].eq("both")].copy()
    if joined.empty:
        blockers.append({"stage": "join", "reason": "NO_JOINED_ROWS", "detail": ""})
        return pd.DataFrame(), blockers

    quote_ts = pd.to_datetime(joined["quote_timestamp"], utc=True, errors="coerce")
    model_ts = pd.to_datetime(joined["model_snapshot_time"], utc=True, errors="coerce")
    snapshot_ts = pd.concat([quote_ts, model_ts], axis=1).max(axis=1)
    out = pd.DataFrame(
        {
            "race_id": joined["race_id"],
            "runner_id": joined["runner_id"],
            "snapshot_id": [
                stable_hash([CONTRACT_VERSION, r.race_id, r.runner_id, r.model_snapshot_id, r.quote_snapshot_id, r.quote_timestamp])
                for r in joined.itertuples()
            ],
            "snapshot_time": snapshot_ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scheduled_start_time": joined["scheduled_start_time"],
            "quote_timestamp": joined["quote_timestamp"],
            "market_source": joined["market_source"],
            "provider": joined["provider"],
            "quote_certified": joined["quote_certified"],
            "model_id": joined["model_id"],
            "model_version": joined["model_version"],
            "model_snapshot_id": joined["model_snapshot_id"],
            "model_snapshot_sha256": joined["model_snapshot_sha256"],
            "feature_manifest_sha256": joined["feature_manifest_sha256"],
            "model_probability": joined["model_probability"],
            "probability_certified": joined["probability_certified"],
            "data_certified": joined["data_certified"],
            "commission_rate": joined["commission_rate"],
            "back_quote_type": joined["back_quote_type"],
            "back_odds": joined["back_odds"],
            "back_available": joined["back_available"],
            "lay_quote_type": joined["lay_quote_type"],
            "lay_odds": joined["lay_odds"],
            "lay_available": joined["lay_available"],
            "model_source_sha256": joined["model_source_sha256"],
            "quote_source_sha256": joined["quote_source_sha256"],
            "artifact_manifest_sha256": joined["artifact_manifest_sha256"],
            "quote_snapshot_id": joined["quote_snapshot_id"],
        }
    )
    return out, blockers


def reason_counts(blockers: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in blockers:
        key = f"{item['stage']}:{item['reason']}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage011-output", required=True, type=Path)
    parser.add_argument("--quote-snapshots", required=True, type=Path)
    parser.add_argument("--artifact-manifest", required=True, type=Path)
    parser.add_argument("--v2-input-output", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    args = parser.parse_args()

    model, model_blockers, model_evidence = adapt_model(args.stage011_output, args.artifact_manifest)
    quotes, quote_blockers, quote_evidence = adapt_quotes(args.quote_snapshots)
    v2_input, join_blockers = build_v2_input(model, quotes)
    blockers = model_blockers + quote_blockers + join_blockers

    args.v2_input_output.parent.mkdir(parents=True, exist_ok=True)
    if not v2_input.empty:
        v2_input.to_csv(args.v2_input_output, index=False)
    else:
        args.v2_input_output.write_text("", encoding="utf-8")

    audit = {
        "contract_version": CONTRACT_VERSION,
        "research_only": True,
        "execution_authorized": False,
        "profitability_claim": False,
        "market_as_model_feature": False,
        "stage011_output": model_evidence,
        "quote_snapshot": quote_evidence,
        "certified_model_rows": int(len(model)),
        "certified_quote_rows": int(len(quotes)),
        "joined_v2_rows": int(len(v2_input)),
        "joined_races": int(v2_input["race_id"].nunique()) if not v2_input.empty else 0,
        "blocker_count": int(len(blockers)),
        "blocker_reason_counts": reason_counts(blockers),
        "blockers": blockers[:500],
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("EDGEIQ SELECTION GATE V2 READINESS")
    print("CERTIFIED_MODEL_ROWS", len(model))
    print("CERTIFIED_QUOTE_ROWS", len(quotes))
    print("JOINED_V2_ROWS", len(v2_input))
    print("BLOCKERS", len(blockers), reason_counts(blockers))
    print("V2_INPUT", args.v2_input_output)
    print("AUDIT", args.audit)
    print("RESEARCH_ONLY; NO_OUTCOMES; NO_EXECUTION; NO_PROFITABILITY_CLAIM")


if __name__ == "__main__":
    main()
