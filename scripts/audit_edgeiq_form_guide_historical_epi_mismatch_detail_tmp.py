import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "full-product-implementation"

FORM = DATA / "edgeiq_form_guide_enriched_v2.json"
HIST = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"

OUT_TXT = DOCS / "FORM_GUIDE_HISTORICAL_EPI_MISMATCH_DETAIL_AUDIT.txt"
OUT_CSV = DOCS / "FORM_GUIDE_HISTORICAL_EPI_MISMATCH_DETAIL_AUDIT.csv"


def text(value: Any) -> str:
    if value is None:
        return ""
    output = str(value).strip()
    if output.lower() in {"", "-", "none", "null", "undefined", "n/a", "na"}:
        return ""
    return output


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def horse_key(value: Any) -> str:
    output = norm(value)

    # Remove common country suffixes only when attached to a longer name.
    for suffix in ("AUS", "NZ", "GB", "IRE", "USA", "FR", "JPN"):
        if output.endswith(suffix) and len(output) > len(suffix) + 2:
            output = output[:-len(suffix)]

    return output


def distance_key(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""

    match = re.search(r"\d+(?:\.\d+)?", raw.replace(",", ""))
    if not match:
        return norm(raw)

    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else str(number)


def date_key(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""

    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return raw


def numeric_distance(value: Any) -> float | None:
    try:
        return float(distance_key(value))
    except (TypeError, ValueError):
        return None


def date_difference_days(left: str, right: str) -> int | None:
    try:
        left_date = datetime.strptime(left, "%Y-%m-%d")
        right_date = datetime.strptime(right, "%Y-%m-%d")
        return abs((left_date - right_date).days)
    except ValueError:
        return None


with FORM.open(encoding="utf-8") as handle:
    form_payload = json.load(handle)

with HIST.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
    research_rows = list(csv.DictReader(handle))


by_full: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
by_horse_date_distance: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
by_horse_date_track: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
by_horse_track_distance: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)

for row in research_rows:
    horse = horse_key(row.get("horse"))
    date = date_key(row.get("race_date"))
    track = norm(row.get("track"))
    distance = distance_key(row.get("distance"))

    by_full[(horse, date, track, distance)].append(row)
    by_horse_date_distance[(horse, date, distance)].append(row)
    by_horse_date_track[(horse, date, track)].append(row)
    by_horse_track_distance[(horse, track, distance)].append(row)
    by_horse[horse].append(row)


records: list[dict[str, Any]] = []
counts = Counter()
track_pairs = Counter()
distance_pairs = Counter()
date_offsets = Counter()

for race in form_payload.get("races", []) or []:
    current_meeting = text(race.get("meeting"))
    current_race_date = date_key(race.get("raceDate"))
    current_race_number = text(race.get("raceNumber"))

    for runner in race.get("runners", []) or []:
        runner_name = text(
            runner.get("runnerName")
            or runner.get("runner")
            or runner.get("horse")
            or runner.get("name")
        )
        horse = horse_key(runner_name)

        for run_index, run in enumerate(runner.get("fullForm", []) or [], start=1):
            form_date = date_key(run.get("date") or run.get("raceDate"))
            form_track_raw = text(run.get("track"))
            form_track = norm(form_track_raw)
            form_distance_raw = text(run.get("distance"))
            form_distance = distance_key(form_distance_raw)

            full_key = (horse, form_date, form_track, form_distance)

            category = ""
            candidates: list[dict[str, str]] = []

            if by_full.get(full_key):
                category = "FULL_MATCH"
                candidates = by_full[full_key]

            elif by_horse_date_distance.get((horse, form_date, form_distance)):
                category = "TRACK_ONLY"
                candidates = by_horse_date_distance[(horse, form_date, form_distance)]

            elif by_horse_date_track.get((horse, form_date, form_track)):
                category = "DISTANCE_ONLY"
                candidates = by_horse_date_track[(horse, form_date, form_track)]

            elif by_horse_track_distance.get((horse, form_track, form_distance)):
                category = "DATE_ONLY"
                candidates = by_horse_track_distance[(horse, form_track, form_distance)]

            elif by_horse.get(horse):
                category = "NAME_ONLY"
                candidates = by_horse[horse]

            else:
                category = "HORSE_NOT_PRESENT"

            counts[category] += 1

            if category == "FULL_MATCH":
                continue

            candidate_tracks = sorted(
                {text(row.get("track")) for row in candidates if text(row.get("track"))}
            )
            candidate_distances = sorted(
                {distance_key(row.get("distance")) for row in candidates if distance_key(row.get("distance"))},
                key=lambda value: float(value) if value.replace(".", "", 1).isdigit() else 999999,
            )
            candidate_dates = sorted(
                {date_key(row.get("race_date")) for row in candidates if date_key(row.get("race_date"))}
            )

            nearest_rows: list[dict[str, str]] = []

            if category == "NAME_ONLY":
                scored = []

                for candidate in candidates:
                    source_date = date_key(candidate.get("race_date"))
                    source_track = norm(candidate.get("track"))
                    source_distance = distance_key(candidate.get("distance"))

                    date_gap = date_difference_days(form_date, source_date)
                    form_distance_number = numeric_distance(form_distance)
                    source_distance_number = numeric_distance(source_distance)

                    distance_gap = (
                        abs(form_distance_number - source_distance_number)
                        if form_distance_number is not None and source_distance_number is not None
                        else 999999
                    )

                    track_penalty = 0 if source_track == form_track else 1

                    score = (
                        date_gap if date_gap is not None else 999999,
                        track_penalty,
                        distance_gap,
                    )

                    scored.append((score, candidate))

                scored.sort(key=lambda item: item[0])
                nearest_rows = [row for _, row in scored[:3]]

            else:
                nearest_rows = candidates[:3]

            nearest_summary = " | ".join(
                (
                    f"{text(row.get('race_date'))}"
                    f" / {text(row.get('track'))}"
                    f" / {text(row.get('distance'))}"
                    f" / EPI={text(row.get('performance_rating_v6_1_research'))}"
                    f" / source={text(row.get('source_file'))}"
                )
                for row in nearest_rows
            )

            if category == "TRACK_ONLY":
                for source_track in candidate_tracks:
                    track_pairs[(form_track_raw, source_track)] += 1

            if category == "DISTANCE_ONLY":
                for source_distance in candidate_distances:
                    distance_pairs[(form_distance, source_distance)] += 1

            if category == "DATE_ONLY":
                for source_date in candidate_dates:
                    offset = date_difference_days(form_date, source_date)
                    if offset is not None:
                        date_offsets[offset] += 1

            records.append(
                {
                    "category": category,
                    "current_meeting": current_meeting,
                    "current_race_date": current_race_date,
                    "current_race_number": current_race_number,
                    "runner": runner_name,
                    "historical_run_index": run_index,
                    "form_date": form_date,
                    "form_track": form_track_raw,
                    "form_track_key": form_track,
                    "form_distance": form_distance,
                    "research_candidate_count": len(candidates),
                    "research_tracks": " | ".join(candidate_tracks[:20]),
                    "research_distances": " | ".join(candidate_distances[:20]),
                    "research_dates": " | ".join(candidate_dates[:20]),
                    "nearest_research_rows": nearest_summary,
                }
            )


OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

fieldnames = [
    "category",
    "current_meeting",
    "current_race_date",
    "current_race_number",
    "runner",
    "historical_run_index",
    "form_date",
    "form_track",
    "form_track_key",
    "form_distance",
    "research_candidate_count",
    "research_tracks",
    "research_distances",
    "research_dates",
    "nearest_research_rows",
]

with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)


