from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import math
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

CORE_DETAIL_PATH = DATA_DIR / "edgeiq_v6_1_probability_calibration_v2_by_match_tier_detail.csv"
OVERLAY_PATH = DATA_DIR / "edgeiq_v6_1_overlay_replay_v1.csv"
DNA_PATH = DATA_DIR / "edgeiq_runner_dna_v6_3_historical_replay_v1.csv"
BET_QUALITY_PATH = DATA_DIR / "edgeiq_bet_quality_engine_v1_1.csv"
LIVE_BOARD_PATH = DATA_DIR / "edgeiq_live_runner_board_v1.csv"
LIVE_TRACK_PATH = DATA_DIR / "edgeiq_live_track_intelligence_v1.csv"
LIVE_DRAWER_PATH = DATA_DIR / "edgeiq_horse_intelligence_drawer_current.csv"
LIVE_RUNNER_INTEL_PATH = DATA_DIR / "edgeiq_runner_intelligence_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_metric_usefulness_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_metric_usefulness_v1_summary.csv"
RECOMMENDATIONS_PATH = DATA_DIR / "edgeiq_metric_display_recommendations_v1.csv"


ORDERED_BANDS = {
    "projection_band": {
        "POOR": 1,
        "NEGATIVE": 2,
        "NEUTRAL": 3,
        "POSITIVE": 4,
        "STRONG": 5,
        "ELITE": 6,
    },
    "dna_band": {
        "POOR": 1,
        "NEGATIVE": 2,
        "NEUTRAL": 3,
        "POSITIVE": 4,
        "STRONG": 5,
        "ELITE": 6,
    },
    "grade_band": {
        "PASS": 1,
        "D": 2,
        "C": 3,
        "B": 4,
        "A": 5,
        "A+": 6,
        "VERY LOW": 1,
        "LOW": 2,
        "MEDIUM": 3,
        "HIGH": 4,
        "VERY HIGH": 5,
    },
    "factor_band": {
        "POOR": 1,
        "NEGATIVE": 2,
        "LOW_SAMPLE": 3,
        "NEUTRAL": 4,
        "POSITIVE": 5,
        "ELITE": 6,
    },
    "barrier_band": {
        "STRONG_NEGATIVE": 1,
        "NEGATIVE": 2,
        "NEUTRAL": 3,
        "POSITIVE": 4,
        "STRONG_POSITIVE": 5,
    },
}


@dataclass(frozen=True)
class MetricSpec:
    metric_family: str
    metric_label: str
    dataset_key: str | None
    column_name: str | None
    metric_kind: str
    direction: str = "higher_better"
    base_tier: str = "TIER_2_EXPLANATION"
    proxy_note: str = ""
    notes: str = ""
    ordered_band_key: str | None = None


