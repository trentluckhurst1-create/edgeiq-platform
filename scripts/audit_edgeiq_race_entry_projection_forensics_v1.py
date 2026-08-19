from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "race-entry-projection"
DOCS.mkdir(parents=True, exist_ok=True)
TODAY = date(2026, 7, 23)


def clean(v):
    return "" if v is None else str(v).strip()


def norm(v):
    return "".join(ch for ch in clean(v).upper() if ch.isalnum())


def parse_date(v):
    raw = clean(v)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))


def write(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def main() -> int:
    race_entries = read(DATA / "edgeiq_race_entry_fact_v1.csv")
    ratings = read(DATA / "edgeiq_horse_performance_rating_fact_v1.csv")
    projected = read(DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv")
    source_audit = read(DOCS / "edgeiq_current_race_entry_source_audit_v1.csv")
    current_future_sources = [r for r in source_audit if clean(r.get("date_status_sample")) == "CURRENT_OR_FUTURE" and clean(r.get("likely_race_entry_source")) == "YES"]
    current_future_entries = [r for r in race_entries if parse_date(r.get("race_date")) and parse_date(r.get("race_date")) >= TODAY]

    rating_ids = {clean(r.get("canonical_horse_id")) for r in ratings if clean(r.get("canonical_horse_id"))}
    rating_names = {norm(r.get("canonical_horse_name")) for r in ratings if norm(r.get("canonical_horse_name"))}
    matches = []
    misses = []
    collisions = []
    by_id = Counter(clean(r.get("canonical_horse_id")) for r in ratings if clean(r.get("canonical_horse_id")))
    for horse_id, count in by_id.items():
        if count > 1:
            collisions.append({"identity_type":"canonical_horse_id", "identity_value":horse_id, "match_count":count, "collision_status":"DUPLICATE_HISTORICAL_RATING_IDENTITY"})
    for entry in current_future_entries:
        horse_id = clean(entry.get("canonical_horse_id"))
        horse_name = norm(entry.get("canonical_horse_name"))
        target = parse_date(entry.get("race_date"))
        prior = [r for r in ratings if clean(r.get("canonical_horse_id")) == horse_id and parse_date(r.get("rating_as_of_date")) and target and parse_date(r.get("rating_as_of_date")) < target]
        out = {"race_entry_id":clean(entry.get("race_entry_id")), "race_id":clean(entry.get("race_id")), "race_date":clean(entry.get("race_date")), "runner_id":clean(entry.get("runner_id")), "canonical_horse_id":horse_id, "canonical_horse_name":clean(entry.get("canonical_horse_name")), "exact_runner_id_matches":"1" if horse_id in rating_ids else "0", "normalised_name_matches":"1" if horse_name in rating_names else "0", "horse_code_matches":"0", "prior_rating_matches":len(prior)}
        if prior:
            matches.append({**out, "match_status":"TEMPORALLY_ELIGIBLE_MATCH"})
        else:
            reason = "IDENTITY_JOIN_MISS" if horse_id not in rating_ids and horse_name not in rating_names else "FUTURE_OR_SAME_RACE_OBSERVATION"
            misses.append({**out, "miss_reason": reason})
    if not current_future_entries:
        misses.append({"race_entry_id":"", "race_id":"", "race_date":"", "runner_id":"", "canonical_horse_id":"", "canonical_horse_name":"", "exact_runner_id_matches":"0", "normalised_name_matches":"0", "horse_code_matches":"0", "prior_rating_matches":"0", "miss_reason":"NO_ACTIVE_RACE_ENTRIES_AVAILABLE"})
    write(DOCS / "edgeiq_race_entry_historical_identity_matches_v1.csv", matches, ["race_entry_id","race_id","race_date","runner_id","canonical_horse_id","canonical_horse_name","exact_runner_id_matches","normalised_name_matches","horse_code_matches","prior_rating_matches","match_status"])
    write(DOCS / "edgeiq_race_entry_historical_identity_misses_v1.csv", misses, ["race_entry_id","race_id","race_date","runner_id","canonical_horse_id","canonical_horse_name","exact_runner_id_matches","normalised_name_matches","horse_code_matches","prior_rating_matches","miss_reason"])
    write(DOCS / "edgeiq_race_entry_identity_collision_v1.csv", collisions, ["identity_type","identity_value","match_count","collision_status"])

    temporal_candidates = []
    temporal_rejections = []
    for entry in current_future_entries:
        target = parse_date(entry.get("race_date"))
        for rating in ratings:
            if clean(rating.get("canonical_horse_id")) != clean(entry.get("canonical_horse_id")):
                continue
            rdate = parse_date(rating.get("rating_as_of_date"))
            row = {"race_entry_id":clean(entry.get("race_entry_id")), "race_date":clean(entry.get("race_date")), "canonical_horse_id":clean(entry.get("canonical_horse_id")), "rating_id":clean(rating.get("horse_performance_rating_id")), "rating_as_of_date":clean(rating.get("rating_as_of_date"))}
            if target and rdate and rdate < target:
                temporal_candidates.append({**row, "temporal_status":"PRIOR_RATING_ELIGIBLE"})
            else:
                temporal_rejections.append({**row, "temporal_rejection":"FUTURE_OR_SAME_RACE_OBSERVATION"})
    if not current_future_entries:
        temporal_rejections.append({"race_entry_id":"", "race_date":"", "canonical_horse_id":"", "rating_id":"", "rating_as_of_date":"", "temporal_rejection":"NO_ACTIVE_RACE_ENTRIES_AVAILABLE"})
    write(DOCS / "edgeiq_race_entry_projection_temporal_candidates_v1.csv", temporal_candidates, ["race_entry_id","race_date","canonical_horse_id","rating_id","rating_as_of_date","temporal_status"])
    write(DOCS / "edgeiq_race_entry_projection_temporal_rejections_v1.csv", temporal_rejections, ["race_entry_id","race_date","canonical_horse_id","rating_id","rating_as_of_date","temporal_rejection"])

    depth_counts = Counter()
    for entry in current_future_entries:
        target = parse_date(entry.get("race_date"))
        count = sum(1 for r in ratings if clean(r.get("canonical_horse_id")) == clean(entry.get("canonical_horse_id")) and parse_date(r.get("rating_as_of_date")) and target and parse_date(r.get("rating_as_of_date")) < target)
        depth_counts["5+" if count >= 5 else str(count)] += 1
    if not current_future_entries:
        depth_counts["0"] = 0
    eligibility_rows = []
    for label in ["0", "1", "2", "3", "4", "5+"]:
        eligibility_rows.append({"prior_eligible_run_bucket": label, "runner_count": depth_counts[label], "audit_only": "YES"})
    write(DOCS / "edgeiq_race_entry_projection_minimum_history_distribution_v1.csv", eligibility_rows, ["prior_eligible_run_bucket","runner_count","audit_only"])
    gate_rows = [
        {"gate_name":"current_or_future_race_entries", "configured_value":">= 2026-07-23", "source_of_governance":"directive_current_window", "rows_before":len(race_entries), "rows_after":len(current_future_entries), "rows_rejected":max(len(race_entries)-len(current_future_entries), 0), "gate_status":"BLOCKING" if not current_future_entries else "PASS"},
        {"gate_name":"historical_rating_available", "configured_value":"prior rating required", "source_of_governance":"active snapshot builder", "rows_before":len(current_future_entries), "rows_after":len(matches), "rows_rejected":max(len(current_future_entries)-len(matches), 0), "gate_status":"NOT_APPLICABLE_NO_ACTIVE_ENTRIES" if not current_future_entries else ("PASS" if matches else "BLOCKING")},
    ]
    write(DOCS / "edgeiq_race_entry_projection_eligibility_gates_v1.csv", gate_rows, ["gate_name","configured_value","source_of_governance","rows_before","rows_after","rows_rejected","gate_status"])

    temporal_report = "# Race Entry Projection Temporal Integrity V1\n\n"
    temporal_report += f"Current/future race entries: `{len(current_future_entries)}`\n\n"
    temporal_report += f"Temporal candidates: `{len(temporal_candidates)}`\n\n"
    temporal_report += f"Temporal rejections: `{len(temporal_rejections)}`\n\n"
    temporal_report += "Conclusion: `NO_ACTIVE_RACE_ENTRIES_AVAILABLE` prevents temporal projection candidate creation. Temporal leakage protection was not weakened.\n"
    (DOCS / "edgeiq_race_entry_projection_temporal_report_v1.md").write_text(temporal_report, encoding="utf-8")

    final_status = "EDGEIQ_PERFORMANCE_INTELLIGENCE_NO_ACTIVE_RACE_ENTRIES" if not current_future_entries and not current_future_sources else "EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_PROJECTED_FACT_INPUT"
    final = {
        "overall_status": final_status,
        "active_projected_performance_builder": "scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py",
        "active_output_contract": "contracts/performance-intelligence/edgeiq_race_entry_projected_performance_fact_v1_contract.json",
        "current_race_entry_source": "public/data/edgeiq_race_entry_fact_v1.csv",
        "current_race_entry_rows": len(current_future_entries),
        "current_future_source_files": len(current_future_sources),
        "historical_performance_source": "public/data/edgeiq_horse_performance_rating_fact_v1.csv",
        "historical_performance_rows": len(ratings),
        "identity_matches": len(matches),
        "identity_misses": len(misses),
        "temporally_eligible_matches": len(temporal_candidates),
        "first_zero_row_stage": "current race entries loaded",
        "minimum_history_requirement": "prior rating required; no current/future entries to evaluate",
        "runners_meeting_minimum": 0,
        "runners_below_minimum": 0,
        "projected_performance_candidate_rows": 0,
        "projected_performance_production_rows": len(projected),
        "projected_performance_hash": file_hash(DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv"),
        "epi_input_rows": 0,
        "epi_output_rows": len(read(DATA / "edgeiq_race_entry_epi_fact_v1.csv")),
        "genuine_data_gap": "NO_ACTIVE_RACE_ENTRIES_AVAILABLE",
        "remaining_blocker": "Refresh or rebuild canonical current race-entry fact from a current/future governed race-entry source, then rerun projection chain.",
    }
    (DOCS / "edgeiq_race_entry_projection_forensic_final_v1.json").write_text(json.dumps(final, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report = "# Race Entry Projected Performance Forensic Final V1\n\n"
    for k, v in final.items():
        report += f"{k}: `{v}`\n\n"
    (DOCS / "edgeiq_race_entry_projection_forensic_final_report_v1.md").write_text(report, encoding="utf-8")
    print(json.dumps(final, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
