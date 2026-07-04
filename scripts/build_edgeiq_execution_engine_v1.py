from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ELITE_OVERLAY_REPLAY_PATH = DATA / "edgeiq_elite_overlay_replay_v1.csv"
ELITE_EXECUTION_REPLAY_PATH = DATA / "edgeiq_elite_execution_replay_v1.csv"
TRUST_PROFILE_ENGINE_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"
RANK_GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
HISTORICAL_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"

OUT_PATH = DATA / "edgeiq_execution_engine_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_execution_engine_v1_summary.csv"
BY_ACTION_OUT = DATA / "edgeiq_execution_engine_v1_by_action.csv"
BY_RANK_OUT = DATA / "edgeiq_execution_engine_v1_by_rank.csv"
BY_TRUST_PROFILE_OUT = DATA / "edgeiq_execution_engine_v1_by_trust_profile.csv"

ACTION_ORDER = ["ELITE_EXECUTE", "EXECUTE", "WATCH", "NO_BET"]
RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
TRUST_PROFILE_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC", "UNKNOWN"]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse_key(value: object, fallback: object = "") -> str:
    raw = clean_text(value)
    if raw == "":
        raw = clean_text(fallback)
    return re.sub(r"[^A-Z0-9]+", "", raw.upper())


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_join_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, track_col: str = "track", horse_key_col: str = "horse_key", horse_col: str = "horse") -> pd.Series:
    horse_component = [normalize_horse_key(horse_key, horse) for horse_key, horse in zip(df[horse_key_col], df[horse_col])]
    return build_join_key(df, track_col=track_col) + "|" + pd.Series(horse_component, index=df.index)


def first_valid_text(values: pd.Series, default: str = "") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def action_priority(action: str) -> int:
    if action == "ELITE_EXECUTE":
        return 1
    if action == "EXECUTE":
        return 2
    if action == "WATCH":
        return 3
    return 4


def classify_action(row: pd.Series) -> tuple[str, str]:
    elite_flag = clean_text(row.get("elite_execution_flag", "")).upper() == "TRUE"
    rank = pd.to_numeric(row.get("runner_rank"), errors="coerce")
    edge = pd.to_numeric(row.get("edge_proxy_pct"), errors="coerce")
    positive_overlay = pd.notna(edge) and edge > 0

    if elite_flag and pd.notna(rank) and rank == 1 and positive_overlay:
        return "ELITE_EXECUTE", "RULE_F_RANK1_POSITIVE_OVERLAY"
    if elite_flag and pd.notna(rank) and rank <= 3 and positive_overlay:
        return "EXECUTE", "RULE_F_TOP3_POSITIVE_OVERLAY"
    if positive_overlay:
        return "WATCH", "POSITIVE_OVERLAY_OUTSIDE_RULE_F_EXECUTE"
    return "NO_BET", "NO_POSITIVE_OVERLAY"


def load_elite_overlay_replay() -> pd.DataFrame:
    if not ELITE_OVERLAY_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing elite overlay replay file: {ELITE_OVERLAY_REPLAY_PATH}")

    df = pd.read_csv(ELITE_OVERLAY_REPLAY_PATH, low_memory=False)
    text_cols = [
        "meeting_date",
        "track",
        "horse",
        "rank_bucket",
        "score_band",
        "trust_profile_v1",
        "execution_class_v1",
        "dominance_certainty_band",
        "score_share_band",
        "overlay_band",
        "elite_execution_flag",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)

    numeric_cols = [
        "race_no",
        "runner_rank",
        "runner_score",
        "field_size",
        "finish_position",
        "won",
        "placed",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "market_proxy_fair_odds",
        "edge_proxy_pct",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])

    if "horse_key" in df.columns:
        df["horse_key"] = df["horse_key"].fillna("").astype(str).map(clean_text)
    else:
        df["horse_key"] = ""

    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    return df.copy()


