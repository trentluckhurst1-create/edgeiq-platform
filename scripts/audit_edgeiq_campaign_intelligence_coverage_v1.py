import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
CAMPAIGN_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1.csv"

OUT_AUDIT = DATA / "edgeiq_campaign_intelligence_coverage_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_campaign_intelligence_coverage_audit_v1_summary.csv"

NOW_UTC = datetime.now(timezone.utc).isoformat()

EXPLICIT_SOURCES = [
    "edgeiq_runner_history_detail_v1.csv",
    "runner_form_history.csv",
    "edgeiq_runner_form_engine_current.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_horse_career_intelligence_v1.csv",
    "edgeiq_horse_trajectory_engine_v1.csv",
    "edgeiq_racingcom_results_warehouse_full_v1.csv",
    "edgeiq_results_warehouse_full_v1.csv",
    "edgeiq_historical_performance_rating_v6_research.csv",
    "edgeiq_historical_performance_rating_v6_1_research.csv",
    "edgeiq_historical_run_ratings_master_v1.csv",
    "historical_form_table.csv",
    "edgeiq_trainer_jockey_runner_history_v1.csv",
    "edgeiq_trainer_jockey_runner_history_canonical_v1.csv",
]

CURRENT_ENGINE_SOURCE_NAMES = {
    "edgeiq_runner_history_detail_v1.csv",
    "runner_form_history.csv",
}

FILE_DISCOVERY_TOKENS = ("history", "historical", "result", "results", "performance", "rating")
AUTO_INCLUDE_PATTERNS = (
    "results_warehouse",
    "historical_run_ratings",
    "historical_performance",
    "historical_form_table",
    "runner_history",
    "runner_form_history",
    "career_intelligence",
    "trajectory_engine",
    "trainer_jockey_runner_history",
)
AUTO_EXCLUDE_PATTERNS = (
    "_summary",
    "_audit",
    "_diagnostic",
    "_diagnostics",
    "_report",
    "_review",
    "_queue",
    "_manifest",
    "_backup",
    "checkpoint",
    "_working_",
    "_broken_",
    "graphql_",
)

HORSE_COLUMNS = [
    "horse_key",
    "horsekey",
    "runner_key",
    "runnerkey",
    "horse",
    "horse_name",
    "horsename",
    "runner",
    "runner_name",
    "runnername",
]

DATE_COLUMNS = [
    "run_date_iso",
    "race_date",
    "meeting_date",
    "run_date",
    "date",
]

RATING_COLUMNS = [
    "performance_rating_v6_1_research",
    "performance_rating_v6_research",
    "performance_rating",
    "run_rating_final",
    "run_rating",
    "race_rating",
    "rating",
    "projected_rating",
    "latest_rating",
    "peak_rating",
    "last_start_rating",
]


def normalize_strict(value):
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def normalize_loose(value):
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def pick_first_value(row, keys):
    for key in keys:
        value = row.get(key, "")
        if pd.notna(value) and str(value).strip() != "":
            return value
    return ""


def normalize_column_map(columns):
    return {str(column).strip().lower(): str(column) for column in columns}


def resolve_columns(columns, candidates):
    column_map = normalize_column_map(columns)
    return [column_map[candidate] for candidate in candidates if candidate in column_map]


def resolve_first_column(columns, candidates):
    matches = resolve_columns(columns, candidates)
    return matches[0] if matches else None


def fast_csv_row_count(path):
    try:
        with path.open("rb") as handle:
            line_count = 0
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                line_count += chunk.count(b"\n")
        return max(line_count - 1, 0)
    except Exception:
        return math.nan


def read_header(path):
    try:
        frame = pd.read_csv(path, nrows=0, low_memory=False)
        return [str(column) for column in frame.columns]
    except Exception:
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                return next(reader)
        except Exception:
            return []


def parse_dates(series):
    return pd.to_datetime(series, errors="coerce")


def select_rating_mask(chunk, rating_cols):
    if not rating_cols:
        return pd.Series([False] * len(chunk), index=chunk.index)
    numeric_frame = chunk[rating_cols].apply(pd.to_numeric, errors="coerce")
    return numeric_frame.notna().any(axis=1)


