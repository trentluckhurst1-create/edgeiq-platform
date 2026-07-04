from __future__ import annotations

import csv
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY_PATH = DATA / "edgeiq_price_truth_history_v1.csv"
PREVIEW_PATH = DATA / "racing_australia_settlement_preview_v1.csv"
BACKUP_DIR = DATA / "backups"
AUDIT_PATH = DATA / "edgeiq_price_truth_settlement_v1_audit.csv"

SAFE_SETTLEMENT_STATUSES = {"FINAL", "FAILED_TO_FINISH", "CONFIRMED_SCRATCHED"}
RESULT_COLUMNS = ["result_status", "finish_position", "won", "starting_price", "settlement_source"]

AUDIT_COLUMNS = ["section", "metric", "value", "source_path", "notes", "built_at"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def clean(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("&", " AND ")
    text = re.sub(r"['`]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def horse_key(value: object) -> str:
    return normalise_text(value).replace(" ", "")


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bSPORTS\s*BET\b", "SPORTSBET", track)
    track = re.sub(r"\bVIC\b|\bPROFESSIONAL\b|\bMETRO\b|\bTAB\b|\bMEETING\b", " ", track)
    track = re.sub(r"\bMELBOURNE\b|\bRACING\b|\bCLUB\b", " ", track)
    track = re.sub(r"\s+", " ", track).strip()
    if "SANDOWN" in track and "LAKESIDE" in track:
        return "SANDOWN LAKESIDE"
    if track.startswith("SPORTSBET "):
        track = track.replace("SPORTSBET ", "", 1)
    return track


def clean_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def settlement_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            clean(row.get("race_date")),
            normalise_track(row.get("track")),
            clean_race_no(row.get("race_no")),
            horse_key(row.get("horse_key")) or horse_key(row.get("horse")),
        ]
    )


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def audit_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_preview_index(preview_rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], list[str]]:
    index: dict[str, dict[str, str]] = {}
    duplicate_keys: list[str] = []
    for row in preview_rows:
        key = settlement_key(row)
        if key in index:
            duplicate_keys.append(key)
        index[key] = row
    return index, duplicate_keys


def preview_is_ready(preview_rows: list[dict[str, str]], duplicate_keys: list[str]) -> tuple[bool, str]:
    if len(preview_rows) != 87:
        return False, f"preview row count is {len(preview_rows)}, expected 87"
    if duplicate_keys:
        return False, f"preview has duplicate settlement keys: {duplicate_keys[:5]}"
    statuses = {clean(row.get("result_status")) for row in preview_rows}
    unsafe = sorted(status for status in statuses if status not in SAFE_SETTLEMENT_STATUSES)
    if unsafe:
        return False, f"preview contains unsafe statuses: {unsafe}"
    blockers = [row for row in preview_rows if clean(row.get("settlement_blocker"))]
    if blockers:
        return False, f"preview still has settlement blockers: {len(blockers)}"
    return True, "preview has 87 unique rows and only safe terminal statuses"


def settlement_values(preview_row: dict[str, str]) -> dict[str, str]:
    status = clean(preview_row.get("result_status"))
    if status == "FINAL":
        finish_position = clean(preview_row.get("finish_position"))
        won = "TRUE" if finish_position == "1" else "FALSE"
        return {
            "result_status": "FINAL",
            "finish_position": finish_position,
            "won": won,
            "starting_price": clean(preview_row.get("starting_price")),
            "settlement_source": "Racing Australia",
        }
    if status == "FAILED_TO_FINISH":
        return {
            "result_status": "FAILED_TO_FINISH",
            "finish_position": "FF",
            "won": "FALSE",
            "starting_price": clean(preview_row.get("starting_price")),
            "settlement_source": "Racing Australia",
        }
    if status == "CONFIRMED_SCRATCHED":
        return {
            "result_status": "CONFIRMED_SCRATCHED",
            "finish_position": "SCR",
            "won": "FALSE",
            "starting_price": "",
            "settlement_source": "USER_VERIFIED_OFFICIAL_RACING_AUSTRALIA_PAGE",
        }
    raise ValueError(f"Unsupported settlement status: {status}")


