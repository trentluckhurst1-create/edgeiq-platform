from __future__ import annotations

from pathlib import Path
import math
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

OVERLAY_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1.csv"
RUNNER_V6_PATH = DATA_DIR / "edgeiq_runner_score_v6.csv"
PACE_TRUST_PATH = DATA_DIR / "edgeiq_pace_trust_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_empirical_signal_filter_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_empirical_signal_filter_v1_summary.csv"

ACTION_ORDER = {
    "EXECUTE": 1,
    "STRONG_WATCH": 2,
    "WATCH": 3,
    "NO_BET": 4,
}


def normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def to_float(value: object) -> float:
    if value is None:
        return float("nan")
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else float("nan")
    text = str(value).strip().replace(",", "")
    if text == "":
        return float("nan")
    try:
        number = float(text)
    except Exception:
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def to_int(value: object) -> float:
    number = to_float(value)
    if math.isnan(number):
        return float("nan")
    return int(number)


def governance_flag(governance: str) -> str:
    gov = (governance or "").strip().upper()
    if gov in {"FIRST_STARTER_OR_UNKNOWN", "IMPORT_UNKNOWN"}:
        return "UNKNOWN_GOVERNANCE"
    if "LIMITED" in gov:
        return "LIMITED_GOVERNANCE"
    return ""


def pace_flag(pace_trust_band: str) -> str:
    trust = (pace_trust_band or "").strip().upper()
    if trust == "IGNORE":
        return "PACE_IGNORE"
    if trust == "LOW_TRUST":
        return "PACE_LOW_TRUST"
    if trust == "MEDIUM_TRUST":
        return "PACE_MEDIUM_TRUST"
    return ""


def join_flags(*flags: str) -> str:
    cleaned: list[str] = []
    for flag in flags:
        if not flag:
            continue
        for piece in str(flag).split("|"):
            item = piece.strip()
            if item and item not in cleaned:
                cleaned.append(item)
    return "|".join(cleaned) if cleaned else "CLEAN"


def format_number(value: float, decimals: int = 2) -> str:
    if value is None or math.isnan(value):
        return "NA"
    return f"{value:.{decimals}f}"


