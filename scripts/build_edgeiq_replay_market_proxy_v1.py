from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY = DATA / "edgeiq_historical_replay_v1.csv"
SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT = DATA / "edgeiq_replay_market_proxy_v1.csv"
SUMMARY = DATA / "edgeiq_replay_market_proxy_v1_summary.csv"
BY_RANK = DATA / "edgeiq_replay_expected_value_by_rank_v1.csv"
BY_SCORE = DATA / "edgeiq_replay_expected_value_by_score_band_v1.csv"
MONOTONICITY = DATA / "edgeiq_replay_monotonicity_audit_v1.csv"

RANK_ORDER = [
    "RANK_1",
    "RANK_2",
    "RANK_3",
    "RANK_4_5",
    "RANK_6_10",
    "RANK_11_PLUS",
]

SCORE_ORDER = [
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
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def upper_text(value: object) -> str:
    return clean_text(value).upper()


def canon_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value: object) -> str:
    text = upper_text(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"\s+", " ", text).strip()


def parse_float(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).replace("$", "").replace(",", "").replace("kg", "").strip()
    if text == "":
        return np.nan
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return np.nan
    try:
        return float(match.group(0))
    except ValueError:
        return np.nan


def rank_bucket(value: object) -> str:
    rank_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(rank_value):
        return "NO_RANK"
    rank_int = int(rank_value)
    if rank_int == 1:
        return "RANK_1"
    if rank_int == 2:
        return "RANK_2"
    if rank_int == 3:
        return "RANK_3"
    if rank_int <= 5:
        return "RANK_4_5"
    if rank_int <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def score_band(value: object) -> str:
    score_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(score_value):
        return "UNKNOWN"
    if score_value < 40:
        return "LT_40"
    if score_value < 45:
        return "40_44"
    if score_value < 50:
        return "45_49"
    if score_value < 55:
        return "50_54"
    if score_value < 60:
        return "55_59"
    if score_value < 65:
        return "60_64"
    if score_value < 70:
        return "65_69"
    if score_value < 75:
        return "70_74"
    if score_value < 80:
        return "75_79"
    return "80_PLUS"


def empirical_fair_odds(win_rate: float) -> float:
    if pd.isna(win_rate) or win_rate <= 0:
        return np.nan
    return 1.0 / win_rate


def biased_implied_probability(avg_sp: float) -> float:
    if pd.isna(avg_sp) or avg_sp <= 1:
        return np.nan
    return 1.0 / avg_sp


