
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RacingComSpeedDataParseError(ValueError):
    pass


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def seconds(value: str) -> float | None:
    text = clean(value)
    if not text or text == "00:00:00.000":
        return None
    parts = text.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(text)
    except Exception:
        return None


def fnum(value: Any) -> float | None:
    try:
        text = clean(value)
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def norm_horse(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def parse_metadata(row: list[str]) -> dict[str, str]:
    if len(row) < 5:
        raise RacingComSpeedDataParseError("MISSING_METADATA")
    date_raw, meeting_raw, race_name, race_time, code = [clean(x) for x in row[:5]]
    date_match = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", date_raw)
    if not date_match:
        raise RacingComSpeedDataParseError("BAD_METADATA_DATE")
    race_date = f"{int(date_match.group(3)):04d}-{int(date_match.group(2)):02d}-{int(date_match.group(1)):02d}"
    track = clean(meeting_raw.split("-Professional-")[0] if "-Professional-" in meeting_raw else meeting_raw)
    distance_match = re.search(r"_(\d+)m", code, re.I)
    distance = distance_match.group(1) if distance_match else ""
    return {"race_date": race_date, "track": track, "race_name": race_name, "race_time": race_time, "distance": distance, "metadata_code": code}


def parse_speed_csv(path: Path, source_url: str = "", race_id: str = "") -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    body = path.read_text(encoding="utf-8-sig", errors="replace")
    stripped = body.lstrip()
    if not stripped:
        raise RacingComSpeedDataParseError("EMPTY_CSV")
    low = stripped[:500].lower()
    if low.startswith("<!doctype") or "<html" in low:
        raise RacingComSpeedDataParseError("HTML_BODY")
    rows = list(csv.reader(body.splitlines(), delimiter=";"))
    if not rows:
        raise RacingComSpeedDataParseError("EMPTY_CSV")
    meta = parse_metadata(rows[0])
    parsed: list[dict[str, str]] = []
    rejects: list[dict[str, str]] = []
    seen: set[str] = set()
    for line_no, row in enumerate(rows[1:], start=2):
        if len(row) < 5:
            rejects.append({"line_no": str(line_no), "reason": "MALFORMED_ROW", "raw": ";".join(row)})
            continue
        horse = clean(row[0])
        barrier = clean(row[1])
        if not horse:
            rejects.append({"line_no": str(line_no), "reason": "MISSING_HORSE", "raw": ";".join(row)})
            continue
        key = norm_horse(horse)
        if key in seen:
            rejects.append({"line_no": str(line_no), "reason": "DUPLICATE_RUNNER", "raw": ";".join(row)})
            continue
        seen.add(key)
        markers = []
        speeds = []
        splits = []
        triplets = row[2:]
        for idx in range(0, len(triplets) - 2, 3):
            marker = clean(triplets[idx])
            speed = fnum(triplets[idx + 1])
            split = seconds(triplets[idx + 2])
            if not marker:
                continue
            markers.append(marker)
            if speed and speed > 0:
                speeds.append(speed)
            if split and split > 0:
                splits.append(split)
        third = max(1, len(speeds) // 3) if speeds else 1
        early = speeds[:third]
        mid = speeds[third:third*2]
        late = speeds[third*2:]
        def avg(values: list[float]) -> str:
            return f"{sum(values)/len(values):.3f}" if values else ""
        def split_sum(n: int) -> str:
            return f"{sum(splits[-n:]):.2f}" if len(splits) >= n else ""
        parsed.append({
            "horse": horse,
            "horse_key": key,
            "race_date": meta["race_date"],
            "track": meta["track"],
            "state": "VIC",
            "race_no": re.search(r"_R(\d+)$", race_id).group(1) if re.search(r"_R(\d+)$", race_id) else "",
            "distance": meta["distance"],
            "barrier": barrier,
            "last200": split_sum(1),
            "last400": split_sum(2),
            "last600": split_sum(3),
            "last_200": split_sum(1),
            "last_400": split_sum(2),
            "last_600": split_sum(3),
            "early_speed": avg(early),
            "mid_speed": avg(mid),
            "late_speed": avg(late),
            "peak_speed": f"{max(speeds):.3f}" if speeds else "",
            "avg_speed": avg(speeds),
            "race_time": meta["race_time"],
            "tempo_grade": "STANDARD_LAST600" if split_sum(3) else "NO_SECTIONAL_VALUES" if not speeds and not splits else "STANDARD_SPEED_ONLY",
            "pace_profile": "",
            "sectional_source": "RACING.COM_DIRECT_CSV_V2",
            "source_url": source_url,
            "source_cache_path": str(path),
            "parser_version": "racingcom_speed_data_parser_v2",
        })
    return parsed, rejects
