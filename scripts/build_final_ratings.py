import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from normalise_race_class import apply_race_class_normalisation, class_rating_from_band

print("=" * 80)
print("BUILD FINAL RATINGS - HARD KEY MATCH + BASELINE SAFE")
print("=" * 80)

FIELDS_PATH = "public/data/race_fields.csv"
FORM_PATH = "public/data/form_engine_context.csv"
RUNS_PATH = r"..\..\outputs\enrichment\run_context.csv"
OUT_PATH = "public/data/ratings_final_v2.csv"
JOCKEY_CONFIG_PATH = "config/jockey_adjustments.csv"
JOCKEY_STATS_PATH = "public/data/jockey_stats.csv"
TRAINER_STATS_PATH = "public/data/trainer_stats.csv"
COMBO_STATS_PATH = "public/data/trainer_jockey_combo_stats.csv"
PACE_PRESSURE_PATH = "public/data/pace_pressure.csv"
MARKET_SIGNALS_PATH = "public/data/market_signals.csv"
BASELINE_FORM_RATING = 55.0
COUNTRY_SUFFIX_RE = re.compile(
    r"\s*\((?:AUS|NZ|IRE|GB|UK|USA|FR|GER|JPN|SAF|ARG|CAN|CHI|ITY|BRZ|UAE|HK|SIN|KOR)\)\s*$",
    re.IGNORECASE,
)


def hard_horse_key(value):
    if pd.isna(value):
        return ""
    s = str(value).upper().strip()
    if not s or s in {"NAN", "NONE", "NULL", "<NA>"}:
        return ""
    s = s.replace("’", "").replace("'", "").replace("`", "")
    s = COUNTRY_SUFFIX_RE.sub("", s)
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\b([A-Z])\s+([A-Z])\b", r"\1\2", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def parse_num(x):
    if pd.isna(x):
        return np.nan
    m = re.search(r"\d+", str(x))
    return float(m.group()) if m else np.nan


def parse_margin(x):
    if pd.isna(x):
        return np.nan
    s = str(x).lower().strip()
    specials = {"nk": 0.30, "neck": 0.30, "hd": 0.20, "head": 0.20, "shd": 0.10, "short head": 0.10, "nose": 0.05}
    if s in specials:
        return specials[s]
    m = re.search(r"([\d\.]+)", s)
    return float(m.group(1)) if m else np.nan


def class_score(row):
    return class_rating_from_band(
        row.get("race_class_clean", row.get("race_class", "")),
        row.get("race_class_band", ""),
        row.get("class_confidence", ""),
    )


def ensure_col(df, col, default=np.nan):
    if col not in df.columns:
        df[col] = default


def lengths_to_points(distance):
    d = parse_num(distance)
    if pd.isna(d):
        return 1.8
    if d <= 1200:
        return 2.5
    if 1300 <= d <= 1500:
        return 1.5
    if 1501 <= d <= 1900:
        return 1.7
    if d >= 2200:
        return 2.0
    return 1.8


def parse_weight(x):
    if pd.isna(x):
        return np.nan
    s = str(x)
    m = re.search(r"(\d{2}(?:\.\d+)?)\s*kg", s, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"\b(\d{2}(?:\.\d+)?)\b", s)
    return float(m.group(1)) if m else np.nan


def norm_name(value):
    return re.sub(r"[^A-Z ]+", " ", str(value or "").upper()).strip()


def load_jockey_adjustments(path):
    cols = ["jockey", "adjustment_lengths", "notes"]
    try:
        cfg = pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame(columns=cols + ["jockey_key"])
    for col in cols:
        if col not in cfg.columns:
            cfg[col] = "" if col != "adjustment_lengths" else 0
    cfg["jockey_key"] = cfg["jockey"].apply(norm_name)
    cfg["adjustment_lengths"] = pd.to_numeric(cfg["adjustment_lengths"], errors="coerce").fillna(0.0)
    return cfg[cfg["jockey_key"].ne("")].copy()


def load_jockey_stats(path):
    cols = [
        "jockey_key",
        "jockey_stat_rating_points",
        "jockey_tier",
        "win_sr_last_100",
        "place_sr_last_100",
        "actual_minus_expected_last_100",
        "roi_last_100",
        "best_track",
        "best_distance_band",
        "best_trainer_combo",
    ]
    try:
        stats = pd.read_csv(path, low_memory=False)
    except FileNotFoundError:
        return pd.DataFrame(columns=cols)
    for col in cols:
        if col not in stats.columns:
            stats[col] = np.nan if col not in {"jockey_key", "jockey_tier", "best_track", "best_distance_band", "best_trainer_combo"} else ""
    stats["jockey_key"] = stats["jockey_key"].fillna("").astype(str).apply(norm_name)
    stats["jockey_stat_rating_points"] = pd.to_numeric(stats["jockey_stat_rating_points"], errors="coerce").fillna(0.0).clip(-3, 3)
    stats["win_sr_last_100"] = pd.to_numeric(stats["win_sr_last_100"], errors="coerce")
    stats["place_sr_last_100"] = pd.to_numeric(stats["place_sr_last_100"], errors="coerce")
    stats["actual_minus_expected_last_100"] = pd.to_numeric(stats["actual_minus_expected_last_100"], errors="coerce")
    stats["roi_last_100"] = pd.to_numeric(stats["roi_last_100"], errors="coerce")
    stats = stats[stats["jockey_key"].ne("")].drop_duplicates("jockey_key", keep="first")
    return stats[cols].copy()


