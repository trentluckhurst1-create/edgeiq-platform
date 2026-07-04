from pathlib import Path
from functools import lru_cache
import re

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"

SECTIONAL_MASTER = DATA / "edgeiq_sectional_master_v1.csv"
OFFICIAL_RUNS_MASTER = DATA / "edgeiq_official_runs_master_v1.csv"
LIVE_BOARD = DATA / "edgeiq_execution_board_live.csv"
RACE_FIELDS = DATA / "race_fields.csv"
VIC_SPEED_DIAGNOSTICS = DATA / "edgeiq_vic_racingcom_speed_data_diagnostics_v1.csv"
RACINGCOM_GRAPHQL = DATA / "edgeiq_racingcom_graphql_parser_v1.csv"
RACINGCOM_GRAPHQL_DIAGNOSTICS = DATA / "edgeiq_racingcom_graphql_diagnostics_v1.csv"
RACINGCOM_CSV = DATA / "edgeiq_racingcom_csv_ingestion_v1.csv"
RACINGCOM_CSV_DIAGNOSTICS = DATA / "edgeiq_racingcom_csv_ingestion_diagnostics_v1.csv"

AUDIT_OUT = DATA / "edgeiq_sectional_match_quality_audit_v1.csv"
REASON_OUT = DATA / "edgeiq_sectional_match_quality_by_reason_v1.csv"
ACTIONS_OUT = DATA / "edgeiq_sectional_match_quality_actions_v1.csv"

AUDIT_COLUMNS = [
    "horse",
    "horse_key",
    "track",
    "race_date",
    "race_no",
    "state",
    "matched_to_official_runs_master",
    "matched_to_sectional_master",
    "sectionals_available_by_horse_only",
    "sectionals_available_by_track_date",
    "sectionals_available_by_track_alias",
    "sectionals_available_by_date_nearby",
    "sectionals_available_by_race_no",
    "likely_failure_reason",
    "matched_sectional_source_file",
    "track_alias_candidate",
    "nearest_sectional_date",
]

REASON_COLUMNS = [
    "likely_failure_reason",
    "live_runner_count",
    "pct_live_runners",
    "recommended_action",
]

ACTIONS_COLUMNS = [
    "action_type",
    "priority",
    "metric",
    "value",
    "reason",
    "recommended_action",
]


def log(message: str) -> None:
    print(f"[sectional_match_quality_v1] {message}")


def clean(value) -> str:
    return str(value or "").strip()


def has_value(value) -> bool:
    text = clean(value)
    return bool(text) and text.upper() not in {"NAN", "NONE", "NULL", "UNKNOWN", "N/A", "NA", "-"}


@lru_cache(maxsize=50000)
def norm(value) -> str:
    text = re.sub(r"\([^)]*\)", "", clean(value).upper())
    return re.sub(r"[^A-Z0-9]+", "", text)


