
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"
LIVE = DATA / "edgeiq_race_entry_fact_v1.csv"
RATINGS = DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
OUT_PUBLIC = DATA / "edgeiq_live_entry_historical_rating_coverage_v1.csv"
OUT_DOC = DOC_DIR / "edgeiq_live_entry_historical_rating_coverage_v1.csv"
REPORT = DOC_DIR / "edgeiq_live_entry_historical_rating_coverage_report_v1.md"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

live_fields, live_rows = read_rows(LIVE)
rating_fields, rating_rows = read_rows(RATINGS)
ratings_by_horse = {}
for row in rating_rows:
    horse_id = text(row.get("canonical_horse_id"))
    if not horse_id:
        continue
    ratings_by_horse.setdefault(horse_id, []).append(row)

rows = []
for row in live_rows:
    runner_id = text(row.get("canonical_runner_id"))
    status = text(row.get("declaration_status"))
    scratching = text(row.get("scratching_status"))
    runner_name = text(row.get("runner_name"))
    if scratching.upper() == "SCRATCHED" or status.upper() == "SCRATCHED_ENTRY":
        coverage_status = "SCRATCHED"
    elif status.upper() == "EMERGENCY_ENTRY":
        coverage_status = "EMERGENCY"
    elif runner_id in ratings_by_horse:
        coverage_status = "HISTORICAL_RATING_AVAILABLE"
    elif not runner_id:
        coverage_status = "NO_IDENTITY_MATCH"
    else:
        coverage_status = "INSUFFICIENT_HISTORY"
    rows.append({
        "canonical_race_id": text(row.get("canonical_race_id")),
        "canonical_runner_id": runner_id,
        "race_date": text(row.get("race_date")),
        "canonical_track": text(row.get("canonical_track")),
        "race_number": text(row.get("race_number")),
        "runner_name": runner_name,
        "declaration_status": status,
        "scratching_status": scratching,
        "historical_rating_match_count": len(ratings_by_horse.get(runner_id, [])),
        "coverage_status": coverage_status,
    })

fields = ["canonical_race_id", "canonical_runner_id", "race_date", "canonical_track", "race_number", "runner_name", "declaration_status", "scratching_status", "historical_rating_match_count", "coverage_status"]
write(OUT_PUBLIC, fields, rows)
write(OUT_DOC, fields, rows)
counts = Counter(row["coverage_status"] for row in rows)
active_rows = [row for row in rows if row["coverage_status"] not in {"SCRATCHED", "EMERGENCY"}]
lines = [
    "# EDGEiQ Live Entry Historical Rating Coverage V1",
    "",
    f"Live entries: `{len(rows)}`",
    f"Active live entries: `{len(active_rows)}`",
    f"Horse performance rating rows: `{len(rating_rows)}`",
    f"Live horses with historical ratings: `{counts.get('HISTORICAL_RATING_AVAILABLE', 0)}`",
    f"Live horses without historical ratings: `{len(active_rows) - counts.get('HISTORICAL_RATING_AVAILABLE', 0)}`",
    "",
    "## Status Counts",
]
for key, value in sorted(counts.items()):
    lines.append(f"- `{key}`: {value}")
lines.extend([
    "",
    "## Finding",
    "No live race-entry runner currently matches a governed horse-performance rating because `edgeiq_horse_performance_rating_fact_v1.csv` has zero data rows. Scratched and emergency statuses are preserved separately; active entries are marked `INSUFFICIENT_HISTORY` rather than assigned synthetic ratings.",
])
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({
    "live_entries": len(rows),
    "active_live_entries": len(active_rows),
    "rating_rows": len(rating_rows),
    "counts": dict(counts),
    "public_output": str(OUT_PUBLIC),
    "report": str(REPORT),
}, indent=2))
