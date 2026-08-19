from pathlib import Path
import json
import requests

ROOT = Path(__file__).resolve().parents[1]

OUT = ROOT / "data" / "weather-source-audit" / "turftrax-stream-endpoints"
OUT.mkdir(parents=True, exist_ok=True)

CLIENTS = {
    "caulfield":"https://its.turftrax.co.uk/visualiser/stream/caulfield.html",
    "ladbrokes":"https://its.turftrax.co.uk/visualiser/stream/ladbrokes.html",
    "mornington":"https://its.turftrax.co.uk/visualiser/stream/mornington.html",
}

HEADERS = {
    "User-Agent":"Mozilla/5.0",
    "Accept":"*/*",
    "Referer":"https://its.turftrax.co.uk/",
}

summary=[]

for name,url in CLIENTS.items():

    print(f"[EDGEIQ] Testing {name}")

    record={
        "client":name,
        "url":url
    }

    try:

        r=requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        record["status"]=r.status_code
        record["content_type"]=r.headers.get("Content-Type")
        record["bytes"]=len(r.content)

        preview=r.text[:4000]

        (OUT/f"{name}_response.txt").write_text(
            preview,
            encoding="utf8",
            errors="ignore"
        )

        try:
            js=r.json()

            (OUT/f"{name}_response.json").write_text(
                json.dumps(js,indent=2),
                encoding="utf8"
            )

            record["json"]=True

        except Exception:
            record["json"]=False

        record["preview"]=preview[:250]

    except Exception as exc:

        record["error"]=str(exc)

    summary.append(record)

(OUT/"summary.json").write_text(
    json.dumps(summary,indent=2),
    encoding="utf8"
)

with open(OUT/"EDGEIQ_TURFTRAX_ENDPOINT_TEST.txt","w",encoding="utf8") as f:

    f.write("EDGEIQ TURFTRAX ENDPOINT TEST\n")
    f.write("="*60+"\n\n")

    for row in summary:

        f.write(f"CLIENT : {row['client']}\n")
        f.write(f"URL    : {row['url']}\n")
        f.write(f"STATUS : {row.get('status')}\n")
        f.write(f"TYPE   : {row.get('content_type')}\n")
        f.write(f"BYTES  : {row.get('bytes')}\n")
        f.write(f"JSON   : {row.get('json')}\n")

        if "error" in row:
            f.write(f"ERROR  : {row['error']}\n")

        f.write("\n")
        f.write("-"*60)
        f.write("\n\n")

print()
print("[EDGEIQ] TurfTrax endpoint verification complete")
print("[EDGEIQ] Output:",OUT)
