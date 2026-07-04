from __future__ import annotations

from edgeiq_results_common_v1 import DATA, ROOT, first, key_for, normalized_runner, read_csv, write_csv


AUDIT = DATA / "edgeiq_gear_source_audit_v1.csv"
OUT = DATA / "edgeiq_gear_profile_feed_v1.csv"
SUMMARY = DATA / "edgeiq_gear_profile_feed_summary_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_key",
    "runner",
    "normalized_runner",
    "gear_current",
    "gear_changes",
    "gear_added",
    "gear_removed",
    "first_time_gear",
    "gear_change_flag",
    "source_file",
    "source_confidence",
]


def source_candidates() -> list[tuple[str, list[str]]]:
    rows = []
    if not AUDIT.exists():
        return rows
    for row in read_csv(AUDIT):
        if int(row.get("gear_non_null_values", "0") or 0) <= 0:
            continue
        cols = [col for col in row.get("candidate_columns", "").split(";") if col]
        if cols:
            rows.append((row["file_path"], cols))
    return rows[:80]


def classify_changes(text: str) -> tuple[str, str, str]:
    raw = text or ""
    lower = raw.lower()
    added = raw if any(token in lower for token in ["first", "again", "on", "added", "new"]) else ""
    removed = raw if any(token in lower for token in ["off", "removed", "without"]) else ""
    first_time = "YES" if "first" in lower or "1st" in lower else ""
    return added, removed, first_time


def main() -> None:
    best: dict[str, dict[str, str]] = {}
    for rel, cols in source_candidates():
        path = ROOT / rel
        if not path.exists():
            continue
        for row in read_csv(path):
            date = first(row, ["race_date", "meeting_date", "date", "run_date", "date_k"])
            track = first(row, ["track", "venue_name", "meeting", "track_name"])
            race_no = first(row, ["race_no", "race_number", "race", "race_k"])
            runner = first(row, ["runner", "horse", "horse_name", "horseName", "runner_name"])
            if not (date and track and race_no and runner):
                continue
            gear_current = first(row, ["gear", "equipment", "current_gear", "gear_current"])
            changes = first(row, ["gear_change", "gear_changes", "new_gear", "removed_gear", "gear_changes_text"])
            if not gear_current and not changes:
                values = [row.get(col, "") for col in cols if row.get(col, "")]
                if values:
                    changes = "; ".join(values)
            if not gear_current and not changes:
                continue
            added, removed, first_time = classify_changes(changes)
            out = {
                "race_date": date,
                "track": track,
                "race_no": race_no,
                "race_key": key_for(date, track, race_no),
                "runner": runner,
                "normalized_runner": normalized_runner(runner),
                "gear_current": gear_current,
                "gear_changes": changes,
                "gear_added": added,
                "gear_removed": removed,
                "first_time_gear": first_time,
                "gear_change_flag": "YES" if changes else "NO",
                "source_file": rel,
                "source_confidence": "HIGH" if gear_current or changes else "LOW",
            }
            key = key_for(date, track, race_no, runner)
            if key not in best:
                best[key] = out
    rows = sorted(best.values(), key=lambda r: (r["race_date"], r["track"], r["race_no"], r["normalized_runner"]))
    write_csv(OUT, rows, FIELDS)
    summary = {
        "gear_rows": len(rows),
        "gear_change_rows": sum(1 for row in rows if row["gear_change_flag"] == "YES"),
        "first_time_gear_rows": sum(1 for row in rows if row["first_time_gear"] == "YES"),
        "unique_races": len({row["race_key"] for row in rows}),
        "unique_runners": len({row["normalized_runner"] for row in rows}),
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
