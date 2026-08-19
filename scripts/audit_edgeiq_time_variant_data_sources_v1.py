from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUTPUT_AUDIT = DATA / "edgeiq_time_variant_data_sources_audit_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_time_variant_data_sources_summary_v1.csv"

INCLUDE_TERMS = (
    "results",
    "warehouse",
    "time",
    "sectional",
    "track",
    "distance",
    "condition",
    "rail",
    "margin",
    "beaten",
    "rating",
    "winner",
    "class",
    "form",
)

EXACT_SOURCE_PRIORITY = [
    "edgeiq_historical_results_warehouse_v2_graphql.csv",
    "edgeiq_racingcom_results_warehouse_full_v1.csv",
    "edgeiq_racingcom_results_warehouse_all_v1.csv",
    "edgeiq_historical_run_ratings_master_v1.csv",
    "edgeiq_historical_performance_rating_v6_1_research.csv",
    "edgeiq_horse_results_power_ratings_v1.csv",
    "historical_form_table.csv",
    "results_history.csv",
    "results_history_clean.csv",
    "race_results.csv",
    "ra_calendar_official_results.csv",
    "sectionals.csv",
    "racingcom_sectional_warehouse_v2.csv",
    "racingcom_sectional_history_master_v1.csv",
]

EXCLUDE_PATTERNS = [
    re.compile(r"_summary\.csv$", re.IGNORECASE),
    re.compile(r"_audit(?:_[^.]*)?\.csv$", re.IGNORECASE),
    re.compile(r"_report\.csv$", re.IGNORECASE),
    re.compile(r"_manifest\.csv$", re.IGNORECASE),
    re.compile(r"_seed\.csv$", re.IGNORECASE),
    re.compile(r"_coverage(?:_[^.]*)?\.csv$", re.IGNORECASE),
    re.compile(r"_diagnostic(?:_[^.]*)?\.csv$", re.IGNORECASE),
    re.compile(r"_diagnostics(?:_[^.]*)?\.csv$", re.IGNORECASE),
    re.compile(r"_CHECKPOINT_.*\.csv$", re.IGNORECASE),
    re.compile(r"_BACKUP.*\.csv$", re.IGNORECASE),
    re.compile(r"^edgeiq_graphql_.*_results_v1\.csv$", re.IGNORECASE),
]


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def normalize_name(value: object) -> str:
    txt = upper(value)
    return "".join(ch for ch in txt if ch.isalnum())


def find_column(headers: Sequence[str], aliases: Sequence[str]) -> str:
    lowered = {header.lower(): header for header in headers}
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    return ""


def parse_date(value: object) -> Optional[datetime]:
    txt = clean(value)
    if txt == "":
        return None
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def count_rows_fast(path: Path) -> int:
    with path.open("rb") as handle:
        count = 0
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            count += chunk.count(b"\n")
    return max(count - 1, 0)


def is_candidate(path: Path) -> bool:
    name = path.name.lower()
    if path.suffix.lower() != ".csv":
        return False
    if not any(term in name for term in INCLUDE_TERMS):
        return False
    for pattern in EXCLUDE_PATTERNS:
        if pattern.search(path.name):
            return False
    return True


def discover_candidate_files() -> List[Path]:
    candidates: List[Path] = []
    prioritized = {name.lower(): index for index, name in enumerate(EXACT_SOURCE_PRIORITY)}

    for path in DATA.glob("*.csv"):
        if is_candidate(path):
            candidates.append(path)

    def sort_key(path: Path) -> Tuple[int, str]:
        return (prioritized.get(path.name.lower(), 9999), path.name.lower())

    candidates.sort(key=sort_key)
    return candidates


def detect_usefulness(
    filename: str,
    row_count: int,
    date_col: str,
    track_col: str,
    race_no_col: str,
    race_id_col: str,
    horse_col: str,
    finish_col: str,
    time_col: str,
    margin_col: str,
    condition_col: str,
    rail_col: str,
    class_col: str,
    sectionals_available: bool,
) -> str:
    tags: List[str] = []
    if time_col and date_col and track_col and (race_no_col or race_id_col):
        tags.append("STANDARD_TIME_SOURCE")
    if time_col and condition_col and track_col and date_col:
        tags.append("VARIANT_SOURCE")
    if time_col and margin_col and horse_col and finish_col and date_col and track_col:
        tags.append("EPF_SOURCE")
    if sectionals_available:
        tags.append("SECTIONAL_SOURCE")
    if not tags:
        return "NOT_USEFUL"
    if row_count < 100:
        tags.append("LOW_SAMPLE")
    return ";".join(tags)


