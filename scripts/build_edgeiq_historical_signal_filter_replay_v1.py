from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_REPLAY = DATA / "edgeiq_historical_replay_v1.csv"
HISTORICAL_PACE_TRUST = DATA / "edgeiq_historical_pace_trust_replay_v1.csv"

OUT = DATA / "edgeiq_historical_signal_filter_replay_v1.csv"
SUMMARY = DATA / "edgeiq_historical_signal_filter_replay_v1_summary.csv"
BY_ACTION = DATA / "edgeiq_historical_signal_filter_replay_v1_by_action.csv"
BY_RANK = DATA / "edgeiq_historical_signal_filter_replay_v1_by_rank.csv"
BY_GOVERNANCE = DATA / "edgeiq_historical_signal_filter_replay_v1_by_governance.csv"
BY_SCORE_BAND = DATA / "edgeiq_historical_signal_filter_replay_v1_by_score_band.csv"
FALSE_POSITIVE_AUDIT = DATA / "edgeiq_historical_signal_filter_replay_v1_false_positive_audit.csv"

ACTION_ORDER = {
    "EXECUTE": 1,
    "STRONG_WATCH": 2,
    "WATCH": 3,
    "NO_BET": 4,
}

GOVERNANCE_ORDER = [
    "PROVEN",
    "LIMITED_DATA_3_4_STARTS",
    "LIMITED_DATA_2_STARTS",
    "LIMITED_DATA_1_START",
    "IMPORT_UNKNOWN",
    "FIRST_STARTER_OR_UNKNOWN",
    "UNKNOWN",
]

RANK_BUCKET_ORDER = [
    "RANK_1",
    "RANK_2",
    "RANK_3",
    "RANK_4_5",
    "RANK_6_10",
    "RANK_11_PLUS",
    "UNKNOWN",
]

