from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_epi_current_rating_audit_v1.csv"
SUMMARY = DATA / "edgeiq_epi_current_rating_audit_summary_v1.csv"
JSON_PATH = DATA / "edgeiq_epi_current_rating_v1.json"
DIST = DATA / "edgeiq_epi_distribution_v1.csv"

checks = []

def add(name: str, status: str, detail: str) -> None:
    checks.append({"check": name, "status": status, "detail": detail})

def write(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)

try:
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    runners = payload.get("runners", [])
    add("json_exists", "PASS", str(JSON_PATH))
    add("schema", "PASS" if payload.get("schemaVersion") == "EDGEIQ_EPI_CURRENT_RATING_V1" else "FAIL", str(payload.get("schemaVersion")))
    active = [r for r in runners if r.get("status") == "CURRENT"]
    missing = [r for r in runners if r.get("status") == "MISSING"]
    zero_defaults = [r for r in active if r.get("value") in (0, "0", 0.0)]
    required = ["value", "display", "version", "source", "status", "rankInRace", "activeFieldSize", "fieldHigh", "fieldAverage", "differenceFromFieldAverage", "recentChange", "trend"]
    missing_fields = [field for field in required if any(field not in r for r in runners)]
    add("runner_rows", "PASS" if runners else "FAIL", str(len(runners)))
    add("active_epi_values", "PASS" if active else "FAIL", str(len(active)))
    add("missing_without_default", "PASS" if not zero_defaults else "FAIL", f"zero_defaults={len(zero_defaults)} missing={len(missing)}")
    add("typed_epi_fields", "PASS" if not missing_fields else "FAIL", ",".join(missing_fields))
except Exception as exc:
    add("json_load", "FAIL", repr(exc))

add("distribution_csv", "PASS" if DIST.exists() else "FAIL", str(DIST))
write(OUT, checks, ["check", "status", "detail"])
summary = [{"metric": "status", "value": "PASS" if all(r["status"] == "PASS" for r in checks) else "FAIL"}, {"metric": "checks", "value": str(len(checks))}]
write(SUMMARY, summary, ["metric", "value"])
print(summary[0]["value"])
if summary[0]["value"] != "PASS":
    raise SystemExit(1)
