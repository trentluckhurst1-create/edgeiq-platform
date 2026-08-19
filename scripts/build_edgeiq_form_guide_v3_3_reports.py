from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INVENTORY_CSV = DATA / "edgeiq_form_guide_v3_3_source_inventory.csv"
INVENTORY_SUMMARY = DATA / "edgeiq_form_guide_v3_3_source_inventory_summary.txt"
JOIN_AUDIT_CSV = DATA / "edgeiq_form_guide_v3_3_join_audit.csv"
COVERAGE_CSV = DATA / "edgeiq_form_guide_v3_3_coverage.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_form_guide_v3_3_coverage_summary.txt"


SOURCE_CANDIDATES = [
    {
        "file": "edgeiq_form_guide_enriched_v1.json",
        "role": "canonical",
        "use_status": "SELECTED",
        "reason": "Current Form Guide V3.3 terminal feed; contains race, runner, profile, current price, EPI, and official recent form contract.",
    },
    {
        "file": "edgeiq_form_guide_enriched_v1.csv",
        "role": "flat_summary",
        "use_status": "SELECTED",
        "reason": "Flat companion summary for source validation and audit review.",
    },
    {
        "file": "edgeiq_three_day_product_catalog_v1.json",
        "role": "current_race_shell",
        "use_status": "SELECTED",
        "reason": "Current meeting, race, runner, official runner identity and silks used by the OS race shell.",
    },
    {
        "file": "edgeiq_live_runner_board_v1.csv",
        "role": "current_ratings",
        "use_status": "REFERENCE_ONLY",
        "reason": "Live board is useful for current race completeness checks but Form Guide V3.3 does not copy unwired model fields into display columns.",
    },
    {
        "file": "edgeiq_live_runner_board_governed_v1.csv",
        "role": "governed_current_ratings",
        "use_status": "REFERENCE_ONLY",
        "reason": "Governed live board is reserved for model output stability checks, not direct form-guide fabrication.",
    },
    {
        "file": "edgeiq_historical_results_warehouse_v2_graphql.csv",
        "role": "historical_results",
        "use_status": "UPSTREAM",
        "reason": "Official historical result source used by enriched builder for career/profile/recent form aggregates.",
    },
    {
        "file": "edgeiq_live_sectional_intelligence_v1.csv",
        "role": "sectional_intelligence",
        "use_status": "NOT_WIRED",
        "reason": "Available sectional intelligence is not yet contracted to the V3.3 per-runner table/recent-form columns, so missing cells remain blank.",
    },
    {
        "file": "edgeiq_runner_dna_drawer_feed_v2.csv",
        "role": "runner_dna",
        "use_status": "NOT_WIRED",
        "reason": "DNA feed supports adjacent analysis; not used to populate Form Guide V3.3 metric columns without an approved join contract.",
    },
    {
        "file": "edgeiq_race_shape_story_v1.csv",
        "role": "race_shape_story",
        "use_status": "NOT_WIRED",
        "reason": "Race-level story feed is not runner-specific enough for the V3.3 RACE SHAPE column.",
    },
    {
        "file": "edgeiq_barrier_rail_condition_bias_replay_v1.csv",
        "role": "bias_replay",
        "use_status": "NOT_WIRED",
        "reason": "Historical replay/bias evidence is not a current runner display contract for V3.3.",
    },
]


def read_csv_headers_and_count(path: Path) -> tuple[list[str], int, dict[str, str]]:
    if not path.exists():
        return [], 0, {"min_date": "", "max_date": ""}
    count = 0
    min_date = ""
    max_date = ""
    headers: list[str] = []
    date_keys = ["race_date", "date", "meeting_date", "run_date"]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        date_col = next((key for key in date_keys if key in headers), "")
        for row in reader:
            count += 1
            value = (row.get(date_col, "") or "")[:10] if date_col else ""
            if value:
                min_date = value if not min_date or value < min_date else min_date
                max_date = value if not max_date or value > max_date else max_date
    return headers, count, {"min_date": min_date, "max_date": max_date}


def inspect_json(path: Path) -> tuple[list[str], int, dict[str, str]]:
    if not path.exists():
        return [], 0, {"min_date": "", "max_date": ""}
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, dict) and isinstance(obj.get("races"), list):
        runners = []
        min_date = ""
        max_date = ""
        for race in obj["races"]:
            value = str(race.get("raceDate", "") or "")[:10]
            if value:
                min_date = value if not min_date or value < min_date else min_date
                max_date = value if not max_date or value > max_date else max_date
            runners.extend(race.get("runners") or [])
        headers = sorted({key for runner in runners for key in runner.keys()})
        return headers, len(runners), {"min_date": min_date, "max_date": max_date}
    if isinstance(obj, dict):
        headers = sorted(obj.keys())
        return headers, 1, {"min_date": "", "max_date": ""}
    if isinstance(obj, list):
        headers = sorted({key for item in obj if isinstance(item, dict) for key in item.keys()})
        return headers, len(obj), {"min_date": "", "max_date": ""}
    return [], 0, {"min_date": "", "max_date": ""}


