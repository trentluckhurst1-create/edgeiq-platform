import csv
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
SOURCES = [
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_command_enrichment_feed_v3.csv",
]
OUT = DATA / "edgeiq_product_shell_sources_v1.csv"
SUMMARY = DATA / "edgeiq_product_shell_sources_v1_summary.csv"
REPORT = DATA / "edgeiq_product_shell_sources_v1_report.txt"

FIELD_SETS = {
    "meeting_date": ["meeting_date", "race_date", "date", "_date"],
    "track": ["track", "_track"],
    "race_no": ["race_no", "race", "_race"],
    "race_time": ["race_time", "jump_time", "start_time"],
    "distance": ["distance", "race_distance", "distance_m"],
    "race_class": ["race_class", "class", "race_type"],
    "race_title": ["race_title", "race_name", "race"],
    "track_condition": ["track_condition", "condition", "going", "official_condition"],
    "rail_position": ["rail_position", "rail", "rail_clean"],
    "meeting_status": ["meeting_status", "dashboard_ready", "ui_status"],
    "market_state": ["market_state", "tab_fixed_betting_status", "market_source_status"],
    "field_ready": ["dashboard_ready", "runner_status", "ui_status"],
}

def read_rows(path):
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, reader.fieldnames or []

def first(row, keys):
    for key in keys:
        value = row.get(key, "")
        if value not in (None, ""):
            return str(value).strip()
    return ""

records = []
summary_rows = []
for source in SOURCES:
    rows, fields = read_rows(source)
    if not source.exists():
        records.append({"source_file": source.name, "status": "SOURCE_MISSING"})
        summary_rows.append({"metric": f"{source.name}_status", "value": "SOURCE_MISSING"})
        continue
    races = set()
    meetings = set()
    ready = {}
    for row in rows:
        date = first(row, FIELD_SETS["meeting_date"])
        track = first(row, FIELD_SETS["track"]).upper()
        race = first(row, FIELD_SETS["race_no"])
        if track and race:
            races.add((date, track, race))
        if track:
            meetings.add((date, track))
    source_record = {
        "source_file": source.name,
        "status": "AVAILABLE",
        "rows": len(rows),
        "meetings": len(meetings),
        "races": len(races),
    }
    for label, keys in FIELD_SETS.items():
        matching = [key for key in keys if key in fields]
        non_blank = sum(1 for row in rows if first(row, keys)) if matching else 0
        source_record[f"has_{label}"] = "YES" if matching else "NO"
        source_record[f"{label}_columns"] = "|".join(matching)
        source_record[f"{label}_non_blank"] = non_blank
    records.append(source_record)

best = max([r for r in records if r.get("status") == "AVAILABLE"], key=lambda r: (int(r.get("races", 0)), int(r.get("rows", 0))), default={})
for key, value in best.items():
    summary_rows.append({"metric": f"best_source_{key}", "value": value})
summary_rows.extend([
    {"metric": "recommended_source", "value": best.get("source_file", "NONE")},
    {"metric": "product_shell_source_status", "value": "READY" if best else "NOT_READY"},
])

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sorted({k for r in records for k in r.keys()}))
    writer.writeheader(); writer.writerows(records)
with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader(); writer.writerows(summary_rows)
REPORT.write_text("EDGEiQ PRODUCT SHELL SOURCE AUDIT V1\n" + "\n".join(f"{r.get('source_file')}: {r.get('status')} rows={r.get('rows','')} races={r.get('races','')} meetings={r.get('meetings','')}" for r in records) + f"\nrecommended_source={best.get('source_file','NONE')}\nstatus={'READY' if best else 'NOT_READY'}\n", encoding="utf-8")
print(REPORT)
