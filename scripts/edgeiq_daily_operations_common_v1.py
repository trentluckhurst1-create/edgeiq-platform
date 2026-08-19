from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "daily-operations-engine-v1"
CONFIG_PATH = ROOT / "config" / "edgeiq_daily_operations_v1.json"
BUILDER_VERSION = "EDGEIQ_DAILY_OPERATIONS_ENGINE_V1"
CONTRACT_VERSION = "1.0.0"
TZ = ZoneInfo("Australia/Sydney")

DATE_MODES = {"PREVIOUS_DAY", "RECENT_BACKFILL", "DEEP_BACKFILL", "CURRENT_DAY_REFRESH", "SPEED_PENDING_REFRESH", "RESULT_PENDING_REFRESH", "CORRECTION_REFRESH", "DAILY", "CURRENT_DAY", "RESULTS_ONLY", "SPEED_ONLY", "BACKFILL", "PERFORMANCE_REFRESH_ONLY", "HEALTH_CHECK", "DRY_RUN", "FULL_REBUILD"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def now_local_date() -> date:
    return datetime.now(TZ).date()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def norm_track(value: object) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def row_sha(row: dict[str, object]) -> str:
    payload = json.dumps({k: clean(row.get(k)) for k in sorted(row)}, sort_keys=True, separators=(",", ":"))
    return sha_text(payload)


def key_hash(parts: list[object], n: int = 16) -> str:
    return sha_text("\x1f".join(clean(p) for p in parts))[:n].upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    csv.field_size_limit(min(sys.maxsize, 2147483647))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def write_csv_atomic(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: clean(row.get(field)) for field in fields})
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def parse_date(value: str | None) -> date | None:
    raw = clean(value)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def resolve_date_window(args: argparse.Namespace) -> tuple[date, date, str]:
    mode = clean(getattr(args, "mode", "DAILY")).upper() or "DAILY"
    today = now_local_date()
    explicit = parse_date(getattr(args, "date", None))
    start = parse_date(getattr(args, "date_from", None))
    end = parse_date(getattr(args, "date_to", None))
    lookback = int(getattr(args, "lookback_days", 14) or 14)
    if mode in {"DAILY", "PREVIOUS_DAY", "RESULTS_ONLY"}:
        d = explicit or (today - timedelta(days=1))
        return d, d, "PREVIOUS_DAY"
    if mode in {"CURRENT_DAY", "CURRENT_DAY_REFRESH"}:
        d = explicit or today
        return d, d, "CURRENT_DAY_REFRESH"
    if mode in {"BACKFILL", "RECENT_BACKFILL", "SPEED_ONLY", "SPEED_PENDING_REFRESH", "RESULT_PENDING_REFRESH", "CORRECTION_REFRESH"}:
        return start or (today - timedelta(days=lookback)), end or (today - timedelta(days=1)), "RECENT_BACKFILL"
    if mode == "DEEP_BACKFILL":
        if not start or not end:
            raise SystemExit("DEEP_BACKFILL requires --date-from and --date-to")
        return start, end, "DEEP_BACKFILL"
    if mode in {"DRY_RUN", "HEALTH_CHECK"}:
        d = explicit or (today - timedelta(days=1))
        return d, d, mode
    return start or (explicit or (today - timedelta(days=1))), end or (explicit or (today - timedelta(days=1))), mode


def add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--mode", default="DAILY")
    parser.add_argument("--date", default="")
    parser.add_argument("--date-from", dest="date_from", default="")
    parser.add_argument("--date-to", dest="date_to", default="")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--state", default="VIC")
    parser.add_argument("--track", default="")
    parser.add_argument("--meeting-id", default="")
    parser.add_argument("--race-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-recheck", action="store_true")
    parser.add_argument("--no-publish", action="store_true")
    parser.add_argument("--output-root", default=str(DATA))
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--fixture-root", default="")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--resume-run-id", default="")
    return parser


