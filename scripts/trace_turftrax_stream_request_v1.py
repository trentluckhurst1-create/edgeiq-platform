from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "weather-source-audit" / "turftrax"

patterns = [
    "streamApi",
    "/visualiser/stream/",
    "client",
    "clientName",
    "updateInterval",
    "$.ajax",
    "fetch(",
    "XMLHttpRequest",
    "axios",
    "FormData",
    "setRequestHeader",
    "poll",
    "stream",
    "responseInterval",
]

for venue in ["caulfield","sandown","mornington"]:
    print("="*80)
    print(venue.upper())
    print("="*80)

    for file in sorted(SRC.joinpath(venue).glob("*")):
        if file.suffix.lower() not in [".js",".html",".txt",".json"]:
            continue

        try:
            text = file.read_text(encoding="utf-8",errors="ignore")
        except:
            continue

        for pattern in patterns:
            for m in re.finditer(re.escape(pattern), text, flags=re.I):
                start=max(0,m.start()-250)
                end=min(len(text),m.end()+500)

                print()
                print("-"*80)
                print(file.name)
                print("Pattern:",pattern)
                print("-"*80)
                print(text[start:end])
                print()

print()
print("[EDGEIQ] JS trace complete")
