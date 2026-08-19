from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "race-entry-projection"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "race_entry_fact": DATA / "edgeiq_race_entry_fact_v1.csv",
    "horse_performance_rating": DATA / "edgeiq_horse_performance_rating_fact_v1.csv",
    "horse_snapshot": DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
    "performance_context": DATA / "edgeiq_race_entry_performance_context_fact_v1.csv",
    "context_eligibility": DATA / "edgeiq_race_entry_context_eligibility_fact_v1.csv",
    "parameter_selection": DATA / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
    "context_adjustment": DATA / "edgeiq_race_entry_context_adjustment_fact_v1.csv",
    "context_adjusted": DATA / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv",
    "suitability_component": DATA / "edgeiq_race_entry_suitability_component_fact_v1.csv",
    "suitability_aggregate": DATA / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
    "projected_performance": DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv",
    "epi_component": DATA / "edgeiq_race_entry_epi_component_fact_v1.csv",
    "epi": DATA / "edgeiq_race_entry_epi_fact_v1.csv",
}


def clean(v):
    return "" if v is None else str(v).strip()


def norm(v):
    return "".join(ch for ch in clean(v).upper() if ch.isalnum())


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))


def fields(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h).fieldnames or [])


def safe_date(v):
    raw = clean(v)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def race_count(rows):
    return len({clean(r.get("race_id") or r.get("canonical_race_id") or r.get("race_key")) for r in rows if clean(r.get("race_id") or r.get("canonical_race_id") or r.get("race_key"))})


def runner_count(rows):
    return len({clean(r.get("race_entry_id") or r.get("runner_id") or r.get("canonical_runner_id") or r.get("canonical_horse_id")) for r in rows if clean(r.get("race_entry_id") or r.get("runner_id") or r.get("canonical_runner_id") or r.get("canonical_horse_id"))})


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)