def current_universe_join_potential(date_col: str, track_col: str, race_no_col: str, horse_col: str) -> str:
    if date_col and track_col and race_no_col and horse_col:
        return "HIGH"
    if track_col and race_no_col and horse_col:
        return "MEDIUM"
    if horse_col and date_col:
        return "LOW_MEDIUM"
    if horse_col:
        return "LOW"
    return "NONE"


def profile_source(path: Path) -> Dict[str, object]:
    row_count = count_rows_fast(path)

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []

        date_col = find_column(headers, ["race_date", "meeting_date", "date"])
        track_col = find_column(headers, ["track", "venue_name"])
        race_no_col = find_column(headers, ["race_no", "race_number"])
        race_id_col = find_column(headers, ["race_id", "race_key", "meet_code"])
        horse_col = find_column(headers, ["horse", "horseName", "horse_name"])
        horse_key_col = find_column(headers, ["horse_key", "horseKey", "horse_code", "horseKey"])
        finish_col = find_column(
            headers,
            ["finish_num", "finish_position", "finishPosition", "finish_pos", "finish", "placed", "won"],
        )
        time_col = find_column(headers, ["winning_time", "raceTime", "race_time", "winner_time", "actual_time"])
        margin_col = find_column(headers, ["margin_l", "margin_num", "margin", "bb", "beaten_margin"])
        condition_col = find_column(headers, ["track_condition", "trackCondition", "condition", "track_condition_raw"])
        rail_col = find_column(headers, ["rail_position", "rail", "previous_rail_position"])
        class_col = find_column(headers, ["race_class", "raceClass", "class_name", "race_class_clean"])

        sectionals_available = any("section" in header.lower() for header in headers)

        date_min: Optional[datetime] = None
        date_max: Optional[datetime] = None
        tracks: Set[str] = set()
        distances: Set[str] = set()
        timed_rows = 0
        margin_rows = 0
        condition_rows = 0
        rail_rows = 0
        horse_rows = 0
        finish_rows = 0
        rating_rows = 0
        sample_limit = 5000
        sampled = 0

        rating_cols = [header for header in headers if "rating" in header.lower()]

        for row in reader:
            if sampled < sample_limit:
                if date_col:
                    parsed = parse_date(row.get(date_col))
                    if parsed is not None:
                        date_min = parsed if date_min is None or parsed < date_min else date_min
                        date_max = parsed if date_max is None or parsed > date_max else date_max
                if track_col:
                    track_value = upper(row.get(track_col))
                    if track_value:
                        tracks.add(track_value)
                distance_col = find_column(headers, ["distance", "distance_m"])
                if distance_col:
                    distance_value = clean(row.get(distance_col))
                    if distance_value:
                        distances.add(distance_value)
                sampled += 1

            if time_col and clean(row.get(time_col)):
                timed_rows += 1
            if margin_col and clean(row.get(margin_col)):
                margin_rows += 1
            if condition_col and clean(row.get(condition_col)):
                condition_rows += 1
            if rail_col and clean(row.get(rail_col)):
                rail_rows += 1
            if horse_col and clean(row.get(horse_col)):
                horse_rows += 1
            if finish_col and clean(row.get(finish_col)):
                finish_rows += 1
            if rating_cols and any(clean(row.get(column)) for column in rating_cols):
                rating_rows += 1

    usefulness = detect_usefulness(
        filename=path.name,
        row_count=row_count,
        date_col=date_col,
        track_col=track_col,
        race_no_col=race_no_col,
        race_id_col=race_id_col,
        horse_col=horse_col,
        finish_col=finish_col,
        time_col=time_col,
        margin_col=margin_col,
        condition_col=condition_col,
        rail_col=rail_col,
        class_col=class_col,
        sectionals_available=sectionals_available,
    )

    return {
        "file_name": path.name,
        "rows": row_count,
        "date_min": date_min.strftime("%Y-%m-%d") if date_min else "",
        "date_max": date_max.strftime("%Y-%m-%d") if date_max else "",
        "tracks_sampled": len(tracks),
        "distances_sampled": len(distances),
        "race_time_column": time_col,
        "winner_time_column": time_col,
        "margin_column": margin_col,
        "condition_column": condition_col,
        "rail_column": rail_col,
        "class_column": class_col,
        "race_id_column": race_id_col,
        "race_no_column": race_no_col,
        "horse_column": horse_col,
        "horse_key_column": horse_key_col,
        "finish_position_column": finish_col,
        "timed_rows": timed_rows,
        "margin_rows": margin_rows,
        "condition_rows": condition_rows,
        "rail_rows": rail_rows,
        "horse_rows": horse_rows,
        "finish_rows": finish_rows,
        "rating_rows": rating_rows,
        "sectionals_available": "YES" if sectionals_available else "NO",
        "current_universe_join_potential": current_universe_join_potential(
            date_col=date_col,
            track_col=track_col,
            race_no_col=race_no_col,
            horse_col=horse_col,
        ),
        "usefulness": usefulness,
    }


