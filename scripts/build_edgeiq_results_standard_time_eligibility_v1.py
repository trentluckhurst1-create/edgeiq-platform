from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
SOURCE = DATA / "edgeiq_standard_time_performance_facts_from_results_v1.csv"
ELIGIBLE_OUT = DATA / "edgeiq_results_standard_time_eligible_observations_v1.csv"
DIST = DOCS / "edgeiq_results_standard_time_group_distribution_v1.csv"
AUDIT = DOCS / "edgeiq_results_standard_time_eligibility_audit_v1.csv"
REPORT = DOCS / "edgeiq_results_standard_time_eligibility_report_v1.md"
SUMMARY = DOCS / "edgeiq_results_standard_time_eligibility_summary_v1.json"
MIN_SAMPLE = 20

def clean(value: object) -> str:
    return "" if value is None else str(value).strip()

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})

def bucket(count: int) -> str:
    if count >= MIN_SAMPLE: return "MEETS_MINIMUM"
    if count >= max(1, MIN_SAMPLE // 2): return "HALF_TO_MINIMUM"
    if count >= max(1, MIN_SAMPLE // 4): return "QUARTER_TO_HALF"
    return "BELOW_QUARTER"

def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    rows = read_csv(SOURCE)
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if clean(row.get("eligibility_status")) == "ELIGIBLE":
            gid = clean(row.get("benchmark_group_id"))
            if gid: groups[gid].append(row)

    distribution=[]; eligible_rows=[]
    for group_id, group_rows in sorted(groups.items()):
        sample_count=len(group_rows); first=group_rows[0]
        source_races=len({clean(r.get("canonical_race_id")) for r in group_rows})
        source_runners=len({(clean(r.get("canonical_race_id")),clean(r.get("canonical_runner_id"))) for r in group_rows})
        status="STANDARD_TIME_ELIGIBLE" if sample_count >= MIN_SAMPLE else "BELOW_MINIMUM_SAMPLE"
        distribution.append({"benchmark_group_id":group_id,"track":clean(first.get("track")),"race_distance_metres":clean(first.get("race_distance_metres")),"segment_start_metres":clean(first.get("segment_start_metres")),"segment_end_metres":clean(first.get("segment_end_metres")),"segment_distance_metres":clean(first.get("segment_distance_metres")),"observation_count":sample_count,"source_race_count":source_races,"source_runner_count":source_runners,"minimum_sample":MIN_SAMPLE,"deficit_to_minimum":max(0,MIN_SAMPLE-sample_count),"group_bucket":bucket(sample_count),"standard_time_eligibility_status":status})
        if status == "STANDARD_TIME_ELIGIBLE": eligible_rows.extend({**r,"standard_time_eligibility_status":status} for r in group_rows)

    counts=[len(v) for v in groups.values()]; meeting_min=sum(c >= MIN_SAMPLE for c in counts)
    source_eligible=sum(clean(r.get("eligibility_status")) == "ELIGIBLE" for r in rows)
    summary={"total_detailed_observations":len(rows),"source_eligible_observations":source_eligible,"source_ineligible_observations":len(rows)-source_eligible,"benchmark_groups":len(groups),"groups_meeting_minimum":meeting_min,"groups_below_minimum":len(groups)-meeting_min,"largest_group_size":max(counts) if counts else 0,"median_group_size":statistics.median(counts) if counts else 0,"total_deficit":sum(max(0,MIN_SAMPLE-c) for c in counts),"minimum_sample":MIN_SAMPLE,"bucket_counts":dict(Counter(bucket(c) for c in counts)),"standard_time_eligible_output_rows":len(eligible_rows)}
    write_csv(DIST,distribution,["benchmark_group_id","track","race_distance_metres","segment_start_metres","segment_end_metres","segment_distance_metres","observation_count","source_race_count","source_runner_count","minimum_sample","deficit_to_minimum","group_bucket","standard_time_eligibility_status"])
    fields=list(rows[0].keys())+["standard_time_eligibility_status"] if rows else ["standard_time_eligibility_status"]
    write_csv(ELIGIBLE_OUT,eligible_rows,fields)
    audit_rows=[
        {"check":"source_nonempty","status":"PASS" if rows else "FAIL","value":len(rows),"detail":"Current performance fact source must contain observations."},
        {"check":"source_eligible_nonempty","status":"PASS" if source_eligible else "FAIL","value":source_eligible,"detail":"At least one structurally eligible current observation is required."},
        {"check":"benchmark_groups_present","status":"PASS" if groups else "FAIL","value":len(groups),"detail":"Current observations must form benchmark groups."},
        {"check":"groups_meeting_minimum","status":"PASS" if meeting_min else "WARN","value":meeting_min,"detail":f"Current groups reaching governed minimum sample {MIN_SAMPLE}."},
        {"check":"eligible_output_consistent","status":"PASS" if all(clean(r.get("standard_time_eligibility_status")) == "STANDARD_TIME_ELIGIBLE" for r in eligible_rows) else "FAIL","value":len(eligible_rows),"detail":"Output contains only groups satisfying the governed sample rule."}
    ]
    write_csv(AUDIT,audit_rows,["check","status","value","detail"])
    SUMMARY.write_text(json.dumps(summary,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
    REPORT.write_text("# Results Standard Time Eligibility V1\n\n"+f"Current detailed observations: `{len(rows)}`\n\n"+f"Current benchmark groups: `{len(groups)}`\n\n"+f"Groups meeting governed minimum {MIN_SAMPLE}: `{meeting_min}`\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return 0 if all(r["status"] in {"PASS","WARN"} for r in audit_rows) else 1

if __name__ == "__main__": raise SystemExit(main())
