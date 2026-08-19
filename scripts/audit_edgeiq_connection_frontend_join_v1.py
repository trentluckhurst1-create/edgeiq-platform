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

OUT_AUDIT_PATH = DATA / "edgeiq_connection_frontend_join_audit_v1.csv"
OUT_SUMMARY_PATH = DATA / "edgeiq_connection_frontend_join_audit_v1_summary.csv"

CONNECTION_FIELDS = [
    "connection_score",
    "connection_band",
    "trainer_track_sr",
    "jockey_track_sr",
    "combo_sr",
    "combo_track_sr",
    "connection_narrative",
    "connection_positive_1",
    "connection_risk_1",
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
        "edgeiq_connection_intelligence_v1.csv",
        "edgeiq_live_runner_factor_scorecard_v2.csv",
        "edgeiq_runner_profile_engine_current.csv",
        "edgeiq_explainability_terminal_feed_v1_2.csv",
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
    prepared["track_norm"] = prepared["track_value"].map(normalize_track)
    prepared["horse_norm"] = prepared["horse_value"].map(normalize_horse)
    prepared["horse_loose"] = prepared["horse_value"].map(normalize_horse_loose)
    prepared["horse_key_norm"] = prepared["horse_key_value"].map(normalize_horse)
    return prepared


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

        if date_value and track_value and race_no_value and horse_key_value:
            key_sets["exact_horse_key"].add("|".join([date_value, track_value, race_no_value, horse_key_value]))
        if date_value and track_value and race_no_value and horse_value:
            key_sets["exact_horse"].add("|".join([date_value, track_value, race_no_value, horse_value]))
        if date_value and track_norm and race_no_value and horse_key_norm:
            key_sets["cleaned_key"].add("|".join([date_value, track_norm, race_no_value, horse_key_norm]))
        if date_value and track_norm and race_no_value and horse_norm:
            key_sets["cleaned_horse"].add("|".join([date_value, track_norm, race_no_value, horse_norm]))
        if date_value and track_norm and race_no_value and horse_loose:
            key_sets["cleaned_loose"].add("|".join([date_value, track_norm, race_no_value, horse_loose]))
        if horse_key_norm:
            key_sets["horse_only_key"].add(horse_key_norm)
        if horse_norm:
            key_sets["horse_only_horse"].add(horse_norm)
        if horse_loose:
            key_sets["horse_only_loose"].add(horse_loose)
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
        else:
            raise ValueError(f"Unknown join mode: {mode}")
        if is_match:
            matched.append(live_row["horse_value"])
    return len(matched), matched


def connection_payload_rows(df: pd.DataFrame) -> int:
    present = [field for field in CONNECTION_FIELDS if field in df.columns]
    if not present:
        return 0
    return int(df[present].apply(lambda col: col.map(text)).replace("", pd.NA).notna().any(axis=1).sum())


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
        raw = load_csv(path)
        source = prepare_source(raw)
        source_sets = build_source_key_sets(source)

        date_col = next((col for col in ["race_date", "meeting_date", "date", "raceDate", "current_race_date"] if col in raw.columns), "")
        track_col = next((col for col in ["track", "meeting", "meeting_name"] if col in raw.columns), "")
        race_col = next((col for col in ["race_no", "raceNo", "race_number", "race"] if col in raw.columns), "")
        horse_col = next((col for col in ["horse_key", "horseKey", "horse", "horseName", "runner", "runner_name"] if col in raw.columns), "")

        exact_horse_key_count, _ = join_count(active, source_sets, "exact_horse_key") if not source.empty else (0, [])
        exact_horse_count, _ = join_count(active, source_sets, "exact_horse") if not source.empty else (0, [])
        cleaned_count, _ = join_count(active, source_sets, "cleaned") if not source.empty else (0, [])
        horse_only_count, _ = join_count(active, source_sets, "horse_only") if not source.empty else (0, [])

        bendigo_source = source[
            (source["race_date_value"] == "2026-06-25")
            & (source["track_norm"] == normalize_track("BENDIGO"))
            & (source["race_no_value"] == "6")
        ].copy() if not source.empty else pd.DataFrame()

        bendigo_sets = build_source_key_sets(bendigo_source)
        bendigo_exact_horse_key_count, _ = join_count(active_bendigo, bendigo_sets, "exact_horse_key") if not bendigo_source.empty else (0, [])
        bendigo_cleaned_count, bendigo_cleaned_matches = join_count(active_bendigo, bendigo_sets, "cleaned") if not bendigo_source.empty else (0, [])

        payload_rows = connection_payload_rows(raw) if not raw.empty else 0
        bendigo_payload_rows = connection_payload_rows(bendigo_source) if not bendigo_source.empty else 0
        bendigo_trainer_rows = int((bendigo_source.get("trainer_track_sr", pd.Series(dtype=str)).map(text) != "").sum()) if not bendigo_source.empty and "trainer_track_sr" in bendigo_source.columns else 0
        bendigo_jockey_rows = int((bendigo_source.get("jockey_track_sr", pd.Series(dtype=str)).map(text) != "").sum()) if not bendigo_source.empty and "jockey_track_sr" in bendigo_source.columns else 0
        bendigo_combo_rows = int((bendigo_source.get("combo_sr", pd.Series(dtype=str)).map(text) != "").sum()) if not bendigo_source.empty and "combo_sr" in bendigo_source.columns else 0

        unmatched_examples = [
            horse_name
            for horse_name in active_bendigo["horse_value"].tolist()
            if horse_name not in set(bendigo_cleaned_matches)
        ]

        if not path.exists():
            root_cause = "SOURCE_FILE_MISSING"
            readiness = "NOT_READY"
            recommended_fix = "Restore or rebuild the source file before changing the frontend."
        elif raw.empty:
            root_cause = "SOURCE_EMPTY"
            readiness = "NOT_READY"
            recommended_fix = "Rebuild the source; it has no rows."
        elif len(bendigo_source) == 0 and len(raw) > 0:
            root_cause = "STALE_OR_DIFFERENT_RACE_UNIVERSE"
            readiness = "NEEDS_ENGINE_REBUILD"
            recommended_fix = "Rebuild current-race connection evidence and refresh explainability V1.2 from that rebuilt universe."
        elif bendigo_cleaned_count == 0 and horse_only_count > 0:
            root_cause = "TRACK_OR_RACE_JOIN_MISMATCH"
            readiness = "READY_TO_FIX_FRONTEND_JOIN"
            recommended_fix = "Use strict current-race join: race_date + cleanTrack(track) + race_no + cleanHorse(horse_key || horse)."
        elif bendigo_cleaned_count > 0 and bendigo_payload_rows == 0:
            root_cause = "TRUE_LOW_COVERAGE"
            readiness = "TRUE_LOW_COVERAGE"
            recommended_fix = "Connection rows exist but meaningful connection payload is absent for this race."
        else:
            root_cause = "HEALTHY"
            readiness = "READY_TO_FIX_FRONTEND_JOIN"
            recommended_fix = "Current source and join look usable."

        audit_rows.append(
            {
                "source_file": path.name,
                "file_exists": "YES" if path.exists() else "NO",
                "rows": len(raw),
                "unique_horses": int(source["horse_norm"].replace("", pd.NA).dropna().nunique()) if not source.empty else 0,
                "date_column": date_col,
                "track_column": track_col,
                "race_no_column": race_col,
                "horse_column": horse_col,
                "connection_fields_present": "; ".join(field for field in CONNECTION_FIELDS if field in raw.columns),
                "true_connection_payload_rows": payload_rows,
                "exact_date_track_race_horse_key_match_count": exact_horse_key_count,
                "exact_date_track_race_horse_match_count": exact_horse_count,
                "cleaned_current_race_join_match_count": cleaned_count,
                "horse_only_match_count": horse_only_count,
                "bendigo_r6_active_runners": len(active_bendigo),
                "bendigo_r6_rows_available": len(bendigo_source),
                "bendigo_r6_exact_key_matches": bendigo_exact_horse_key_count,
                "bendigo_r6_cleaned_matches": bendigo_cleaned_count,
                "bendigo_r6_true_connection_payload_rows": bendigo_payload_rows,
                "bendigo_r6_trainer_only_rows": bendigo_trainer_rows,
                "bendigo_r6_jockey_only_rows": bendigo_jockey_rows,
                "bendigo_r6_combo_rows": bendigo_combo_rows,
                "bendigo_r6_unmatched_examples": " | ".join(unmatched_examples[:8]),
                "likely_root_cause": root_cause,
                "recommended_fix": recommended_fix,
                "ui_wire_readiness": readiness,
                "built_at": built_at,
            }
        )

    audit_df = pd.DataFrame(audit_rows).sort_values(
        ["bendigo_r6_cleaned_matches", "true_connection_payload_rows", "rows"],
        ascending=[False, False, False],
    )
    audit_df.to_csv(OUT_AUDIT_PATH, index=False)

    best_source_row = audit_df.iloc[0] if not audit_df.empty else None
    any_bendigo_rows = int((audit_df["bendigo_r6_rows_available"] > 0).sum()) if not audit_df.empty else 0
    likely_root_cause = (
        "STALE_CONNECTION_SOURCE_UNIVERSE"
        if any_bendigo_rows == 0
        else ("TRUE_LOW_COVERAGE" if int(audit_df["bendigo_r6_true_connection_payload_rows"].max()) == 0 else "JOIN_OR_SOURCE_SPECIFIC")
    )
    recommended_fix = (
        "Rebuild edgeiq_connection_intelligence_v1.csv for the active universe and regenerate edgeiq_explainability_terminal_feed_v1_2.csv from that rebuilt connection payload before changing frontend logic."
        if likely_root_cause == "STALE_CONNECTION_SOURCE_UNIVERSE"
        else (
            "Connection evidence is genuinely sparse for the current race."
            if likely_root_cause == "TRUE_LOW_COVERAGE"
            else "Use strict current-race connection joins: race_date + cleanTrack(track) + race_no + cleanHorse(horse_key || horse)."
        )
    )
    readiness = (
        "NEEDS_ENGINE_REBUILD"
        if likely_root_cause == "STALE_CONNECTION_SOURCE_UNIVERSE"
        else ("TRUE_LOW_COVERAGE" if likely_root_cause == "TRUE_LOW_COVERAGE" else "READY_TO_FIX_FRONTEND_JOIN")
    )

    summary_df = pd.DataFrame(
        [
            {
                "audit_status": "PASS",
                "active_runners": len(active),
                "best_source": "" if best_source_row is None else best_source_row["source_file"],
                "best_source_rows": 0 if best_source_row is None else best_source_row["rows"],
                "best_source_join_success": 0 if best_source_row is None else best_source_row["cleaned_current_race_join_match_count"],
                "bendigo_r6_join_success": 0 if best_source_row is None else best_source_row["bendigo_r6_cleaned_matches"],
                "likely_root_cause": likely_root_cause,
                "recommended_fix": recommended_fix,
                "recommended_frontend_join_strategy": "race_date + cleanTrack(track) + race_no + cleanHorse(horse_key || horse), with horse-only fallbacks reserved for non-race-scoped historical sources.",
                "ui_wire_readiness": readiness,
                "built_at": built_at,
            }
        ]
    )
    summary_df.to_csv(OUT_SUMMARY_PATH, index=False)

    print("[EDGEIQ_CONNECTION_FRONTEND_JOIN_AUDIT_V1] COMPLETE")
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