lines = [
    "EDGEIQ FORM GUIDE HISTORICAL EPI MISMATCH DETAIL AUDIT",
    "=" * 92,
    "",
    "CLASSIFICATION",
    "-" * 92,
]

for category in (
    "FULL_MATCH",
    "TRACK_ONLY",
    "DISTANCE_ONLY",
    "DATE_ONLY",
    "NAME_ONLY",
    "HORSE_NOT_PRESENT",
):
    lines.append(f"{category}={counts[category]}")

lines.extend(
    [
        "",
        "TOP TRACK-ONLY MAPPINGS",
        "-" * 92,
    ]
)

for (form_track, source_track), count in track_pairs.most_common(100):
    lines.append(f"{count:>5} | {form_track} -> {source_track}")

lines.extend(
    [
        "",
        "TOP DISTANCE-ONLY DIFFERENCES",
        "-" * 92,
    ]
)

for (form_distance, source_distance), count in distance_pairs.most_common(100):
    try:
        difference = float(form_distance) - float(source_distance)
        difference_text = f"{difference:+g}m"
    except ValueError:
        difference_text = "UNKNOWN"

    lines.append(
        f"{count:>5} | FORM={form_distance} SOURCE={source_distance} DIFF={difference_text}"
    )

lines.extend(
    [
        "",
        "DATE-ONLY ABSOLUTE OFFSETS",
        "-" * 92,
    ]
)

for offset, count in date_offsets.most_common(100):
    lines.append(f"{count:>5} | {offset} day(s)")

lines.extend(
    [
        "",
        "NAME-ONLY SAMPLE WITH NEAREST RESEARCH ROWS",
        "-" * 92,
    ]
)

name_only_records = [row for row in records if row["category"] == "NAME_ONLY"]

for row in name_only_records[:100]:
    lines.append(
        f"{row['runner']} | "
        f"{row['form_date']} | "
        f"{row['form_track']} | "
        f"{row['form_distance']} | "
        f"candidates={row['research_candidate_count']}"
    )
    lines.append(f"  nearest={row['nearest_research_rows']}")

lines.extend(
    [
        "",
        f"DETAIL_CSV={OUT_CSV}",
        "",
        "EDGEIQ_FORM_GUIDE_HISTORICAL_EPI_MISMATCH_DETAIL_AUDIT_PASS",
    ]
)

OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print()
print(f"WROTE_TXT={OUT_TXT}")
print(f"WROTE_CSV={OUT_CSV}")