def load_historical_replay_backfill() -> pd.DataFrame:
    if not HISTORICAL_REPLAY_PATH.exists():
        return pd.DataFrame(columns=["runner_join_key_v1", "finish_position_backfill", "won_backfill", "placed_backfill"])

    usecols = ["meeting_date", "track", "race_no", "horse", "horse_key", "finish_position", "won"]
    df = pd.read_csv(HISTORICAL_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse", "horse_key"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "finish_position", "won"]:
        df[col] = to_num(df[col])
    df["placed_backfill"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    return df[["runner_join_key_v1", "finish_position", "won", "placed_backfill"]].rename(
        columns={
            "finish_position": "finish_position_backfill",
            "won": "won_backfill",
        }
    ).copy()


def load_execution_replay_backfill() -> pd.DataFrame:
    if not ELITE_EXECUTION_REPLAY_PATH.exists():
        return pd.DataFrame(columns=["join_key_v1", "trust_index_v1", "trust_band_v1", "trust_profile_score_v1", "trust_profile_v1", "race_execution_class_v1"])

    df = pd.read_csv(ELITE_EXECUTION_REPLAY_PATH, low_memory=False)
    text_cols = [
        "meeting_date",
        "track",
        "join_key_v1",
        "trust_band_v1",
        "trust_profile_v1",
        "race_execution_class_v1",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)
    numeric_cols = ["race_no", "trust_index_v1", "trust_profile_score_v1"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])
    if "join_key_v1" not in df.columns or df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)
    return df[[
        "join_key_v1",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "race_execution_class_v1",
    ]].drop_duplicates(subset=["join_key_v1"]).copy()


def load_rank_gap_backfill() -> pd.DataFrame:
    if not RANK_GAP_ENGINE_PATH.exists():
        return pd.DataFrame(columns=["join_key_v1", "score_share_band"])

    usecols = ["meeting_date", "track", "race_no", "join_key_v1", "score_share_band"]
    df = pd.read_csv(RANK_GAP_ENGINE_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "join_key_v1", "score_share_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    df["race_no"] = to_num(df["race_no"])
    if df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)
    return df[["join_key_v1", "score_share_band"]].drop_duplicates(subset=["join_key_v1"]).copy()


def load_trust_profile_catalog() -> pd.DataFrame:
    if not TRUST_PROFILE_ENGINE_PATH.exists():
        return pd.DataFrame(columns=["trust_profile_v1"])
    df = pd.read_csv(TRUST_PROFILE_ENGINE_PATH, low_memory=False, usecols=["trust_profile_v1"])
    df["trust_profile_v1"] = df["trust_profile_v1"].fillna("").astype(str).map(clean_text)
    return df.drop_duplicates().reset_index(drop=True)


def prepare_execution_frame() -> pd.DataFrame:
    overlay_df = load_elite_overlay_replay()
    replay_backfill_df = load_historical_replay_backfill()
    execution_backfill_df = load_execution_replay_backfill()
    rank_gap_backfill_df = load_rank_gap_backfill()
    _trust_catalog_df = load_trust_profile_catalog()

    df = overlay_df.merge(replay_backfill_df, on="runner_join_key_v1", how="left")
    df = df.merge(execution_backfill_df, on="join_key_v1", how="left", suffixes=("", "_exec"))
    df = df.merge(rank_gap_backfill_df, on="join_key_v1", how="left", suffixes=("", "_gap"))

    df["finish_position"] = to_num(df["finish_position"]).fillna(to_num(df.get("finish_position_backfill")))
    df["won"] = to_num(df["won"]).fillna(to_num(df.get("won_backfill"))).fillna(0).astype(int)
    df["placed"] = to_num(df["placed"]).fillna(to_num(df.get("placed_backfill"))).fillna(df["finish_position"].le(3)).astype(int)
    df["trust_index_v1"] = to_num(df.get("trust_index_v1")).fillna(to_num(df.get("trust_index_v1_exec")))
    df["trust_profile_score_v1"] = to_num(df.get("trust_profile_score_v1")).fillna(to_num(df.get("trust_profile_score_v1_exec")))

    for base_col, fill_col in [
        ("trust_band_v1", "trust_band_v1_exec"),
        ("trust_profile_v1", "trust_profile_v1_exec"),
        ("execution_class_v1", "race_execution_class_v1"),
        ("score_share_band", "score_share_band_gap"),
    ]:
        if fill_col in df.columns:
            df[base_col] = df[base_col].replace("", pd.NA)
            df[base_col] = df[base_col].fillna(df[fill_col])
        df[base_col] = df[base_col].fillna("UNKNOWN")

    action_cols = df.apply(classify_action, axis=1, result_type="expand")
    df["execution_action_v1"] = action_cols[0]
    df["execution_action_reason_v1"] = action_cols[1]
    df["execution_action_sort_v1"] = df["execution_action_v1"].map({name: idx for idx, name in enumerate(ACTION_ORDER, start=1)}).fillna(999)

    race_summary = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            has_elite_execute_v1=("execution_action_v1", lambda s: int((s.astype(str) == "ELITE_EXECUTE").any())),
            has_execute_v1=("execution_action_v1", lambda s: int((s.astype(str) == "EXECUTE").any())),
            has_watch_v1=("execution_action_v1", lambda s: int((s.astype(str) == "WATCH").any())),
        )
        .reset_index()
    )

    def race_signal_bucket(row: pd.Series) -> str:
        if int(row["has_elite_execute_v1"]) == 1:
            return "ELITE_EXECUTE"
        if int(row["has_execute_v1"]) == 1:
            return "EXECUTE"
        if int(row["has_watch_v1"]) == 1:
            return "WATCH_ONLY"
        return "NO_SIGNAL"

    race_summary["race_signal_bucket_v1"] = race_summary.apply(race_signal_bucket, axis=1)
    df = df.merge(race_summary[["join_key_v1", "race_signal_bucket_v1"]], on="join_key_v1", how="left")

    keep_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_rank",
        "runner_score",
        "rank_bucket",
        "score_band",
        "finish_position",
        "won",
        "placed",
        "trust_profile_v1",
        "trust_band_v1",
        "trust_index_v1",
        "execution_class_v1",
        "dominance_certainty_band",
        "score_share_band",
        "edge_proxy_pct",
        "overlay_band",
        "elite_execution_flag",
        "execution_action_v1",
        "execution_action_reason_v1",
        "race_signal_bucket_v1",
        "join_key_v1",
        "runner_join_key_v1",
        "execution_action_sort_v1",
    ]
    out_df = df[keep_cols].copy()
    out_df = out_df.sort_values(
        ["execution_action_sort_v1", "meeting_date", "track", "race_no", "runner_rank", "runner_score", "horse"],
        ascending=[True, True, True, True, True, False, True],
    ).reset_index(drop=True)
    return out_df


