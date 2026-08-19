from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from edgeiq_results_common_v1 import DATA, ROOT, first, has_value, key_for, normalized_runner, normalized_track, parse_date, read_csv, write_csv


CANDIDATES = DATA / "edgeiq_speed_candidate_columns_v1.csv"
OUT = DATA / "edgeiq_speed_source_coverage_v1.csv"
SUMMARY = DATA / "edgeiq_speed_source_coverage_summary_v1.csv"
BEST = DATA / "edgeiq_speed_best_sources_v1.csv"
MAX_DEEP_SCAN_SOURCES = 50
ELIGIBLE_TERMS = ("result", "warehouse", "history", "sectional", "speed", "pace")
EXCLUDED_TERMS = (
    "bet_",
    "bet-",
    "fair_price",
    "price_",
    "pricing",
    "probability",
    "execution",
    "market",
    "prior_asof",
    "v6_1",
    "capital",
    "portfolio",
    "checkpoint",
    "edgeiq_results_master_v1",
    "edgeiq_results_terminal_feed",
    "edgeiq_results_calendar",
    "edgeiq_sectionals_retry_queue",
)


def eligible_source(rel: str) -> bool:
    lower = rel.lower().replace("\\", "/")
    return any(term in lower for term in ELIGIBLE_TERMS) and not any(term in lower for term in EXCLUDED_TERMS)


def candidate_map() -> tuple[dict[str, list[str]], dict[str, int], dict[str, int]]:
    out: dict[str, list[str]] = defaultdict(list)
    value_counts: dict[str, int] = defaultdict(int)
    row_counts: dict[str, int] = {}
    if not CANDIDATES.exists():
        return out, value_counts, row_counts
    for row in read_csv(CANDIDATES):
        non_null = int(row.get("non_null_count", "0") or 0)
        if non_null <= 0:
            continue
        out[row["file_path"]].append(row["candidate_column"])
        value_counts[row["file_path"]] += non_null
        row_counts[row["file_path"]] = int(row.get("rows", "0") or 0)
    return out, value_counts, row_counts


def source_path(rel: str) -> Path:
    return ROOT / rel


def main() -> None:
    candidates, value_counts, row_counts = candidate_map()
    ranked_files = sorted(candidates.keys(), key=lambda rel: value_counts[rel], reverse=True)
    eligible_ranked = [rel for rel in ranked_files if eligible_source(rel)]
    deep_scan_files = set(eligible_ranked[:MAX_DEEP_SCAN_SOURCES])
    rows = []
    for rel in ranked_files:
        cols = candidates[rel]
        path = source_path(rel)
        total_values = value_counts[rel]
        runner_rows = 0
        races = set()
        runners = set()
        tracks = set()
        dates = []
        scan_status = "INVENTORY_RANKED_ONLY"
        if not eligible_source(rel):
            scan_status = "INVENTORY_ONLY_EXCLUDED_NON_RESULT_SOURCE"
        elif rel in deep_scan_files:
            scan_status = "DEEP_SCANNED"
            for row in read_csv(path):
                values = [row.get(col, "") for col in cols if has_value(row.get(col, ""))]
                if not values:
                    continue
                date = parse_date(first(row, ["race_date", "meeting_date", "date_k", "run_date", "date"]))
                track = first(row, ["track", "venue_name", "meeting", "track_name"])
                race_no = first(row, ["race_no", "race_k", "race_number", "race"])
                runner = first(row, ["horse", "horseName", "horse_name", "runner", "runner_name"])
                runner_rows += 1
                if date:
                    dates.append(date)
                if track:
                    tracks.add(normalized_track(track))
                if date and track and race_no:
                    races.add(key_for(date, track, race_no))
                if date and track and race_no and runner:
                    runners.add(key_for(date, track, race_no, runner))
        else:
            runner_rows = row_counts.get(rel, 0)
        rows.append(
            {
                "file_path": rel,
                "speed_like_non_null_values": total_values,
                "runner_rows_with_speed": runner_rows,
                "unique_races_with_speed": len(races),
                "unique_runner_keys_with_speed": len(runners),
                "first_date": min(dates) if dates else "",
                "last_date": max(dates) if dates else "",
                "track_coverage": len(tracks),
                "columns_available": ";".join(cols),
                "scan_status": scan_status,
                "source_rank_score": 0 if not eligible_source(rel) else total_values + len(races) * 25 + len(runners) * 5 + len(tracks) * 50,
            }
        )

    rows.sort(key=lambda row: int(row["source_rank_score"]), reverse=True)
    fields = ["file_path", "speed_like_non_null_values", "runner_rows_with_speed", "unique_races_with_speed", "unique_runner_keys_with_speed", "first_date", "last_date", "track_coverage", "columns_available", "scan_status", "source_rank_score"]
    write_csv(OUT, rows, fields)
    write_csv(BEST, [row for row in rows if row["scan_status"] == "DEEP_SCANNED"][:50], fields)
    summary = {
        "sources_ranked": len(rows),
        "best_source": rows[0]["file_path"] if rows else "",
        "best_source_values": rows[0]["speed_like_non_null_values"] if rows else 0,
        "best_source_races": rows[0]["unique_races_with_speed"] if rows else 0,
        "total_sources_with_speed_like_values": sum(1 for row in rows if int(row["speed_like_non_null_values"]) > 0),
        "deep_scanned_sources": sum(1 for row in rows if row["scan_status"] == "DEEP_SCANNED"),
        "excluded_non_result_sources": sum(1 for row in rows if row["scan_status"] == "INVENTORY_ONLY_EXCLUDED_NON_RESULT_SOURCE"),
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Ranked {len(rows)} speed-like sources")


if __name__ == "__main__":
    main()
