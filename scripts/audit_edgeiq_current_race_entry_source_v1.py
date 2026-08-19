from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "race-entry-projection"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TODAY = date(2026, 7, 23)

RACE_FIELDS = ["race_id", "canonical_race_id", "race_key", "race_date", "meeting_date", "date", "track", "track_name", "race_no", "race_number"]
RUNNER_FIELDS = ["race_entry_id", "runner_id", "canonical_runner_id", "horse", "horse_name", "runner_name", "canonical_horse_name", "canonical_horse_id"]
NAME_HINTS = ["race", "runner", "field", "catalog", "meeting", "form", "entries"]
MAX_SAMPLE_ROWS = 50000
MAX_IDENTITY_ROWS = 200


def clean(v):
    return "" if v is None else str(v).strip()


def parse_date(v):
    raw = clean(v)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def best_field(fields, candidates):
    lowered = {f.lower(): f for f in fields}
    for c in candidates:
        if c.lower() in lowered:
            return lowered[c.lower()]
    return ""


def main() -> int:
    source_rows = []
    identity_rows = []
    likely = []
    candidates = [p for p in DATA.glob("*.csv") if any(h in p.name.lower() for h in NAME_HINTS)]
    for path in candidates:
        try:
            h = path.open("r", encoding="utf-8-sig", newline="")
        except Exception:
            continue
        with h:
            reader = csv.DictReader(h)
            fields = list(reader.fieldnames or [])
            if not fields:
                continue
            race_date_field = best_field(fields, ["race_date", "meeting_date", "date"])
            track_field = best_field(fields, ["track_name", "track", "meeting_track"])
            race_no_field = best_field(fields, ["race_no", "race_number", "race"])
            horse_field = best_field(fields, ["canonical_horse_name", "horse_name", "runner_name", "horse"])
            has_shape = bool((race_date_field or "race_id" in fields or "canonical_race_id" in fields or "race_key" in fields) and horse_field)
            if not has_shape:
                continue
            row_count = 0
            race_dates = []
            race_keys = set()
            runner_keys = set()
            canon_race_coverage = 0
            canon_runner_coverage = 0
            sample_identities = []
            for row in reader:
                row_count += 1
                if row_count <= MAX_SAMPLE_ROWS:
                    d = parse_date(row.get(race_date_field)) if race_date_field else None
                    if d:
                        race_dates.append(d)
                    race_key = "|".join([clean(row.get(race_date_field)), clean(row.get(track_field)).upper(), clean(row.get(race_no_field))]) if race_date_field and track_field and race_no_field else clean(row.get("race_id") or row.get("canonical_race_id") or row.get("race_key"))
                    runner_key = clean(row.get("race_entry_id") or row.get("runner_id") or row.get("canonical_runner_id") or row.get("canonical_horse_id") or row.get(horse_field))
                    if race_key.strip("|"):
                        race_keys.add(race_key)
                    if runner_key:
                        runner_keys.add(runner_key)
                    if clean(row.get("canonical_race_id") or row.get("race_id") or row.get("race_key")):
                        canon_race_coverage += 1
                    if clean(row.get("canonical_runner_id") or row.get("runner_id") or row.get("race_entry_id") or row.get("canonical_horse_id")):
                        canon_runner_coverage += 1
                    if len(sample_identities) < MAX_IDENTITY_ROWS:
                        sample_identities.append(row)
                # still count all rows
            future_current = sum(1 for d in race_dates if d >= TODAY)
            past = sum(1 for d in race_dates if d < TODAY)
            status = "CURRENT_OR_FUTURE" if future_current else ("PAST_ONLY" if past else "UNKNOWN_DATE")
            required_present = bool(race_date_field and track_field and race_no_field and horse_field)
            likely_flag = required_present and row_count > 0 and (future_current or "live" in path.name.lower() or "three_day" in path.name.lower() or "catalog" in path.name.lower())
            row_out = {
                "source_file": str(path.relative_to(ROOT)),
                "row_count": row_count,
                "sampled_rows": min(row_count, MAX_SAMPLE_ROWS),
                "race_count_sample": len(race_keys),
                "runner_count_sample": len(runner_keys),
                "date_min_sample": min(race_dates).isoformat() if race_dates else "",
                "date_max_sample": max(race_dates).isoformat() if race_dates else "",
                "date_status_sample": status,
                "required_fields_present": "YES" if required_present else "NO",
                "race_date_field": race_date_field,
                "track_field": track_field,
                "race_no_field": race_no_field,
                "horse_field": horse_field,
                "canonical_race_id_coverage_sample": canon_race_coverage,
                "canonical_runner_id_coverage_sample": canon_runner_coverage,
                "likely_race_entry_source": "YES" if likely_flag else "NO",
            }
            source_rows.append(row_out)
            if likely_flag:
                likely.append(row_out)
                for sample in sample_identities[:50]:
                    identity_rows.append({
                        "source_file": str(path.relative_to(ROOT)),
                        "race_date": clean(sample.get(race_date_field)),
                        "track": clean(sample.get(track_field)),
                        "race_no": clean(sample.get(race_no_field)),
                        "horse": clean(sample.get(horse_field)),
                        "race_id": clean(sample.get("race_id") or sample.get("canonical_race_id") or sample.get("race_key")),
                        "runner_id": clean(sample.get("runner_id") or sample.get("canonical_runner_id") or sample.get("race_entry_id") or sample.get("canonical_horse_id")),
                    })
    source_rows.sort(key=lambda r: (r["likely_race_entry_source"] != "YES", -int(r["row_count"]), r["source_file"]))
    fields_out = ["source_file","row_count","sampled_rows","race_count_sample","runner_count_sample","date_min_sample","date_max_sample","date_status_sample","required_fields_present","race_date_field","track_field","race_no_field","horse_field","canonical_race_id_coverage_sample","canonical_runner_id_coverage_sample","likely_race_entry_source"]
    with (OUT_DIR / "edgeiq_current_race_entry_source_audit_v1.csv").open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields_out); w.writeheader(); w.writerows(source_rows)
    with (OUT_DIR / "edgeiq_current_race_entry_identity_coverage_v1.csv").open("w", encoding="utf-8", newline="") as h:
        fields2 = ["source_file", "race_date", "track", "race_no", "horse", "race_id", "runner_id"]
        w = csv.DictWriter(h, fieldnames=fields2); w.writeheader(); w.writerows(identity_rows)
    canonical_path = DATA / "edgeiq_race_entry_fact_v1.csv"
    canonical_exists = canonical_path.exists()
    canonical_rows = 0
    if canonical_exists:
        with canonical_path.open("r", encoding="utf-8-sig", newline="") as h:
            canonical_rows = sum(1 for _ in csv.DictReader(h))
    current_future_likely = [row for row in likely if row["date_status_sample"] == "CURRENT_OR_FUTURE"]
    conclusion = "NO_ACTIVE_RACE_ENTRIES_AVAILABLE" if not current_future_likely else ("RACE_ENTRY_FACT_BUILDER_OR_PATH_MISSING" if canonical_rows == 0 else "CANONICAL_RACE_ENTRIES_AVAILABLE")
    report = "# Current Race Entry Source Audit V1\n\n"
    report += f"Canonical race-entry fact exists: `{canonical_exists}`\n\n"
    report += f"Canonical race-entry rows: `{canonical_rows}`\n\n"
    report += f"Likely source files with usable race-entry shape: `{len(likely)}`\n\n"
    report += f"Conclusion: `{conclusion}`\n\n"
    report += "## Top likely sources\n\n"
    for row in likely[:20]:
        report += f"- `{row['source_file']}` rows={row['row_count']} races(sample)={row['race_count_sample']} runners(sample)={row['runner_count_sample']} dates(sample)={row['date_min_sample']}..{row['date_max_sample']}\n"
    (OUT_DIR / "edgeiq_current_race_entry_source_report_v1.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":"CURRENT_RACE_ENTRY_SOURCE_AUDIT_WRITTEN", "canonical_rows": canonical_rows, "likely_sources": len(likely), "current_future_likely_sources": len(current_future_likely), "conclusion": conclusion}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


