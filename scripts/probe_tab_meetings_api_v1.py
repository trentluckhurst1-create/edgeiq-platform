from pathlib import Path
import json
import urllib.request
from datetime import datetime

ROOT = Path(".")
OUT = ROOT / "public/data/tab_api_meetings_probe_v1.json"
SUMMARY = ROOT / "public/data/tab_api_meetings_probe_v1_summary.csv"

date = "2026-06-17"

urls = [
    f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{date}/meetings?jurisdiction=NSW",
    f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{date}/meetings/R?jurisdiction=NSW",
    f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{date}/meetings?jurisdiction=VIC",
    f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{date}/meetings/R?jurisdiction=VIC",
]

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.tab.com.au/racing/meetings/today/R",
    "Origin": "https://www.tab.com.au",
}

results = []

for url in urls:
    print("\n[TRY]", url)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=45) as r:
            txt = r.read().decode("utf-8", errors="replace")
            print("[OK]", len(txt))
            results.append({
                "url": url,
                "status": "OK",
                "length": len(txt),
                "text": txt[:500000],
            })
    except Exception as e:
        print("[FAIL]", repr(e))
        results.append({
            "url": url,
            "status": "FAIL",
            "length": 0,
            "error": repr(e),
        })

OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")

with SUMMARY.open("w", encoding="utf-8") as f:
    f.write("checked_at,url,status,length,error\n")
    for x in results:
        f.write(f"{datetime.now().isoformat(timespec='seconds')},{x.get('url','')},{x.get('status','')},{x.get('length',0)},{str(x.get('error','')).replace(',', ' ')}\n")

print("\nWROTE", OUT)
print("WROTE", SUMMARY)
