from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

RUNNER_V6_PATH = DATA_DIR / "edgeiq_runner_score_v6.csv"
OVERLAY_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1.csv"
TRUST_PROFILE_LIVE_PATH = DATA_DIR / "edgeiq_trust_profile_live_audit_v1.csv"
TRUST_INDEX_PATH = DATA_DIR / "edgeiq_trust_index_v1.csv"
RANK_GAP_PATH = DATA_DIR / "edgeiq_rank_gap_engine_v1.csv"
DOMINANCE_PATH = DATA_DIR / "edgeiq_dominance_engine_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_execution_engine_v2_live.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_execution_engine_v2_live_summary.csv"
CANDIDATES_PATH = DATA_DIR / "edgeiq_execution_engine_v2_live_candidates.csv"

ACTION_PRIORITY = {
    "ELITE_EXECUTE": 1,
    "EXECUTE": 2,
    "STRONG_WATCH": 3,
    "WATCH": 4,
    "NO_BET": 5,
}

ACTION_PERMISSION = {
    "ELITE_EXECUTE": "FULL_EXECUTION",
    "EXECUTE": "REDUCED_EXECUTION",
    "STRONG_WATCH": "WATCH_ONLY",
    "WATCH": "WATCH_ONLY",
    "NO_BET": "NO_BET",
}

OUTPUT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "runner_rank_v6",
    "runner_score_v6",
    "trust_profile_v1",
    "trust_band_v1",
    "trust_index_v1",
    "score_share_band",
    "dominance_certainty_band",
    "empirical_fair_price_v1",
    "market_price_v1",
    "edge_pct_v1",
    "edge_band_v1",
    "execution_action_v2",
    "execution_permission_v2",
    "execution_reason_v2",
    "risk_flags_v2",
]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_text(value: object) -> str:
    text = clean_text(value)
    if text == "":
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " AND ")
    text = text.upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_race_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df[track_col].map(normalize_text) + "|" + race_no


def build_runner_key(
    df: pd.DataFrame,
    track_col: str = "track",
    horse_col: str = "horse",
    horse_key_col: str | None = None,
) -> pd.Series:
    if horse_key_col is not None and horse_key_col in df.columns:
        horse_component = df[horse_key_col].where(df[horse_key_col].fillna("").astype(str).str.strip().ne(""), df[horse_col])
    else:
        horse_component = df[horse_col]
    horse_component = horse_component.map(normalize_text)
    return build_race_key(df, track_col=track_col) + "|" + horse_component


def midpoint(a: float | None, b: float | None, fallback: float) -> float:
    if a is None and b is None:
        return fallback
    if a is None:
        return float(b)
    if b is None:
        return float(a)
    return (float(a) + float(b)) / 2.0


def infer_score_share_thresholds(rank_gap_df: pd.DataFrame) -> dict[str, float]:
    df = rank_gap_df.copy()
    df["score_share_total"] = to_num(df.get("score_share_total", pd.Series(dtype=float)))
    df["score_share_band"] = df.get("score_share_band", pd.Series(dtype=str)).fillna("").astype(str).str.upper()
    df = df[df["score_share_total"].notna() & df["score_share_band"].ne("")]

    low_values = df.loc[df["score_share_band"] == "LOW", "score_share_total"]
    medium_values = df.loc[df["score_share_band"] == "MEDIUM", "score_share_total"]
    high_values = df.loc[df["score_share_band"] == "HIGH", "score_share_total"]
    very_high_values = df.loc[df["score_share_band"] == "VERY_HIGH", "score_share_total"]

    low_max = float(low_values.max()) if not low_values.empty else None
    medium_min = float(medium_values.min()) if not medium_values.empty else None
    medium_max = float(medium_values.max()) if not medium_values.empty else None
    high_min = float(high_values.min()) if not high_values.empty else None
    high_max = float(high_values.max()) if not high_values.empty else None
    very_high_min = float(very_high_values.min()) if not very_high_values.empty else None

    return {
        "low_to_medium": midpoint(low_max, medium_min, 0.115),
        "medium_to_high": midpoint(medium_max, high_min, 0.18),
        "high_to_very_high": midpoint(high_max, very_high_min, 0.24),
    }


def classify_score_share_band(score_share: object, thresholds: dict[str, float]) -> str:
    value = pd.to_numeric(score_share, errors="coerce")
    if pd.isna(value):
        return "UNKNOWN"
    value = float(value)
    if value >= thresholds["high_to_very_high"]:
        return "VERY_HIGH"
    if value >= thresholds["medium_to_high"]:
        return "HIGH"
    if value >= thresholds["low_to_medium"]:
        return "MEDIUM"
    return "LOW"


