from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Iterable

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"

OUT_AUDIT_PATH = DATA / "edgeiq_dna_frontend_join_audit_v1.csv"
OUT_SUMMARY_PATH = DATA / "edgeiq_dna_frontend_join_audit_v1_summary.csv"

DNA_FIELD_CANDIDATES = [
    "distance_fit_score",
    "distance_fit_band",
    "condition_fit_score",
    "condition_fit_band",
    "class_fit_score",
    "class_fit_band",
    "dna_v6_2_score",
    "dna_v6_2_band",
    "runner_dna_v6_2_narrative",
    "runner_dna_customer_summary",
    "positive_1_factor",
    "negative_1_factor",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: object) -> str:
    if value is None:
        return ""
    result = str(value).strip()
    return "" if result.lower() == "nan" else result


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def normalize_horse(value: object) -> str:
    base = text(value).upper()
    base = re.sub(r"\([^)]*\)", "", base)
    return re.sub(r"[^A-Z0-9]+", "", base)


def normalize_horse_loose(value: object) -> str:
    return re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", normalize_horse(value))


def first_present(row: pd.Series, columns: Iterable[str]) -> str:
    for column in columns:
        if column in row.index:
            value = text(row[column])
            if value:
                return value
    return ""


def truthy_flag(value: object) -> bool:
    return text(value).upper() in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHED", "LATESCRATCHED"}


def detect_source_files() -> list[Path]:
    explicit = [
        "edgeiq_live_runner_dna_v6_2.csv",
        "edgeiq_runner_dna_v6_2.csv",
        "edgeiq_runner_dna_drawer_feed_v2.csv",
        "edgeiq_live_runner_factor_scorecard_v2.csv",
        "edgeiq_runner_profile_engine_current.csv",
        "edgeiq_live_class_dna_v3.csv",
        "edgeiq_live_condition_dna_v1.csv",
        "edgeiq_live_distance_dna_v1.csv",
    ]
    return [DATA / name for name in explicit]


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str).fillna("")
    except (EmptyDataError, ParserError, UnicodeDecodeError):
        return pd.DataFrame()


def load_active_live() -> pd.DataFrame:
    live = load_csv(LIVE_PATH)
    if live.empty:
        raise FileNotFoundError(f"Missing or empty live runner board: {LIVE_PATH}")
    active_mask = ~live.apply(
        lambda row: (
            text(row.get("runner_status")).upper() == "SCRATCHED"
            or truthy_flag(row.get("is_scratched"))
            or "SCRATCH" in text(row.get("scratch_status")).upper()
        ),
        axis=1,
    )
    active = live.loc[active_mask].copy()
    active["race_date_value"] = active.apply(lambda row: first_present(row, ["race_date", "meeting_date", "date", "raceDate"]), axis=1)
    active["track_value"] = active.apply(lambda row: first_present(row, ["track", "meeting", "meeting_name"]), axis=1)
    active["race_no_value"] = active.apply(lambda row: first_present(row, ["race_no", "raceNo", "race_number", "race"]), axis=1)
    active["horse_value"] = active.apply(lambda row: first_present(row, ["horse", "horseName", "runner", "runner_name"]), axis=1)
    active["horse_key_value"] = active.apply(lambda row: first_present(row, ["horse_key", "horseKey", "runner_key", "runnerKey"]), axis=1)
    active["runner_key_value"] = active.apply(lambda row: first_present(row, ["runner_key", "runnerKey"]), axis=1)
    active["race_key_value"] = active.apply(lambda row: first_present(row, ["race_key", "raceKey"]), axis=1)
    active["track_norm"] = active["track_value"].map(normalize_track)
    active["horse_norm"] = active["horse_value"].map(normalize_horse)
    active["horse_loose"] = active["horse_value"].map(normalize_horse_loose)
    active["horse_key_norm"] = active["horse_key_value"].map(normalize_horse)
    return active