def operation_run_id(prefix: str, start: date, end: date) -> str:
    return f"{prefix}-{start.isoformat()}-{end.isoformat()}-{key_hash([prefix, start.isoformat(), end.isoformat(), now_utc()], 10)}"


def canonical_meeting_id(meeting_date: object, track: object) -> str:
    return "EIQM-" + key_hash([meeting_date, norm_track(track)], 24)


def canonical_race_id(race_date: object, track: object, race_no: object, distance: object = "") -> str:
    return "EIQD-" + key_hash([race_date, norm_track(track), race_no, distance], 24)


def race_key(race_date: object, track: object, race_no: object) -> str:
    return f"{clean(race_date)}|{norm_track(track)}|R{clean(race_no).replace('R','').zfill(2)}"


def first(row: dict[str, str], names: list[str], default: str = "") -> str:
    lower = {k.lower(): v for k, v in row.items()}
    for name in names:
        if name in row and clean(row.get(name)):
            return clean(row.get(name))
        if name.lower() in lower and clean(lower.get(name.lower())):
            return clean(lower.get(name.lower()))
    return default


def in_window(row: dict[str, str], start: date, end: date, field_names: list[str] | None = None) -> bool:
    for name in field_names or ["race_date", "meeting_date", "date"]:
        d = parse_date(first(row, [name]))
        if d and start <= d <= end:
            return True
    return False


def manifest_status(path: Path, payload: dict) -> None:
    write_json_atomic(path, payload)


def rows_by_key(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        k = clean(row.get(key))
        if k:
            out[k] = row
    return out


def acquire_lock(lock_path: Path, mode: str, allow_read_only: bool = False) -> dict:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists() and not allow_read_only:
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {"raw": lock_path.read_text(encoding="utf-8", errors="ignore")}
        pid = existing.get("process_id")
        if pid:
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue"], capture_output=True, text=True, timeout=10)
                # PowerShell command itself is not sufficient to clear an active lock; never auto-clear here.
            except Exception:
                pass
        raise SystemExit(f"EDGEIQ_DAILY_OPERATIONS_LOCK_EXISTS:{lock_path}")
    payload = {"operation_run_id": f"LOCK-{key_hash([mode, now_utc(), os.getpid()], 12)}", "started_at_utc": now_utc(), "host": socket.gethostname(), "process_id": os.getpid(), "mode": mode}
    write_json_atomic(lock_path, payload)
    return payload


def release_lock(lock_path: Path, lock: dict) -> None:
    if lock_path.exists():
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
            if existing.get("process_id") == lock.get("process_id"):
                lock_path.unlink()
        except Exception:
            pass


def count_rows(path: Path) -> int:
    if not path.exists(): return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def stage_checkpoint(run_id: str, stage: str, status: str, inputs: dict, outputs: dict, exception: str = "", retryable: bool = False, promoted: bool = False, rollback_path: str = "", next_stage: str = "") -> None:
    path = DATA / "edgeiq_daily_operations_checkpoint_fact_v1.csv"
    fields = ["operation_run_id","stage","status","timestamp_utc","input_hashes","output_hashes","input_rows","output_rows","rejected_rows","exception","retryable","promoted","rollback_path","next_stage","builder_version"]
    prior = read_csv(path)
    row = {
        "operation_run_id": run_id,
        "stage": stage,
        "status": status,
        "timestamp_utc": now_utc(),
        "input_hashes": json.dumps(inputs.get("hashes", {}), sort_keys=True),
        "output_hashes": json.dumps(outputs.get("hashes", {}), sort_keys=True),
        "input_rows": json.dumps(inputs.get("rows", {}), sort_keys=True),
        "output_rows": json.dumps(outputs.get("rows", {}), sort_keys=True),
        "rejected_rows": clean(outputs.get("rejected_rows", "0")),
        "exception": exception,
        "retryable": str(bool(retryable)).upper(),
        "promoted": str(bool(promoted)).upper(),
        "rollback_path": rollback_path,
        "next_stage": next_stage,
        "builder_version": BUILDER_VERSION,
    }
    prior.append(row)
    write_csv_atomic(path, prior, fields)