def load_trainer_stats(path):
    cols = [
        "trainer_key",
        "trainer_stat_rating_points",
        "trainer_tier",
        "win_sr_last_100",
        "roi_last_100",
        "actual_minus_expected_last_100",
        "best_track",
        "best_distance_band",
        "best_condition",
        "best_class_band",
    ]
    try:
        stats = pd.read_csv(path, low_memory=False)
    except FileNotFoundError:
        return pd.DataFrame(columns=cols)
    for col in cols:
        if col not in stats.columns:
            stats[col] = "" if col in {"trainer_key", "trainer_tier", "best_track", "best_distance_band", "best_condition", "best_class_band"} else np.nan
    stats["trainer_key"] = stats["trainer_key"].fillna("").astype(str).apply(norm_name)
    stats["trainer_stat_rating_points"] = pd.to_numeric(stats["trainer_stat_rating_points"], errors="coerce").fillna(0.0).clip(-2, 2)
    stats["win_sr_last_100"] = pd.to_numeric(stats["win_sr_last_100"], errors="coerce")
    stats["roi_last_100"] = pd.to_numeric(stats["roi_last_100"], errors="coerce")
    stats["actual_minus_expected_last_100"] = pd.to_numeric(stats["actual_minus_expected_last_100"], errors="coerce")
    stats = stats[stats["trainer_key"].ne("")].drop_duplicates("trainer_key", keep="first")
    return stats[cols].copy()


def load_combo_stats(path):
    cols = [
        "trainer_key",
        "jockey_key",
        "rides",
        "win_sr",
        "actual_minus_expected",
        "roi",
        "combo_rating_points",
        "combo_label",
    ]
    try:
        stats = pd.read_csv(path, low_memory=False)
    except FileNotFoundError:
        return pd.DataFrame(columns=cols)
    for col in cols:
        if col not in stats.columns:
            stats[col] = "" if col in {"trainer_key", "jockey_key", "combo_label"} else np.nan
    stats["trainer_key"] = stats["trainer_key"].fillna("").astype(str).apply(norm_name)
    stats["jockey_key"] = stats["jockey_key"].fillna("").astype(str).apply(norm_name)
    stats["rides"] = pd.to_numeric(stats["rides"], errors="coerce").fillna(0)
    stats["win_sr"] = pd.to_numeric(stats["win_sr"], errors="coerce")
    stats["actual_minus_expected"] = pd.to_numeric(stats["actual_minus_expected"], errors="coerce")
    stats["roi"] = pd.to_numeric(stats["roi"], errors="coerce")
    stats["combo_rating_points"] = pd.to_numeric(stats["combo_rating_points"], errors="coerce").fillna(0.0).clip(-1.5, 1.5)
    stats.loc[stats["rides"] < 5, "combo_rating_points"] = 0.0
    stats = stats[stats["trainer_key"].ne("") & stats["jockey_key"].ne("")]
    stats = stats.sort_values(["trainer_key", "jockey_key", "rides"], ascending=[True, True, False]).drop_duplicates(["trainer_key", "jockey_key"], keep="first")
    return stats[cols].copy()


