from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RACE_RELIABILITY_PATH = DATA / "edgeiq_race_reliability_v1.csv"
ENV_V2_FALLBACK_PATH = DATA / "edgeiq_environment_v2_trust_field_core.csv"
LIVE_SOURCE_PATHS = [
    ("edgeiq_live_runner_board_v1.csv", "LIVE_RUNNER_BOARD"),
    ("edgeiq_live_terminal_feed_v1.csv", "LIVE_TERMINAL_FEED"),
    ("edgeiq_tab_vic_racecards_v1.csv", "TAB_VIC_RACECARDS"),
    ("edgeiq_tab_market_v1.csv", "TAB_MARKET"),
    ("sportsbet_live_market_v1.csv", "SPORTSBET_LIVE_MARKET"),
]

OUTPUT_ENV_MAIN = DATA / "edgeiq_live_environment_v2_feed.csv"
OUTPUT_ENV_SUMMARY = DATA / "edgeiq_live_environment_v2_feed_summary.csv"
OUTPUT_ENV_UNMATCHED = DATA / "edgeiq_live_environment_v2_feed_unmatched.csv"

OUTPUT_RR_MAIN = DATA / "edgeiq_live_race_reliability_v1_feed.csv"
OUTPUT_RR_SUMMARY = DATA / "edgeiq_live_race_reliability_v1_feed_summary.csv"
OUTPUT_RR_UNMATCHED = DATA / "edgeiq_live_race_reliability_v1_feed_unmatched.csv"

ENV_DISPLAY_LABELS = {
    "POOR": "POOR ENV",
    "NEGATIVE": "NEGATIVE ENV",
    "NEUTRAL": "NEUTRAL ENV",
    "POSITIVE": "POSITIVE ENV",
    "ELITE": "ELITE ENV",
    "UNKNOWN": "UNKNOWN ENV",
}

ENV_DISPLAY_RANKS = {
    "POOR": 1,
    "NEGATIVE": 2,
    "NEUTRAL": 3,
    "POSITIVE": 4,
    "ELITE": 5,
    "UNKNOWN": 0,
}

ENV_GOVERNANCE_HINTS = {
    "POOR": "HIGH VARIANCE / DO NOT TRUST BLINDLY",
    "NEGATIVE": "CAUTION / ENVIRONMENT AGAINST MODEL",
    "NEUTRAL": "STANDARD / NO ENVIRONMENT EDGE",
    "POSITIVE": "FAVOURABLE / MODEL MORE TRUSTWORTHY",
    "ELITE": "ELITE SETUP / MODEL HIGHLY TRUSTWORTHY",
    "UNKNOWN": "UNKNOWN ENVIRONMENT",
}

RR_DISPLAY_LABELS = {
    "POOR": "Race Reliability: Poor",
    "NEGATIVE": "Race Reliability: Negative",
    "NEUTRAL": "Race Reliability: Neutral",
    "POSITIVE": "Race Reliability: Positive",
    "ELITE": "Race Reliability: Elite",
    "UNKNOWN": "Race Reliability: Unknown",
}

RR_DISPLAY_RANKS = {
    "POOR": 1,
    "NEGATIVE": 2,
    "NEUTRAL": 3,
    "POSITIVE": 4,
    "ELITE": 5,
    "UNKNOWN": 0,
}

RR_PLAIN_ENGLISH = {
    "POOR": "This race is historically less reliable for the model.",
    "NEGATIVE": "This race has more risk and the model should be treated carefully.",
    "NEUTRAL": "This race is standard for model reliability.",
    "POSITIVE": "This race is a favourable setup for trusting the model.",
    "ELITE": "This race is historically one of the cleanest setups for the model.",
    "UNKNOWN": "Race reliability is unavailable.",
}

RR_UI_HINTS = {
    "POOR": "High variance race",
    "NEGATIVE": "Caution race",
    "NEUTRAL": "Standard race",
    "POSITIVE": "Model-friendly race",
    "ELITE": "High-confidence race shape",
    "UNKNOWN": "Unknown reliability",
}

BAND_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]

