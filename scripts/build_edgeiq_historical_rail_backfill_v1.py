from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_CALENDAR = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"
IN_RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT_MAIN = DATA / "edgeiq_historical_rail_backfill_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_historical_rail_backfill_v1_summary.csv"
OUT_UNMATCHED = DATA / "edgeiq_historical_rail_backfill_v1_unmatched.csv"
OUT_JSON = DATA / "edgeiq_historical_rail_backfill_v1.json"

RACINGCOM_FORM_CONFIG = "https://www.racing.com/form/config.js"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
SPONSOR_TOKENS = [
    "BET365",
    "SPORTSBET",
    "LADBROKES",
    "TAB",
    "RACINGCOM",
    "RACING COM",
    "PICKLEBET",
    "APIAM",
    "BETDELUXE",
    "SOUTHSIDE",
]
COMMON_NON_VALUES = {"", "N/A", "NA", "NULL", "NONE", "NAN", "0.00", "0001-01-01"}
GRAPHQL_QUERY_MONTH = """
query($year:Int,$month:Int){
  GetMeetingByMonth(year:$year, month:$month){
    id
    date
    venueName
    venueCode
    trackName
    railPosition
    trackCondition
    penetrometer
    weather
    previousRailDate
    previousRailPosition
    previousTrackCondition
    racesCount
  }
}
"""