def create_backup() -> Path:
    if not HISTORY_PATH.exists():
        raise FileNotFoundError(f"History file not found: {HISTORY_PATH}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"edgeiq_price_truth_history_v1_before_settlement_{timestamp_for_filename()}.csv"
    shutil.copy2(HISTORY_PATH, backup_path)
    return backup_path


def apply_settlement(
    history_rows: list[dict[str, str]],
    preview_index: dict[str, dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    updated_rows: list[dict[str, str]] = []
    history_keys = Counter(settlement_key(row) for row in history_rows)
    matched_preview_keys: set[str] = set()
    updated_status_counts: Counter[str] = Counter()
    updated_snapshots: set[str] = set()
    updated_races: set[str] = set()
    updated_runners: set[str] = set()
    rows_updated = 0
    unmatched_history_rows = 0

    for row in history_rows:
        key = settlement_key(row)
        preview_row = preview_index.get(key)
        if not preview_row:
            unmatched_history_rows += 1
            updated_rows.append(row)
            continue
        values = settlement_values(preview_row)
        for column, value in values.items():
            row[column] = value
        rows_updated += 1
        matched_preview_keys.add(key)
        updated_status_counts[values["result_status"]] += 1
        updated_snapshots.add(clean(row.get("snapshot_timestamp")))
        updated_races.add("|".join([clean(row.get("race_date")), normalise_track(row.get("track")), clean_race_no(row.get("race_no"))]))
        updated_runners.add(key)
        updated_rows.append(row)

    unmatched_settlement_keys = sorted(set(preview_index).difference(history_keys))
    stats: dict[str, object] = {
        "rows_updated": rows_updated,
        "snapshots_updated": len(updated_snapshots),
        "races_updated": len(updated_races),
        "runners_updated": len(updated_runners),
        "unmatched_history_rows": unmatched_history_rows,
        "unmatched_settlement_rows": len(unmatched_settlement_keys),
        "unmatched_settlement_keys": " | ".join(unmatched_settlement_keys[:20]),
        "FINAL_rows_updated": updated_status_counts.get("FINAL", 0),
        "FAILED_TO_FINISH_rows_updated": updated_status_counts.get("FAILED_TO_FINISH", 0),
        "CONFIRMED_SCRATCHED_rows_updated": updated_status_counts.get("CONFIRMED_SCRATCHED", 0),
        "matched_preview_keys": len(matched_preview_keys),
    }
    return updated_rows, stats


def main() -> None:
    history_fieldnames, history_rows = read_csv(HISTORY_PATH)
    preview_fieldnames, preview_rows = read_csv(PREVIEW_PATH)

    required_history = {"race_date", "track", "race_no", "horse", "horse_key", *RESULT_COLUMNS}
    required_preview = {"race_date", "track", "race_no", "horse", "horse_key", "result_status", "finish_position", "won", "starting_price"}
    missing_history = sorted(required_history.difference(history_fieldnames))
    missing_preview = sorted(required_preview.difference(preview_fieldnames))
    if missing_history:
        raise ValueError(f"History file missing required columns: {missing_history}")
    if missing_preview:
        raise ValueError(f"Settlement preview missing required columns: {missing_preview}")

    preview_index, duplicate_preview_keys = build_preview_index(preview_rows)
    ready, readiness_note = preview_is_ready(preview_rows, duplicate_preview_keys)
    backup_created = False
    backup_path = Path("")
    write_status = "SETTLEMENT_WRITE_FAIL"
    stats: dict[str, object] = {
        "rows_updated": 0,
        "snapshots_updated": 0,
        "races_updated": 0,
        "runners_updated": 0,
        "unmatched_history_rows": len(history_rows),
        "unmatched_settlement_rows": len(preview_rows),
        "unmatched_settlement_keys": "",
        "FINAL_rows_updated": 0,
        "FAILED_TO_FINISH_rows_updated": 0,
        "CONFIRMED_SCRATCHED_rows_updated": 0,
        "matched_preview_keys": 0,
    }

    if ready:
        backup_path = create_backup()
        backup_created = backup_path.exists()
        updated_rows, stats = apply_settlement(history_rows, preview_index)
        if backup_created and stats["unmatched_settlement_rows"] == 0 and stats["rows_updated"] > 0:
            write_csv(HISTORY_PATH, updated_rows, history_fieldnames)
            write_status = "SETTLEMENT_WRITE_PASS"

    audit_rows = [
        audit_row("input", "history_rows_loaded", len(history_rows), HISTORY_PATH),
        audit_row("input", "settlement_preview_rows_loaded", len(preview_rows), PREVIEW_PATH),
        audit_row("backup", "backup_created", "YES" if backup_created else "NO", backup_path),
        audit_row("write", "rows_updated", stats["rows_updated"], HISTORY_PATH),
        audit_row("write", "snapshots_updated", stats["snapshots_updated"], HISTORY_PATH),
        audit_row("write", "races_updated", stats["races_updated"], HISTORY_PATH),
        audit_row("write", "runners_updated", stats["runners_updated"], HISTORY_PATH),
        audit_row("write", "unmatched_history_rows", stats["unmatched_history_rows"], HISTORY_PATH),
        audit_row("write", "unmatched_settlement_rows", stats["unmatched_settlement_rows"], PREVIEW_PATH, str(stats["unmatched_settlement_keys"])),
        audit_row("write", "FINAL_rows_updated", stats["FINAL_rows_updated"], HISTORY_PATH),
        audit_row("write", "FAILED_TO_FINISH_rows_updated", stats["FAILED_TO_FINISH_rows_updated"], HISTORY_PATH),
        audit_row("write", "CONFIRMED_SCRATCHED_rows_updated", stats["CONFIRMED_SCRATCHED_rows_updated"], HISTORY_PATH),
        audit_row("readiness", "settlement_ready_before_write", "TRUE" if ready else "FALSE", PREVIEW_PATH, readiness_note),
        audit_row("status", "settlement_write_status", write_status, AUDIT_PATH),
    ]
    write_csv(AUDIT_PATH, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("EDGEIQ PRICE TRUTH SETTLEMENT V1")
    print("=" * 96)
    for row in audit_rows:
        print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {HISTORY_PATH if write_status == 'SETTLEMENT_WRITE_PASS' else 'NO_HISTORY_WRITE'}")
    print(f"wrote: {AUDIT_PATH}")
    print("=" * 96)


if __name__ == "__main__":
    main()