def classify_dominance_band(score: object) -> str:
    value = pd.to_numeric(score, errors="coerce")
    if pd.isna(value):
        return "UNKNOWN"
    value = float(value)
    if value >= 80:
        return "VERY_HIGH"
    if value >= 65:
        return "HIGH"
    if value >= 50:
        return "MEDIUM"
    return "LOW"


def cap_action(action: str, cap_to: str) -> str:
    if ACTION_PRIORITY[action] < ACTION_PRIORITY[cap_to]:
        return cap_to
    return action


def determine_base_action(row: pd.Series) -> tuple[str, str]:
    trust_profile = clean_text(row.get("trust_profile_v1", "")).upper()
    dominance_band = clean_text(row.get("dominance_certainty_band", "")).upper()
    score_share_band = clean_text(row.get("score_share_band", "")).upper()
    rank = pd.to_numeric(row.get("runner_rank_v6"), errors="coerce")
    edge = pd.to_numeric(row.get("edge_pct_v1"), errors="coerce")
    market_valid = bool(row.get("market_valid_v1", False))
    scratched = bool(row.get("scratched_v1", False))

    rule_f_race = (
        trust_profile in {"ELITE", "STRONG"}
        and dominance_band in {"VERY_HIGH", "HIGH"}
        and score_share_band == "VERY_HIGH"
    )

    if rule_f_race and market_valid and not scratched and pd.notna(rank) and rank == 1 and pd.notna(edge) and edge > 0:
        return "ELITE_EXECUTE", "RULE_F_RANK1_OVERLAY"
    if rule_f_race and market_valid and not scratched and pd.notna(rank) and rank <= 3 and pd.notna(edge) and edge >= 10:
        return "EXECUTE", "RULE_F_TOP3_EDGE"
    if market_valid and not scratched and trust_profile != "CHAOTIC" and pd.notna(rank) and rank <= 5 and pd.notna(edge) and edge >= 10:
        return "STRONG_WATCH", "NON_CHAOTIC_TOP5_EDGE"
    if market_valid and not scratched and pd.notna(edge) and edge > 0:
        return "WATCH", "POSITIVE_OVERLAY_ONLY"
    return "NO_BET", "NO_EDGE"


def determine_final_action(row: pd.Series) -> tuple[str, str, str, str]:
    base_action, base_reason = determine_base_action(row)
    final_action = base_action
    final_reason = base_reason

    trust_profile = clean_text(row.get("trust_profile_v1", "")).upper()
    trust_index = pd.to_numeric(row.get("trust_index_v1"), errors="coerce")
    dominance_band = clean_text(row.get("dominance_certainty_band", "")).upper()
    score_share_band = clean_text(row.get("score_share_band", "")).upper()
    rank = pd.to_numeric(row.get("runner_rank_v6"), errors="coerce")
    edge = pd.to_numeric(row.get("edge_pct_v1"), errors="coerce")
    market_price = pd.to_numeric(row.get("market_price_v1"), errors="coerce")

    scratched = bool(row.get("scratched_v1", False))
    no_market = bool(row.get("no_market_v1", False))
    market_valid = bool(row.get("market_valid_v1", False))

    flags: list[str] = []
    if scratched:
        flags.append("SCRATCHED")
    if no_market:
        flags.append("NO_MARKET")
    if trust_profile == "CHAOTIC":
        flags.append("CHAOTIC_RACE")
    if pd.notna(trust_index) and float(trust_index) < 25:
        flags.append("LOW_TRUST_INDEX")
    if pd.notna(market_price) and float(market_price) > 101:
        flags.append("LONG_PRICE_CAP")
    if pd.notna(rank) and float(rank) > 5:
        flags.append("DEEP_RANK")
    if pd.notna(edge) and float(edge) <= 0:
        flags.append("NON_POSITIVE_EDGE")
    if dominance_band not in {"VERY_HIGH", "HIGH"}:
        flags.append("LOW_DOMINANCE_CERTAINTY")
    if score_share_band != "VERY_HIGH":
        flags.append("NOT_VERY_HIGH_SCORE_SHARE")
    if not market_valid and not no_market and not scratched:
        flags.append("INVALID_MARKET")

    if scratched:
        final_action = "NO_BET"
        final_reason = "SCRATCHED"
    elif no_market or not market_valid:
        final_action = "NO_BET"
        final_reason = "NO_MARKET"
    elif pd.notna(trust_index) and float(trust_index) < 25:
        final_action = "NO_BET"
        final_reason = "LOW_TRUST_INDEX"
    else:
        if trust_profile == "CHAOTIC" and final_action in {"ELITE_EXECUTE", "EXECUTE"}:
            final_action = "WATCH" if pd.notna(edge) and float(edge) > 0 else "NO_BET"
            final_reason = "CHAOTIC_RACE"
        if trust_profile == "CHAOTIC" and pd.notna(rank) and float(rank) > 3:
            final_action = "NO_BET"
            final_reason = "CHAOTIC_RACE"
        if pd.notna(market_price) and float(market_price) > 101:
            capped_action = cap_action(final_action, "WATCH")
            if capped_action != final_action:
                final_reason = "LONG_PRICE_CAP"
            final_action = capped_action
        if pd.notna(rank) and float(rank) > 5:
            capped_action = cap_action(final_action, "WATCH")
            if capped_action != final_action:
                final_reason = "DEEP_RANK"
            final_action = capped_action

        if final_action == "ELITE_EXECUTE":
            final_reason = "ELITE_RACE" if trust_profile == "ELITE" else "STRONG_RACE"
        elif final_action == "EXECUTE" and final_reason in {"RULE_F_TOP3_EDGE", "RULE_F_RANK1_OVERLAY"}:
            final_reason = "RULE_F_TOP3_EDGE"
        elif final_action == "STRONG_WATCH":
            final_reason = "STANDARD_RISK_REDUCTION" if trust_profile == "STANDARD" else "STRONG_WATCH_EDGE"
        elif final_action == "WATCH" and trust_profile == "CHAOTIC":
            final_reason = "CHAOTIC_RACE"

    permission = ACTION_PERMISSION[final_action]
    risk_flags = "|".join(dict.fromkeys(flags)) if flags else "CLEAN"
    return final_action, permission, final_reason, risk_flags


