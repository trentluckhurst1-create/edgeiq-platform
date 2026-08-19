from __future__ import annotations
import csv, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SOURCE = DATA / "edgeiq_vic_historical_backfill_manifest_v1.csv"

MONTHS = [
    ("JAN","01"),("FEB","02"),("MAR","03"),("APR","04"),
    ("MAY","05"),("JUN","06"),("JUL","07"),("AUG","08"),
    ("SEP","09"),("OCT","10"),("NOV","11"),("DEC","12"),
]

def clean(v): return "" if v is None else str(v).strip()

with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

built_at = datetime.now(timezone.utc).isoformat()
summary = []

for year in range(2000, 2023):
    for mon_code, mon_num in MONTHS:
        code = f"{mon_code}{year}"
        ym = f"{year}-{mon_num}"
        meetings = {}

        for r in rows:
            d = clean(r.get("meeting_date"))
            t = clean(r.get("track"))
            u = clean(r.get("meeting_url"))

            if not d.startswith(ym): continue
            if not d or not t or not u: continue

            key = f"{d}|{t}|{u}"
            meetings[key] = {
                "meeting_date": d,
                "track": t,
                "meeting_url": u,
                "source": SOURCE.name,
                "built_at": built_at,
            }

        out = DATA / f"edgeiq_manifest_{code}.json"
        payload = sorted(meetings.values(), key=lambda x: (x["meeting_date"], x["track"]))
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        summary.append({"year": year, "month_code": code, "meetings": len(payload), "output": str(out)})
        print(f"[DEEP_MANIFEST] {code} meetings={len(payload)}")

summary_path = DATA / "edgeiq_graphql_deep_manifest_factory_2000_2022_v1_summary.csv"
with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["year","month_code","meetings","output"])
    w.writeheader()
    w.writerows(summary)

print("[DEEP_MANIFEST_FACTORY] COMPLETE")
print(summary_path)
