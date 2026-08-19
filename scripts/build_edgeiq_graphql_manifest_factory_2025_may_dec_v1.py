from __future__ import annotations

import csv
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CANDIDATES = [
    DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv",
    DATA / "edgeiq_vic_historical_backfill_manifest_v1.csv",
]

MONTHS = [
    ("MAY2025", "2025-05"),
    ("JUN2025", "2025-06"),
    ("JUL2025", "2025-07"),
    ("AUG2025", "2025-08"),
    ("SEP2025", "2025-09"),
    ("OCT2025", "2025-10"),
    ("NOV2025", "2025-11"),
    ("DEC2025", "2025-12"),
]

SUMMARY = DATA / "edgeiq_graphql_manifest_factory_2025_may_dec_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def pick_source():
    for p in CANDIDATES:
        if p.exists():
            rows = read_csv(p)
            if rows:
                return p, rows
    raise FileNotFoundError("No usable historical calendar/backfill source found.")

def main():
    built_at = datetime.now(timezone.utc).isoformat()
    src, rows = pick_source()

    summary = []

    for code, ym in MONTHS:
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
                "source": src.name,
                "built_at": built_at,
            }

        out = DATA / f"edgeiq_manifest_{code}.json"
        payload = list(meetings.values())
        payload.sort(key=lambda x: (x["meeting_date"], x["track"], x["meeting_url"]))

        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        summary.append({
            "month_code": code,
            "month": ym,
            "source": str(src),
            "meetings": len(payload),
            "output": str(out),
            "built_at": built_at,
        })

        print(f"[MANIFEST_FACTORY] {code} meetings={len(payload)} output={out}")

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["month_code", "month", "source", "meetings", "output", "built_at"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_MANIFEST_FACTORY_2025_MAY_DEC_V1] COMPLETE")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
