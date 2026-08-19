from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"
ARCHIVE = DATA / "edgeiq_historical_race_shape_archive_v1.csv"
CALENDAR = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"
CURRENT_PROJECTION = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"
CURRENT_FAIR = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"

OUT_MAIN = DATA / "edgeiq_projection_calibration_audit_v1.csv"
OUT_GAP = DATA / "edgeiq_projection_gap_distribution_v1.csv"
OUT_CONVERSION = DATA / "edgeiq_probability_conversion_audit_v1.csv"
OUT_REALISM = DATA / "edgeiq_price_realism_audit_v1.csv"
OUT_REPORT = DATA / "edgeiq_projection_calibration_report_v1.md"

POWER_STANDARD = 0.55
POWER_WEAK = 0.35
WEAK_RACE_TOP_GAP_THRESHOLD = 2.0
PROB_CAP = 0.35

GAP_BUCKETS_POSITIVE = [
    (0.0, 1.0, "0_1"),
    (1.0, 2.0, "1_2"),
    (2.0, 3.0, "2_3"),
    (3.0, 5.0, "3_5"),
    (5.0, 10.0, "5_10"),
    (10.0, 15.0, "10_15"),
    (15.0, 20.0, "15_20"),
    (20.0, 30.0, "20_30"),
    (30.0, 10_000.0, "30_PLUS"),
]

PROBABILITY_BUCKETS = [
    (0.0, 0.05, "LT_5"),
    (0.05, 0.10, "P5_10"),
    (0.10, 0.15, "P10_15"),
    (0.15, 0.20, "P15_20"),
    (0.20, 0.25, "P20_25"),
    (0.25, 1.00, "P25_PLUS"),
]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def norm_track(value: object) -> str:
    text = upper(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"\s+", " ", text).strip()


def canon_horse(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def race_no_key(value: object) -> str:
    return re.sub(r"[^0-9]", "", clean(value))


def to_float(value: object) -> float | None:
    try:
        text = clean(value).replace(",", "")
        if text == "":
            return None
        parsed = float(text)
        if not math.isfinite(parsed):
            return None
        return parsed
    except Exception:
        return None


def parse_sp(value: object) -> float | None:
    text = clean(value)
    if text == "" or text == "-" or text.upper() == "SP":
        return None
    text = text.replace("$", "").replace("F", "").replace("SP", "").strip()
    return to_float(text)


def safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator) * 100.0


def round_num(value: float | None, places: int = 2) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), places)


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def condition_group(value: object) -> str:
    text = upper(value)
    if "SYNTH" in text:
        return "SYNTHETIC"
    if "HEAVY" in text:
        return "HEAVY"
    if "SOFT" in text:
        return "SOFT"
    if "GOOD" in text or "FIRM" in text:
        return "GOOD"
    return "UNKNOWN"