def text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def as_float(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw:
        return None
    try:
        number = float(raw)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def pct(value: float | None, digits: int = 3) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return ""
    return f"{value:.{digits}f}"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def header_scan() -> dict[str, list[str]]:
    scan: dict[str, list[str]] = {}
    for path in sorted(DATA_DIR.glob("*.csv")):
        try:
            with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
                header = handle.readline().strip()
        except OSError:
            continue
        columns = [part.strip() for part in header.split(",") if part.strip()]
        for column in columns:
            scan.setdefault(column, []).append(path.name)
    return scan


def numeric_series(frame: pd.DataFrame, column: str | None) -> pd.Series:
    if frame.empty or not column or column not in frame.columns:
        return pd.Series([pd.NA] * len(frame), index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def band_series(frame: pd.DataFrame, column: str | None) -> pd.Series:
    if frame.empty or not column or column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index, dtype="object")
    return frame[column].astype(str).fillna("").map(lambda value: text(value).replace("_", " ").upper())


def metric_recommendation(
    *,
    base_tier: str,
    coverage_pct: float,
    lift_pct: float | None,
    rank_win_pct: float | None,
    has_historical_evidence: bool,
    metric_family: str,
) -> str:
    if metric_family in {
        "win_pct",
        "fair_price",
        "implied_probability",
        "value_edge / edge_pct",
        "EDGEiQ confidence",
    }:
        if has_historical_evidence:
            return "TIER_1_DECISION"
        return "TIER_2_EXPLANATION"

    if not has_historical_evidence:
        if metric_family in {
            "track_dna / track_intelligence label",
            "barrier_bias",
            "fit_score",
            "sectional_weapon_score",
            "late_power",
            "projected_spd",
            "dna_v6_2_score",
            "dna_v6_2_band",
        }:
            return "TIER_2_EXPLANATION"
        return "HIDE_OR_DRAWER"

    if coverage_pct < 10:
        return "HIDE_OR_DRAWER"

    if lift_pct is not None and abs(lift_pct) < 2 and (rank_win_pct is None or rank_win_pct < 18):
        return "TIER_3_RESEARCH"

    if base_tier == "TIER_1_DECISION":
        return "TIER_1_DECISION"

    if base_tier == "HIDE_OR_DRAWER":
        return "HIDE_OR_DRAWER"

    if lift_pct is not None and abs(lift_pct) >= 8:
        return "TIER_2_EXPLANATION"
    if lift_pct is not None and abs(lift_pct) >= 4:
        return "TIER_2_EXPLANATION"
    return "TIER_3_RESEARCH"


def recommendation_reason(
    metric_family: str,
    recommended_tier: str,
    coverage_pct: float,
    lift_pct: float | None,
    rank_win_pct: float | None,
    proxy_note: str,
    has_historical_evidence: bool,
) -> str:
    reasons: list[str] = []
    if has_historical_evidence:
        reasons.append(f"historical coverage {coverage_pct:.1f}%")
    else:
        reasons.append("no settled replay evidence in the current audit set")
    if lift_pct is not None:
        reasons.append(f"top-vs-bottom lift {lift_pct:.2f} pts")
    if rank_win_pct is not None:
        reasons.append(f"top-ranked win {rank_win_pct:.2f}%")
    if proxy_note:
        reasons.append(proxy_note)

    tier_explainer = {
        "TIER_1_DECISION": "keep visible in the primary decision surface",
        "TIER_2_EXPLANATION": "keep visible as supporting explanation",
        "TIER_3_RESEARCH": "demote to lower emphasis / secondary context",
        "HIDE_OR_DRAWER": "move to drawer or hide from the default view",
    }
    reasons.append(tier_explainer[recommended_tier])
    return "; ".join(reasons)


def top_rank_win_pct(
    frame: pd.DataFrame,
    metric_values: pd.Series,
    *,
    race_key_column: str | None,
    direction: str,
) -> tuple[float | None, float | None]:
    if not race_key_column or race_key_column not in frame.columns:
        return None, None

    working = pd.DataFrame(
        {
            "race_key": frame[race_key_column].astype(str),
            "metric": metric_values,
            "won": pd.to_numeric(frame.get("won"), errors="coerce"),
            "placed": pd.to_numeric(frame.get("placed"), errors="coerce"),
        }
    ).dropna(subset=["race_key", "metric"])

    if working.empty:
        return None, None

    ascending = direction == "lower_better"
    top_rows = (
        working.sort_values(["race_key", "metric"], ascending=[True, ascending])
        .groupby("race_key", as_index=False)
        .head(1)
    )

    if top_rows.empty:
        return None, None

    win_pct = float(top_rows["won"].fillna(0).mean() * 100.0)
    place_pct = float(top_rows["placed"].fillna(0).mean() * 100.0)
    return win_pct, place_pct


def numeric_metric_row(
    spec: MetricSpec,
    frame: pd.DataFrame,
    metric_values: pd.Series,
    *,
    race_key_column: str | None,
    won_column: str,
    placed_column: str,
    source_file: str,
) -> dict[str, object]:
    total_rows = int(len(frame))
    metric_present = metric_values.dropna()
    coverage_rows = int(metric_present.shape[0])
    coverage_pct = (coverage_rows / total_rows * 100.0) if total_rows else 0.0

    won = pd.to_numeric(frame.get(won_column), errors="coerce")
    placed = pd.to_numeric(frame.get(placed_column), errors="coerce")

    win_corr = None
    place_corr = None
    if coverage_rows >= 25:
        aligned = pd.DataFrame({"metric": metric_values, "won": won, "placed": placed}).dropna()
        if aligned["metric"].nunique() > 1:
            win_corr = float(aligned["metric"].corr(aligned["won"], method="spearman"))
            place_corr = float(aligned["metric"].corr(aligned["placed"], method="spearman"))

    top_label = ""
    bottom_label = ""
    top_win_pct = None
    bottom_win_pct = None
    top_place_pct = None
    bottom_place_pct = None
    lift_pct = None

    if coverage_rows >= 25 and metric_present.nunique() > 1:
        q20 = float(metric_present.quantile(0.2))
        q80 = float(metric_present.quantile(0.8))

        if spec.direction == "lower_better":
            top_mask = metric_values <= q20
            bottom_mask = metric_values >= q80
            top_label = "LOWEST_20_PCT"
            bottom_label = "HIGHEST_20_PCT"
        else:
            top_mask = metric_values >= q80
            bottom_mask = metric_values <= q20
            top_label = "HIGHEST_20_PCT"
            bottom_label = "LOWEST_20_PCT"

        top_df = pd.DataFrame({"won": won[top_mask], "placed": placed[top_mask]}).dropna()
        bottom_df = pd.DataFrame({"won": won[bottom_mask], "placed": placed[bottom_mask]}).dropna()

        if not top_df.empty:
            top_win_pct = float(top_df["won"].mean() * 100.0)
            top_place_pct = float(top_df["placed"].mean() * 100.0)
        if not bottom_df.empty:
            bottom_win_pct = float(bottom_df["won"].mean() * 100.0)
            bottom_place_pct = float(bottom_df["placed"].mean() * 100.0)
        if top_win_pct is not None and bottom_win_pct is not None:
            lift_pct = top_win_pct - bottom_win_pct

    rank_win_pct, rank_place_pct = top_rank_win_pct(
        frame,
        metric_values,
        race_key_column=race_key_column,
        direction=spec.direction,
    )

    races = int(frame[race_key_column].nunique()) if race_key_column and race_key_column in frame.columns else 0
    has_historical_evidence = coverage_rows > 0
    recommended_tier = metric_recommendation(
        base_tier=spec.base_tier,
        coverage_pct=coverage_pct,
        lift_pct=lift_pct,
        rank_win_pct=rank_win_pct,
        has_historical_evidence=has_historical_evidence,
        metric_family=spec.metric_family,
    )

    return {
        "metric_family": spec.metric_family,
        "metric_label": spec.metric_label,
        "metric_kind": spec.metric_kind,
        "metric_column_used": spec.column_name or "",
        "source_file": source_file,
        "proxy_note": spec.proxy_note,
        "notes": spec.notes,
        "rows": total_rows,
        "races": races,
        "coverage_rows": coverage_rows,
        "coverage_pct": round(coverage_pct, 3),
        "win_correlation": pct(win_corr, 4),
        "place_correlation": pct(place_corr, 4),
        "top_bucket_label": top_label,
        "top_bucket_win_pct": pct(top_win_pct),
        "top_bucket_place_pct": pct(top_place_pct),
        "bottom_bucket_label": bottom_label,
        "bottom_bucket_win_pct": pct(bottom_win_pct),
        "bottom_bucket_place_pct": pct(bottom_place_pct),
        "lift_pct": pct(lift_pct),
        "rank_usefulness_win_pct": pct(rank_win_pct),
        "rank_usefulness_place_pct": pct(rank_place_pct),
        "has_historical_evidence": "YES" if has_historical_evidence else "NO",
        "recommended_display_tier": recommended_tier,
        "recommendation_reason": recommendation_reason(
            spec.metric_family,
            recommended_tier,
            coverage_pct,
            lift_pct,
            rank_win_pct,
            spec.proxy_note,
            has_historical_evidence,
        ),
    }


def categorical_metric_row(
    spec: MetricSpec,
    frame: pd.DataFrame,
    metric_values: pd.Series,
    *,
    race_key_column: str | None,
    won_column: str,
    placed_column: str,
    source_file: str,
) -> dict[str, object]:
    total_rows = int(len(frame))
    clean_values = metric_values.fillna("").astype(str).map(lambda value: text(value).replace("_", " ").upper())
    coverage_mask = clean_values.ne("")
    coverage_rows = int(coverage_mask.sum())
    coverage_pct = (coverage_rows / total_rows * 100.0) if total_rows else 0.0

    races = int(frame[race_key_column].nunique()) if race_key_column and race_key_column in frame.columns else 0
    won = pd.to_numeric(frame.get(won_column), errors="coerce")
    placed = pd.to_numeric(frame.get(placed_column), errors="coerce")

    top_label = ""
    bottom_label = ""
    top_win_pct = None
    bottom_win_pct = None
    top_place_pct = None
    bottom_place_pct = None
    lift_pct = None
    win_corr = None
    place_corr = None
    rank_win_pct = None
    rank_place_pct = None

    grouped = (
        pd.DataFrame({"metric": clean_values, "won": won, "placed": placed})[coverage_mask]
        .groupby("metric", dropna=False)
        .agg(rows=("metric", "size"), won_rate=("won", "mean"), place_rate=("placed", "mean"))
        .reset_index()
    )
    grouped["won_rate_pct"] = grouped["won_rate"] * 100.0
    grouped["place_rate_pct"] = grouped["place_rate"] * 100.0

    order_map = ORDERED_BANDS.get(spec.ordered_band_key or "")
    if order_map and not grouped.empty:
        grouped["order"] = grouped["metric"].map(lambda value: order_map.get(value, math.nan))
        ordered = grouped.dropna(subset=["order"]).sort_values("order")
        if not ordered.empty:
            bottom_row = ordered.iloc[0]
            top_row = ordered.iloc[-1]
            top_label = str(top_row["metric"])
            bottom_label = str(bottom_row["metric"])
            top_win_pct = float(top_row["won_rate_pct"])
            bottom_win_pct = float(bottom_row["won_rate_pct"])
            top_place_pct = float(top_row["place_rate_pct"])
            bottom_place_pct = float(bottom_row["place_rate_pct"])
            lift_pct = top_win_pct - bottom_win_pct

            encoded = clean_values.map(lambda value: order_map.get(value, math.nan))
            aligned = pd.DataFrame({"metric": encoded, "won": won, "placed": placed}).dropna()
            if aligned["metric"].nunique() > 1:
                win_corr = float(aligned["metric"].corr(aligned["won"], method="spearman"))
                place_corr = float(aligned["metric"].corr(aligned["placed"], method="spearman"))

            rank_win_pct, rank_place_pct = top_rank_win_pct(
                pd.DataFrame(
                    {
                        race_key_column or "race_key": frame[race_key_column] if race_key_column and race_key_column in frame.columns else "",
                        "won": won,
                        "placed": placed,
                    }
                ),
                encoded,
                race_key_column=race_key_column if race_key_column and race_key_column in frame.columns else None,
                direction="higher_better",
            )
    elif not grouped.empty:
        ranked = grouped[grouped["rows"] >= 25].sort_values(["won_rate_pct", "rows"], ascending=[False, False])
        if ranked.empty:
            ranked = grouped.sort_values(["won_rate_pct", "rows"], ascending=[False, False])
        if not ranked.empty:
            top_row = ranked.iloc[0]
            bottom_row = ranked.iloc[-1]
            top_label = str(top_row["metric"])
            bottom_label = str(bottom_row["metric"])
            top_win_pct = float(top_row["won_rate_pct"])
            bottom_win_pct = float(bottom_row["won_rate_pct"])
            top_place_pct = float(top_row["place_rate_pct"])
            bottom_place_pct = float(bottom_row["place_rate_pct"])
            lift_pct = top_win_pct - bottom_win_pct

    has_historical_evidence = coverage_rows > 0
    recommended_tier = metric_recommendation(
        base_tier=spec.base_tier,
        coverage_pct=coverage_pct,
        lift_pct=lift_pct,
        rank_win_pct=rank_win_pct,
        has_historical_evidence=has_historical_evidence,
        metric_family=spec.metric_family,
    )

    return {
        "metric_family": spec.metric_family,
        "metric_label": spec.metric_label,
        "metric_kind": spec.metric_kind,
        "metric_column_used": spec.column_name or "",
        "source_file": source_file,
        "proxy_note": spec.proxy_note,
        "notes": spec.notes,
        "rows": total_rows,
        "races": races,
        "coverage_rows": coverage_rows,
        "coverage_pct": round(coverage_pct, 3),
        "win_correlation": pct(win_corr, 4),
        "place_correlation": pct(place_corr, 4),
        "top_bucket_label": top_label,
        "top_bucket_win_pct": pct(top_win_pct),
        "top_bucket_place_pct": pct(top_place_pct),
        "bottom_bucket_label": bottom_label,
        "bottom_bucket_win_pct": pct(bottom_win_pct),
        "bottom_bucket_place_pct": pct(bottom_place_pct),
        "lift_pct": pct(lift_pct),
        "rank_usefulness_win_pct": pct(rank_win_pct),
        "rank_usefulness_place_pct": pct(rank_place_pct),
        "has_historical_evidence": "YES" if has_historical_evidence else "NO",
        "recommended_display_tier": recommended_tier,
        "recommendation_reason": recommendation_reason(
            spec.metric_family,
            recommended_tier,
            coverage_pct,
            lift_pct,
            rank_win_pct,
            spec.proxy_note,
            has_historical_evidence,
        ),
    }


def unavailable_metric_row(
    spec: MetricSpec,
    header_index: dict[str, list[str]],
) -> dict[str, object]:
    reference_files = []
    if spec.column_name:
        reference_files = header_index.get(spec.column_name, [])

    recommended_tier = metric_recommendation(
        base_tier=spec.base_tier,
        coverage_pct=0.0,
        lift_pct=None,
        rank_win_pct=None,
        has_historical_evidence=False,
        metric_family=spec.metric_family,
    )
    reason = recommendation_reason(
        spec.metric_family,
        recommended_tier,
        0.0,
        None,
        None,
        spec.proxy_note,
        False,
    )
    if reference_files:
        reason = f"{reason}; live/schema references: {'|'.join(reference_files[:6])}"

    return {
        "metric_family": spec.metric_family,
        "metric_label": spec.metric_label,
        "metric_kind": spec.metric_kind,
        "metric_column_used": spec.column_name or "",
        "source_file": "|".join(reference_files[:6]),
        "proxy_note": spec.proxy_note,
        "notes": spec.notes,
        "rows": 0,
        "races": 0,
        "coverage_rows": 0,
        "coverage_pct": 0.0,
        "win_correlation": "",
        "place_correlation": "",
        "top_bucket_label": "",
        "top_bucket_win_pct": "",
        "top_bucket_place_pct": "",
        "bottom_bucket_label": "",
        "bottom_bucket_win_pct": "",
        "bottom_bucket_place_pct": "",
        "lift_pct": "",
        "rank_usefulness_win_pct": "",
        "rank_usefulness_place_pct": "",
        "has_historical_evidence": "NO",
        "recommended_display_tier": recommended_tier,
        "recommendation_reason": reason,
    }


def main() -> int:
    built_at = datetime.now().astimezone().isoformat(timespec="seconds")
    header_index = header_scan()

    core_detail = read_csv(CORE_DETAIL_PATH)
    if not core_detail.empty and "tier_name" in core_detail.columns:
        tier_priority = ["HIGH_PLUS_MEDIUM", "ALL_V2_EXPANDED", "HIGH_CONFIDENCE_ONLY"]
        selected_tier = next((tier for tier in tier_priority if tier in set(core_detail["tier_name"])), "")
        if selected_tier:
            core_detail = core_detail[core_detail["tier_name"].eq(selected_tier)].copy()
    else:
        selected_tier = ""

    overlay = read_csv(OVERLAY_PATH)
    dna = read_csv(DNA_PATH)
    bet_quality = read_csv(BET_QUALITY_PATH)
    live_board = read_csv(LIVE_BOARD_PATH)
    live_track = read_csv(LIVE_TRACK_PATH)
    live_drawer = read_csv(LIVE_DRAWER_PATH)
    live_runner_intel = read_csv(LIVE_RUNNER_INTEL_PATH)

    datasets: dict[str, tuple[pd.DataFrame, str, str, str, str | None]] = {
        "core": (core_detail, CORE_DETAIL_PATH.name, "won", "placed", "race_key"),
        "overlay": (overlay, OVERLAY_PATH.name, "won", "placed", "race_key"),
        "dna": (dna, DNA_PATH.name, "won", "placed", "race_key"),
        "bet_quality": (bet_quality, BET_QUALITY_PATH.name, "won", "placed", "race_key"),
        "live_board_reference": (live_board, LIVE_BOARD_PATH.name, "", "", "race_key"),
        "live_track_reference": (live_track, LIVE_TRACK_PATH.name, "", "", "race_key"),
        "live_drawer_reference": (live_drawer, LIVE_DRAWER_PATH.name, "", "", "race_key"),
        "live_runner_intel_reference": (live_runner_intel, LIVE_RUNNER_INTEL_PATH.name, "", "", "race_key"),
    }

    metric_specs = [
        MetricSpec("win_pct", "Win %", "core", "V6_1_RESEARCH_probability", "numeric", "higher_better", "TIER_1_DECISION", notes="Converted to percentage from matched V6.1 probability replay."),
        MetricSpec("fair_price", "Fair Price", "core", "V6_1_RESEARCH_fair_price", "numeric", "lower_better", "TIER_1_DECISION", notes="Model fair price from matched V6.1 probability replay."),
        MetricSpec("implied_probability", "Implied Probability", "core", "V6_1_RESEARCH_probability", "numeric", "higher_better", "TIER_1_DECISION", notes="Probability-scale duplicate of win %."),
        MetricSpec("value_edge / edge_pct", "Value Edge", "overlay", "baseline_overlay_pct_v1", "numeric", "higher_better", "TIER_1_DECISION", notes="Historical overlay replay used as the closest settled value-edge source."),
        MetricSpec("projection_gap", "Projection Gap", "core", "projection_gap_V6_1_RESEARCH", "numeric", "higher_better", "TIER_2_EXPLANATION"),
        MetricSpec("projection_band", "Projection Band", "core", "projection_band_V6_1_RESEARCH", "categorical", "higher_better", "TIER_2_EXPLANATION", ordered_band_key="projection_band"),
        MetricSpec("dna_v6_2_score", "Runner DNA Score", "dna", "v6_3_research_score", "numeric", "higher_better", "TIER_2_EXPLANATION", proxy_note="using Runner DNA V6.3 historical replay as the closest settled proxy"),
        MetricSpec("dna_v6_2_band", "Runner DNA Band", "dna", "v6_3_research_band", "categorical", "higher_better", "TIER_2_EXPLANATION", proxy_note="using Runner DNA V6.3 historical replay as the closest settled proxy", ordered_band_key="dna_band"),
        MetricSpec("confidence_score", "Confidence Score", None, "confidence_score", "numeric", "higher_better", "TIER_3_RESEARCH", notes="Current live field exists, but no dedicated settled replay source was found in this audit set."),
        MetricSpec("EDGEiQ confidence", "EDGEiQ Confidence", "bet_quality", "bet_quality_grade_v1_1", "categorical", "higher_better", "TIER_1_DECISION", proxy_note="using bet quality grade as the current customer-facing confidence proxy", ordered_band_key="grade_band"),
        MetricSpec("bet_quality", "Bet Quality", "bet_quality", "bet_quality_score_v1_1", "numeric", "higher_better", "TIER_2_EXPLANATION", proxy_note="using historical bet-quality engine replay"),
        MetricSpec("track_dna / track_intelligence label", "Track DNA Label", None, "track_dna_label", "categorical", "higher_better", "TIER_2_EXPLANATION", notes="Live intelligence label found, but no settled replay join was available in this audit pass."),
        MetricSpec("barrier_bias", "Barrier Bias", "overlay", "barrier_rail_condition_score_v1", "numeric", "higher_better", "TIER_2_EXPLANATION", proxy_note="using barrier+rail+condition score as the closest settled barrier-bias proxy"),
        MetricSpec("fit_score", "Track Fit Score", None, "track_fit_score", "numeric", "higher_better", "TIER_2_EXPLANATION", notes="Live runner-level track fit exists, but no settled replay join was available in this audit pass."),
        MetricSpec("sectional_weapon_score", "Sectional Weapon Score", None, "sectional_weapon_score", "numeric", "higher_better", "TIER_2_EXPLANATION", notes="Current live drawer field exists, but no dedicated settled replay source was found in this audit set."),
        MetricSpec("late_power", "Late Power", None, "late_power_index", "numeric", "higher_better", "TIER_2_EXPLANATION", notes="Current live drawer field exists, but no dedicated settled replay source was found in this audit set."),
        MetricSpec("projected_spd", "Projected SPD", None, "projected_spd", "numeric", "higher_better", "TIER_2_EXPLANATION", notes="Current live drawer field exists, but no dedicated settled replay source was found in this audit set."),
        MetricSpec("jockey_score", "Jockey Score", "overlay", "jockey_factor_band_v1", "categorical", "higher_better", "TIER_2_EXPLANATION", proxy_note="band-only historical replay available via jockey factor band", ordered_band_key="factor_band"),
        MetricSpec("trainer_score", "Trainer Score", "overlay", "trainer_factor_band_v1", "categorical", "higher_better", "TIER_2_EXPLANATION", proxy_note="band-only historical replay available via trainer factor band", ordered_band_key="factor_band"),
        MetricSpec("connection_score", "Connection Score", "overlay", "trainer_jockey_blend_score_v1", "numeric", "higher_better", "TIER_2_EXPLANATION", proxy_note="using trainer-jockey blend score as the settled connection proxy"),
    ]

    rows: list[dict[str, object]] = []
    for spec in metric_specs:
        if not spec.dataset_key or spec.dataset_key not in datasets:
            rows.append(unavailable_metric_row(spec, header_index))
            continue

        frame, source_file, won_column, placed_column, race_key_column = datasets[spec.dataset_key]
        if frame.empty or not spec.column_name or spec.column_name not in frame.columns:
            rows.append(unavailable_metric_row(spec, header_index))
            continue

        if spec.metric_kind == "numeric":
            metric_values = numeric_series(frame, spec.column_name)
            if spec.metric_family in {"win_pct", "implied_probability"}:
                metric_values = metric_values * 100.0
            rows.append(
                numeric_metric_row(
                    spec,
                    frame,
                    metric_values,
                    race_key_column=race_key_column,
                    won_column=won_column,
                    placed_column=placed_column,
                    source_file=source_file,
                )
            )
        else:
            metric_values = band_series(frame, spec.column_name)
            rows.append(
                categorical_metric_row(
                    spec,
                    frame,
                    metric_values,
                    race_key_column=race_key_column,
                    won_column=won_column,
                    placed_column=placed_column,
                    source_file=source_file,
                )
            )

    metrics_df = pd.DataFrame(rows)
    metrics_df.insert(0, "built_at", built_at)
    metrics_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    recommendations = metrics_df[
        [
            "metric_family",
            "metric_label",
            "source_file",
            "coverage_pct",
            "lift_pct",
            "rank_usefulness_win_pct",
            "has_historical_evidence",
            "recommended_display_tier",
            "recommendation_reason",
        ]
    ].copy()
    recommendations["display_recommendation"] = recommendations["recommended_display_tier"].map(
        {
            "TIER_1_DECISION": "show in the primary decision surface",
            "TIER_2_EXPLANATION": "show as supporting explanation",
            "TIER_3_RESEARCH": "de-emphasise / secondary context",
            "HIDE_OR_DRAWER": "move to drawer or hide by default",
        }
    )
    recommendations.to_csv(RECOMMENDATIONS_PATH, index=False, encoding="utf-8")

    tier_counts = recommendations["recommended_display_tier"].value_counts().to_dict()
    strongest_decision = recommendations[
        recommendations["recommended_display_tier"].eq("TIER_1_DECISION")
    ]["metric_family"].tolist()
    weak_metrics = recommendations[
        recommendations["has_historical_evidence"].eq("NO")
    ]["metric_family"].tolist()

    summary_rows = [
        {"metric": "built_at", "value": built_at},
        {"metric": "core_probability_source", "value": CORE_DETAIL_PATH.name},
        {"metric": "core_probability_tier_used", "value": selected_tier or "UNFILTERED"},
        {"metric": "overlay_source", "value": OVERLAY_PATH.name if OVERLAY_PATH.exists() else "MISSING"},
        {"metric": "runner_dna_source", "value": DNA_PATH.name if DNA_PATH.exists() else "MISSING"},
        {"metric": "bet_quality_source", "value": BET_QUALITY_PATH.name if BET_QUALITY_PATH.exists() else "MISSING"},
        {"metric": "metrics_requested", "value": len(metric_specs)},
        {"metric": "metrics_with_historical_evidence", "value": int((metrics_df["has_historical_evidence"] == "YES").sum())},
        {"metric": "tier_1_decision_count", "value": tier_counts.get("TIER_1_DECISION", 0)},
        {"metric": "tier_2_explanation_count", "value": tier_counts.get("TIER_2_EXPLANATION", 0)},
        {"metric": "tier_3_research_count", "value": tier_counts.get("TIER_3_RESEARCH", 0)},
        {"metric": "hide_or_drawer_count", "value": tier_counts.get("HIDE_OR_DRAWER", 0)},
        {"metric": "strongest_tier_1_metrics", "value": "|".join(strongest_decision)},
        {"metric": "metrics_without_settled_evidence", "value": "|".join(weak_metrics)},
        {
            "metric": "headline",
            "value": "Keep win%, fair price, value edge, and EDGEiQ confidence in the primary surface. Push DNA / projection / track-fit signals into explanation, and demote raw research/data-quality fields.",
        },
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY_PATH, index=False, encoding="utf-8")

    print("[EDGEIQ_METRIC_USEFULNESS_V1] COMPLETE")
    print(f"metrics={len(metric_specs)}")
    print(f"metrics_with_historical_evidence={(metrics_df['has_historical_evidence'] == 'YES').sum()}")
    print(f"tier_1_decision_count={tier_counts.get('TIER_1_DECISION', 0)}")
    print(f"tier_2_explanation_count={tier_counts.get('TIER_2_EXPLANATION', 0)}")
    print(f"tier_3_research_count={tier_counts.get('TIER_3_RESEARCH', 0)}")
    print(f"hide_or_drawer_count={tier_counts.get('HIDE_OR_DRAWER', 0)}")
    print(f"wrote={OUTPUT_PATH}")
    print(f"wrote={SUMMARY_PATH}")
    print(f"wrote={RECOMMENDATIONS_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"[EDGEIQ_METRIC_USEFULNESS_V1] FAILED: {exc}", file=sys.stderr)
        raise
