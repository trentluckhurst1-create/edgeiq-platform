from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_SCORES = DATA / "edgeiq_historical_runner_scores_v1.csv"
HISTORICAL_DOMINANCE_V1 = DATA / "edgeiq_historical_dominance_replay_v1.csv"

ENGINE_V2_OUT = DATA / "edgeiq_dominance_engine_v2.csv"
HISTORICAL_REPLAY_V2_OUT = DATA / "edgeiq_historical_dominance_v2_replay.csv"
SUMMARY_V2_OUT = DATA / "edgeiq_historical_dominance_v2_summary.csv"

MODELS = {
    "MODEL_A_RUNNER_ONLY": {"runner_weight": 1.0, "dominance_weight": 0.0},
    "MODEL_B_DOMINANCE_ONLY": {"runner_weight": 0.0, "dominance_weight": 1.0},
    "MODEL_C_BLEND_50_50": {"runner_weight": 0.5, "dominance_weight": 0.5},
    "MODEL_D_BLEND_70_30": {"runner_weight": 0.7, "dominance_weight": 0.3},
    "MODEL_E_BLEND_30_70": {"runner_weight": 0.3, "dominance_weight": 0.7},
}
MODEL_ORDER = list(MODELS.keys())
CERTAINTY_BAND_ORDER = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]


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


def to_float(value: object) -> float:
    if value is None or pd.isna(value):
        return math.nan
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else math.nan
    text = str(value).replace("$", "").replace(",", "").strip()
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


def certainty_band(value: object) -> str:
    score = to_float(value)
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 80:
        return "VERY_HIGH"
    if score >= 65:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def empirical_cdf(reference: pd.Series, values: pd.Series) -> pd.Series:
    ref = pd.to_numeric(reference, errors="coerce").dropna().to_numpy(dtype=float)
    if ref.size == 0:
        return pd.Series(np.nan, index=values.index)
    ref = np.sort(ref.copy())
    arr = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    out = np.full(arr.shape, np.nan, dtype=float)
    mask = np.isfinite(arr)
    if mask.any():
        out[mask] = np.searchsorted(ref, arr[mask], side="right") / ref.size
    return pd.Series(out, index=values.index)


def format_model_set(models: list[str]) -> str:
    ordered = [model for model in MODEL_ORDER if model in set(models)]
    if len(ordered) == 1:
        return ordered[0]
    return "TIE::" + "|".join(ordered)