def inspect_source(file_name: str) -> tuple[list[str], int, dict[str, str]]:
    path = DATA / file_name
    if file_name.lower().endswith(".json"):
        return inspect_json(path)
    if file_name.lower().endswith(".csv"):
        return read_csv_headers_and_count(path)
    return [], 0, {"min_date": "", "max_date": ""}


def value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in {"", "-", "None", "none", "null", "NULL"}
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return bool(value)
    return True


def record_present(value: Any) -> bool:
    return isinstance(value, dict) and bool(value.get("starts"))


def load_enriched() -> dict[str, Any]:
    path = DATA / "edgeiq_form_guide_enriched_v1.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def build_inventory() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for candidate in SOURCE_CANDIDATES:
        file_name = candidate["file"]
        path = DATA / file_name
        headers, count, dates = inspect_source(file_name)
        lower_headers = {header.lower() for header in headers}
        horse_keys = [header for header in headers if "horse" in header.lower() or "runner" in header.lower()]
        rows.append(
            {
                "source_file": file_name,
                "exists": str(path.exists()),
                "row_count": str(count),
                "horse_key_fields": "|".join(horse_keys[:20]),
                "available_columns": "|".join(headers[:180]),
                "date_coverage_min": dates.get("min_date", ""),
                "date_coverage_max": dates.get("max_date", ""),
                "can_support_career": str(any(key in lower_headers for key in ["careerrecord", "career_record", "career"])),
                "can_support_track": str(any("track" in key for key in lower_headers)),
                "can_support_distance": str(any("distance" in key for key in lower_headers)),
                "can_support_condition": str(any("condition" in key or "going" in key for key in lower_headers)),
                "can_support_class": str(any("class" in key for key in lower_headers)),
                "can_support_first_up": str(any("first" in key or "race_day_pattern" in key for key in lower_headers)),
                "can_support_last_start": str(any("laststart" in key or "last_start" in key or "fullform" in key for key in lower_headers)),
                "role": candidate["role"],
                "use_status": candidate["use_status"],
                "reason": candidate["reason"],
            }
        )
    return rows


def match_flag(value: Any) -> str:
    return "YES" if value_present(value) else "NO"