def load_pace_pressure(path):
    cols = [
        "race_date",
        "track",
        "race_no",
        "horse_key",
        "run_style",
        "early_speed_score",
        "expected_tempo",
        "pace_pressure_score",
        "uncontested_lead_possible",
        "pace_collapse_risk",
        "swooper_advantage",
        "pace_setup_rating",
        "likely_beneficiary",
        "likely_disadvantaged",
        "pace_adj_points",
        "pace_setup_label",
    ]
    try:
        pace = pd.read_csv(path, low_memory=False)
    except FileNotFoundError:
        return pd.DataFrame(columns=cols)
    for col in cols:
        if col not in pace.columns:
            pace[col] = "" if col in {"race_date", "track", "horse_key", "run_style", "expected_tempo", "uncontested_lead_possible", "pace_collapse_risk", "swooper_advantage", "likely_beneficiary", "likely_disadvantaged", "pace_setup_label"} else np.nan
    pace["race_date"] = pd.to_datetime(pace["race_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    pace["track"] = pace["track"].astype(str).str.upper().str.strip()
    pace["race_no"] = pd.to_numeric(pace["race_no"], errors="coerce").fillna(0).astype(int)
    pace["horse_key"] = pace["horse_key"].apply(hard_horse_key)
    pace["pace_adj_points"] = pd.to_numeric(pace["pace_adj_points"], errors="coerce").fillna(0.0).clip(-2, 2)
    pace["pace_setup_rating"] = pd.to_numeric(pace["pace_setup_rating"], errors="coerce")
    pace["pace_pressure_score"] = pd.to_numeric(pace["pace_pressure_score"], errors="coerce")
    pace["early_speed_score"] = pd.to_numeric(pace["early_speed_score"], errors="coerce")
    pace = pace[pace["horse_key"].ne("")].drop_duplicates(["race_date", "track", "race_no", "horse_key"], keep="first")
    return pace[cols].copy()


def load_market_signals(path):
    cols = [
        "race_date",
        "track",
        "race_no",
        "horse_key",
        "current_price",
        "market_signal",
        "market_confidence",
    ]
    try:
        market = pd.read_csv(path, low_memory=False)
    except FileNotFoundError:
        return pd.DataFrame(columns=cols)
    for col in cols:
        if col not in market.columns:
            market[col] = "" if col in {"race_date", "track", "horse_key", "market_signal", "market_confidence"} else np.nan
    market["race_date"] = pd.to_datetime(market["race_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    market["track"] = market["track"].astype(str).str.upper().str.strip()
    market["race_no"] = pd.to_numeric(market["race_no"], errors="coerce").fillna(0).astype(int)
    market["horse_key"] = market["horse_key"].apply(hard_horse_key)
    market["current_price"] = pd.to_numeric(market["current_price"], errors="coerce")
    market["market_signal"] = market["market_signal"].fillna("").astype(str).str.upper().str.strip()
    market["market_confidence"] = market["market_confidence"].fillna("").astype(str).str.upper().str.strip()
    market = market[market["horse_key"].ne("")].drop_duplicates(["race_date", "track", "race_no", "horse_key"], keep="last")
    return market[cols].copy()


def apply_handicapper_layer(df, runs):
    df = df.copy()
    runs = runs.copy()
    df["lengths_point_scale"] = df["today_distance_m"].apply(lengths_to_points)
    df["elite_today_rating_before_handicapper"] = pd.to_numeric(df["elite_today_rating"], errors="coerce")

    for flag in ["held_up", "checked", "wide", "slow", "vet", "has_gear_change"]:
        ensure_col(runs, flag, 0)
        runs[flag] = pd.to_numeric(runs[flag], errors="coerce").fillna(0)

    runs["lengths_point_scale_run"] = runs["distance_m"].apply(lengths_to_points)
    runs["trip_upgrade_lengths"] = (
        runs["held_up"].clip(0, 1) * 1.00
        + runs["checked"].clip(0, 1) * 1.00
        + runs["wide"].clip(0, 1) * 0.75
        + runs["slow"].clip(0, 1) * 0.50
    )
    runs["trip_adj_run_points"] = (runs["trip_upgrade_lengths"] * runs["lengths_point_scale_run"]).clip(0, 5)

    for col in ["weight_carried", "weight", "probable_weight"]:
        ensure_col(runs, col)
    weight_source = runs["weight_carried"].combine_first(runs["weight"]).combine_first(runs["probable_weight"]).combine_first(runs.get("raw_text"))
    runs["weight_carried_num"] = weight_source.apply(parse_weight)
    runs["race_weight_group"] = runs["run_date"].astype(str) + "|" + runs["track"].astype(str) + "|" + runs["distance_m"].round(0).astype(str)
    runs["race_avg_weight"] = runs.groupby("race_weight_group")["weight_carried_num"].transform("mean")
    runs["weight_adj_run_points"] = ((runs["weight_carried_num"] - runs["race_avg_weight"]) * 1.5).clip(-3, 3).fillna(0)

    trip_rows = []
    for horse_key, g in runs.dropna(subset=["run_date"]).sort_values("run_date", ascending=False).groupby("horse_key"):
        recent = g.head(5)
        trip_avg = float(recent["trip_adj_run_points"].mean()) if len(recent) else 0.0
        weight_avg = float(recent["weight_adj_run_points"].mean()) if len(recent) else 0.0
        trip_rows.append({
            "horse_key": horse_key,
            "trip_adj_points": round(min(3.0, max(0.0, trip_avg)), 3),
            "weight_adj_points": round(max(-3.0, min(3.0, weight_avg)), 3),
            "trip_upgrade_runs": int((recent["trip_adj_run_points"] > 0).sum()),
            "vet_flag_recent": int((recent["vet"].clip(0, 1).sum() + recent.get("lame", 0).clip(0, 1).sum()) > 0) if "lame" in recent.columns else int(recent["vet"].clip(0, 1).sum() > 0),
            "gear_change_recent": int(recent["has_gear_change"].clip(0, 1).sum() > 0),
        })

    trip_df = pd.DataFrame(trip_rows)
    if trip_df.empty:
        trip_df = pd.DataFrame(columns=["horse_key", "trip_adj_points", "weight_adj_points", "trip_upgrade_runs", "vet_flag_recent", "gear_change_recent"])
    df = df.merge(trip_df, on="horse_key", how="left")
    for col in ["trip_adj_points", "weight_adj_points", "trip_upgrade_runs", "vet_flag_recent", "gear_change_recent"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["jockey_key"] = df.get("jockey", "").apply(norm_name)

    jockey_stats = load_jockey_stats(JOCKEY_STATS_PATH)
    if jockey_stats.empty:
        df["jockey_stat_rating_points"] = 0.0
        df["jockey_tier"] = "UNKNOWN"
        df["jockey_recent_win_sr"] = np.nan
        df["jockey_recent_place_sr"] = np.nan
        df["jockey_actual_minus_expected"] = np.nan
        df["jockey_roi_last_100"] = np.nan
        df["jockey_best_track"] = ""
        df["jockey_best_distance_band"] = ""
        df["jockey_best_trainer_combo"] = ""
    else:
        df = df.merge(jockey_stats, on="jockey_key", how="left")
        df["jockey_stat_rating_points"] = pd.to_numeric(df["jockey_stat_rating_points"], errors="coerce").fillna(0.0).clip(-3, 3)
        df["jockey_tier"] = df["jockey_tier"].fillna("UNKNOWN").replace("", "UNKNOWN")
        df["jockey_recent_win_sr"] = pd.to_numeric(df["win_sr_last_100"], errors="coerce")
        df["jockey_recent_place_sr"] = pd.to_numeric(df["place_sr_last_100"], errors="coerce")
        df["jockey_actual_minus_expected"] = pd.to_numeric(df["actual_minus_expected_last_100"], errors="coerce")
        df["jockey_roi_last_100"] = pd.to_numeric(df["roi_last_100"], errors="coerce")
        df["jockey_best_track"] = df["best_track"].fillna("").astype(str)
        df["jockey_best_distance_band"] = df["best_distance_band"].fillna("").astype(str)
        df["jockey_best_trainer_combo"] = df["best_trainer_combo"].fillna("").astype(str)
        df = df.drop(columns=["win_sr_last_100", "place_sr_last_100", "actual_minus_expected_last_100", "roi_last_100", "best_track", "best_distance_band", "best_trainer_combo"], errors="ignore")

    jockey_cfg = load_jockey_adjustments(JOCKEY_CONFIG_PATH)
    if jockey_cfg.empty:
        df["jockey_adj_lengths"] = 0.0
        df["manual_jockey_adj_points"] = 0.0
        df["jockey_adj_label"] = ""
    else:
        df = df.merge(jockey_cfg[["jockey_key", "adjustment_lengths", "notes"]], on="jockey_key", how="left")
        df["jockey_adj_lengths"] = pd.to_numeric(df["adjustment_lengths"], errors="coerce").fillna(0.0)
        df["manual_jockey_adj_points"] = (df["jockey_adj_lengths"] * df["lengths_point_scale"]).clip(-4, 4).round(3)
        df["jockey_adj_label"] = np.where(df["manual_jockey_adj_points"].ne(0), df["notes"].fillna("Manual jockey adjustment applied"), "")
        df = df.drop(columns=["adjustment_lengths", "notes"], errors="ignore")

    if "manual_jockey_adj_points" not in df.columns:
        df["manual_jockey_adj_points"] = 0.0
    df["manual_jockey_adj_points"] = pd.to_numeric(df["manual_jockey_adj_points"], errors="coerce").fillna(0.0).clip(-4, 4)
    df["jockey_adj_points"] = (df["jockey_stat_rating_points"] + df["manual_jockey_adj_points"]).clip(-4, 4).round(3)

    df["trainer_key"] = df.get("trainer", "").apply(norm_name)
    trainer_stats = load_trainer_stats(TRAINER_STATS_PATH)
    if trainer_stats.empty:
        df["trainer_stat_rating_points"] = 0.0
        df["trainer_adj_points"] = 0.0
        df["trainer_adj_label"] = "UNKNOWN"
        df["trainer_tier"] = "UNKNOWN"
        df["trainer_recent_win_sr"] = np.nan
        df["trainer_roi_last_100"] = np.nan
        df["trainer_actual_minus_expected"] = np.nan
        df["trainer_best_track"] = ""
        df["trainer_best_distance_band"] = ""
        df["trainer_best_condition"] = ""
        df["trainer_best_class_band"] = ""
    else:
        df = df.merge(trainer_stats, on="trainer_key", how="left")
        df["trainer_stat_rating_points"] = pd.to_numeric(df["trainer_stat_rating_points"], errors="coerce").fillna(0.0).clip(-2, 2)
        df["trainer_adj_points"] = df["trainer_stat_rating_points"].round(3)
        df["trainer_tier"] = df["trainer_tier"].fillna("UNKNOWN").replace("", "UNKNOWN")
        df["trainer_adj_label"] = df["trainer_tier"]
        df["trainer_recent_win_sr"] = pd.to_numeric(df["win_sr_last_100"], errors="coerce")
        df["trainer_roi_last_100"] = pd.to_numeric(df["roi_last_100"], errors="coerce")
        df["trainer_actual_minus_expected"] = pd.to_numeric(df["actual_minus_expected_last_100"], errors="coerce")
        df["trainer_best_track"] = df["best_track"].fillna("").astype(str)
        df["trainer_best_distance_band"] = df["best_distance_band"].fillna("").astype(str)
        df["trainer_best_condition"] = df["best_condition"].fillna("").astype(str)
        df["trainer_best_class_band"] = df["best_class_band"].fillna("").astype(str)
        df = df.drop(columns=["win_sr_last_100", "roi_last_100", "actual_minus_expected_last_100", "best_track", "best_distance_band", "best_condition", "best_class_band"], errors="ignore")

    combo_stats = load_combo_stats(COMBO_STATS_PATH)
    if combo_stats.empty:
        df["combo_adj_points"] = 0.0
        df["combo_adj_label"] = "NO COMBO SAMPLE"
        df["combo_rides"] = 0
        df["combo_win_sr"] = np.nan
        df["combo_actual_minus_expected"] = np.nan
        df["combo_roi"] = np.nan
    else:
        df = df.merge(combo_stats, on=["trainer_key", "jockey_key"], how="left", suffixes=("", "_combo"))
        df["combo_adj_points"] = pd.to_numeric(df["combo_rating_points"], errors="coerce").fillna(0.0).clip(-1.5, 1.5).round(3)
        df["combo_adj_label"] = df["combo_label"].fillna("NO COMBO SAMPLE").replace("", "NO COMBO SAMPLE")
        df["combo_rides"] = pd.to_numeric(df["rides"], errors="coerce").fillna(0).astype(int)
        df["combo_win_sr"] = pd.to_numeric(df["win_sr"], errors="coerce")
        df["combo_actual_minus_expected"] = pd.to_numeric(df["actual_minus_expected"], errors="coerce")
        df["combo_roi"] = pd.to_numeric(df["roi"], errors="coerce")
        df = df.drop(columns=["rides", "win_sr", "actual_minus_expected", "roi", "combo_rating_points", "combo_label"], errors="ignore")

    df["trainer_adj_points"] = pd.to_numeric(df["trainer_adj_points"], errors="coerce").fillna(0.0).clip(-2, 2).round(3)
    df["combo_adj_points"] = pd.to_numeric(df["combo_adj_points"], errors="coerce").fillna(0.0).clip(-1.5, 1.5).round(3)
    df["total_connections_adj"] = (df["trainer_adj_points"] + df["combo_adj_points"]).clip(-3, 3).round(3)

    pace = load_pace_pressure(PACE_PRESSURE_PATH)
    if pace.empty:
        df["pace_adj_points"] = 0.0
        df["pace_setup_label"] = "NO PACE SAMPLE"
        df["run_style"] = ""
        df["expected_tempo"] = ""
        df["pace_pressure_score"] = np.nan
        df["uncontested_lead_possible"] = ""
        df["pace_collapse_risk"] = ""
        df["swooper_advantage"] = ""
        df["pace_setup_rating"] = np.nan
        df["likely_beneficiary"] = "NO"
        df["likely_disadvantaged"] = "NO"
    else:
        df["race_date_key"] = pd.to_datetime(df.get("race_date"), errors="coerce").dt.strftime("%Y-%m-%d")
        df["race_no_key"] = pd.to_numeric(df.get("race_no"), errors="coerce").fillna(0).astype(int)
        df = df.merge(
            pace,
            left_on=["race_date_key", "track", "race_no_key", "horse_key"],
            right_on=["race_date", "track", "race_no", "horse_key"],
            how="left",
            suffixes=("", "_pace"),
        )
        df["pace_adj_points"] = pd.to_numeric(df["pace_adj_points"], errors="coerce").fillna(0.0).clip(-2, 2).round(3)
        df["pace_setup_label"] = df["pace_setup_label"].fillna("NO PACE SAMPLE").replace("", "NO PACE SAMPLE")
        for col in ["run_style", "expected_tempo", "uncontested_lead_possible", "pace_collapse_risk", "swooper_advantage", "likely_beneficiary", "likely_disadvantaged"]:
            df[col] = df[col].fillna("").astype(str)
        df["pace_pressure_score"] = pd.to_numeric(df["pace_pressure_score"], errors="coerce")
        df["pace_setup_rating"] = pd.to_numeric(df["pace_setup_rating"], errors="coerce")
        df["early_speed_score"] = pd.to_numeric(df["early_speed_score"], errors="coerce")
        df = df.drop(columns=["race_date_key", "race_no_key", "race_date_pace", "race_no_pace"], errors="ignore")

    df["handicapper_adj_total"] = (
        df["trip_adj_points"]
        + df["weight_adj_points"]
        + df["jockey_adj_points"]
        + df["total_connections_adj"]
        + df["pace_adj_points"]
    ).clip(-6, 6).round(3)
    df["handicapper_rating"] = (df["elite_today_rating_before_handicapper"] + df["handicapper_adj_total"]).clip(35, 120).round(3)
    df["elite_today_rating"] = df["handicapper_rating"]
    df["handicapper_context_flags"] = np.select(
        [df["vet_flag_recent"].gt(0), df["gear_change_recent"].gt(0), df["trip_upgrade_runs"].gt(0), df["manual_jockey_adj_points"].ne(0), df["jockey_stat_rating_points"].abs().ge(0.75)],
        ["VET FLAG RECENT", "GEAR CHANGE RECENT", "TRIP UPGRADE", "MANUAL JOCKEY", "JOCKEY STAT"],
        default=""
    )
    return df
MARKET_TEMPERATURE = 11.0
UNIFORM_BLEND = 0.24


def boolish_value(x):
    s = str(x).strip().lower()
    return s in {"1", "true", "yes", "y"}


def add_model_prices(df, rating_col, price_col, prob_col, sum_col=None):
    df = df.copy()
    if "is_scratched" not in df.columns:
        df["is_scratched"] = 0
    if "is_scratched_bool" not in df.columns:
        df["is_scratched_bool"] = df["is_scratched"].apply(boolish_value)
    if sum_col:
        df[sum_col] = np.nan
    df[prob_col] = np.nan

    for _, g in df.groupby("race_id", dropna=False):
        live = g[(~g["is_scratched_bool"]) & pd.to_numeric(g[rating_col], errors="coerce").notna()].copy()
        if live.empty:
            continue
        ratings = pd.to_numeric(live[rating_col], errors="coerce").astype(float)
        if len(live) == 1:
            probs = np.array([1.0])
        else:
            centered = ((ratings - ratings.max()) / MARKET_TEMPERATURE).clip(-6, 6)
            weights = np.exp(centered)
            softmax = weights / weights.sum()
            uniform = np.ones(len(live)) / len(live)
            probs = ((1 - UNIFORM_BLEND) * softmax) + (UNIFORM_BLEND * uniform)
            probs = probs / probs.sum()
        if sum_col:
            df.loc[live.index, sum_col] = float(ratings.sum())
        df.loc[live.index, prob_col] = probs

    df[price_col] = np.where(df[prob_col] > 0, 1 / df[prob_col], np.nan)
    df.loc[df["is_scratched_bool"], price_col] = np.nan
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce").round(3)
    return df


def apply_race_softmax_prices(df):
    df = df.copy()
    if "is_scratched" not in df.columns:
        df["is_scratched"] = 0
    df["is_scratched_bool"] = df["is_scratched"].apply(boolish_value)
    return add_model_prices(df, "elite_today_rating", "elite_rated_price", "prob", "rating_sum")


def confidence_band(score):
    if score >= 75:
        return "HIGH"
    if score >= 55:
        return "MEDIUM"
    if score >= 35:
        return "LOW"
    return "VERY LOW"


def calibration_label(adj, risk, band, signal):
    if signal in {"DRIFTER", "BIG DRIFTER"} and adj < 0:
        return "MARKET DISAGREES"
    if band == "VERY LOW" and adj < 0:
        return "VERY LOW CONFIDENCE"
    if adj <= -2.0 or risk == "HIGH":
        return "HARD DAMPEN"
    if adj < -0.05:
        return "SOFT DAMPEN"
    return "UNCHANGED"


def apply_final_calibration(df):
    df = df.copy()
    df["raw_elite_today_rating"] = pd.to_numeric(df["elite_today_rating"], errors="coerce")
    df = add_model_prices(df, "raw_elite_today_rating", "raw_model_rated_price", "raw_model_prob")

    market = load_market_signals(MARKET_SIGNALS_PATH)
    df["race_date_key"] = pd.to_datetime(df.get("race_date"), errors="coerce").dt.strftime("%Y-%m-%d")
    df["race_no_key"] = pd.to_numeric(df.get("race_no"), errors="coerce").fillna(0).astype(int)
    if market.empty:
        df["market_signal"] = ""
        df["market_signal_price"] = np.nan
        df["market_confidence"] = ""
    else:
        df = df.merge(
            market,
            left_on=["race_date_key", "track", "race_no_key", "horse_key"],
            right_on=["race_date", "track", "race_no", "horse_key"],
            how="left",
            suffixes=("", "_signal"),
        )
        df["market_signal_price"] = pd.to_numeric(df["current_price"], errors="coerce")
        df = df.drop(columns=["race_date_signal", "race_no_signal", "current_price"], errors="ignore")

    df["market_signal"] = df.get("market_signal", "").fillna("").astype(str).str.upper().str.strip()
    df["market_confidence"] = df.get("market_confidence", "").fillna("").astype(str).str.upper().str.strip()
    df["market_price_for_confidence"] = pd.to_numeric(df.get("market_signal_price"), errors="coerce").combine_first(pd.to_numeric(df.get("fixed_win"), errors="coerce"))
    df.loc[df["market_price_for_confidence"].le(1), "market_price_for_confidence"] = np.nan

    support_score = (
        pd.to_numeric(df.get("trainer_adj_points"), errors="coerce").fillna(0)
        + pd.to_numeric(df.get("combo_adj_points"), errors="coerce").fillna(0)
        + pd.to_numeric(df.get("jockey_adj_points"), errors="coerce").fillna(0)
        + pd.to_numeric(df.get("pace_adj_points"), errors="coerce").fillna(0)
    )

    scores = []
    risks = []
    reasons = []
    adjs = []
    labels = []

    for idx, row in df.iterrows():
        score = 50.0
        runs = pd.to_numeric(pd.Series([row.get("runs_used")]), errors="coerce").iloc[0]
        raw_price = pd.to_numeric(pd.Series([row.get("raw_model_rated_price")]), errors="coerce").iloc[0]
        market_price = pd.to_numeric(pd.Series([row.get("market_price_for_confidence")]), errors="coerce").iloc[0]
        signal = str(row.get("market_signal", "") or "").upper().strip()
        support = float(support_score.loc[idx]) if idx in support_score.index else 0.0

        if pd.notna(runs):
            if runs >= 8:
                score += 20
            elif runs >= 4:
                score += 10
            elif runs <= 1:
                score -= 20
            elif runs <= 3:
                score -= 10
        else:
            score -= 15

        if support >= 1.0:
            score += 8
        elif support <= -1.0:
            score -= 8

        if signal in {"STEAMER", "FIRMING"}:
            score += 8
        elif signal in {"DRIFTER", "BIG DRIFTER"}:
            score -= 10
        elif signal == "NO MARKET" or pd.isna(market_price):
            score -= 8

        score = max(0.0, min(100.0, score))
        band = confidence_band(score)

        reason_parts = []
        risk = "LOW"
        adj = 0.0
        estimated_edge = np.nan
        if pd.notna(market_price) and pd.notna(raw_price) and raw_price > 0:
            estimated_edge = ((market_price / raw_price) - 1.0) * 100.0

        if pd.isna(market_price):
            reason_parts.append("NO MARKET")
            adj -= 0.75
            risk = "MEDIUM" if band in {"LOW", "VERY LOW"} else "LOW"

        if pd.notna(runs) and runs <= 2:
            reason_parts.append("LOW FORM SAMPLE")
            adj -= 1.0 if runs <= 1 else 0.55
            if pd.notna(raw_price) and raw_price <= 8:
                risk = "HIGH"
            elif risk != "HIGH":
                risk = "MEDIUM"

        if pd.notna(market_price) and pd.notna(raw_price):
            if market_price >= 26 and raw_price <= 10 and score < 65:
                reason_parts.append("LONG MARKET / SHORT MODEL")
                adj -= 2.35
                risk = "HIGH"
            elif market_price >= 18 and raw_price <= 8 and score < 75:
                reason_parts.append("LONG MARKET / SHORT MODEL")
                adj -= 1.2
                risk = "MEDIUM" if risk != "HIGH" else risk

        if pd.notna(estimated_edge) and estimated_edge >= 180 and score < 55:
            reason_parts.append("EXTREME EDGE LOW CONF")
            adj -= 1.75
            risk = "HIGH"
        elif pd.notna(estimated_edge) and estimated_edge >= 90 and score < 65:
            reason_parts.append("EXTREME EDGE LOW CONF")
            adj -= 0.85
            risk = "MEDIUM" if risk != "HIGH" else risk

        if signal in {"DRIFTER", "BIG DRIFTER"} and score < 65:
            reason_parts.append("MARKET DRIFT AGAINST")
            adj -= 0.85 if signal == "DRIFTER" else 1.15
            risk = "MEDIUM" if risk != "HIGH" else risk

        if band == "VERY LOW":
            reason_parts.append("VERY LOW CONFIDENCE")
            adj -= 1.0
            risk = "HIGH" if risk != "HIGH" and (pd.notna(raw_price) and raw_price <= 12) else risk
        elif band == "LOW":
            adj -= 0.5

        if pd.notna(raw_price) and raw_price < 2.0 and score < 75:
            reason_parts.append("SHORT MODEL PRICE CHECK")
            adj -= 1.0
            risk = "MEDIUM" if risk != "HIGH" else risk
        elif pd.notna(raw_price) and raw_price < 3.0 and score < 65:
            reason_parts.append("SHORT MODEL PRICE CHECK")
            adj -= 0.65
            risk = "MEDIUM" if risk != "HIGH" else risk

        if support >= 2.0 and score >= 75 and not reason_parts:
            adj += 0.35

        adj = float(np.clip(adj, -5.0, 0.75))
        if not reason_parts:
            reason_parts.append("OK")
            risk = "LOW"
            if adj < 0:
                adj = max(adj, -0.25)

        scores.append(round(score, 1))
        risks.append(risk)
        reasons.append(" | ".join(dict.fromkeys(reason_parts)))
        adjs.append(round(adj, 3))
        labels.append(calibration_label(adj, risk, band, signal))

    df["model_confidence_score"] = scores
    df["price_confidence_band"] = [confidence_band(x) for x in scores]
    df["fake_overlay_risk"] = risks
    df["fake_overlay_reason"] = reasons
    df["calibration_adj_points"] = adjs
    df["calibration_label"] = labels
    df["calibrated_today_rating"] = (df["raw_elite_today_rating"] + df["calibration_adj_points"]).clip(35, 120).round(3)
    df["elite_today_rating"] = df["calibrated_today_rating"]
    df = df.drop(columns=["race_date_key", "race_no_key"], errors="ignore")
    return df

fields = pd.read_csv(FIELDS_PATH, low_memory=False)
form = pd.read_csv(FORM_PATH, low_memory=False)
runs = pd.read_csv(RUNS_PATH, low_memory=False)

print("FIELD ROWS:", len(fields))
print("FORM ROWS:", len(form))
print("RUN CONTEXT ROWS:", len(runs))

ensure_col(fields, "horse")
ensure_col(form, "horse")
ensure_col(runs, "horse")

fields["horse_key"] = fields["horse"].apply(hard_horse_key)
form["horse_key"] = form.get("horse_key", form["horse"]).apply(hard_horse_key)
runs["horse_key"] = runs.get("horse_key", runs["horse"]).apply(hard_horse_key)

form["form_rating"] = pd.to_numeric(form.get("form_rating"), errors="coerce")
form["runs_used"] = pd.to_numeric(form.get("runs_used"), errors="coerce").fillna(0)
form = (
    form[form["horse_key"].ne("")]
    .sort_values(["horse_key", "runs_used", "form_rating"], ascending=[True, False, False])
    .drop_duplicates("horse_key", keep="first")
)

form_cols = ["horse_key", "form_rating", "runs_used"]
for optional in ["base_last5", "context_last5", "context_bonus_total_last5"]:
    if optional in form.columns:
        form_cols.append(optional)

df = fields.merge(form[form_cols], on="horse_key", how="left")
df["matched_form"] = df["form_rating"].notna()
df["form_rating"] = pd.to_numeric(df["form_rating"], errors="coerce").fillna(BASELINE_FORM_RATING)
df["runs_used"] = pd.to_numeric(df["runs_used"], errors="coerce").fillna(0).astype(int)

runs["run_date"] = pd.to_datetime(runs.get("run_date"), errors="coerce")
ensure_col(runs, "distance")
ensure_col(runs, "finish_pos")
ensure_col(runs, "margin")
runs["distance_m"] = runs["distance"].apply(parse_num)
runs["finish_pos_num"] = runs["finish_pos"].apply(parse_num)
runs["margin_num"] = runs["margin"].apply(parse_margin)

for col in ["pos_800", "pos_400"]:
    ensure_col(runs, col)
    runs[col + "_num"] = runs[col].apply(parse_num)

if "run_type" in runs.columns:
    rt = runs["run_type"].astype(str).str.upper()
    runs = runs[~rt.str.contains("TRIAL|JUMPOUT|BT", na=False)].copy()

runs = runs[runs["horse_key"].ne("")].copy()
runs["run_rating_base"] = (
    100
    - runs["finish_pos_num"].fillna(8) * 3
    - runs["margin_num"].fillna(5) * 2
).clip(20, 100)

# Recency layer
ensure_col(df, "race_date")
df["race_date_dt"] = pd.to_datetime(df["race_date"], errors="coerce")
recency_rows = []
for horse_key, g in runs.dropna(subset=["run_date"]).sort_values("run_date", ascending=False).groupby("horse_key"):
    g = g.sort_values("run_date", ascending=False).head(8)
    if g.empty:
        continue
    weights = np.array([1.00, 0.82, 0.67, 0.55, 0.45, 0.37, 0.30, 0.25])[: len(g)]
    ratings = g["run_rating_base"].astype(float).values
    weighted_recent_rating = float(np.sum(ratings * weights) / np.sum(weights))
    simple_avg = float(np.mean(ratings))
    recency_rows.append(
        {
            "horse_key": horse_key,
            "last_run_date": g["run_date"].iloc[0],
            "weighted_recent_rating": round(weighted_recent_rating, 3),
            "recent_simple_avg": round(simple_avg, 3),
            "recency_momentum": round(weighted_recent_rating - simple_avg, 3),
        }
    )

recency_df = pd.DataFrame(recency_rows)
if recency_df.empty:
    recency_df = pd.DataFrame(columns=["horse_key", "last_run_date", "weighted_recent_rating", "recent_simple_avg", "recency_momentum"])
df = df.merge(recency_df, on="horse_key", how="left")
df["last_run_date"] = pd.to_datetime(df["last_run_date"], errors="coerce")
df["days_since_last"] = (df["race_date_dt"] - df["last_run_date"]).dt.days

df["recency_adj"] = 1.0
df.loc[df["days_since_last"].between(7, 45, inclusive="both"), "recency_adj"] = 1.015
df.loc[df["days_since_last"].between(1, 6, inclusive="both"), "recency_adj"] = 0.985
df.loc[df["days_since_last"].between(46, 90, inclusive="both"), "recency_adj"] = 1.000
df.loc[df["days_since_last"].between(91, 180, inclusive="both"), "recency_adj"] = 0.970
df.loc[df["days_since_last"] > 180, "recency_adj"] = 0.940
df.loc[df["days_since_last"].isna(), "recency_adj"] = 0.985

df["recency_momentum"] = pd.to_numeric(df["recency_momentum"], errors="coerce").fillna(0)
df["momentum_adj"] = (1 + (df["recency_momentum"] / 300)).clip(0.95, 1.05)

# Speed layer
runs["gain_800_finish"] = runs["pos_800_num"] - runs["finish_pos_num"]
runs["gain_400_finish"] = runs["pos_400_num"] - runs["finish_pos_num"]
runs["late_gain_score"] = runs["gain_800_finish"].fillna(0) * 0.6 + runs["gain_400_finish"].fillna(0) * 1.0
runs["margin_speed_score"] = (5 - runs["margin_num"].fillna(5)).clip(-10, 5) * 0.35
runs["run_speed_score"] = (runs["late_gain_score"] + runs["margin_speed_score"]).clip(-8, 8)

speed_rows = []
for horse_key, g in runs.dropna(subset=["run_date"]).sort_values("run_date", ascending=False).groupby("horse_key"):
    recent = g.head(5)
    speed_score = float(recent["run_speed_score"].mean()) if len(recent) else 0.0
    speed_adj = max(0.94, min(1.06, 1 + speed_score / 150))
    speed_rows.append({"horse_key": horse_key, "speed_score": round(speed_score, 3), "speed_adj": round(speed_adj, 4)})

speed_df = pd.DataFrame(speed_rows)
if speed_df.empty:
    speed_df = pd.DataFrame(columns=["horse_key", "speed_score", "speed_adj"])
df = df.merge(speed_df, on="horse_key", how="left")
df["speed_score"] = pd.to_numeric(df["speed_score"], errors="coerce").fillna(0)
df["speed_adj"] = pd.to_numeric(df["speed_adj"], errors="coerce").fillna(0.99)

# Class and distance
ensure_col(df, "race_class")
ensure_col(df, "distance")
df = apply_race_class_normalisation(df, "race_class", "race_name")
df["today_class_score"] = df.apply(class_score, axis=1)
df["class_adj_raw"] = (1 + ((df["today_class_score"] - 64) / 500)).clip(0.90, 1.12)
confidence_scale = df["class_confidence"].fillna("UNKNOWN").astype(str).str.upper().map({"HIGH": 1.0, "MEDIUM": 0.65, "LOW": 0.35, "UNKNOWN": 0.0}).fillna(0.0)
df["class_adj_confidence"] = confidence_scale
df["class_adj"] = (1 + ((df["class_adj_raw"] - 1) * confidence_scale)).clip(0.94, 1.08)
df["reliability_adj"] = 0.90 + (df["runs_used"].clip(0, 10) / 10) * 0.10
df["today_distance_m"] = df["distance"].apply(parse_num)

distance_rows = []
for _, row in df[["horse_key", "today_distance_m"]].drop_duplicates().iterrows():
    horse_key = row["horse_key"]
    today_distance = row["today_distance_m"]
    h = runs[runs["horse_key"] == horse_key].copy()
    if pd.isna(today_distance):
        distance_rows.append({"horse_key": horse_key, "today_distance_m": today_distance, "distance_runs": 0, "distance_adj": 1.0, "distance_note": "NO DISTANCE"})
        continue
    if h.empty:
        distance_rows.append({"horse_key": horse_key, "today_distance_m": today_distance, "distance_runs": 0, "distance_adj": 0.99, "distance_note": "NO HISTORY"})
        continue
    overall = h["run_rating_base"].mean()
    near = h[(h["distance_m"] >= today_distance - 200) & (h["distance_m"] <= today_distance + 200)]
    if len(near) == 0 or pd.isna(overall):
        distance_rows.append({"horse_key": horse_key, "today_distance_m": today_distance, "distance_runs": 0, "distance_adj": 0.98, "distance_note": "NO NEAR DISTANCE"})
    else:
        dist_avg = near["run_rating_base"].mean()
        adj = max(0.92, min(1.08, 1 + ((dist_avg - overall) / 250)))
        distance_rows.append({"horse_key": horse_key, "today_distance_m": today_distance, "distance_runs": int(len(near)), "distance_adj": adj, "distance_note": f"{len(near)} NEAR RUNS"})

dist_df = pd.DataFrame(distance_rows)
if dist_df.empty:
    dist_df = pd.DataFrame(columns=["horse_key", "today_distance_m", "distance_runs", "distance_adj", "distance_note"])
df["today_distance_m"] = pd.to_numeric(df["today_distance_m"], errors="coerce")
dist_df["today_distance_m"] = pd.to_numeric(dist_df["today_distance_m"], errors="coerce")
df = df.merge(dist_df, on=["horse_key", "today_distance_m"], how="left")
df["distance_adj"] = pd.to_numeric(df["distance_adj"], errors="coerce").fillna(1.0)
df["distance_runs"] = pd.to_numeric(df["distance_runs"], errors="coerce").fillna(0).astype(int)

# Final rating and race-normalised price
df["elite_today_rating"] = (
    df["form_rating"]
    * df["class_adj"]
    * df["reliability_adj"]
    * df["distance_adj"]
    * df["speed_adj"]
    * df["recency_adj"]
    * df["momentum_adj"]
).clip(35, 120).round(3)

df = apply_handicapper_layer(df, runs)

df["race_date"] = pd.to_datetime(df["race_date"], errors="coerce").dt.date
df["track"] = df.get("track", "").astype(str).str.upper().str.strip()
df["race_no"] = pd.to_numeric(df.get("race_no"), errors="coerce")
df["race_id"] = df["race_date"].astype(str) + "_" + df["track"] + "_" + df["race_no"].astype(str)
df = apply_final_calibration(df)
df = apply_race_softmax_prices(df)


df.to_csv(OUT_PATH, index=False)

matched = int((df["runs_used"] > 0).sum())
baseline = int((df["runs_used"] == 0).sum())
print("SAVED:", OUT_PATH)
print("ROWS:", len(df))
print("TRUE FORM MATCHED:", matched, "/", len(df))
print("BASELINE / NO HISTORY:", baseline)
print("UNMATCHED SAMPLE:")
print(df.loc[df["runs_used"] == 0, ["race_date", "track", "race_no", "horse", "horse_key", "form_rating", "elite_today_rating_before_handicapper", "trip_adj_points", "weight_adj_points", "jockey_adj_points", "handicapper_adj_total", "elite_today_rating", "elite_rated_price"]].head(30).to_string(index=False))
print("\nPRICE CHECK:")
print(df[["race_date", "track", "race_no", "horse", "horse_key", "form_rating", "runs_used", "class_adj", "distance_adj", "speed_adj", "recency_adj", "elite_today_rating_before_handicapper", "trip_adj_points", "weight_adj_points", "jockey_adj_points", "handicapper_adj_total", "elite_today_rating", "elite_rated_price"]].head(80).to_string(index=False))






