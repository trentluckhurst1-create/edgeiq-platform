from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_SCORE_V6_PATH = DATA / "edgeiq_runner_score_v6.csv"
TRUST_PROFILE_LIVE_AUDIT_PATH = DATA / "edgeiq_trust_profile_live_audit_v1.csv"
TRUST_INDEX_PATH = DATA / "edgeiq_trust_index_v1.csv"
SIGNAL_FILTER_PATH = DATA / "edgeiq_empirical_signal_filter_v1.csv"

OUT_PATH = DATA / "edgeiq_execution_governance_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_execution_governance_v1_summary.csv"

PERMISSION_ORDER = ["FULL_EXECUTION", "REDUCED_EXECUTION", "WATCH_ONLY", "NO_BET"]
PROFILE_BASE_PERMISSION = {
    "ELITE": "FULL_EXECUTION",
    "STRONG": "FULL_EXECUTION",
    "STANDARD": "REDUCED_EXECUTION",
    "CHAOTIC": "WATCH_ONLY",
}
PROFILE_REASON = {
    "ELITE": "ELITE_RACE",
    "STRONG": "STRONG_RACE",
    "STANDARD": "STANDARD_RISK_REDUCTION",
    "CHAOTIC": "CHAOTIC_RACE",
}
PERMISSION_RANK = {name: idx for idx, name in enumerate(PERMISSION_ORDER)}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_race_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, track_col: str = "track", horse_col: str = "horse") -> pd.Series:
    return build_race_key(df, track_col=track_col) + "|" + df[horse_col].map(normalize_horse)


def downgrade_permission(permission: str) -> str:
    current_rank = PERMISSION_RANK.get(permission, len(PERMISSION_ORDER) - 1)
    downgraded_rank = min(current_rank + 1, len(PERMISSION_ORDER) - 1)
    return PERMISSION_ORDER[downgraded_rank]


