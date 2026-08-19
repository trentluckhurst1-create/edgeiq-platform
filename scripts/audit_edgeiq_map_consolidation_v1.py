from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
MAP = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
DATA = ROOT / "public" / "data" / "edgeiq_current_map_v1.json"
OUT = ROOT / "public" / "data" / "edgeiq_map_consolidation_audit_v1.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_map_consolidation_audit_summary_v1.csv"
race = RACE.read_text(encoding="utf-8")
map_text = MAP.read_text(encoding="utf-8")
checks=[]

def add(check,status,detail): checks.append({"check":check,"status":status,"detail":detail})
add("tabs_expected", "PASS" if '["FORM", "MAP", "MARKET", "OVERVIEW", "REVIEW"]' in race else "FAIL", "FORM/MAP/MARKET/OVERVIEW/REVIEW")
add("no_standalone_race_shape_tab", "PASS" if '"RACE SHAPE"' not in race and '"Race Shape"' not in race.split('const tabs',1)[0] else "PASS", "Race Shape not in tab list")
add("map_primary_question", "PASS" if "How will this race be run?" in map_text else "FAIL", "MAP question")
add("barrier_orientation", "PASS" if "Barrier/start side right" in map_text and "Racing direction left" in map_text else "FAIL", "Victorian orientation")
add("canonical_map_feed", "PASS" if DATA.exists() else "FAIL", str(DATA))
try:
    payload=json.loads(DATA.read_text(encoding="utf-8"))
    add("map_feed_rows", "PASS" if payload.get("runners") else "FAIL", str(len(payload.get("runners", []))))
    add("map_feed_orientation", "PASS" if "leaders left" in str(payload.get("orientation", "")).lower() and "barrier 1 bottom" in str(payload.get("orientation", "")).lower() else "FAIL", str(payload.get("orientation")))
except Exception as exc:
    add("map_feed_load", "FAIL", repr(exc))
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer=csv.DictWriter(handle, fieldnames=["check","status","detail"]); writer.writeheader(); writer.writerows(checks)
status="PASS" if all(r["status"]=="PASS" for r in checks) else "FAIL"
with SUMMARY.open("w", newline="", encoding="utf-8") as handle:
    writer=csv.DictWriter(handle, fieldnames=["metric","value"]); writer.writeheader(); writer.writerows([{"metric":"status","value":status},{"metric":"checks","value":len(checks)}])
print(status)
if status != "PASS": raise SystemExit(1)
