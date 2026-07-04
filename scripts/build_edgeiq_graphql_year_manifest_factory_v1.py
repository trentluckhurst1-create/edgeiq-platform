from __future__ import annotations

import csv
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_year_manifest_factory_v1_summary.csv"

MONTHS = [
    ("JAN", "01", "january"),
    ("FEB", "02", "february"),
    ("MAR", "03", "march"),
    ("APR", "04", "april"),
    ("MAY", "05", "may"),
    ("JUN", "06", "june"),
    ("JUL", "07", "july"),
    ("AUG", "08", "august"),
    ("SEP", "09", "september"),
    ("OCT", "10", "october"),
    ("NOV", "11", "november"),
    ("DEC", "12", "december"),
]

YEARS = [2023, 2024, 2026]

def clean(v):
    return "" if v is None else str(v).strip()

def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source: {SOURCE}")

    rows = read_csv(SOURCE)
    built_at = datetime.now(timezone.utc).isoformat()
    summary = []

    for year in YEARS:
        for mon_code, mon_num, mon_name in MONTHS:
            ym = f"{year}-{mon_num}"
            code = f"{mon_code}{year}"

            meetings = {}

            for r in rows:
                meeting_date = clean(r.get("meeting_date"))
                track = clean(r.get("track"))
                meeting_url = clean(r.get("meeting_url"))

                if not meeting_date.startswith(ym):
                    continue
                if not meeting_date or not track or not meeting_url:
                    continue

                key = f"{meeting_date}|{track}|{meeting_url}"
                meetings[key] = {
                    "meeting_date": meeting_date,
                    "track": track,
                    "meeting_url": meeting_url,
                    "source": SOURCE.name,
                    "built_at": built_at,
                }

            payload = list(meetings.values())
            payload.sort(key=lambda x: (x["meeting_date"], x["track"], x["meeting_url"]))

            out = DATA / f"edgeiq_manifest_{code}.json"
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            summary.append({
                "year": year,
                "month_code": code,
                "month": ym,
                "meetings": len(payload),
                "output": str(out),
                "built_at": built_at,
            })

            print(f"[YEAR_MANIFEST_FACTORY] {code} meetings={len(payload)}")

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["year", "month_code", "month", "meetings", "output", "built_at"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_YEAR_MANIFEST_FACTORY_V1] COMPLETE")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