SCORE_BAND_ORDER = [
    "LT_40",
    "40_44",
    "45_49",
    "50_54",
    "55_59",
    "60_64",
    "65_69",
    "70_74",
    "75_79",
    "80_PLUS",
    "UNKNOWN",
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def upper_text(value: object) -> str:
    return clean_text(value).upper()


def to_float(value: object) -> float:
    if value is None or pd.isna(value):
        return math.nan
    if isinstance(value, (int, float)):
        value = float(value)
        return value if math.isfinite(value) else math.nan
    text = str(value).replace("$", "").replace(",", "").replace("kg", "").strip()
    if text == "":
        return math.nan
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return math.nan
    try:
        number = float(match.group(0))
    except ValueError:
        return math.nan
    return number if math.isfinite(number) else math.nan


def to_int(value: object) -> float:
    number = to_float(value)
    if pd.isna(number):
        return math.nan
    return int(number)


def governance_status(starts: object, horse_name: object) -> str:
    starts_num = to_int(starts)
    horse = upper_text(horse_name)
    if pd.isna(starts_num) or starts_num <= 0:
        if any(tag in horse for tag in ["(GB)", "(IRE)", "(FR)", "(USA)", "(JPN)", "(NZ)"]):
            return "IMPORT_UNKNOWN"
        return "FIRST_STARTER_OR_UNKNOWN"
    if starts_num == 1:
        return "LIMITED_DATA_1_START"
    if starts_num == 2:
        return "LIMITED_DATA_2_STARTS"
    if starts_num < 5:
        return "LIMITED_DATA_3_4_STARTS"
    return "PROVEN"


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
    if pd.isna(value):
        return "NA"
    return f"{float(value):.{decimals}f}"


def rank_bucket(rank_value: object) -> str:
    rank_num = to_int(rank_value)
    if pd.isna(rank_num):
        return "UNKNOWN"
    if rank_num == 1:
        return "RANK_1"
    if rank_num == 2:
        return "RANK_2"
    if rank_num == 3:
        return "RANK_3"
    if rank_num <= 5:
        return "RANK_4_5"
    if rank_num <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def score_band(score_value: object) -> str:
    score_num = to_float(score_value)
    if pd.isna(score_num):
        return "UNKNOWN"
    if score_num < 40:
        return "LT_40"
    if score_num < 45:
        return "40_44"
    if score_num < 50:
        return "45_49"
    if score_num < 55:
        return "50_54"
    if score_num < 60:
        return "55_59"
    if score_num < 65:
        return "60_64"
    if score_num < 70:
        return "65_69"
    if score_num < 75:
        return "70_74"
    if score_num < 80:
        return "75_79"
    return "80_PLUS"


def softmax_probabilities(scores: pd.Series, temperature: float) -> pd.Series:
    numeric_scores = pd.to_numeric(scores, errors="coerce").fillna(0.0)
    scaled = numeric_scores / max(temperature, 1.0)
    scaled = scaled - scaled.max()
    exp_values = np.exp(scaled)
    denom = exp_values.sum()
    if denom <= 0:
        return pd.Series(np.repeat(1.0 / max(len(scores), 1), len(scores)), index=scores.index)
    return pd.Series(exp_values / denom, index=scores.index)


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0.0:
        return math.nan
    return float(numerator) / float(denominator)


def roi_proxy(df: pd.DataFrame) -> float:
    if df.empty:
        return math.nan
    expected_random_wins = pd.to_numeric(df["random_win_prob_v1"], errors="coerce").fillna(0.0).sum()
    if expected_random_wins <= 0:
        return math.nan
    wins = pd.to_numeric(df["won"], errors="coerce").fillna(0.0).sum()
    return (float(wins) / float(expected_random_wins)) - 1.0


def load_base_replay() -> pd.DataFrame:
    if not HISTORICAL_REPLAY.exists():
        raise FileNotFoundError(f"Missing historical replay file: {HISTORICAL_REPLAY}")

    df = pd.read_csv(HISTORICAL_REPLAY, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["runner_score"] = pd.to_numeric(df["runner_score"], errors="coerce")
    df["runner_rank"] = pd.to_numeric(df["runner_rank"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["placed"] = df["finish_position"].le(3).astype(int)
    df["governance_band_v1"] = df["projection_status_v6"].fillna("").astype(str).str.strip()
    missing_governance = df["governance_band_v1"].eq("")
    if missing_governance.any():
        df.loc[missing_governance, "governance_band_v1"] = df.loc[missing_governance].apply(
            lambda row: governance_status(row.get("starts_before"), row.get("horse")),
            axis=1,
        )
    df["governance_band_v1"] = df["governance_band_v1"].replace({"": "UNKNOWN"}).fillna("UNKNOWN")
    return df


def load_optional_pace_trust() -> pd.DataFrame:
    if not HISTORICAL_PACE_TRUST.exists():
        return pd.DataFrame(columns=[
            "race_key",
            "horse_key",
            "pace_pressure_band_v1",
            "pace_trust_band_v1",
            "pace_trust_reason_v1",
            "field_size_v1",
            "runner_score_pace_trust_v1",
            "runner_rank_pace_trust_v1",
        ])

    cols = [
        "race_key",
        "horse_key",
        "pace_pressure_band_v1",
        "pace_trust_band_v1",
        "pace_trust_reason_v1",
        "field_size_v1",
        "runner_score_pace_trust_v1",
        "runner_rank_pace_trust_v1",
    ]
    df = pd.read_csv(HISTORICAL_PACE_TRUST, low_memory=False, usecols=cols)
    df["pace_pressure_band_v1"] = df["pace_pressure_band_v1"].fillna("UNKNOWN")
    df["pace_trust_band_v1"] = df["pace_trust_band_v1"].fillna("IGNORE")
    df["pace_trust_reason_v1"] = df["pace_trust_reason_v1"].fillna("")
    df["field_size_v1"] = pd.to_numeric(df["field_size_v1"], errors="coerce")
    df["runner_score_pace_trust_v1"] = pd.to_numeric(df["runner_score_pace_trust_v1"], errors="coerce")
    df["runner_rank_pace_trust_v1"] = pd.to_numeric(df["runner_rank_pace_trust_v1"], errors="coerce")
    return df


def build_probability_proxy(df: pd.DataFrame) -> pd.DataFrame:
    train = df.copy()
    train["rank_bucket_v1"] = train["runner_rank_signal_v1"].apply(rank_bucket)
    train["score_band_v1"] = train["runner_score_signal_v1"].apply(score_band)

    rank_stats = (
        train.groupby("rank_bucket_v1", dropna=False)
        .agg(runners=("horse", "size"), wins=("won", "sum"))
        .reset_index()
    )
    rank_stats["rank_true_win_rate_v1"] = rank_stats["wins"] / rank_stats["runners"]
    rank_prob_map = dict(zip(rank_stats["rank_bucket_v1"], rank_stats["rank_true_win_rate_v1"]))

    score_stats = (
        train.groupby("score_band_v1", dropna=False)
        .agg(runners=("horse", "size"), wins=("won", "sum"))
        .reset_index()
    )
    score_stats["score_true_win_rate_v1"] = score_stats["wins"] / score_stats["runners"]
    score_prob_map = dict(zip(score_stats["score_band_v1"], score_stats["score_true_win_rate_v1"]))

    temperature = float(pd.to_numeric(train["runner_score_signal_v1"], errors="coerce").std())
    if pd.isna(temperature) or temperature <= 0:
        temperature = 15.0

    df = df.copy()
    df["rank_bucket_v1"] = df["runner_rank_signal_v1"].apply(rank_bucket)
    df["score_band_v1"] = df["runner_score_signal_v1"].apply(score_band)
    df["rank_true_win_rate_v1"] = df["rank_bucket_v1"].map(rank_prob_map)
    df["score_true_win_rate_v1"] = df["score_band_v1"].map(score_prob_map)
    df["softmax_prob_v1"] = df.groupby("race_key")["runner_score_signal_v1"].transform(lambda values: softmax_probabilities(values, temperature))
    df["empirical_fair_prob_raw_v1"] = pd.concat(
        [df["rank_true_win_rate_v1"], df["score_true_win_rate_v1"], df["softmax_prob_v1"]],
        axis=1,
    ).mean(axis=1)
    df["empirical_fair_prob_v1"] = df["empirical_fair_prob_raw_v1"] / df.groupby("race_key")["empirical_fair_prob_raw_v1"].transform("sum")
    df["empirical_fair_price_v1"] = np.where(
        df["empirical_fair_prob_v1"] > 0,
        1.0 / df["empirical_fair_prob_v1"],
        np.nan,
    )
    df["edge_proxy_pct_v1"] = ((df["field_size_v1"] / df["empirical_fair_price_v1"]) - 1.0) * 100.0
    return df


def assign_actions(df: pd.DataFrame) -> pd.DataFrame:
    actions: list[str] = []
    risk_flags: list[str] = []
    reasons: list[str] = []

    for row in df.itertuples(index=False):
        score_value = to_float(getattr(row, "runner_score_signal_v1"))
        rank_value = to_int(getattr(row, "runner_rank_signal_v1"))
        fair_price = to_float(getattr(row, "empirical_fair_price_v1"))
        edge_proxy = to_float(getattr(row, "edge_proxy_pct_v1"))
        governance = str(getattr(row, "governance_band_v1") or "UNKNOWN")
        pace_trust = str(getattr(row, "pace_trust_band_v1") or "IGNORE")
        pace_reason = str(getattr(row, "pace_trust_reason_v1") or "")

        action = "NO_BET"
        primary_flag = ""
        reason = ""

        if pd.isna(score_value) or score_value < 35:
            primary_flag = "LOW_SCORE_LT_35"
            reason = f"NO_BET | runner score {format_number(score_value)} below 35 floor"
        elif pd.isna(fair_price):
            primary_flag = "NO_FAIR_PRICE"
            reason = "NO_BET | empirical fair price proxy unavailable"
        elif fair_price > 101:
            primary_flag = "LONG_FAIR_PRICE_GT_101"
            reason = f"NO_BET | empirical fair price {format_number(fair_price)} above 101 ceiling"
        elif fair_price < 3:
            primary_flag = "SHORT_FAIR_PRICE_LT_3"
            reason = f"NO_BET | empirical fair price {format_number(fair_price)} below 3 minimum"
        elif not pd.isna(rank_value) and rank_value >= 11:
            if (not pd.isna(edge_proxy)) and edge_proxy >= 100 and score_value >= 45 and 3 <= fair_price <= 101:
                action = "WATCH"
                primary_flag = "DEEP_RANK_EXCEPTION"
                reason = (
                    f"WATCH | rank 11+ exception allowed: proxy edge {format_number(edge_proxy)}%, "
                    f"score {format_number(score_value, 3)}, fair {format_number(fair_price)}"
                )
            else:
                primary_flag = "DEEP_RANK_11_PLUS"
                reason = "NO_BET | rank 11+ blocked unless proxy edge >= 100 and score >= 45"
        elif (not pd.isna(edge_proxy)) and edge_proxy >= 20 and rank_value <= 5 and score_value >= 50 and 3 <= fair_price <= 51:
            action = "EXECUTE"
            reason = (
                f"EXECUTE | proxy edge {format_number(edge_proxy)}% >= 20, rank {int(rank_value)} <= 5, "
                f"score {format_number(score_value, 3)} >= 50, fair {format_number(fair_price)} in 3-51"
            )
        elif (not pd.isna(edge_proxy)) and edge_proxy >= 15 and rank_value <= 8 and score_value >= 45 and 3 <= fair_price <= 71:
            action = "STRONG_WATCH"
            reason = (
                f"STRONG_WATCH | proxy edge {format_number(edge_proxy)}% >= 15, rank {int(rank_value)} <= 8, "
                f"score {format_number(score_value, 3)} >= 45, fair {format_number(fair_price)} in 3-71"
            )
        elif (not pd.isna(edge_proxy)) and edge_proxy >= 10 and rank_value <= 10 and score_value >= 40 and 3 <= fair_price <= 101:
            action = "WATCH"
            reason = (
                f"WATCH | proxy edge {format_number(edge_proxy)}% >= 10, rank {int(rank_value)} <= 10, "
                f"score {format_number(score_value, 3)} >= 40, fair {format_number(fair_price)} in 3-101"
            )
        else:
            primary_flag = "NO_RULE_MATCH"
            reason = "NO_BET | replay-side proxy did not clear signal thresholds"

        combined_flag = join_flags(primary_flag, governance_flag(governance), pace_flag(pace_trust))
        reason = (
            reason
            + f" | governance={governance}"
            + f" | pace_trust={pace_trust}"
            + (f" | pace_note={pace_reason}" if pace_reason else "")
            + " | mode=historical_empirical_proxy"
        )
        actions.append(action)
        risk_flags.append(combined_flag)
        reasons.append(reason)

    df = df.copy()
    df["action"] = actions
    df["risk_flag_v1"] = risk_flags
    df["reason_v1"] = reasons
    df["signal_flag_v1"] = df["action"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"]).astype(int)
    df["execute_false_positive_v1"] = ((df["action"] == "EXECUTE") & (df["won"] != 1)).astype(int)
    return df


def build_action_summary(signal_df: pd.DataFrame, total_rows: int, total_winners: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for action in ["EXECUTE", "STRONG_WATCH", "WATCH"]:
        subset = signal_df[signal_df["action"] == action].copy()
        rows.append(
            {
                "action": action,
                "signals": int(len(subset)),
                "signal_rate": safe_rate(len(subset), total_rows),
                "wins": int(subset["won"].sum()),
                "places": int(subset["placed"].sum()),
                "win_rate": safe_rate(subset["won"].sum(), len(subset)),
                "place_rate": safe_rate(subset["placed"].sum(), len(subset)),
                "avg_finish": float(subset["finish_position"].mean()) if len(subset) else math.nan,
                "avg_rank": float(subset["runner_rank_signal_v1"].mean()) if len(subset) else math.nan,
                "avg_score": float(subset["runner_score_signal_v1"].mean()) if len(subset) else math.nan,
                "expected_random_wins": float(subset["random_win_prob_v1"].sum()) if len(subset) else math.nan,
                "roi_proxy": roi_proxy(subset),
                "winner_top1_capture": safe_rate(((subset["won"] == 1) & (subset["runner_rank_signal_v1"] <= 1)).sum(), total_winners),
                "winner_top3_capture": safe_rate(((subset["won"] == 1) & (subset["runner_rank_signal_v1"] <= 3)).sum(), total_winners),
                "winner_top5_capture": safe_rate(((subset["won"] == 1) & (subset["runner_rank_signal_v1"] <= 5)).sum(), total_winners),
            }
        )
    out = pd.DataFrame(rows)
    out["sort_order"] = out["action"].map(ACTION_ORDER)
    out = out.sort_values(["sort_order", "action"]).drop(columns=["sort_order"])
    return out


def build_group_table(df: pd.DataFrame, group_col: str, sort_order: list[str] | None = None, include_roi: bool = False) -> pd.DataFrame:
    grouped = (
        df.groupby(group_col, dropna=False)
        .agg(
            signals=("horse", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("finish_position", "mean"),
            avg_rank=("runner_rank_signal_v1", "mean"),
            avg_score=("runner_score_signal_v1", "mean"),
            avg_fair_price=("empirical_fair_price_v1", "mean"),
            avg_edge_proxy=("edge_proxy_pct_v1", "mean"),
            expected_random_wins=("random_win_prob_v1", "sum"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["signals"]
    grouped["place_rate"] = grouped["places"] / grouped["signals"]
    if include_roi:
        roi_values: list[float] = []
        for group_value in grouped[group_col].tolist():
            subset = df[df[group_col] == group_value]
            roi_values.append(roi_proxy(subset))
        grouped["roi_proxy"] = roi_values
    if sort_order is not None:
        grouped["sort_order"] = grouped[group_col].map({value: idx for idx, value in enumerate(sort_order, start=1)}).fillna(999)
        grouped = grouped.sort_values(["sort_order", group_col]).drop(columns=["sort_order"])
    else:
        grouped = grouped.sort_values(["signals", group_col], ascending=[False, True])
    return grouped


def build_false_positive_audit(execute_df: pd.DataFrame) -> pd.DataFrame:
    loss_df = execute_df[execute_df["won"] != 1].copy()
    total_losses = int(len(loss_df))
    rows: list[dict[str, object]] = []

    dimensions = [
        ("governance", "governance_band_v1"),
        ("pace_trust", "pace_trust_band_v1"),
        ("rank_bucket", "rank_bucket_v1"),
        ("score_bucket", "score_band_v1"),
    ]

    for label, column in dimensions:
        all_groups = execute_df.groupby(column, dropna=False)
        loss_groups = loss_df.groupby(column, dropna=False)
        for group_value, group_df in all_groups:
            losing_execute_count = int(loss_groups.size().get(group_value, 0))
            execute_signals = int(len(group_df))
            execute_wins = int(group_df["won"].sum())
            rows.append(
                {
                    "audit_dimension": label,
                    "audit_value": group_value,
                    "execute_signals": execute_signals,
                    "execute_wins": execute_wins,
                    "losing_execute_count": losing_execute_count,
                    "execute_loss_rate": safe_rate(losing_execute_count, execute_signals),
                    "execute_win_rate": safe_rate(execute_wins, execute_signals),
                    "avg_finish": float(group_df["finish_position"].mean()) if execute_signals else math.nan,
                    "avg_rank": float(group_df["runner_rank_signal_v1"].mean()) if execute_signals else math.nan,
                    "avg_score": float(group_df["runner_score_signal_v1"].mean()) if execute_signals else math.nan,
                    "share_of_all_execute_losses": safe_rate(losing_execute_count, total_losses),
                }
            )

    audit = pd.DataFrame(rows)
    audit = audit.sort_values(
        ["losing_execute_count", "execute_loss_rate", "execute_signals", "audit_dimension", "audit_value"],
        ascending=[False, False, False, True, True],
    ).reset_index(drop=True)
    return audit


def main() -> None:
    base = load_base_replay()
    pace = load_optional_pace_trust()

    if not pace.empty:
        merged = base.merge(pace, on=["race_key", "horse_key"], how="left")
    else:
        merged = base.copy()
        merged["pace_pressure_band_v1"] = "UNKNOWN"
        merged["pace_trust_band_v1"] = "IGNORE"
        merged["pace_trust_reason_v1"] = "historical pace trust replay unavailable"
        merged["field_size_v1"] = np.nan
        merged["runner_score_pace_trust_v1"] = np.nan
        merged["runner_rank_pace_trust_v1"] = np.nan

    merged["pace_pressure_band_v1"] = merged["pace_pressure_band_v1"].fillna("UNKNOWN")
    merged["pace_trust_band_v1"] = merged["pace_trust_band_v1"].fillna("IGNORE")
    merged["pace_trust_reason_v1"] = merged["pace_trust_reason_v1"].fillna("")
    merged["field_size_v1"] = pd.to_numeric(merged["field_size_v1"], errors="coerce")
    merged["field_size_v1"] = merged["field_size_v1"].fillna(merged.groupby("race_key")["horse"].transform("size"))
    merged["field_size_v1"] = pd.to_numeric(merged["field_size_v1"], errors="coerce")
    merged["runner_score_pace_trust_v1"] = pd.to_numeric(merged["runner_score_pace_trust_v1"], errors="coerce")
    merged["runner_rank_pace_trust_v1"] = pd.to_numeric(merged["runner_rank_pace_trust_v1"], errors="coerce")
    merged["runner_score_signal_v1"] = merged["runner_score_pace_trust_v1"].where(merged["runner_score_pace_trust_v1"].notna(), merged["runner_score"])
    merged["runner_rank_signal_v1"] = merged["runner_rank_pace_trust_v1"].where(merged["runner_rank_pace_trust_v1"].notna(), merged["runner_rank"])
    merged["random_win_prob_v1"] = np.where(merged["field_size_v1"] > 0, 1.0 / merged["field_size_v1"], np.nan)

    merged = build_probability_proxy(merged)
    merged = assign_actions(merged)

    ordered = merged.copy()
    ordered["action_sort_v1"] = ordered["action"].map(ACTION_ORDER).fillna(999)
    ordered = ordered.sort_values(
        ["meeting_date", "track", "race_no", "action_sort_v1", "edge_proxy_pct_v1", "runner_rank_signal_v1", "runner_score_signal_v1", "horse"],
        ascending=[True, True, True, True, False, True, False, True],
    ).drop(columns=["action_sort_v1"])

    output_columns = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_key",
        "horse_key",
        "action",
        "runner_rank",
        "runner_score",
        "runner_rank_signal_v1",
        "runner_score_signal_v1",
        "rank_bucket_v1",
        "score_band_v1",
        "governance_band_v1",
        "pace_pressure_band_v1",
        "pace_trust_band_v1",
        "field_size_v1",
        "empirical_fair_prob_v1",
        "empirical_fair_price_v1",
        "edge_proxy_pct_v1",
        "finish_position",
        "won",
        "placed",
        "signal_flag_v1",
        "execute_false_positive_v1",
        "risk_flag_v1",
        "reason_v1",
    ]
    ordered[output_columns].to_csv(OUT, index=False)

    signal_df = ordered[ordered["signal_flag_v1"] == 1].copy()
    winners_df = ordered[ordered["won"] == 1].copy()
    total_rows = int(len(ordered))
    total_races = int(ordered["race_key"].nunique())
    total_winners = int(len(winners_df))
    execute_df = ordered[ordered["action"] == "EXECUTE"].copy()
    strong_watch_df = ordered[ordered["action"] == "STRONG_WATCH"].copy()
    watch_df = ordered[ordered["action"] == "WATCH"].copy()

    action_summary = build_action_summary(signal_df, total_rows, total_winners)
    action_summary.to_csv(BY_ACTION, index=False)

    by_rank = build_group_table(signal_df, "rank_bucket_v1", RANK_BUCKET_ORDER, include_roi=False)
    by_rank.to_csv(BY_RANK, index=False)

    by_governance = build_group_table(signal_df, "governance_band_v1", GOVERNANCE_ORDER, include_roi=True)
    by_governance.to_csv(BY_GOVERNANCE, index=False)

    by_score_band = build_group_table(signal_df, "score_band_v1", SCORE_BAND_ORDER, include_roi=False)
    by_score_band.to_csv(BY_SCORE_BAND, index=False)

    false_positive = build_false_positive_audit(execute_df)
    false_positive.to_csv(FALSE_POSITIVE_AUDIT, index=False)

    summary_rows = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "total_races", "value": total_races},
        {"metric": "signals", "value": int(len(signal_df))},
        {"metric": "signal_rate", "value": safe_rate(len(signal_df), total_rows)},
        {"metric": "execute_count", "value": int(len(execute_df))},
        {"metric": "strong_watch_count", "value": int(len(strong_watch_df))},
        {"metric": "watch_count", "value": int(len(watch_df))},
        {"metric": "wins", "value": int(signal_df["won"].sum())},
        {"metric": "places", "value": int(signal_df["placed"].sum())},
        {"metric": "signal_win_rate", "value": safe_rate(signal_df["won"].sum(), len(signal_df))},
        {"metric": "signal_place_rate", "value": safe_rate(signal_df["placed"].sum(), len(signal_df))},
        {"metric": "execute_win_rate", "value": safe_rate(execute_df["won"].sum(), len(execute_df))},
        {"metric": "strong_watch_win_rate", "value": safe_rate(strong_watch_df["won"].sum(), len(strong_watch_df))},
        {"metric": "watch_win_rate", "value": safe_rate(watch_df["won"].sum(), len(watch_df))},
        {"metric": "winner_top1_capture", "value": safe_rate(((signal_df["won"] == 1) & (signal_df["runner_rank_signal_v1"] <= 1)).sum(), total_winners)},
        {"metric": "winner_top3_capture", "value": safe_rate(((signal_df["won"] == 1) & (signal_df["runner_rank_signal_v1"] <= 3)).sum(), total_winners)},
        {"metric": "winner_top5_capture", "value": safe_rate(((signal_df["won"] == 1) & (signal_df["runner_rank_signal_v1"] <= 5)).sum(), total_winners)},
        {"metric": "avg_finish", "value": float(signal_df["finish_position"].mean()) if len(signal_df) else math.nan},
        {"metric": "execute_place_rate", "value": safe_rate(execute_df["placed"].sum(), len(execute_df))},
        {"metric": "execute_avg_rank", "value": float(execute_df["runner_rank_signal_v1"].mean()) if len(execute_df) else math.nan},
        {"metric": "execute_avg_score", "value": float(execute_df["runner_score_signal_v1"].mean()) if len(execute_df) else math.nan},
        {"metric": "execute_roi_proxy", "value": roi_proxy(execute_df)},
        {"metric": "strong_watch_roi_proxy", "value": roi_proxy(strong_watch_df)},
        {"metric": "watch_roi_proxy", "value": roi_proxy(watch_df)},
        {"metric": "false_positive_execute_count", "value": int((execute_df["won"] != 1).sum())},
        {"metric": "false_positive_execute_rate", "value": safe_rate((execute_df["won"] != 1).sum(), len(execute_df))},
        {"metric": "filter_mode", "value": "historical_empirical_proxy_no_market"},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[EDGEIQ_HISTORICAL_SIGNAL_FILTER_REPLAY_V1] COMPLETE")
    print(f"rows={total_rows}")
    print(f"races={total_races}")
    print(f"signals={len(signal_df)}")
    print(f"execute_count={len(execute_df)}")
    print(f"strong_watch_count={len(strong_watch_df)}")
    print(f"watch_count={len(watch_df)}")
    print(f"signal_win_rate={safe_rate(signal_df['won'].sum(), len(signal_df)):.6f}")
    print(f"execute_win_rate={safe_rate(execute_df['won'].sum(), len(execute_df)):.6f}")
    print(f"summary_out={SUMMARY}")
    print(f"by_action_out={BY_ACTION}")
    print(f"false_positive_out={FALSE_POSITIVE_AUDIT}")


if __name__ == "__main__":
    main()
