from __future__ import annotations

import csv
import gc
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
MEMORY_HEALTH = DATA / "edgeiq_worker_memory_health_v1.csv"
MEMORY_SUMMARY = DATA / "edgeiq_worker_memory_health_summary_v1.csv"

MEMORY_FIELDS = ["timestamp_utc", "step_name", "memory_mb", "status", "notes"]
SUMMARY_FIELDS = ["metric", "value"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def env_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def current_memory_mb() -> float:
    try:
        import psutil  # type: ignore

        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        pass
    try:
        import resource  # type: ignore

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(usage / 1024, 2)
    except Exception:
        return 0.0


def stream_csv_rows(path: Path | str) -> Iterator[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def count_csv_rows_streaming(path: Path | str) -> int:
    csv_path = Path(path)
    if not csv_path.exists():
        return 0
    count = 0
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for _ in reader:
            count += 1
    return count


def safe_read_csv(path: Path | str, max_rows: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    try:
        for index, row in enumerate(stream_csv_rows(path)):
            if max_rows is not None and index >= max_rows:
                break
            rows.append(row)
    except Exception:
        return []
    return rows


def write_csv_atomic(path: Path | str, rows: Iterable[dict[str, object]], fields: list[str]) -> bool:
    csv_path = Path(path)
    try:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        materialised = list(rows)
        tmp = csv_path.with_name(f"{csv_path.stem}.{os.getpid()}.{int(datetime.now().timestamp() * 1000)}.tmp")
        try:
            with tmp.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(materialised)
            tmp.replace(csv_path)
            return True
        except PermissionError:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(materialised)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            return True
    except Exception:
        return False


def read_memory_health() -> list[dict[str, str]]:
    return safe_read_csv(MEMORY_HEALTH, max_rows=5000)


def write_memory_summary(rows: list[dict[str, str]]) -> bool:
    memory_values = []
    for row in rows:
        try:
            memory_values.append(float(row.get("memory_mb", "0") or 0))
        except ValueError:
            pass
    latest = memory_values[-1] if memory_values else current_memory_mb()
    max_seen = max(memory_values) if memory_values else latest
    research_enabled = "YES" if env_true("EDGEIQ_ENABLE_RESEARCH_PIPELINE") else "NO"
    if max_seen >= float(os.getenv("EDGEIQ_MEMORY_FAIL_MB", "900")):
        status = "FAIL"
    elif max_seen >= float(os.getenv("EDGEIQ_MEMORY_WARN_MB", "650")):
        status = "WARN"
    else:
        status = "OK"
    values = [
        {"metric": "latest_memory_mb", "value": f"{latest:.2f}"},
        {"metric": "max_memory_mb_seen", "value": f"{max_seen:.2f}"},
        {"metric": "research_pipeline_enabled", "value": research_enabled},
        {"metric": "worker_safety_status", "value": status},
    ]
    return write_csv_atomic(MEMORY_SUMMARY, values, SUMMARY_FIELDS)


def log_memory_usage(label: str, status: str = "OK", notes: str = "") -> dict[str, object]:
    row = {
        "timestamp_utc": utc_now(),
        "step_name": label,
        "memory_mb": f"{current_memory_mb():.2f}",
        "status": status,
        "notes": notes,
    }
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        existing = read_memory_health()
        existing.append({key: str(value) for key, value in row.items()})
        existing = existing[-1000:]
        write_csv_atomic(MEMORY_HEALTH, existing, MEMORY_FIELDS)
        write_memory_summary(existing)
    except Exception:
        pass
    return row


def collect_garbage(label: str = "gc") -> dict[str, object]:
    gc.collect()
    return log_memory_usage(label, "OK", "gc.collect completed")