def fuzzy_safe_candidate(target_key, source_keys):
    if not target_key or not source_keys:
        return ("", 0.0)

    prefix_candidates = [
        candidate
        for candidate in source_keys
        if candidate
        and abs(len(candidate) - len(target_key)) <= 2
        and candidate[: min(6, len(target_key))] == target_key[: min(6, len(target_key))]
    ]

    if not prefix_candidates:
        prefix_candidates = [
            candidate
            for candidate in source_keys
            if candidate
            and abs(len(candidate) - len(target_key)) <= 2
            and candidate[: min(4, len(target_key))] == target_key[: min(4, len(target_key))]
        ]

    if not prefix_candidates:
        return ("", 0.0)

    scored = sorted(
        ((candidate, SequenceMatcher(None, target_key, candidate).ratio()) for candidate in prefix_candidates),
        key=lambda item: item[1],
        reverse=True,
    )
    best_candidate, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0
    if best_score >= 0.94 and best_score - second_score >= 0.02:
        return (best_candidate, best_score)
    return ("", 0.0)


def source_priority_score(profile):
    detailed = 1 if profile.get("detailed_profile_status") == "PROFILED" else 0
    strong_matches = int(profile.get("strict_dated_rated_match_current_runners") or 0)
    loose_matches = int(profile.get("loose_dated_rated_match_current_runners") or 0)
    total_matches = int(profile.get("matched_current_runners_by_strict_clean_horse_key") or 0) + int(profile.get("matched_current_runners_by_loose_clean_horse_key") or 0)
    rating_rows = int(profile.get("rating_rows") or 0)
    dated_rows = int(profile.get("dated_rows") or 0)
    engine_bonus = 0 if profile.get("source_name") in CURRENT_ENGINE_SOURCE_NAMES else 1
    return (
        detailed * 1_000_000
        + strong_matches * 10_000
        + loose_matches * 5_000
        + total_matches * 100
        + min(rating_rows, 50_000)
        + min(dated_rows, 50_000) * 0.1
        + engine_bonus
    )


def should_include_source(path):
    lower_name = path.name.lower()
    if path.suffix.lower() != ".csv":
        return False
    if any(pattern in lower_name for pattern in AUTO_EXCLUDE_PATTERNS):
        return False
    if path.name in EXPLICIT_SOURCES:
        return True
    if any(token in lower_name for token in FILE_DISCOVERY_TOKENS) and any(pattern in lower_name for pattern in AUTO_INCLUDE_PATTERNS):
        return True
    return False


