from __future__ import annotations

import csv
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "-", "n/a"} else text


def num(value: object, default: float = math.nan) -> float:
    try:
        text = clean(value).replace("$", "").replace(",", "").replace("%", "")
        return float(text) if text else default
    except ValueError:
        return default


def boolish(value: object) -> bool:
    return clean(value).upper() in {"1", "Y", "YES", "TRUE", "SCR", "SCRATCHED", "LATE SCR", "WITHDRAWN"}


def canon(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    text = clean(value).upper().replace("RACE", "").replace("R", "")
    digits = re.sub(r"[^0-9]", "", text)
    return str(int(digits)) if digits else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def first(row: dict[str, str] | None, names: list[str]) -> str:
    if row is None:
        return ""
    for name in names:
        if clean(row.get(name)):
            return clean(row.get(name))
    return ""


def runner_key(row: dict[str, str]) -> str:
    track = canon(first(row, ["track", "meeting"]))
    rn = race_no(first(row, ["race_no", "race_number", "race"]))
    horse = canon(first(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"]))
    return "|".join([track, rn, horse])


def build_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        key = runner_key(row)
        if key and key not in lookup:
            lookup[key] = row
    return lookup


def merge_rows(primary: list[dict[str, str]], extras: list[list[dict[str, str]]]) -> list[dict[str, str]]:
    merged = [dict(row) for row in primary]
    extra_maps = [build_lookup(rows) for rows in extras]
    for row in merged:
        key = runner_key(row)
        for mapping in extra_maps:
            extra = mapping.get(key)
            if not extra:
                continue
            for col, value in extra.items():
                if clean(value) and not clean(row.get(col)):
                    row[col] = value
                elif clean(value):
                    row[f"{col}_extra"] = value
    return merged


def file_age_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return round((datetime.now(timezone.utc) - modified).total_seconds(), 1)


def parse_datetime(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone(timedelta(hours=10)))
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone(timedelta(hours=10)))
    except ValueError:
        return None