def load_historical_scores() -> pd.DataFrame:
    if not HISTORICAL_SCORES.exists():
        raise FileNotFoundError(f"Missing historical scores file: {HISTORICAL_SCORES}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "finish_position",
        "won",
        "placed",
        "field_size",
        "governance_band_hist_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]
    df = pd.read_csv(HISTORICAL_SCORES, low_memory=False, usecols=usecols)
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["horse"] = df["horse"].fillna("")
    df["horse_key"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["placed"] = pd.to_numeric(df["placed"], errors="coerce").fillna(0).astype(int)
    df["field_size_v1"] = pd.to_numeric(df["field_size"], errors="coerce")
    df["governance_band_hist_v1"] = df["governance_band_hist_v1"].fillna("UNKNOWN").astype(str)
    df["runner_score_hist_v1"] = pd.to_numeric(df["runner_score_hist_v1"], errors="coerce")
    df["runner_rank_hist_v1"] = pd.to_numeric(df["runner_rank_hist_v1"], errors="coerce")
    return df.copy()


def load_dominance_v1() -> pd.DataFrame:
    if not HISTORICAL_DOMINANCE_V1.exists():
        raise FileNotFoundError(f"Missing historical dominance replay file: {HISTORICAL_DOMINANCE_V1}")

    df = pd.read_csv(HISTORICAL_DOMINANCE_V1, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["horse"] = df["horse"].fillna("")
    df["horse_key"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    numeric_cols = [
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "race_avg_score_v1",
        "race_total_score_v1",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_of_race",
        "dominance_score_v1",
        "dominance_rank_v1",
        "dominance_percentile",
        "finish_position",
        "won",
        "placed",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "governance_band_hist_v1" in df.columns:
        df["governance_band_hist_v1"] = df["governance_band_hist_v1"].fillna("UNKNOWN").astype(str)
    else:
        df["governance_band_hist_v1"] = "UNKNOWN"
    return df.copy()


def build_base_dataframe() -> pd.DataFrame:
    hist_scores = load_historical_scores()
    dom_v1 = load_dominance_v1()

    hist_subset = hist_scores[[
        "race_key",
        "horse_key",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "finish_position",
        "won",
        "placed",
        "field_size_v1",
        "governance_band_hist_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]].copy()

    df = dom_v1.merge(
        hist_subset,
        on=["race_key", "horse_key"],
        how="outer",
        suffixes=("", "_histsrc"),
    )

    for col in ["meeting_date", "track", "race_no", "horse"]:
        df[col] = df[col].combine_first(df[f"{col}_histsrc"])

    for col in [
        "finish_position",
        "won",
        "placed",
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]:
        df[col] = df[col].combine_first(df[f"{col}_histsrc"])

    df["governance_band_hist_v1"] = df["governance_band_hist_v1"].combine_first(df["governance_band_hist_v1_histsrc"])
    df["governance_band_hist_v1"] = df["governance_band_hist_v1"].fillna("UNKNOWN").astype(str)

    drop_cols = [col for col in df.columns if col.endswith("_histsrc")]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    numeric_cols = [
        "finish_position",
        "won",
        "placed",
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "race_avg_score_v1",
        "race_total_score_v1",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_of_race",
        "dominance_score_v1",
        "dominance_rank_v1",
        "dominance_percentile",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["horse"] = df["horse"].fillna("")
    df["horse_key"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["placed"] = pd.to_numeric(df["placed"], errors="coerce").fillna(0).astype(int)
    df["field_size_v1"] = df["field_size_v1"].fillna(df.groupby("race_key")["horse"].transform("size"))

    return df.copy()


def add_v2_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    race_avg_dom = df.groupby("race_key", dropna=False)["dominance_score_v1"].transform("mean")
    df["race_average_dominance_v1"] = race_avg_dom
    df["dominance_strength_ratio"] = np.where(
        race_avg_dom.ne(0) & race_avg_dom.notna(),
        df["dominance_score_v1"] / race_avg_dom,
        np.nan,
    )
    df["dominance_gap_rank2_pct"] = np.where(
        df["score_rank_2"].ne(0) & df["score_rank_2"].notna(),
        (df["score_rank_1"] - df["score_rank_2"]) / df["score_rank_2"],
        np.nan,
    )
    df["dominance_gap_rank3_pct"] = np.where(
        df["score_rank_3"].ne(0) & df["score_rank_3"].notna(),
        (df["score_rank_1"] - df["score_rank_3"]) / df["score_rank_3"],
        np.nan,
    )

    race_gap_reference = (
        df[["race_key", "dominance_gap_rank2_pct", "dominance_gap_rank3_pct"]]
        .drop_duplicates(subset=["race_key"])
        .copy()
    )
    df["dominance_strength_ratio_scaled_v1"] = empirical_cdf(df["dominance_strength_ratio"], df["dominance_strength_ratio"])
    race_gap_reference["dominance_gap_rank2_pct_scaled_v1"] = empirical_cdf(
        race_gap_reference["dominance_gap_rank2_pct"],
        race_gap_reference["dominance_gap_rank2_pct"],
    )
    race_gap_reference["dominance_gap_rank3_pct_scaled_v1"] = empirical_cdf(
        race_gap_reference["dominance_gap_rank3_pct"],
        race_gap_reference["dominance_gap_rank3_pct"],
    )
    df = df.merge(
        race_gap_reference[["race_key", "dominance_gap_rank2_pct_scaled_v1", "dominance_gap_rank3_pct_scaled_v1"]],
        on="race_key",
        how="left",
    )
    df["dominance_certainty_score_v1"] = (
        100.0
        * (
            0.50 * df["dominance_strength_ratio_scaled_v1"]
            + 0.30 * df["dominance_gap_rank2_pct_scaled_v1"]
            + 0.20 * df["dominance_gap_rank3_pct_scaled_v1"]
        )
    ).round(3)
    df["dominance_certainty_v1"] = df["dominance_certainty_score_v1"].apply(certainty_band)
    return df


def add_model_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["runner_score_component_v1"] = (100.0 * empirical_cdf(df["runner_score_hist_v1"], df["runner_score_hist_v1"])).round(6)
    df["dominance_component_v1"] = (100.0 * empirical_cdf(df["dominance_score_v1"], df["dominance_score_v1"])).round(6)

    for model_name, config in MODELS.items():
        score_col = f"{model_name.lower()}_score_v1"
        rank_col = f"{model_name.lower()}_rank_v1"
        order_col = f"{model_name.lower()}_order_v1"
        df[score_col] = (
            (config["runner_weight"] * df["runner_score_component_v1"])
            + (config["dominance_weight"] * df["dominance_component_v1"])
        ).round(6)

        ranked = df[["race_key", "horse_key", "horse", score_col, "dominance_score_v1", "runner_score_hist_v1"]].copy()
        ranked["orig_index_v1"] = ranked.index
        ranked = ranked.sort_values(
            ["race_key", score_col, "dominance_score_v1", "runner_score_hist_v1", "horse"],
            ascending=[True, False, False, False, True],
        ).reset_index(drop=True)
        ranked[order_col] = ranked.groupby("race_key").cumcount() + 1
        ranked[rank_col] = pd.Series(ranked[order_col], index=ranked.index, dtype="Int64")
        ranked = ranked.set_index("orig_index_v1")
        df[order_col] = ranked.loc[df.index, order_col].astype("Int64")
        df[rank_col] = ranked.loc[df.index, rank_col].astype("Int64")

    return df


def extract_model_metrics(df: pd.DataFrame, rank_col: str) -> dict[str, float]:
    winners = df[df["won"].eq(1)].copy()
    ranks = pd.to_numeric(winners[rank_col], errors="coerce")
    return {
        "Top1": float(ranks.le(1).mean()),
        "Top3": float(ranks.le(3).mean()),
        "Top5": float(ranks.le(5).mean()),
        "Top10": float(ranks.le(10).mean()),
        "avg_winner_rank": float(ranks.mean()),
        "winner_rows": int(len(winners)),
    }


def compute_disagreement_stats(df: pd.DataFrame) -> dict[str, object]:
    rank_cols = [f"{model.lower()}_rank_v1" for model in MODEL_ORDER]
    base_col = rank_cols[0]
    disagreement_mask = pd.Series(False, index=df.index)
    for rank_col in rank_cols[1:]:
        disagreement_mask = disagreement_mask | df[rank_col].ne(df[base_col])

    rows_with_any_disagreement = int(disagreement_mask.sum())
    races_with_any_disagreement = int(df.loc[disagreement_mask, "race_key"].nunique()) if rows_with_any_disagreement > 0 else 0
    all_models_identical_rankings = rows_with_any_disagreement == 0

    top_pick_frames = []
    for model_name in MODEL_ORDER:
        rank_col = f"{model_name.lower()}_rank_v1"
        top_frame = df.loc[df[rank_col].eq(1), ["race_key", "horse_key"]].copy()
        top_frame = top_frame.rename(columns={"horse_key": model_name})
        top_pick_frames.append(top_frame)

    top_pick_compare = top_pick_frames[0]
    for frame in top_pick_frames[1:]:
        top_pick_compare = top_pick_compare.merge(frame, on="race_key", how="inner")

    top_pick_cols = [col for col in top_pick_compare.columns if col != "race_key"]
    top_pick_disagreement_mask = pd.Series(False, index=top_pick_compare.index)
    first_top_col = top_pick_cols[0]
    for col in top_pick_cols[1:]:
        top_pick_disagreement_mask = top_pick_disagreement_mask | top_pick_compare[col].ne(top_pick_compare[first_top_col])

    races_with_top_pick_disagreement = int(top_pick_disagreement_mask.sum())
    top_pick_agreement_rate = 1.0 - (races_with_top_pick_disagreement / max(len(top_pick_compare), 1))

    return {
        "all_models_identical_rankings_v1": all_models_identical_rankings,
        "rows_with_any_rank_disagreement_v1": rows_with_any_disagreement,
        "races_with_any_rank_disagreement_v1": races_with_any_disagreement,
        "races_with_top_pick_disagreement_v1": races_with_top_pick_disagreement,
        "top_pick_agreement_rate_v1": top_pick_agreement_rate,
    }


def infer_dominance_role(best_metric_models: list[str], disagreement_stats: dict[str, object]) -> str:
    if bool(disagreement_stats["all_models_identical_rankings_v1"]):
        return "EQUIVALENT_ORDERING"
    if best_metric_models == ["MODEL_B_DOMINANCE_ONLY"]:
        return "PRIMARY"
    if any(model in {"MODEL_C_BLEND_50_50", "MODEL_D_BLEND_70_30", "MODEL_E_BLEND_30_70"} for model in best_metric_models):
        return "SUPPORTING"
    if best_metric_models == ["MODEL_A_RUNNER_ONLY"]:
        return "SECONDARY"
    return "MIXED"


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    model_metrics: dict[str, dict[str, float]] = {}

    for model_name, config in MODELS.items():
        rank_col = f"{model_name.lower()}_rank_v1"
        metrics = extract_model_metrics(df, rank_col)
        model_metrics[model_name] = metrics
        rows.append(
            {
                "section": "MODEL_COMPARISON",
                "model": model_name,
                "certainty_band": "",
                "runner_score_weight_v1": config["runner_weight"],
                "dominance_weight_v1": config["dominance_weight"],
                "top1_rows": np.nan,
                "wins": np.nan,
                "top1_win_rate": np.nan,
                "Top1": metrics["Top1"],
                "Top3": metrics["Top3"],
                "Top5": metrics["Top5"],
                "Top10": metrics["Top10"],
                "avg_winner_rank": metrics["avg_winner_rank"],
                "metric": "",
                "value": np.nan,
            }
        )

    compare_df = pd.DataFrame(rows)
    metric_preferences = {
        "Top1": True,
        "Top3": True,
        "Top5": True,
        "Top10": True,
        "avg_winner_rank": False,
    }
    best_counts = {model_name: 0 for model_name in MODEL_ORDER}
    for metric_name, higher_is_better in metric_preferences.items():
        metric_series = compare_df.set_index("model")[metric_name]
        if higher_is_better:
            best_value = metric_series.max()
            winners = metric_series[metric_series.eq(best_value)].index.tolist()
        else:
            best_value = metric_series.min()
            winners = metric_series[metric_series.eq(best_value)].index.tolist()
        for model_name in winners:
            best_counts[model_name] += 1

    top1_series = compare_df.set_index("model")["Top1"]
    best_top1_models = top1_series[top1_series.eq(top1_series.max())].index.tolist()

    max_metric_wins = max(best_counts.values())
    best_metric_models = [model for model in MODEL_ORDER if best_counts[model] == max_metric_wins]

    disagreement_stats = compute_disagreement_stats(df)
    dominance_role = infer_dominance_role(best_metric_models, disagreement_stats)

    overall_rows = [
        {"metric": "best_model_by_top1", "value": format_model_set(best_top1_models)},
        {"metric": "best_model_by_metric_count", "value": format_model_set(best_metric_models)},
        {"metric": "dominance_role_inference_v1", "value": dominance_role},
        {"metric": "all_models_identical_rankings_v1", "value": disagreement_stats["all_models_identical_rankings_v1"]},
        {"metric": "rows_with_any_rank_disagreement_v1", "value": disagreement_stats["rows_with_any_rank_disagreement_v1"]},
        {"metric": "races_with_any_rank_disagreement_v1", "value": disagreement_stats["races_with_any_rank_disagreement_v1"]},
        {"metric": "races_with_top_pick_disagreement_v1", "value": disagreement_stats["races_with_top_pick_disagreement_v1"]},
        {"metric": "top_pick_agreement_rate_v1", "value": disagreement_stats["top_pick_agreement_rate_v1"]},
    ]
    for model_name in MODEL_ORDER:
        overall_rows.append({"metric": f"metric_win_count::{model_name}", "value": best_counts[model_name]})

    for item in overall_rows:
        rows.append(
            {
                "section": "OVERALL",
                "model": "",
                "certainty_band": "",
                "runner_score_weight_v1": np.nan,
                "dominance_weight_v1": np.nan,
                "top1_rows": np.nan,
                "wins": np.nan,
                "top1_win_rate": np.nan,
                "Top1": np.nan,
                "Top3": np.nan,
                "Top5": np.nan,
                "Top10": np.nan,
                "avg_winner_rank": np.nan,
                "metric": item["metric"],
                "value": item["value"],
            }
        )

    for model_name, config in MODELS.items():
        rank_col = f"{model_name.lower()}_rank_v1"
        top_picks = df[df[rank_col].eq(1)].copy()
        grouped = (
            top_picks.groupby("dominance_certainty_v1", dropna=False)
            .agg(
                top1_rows=("horse", "size"),
                wins=("won", "sum"),
            )
            .reset_index()
        )
        grouped["top1_win_rate"] = grouped["wins"] / grouped["top1_rows"]
        grouped["sort_order"] = grouped["dominance_certainty_v1"].map(
            {value: idx for idx, value in enumerate(CERTAINTY_BAND_ORDER, start=1)}
        ).fillna(999)
        grouped = grouped.sort_values(["sort_order", "dominance_certainty_v1"]).drop(columns=["sort_order"])

        for row in grouped.itertuples(index=False):
            rows.append(
                {
                    "section": "TOP1_WIN_RATE_BY_CERTAINTY_BAND",
                    "model": model_name,
                    "certainty_band": row.dominance_certainty_v1,
                    "runner_score_weight_v1": config["runner_weight"],
                    "dominance_weight_v1": config["dominance_weight"],
                    "top1_rows": row.top1_rows,
                    "wins": row.wins,
                    "top1_win_rate": row.top1_win_rate,
                    "Top1": np.nan,
                    "Top3": np.nan,
                    "Top5": np.nan,
                    "Top10": np.nan,
                    "avg_winner_rank": np.nan,
                    "metric": "",
                    "value": np.nan,
                }
            )

    summary = pd.DataFrame(rows)
    return summary


def build_output_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "governance_band_hist_v1",
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "dominance_score_v1",
        "dominance_rank_v1",
        "dominance_percentile",
        "race_average_dominance_v1",
        "dominance_strength_ratio",
        "dominance_gap_rank2_pct",
        "dominance_gap_rank3_pct",
        "dominance_certainty_score_v1",
        "dominance_certainty_v1",
        "runner_score_component_v1",
        "dominance_component_v1",
    ]
    for model_name in MODEL_ORDER:
        lower = model_name.lower()
        engine_cols.extend([
            f"{lower}_score_v1",
            f"{lower}_order_v1",
            f"{lower}_rank_v1",
        ])
    engine_cols.extend([
        "finish_position",
        "won",
        "placed",
    ])
    engine_df = df[engine_cols].copy()

    replay_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "governance_band_hist_v1",
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "dominance_score_v1",
        "dominance_strength_ratio",
        "dominance_gap_rank2_pct",
        "dominance_gap_rank3_pct",
        "dominance_certainty_score_v1",
        "dominance_certainty_v1",
    ]
    for model_name in MODEL_ORDER:
        lower = model_name.lower()
        replay_cols.extend([
            f"{lower}_score_v1",
            f"{lower}_rank_v1",
        ])
    replay_cols.extend([
        "finish_position",
        "won",
        "placed",
    ])
    replay_df = df[replay_cols].copy()
    return engine_df, replay_df


def main() -> None:
    df = build_base_dataframe()
    df = add_v2_features(df)
    df = add_model_scores(df)

    engine_df, replay_df = build_output_tables(df)
    summary_df = build_summary(df)

    engine_df.to_csv(ENGINE_V2_OUT, index=False)
    replay_df.to_csv(HISTORICAL_REPLAY_V2_OUT, index=False)
    summary_df.to_csv(SUMMARY_V2_OUT, index=False)

    compare_rows = summary_df[summary_df["section"] == "MODEL_COMPARISON"].copy()
    overall_rows = summary_df[summary_df["section"] == "OVERALL"].copy()
    overall_map = dict(zip(overall_rows["metric"], overall_rows["value"]))
    best_top1_value = float(compare_rows["Top1"].max())
    best_top3_value = float(compare_rows["Top3"].max())
    best_top5_value = float(compare_rows["Top5"].max())
    best_top10_value = float(compare_rows["Top10"].max())
    best_avg_rank_value = float(compare_rows["avg_winner_rank"].min())

    print("[EDGEIQ_DOMINANCE_ENGINE_V2] COMPLETE")
    print(f"rows={len(df)}")
    print(f"races={df['race_key'].nunique()}")
    print(f"best_model_by_top1={overall_map.get('best_model_by_top1', '')}")
    print(f"best_model_by_metric_count={overall_map.get('best_model_by_metric_count', '')}")
    print(f"dominance_role_inference_v1={overall_map.get('dominance_role_inference_v1', '')}")
    print(f"all_models_identical_rankings_v1={overall_map.get('all_models_identical_rankings_v1', '')}")
    print(f"top_pick_agreement_rate_v1={overall_map.get('top_pick_agreement_rate_v1', '')}")
    print(f"best_model_top1={best_top1_value:.6f}")
    print(f"best_model_top3={best_top3_value:.6f}")
    print(f"best_model_top5={best_top5_value:.6f}")
    print(f"best_model_top10={best_top10_value:.6f}")
    print(f"best_model_avg_winner_rank={best_avg_rank_value:.6f}")
    print(f"engine_out={ENGINE_V2_OUT}")
    print(f"replay_out={HISTORICAL_REPLAY_V2_OUT}")
    print(f"summary_out={SUMMARY_V2_OUT}")


if __name__ == "__main__":
    main()
