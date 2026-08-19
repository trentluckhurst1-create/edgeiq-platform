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

OUT_AUDIT = DATA / "edgeiq_rail_data_discovery_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_rail_data_discovery_audit_summary_v1.csv"
OUT_JSON = DATA / "edgeiq_rail_data_discovery_audit_v1.json"

RACINGCOM_FORM_CONFIG = "https://www.racing.com/form/config.js"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
SPONSOR_TOKENS = ["BET365", "SPORTSBET", "LADBROKES", "TAB", "RACINGCOM", "RACING COM", "PICKLEBET", "APIAM"]
COMMON_NON_VALUES = {"", "N/A", "NA", "NULL", "NONE", "NAN", "0.00", "0001-01-01"}


@dataclass
class GraphQLConfig:
    endpoint: str
    api_key: str


def data_path(name: str) -> Path:
    return DATA / name


def read_csv(name: str, **kwargs) -> pd.DataFrame:
    path = data_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    if "low_memory" not in kwargs:
        kwargs["low_memory"] = False
    return pd.read_csv(path, **kwargs)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def write_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize_track(value) -> str:
    text = "" if pd.isna(value) else str(value).upper()
    for token in SPONSOR_TOKENS:
        text = text.replace(token, " ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def alias_track_key(value) -> str:
    text = normalize_track(value)
    replacements = {
        "PARK WODONGA": "WODONGA",
        "BALLARAT SYNTHETIC": "BALLARAT SYN",
        "SOUTHSIDE PAKENHAM SYNTHETIC": "PAKENHAM SYNTHETIC",
        "BETDELUXE WARRACKNABEAL": "WARRACKNABEAL",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def nonblank_pct(series: pd.Series) -> float | None:
    if series is None:
        return None
    values = series.fillna("").astype(str).str.strip()
    if len(values) == 0:
        return None
    nonblank = ~values.str.upper().isin(COMMON_NON_VALUES)
    return round(float(nonblank.mean()) * 100.0, 2)


def safe_int(value) -> int:
    if pd.isna(value):
        return 0
    return int(value)


def file_exists(name: str) -> bool:
    return data_path(name).exists()


def local_source_row(name: str) -> dict:
    path = data_path(name)
    if not path.exists():
        return {
            "section_v1": "LOCAL_SOURCE_AUDIT",
            "source_name_v1": name,
            "source_type_v1": "LOCAL_CSV",
            "file_or_url_v1": str(path),
            "file_exists_v1": False,
            "rows_v1": 0,
            "meetings_v1": 0,
            "races_v1": 0,
            "tracks_v1": 0,
            "date_start_v1": "",
            "date_end_v1": "",
            "rail_field_found_v1": False,
            "rail_nonblank_pct_v1": None,
            "track_condition_field_found_v1": False,
            "track_condition_nonblank_pct_v1": None,
            "weather_field_found_v1": False,
            "weather_nonblank_pct_v1": None,
            "penetrometer_field_found_v1": False,
            "penetrometer_nonblank_pct_v1": None,
            "notes_v1": "Missing local source file.",
            "evidence_sample_v1": "",
        }

    df = pd.read_csv(path, low_memory=False)
    cols_lower = {str(col).lower(): col for col in df.columns}

    def get_col(candidates: list[str]) -> str | None:
        for candidate in candidates:
            col = cols_lower.get(candidate.lower())
            if col:
                return col
        return None

    meeting_col = get_col(["meeting_date", "race_date", "date"])
    track_col = get_col(["track", "meeting_name", "location", "track_name"])
    race_col = get_col(["race_no", "race_number"])
    rail_col = get_col(["rail_position", "rail", "rail_position_rated", "track_rail", "rail_movement"])
    condition_col = get_col(["trackcondition", "track_condition", "track_condition_rated"])
    weather_col = get_col(["weather", "weather_condition", "weather_rated"])
    pen_col = get_col(["penetrometer"])

    date_start = ""
    date_end = ""
    if meeting_col:
        dates = pd.to_datetime(df[meeting_col], errors="coerce").dropna()
        if not dates.empty:
            date_start = dates.min().strftime("%Y-%m-%d")
            date_end = dates.max().strftime("%Y-%m-%d")

    meetings = 0
    races = 0
    if meeting_col and track_col:
        meetings = int(df[[meeting_col, track_col]].astype(str).drop_duplicates().shape[0])
        if race_col:
            races = int(df[[meeting_col, track_col, race_col]].astype(str).drop_duplicates().shape[0])

    sample = ""
    if rail_col:
        sample_values = (
            df[rail_col]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: ~s.str.upper().isin(COMMON_NON_VALUES)]
            .drop_duplicates()
            .head(5)
            .tolist()
        )
        sample = " | ".join(sample_values)

    notes = []
    if rail_col:
        notes.append(f"Rail column found: {rail_col}")
    else:
        notes.append("No rail-like column found.")
    if track_col:
        notes.append(f"Track source column: {track_col}")
    if meeting_col:
        notes.append(f"Date source column: {meeting_col}")

    return {
        "section_v1": "LOCAL_SOURCE_AUDIT",
        "source_name_v1": name,
        "source_type_v1": "LOCAL_CSV",
        "file_or_url_v1": str(path),
        "file_exists_v1": True,
        "rows_v1": int(len(df)),
        "meetings_v1": meetings,
        "races_v1": races,
        "tracks_v1": int(df[track_col].astype(str).nunique()) if track_col else 0,
        "date_start_v1": date_start,
        "date_end_v1": date_end,
        "rail_field_found_v1": rail_col is not None,
        "rail_nonblank_pct_v1": nonblank_pct(df[rail_col]) if rail_col else None,
        "track_condition_field_found_v1": condition_col is not None,
        "track_condition_nonblank_pct_v1": nonblank_pct(df[condition_col]) if condition_col else None,
        "weather_field_found_v1": weather_col is not None,
        "weather_nonblank_pct_v1": nonblank_pct(df[weather_col]) if weather_col else None,
        "penetrometer_field_found_v1": pen_col is not None,
        "penetrometer_nonblank_pct_v1": nonblank_pct(df[pen_col]) if pen_col else None,
        "notes_v1": " ".join(notes),
        "evidence_sample_v1": sample,
    }


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


def html_page_row(label: str, url: str) -> dict:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    text = response.text
    token_counts = {
        token: len(re.findall(token, text, re.I))
        for token in ["rail", "rail_position", "trackCondition", "weather", "penetrometer", "graphql", "config.js"]
    }
    sample_lines = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"rail|trackCondition|weather|penetrometer|graphql|config\.js", line, re.I)
    ][:5]
    return {
        "section_v1": "RACINGCOM_PAGE_HTML_SAMPLE",
        "source_name_v1": label,
        "source_type_v1": "RACINGCOM_HTML",
        "file_or_url_v1": url,
        "file_exists_v1": True,
        "rows_v1": None,
        "meetings_v1": None,
        "races_v1": None,
        "tracks_v1": None,
        "date_start_v1": "",
        "date_end_v1": "",
        "rail_field_found_v1": token_counts["rail"] > 0 or token_counts["rail_position"] > 0,
        "rail_nonblank_pct_v1": None,
        "track_condition_field_found_v1": token_counts["trackCondition"] > 0,
        "track_condition_nonblank_pct_v1": None,
        "weather_field_found_v1": token_counts["weather"] > 0,
        "weather_nonblank_pct_v1": None,
        "penetrometer_field_found_v1": token_counts["penetrometer"] > 0,
        "penetrometer_nonblank_pct_v1": None,
        "notes_v1": (
            f"Raw page shell token counts rail={token_counts['rail']} rail_position={token_counts['rail_position']} "
            f"trackCondition={token_counts['trackCondition']} weather={token_counts['weather']} "
            f"penetrometer={token_counts['penetrometer']} graphql={token_counts['graphql']} config.js={token_counts['config.js']}"
        ),
        "evidence_sample_v1": " | ".join(sample_lines),
    }