def choose_best_source(rows: List[Dict[str, object]], tag: str) -> str:
    best: Optional[Tuple[int, int, str]] = None
    best_name = ""
    for row in rows:
        usefulness = clean(row.get("usefulness"))
        if tag not in usefulness:
            continue
        score = (
            int(row.get("rows") or 0),
            int(row.get("timed_rows") or 0) + int(row.get("margin_rows") or 0) + int(row.get("rail_rows") or 0),
            clean(row.get("file_name")),
        )
        if best is None or score > best:
            best = score
            best_name = clean(row.get("file_name"))
    return best_name


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    candidates = discover_candidate_files()

    audit_rows = [profile_source(path) for path in candidates]

    best_time = choose_best_source(audit_rows, "STANDARD_TIME_SOURCE")
    best_margin = choose_best_source(audit_rows, "EPF_SOURCE")
    best_condition = choose_best_source(audit_rows, "VARIANT_SOURCE")
    best_rail = ""
    for row in audit_rows:
        if clean(row.get("rail_column")) and int(row.get("rail_rows") or 0) > 0:
            if best_rail == "" or int(row.get("rows") or 0) > next(
                (int(x.get("rows") or 0) for x in audit_rows if clean(x.get("file_name")) == best_rail),
                -1,
            ):
                best_rail = clean(row.get("file_name"))

    epf_ready = "YES" if best_time and best_margin and best_condition else "NO"
    standard_time_ready = "READY" if best_time else "NOT_READY"
    variant_ready = "READY" if best_time and best_condition else "NOT_READY"

    summary_row = {
        "status": "EDGEIQ_TIME_VARIANT_DATA_SOURCES_AUDIT_BUILT",
        "candidate_files": len(audit_rows),
        "best_source_historical_race_times": best_time,
        "best_source_runner_level_beaten_margins": best_margin,
        "best_source_track_condition": best_condition,
        "best_source_rail_position": best_rail,
        "standard_time_readiness": standard_time_ready,
        "track_variant_readiness": variant_ready,
        "epf_v1_feasible": epf_ready,
        "built_at": built_at,
    }

    audit_fieldnames = [
        "file_name",
        "rows",
        "date_min",
        "date_max",
        "tracks_sampled",
        "distances_sampled",
        "race_time_column",
        "winner_time_column",
        "margin_column",
        "condition_column",
        "rail_column",
        "class_column",
        "race_id_column",
        "race_no_column",
        "horse_column",
        "horse_key_column",
        "finish_position_column",
        "timed_rows",
        "margin_rows",
        "condition_rows",
        "rail_rows",
        "horse_rows",
        "finish_rows",
        "rating_rows",
        "sectionals_available",
        "current_universe_join_potential",
        "usefulness",
    ]
    summary_fieldnames = list(summary_row.keys())

    write_csv(OUTPUT_AUDIT, audit_rows, audit_fieldnames)
    write_csv(OUTPUT_SUMMARY, [summary_row], summary_fieldnames)

    print("EDGEiQ time/variant data source audit complete")
    print(f"Candidate files: {len(audit_rows)}")
    print(f"Best race-time source: {best_time or 'NONE'}")
    print(f"Best beaten-margin source: {best_margin or 'NONE'}")
    print(f"Best track-condition source: {best_condition or 'NONE'}")
    print(f"Best rail source: {best_rail or 'NONE'}")
    print(f"Standard time readiness: {standard_time_ready}")
    print(f"Track variant readiness: {variant_ready}")
    print(f"EPF V1 feasible: {epf_ready}")


if __name__ == "__main__":
    main()