@lru_cache(maxsize=10000)
def race_no_key(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing {path.relative_to(PROJECT_ROOT)}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        log(f"read {path.relative_to(PROJECT_ROOT)}: {len(df)} rows")
        return df
    except Exception as exc:
        log(f"warning: failed to read {path}: {exc}")
        return pd.DataFrame()


def first_existing(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row.index and has_value(row.get(name, "")):
            return clean(row.get(name, ""))
    return ""


@lru_cache(maxsize=50000)
def date_key(value) -> str:
    if not has_value(value):
        return ""
    raw = clean(value)
    dayfirst = not bool(re.match(r"^\d{4}-\d{1,2}-\d{1,2}", raw))
    parsed = pd.to_datetime(pd.Series([raw]), errors="coerce", dayfirst=dayfirst).iloc[0]
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def date_value(value):
    key = date_key(value)
    if not key:
        return pd.NaT
    return pd.to_datetime(key, errors="coerce")


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00"
    return f"{(numerator / denominator) * 100:.2f}"


def with_keys(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["_horse_key"] = out.apply(
        lambda row: norm(first_existing(row, ["horse_key", "_horse_key", "horse", "runner", "runner_name"])),
        axis=1,
    )
    out["_track_key"] = out.apply(lambda row: norm(first_existing(row, ["track", "meeting", "venue"])), axis=1)
    out["_date_key"] = out.apply(lambda row: date_key(first_existing(row, ["race_date", "date", "run_date", "meeting_date"])), axis=1)
    out["_race_no_key"] = out.apply(lambda row: race_no_key(first_existing(row, ["race_no", "race_number", "race"])), axis=1)
    out["_state_key"] = out.apply(lambda row: norm(first_existing(row, ["state", "jurisdiction"])), axis=1)
    return out


def key_tuple(row: pd.Series, fields: list[str]) -> tuple[str, ...]:
    return tuple(clean(row.get(field, "")) for field in fields)


def make_set(df: pd.DataFrame, fields: list[str]) -> set[tuple[str, ...]]:
    if df.empty:
        return set()
    return {key_tuple(row, fields) for _, row in df.iterrows() if all(has_value(row.get(field, "")) for field in fields)}


def nearest_date_for_horse(sec: pd.DataFrame, horse_key: str, target_date: str) -> str:
    if sec.empty or not horse_key or not target_date:
        return ""
    candidates = sec[sec["_horse_key"] == horse_key].copy()
    if candidates.empty:
        return ""
    target = pd.to_datetime(target_date, errors="coerce")
    if pd.isna(target):
        return ""
    candidates["_dt"] = pd.to_datetime(candidates["_date_key"], errors="coerce")
    candidates = candidates.dropna(subset=["_dt"])
    if candidates.empty:
        return ""
    candidates["_gap"] = (candidates["_dt"] - target).abs()
    return clean(candidates.sort_values("_gap").iloc[0].get("_date_key", ""))


def live_rows(live: pd.DataFrame, race_fields: pd.DataFrame) -> pd.DataFrame:
    if not live.empty:
        return live
    return race_fields


def reason_to_action(reason: str) -> str:
    mapping = {
        "NO_SECTIONAL_HISTORY_FOR_HORSE": "EXPAND_SECTIONAL_SOURCE_COVERAGE",
        "HORSE_KEY_MISMATCH": "IMPROVE_HORSE_KEY",
        "TRACK_ALIAS_MISMATCH": "ADD_TRACK_ALIAS",
        "DATE_MISMATCH": "NORMALISE_DATES",
        "RACE_NO_MISMATCH": "NORMALISE_RACE_NO",
        "STATE_COVERAGE_GAP": "EXPAND_SECTIONAL_SOURCE_COVERAGE",
        "SECTIONAL_SOURCE_TOO_RECENT_OR_TOO_OLD": "FETCH_MORE_Qld_ZIPS",
        "LIVE_RUNNER_HAS_NO_OFFICIAL_HISTORY": "EXPAND_SECTIONAL_SOURCE_COVERAGE",
        "UNKNOWN": "EXPAND_SECTIONAL_SOURCE_COVERAGE",
    }
    return mapping.get(reason, "EXPAND_SECTIONAL_SOURCE_COVERAGE")


def audit_live(live: pd.DataFrame, official: pd.DataFrame, sectional: pd.DataFrame) -> pd.DataFrame:
    if live.empty:
        return pd.DataFrame(columns=AUDIT_COLUMNS)

    official_sets = {
        "exact": make_set(official, ["_horse_key", "_date_key", "_track_key", "_race_no_key"]),
        "horse": make_set(official, ["_horse_key"]),
    }
    sectional_sets = {
        "exact": make_set(sectional, ["_horse_key", "_date_key", "_track_key", "_race_no_key"]),
        "horse": make_set(sectional, ["_horse_key"]),
        "track_date": make_set(sectional, ["_track_key", "_date_key"]),
        "date_race": make_set(sectional, ["_date_key", "_race_no_key"]),
        "horse_date": make_set(sectional, ["_horse_key", "_date_key"]),
        "horse_date_race": make_set(sectional, ["_horse_key", "_date_key", "_race_no_key"]),
        "horse_track_race": make_set(sectional, ["_horse_key", "_track_key", "_race_no_key"]),
    }
    sectional_states = {clean(v) for v in sectional.get("_state_key", pd.Series(dtype=str)).tolist() if has_value(v)}
    sectional_min_date = pd.to_datetime(sectional.get("_date_key", pd.Series(dtype=str)), errors="coerce").min()
    sectional_max_date = pd.to_datetime(sectional.get("_date_key", pd.Series(dtype=str)), errors="coerce").max()

    rows = []
    for _, row in live.iterrows():
        horse = first_existing(row, ["horse", "runner", "runner_name", "selection"])
        horse_key = norm(first_existing(row, ["horse_key", "_horse_key"]) or horse)
        track = first_existing(row, ["track", "meeting", "venue"])
        track_key = norm(track)
        raw_date = first_existing(row, ["race_date", "date", "run_date", "meeting_date"])
        dkey = date_key(raw_date)
        rno = race_no_key(first_existing(row, ["race_no", "race_number", "race"]))
        state = first_existing(row, ["state", "jurisdiction"])
        state_key = norm(state)

        exact_key = (horse_key, dkey, track_key, rno)
        matched_official = exact_key in official_sets["exact"]
        matched_sectional = exact_key in sectional_sets["exact"]
        by_horse = (horse_key,) in sectional_sets["horse"]
        by_track_date = (track_key, dkey) in sectional_sets["track_date"]
        by_track_alias = (horse_key, dkey, rno) in sectional_sets["horse_date_race"] and not matched_sectional
        by_date_nearby = False
        by_race_no = (dkey, rno) in sectional_sets["date_race"]
        nearest = nearest_date_for_horse(sectional, horse_key, dkey)
        if nearest and dkey:
            gap = abs((pd.to_datetime(nearest) - pd.to_datetime(dkey)).days)
            by_date_nearby = 0 < gap <= 14

        source_file = ""
        alias_candidate = ""
        if matched_sectional:
            match = sectional[
                (sectional["_horse_key"] == horse_key)
                & (sectional["_date_key"] == dkey)
                & (sectional["_track_key"] == track_key)
                & (sectional["_race_no_key"] == rno)
            ]
            if not match.empty:
                source_file = clean(match.iloc[0].get("source_file", ""))
        if by_track_alias:
            alias_match = sectional[
                (sectional["_horse_key"] == horse_key)
                & (sectional["_date_key"] == dkey)
                & (sectional["_race_no_key"] == rno)
            ]
            if not alias_match.empty:
                alias_candidate = clean(alias_match.iloc[0].get("track", ""))

        if matched_sectional:
            reason = "MATCHED"
        elif not ((horse_key,) in official_sets["horse"]):
            reason = "LIVE_RUNNER_HAS_NO_OFFICIAL_HISTORY"
        elif not by_horse:
            reason = "NO_SECTIONAL_HISTORY_FOR_HORSE"
        elif by_track_alias:
            reason = "TRACK_ALIAS_MISMATCH"
        elif (horse_key, dkey) not in sectional_sets["horse_date"]:
            live_dt = pd.to_datetime(dkey, errors="coerce")
            if pd.notna(live_dt) and pd.notna(sectional_min_date) and pd.notna(sectional_max_date) and (live_dt < sectional_min_date or live_dt > sectional_max_date):
                reason = "SECTIONAL_SOURCE_TOO_RECENT_OR_TOO_OLD"
            else:
                reason = "DATE_MISMATCH"
        elif (horse_key, track_key, rno) not in sectional_sets["horse_track_race"]:
            reason = "RACE_NO_MISMATCH"
        elif state_key and sectional_states and state_key not in sectional_states:
            reason = "STATE_COVERAGE_GAP"
        elif by_horse:
            reason = "HORSE_KEY_MISMATCH"
        else:
            reason = "UNKNOWN"

        rows.append({
            "horse": horse,
            "horse_key": horse_key,
            "track": track,
            "race_date": dkey or raw_date,
            "race_no": rno,
            "state": state,
            "matched_to_official_runs_master": str(bool(matched_official)).upper(),
            "matched_to_sectional_master": str(bool(matched_sectional)).upper(),
            "sectionals_available_by_horse_only": str(bool(by_horse)).upper(),
            "sectionals_available_by_track_date": str(bool(by_track_date)).upper(),
            "sectionals_available_by_track_alias": str(bool(by_track_alias)).upper(),
            "sectionals_available_by_date_nearby": str(bool(by_date_nearby)).upper(),
            "sectionals_available_by_race_no": str(bool(by_race_no)).upper(),
            "likely_failure_reason": reason,
            "matched_sectional_source_file": source_file,
            "track_alias_candidate": alias_candidate,
            "nearest_sectional_date": nearest,
        })

    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def global_metrics(official: pd.DataFrame, sectional: pd.DataFrame) -> dict[str, str]:
    official_exact = make_set(official, ["_horse_key", "_date_key", "_track_key", "_race_no_key"])
    official_hdt = make_set(official, ["_horse_key", "_date_key", "_track_key"])
    official_hd = make_set(official, ["_horse_key", "_date_key"])
    official_horse = make_set(official, ["_horse_key"])
    official_tdr = make_set(official, ["_track_key", "_date_key", "_race_no_key"])

    sectional_exact = make_set(sectional, ["_horse_key", "_date_key", "_track_key", "_race_no_key"])
    sectional_hdt = make_set(sectional, ["_horse_key", "_date_key", "_track_key"])
    sectional_hd = make_set(sectional, ["_horse_key", "_date_key"])
    sectional_horse = make_set(sectional, ["_horse_key"])
    sectional_tdr = make_set(sectional, ["_track_key", "_date_key", "_race_no_key"])

    exact = len(official_exact & sectional_exact)
    hdt = len(official_hdt & sectional_hdt)
    hd = len(official_hd & sectional_hd)
    horse_only = len(official_horse & sectional_horse)
    tdr = len(official_tdr & sectional_tdr)
    unmatched_sec = len(sectional_exact - official_exact)
    unmatched_off = len(official_exact - sectional_exact)

    official_dates = pd.to_datetime(official.get("_date_key", pd.Series(dtype=str)), errors="coerce").dropna()
    sectional_dates = pd.to_datetime(sectional.get("_date_key", pd.Series(dtype=str)), errors="coerce").dropna()
    if official_dates.empty or sectional_dates.empty:
        overlap = "NO_DATE_OVERLAP"
    else:
        start = max(official_dates.min(), sectional_dates.min())
        end = min(official_dates.max(), sectional_dates.max())
        overlap = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}" if start <= end else "NO_DATE_OVERLAP"

    state_values = sorted({v for v in sectional.get("_state_key", pd.Series(dtype=str)).tolist() if has_value(v)})
    vic_rows = int((sectional.get("_state_key", pd.Series(dtype=str)).astype(str) == "VIC").sum()) if "_state_key" in sectional.columns else 0
    alias_candidates = find_track_alias_candidates(official, sectional)

    return {
        "official_rows": str(len(official)),
        "sectional_rows": str(len(sectional)),
        "exact_match_count": str(exact),
        "exact_match_pct": pct(exact, len(official_exact)),
        "horse_date_track_match_count": str(hdt),
        "horse_date_match_count": str(hd),
        "horse_only_match_count": str(horse_only),
        "horse_only_match_pct": pct(horse_only, len(official_horse)),
        "track_date_race_match_count": str(tdr),
        "track_date_race_match_pct": pct(tdr, len(official_tdr)),
        "unmatched_sectional_rows": str(unmatched_sec),
        "unmatched_official_rows": str(unmatched_off),
        "date_range_overlap": overlap,
        "state_coverage": ", ".join(state_values[:12]),
        "vic_sectional_rows": str(vic_rows),
        "track_alias_candidates": alias_candidates,
    }


def find_track_alias_candidates(official: pd.DataFrame, sectional: pd.DataFrame) -> str:
    if official.empty or sectional.empty:
        return ""
    off = official[["_horse_key", "_date_key", "_race_no_key", "track"]].drop_duplicates()
    sec = sectional[["_horse_key", "_date_key", "_race_no_key", "track"]].drop_duplicates()
    merged = off.merge(sec, on=["_horse_key", "_date_key", "_race_no_key"], how="inner", suffixes=("_official", "_sectional"))
    if merged.empty:
        return ""
    merged["_official_key"] = merged["track_official"].map(norm)
    merged["_sectional_key"] = merged["track_sectional"].map(norm)
    mismatches = merged[merged["_official_key"] != merged["_sectional_key"]]
    if mismatches.empty:
        return ""
    counts = (
        mismatches.groupby(["track_official", "track_sectional"])
        .size()
        .sort_values(ascending=False)
        .head(5)
    )
    return " | ".join([f"{a} -> {b} ({count})" for (a, b), count in counts.items()])


def build_reason_summary(audit: pd.DataFrame) -> pd.DataFrame:
    if audit.empty:
        return pd.DataFrame(columns=REASON_COLUMNS)
    counts = audit["likely_failure_reason"].value_counts().reset_index()
    counts.columns = ["likely_failure_reason", "live_runner_count"]
    counts["pct_live_runners"] = counts["live_runner_count"].map(lambda value: pct(int(value), len(audit)))
    counts["recommended_action"] = counts["likely_failure_reason"].map(reason_to_action)
    return counts[REASON_COLUMNS]


def build_actions(metrics: dict[str, str], audit: pd.DataFrame, reasons: pd.DataFrame) -> pd.DataFrame:
    vic_live = audit[audit["state"].astype(str).str.upper().str.contains("VIC", na=False)] if not audit.empty else audit
    vic_live_matched = int((vic_live["matched_to_sectional_master"] == "TRUE").sum()) if not vic_live.empty else 0
    vic_live_coverage = pct(vic_live_matched, len(vic_live))
    racingcom_csv_live_matched = int(
        audit["matched_sectional_source_file"].astype(str).str.contains("racingcom_csv", case=False, na=False).sum()
    ) if not audit.empty and "matched_sectional_source_file" in audit.columns else 0
    racingcom_csv_live_coverage = pct(racingcom_csv_live_matched, len(audit))
    racingcom_dynamic_failures = "0"
    if VIC_SPEED_DIAGNOSTICS.exists():
        diag = read_csv(VIC_SPEED_DIAGNOSTICS)
        match = diag[diag.get("metric", pd.Series(dtype=str)).astype(str) == "dynamic_failures"] if not diag.empty else pd.DataFrame()
        if not match.empty:
            racingcom_dynamic_failures = clean(match.iloc[0].get("value", "0"))
    racingcom_graphql_rows = "0"
    racingcom_graphql_has_sectionals_count = "0"
    racingcom_graphql_speed_value_count = "0"
    racingcom_csv_rows = "0"
    racingcom_csv_last200_coverage = "0.00"
    racingcom_csv_last400_coverage = "0.00"
    racingcom_csv_last600_coverage = "0.00"
    if RACINGCOM_CSV.exists():
        csv_rows = read_csv(RACINGCOM_CSV)
        racingcom_csv_rows = str(len(csv_rows))
        if not csv_rows.empty:
            racingcom_csv_last200_coverage = pct(int(csv_rows.get("last200", pd.Series(dtype=str)).map(has_value).sum()), len(csv_rows))
            racingcom_csv_last400_coverage = pct(int(csv_rows.get("last400", pd.Series(dtype=str)).map(has_value).sum()), len(csv_rows))
            racingcom_csv_last600_coverage = pct(int(csv_rows.get("last600", pd.Series(dtype=str)).map(has_value).sum()), len(csv_rows))
    if RACINGCOM_CSV_DIAGNOSTICS.exists():
        csv_diag = read_csv(RACINGCOM_CSV_DIAGNOSTICS)
        if not csv_diag.empty and "metric" in csv_diag.columns:
            for metric, target in [
                ("rows_parsed", "racingcom_csv_rows"),
                ("last200_coverage_pct", "racingcom_csv_last200_coverage"),
                ("last400_coverage_pct", "racingcom_csv_last400_coverage"),
                ("last600_coverage_pct", "racingcom_csv_last600_coverage"),
            ]:
                match = csv_diag[csv_diag["metric"].astype(str) == metric]
                if match.empty:
                    continue
                value = clean(match.iloc[0].get("value", ""))
                if target == "racingcom_csv_rows":
                    racingcom_csv_rows = value
                elif target == "racingcom_csv_last200_coverage":
                    racingcom_csv_last200_coverage = value
                elif target == "racingcom_csv_last400_coverage":
                    racingcom_csv_last400_coverage = value
                elif target == "racingcom_csv_last600_coverage":
                    racingcom_csv_last600_coverage = value
    if RACINGCOM_GRAPHQL.exists():
        gql = read_csv(RACINGCOM_GRAPHQL)
        racingcom_graphql_rows = str(len(gql))
        if not gql.empty:
            if "has_sectionals" in gql.columns:
                racingcom_graphql_has_sectionals_count = str(int(gql["has_sectionals"].astype(str).str.upper().isin(["1", "TRUE", "YES"]).sum()))
            if "speed_value" in gql.columns:
                racingcom_graphql_speed_value_count = str(int(gql["speed_value"].astype(str).map(has_value).sum()))
    if RACINGCOM_GRAPHQL_DIAGNOSTICS.exists():
        gql_diag = read_csv(RACINGCOM_GRAPHQL_DIAGNOSTICS)
        if not gql_diag.empty and "metric" in gql_diag.columns:
            for metric, target in [
                ("rows_parsed", "racingcom_graphql_rows"),
                ("has_sectionals_count", "racingcom_graphql_has_sectionals_count"),
                ("speed_value_count", "racingcom_graphql_speed_value_count"),
            ]:
                match = gql_diag[gql_diag["metric"].astype(str) == metric]
                if match.empty:
                    continue
                value = clean(match.iloc[0].get("value", ""))
                if target == "racingcom_graphql_rows":
                    racingcom_graphql_rows = value
                elif target == "racingcom_graphql_has_sectionals_count":
                    racingcom_graphql_has_sectionals_count = value
                elif target == "racingcom_graphql_speed_value_count":
                    racingcom_graphql_speed_value_count = value

    rows = [
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "exact_match_pct",
            "value": metrics.get("exact_match_pct", "0.00"),
            "reason": f"{metrics.get('exact_match_count', '0')} official rows matched sectional rows exactly",
            "recommended_action": "MEASURE_BASELINE",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "horse_only_match_pct",
            "value": metrics.get("horse_only_match_pct", "0.00"),
            "reason": f"{metrics.get('horse_only_match_count', '0')} official horse keys have some sectional history",
            "recommended_action": "MEASURE_HORSE_KEY_OVERLAP",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "live_sectional_coverage_pct",
            "value": pct(int((audit["matched_to_sectional_master"] == "TRUE").sum()) if not audit.empty else 0, len(audit)),
            "reason": f"{int((audit['matched_to_sectional_master'] == 'TRUE').sum()) if not audit.empty else 0} live runners matched Sectional Master",
            "recommended_action": "TRACK_LIVE_COVERAGE",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "track_alias_candidates",
            "value": metrics.get("track_alias_candidates", ""),
            "reason": "Most common official/sectional track-name mismatches",
            "recommended_action": "ADD_TRACK_ALIAS",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "vic_sectional_rows",
            "value": metrics.get("vic_sectional_rows", "0"),
            "reason": "VIC rows currently present in Sectional Master",
            "recommended_action": "ADD_VIC_DYNAMIC_SPEED_DATA",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "vic_live_sectional_coverage",
            "value": vic_live_coverage,
            "reason": f"{vic_live_matched} VIC live runners matched Sectional Master",
            "recommended_action": "TRACK_VIC_LIVE_COVERAGE",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_dynamic_failures",
            "value": racingcom_dynamic_failures,
            "reason": "Racing.com pages fetched where speed data was not present in static HTML",
            "recommended_action": "ADD_VIC_DYNAMIC_SPEED_DATA",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_csv_rows",
            "value": racingcom_csv_rows,
            "reason": "Runner split rows parsed from Racing.com direct CSV downloads",
            "recommended_action": "USE_RACINGCOM_DIRECT_CSV_SECTIONALS",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_csv_live_coverage",
            "value": racingcom_csv_live_coverage,
            "reason": f"{racingcom_csv_live_matched} live runners matched Racing.com direct CSV rows",
            "recommended_action": "TRACK_RACINGCOM_CSV_LIVE_COVERAGE",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_csv_last200_coverage",
            "value": racingcom_csv_last200_coverage,
            "reason": "Racing.com direct CSV rows with final 200m split",
            "recommended_action": "TRACK_RACINGCOM_CSV_SPLIT_COVERAGE",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_csv_last400_coverage",
            "value": racingcom_csv_last400_coverage,
            "reason": "Racing.com direct CSV rows with final 400m aggregate",
            "recommended_action": "TRACK_RACINGCOM_CSV_SPLIT_COVERAGE",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_csv_last600_coverage",
            "value": racingcom_csv_last600_coverage,
            "reason": "Racing.com direct CSV rows with final 600m aggregate",
            "recommended_action": "TRACK_RACINGCOM_CSV_SPLIT_COVERAGE",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_graphql_rows",
            "value": racingcom_graphql_rows,
            "reason": "Runner metadata rows parsed from Racing.com GraphQL responses",
            "recommended_action": "TRACK_RACINGCOM_GRAPHQL_METADATA",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_graphql_has_sectionals_count",
            "value": racingcom_graphql_has_sectionals_count,
            "reason": "Racing.com GraphQL rows where race metadata says hasSectionals",
            "recommended_action": "TARGET_RUNNER_LEVEL_SECTIONALS",
        },
        {
            "action_type": "METRIC",
            "priority": "INFO",
            "metric": "racingcom_graphql_speed_value_count",
            "value": racingcom_graphql_speed_value_count,
            "reason": "Racing.com GraphQL rows with runner speedValue metadata",
            "recommended_action": "USE_AS_VIC_SPEED_METADATA",
        },
    ]

    if not reasons.empty:
        top = reasons.iloc[0]
        rows.append({
            "action_type": reason_to_action(clean(top["likely_failure_reason"])),
            "priority": "P1",
            "metric": "top_failure_reason",
            "value": clean(top["likely_failure_reason"]),
            "reason": f"{clean(top['live_runner_count'])} live runners: {clean(top['pct_live_runners'])}%",
            "recommended_action": clean(top["recommended_action"]),
        })

    exact_pct = float(metrics.get("exact_match_pct", "0") or 0)
    horse_pct = float(metrics.get("horse_only_match_pct", "0") or 0)
    if exact_pct < 5 and horse_pct > exact_pct:
        rows.append({
            "action_type": "IMPROVE_HORSE_KEY",
            "priority": "P1",
            "metric": "low_exact_high_horse_overlap",
            "value": f"exact={exact_pct:.2f}; horse={horse_pct:.2f}",
            "reason": "Horse-level overlap is materially better than exact race matching, so date/track/race normalisation is the next leverage point.",
            "recommended_action": "NORMALISE_DATES_AND_TRACK_ALIASES",
        })

    state_coverage = metrics.get("state_coverage", "")
    if "VIC" not in state_coverage:
        rows.append({
            "action_type": "ADD_VIC_DYNAMIC_SPEED_DATA",
            "priority": "P1",
            "metric": "state_coverage_gap",
            "value": state_coverage,
            "reason": "Current sectional state coverage does not include VIC rows in the unified master.",
            "recommended_action": "ADD_VIC_DYNAMIC_SPEED_DATA",
        })
    if "QLD" in state_coverage:
        rows.append({
            "action_type": "FETCH_MORE_Qld_ZIPS",
            "priority": "P2",
            "metric": "qld_source_strength",
            "value": "QLD present",
            "reason": "Racing Queensland exposes CSV/ZIP sources and is currently the strongest public sectional feed.",
            "recommended_action": "FETCH_MORE_Qld_ZIPS",
        })
    rows.append({
        "action_type": "ADD_WA_BACKOFF_FOR_429",
        "priority": "P3",
        "metric": "wa_fetch_status",
        "value": "HTTP_429_OBSERVED",
        "reason": "WA source can rate-limit direct fetches; keep respectful backoff before retrying.",
        "recommended_action": "ADD_WA_BACKOFF_FOR_429",
    })

    return pd.DataFrame(rows, columns=ACTIONS_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)

    sectional = with_keys(read_csv(SECTIONAL_MASTER))
    official = with_keys(read_csv(OFFICIAL_RUNS_MASTER))
    live = with_keys(live_rows(read_csv(LIVE_BOARD), read_csv(RACE_FIELDS)))

    audit = audit_live(live, official, sectional)
    reasons = build_reason_summary(audit)
    metrics = global_metrics(official, sectional)
    actions = build_actions(metrics, audit, reasons)

    audit.to_csv(AUDIT_OUT, index=False, encoding="utf-8")
    reasons.to_csv(REASON_OUT, index=False, encoding="utf-8")
    actions.to_csv(ACTIONS_OUT, index=False, encoding="utf-8")

    log(f"live runners audited: {len(audit)}")
    log(f"exact match pct: {metrics.get('exact_match_pct', '0.00')}%")
    log(f"horse-only match pct: {metrics.get('horse_only_match_pct', '0.00')}%")
    log(f"live runner sectional coverage: {actions.loc[actions['metric'] == 'live_sectional_coverage_pct', 'value'].iloc[0] if not actions.empty else '0.00'}%")
    top_reason = reasons.iloc[0]["likely_failure_reason"] if not reasons.empty else "UNKNOWN"
    top_action = actions[actions["metric"] == "top_failure_reason"]["recommended_action"].iloc[0] if (actions["metric"] == "top_failure_reason").any() else "EXPAND_SECTIONAL_SOURCE_COVERAGE"
    log(f"top failure reason: {top_reason}")
    log(f"top recommended action: {top_action}")
    log(f"wrote {AUDIT_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {REASON_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {ACTIONS_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