def format_pct(value: float) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.2f}%"


def main() -> None:
    overlay_df = pd.read_csv(OVERLAY_PATH, low_memory=False)
    runner_df = pd.read_csv(RUNNER_V6_PATH, low_memory=False)
    trust_profile_df = pd.read_csv(TRUST_PROFILE_LIVE_PATH, low_memory=False)
    trust_index_df = pd.read_csv(TRUST_INDEX_PATH, low_memory=False)
    rank_gap_df = pd.read_csv(RANK_GAP_PATH, low_memory=False)
    dominance_df = pd.read_csv(DOMINANCE_PATH, low_memory=False)

    score_share_thresholds = infer_score_share_thresholds(rank_gap_df)

    overlay_df = overlay_df.copy()
    overlay_df["meeting_date"] = overlay_df["meeting_date"].astype(str).str[:10]
    overlay_df["race_no"] = to_num(overlay_df["race_no"]).astype("Int64")
    overlay_df["race_join_key_v1"] = build_race_key(overlay_df)
    overlay_df["runner_join_key_v1"] = build_runner_key(overlay_df, horse_col="horse")
    overlay_df["runner_score_v6"] = to_num(overlay_df.get("runner_score_v6", pd.Series(dtype=float)))
    overlay_df["runner_rank_v6"] = to_num(overlay_df.get("runner_rank_v6", pd.Series(dtype=float)))
    overlay_df["empirical_fair_price_v1"] = to_num(overlay_df.get("empirical_fair_price_v1", pd.Series(dtype=float)))
    overlay_df["market_price_v1"] = to_num(overlay_df.get("market_price_v1", pd.Series(dtype=float)))
    overlay_df["edge_pct_v1"] = to_num(overlay_df.get("edge_pct_v1", pd.Series(dtype=float)))
    overlay_df["market_match_status_v1"] = overlay_df.get("market_match_status_v1", pd.Series(dtype=str)).fillna("").astype(str).map(clean_text)
    overlay_df["edge_band_v1"] = overlay_df.get("edge_band_v1", pd.Series(dtype=str)).fillna("").astype(str).map(clean_text)
    overlay_df["scratched_v1"] = overlay_df["market_match_status_v1"].str.upper().eq("SCRATCHED") | overlay_df["edge_band_v1"].str.upper().eq("SCRATCHED")
    overlay_df["no_market_v1"] = overlay_df["market_match_status_v1"].str.upper().eq("NO_MARKET") | (~overlay_df["scratched_v1"] & overlay_df["market_price_v1"].isna()) | (~overlay_df["scratched_v1"] & (overlay_df["market_price_v1"] <= 1))
    overlay_df["market_valid_v1"] = (~overlay_df["scratched_v1"]) & (~overlay_df["no_market_v1"]) & overlay_df["market_match_status_v1"].str.upper().eq("MATCHED") & overlay_df["market_price_v1"].gt(1)

    runner_df = runner_df.copy()
    runner_df["meeting_date"] = runner_df["meeting_date"].astype(str).str[:10]
    runner_df["race_no"] = to_num(runner_df["race_no"]).astype("Int64")
    runner_df["runner_join_key_v1"] = build_runner_key(runner_df, horse_col="horse", horse_key_col="horse_key")
    runner_lookup = runner_df[["runner_join_key_v1", "runner_score_v6", "runner_rank_v6"]].copy()
    runner_lookup["runner_score_v6"] = to_num(runner_lookup["runner_score_v6"])
    runner_lookup["runner_rank_v6"] = to_num(runner_lookup["runner_rank_v6"])
    runner_lookup = runner_lookup.drop_duplicates("runner_join_key_v1", keep="first")

    trust_profile_df = trust_profile_df.copy()
    trust_profile_df["meeting_date"] = trust_profile_df["meeting_date"].astype(str).str[:10]
    trust_profile_df["race_no"] = to_num(trust_profile_df["race_no"]).astype("Int64")
    trust_profile_df["race_join_key_v1"] = build_race_key(trust_profile_df)
    trust_profile_lookup = trust_profile_df[
        [
            "race_join_key_v1",
            "trust_profile_v1",
            "trust_band_v1",
            "trust_index_v1",
            "score_share_band",
            "field_size",
            "score_share_total_v6",
        ]
    ].copy()
    trust_profile_lookup["trust_profile_v1"] = trust_profile_lookup["trust_profile_v1"].fillna("").astype(str).map(clean_text)
    trust_profile_lookup["trust_band_v1"] = trust_profile_lookup["trust_band_v1"].fillna("").astype(str).map(clean_text)
    trust_profile_lookup["score_share_band"] = trust_profile_lookup["score_share_band"].fillna("").astype(str).map(clean_text)
    trust_profile_lookup["trust_index_v1"] = to_num(trust_profile_lookup["trust_index_v1"])
    trust_profile_lookup["field_size"] = to_num(trust_profile_lookup["field_size"])
    trust_profile_lookup["score_share_total_v6"] = to_num(trust_profile_lookup.get("score_share_total_v6", pd.Series(dtype=float)))
    trust_profile_lookup = trust_profile_lookup.drop_duplicates("race_join_key_v1", keep="first")

    trust_index_df = trust_index_df.copy()
    trust_index_df["meeting_date"] = trust_index_df["meeting_date"].astype(str).str[:10]
    trust_index_df["race_no"] = to_num(trust_index_df["race_no"]).astype("Int64")
    trust_index_df["race_join_key_v1"] = build_race_key(trust_index_df)
    trust_index_lookup = trust_index_df[["race_join_key_v1", "trust_index_v1", "trust_band_v1", "dominance_certainty_band"]].copy()
    trust_index_lookup["trust_index_v1"] = to_num(trust_index_lookup["trust_index_v1"])
    trust_index_lookup["trust_band_v1"] = trust_index_lookup["trust_band_v1"].fillna("").astype(str).map(clean_text)
    trust_index_lookup["dominance_certainty_band"] = trust_index_lookup["dominance_certainty_band"].fillna("").astype(str).map(clean_text)
    trust_index_lookup = trust_index_lookup.drop_duplicates("race_join_key_v1", keep="first")

    dominance_df = dominance_df.copy()
    dominance_df["meeting_date"] = dominance_df["meeting_date"].astype(str).str[:10]
    dominance_df["race_no"] = to_num(dominance_df["race_no"]).astype("Int64")
    dominance_df["race_join_key_v1"] = build_race_key(dominance_df)
    dominance_df["dominance_score_v1"] = to_num(dominance_df.get("dominance_score_v1", pd.Series(dtype=float)))
    dominance_df["score_share_of_race"] = to_num(dominance_df.get("score_share_of_race", pd.Series(dtype=float)))
    dominance_df["dominance_rank_v1"] = to_num(dominance_df.get("dominance_rank_v1", pd.Series(dtype=float)))
    dominance_top = dominance_df[dominance_df["dominance_rank_v1"] == 1].copy()
    if dominance_top.empty:
        dominance_top = dominance_df.sort_values(["race_join_key_v1", "dominance_score_v1"], ascending=[True, False]).drop_duplicates("race_join_key_v1", keep="first")
    dominance_top["dominance_certainty_band_fallback"] = dominance_top["dominance_score_v1"].map(classify_dominance_band)
    dominance_top["score_share_band_fallback"] = dominance_top["score_share_of_race"].map(lambda value: classify_score_share_band(value, score_share_thresholds))
    dominance_top_lookup = dominance_top[["race_join_key_v1", "dominance_certainty_band_fallback", "score_share_band_fallback"]].copy()
    dominance_top_lookup = dominance_top_lookup.drop_duplicates("race_join_key_v1", keep="first")

    live_df = overlay_df.merge(runner_lookup, on="runner_join_key_v1", how="left", suffixes=("", "_runner"))
    live_df = live_df.merge(trust_profile_lookup, on="race_join_key_v1", how="left", suffixes=("", "_profile"))
    live_df = live_df.merge(trust_index_lookup, on="race_join_key_v1", how="left", suffixes=("", "_trust"))
    live_df = live_df.merge(dominance_top_lookup, on="race_join_key_v1", how="left")

    live_df["runner_score_v6"] = live_df["runner_score_v6"].fillna(live_df.get("runner_score_v6_runner"))
    live_df["runner_rank_v6"] = live_df["runner_rank_v6"].fillna(live_df.get("runner_rank_v6_runner"))

    if "trust_profile_v1_profile" in live_df.columns:
        live_df["trust_profile_v1"] = live_df["trust_profile_v1_profile"].fillna(live_df.get("trust_profile_v1"))
    if "trust_band_v1_profile" in live_df.columns:
        live_df["trust_band_v1"] = live_df["trust_band_v1_profile"].fillna(live_df.get("trust_band_v1"))
    if "trust_index_v1_profile" in live_df.columns:
        live_df["trust_index_v1"] = live_df["trust_index_v1_profile"].fillna(live_df.get("trust_index_v1"))
    if "trust_index_v1_trust" in live_df.columns:
        live_df["trust_index_v1"] = live_df["trust_index_v1"].fillna(live_df["trust_index_v1_trust"])
    if "trust_band_v1_trust" in live_df.columns:
        live_df["trust_band_v1"] = live_df["trust_band_v1"].fillna(live_df["trust_band_v1_trust"])

    live_df["score_share_band"] = live_df.get("score_share_band", pd.Series(index=live_df.index, dtype=object)).fillna("").astype(str).map(clean_text)
    if "score_share_total_v6" in live_df.columns:
        live_df["score_share_band"] = live_df.apply(
            lambda row: row["score_share_band"] if clean_text(row["score_share_band"]) != "" else classify_score_share_band(row.get("score_share_total_v6"), score_share_thresholds),
            axis=1,
        )
    live_df["score_share_band"] = live_df.apply(
        lambda row: row["score_share_band"] if clean_text(row["score_share_band"]) != "" else clean_text(row.get("score_share_band_fallback", "UNKNOWN")),
        axis=1,
    )

    live_df["dominance_certainty_band"] = live_df.get("dominance_certainty_band", pd.Series(index=live_df.index, dtype=object)).fillna("").astype(str).map(clean_text)
    live_df["dominance_certainty_band"] = live_df.apply(
        lambda row: row["dominance_certainty_band"] if clean_text(row["dominance_certainty_band"]) != "" else clean_text(row.get("dominance_certainty_band_fallback", "UNKNOWN")),
        axis=1,
    )

    live_df["trust_profile_v1"] = live_df.get("trust_profile_v1", pd.Series(index=live_df.index, dtype=object)).fillna("UNKNOWN").astype(str).map(clean_text)
    live_df["trust_band_v1"] = live_df.get("trust_band_v1", pd.Series(index=live_df.index, dtype=object)).fillna("UNKNOWN").astype(str).map(clean_text)
    live_df["trust_index_v1"] = to_num(live_df.get("trust_index_v1", pd.Series(dtype=float)))

    classifications = live_df.apply(determine_final_action, axis=1, result_type="expand")
    classifications.columns = ["execution_action_v2", "execution_permission_v2", "execution_reason_v2", "risk_flags_v2"]
    live_df = pd.concat([live_df, classifications], axis=1)

    live_df["action_priority_v2"] = live_df["execution_action_v2"].map(ACTION_PRIORITY)
    live_df["candidate_flag_v2"] = live_df["execution_action_v2"].isin(["ELITE_EXECUTE", "EXECUTE", "STRONG_WATCH", "WATCH"])

    live_df["race_label_v2"] = live_df["meeting_date"].astype(str) + "|" + live_df["track"].astype(str) + "|R" + live_df["race_no"].astype(str)
    live_df = live_df.sort_values(["meeting_date", "track", "race_no", "runner_rank_v6", "horse"], kind="mergesort")

    output_df = live_df[OUTPUT_COLUMNS].copy()
    output_df.to_csv(OUTPUT_PATH, index=False)

    candidates_df = live_df[live_df["candidate_flag_v2"]].copy()
    candidates_df = candidates_df.sort_values(["action_priority_v2", "edge_pct_v1", "runner_rank_v6", "horse"], ascending=[True, False, True, True], kind="mergesort")
    candidates_df = candidates_df[OUTPUT_COLUMNS].copy()
    candidates_df.to_csv(CANDIDATES_PATH, index=False)

    race_action = live_df.groupby("race_join_key_v1", dropna=False)["action_priority_v2"].min().reset_index(name="best_action_priority")
    reverse_action = {priority: action for action, priority in ACTION_PRIORITY.items()}
    race_action["best_action"] = race_action["best_action_priority"].map(reverse_action)
    highest_action_priority = int(race_action["best_action_priority"].min()) if not race_action.empty else ACTION_PRIORITY["NO_BET"]
    highest_action_label = reverse_action[highest_action_priority]
    highest_action_race_count = int((race_action["best_action_priority"] == highest_action_priority).sum()) if not race_action.empty else 0

    chaotic_races = live_df.loc[live_df["trust_profile_v1"].str.upper() == "CHAOTIC", "race_join_key_v1"].nunique()
    scratched_count = int(live_df["scratched_v1"].sum())
    market_missing_count = int(live_df["no_market_v1"].sum())

    summary_rows = [
        {"metric": "rows", "value": int(len(live_df))},
        {"metric": "races", "value": int(live_df["race_join_key_v1"].nunique())},
        {"metric": "elite_execute_count", "value": int((live_df["execution_action_v2"] == "ELITE_EXECUTE").sum())},
        {"metric": "execute_count", "value": int((live_df["execution_action_v2"] == "EXECUTE").sum())},
        {"metric": "strong_watch_count", "value": int((live_df["execution_action_v2"] == "STRONG_WATCH").sum())},
        {"metric": "watch_count", "value": int((live_df["execution_action_v2"] == "WATCH").sum())},
        {"metric": "no_bet_count", "value": int((live_df["execution_action_v2"] == "NO_BET").sum())},
        {"metric": "market_missing_count", "value": market_missing_count},
        {"metric": "scratched_count", "value": scratched_count},
        {"metric": "chaotic_race_count", "value": int(chaotic_races)},
        {"metric": "highest_action_present", "value": highest_action_label},
        {"metric": "highest_action_race_count", "value": highest_action_race_count},
    ]
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    action_counts = (
        live_df.groupby("execution_action_v2", dropna=False)
        .size()
        .rename("runners")
        .reset_index()
        .sort_values("execution_action_v2", key=lambda series: series.map(ACTION_PRIORITY), kind="mergesort")
    )

    trust_counts = (
        live_df.groupby("trust_profile_v1", dropna=False)
        .size()
        .rename("runners")
        .reset_index()
        .sort_values("runners", ascending=False, kind="mergesort")
    )

    print("EDGEIQ Execution Engine V2 Live")
    print(summary_df.to_string(index=False))
    print("\nCounts By Action")
    print(action_counts.to_string(index=False))
    print("\nCounts By Trust Profile")
    print(trust_counts.to_string(index=False))
    print("\nTop Candidates")
    if candidates_df.empty:
        print("No live candidates passed the action filters.")
    else:
        preview_cols = [
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "execution_action_v2",
            "runner_rank_v6",
            "runner_score_v6",
            "trust_profile_v1",
            "dominance_certainty_band",
            "score_share_band",
            "empirical_fair_price_v1",
            "market_price_v1",
            "edge_pct_v1",
            "execution_reason_v2",
            "risk_flags_v2",
        ]
        print(candidates_df[preview_cols].to_string(index=False))


if __name__ == "__main__":
    main()
