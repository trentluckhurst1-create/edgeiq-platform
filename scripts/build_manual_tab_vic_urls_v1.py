from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_tab_vic_thoroughbred_urls_v1.csv"

rows = []

meetings = [
    {
        "meeting_date": "2026-06-06",
        "meeting_name": "FLEMINGTON",
        "meeting_slug": "FLEMINGTON",
        "venue_mnemonic": "FLE",
        "location": "VIC",
        "race_type": "R",
        "race_numbers": list(range(1, 10)),
    },
    {
        "meeting_date": "2026-06-06",
        "meeting_name": "SWAN HILL",
        "meeting_slug": "SWAN-HILL",
        "venue_mnemonic": "SWH",
        "location": "VIC",
        "race_type": "R",
        "race_numbers": list(range(1, 10)),
    },
]

for m in meetings:
    for rn in m["race_numbers"]:
        rows.append({
            "meeting_date": m["meeting_date"],
            "meeting_name": m["meeting_name"],
            "location": m["location"],
            "race_type": m["race_type"],
            "venue_mnemonic": m["venue_mnemonic"],
            "race_no": rn,
            "tab_frontend_url": f"https://www.tab.com.au/racing/{m['meeting_date']}/{m['meeting_slug']}/{m['venue_mnemonic']}/{m['race_type']}/{rn}",
        })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

print("[manual_vic_urls] rows", len(df))
print("[manual_vic_urls] wrote", OUT)
print(df.to_string(index=False))