def build_join_and_coverage(feed: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    join_rows: list[dict[str, str]] = []
    coverage_rows: list[dict[str, str]] = []
    duplicate_keys: set[tuple[str, str, str, str]] = set()
    seen_keys: set[tuple[str, str, str, str]] = set()
    ambiguous = 0
    unmatched = 0
    total = 0

    fields = [
        "runner_id",
        "last_five",
        "market",
        "epi",
        "edgeiq_price",
        "career_profile",
        "track_profile",
        "distance_profile",
        "condition_profile",
        "class_profile",
        "jockey_profile",
        "prep_profile",
        "last_start",
        "full_form",
        "early_speed",
        "suitability",
        "race_shape",
        "late_speed",
        "form_momentum",
    ]

    totals = {field: 0 for field in fields}

    for race in feed.get("races", []):
        race_total = len(race.get("runners") or [])
        race_counts = {field: 0 for field in fields}
        for runner in race.get("runners") or []:
            total += 1
            key = (
                str(race.get("raceDate") or ""),
                str(race.get("meeting") or ""),
                str(race.get("raceNumber") or ""),
                str(runner.get("runnerNumber") or ""),
            )
            if key in seen_keys:
                duplicate_keys.add(key)
            seen_keys.add(key)

            join_method = str(runner.get("joinMethod") or "")
            if join_method == "AMBIGUOUS":
                ambiguous += 1
            if join_method == "UNMATCHED":
                unmatched += 1

            field_values = {
                "runner_id": runner.get("runnerId"),
                "last_five": runner.get("lastFive"),
                "market": runner.get("marketPrice"),
                "epi": runner.get("epi"),
                "edgeiq_price": runner.get("edgeiqPrice"),
                "career_profile": runner.get("careerRecord"),
                "track_profile": runner.get("trackRecord"),
                "distance_profile": runner.get("distanceRecord"),
                "condition_profile": runner.get("conditionProfile"),
                "class_profile": runner.get("classProfile"),
                "jockey_profile": runner.get("jockeyProfile"),
                "prep_profile": runner.get("raceDayPattern"),
                "last_start": runner.get("lastStart"),
                "full_form": runner.get("fullForm"),
                "early_speed": runner.get("earlySpeed"),
                "suitability": runner.get("suitability"),
                "race_shape": runner.get("raceShape"),
                "late_speed": runner.get("lateSpeed"),
                "form_momentum": runner.get("formMomentum"),
            }
            for field, value in field_values.items():
                if value_present(value):
                    race_counts[field] += 1
                    totals[field] += 1

            join_rows.append(
                {
                    "race_date": str(runner.get("raceDate") or race.get("raceDate") or ""),
                    "meeting": str(runner.get("meeting") or race.get("meeting") or ""),
                    "race_number": str(runner.get("raceNumber") or race.get("raceNumber") or ""),
                    "runner_number": str(runner.get("runnerNumber") or ""),
                    "runner_name": str(runner.get("runnerName") or ""),
                    "runner_id": str(runner.get("runnerId") or ""),
                    "join_method": join_method,
                    "matched_source": "|".join(filter(None, [str(runner.get("historySource") or ""), str(runner.get("recordSource") or "")])),
                    "market_match": match_flag(runner.get("marketPrice")),
                    "epi_match": match_flag(runner.get("epi")),
                    "edgeiq_price_match": match_flag(runner.get("edgeiqPrice")),
                    "early_speed_match": "NO",
                    "suitability_match": "NO",
                    "race_shape_match": "NO",
                    "late_speed_match": "NO",
                    "momentum_match": "NO",
                    "profile_match": "YES"
                    if any(record_present(runner.get(key)) for key in ["careerRecord", "trackRecord", "distanceRecord"])
                    else "NO",
                    "form_match": match_flag(runner.get("fullForm")),
                    "ambiguity_reason": "" if join_method not in {"AMBIGUOUS", "UNMATCHED"} else join_method,
                }
            )

        for field in fields:
            count = race_counts[field]
            coverage_rows.append(
                {
                    "race_date": str(race.get("raceDate") or ""),
                    "meeting": str(race.get("meeting") or ""),
                    "race_number": str(race.get("raceNumber") or ""),
                    "field": field,
                    "covered": str(count),
                    "total_runners": str(race_total),
                    "coverage_pct": f"{(count / race_total * 100):.1f}" if race_total else "0.0",
                    "notes": "Not wired in approved V3.3 source contract" if count == 0 and field in {"early_speed", "suitability", "race_shape", "late_speed", "form_momentum"} else "",
                }
            )

    summary = {
        "total_runners": total,
        "ambiguous_joins": ambiguous,
        "unmatched_joins": unmatched,
        "duplicate_runner_keys": len(duplicate_keys),
        "field_totals": totals,
    }
    return join_rows, coverage_rows, summary


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    feed = load_enriched()
    inventory = build_inventory()
    join_rows, coverage_rows, coverage_summary = build_join_and_coverage(feed)

    write_csv(INVENTORY_CSV, inventory)
    write_csv(JOIN_AUDIT_CSV, join_rows)
    write_csv(COVERAGE_CSV, coverage_rows)

    generated = datetime.now(timezone.utc).isoformat()
    selected = [row for row in inventory if row["use_status"] == "SELECTED"]
    INVENTORY_SUMMARY.write_text(
        "\n".join(
            [
                "EDGEIQ Form Guide V3.3 Source Inventory",
                f"Generated: {generated}",
                f"Sources inspected: {len(inventory)}",
                f"Selected sources: {', '.join(row['source_file'] for row in selected)}",
                "Canonical runner profile source: edgeiq_form_guide_enriched_v1.json",
                "Reason: it is the compact, current terminal feed built from official/current sources and already keyed to the OS race runner contract.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    totals = coverage_summary["field_totals"]
    total_runners = int(coverage_summary["total_runners"] or 0)
    coverage_lines = [
        "EDGEIQ Form Guide V3.3 Coverage Summary",
        f"Generated: {generated}",
        f"Total runners audited: {total_runners}",
        f"Ambiguous joins: {coverage_summary['ambiguous_joins']}",
        f"Unmatched joins: {coverage_summary['unmatched_joins']}",
        f"Duplicate runner keys: {coverage_summary['duplicate_runner_keys']}",
    ]
    for field, count in totals.items():
        pct = (count / total_runners * 100) if total_runners else 0
        coverage_lines.append(f"{field}: {count}/{total_runners} ({pct:.1f}%)")
    COVERAGE_SUMMARY.write_text("\n".join(coverage_lines) + "\n", encoding="utf-8")

    print("EDGEIQ_FORM_GUIDE_V3_3_REPORTS_BUILT")
    print(f"inventory={INVENTORY_CSV}")
    print(f"join_audit={JOIN_AUDIT_CSV}")
    print(f"coverage={COVERAGE_CSV}")


if __name__ == "__main__":
    main()
