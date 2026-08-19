from __future__ import annotations

import csv
from pathlib import Path

from edgeiq_results_common_v1 import (
    CANONICAL_FIELDS,
    DATA,
    SECTIONAL_SOURCES,
    SPEED_RAW_FIELDS,
    canonical_from_row,
    completion_score,
    first,
    has_value,
    key_for,
    now_iso,
    read_csv,
    source_paths,
    write_csv,
)


OUTPUT = DATA / "edgeiq_results_master_v1.csv"
SUMMARY = DATA / "edgeiq_results_master_summary_v1.csv"


def build_sectional_lookup() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for name in SECTIONAL_SOURCES:
        path = DATA / name
        if not path.exists():
            continue
        for row in read_csv(path):
            date = first(row, ["race_date", "meeting_date", "run_date"])
            track = first(row, ["track"])
            race_no = first(row, ["race_no", "race"])
            runner = first(row, ["horse", "horse_name", "horseName", "runner"])
            if not (date and track and race_no and runner):
                continue
            key = key_for(date, track, race_no, runner)
            sectionals = {
                "sectional_800": first(row, ["sectional_800", "last_800", "early_speed"]),
                "sectional_600": first(row, ["sectional_600", "last_600", "mid_speed"]),
                "sectional_400": first(row, ["sectional_400", "last_400", "late_speed"]),
                "sectional_200": first(row, ["sectional_200", "last_200", "peak_speed"]),
                "sectional_finish": first(row, ["sectional_finish", "avg_speed", "sectional_score"]),
                "source_file": name,
            }
            if any(has_value(value) for field, value in sectionals.items() if field != "source_file"):
                existing = lookup.get(key, {})
                if sum(has_value(v) for v in sectionals.values()) > sum(has_value(v) for v in existing.values()):
                    lookup[key] = sectionals
    return lookup


def build_speed_lookup() -> tuple[dict[str, dict[str, str]], dict[tuple[str, str, str, str], dict[str, str]]]:
    path = DATA / "edgeiq_speed_master_v1.csv"
    by_runner: dict[str, dict[str, str]] = {}
    by_runner_no: dict[tuple[str, str, str, str], dict[str, str]] = {}
    if not path.exists():
        return by_runner, by_runner_no
    for row in read_csv(path):
        key = key_for(row.get("race_date", ""), row.get("track", ""), row.get("race_no", ""), row.get("runner", ""))
        if key and any(has_value(row.get(field, "")) for field in SPEED_RAW_FIELDS):
            existing = by_runner.get(key)
            if existing is None or speed_score(row) > speed_score(existing):
                by_runner[key] = row
            runner_no = row.get("runner_no", "")
            if runner_no:
                by_runner_no[(row.get("race_date", ""), row.get("normalized_track", ""), row.get("race_no", ""), runner_no)] = row
    return by_runner, by_runner_no


def speed_score(row: dict[str, str]) -> int:
    return sum(1 for field in SPEED_RAW_FIELDS if has_value(row.get(field, "")))


def apply_speed(canonical: dict[str, object], speed: dict[str, str]) -> None:
    canonical["speed_available"] = "YES"
    canonical["speed_source_file"] = speed.get("source_file", "")
    canonical["speed_source_columns_used"] = speed.get("source_columns_used", "")
    canonical["sectional_source_type"] = speed.get("sectional_source_type", "")
    for field in SPEED_RAW_FIELDS:
        if not has_value(canonical.get(field, "")) and has_value(speed.get(field, "")):
            canonical[field] = speed[field]
    if any(has_value(canonical.get(field, "")) for field in SPEED_RAW_FIELDS):
        canonical["sectional_status"] = "SPEED_AVAILABLE"


def main() -> None:
    built_at = now_iso()
    best: dict[str, dict[str, object]] = {}
    seen_rows = 0
    source_counts: dict[str, int] = {}
    sectional_lookup = build_sectional_lookup()
    speed_lookup, speed_by_runner_no = build_speed_lookup()

    for path, priority in source_paths():
        source_counts[path.name] = 0
        for row in read_csv(path):
            seen_rows += 1
            canonical = canonical_from_row(row, path.name, priority, built_at)
            if canonical is None:
                continue
            source_counts[path.name] += 1
            key = key_for(canonical["race_date"], canonical["track"], canonical["race_no"], canonical["runner"])
            sectionals = sectional_lookup.get(key)
            if sectionals:
                for field in ["sectional_800", "sectional_600", "sectional_400", "sectional_200", "sectional_finish"]:
                    if not has_value(canonical.get(field, "")) and has_value(sectionals.get(field, "")):
                        canonical[field] = sectionals[field]
                canonical["sectional_status"] = "CAPTURED"
            speed = speed_lookup.get(key)
            if speed is None:
                runner_no = str(canonical.get("runner_no", ""))
                speed = speed_by_runner_no.get((str(canonical.get("race_date", "")), str(canonical.get("normalized_track", "")), str(canonical.get("race_no", "")), runner_no))
            if speed:
                apply_speed(canonical, speed)
            current = best.get(key)
            if current is None:
                best[key] = canonical
                continue
            candidate_score = completion_score(canonical) * 10 + int(canonical["source_priority"])
            current_score = completion_score(current) * 10 + int(current["source_priority"])
            if candidate_score > current_score:
                best[key] = canonical

    rows = sorted(best.values(), key=lambda row: (str(row["race_date"]), str(row["normalized_track"]), int(row["race_no"]) if str(row["race_no"]).isdigit() else 999, str(row["normalized_runner"])))
    write_csv(OUTPUT, rows, CANONICAL_FIELDS)

    dates = [str(row["race_date"]) for row in rows if row.get("race_date")]
    races = {row["race_key"] for row in rows if row.get("race_key")}
    meetings = {row["meeting_key"] for row in rows if row.get("meeting_key")}
    summary = [{
        "input_rows_scanned": seen_rows,
        "results_master_rows": len(rows),
        "first_date": min(dates) if dates else "",
        "last_date": max(dates) if dates else "",
        "unique_meetings": len(meetings),
        "unique_races": len(races),
        "source_counts": ";".join(f"{k}:{v}" for k, v in source_counts.items()),
        "sectional_lookup_rows": len(sectional_lookup),
        "speed_lookup_rows": len(speed_lookup),
        "built_at": built_at,
    }]
    write_csv(SUMMARY, summary, list(summary[0].keys()))
    print(f"Wrote {OUTPUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
