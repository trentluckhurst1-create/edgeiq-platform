from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

TARGETS = [
    DATA / "edgeiq_live_runner_dna_v6_2.csv",
    DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
    DATA / "edgeiq_live_runner_factor_scorecard_v2.csv",
    DATA / "edgeiq_runner_profile_engine_current.csv",
]

AUDIT_OUT = DATA / "edgeiq_current_dna_universe_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_current_dna_universe_audit_v1_summary.csv"

TRUTHY = {"1", "TRUE", "YES", "Y"}


@dataclass(frozen=True)
class KeyColumns:
    race_date: str | None
    track: str | None
    race_no: str | None
    horse: str | None
    horse_key: str | None


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_track(value: object) -> str:
    text = safe_text(value).upper()
    text = text.replace("SPORTSBET-", "SPORTSBET ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_horse(value: object) -> str:
    text = safe_text(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def detect_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {column.lower(): column for column in frame.columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def detect_key_columns(frame: pd.DataFrame) -> KeyColumns:
    return KeyColumns(
        race_date=detect_column(frame, ["race_date", "meeting_date", "date"]),
        track=detect_column(frame, ["track", "meeting_name"]),
        race_no=detect_column(frame, ["race_no", "race_number"]),
        horse=detect_column(frame, ["horse", "runner", "runner_name", "horseName"]),
        horse_key=detect_column(frame, ["horse_key", "horseKey"]),
    )


def build_runner_key(frame: pd.DataFrame, key_cols: KeyColumns, horse_key_fallback: bool = True) -> pd.Series:
    race_date = frame.get(key_cols.race_date, pd.Series("", index=frame.index)).map(safe_text).str[:10]
    track = frame.get(key_cols.track, pd.Series("", index=frame.index)).map(clean_track)
    race_no = frame.get(key_cols.race_no, pd.Series("", index=frame.index)).map(safe_text)
    horse_series = frame.get(key_cols.horse_key, pd.Series("", index=frame.index)) if horse_key_fallback and key_cols.horse_key else pd.Series("", index=frame.index)
    horse = horse_series.map(clean_horse)
    if key_cols.horse is not None:
        fallback = frame.get(key_cols.horse, pd.Series("", index=frame.index)).map(clean_horse)
        horse = horse.where(horse != "", fallback)
    return race_date + "|" + track + "|" + race_no + "|" + horse


def load_active_universe() -> pd.DataFrame:
    if not LIVE_BOARD.exists():
        raise FileNotFoundError(f"Missing live runner board: {LIVE_BOARD}")

    frame = pd.read_csv(LIVE_BOARD, dtype=str, keep_default_na=False, low_memory=False)
    if "runner_status" in frame.columns:
        frame = frame[frame["runner_status"].astype(str).str.upper().ne("SCRATCHED")].copy()
    if "is_scratched" in frame.columns:
        frame = frame[~frame["is_scratched"].astype(str).str.upper().isin(TRUTHY)].copy()

    key_cols = detect_key_columns(frame)
    frame["audit_runner_key"] = build_runner_key(frame, key_cols)
    frame["audit_track"] = frame.get(key_cols.track, pd.Series("", index=frame.index)).map(clean_track)
    frame["audit_race_date"] = frame.get(key_cols.race_date, pd.Series("", index=frame.index)).map(safe_text).str[:10]
    frame["audit_race_no"] = frame.get(key_cols.race_no, pd.Series("", index=frame.index)).map(safe_text)
    frame["audit_horse"] = frame.get(key_cols.horse, pd.Series("", index=frame.index)).map(safe_text)
    return frame


def summarize_set(values: pd.Series) -> str:
    cleaned = sorted({safe_text(value) for value in values if safe_text(value) != ""})
    return "|".join(cleaned)


def candidate_status(active_matches: int, active_total: int, stale_flag: str, exists: bool) -> str:
    if not exists:
        return "MISSING"
    if stale_flag == "YES":
        return "STALE"
    if active_matches == active_total:
        return "CURRENT_FULL_MATCH"
    if active_matches > 0:
        return "PARTIAL_MATCH"
    return "NO_CURRENT_MATCH"


def recommendation(file_name: str, status: str) -> str:
    if file_name == "edgeiq_runner_profile_engine_current.csv":
        return "OUT_OF_SCOPE_REVIEW" if status != "CURRENT_FULL_MATCH" else "REUSE"
    if status in {"STALE", "NO_CURRENT_MATCH", "PARTIAL_MATCH"}:
        return "REBUILD"
    if status == "CURRENT_FULL_MATCH":
        return "REUSE"
    return "INVESTIGATE"


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    active = load_active_universe()
    active_total = len(active)
    bendigo_r6 = active[
        (active["audit_race_date"] == "2026-06-25")
        & (active["audit_track"] == "BENDIGO")
        & (active["audit_race_no"] == "6")
    ].copy()

    audit_rows: list[dict[str, object]] = []

    active_dates = sorted(active["audit_race_date"].dropna().astype(str).unique().tolist())
    active_tracks = sorted(active["audit_track"].dropna().astype(str).unique().tolist())

    for path in TARGETS:
        exists = path.exists()
        row: dict[str, object] = {
            "file": path.name,
            "exists": "YES" if exists else "NO",
            "rows": 0,
            "unique_runner_rows": 0,
            "active_universe_rows": active_total,
            "active_matches": 0,
            "active_match_pct": 0.0,
            "bendigo_r6_active_rows": len(bendigo_r6),
            "bendigo_r6_matches": 0,
            "bendigo_r6_match_pct": 0.0,
            "file_min_race_date": "",
            "file_max_race_date": "",
            "date_coverage": "",
            "track_coverage": "",
            "race_coverage": "",
            "horse_coverage": "",
            "stale_flag": "YES" if not exists else "UNKNOWN",
            "status": "MISSING" if not exists else "UNKNOWN",
            "recommended_action": "REBUILD" if not exists else "INVESTIGATE",
            "notes": "",
            "built_at": built_at,
        }

        if not exists:
            audit_rows.append(row)
            continue

        frame = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
        key_cols = detect_key_columns(frame)

        row["rows"] = len(frame)
        row["notes"] = ""

        if key_cols.race_date is None or key_cols.track is None or key_cols.race_no is None or key_cols.horse is None:
            row["notes"] = "Missing one or more join columns"
            row["stale_flag"] = "YES"
            row["status"] = "JOIN_COLUMNS_MISSING"
            row["recommended_action"] = recommendation(path.name, str(row["status"]))
            audit_rows.append(row)
            continue

        frame["audit_runner_key"] = build_runner_key(frame, key_cols)
        frame["audit_race_date"] = frame.get(key_cols.race_date, pd.Series("", index=frame.index)).map(safe_text).str[:10]
        frame["audit_track"] = frame.get(key_cols.track, pd.Series("", index=frame.index)).map(clean_track)
        frame["audit_race_no"] = frame.get(key_cols.race_no, pd.Series("", index=frame.index)).map(safe_text)
        frame["audit_horse"] = frame.get(key_cols.horse, pd.Series("", index=frame.index)).map(safe_text)

        unique_runners = frame[["audit_runner_key"]].drop_duplicates()
        matched_keys = set(unique_runners["audit_runner_key"]).intersection(set(active["audit_runner_key"]))
        bendigo_matches = set(unique_runners["audit_runner_key"]).intersection(set(bendigo_r6["audit_runner_key"]))

        row["unique_runner_rows"] = len(unique_runners)
        row["active_matches"] = len(matched_keys)
        row["active_match_pct"] = round((len(matched_keys) / active_total) * 100, 2) if active_total else 0.0
        row["bendigo_r6_matches"] = len(bendigo_matches)
        row["bendigo_r6_match_pct"] = round((len(bendigo_matches) / len(bendigo_r6)) * 100, 2) if len(bendigo_r6) else 0.0

        row["file_min_race_date"] = min(frame["audit_race_date"]) if len(frame) else ""
        row["file_max_race_date"] = max(frame["audit_race_date"]) if len(frame) else ""
        row["date_coverage"] = summarize_set(frame["audit_race_date"])
        row["track_coverage"] = summarize_set(frame["audit_track"])
        row["race_coverage"] = str(frame[["audit_race_date", "audit_track", "audit_race_no"]].drop_duplicates().shape[0])
        row["horse_coverage"] = str(frame["audit_runner_key"].nunique())

        has_active_dates = any(date in set(frame["audit_race_date"]) for date in active_dates)
        has_active_tracks = any(track in set(frame["audit_track"]) for track in active_tracks)
        stale_flag = "NO"
        notes: list[str] = []
        if len(matched_keys) == 0:
            stale_flag = "YES"
            notes.append("No active-universe runner joins")
        elif not has_active_dates:
            stale_flag = "YES"
            notes.append("No active dates present")
        elif not has_active_tracks:
            stale_flag = "YES"
            notes.append("No active tracks present")
        elif row["file_max_race_date"] and row["file_max_race_date"] < min(active_dates):
            stale_flag = "YES"
            notes.append("File max date predates active universe")

        row["stale_flag"] = stale_flag
        row["status"] = candidate_status(len(matched_keys), active_total, stale_flag, exists)
        row["recommended_action"] = recommendation(path.name, str(row["status"]))
        row["notes"] = "; ".join(notes)
        audit_rows.append(row)

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT_OUT, index=False)

    summary_rows = [
        {"metric": "status", "value": "EDGEIQ_CURRENT_DNA_UNIVERSE_AUDIT_BUILT"},
        {"metric": "active_universe_rows", "value": active_total},
        {"metric": "bendigo_r6_active_rows", "value": len(bendigo_r6)},
        {"metric": "active_dates", "value": "|".join(active_dates)},
        {"metric": "active_tracks", "value": "|".join(active_tracks)},
        {"metric": "files_audited", "value": len(audit)},
        {"metric": "files_marked_rebuild", "value": int((audit["recommended_action"] == "REBUILD").sum())},
        {"metric": "stale_files", "value": int((audit["stale_flag"] == "YES").sum())},
        {"metric": "best_reusable_file", "value": audit.sort_values(["active_match_pct", "rows"], ascending=[False, False]).iloc[0]["file"] if not audit.empty else ""},
        {"metric": "profile_engine_status", "value": audit.loc[audit["file"] == "edgeiq_runner_profile_engine_current.csv", "status"].iloc[0] if (audit["file"] == "edgeiq_runner_profile_engine_current.csv").any() else ""},
        {"metric": "runner_dna_v62_status", "value": audit.loc[audit["file"] == "edgeiq_live_runner_dna_v6_2.csv", "status"].iloc[0] if (audit["file"] == "edgeiq_live_runner_dna_v6_2.csv").any() else ""},
        {"metric": "drawer_v2_status", "value": audit.loc[audit["file"] == "edgeiq_runner_dna_drawer_feed_v2.csv", "status"].iloc[0] if (audit["file"] == "edgeiq_runner_dna_drawer_feed_v2.csv").any() else ""},
        {"metric": "factor_scorecard_v2_status", "value": audit.loc[audit["file"] == "edgeiq_live_runner_factor_scorecard_v2.csv", "status"].iloc[0] if (audit["file"] == "edgeiq_live_runner_factor_scorecard_v2.csv").any() else ""},
        {"metric": "built_at", "value": built_at},
    ]

    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_CURRENT_DNA_UNIVERSE_AUDIT_V1] COMPLETE")
    print(audit.to_string(index=False))
    print()
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"audit={AUDIT_OUT}")
    print(f"summary={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