def main() -> None:
    overlay_df = pd.read_csv(OVERLAY_PATH)
    runner_df = pd.read_csv(RUNNER_V6_PATH)
    pace_df = pd.read_csv(PACE_TRUST_PATH)

    overlay_df = overlay_df.copy()
    overlay_df["meeting_date"] = overlay_df["meeting_date"].astype(str).str[:10]
    overlay_df["race_no"] = overlay_df["race_no"].apply(to_int)
    overlay_df["join_track"] = overlay_df["track"].apply(normalize_text)
    overlay_df["join_horse"] = overlay_df["horse"].apply(normalize_text)
    overlay_df["join_key"] = (
        overlay_df["meeting_date"].astype(str)
        + "|"
        + overlay_df["join_track"]
        + "|"
        + overlay_df["race_no"].fillna(-1).astype(int).astype(str)
        + "|"
        + overlay_df["join_horse"]
    )

    runner_df = runner_df.copy()
    meeting_date_col = "meeting_date" if "meeting_date" in runner_df.columns else "race_date"
    runner_df[meeting_date_col] = runner_df[meeting_date_col].astype(str).str[:10]
    runner_df["race_no"] = runner_df["race_no"].apply(to_int)
    runner_df["join_track"] = runner_df["track"].apply(normalize_text)
    runner_df["join_horse"] = runner_df["horse"].apply(normalize_text)
    runner_df["join_key"] = (
        runner_df[meeting_date_col].astype(str)
        + "|"
        + runner_df["join_track"]
        + "|"
        + runner_df["race_no"].fillna(-1).astype(int).astype(str)
        + "|"
        + runner_df["join_horse"]
    )
    runner_lookup = runner_df[["join_key", "runner_score_v6", "runner_rank_v6", "governance_band_v7_2"]].copy()
    runner_lookup["runner_score_v6"] = runner_lookup["runner_score_v6"].apply(to_float)
    runner_lookup["runner_rank_v6"] = runner_lookup["runner_rank_v6"].apply(to_int)
    runner_lookup["governance_band_v7_2"] = runner_lookup["governance_band_v7_2"].fillna("")
    runner_lookup = runner_lookup.drop_duplicates(subset=["join_key"], keep="last")

    pace_df = pace_df.copy()
    pace_df["race_no"] = pace_df["race_no"].apply(to_int)
    pace_df["join_track"] = pace_df["track"].apply(normalize_text)
    pace_lookup = pace_df[["join_track", "race_no", "pace_pressure_band_v1", "pace_trust_band_v1", "pace_trust_reason_v1"]].copy()
    pace_lookup = pace_lookup.drop_duplicates(subset=["join_track", "race_no"], keep="last")

    df = overlay_df.merge(runner_lookup, on="join_key", how="left", suffixes=("", "_runner"))
    df = df.merge(pace_lookup, on=["join_track", "race_no"], how="left")

    df["runner_score_v6"] = np.where(df["runner_score_v6"].notna(), df["runner_score_v6"], df["runner_score_v6_runner"])
    df["runner_rank_v6"] = np.where(df["runner_rank_v6"].notna(), df["runner_rank_v6"], df["runner_rank_v6_runner"])
    df["governance_band_v7_2"] = np.where(df["governance_band_v7_2"].fillna("") != "", df["governance_band_v7_2"], df["governance_band_v7_2_runner"])

    df["runner_score_v6"] = pd.to_numeric(df["runner_score_v6"], errors="coerce")
    df["runner_rank_v6"] = pd.to_numeric(df["runner_rank_v6"], errors="coerce")
    df["empirical_fair_price_v1"] = pd.to_numeric(df["empirical_fair_price_v1"], errors="coerce")
    df["market_price_v1"] = pd.to_numeric(df["market_price_v1"], errors="coerce")
    df["edge_pct_v1"] = pd.to_numeric(df["edge_pct_v1"], errors="coerce")
    df["governance_band_v7_2"] = df["governance_band_v7_2"].fillna("")
    df["pace_trust_band_v1"] = df["pace_trust_band_v1"].fillna("UNKNOWN")
    df["pace_trust_reason_v1"] = df["pace_trust_reason_v1"].fillna("")
    df["market_match_status_v1"] = df["market_match_status_v1"].fillna("")

    actions: list[str] = []
    risk_flags: list[str] = []
    reasons: list[str] = []

    for row in df.itertuples(index=False):
        market_price = to_float(getattr(row, "market_price_v1"))
        fair_price = to_float(getattr(row, "empirical_fair_price_v1"))
        edge_pct = to_float(getattr(row, "edge_pct_v1"))
        runner_score = to_float(getattr(row, "runner_score_v6"))
        runner_rank = to_int(getattr(row, "runner_rank_v6"))
        governance = str(getattr(row, "governance_band_v7_2") or "")
        pace_trust = str(getattr(row, "pace_trust_band_v1") or "UNKNOWN")
        pace_reason = str(getattr(row, "pace_trust_reason_v1") or "")
        market_status = str(getattr(row, "market_match_status_v1") or "")

        gov_flag = governance_flag(governance)
        trust_flag = pace_flag(pace_trust)
        scratched = market_status.upper() == "SCRATCHED"
        market_valid = market_status.upper() == "MATCHED" and not math.isnan(market_price) and market_price > 1

        action = "NO_BET"
        primary_flag = ""
        reason = ""

        if scratched:
            primary_flag = "SCRATCHED"
            reason = "NO_BET | runner scratched in live TAB market"
        elif not market_valid:
            primary_flag = "NO_MARKET"
            reason = "NO_BET | no valid live TAB market price"
        elif math.isnan(runner_score) or runner_score < 35:
            primary_flag = "LOW_SCORE_LT_35"
            reason = f"NO_BET | runner score {format_number(runner_score)} below 35 floor"
        elif market_price > 101:
            primary_flag = "LONG_PRICE_GT_101"
            reason = f"NO_BET | market price {format_number(market_price)} above 101 ceiling"
        elif market_price < 3:
            primary_flag = "SHORT_PRICE_LT_3"
            reason = f"NO_BET | market price {format_number(market_price)} below 3 minimum"
        elif not math.isnan(runner_rank) and runner_rank >= 11:
            if (not math.isnan(edge_pct)) and edge_pct >= 100 and runner_score >= 45 and 3 <= market_price <= 101:
                action = "WATCH"
                primary_flag = "DEEP_RANK_EXCEPTION"
                reason = (
                    f"WATCH | rank 11+ exception allowed: edge {format_number(edge_pct)}%, "
                    f"score {format_number(runner_score, 3)}, market {format_number(market_price)}"
                )
            else:
                primary_flag = "DEEP_RANK_11_PLUS"
                reason = "NO_BET | rank 11+ blocked unless edge >= 100 and score >= 45"
        elif (not math.isnan(edge_pct)) and edge_pct >= 20 and runner_rank <= 5 and runner_score >= 50 and 3 <= market_price <= 51:
            action = "EXECUTE"
            reason = (
                f"EXECUTE | edge {format_number(edge_pct)}% >= 20, rank {int(runner_rank)} <= 5, "
                f"score {format_number(runner_score, 3)} >= 50, market {format_number(market_price)} in 3-51"
            )
        elif (not math.isnan(edge_pct)) and edge_pct >= 15 and runner_rank <= 8 and runner_score >= 45 and 3 <= market_price <= 71:
            action = "STRONG_WATCH"
            reason = (
                f"STRONG_WATCH | edge {format_number(edge_pct)}% >= 15, rank {int(runner_rank)} <= 8, "
                f"score {format_number(runner_score, 3)} >= 45, market {format_number(market_price)} in 3-71"
            )
        elif (not math.isnan(edge_pct)) and edge_pct >= 10 and runner_rank <= 10 and runner_score >= 40 and 3 <= market_price <= 101:
            action = "WATCH"
            reason = (
                f"WATCH | edge {format_number(edge_pct)}% >= 10, rank {int(runner_rank)} <= 10, "
                f"score {format_number(runner_score, 3)} >= 40, market {format_number(market_price)} in 3-101"
            )
        else:
            primary_flag = "NO_RULE_MATCH"
            reason = "NO_BET | overlay did not clear signal filter thresholds"

        combined_flag = join_flags(primary_flag, gov_flag, trust_flag)
        if action != "NO_BET":
            reason = (
                reason
                + f" | governance={governance or 'UNKNOWN'}"
                + f" | pace_trust={pace_trust}"
                + (f" | pace_note={pace_reason}" if pace_reason else "")
            )
        else:
            reason = (
                reason
                + f" | governance={governance or 'UNKNOWN'}"
                + f" | pace_trust={pace_trust}"
            )

        actions.append(action)
        risk_flags.append(combined_flag)
        reasons.append(reason)

    df["action"] = actions
    df["risk_flag"] = risk_flags
    df["reason"] = reasons

    output_df = df[
        [
            "track",
            "race_no",
            "horse",
            "action",
            "runner_rank_v6",
            "runner_score_v6",
            "empirical_fair_price_v1",
            "market_price_v1",
            "edge_pct_v1",
            "governance_band_v7_2",
            "risk_flag",
            "reason",
        ]
    ].copy()
    output_df = output_df.rename(
        columns={
            "empirical_fair_price_v1": "fair_price",
            "market_price_v1": "market_price",
            "edge_pct_v1": "edge_pct",
            "governance_band_v7_2": "governance",
        }
    )
    output_df["_action_order"] = output_df["action"].map(ACTION_ORDER).fillna(999)
    output_df["_edge_sort"] = output_df["edge_pct"].fillna(-999999.0)
    output_df = output_df.sort_values(["_action_order", "_edge_sort", "runner_rank_v6", "runner_score_v6"], ascending=[True, False, True, False])
    output_df = output_df.drop(columns=["_action_order", "_edge_sort"])
    output_df.to_csv(OUTPUT_PATH, index=False)

    signal_df = output_df[output_df["action"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"])].copy()
    source_df = df.copy()

    summary_df = pd.DataFrame(
        {
            "metric": [
                "rows",
                "execute_count",
                "strong_watch_count",
                "watch_count",
                "no_bet_count",
                "signal_count",
                "avg_signal_edge",
                "median_signal_edge",
                "max_signal_edge",
                "high_trust_signal_count",
                "medium_trust_signal_count",
                "low_trust_signal_count",
                "ignore_trust_signal_count",
                "deep_rank_exception_watch_count",
            ],
            "value": [
                int(len(output_df)),
                int((output_df["action"] == "EXECUTE").sum()),
                int((output_df["action"] == "STRONG_WATCH").sum()),
                int((output_df["action"] == "WATCH").sum()),
                int((output_df["action"] == "NO_BET").sum()),
                int(len(signal_df)),
                float(signal_df["edge_pct"].mean()) if len(signal_df) else float("nan"),
                float(signal_df["edge_pct"].median()) if len(signal_df) else float("nan"),
                float(signal_df["edge_pct"].max()) if len(signal_df) else float("nan"),
                int(((source_df["pace_trust_band_v1"] == "HIGH_TRUST") & (source_df["action"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"]))).sum()),
                int(((source_df["pace_trust_band_v1"] == "MEDIUM_TRUST") & (source_df["action"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"]))).sum()),
                int(((source_df["pace_trust_band_v1"] == "LOW_TRUST") & (source_df["action"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"]))).sum()),
                int(((source_df["pace_trust_band_v1"] == "IGNORE") & (source_df["action"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"]))).sum()),
                int(((output_df["action"] == "WATCH") & output_df["risk_flag"].str.contains("DEEP_RANK_EXCEPTION", na=False)).sum()),
            ],
        }
    )
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_EMPIRICAL_SIGNAL_FILTER_V1] COMPLETE")
    print(f"rows={len(output_df)}")
    print(f"execute_count={(output_df['action'] == 'EXECUTE').sum()}")
    print(f"strong_watch_count={(output_df['action'] == 'STRONG_WATCH').sum()}")
    print(f"watch_count={(output_df['action'] == 'WATCH').sum()}")
    print(f"no_bet_count={(output_df['action'] == 'NO_BET').sum()}")
    print(f"signal_count={len(signal_df)}")
    print(f"out={OUTPUT_PATH}")
    print(f"summary_out={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