@dataclass
class GraphQLConfig:
    endpoint: str
    api_key: str


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    if "low_memory" not in kwargs:
        kwargs["low_memory"] = False
    return pd.read_csv(path, **kwargs)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def write_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def nonblank_series_mask(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip().str.upper()
    return ~values.isin(COMMON_NON_VALUES)


def normalize_track(value) -> str:
    text = "" if pd.isna(value) else str(value).upper()
    for token in SPONSOR_TOKENS:
        text = text.replace(token, " ")
    text = text.replace("-", " ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def alias_track_key(value) -> str:
    text = normalize_track(value)
    replacements = {
        "PARK WODONGA": "WODONGA",
        "BALLARAT SYNTHETIC": "BALLARAT SYN",
        "PAKENHAM SYNTHETIC": "PAKENHAM SYNTHETIC",
        "SOUTHSIDE PAKENHAM SYNTHETIC": "PAKENHAM SYNTHETIC",
        "BETDELUXE WARRACKNABEAL": "WARRACKNABEAL",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def parse_float(text: str) -> float | None:
    try:
        return float(text)
    except Exception:
        return None


def rail_normalization(raw_value) -> tuple[bool, float | None, str]:
    if pd.isna(raw_value):
        return False, None, "UNKNOWN"
    raw_text = str(raw_value).strip()
    if not raw_text or raw_text.upper() in COMMON_NON_VALUES:
        return False, None, "UNKNOWN"

    text = raw_text.upper()
    meter_matches = [
        value
        for value in (
            parse_float(match)
            for match in re.findall(r"(\d+(?:\.\d+)?)\s*M", text)
        )
        if value is not None
    ]
    if meter_matches:
        meters = max(meter_matches)
        if meters >= 12:
            bucket = "12M_PLUS"
        elif meters >= 9:
            bucket = "9_12M"
        elif meters >= 6:
            bucket = "6_9M"
        elif meters >= 3:
            bucket = "3_6M"
        else:
            bucket = "0_3M"
        return False, round(float(meters), 2), bucket

    true_flag = bool(re.search(r"\bTRUE\b", text))
    if true_flag:
        return True, 0.0, "TRUE"
    return False, None, "UNKNOWN"


def fetch_config() -> GraphQLConfig:
    response = requests.get(
        RACINGCOM_FORM_CONFIG,
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    text = response.text
    endpoint_match = re.search(r'GraphqlEndpoint:"([^"]+)"', text)
    key_match = re.search(r'ChampionDataEndpointKey:"([^"]+)"', text)
    if not endpoint_match or not key_match:
        raise RuntimeError("Could not parse Racing.com GraphQL config.")
    return GraphQLConfig(endpoint=endpoint_match.group(1), api_key=key_match.group(1))


def graphql_post(config: GraphQLConfig, query: str, variables: dict | None = None) -> dict:
    headers = {
        "x-api-key": config.api_key,
        "User-Agent": USER_AGENT,
        "Origin": "https://www.racing.com",
        "Referer": "https://www.racing.com/",
    }
    response = requests.post(
        config.endpoint,
        json={"query": query, "variables": variables or {}},
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise RuntimeError(json.dumps(payload["errors"][:3]))
    return payload["data"]


def iter_months(start_dt: date, end_dt: date) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    year = start_dt.year
    month = start_dt.month
    while (year, month) <= (end_dt.year, end_dt.month):
        months.append((year, month))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months


def load_graphql_historical_meets(config: GraphQLConfig, start_dt: date, end_dt: date) -> pd.DataFrame:
    rows: list[dict] = []
    for year, month in iter_months(start_dt, end_dt):
        payload = graphql_post(config, GRAPHQL_QUERY_MONTH, {"year": year, "month": month})
        for item in payload.get("GetMeetingByMonth", []):
            rows.append(item)

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("Racing.com GraphQL historical meet query returned no rows.")

    df["meeting_date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["normalized_track"] = df["trackName"].map(normalize_track)
    df["alias_track"] = df["trackName"].map(alias_track_key)
    df["rail_present_flag_v1"] = nonblank_series_mask(df["railPosition"])
    df["track_condition_present_flag_v1"] = nonblank_series_mask(df["trackCondition"])
    df["weather_present_flag_v1"] = nonblank_series_mask(df["weather"])
    df["penetrometer_present_flag_v1"] = nonblank_series_mask(df["penetrometer"])
    df["previous_rail_present_flag_v1"] = nonblank_series_mask(df["previousRailPosition"])
    df["source_meet_id"] = df["id"].astype(str)
    return df


def load_results_race_universe() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = read_csv(
        IN_RESULTS,
        usecols=["meeting_date", "track", "race_no", "finishPosition", "source_url"],
    )
    raw["finish_position_num"] = pd.to_numeric(raw["finishPosition"], errors="coerce")
    usable = raw[raw["finish_position_num"].notna()].copy()
    usable["meeting_date"] = pd.to_datetime(usable["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    usable["race_no"] = pd.to_numeric(usable["race_no"], errors="coerce").astype("Int64")
    usable = usable[usable["meeting_date"].notna() & usable["race_no"].notna()].copy()
    usable["normalized_track"] = usable["track"].map(normalize_track)
    usable["alias_track"] = usable["track"].map(alias_track_key)

    races = (
        usable.groupby(["meeting_date", "track", "normalized_track", "alias_track", "race_no"], dropna=False)
        .agg(results_source_url=("source_url", lambda s: s.dropna().iloc[0] if not s.dropna().empty else ""))
        .reset_index()
    )
    races["race_key"] = (
        races["meeting_date"].astype(str)
        + "|"
        + races["normalized_track"].astype(str)
        + "|R"
        + races["race_no"].astype(str)
    )

    meetings = (
        races.groupby(["meeting_date", "track", "normalized_track", "alias_track"], dropna=False)
        .agg(races_in_meeting=("race_no", "nunique"))
        .reset_index()
    )
    return races, meetings


def load_calendar_races() -> pd.DataFrame:
    calendar = read_csv(
        IN_CALENDAR,
        usecols=[
            "meeting_date",
            "track",
            "race_no",
            "meeting_url",
            "race_url",
            "source_url",
            "discovery_status",
            "state",
            "meet_status",
        ],
    )
    calendar["meeting_date"] = pd.to_datetime(calendar["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    calendar["race_no"] = pd.to_numeric(calendar["race_no"], errors="coerce").astype("Int64")
    calendar = calendar[calendar["meeting_date"].notna() & calendar["race_no"].notna()].copy()
    calendar["normalized_track"] = calendar["track"].map(normalize_track)
    calendar["alias_track"] = calendar["track"].map(alias_track_key)

    calendar = (
        calendar.sort_values(["meeting_date", "track", "race_no"])
        .drop_duplicates(subset=["meeting_date", "normalized_track", "race_no"], keep="first")
        .reset_index(drop=True)
    )
    return calendar


def prepare_graphql_match_tables(graphql_meets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sort_cols = [
        "rail_present_flag_v1",
        "track_condition_present_flag_v1",
        "weather_present_flag_v1",
        "penetrometer_present_flag_v1",
        "racesCount",
    ]
    strict = (
        graphql_meets.sort_values(sort_cols, ascending=[False, False, False, False, False])
        .drop_duplicates(subset=["meeting_date", "normalized_track"], keep="first")
        .reset_index(drop=True)
    )
    alias = (
        graphql_meets.sort_values(sort_cols, ascending=[False, False, False, False, False])
        .drop_duplicates(subset=["meeting_date", "alias_track"], keep="first")
        .reset_index(drop=True)
    )
    return strict, alias


def merge_graphql_metadata(races: pd.DataFrame, strict: pd.DataFrame, alias: pd.DataFrame) -> pd.DataFrame:
    strict_cols = [
        "meeting_date",
        "normalized_track",
        "source_meet_id",
        "trackName",
        "venueName",
        "venueCode",
        "railPosition",
        "previousRailPosition",
        "previousRailDate",
        "trackCondition",
        "weather",
        "penetrometer",
        "racesCount",
        "rail_present_flag_v1",
        "track_condition_present_flag_v1",
        "weather_present_flag_v1",
        "penetrometer_present_flag_v1",
    ]
    alias_cols = [
        "meeting_date",
        "alias_track",
        "source_meet_id",
        "trackName",
        "venueName",
        "venueCode",
        "railPosition",
        "previousRailPosition",
        "previousRailDate",
        "trackCondition",
        "weather",
        "penetrometer",
        "racesCount",
        "rail_present_flag_v1",
        "track_condition_present_flag_v1",
        "weather_present_flag_v1",
        "penetrometer_present_flag_v1",
    ]

    merged = races.merge(
        strict[strict_cols].rename(columns={col: f"strict_{col}" for col in strict_cols if col not in {"meeting_date", "normalized_track"}}),
        on=["meeting_date", "normalized_track"],
        how="left",
    )
    merged = merged.merge(
        alias[alias_cols].rename(columns={col: f"alias_{col}" for col in alias_cols if col not in {"meeting_date", "alias_track"}}),
        on=["meeting_date", "alias_track"],
        how="left",
    )

    strict_match = merged["strict_source_meet_id"].notna()
    alias_match = merged["alias_source_meet_id"].notna()
    use_alias = (~strict_match) & alias_match

    chosen_fields = {
        "source_meet_id": ("strict_source_meet_id", "alias_source_meet_id"),
        "source_track_name": ("strict_trackName", "alias_trackName"),
        "source_venue_name": ("strict_venueName", "alias_venueName"),
        "source_venue_code": ("strict_venueCode", "alias_venueCode"),
        "rail_position": ("strict_railPosition", "alias_railPosition"),
        "previous_rail_position": ("strict_previousRailPosition", "alias_previousRailPosition"),
        "previous_rail_date": ("strict_previousRailDate", "alias_previousRailDate"),
        "track_condition_graphql": ("strict_trackCondition", "alias_trackCondition"),
        "weather_graphql": ("strict_weather", "alias_weather"),
        "penetrometer_graphql": ("strict_penetrometer", "alias_penetrometer"),
        "source_races_count": ("strict_racesCount", "alias_racesCount"),
        "rail_present_flag_v1": ("strict_rail_present_flag_v1", "alias_rail_present_flag_v1"),
        "track_condition_present_flag_v1": (
            "strict_track_condition_present_flag_v1",
            "alias_track_condition_present_flag_v1",
        ),
        "weather_present_flag_v1": ("strict_weather_present_flag_v1", "alias_weather_present_flag_v1"),
        "penetrometer_present_flag_v1": (
            "strict_penetrometer_present_flag_v1",
            "alias_penetrometer_present_flag_v1",
        ),
    }

    for out_col, (strict_col, alias_col) in chosen_fields.items():
        merged[out_col] = merged[strict_col]
        merged.loc[use_alias, out_col] = merged.loc[use_alias, alias_col]

    strict_rail_present = merged["strict_rail_present_flag_v1"].fillna(False).astype(bool)
    alias_rail_present = merged["alias_rail_present_flag_v1"].fillna(False).astype(bool)
    merged["source_match_method"] = "UNMATCHED"
    merged.loc[strict_match, "source_match_method"] = "STRICT"
    merged.loc[use_alias, "source_match_method"] = "ALIAS"

    merged["source_status"] = "UNMATCHED_NO_GRAPHQL_MEET"
    merged.loc[strict_match & strict_rail_present, "source_status"] = "MATCHED_STRICT"
    merged.loc[strict_match & ~strict_rail_present, "source_status"] = "MATCHED_STRICT_RAIL_NULL"
    merged.loc[use_alias & alias_rail_present, "source_status"] = "MATCHED_ALIAS"
    merged.loc[use_alias & ~alias_rail_present, "source_status"] = "MATCHED_ALIAS_RAIL_NULL"

    return merged


def enrich_with_calendar(races: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    merged = races.merge(
        calendar[
            [
                "meeting_date",
                "normalized_track",
                "race_no",
                "meeting_url",
                "race_url",
                "source_url",
                "discovery_status",
                "state",
                "meet_status",
            ]
        ].rename(
            columns={
                "source_url": "calendar_source_url",
                "discovery_status": "calendar_discovery_status",
                "state": "calendar_state",
                "meet_status": "calendar_meet_status",
            }
        ),
        on=["meeting_date", "normalized_track", "race_no"],
        how="left",
    )
    return merged


def add_rail_normalization(df: pd.DataFrame) -> pd.DataFrame:
    parsed = df["rail_position"].apply(rail_normalization)
    df["rail_true_flag"] = parsed.map(lambda item: item[0])
    df["rail_out_meters"] = parsed.map(lambda item: item[1])
    df["rail_bucket"] = parsed.map(lambda item: item[2])
    return df


def build_summary(main_df: pd.DataFrame, meeting_df: pd.DataFrame) -> pd.DataFrame:
    total_races = int(len(main_df))
    matched_races = int((main_df["source_status"] != "UNMATCHED_NO_GRAPHQL_MEET").sum())
    rail_nonblank = int(nonblank_series_mask(main_df["rail_position"]).sum())
    rail_null = int((main_df["source_status"] != "UNMATCHED_NO_GRAPHQL_MEET").sum() - rail_nonblank)
    matched_meetings = int((meeting_df["source_status"] != "UNMATCHED_NO_GRAPHQL_MEET").sum())
    unmatched_meetings = int((meeting_df["source_status"] == "UNMATCHED_NO_GRAPHQL_MEET").sum())

    metrics = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "historical_universe_races", "value": total_races},
        {"metric": "rail_rows", "value": total_races},
        {"metric": "matched_races", "value": matched_races},
        {"metric": "rail_coverage_pct", "value": round((rail_nonblank / total_races) * 100.0, 2) if total_races else 0.0},
        {"metric": "matched_meetings", "value": matched_meetings},
        {"metric": "unmatched_meetings", "value": unmatched_meetings},
        {"metric": "rail_null_rows", "value": rail_null},
        {"metric": "earliest_date", "value": main_df["meeting_date"].min() if total_races else ""},
        {"metric": "latest_date", "value": main_df["meeting_date"].max() if total_races else ""},
        {"metric": "weather_coverage_pct", "value": round((nonblank_series_mask(main_df["weather_graphql"]).sum() / total_races) * 100.0, 2) if total_races else 0.0},
        {"metric": "condition_coverage_pct", "value": round((nonblank_series_mask(main_df["track_condition_graphql"]).sum() / total_races) * 100.0, 2) if total_races else 0.0},
        {"metric": "penetrometer_coverage_pct", "value": round((nonblank_series_mask(main_df["penetrometer_graphql"]).sum() / total_races) * 100.0, 2) if total_races else 0.0},
        {"metric": "strict_match_races", "value": int((main_df["source_match_method"] == "STRICT").sum())},
        {"metric": "alias_match_races", "value": int((main_df["source_match_method"] == "ALIAS").sum())},
        {"metric": "unmatched_races", "value": int((main_df["source_match_method"] == "UNMATCHED").sum())},
        {"metric": "true_rail_rows", "value": int((main_df["rail_bucket"] == "TRUE").sum())},
        {"metric": "unknown_rail_bucket_rows", "value": int((main_df["rail_bucket"] == "UNKNOWN").sum())},
    ]
    return pd.DataFrame(metrics)


def build_json_payload(main_df: pd.DataFrame, unmatched_df: pd.DataFrame, summary_df: pd.DataFrame) -> dict:
    bucket_counts = (
        main_df.groupby("rail_bucket", dropna=False)
        .size()
        .reset_index(name="races")
        .sort_values(["races", "rail_bucket"], ascending=[False, True])
    )
    bucket_counts["pct"] = (bucket_counts["races"] / len(main_df) * 100.0).round(2) if len(main_df) else 0.0

    unmatched_tracks = (
        unmatched_df.groupby("track", dropna=False)
        .agg(races=("race_no", "size"), meetings=("meeting_date", "nunique"))
        .reset_index()
        .sort_values(["races", "meetings", "track"], ascending=[False, False, True])
        .head(25)
    )

    return {
        "status": "COMPLETE",
        "summary_metrics": {row["metric"]: row["value"] for row in summary_df.to_dict("records")},
        "top_unmatched_tracks": unmatched_tracks.to_dict("records"),
        "rail_bucket_distribution": bucket_counts.to_dict("records"),
        "source_status_distribution": (
            main_df.groupby("source_status", dropna=False)
            .size()
            .reset_index(name="races")
            .sort_values(["races", "source_status"], ascending=[False, True])
            .to_dict("records")
        ),
        "notes": [
            "Meeting-level Racing.com GraphQL metadata has been expanded to race-level rows for the historical results universe.",
            "Alias recovery is intentionally limited to known discovery misses so the sidecar stays conservative.",
            "rail_true_flag is only set when the raw rail text indicates true rail without an explicit positive meter offset.",
            "rail_out_meters uses the largest explicit meter value found in the raw rail text.",
        ],
    }


def main() -> None:
    results_races, results_meetings = load_results_race_universe()
    calendar = load_calendar_races()

    start_dt = pd.to_datetime(results_races["meeting_date"], errors="coerce").min().date()
    end_dt = pd.to_datetime(results_races["meeting_date"], errors="coerce").max().date()

    config = fetch_config()
    graphql_meets = load_graphql_historical_meets(config, start_dt, end_dt)
    strict_meets, alias_meets = prepare_graphql_match_tables(graphql_meets)

    main_df = merge_graphql_metadata(results_races, strict_meets, alias_meets)
    main_df = enrich_with_calendar(main_df, calendar)
    main_df = add_rail_normalization(main_df)

    main_df["normalized_track"] = main_df["normalized_track"].fillna("")
    previous_dt = pd.to_datetime(main_df["previous_rail_date"], errors="coerce")
    main_df["previous_rail_date"] = previous_dt.dt.strftime("%Y-%m-%d")
    main_df.loc[previous_dt.dt.year.fillna(0).lt(1901), "previous_rail_date"] = ""
    main_df["previous_rail_date"] = main_df["previous_rail_date"].fillna("")
    main_df["environment_source_note_v1"] = "RESEARCH_SIDECAR_ONLY"

    output_cols = [
        "meeting_date",
        "track",
        "normalized_track",
        "race_no",
        "race_key",
        "rail_position",
        "previous_rail_position",
        "previous_rail_date",
        "track_condition_graphql",
        "weather_graphql",
        "penetrometer_graphql",
        "source_meet_id",
        "source_track_name",
        "source_venue_name",
        "source_venue_code",
        "source_match_method",
        "source_status",
        "rail_true_flag",
        "rail_out_meters",
        "rail_bucket",
        "calendar_state",
        "calendar_meet_status",
        "meeting_url",
        "race_url",
        "calendar_source_url",
        "calendar_discovery_status",
        "results_source_url",
        "environment_source_note_v1",
    ]
    main_df = main_df[output_cols].sort_values(["meeting_date", "track", "race_no"]).reset_index(drop=True)

    unmatched_df = main_df[main_df["source_status"] == "UNMATCHED_NO_GRAPHQL_MEET"].copy()

    meeting_status_df = (
        main_df.groupby(["meeting_date", "track", "normalized_track"], dropna=False)
        .agg(
            races=("race_no", "size"),
            source_status=("source_status", lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]),
        )
        .reset_index()
    )
    summary_df = build_summary(main_df, meeting_status_df)
    json_payload = build_json_payload(main_df, unmatched_df, summary_df)

    write_csv(main_df, OUT_MAIN)
    write_csv(summary_df, OUT_SUMMARY)
    write_csv(unmatched_df, OUT_UNMATCHED)
    write_json(json_payload, OUT_JSON)

    total_rows = len(main_df)
    matched_rows = int((main_df["source_status"] != "UNMATCHED_NO_GRAPHQL_MEET").sum())
    coverage = round((nonblank_series_mask(main_df["rail_position"]).sum() / total_rows) * 100.0, 2) if total_rows else 0.0

    print("[HISTORICAL_RAIL_BACKFILL_V1] COMPLETE")
    print("status=COMPLETE")
    print(f"historical_universe_races={total_rows}")
    print(f"matched_races={matched_rows}")
    print(f"rail_coverage_pct={coverage}")
    print(f"matched_meetings={int((meeting_status_df['source_status'] != 'UNMATCHED_NO_GRAPHQL_MEET').sum())}")
    print(f"unmatched_meetings={int((meeting_status_df['source_status'] == 'UNMATCHED_NO_GRAPHQL_MEET').sum())}")
    print(f"rail_null_rows={int((main_df['source_status'] != 'UNMATCHED_NO_GRAPHQL_MEET').sum() - nonblank_series_mask(main_df['rail_position']).sum())}")
    print(f"earliest_date={main_df['meeting_date'].min() if total_rows else ''}")
    print(f"latest_date={main_df['meeting_date'].max() if total_rows else ''}")
    print(f"weather_coverage_pct={round((nonblank_series_mask(main_df['weather_graphql']).sum() / total_rows) * 100.0, 2) if total_rows else 0.0}")
    print(f"condition_coverage_pct={round((nonblank_series_mask(main_df['track_condition_graphql']).sum() / total_rows) * 100.0, 2) if total_rows else 0.0}")
    print(f"penetrometer_coverage_pct={round((nonblank_series_mask(main_df['penetrometer_graphql']).sum() / total_rows) * 100.0, 2) if total_rows else 0.0}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_UNMATCHED}")
    print(f"wrote={OUT_JSON}")


if __name__ == "__main__":
    main()