def summarise_bucket(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            runners=("horse", "size"),
            races=("join_key_v1", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("finish_position", "mean"),
            avg_rank=("runner_rank", "mean"),
            avg_score=("runner_score", "mean"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["runners"]
    grouped["place_rate"] = grouped["places"] / grouped["runners"]
    return grouped


def build_by_action(df: pd.DataFrame) -> pd.DataFrame:
    grouped = summarise_bucket(df, ["execution_action_v1"])
    grouped["action_sort_v1"] = grouped["execution_action_v1"].map({name: idx for idx, name in enumerate(ACTION_ORDER, start=1)}).fillna(999)
    grouped = grouped.sort_values(["action_sort_v1", "execution_action_v1"]).drop(columns=["action_sort_v1"]).reset_index(drop=True)
    return grouped[["execution_action_v1", "runners", "races", "wins", "places", "win_rate", "place_rate", "avg_finish", "avg_rank", "avg_score", "avg_edge_proxy_pct"]].copy()


def build_by_rank(df: pd.DataFrame) -> pd.DataFrame:
    grouped = summarise_bucket(df, ["execution_action_v1", "rank_bucket"])
    grouped["action_sort_v1"] = grouped["execution_action_v1"].map({name: idx for idx, name in enumerate(ACTION_ORDER, start=1)}).fillna(999)
    grouped["rank_sort_v1"] = grouped["rank_bucket"].map({name: idx for idx, name in enumerate(RANK_BUCKET_ORDER, start=1)}).fillna(999)
    grouped = grouped.sort_values(["action_sort_v1", "rank_sort_v1", "execution_action_v1"]).drop(columns=["action_sort_v1", "rank_sort_v1"]).reset_index(drop=True)
    return grouped[["execution_action_v1", "rank_bucket", "runners", "races", "wins", "places", "win_rate", "place_rate", "avg_finish", "avg_rank", "avg_score", "avg_edge_proxy_pct"]].copy()


def build_by_trust_profile(df: pd.DataFrame) -> pd.DataFrame:
    grouped = summarise_bucket(df, ["execution_action_v1", "trust_profile_v1"])
    grouped["action_sort_v1"] = grouped["execution_action_v1"].map({name: idx for idx, name in enumerate(ACTION_ORDER, start=1)}).fillna(999)
    grouped["trust_sort_v1"] = grouped["trust_profile_v1"].map({name: idx for idx, name in enumerate(TRUST_PROFILE_ORDER, start=1)}).fillna(999)
    grouped = grouped.sort_values(["action_sort_v1", "trust_sort_v1", "execution_action_v1"]).drop(columns=["action_sort_v1", "trust_sort_v1"]).reset_index(drop=True)
    return grouped[["execution_action_v1", "trust_profile_v1", "runners", "races", "wins", "places", "win_rate", "place_rate", "avg_finish", "avg_rank", "avg_score", "avg_edge_proxy_pct"]].copy()


def build_summary(df: pd.DataFrame, by_action_df: pd.DataFrame) -> pd.DataFrame:
    total_rows = int(len(df))
    total_races = int(df["join_key_v1"].nunique())

    action_lookup = by_action_df.set_index("execution_action_v1") if not by_action_df.empty else pd.DataFrame()

    def metric_from_action(action: str, metric: str) -> float:
        if isinstance(action_lookup, pd.DataFrame) and action in action_lookup.index:
            return action_lookup.at[action, metric]
        return math.nan

    race_bucket_counts = df[["join_key_v1", "race_signal_bucket_v1"]].drop_duplicates().groupby("race_signal_bucket_v1").size().to_dict()

    rows = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "total_races", "value": total_races},
        {"metric": "elite_execute_count", "value": int(metric_from_action("ELITE_EXECUTE", "runners")) if pd.notna(metric_from_action("ELITE_EXECUTE", "runners")) else 0},
        {"metric": "execute_count", "value": int(metric_from_action("EXECUTE", "runners")) if pd.notna(metric_from_action("EXECUTE", "runners")) else 0},
        {"metric": "watch_count", "value": int(metric_from_action("WATCH", "runners")) if pd.notna(metric_from_action("WATCH", "runners")) else 0},
        {"metric": "no_bet_count", "value": int(metric_from_action("NO_BET", "runners")) if pd.notna(metric_from_action("NO_BET", "runners")) else 0},
        {"metric": "elite_execute_win_rate", "value": metric_from_action("ELITE_EXECUTE", "win_rate")},
        {"metric": "elite_execute_place_rate", "value": metric_from_action("ELITE_EXECUTE", "place_rate")},
        {"metric": "execute_win_rate", "value": metric_from_action("EXECUTE", "win_rate")},
        {"metric": "execute_place_rate", "value": metric_from_action("EXECUTE", "place_rate")},
        {"metric": "watch_win_rate", "value": metric_from_action("WATCH", "win_rate")},
        {"metric": "watch_place_rate", "value": metric_from_action("WATCH", "place_rate")},
        {"metric": "races_with_elite_execute", "value": int(race_bucket_counts.get("ELITE_EXECUTE", 0))},
        {"metric": "races_with_execute", "value": int(race_bucket_counts.get("EXECUTE", 0))},
        {"metric": "races_with_watch_only", "value": int(race_bucket_counts.get("WATCH_ONLY", 0))},
        {"metric": "races_no_signal", "value": int(race_bucket_counts.get("NO_SIGNAL", 0))},
    ]
    return pd.DataFrame(rows)


def main() -> None:
    df = prepare_execution_frame()
    by_action_df = build_by_action(df)
    by_rank_df = build_by_rank(df)
    by_trust_profile_df = build_by_trust_profile(df)
    summary_df = build_summary(df, by_action_df)

    out_df = df.drop(columns=["execution_action_sort_v1"]).copy()
    out_df.to_csv(OUT_PATH, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    by_action_df.to_csv(BY_ACTION_OUT, index=False)
    by_rank_df.to_csv(BY_RANK_OUT, index=False)
    by_trust_profile_df.to_csv(BY_TRUST_PROFILE_OUT, index=False)

    print("[EDGEIQ_EXECUTION_ENGINE_V1] COMPLETE")
    print(f"output={OUT_PATH}")
    print(f"summary={SUMMARY_OUT}")
    print(f"by_action={BY_ACTION_OUT}")
    print(f"by_rank={BY_RANK_OUT}")
    print(f"by_trust_profile={BY_TRUST_PROFILE_OUT}")
    print(f"rows={len(out_df)}")
    print(f"races={out_df['join_key_v1'].nunique()}")


if __name__ == "__main__":
    main()