def schema_row(config: GraphQLConfig) -> dict:
    query = """
    {
      __type(name: "Meet") {
        fields {
          name
        }
      }
    }
    """
    fields = graphql_post(config, query)["__type"]["fields"]
    field_names = sorted(field["name"] for field in fields)
    interesting = [name for name in field_names if any(token in name.lower() for token in ["rail", "weather", "penet", "condition"])]
    return {
        "section_v1": "RACINGCOM_GRAPHQL_SCHEMA",
        "source_name_v1": "RACINGCOM_GRAPHQL_MEET_SCHEMA",
        "source_type_v1": "RACINGCOM_GRAPHQL",
        "file_or_url_v1": config.endpoint,
        "file_exists_v1": True,
        "rows_v1": len(field_names),
        "meetings_v1": None,
        "races_v1": None,
        "tracks_v1": None,
        "date_start_v1": "",
        "date_end_v1": "",
        "rail_field_found_v1": "railPosition" in field_names,
        "rail_nonblank_pct_v1": None,
        "track_condition_field_found_v1": "trackCondition" in field_names,
        "track_condition_nonblank_pct_v1": None,
        "weather_field_found_v1": "weather" in field_names,
        "weather_nonblank_pct_v1": None,
        "penetrometer_field_found_v1": "penetrometer" in field_names,
        "penetrometer_nonblank_pct_v1": None,
        "notes_v1": "Meet schema includes previousRailPosition and previousRailDate as well as live railPosition.",
        "evidence_sample_v1": " | ".join(interesting),
    }


