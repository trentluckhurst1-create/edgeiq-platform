"""EDGEiQ BACK/LAY qualification gate V2, research-only.

This script consumes point-in-time model probabilities and timestamped market
quotes, then produces independent BACK WIN and LAY WIN research qualifications.
It never places bets, never consumes outcomes, and never claims historical ROI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


CONTRACT_VERSION = "EDGEIQ_SELECTION_GATE_V2_INPUT_CONTRACT_2026-10-13"
RESEARCH_ONLY = True

REQUIRED = [
    "race_id",
    "runner_id",
    "snapshot_id",
    "snapshot_time",
    "scheduled_start_time",
    "quote_timestamp",
    "market_source",
    "provider",
    "quote_certified",
    "model_id",
    "model_version",
    "model_snapshot_id",
    "model_snapshot_sha256",
    "feature_manifest_sha256",
    "model_probability",
    "probability_certified",
    "data_certified",
    "commission_rate",
    "back_quote_type",
    "back_odds",
    "back_available",
    "lay_quote_type",
    "lay_odds",
    "lay_available",
]

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

BACK_QUOTE_TYPES = {"BETFAIR_BACK", "BOOKMAKER_FIXED_WIN"}
LAY_QUOTE_TYPES = {"BETFAIR_LAY"}
EXCHANGE_SOURCES = {"BETFAIR_EXCHANGE"}


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_hash(values: Iterable[object]) -> str:
    payload = json.dumps([str(v) for v in values], separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reason_join(reasons: list[str]) -> str:
    if not reasons:
        return "PASS"
    return "|".join(sorted(set(reasons)))


def load_input(path: Path) -> tuple[pd.DataFrame, str]:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    forbidden = [c for c in header if c.lower() in FORBIDDEN_LOWER]
    if forbidden:
        raise ValueError(f"STOP: outcomes, closing prices, or returns in input: {forbidden}")
    missing = sorted(set(REQUIRED) - set(header))
    if missing:
        raise ValueError(f"STOP: missing columns {missing}")

    frame = pd.read_csv(path, dtype="string")
    if frame.empty:
        raise ValueError("STOP: empty input")
    return frame, file_sha256(path)


def classify(args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    source, source_hash = load_input(args.input)
    d = source.copy()

    numeric = [
        "model_probability",
        "commission_rate",
        "back_odds",
        "lay_odds",
        "back_available",
        "lay_available",
    ]
    for col in numeric:
        d[col] = pd.to_numeric(d[col], errors="coerce")

    snapshot_time = pd.to_datetime(d["snapshot_time"], utc=True, errors="coerce")
    scheduled_start = pd.to_datetime(d["scheduled_start_time"], utc=True, errors="coerce")
    quote_time = pd.to_datetime(d["quote_timestamp"], utc=True, errors="coerce")
    quote_age_seconds = (snapshot_time - quote_time).dt.total_seconds()

    if d[["race_id", "runner_id", "snapshot_id", "model_id", "model_version"]].duplicated().any():
        raise ValueError("STOP: duplicate runner snapshot keys")
    if d["snapshot_id"].duplicated().any():
        # Snapshot IDs are immutable event IDs for this research log.
        raise ValueError("STOP: duplicate snapshot_id")

    certified = (
        d["probability_certified"].map(truth)
        & d["data_certified"].map(truth)
        & d["quote_certified"].map(truth)
    ).fillna(False)

    model_invalid = (
        d["model_probability"].isna()
        | d["model_probability"].le(0)
        | d["model_probability"].ge(1)
        | d["commission_rate"].isna()
        | d["commission_rate"].lt(0)
        | d["commission_rate"].ge(1)
        | d["model_snapshot_sha256"].isna()
        | d["feature_manifest_sha256"].isna()
        | d["model_snapshot_id"].isna()
    ).fillna(True)

    timestamp_invalid = (
        snapshot_time.isna()
        | scheduled_start.isna()
        | quote_time.isna()
        | snapshot_time.ge(scheduled_start)
        | quote_time.gt(snapshot_time)
        | quote_age_seconds.lt(0)
        | quote_age_seconds.gt(args.max_quote_age_seconds)
    ).fillna(True)

    source_invalid = (
        d["market_source"].isna()
        | d["provider"].isna()
        | d["market_source"].str.strip().eq("")
        | d["provider"].str.strip().eq("")
    ).fillna(True)

    back_quote_type = d["back_quote_type"].fillna("").str.upper().str.strip()
    lay_quote_type = d["lay_quote_type"].fillna("").str.upper().str.strip()
    market_source = d["market_source"].fillna("").str.upper().str.strip()

    back_quote_invalid = (
        d["back_odds"].isna()
        | d["back_available"].isna()
        | d["back_odds"].le(1)
        | d["back_available"].lt(0)
        | ~back_quote_type.isin(BACK_QUOTE_TYPES)
    ).fillna(True)
    lay_quote_invalid = (
        d["lay_odds"].isna()
        | d["lay_available"].isna()
        | d["lay_odds"].le(1)
        | d["lay_available"].lt(0)
        | ~lay_quote_type.isin(LAY_QUOTE_TYPES)
    ).fillna(True)

    is_exchange = market_source.isin(EXCHANGE_SOURCES)
    crossed_exchange = (is_exchange & ~back_quote_invalid & ~lay_quote_invalid & d["back_odds"].ge(d["lay_odds"])).fillna(False)
    lay_source_invalid = (~is_exchange).fillna(True)
    back_source_invalid = (~(is_exchange | back_quote_type.eq("BOOKMAKER_FIXED_WIN"))).fillna(True)

    lay_liability_at_policy_stake = args.min_depth * (d["lay_odds"] - 1)
    back_market_ok = (
        ~back_quote_invalid
        & ~source_invalid
        & ~timestamp_invalid
        & ~crossed_exchange
        & ~back_source_invalid
        & d["back_available"].ge(args.min_depth)
    ).fillna(False)
    lay_market_ok = (
        ~lay_quote_invalid
        & ~source_invalid
        & ~timestamp_invalid
        & ~crossed_exchange
        & ~lay_source_invalid
        & d["lay_available"].ge(args.min_depth)
        & lay_liability_at_policy_stake.le(args.max_lay_liability)
    ).fillna(False)

    p = d["model_probability"]
    commission = d["commission_rate"]
    back_ev = p * (d["back_odds"] - 1) * (1 - commission) - (1 - p)
    lay_ev = (1 - p) * (1 - commission) / (d["lay_odds"] - 1) - p

    result = pd.DataFrame(
        {
            "contract_version": CONTRACT_VERSION,
            "snapshot_id": d["snapshot_id"],
            "race_id": d["race_id"],
            "runner_id": d["runner_id"],
            "snapshot_time": d["snapshot_time"],
            "scheduled_start_time": d["scheduled_start_time"],
            "quote_timestamp": d["quote_timestamp"],
            "quote_age_seconds": quote_age_seconds,
            "market_source": d["market_source"],
            "provider": d["provider"],
            "model_id": d["model_id"],
            "model_version": d["model_version"],
            "model_snapshot_id": d["model_snapshot_id"],
            "model_snapshot_sha256": d["model_snapshot_sha256"],
            "feature_manifest_sha256": d["feature_manifest_sha256"],
            "model_probability": p,
            "back_quote_type": back_quote_type,
            "back_odds": d["back_odds"],
            "back_available": d["back_available"],
            "back_ev_per_stake": back_ev,
            "lay_quote_type": lay_quote_type,
            "lay_odds": d["lay_odds"],
            "lay_available": d["lay_available"],
            "lay_liability_at_policy_stake": lay_liability_at_policy_stake,
            "lay_ev_per_liability": lay_ev,
            "execution_authorized": False,
            "research_only": RESEARCH_ONLY,
            "source_input_sha256": source_hash,
        }
    )

    back_status: list[str] = []
    lay_status: list[str] = []
    back_reasons: list[str] = []
    lay_reasons: list[str] = []
    for i in range(len(d)):
        common = []
        if model_invalid.iloc[i]:
            common.append("MODEL_INPUT_INVALID")
        if not certified.iloc[i]:
            common.append("CERTIFICATION_FAIL")
        if timestamp_invalid.iloc[i]:
            common.append("TIMESTAMP_FAIL")
        if source_invalid.iloc[i]:
            common.append("SOURCE_PROVIDER_FAIL")
        if crossed_exchange.iloc[i]:
            common.append("CROSSED_EXCHANGE_QUOTE")

        b_reasons = list(common)
        if back_quote_invalid.iloc[i]:
            b_reasons.append("BACK_QUOTE_INVALID")
        if back_source_invalid.iloc[i]:
            b_reasons.append("BACK_SOURCE_UNSUPPORTED")
        if not pd.isna(d["back_available"].iloc[i]) and d["back_available"].iloc[i] < args.min_depth:
            b_reasons.append("BACK_LIQUIDITY_FAIL")
        if b_reasons:
            back_status.append("FAIL_CLOSED")
        elif back_ev.iloc[i] >= args.min_edge and back_market_ok.iloc[i]:
            back_status.append("RESEARCH_CANDIDATE")
        else:
            back_status.append("NO_VALUE")

        l_reasons = list(common)
        if lay_quote_invalid.iloc[i]:
            l_reasons.append("LAY_QUOTE_INVALID")
        if lay_source_invalid.iloc[i]:
            l_reasons.append("LAY_REQUIRES_BETFAIR_EXCHANGE")
        if not pd.isna(d["lay_available"].iloc[i]) and d["lay_available"].iloc[i] < args.min_depth:
            l_reasons.append("LAY_LIQUIDITY_FAIL")
        if not pd.isna(lay_liability_at_policy_stake.iloc[i]) and lay_liability_at_policy_stake.iloc[i] > args.max_lay_liability:
            l_reasons.append("LAY_LIABILITY_FAIL")
        if l_reasons:
            lay_status.append("FAIL_CLOSED")
        elif lay_ev.iloc[i] >= args.min_edge and lay_market_ok.iloc[i]:
            lay_status.append("RESEARCH_CANDIDATE")
        else:
            lay_status.append("NO_VALUE")

        back_reasons.append(reason_join(b_reasons))
        lay_reasons.append(reason_join(l_reasons))

    result["back_status"] = back_status
    result["back_reason_codes"] = back_reasons
    result["lay_status"] = lay_status
    result["lay_reason_codes"] = lay_reasons
    result["paper_event_id"] = [
        stable_hash(
            [
                CONTRACT_VERSION,
                result.at[i, "snapshot_id"],
                result.at[i, "race_id"],
                result.at[i, "runner_id"],
                result.at[i, "model_snapshot_sha256"],
                result.at[i, "source_input_sha256"],
            ]
        )
        for i in result.index
    ]

    audit = {
        "contract_version": CONTRACT_VERSION,
        "research_only": RESEARCH_ONLY,
        "input": str(args.input),
        "input_sha256": source_hash,
        "rows": int(len(result)),
        "min_edge": args.min_edge,
        "min_depth": args.min_depth,
        "max_lay_liability": args.max_lay_liability,
        "max_quote_age_seconds": args.max_quote_age_seconds,
        "back_status_counts": result["back_status"].value_counts().to_dict(),
        "lay_status_counts": result["lay_status"].value_counts().to_dict(),
        "market_as_model_feature": False,
        "execution_authorized": False,
        "profitability_claim": False,
    }
    return result, audit


def write_paper_log(path: Path, classified: pd.DataFrame) -> None:
    log_cols = [
        "paper_event_id",
        "contract_version",
        "snapshot_id",
        "race_id",
        "runner_id",
        "snapshot_time",
        "scheduled_start_time",
        "quote_timestamp",
        "market_source",
        "provider",
        "model_id",
        "model_version",
        "model_probability",
        "back_status",
        "back_reason_codes",
        "back_ev_per_stake",
        "lay_status",
        "lay_reason_codes",
        "lay_ev_per_liability",
        "source_input_sha256",
        "execution_authorized",
        "research_only",
    ]
    rows = classified[log_cols].copy()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = pd.read_csv(path, dtype="string")
        duplicated = set(existing["paper_event_id"].astype(str)) & set(rows["paper_event_id"].astype(str))
        if duplicated:
            raise ValueError(f"STOP: paper log already contains event ids: {sorted(duplicated)[:5]}")
        rows.to_csv(path, mode="a", index=False, header=False)
    else:
        rows.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--paper-log", type=Path)
    parser.add_argument("--min-edge", type=float, default=0.03)
    parser.add_argument("--min-depth", type=float, default=50.0)
    parser.add_argument("--max-lay-liability", type=float, default=100.0)
    parser.add_argument("--max-quote-age-seconds", type=float, default=60.0)
    args = parser.parse_args()

    if args.output.exists():
        raise ValueError("STOP: output already exists")
    if not (0 < args.min_edge < 1):
        raise ValueError("STOP: invalid min-edge")
    if args.min_depth <= 0 or args.max_lay_liability <= 0 or args.max_quote_age_seconds < 0:
        raise ValueError("STOP: invalid policy")

    result, audit = classify(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    if args.audit:
        args.audit.parent.mkdir(parents=True, exist_ok=True)
        args.audit.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    if args.paper_log:
        write_paper_log(args.paper_log, result)

    print("EDGEIQ QUALIFICATION GATE V2")
    print("CONTRACT", CONTRACT_VERSION)
    print("ROWS", len(result), "BACK", result.back_status.value_counts().to_dict(), "LAY", result.lay_status.value_counts().to_dict())
    print("OUTPUT", args.output)
    if args.paper_log:
        print("PAPER_LOG", args.paper_log)
    print("RESEARCH_ONLY; NO_EXECUTION; NO_PROFITABILITY_CLAIM")


if __name__ == "__main__":
    main()