def main() -> int:
    loaded = {name: read(path) for name, path in FILES.items()}
    funnel = []
    order = [
        ("current race entries loaded", "race_entry_fact", "NO_CURRENT_RACE_ENTRY"),
        ("historical performance loaded", "horse_performance_rating", "NO_HISTORICAL_PERFORMANCE"),
        ("historical observations date-filtered", "horse_snapshot", "FUTURE_OR_SAME_RACE_OBSERVATION"),
        ("declared context loaded", "performance_context", "MISSING_REQUIRED_FIELD"),
        ("context eligibility applied", "context_eligibility", "MISSING_REQUIRED_FIELD"),
        ("context parameter selection", "parameter_selection", "BELOW_MINIMUM_HISTORY"),
        ("context adjustment", "context_adjustment", "MISSING_REQUIRED_FIELD"),
        ("context adjusted performance", "context_adjusted", "MISSING_REQUIRED_FIELD"),
        ("suitability components", "suitability_component", "MISSING_REQUIRED_FIELD"),
        ("projection aggregation", "suitability_aggregate", "MISSING_REQUIRED_FIELD"),
        ("final output validation", "projected_performance", "UNKNOWN"),
        ("EPI components", "epi_component", "UNKNOWN"),
        ("EPI output", "epi", "UNKNOWN"),
    ]
    previous_rows = None
    first_zero = ""
    for index, (stage, key, default_reason) in enumerate(order):
        rows = loaded[key]
        accepted = len(rows)
        input_rows = previous_rows if previous_rows is not None else len(rows)
        rejected = max(input_rows - accepted, 0) if previous_rows is not None else 0
        if accepted == 0 and not first_zero:
            first_zero = stage
        funnel.append({
            "stage_order": index + 1,
            "stage": stage,
            "source_key": key,
            "source_file": str(FILES[key].relative_to(ROOT)),
            "file_exists": "YES" if FILES[key].exists() else "NO",
            "input_rows": input_rows,
            "accepted_rows": accepted,
            "rejected_rows": rejected,
            "unique_races": race_count(rows),
            "unique_runners": runner_count(rows),
            "primary_rejection_reason": default_reason if accepted == 0 else "",
        })
        previous_rows = accepted
    # detailed rejections from earliest sources
    rejections = []
    race_entries = loaded["race_entry_fact"]
    ratings = loaded["horse_performance_rating"]
    if not FILES["race_entry_fact"].exists():
        rejections.append({"stage":"current race entries loaded", "identity":"edgeiq_race_entry_fact_v1.csv", "rejection_reason":"NO_CURRENT_RACE_ENTRY", "detail":"Canonical race-entry fact file is missing."})
    elif not race_entries:
        rejections.append({"stage":"current race entries loaded", "identity":"edgeiq_race_entry_fact_v1.csv", "rejection_reason":"NO_CURRENT_RACE_ENTRY", "detail":"Canonical race-entry fact file has zero data rows."})
    if not ratings:
        rejections.append({"stage":"historical performance loaded", "identity":"edgeiq_horse_performance_rating_fact_v1.csv", "rejection_reason":"NO_HISTORICAL_PERFORMANCE", "detail":"Canonical horse performance rating fact has zero data rows."})
    # identity coverage diagnostic if both sides have rows
    join_rows = []
    rating_ids = {clean(r.get("canonical_horse_id")) for r in ratings if clean(r.get("canonical_horse_id"))}
    rating_names = {norm(r.get("canonical_horse_name")) for r in ratings if norm(r.get("canonical_horse_name"))}
    for entry in race_entries:
        horse_id = clean(entry.get("canonical_horse_id"))
        horse_name = norm(entry.get("canonical_horse_name"))
        target_date = safe_date(entry.get("race_date"))
        prior = [r for r in ratings if clean(r.get("canonical_horse_id")) == horse_id and safe_date(r.get("rating_as_of_date")) and target_date and safe_date(r.get("rating_as_of_date")) < target_date]
        reason = "OK" if prior else ("IDENTITY_JOIN_MISS" if horse_id not in rating_ids and horse_name not in rating_names else "FUTURE_OR_SAME_RACE_OBSERVATION")
        join_rows.append({
            "race_entry_id": clean(entry.get("race_entry_id")),
            "race_id": clean(entry.get("race_id")),
            "race_date": clean(entry.get("race_date")),
            "runner_id": clean(entry.get("runner_id")),
            "canonical_horse_id": horse_id,
            "canonical_horse_name": clean(entry.get("canonical_horse_name")),
            "exact_id_match": "YES" if horse_id in rating_ids else "NO",
            "normalised_name_match": "YES" if horse_name in rating_names else "NO",
            "prior_rating_count": len(prior),
            "join_status": reason,
        })
    write_csv(OUT_DIR / "edgeiq_race_entry_projection_row_funnel_v1.csv", funnel, ["stage_order","stage","source_key","source_file","file_exists","input_rows","accepted_rows","rejected_rows","unique_races","unique_runners","primary_rejection_reason"])
    write_csv(OUT_DIR / "edgeiq_race_entry_projection_rejections_v1.csv", rejections, ["stage","identity","rejection_reason","detail"])
    write_csv(OUT_DIR / "edgeiq_race_entry_projection_join_coverage_v1.csv", join_rows, ["race_entry_id","race_id","race_date","runner_id","canonical_horse_id","canonical_horse_name","exact_id_match","normalised_name_match","prior_rating_count","join_status"])
    dist = Counter()
    for row in join_rows:
        count = int(row["prior_rating_count"])
        dist["5+" if count >= 5 else str(count)] += 1
    report = "# Race Entry Projection Row Funnel V1\n\n"
    report += f"First zero-row stage: `{first_zero}`\n\n"
    report += "## Stage Counts\n\n"
    for row in funnel:
        report += f"- {row['stage']}: accepted `{row['accepted_rows']}` from `{row['source_file']}` ({row['primary_rejection_reason']})\n"
    report += "\n## History Depth Distribution\n\n"
    for key in ["0","1","2","3","4","5+"]:
        report += f"- {key} prior eligible runs: `{dist[key]}`\n"
    report += "\nConclusion: canonical current race-entry and/or canonical horse rating source availability is the blocker when their accepted rows are zero. No projected-performance formula change is indicated by this funnel.\n"
    (OUT_DIR / "edgeiq_race_entry_projection_row_funnel_report_v1.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":"ROW_FUNNEL_WRITTEN", "first_zero_stage": first_zero, "race_entry_rows": len(race_entries), "rating_rows": len(ratings)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