def config_row(config: GraphQLConfig) -> dict:
    return {
        "section_v1": "RACINGCOM_CONFIG",
        "source_name_v1": "RACINGCOM_FORM_CONFIG_JS",
        "source_type_v1": "RACINGCOM_CONFIG",
        "file_or_url_v1": RACINGCOM_FORM_CONFIG,
        "file_exists_v1": True,
        "rows_v1": None,
        "meetings_v1": None,
        "races_v1": None,
        "tracks_v1": None,
        "date_start_v1": "",
        "date_end_v1": "",
        "rail_field_found_v1": None,
        "rail_nonblank_pct_v1": None,
        "track_condition_field_found_v1": None,
        "track_condition_nonblank_pct_v1": None,
        "weather_field_found_v1": None,
        "weather_nonblank_pct_v1": None,
        "penetrometer_field_found_v1": None,
        "penetrometer_nonblank_pct_v1": None,
        "notes_v1": "Config exposes GraphQL endpoint and API key used by the Racing.com form app.",
        "evidence_sample_v1": f"endpoint={config.endpoint} | api_key_present=YES",
    }


def load_results_meeting_universe() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = read_csv("edgeiq_racingcom_results_warehouse_v1.csv", usecols=["meeting_date", "track", "race_no", "finishPosition", "source_url"])
    raw["finish_position_num"] = pd.to_numeric(raw["finishPosition"], errors="coerce")
    usable = raw[raw["finish_position_num"].notna()].copy()
    usable["meeting_date"] = pd.to_datetime(usable["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    usable["track_norm"] = usable["track"].map(normalize_track)
    usable["race_no_num"] = pd.to_numeric(usable["race_no"], errors="coerce").astype("Int64")
    meetings = (
        usable.groupby(["meeting_date", "track_norm"], dropna=False)
        .agg(
            track_raw=("track", lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]),
            results_rows=("track", "size"),
            results_races=("race_no_num", "nunique"),
            sample_source_url=("source_url", lambda s: s.dropna().iloc[0] if not s.dropna().empty else ""),
        )
        .reset_index()
    )
    return usable, meetings


def iter_months(start_dt: date, end_dt: date) -> list[tuple[int, int]]:
    months = []
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
    query = """
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
    rows: list[dict] = []
    for year, month in iter_months(start_dt, end_dt):
        data = graphql_post(config, query, {"year": year, "month": month}).get("GetMeetingByMonth", [])
        for item in data:
            rows.append(item)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["meeting_date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["track_norm"] = df["trackName"].map(normalize_track)
    df["venue_norm"] = df["venueName"].map(lambda s: normalize_track(str(s).replace("-", " ")))
    df["rail_present_flag_v1"] = ~df["railPosition"].fillna("").astype(str).str.strip().str.upper().isin(COMMON_NON_VALUES)
    df["condition_present_flag_v1"] = ~df["trackCondition"].fillna("").astype(str).str.strip().str.upper().isin(COMMON_NON_VALUES)
    df["weather_present_flag_v1"] = ~df["weather"].fillna("").astype(str).str.strip().str.upper().isin(COMMON_NON_VALUES)
    df["penetrometer_present_flag_v1"] = ~df["penetrometer"].fillna("").astype(str).str.strip().str.upper().isin(COMMON_NON_VALUES)
    df["previous_rail_present_flag_v1"] = ~df["previousRailPosition"].fillna("").astype(str).str.strip().str.upper().isin(COMMON_NON_VALUES)
    return df


def build_historical_match(meetings: pd.DataFrame, graphql_meets: pd.DataFrame) -> pd.DataFrame:
    api = graphql_meets.copy()
    api = api.sort_values(
        ["rail_present_flag_v1", "condition_present_flag_v1", "weather_present_flag_v1", "penetrometer_present_flag_v1", "racesCount"],
        ascending=[False, False, False, False, False],
    )
    api = api.drop_duplicates(subset=["meeting_date", "track_norm"], keep="first")

    matched = meetings.merge(
        api[
            [
                "meeting_date",
                "track_norm",
                "id",
                "trackName",
                "venueName",
                "railPosition",
                "trackCondition",
                "penetrometer",
                "weather",
                "previousRailDate",
                "previousRailPosition",
                "previousTrackCondition",
                "racesCount",
                "rail_present_flag_v1",
                "condition_present_flag_v1",
                "weather_present_flag_v1",
                "penetrometer_present_flag_v1",
                "previous_rail_present_flag_v1",
            ]
        ],
        on=["meeting_date", "track_norm"],
        how="left",
    )
    matched["match_status_v1"] = matched["id"].notna().map({True: "MATCHED", False: "UNMATCHED"})
    matched["year_v1"] = matched["meeting_date"].str[:4]
    matched["rail_present_flag_v1"] = matched["rail_present_flag_v1"].fillna(False)
    matched["condition_present_flag_v1"] = matched["condition_present_flag_v1"].fillna(False)
    matched["weather_present_flag_v1"] = matched["weather_present_flag_v1"].fillna(False)
    matched["penetrometer_present_flag_v1"] = matched["penetrometer_present_flag_v1"].fillna(False)
    matched["previous_rail_present_flag_v1"] = matched["previous_rail_present_flag_v1"].fillna(False)
    return matched


def estimate_alias_recovery(meetings: pd.DataFrame, graphql_meets: pd.DataFrame, matched: pd.DataFrame) -> pd.DataFrame:
    unmatched = matched[matched["match_status_v1"] == "UNMATCHED"][["meeting_date", "track_norm", "track_raw", "results_rows", "results_races", "sample_source_url"]].copy()
    if unmatched.empty:
        return unmatched
    unmatched["alias_track_norm_v1"] = unmatched["track_raw"].map(alias_track_key)

    api = graphql_meets.copy()
    api["alias_track_norm_v1"] = api["trackName"].map(alias_track_key)
    api = api.sort_values(
        ["rail_present_flag_v1", "condition_present_flag_v1", "weather_present_flag_v1", "penetrometer_present_flag_v1", "racesCount"],
        ascending=[False, False, False, False, False],
    )
    api = api.drop_duplicates(subset=["meeting_date", "alias_track_norm_v1"], keep="first")

    recovered = unmatched.merge(
        api[
            [
                "meeting_date",
                "alias_track_norm_v1",
                "trackName",
                "venueName",
                "railPosition",
                "trackCondition",
                "weather",
                "penetrometer",
                "rail_present_flag_v1",
            ]
        ],
        on=["meeting_date", "alias_track_norm_v1"],
        how="left",
    )
    recovered["alias_recoverable_match_v1"] = recovered["trackName"].notna()
    return recovered


def historical_summary_rows(matched: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    overall = {
        "section_v1": "HISTORICAL_UNIVERSE_COVERAGE",
        "source_name_v1": "RACINGCOM_GRAPHQL_MEET_MATCH",
        "source_type_v1": "RACINGCOM_GRAPHQL",
        "file_or_url_v1": "https://graphql.rmdprod.racing.com/",
        "file_exists_v1": True,
        "rows_v1": int(matched["results_rows"].sum()),
        "meetings_v1": int(len(matched)),
        "races_v1": int(matched["results_races"].sum()),
        "tracks_v1": int(matched["track_norm"].nunique()),
        "date_start_v1": matched["meeting_date"].min(),
        "date_end_v1": matched["meeting_date"].max(),
        "rail_field_found_v1": True,
        "rail_nonblank_pct_v1": round(float(matched["rail_present_flag_v1"].mean()) * 100.0, 2),
        "track_condition_field_found_v1": True,
        "track_condition_nonblank_pct_v1": round(float(matched["condition_present_flag_v1"].mean()) * 100.0, 2),
        "weather_field_found_v1": True,
        "weather_nonblank_pct_v1": round(float(matched["weather_present_flag_v1"].mean()) * 100.0, 2),
        "penetrometer_field_found_v1": True,
        "penetrometer_nonblank_pct_v1": round(float(matched["penetrometer_present_flag_v1"].mean()) * 100.0, 2),
        "notes_v1": (
            f"Meeting match pct={round(float((matched['match_status_v1'] == 'MATCHED').mean()) * 100.0, 2)} "
            f"| race-weighted rail coverage={round(float(matched.loc[matched['rail_present_flag_v1'], 'results_races'].sum() / matched['results_races'].sum()) * 100.0, 2)}"
        ),
        "evidence_sample_v1": "",
    }
    rows.append(overall)

    for year, sub in matched.groupby("year_v1", dropna=False):
        rows.append(
            {
                "section_v1": "HISTORICAL_YEAR_COVERAGE",
                "source_name_v1": f"RACINGCOM_GRAPHQL_YEAR_{year}",
                "source_type_v1": "RACINGCOM_GRAPHQL",
                "file_or_url_v1": "https://graphql.rmdprod.racing.com/",
                "file_exists_v1": True,
                "rows_v1": int(sub["results_rows"].sum()),
                "meetings_v1": int(len(sub)),
                "races_v1": int(sub["results_races"].sum()),
                "tracks_v1": int(sub["track_norm"].nunique()),
                "date_start_v1": sub["meeting_date"].min(),
                "date_end_v1": sub["meeting_date"].max(),
                "rail_field_found_v1": True,
                "rail_nonblank_pct_v1": round(float(sub["rail_present_flag_v1"].mean()) * 100.0, 2),
                "track_condition_field_found_v1": True,
                "track_condition_nonblank_pct_v1": round(float(sub["condition_present_flag_v1"].mean()) * 100.0, 2),
                "weather_field_found_v1": True,
                "weather_nonblank_pct_v1": round(float(sub["weather_present_flag_v1"].mean()) * 100.0, 2),
                "penetrometer_field_found_v1": True,
                "penetrometer_nonblank_pct_v1": round(float(sub["penetrometer_present_flag_v1"].mean()) * 100.0, 2),
                "notes_v1": f"Race-weighted rail coverage={round(float(sub.loc[sub['rail_present_flag_v1'], 'results_races'].sum() / sub['results_races'].sum()) * 100.0, 2)}",
                "evidence_sample_v1": "",
            }
        )
    return rows


def current_graphql_row(config: GraphQLConfig, target_date: str) -> dict:
    query = """
    query($date:String){
      GetMeetingByDate(date:$date){
        date
        venueName
        trackName
        railPosition
        trackCondition
        penetrometer
        weather
        racesCount
      }
    }
    """
    data = graphql_post(config, query, {"date": target_date}).get("GetMeetingByDate", [])
    current = pd.DataFrame(data)
    if current.empty:
        return {
            "section_v1": "CURRENT_RACINGCOM_DAY",
            "source_name_v1": f"RACINGCOM_CURRENT_{target_date}",
            "source_type_v1": "RACINGCOM_GRAPHQL",
            "file_or_url_v1": "https://graphql.rmdprod.racing.com/",
            "file_exists_v1": True,
            "rows_v1": 0,
            "meetings_v1": 0,
            "races_v1": 0,
            "tracks_v1": 0,
            "date_start_v1": target_date,
            "date_end_v1": target_date,
            "rail_field_found_v1": True,
            "rail_nonblank_pct_v1": 0.0,
            "track_condition_field_found_v1": True,
            "track_condition_nonblank_pct_v1": 0.0,
            "weather_field_found_v1": True,
            "weather_nonblank_pct_v1": 0.0,
            "penetrometer_field_found_v1": True,
            "penetrometer_nonblank_pct_v1": 0.0,
            "notes_v1": "No meetings returned for current date query.",
            "evidence_sample_v1": "",
        }

    current["track_norm"] = current["trackName"].map(normalize_track)
    vicish = current[current["track_norm"].isin({"MORNINGTON", "GEELONG SYNTHETIC", "CAULFIELD HEATH", "FLEMINGTON", "SWAN HILL", "WARRNAMBOOL", "GEELONG", "BALLARAT", "CRANBOURNE", "THE VALLEY"})].copy()
    if vicish.empty:
        vicish = current.copy()

    rail_pct = nonblank_pct(vicish["railPosition"])
    cond_pct = nonblank_pct(vicish["trackCondition"])
    weather_pct = nonblank_pct(vicish["weather"])
    pen_pct = nonblank_pct(vicish["penetrometer"])
    sample = " | ".join(
        (
            vicish[["trackName", "railPosition", "trackCondition", "weather"]]
            .fillna("")
            .astype(str)
            .agg(" :: ".join, axis=1)
            .head(5)
            .tolist()
        )
    )
    return {
        "section_v1": "CURRENT_RACINGCOM_DAY",
        "source_name_v1": f"RACINGCOM_CURRENT_{target_date}",
        "source_type_v1": "RACINGCOM_GRAPHQL",
        "file_or_url_v1": "https://graphql.rmdprod.racing.com/",
        "file_exists_v1": True,
        "rows_v1": int(vicish["racesCount"].fillna(0).sum()),
        "meetings_v1": int(len(vicish)),
        "races_v1": int(vicish["racesCount"].fillna(0).sum()),
        "tracks_v1": int(vicish["track_norm"].nunique()),
        "date_start_v1": target_date,
        "date_end_v1": target_date,
        "rail_field_found_v1": True,
        "rail_nonblank_pct_v1": rail_pct,
        "track_condition_field_found_v1": True,
        "track_condition_nonblank_pct_v1": cond_pct,
        "weather_field_found_v1": True,
        "weather_nonblank_pct_v1": weather_pct,
        "penetrometer_field_found_v1": True,
        "penetrometer_nonblank_pct_v1": pen_pct,
        "notes_v1": "Current Racing.com upcoming meetings can return N/A or null before metadata is published.",
        "evidence_sample_v1": sample,
    }


def build_summary(metrics: dict) -> pd.DataFrame:
    return pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()])


def main():
    local_rows = [
        local_source_row("edgeiq_racingcom_historical_calendar_backfill_v1.csv"),
        local_source_row("edgeiq_racingcom_results_warehouse_v1.csv"),
        local_source_row("edgeiq_live_terminal_feed_v1.csv"),
        local_source_row("edgeiq_vic_three_day_meeting_universe.csv"),
        local_source_row("edgeiq_tab_vic_racecards_v1.csv"),
    ]

    config = fetch_config()
    usable_results, results_meetings = load_results_meeting_universe()
    min_date = pd.to_datetime(results_meetings["meeting_date"]).min().date()
    max_date = pd.to_datetime(results_meetings["meeting_date"]).max().date()
    graphql_meets = load_graphql_historical_meets(config, min_date, max_date)
    matched = build_historical_match(results_meetings, graphql_meets)
    alias_recovery = estimate_alias_recovery(results_meetings, graphql_meets, matched)

    sample_urls = []
    for year in ["2023", "2024", "2025", "2026"]:
        year_rows = results_meetings[results_meetings["meeting_date"].str.startswith(year)]
        if not year_rows.empty:
            sample_urls.append((f"RESULTS_PAGE_SAMPLE_{year}", year_rows.iloc[0]["sample_source_url"]))
    page_rows = [html_page_row(label, url) for label, url in sample_urls if isinstance(url, str) and url]

    config_audit = config_row(config)
    schema_audit = schema_row(config)
    current_row = current_graphql_row(config, "2026-06-10")

    historical_rows = historical_summary_rows(matched)

    meeting_detail_rows = []
    for row in matched.itertuples(index=False):
        meeting_detail_rows.append(
            {
                "section_v1": "HISTORICAL_MEETING_MATCH",
                "source_name_v1": "RACINGCOM_GRAPHQL_MEET_MATCH_DETAIL",
                "source_type_v1": "RACINGCOM_GRAPHQL",
                "file_or_url_v1": "https://graphql.rmdprod.racing.com/",
                "file_exists_v1": True,
                "meeting_date_v1": row.meeting_date,
                "track_v1": row.track_raw,
                "track_norm_v1": row.track_norm,
                "results_rows_v1": safe_int(row.results_rows),
                "results_races_v1": safe_int(row.results_races),
                "match_status_v1": row.match_status_v1,
                "api_meet_id_v1": row.id if pd.notna(row.id) else "",
                "api_track_name_v1": row.trackName if pd.notna(row.trackName) else "",
                "api_venue_name_v1": row.venueName if pd.notna(row.venueName) else "",
                "api_races_count_v1": safe_int(row.racesCount) if pd.notna(row.racesCount) else 0,
                "rail_position_v1": row.railPosition if pd.notna(row.railPosition) else "",
                "rail_present_flag_v1": bool(row.rail_present_flag_v1),
                "track_condition_v1": row.trackCondition if pd.notna(row.trackCondition) else "",
                "condition_present_flag_v1": bool(row.condition_present_flag_v1),
                "penetrometer_v1": row.penetrometer if pd.notna(row.penetrometer) else "",
                "penetrometer_present_flag_v1": bool(row.penetrometer_present_flag_v1),
                "weather_v1": row.weather if pd.notna(row.weather) else "",
                "weather_present_flag_v1": bool(row.weather_present_flag_v1),
                "previous_rail_date_v1": row.previousRailDate if pd.notna(row.previousRailDate) else "",
                "previous_rail_position_v1": row.previousRailPosition if pd.notna(row.previousRailPosition) else "",
                "previous_rail_present_flag_v1": bool(row.previous_rail_present_flag_v1),
                "sample_source_url_v1": row.sample_source_url,
            }
        )

    audit_df = pd.concat(
        [
            pd.DataFrame(local_rows),
            pd.DataFrame(page_rows),
            pd.DataFrame([config_audit, schema_audit, current_row]),
            pd.DataFrame(historical_rows),
            pd.DataFrame(meeting_detail_rows),
        ],
        ignore_index=True,
        sort=False,
    )
    write_csv(audit_df, OUT_AUDIT)

    matched_meetings = int((matched["match_status_v1"] == "MATCHED").sum())
    total_meetings = int(len(matched))
    matched_races = int(matched.loc[matched["match_status_v1"] == "MATCHED", "results_races"].sum())
    total_races = int(matched["results_races"].sum())
    rail_races = int(matched.loc[matched["rail_present_flag_v1"], "results_races"].sum())
    rail_meetings = int(matched["rail_present_flag_v1"].sum())
    alias_recoverable_races = int(alias_recovery.loc[alias_recovery["alias_recoverable_match_v1"], "results_races"].sum()) if not alias_recovery.empty else 0
    alias_recoverable_meetings = int(alias_recovery["alias_recoverable_match_v1"].sum()) if not alias_recovery.empty else 0
    alias_recovered_rail_races = int(alias_recovery.loc[alias_recovery["alias_recoverable_match_v1"] & alias_recovery["rail_present_flag_v1"], "results_races"].sum()) if not alias_recovery.empty else 0
    potential_rail_races = rail_races + alias_recovered_rail_races
    cond_races = int(matched.loc[matched["condition_present_flag_v1"], "results_races"].sum())
    weather_races = int(matched.loc[matched["weather_present_flag_v1"], "results_races"].sum())
    pen_races = int(matched.loc[matched["penetrometer_present_flag_v1"], "results_races"].sum())
    earliest_rail_date = matched.loc[matched["rail_present_flag_v1"], "meeting_date"].min()

    best_source = "RACINGCOM_GRAPHQL_MEET_METADATA"
    live_terminal_rail_pct = next(
        (row["rail_nonblank_pct_v1"] for row in local_rows if row["source_name_v1"] == "edgeiq_live_terminal_feed_v1.csv"),
        None,
    )

    is_rail_available_today = "YES_MIXED"
    if current_row["rail_nonblank_pct_v1"] in (None, 0.0):
        if live_terminal_rail_pct and live_terminal_rail_pct > 0:
            is_rail_available_today = "YES_IN_EDGEIQ_LIVE_FEED_NOT_IN_RACINGCOM_CURRENT_QUERY"
        else:
            is_rail_available_today = "NO"

    can_backfill = matched_races > 0 and rail_races / total_races >= 0.8 and matched_meetings / total_meetings >= 0.95
    verdict = "RAIL_ENGINE_FEASIBLE" if can_backfill else "RAIL_ENGINE_NOT_FEASIBLE"

    summary_metrics = {
        "status": "COMPLETE",
        "historical_universe_rows": int(len(usable_results)),
        "historical_universe_races": total_races,
        "historical_universe_meetings": total_meetings,
        "historical_universe_tracks": int(results_meetings["track_norm"].nunique()),
        "racingcom_graphql_matched_meetings": matched_meetings,
        "racingcom_graphql_matched_meeting_pct": round(float(matched_meetings / total_meetings) * 100.0, 2) if total_meetings else 0.0,
        "racingcom_graphql_matched_races": matched_races,
        "racingcom_graphql_matched_race_pct": round(float(matched_races / total_races) * 100.0, 2) if total_races else 0.0,
        "estimated_rail_coverage_races": rail_races,
        "estimated_rail_coverage_pct": round(float(rail_races / total_races) * 100.0, 2) if total_races else 0.0,
        "estimated_rail_coverage_meetings_pct": round(float(rail_meetings / total_meetings) * 100.0, 2) if total_meetings else 0.0,
        "alias_recoverable_meetings": alias_recoverable_meetings,
        "alias_recoverable_races": alias_recoverable_races,
        "potential_rail_coverage_pct_after_alias": round(float(potential_rail_races / total_races) * 100.0, 2) if total_races else 0.0,
        "estimated_track_condition_coverage_pct": round(float(cond_races / total_races) * 100.0, 2) if total_races else 0.0,
        "estimated_weather_coverage_pct": round(float(weather_races / total_races) * 100.0, 2) if total_races else 0.0,
        "estimated_penetrometer_coverage_pct": round(float(pen_races / total_races) * 100.0, 2) if total_races else 0.0,
        "earliest_available_date_in_historical_universe": earliest_rail_date,
        "is_rail_available_today": is_rail_available_today,
        "current_racingcom_day_rail_nonblank_pct": current_row["rail_nonblank_pct_v1"],
        "current_edgeiq_live_terminal_rail_nonblank_pct": live_terminal_rail_pct,
        "best_source": best_source,
        "can_rail_be_backfilled_historically": "YES" if can_backfill else "NO",
        "coverage_percentage_achievable": round(float(rail_races / total_races) * 100.0, 2) if total_races else 0.0,
        "final_verdict": verdict,
    }
    write_csv(build_summary(summary_metrics), OUT_SUMMARY)

    json_payload = {
        "status": "COMPLETE",
        "questions": {
            "is_rail_available_today": is_rail_available_today,
            "can_rail_be_backfilled_historically": "YES" if can_backfill else "NO",
            "earliest_available_date": earliest_rail_date,
            "coverage_percentage_achievable": summary_metrics["coverage_percentage_achievable"],
            "best_source": best_source,
            "estimated_rail_coverage_across_13576_races": {
                "races_with_rail": rail_races,
                "total_races": total_races,
                "coverage_pct": summary_metrics["estimated_rail_coverage_pct"],
            },
            "verdict": verdict,
        },
        "evidence": {
            "local_sources": local_rows,
            "html_page_samples": page_rows,
            "graphql_config": {"endpoint": config.endpoint, "api_key_present": True},
            "current_day": current_row,
            "historical_match_summary": {
                "matched_meetings": matched_meetings,
                "total_meetings": total_meetings,
                "matched_races": matched_races,
                "total_races": total_races,
                "rail_races": rail_races,
                "rail_meetings": rail_meetings,
                "alias_recoverable_meetings": alias_recoverable_meetings,
                "alias_recoverable_races": alias_recoverable_races,
                "potential_rail_coverage_pct_after_alias": summary_metrics["potential_rail_coverage_pct_after_alias"],
            },
        },
    }
    write_json(json_payload, OUT_JSON)

    print("[RAIL_DATA_DISCOVERY_AUDIT_V1] COMPLETE")
    print(f"historical_universe_races={total_races}")
    print(f"historical_universe_meetings={total_meetings}")
    print(f"matched_meetings={matched_meetings}")
    print(f"matched_races={matched_races}")
    print(f"rail_coverage_races={rail_races}")
    print(f"rail_coverage_pct={summary_metrics['estimated_rail_coverage_pct']}")
    print(f"is_rail_available_today={is_rail_available_today}")
    print(f"best_source={best_source}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT_AUDIT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_JSON}")


if __name__ == "__main__":
    main()