def load_runner_scores() -> pd.DataFrame:
    if not RUNNER_SCORE_V6_PATH.exists():
        raise FileNotFoundError(f"Missing runner score v6 file: {RUNNER_SCORE_V6_PATH}")

    usecols = ["meeting_date", "track", "race_no", "horse", "runner_rank_v6", "runner_score_v6"]
    df = pd.read_csv(RUNNER_SCORE_V6_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_rank_v6", "runner_score_v6"]:
        df[col] = to_num(df[col])
    df["race_join_key_v1"] = build_race_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    return df.copy()


def load_trust_profile_live_audit() -> pd.DataFrame:
    if not TRUST_PROFILE_LIVE_AUDIT_PATH.exists():
        raise FileNotFoundError(f"Missing trust profile live audit file: {TRUST_PROFILE_LIVE_AUDIT_PATH}")

    usecols = ["meeting_date", "track", "race_no", "trust_profile_v1"]
    df = pd.read_csv(TRUST_PROFILE_LIVE_AUDIT_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "trust_profile_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    df["race_no"] = to_num(df["race_no"])
    df["race_join_key_v1"] = build_race_key(df)
    df = df.drop_duplicates(subset=["race_join_key_v1"]).reset_index(drop=True)
    return df[["race_join_key_v1", "trust_profile_v1"]].copy()


def load_trust_index() -> pd.DataFrame:
    if not TRUST_INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing trust index file: {TRUST_INDEX_PATH}")

    usecols = ["meeting_date", "track", "race_no", "trust_band_v1", "trust_index_v1"]
    df = pd.read_csv(TRUST_INDEX_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "trust_band_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "trust_index_v1"]:
        df[col] = to_num(df[col])
    df["race_join_key_v1"] = build_race_key(df)
    df = df.drop_duplicates(subset=["race_join_key_v1"]).reset_index(drop=True)
    return df[["race_join_key_v1", "trust_band_v1", "trust_index_v1"]].copy()


def load_signal_filter() -> pd.DataFrame:
    if not SIGNAL_FILTER_PATH.exists():
        raise FileNotFoundError(f"Missing empirical signal filter file: {SIGNAL_FILTER_PATH}")

    usecols = ["track", "race_no", "horse", "action", "edge_pct"]
    df = pd.read_csv(SIGNAL_FILTER_PATH, low_memory=False, usecols=usecols)
    for col in ["track", "horse", "action"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "edge_pct"]:
        df[col] = to_num(df[col])
    df["runner_join_key_v1"] = build_runner_key(df)
    df = df.drop_duplicates(subset=["runner_join_key_v1"]).reset_index(drop=True)
    df = df.rename(columns={"action": "current_signal_action"})
    return df[["runner_join_key_v1", "current_signal_action", "edge_pct"]].copy()


def determine_execution(row: pd.Series) -> tuple[str, str]:
    trust_profile = clean_text(row.get("trust_profile_v1", "")).upper()
    runner_rank = to_num(pd.Series([row.get("runner_rank_v6")])).iloc[0]
    trust_index = to_num(pd.Series([row.get("trust_index_v1")])).iloc[0]

    permission = PROFILE_BASE_PERMISSION.get(trust_profile, "NO_BET")
    reasons: list[str] = [PROFILE_REASON.get(trust_profile, "UNKNOWN_PROFILE")]

    if not pd.isna(runner_rank) and runner_rank > 5:
        permission = downgrade_permission(permission)
        reasons.append("DEEP_RANK")

    if not pd.isna(trust_index) and trust_index < 25:
        permission = "NO_BET"
        reasons.append("LOW_TRUST_INDEX")

    if trust_profile == "CHAOTIC" and not pd.isna(runner_rank) and runner_rank > 3:
        permission = "NO_BET"
        if "CHAOTIC_RACE" not in reasons:
            reasons.append("CHAOTIC_RACE")

    unique_reasons: list[str] = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)

    return permission, "|".join(unique_reasons)


def build_summary(execution_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    overall_metrics = {
        "runners": int(len(execution_df)),
        "races": int(execution_df["race_join_key_v1"].nunique()),
        "full_execution_count": int(execution_df["execution_permission_v1"].eq("FULL_EXECUTION").sum()),
        "reduced_execution_count": int(execution_df["execution_permission_v1"].eq("REDUCED_EXECUTION").sum()),
        "watch_only_count": int(execution_df["execution_permission_v1"].eq("WATCH_ONLY").sum()),
        "no_bet_count": int(execution_df["execution_permission_v1"].eq("NO_BET").sum()),
    }
    for metric, value in overall_metrics.items():
        rows.append({
            "section": "OVERALL",
            "metric": metric,
            "value": value,
            "execution_permission_v1": "",
            "rank_within_execution_v1": "",
            "track": "",
            "race_no": "",
            "horse": "",
            "runner_rank_v6": "",
            "runner_score_v6": "",
            "edge_pct": "",
            "current_signal_action": "",
        })

    top_candidates = execution_df.copy()
    top_candidates["edge_sort_v1"] = top_candidates["edge_pct"].fillna(-999999.0)
    top_candidates = top_candidates.sort_values(
        ["execution_permission_sort_v1", "runner_rank_v6", "runner_score_v6", "edge_sort_v1", "track", "race_no", "horse"],
        ascending=[True, True, False, False, True, True, True],
    )

    for permission in PERMISSION_ORDER:
        subset = top_candidates[top_candidates["execution_permission_v1"].eq(permission)].head(3).reset_index(drop=True)
        for idx, row in subset.iterrows():
            rows.append({
                "section": "TOP_RUNNERS_BY_EXECUTION",
                "metric": "top_runner",
                "value": "",
                "execution_permission_v1": permission,
                "rank_within_execution_v1": idx + 1,
                "track": row["track"],
                "race_no": int(row["race_no"]),
                "horse": row["horse"],
                "runner_rank_v6": int(row["runner_rank_v6"]) if not pd.isna(row["runner_rank_v6"]) else "",
                "runner_score_v6": float(row["runner_score_v6"]) if not pd.isna(row["runner_score_v6"]) else "",
                "edge_pct": float(row["edge_pct"]) if not pd.isna(row["edge_pct"]) else "",
                "current_signal_action": row["current_signal_action"],
            })

    return pd.DataFrame(rows)


def main() -> None:
    runner_df = load_runner_scores()
    trust_profile_df = load_trust_profile_live_audit()
    trust_index_df = load_trust_index()
    signal_df = load_signal_filter()

    execution_df = runner_df.merge(trust_profile_df, on="race_join_key_v1", how="left")
    execution_df = execution_df.merge(trust_index_df, on="race_join_key_v1", how="left")
    execution_df = execution_df.merge(signal_df, on="runner_join_key_v1", how="left")

    execution_df["trust_profile_v1"] = execution_df["trust_profile_v1"].fillna("UNKNOWN")
    execution_df["trust_band_v1"] = execution_df["trust_band_v1"].fillna("UNKNOWN")
    execution_df["current_signal_action"] = execution_df["current_signal_action"].fillna("NO_SIGNAL")

    execution_results = execution_df.apply(determine_execution, axis=1, result_type="expand")
    execution_df["execution_permission_v1"] = execution_results[0]
    execution_df["execution_reason_v1"] = execution_results[1]
    execution_df["execution_permission_sort_v1"] = execution_df["execution_permission_v1"].map(PERMISSION_RANK).fillna(999)

    execution_df = execution_df[[
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_rank_v6",
        "runner_score_v6",
        "trust_profile_v1",
        "trust_band_v1",
        "trust_index_v1",
        "edge_pct",
        "current_signal_action",
        "execution_permission_v1",
        "execution_reason_v1",
        "race_join_key_v1",
        "runner_join_key_v1",
        "execution_permission_sort_v1",
    ]].copy()

    execution_df = execution_df.sort_values(
        ["execution_permission_sort_v1", "runner_rank_v6", "runner_score_v6", "edge_pct", "track", "race_no", "horse"],
        ascending=[True, True, False, False, True, True, True],
    ).reset_index(drop=True)

    summary_df = build_summary(execution_df)

    execution_df.to_csv(OUT_PATH, index=False)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_EXECUTION_GOVERNANCE_V1] COMPLETE")
    print(f"output={OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")
    print(f"runners={len(execution_df)}")
    print(f"races={execution_df['race_join_key_v1'].nunique()}")
    print(f"full_execution_count={int(execution_df['execution_permission_v1'].eq('FULL_EXECUTION').sum())}")
    print(f"reduced_execution_count={int(execution_df['execution_permission_v1'].eq('REDUCED_EXECUTION').sum())}")
    print(f"watch_only_count={int(execution_df['execution_permission_v1'].eq('WATCH_ONLY').sum())}")
    print(f"no_bet_count={int(execution_df['execution_permission_v1'].eq('NO_BET').sum())}")


if __name__ == "__main__":
    main()
