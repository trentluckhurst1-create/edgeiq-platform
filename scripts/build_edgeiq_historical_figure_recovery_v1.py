from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
DETAIL_PATH = DATA / "edgeiq_runner_history_detail_v1.csv"
TRACK_ALIAS_PATH = DATA / "edgeiq_track_alias_bridge_v1.csv"
RUN_RATINGS_PATH = DATA / "run_ratings_v1.csv"
FORM_TABLE_PATH = DATA / "historical_form_table.csv"
RESULTS_REPORT_PATH = DATA / "results_report.csv"
ALL_RUNS_RATED_PATH = DATA / "all_horse_runs_rated.csv"
POWER_RATINGS_PATH = DATA / "edgeiq_horse_results_power_ratings_v1.csv"
PERF_V61_PATH = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"

OUT_PATH = DATA / "edgeiq_historical_figure_recovery_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_historical_figure_recovery_v1_summary.csv"
RICH_NEW_ROW_SOURCES = {"run_ratings_v1.csv", "historical_form_table.csv", "results_report.csv", "all_horse_runs_rated.csv"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper_text(value: object) -> str:
    return safe_text(value).upper()


def normalize_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", safe_text(value)).strip()


def compact(value: object) -> str:
    text = upper_text(value).replace("'", "'").replace("'", "'")
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalize_horse(value: object) -> str:
    text = upper_text(value).replace("'", "'").replace("'", "'")
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalize_track_basic(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    for old, new in {
        "SPORTSBET-": "",
        "SPORTSBET ": "",
        "BET365 ": "",
        "LADBROKES ": "",
        "TAB ": "",
        "THE VALLEY": "MOONEE VALLEY",
        "MT V": "MOONEE VALLEY",
    }.items():
        text = text.replace(old, new)
    return normalize_spaces(re.sub(r"[^A-Z0-9]+", " ", text))


def parse_float(value: object) -> float | None:
    text = safe_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("KG", "").replace("kg", "").replace("L", "")
    if text.upper() in {"-", "--", "N/A", "SCR", "DNS", "DNF"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    return None if math.isnan(number) else number


def format_num(value: object, digits: int = 2) -> str:
    number = parse_float(value)
    return "" if number is None else f"{number:.{digits}f}"


def normalize_distance(value: object) -> str:
    number = parse_float(value)
    return "" if number is None else str(int(round(number)))


def normalize_race_no(value: object) -> str:
    text = safe_text(value)
    if not text:
        return ""
    match = re.search(r"\d+", text)
    return match.group(0) if match else text.upper()


def normalize_finish(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    if text in {"SCR", "SCRATCHED", "LATE SCRATCHED", "LATESCRATCHED", "DNS", "VAC"}:
        return text
    match = re.search(r"\d+", text)
    return match.group(0) if match else text


def canonical_condition(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    if text.startswith("GOOD"):
        return text.replace("GOOD ", "GOOD")
    if text.startswith("SOFT"):
        return text.replace("SOFT ", "SOFT")
    if text.startswith("HEAVY"):
        return text.replace("HEAVY ", "HEAVY")
    if "SYN" in text:
        return "SYNTH"
    return normalize_spaces(text)


def load_track_alias_map() -> dict[str, str]:
    if not TRACK_ALIAS_PATH.exists():
        return {}
    df = pd.read_csv(TRACK_ALIAS_PATH, dtype=str).fillna("")
    alias_map = {}
    for row in df.to_dict("records"):
        chosen = upper_text(row.get("chosen"))
        if chosen not in {"", "YES", "TRUE", "1"}:
            continue
        alias_key = compact(row.get("alias_key"))
        canonical = upper_text(row.get("canonical_track"))
        if alias_key and canonical:
            alias_map[alias_key] = canonical
    return alias_map


def canonical_track(value: object, alias_map: dict[str, str]) -> str:
    raw = upper_text(value)
    if not raw:
        return ""
    for candidate in [compact(raw), compact(normalize_track_basic(raw))]:
        if candidate and candidate in alias_map:
            return alias_map[candidate]
    return normalize_track_basic(raw) or raw


def first_non_blank(*values: object) -> str:
    for value in values:
        text = safe_text(value)
        if text:
            return text
    return ""


def compute_keys(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["horse_match_key"] = df.apply(lambda row: normalize_horse(row.get("horse_key") or row.get("horse")), axis=1)
    df["track_key_norm"] = df["track"].map(compact)
    df["distance_norm"] = df["distance"].map(normalize_distance)
    df["race_no_norm"] = df["race_no"].map(normalize_race_no)
    df["match_key_primary"] = df.apply(lambda row: "|".join([safe_text(row["horse_match_key"]), safe_text(row["run_date_iso"]), safe_text(row["track_key_norm"]), safe_text(row["distance_norm"]), safe_text(row["race_no_norm"])]), axis=1)
    df["match_key_track_distance"] = df.apply(lambda row: "|".join([safe_text(row["horse_match_key"]), safe_text(row["run_date_iso"]), safe_text(row["track_key_norm"]), safe_text(row["distance_norm"])]), axis=1)
    df["match_key_track"] = df.apply(lambda row: "|".join([safe_text(row["horse_match_key"]), safe_text(row["run_date_iso"]), safe_text(row["track_key_norm"])]), axis=1)
    df["match_key_date"] = df.apply(lambda row: "|".join([safe_text(row["horse_match_key"]), safe_text(row["run_date_iso"])]), axis=1)
    return df


def standardize_source(df: pd.DataFrame, source_file: str, alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy().fillna("")
    df["horse"] = df.apply(lambda row: safe_text(row.get("horse")) or registry.get(normalize_horse(row.get("horse_key") or row.get("horse")), {}).get("horse", ""), axis=1)
    df["horse_key"] = df.apply(lambda row: safe_text(row.get("horse_key")) or registry.get(normalize_horse(row.get("horse_key") or row.get("horse")), {}).get("horse_key", normalize_horse(row.get("horse"))), axis=1)
    df["track"] = df["track"].map(lambda value: canonical_track(value, alias_map))
    df["track_key"] = df["track"].map(compact)
    df["race_date"] = df.apply(lambda row: safe_text(row.get("race_date")) or safe_text(row.get("run_date_iso")), axis=1)
    df["run_date_iso"] = df.apply(lambda row: safe_text(row.get("run_date_iso")) or safe_text(row.get("race_date")), axis=1)
    df["race_no"] = df["race_no"].map(normalize_race_no)
    df["distance"] = df["distance"].map(normalize_distance)
    df["finish_pos"] = df["finish_pos"].map(normalize_finish)
    df["condition"] = df["condition"].map(canonical_condition)
    df["sp"] = df["sp"].map(format_num)
    df["candidate_rating"] = df["candidate_rating"].map(format_num)
    df["source_file"] = source_file
    df = compute_keys(df)
    df["candidate_rating_num"] = df["candidate_rating"].map(parse_float)
    df["row_populated_score"] = df.apply(lambda row: sum(safe_text(value) != "" for value in row), axis=1)
    return df


def load_live_registry(alias_map: dict[str, str]) -> tuple[dict[str, dict[str, str]], set[str]]:
    live_df = pd.read_csv(LIVE_PATH, dtype=str, usecols=lambda c: c in {"horse", "horse_key", "track"}).fillna("")
    registry = {}
    for row in live_df.to_dict("records"):
        horse_match_key = normalize_horse(row.get("horse_key") or row.get("horse"))
        if horse_match_key and horse_match_key not in registry:
            registry[horse_match_key] = {
                "horse": safe_text(row.get("horse")),
                "horse_key": safe_text(row.get("horse_key")) or horse_match_key,
                "track": canonical_track(row.get("track"), alias_map),
            }
    return registry, set(registry.keys())


def load_detail(alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    df = pd.read_csv(DETAIL_PATH, dtype=str).fillna("")
    df["horse"] = df.apply(lambda row: safe_text(row.get("horse")) or registry.get(normalize_horse(row.get("horse_key") or row.get("horse")), {}).get("horse", ""), axis=1)
    df["horse_key"] = df.apply(lambda row: safe_text(row.get("horse_key")) or normalize_horse(row.get("horse")), axis=1)
    df["track"] = df["track"].map(lambda value: canonical_track(value, alias_map))
    df["run_date_iso"] = df.apply(lambda row: safe_text(row.get("run_date_iso")) or safe_text(row.get("race_date")), axis=1)
    df["race_date"] = df.apply(lambda row: safe_text(row.get("race_date")) or safe_text(row.get("run_date_iso")), axis=1)
    for col in ["run_rating", "performance_rating", "race_strength", "trainer"]:
        if col not in df.columns:
            df[col] = ""
    df = compute_keys(df)
    df["detail_recovery_key"] = df.apply(lambda row: row["match_key_primary"] if safe_text(row["race_no_norm"]) else row["match_key_track_distance"], axis=1)
    df["has_any_existing_rating"] = df[["run_rating", "performance_rating"]].astype(str).apply(lambda col: col.str.strip().ne(""), axis=0).any(axis=1)
    return df

def load_run_ratings(current_horses: set[str], alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    if not RUN_RATINGS_PATH.exists():
        return pd.DataFrame()
    cols = {"horse", "horse_key", "run_date", "track", "distance", "race_class", "finish_pos", "barrier", "jockey", "trainer", "weight_carried", "margin", "sp_num", "sp", "field_size", "run_rating"}
    df = pd.read_csv(RUN_RATINGS_PATH, dtype=str, usecols=lambda c: c in cols).fillna("")
    df["horse_match_key"] = df.apply(lambda row: normalize_horse(row.get("horse_key") or row.get("horse")), axis=1)
    df = df[df["horse_match_key"].isin(current_horses)].copy()
    if df.empty:
        return df
    standardized = pd.DataFrame({
        "horse": df["horse"], "horse_key": df["horse_key"], "track": df["track"], "track_key": "",
        "race_date": df["run_date"], "run_date_iso": df["run_date"], "race_no": "", "distance": df["distance"],
        "class_name": df["race_class"], "condition": "", "finish_pos": df["finish_pos"], "field_size": df["field_size"],
        "barrier": df["barrier"], "jockey": df["jockey"], "trainer": df["trainer"], "weight": df["weight_carried"],
        "margin": df["margin"], "sp": df["sp_num"].where(df["sp_num"].astype(str).str.strip().ne(""), df["sp"]),
        "race_strength": "", "candidate_rating": df["run_rating"], "source_confidence": "HIGH_RUN_RATINGS",
    })
    return standardize_source(standardized, RUN_RATINGS_PATH.name, alias_map, registry)


def load_historical_form_table(current_horses: set[str], alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    if not FORM_TABLE_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(FORM_TABLE_PATH, dtype=str).fillna("")
    df["horse_match_key"] = df["horse"].map(normalize_horse)
    df = df[df["horse_match_key"].isin(current_horses)].copy()
    if df.empty:
        return df
    standardized = pd.DataFrame({
        "horse": df["horse"], "horse_key": "", "track": df["track"], "track_key": "",
        "race_date": df["race_date"], "run_date_iso": df["race_date"], "race_no": df["race_no"], "distance": df["distance"],
        "class_name": "", "condition": df["track_condition"], "finish_pos": df["finish_pos"], "field_size": "",
        "barrier": df["barrier"], "jockey": df["jockey"], "trainer": df["trainer"], "weight": "", "margin": df["margin"],
        "sp": df["sp"], "race_strength": df["race_rating"], "candidate_rating": df["run_rating"],
        "source_confidence": "HIGH_FORM_TABLE",
    })
    return standardize_source(standardized, FORM_TABLE_PATH.name, alias_map, registry)


def load_results_report(current_horses: set[str], alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    if not RESULTS_REPORT_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(RESULTS_REPORT_PATH, dtype=str).fillna("")
    df["horse_match_key"] = df["horse"].map(normalize_horse)
    df = df[df["horse_match_key"].isin(current_horses)].copy()
    if df.empty:
        return df
    field_sizes = df.groupby(["race_date", "track", "race_no"])["horse"].transform("count").astype(str)
    standardized = pd.DataFrame({
        "horse": df["horse"], "horse_key": "", "track": df["track"], "track_key": "",
        "race_date": df["race_date"], "run_date_iso": df["race_date"], "race_no": df["race_no"], "distance": df["distance"],
        "class_name": "", "condition": df["track_condition"], "finish_pos": df["finish_pos"], "field_size": field_sizes,
        "barrier": df["barrier"], "jockey": df["jockey"], "trainer": "", "weight": "", "margin": df["margin"],
        "sp": df["sp"], "race_strength": df["race_strength"].where(df["race_strength"].astype(str).str.strip().ne(""), df["race_rating"]),
        "candidate_rating": df["run_rating"], "source_confidence": "MEDIUM_RESULTS_REPORT",
    })
    return standardize_source(standardized, RESULTS_REPORT_PATH.name, alias_map, registry)


def load_all_horse_runs_rated(current_horses: set[str], alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    if not ALL_RUNS_RATED_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(ALL_RUNS_RATED_PATH, dtype=str).fillna("")
    df["horse_match_key"] = df.apply(lambda row: normalize_horse(row.get("horse_key") or row.get("horse_name")), axis=1)
    df = df[df["horse_match_key"].isin(current_horses)].copy()
    if df.empty:
        return df
    standardized = pd.DataFrame({
        "horse": df["horse_name"], "horse_key": df["horse_key"], "track": df["track"], "track_key": df.get("track_code", ""),
        "race_date": df["run_date"], "run_date_iso": df["run_date"], "race_no": "", "distance": df["distance"],
        "class_name": df["race_class"], "condition": df["track_condition"],
        "finish_pos": df["finish_pos"].where(df["finish_pos"].astype(str).str.strip().ne(""), df["finish_pos_num"]),
        "field_size": df["field_size"].where(df["field_size"].astype(str).str.strip().ne(""), df["field_size_num"]),
        "barrier": df["barrier"].where(df["barrier"].astype(str).str.strip().ne(""), df["barrier_num"]),
        "jockey": df["jockey"], "trainer": "", "weight": df["weight"].where(df["weight"].astype(str).str.strip().ne(""), df["weight_num"]),
        "margin": df["margin"].where(df["margin"].astype(str).str.strip().ne(""), df["margin_num"]),
        "sp": df["sp"], "race_strength": df["race_strength"], "candidate_rating": df["run_rating"],
        "source_confidence": "MEDIUM_ALL_RUNS_RATED",
    })
    return standardize_source(standardized, ALL_RUNS_RATED_PATH.name, alias_map, registry)


def load_power_ratings(current_horses: set[str], alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    if not POWER_RATINGS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(POWER_RATINGS_PATH, dtype=str).fillna("")
    df["horse_match_key"] = df.apply(lambda row: normalize_horse(row.get("horse_key") or row.get("horse")), axis=1)
    df = df[df["horse_match_key"].isin(current_horses)].copy()
    if df.empty:
        return df
    standardized = pd.DataFrame({
        "horse": df["horse"], "horse_key": df["horse_key"], "track": "", "track_key": "",
        "race_date": df["meeting_date"], "run_date_iso": df["meeting_date"], "race_no": "", "distance": "",
        "class_name": "", "condition": "", "finish_pos": df["finish"], "field_size": "", "barrier": "", "jockey": "", "trainer": "",
        "weight": "", "margin": df["margin"], "sp": "", "race_strength": "", "candidate_rating": df["performance_rating"],
        "source_confidence": "LOW_POWER_RATING_FALLBACK",
    })
    return standardize_source(standardized, POWER_RATINGS_PATH.name, alias_map, registry)


def load_perf_v61(current_horses: set[str], alias_map: dict[str, str], registry: dict[str, dict[str, str]]) -> pd.DataFrame:
    if not PERF_V61_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(PERF_V61_PATH, dtype=str).fillna("")
    df["horse_match_key"] = df["horse"].map(normalize_horse)
    df = df[df["horse_match_key"].isin(current_horses)].copy()
    if df.empty:
        return df
    standardized = pd.DataFrame({
        "horse": df["horse"], "horse_key": "", "track": df["track"], "track_key": "",
        "race_date": df["race_date"], "run_date_iso": df["race_date"], "race_no": "", "distance": df["distance"],
        "class_name": df["race_class_clean"].where(df["race_class_clean"].astype(str).str.strip().ne(""), df["race_class_recovered"]),
        "condition": df["condition_recovered"], "finish_pos": df["finish_position"], "field_size": df["real_field_size"],
        "barrier": "", "jockey": "", "trainer": "", "weight": "", "margin": df["margin"], "sp": "", "race_strength": "",
        "candidate_rating": df["performance_rating_v6_1_research"], "source_confidence": "LOW_PERFORMANCE_V61",
    })
    return standardize_source(standardized, PERF_V61_PATH.name, alias_map, registry)

def build_unique_map(df: pd.DataFrame, key_col: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    if df.empty or key_col not in df.columns:
        return result
    usable = df[df["candidate_rating_num"].notna()].copy()
    if usable.empty:
        return result
    for key, group in usable.groupby(key_col, dropna=False):
        key_text = safe_text(key)
        if not key_text:
            continue
        ratings = group["candidate_rating_num"].dropna().round(4).unique().tolist()
        if len(ratings) > 1:
            continue
        best = group.sort_values(by=["row_populated_score"], ascending=False).iloc[0]
        result[key_text] = best.to_dict()
    return result


def source_maps(df: pd.DataFrame) -> dict[str, dict[str, dict[str, str]]]:
    return {
        "primary": build_unique_map(df, "match_key_primary"),
        "track_distance": build_unique_map(df, "match_key_track_distance"),
        "track": build_unique_map(df, "match_key_track"),
        "date": build_unique_map(df, "match_key_date"),
    }


def pick_recovery_candidate(detail_row: pd.Series, sources: list[tuple[str, dict[str, dict[str, dict[str, str]]]]]) -> tuple[dict[str, str] | None, str, str]:
    keys = {
        "PRIMARY": safe_text(detail_row.get("match_key_primary")),
        "TRACK_DISTANCE": safe_text(detail_row.get("match_key_track_distance")),
        "TRACK": safe_text(detail_row.get("match_key_track")),
        "DATE_HORSE": safe_text(detail_row.get("match_key_date")),
    }
    for source_name, maps in sources:
        for method, bucket in [("PRIMARY", "primary"), ("TRACK_DISTANCE", "track_distance"), ("TRACK", "track")]:
            key = keys[method]
            if key and key in maps[bucket]:
                return maps[bucket][key], source_name, method
        if source_name == POWER_RATINGS_PATH.name:
            key = keys["DATE_HORSE"]
            if key and key in maps["date"]:
                return maps["date"][key], source_name, "DATE_HORSE"
    return None, "", ""


def build_detail_recovery_rows(detail_df: pd.DataFrame, sources: list[tuple[str, dict[str, dict[str, dict[str, str]]]]], built_at: str) -> pd.DataFrame:
    rows = []
    for row in detail_df.to_dict("records"):
        row_series = pd.Series(row)
        original_run = safe_text(row.get("run_rating"))
        original_perf = safe_text(row.get("performance_rating"))
        candidate, source_name, method = (None, "", "") if original_run else pick_recovery_candidate(row_series, sources)
        recovered_rating = original_run or safe_text((candidate or {}).get("candidate_rating")) or original_perf
        action = "ORIGINAL" if original_run else "RECOVERED_EXTERNAL" if candidate and safe_text(candidate.get("candidate_rating")) else "RECOVERED_EXISTING_PERFORMANCE" if original_perf else "MISSING"
        merged = candidate or {}
        rows.append({
            "detail_row_exists": "YES",
            "detail_recovery_key": safe_text(row.get("detail_recovery_key")),
            "horse": safe_text(row.get("horse")), "horse_key": safe_text(row.get("horse_key")), "track": safe_text(row.get("track")), "track_key": safe_text(row.get("track_key")),
            "race_date": safe_text(row.get("race_date")), "run_date_iso": safe_text(row.get("run_date_iso")), "race_no": safe_text(row.get("race_no")), "distance": safe_text(row.get("distance")),
            "class_name": first_non_blank(row.get("class_name"), merged.get("class_name")), "condition": first_non_blank(row.get("condition"), merged.get("condition")),
            "finish_pos": first_non_blank(row.get("finish_pos"), merged.get("finish_pos")), "field_size": first_non_blank(row.get("field_size"), merged.get("field_size")),
            "barrier": first_non_blank(row.get("barrier"), merged.get("barrier")), "jockey": first_non_blank(row.get("jockey"), merged.get("jockey")), "trainer": first_non_blank(row.get("trainer"), merged.get("trainer")),
            "weight": first_non_blank(row.get("weight"), merged.get("weight")), "margin": first_non_blank(row.get("margin"), merged.get("margin")), "sp": first_non_blank(row.get("sp"), merged.get("sp")),
            "race_strength": first_non_blank(row.get("race_strength"), merged.get("race_strength")),
            "original_run_rating": original_run, "original_performance_rating": original_perf, "performance_rating": original_perf,
            "recovered_rating": recovered_rating, "source_file": first_non_blank(row.get("source_file"), merged.get("source_file")), "source_confidence": first_non_blank(row.get("source_confidence"), merged.get("source_confidence")),
            "match_method": method, "recovery_action": action, "recovery_source_file": source_name or ("DETAIL_EXISTING_PERFORMANCE_RATING" if action == "RECOVERED_EXISTING_PERFORMANCE" else "DETAIL_ORIGINAL_RUN_RATING" if action == "ORIGINAL" else ""),
            "recovery_source_confidence": safe_text((candidate or {}).get("source_confidence")) or ("RECOVERED_FROM_EXISTING_PERFORMANCE" if action == "RECOVERED_EXISTING_PERFORMANCE" else "ORIGINAL" if action == "ORIGINAL" else ""),
            "horse_match_key": safe_text(row.get("horse_match_key")), "track_key_norm": safe_text(row.get("track_key_norm")), "distance_norm": safe_text(row.get("distance_norm")), "race_no_norm": safe_text(row.get("race_no_norm")), "built_at": built_at,
        })
    return pd.DataFrame(rows)


def collect_safe_new_rows(detail_df: pd.DataFrame, source_frames: list[pd.DataFrame], built_at: str) -> pd.DataFrame:
    frames = [frame for frame in source_frames if not frame.empty and safe_text(frame["source_file"].iloc[0]) in RICH_NEW_ROW_SOURCES]
    if not frames:
        return pd.DataFrame()
    existing_primary = set(detail_df["match_key_primary"].astype(str))
    existing_secondary = set(detail_df["match_key_track_distance"].astype(str))
    all_candidates = pd.concat(frames, ignore_index=True)
    all_candidates = all_candidates[all_candidates["candidate_rating_num"].notna()].copy()
    all_candidates = all_candidates[all_candidates["run_date_iso"].astype(str).str.strip().ne("") & all_candidates["track_key_norm"].astype(str).str.strip().ne("") & all_candidates["distance_norm"].astype(str).str.strip().ne("")].copy()
    if all_candidates.empty:
        return pd.DataFrame()
    all_candidates["new_row_key"] = all_candidates.apply(lambda row: row["match_key_primary"] if safe_text(row["race_no_norm"]) else row["match_key_track_distance"], axis=1)
    all_candidates = all_candidates[~all_candidates["match_key_primary"].isin(existing_primary) & ~all_candidates["match_key_track_distance"].isin(existing_secondary)].copy()
    priority = {"historical_form_table.csv": 1, "run_ratings_v1.csv": 2, "results_report.csv": 3, "all_horse_runs_rated.csv": 4}
    all_candidates["source_priority"] = all_candidates["source_file"].map(priority).fillna(99)
    rows = []
    for key, group in all_candidates.groupby("new_row_key", dropna=False):
        ratings = group["candidate_rating_num"].dropna().round(4).unique().tolist()
        if len(ratings) > 1:
            continue
        best = group.sort_values(by=["source_priority", "row_populated_score"], ascending=[True, False]).iloc[0].to_dict()
        rows.append({
            "detail_row_exists": "NO", "detail_recovery_key": safe_text(key),
            "horse": safe_text(best.get("horse")), "horse_key": safe_text(best.get("horse_key")), "track": safe_text(best.get("track")), "track_key": safe_text(best.get("track_key")),
            "race_date": safe_text(best.get("race_date")), "run_date_iso": safe_text(best.get("run_date_iso")), "race_no": safe_text(best.get("race_no")), "distance": safe_text(best.get("distance")),
            "class_name": safe_text(best.get("class_name")), "condition": safe_text(best.get("condition")), "finish_pos": safe_text(best.get("finish_pos")), "field_size": safe_text(best.get("field_size")),
            "barrier": safe_text(best.get("barrier")), "jockey": safe_text(best.get("jockey")), "trainer": safe_text(best.get("trainer")), "weight": safe_text(best.get("weight")), "margin": safe_text(best.get("margin")),
            "sp": safe_text(best.get("sp")), "race_strength": safe_text(best.get("race_strength")), "original_run_rating": "", "original_performance_rating": "", "performance_rating": "", "recovered_rating": safe_text(best.get("candidate_rating")),
            "source_file": safe_text(best.get("source_file")), "source_confidence": safe_text(best.get("source_confidence")), "match_method": "NEW_SAFE_HISTORY_ROW", "recovery_action": "NEW_SAFE_HISTORY_ROW",
            "recovery_source_file": safe_text(best.get("source_file")), "recovery_source_confidence": safe_text(best.get("source_confidence")), "horse_match_key": safe_text(best.get("horse_match_key")), "track_key_norm": safe_text(best.get("track_key_norm")), "distance_norm": safe_text(best.get("distance_norm")), "race_no_norm": safe_text(best.get("race_no_norm")), "built_at": built_at,
        })
    return pd.DataFrame(rows)


def main() -> None:
    built_at = now_iso()
    alias_map = load_track_alias_map()
    registry, current_horses = load_live_registry(alias_map)
    detail_df = load_detail(alias_map, registry)
    source_frames = [
        load_historical_form_table(current_horses, alias_map, registry),
        load_run_ratings(current_horses, alias_map, registry),
        load_results_report(current_horses, alias_map, registry),
        load_all_horse_runs_rated(current_horses, alias_map, registry),
        load_perf_v61(current_horses, alias_map, registry),
        load_power_ratings(current_horses, alias_map, registry),
    ]
    sources = [(safe_text(frame["source_file"].iloc[0]), source_maps(frame)) for frame in source_frames if not frame.empty]
    recovery_existing_df = build_detail_recovery_rows(detail_df, sources, built_at)
    new_rows_df = collect_safe_new_rows(detail_df, source_frames, built_at)
    combined_df = pd.concat([recovery_existing_df, new_rows_df], ignore_index=True) if not new_rows_df.empty else recovery_existing_df.copy()
    combined_df.to_csv(OUT_PATH, index=False)

    before_pct = round(float(detail_df["has_any_existing_rating"].mean() * 100.0), 2) if len(detail_df) else 0.0
    after_pct = round(float((recovery_existing_df["recovered_rating"].astype(str).str.strip() != "").mean() * 100.0), 2) if len(recovery_existing_df) else 0.0
    projected_rows = int(len(detail_df) + len(new_rows_df))
    projected_rated = int((recovery_existing_df["recovered_rating"].astype(str).str.strip() != "").sum() + len(new_rows_df))
    projected_pct = round((projected_rated / projected_rows) * 100.0, 2) if projected_rows else 0.0
    status = "PASS" if after_pct >= 85 else "WARN" if after_pct >= 55 else "FAIL"
    pd.DataFrame([{
        "status": status,
        "detail_rows": int(len(detail_df)),
        "detail_rows_with_existing_rating": int(detail_df["has_any_existing_rating"].sum()),
        "coverage_before_pct": before_pct,
        "detail_rows_with_recovered_rating": int((recovery_existing_df["recovered_rating"].astype(str).str.strip() != "").sum()),
        "coverage_after_existing_rows_pct": after_pct,
        "new_safe_history_rows": int(len(new_rows_df)),
        "projected_final_rows": projected_rows,
        "projected_final_rated_rows": projected_rated,
        "projected_final_coverage_pct": projected_pct,
        "rows_recovered_external": int((recovery_existing_df["recovery_action"] == "RECOVERED_EXTERNAL").sum()),
        "rows_recovered_existing_performance": int((recovery_existing_df["recovery_action"] == "RECOVERED_EXISTING_PERFORMANCE").sum()),
        "rows_still_missing": int((recovery_existing_df["recovery_action"] == "MISSING").sum()),
        "candidate_sources_used": "; ".join(name for name, _ in sources),
        "built_at": built_at,
    }]).to_csv(SUMMARY_PATH, index=False)
    print("[EDGEIQ_HISTORICAL_FIGURE_RECOVERY_V1] rows=", len(combined_df))
    print(pd.read_csv(SUMMARY_PATH).to_string(index=False))


if __name__ == "__main__":
    main()


