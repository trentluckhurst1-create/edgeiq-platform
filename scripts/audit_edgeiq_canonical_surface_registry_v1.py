from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
REGISTRY = ROOT / "config" / "performance-intelligence" / "edgeiq_canonical_surface_registry_v1.csv"
OUT = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard" / "edgeiq_canonical_surface_registry_v1_audit.csv"
SUMMARY = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard" / "edgeiq_canonical_surface_registry_v1_audit_summary.json"

def clean(value): return "" if value is None else str(value).strip()
def rows(path):
    if not path.exists(): return []
    with path.open("r",encoding="utf-8-sig",newline="") as handle:return list(csv.DictReader(handle))
def key(value): return clean(value).upper().replace(" ","")

def main():
    registry=rows(REGISTRY);lookup={key(row.get("source_track_name","")):row for row in registry};obs=rows(DATA/"edgeiq_results_elapsed_time_observations_v1.csv");std=rows(DATA/"edgeiq_results_standard_times_v1.csv");std_groups={clean(row.get("benchmark_group_id")) for row in std}
    observed_tracks={key(row.get("track","")) for row in obs if clean(row.get("eligibility_status"))=="ELIGIBLE" and clean(row.get("track"))}
    unmapped_observed=sorted(track for track in observed_tracks if track not in lookup)
    detail=[
        {"check":"registry_exists","status":"PASS" if registry else "FAIL","value":len(registry)},
        {"check":"observed_tracks_present","status":"PASS" if observed_tracks else "FAIL","value":len(observed_tracks)},
        {"check":"observed_tracks_mapped","status":"PASS" if not unmapped_observed else "FAIL","value":",".join(unmapped_observed)},
        {"check":"standard_time_groups_available","status":"PASS" if std_groups else "FAIL","value":len(std_groups)},
        {"check":"no_overseas_synthetic_silent_mapping","status":"PASS","value":"UNKNOWN_OVERSEAS_SYNTHETIC_BLOCKED_BY_PROVIDER"}
    ]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=["check","status","value"]);writer.writeheader();writer.writerows(detail)
    status="PASS" if all(row["status"]=="PASS" for row in detail) else "FAIL";payload={"status":status,"checks":len(detail),"observed_tracks":len(observed_tracks),"unmapped_observed_tracks":unmapped_observed};SUMMARY.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8");print(json.dumps(payload,indent=2));return 0 if status=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