def prepare_replay(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["meeting_date"] = out["meeting_date"].astype(str).str.slice(0, 10)
    out["track_norm_join"] = out["track_norm"].where(
        out.get("track_norm", "").fillna("").astype(str).str.strip().ne(""),
        out["track"].map(norm_track),
    ) if "track_norm" in out.columns else out["track"].map(norm_track)
    out["race_no_join"] = pd.to_numeric(out["race_no"], errors="coerce").astype("Int64")
    out["horse_join"] = out["horse_key"].where(
        out.get("horse_key", "").fillna("").astype(str).str.strip().ne(""),
        out["horse"].map(canon_horse),
    ) if "horse_key" in out.columns else out["horse"].map(canon_horse)
    out["rank_bucket"] = out["runner_rank"].map(rank_bucket)
    out["score_band"] = out["runner_score"].map(score_band)
    out["won"] = pd.to_numeric(out["won"], errors="coerce").fillna(0).astype(int)
    out["finish_position"] = pd.to_numeric(out["finish_position"], errors="coerce")
    return out


def prepare_settled(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["meeting_date"] = out["meeting_date"].astype(str).str.slice(0, 10)
    out["track_norm_join"] = out["track_norm_join"].where(
        out.get("track_norm_join", "").fillna("").astype(str).str.strip().ne(""),
        out["track"].map(norm_track),
    ) if "track_norm_join" in out.columns else out["track"].map(norm_track)
    out["race_no_join"] = pd.to_numeric(out["race_no_join"], errors="coerce").astype("Int64") if "race_no_join" in out.columns else pd.to_numeric(out["race_no"], errors="coerce").astype("Int64")
    out["horse_join"] = out["horse_join"].where(
        out.get("horse_join", "").fillna("").astype(str).str.strip().ne(""),
        out["horse"].map(canon_horse),
    ) if "horse_join" in out.columns else out["horse"].map(canon_horse)
    if "sp_settled" not in out.columns:
        out["sp_settled"] = out["sp"] if "sp" in out.columns else ""
    out["sp_num_settled"] = out["sp_settled"].map(parse_float)
    out["biased_sp_valid"] = out["sp_num_settled"].gt(1)
    return out


def build_proxy_table(df: pd.DataFrame, group_col: str, output_col: str) -> pd.DataFrame:
    work = df.copy()
    grouped = (
        work.groupby(group_col, dropna=False)
        .agg(
            runners=(group_col, "count"),
            races=("race_key", "nunique"),
            wins=("won", "sum"),
            true_win_rate=("won", "mean"),
            biased_sp_rows=("biased_sp_valid", "sum"),
            biased_avg_sp=("sp_num_settled", lambda s: s[s.gt(1)].mean()),
        )
        .reset_index()
        .rename(columns={group_col: output_col})
    )
    grouped["empirical_fair_odds"] = grouped["true_win_rate"].map(empirical_fair_odds)
    grouped["biased_sp_implied_prob"] = grouped["biased_avg_sp"].map(biased_implied_probability)
    grouped["implied_edge_vs_biased_sp"] = grouped["true_win_rate"] - grouped["biased_sp_implied_prob"]
    for col in [
        "true_win_rate",
        "empirical_fair_odds",
        "biased_avg_sp",
        "biased_sp_implied_prob",
        "implied_edge_vs_biased_sp",
    ]:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce").round(4)
    grouped["biased_sp_rows"] = grouped["biased_sp_rows"].fillna(0).astype(int)
    grouped["runners"] = grouped["runners"].fillna(0).astype(int)
    grouped["races"] = grouped["races"].fillna(0).astype(int)
    grouped["wins"] = grouped["wins"].fillna(0).astype(int)
    return grouped


def build_monotonicity_rows(table: pd.DataFrame, label_col: str, order: list[str], direction: str, dimension: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    win_rate_map = {str(row[label_col]): pd.to_numeric(row["true_win_rate"], errors="coerce") for _, row in table.iterrows()}

    checked = 0
    passed = 0
    first_value = np.nan
    last_value = np.nan

    for idx in range(len(order) - 1):
        left = order[idx]
        right = order[idx + 1]
        left_rate = win_rate_map.get(left, np.nan)
        right_rate = win_rate_map.get(right, np.nan)
        if pd.isna(left_rate) or pd.isna(right_rate):
            status = "SKIP"
            pass_flag = np.nan
        else:
            checked += 1
            if pd.isna(first_value):
                first_value = left_rate
            last_value = right_rate
            if direction == "descending":
                condition = left_rate > right_rate
            else:
                condition = right_rate > left_rate
            pass_flag = bool(condition)
            passed += int(condition)
            status = "PASS" if condition else "FAIL"
        rows.append(
            {
                "dimension": dimension,
                "comparison_type": "adjacent",
                "from_bucket": left,
                "to_bucket": right,
                "from_true_win_rate": round(float(left_rate), 4) if not pd.isna(left_rate) else np.nan,
                "to_true_win_rate": round(float(right_rate), 4) if not pd.isna(right_rate) else np.nan,
                "delta": round(float(right_rate - left_rate), 4) if not pd.isna(left_rate) and not pd.isna(right_rate) else np.nan,
                "expected_direction": direction,
                "status": status,
                "pass_flag": pass_flag,
            }
        )

    strict_pass = checked > 0 and passed == checked
    pass_rate = (passed / checked) if checked else np.nan
    if dimension == "score_band":
        general_pass = bool((checked > 0) and (pass_rate >= 0.75) and (not pd.isna(first_value)) and (not pd.isna(last_value)) and (last_value > first_value))
    else:
        general_pass = strict_pass

    rows.append(
        {
            "dimension": dimension,
            "comparison_type": "overall",
            "from_bucket": order[0] if order else "",
            "to_bucket": order[-1] if order else "",
            "from_true_win_rate": round(float(first_value), 4) if not pd.isna(first_value) else np.nan,
            "to_true_win_rate": round(float(last_value), 4) if not pd.isna(last_value) else np.nan,
            "delta": round(float(last_value - first_value), 4) if not pd.isna(first_value) and not pd.isna(last_value) else np.nan,
            "expected_direction": direction,
            "status": "PASS" if strict_pass else "FAIL",
            "pass_flag": strict_pass,
            "checked_pairs": checked,
            "passed_pairs": passed,
            "pass_rate": round(float(pass_rate), 4) if not pd.isna(pass_rate) else np.nan,
            "general_improvement_pass": general_pass,
        }
    )
    return rows


def main() -> None:
    if not REPLAY.exists():
        raise FileNotFoundError(f"Missing replay input: {REPLAY}")
    if not SETTLED.exists():
        raise FileNotFoundError(f"Missing settled replay input: {SETTLED}")

    replay = prepare_replay(pd.read_csv(REPLAY, low_memory=False))
    settled = prepare_settled(pd.read_csv(SETTLED, low_memory=False))

    settled_keep = (
        settled[["meeting_date", "track_norm_join", "race_no_join", "horse_join", "sp_settled", "sp_num_settled", "biased_sp_valid"]]
        .sort_values(["meeting_date", "track_norm_join", "race_no_join", "horse_join", "biased_sp_valid"], ascending=[True, True, True, True, False])
        .drop_duplicates(["meeting_date", "track_norm_join", "race_no_join", "horse_join"], keep="first")
    )

    merged = replay.merge(
        settled_keep,
        on=["meeting_date", "track_norm_join", "race_no_join", "horse_join"],
        how="left",
    )

    merged["sp_settled"] = merged["sp_settled"].fillna("")
    merged["sp_num_settled"] = pd.to_numeric(merged["sp_num_settled"], errors="coerce")
    merged["biased_sp_valid"] = merged["biased_sp_valid"].fillna(False).astype(bool)
    merged["governance"] = merged.get("projection_status_v6", "UNKNOWN").fillna("UNKNOWN").astype(str).str.strip().replace("", "UNKNOWN")

    by_rank = build_proxy_table(merged, "rank_bucket", "rank_bucket")
    by_score = build_proxy_table(merged, "score_band", "score_band")

    by_rank["_sort"] = by_rank["rank_bucket"].map({name: idx for idx, name in enumerate(RANK_ORDER, start=1)}).fillna(999).astype(int)
    by_score["_sort"] = by_score["score_band"].map({name: idx for idx, name in enumerate(SCORE_ORDER, start=1)}).fillna(999).astype(int)

    by_rank = by_rank.sort_values(["_sort", "rank_bucket"]).drop(columns=["_sort"])
    by_score = by_score.sort_values(["_sort", "score_band"]).drop(columns=["_sort"])

    monotonicity_rows = []
    monotonicity_rows.extend(build_monotonicity_rows(by_rank, "rank_bucket", RANK_ORDER, "descending", "rank_bucket"))
    monotonicity_rows.extend(build_monotonicity_rows(by_score, "score_band", SCORE_ORDER, "ascending", "score_band"))
    monotonicity = pd.DataFrame(monotonicity_rows)

    rank_overall = monotonicity[(monotonicity["dimension"] == "rank_bucket") & (monotonicity["comparison_type"] == "overall")].head(1)
    score_overall = monotonicity[(monotonicity["dimension"] == "score_band") & (monotonicity["comparison_type"] == "overall")].head(1)

    summary = pd.DataFrame(
        [
            {"metric": "replay_rows", "value": len(merged)},
            {"metric": "replay_races", "value": merged["race_key"].nunique()},
            {"metric": "biased_sp_rows", "value": int(merged["biased_sp_valid"].sum())},
            {"metric": "biased_sp_coverage", "value": round(float(merged["biased_sp_valid"].mean()), 4)},
            {"metric": "rank_monotonic_strict", "value": bool(rank_overall["pass_flag"].iloc[0]) if len(rank_overall) else False},
            {"metric": "rank_monotonic_pass_rate", "value": round(float(rank_overall["pass_rate"].iloc[0]), 4) if len(rank_overall) and pd.notna(rank_overall["pass_rate"].iloc[0]) else np.nan},
            {"metric": "score_monotonic_strict", "value": bool(score_overall["pass_flag"].iloc[0]) if len(score_overall) else False},
            {"metric": "score_monotonic_general", "value": bool(score_overall["general_improvement_pass"].iloc[0]) if len(score_overall) else False},
            {"metric": "score_monotonic_pass_rate", "value": round(float(score_overall["pass_rate"].iloc[0]), 4) if len(score_overall) and pd.notna(score_overall["pass_rate"].iloc[0]) else np.nan},
        ]
    )

    rank_map = by_rank.set_index("rank_bucket")
    score_map = by_score.set_index("score_band")

    merged["rank_true_win_rate_v1"] = merged["rank_bucket"].map(rank_map["true_win_rate"]) if not by_rank.empty else np.nan
    merged["rank_empirical_fair_odds_v1"] = merged["rank_bucket"].map(rank_map["empirical_fair_odds"]) if not by_rank.empty else np.nan
    merged["rank_biased_avg_sp_v1"] = merged["rank_bucket"].map(rank_map["biased_avg_sp"]) if not by_rank.empty else np.nan
    merged["rank_implied_edge_vs_biased_sp_v1"] = merged["rank_bucket"].map(rank_map["implied_edge_vs_biased_sp"]) if not by_rank.empty else np.nan
    merged["score_true_win_rate_v1"] = merged["score_band"].map(score_map["true_win_rate"]) if not by_score.empty else np.nan
    merged["score_empirical_fair_odds_v1"] = merged["score_band"].map(score_map["empirical_fair_odds"]) if not by_score.empty else np.nan
    merged["score_biased_avg_sp_v1"] = merged["score_band"].map(score_map["biased_avg_sp"]) if not by_score.empty else np.nan
    merged["score_implied_edge_vs_biased_sp_v1"] = merged["score_band"].map(score_map["implied_edge_vs_biased_sp"]) if not by_score.empty else np.nan

    merged.to_csv(OUT, index=False)
    summary.to_csv(SUMMARY, index=False)
    by_rank.to_csv(BY_RANK, index=False)
    by_score.to_csv(BY_SCORE, index=False)
    monotonicity.to_csv(MONOTONICITY, index=False)

    print("[EDGEIQ_REPLAY_MARKET_PROXY_V1] COMPLETE")
    print(f"replay_rows={len(merged)}")
    print(f"replay_races={merged['race_key'].nunique()}")
    print(f"biased_sp_rows={int(merged['biased_sp_valid'].sum())}")
    print(f"biased_sp_coverage={round(float(merged['biased_sp_valid'].mean()), 4)}")
    if len(rank_overall):
        print(f"rank_monotonic_strict={bool(rank_overall['pass_flag'].iloc[0])}")
        print(f"rank_monotonic_pass_rate={round(float(rank_overall['pass_rate'].iloc[0]), 4)}")
    if len(score_overall):
        print(f"score_monotonic_strict={bool(score_overall['pass_flag'].iloc[0])}")
        print(f"score_monotonic_general={bool(score_overall['general_improvement_pass'].iloc[0])}")
        print(f"score_monotonic_pass_rate={round(float(score_overall['pass_rate'].iloc[0]), 4)}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")
    print(f"by_rank={BY_RANK}")
    print(f"by_score={BY_SCORE}")
    print(f"monotonicity={MONOTONICITY}")


if __name__ == "__main__":
    main()
