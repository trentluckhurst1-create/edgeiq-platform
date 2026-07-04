import requests, re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "tab_endpoint_discovery_sandown_v1.txt"

urls = [
    "https://www.tab.com.au/racing/2026-06-13/Sandown/SAN/R/1",
    "https://www.tab.com.au/racing/2026-06-13/Sandown-Hillside/SAN/R/1",
]

headers = {"User-Agent":"Mozilla/5.0"}

lines = []
for u in urls:
    print("GET", u)
    r = requests.get(u, headers=headers, timeout=20)
    lines.append(f"\n===== {u} =====\nSTATUS {r.status_code}\n")
    txt = r.text
    lines.append(txt[:3000])

    for pat in [
        r"api\.beta\.tab\.com\.au[^\"'<> ]+",
        r"/v1/tab-info-service/racing/[^\"'<> ]+",
        r"/racing/dates/[^\"'<> ]+",
        r"tab-info-service[^\"'<> ]+",
        r"raceNumber",
        r"venueMnemonic",
        r"meetingName",
        r"raceType",
    ]:
        hits = re.findall(pat, txt)
        lines.append(f"\nPATTERN {pat}: {len(hits)}\n")
        for h in hits[:40]:
            lines.append(str(h) + "\n")

OUT.write_text("".join(lines), encoding="utf-8")
print("wrote", OUT)