def prepare_source(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    prepared = df.copy()
    prepared["race_date_value"] = prepared.apply(
        lambda row: first_present(row, ["race_date", "meeting_date", "date", "raceDate", "current_race_date"]),
        axis=1,
    )
    prepared["track_value"] = prepared.apply(lambda row: first_present(row, ["track", "meeting", "meeting_name"]), axis=1)
    prepared["race_no_value"] = prepared.apply(lambda row: first_present(row, ["race_no", "raceNo", "race_number", "race"]), axis=1)
    prepared["horse_value"] = prepared.apply(lambda row: first_present(row, ["horse", "horseName", "runner", "runner_name"]), axis=1)
    prepared["horse_key_value"] = prepared.apply(lambda row: first_present(row, ["horse_key", "horseKey", "runner_key", "runnerKey"]), axis=1)
    prepared["runner_key_value"] = prepared.apply(lambda row: first_present(row, ["runner_key", "runnerKey"]), axis=1)
    prepared["race_key_value"] = prepared.apply(lambda row: first_present(row, ["race_key", "raceKey"]), axis=1)
    prepared["track_norm"] = prepared["track_value"].map(normalize_track)
    prepared["horse_norm"] = prepared["horse_value"].map(normalize_horse)
    prepared["horse_loose"] = prepared["horse_value"].map(normalize_horse_loose)
    prepared["horse_key_norm"] = prepared["horse_key_value"].map(normalize_horse)
    return prepared


def same_runner_frontend(source_row: pd.Series, live_row: pd.Series) -> bool:
    source_runner_key = text(source_row.get("runner_key_value"))
    live_runner_key = text(live_row.get("runner_key_value"))
    if source_runner_key and live_runner_key and source_runner_key == live_runner_key:
        return True

    source_race_key = text(source_row.get("race_key_value"))
    live_race_key = text(live_row.get("race_key_value"))
    source_horse_key = normalize_horse(source_row.get("horse_key_value"))
    live_horse_key = normalize_horse(live_row.get("horse_key_value"))
    if source_race_key and live_race_key and source_horse_key and live_horse_key and source_race_key == live_race_key and source_horse_key == live_horse_key:
        return True

    source_date = text(source_row.get("race_date_value"))
    live_date = text(live_row.get("race_date_value"))
    if source_date and live_date and source_date != live_date:
        return False
    if normalize_track(source_row.get("track_value")) != normalize_track(live_row.get("track_value")):
        return False
    if text(source_row.get("race_no_value")) != text(live_row.get("race_no_value")):
        return False

    source_tokens = {
        normalize_horse(source_row.get("horse_key_value")),
        normalize_horse(source_row.get("horse_canon")),
        normalize_horse(source_row.get("horse_value")),
        normalize_horse_loose(source_row.get("horse_key_value")),
        normalize_horse_loose(source_row.get("horse_canon")),
        normalize_horse_loose(source_row.get("horse_value")),
    }
    live_tokens = {
        normalize_horse(live_row.get("horse_key_value")),
        normalize_horse(live_row.get("horse_canon")),
        normalize_horse(live_row.get("horse_value")),
        normalize_horse_loose(live_row.get("horse_key_value")),
        normalize_horse_loose(live_row.get("horse_canon")),
        normalize_horse_loose(live_row.get("horse_value")),
    }
    source_tokens.discard("")
    live_tokens.discard("")
    return bool(source_tokens & live_tokens)


def build_source_key_sets(source: pd.DataFrame) -> dict[str, set[str]]:
    key_sets: dict[str, set[str]] = {
        "exact_horse_key": set(),
        "exact_horse": set(),
        "cleaned_key": set(),
        "cleaned_horse": set(),
        "cleaned_loose": set(),
        "horse_only_key": set(),
        "horse_only_horse": set(),
        "horse_only_loose": set(),
        "runner_key": set(),
        "racekey_horsekey": set(),
        "frontend_key": set(),
        "frontend_horse": set(),
        "frontend_loose": set(),
    }
    if source.empty:
        return key_sets

    for _, row in source.iterrows():
        date_value = text(row.get("race_date_value"))
        track_value = text(row.get("track_value"))
        track_norm = text(row.get("track_norm"))
        race_no_value = text(row.get("race_no_value"))
        horse_value = text(row.get("horse_value"))
        horse_norm = text(row.get("horse_norm"))
        horse_loose = text(row.get("horse_loose"))
        horse_key_value = text(row.get("horse_key_value"))
        horse_key_norm = text(row.get("horse_key_norm"))
        runner_key_value = text(row.get("runner_key_value"))
        race_key_value = text(row.get("race_key_value"))

        if date_value and track_value and race_no_value and horse_key_value:
            key_sets["exact_horse_key"].add("|".join([date_value, track_value, race_no_value, horse_key_value]))
        if date_value and track_value and race_no_value and horse_value:
            key_sets["exact_horse"].add("|".join([date_value, track_value, race_no_value, horse_value]))
        if date_value and track_norm and race_no_value and horse_key_norm:
            key_sets["cleaned_key"].add("|".join([date_value, track_norm, race_no_value, horse_key_norm]))
            key_sets["frontend_key"].add("|".join([date_value, track_norm, race_no_value, horse_key_norm]))
        if date_value and track_norm and race_no_value and horse_norm:
            key_sets["cleaned_horse"].add("|".join([date_value, track_norm, race_no_value, horse_norm]))
            key_sets["frontend_horse"].add("|".join([date_value, track_norm, race_no_value, horse_norm]))
        if date_value and track_norm and race_no_value and horse_loose:
            key_sets["cleaned_loose"].add("|".join([date_value, track_norm, race_no_value, horse_loose]))
            key_sets["frontend_loose"].add("|".join([date_value, track_norm, race_no_value, horse_loose]))
        if horse_key_norm:
            key_sets["horse_only_key"].add(horse_key_norm)
        if horse_norm:
            key_sets["horse_only_horse"].add(horse_norm)
        if horse_loose:
            key_sets["horse_only_loose"].add(horse_loose)
        if runner_key_value:
            key_sets["runner_key"].add(runner_key_value)
        if race_key_value and horse_key_norm:
            key_sets["racekey_horsekey"].add("|".join([race_key_value, horse_key_norm]))

    return key_sets


def join_count(active: pd.DataFrame, source_sets: dict[str, set[str]], mode: str) -> tuple[int, list[str]]:
    matched: list[str] = []
    for _, live_row in active.iterrows():
        if mode == "exact_horse_key":
            key = "|".join([text(live_row["race_date_value"]), text(live_row["track_value"]), text(live_row["race_no_value"]), text(live_row["horse_key_value"])])
            is_match = bool(key) and key in source_sets["exact_horse_key"]
        elif mode == "exact_horse":
            key = "|".join([text(live_row["race_date_value"]), text(live_row["track_value"]), text(live_row["race_no_value"]), text(live_row["horse_value"])])
            is_match = bool(key) and key in source_sets["exact_horse"]
        elif mode == "cleaned":
            prefix = "|".join([text(live_row["race_date_value"]), text(live_row["track_norm"]), text(live_row["race_no_value"])])
            by_key = "|".join([prefix, text(live_row["horse_key_norm"])]) if text(live_row["horse_key_norm"]) else ""
            by_horse = "|".join([prefix, text(live_row["horse_norm"])]) if text(live_row["horse_norm"]) else ""
            by_loose = "|".join([prefix, text(live_row["horse_loose"])]) if text(live_row["horse_loose"]) else ""
            is_match = (
                (by_key and by_key in source_sets["cleaned_key"])
                or (by_horse and by_horse in source_sets["cleaned_horse"])
                or (by_loose and by_loose in source_sets["cleaned_loose"])
            )
        elif mode == "horse_only":
            is_match = (
                (text(live_row["horse_key_norm"]) and text(live_row["horse_key_norm"]) in source_sets["horse_only_key"])
                or (text(live_row["horse_norm"]) and text(live_row["horse_norm"]) in source_sets["horse_only_horse"])
                or (text(live_row["horse_loose"]) and text(live_row["horse_loose"]) in source_sets["horse_only_loose"])
            )
        elif mode == "frontend":
            runner_key = text(live_row.get("runner_key_value"))
            race_key = text(live_row.get("race_key_value"))
            horse_key_norm = text(live_row.get("horse_key_norm"))
            prefix = "|".join([text(live_row["race_date_value"]), text(live_row["track_norm"]), text(live_row["race_no_value"])])
            frontend_key = "|".join([prefix, horse_key_norm]) if horse_key_norm else ""
            frontend_horse = "|".join([prefix, text(live_row["horse_norm"])]) if text(live_row["horse_norm"]) else ""
            frontend_loose = "|".join([prefix, text(live_row["horse_loose"])]) if text(live_row["horse_loose"]) else ""
            racekey_horsekey = "|".join([race_key, horse_key_norm]) if race_key and horse_key_norm else ""
            is_match = (
                (runner_key and runner_key in source_sets["runner_key"])
                or (racekey_horsekey and racekey_horsekey in source_sets["racekey_horsekey"])
                or (frontend_key and frontend_key in source_sets["frontend_key"])
                or (frontend_horse and frontend_horse in source_sets["frontend_horse"])
                or (frontend_loose and frontend_loose in source_sets["frontend_loose"])
            )
        else:
            raise ValueError(f"Unknown join mode: {mode}")
        if is_match:
            matched.append(live_row["horse_value"])
    return len(matched), matched


def infer_root_cause(path: Path, source: pd.DataFrame, active: pd.DataFrame, bendigo_source_rows: int, frontend_count: int, cleaned_count: int, dna_payload_rows: int) -> str:
    if not path.exists():
        return "SOURCE_FILE_MISSING"
    if source.empty:
        return "SOURCE_EMPTY"
    if bendigo_source_rows == 0 and len(source) > 0:
        if source["race_date_value"].nunique() > 0:
            return "STALE_SOURCE_FILE"
        return "NO_BENDIGO_R6_ROWS"
    if frontend_count == 0 and cleaned_count > 0:
        return "FRONTEND_JOIN_LOGIC_ISSUE"
    if cleaned_count > 0 and dna_payload_rows == 0:
        return "EVIDENCE_FIELDS_BLANK"
    if cleaned_count == 0 and len(source) > 0:
        return "TRACK_RACE_OR_HORSE_MISMATCH"
    return "HEALTHY"


def main() -> None:
    built_at = now_iso()
    active = load_active_live()
    active_bendigo = active[
        (active["race_date_value"] == "2026-06-25")
        & (active["track_norm"] == normalize_track("BENDIGO"))
        & (active["race_no_value"] == "6")
    ].copy()

    audit_rows: list[dict[str, object]] = []

    for path in detect_source_files():
        source_name = path.name
        raw = load_csv(path)
        source = prepare_source(raw)
        source_sets = build_source_key_sets(source)

        if not raw.empty:
            horse_column = next((col for col in ["horse_key", "horse", "runner", "runner_name", "horseName"] if col in raw.columns), "")
            date_column = next((col for col in ["race_date", "meeting_date", "date", "raceDate", "current_race_date"] if col in raw.columns), "")
            track_column = next((col for col in ["track", "meeting", "meeting_name"] if col in raw.columns), "")
            race_no_column = next((col for col in ["race_no", "raceNo", "race_number", "race"] if col in raw.columns), "")
            matched_field_names = [field for field in DNA_FIELD_CANDIDATES if field in raw.columns]
            dna_payload_rows = int(
                raw[matched_field_names].apply(lambda col: col.map(text)).replace("", pd.NA).notna().any(axis=1).sum()
            ) if matched_field_names else 0
        else:
            horse_column = date_column = track_column = race_no_column = ""
            matched_field_names = []
            dna_payload_rows = 0

        exact_horse_key_count, _ = join_count(active, source_sets, "exact_horse_key") if not source.empty else (0, [])
        exact_horse_count, _ = join_count(active, source_sets, "exact_horse") if not source.empty else (0, [])
        cleaned_count, cleaned_matches = join_count(active, source_sets, "cleaned") if not source.empty else (0, [])
        horse_only_count, _ = join_count(active, source_sets, "horse_only") if not source.empty else (0, [])
        frontend_count, frontend_matches = join_count(active, source_sets, "frontend") if not source.empty else (0, [])

        bendigo_source = source[
            (source["race_date_value"] == "2026-06-25")
            & (source["track_norm"] == normalize_track("BENDIGO"))
            & (source["race_no_value"] == "6")
        ].copy() if not source.empty else pd.DataFrame()

        bendigo_sets = build_source_key_sets(bendigo_source)
        bendigo_exact_key_count, _ = join_count(active_bendigo, bendigo_sets, "exact_horse_key") if not bendigo_source.empty else (0, [])
        bendigo_exact_horse_count, _ = join_count(active_bendigo, bendigo_sets, "exact_horse") if not bendigo_source.empty else (0, [])
        bendigo_cleaned_count, _ = join_count(active_bendigo, bendigo_sets, "cleaned") if not bendigo_source.empty else (0, [])
        bendigo_frontend_count, bendigo_frontend_matches = join_count(active_bendigo, bendigo_sets, "frontend") if not bendigo_source.empty else (0, [])

        unmatched_bendigo = [
            horse_name
            for horse_name in active_bendigo["horse_value"].tolist()
            if horse_name not in set(bendigo_frontend_matches)
        ]

        root_cause = infer_root_cause(path, source, active, len(bendigo_source), frontend_count, cleaned_count, dna_payload_rows)
        if root_cause == "SOURCE_FILE_MISSING":
            recommended_fix = "Restore or rebuild the source file before attempting any frontend change."
            readiness = "NOT_READY"
        elif root_cause == "STALE_SOURCE_FILE":
            recommended_fix = "Rebuild the race-scoped DNA feeds for the current live universe before touching the frontend join."
            readiness = "NEEDS_ENGINE_REBUILD"
        elif root_cause == "FRONTEND_JOIN_LOGIC_ISSUE":
            recommended_fix = "Use strict current-race join: race_date + cleanTrack(track) + race_no + cleanHorse(horse_key || horse), with loose horse fallback only when horse_key is missing."
            readiness = "READY_TO_FIX_FRONTEND_JOIN"
        elif root_cause == "EVIDENCE_FIELDS_BLANK":
            recommended_fix = "Switch to a richer DNA source for footer/profile usage, or repopulate the fit-band payload in the current source."
            readiness = "READY_TO_SWITCH_SOURCE"
        elif root_cause == "TRACK_RACE_OR_HORSE_MISMATCH":
            recommended_fix = "Audit rebuild scope and horse normalization; the source exists but is not aligned to the current race universe."
            readiness = "NOT_READY"
        else:
            recommended_fix = "Current source and join look healthy."
            readiness = "READY_TO_FIX_FRONTEND_JOIN"

        audit_rows.append(
            {
                "source_file": source_name,
                "file_exists": "YES" if path.exists() else "NO",
                "rows": len(raw),
                "unique_horses": int(source["horse_norm"].replace("", pd.NA).dropna().nunique()) if not source.empty else 0,
                "track_column": track_column,
                "race_no_column": race_no_column,
                "date_column": date_column,
                "horse_column": horse_column,
                "horse_key_column": "horse_key" if "horse_key" in raw.columns else ("horseKey" if "horseKey" in raw.columns else ""),
                "dna_fields_present": "; ".join(matched_field_names),
                "dna_payload_rows": dna_payload_rows,
                "exact_date_track_race_horse_key_match_count": exact_horse_key_count,
                "exact_date_track_race_horse_match_count": exact_horse_count,
                "cleaned_track_race_horse_match_count": cleaned_count,
                "horse_only_match_count": horse_only_count,
                "frontend_style_match_count": frontend_count,
                "best_join_success_pct": round((max(frontend_count, cleaned_count) / len(active)) * 100.0, 2) if len(active) else 0.0,
                "bendigo_r6_active_runners": len(active_bendigo),
                "bendigo_r6_source_rows": len(bendigo_source),
                "bendigo_r6_exact_key_matches": bendigo_exact_key_count,
                "bendigo_r6_exact_horse_matches": bendigo_exact_horse_count,
                "bendigo_r6_cleaned_matches": bendigo_cleaned_count,
                "bendigo_r6_frontend_matches": bendigo_frontend_count,
                "bendigo_r6_unmatched_examples": " | ".join(unmatched_bendigo[:8]),
                "likely_root_cause": root_cause,
                "recommended_fix": recommended_fix,
                "ui_wire_readiness": readiness,
                "built_at": built_at,
            }
        )

    audit_df = pd.DataFrame(audit_rows).sort_values(
        ["frontend_style_match_count", "cleaned_track_race_horse_match_count", "dna_payload_rows", "rows"],
        ascending=[False, False, False, False],
    )
    audit_df.to_csv(OUT_AUDIT_PATH, index=False)

    best_source_row = audit_df.iloc[0] if not audit_df.empty else None
    any_current_bendigo = int((audit_df["bendigo_r6_source_rows"] > 0).sum()) if not audit_df.empty else 0
    likely_root_cause = (
        "STALE_OR_NARROW_DNA_FEEDS"
        if any_current_bendigo == 0
        else ("FRONTEND_JOIN_LOGIC_ISSUE" if int((audit_df["likely_root_cause"] == "FRONTEND_JOIN_LOGIC_ISSUE").sum()) > 0 else "SOURCE_SPECIFIC")
    )
    recommended_fix = (
        "Rebuild current-race DNA feeds (runner DNA, DNA drawer, factor scorecard/profile) for the active universe first; only then revisit frontend joins."
        if likely_root_cause == "STALE_OR_NARROW_DNA_FEEDS"
        else "Use strict current-race DNA joins: race_date + cleanTrack(track) + race_no + cleanHorse(horse_key || horse), with loose horse fallback only when horse_key is missing."
    )
    readiness = "NEEDS_ENGINE_REBUILD" if likely_root_cause == "STALE_OR_NARROW_DNA_FEEDS" else "READY_TO_FIX_FRONTEND_JOIN"

    summary_df = pd.DataFrame(
        [
            {
                "audit_status": "PASS",
                "active_runners": len(active),
                "best_source": "" if best_source_row is None else best_source_row["source_file"],
                "best_source_rows": 0 if best_source_row is None else best_source_row["rows"],
                "best_source_join_success": 0 if best_source_row is None else best_source_row["frontend_style_match_count"],
                "bendigo_r6_join_success": 0 if best_source_row is None else best_source_row["bendigo_r6_frontend_matches"],
                "likely_root_cause": likely_root_cause,
                "recommended_fix": recommended_fix,
                "best_source_for_footer_coverage": "" if best_source_row is None else best_source_row["source_file"],
                "best_source_for_profile_cards": "" if best_source_row is None else best_source_row["source_file"],
                "recommended_frontend_join_strategy": "race_date + cleanTrack(track) + race_no + cleanHorse(horse_key || horse), fallback to cleanHorseLoose(horse) only if horse_key missing",
                "ui_wire_readiness": readiness,
                "built_at": built_at,
            }
        ]
    )
    summary_df.to_csv(OUT_SUMMARY_PATH, index=False)

    print("[EDGEIQ_DNA_FRONTEND_JOIN_AUDIT_V1] COMPLETE")
    print(f"active_runners={len(active)}")
    print(f"best_source={summary_df.loc[0, 'best_source']}")
    print(f"best_source_join_success={summary_df.loc[0, 'best_source_join_success']}")
    print(f"bendigo_r6_join_success={summary_df.loc[0, 'bendigo_r6_join_success']}")
    print(f"likely_root_cause={summary_df.loc[0, 'likely_root_cause']}")
    print(f"recommended_fix={summary_df.loc[0, 'recommended_fix']}")
    print(f"wrote={OUT_AUDIT_PATH}")
    print(f"summary={OUT_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