def main():
    if not LIVE_PATH.exists():
        raise FileNotFoundError(f"Missing live runner board: {LIVE_PATH}")
    if not CAMPAIGN_PATH.exists():
        raise FileNotFoundError(f"Missing campaign engine output: {CAMPAIGN_PATH}")

    print("[CAMPAIGN_COVERAGE_AUDIT_V1] loading current runner board ...")
    live = pd.read_csv(LIVE_PATH, low_memory=False)
    campaign = pd.read_csv(CAMPAIGN_PATH, low_memory=False)

    scratched_mask = pd.Series([False] * len(live), index=live.index)
    if "runner_status" in live.columns:
        scratched_mask = scratched_mask | live["runner_status"].fillna("").astype(str).str.upper().eq("SCRATCHED")
    if "is_scratched" in live.columns:
        scratched_mask = scratched_mask | live["is_scratched"].fillna("").astype(str).str.upper().isin({"TRUE", "1", "YES"})

    active_live = live[~scratched_mask].copy()
    active_live["current_runner_id"] = active_live.apply(
        lambda row: "|".join(
            [
                str(row.get("race_date", "")).strip(),
                str(row.get("track", "")).strip(),
                str(row.get("race_no", "")).strip(),
                str(row.get("horse", "")).strip(),
            ]
        ),
        axis=1,
    )
    active_live["strict_key"] = active_live.apply(
        lambda row: normalize_strict(row.get("horse_key", "")) or normalize_strict(row.get("horse", "")),
        axis=1,
    )
    active_live["loose_key"] = active_live["horse"].map(normalize_loose)

    active_runner_ids = active_live["current_runner_id"].tolist()
    active_strict_to_ids = defaultdict(set)
    active_loose_to_ids = defaultdict(set)
    for _, row in active_live.iterrows():
        if row["strict_key"]:
            active_strict_to_ids[row["strict_key"]].add(row["current_runner_id"])
        if row["loose_key"]:
            active_loose_to_ids[row["loose_key"]].add(row["current_runner_id"])

    campaign["current_runner_id"] = campaign.apply(
        lambda row: "|".join(
            [
                str(row.get("current_race_date", "")).strip(),
                str(row.get("track", "")).strip(),
                str(row.get("race_no", "")).strip(),
                str(row.get("horse", "")).strip(),
            ]
        ),
        axis=1,
    )
    campaign_no_history_ids = set(
        campaign[campaign["evidence_status"].fillna("").astype(str).str.upper().eq("NO_HISTORY")]["current_runner_id"].tolist()
    )

    discovered_files = sorted(
        {
            *(path.name for path in DATA.iterdir() if path.is_file() and should_include_source(path)),
            *EXPLICIT_SOURCES,
        }
    )

    source_profiles = []
    audit_rows = []
    per_source_runner_map = {}

    print("[CAMPAIGN_COVERAGE_AUDIT_V1] auditing source inventory and candidate coverage ...")
    for source_name in discovered_files:
        source_path = DATA / source_name
        exists = source_path.exists()
        row_count = fast_csv_row_count(source_path) if exists else 0
        columns = read_header(source_path) if exists else []

        horse_key_col = resolve_first_column(columns, ["horse_key", "horsekey", "runner_key", "runnerkey", "horsekey"])
        horse_text_col = resolve_first_column(columns, ["horse", "horse_name", "horsename", "runner", "runner_name", "runnername", "horseName", "horseName".lower()])
        date_col = resolve_first_column(columns, DATE_COLUMNS)
        rating_cols = resolve_columns(columns, RATING_COLUMNS)

        profile = {
            "record_type": "source_profile",
            "source_name": source_name,
            "source_exists": "YES" if exists else "NO",
            "rows": row_count,
            "unique_horses": "",
            "dated_rows": "",
            "rating_rows": "",
            "matched_current_runners_by_strict_clean_horse_key": "",
            "matched_current_runners_by_loose_clean_horse_key": "",
            "matched_current_runners_by_fuzzy_safe_fallback": "",
            "strict_dated_match_current_runners": "",
            "strict_rated_match_current_runners": "",
            "strict_dated_rated_match_current_runners": "",
            "loose_dated_match_current_runners": "",
            "loose_rated_match_current_runners": "",
            "loose_dated_rated_match_current_runners": "",
            "horse_key_column_detected": horse_key_col or "",
            "horse_column_detected": horse_text_col or "",
            "date_column_detected": date_col or "",
            "rating_column_detected": "; ".join(rating_cols),
            "date_parse_failure_rows": "",
            "column_inventory": " | ".join(columns),
            "detailed_profile_status": "",
            "notes": "",
        }

        # Always emit column inventory information.
        audit_rows.append(
            {
                "record_type": "source_column_inventory",
                "source_name": source_name,
                "source_exists": "YES" if exists else "NO",
                "horse_key_column_detected": horse_key_col or "",
                "horse_column_detected": horse_text_col or "",
                "date_column_detected": date_col or "",
                "rating_column_detected": "; ".join(rating_cols),
                "column_inventory": " | ".join(columns),
                "notes": "Explicit source" if source_name in EXPLICIT_SOURCES else "Auto-discovered matching filename",
            }
        )

        if not exists:
            profile["detailed_profile_status"] = "MISSING"
            profile["notes"] = "Source file not found."
            source_profiles.append(profile)
            per_source_runner_map[source_name] = {}
            continue

        if not horse_key_col and not horse_text_col:
            profile["detailed_profile_status"] = "HEADER_ONLY"
            profile["notes"] = "No horse-like column detected; source not suitable for runner-level campaign coverage."
            source_profiles.append(profile)
            per_source_runner_map[source_name] = {}
            continue

        # Detailed candidate profile.
        usecols = [column for column in [horse_key_col, horse_text_col, date_col, *rating_cols] if column]
        strict_any_ids = set()
        loose_any_ids = set()
        strict_dated_ids = set()
        loose_dated_ids = set()
        strict_rated_ids = set()
        loose_rated_ids = set()
        strict_dated_rated_ids = set()
        loose_dated_rated_ids = set()
        strict_keys_seen = set()
        loose_keys_seen = set()
        unique_horse_tokens = set()
        dated_rows = 0
        rating_rows = 0
        parse_fail_rows = 0
        source_loose_keys = set()

        try:
            for chunk in pd.read_csv(source_path, usecols=usecols, chunksize=100000, low_memory=False):
                if horse_key_col:
                    strict_series = chunk[horse_key_col].map(normalize_strict)
                else:
                    strict_series = chunk[horse_text_col].map(normalize_strict) if horse_text_col else pd.Series([""] * len(chunk), index=chunk.index)

                if horse_text_col:
                    loose_series = chunk[horse_text_col].map(normalize_loose)
                elif horse_key_col:
                    loose_series = chunk[horse_key_col].map(normalize_loose)
                else:
                    loose_series = pd.Series([""] * len(chunk), index=chunk.index)

                unique_horse_tokens.update({value for value in strict_series if value})
                unique_horse_tokens.update({value for value in loose_series if value})
                strict_keys_seen.update({value for value in strict_series if value})
                loose_keys_seen.update({value for value in loose_series if value})
                source_loose_keys.update({value for value in loose_series if value})

                if date_col:
                    raw_dates = chunk[date_col].fillna("").astype(str).str.strip()
                    parsed_dates = parse_dates(raw_dates)
                    dated_mask = parsed_dates.notna()
                    dated_rows += int(dated_mask.sum())
                    parse_fail_rows += int(((raw_dates != "") & (~dated_mask)).sum())
                else:
                    dated_mask = pd.Series([False] * len(chunk), index=chunk.index)

                rating_mask = select_rating_mask(chunk, rating_cols)
                rating_rows += int(rating_mask.sum())
                dated_rated_mask = dated_mask & rating_mask

                strict_match_mask = strict_series.isin(active_strict_to_ids.keys()) if len(active_strict_to_ids) else pd.Series([False] * len(chunk), index=chunk.index)
                loose_match_mask = loose_series.isin(active_loose_to_ids.keys()) if len(active_loose_to_ids) else pd.Series([False] * len(chunk), index=chunk.index)

                for key in set(strict_series[strict_match_mask].tolist()):
                    strict_any_ids.update(active_strict_to_ids.get(key, set()))
                for key in set(loose_series[loose_match_mask].tolist()):
                    loose_any_ids.update(active_loose_to_ids.get(key, set()))

                for key in set(strict_series[strict_match_mask & dated_mask].tolist()):
                    strict_dated_ids.update(active_strict_to_ids.get(key, set()))
                for key in set(loose_series[loose_match_mask & dated_mask].tolist()):
                    loose_dated_ids.update(active_loose_to_ids.get(key, set()))

                for key in set(strict_series[strict_match_mask & rating_mask].tolist()):
                    strict_rated_ids.update(active_strict_to_ids.get(key, set()))
                for key in set(loose_series[loose_match_mask & rating_mask].tolist()):
                    loose_rated_ids.update(active_loose_to_ids.get(key, set()))

                for key in set(strict_series[strict_match_mask & dated_rated_mask].tolist()):
                    strict_dated_rated_ids.update(active_strict_to_ids.get(key, set()))
                for key in set(loose_series[loose_match_mask & dated_rated_mask].tolist()):
                    loose_dated_rated_ids.update(active_loose_to_ids.get(key, set()))
        except Exception as exc:
            profile["detailed_profile_status"] = "ERROR"
            profile["notes"] = f"Detailed profiling failed: {exc}"
            source_profiles.append(profile)
            per_source_runner_map[source_name] = {}
            continue

        fuzzy_ids = set()
        fuzzy_candidate_map = {}
        unmatched_runner_ids = set(active_runner_ids) - strict_any_ids - loose_any_ids
        runner_lookup = active_live.set_index("current_runner_id").to_dict(orient="index")
        for runner_id in unmatched_runner_ids:
            runner_info = runner_lookup.get(runner_id, {})
            candidate_key, score = fuzzy_safe_candidate(runner_info.get("loose_key", ""), source_loose_keys)
            if candidate_key:
                fuzzy_ids.add(runner_id)
                fuzzy_candidate_map[runner_id] = f"{candidate_key} ({score:.3f})"

        profile.update(
            {
                "unique_horses": len(unique_horse_tokens),
                "dated_rows": dated_rows,
                "rating_rows": rating_rows,
                "matched_current_runners_by_strict_clean_horse_key": len(strict_any_ids),
                "matched_current_runners_by_loose_clean_horse_key": len(loose_any_ids),
                "matched_current_runners_by_fuzzy_safe_fallback": len(fuzzy_ids),
                "strict_dated_match_current_runners": len(strict_dated_ids),
                "strict_rated_match_current_runners": len(strict_rated_ids),
                "strict_dated_rated_match_current_runners": len(strict_dated_rated_ids),
                "loose_dated_match_current_runners": len(loose_dated_ids),
                "loose_rated_match_current_runners": len(loose_rated_ids),
                "loose_dated_rated_match_current_runners": len(loose_dated_rated_ids),
                "date_parse_failure_rows": parse_fail_rows,
                "detailed_profile_status": "PROFILED",
                "notes": "Current engine source" if source_name in CURRENT_ENGINE_SOURCE_NAMES else "Alternative candidate source",
            }
        )
        source_profiles.append(profile)

        per_source_runner_map[source_name] = {
            "strict_any": strict_any_ids,
            "loose_any": loose_any_ids,
            "strict_dated": strict_dated_ids,
            "loose_dated": loose_dated_ids,
            "strict_rated": strict_rated_ids,
            "loose_rated": loose_rated_ids,
            "strict_dated_rated": strict_dated_rated_ids,
            "loose_dated_rated": loose_dated_rated_ids,
            "fuzzy": fuzzy_ids,
            "fuzzy_candidate_map": fuzzy_candidate_map,
            "profile": profile,
        }

    # Build per-runner diagnostics for NO_HISTORY rows.
    current_row_lookup = active_live.set_index("current_runner_id").to_dict(orient="index")
    no_history_reasons = Counter()
    no_history_diagnostics = []
    matched_elsewhere = []

    detailed_source_profiles = [profile for profile in source_profiles if profile.get("detailed_profile_status") == "PROFILED"]

    def best_alt_source_for_runner(runner_id):
        best = None
        best_score = (-1, -1, -1, "")
        for source_name, match_map in per_source_runner_map.items():
            if source_name in CURRENT_ENGINE_SOURCE_NAMES or not match_map:
                continue
            score_tuple = (
                int(runner_id in match_map.get("strict_dated_rated", set())),
                int(runner_id in match_map.get("loose_dated_rated", set())),
                int(runner_id in match_map.get("strict_dated", set()) or runner_id in match_map.get("loose_dated", set())),
                source_name,
            )
            if score_tuple > best_score:
                best_score = score_tuple
                best = source_name
        return best

    for runner_id in campaign_no_history_ids:
        runner_info = current_row_lookup.get(runner_id, {})

        engine_match = False
        engine_dated = False
        engine_rated = False
        engine_fuzzy = False
        for source_name in CURRENT_ENGINE_SOURCE_NAMES:
            match_map = per_source_runner_map.get(source_name, {})
            engine_match = engine_match or runner_id in match_map.get("strict_any", set()) or runner_id in match_map.get("loose_any", set())
            engine_dated = engine_dated or runner_id in match_map.get("strict_dated", set()) or runner_id in match_map.get("loose_dated", set())
            engine_rated = engine_rated or runner_id in match_map.get("strict_rated", set()) or runner_id in match_map.get("loose_rated", set())
            engine_fuzzy = engine_fuzzy or runner_id in match_map.get("fuzzy", set())

        any_alt_match = False
        any_alt_dated = False
        any_alt_rated = False
        any_alt_dated_rated = False
        fuzzy_alt_sources = []
        parse_failure_sources = []

        for source_name, match_map in per_source_runner_map.items():
            if source_name in CURRENT_ENGINE_SOURCE_NAMES or not match_map:
                continue
            profile = match_map["profile"]
            alt_match = runner_id in match_map.get("strict_any", set()) or runner_id in match_map.get("loose_any", set())
            alt_dated = runner_id in match_map.get("strict_dated", set()) or runner_id in match_map.get("loose_dated", set())
            alt_rated = runner_id in match_map.get("strict_rated", set()) or runner_id in match_map.get("loose_rated", set())
            alt_dated_rated = runner_id in match_map.get("strict_dated_rated", set()) or runner_id in match_map.get("loose_dated_rated", set())
            alt_fuzzy = runner_id in match_map.get("fuzzy", set())

            any_alt_match = any_alt_match or alt_match
            any_alt_dated = any_alt_dated or alt_dated
            any_alt_rated = any_alt_rated or alt_rated
            any_alt_dated_rated = any_alt_dated_rated or alt_dated_rated

            if alt_fuzzy:
                fuzzy_alt_sources.append(f"{source_name}: {match_map['fuzzy_candidate_map'].get(runner_id, '')}")
            if alt_match and int(profile.get("date_parse_failure_rows") or 0) > 0 and not alt_dated:
                parse_failure_sources.append(source_name)

        if engine_match and not engine_dated:
            if parse_failure_sources:
                reason = "DATE_PARSE_FAILURE_OR_BAD_DATE_FIELD"
            else:
                reason = "HORSE_MATCHED_BUT_NO_DATE_IN_ENGINE_SOURCE"
        elif engine_dated and not engine_rated:
            reason = "HORSE_MATCHED_BUT_NO_RATING_IN_ENGINE_SOURCE"
        elif any_alt_dated_rated and not engine_match:
            reason = "SOURCE_NOT_BEING_USED_BY_ENGINE"
        elif any_alt_match and not any_alt_dated:
            if parse_failure_sources:
                reason = "DATE_PARSE_FAILURE_OR_BAD_DATE_FIELD"
            else:
                reason = "HORSE_MATCHED_BUT_NO_DATE"
        elif any_alt_dated and not any_alt_rated:
            reason = "HORSE_MATCHED_BUT_NO_RATING"
        elif fuzzy_alt_sources:
            reason = "NAMING_MISMATCH_POSSIBLE"
        else:
            reason = "NO_HORSE_MATCH"

        no_history_reasons[reason] += 1

        alt_source = best_alt_source_for_runner(runner_id)
        alt_match_map = per_source_runner_map.get(alt_source, {}) if alt_source else {}
        alt_match_type = ""
        if alt_source:
            if runner_id in alt_match_map.get("strict_dated_rated", set()):
                alt_match_type = "STRICT_DATED_RATED"
            elif runner_id in alt_match_map.get("loose_dated_rated", set()):
                alt_match_type = "LOOSE_DATED_RATED"
            elif runner_id in alt_match_map.get("strict_dated", set()):
                alt_match_type = "STRICT_DATED"
            elif runner_id in alt_match_map.get("loose_dated", set()):
                alt_match_type = "LOOSE_DATED"
            elif runner_id in alt_match_map.get("strict_any", set()):
                alt_match_type = "STRICT_MATCH_ONLY"
            elif runner_id in alt_match_map.get("loose_any", set()):
                alt_match_type = "LOOSE_MATCH_ONLY"
            elif runner_id in alt_match_map.get("fuzzy", set()):
                alt_match_type = "FUZZY_SAFE"

        no_history_diagnostics.append(
            {
                "record_type": "no_history_diagnostic",
                "track": runner_info.get("track", ""),
                "race_no": runner_info.get("race_no", ""),
                "horse": runner_info.get("horse", ""),
                "horse_key": runner_info.get("horse_key", ""),
                "issue_type": reason,
                "engine_history_detail_match": "YES" if runner_id in per_source_runner_map.get("edgeiq_runner_history_detail_v1.csv", {}).get("strict_any", set()) or runner_id in per_source_runner_map.get("edgeiq_runner_history_detail_v1.csv", {}).get("loose_any", set()) else "NO",
                "engine_runner_form_history_match": "YES" if runner_id in per_source_runner_map.get("runner_form_history.csv", {}).get("strict_any", set()) or runner_id in per_source_runner_map.get("runner_form_history.csv", {}).get("loose_any", set()) else "NO",
                "best_alternative_source": alt_source or "",
                "best_alternative_match_type": alt_match_type,
                "fuzzy_alt_sources": " | ".join(fuzzy_alt_sources),
                "parse_failure_sources": " | ".join(parse_failure_sources),
            }
        )

        if alt_source and not engine_match:
            matched_elsewhere.append(
                {
                    "record_type": "matched_elsewhere_not_engine",
                    "track": runner_info.get("track", ""),
                    "race_no": runner_info.get("race_no", ""),
                    "horse": runner_info.get("horse", ""),
                    "horse_key": runner_info.get("horse_key", ""),
                    "alternative_source": alt_source,
                    "alternative_match_type": alt_match_type,
                    "issue_type": reason,
                }
            )

    # Keep the audit file useful, not endless.
    reason_rank = {"SOURCE_NOT_BEING_USED_BY_ENGINE": 1, "NAMING_MISMATCH_POSSIBLE": 2, "HORSE_MATCHED_BUT_NO_DATE": 3, "HORSE_MATCHED_BUT_NO_RATING": 4, "NO_HORSE_MATCH": 5}
    no_history_diagnostics = sorted(
        no_history_diagnostics,
        key=lambda row: (reason_rank.get(row["issue_type"], 9), row["best_alternative_source"] == "", row["track"], row["race_no"], row["horse"]),
    )
    matched_elsewhere = sorted(
        matched_elsewhere,
        key=lambda row: (row["alternative_match_type"] != "STRICT_DATED_RATED", row["alternative_source"], row["track"], row["race_no"], row["horse"]),
    )

    audit_rows.extend(no_history_diagnostics[:20])
    audit_rows.extend(matched_elsewhere[:20])
    audit_rows.extend(source_profiles)

    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(OUT_AUDIT, index=False)

    profiled_sources = [profile for profile in source_profiles if profile.get("detailed_profile_status") == "PROFILED"]
    recommended_sources = sorted(profiled_sources, key=source_priority_score, reverse=True)

    summary_rows = [
        {"summary_type": "overall", "label": "active_current_runners", "value": len(active_live), "detail": ""},
        {"summary_type": "overall", "label": "campaign_engine_no_history_rows", "value": len(campaign_no_history_ids), "detail": ""},
        {"summary_type": "overall", "label": "matching_sources_discovered", "value": len(discovered_files), "detail": "Filename discovery uses history/results/performance/rating plus explicit campaign sources."},
        {"summary_type": "overall", "label": "sources_profiled_in_detail", "value": len(profiled_sources), "detail": "Detailed profiling requires a horse-like column."},
    ]

    for reason, count in sorted(no_history_reasons.items(), key=lambda item: (-item[1], item[0])):
        summary_rows.append(
            {"summary_type": "no_history_reason", "label": reason, "value": count, "detail": ""}
        )

    for rank, profile in enumerate(recommended_sources[:6], start=1):
        summary_rows.append(
            {
                "summary_type": "recommended_source_priority",
                "label": str(rank),
                "value": profile["source_name"],
                "detail": (
                    f"strict_dated_rated={profile.get('strict_dated_rated_match_current_runners','')}; "
                    f"loose_dated_rated={profile.get('loose_dated_rated_match_current_runners','')}; "
                    f"dated_rows={profile.get('dated_rows','')}; rating_rows={profile.get('rating_rows','')}"
                ),
            }
        )

    if recommended_sources:
        best = recommended_sources[0]
        summary_rows.append(
            {
                "summary_type": "recommendation",
                "label": "best_source_for_campaign_engine_v1_1",
                "value": best["source_name"],
                "detail": "Highest combined runner-match coverage with dated and rating evidence.",
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_SUMMARY, index=False)

    print("[CAMPAIGN_COVERAGE_AUDIT_V1] COMPLETE")
    print(f"audit={OUT_AUDIT}")
    print(f"summary={OUT_SUMMARY}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
