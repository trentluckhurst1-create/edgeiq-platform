from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import (
    DATA,
    classify_speed_column,
    first,
    has_value,
    key_for,
    meeting_key_for,
    normalize_distance,
    normalize_race_no,
    normalized_runner,
    normalized_track,
    now_iso,
    parse_date,
    read_csv,
    write_csv,
)


BEST = DATA / "edgeiq_speed_best_sources_v1.csv"
OUT = DATA / "edgeiq_speed_master_v1.csv"
SUMMARY = DATA / "edgeiq_speed_master_summary_v1.csv"

FIELDS = [
    "race_date",
    "year",
    "month",
    "track",
    "normalized_track",
    "race_no",
    "race_key",
    "meeting_key",
    "runner",
    "normalized_runner",
    "runner_no",
    "position",
    "barrier",
    "distance",
    "class",
    "condition",
    "official_time",
    "last_600_raw",
    "last_400_raw",
    "last_200_raw",
    "speed_raw",
    "speed_rating_raw",
    "early_raw",
    "mid_raw",
    "late_raw",
    "benchmark_raw",
    "par_raw",
    "standard_raw",
    "sectional_source_type",
    "source_file",
    "source_columns_used",
    "source_confidence",
    "built_at",
]


def source_columns() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not BEST.exists():
        return out
    for row in read_csv(BEST):
        rel_lower = row.get("file_path", "").lower()
        if any(token in rel_lower for token in ["checkpoint", "edgeiq_results_master_v1", "edgeiq_results_terminal_feed", "edgeiq_results_calendar", "edgeiq_sectionals_retry_queue"]):
            continue
        cols = [col for col in row.get("columns_available", "").split(";") if col]
        if cols:
            out[row["file_path"]] = cols
    return out


def score(row: dict[str, object]) -> int:
    fields = ["last_600_raw", "last_400_raw", "last_200_raw", "speed_raw", "speed_rating_raw", "early_raw", "mid_raw", "late_raw", "benchmark_raw", "par_raw", "standard_raw"]
    return sum(1 for field in fields if has_value(row.get(field, "")))


def confidence(row: dict[str, object]) -> str:
    if all(has_value(row.get(field, "")) for field in ["last_600_raw", "last_400_raw", "last_200_raw"]):
        return "HIGH"
    if any(has_value(row.get(field, "")) for field in ["early_raw", "mid_raw", "late_raw"]):
        return "HIGH"
    if has_value(row.get("speed_rating_raw", "")) or has_value(row.get("speed_raw", "")):
        return "MEDIUM"
    return "LOW"


def main() -> None:
    built_at = now_iso()
    best_rows: dict[str, dict[str, object]] = {}
    source_counts = defaultdict(int)
    used_sources = source_columns()

    for rel, cols in used_sources.items():
        path = DATA.parent.parent / rel
        if not path.exists():
            continue
        for row in read_csv(path):
            date = parse_date(first(row, ["race_date", "meeting_date", "date_k", "run_date", "date"]))
            track = first(row, ["track", "venue_name", "meeting", "track_name"])
            race_no = normalize_race_no(first(row, ["race_no", "race_k", "race_number", "race"]))
            runner = first(row, ["horse", "horseName", "horse_name", "runner", "runner_name"])
            if not (date and track and race_no and runner):
                continue
            out = {
                "race_date": date,
                "year": date[:4],
                "month": date[5:7],
                "track": track,
                "normalized_track": normalized_track(track),
                "race_no": race_no,
                "race_key": f"{date}_{normalized_track(track)}_R{race_no}",
                "meeting_key": meeting_key_for(date, track),
                "runner": runner,
                "normalized_runner": normalized_runner(runner),
                "runner_no": first(row, ["runner_no", "race_entry_number", "horseNo", "horse_no"]),
                "position": first(row, ["position", "finish", "finish_num", "finishPosition", "finish_position", "finish_pos", "finish_pos_num"]),
                "barrier": first(row, ["barrier", "live_barrier"]),
                "distance": normalize_distance(first(row, ["distance", "dist"])),
                "class": first(row, ["race_class", "raceClass", "class"]),
                "condition": first(row, ["track_condition", "trackCondition", "condition", "going"]),
                "official_time": first(row, ["winning_time", "raceTime", "race_time", "official_time"]),
                "last_600_raw": "",
                "last_400_raw": "",
                "last_200_raw": "",
                "speed_raw": "",
                "speed_rating_raw": "",
                "early_raw": "",
                "mid_raw": "",
                "late_raw": "",
                "benchmark_raw": "",
                "par_raw": "",
                "standard_raw": "",
                "sectional_source_type": "",
                "source_file": rel,
                "source_columns_used": "",
                "source_confidence": "",
                "built_at": built_at,
            }
            used = []
            types = []
            for col in cols:
                value = row.get(col, "")
                if not has_value(value):
                    continue
                field, source_type = classify_speed_column(col)
                if not has_value(out.get(field, "")):
                    out[field] = value
                    used.append(col)
                    types.append(source_type)
            if not used:
                continue
            out["source_columns_used"] = ";".join(used)
            out["sectional_source_type"] = ";".join(sorted(set(types)))
            out["source_confidence"] = confidence(out)
            key = key_for(date, track, race_no, runner)
            current = best_rows.get(key)
            if current is None or score(out) > score(current):
                best_rows[key] = out
            source_counts[rel] += 1

    rows = sorted(best_rows.values(), key=lambda row: (row["race_date"], row["normalized_track"], int(row["race_no"]) if str(row["race_no"]).isdigit() else 999, row["normalized_runner"]))
    write_csv(OUT, rows, FIELDS)
    dates = [row["race_date"] for row in rows if row.get("race_date")]
    summary = {
        "speed_master_rows": len(rows),
        "first_date": min(dates) if dates else "",
        "last_date": max(dates) if dates else "",
        "unique_races": len({row["race_key"] for row in rows}),
        "unique_meetings": len({row["meeting_key"] for row in rows}),
        "source_counts": ";".join(f"{k}:{v}" for k, v in source_counts.items()),
        "built_at": built_at,
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