JOIN_FIELD_COLUMNS = [
    "trust_profile_v1",
    "environment_score_v2",
    "environment_band_v2",
    "environment_reason_v2",
    "environment_score_v1",
    "environment_band_v1",
    "environment_reason_v1",
    "environment_band_comparison_v2_vs_v1",
    "environment_band_delta_v2_vs_v1",
    "race_reliability_score_v1",
    "race_reliability_band_v1",
    "race_reliability_reason_v1",
    "race_reliability_display_label_v1",
    "race_reliability_display_rank_v1",
    "race_reliability_plain_english_v1",
    "race_reliability_ui_hint_v1",
]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def normalise_text(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\s+", " ", text)
    return text


def normalise_track(value: object) -> str:
    text = normalise_text(value)
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalise_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        return pd.to_datetime(text).strftime("%Y-%m-%d")
    except Exception:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        return match.group(1) if match else text


def normalise_race_no(value: object) -> str:
    text = clean_text(value)
    match = re.search(r"(\d+)", text)
    return str(int(match.group(1))) if match else ""


def normalise_horse_key(value: object) -> str:
    text = normalise_text(value)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def derive_race_key(meeting_date: object, track: object, race_no: object) -> str:
    date_part = normalise_date(meeting_date)
    track_part = normalise_track(track)
    race_part = normalise_race_no(race_no)
    if not date_part or not track_part or not race_part:
        return ""
    return f"{date_part}|{track_part}|R{race_part}"


def derive_runner_key(meeting_date: object, track: object, race_no: object, horse_key: object, horse: object) -> str:
    race_key = derive_race_key(meeting_date, track, race_no)
    horse_part = normalise_horse_key(horse_key if clean_text(horse_key) else horse)
    if not race_key or not horse_part:
        return ""
    return f"{race_key}|{horse_part}"


def standardise_race_key_value(value: object, meeting_date: object, track: object, race_no: object) -> str:
    text = clean_text(value)
    if text:
        pipe_match = re.search(r"(\d{4}-\d{2}-\d{2})\|(.+?)\|R?(\d+)", text, flags=re.IGNORECASE)
        if pipe_match:
            return derive_race_key(pipe_match.group(1), pipe_match.group(2), pipe_match.group(3))
    return derive_race_key(meeting_date, track, race_no)


def first_existing(candidates: list[str], columns: list[str]) -> str | None:
    lookup = {column.lower(): column for column in columns}
    for candidate in candidates:
        found = lookup.get(candidate.lower())
        if found:
            return found
    return None


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, low_memory=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def rows_by_band(series: pd.Series) -> str:
    counts = series.fillna("UNKNOWN").astype(str).value_counts()
    ordered = [band for band in BAND_ORDER if band in counts.index] + [key for key in counts.index if key not in BAND_ORDER]
    return "|".join(f"{key}:{int(counts[key])}" for key in ordered)


def build_standard_live_feed(df: pd.DataFrame, source_file_name: str, source_type: str, source_priority: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    out_df = df.copy().reset_index(drop=True)

    if "state" in out_df.columns:
        out_df = out_df[out_df["state"].map(normalise_text).eq("VIC")].copy()
    elif "location" in out_df.columns and "meeting_name" in out_df.columns:
        out_df = out_df[out_df["location"].map(normalise_text).eq("VIC")].copy()

    if out_df.empty:
        return pd.DataFrame()

    out_df = out_df.reset_index(drop=True)
    out_df["_source_index_v2"] = out_df.index

    date_col = first_existing(["meeting_date", "race_date", "date"], list(out_df.columns))
    track_col = first_existing(["track", "meeting_name", "location"], list(out_df.columns))
    race_col = first_existing(["race_no", "race_number"], list(out_df.columns))
    horse_col = first_existing(["horse", "runner_name", "runner"], list(out_df.columns))
    horse_key_col = first_existing(["horse_key", "horse_canon", "_horse_key"], list(out_df.columns))
    race_key_col = first_existing(["race_key"], list(out_df.columns))
    runner_no_col = first_existing(["runner_no", "horse_no", "saddlecloth"], list(out_df.columns))
    barrier_col = first_existing(["barrier"], list(out_df.columns))
    jockey_col = first_existing(["jockey"], list(out_df.columns))
    trainer_col = first_existing(["trainer"], list(out_df.columns))

    if not all([date_col, track_col, race_col, horse_col]):
        return pd.DataFrame()

    feed = pd.DataFrame()
    feed["_source_index_v2"] = out_df["_source_index_v2"]
    feed["meeting_date"] = out_df[date_col].map(normalise_date)
    feed["track"] = out_df[track_col].map(clean_text)
    feed["race_no"] = out_df[race_col].map(normalise_race_no)
    feed["horse"] = out_df[horse_col].map(clean_text)
    feed["horse_key"] = [
        normalise_horse_key(horse_key if horse_key_col else horse)
        for horse_key, horse in zip(out_df[horse_key_col] if horse_key_col else [""] * len(out_df), out_df[horse_col])
    ]
    feed["runner_no"] = out_df[runner_no_col].map(clean_text) if runner_no_col else ""
    feed["barrier"] = out_df[barrier_col].map(clean_text) if barrier_col else ""
    feed["jockey"] = out_df[jockey_col].map(clean_text) if jockey_col else ""
    feed["trainer"] = out_df[trainer_col].map(clean_text) if trainer_col else ""
    feed["source_file_used_v2"] = source_file_name
    feed["source_type_used_v2"] = source_type
    feed["source_priority_v2"] = source_priority

    feed = feed[
        (feed["meeting_date"] != "")
        & (feed["track"] != "")
        & (feed["race_no"] != "")
        & (feed["horse"] != "")
    ].copy()

    if feed.empty:
        return pd.DataFrame()

    source_lookup = out_df.set_index("_source_index_v2")
    if race_key_col:
        feed["race_key_raw_v2"] = [clean_text(source_lookup.at[idx, race_key_col]) for idx in feed["_source_index_v2"]]
    else:
        feed["race_key_raw_v2"] = ""
    feed["race_key_stage1_v2"] = [
        standardise_race_key_value(raw_value, date, track, race_no)
        for raw_value, date, track, race_no in zip(feed["race_key_raw_v2"], feed["meeting_date"], feed["track"], feed["race_no"])
    ]
    feed["race_key"] = [derive_race_key(date, track, race_no) for date, track, race_no in zip(feed["meeting_date"], feed["track"], feed["race_no"])]
    feed["race_composite_key_v2"] = feed["race_key"]
    feed["environment_v2_join_key"] = [
        derive_runner_key(date, track, race_no, horse_key, horse)
        for date, track, race_no, horse_key, horse in zip(
            feed["meeting_date"],
            feed["track"],
            feed["race_no"],
            feed["horse_key"],
            feed["horse"],
        )
    ]
    feed["field_size"] = feed.groupby("race_composite_key_v2")["horse"].transform("count").astype(int)
    return feed.reset_index(drop=True)


def ensure_race_reliability_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["environment_band_v2"] = out.get("environment_band_v2", "UNKNOWN").map(lambda value: clean_text(value).upper() if clean_text(value).upper() in RR_DISPLAY_LABELS else "UNKNOWN")
    if "race_reliability_score_v1" not in out.columns:
        out["race_reliability_score_v1"] = pd.to_numeric(out.get("environment_score_v2"), errors="coerce")
    if "race_reliability_band_v1" not in out.columns:
        out["race_reliability_band_v1"] = out["environment_band_v2"]
    out["race_reliability_band_v1"] = out["race_reliability_band_v1"].map(lambda value: clean_text(value).upper() if clean_text(value).upper() in RR_DISPLAY_LABELS else "UNKNOWN")
    if "race_reliability_reason_v1" not in out.columns:
        out["race_reliability_reason_v1"] = out.get("environment_reason_v2", "")
    if "race_reliability_display_label_v1" not in out.columns:
        out["race_reliability_display_label_v1"] = out["race_reliability_band_v1"].map(RR_DISPLAY_LABELS)
    if "race_reliability_display_rank_v1" not in out.columns:
        out["race_reliability_display_rank_v1"] = out["race_reliability_band_v1"].map(RR_DISPLAY_RANKS)
    if "race_reliability_plain_english_v1" not in out.columns:
        out["race_reliability_plain_english_v1"] = out["race_reliability_band_v1"].map(RR_PLAIN_ENGLISH)
    if "race_reliability_ui_hint_v1" not in out.columns:
        out["race_reliability_ui_hint_v1"] = out["race_reliability_band_v1"].map(RR_UI_HINTS)
    return out


def build_reliability_maps(source_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = ensure_race_reliability_columns(source_df)
    base["meeting_date"] = base["meeting_date"].map(normalise_date)
    base["track"] = base["track"].map(clean_text)
    base["race_no"] = base["race_no"].map(normalise_race_no)
    if "environment_horse_key_v2" not in base.columns:
        horse_series = base.get("rank1_horse", base.get("horse", ""))
        base["environment_horse_key_v2"] = pd.Series(horse_series).map(normalise_horse_key)
    else:
        base["environment_horse_key_v2"] = base["environment_horse_key_v2"].map(normalise_horse_key)

    base["race_key_stage1_v2"] = [
        standardise_race_key_value(raw_race_key, meeting_date, track, race_no)
        for raw_race_key, meeting_date, track, race_no in zip(
            base.get("race_key", [""] * len(base)),
            base["meeting_date"],
            base["track"],
            base["race_no"],
        )
    ]
    base["race_composite_key_v2"] = [
        derive_race_key(meeting_date, track, race_no)
        for meeting_date, track, race_no in zip(base["meeting_date"], base["track"], base["race_no"])
    ]
    base["environment_v2_join_key"] = [
        derive_runner_key(meeting_date, track, race_no, horse_key, horse)
        for meeting_date, track, race_no, horse_key, horse in zip(
            base["meeting_date"],
            base["track"],
            base["race_no"],
            base["environment_horse_key_v2"],
            base.get("rank1_horse", base.get("horse", [""] * len(base))),
        )
    ]

    race_key_map = base[["race_key_stage1_v2"] + JOIN_FIELD_COLUMNS].copy()
    race_key_map = race_key_map[race_key_map["race_key_stage1_v2"] != ""].drop_duplicates("race_key_stage1_v2")

    race_composite_map = base[["race_composite_key_v2"] + JOIN_FIELD_COLUMNS].copy()
    race_composite_map = race_composite_map[race_composite_map["race_composite_key_v2"] != ""].drop_duplicates("race_composite_key_v2")

    runner_map = base[["environment_v2_join_key"] + JOIN_FIELD_COLUMNS].copy()
    runner_map = runner_map[runner_map["environment_v2_join_key"] != ""].drop_duplicates("environment_v2_join_key")

    return base, race_key_map, race_composite_map, runner_map


def evaluate_source(feed: pd.DataFrame, race_key_map: pd.DataFrame, race_composite_map: pd.DataFrame) -> dict[str, object]:
    race_key_values = set(race_key_map["race_key_stage1_v2"].astype(str))
    race_composite_values = set(race_composite_map["race_composite_key_v2"].astype(str))

    stage1_hits = feed["race_key_stage1_v2"].astype(str).isin(race_key_values) & (feed["race_key_stage1_v2"].astype(str) != "")
    stage2_hits = feed["race_composite_key_v2"].astype(str).isin(race_composite_values) & ~stage1_hits
    matched_rows = int((stage1_hits | stage2_hits).sum())
    match_rate = round((matched_rows / len(feed)) * 100, 2) if len(feed) else 0.0

    return {
        "source_file_used": feed["source_file_used_v2"].iloc[0],
        "source_type_used": feed["source_type_used_v2"].iloc[0],
        "source_priority_v2": int(feed["source_priority_v2"].iloc[0]),
        "rows": int(len(feed)),
        "race_key_match_rows": int(stage1_hits.sum()),
        "race_composite_match_rows": int(stage2_hits.sum()),
        "matched_rows": matched_rows,
        "match_rate_pct": match_rate,
    }


def select_best_live_source(race_key_map: pd.DataFrame, race_composite_map: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    candidates: list[tuple[pd.DataFrame, dict[str, object]]] = []

    for source_priority, (file_name, source_type) in enumerate(LIVE_SOURCE_PATHS):
        path = DATA / file_name
        df = read_csv_if_exists(path)
        if df is None or df.empty:
            continue
        feed = build_standard_live_feed(df, file_name, source_type, source_priority)
        if feed.empty:
            continue
        audit = evaluate_source(feed, race_key_map, race_composite_map)
        candidates.append((feed, audit))

    if not candidates:
        return pd.DataFrame(), {
            "source_file_used": "",
            "source_type_used": "NO_LIVE_SOURCE",
            "source_priority_v2": 999,
            "rows": 0,
            "race_key_match_rows": 0,
            "race_composite_match_rows": 0,
            "matched_rows": 0,
            "match_rate_pct": 0.0,
        }

    candidates.sort(
        key=lambda item: (
            float(item[1]["match_rate_pct"]),
            int(item[1]["matched_rows"]),
            -int(item[1]["source_priority_v2"]),
        ),
        reverse=True,
    )
    return candidates[0]


def merge_with_suffix(feed: pd.DataFrame, lookup: pd.DataFrame, left_key: str, right_key: str, suffix: str) -> pd.DataFrame:
    rename_map = {column: f"{column}{suffix}" for column in JOIN_FIELD_COLUMNS}
    lookup_renamed = lookup.rename(columns=rename_map)
    merged = feed.merge(lookup_renamed, left_on=left_key, right_on=right_key, how="left")
    return merged.drop(columns=[right_key], errors="ignore")


def coalesce_match_columns(feed: pd.DataFrame) -> pd.DataFrame:
    for base_col in JOIN_FIELD_COLUMNS:
        race_key_col = f"{base_col}_racekey"
        race_comp_col = f"{base_col}_racecmp"
        horse_col = f"{base_col}_horse"

        if base_col not in feed.columns:
            feed[base_col] = pd.NA

        if race_key_col in feed.columns:
            feed[base_col] = feed[base_col].where(feed[base_col].notna(), feed[race_key_col])
        if race_comp_col in feed.columns:
            feed[base_col] = feed[base_col].where(feed[base_col].notna(), feed[race_comp_col])
        if horse_col in feed.columns:
            feed[base_col] = feed[base_col].where(feed[base_col].notna(), feed[horse_col])

    return feed


def build_output_frames(feed: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    env_output_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "runner_no",
        "barrier",
        "jockey",
        "trainer",
        "field_size",
        "trust_profile_v1",
        "environment_score_v2",
        "environment_band_v2",
        "environment_reason_v2",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
        "environment_band_comparison_v2_vs_v1",
        "environment_band_delta_v2_vs_v1",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "race_reliability_reason_v1",
        "race_reliability_display_label_v1",
        "race_reliability_display_rank_v1",
        "race_reliability_plain_english_v1",
        "race_reliability_ui_hint_v1",
        "environment_live_display_label_v2",
        "environment_live_display_rank_v2",
        "environment_live_governance_hint_v2",
        "environment_v2_source_status",
        "environment_v2_join_key",
    ]
    for column in env_output_columns:
        if column not in feed.columns:
            feed[column] = ""
    env_output = feed[env_output_columns].copy()

    rr_output_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "runner_no",
        "barrier",
        "jockey",
        "trainer",
        "field_size",
        "trust_profile_v1",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "race_reliability_reason_v1",
        "race_reliability_display_label_v1",
        "race_reliability_display_rank_v1",
        "race_reliability_plain_english_v1",
        "race_reliability_ui_hint_v1",
        "environment_score_v2",
        "environment_band_v2",
        "environment_reason_v2",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
        "environment_v2_source_status",
        "environment_v2_join_key",
    ]
    for column in rr_output_columns:
        if column not in feed.columns:
            feed[column] = ""
    rr_output = feed[rr_output_columns].copy()
    return env_output, rr_output


def main() -> None:
    source_path = RACE_RELIABILITY_PATH if RACE_RELIABILITY_PATH.exists() else ENV_V2_FALLBACK_PATH
    if not source_path.exists():
        raise SystemExit(f"Missing Race Reliability source file: {RACE_RELIABILITY_PATH}")

    source_df = pd.read_csv(source_path, low_memory=False)
    base_df, race_key_map, race_composite_map, runner_map = build_reliability_maps(source_df)

    live_feed, source_audit = select_best_live_source(race_key_map, race_composite_map)
    using_source_only = live_feed.empty

    if using_source_only:
        feed = pd.DataFrame()
        feed["meeting_date"] = base_df["meeting_date"].map(normalise_date)
        feed["track"] = base_df["track"].map(clean_text)
        feed["race_no"] = base_df["race_no"].map(normalise_race_no)
        feed["race_key"] = base_df["race_composite_key_v2"]
        feed["horse"] = base_df.get("rank1_horse", base_df.get("horse", "")).map(clean_text)
        feed["horse_key"] = base_df["environment_horse_key_v2"].map(normalise_horse_key)
        feed["runner_no"] = ""
        feed["barrier"] = ""
        feed["jockey"] = ""
        feed["trainer"] = ""
        feed["field_size"] = pd.to_numeric(base_df.get("field_size"), errors="coerce")
        feed["environment_v2_join_key"] = base_df["environment_v2_join_key"]
        for column in JOIN_FIELD_COLUMNS:
            feed[column] = base_df.get(column, pd.NA)
        feed["environment_v2_source_status"] = "RACE_RELIABILITY_SELF_SOURCE"
        source_file_used = source_path.name
        source_type_used = "RACE_RELIABILITY_SELF_SOURCE"
        race_key_match_rows = len(feed)
        race_composite_match_rows = 0
        horse_fallback_match_rows = 0
    else:
        source_file_used = str(source_audit["source_file_used"])
        source_type_used = str(source_audit["source_type_used"])

        feed = live_feed.copy()
        feed = merge_with_suffix(feed, race_key_map, "race_key_stage1_v2", "race_key_stage1_v2", "_racekey")
        feed = merge_with_suffix(feed, race_composite_map, "race_composite_key_v2", "race_composite_key_v2", "_racecmp")
        feed = merge_with_suffix(feed, runner_map, "environment_v2_join_key", "environment_v2_join_key", "_horse")
        feed = coalesce_match_columns(feed)

        race_key_hits = feed["race_reliability_band_v1_racekey"].notna() if "race_reliability_band_v1_racekey" in feed.columns else pd.Series(False, index=feed.index)
        race_composite_hits = (~race_key_hits) & feed["race_reliability_band_v1_racecmp"].notna() if "race_reliability_band_v1_racecmp" in feed.columns else pd.Series(False, index=feed.index)
        horse_hits = (~race_key_hits) & (~race_composite_hits) & feed["race_reliability_band_v1_horse"].notna() if "race_reliability_band_v1_horse" in feed.columns else pd.Series(False, index=feed.index)

        feed["environment_v2_source_status"] = "NO_ENVIRONMENT_MATCH"
        feed.loc[race_key_hits, "environment_v2_source_status"] = "RACE_KEY_MATCH"
        feed.loc[race_composite_hits, "environment_v2_source_status"] = "RACE_COMPOSITE_MATCH"
        feed.loc[horse_hits, "environment_v2_source_status"] = "HORSE_LEVEL_FALLBACK_MATCH"

        race_key_match_rows = int(race_key_hits.sum())
        race_composite_match_rows = int(race_composite_hits.sum())
        horse_fallback_match_rows = int(horse_hits.sum())

    feed["environment_band_v2"] = feed["environment_band_v2"].fillna("UNKNOWN")
    feed["race_reliability_band_v1"] = feed["race_reliability_band_v1"].fillna("UNKNOWN")
    feed["race_reliability_display_label_v1"] = feed["race_reliability_band_v1"].map(lambda value: RR_DISPLAY_LABELS.get(value, RR_DISPLAY_LABELS["UNKNOWN"]))
    feed["race_reliability_display_rank_v1"] = feed["race_reliability_band_v1"].map(lambda value: RR_DISPLAY_RANKS.get(value, 0))
    feed["race_reliability_plain_english_v1"] = feed["race_reliability_band_v1"].map(lambda value: RR_PLAIN_ENGLISH.get(value, RR_PLAIN_ENGLISH["UNKNOWN"]))
    feed["race_reliability_ui_hint_v1"] = feed["race_reliability_band_v1"].map(lambda value: RR_UI_HINTS.get(value, RR_UI_HINTS["UNKNOWN"]))
    feed["environment_live_display_label_v2"] = feed["environment_band_v2"].map(lambda value: ENV_DISPLAY_LABELS.get(value, ENV_DISPLAY_LABELS["UNKNOWN"]))
    feed["environment_live_display_rank_v2"] = feed["environment_band_v2"].map(lambda value: ENV_DISPLAY_RANKS.get(value, 0))
    feed["environment_live_governance_hint_v2"] = feed["environment_band_v2"].map(lambda value: ENV_GOVERNANCE_HINTS.get(value, ENV_GOVERNANCE_HINTS["UNKNOWN"]))

    env_output, rr_output = build_output_frames(feed)
    env_output.to_csv(OUTPUT_ENV_MAIN, index=False)
    rr_output.to_csv(OUTPUT_RR_MAIN, index=False)

    unmatched_mask = feed["environment_v2_source_status"] == "NO_ENVIRONMENT_MATCH"
    env_output.loc[unmatched_mask].to_csv(OUTPUT_ENV_UNMATCHED, index=False)
    rr_output.loc[unmatched_mask].to_csv(OUTPUT_RR_UNMATCHED, index=False)

    live_rows = int(len(feed))
    matched_rows = int((feed["environment_v2_source_status"] != "NO_ENVIRONMENT_MATCH").sum())
    unmatched_rows = int(unmatched_mask.sum())
    match_rate_pct = round((matched_rows / live_rows) * 100, 2) if live_rows else 0.0

    if match_rate_pct >= 95:
        verdict = "LIVE_RACE_RELIABILITY_V1_READY"
    elif match_rate_pct >= 80:
        verdict = "LIVE_RACE_RELIABILITY_V1_PARTIAL_READY"
    else:
        verdict = "LIVE_RACE_RELIABILITY_V1_JOIN_NEEDS_REVIEW"

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "source_file_used", "value": source_file_used},
        {"metric": "source_type_used", "value": source_type_used},
        {"metric": "source_selection_mode", "value": "BEST_RACE_LEVEL_COVERAGE"},
        {"metric": "live_rows", "value": live_rows},
        {"metric": "matched_environment_v2_rows", "value": matched_rows},
        {"metric": "matched_race_reliability_rows", "value": matched_rows},
        {"metric": "unmatched_environment_v2_rows", "value": unmatched_rows},
        {"metric": "unmatched_race_reliability_rows", "value": unmatched_rows},
        {"metric": "match_rate_pct", "value": match_rate_pct},
        {"metric": "race_key_match_rows", "value": race_key_match_rows},
        {"metric": "race_composite_match_rows", "value": race_composite_match_rows},
        {"metric": "horse_level_fallback_match_rows", "value": horse_fallback_match_rows},
        {"metric": "rows_by_environment_band_v2", "value": rows_by_band(feed["environment_band_v2"])},
        {"metric": "rows_by_race_reliability_band_v1", "value": rows_by_band(feed["race_reliability_band_v1"])},
        {"metric": "v2_elite_rows", "value": int((feed["environment_band_v2"] == "ELITE").sum())},
        {"metric": "v2_positive_rows", "value": int((feed["environment_band_v2"] == "POSITIVE").sum())},
        {"metric": "v2_neutral_rows", "value": int((feed["environment_band_v2"] == "NEUTRAL").sum())},
        {"metric": "v2_negative_rows", "value": int((feed["environment_band_v2"] == "NEGATIVE").sum())},
        {"metric": "v2_poor_rows", "value": int((feed["environment_band_v2"] == "POOR").sum())},
        {"metric": "race_reliability_elite_rows", "value": int((feed["race_reliability_band_v1"] == "ELITE").sum())},
        {"metric": "race_reliability_positive_rows", "value": int((feed["race_reliability_band_v1"] == "POSITIVE").sum())},
        {"metric": "race_reliability_neutral_rows", "value": int((feed["race_reliability_band_v1"] == "NEUTRAL").sum())},
        {"metric": "race_reliability_negative_rows", "value": int((feed["race_reliability_band_v1"] == "NEGATIVE").sum())},
        {"metric": "race_reliability_poor_rows", "value": int((feed["race_reliability_band_v1"] == "POOR").sum())},
        {"metric": "output_environment_file", "value": str(OUTPUT_ENV_MAIN)},
        {"metric": "output_race_reliability_file", "value": str(OUTPUT_RR_MAIN)},
        {"metric": "verdict", "value": verdict},
    ]
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUTPUT_ENV_SUMMARY, index=False)
    summary_df.to_csv(OUTPUT_RR_SUMMARY, index=False)

    print("[LIVE_RACE_RELIABILITY_V1_FEED] COMPLETE")
    print("status=COMPLETE")
    print(f"source_file_used={source_file_used}")
    print(f"live_rows={live_rows}")
    print(f"matched_race_reliability_rows={matched_rows}")
    print(f"unmatched_race_reliability_rows={unmatched_rows}")
    print(f"match_rate_pct={match_rate_pct}")
    print(f"verdict={verdict}")
    print(f"wrote={OUTPUT_RR_MAIN}")
    print(f"wrote={OUTPUT_RR_SUMMARY}")
    print(f"wrote={OUTPUT_RR_UNMATCHED}")
    print(f"wrote={OUTPUT_ENV_MAIN}")
    print(f"wrote={OUTPUT_ENV_SUMMARY}")
    print(f"wrote={OUTPUT_ENV_UNMATCHED}")


if __name__ == "__main__":
    main()
