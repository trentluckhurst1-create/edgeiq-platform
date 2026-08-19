import json
import urllib.request

date = "2026-06-17"
codes = [
    "CHT","CAH","CFH","CAU","CFL","CFT",
    "MOR","MORN","MOE",
    "GEE","GEL","GEO",
    "SAL","SAN","SWN","BEN","BAL","PAK"
]

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.tab.com.au/racing",
}

for code in codes:
    url = f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{date}/meetings/R/{code}/races/1?returnPromo=true&returnOffers=true&jurisdiction=NSW"
    print("\n===", code, "===")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.loads(r.read().decode("utf-8"))
        m = payload.get("meeting", {})
        print("OK", m.get("meetingName"), m.get("location"), m.get("venueMnemonic"), "runners", len(payload.get("runners", [])))
    except Exception as e:
        print("FAIL", repr(e))