def gap_bucket(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "NO_GAP"
    if value < 0:
        return "NEGATIVE"
    for low, high, label in GAP_BUCKETS_POSITIVE:
        if low <= value < high:
            return label
    return "30_PLUS"


def prob_bucket(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "NO_PROB"
    for low, high, label in PROBABILITY_BUCKETS:
        if low <= value < high:
            return label
    return "P25_PLUS"


def compression_band(rank1_rank2_gap: float, rank1_field_avg_gap: float) -> str:
    if rank1_rank2_gap < 1.0 and rank1_field_avg_gap < 3.0:
        return "ULTRA_COMPRESSED"
    if rank1_rank2_gap < 2.0 and rank1_field_avg_gap < 5.0:
        return "COMPRESSED"
    if rank1_rank2_gap >= 5.0 and rank1_field_avg_gap >= 12.0:
        return "DOMINANT"
    if rank1_rank2_gap >= 3.0 and rank1_field_avg_gap >= 7.0:
        return "SEPARATED"
    return "NORMAL"


def roi_pct_from_sp(frame: pd.DataFrame, win_col: str = "won", sp_col: str = "sp_num") -> float | None:
    usable = frame[frame[sp_col].notna()].copy()
    if usable.empty:
        return None
    returns = np.where(
        usable[win_col].eq(1),
        usable[sp_col] - 1.0,
        -1.0,
    )
    return float(np.mean(returns) * 100.0)


def load_vic_context() -> tuple[pd.DataFrame, dict[str, set[tuple[str, str]]]]:
    calendar = load_required_csv(CALENDAR)
    archive = load_required_csv(ARCHIVE)

    calendar["date_key"] = calendar["meeting_date"].map(clean).str[:10]
    calendar["track_key"] = calendar["track"].map(norm_track)
    calendar["race_no_key"] = calendar["race_no"].map(race_no_key)
    vic_calendar = calendar[calendar["state"].map(upper).eq("VIC")].copy()

    vic_track_dates = {
        (row.date_key, row.track_key)
        for row in vic_calendar.itertuples(index=False)
        if row.date_key and row.track_key
    }
    vic_track_date_races = {
        (row.date_key, row.track_key, row.race_no_key)
        for row in vic_calendar.itertuples(index=False)
        if row.date_key and row.track_key and row.race_no_key
    }

    archive["date_key"] = archive["meeting_date"].map(clean).str[:10]
    archive["track_key"] = archive["track"].map(norm_track)
    archive["race_no_key"] = archive["race_no"].map(race_no_key)
    archive["horse_key"] = archive["horse_key_join"].where(
        archive["horse_key_join"].map(clean).ne(""),
        archive["horseName"].map(canon_horse),
    )
    archive["horse_key"] = archive["horse_key"].map(canon_horse)
    archive["distance_num"] = pd.to_numeric(
        archive["distance"].map(lambda x: re.sub(r"[^0-9]", "", clean(x))),
        errors="coerce",
    )
    archive["sp_num"] = archive["sp"].map(parse_sp)
    archive["condition_group_v1"] = archive["trackCondition"].map(condition_group)
    archive = archive[
        archive.apply(
            lambda row: (row["date_key"], row["track_key"], row["race_no_key"]) in vic_track_date_races,
            axis=1,
        )
    ].copy()

    archive_small = archive[
        [
            "date_key",
            "track_key",
            "horse_key",
            "race_no_key",
            "race_key_join",
            "raceName",
            "trackCondition",
            "condition_group_v1",
            "distance_num",
            "sp_num",
            "won",
            "placed",
        ]
    ].drop_duplicates(["date_key", "track_key", "horse_key"], keep="first")

    return archive_small, {
        "vic_track_dates": vic_track_dates,
    }


def load_backtest(archive_small: pd.DataFrame, context_sets: dict[str, set[tuple[str, str]]]) -> pd.DataFrame:
    back = load_required_csv(BACKTEST)
    back = back[back["model"].map(upper).eq("V6_1_RESEARCH_PRIOR")].copy()
    back["date_key"] = back["race_date"].map(clean).str[:10]
    back["track_key"] = back["track"].map(norm_track)
    back["horse_key"] = back["horse"].map(canon_horse)
    back = back[
        back.apply(lambda row: (row["date_key"], row["track_key"]) in context_sets["vic_track_dates"], axis=1)
    ].copy()

    numeric_cols = [
        "distance",
        "finish_position_num",
        "field_size",
        "prior_starts",
        "earned_rating",
        "prior_rating",
        "rating",
        "race_median_rating",
        "rating_gap",
        "rank",
        "model_prob",
        "fair_price",
        "won",
        "placed",
    ]
    for col in numeric_cols:
        back[col] = pd.to_numeric(back[col], errors="coerce")

    merged = back.merge(
        archive_small,
        how="left",
        on=["date_key", "track_key", "horse_key"],
        suffixes=("", "_archive"),
    )
    merged["race_no"] = merged["race_no_key"].map(lambda x: int(x) if clean(x) else np.nan)
    merged["projection_gap_source_v1"] = "HISTORICAL_V6_1_PRIOR_RATING_GAP_PROXY"
    merged["gap_bucket_v1"] = merged["rating_gap"].map(gap_bucket)
    merged["prob_bucket_v1"] = merged["model_prob"].map(prob_bucket)
    merged["sp_available_v1"] = merged["sp_num"].notna()
    merged["roi_return_sp_v1"] = np.where(
        merged["sp_num"].notna(),
        np.where(merged["won"].eq(1), merged["sp_num"] - 1.0, -1.0),
        np.nan,
    )
    return merged


def add_live_formula_proxy(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []

    for _, race in df.groupby("race_key", dropna=False):
        work = race.copy()
        min_gap = float(work["rating_gap"].min())
        max_gap = float(work["rating_gap"].max())
        power_used = POWER_WEAK if max_gap < WEAK_RACE_TOP_GAP_THRESHOLD else POWER_STANDARD
        work["builder_proxy_power_v1"] = power_used
        work["builder_proxy_score_v1"] = np.power(
            np.clip(work["rating_gap"] - min_gap + 1.0, 0.000001, None),
            power_used,
        )
        score_sum = float(work["builder_proxy_score_v1"].sum())
        work["builder_proxy_prob_pre_cap_v1"] = work["builder_proxy_score_v1"] / score_sum if score_sum > 0 else np.nan
        work["builder_proxy_prob_post_cap_no_renorm_v1"] = work["builder_proxy_prob_pre_cap_v1"].clip(upper=PROB_CAP)
        no_renorm_sum = float(work["builder_proxy_prob_post_cap_no_renorm_v1"].sum())
        work["builder_proxy_prob_sum_no_renorm_v1"] = no_renorm_sum
        if no_renorm_sum > 0:
            work["builder_proxy_prob_post_cap_renorm_v1"] = (
                work["builder_proxy_prob_post_cap_no_renorm_v1"] / no_renorm_sum
            )
        else:
            work["builder_proxy_prob_post_cap_renorm_v1"] = np.nan
        work["builder_proxy_fair_price_no_renorm_v1"] = np.where(
            work["builder_proxy_prob_post_cap_no_renorm_v1"] > 0,
            1.0 / work["builder_proxy_prob_post_cap_no_renorm_v1"],
            np.nan,
        )
        work["builder_proxy_fair_price_renorm_v1"] = np.where(
            work["builder_proxy_prob_post_cap_renorm_v1"] > 0,
            1.0 / work["builder_proxy_prob_post_cap_renorm_v1"],
            np.nan,
        )
        work["builder_proxy_prob_delta_pts_v1"] = (
            work["builder_proxy_prob_post_cap_no_renorm_v1"] - work["model_prob"]
        ) * 100.0
        work["builder_proxy_fair_delta_v1"] = (
            work["builder_proxy_fair_price_no_renorm_v1"] - work["fair_price"]
        )
        rows.append(work)

    return pd.concat(rows, ignore_index=True)


def projection_gap_distribution(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for section_name, subset in [
        ("ALL_RUNNERS", df),
        ("RANK_1_ONLY", df[df["rank"].eq(1)].copy()),
    ]:
        for bucket, group in subset.groupby("gap_bucket_v1", dropna=False):
            rows.append(
                {
                    "section": section_name,
                    "gap_metric_source_v1": "HISTORICAL_V6_1_PRIOR_RATING_GAP_PROXY",
                    "projection_gap_bucket_v1": bucket,
                    "race_count": int(group["race_key"].nunique()),
                    "runner_count": int(len(group)),
                    "wins": int(group["won"].sum()),
                    "winner_pct": round(safe_pct(group["won"].sum(), len(group)), 2),
                    "places": int(group["placed"].sum()),
                    "place_pct": round(safe_pct(group["placed"].sum(), len(group)), 2),
                    "avg_gap_v1": round_num(group["rating_gap"].mean(), 4),
                    "avg_model_prob_pct_v1": round_num(group["model_prob"].mean() * 100.0, 2),
                    "avg_fair_price_v1": round_num(group["fair_price"].mean(), 3),
                    "actual_sp_rows": int(group["sp_num"].notna().sum()),
                    "avg_actual_sp_v1": round_num(group["sp_num"].mean(), 3),
                    "median_actual_sp_v1": round_num(group["sp_num"].median(), 3),
                }
            )

    order = ["NEGATIVE"] + [label for _, _, label in GAP_BUCKETS_POSITIVE] + ["NO_GAP"]
    out = pd.DataFrame(rows)
    out["sort_key_v1"] = out["projection_gap_bucket_v1"].map(lambda x: order.index(x) if x in order else 999)
    out = out.sort_values(["section", "sort_key_v1"]).drop(columns=["sort_key_v1"])
    return out


def build_field_compression(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    race_rows: list[dict[str, object]] = []

    for race_key, race in df.groupby("race_key", dropna=False):
        work = race.sort_values(["rank", "rating"], ascending=[True, False]).copy()
        if work.empty:
            continue

        top = work.iloc[0]
        second = work.iloc[1] if len(work) >= 2 else None
        third = work.iloc[2] if len(work) >= 3 else None
        winner = work[work["won"].eq(1)].head(1)
        winner_row = winner.iloc[0] if not winner.empty else None

        rank1_rank2_gap = float(top["rating"] - second["rating"]) if second is not None else np.nan
        rank1_rank3_gap = float(top["rating"] - third["rating"]) if third is not None else np.nan
        rank1_field_avg_gap = float(top["rating"] - work["rating"].mean())
        band = compression_band(
            rank1_rank2_gap if not math.isnan(rank1_rank2_gap) else 0.0,
            rank1_field_avg_gap if not math.isnan(rank1_field_avg_gap) else 0.0,
        )

        race_rows.append(
            {
                "section": "FIELD_COMPRESSION_RACE",
                "race_key": race_key,
                "race_date": top["race_date"],
                "track": top["track"],
                "race_no": top["race_no"],
                "field_size": int(len(work)),
                "rank1_horse": top["horse"],
                "rank1_rating": round_num(top["rating"], 4),
                "rank1_fair_price": round_num(top["fair_price"], 4),
                "rank1_model_prob_pct": round_num(top["model_prob"] * 100.0, 2),
                "rank1_rank2_gap": round_num(rank1_rank2_gap, 4),
                "rank1_rank3_gap": round_num(rank1_rank3_gap, 4),
                "rank1_field_avg_gap": round_num(rank1_field_avg_gap, 4),
                "compression_band_v1": band,
                "rank1_won": int(top["won"]),
                "rank1_placed": int(top["placed"]),
                "winner_rank": int(winner_row["rank"]) if winner_row is not None and pd.notna(winner_row["rank"]) else None,
                "winner_horse": winner_row["horse"] if winner_row is not None else "",
                "winner_fair_price": round_num(float(winner_row["fair_price"]), 4) if winner_row is not None else None,
                "winner_sp_num": round_num(float(winner_row["sp_num"]), 4) if winner_row is not None and pd.notna(winner_row["sp_num"]) else None,
                "rank1_sp_num": round_num(float(top["sp_num"]), 4) if pd.notna(top["sp_num"]) else None,
                "rank1_sp_roi_return_v1": round_num(float(top["roi_return_sp_v1"]), 4) if pd.notna(top["roi_return_sp_v1"]) else None,
            }
        )

    race_df = pd.DataFrame(race_rows)

    summary_rows: list[dict[str, object]] = []
    for band, group in race_df.groupby("compression_band_v1", dropna=False):
        rank1_roi_pct = None
        usable_roi = pd.to_numeric(group["rank1_sp_roi_return_v1"], errors="coerce")
        if usable_roi.notna().any():
            rank1_roi_pct = float(usable_roi.mean() * 100.0)
        summary_rows.append(
            {
                "section": "FIELD_COMPRESSION_BAND_SUMMARY",
                "compression_band_v1": band,
                "race_count": int(len(group)),
                "rank1_win_pct": round(safe_pct(group["rank1_won"].sum(), len(group)), 2),
                "rank1_place_pct": round(safe_pct(group["rank1_placed"].sum(), len(group)), 2),
                "avg_rank1_rank2_gap": round_num(pd.to_numeric(group["rank1_rank2_gap"], errors="coerce").mean(), 4),
                "avg_rank1_rank3_gap": round_num(pd.to_numeric(group["rank1_rank3_gap"], errors="coerce").mean(), 4),
                "avg_rank1_field_avg_gap": round_num(pd.to_numeric(group["rank1_field_avg_gap"], errors="coerce").mean(), 4),
                "avg_rank1_fair_price": round_num(pd.to_numeric(group["rank1_fair_price"], errors="coerce").mean(), 4),
                "avg_winner_fair_price": round_num(pd.to_numeric(group["winner_fair_price"], errors="coerce").mean(), 4),
                "avg_winner_sp": round_num(pd.to_numeric(group["winner_sp_num"], errors="coerce").mean(), 4),
                "rank1_sp_roi_pct": round_num(rank1_roi_pct, 2),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    order = {
        "ULTRA_COMPRESSED": 1,
        "COMPRESSED": 2,
        "NORMAL": 3,
        "SEPARATED": 4,
        "DOMINANT": 5,
    }
    if not summary_df.empty:
        summary_df["sort_key_v1"] = summary_df["compression_band_v1"].map(lambda x: order.get(x, 999))
        summary_df = summary_df.sort_values("sort_key_v1").drop(columns=["sort_key_v1"])
    return race_df, summary_df


def probability_conversion_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    races_with_cap = 0
    races_with_underround = 0
    race_detail_rows: list[dict[str, object]] = []

    for race_key, race in df.groupby("race_key", dropna=False):
        work = race.sort_values(["model_prob", "rating"], ascending=[False, False]).copy()
        live = work.sort_values(["builder_proxy_prob_post_cap_no_renorm_v1", "rating"], ascending=[False, False]).copy()

        base_top = work.iloc[0]
        base_second = work.iloc[1] if len(work) >= 2 else None
        live_top = live.iloc[0]
        live_second = live.iloc[1] if len(live) >= 2 else None
        cap_hits = int((work["builder_proxy_prob_pre_cap_v1"] > PROB_CAP).sum())
        underround_sum = float(work["builder_proxy_prob_sum_no_renorm_v1"].iloc[0])
        if cap_hits > 0:
            races_with_cap += 1
        if underround_sum < 0.9999:
            races_with_underround += 1

        base_top_prob = float(base_top["model_prob"]) * 100.0
        base_second_prob = float(base_second["model_prob"]) * 100.0 if base_second is not None else np.nan
        live_top_prob = float(live_top["builder_proxy_prob_post_cap_no_renorm_v1"]) * 100.0
        live_second_prob = (
            float(live_second["builder_proxy_prob_post_cap_no_renorm_v1"]) * 100.0 if live_second is not None else np.nan
        )
        base_cliff = base_top_prob - base_second_prob if base_second is not None else np.nan
        live_cliff = live_top_prob - live_second_prob if live_second is not None else np.nan
        top_gap_spread = float(work["rating"].max() - work["rating"].min())

        distortion_flag = "NONE"
        if underround_sum < 0.98:
            distortion_flag = "CAP_UNDERROUND"
        elif live_top_prob - base_top_prob >= 4.0 and top_gap_spread <= 12.0:
            distortion_flag = "ARTIFICIAL_BLOWOUT"
        elif base_top_prob - live_top_prob >= 4.0 and top_gap_spread >= 12.0:
            distortion_flag = "ARTIFICIAL_COMPRESSION"
        elif not math.isnan(live_cliff) and not math.isnan(base_cliff) and (live_cliff - base_cliff) >= 4.0:
            distortion_flag = "PROBABILITY_CLIFF"

        race_detail_rows.append(
            {
                "section": "RACE_CONVERSION_DETAIL",
                "race_key": race_key,
                "race_date": base_top["race_date"],
                "track": base_top["track"],
                "race_no": base_top["race_no"],
                "field_size": int(len(work)),
                "base_top_horse": base_top["horse"],
                "base_top_prob_pct": round_num(base_top_prob, 3),
                "base_second_prob_pct": round_num(base_second_prob, 3),
                "base_prob_cliff_pts": round_num(base_cliff, 3),
                "base_shortest_fair_price": round_num(float(base_top["fair_price"]), 4),
                "live_proxy_top_horse": live_top["horse"],
                "live_proxy_top_prob_pct": round_num(live_top_prob, 3),
                "live_proxy_second_prob_pct": round_num(live_second_prob, 3),
                "live_proxy_prob_cliff_pts": round_num(live_cliff, 3),
                "live_proxy_shortest_fair_price": round_num(float(live_top["builder_proxy_fair_price_no_renorm_v1"]), 4),
                "top_prob_delta_live_minus_base_pts": round_num(live_top_prob - base_top_prob, 3),
                "underround_prob_sum_v1": round_num(underround_sum * 100.0, 3),
                "cap_hits_v1": cap_hits,
                "builder_proxy_power_v1": round_num(float(base_top["builder_proxy_power_v1"]), 3),
                "gap_spread_v1": round_num(top_gap_spread, 4),
                "distortion_flag_v1": distortion_flag,
            }
        )

    race_detail_df = pd.DataFrame(race_detail_rows)

    rows.extend(
        [
            {
                "section": "OVERALL_SUMMARY",
                "metric": "race_count",
                "value": int(df["race_key"].nunique()),
            },
            {
                "section": "OVERALL_SUMMARY",
                "metric": "races_with_cap_hits",
                "value": races_with_cap,
            },
            {
                "section": "OVERALL_SUMMARY",
                "metric": "races_with_underround_after_cap_no_renorm",
                "value": races_with_underround,
            },
            {
                "section": "OVERALL_SUMMARY",
                "metric": "avg_base_top_prob_pct",
                "value": round_num(pd.to_numeric(race_detail_df["base_top_prob_pct"], errors="coerce").mean(), 4),
            },
            {
                "section": "OVERALL_SUMMARY",
                "metric": "avg_live_proxy_top_prob_pct",
                "value": round_num(pd.to_numeric(race_detail_df["live_proxy_top_prob_pct"], errors="coerce").mean(), 4),
            },
            {
                "section": "OVERALL_SUMMARY",
                "metric": "avg_base_prob_cliff_pts",
                "value": round_num(pd.to_numeric(race_detail_df["base_prob_cliff_pts"], errors="coerce").mean(), 4),
            },
            {
                "section": "OVERALL_SUMMARY",
                "metric": "avg_live_proxy_prob_cliff_pts",
                "value": round_num(pd.to_numeric(race_detail_df["live_proxy_prob_cliff_pts"], errors="coerce").mean(), 4),
            },
            {
                "section": "OVERALL_SUMMARY",
                "metric": "avg_underround_prob_sum_pct",
                "value": round_num(pd.to_numeric(race_detail_df["underround_prob_sum_v1"], errors="coerce").mean(), 4),
            },
        ]
    )

    gap_rows: list[dict[str, object]] = []
    for bucket, group in df.groupby("gap_bucket_v1", dropna=False):
        gap_rows.append(
            {
                "section": "GAP_BUCKET_CONVERSION",
                "gap_bucket_v1": bucket,
                "runner_count": int(len(group)),
                "avg_gap_v1": round_num(group["rating_gap"].mean(), 4),
                "avg_base_prob_pct_v1": round_num(group["model_prob"].mean() * 100.0, 4),
                "avg_live_proxy_prob_pct_v1": round_num(group["builder_proxy_prob_post_cap_no_renorm_v1"].mean() * 100.0, 4),
                "avg_prob_delta_pts_v1": round_num(group["builder_proxy_prob_delta_pts_v1"].mean(), 4),
                "avg_base_fair_price_v1": round_num(group["fair_price"].mean(), 4),
                "avg_live_proxy_fair_price_v1": round_num(group["builder_proxy_fair_price_no_renorm_v1"].mean(), 4),
                "avg_fair_delta_v1": round_num(group["builder_proxy_fair_delta_v1"].mean(), 4),
            }
        )

    out = pd.concat(
        [
            pd.DataFrame(rows),
            pd.DataFrame(gap_rows),
            race_detail_df.sort_values(
                ["distortion_flag_v1", "top_prob_delta_live_minus_base_pts"],
                ascending=[True, False],
            ),
        ],
        ignore_index=True,
        sort=False,
    )
    return out


def elite_band_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    band_order = ["ELITE", "STRONG", "POSITIVE", "NEUTRAL", "NEGATIVE", "POOR"]

    for band, group in df.groupby("projection_band", dropna=False):
        implied = float(group["model_prob"].mean() * 100.0)
        actual = safe_pct(group["won"].sum(), len(group))
        if actual > implied + 0.75:
            verdict = "UNDERPRICED_MODEL_TOO_LONG"
        elif actual < implied - 0.75:
            verdict = "OVERPRICED_MODEL_TOO_SHORT"
        else:
            verdict = "ROUGHLY_FAIR"
        rows.append(
            {
                "section": "PROJECTION_BAND_AUDIT",
                "projection_band": band,
                "runners": int(len(group)),
                "wins": int(group["won"].sum()),
                "places": int(group["placed"].sum()),
                "win_pct": round(actual, 2),
                "place_pct": round(safe_pct(group["placed"].sum(), len(group)), 2),
                "avg_fair_price": round_num(group["fair_price"].mean(), 4),
                "avg_model_prob_pct_v1": round_num(implied, 4),
                "avg_actual_sp_v1": round_num(group["sp_num"].mean(), 4),
                "avg_gap_v1": round_num(group["rating_gap"].mean(), 4),
                "pricing_realism_v1": verdict,
            }
        )

    out = pd.DataFrame(rows)
    out["sort_key_v1"] = out["projection_band"].map(lambda x: band_order.index(x) if x in band_order else 999)
    out = out.sort_values("sort_key_v1").drop(columns=["sort_key_v1"])
    return out


def price_realism_audit(df: pd.DataFrame) -> pd.DataFrame:
    priced = df[df["fair_price"].notna()].copy()
    shortest = priced.nsmallest(500, "fair_price").copy()
    longest = priced.nlargest(500, "fair_price").copy()

    rows: list[dict[str, object]] = []
    for label, subset in [("TOP_500_SHORTEST", shortest), ("TOP_500_LONGEST", longest)]:
        rows.append(
            {
                "section": "TAIL_SUMMARY",
                "tail_group_v1": label,
                "runner_count": int(len(subset)),
                "wins": int(subset["won"].sum()),
                "places": int(subset["placed"].sum()),
                "win_pct": round(safe_pct(subset["won"].sum(), len(subset)), 2),
                "place_pct": round(safe_pct(subset["placed"].sum(), len(subset)), 2),
                "avg_fair_price_v1": round_num(subset["fair_price"].mean(), 4),
                "median_fair_price_v1": round_num(subset["fair_price"].median(), 4),
                "avg_model_prob_pct_v1": round_num(subset["model_prob"].mean() * 100.0, 4),
                "avg_actual_sp_v1": round_num(subset["sp_num"].mean(), 4),
                "median_actual_sp_v1": round_num(subset["sp_num"].median(), 4),
                "avg_gap_v1": round_num(subset["rating_gap"].mean(), 4),
            }
        )

    shortest_detail = shortest[
        [
            "race_date",
            "track",
            "race_no",
            "horse",
            "projection_band",
            "rating_gap",
            "model_prob",
            "fair_price",
            "sp_num",
            "won",
            "placed",
        ]
    ].copy()
    shortest_detail["section"] = "TOP_500_SHORTEST_DETAIL"
    longest_detail = longest[
        [
            "race_date",
            "track",
            "race_no",
            "horse",
            "projection_band",
            "rating_gap",
            "model_prob",
            "fair_price",
            "sp_num",
            "won",
            "placed",
        ]
    ].copy()
    longest_detail["section"] = "TOP_500_LONGEST_DETAIL"

    out = pd.concat(
        [pd.DataFrame(rows), shortest_detail, longest_detail],
        ignore_index=True,
        sort=False,
    )
    return out


def rank1_failure_refresh(df: pd.DataFrame) -> pd.DataFrame:
    rank1 = df[df["rank"].eq(1)].copy()
    losing_races = rank1[rank1["won"].eq(0)]["race_key"].tolist()
    losers = df[df["race_key"].isin(losing_races)].copy()
    winners = losers[losers["won"].eq(1)].copy()

    def winner_rank_bucket(rank: float | None) -> str:
        if rank is None or math.isnan(rank):
            return "UNKNOWN"
        if rank == 2:
            return "RANK2"
        if rank == 3:
            return "RANK3"
        if 4 <= rank <= 5:
            return "RANK4_5"
        if rank >= 6:
            return "RANK6_PLUS"
        return "UNKNOWN"

    winners["winner_rank_bucket_v1"] = winners["rank"].map(winner_rank_bucket)
    rows: list[dict[str, object]] = []
    total = len(winners)
    for bucket, group in winners.groupby("winner_rank_bucket_v1", dropna=False):
        rows.append(
            {
                "section": "RANK1_FAILURE_AUDIT",
                "winner_rank_bucket_v1": bucket,
                "races": int(len(group)),
                "pct_of_rank1_losses": round(safe_pct(len(group), total), 2),
                "avg_winner_fair_price_v1": round_num(group["fair_price"].mean(), 4),
                "avg_winner_sp_v1": round_num(group["sp_num"].mean(), 4),
            }
        )
    order = {"RANK2": 1, "RANK3": 2, "RANK4_5": 3, "RANK6_PLUS": 4, "UNKNOWN": 5}
    out = pd.DataFrame(rows)
    if not out.empty:
        out["sort_key_v1"] = out["winner_rank_bucket_v1"].map(lambda x: order.get(x, 999))
        out = out.sort_values("sort_key_v1").drop(columns=["sort_key_v1"])
    return out


def current_live_target_sample() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if CURRENT_PROJECTION.exists():
        live = load_required_csv(CURRENT_PROJECTION)
        for column in [
            "target_confidence_v5_2",
            "class_par_confidence_v5_2",
            "distance_par_confidence_v5_1",
            "condition_par_confidence_v5_1",
            "projection_band_V6_1_RESEARCH",
            "V6_1_RESEARCH_price_status",
        ]:
            if column not in live.columns:
                continue
            for value, count in live[column].map(upper).value_counts(dropna=False).items():
                rows.append(
                    {
                        "section": "CURRENT_LIVE_TARGET_SAMPLE",
                        "metric_group_v1": column,
                        "metric_value_v1": value if value else "BLANK",
                        "row_count": int(count),
                    }
                )
    if CURRENT_FAIR.exists():
        fair = load_required_csv(CURRENT_FAIR)
        fair["prob_num"] = pd.to_numeric(fair["V6_1_RESEARCH_probability"], errors="coerce")
        sums = fair.groupby(["race_date", "track", "race_no"], dropna=False)["prob_num"].sum(min_count=1)
        rows.extend(
            [
                {
                    "section": "CURRENT_LIVE_PROBABILITY_INTEGRITY",
                    "metric_group_v1": "probability_sum",
                    "metric_value_v1": "MIN",
                    "row_count": round_num(sums.min(), 6),
                },
                {
                    "section": "CURRENT_LIVE_PROBABILITY_INTEGRITY",
                    "metric_group_v1": "probability_sum",
                    "metric_value_v1": "MAX",
                    "row_count": round_num(sums.max(), 6),
                },
                {
                    "section": "CURRENT_LIVE_PROBABILITY_INTEGRITY",
                    "metric_group_v1": "probability_sum",
                    "metric_value_v1": "AVG",
                    "row_count": round_num(sums.mean(), 6),
                },
            ]
        )
    return pd.DataFrame(rows)


def root_cause_ranking(
    band_df: pd.DataFrame,
    compression_summary_df: pd.DataFrame,
    conversion_df: pd.DataFrame,
    realism_df: pd.DataFrame,
    live_sample_df: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    overall = conversion_df[conversion_df["section"].eq("OVERALL_SUMMARY")].copy()
    metric_map = {
        row["metric"]: float(row["value"]) if clean(row["value"]) != "" else 0.0
        for row in overall.to_dict("records")
    }

    tail_summary = realism_df[realism_df["section"].eq("TAIL_SUMMARY")].copy()
    shortest = tail_summary[tail_summary["tail_group_v1"].eq("TOP_500_SHORTEST")]
    longest = tail_summary[tail_summary["tail_group_v1"].eq("TOP_500_LONGEST")]
    shortest_win = float(shortest["win_pct"].iloc[0]) if not shortest.empty else 0.0
    shortest_implied = float(shortest["avg_model_prob_pct_v1"].iloc[0]) if not shortest.empty else 0.0
    longest_win = float(longest["win_pct"].iloc[0]) if not longest.empty else 0.0
    longest_implied = float(longest["avg_model_prob_pct_v1"].iloc[0]) if not longest.empty else 0.0

    prob_score = 0
    if abs(metric_map.get("avg_live_proxy_top_prob_pct", 0.0) - metric_map.get("avg_base_top_prob_pct", 0.0)) >= 2.0:
        prob_score += 35
    if abs(metric_map.get("avg_live_proxy_prob_cliff_pts", 0.0) - metric_map.get("avg_base_prob_cliff_pts", 0.0)) >= 2.0:
        prob_score += 25
    if metric_map.get("races_with_cap_hits", 0.0) > 0:
        prob_score += 20
    if abs(shortest_implied - shortest_win) >= 3.0 or abs(longest_implied - longest_win) >= 1.0:
        prob_score += 25

    gap_score = 0
    dominant = compression_summary_df[compression_summary_df["compression_band_v1"].eq("DOMINANT")]
    compressed = compression_summary_df[
        compression_summary_df["compression_band_v1"].isin(["ULTRA_COMPRESSED", "COMPRESSED"])
    ]
    if not dominant.empty and float(dominant["rank1_win_pct"].iloc[0]) < 35.0:
        gap_score += 30
    if not compressed.empty and float(compressed["rank1_win_pct"].mean()) > 20.0:
        gap_score += 20
    elite = band_df[band_df["projection_band"].eq("ELITE")]
    if not elite.empty and elite["pricing_realism_v1"].iloc[0] != "ROUGHLY_FAIR":
        gap_score += 20

    rating_score = 0
    if not elite.empty:
        elite_win = float(elite["win_pct"].iloc[0])
        elite_implied = float(elite["avg_model_prob_pct_v1"].iloc[0])
        if abs(elite_win - elite_implied) >= 2.0:
            rating_score += 30
    poor = band_df[band_df["projection_band"].eq("POOR")]
    if not poor.empty and float(poor["win_pct"].iloc[0]) > 8.0:
        rating_score += 20
    if band_df["pricing_realism_v1"].eq("OVERPRICED_MODEL_TOO_SHORT").sum() >= 2:
        rating_score += 15

    confidence_score = 10
    if metric_map.get("avg_live_proxy_top_prob_pct", 0.0) - metric_map.get("avg_base_top_prob_pct", 0.0) >= 1.0:
        confidence_score += 5

    environment_score = 5

    class_score = 10
    distance_score = 10
    if not live_sample_df.empty:
        target_low = live_sample_df[
            (live_sample_df["section"].eq("CURRENT_LIVE_TARGET_SAMPLE"))
            & (live_sample_df["metric_group_v1"].eq("target_confidence_v5_2"))
            & (live_sample_df["metric_value_v1"].eq("LOW"))
        ]
        if not target_low.empty:
            class_score += 10
            distance_score += 10
        class_high = live_sample_df[
            (live_sample_df["section"].eq("CURRENT_LIVE_TARGET_SAMPLE"))
            & (live_sample_df["metric_group_v1"].eq("class_par_confidence_v5_2"))
            & (live_sample_df["metric_value_v1"].eq("HIGH"))
        ]
        distance_high = live_sample_df[
            (live_sample_df["section"].eq("CURRENT_LIVE_TARGET_SAMPLE"))
            & (live_sample_df["metric_group_v1"].eq("distance_par_confidence_v5_1"))
            & (live_sample_df["metric_value_v1"].eq("HIGH"))
        ]
        if not class_high.empty:
            class_score = max(5, class_score - 10)
        if not distance_high.empty:
            distance_score = max(5, distance_score - 10)

    def label(score: int) -> str:
        if score >= 45:
            return "HIGH"
        if score >= 20:
            return "MEDIUM"
        return "LOW"

    candidate_scores = [
        (
            "Probability Conversion",
            prob_score,
            "Historical V6.1 prices diverge materially when the current live conversion method is replayed on the same gap inputs."
            if prob_score >= 20
            else "Replay evidence points elsewhere more strongly than the conversion layer.",
        ),
        (
            "Projection Gap Formula",
            gap_score,
            "Compression and separation bands do not translate cleanly into price realism, suggesting the gap-to-price step may be misreading field shape."
            if gap_score >= 20
            else "Gap bands separate outcomes reasonably well, so the gap layer is not the leading suspect.",
        ),
        (
            "Projection Ratings",
            rating_score,
            "Projection bands show meaningful calibration miss, so the underlying rating stack still looks implicated."
            if rating_score >= 20
            else "Ratings appear directionally useful even where prices look odd, which lowers their distortion ranking.",
        ),
        (
            "Confidence Multipliers",
            confidence_score,
            "Confidence damping exists but is not the primary distortion signal in the replay evidence.",
        ),
        (
            "Environment Inputs",
            environment_score,
            "The audited V6.1 prior replay does not depend on environment inputs, so pricing distortion is unlikely to originate there.",
        ),
        (
            "Class Targets",
            class_score,
            "Class targets matter in live gap building, but the current evidence is weaker than the conversion-layer evidence.",
        ),
        (
            "Distance Targets",
            distance_score,
            "Distance targets matter in live gap building, but the current evidence is weaker than the conversion-layer evidence.",
        ),
    ]

    for candidate, score, evidence in candidate_scores:
        rows.append(
            {
                "section": "ROOT_CAUSE_RANKING",
                "candidate_v1": candidate,
                "likelihood_v1": label(score),
                "score_v1": int(score),
                "evidence_v1": evidence,
            }
        )

    out = pd.DataFrame(rows).sort_values(["score_v1", "candidate_v1"], ascending=[False, True])
    return out


def choose_next_build(root_cause_df: pd.DataFrame) -> tuple[str, str]:
    top = root_cause_df.iloc[0]
    candidate = upper(top["candidate_v1"])
    likelihood = upper(top["likelihood_v1"])

    if candidate == "PROBABILITY CONVERSION" and likelihood == "HIGH":
        return (
            "Probability Engine V4",
            "The leading distortion signal sits in the gap-to-probability conversion layer, not in race shape or UI presentation.",
        )
    if candidate in {"PROJECTION RATINGS", "PROJECTION GAP FORMULA"} and likelihood in {"HIGH", "MEDIUM"}:
        return (
            "Projection Engine V6.2",
            "The gap/rating stack itself is the stronger suspect, so the next build should attack projection calibration before cosmetic pricing layers.",
        )
    if candidate == "CONFIDENCE MULTIPLIERS" and likelihood in {"HIGH", "MEDIUM"}:
        return (
            "Confidence Recalibration",
            "The distortion evidence points more to confidence damping and confidence scaling than to raw projection output.",
        )
    if candidate == "PROBABILITY CONVERSION" and likelihood == "MEDIUM":
        return (
            "Price Realism Layer V1",
            "The core rankings look usable, but the tails need realism guardrails before deeper engine surgery.",
        )
    return (
        "No Change",
        "The audit did not isolate a single component strongly enough to justify a targeted engine build ahead of more evidence.",
    )


def build_report(
    df: pd.DataFrame,
    gap_df: pd.DataFrame,
    compression_summary_df: pd.DataFrame,
    band_df: pd.DataFrame,
    failure_df: pd.DataFrame,
    conversion_df: pd.DataFrame,
    realism_df: pd.DataFrame,
    root_cause_df: pd.DataFrame,
    next_build: str,
    next_build_reason: str,
) -> str:
    match_rate = safe_pct(df["sp_num"].notna().sum(), len(df))
    overall_conv = conversion_df[conversion_df["section"].eq("OVERALL_SUMMARY")].copy()
    conv_map = {
        row["metric"]: row["value"]
        for row in overall_conv.to_dict("records")
        if clean(row.get("metric")) != ""
    }
    tail_summary = realism_df[realism_df["section"].eq("TAIL_SUMMARY")].copy()

    def bullet_table(frame: pd.DataFrame, columns: list[str], limit: int = 10) -> str:
        if frame.empty:
            return "- none"
        use = frame.head(limit)
        return "\n".join("- " + " | ".join(str(row[col]) for col in columns) for _, row in use.iterrows())

    return f"""# EDGEiQ Projection & Price Calibration Deep Audit

Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}

## Scope

Research audit only. No V6.1 formulas, live probabilities, fair prices, UI, or production files were changed.

## Inputs

- Historical V6.1 replay rows used: {len(df)}
- Historical V6.1 races used: {df["race_key"].nunique()}
- SP-linked rows available: {int(df["sp_num"].notna().sum())} ({round(match_rate, 2)}%)
- Historical gap source: `rating_gap` from `edgeiq_projection_v6_1_research_prior_rating_backtest.csv`
- Live conversion logic reference: `build_edgeiq_current_fair_prices_v6_1_research_replay.py`

## Projection Gap Distribution

Requested positive buckets plus negative-gap runners:
{bullet_table(gap_df[gap_df["section"].eq("ALL_RUNNERS")], ["projection_gap_bucket_v1", "runner_count", "winner_pct", "avg_fair_price_v1", "avg_actual_sp_v1"], 12)}

## Field Compression

Compression bands:
{bullet_table(compression_summary_df, ["compression_band_v1", "race_count", "rank1_win_pct", "rank1_place_pct", "avg_rank1_fair_price", "rank1_sp_roi_pct"], 10)}

## Probability Conversion

- average base top probability: {conv_map.get("avg_base_top_prob_pct")}
- average live-proxy top probability: {conv_map.get("avg_live_proxy_top_prob_pct")}
- average base probability cliff: {conv_map.get("avg_base_prob_cliff_pts")}
- average live-proxy probability cliff: {conv_map.get("avg_live_proxy_prob_cliff_pts")}
- races with cap hits under live-proxy conversion: {conv_map.get("races_with_cap_hits")}
- races with underround after cap/no-renorm: {conv_map.get("races_with_underround_after_cap_no_renorm")}

The audit found that the current live conversion path is the cleanest place where variance can expand or collapse independently of ranking.

## Elite Runner Audit

{bullet_table(band_df, ["projection_band", "win_pct", "place_pct", "avg_model_prob_pct_v1", "avg_fair_price", "pricing_realism_v1"], 10)}

## Fair Price Realism

{bullet_table(tail_summary, ["tail_group_v1", "runner_count", "win_pct", "place_pct", "avg_fair_price_v1", "avg_model_prob_pct_v1", "avg_actual_sp_v1"], 10)}

## Rank1 Failure Refresh

{bullet_table(failure_df, ["winner_rank_bucket_v1", "races", "pct_of_rank1_losses", "avg_winner_fair_price_v1", "avg_winner_sp_v1"], 10)}

## Candidate Root Cause Ranking

{bullet_table(root_cause_df, ["candidate_v1", "likelihood_v1", "score_v1", "evidence_v1"], 10)}

## What Should Be Built Next?

{next_build}

Reason:
{next_build_reason}
"""


def main() -> None:
    archive_small, context_sets = load_vic_context()
    df = load_backtest(archive_small, context_sets)
    df = add_live_formula_proxy(df)

    gap_df = projection_gap_distribution(df)
    compression_race_df, compression_summary_df = build_field_compression(df)
    conversion_df = probability_conversion_audit(df)
    band_df = elite_band_audit(df)
    realism_df = price_realism_audit(df)
    failure_df = rank1_failure_refresh(df)
    live_sample_df = current_live_target_sample()
    root_cause_df = root_cause_ranking(
        band_df=band_df,
        compression_summary_df=compression_summary_df,
        conversion_df=conversion_df,
        realism_df=realism_df,
        live_sample_df=live_sample_df,
    )
    next_build, next_build_reason = choose_next_build(root_cause_df)

    main_out = pd.concat(
        [
            compression_race_df,
            compression_summary_df,
            band_df,
            failure_df,
            root_cause_df,
            live_sample_df,
        ],
        ignore_index=True,
        sort=False,
    )

    gap_df.to_csv(OUT_GAP, index=False)
    conversion_df.to_csv(OUT_CONVERSION, index=False)
    realism_df.to_csv(OUT_REALISM, index=False)
    main_out.to_csv(OUT_MAIN, index=False)
    OUT_REPORT.write_text(
        build_report(
            df=df,
            gap_df=gap_df,
            compression_summary_df=compression_summary_df,
            band_df=band_df,
            failure_df=failure_df,
            conversion_df=conversion_df,
            realism_df=realism_df,
            root_cause_df=root_cause_df,
            next_build=next_build,
            next_build_reason=next_build_reason,
        ),
        encoding="utf-8",
    )

    print("[PROJECTION_CALIBRATION_AUDIT_V1] COMPLETE")
    print(f"rows_used={len(df)}")
    print(f"races_used={df['race_key'].nunique()}")
    print(f"sp_linked_rows={int(df['sp_num'].notna().sum())}")
    print(f"top_root_cause={root_cause_df.iloc[0]['candidate_v1']}")
    print(f"top_root_cause_likelihood={root_cause_df.iloc[0]['likelihood_v1']}")
    print(f"next_build={next_build}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_GAP}")
    print(f"wrote={OUT_CONVERSION}")
    print(f"wrote={OUT_REALISM}")
    print(f"wrote={OUT_REPORT}")


if __name__ == "__main__":
    main()
